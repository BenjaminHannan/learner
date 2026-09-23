#!/usr/bin/env python3
"""Exp 265 -- arm assembly: 261b's pipeline with the 265 canon/divert rule.

Registered arm A: ear greedy raw -> brake -> 265 canon/divert
  (first-person -> "me"; group-word TEACH diverted to the fixed ask-whose
  reply, 0 writes) -> checker split at sealed theta 0.25, prompt B, on the
  non-diverted kept TEACH frames -> 261b span guard (imported read-only).

A261b (diagnostic): 261b's A exactly (brake -> 261 canon -> checker 0.25 ->
  guard), recomputed from the same recorded pYES so A vs A261b differ only by
  the divert rule.

Claim identity note (why one pYES file serves both arms): 261-canon and
265-canon produce byte-identical subjects for every non-group frame
(first-person -> "me" in both; named spans untouched in both), so the prompt-B
claims rendered for non-diverted frames are byte-identical under both canons.
Checker teach indices count kept TEACH frames in kept order under 261-canon;
arm A consumes the subsequence at non-diverted positions. Diverted frames
spend a query but their pYES is never used by arm A (only by A261b).

M6-analogue: every A frame is byte-identical in A261b (divert/checker/guard
only remove frames), and every A frame is byte-identical in A_brake.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261b_guard as G  # noqa: E402
import claude_ear265_canon as C265  # noqa: E402

THETA = 0.25


def kept_265(raw, turn):
    """Brake then 265 canon (mirrors 261's brake-first order)."""
    kept, _ = E.brake(E.parse_frames(raw), turn)
    return C265.canonicalise_265(kept)


def a265_split(kept265, p_all, theta=THETA):
    """Split 265-canonicalised kept frames.

    p_all: pYES list indexed by kept TEACH position under 261-canon order
    (same frames, same order -- canon never adds/removes/reorders).
    Returns (saved, unsure, diverted, reply).
    """
    saved, unsure, diverted = [], [], []
    ti = 0
    for f in kept265:
        if f.get("act") != "TEACH":
            saved.append(f)
            continue
        p = float(p_all[ti])
        ti += 1
        if C265.is_group_subject(f.get("subject", "")):
            diverted.append(dict(f, why="ASK_WHOSE",
                                 reply=C265.ask_whose_reply(f), pyes=p))
        elif p >= theta:
            saved.append(f)
        else:
            unsure.append(dict(f, why="CHECKER_UNSURE", pyes=p))
    assert ti == len(p_all), (ti, len(p_all))
    return saved, unsure, diverted, C265.turn_reply(diverted)


def apply_guard(saved_frames):
    t0 = time.perf_counter()
    kept, held = G.guard_split(saved_frames)
    ms = (time.perf_counter() - t0) * 1000.0
    return kept, held, ms
