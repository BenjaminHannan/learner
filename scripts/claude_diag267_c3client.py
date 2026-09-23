#!/usr/bin/env python3
"""Exp 267 -- C3 answer client (stdlib only, runs on BensPC against the same
llama-server the C1/C2 clients use). Same Qwen3 chat-template transport,
temperature 0.0, n_predict 8 (the answer is one digit). Records raw text + ms.
Reads checks.json [{id, prompt}]; writes {summary, checks: {id: {text, ms}}}.
python claude_diag267_c3client.py --url http://127.0.0.1:8081 --in checks.json --out c3.json"""
import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path

WRAP_PRE = "<|im_start|>user\n"
WRAP_POST = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def post_completion(url, prompt, n_predict=8, timeout=180):
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
    a = ap.parse_args()
    checks = json.loads(Path(a.inp).read_text(encoding="utf-8"))
    out, lat = {}, []
    for c in checks:
        d, ms = post_completion(a.url, c["prompt"])
        text = str(d.get("content", ""))
        lat.append(ms)
        out[str(c["id"])] = dict(text=text, ms=round(ms, 2),
                                 fallback=(not text.strip()))
    summ = dict(n=len(out),
                fallbacks=sum(1 for v in out.values() if v["fallback"]),
                median_ms=round(statistics.median(lat), 1) if lat else None,
                p90_ms=round(sorted(lat)[int(0.9 * len(lat))], 1) if lat else None,
                max_ms=round(max(lat), 1) if lat else None)
    Path(a.out).write_text(json.dumps(dict(summary=summ, checks=out), indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
