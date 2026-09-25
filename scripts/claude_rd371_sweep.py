#!/usr/bin/env python3
"""rd-371: pick the verifier cutoff on dev with the lis-300 rule (smallest grid value with 0 wrong-save turns,
all-or-nothing, claude_lis300_score.score), on a grid dense near 1 because P(yes) is not a min-token probability.
If no grid value reaches 0 wrong turns, T = the largest grid value. Prints the sweep and T.
python claude_rd371_sweep.py --gold DEV.jsonl --pred VERIFIED_READS.jsonl [--out OUT.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_score import load, score  # noqa: E402

GRID = [0.5, 0.7, 0.8, 0.9, 0.95, 0.97, 0.98, 0.99, 0.995, 0.998, 0.999, 0.9995, 0.9999]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    gold, pred = load(a.gold), load(a.pred)
    res = [score(gold, pred, {}, t) for t in GRID]
    for r in res:
        print(f"t={r['threshold']} wrong_turns={r.get('wrong_turns', 0)} recall={r.get('hits', 0)}/{r['gold_writes']}")
    ok = [r["threshold"] for r in res if r.get("wrong_turns", 0) == 0]
    T = ok[0] if ok else GRID[-1]
    print("T =", T, "(rule: smallest grid value with 0 wrong-save turns)" if ok else "(no grid value reached 0; largest)")
    if a.out:
        Path(a.out).write_text(json.dumps({"T": T, "sweep": res}, indent=1))


if __name__ == "__main__":
    main()
