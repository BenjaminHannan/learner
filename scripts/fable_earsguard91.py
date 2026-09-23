"""Exp 91 -- FakeEars guard: screen two silent wrong writes before the doorway acts.

Wraps any object satisfying fable_agent_loop.Ears (default FakeEars) and
implements the same Ears protocol: hear(turn) -> list of actions.

Every write action (teach/correct) whose value looks like one of the two
red-team-81 FakeEars failure shapes becomes a single clarify instead:

  (i)  value contains "?"  -> "Was that a question?"
  (ii) value packs a second fact: another possessive relation phrase
       (X's <word> is), a second copula (is/are), " and <Name>'s", or ";"
       -> "I can take one fact at a time -- could you split that?"
  (iii) value longer than 6 whitespace-separated words -> same split message.

Everything else passes through UNCHANGED (the inner action dicts are
returned as-is). Non-write actions (ask/answer/clarify/...) are never
touched. This file only ADDS behaviour; scripts/fable_agent_loop.py and
every other existing file are imported read-only, never edited.

Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

QUESTION_MSG = "Was that a question?"
SPLIT_MSG = "I can take one fact at a time \u2014 could you split that?"

WRITE_ACTS = ("teach", "correct")

# Another possessive relation phrase inside the value, e.g. "Mira's pet is".
_POSSESSIVE_IS = re.compile(r"['\u2019][sS]\s+\S+\s+is\b", re.IGNORECASE)
# " and <Name>'s", e.g. "Lisbon and Mira's pet ...".
_AND_POSSESSIVE = re.compile(r"\band\b\s+\S*['\u2019][sS]\b", re.IGNORECASE)
# A second copula inside the value (the first one was consumed by the parser).
_SECOND_COPULA = re.compile(r"\b(is|are)\b", re.IGNORECASE)

MAX_VALUE_WORDS = 6


def screen_value(value: str) -> str | None:
    """Return the clarify message for a bad write value, or None to let it pass."""
    text = str(value)
    if "?" in text:
        return QUESTION_MSG
    if (";" in text
            or _POSSESSIVE_IS.search(text)
            or _AND_POSSESSIVE.search(text)
            or _SECOND_COPULA.search(text)):
        return SPLIT_MSG
    if len(text.split()) > MAX_VALUE_WORDS:
        return SPLIT_MSG
    return None


class GuardedEars:
    """Ears wrapper: risky writes become clarifies, everything else passes through."""

    def __init__(self, inner=None) -> None:
        if inner is None:
            import fable_agent_loop as _A
            inner = _A.FakeEars()
        self.inner = inner

    def hear(self, turn: str) -> list[dict]:
        actions = self.inner.hear(turn)
        guarded: list[dict] = []
        for action in actions:
            if isinstance(action, dict) and action.get("act") in WRITE_ACTS:
                msg = screen_value(action.get("value", ""))
                if msg is not None:
                    guarded.append({"act": "clarify", "text": msg})
                    continue
            guarded.append(action)
        return guarded
