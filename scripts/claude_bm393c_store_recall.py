#!/usr/bin/env python3
"""bm-393c: bm-393b's measurement with the ep-382 store version 2 (benchmarks thread, 2026-09-25). New file only.
The one change from bm-393b: scripts/claude_ep382_store_v2.py ranks rows by '<speaker> said, "<text>"' instead of
"<speaker>: <text>". Everything else is bm-393b's sealed code (claude_bm393b_store_recall.run and selftest), run with
the store module swapped. $0 CPU, counts only, labelled "after using LoCoMo for development".

  python -B scripts/claude_bm393c_store_recall.py selftest
  python -B scripts/claude_bm393c_store_recall.py run --data DATA --out artifacts/claude-bm393c-20260925
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm393b_store_recall as R  # noqa: E402
import claude_ep382_store_v2 as M2  # noqa: E402

R.M = M2

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(R.selftest())
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--data", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args()
        sys.exit(R.run(Path(a.data), Path(a.out)))
    raise SystemExit("usage: claude_bm393c_store_recall.py selftest | run --data DATA --out OUT")
