#!/usr/bin/env python3
"""lis-319: split the built dev set for the G1 mark (counts only).

dev_single.jsonl = the single-turn dev rows both readers can be scored on (lis-301 dev + chat318_dev);
dev_hist.jsonl   = hist319_dev (report only).
python claude_lis319_devsplit.py --dev WORK/data/dev.jsonl --out WORK/devsplit
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

SINGLE = {"o0b_l2", "opus_dev", "o0a2", "opus301_dev", "chat318_dev"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    c = Counter()
    with open(out / "dev_single.jsonl", "w", encoding="utf-8") as s, open(out / "dev_hist.jsonl", "w", encoding="utf-8") as h:
        for line in Path(a.dev).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["src"] in SINGLE:
                s.write(line + "\n")
                c["single"] += 1
            elif r["src"] == "hist319_dev":
                h.write(line + "\n")
                c["hist"] += 1
            else:
                c["other:" + r["src"]] += 1
    print(json.dumps(dict(c)))


if __name__ == "__main__":
    main()
