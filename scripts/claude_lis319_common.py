#!/usr/bin/env python3
"""lis-319 shared bits: the reader's prompt WITH the earlier conversation (the one change of lis-319).

lis-300..318 show the reader only the assistant's last reply and the user's turn. lis-319 also shows up to
HIST_TURNS earlier user turns, each followed by the assistant's reply to it, so "she's 84" can resolve to someone
named three turns ago. The frame format and target text are unchanged (claude_lis300_common.frame_text).

history = list of (user_text, assistant_reply) for the EARLIER turns, oldest first. The last pair's reply is the
same text as prev_reply, so it is not repeated: the history block ends with that user turn, then "Assistant said:".
"""
from __future__ import annotations

from claude_lis300_common import SYSTEM, END, frame_text, parse_frame  # noqa: F401 (re-exported)

HIST_TURNS = 6


def history_block(history) -> str:
    h = list(history or [])[-HIST_TURNS:]
    if not h:
        return "(none)"
    lines = []
    for i, (u, a) in enumerate(h):
        lines.append(f"User: {str(u).strip()}")
        if i < len(h) - 1 and str(a or "").strip():
            lines.append(f"Assistant: {str(a).strip()}")
    return "\n".join(lines)


def build_prompt_hist(turn: str, prev_reply: str = "", history=None) -> str:
    return (f"{SYSTEM}\nEarlier chat:\n{history_block(history)}\n"
            f"Assistant said: {str(prev_reply or '').strip() or '(nothing)'}\n"
            f"User said: {str(turn).strip()}\nFrame: ")


def dialog_histories(rows, dialog_of, order_of):
    """rows: list of dicts with 'turn' and 'prev_reply'. Returns {id: history} where history for a row is the
    earlier rows of its dialog as (turn, reply-to-that-turn); the reply to row k is row k+1's prev_reply."""
    by = {}
    for r in rows:
        by.setdefault(dialog_of(r), []).append(r)
    out = {}
    for d, rs in by.items():
        rs.sort(key=order_of)
        for k, r in enumerate(rs):
            out[r["id"]] = [(rs[j]["turn"], rs[j + 1].get("prev_reply", "")) for j in range(k)]
    return out
