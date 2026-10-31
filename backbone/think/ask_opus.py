#!/usr/bin/env python3
"""One Opus call through the Message Batches API (Ben, Oct 25: batches for Claude calls; Oct 28: result reads go to Opus on the API).

  python3 backbone/think/ask_opus.py PROMPT.md OUT.md [--model claude-opus-5-5] [--max-tokens 8000] [--poll 30] [--timeout 7200]

Reads the prompt file, submits it as a one-request batch with LEARNER_ANTHROPIC_API_KEY, waits for the batch to end, and writes the reply's text to
OUT.md (the batch id goes to OUT.md.batch first, so a stopped wait can be picked up with --resume). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.anthropic.com/v1/messages/batches"
CA = "/root/.ccr/ca-bundle.crt"  # the cloud container's proxy CA; absent elsewhere


def call(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"x-api-key": os.environ["LEARNER_ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    ctx = ssl.create_default_context(cafile=CA) if Path(CA).is_file() else None
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
        return r.read().decode()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("out")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("--timeout", type=int, default=7200)
    ap.add_argument("--resume", action="store_true", help="wait for the batch id saved in OUT.md.batch instead of submitting")
    a = ap.parse_args(argv)
    idf = Path(a.out + ".batch")
    if a.resume:
        bid = idf.read_text().strip()
    else:
        body = {"requests": [{"custom_id": "q", "params": {"model": a.model, "max_tokens": a.max_tokens,
                                                           "messages": [{"role": "user", "content": Path(a.prompt).read_text()}]}}]}
        bid = json.loads(call(API, body))["id"]
        idf.write_text(bid + "\n")
    print(f"[ask_opus] batch {bid}", flush=True)
    t0 = time.time()
    while True:
        b = json.loads(call(f"{API}/{bid}"))
        if b["processing_status"] == "ended":
            break
        if time.time() - t0 > a.timeout:
            print(f"[ask_opus] still {b['processing_status']} after {a.timeout} s; rerun with --resume", file=sys.stderr)
            return 3
        time.sleep(a.poll)
    for line in call(b["results_url"]).splitlines():
        r = json.loads(line)
        if r["custom_id"] != "q":
            continue
        if r["result"]["type"] != "succeeded":
            print(f"[ask_opus] request {r['result']['type']}: {json.dumps(r['result'])[:500]}", file=sys.stderr)
            return 1
        msg = r["result"]["message"]
        Path(a.out).write_text("".join(c.get("text", "") for c in msg["content"] if c.get("type") == "text"))
        print(f"[ask_opus] wrote {a.out} ({msg['usage']['input_tokens']} in, {msg['usage']['output_tokens']} out, {time.time() - t0:.0f} s)", flush=True)
        return 0
    print("[ask_opus] no result for the request", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
