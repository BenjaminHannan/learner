#!/usr/bin/env python3
"""bm-391 report-only diagnostic: are an arm's LoCoMo answers wrong, or too long? (benchmarks thread, 2026-09-26)

For each arm, over categories 1-4 it prints: the median reply length in scored words, the mean token precision and
mean token recall against the gold answer, the number of replies at least 3x the gold length, and the F1 the sealed
scorer's own functions give (a check that the numbers line up with claude_bm390_score.py). The reply is cleaned
with official_clean and the gold with official_score's rule, so the words compared are exactly the scored words.
Counts only; nothing is quoted.

  python -B scripts/claude_bm391_prf.py --data DATA --runs RUNDIR --arms T,Q2,E,ER
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390_score as SC  # noqa: E402


def _rows(runs: Path, arm: str) -> list[dict]:
    files = sorted(glob.glob(str(runs / f"locomo_{arm}.jsonl"))) or \
        sorted(glob.glob(str(runs / f"locomo_{arm}.part*.jsonl")))
    if not files:
        raise SystemExit(f"bm391-prf: no locomo_{arm} file in {runs}")
    return [json.loads(line) for f in files for line in open(f, encoding="utf-8") if line.strip()]


def _toks(s: str) -> list[str]:
    return [SC.ps.stem(w) for w in SC.normalize_answer(s).split()]


def arm_stats(gold: dict, rows: list[dict]) -> dict:
    words, prec, rec, f1s = [], [], [], []
    long3 = 0
    for r in rows:
        if r["category"] not in (1, 2, 3, 4):
            continue
        qa = gold[r["qid"]]
        g = str(qa["answer"])
        if qa["category"] == 3:
            g = g.split(";")[0].strip()
        pred = SC.official_clean(r["reply"], r["category"], None)
        pt, gt = _toks(pred), _toks(g)
        same = sum((Counter(pt) & Counter(gt)).values())
        words.append(len(pt))
        prec.append(same / len(pt) if pt else 0.0)
        rec.append(same / len(gt) if gt else 0.0)
        long3 += int(len(pt) >= 3 * max(1, len(gt)))
        f1s.append(SC.official_score(pred, qa["answer"], qa["category"]))
    n = len(f1s)
    return {"questions": n, "median_words": statistics.median(words), "precision": round(100 * sum(prec) / n, 1),
            "recall": round(100 * sum(rec) / n, 1), "replies_3x_gold": long3, "f1_check": round(100 * sum(f1s) / n, 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder holding locomo10.json")
    ap.add_argument("--runs", required=True)
    ap.add_argument("--arms", required=True)
    a = ap.parse_args()
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    gold = {f"{c['sample_id']}#{i}": qa for c in lc for i, qa in enumerate(c["qa"])}
    for arm in a.arms.split(","):
        print(json.dumps({arm: arm_stats(gold, _rows(Path(a.runs), arm))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
