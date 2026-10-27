#!/usr/bin/env python3
"""Merge 138k K2 driver: exp 220's own R1/R2/R3 scorer, re-aimed at 138k.

scripts/fable_fix220_marks.py is imported read-only; only its
load_agent() lookup is rebound in this process so that --agent fixed
builds loop138k (build_agent138k) instead of loop220. Every scoring line
is 220's own. Output files keep 220's names (r1-fixed.json etc.).

usage: claude_merge138k_marks220.py --mode r1|r2|r3 --agent fixed \
         --cases artifacts/fable-restartindex220-20260922/cases220.json --out <dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix220_marks as R220  # noqa: E402 (220 scorer, read-only)

_orig_load = R220.load_agent


def load_agent138k(which: str):
    if which == "fixed":
        import claude_loop138k_agent as K
        return K, K.DEFAULT_CONFIG138K, K.build_agent138k
    return _orig_load(which)


R220.load_agent = load_agent138k

if __name__ == "__main__":
    sys.exit(R220.main())
