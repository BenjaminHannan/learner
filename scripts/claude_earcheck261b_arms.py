#!/usr/bin/env python3
"""Exp 261b -- arm assembly: 261's sealed arm A plus the mixed-case span guard.

Full registered arm A pipeline (all 261 pieces imported read-only, unchanged):
  ear greedy raw -> brake -> canonicalise (TEACH+ASK subjects) ->
  checker split at sealed theta 0.25, prompt B (TEACH saved iff p(YES) >= theta,
  ASK always saved) -> GUARD split (this experiment's one change).

A261 (diagnostic): the checker-split output, i.e. 261's A exactly.
A (registered): guard_split(A261) -- the guard only holds back as UNSURE;
  it never adds, edits or reorders, so every A frame is byte-identical in A261.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_earcheck261b_guard as G  # noqa: E402

THETA = 0.25


def apply_guard(saved_frames):
    """Apply the span guard to checker-saved frames. Returns (kept, held, ms)."""
    t0 = time.perf_counter()
    kept, held = G.guard_split(saved_frames)
    ms = (time.perf_counter() - t0) * 1000.0
    return kept, held, ms
