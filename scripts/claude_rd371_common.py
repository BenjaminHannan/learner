#!/usr/bin/env python3
"""rd-371 learned checker: shared prompt for the verifier ("does this turn state this fact? yes/no")."""
from __future__ import annotations

import re

VSYS = "Does the user's chat turn state this fact? Answer yes or no."


def fact_line(f: dict) -> str:
    return f"{f.get('owner', '')} | {f.get('rel', '')} | {f.get('value', '')} | {f.get('mode', 'ASSERT')}"


def build_vprompt(turn: str, prev_reply: str, f: dict) -> str:
    return (f"{VSYS}\nAssistant said: {(prev_reply or '').strip() or '(nothing)'}\n"
            f"User said: {turn.strip()}\nFact: {fact_line(f)}\nAnswer: ")


_P = re.compile(r"\nAssistant said: (.*)\nUser said: (.*)\nFrame: $", re.S)


def split_reader_prompt(prompt: str):
    """(prev_reply, turn) from a lis-300 style reader prompt (no history block)."""
    m = _P.search(prompt)
    if not m:
        return None
    prev, turn = m.group(1), m.group(2)
    return ("" if prev == "(nothing)" else prev), turn
