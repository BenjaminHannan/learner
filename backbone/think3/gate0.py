"""Gate 0 of backbone/think3/PREREG.md: does K2-Horizon-3.7B do better on village rows with thinking ON (reasoning_effort low) than OFF?

  # Gate 0 proper (both arms, first 1,000 validation rows)
  python backbone/think3/gate0.py --data out/data --split validation --limit 1000 --out out/think3/gate0
  # teacher traces (thinking on, keep only exact-correct)
  python backbone/think3/gate0.py --data out/data --traces --split train --limit 4000 --out out/think3/traces

Offline vLLM (LLM.generate), greedy. The chat template is templates/k2_nothink.jinja (swap-1 patch: default = thinking off; reasoning_effort
"low" opens `<ifm|think_faster>`). The reasoning split is done here on the raw text (same regex as swap/k2_shim.py), not by vLLM's
reasoning parser, because LLM.generate does not run one. Scoring is train.normalise exact match on the final answer only.
The village `test` split is never read (--split is restricted to train / dev / validation).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import train as T  # noqa: E402

TEMPLATE_PATH = HERE / "templates" / "k2_nothink.jinja"
MODEL_ID = "IFM/K2-Horizon-3.7B"
EFFORT_ON = "low"
G0_MARGIN = 0.08  # PREREG: on - off >= 8 points
STOP = "<|ifm|im_end|>"
INSTRUCTION = "Answer with just the answer phrase, nothing else."
THINK_END = re.compile(r"</ifm\|think(?:_fast|_faster)?>")
SPLITS = ("train", "dev", "validation")


# ---------------------------------------------------------------- pure parts

def build_user_message(row) -> str:
    """Context, then the question (as in the backbone village prompts: context + newline + question), then the answer-format instruction."""
    head = (row["context"] + "\n") if row.get("context") else ""
    return f"{head}{row['question']}\n\n{INSTRUCTION}"


def split_think(text: str):
    """Raw generation of a thinking-on prompt (which already opened the think block) -> (think_text, answer_text, closed).
    closed False = the think block never ended (cut off at max_tokens): answer_text is ''."""
    text = text.replace(STOP, "")
    m = THINK_END.search(text)
    if not m:
        return text.strip(), "", False
    return text[:m.start()].strip(), text[m.end():].strip(), True


def clean_answer(text: str) -> str:
    """The answer phrase: first non-empty line, with the stop string and any stray think tags removed."""
    text = THINK_END.sub("", text.replace(STOP, "")).replace("<ifm|think>", "")
    for line in text.strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


def extract_off(text: str) -> str:
    return clean_answer(text)


def extract_on(text: str):
    """-> (think_text, answer, truncated). Only the part after the closing think tag is the answer."""
    think, ans, closed = split_think(text)
    return think, (clean_answer(ans) if closed else ""), not closed


def is_hit(pred: str, gold: str) -> bool:
    return bool(pred) and T.normalise(pred) == T.normalise(gold)


def pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]


def tok_stats(xs):
    if not xs:
        return dict(mean=None, median=None, p95=None, max=None)
    return dict(mean=sum(xs) / len(xs), median=statistics.median(xs), p95=pct(xs, 0.95), max=max(xs))


def g0_decision(hits_off, hits_on):
    n = len(hits_off)
    acc_off, acc_on = sum(hits_off) / n, sum(hits_on) / n
    gap = acc_on - acc_off
    return dict(acc_off=acc_off, acc_on=acc_on, gap=gap, g0_pass=bool(gap >= G0_MARGIN - 1e-12))


def filter_traces(rows, think_texts, answers, n_think, truncated):
    """Keep exact-correct, non-truncated thinking-on generations as trace records."""
    out = []
    for r, th, a, n, tr in zip(rows, think_texts, answers, n_think, truncated):
        if not tr and is_hit(a, r["answer"]):
            out.append(dict(id=r["id"], prompt=build_user_message(r), think_text=th, answer=a, n_think_tokens=n))
    return out


def pick_model_len(prompt_lens, max_new, cap):
    """max_model_len = longest prompt + max_new (+ small slack), capped. Rows whose prompt + max_new exceeds the cap are skipped.
    -> (max_model_len, set of skipped row positions)."""
    need = max(prompt_lens) + max_new + 16 if prompt_lens else max_new + 16
    mml = min(need, cap)
    return mml, {i for i, n in enumerate(prompt_lens) if n + max_new + 16 > mml}


# ---------------------------------------------------------------- model side

def render(tok, template, row, effort):
    kw = {"reasoning_effort": effort} if effort else {}
    msgs = [{"role": "user", "content": build_user_message(row)}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, chat_template=template, **kw)


def generate(llm, tok, template, rows, effort, max_tokens, skip):
    from vllm import SamplingParams
    sp = SamplingParams(temperature=0.0, max_tokens=max_tokens, stop=[STOP], skip_special_tokens=False)  # keep the think tags: split_think needs them
    idx = [i for i in range(len(rows)) if i not in skip]
    prompts = [{"prompt_token_ids": tok(render(tok, template, rows[i], effort), add_special_tokens=False)["input_ids"]} for i in idx]
    outs = llm.generate(prompts, sp)
    res = {}
    for i, o in zip(idx, outs):
        c = o.outputs[0]
        res[i] = dict(text=c.text, n_out=len(c.token_ids), finish=c.finish_reason)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="out/data", help="dir with train.jsonl dev.jsonl validation.jsonl")
    ap.add_argument("--split", default="validation", choices=SPLITS)
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--traces", action="store_true", help="thinking-on only; write correct traces (jsonl) + summary instead of the two-arm score")
    ap.add_argument("--out", default="out/think3/gate0")
    ap.add_argument("--model", default=MODEL_ID)
    ap.add_argument("--max-tokens-on", type=int, default=2048)
    ap.add_argument("--max-tokens-off", type=int, default=48)
    ap.add_argument("--max-model-len-cap", type=int, default=8192, help="rows needing more than this (prompt + max tokens) are skipped and scored wrong")
    ap.add_argument("--gpu-util", type=float, default=0.90)
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--model-impl", default=None, help="e.g. transformers, if the native vLLM implementation fails")
    a = ap.parse_args(argv)

    from transformers import AutoTokenizer
    from vllm import LLM
    template = TEMPLATE_PATH.read_text()
    rows = T.read_jsonl(Path(a.data) / f"{a.split}.jsonl", limit=a.limit)
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    plen = [len(tok(render(tok, template, r, EFFORT_ON), add_special_tokens=False)["input_ids"]) for r in rows]
    max_new = a.max_tokens_on if a.traces else max(a.max_tokens_on, a.max_tokens_off)
    mml, skip = pick_model_len(plen, max_new, a.max_model_len_cap)
    print(f"[gate0] {len(rows)} rows, prompt tokens p50 {pct(plen, .5)} p99 {pct(plen, .99)} max {max(plen)}; max_model_len {mml}; skipped {len(skip)}", flush=True)
    kw = dict(model=a.model, trust_remote_code=True, dtype="bfloat16", max_model_len=mml, gpu_memory_utilization=a.gpu_util,
              enable_prefix_caching=True, max_num_seqs=a.max_num_seqs)
    if a.model_impl:
        kw["model_impl"] = a.model_impl
    llm = LLM(**kw)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    prompt_info = dict(prompt_tokens_p50=pct(plen, .5), prompt_tokens_p99=pct(plen, .99), prompt_tokens_max=max(plen), max_model_len=mml, n_skipped_too_long=len(skip))

    t0 = time.time()
    g_on = generate(llm, tok, template, rows, EFFORT_ON, a.max_tokens_on, skip)
    parsed = []  # per row: (think, answer, truncated, n_think, n_ans)
    for i in range(len(rows)):
        if i in skip:
            parsed.append(("", "", True, 0, 0))
            continue
        think, ans, trunc = extract_on(g_on[i]["text"])
        if g_on[i]["finish"] == "length":
            trunc = True
        parsed.append((think, ans, trunc, len(tok(think, add_special_tokens=False)["input_ids"]) if think else 0,
                       len(tok(ans, add_special_tokens=False)["input_ids"]) if ans else 0))
    hits_on = [is_hit(p[1], r["answer"]) and not p[2] for p, r in zip(parsed, rows)]
    n_trunc = sum(p[2] for i, p in enumerate(parsed) if i not in skip)

    if a.traces:
        traces = filter_traces(rows, [p[0] for p in parsed], [p[1] for p in parsed], [p[3] for p in parsed], [p[2] for p in parsed])
        (out / "traces.jsonl").write_text("".join(json.dumps(t) + "\n" for t in traces))
        summ = dict(split=a.split, n_rows=len(rows), n_correct_kept=len(traces), frac_correct=len(traces) / len(rows), n_truncated=n_trunc,
                    n_wrong_closed=len(rows) - len(skip) - n_trunc - len(traces), think_tokens_kept=tok_stats([t["n_think_tokens"] for t in traces]),
                    max_tokens_on=a.max_tokens_on, seconds=time.time() - t0, **prompt_info)
        (out / "traces_summary.json").write_text(json.dumps(summ, indent=1))
        print(json.dumps(summ, indent=1))
        return 0

    g_off = generate(llm, tok, template, rows, None, a.max_tokens_off, skip)
    preds_off = ["" if i in skip else extract_off(g_off[i]["text"]) for i in range(len(rows))]
    hits_off = [is_hit(p, r["answer"]) for p, r in zip(preds_off, rows)]
    dec = g0_decision(hits_off, hits_on)
    res = dict(model=a.model, split=a.split, n=len(rows), reasoning_effort_on=EFFORT_ON, **dec, g0_margin=G0_MARGIN,
               n_truncated_on=n_trunc, max_tokens_on=a.max_tokens_on,
               think_tokens_on=tok_stats([p[3] for p in parsed]), answer_tokens_on=tok_stats([p[4] for p in parsed]),
               out_tokens_on=tok_stats([g_on[i]["n_out"] for i in g_on]), seconds=time.time() - t0, **prompt_info,
               ids=[r["id"] for r in rows], hits_off=hits_off, hits_on=hits_on)
    (out / "gate0.json").write_text(json.dumps(res))
    print(json.dumps({k: v for k, v in res.items() if k not in ("ids", "hits_off", "hits_on")}, indent=1))
    print(f"[gate0] G0 {'PASS' if dec['g0_pass'] else 'FAIL'}: off {dec['acc_off']:.3f} on {dec['acc_on']:.3f} gap {dec['gap'] * 100:+.1f} pts", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
