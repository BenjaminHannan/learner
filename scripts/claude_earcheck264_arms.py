#!/usr/bin/env python3
"""Exp 264 -- arm assembly: 261b's pipeline with the YES/NO checker replaced by
the QA checker (the ONE change), span guard kept after it.

  ear greedy raw -> brake -> canonicalise (TEACH+ASK subjects, 261 sealed) ->
  QA split (TEACH saved iff value+owner+relation all agree, else UNSURE) ->
  GUARD split (261b sealed guard, imported read-only).

A261b (diagnostic): 261b's A exactly (brake -> canon -> YES/NO checker at
  sealed theta 0.25, prompt B -> guard). Recomputed here from recorded pYES so
  the A vs A261b difference is the checker swap alone.
A (registered): QA path above.
A_brake: canon + brake (261 sealed).
ASK frames never checked and never guarded (questions never write).

M6: every A frame is byte-identical in A_brake (checker+guard only hold back).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261b_guard as G  # noqa: E402
import claude_earcheck264_qa as QA  # noqa: E402

THETA_261B = 0.25


def qa_split(kept_canon, qa_texts):
    """Split kept frames by QA answers.

    qa_texts: {(turn_id, teach_index): (a_value, a_owner, a_relation, ms)}.
    Returns (saved, unsure, per_frame_ms).
    """
    saved, unsure, ms_list = [], [], []
    ti = 0
    for f in kept_canon:
        if f.get("act") != "TEACH":
            saved.append(f)
            continue
        key = ti
        ti += 1
        rec = qa_texts.get(key)
        if rec is None:
            unsure.append(dict(f, why="QA_UNSURE", qa_failed=["missing"]))
            ms_list.append(0.0)
            continue
        av, ao, ar, ms = rec
        ok, failed = QA.qa_decide(f, av, ao, ar)
        ms_list.append(float(ms))
        if ok:
            saved.append(f)
        else:
            unsure.append(dict(f, why="QA_UNSURE", qa_failed=failed,
                               a_value=av, a_owner=ao, a_relation=ar))
    return saved, unsure, ms_list


def apply_guard(saved_frames):
    t0 = time.perf_counter()
    kept, held = G.guard_split(saved_frames)
    ms = (time.perf_counter() - t0) * 1000.0
    return kept, held, ms


def a261b_split(kept_canon, p_list):
    """261b's A (YES/NO checker at 0.25) then guard, for the diagnostic arm."""
    saved, unsure = A261.checker_split(kept_canon, p_list, THETA_261B)
    kept, held, gms = apply_guard(saved)
    return kept, held, saved, unsure, gms


def qa_arm(kept_canon, qa_texts):
    """Registered arm A: QA split then guard."""
    saved, unsure, ms_list = qa_split(kept_canon, qa_texts)
    kept, held, gms = apply_guard(saved)
    return kept, held, saved, unsure, ms_list, gms
