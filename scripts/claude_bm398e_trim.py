#!/usr/bin/env python3
"""bm-398e, a copy-only span trimmer (benchmarks thread, 2026-09-26). Plan and marks:
artifacts/claude-bm398e-20260926/PLAN.md. Problem #4 (answers too long), without changing the model.

The plain MiniCPM5-1B writes its normal answer (T's LoCoMo replies, untouched). The trimmer then replaces the
scored first line with one contiguous span of that same line, so it can only copy the model's own words, in
order, with nothing deleted from the middle. Which span: the same plain 1B scores every candidate span (1 to
MAX_SPAN words, plus the whole line) as the short answer to the question, given only the question and the line:
    score = log P(span tokens, then <|im_end|> | prompt) + LAMBDA * words + BETA * [span is the whole line]
LAMBDA (a per-word bonus) and BETA (a keep-whole bonus) are the only fitted numbers. They are fitted on the plain
1B's own drafts to code-made chats (claude_bm398e_data.py), never on LoCoMo. Lines of at most KEEP_WORDS words are
kept whole. Nothing is trained; GSM8K and MMLU never pass through the trimmer.

  python -B scripts/claude_bm398e_trim.py drafts --made MADE.json --model BASE --out DRAFTS.jsonl
  python -B scripts/claude_bm398e_trim.py spans  --data DATA --replies REPLIES.jsonl --model BASE --out SPANS.jsonl
                                                  [--made MADE.json]   (question source: made-up chats, else LoCoMo)
  python -B scripts/claude_bm398e_trim.py fit    --made MADE.json --spans SPANS.jsonl --replies DRAFTS.jsonl --out PARAMS.json
  python -B scripts/claude_bm398e_trim.py apply  --spans SPANS.jsonl --params PARAMS.json --replies REPLIES.jsonl --out TRIMMED.jsonl
  python -B scripts/claude_bm398e_trim.py score  --data DATA --t T.jsonl --tt TRIMMED.jsonl
  python -B scripts/claude_bm398e_trim.py selftest
SPANS rows hold each candidate's text and score parts; they contain reply text, so keep them outside the repository.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402
import claude_bm390_score as SC  # noqa: E402

MAX_SPAN = 10
MAX_WORDS = 40          # only the first 40 words of the line are split into candidates (the whole line stays one)
KEEP_WORDS = 3
BATCH = 24
END_TOKEN = "<|im_end|>"
TRIM_SYSTEM = "You are a helpful assistant."
TRIM_USER = ("Question: {q}\nLong answer: {line}\n\n"
             "Copy the shortest part of the long answer that fully answers the question.")
LAMBDAS = [x / 4 for x in range(-8, 17)]        # -2.0 .. 4.0 in steps of 0.25
BETAS = [x / 2 for x in range(-8, 17)]          # -4.0 .. 8.0 in steps of 0.5
FIT_SPLIT = 0.5                                 # first half of the made-up conversations fit; the second half checks
BOOT_SEED, BOOT_N = 3984, 10000


def _jsonl(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def first_line(reply: str) -> str:
    """The line claude_bm390_score.official_clean scores, before its lower-casing."""
    answer = reply.replace('\\"', "'").strip()
    lines = [w.strip() for w in answer.split("\n") if not w.strip().isspace()]
    return lines[0] if lines else ""


def candidates(line: str) -> list[tuple[str, int, bool]]:
    """(span text, words, whole?) for every contiguous span of 1..MAX_SPAN words within the first MAX_WORDS words,
    edge punctuation stripped, plus the whole line. Duplicates dropped, first kept."""
    words = [m for m in re.finditer(r"\S+", line)][:MAX_WORDS]
    out, seen = [(line, len(line.split()), True)], {line}
    for i in range(len(words)):
        for j in range(i, min(len(words), i + MAX_SPAN)):
            span = line[words[i].start():words[j].end()].strip(" \t\"'.,;:!?()[]")
            if span and span not in seen:
                seen.add(span)
                out.append((span, j - i + 1, False))
    return out


def _load(model_dir: str):
    tok, model, dev, _ = B.plain_model(model_dir)
    return tok, model, dev


def span_logprobs(model_dir: str, question: str, line: str, spans: list[str]) -> list[tuple[float, int]]:
    """For each span: (log P(span tokens + end token | prompt), number of span tokens)."""
    import torch
    tok, model, dev = _load(model_dir)
    end_id = tok.convert_tokens_to_ids(END_TOKEN)
    prompt = B._ids(tok, TRIM_SYSTEM, TRIM_USER.format(q=question, line=line))["input_ids"][0].tolist()
    seqs = [tok(s, add_special_tokens=False)["input_ids"] + [end_id] for s in spans]
    out: list[tuple[float, int]] = []
    pad = tok.pad_token_id if tok.pad_token_id is not None else end_id
    for k in range(0, len(seqs), BATCH):
        chunk = seqs[k:k + BATCH]
        width = len(prompt) + max(len(s) for s in chunk)
        ids = torch.full((len(chunk), width), pad, dtype=torch.long)
        mask = torch.zeros((len(chunk), width), dtype=torch.long)
        for r, s in enumerate(chunk):
            full = prompt + s
            ids[r, :len(full)] = torch.tensor(full)
            mask[r, :len(full)] = 1
        with torch.no_grad():
            logits = model(input_ids=ids.to(dev), attention_mask=mask.to(dev)).logits.float()
        logp = torch.log_softmax(logits, dim=-1)
        for r, s in enumerate(chunk):
            pos = torch.arange(len(prompt) - 1, len(prompt) - 1 + len(s))
            lp = logp[r, pos, torch.tensor(s)].sum().item()
            out.append((lp, len(s) - 1))
    return out


def pick(cands: list[dict], lam: float, beta: float) -> dict:
    return max(cands, key=lambda c: (c["lp"] + lam * c["words"] + beta * c["whole"], -c["i"]))


def _questions(a) -> dict:
    """qid -> (question, gold, category, conversation id), from made-up chats or LoCoMo."""
    out = {}
    if a.made:
        convs = json.loads(Path(a.made).read_text(encoding="utf-8"))
    else:
        convs = B.load_locomo(Path(a.data), "")
    for c in convs:
        for i, qa in enumerate(c["qa"]):
            out[f"{c['sample_id']}#{i}"] = (qa["question"], qa.get("answer", ""), qa["category"], c["sample_id"])
    return out


def drafts(a) -> int:
    convs = json.loads(Path(a.made).read_text(encoding="utf-8"))
    rows, t0 = [], time.time()
    for c in convs:
        ctx = B.full_context(c)
        for i, qa in enumerate(c["qa"]):
            user = ctx + "\n\n" + B.QA_PROMPT.format(B.question_text(c["sample_id"], i, qa))
            reply, n = B.generate(a.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
            rows.append({"qid": f"{c['sample_id']}#{i}", "category": qa["category"], "reply": reply,
                         "prompt_tokens": n})
        print(f"[bm398e] drafts {len(rows)} seconds={time.time() - t0:.0f}", flush=True)
    B._write(Path(a.out), rows)
    return 0


def spans(a) -> int:
    qs = _questions(a)
    done = {}
    out = Path(a.out)
    if out.exists():                       # resume
        done = {r["qid"]: r for r in _jsonl(out)}
    t0, n = time.time(), 0
    with out.open("a", encoding="utf-8") as f:
        for r in _jsonl(a.replies):
            q, gold, cat, _conv = qs[r["qid"]]
            if cat not in (1, 2, 3, 4) or r["qid"] in done:
                continue
            line = first_line(r["reply"])
            row = {"qid": r["qid"], "category": cat, "line_words": len(line.split()), "cands": []}
            if len(line.split()) > KEEP_WORDS:
                cs = candidates(line)
                lps = span_logprobs(a.model, q, line, [c[0] for c in cs])
                row["cands"] = [{"i": i, "text": c[0], "words": c[1], "whole": int(c[2]), "lp": round(lp, 4),
                                 "tokens": nt} for i, (c, (lp, nt)) in enumerate(zip(cs, lps))]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 50 == 0:
                print(f"[bm398e] spans {n} seconds={time.time() - t0:.0f}", flush=True)
    print(f"[bm398e] spans done {n} new seconds={time.time() - t0:.0f}", flush=True)
    return 0


def _f1(pred: str, gold, cat: int) -> float:
    return SC.official_score(SC.official_clean(pred, cat, None), gold, cat)


def fit(a) -> int:
    qs = _questions(a)
    rows = _jsonl(a.spans)
    convs = sorted({qs[r["qid"]][3] for r in rows})
    fit_convs = set(convs[: int(len(convs) * FIT_SPLIT)])
    part = {"fit": [r for r in rows if qs[r["qid"]][3] in fit_convs],
            "check": [r for r in rows if qs[r["qid"]][3] not in fit_convs]}

    def mean_f1(rs, lam, beta) -> float:
        tot = 0.0
        for r in rs:
            _q, gold, cat, _c = qs[r["qid"]]
            text = pick(r["cands"], lam, beta)["text"] if r["cands"] else None
            tot += _f1(text, gold, cat) if text is not None else r["_keep"]
        return 100 * tot / max(1, len(rs))

    # rows with no candidates keep their line: score them once
    lines = {r["qid"]: r for r in _jsonl(a.replies)}
    for r in rows:
        _q, gold, cat, _c = qs[r["qid"]]
        r["_keep"] = _f1(first_line(lines[r["qid"]]["reply"]), gold, cat)
    grid = [(mean_f1(part["fit"], lam, beta), lam, beta) for lam in LAMBDAS for beta in BETAS]
    best = max(grid, key=lambda x: (round(x[0], 6), -abs(x[1]), -abs(x[2])))
    res = {"lambda": best[1], "beta": best[2], "fit_f1": round(best[0], 2),
           "fit_f1_untrimmed": round(100 * sum(r["_keep"] for r in part["fit"]) / max(1, len(part["fit"])), 2),
           "check_f1": round(mean_f1(part["check"], best[1], best[2]), 2),
           "check_f1_untrimmed": round(100 * sum(r["_keep"] for r in part["check"]) / max(1, len(part["check"])), 2),
           "n_fit": len(part["fit"]), "n_check": len(part["check"]), "fit_convs": sorted(fit_convs)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "fit_convs"}))
    return 0


def apply(a) -> int:
    p = json.loads(Path(a.params).read_text(encoding="utf-8"))
    sp = {r["qid"]: r for r in _jsonl(a.spans)}
    out = []
    for r in _jsonl(a.replies):
        s = sp.get(r["qid"])
        reply = pick(s["cands"], p["lambda"], p["beta"])["text"] if s and s["cands"] else r["reply"]
        out.append({"qid": r["qid"], "category": r.get("category"), "reply": reply,
                    "trimmed": bool(s and s["cands"])})
    B._write(Path(a.out), out)
    print(json.dumps({"rows": len(out), "trimmed": sum(x["trimmed"] for x in out)}))
    return 0


def _boot(qids: list[str], diff: dict) -> list[float]:
    conv = defaultdict(list)
    for q in qids:
        conv[q.split("#")[0]].append(diff[q])
    cs = sorted(conv)
    rng = random.Random(BOOT_SEED)
    ds = []
    for _ in range(BOOT_N):
        vals = [x for c in (rng.choice(cs) for _ in cs) for x in conv[c]]
        ds.append(100 * sum(vals) / len(vals))
    ds.sort()
    return [round(ds[int(0.025 * BOOT_N)], 2), round(ds[int(0.975 * BOOT_N) - 1], 2)]


def score(a) -> int:
    qs = _questions(a)
    t = {r["qid"]: r["reply"] for r in _jsonl(a.t)}
    tt = {r["qid"]: r["reply"] for r in _jsonl(a.tt)}
    ids = sorted(q for q in t if qs[q][2] in (1, 2, 3, 4))
    ft = {q: _f1(t[q], qs[q][1], qs[q][2]) for q in ids}
    ftt = {q: _f1(tt[q], qs[q][1], qs[q][2]) for q in ids}
    res = {"n": len(ids), "T_f1": round(100 * sum(ft.values()) / len(ids), 2),
           "TT_f1": round(100 * sum(ftt.values()) / len(ids), 2)}
    res["TT_minus_T"] = round(res["TT_f1"] - res["T_f1"], 2)
    res["ci95_by_conversation"] = _boot(ids, {q: ftt[q] - ft[q] for q in ids})
    res["by_category"] = {c: {"n": sum(qs[q][2] == c for q in ids),
                              "T": round(100 * sum(ft[q] for q in ids if qs[q][2] == c) / max(1, sum(qs[q][2] == c for q in ids)), 2),
                              "TT": round(100 * sum(ftt[q] for q in ids if qs[q][2] == c) / max(1, sum(qs[q][2] == c for q in ids)), 2)}
                          for c in (1, 2, 3, 4)}
    res["by_half"] = {}
    convs = sorted({q.split("#")[0] for q in ids})
    for name, cs in (("first5", set(convs[:5])), ("last5", set(convs[5:]))):
        qq = [q for q in ids if q.split("#")[0] in cs]
        res["by_half"][name] = {"T": round(100 * sum(ft[q] for q in qq) / len(qq), 2),
                                "TT": round(100 * sum(ftt[q] for q in qq) / len(qq), 2)}
    res["median_words"] = {"T": statistics.median(len(first_line(t[q]).split()) for q in ids),
                           "TT": statistics.median(len(first_line(tt[q]).split()) for q in ids)}
    res["gained"] = sum(ftt[q] > ft[q] for q in ids)
    res["lost"] = sum(ftt[q] < ft[q] for q in ids)
    res["lost_all_overlap"] = sum(ft[q] > 0 and ftt[q] == 0 for q in ids)
    print(json.dumps(res))
    return 0


def selftest(_a) -> int:
    ok = {}
    c = candidates('Varo moved to "Varnholt, the harbour town."')
    texts = [x[0] for x in c]
    ok["whole line is the first candidate"] = c[0][2] and c[0][0] == 'Varo moved to "Varnholt, the harbour town."'
    ok["edge punctuation stripped"] = "Varnholt" in texts and "Varnholt, the harbour town" in texts
    ok["no candidate skips a word"] = all(t in 'Varo moved to "Varnholt, the harbour town."' for t in texts)
    ok["spans capped at MAX_SPAN words"] = all(n <= MAX_SPAN for _t, n, w in candidates(" ".join(["w"] * 30)) if not w)
    ok["first_line matches the scorer"] = SC.official_clean("A b\nC d", 4, None) == first_line("A b\nC d").lower()
    cs = [{"i": 0, "text": "whole line here", "words": 3, "whole": 1, "lp": -9.0},
          {"i": 1, "text": "here", "words": 1, "whole": 0, "lp": -2.0}]
    ok["pick prefers the higher score"] = pick(cs, 0.0, 0.0)["text"] == "here"
    ok["the keep-whole bonus can keep the line"] = pick(cs, 0.0, 8.0)["text"] == "whole line here"
    ok["the word bonus favours longer spans"] = pick(cs, 4.0, 0.0)["text"] == "whole line here"
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398E-TRIM-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["drafts", "spans", "fit", "apply", "score", "selftest"])
    for k in ("data", "made", "model", "out", "replies", "spans", "params", "t", "tt"):
        ap.add_argument("--" + k, default="")
    a = ap.parse_args()
    return {"drafts": drafts, "spans": spans, "fit": fit, "apply": apply, "score": score,
            "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
