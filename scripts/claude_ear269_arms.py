#!/usr/bin/env python3
"""Exp 269 -- arm assembly: 265's arm A plus the text-level group-owner check.

Registered arm A pipeline (everything else is 265's arm A exactly):
  raw turn -> GROUP CHECK (new; before ear/brake) --+
  ear greedy raw -> brake -> 265 canon/divert       |
    -> checker split at sealed theta 0.25, prompt B |
    -> 261b span guard                              |
  reply = diverted reply if it asks, else the generic ask line if the
  text check fired, else "". Saved frames are 265's arm-A frames
  byte-identically (the check changes only the ASK trigger; group frames
  never save via the unchanged divert).

A265 (diagnostic): 265's arm A exactly (claude_ear265_arms, read-only).
A261b (diagnostic): 261b's arm A exactly (recomputed from the same pYES).

Claim identity: same as 265 (one pYES file serves all ear arms).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ear265_arms as A265  # noqa: E402  (read-only, never edited)
import claude_ear269_groupcheck as GC  # noqa: E402

THETA = 0.25


def arm_a(kept265, p_all, turn, theta=THETA):
    """265's split plus the text-level ask. Returns dict with saved,
    unsure, diverted, text check (fires/reasons/ms), reply, ask."""
    t0 = time.perf_counter()
    fires, reasons = GC.check(turn)
    gc_ms = (time.perf_counter() - t0) * 1000.0
    saved, unsure, diverted, reply265 = A265.a265_split(
        kept265, p_all, theta)
    reply = GC.turn_reply(fires, reply265)
    import claude_ear265_canon as C265  # noqa: E402
    return dict(saved=saved, unsure=unsure, diverted=diverted,
                fires=fires, reasons=reasons, gc_ms=round(gc_ms, 3),
                reply=reply, ask=C265.asks_whose(reply),
                reply265=reply265)


def apply_guard(saved_frames):
    return A265.apply_guard(saved_frames)
