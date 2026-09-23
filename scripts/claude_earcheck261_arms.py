#!/usr/bin/env python3
"""Exp 261 -- arm assembly: ear preds -> canonicalised arms -> checker split.

Pipeline (sealed): parse greedy raw -> brake -> canonicalise (TEACH+ASK
subjects) -> checker: TEACH saved iff p(YES) >= theta else UNSURE; ASK always
saved. The checker only keeps or holds back; it never adds, edits or reorders.
A_gate = brake -> margin gate (tau 9.3, recomputed from raw+beams exactly as
257's scorer) -> canonicalise. A_raw = parse -> canonicalise (no brake).

pyes: {frame_key: p} with frame_key = (turn_id, teach_index among kept TEACH).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402
import claude_earcheck261_canon as C  # noqa: E402

GATE_TAU = 9.3


def base_arms(raw, turn, greedy_lp, beams):
    """Ear-only arms (no checker). Returns dict of frame lists."""
    frames = [f for f in E.parse_frames(raw) if f.get("act") in ("TEACH", "ASK")]
    kept, _ = E.brake(E.parse_frames(raw), turn)
    g = B.gate(turn, raw, greedy_lp, [tuple(x) for x in beams], GATE_TAU)
    return dict(
        A_raw=C.canonicalise(frames),
        A_brake=C.canonicalise(kept),
        A_gate=C.canonicalise(g["saved"]),
        kept_canon=C.canonicalise(kept),  # checker input (TEACH filtered later)
        gate_unsure=len(g["unsure"]),
        gate_guard=len(g["guard"]),
    )


def checker_split(kept_canon, p_list, theta):
    """Split kept TEACH frames by p(YES). ASK always saved. Order preserved."""
    saved, unsure = [], []
    ti = 0
    for f in kept_canon:
        if f.get("act") != "TEACH":
            saved.append(f)
            continue
        p = float(p_list[ti])
        ti += 1
        if p >= theta:
            saved.append(f)
        else:
            unsure.append(dict(f, why="CHECKER_UNSURE", pyes=p))
    assert ti == len(p_list), (ti, len(p_list))
    return saved, unsure


def teach_with_p(kept_canon, turn):
    """Build (rendered claims, prompts) for kept TEACH frames. Returns list of
    dicts {frame, claim, prompt} in kept order."""
    out = []
    for f in kept_canon:
        if f.get("act") != "TEACH":
            continue
        h = C.render_claim(f["subject"], f["relation"], f["value"])
        out.append(dict(frame=f, claim=h, prompt=C.build_prompt(turn, h)))
    return out
