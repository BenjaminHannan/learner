#!/usr/bin/env python3
"""Exp 264 -- Qwen QA-checker client (stdlib only, runs on BensPC).

Reads checks.json [{id, prompt, q}] (q in value/owner/relation; prompt built by
claude_earcheck264_qa). POSTs each to llama-server /completion wrapped in the
Qwen3 chat template with thinking deterministically closed (same transport as
261's sealed checker), temperature 0.0, n_predict 32, and records the raw text
answer. The three questions for one frame are sent one after another (sequential).

Writes out.json: {checks: {id: {text, ms}}, summary: {...}}.
Fallback: empty text -> "" (counts as a hold downstream; fallbacks counted).

python claude_earcheck264_client.py --url http://127.0.0.1:8081 --in checks.json --out qa.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path

WRAP_PRE = "<|im_start|>user\n"
WRAP_POST = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def post_completion(url, prompt, n_predict=32, timeout=180):
    body = json.dumps({
        "prompt": WRAP_PRE + prompt + WRAP_POST,
        "temperature": 0.0,
        "n_predict": n_predict,
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-predict", type=int, default=32)
    a = ap.parse_args()
    checks = json.loads(Path(a.inp).read_text(encoding="utf-8"))
    out, lat = {}, []
    for c in checks:
        d, ms = post_completion(a.url, c["prompt"], n_predict=a.n_predict)
        text = str(d.get("content", ""))
        lat.append(ms)
        out[str(c["id"])] = dict(text=text, q=c.get("q"),
                                 fallback=(not text.strip()),
                                 ms=round(ms, 2))
    summ = dict(n=len(out),
                fallbacks=sum(1 for v in out.values() if v["fallback"]),
                median_ms=round(statistics.median(lat), 1) if lat else None,
                p90_ms=round(sorted(lat)[int(0.9 * len(lat))], 1) if lat else None,
                max_ms=round(max(lat), 1) if lat else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, checks=out), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
