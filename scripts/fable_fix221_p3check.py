#!/usr/bin/env python3
"""Exp 221 -- P3 check: every suitediff move must be a sealed prediction.

Reads <diffdir>/{rt136,rt143,sessions152,bench}-diff.json (written by
scripts/fable_suitediff.py) and artifacts/claude-tableask221-20260922/
predicted_moves221.json. Prints EVERY moved case with its prediction
rule(s), base/new verdict and both replies, then the counts:
  unpredicted moves (must be 0), tool-labelled new WRONG / WRONG-WRITE /
  junk (must be 0), predicted-but-unmoved (reported only).
Hand verdicts on each move are written into RESULTS.md, not here.

Run: python3 -B scripts/fable_fix221_p3check.py --diff DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "artifacts" / "claude-tableask221-20260922" / \
    "predicted_moves221.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", required=True)
    args = ap.parse_args(argv)
    pred = json.loads(PRED.read_text(encoding="utf-8"))["suites"]
    total_unpred = 0
    total_bad = 0
    for suite in ("rt136", "rt143", "sessions152", "bench"):
        p = Path(args.diff) / f"{suite}-diff.json"
        if not p.exists():
            print(f"{suite}: NO DIFF FILE")
            continue
        rep = json.loads(p.read_text(encoding="utf-8"))
        prows = pred.get(suite, [])
        pids = {}
        for r in prows:
            pids.setdefault(r["id"], []).append(r["rule"])
        moved = set()
        print(f"== {suite}: {rep['summary_line']}")
        for m in rep["moves"]:
            mid = m["id"]
            moved.add(mid)
            rules = pids.get(mid, [])
            flag = "predicted" if rules else "UNPREDICTED"
            if not rules:
                total_unpred += 1
            if m["class"] in ("new WRONG", "new WRONG-WRITE",
                              "new junk write", "MISSING-BASE"):
                total_bad += 1
            print(f"  [{flag} {','.join(sorted(set(rules)))}] {mid} "
                  f"{m.get('split', '')} class={m['class']} "
                  f"{m.get('base_verdict')}->{m.get('new_verdict')}")
            if m.get("text"):
                print(f"      turn: {m['text']!r}")
            print(f"      base: {m.get('base_reply', '')!r}")
            print(f"      new : {m.get('new_reply', '')!r}")
        unmoved = sorted(set(pids) - moved)
        print(f"  predicted candidates that did not move: {len(unmoved)}")
    print(f"TOTAL unpredicted moves={total_unpred} "
          f"tool-flagged bad moves={total_bad}")
    return 0 if (total_unpred == 0 and total_bad == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
