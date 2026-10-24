"""Tricks Mac test (see tricks/RANKING.md "Next cheap tests" 0 and 1). Apple Silicon, mlx-lm 0.32.x. Stdlib + mlx_lm only; no network
except the model download. Do not rely on the system python3 (Intel/Rosetta); use an arm64 venv:
    python3.12 -m venv ~/venvs/mlx && source ~/venvs/mlx/bin/activate && pip install "mlx-lm>=0.32,<0.33"
Parts (run one model at a time, the Mac has ~32 GB):
    python run_mac.py --part lookup --model MODEL --tag TAG [--no-evidence] [--think off|on] [--batch 8] [--limit N] [--max-tokens N]
        Forced-lookup PopQA-400: evidence from popqa_lookup.jsonl is put in the prompt (--no-evidence = closed-book control).
        Greedy, 64 new tokens. Writes out/rows_TAG.jsonl (resumable: finished ids are skipped) and out/result_TAG.json.
    python run_mac.py --part timing --model MODEL --tag TAG
        300-token maths answer at ~1k and ~8k prompt tokens: one greedy; 8 sampled (T=0.7, top_p=0.8) in ONE batch; the same 8 one by one.
        Writes out/timing_TAG.json. EOS is switched off so every run makes exactly 300 tokens.
--model is a hub id or a local folder. Models found on the HF API (2026-10-24):
    worker: mlx-community/Qwen3.5-4B-4bit   (also: -MLX-4bit, -OptiQ-4bit, -6bit, -8bit, -bf16)
    boss:   LiquidAI/LFM2.5-24B-A2B-MLX-4bit (also -5bit/-6bit/-8bit/-bf16; mlx-community/LFM2.5-24B-A2B-OptiQ-4bit)
    gone from the plan: mlx-community/Qwen3.6-35B-A3B-4bit (and -4bit-DWQ)
Thinking off: Qwen3.5 takes enable_thinking=False in its chat template. LFM2.5-24B-A2B has NO switch: it is a reasoning-only model and
its template always ends the prompt with an open "<think>" (README: "always thinks"). With --think off this script closes the block by
prefill ("<think>" + CLOSE_THINK), which is a hack the model was not trained on (check the [sample] line). Fallbacks: --think on
--max-tokens 1024 (answers after its reasoning; slow), or the instruct predecessor LiquidAI/LFM2-24B-A2B-MLX-4bit (no reasoning).
Any <think>...</think> in an output is stripped before scoring; reasoning that never closes counts as no answer."""
import argparse, json, os, random, re, time
from pathlib import Path

HERE = Path(__file__).parent
LOOK_SYS = "Answer the question in a few words, using the search results."
CLOSED_SYS = "Answer the question in a few words."
CLOSE_THINK = "\n\n</think>\n\n"
TIMING_SYS = "Solve the problem step by step."
TIMING_Q = ("A shop sells pens at 3 for $2 and notebooks at $5 each. Maria buys 12 pens and 4 notebooks and pays with a $50 bill. "
            "How much change does she get? Work through it step by step, then explain how you would check the answer.")
NOUNS = "river stone market engine garden letter winter bridge copper harvest signal window forest ladder anchor valley ribbon lantern meadow harbor".split()
ADJS = "quiet old bright narrow heavy distant early broken simple golden".split()

# ---------------- pure python: scoring, prompts, files ----------------
def popqa_match(text, answers):
    """Any gold alias as a whole word/phrase (so 'US' does not match 'custom'). Same as tricks1.popqa_match."""
    t = (text or "").casefold()
    return any(re.search(r"(?<!\w)" + re.escape(a.casefold()) + r"(?!\w)", t) for a in answers if a.strip())

def strip_think(text, thinking=False):
    """Answer part of a generation. The prompt may already have opened <think>, so only the closing tag is reliable."""
    if "</think>" in text:
        return text.split("</think>")[-1].strip()
    if thinking or text.lstrip().startswith("<think>"):
        return ""  # reasoning that never closed = no answer
    return text.strip()

