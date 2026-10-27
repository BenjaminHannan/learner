#!/usr/bin/env python3
"""lis-319: count training/dev rows longer than --max-len tokens with the real tokenizer (counts only).
Training cuts on the right (claude_lis300_train.encode), so a long row loses the end of its target.
Exit code 3 when more than --max-frac of train rows are longer (the task stops before training).
python claude_lis319_lencheck.py --model BASE --data WORK/data --max-len 512 [--max-frac 0.01]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--max-frac", type=float, default=0.01)
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    rep = {}
    for name in ("train", "dev"):
        L, over = [], Counter()
        for line in (Path(a.data) / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            n = 1 + len(tok(r["prompt"], add_special_tokens=False)["input_ids"]) \
                + len(tok(r["target"], add_special_tokens=False)["input_ids"]) + 1
            L.append(n)
            if n > a.max_len:
                over[r["src"]] += 1
        L.sort()
        rep[name] = {"rows": len(L), "max": L[-1], "p99": L[int(0.99 * (len(L) - 1))],
                     "over": sum(over.values()), "over_by_src": dict(over)}
    print(json.dumps(rep, indent=1))
    if rep["train"]["over"] > a.max_frac * rep["train"]["rows"]:
        print(f"STOP: more than {a.max_frac:.0%} of train rows exceed {a.max_len} tokens")
        sys.exit(3)


if __name__ == "__main__":
    main()
