#!/usr/bin/env python3
"""Exp 261 -- Qwen entailment-checker client, sealed version (stdlib only).

Transport (fixed before the seal; the semantic question text itself lives in
claude_earcheck261_canon.build_prompt and is unchanged): each prompt is sent
to llama-server /completion wrapped in the model's Qwen3 chat template with
thinking deterministically closed, thinking mode off:

  <|im_start|>user\\n{question}<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n

Request: temperature 0.0, n_predict 1, n_probs 10 (first-token distribution).
p(YES) = pYES/(pYES+pNO), where pYES (pNO) sums exp(logprob) over top tokens
whose stripped uppercase form is YES (NO): YES, " YES", Yes, yes, etc.
Fallback (sealed rule): if neither variant appears, use the greedy text:
YES -> 1.0, NO -> 0.0, anything else -> 0.0 (hold back). Fallbacks counted.

Reads checks.json [{id, prompt}]; writes {summary, checks: {id: {p, text,
fallback, ms}}}.

python claude_earcheck261_checker.py --url http://127.0.0.1:8081 --in checks.json --out pyes.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.request
from pathlib import Path

WRAP_PRE = "<|im_start|>user\n"
WRAP_POST = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def post_completion(url, prompt, timeout=120):
    body = json.dumps({
        "prompt": WRAP_PRE + prompt + WRAP_POST,
        "temperature": 0.0,
        "n_predict": 1,
        "n_probs": 10,
        "cache_prompt": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    ms = (time.perf_counter() - t0) * 1000.0
    return d, ms


def _variants(pos):
    """Yield (norm_text, prob) for first-position candidates, handling the
    llama.cpp shapes: {top_logprobs: [{token, logprob}]} (observed b10679),
    {probs: [{tok_str, prob}]}, or a bare list of those."""
    if isinstance(pos, dict):
        cands = pos.get("top_logprobs", pos.get("probs", pos.get("tokens", [])))
    elif isinstance(pos, list):
        cands = pos
    else:
        return
    for t in cands if isinstance(cands, list) else []:
        if not isinstance(t, dict):
            continue
        s = str(t.get("token", t.get("tok_str", t.get("text", ""))))
        if "logprob" in t:
            try:
                p = math.exp(float(t["logprob"]))
            except (TypeError, ValueError):
                continue
        else:
            try:
                p = float(t.get("prob", 0.0))
            except (TypeError, ValueError):
                continue
        yield s, p


def p_yes(d):
    text = str(d.get("content", ""))
    cps = d.get("completion_probabilities") or []
    py = pn = 0.0
    if cps:
        for s, p in _variants(cps[0]):
            u = s.strip().upper()
            if u == "YES":
                py += p
            elif u == "NO":
                pn += p
    if py + pn > 0:
        return py / (py + pn), text, False
    s = text.strip().upper()
    if s == "YES":
        return 1.0, text, True
    if s == "NO":
        return 0.0, text, True
    return 0.0, text, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    checks = json.loads(Path(a.inp).read_text(encoding="utf-8"))
    out, lat = {}, []
    for c in checks:
        d, ms = post_completion(a.url, c["prompt"])
        p, text, fb = p_yes(d)
        lat.append(ms)
        out[str(c["id"])] = dict(p=round(p, 6), text=text, fallback=fb,
                                 ms=round(ms, 2))
    summ = dict(n=len(out), fallbacks=sum(1 for v in out.values() if v["fallback"]),
                median_ms=round(statistics.median(lat), 1) if lat else None,
                p90_ms=round(sorted(lat)[int(0.9 * len(lat))], 1) if lat else None,
                max_ms=round(max(lat), 1) if lat else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, checks=out), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
