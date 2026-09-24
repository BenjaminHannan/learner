#!/usr/bin/env python3
"""lis-316 -- code guards, one wrapper (turn316), outermost in the listener stack.

The one change: before any inner layer sees the reader's frame, every fact that trips a guard
in scripts/claude_lis316_guards.py (me_prev, prev_owner, comma, mixed_case) gets confidence 0.0,
so it is treated as unsure: lis-314 keeps it pending until it is confirmed, and without lis-314,
turn310 or lis-315 asks it back. A guard never saves and never drops a fact.
Dev counts (lis-301 dev readings, 753 writable facts): 0 catches and 1 false hold
(artifacts/claude-lis316-20260924/devcount.json).

New file only; no existing file is edited. The wrapper writes nothing itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_lis310_agent as L310  # noqa: E402 (read-only)
import claude_lis316_guards as G  # noqa: E402


def install_turn316(loop, memo):
    inner = loop.turn
    if getattr(inner, "__name__", "") not in ("turn310", "turn313", "turn315", "turn314"):
        raise RuntimeError("316: needs a listener layer inside")
    loop.turn316_inner = inner
    st = loop.lis316_stats = {"turns": 0, "guarded_facts": 0}
    loop.lis316_fired = []

    def turn316(text):  # type: ignore[no-untyped-def]
        t = str(text)
        st["turns"] += 1
        yn = L310._norm_yesno(t) in (L310.YES310 | L310.NO310)
        if yn and (loop.lis310_pending is not None or getattr(loop, "lis314_confirming", None)):
            return inner(t)
        prev = loop.lis310_prev or ""
        read = memo.read(t, prev)
        frame = read[0] if isinstance(read, (tuple, list)) and read else None
        if isinstance(frame, dict) and frame.get("facts"):
            try:
                confs = list(read[1]) if read[1] is not None else []
            except TypeError:
                confs = []
            new, fired = G.apply_guards(frame, confs, t, prev)
            if fired:
                st["guarded_facts"] += len(fired)
                loop.lis316_fired.append({"turn": t, "fired": fired})
                memo.override(t, prev, (frame, new) + tuple(read[2:]))
        return inner(t)

    turn316.__name__ = "turn316"
    loop.turn = turn316
    return loop