def build_prompt(tok, system, user, thinking=False):
    """Chat prompt string. Qwen: enable_thinking switch. A template that cannot switch (LFM2.5 always ends in an open '<think>')
    gets its think block closed by prefill when thinking is off."""
    p = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                add_generation_prompt=True, tokenize=False, enable_thinking=thinking)
    if not thinking and p.rstrip().endswith("<think>"):
        p = p.rstrip() + CLOSE_THINK
    return p

def encode(tok, prompt):
    """Token ids; no second BOS when the template already wrote one (same rule as mlx_lm.stream_generate)."""
    return tok.encode(prompt, add_special_tokens=tok.bos_token is None or not prompt.startswith(tok.bos_token))

def user_msg(row, evidence=True):
    return f"Search results:\n{row['evidence']}\n\nQuestion: {row['q']}" if evidence else row["q"]

def read_rows(path):
    """Valid rows of a jsonl file; a torn last line (killed mid-write) is dropped and the file rewritten without it."""
    p, rows, torn = Path(path), [], False
    if p.exists():
        for l in p.read_text().splitlines():
            if l.strip():
                try:
                    rows.append(json.loads(l))
                except ValueError:
                    torn = True
        if torn:
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return rows

def limit_rows(rows, limit):
    if not limit:
        return rows
    h = max(1, limit // 2)
    return [r for r in rows if r["bucket"] == "rare"][:h] + [r for r in rows if r["bucket"] == "pop"][:h]

def summarize(recs, meta):
    n = len(recs)
    acc = lambda rs: sum(r["correct"] for r in rs) / len(rs) if rs else None
    sec, gt, pt = sum(r["sec"] for r in recs), sum(r["gtok"] for r in recs), sum(r["ptok"] for r in recs)
    return {**meta, "n": n, "accuracy": acc(recs),
            "rare_accuracy": acc([r for r in recs if r["bucket"] == "rare"]), "pop_accuracy": acc([r for r in recs if r["bucket"] == "pop"]),
            "mean_gen_tokens": gt / n if n else 0.0, "mean_prompt_tokens": pt / n if n else 0.0, "empty_answers": sum(not r["pred"] for r in recs),
            "wall_seconds": sec, "gen_tok_per_s": gt / sec if sec else 0.0, "prompt_tok_per_s": pt / sec if sec else 0.0}

# ---------------- mlx layer ----------------
def load_model(path):
    import mlx_lm
    t0 = time.time()
    model, tok = mlx_lm.load(os.path.expanduser(path))
    print(f"[load] {path} mlx-lm {mlx_lm.__version__} {time.time() - t0:.0f}s", flush=True)
    return model, tok

def generate_all(model, tok, prompts, max_tokens, batch, sampler, procs=None):
    """Token-id prompts -> [(text, n_generated)]. batch>1: mlx_lm.batch_generate (continuous batching); batch==1: one by one."""
    from mlx_lm import batch_generate, stream_generate
    kw = {"sampler": sampler, **({"logits_processors": procs} if procs else {})}
    if batch > 1:
        r = batch_generate(model, tok, prompts, max_tokens=max_tokens, return_token_ids=True,
                           completion_batch_size=batch, prefill_batch_size=min(batch, 8), **kw)
        return [(t, len(ids)) for t, ids in zip(r.texts, r.token_ids)]
    out = []
    for p in prompts:
        text, n = "", 0
        for resp in stream_generate(model, tok, p, max_tokens=max_tokens, **kw):
            text += resp.text; n = resp.generation_tokens - (resp.finish_reason == "stop")  # stream_generate counts the EOS
        out.append((text, n))
    return out

def run_lookup(a, model, tok):
    import mlx.core as mx
    from mlx_lm.sample_utils import make_logits_processors, make_sampler
    thinking = a.think == "on"
    max_tokens = a.max_tokens or (1024 if thinking else 64)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows_f, res_f = out / f"rows_{a.tag}.jsonl", out / f"result_{a.tag}.json"
    meta = {"model": a.model, "tag": a.tag, "mode": "closed_book" if a.no_evidence else "lookup", "think": a.think,
            "max_tokens": max_tokens, "batch": a.batch, "rep_penalty": a.rep_penalty}
    if res_f.exists():
        old = json.loads(res_f.read_text())
        if any(old.get(k) != meta[k] for k in ("model", "mode", "think", "max_tokens")):
            raise SystemExit(f"[error] tag {a.tag} already holds a different run ({old.get('model')}, {old.get('mode')}); pick a new --tag")
    rows = limit_rows([json.loads(l) for l in Path(a.lookup).open()], a.limit)
    recs = read_rows(rows_f)
    done = {r["id"] for r in recs}
    todo = [r for r in rows if r["id"] not in done]
    print(f"[lookup] {a.tag} {len(rows)} rows, {len(done)} done, {len(todo)} to do", flush=True)
    sysmsg = CLOSED_SYS if a.no_evidence else LOOK_SYS
    sampler = make_sampler(temp=0.0)
    procs = make_logits_processors(repetition_penalty=a.rep_penalty) if a.rep_penalty != 1.0 else None
    mx.random.seed(0)
    for i in range(0, len(todo), 50):
        ch = todo[i:i + 50]
        prompts = [encode(tok, build_prompt(tok, sysmsg, user_msg(r, not a.no_evidence), thinking)) for r in ch]
        t0 = time.perf_counter()
        gens = generate_all(model, tok, prompts, max_tokens, a.batch, sampler, procs)
        dt = time.perf_counter() - t0
        new = []
        for r, p, (text, n) in zip(ch, prompts, gens):
            pred = strip_think(text, thinking)
            new.append({"id": r["id"], "bucket": r["bucket"], "q": r["q"], "gold": r["gold"], "pred": pred, "correct": popqa_match(pred, r["gold"]),
                        "ptok": len(p), "gtok": n, "sec": dt / len(ch), "text": text[-1500:]})
        if i == 0:
            print(f"[sample] prompt ends {tok.decode(prompts[0][-24:])!r}\n[sample] output {gens[0][0][:120]!r} -> {new[0]['pred'][:60]!r}", flush=True)
        with rows_f.open("a") as f:
            f.write("".join(json.dumps(x) + "\n" for x in new))
        recs += new
        print(f"[lookup] {len(recs)}/{len(rows)} acc={sum(r['correct'] for r in recs) / len(recs):.3f} {dt:.0f}s/{len(ch)}", flush=True)
    res = summarize(recs, {**meta, "peak_memory_gb": mx.get_peak_memory() / 1e9})
    res_f.write_text(json.dumps(res, indent=1))
    print(f"[result] {a.tag} acc={res['accuracy']:.3f} rare={res['rare_accuracy']} pop={res['pop_accuracy']} gtok={res['mean_gen_tokens']:.1f} "
          f"ptok={res['mean_prompt_tokens']:.0f} t={res['wall_seconds']:.0f}s {res['gen_tok_per_s']:.1f} tok/s empty={res['empty_answers']}", flush=True)

# ---------------- timing ----------------
def filler_text(tok, n):
    """Fixed pseudo-document of n tokens (seeded word salad; speed does not depend on content)."""
    rng, ids = random.Random(0), []
    while len(ids) < n:
        ids += tok.encode(" ".join(f"The {rng.choice(ADJS)} {rng.choice(NOUNS)} near the {rng.choice(NOUNS)} was {rng.choice(ADJS)} by the {rng.choice(NOUNS)}."
                                   for _ in range(40)) + "\n", add_special_tokens=False)
    return tok.decode(ids[:n])

def timing_prompt(tok, n):
    mk = lambda f: encode(tok, build_prompt(tok, TIMING_SYS, f"Background notes (ignore them):\n{f}\n\n{TIMING_Q}" if f else TIMING_Q))
    return mk(filler_text(tok, max(n - len(mk("")), 1)))

def _rec(wall, pre, toks):
    return {"seconds": round(wall, 2), "prefill_s": round(pre, 2), "decode_s": round(wall - pre, 2), "tokens": toks,
            "tok_s": round(toks / wall, 2), "decode_tok_s": round(toks / max(wall - pre, 1e-9), 2)}

def time_single(model, tok, ids, sampler, n):
    from mlx_lm import stream_generate
    t0 = time.perf_counter(); last = None
    for last in stream_generate(model, tok, ids, max_tokens=n, sampler=sampler):
        pass
    return _rec(time.perf_counter() - t0, last.prompt_tokens / last.prompt_tps, last.generation_tokens)

def time_batch(model, tok, ids, k, sampler, n):
    from mlx_lm import batch_generate
    t0 = time.perf_counter()
    r = batch_generate(model, tok, [ids] * k, max_tokens=n, sampler=sampler, return_token_ids=True, completion_batch_size=k, prefill_batch_size=k)
    return _rec(time.perf_counter() - t0, r.stats.prompt_time, sum(len(t) for t in r.token_ids))

def run_timing(a, model, tok):
    import mlx.core as mx
    from mlx_lm.sample_utils import make_sampler
    greedy, samp, N, K = make_sampler(temp=0.0), make_sampler(temp=0.7, top_p=0.8), 300, 8
    mx.random.seed(0)
    tok.eos_token_ids = set()  # never stop early: every run makes exactly N tokens
    short = timing_prompt(tok, 200)
    time_single(model, tok, short, greedy, 8); time_batch(model, tok, short, 2, samp, 8)  # warm-up (kernel compile)
    res = {"model": a.model, "tag": a.tag, "think": "off", "new_tokens": N, "k": K, "cases": {}}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for label, n in (("1k", 1000), ("8k", 8000)):
        ids = timing_prompt(tok, n)
        c = {"prompt_tokens": len(ids), "single": time_single(model, tok, ids, greedy, N)}
        c["single_via_batch"] = time_batch(model, tok, ids, 1, greedy, N)
        c["batched8"] = time_batch(model, tok, ids, K, samp, N)
        runs = [time_single(model, tok, ids, samp, N) for _ in range(K)]
        c["serial8"] = _rec(sum(r["seconds"] for r in runs), sum(r["prefill_s"] for r in runs), sum(r["tokens"] for r in runs))
        s, b = c["single"], c["batched8"]
        c["ratio_batched8_over_single"] = round(b["seconds"] / s["seconds"], 2)  # RANKING item 0: voting is out if > 6
        c["ratio_batched8_over_single_decode_only"] = round(b["decode_s"] / s["decode_s"], 2)
        c["serial8_over_batched8"] = round(c["serial8"]["seconds"] / b["seconds"], 2)
        c["voting_ok"] = c["ratio_batched8_over_single"] <= 6
        res["cases"][label] = c
        res["peak_memory_gb"] = round(mx.get_peak_memory() / 1e9, 1)
        (out / f"timing_{a.tag}.json").write_text(json.dumps(res, indent=1))
        mx.clear_cache()
        print(f"[timing] {label} ptok={c['prompt_tokens']} single={s['seconds']}s ({s['decode_tok_s']} tok/s) batched8={b['seconds']}s "
              f"({b['decode_tok_s']} tok/s total) serial8={c['serial8']['seconds']}s ratio={c['ratio_batched8_over_single']} "
              f"decode-only={c['ratio_batched8_over_single_decode_only']}", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True, choices=["lookup", "timing"]); ap.add_argument("--model", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--no-evidence", action="store_true"); ap.add_argument("--think", choices=["off", "on"], default="off")
    ap.add_argument("--max-tokens", type=int, default=0); ap.add_argument("--batch", type=int, default=8); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rep-penalty", type=float, default=1.0); ap.add_argument("--lookup", default=str(HERE / "popqa_lookup.jsonl"))
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args()
    model, tok = load_model(a.model)
    (run_lookup if a.part == "lookup" else run_timing)(a, model, tok)

if __name__ == "__main__":
    main()
