#!/usr/bin/env python3
"""lis-319 panel scorer (counts only; never prints panel text). readpanel319 rows carry facts with needs_history.
Same rules as claude_lis318_score.py (per-fact release at T, owner + value matching), plus the split:
  R0_hist / gold_hist        gold facts with needs_history = true found in the greedy read (saving mode, no gate)
  R0_local / gold_local      the other gold facts
python claude_lis319_score.py --panel panel.jsonl --reads reads.jsonl --threshold T [--out OUT.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis317_gates import e2e_match  # noqa: E402
from claude_lis318_score import load, score  # noqa: E402

WRITABLE = {"ASSERT", "CORRECT"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    panel, reads = load(a.panel), load(a.reads)
    res = score(panel, reads, a.threshold)
    rd = {r["id"]: r for r in reads}
    for k in ("gold_hist", "R0_hist", "gold_local", "R0_local"):
        res[k] = 0
    for row in panel:
        facts = [f for f in ((rd.get(row["id"]) or {}).get("frame") or {}).get("facts") or [] if isinstance(f, dict)]
        for g in row["facts"]:
            tag = "hist" if g.get("needs_history") else "local"
            res["gold_" + tag] += 1
            if any(e2e_match(f, g) and str(f.get("mode", "")).upper() in WRITABLE for f in facts):
                res["R0_" + tag] += 1
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
