#!/usr/bin/env python3
"""Exp 261 -- Qwen entailment-checker client (stdlib only, runs on BensPC).

Reads checks.json: [{id, prompt}] (prompt built by claude_earcheck261_canon).
POSTs each to llama-server /completion at temperature 0 with n_predict=1 and
n_probs=10, and computes p(YES) = pYES/(pYES+pNO) from the FIRST position's
token distribution (tokens whose stripped uppercase form is YES vs NO).
Fallback (sealed rule): if neither variant is in the top probs, use the greedy
text: YES -> 1.0, NO -> 0.0, anything else -> 0.0 (hold back). The fallback
count is reported.

Writes out.json: {checks: {id: {p: float, text: str, fallback: bool, ms: float}},
                 summary: {...}}.

python claude_earcheck261_qwen.py --url http://127.0.0.1:8081 --in checks.json --out pyes.json
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


def post_completion(url, prompt, timeout=120):
    body = json.dumps({
        "prompt": prompt,
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


def p_yes(d):
    """Return (p, text, fallback) from a /completion response."""
    text = str(d.get("content", ""))
    cps = d.get("completion_probabilities") or []
    py = pn = 0.0
    if cps:
        first = cps[0]
        cand = first.get("probs", first.get("tokens", first if isinstance(first, list) else []))
        if isinstance(cand, dict):
            cand = cand.get("probs", [])
        for t in cand if isinstance(cand, list) else []:
            s = str(t.get("tok_str", t.get("text", ""))).strip().upper()
            try:
                p = float(t.get("prob", 0.0))
            except (TypeError, ValueError):
                continue
            if s == "YES":
                py += p
            elif s == "NO":
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
    import statistics
    summ = dict(n=len(out), fallbacks=sum(1 for v in out.values() if v["fallback"]),
                median_ms=round(statistics.median(lat), 1) if lat else None,
                p90_ms=round(sorted(lat)[int(0.9 * len(lat))], 1) if lat else None,
                max_ms=round(max(lat), 1) if lat else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, checks=out), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
