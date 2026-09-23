#!/usr/bin/env python3
"""Exp 255b -- the one follow-up to 255 (fixed-reply text). Text only.

255b = 255's rewriter with two corrections (director's decision note
design/v3/30-modes/255b-fixedtext-decision.md). This module imports
scripts/claude_fix255_text.py UNCHANGED and post-processes its answer:

  Part A (T02, misread question): 255's "I don't know that. ..." is false
  when the loop failed to read the turn (the fact may be stored). 255b
  says exactly: "I didn't understand that. Could you say it another
  way?" -- true on every turn T02 fires on. Anchors identical to 138m.

  Part B (zero counts): 255's num() says "zero" for 0 on templates with
  no zero branch (T40, T41, T43, T46, T47, T52, T53). A count of 0 uses
  the director's exact texts below.

Every other line is returned exactly as rewrite255 returns it.

New file only; changes nothing in claude_fix255_text.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_fix255_text as T255  # noqa: E402 (base, read-only)

# Part A: the one T02 text (exact, director's note).
T02_NEW_255B = "I didn't understand that. Could you say it another way?"

# Part B: exact zero-count texts (director's note). Keyed by 255 template id.
ZERO_TEXTS_255B: dict[str, str] = {
    "T43_TURNS":
        "We haven't had any turns yet.",
    "T52_YESTERDAY":
        ("I have no record of yesterday. My log starts with our first "
         "turn here, and it is still empty."),
    "T53_NOBODYELSE":
        "Nobody besides you has spoken to me.",
    "T46_REFUSED0":
        "No. I never asked for clarification.",
    "T40_WEBN":
        "No. I don't hold any web rows.",
    "T41_SLEPTN":
        "No. I haven't slept yet.",
    "T47_REFUSEDN":
        "No. I never asked for clarification instead of saving.",
}

# Substrings on the OLD (138m-shaped) line that mark the zero case.
# T46's clarification count is structurally 0 whenever the template fires.
_ZERO_MARKS: dict[str, str] = {
    "T40_WEBN": "I hold 0 quarantined",
    "T41_SLEPTN": "slept 0 times",
    "T43_TURNS": "We have had 0 turns",
    "T46_REFUSED0": "clarification 0 times",
    "T47_REFUSEDN": "Yes, 0 times I asked",
    "T52_YESTERDAY": "holds 0 turns",
    "T53_NOBODYELSE": "All 0 turns are yours",
}

TEMPLATE_IDS = T255.TEMPLATE_IDS
PREFIX_DROPPED = T255.PREFIX_DROPPED


def _is_zero(tid: str, old_line: str) -> bool:
    mark = _ZERO_MARKS.get(tid)
    return mark is not None and mark in old_line


def rewrite255b(reply: str) -> tuple[str, str | None]:
    """(new text, template id) for one whole reply line; (reply, None)
    when the line is not a fixed template. T02 and zero-count lines use
    the 255b texts; every other line is exactly rewrite255's answer
    (including the dropped-question prefix handling)."""
    if not isinstance(reply, str):
        return reply, None
    pre = ""
    line = reply
    if line.startswith(T255.PREFIX_DROPPED):
        pre = T255.PREFIX_DROPPED
        line = line[len(pre):]
    new255, tid = T255.rewrite255(line)
    if tid is None:
        return reply, None
    if tid == "T02_Q2":
        return pre + T02_NEW_255B, tid
    if tid in ZERO_TEXTS_255B and _is_zero(tid, line):
        return pre + ZERO_TEXTS_255B[tid], tid
    if pre:
        return pre + new255, tid
    return new255, tid
