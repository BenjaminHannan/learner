#!/usr/bin/env python3
"""Experiment 167b -- THE ONE CHANGE vs loop167: the verb path's object must
be name-shaped before its possessive twin is handed on.

Director held-out probe on loop167: "Ivy lives in a flat." saved
(Ivy, city, a flat) and "Uma lives in Accra now." saved (Uma, city,
Accra now) -- 2 wrong writes. THE ONE CHANGE (this file only; no 167
file edited, no other experiment file edited): a claimed 167 verb
STATEMENT's object is screened before the twin is handed to
super().hear():

  1. Strip trailing tail words with loop139e's sealed tail machinery
     (scripts/fable_fix139e_tail.py, imported read-only; the strip itself
     is loop139c's sealed strip_chat_tail, scripts/fable_fix139c_tail.py,
     which 139e seals and applies first -- same closed list: too, also,
     actually, though, tho, lol, lmao, haha, btw, again, now, anyway,
     then, instead, rn, right, ok, okay + pairs "as well", "i guess",
     lowercase-only, trailing punctuation tolerated, repeats for stacked
     tails, at least one value word must remain).
  2. If the stripped object is empty, or its FIRST word (case-insensitive)
     is an article/determiner in DETERMINERS below (closed list fixed in
     design/v3/30-modes/167b-verb-value-screen-muse.md before any panel
     read), or its first character is lowercase (a common word such as
     "home", "town", "abroad"), the turn writes NOTHING and replies with
     loop167's own no-write clarify
     ("I didn't understand that. Could you say it another way?" --
     scripts/fable_agent_loop.py:148, the FakeEars fallthrough text that
     loop167 itself returns for every declined verb turn).
  3. Otherwise the twin is rebuilt with the STRIPPED object and handed on
     untouched, so the write/answer is the possessive path's own by the
     same construction as 167.

Verb QUESTIONS are untouched (no object to screen): they take 167's path
literally. Anything 167 declines still declines identically (this mixin
only acts when V167.parse_verb_turn claims the turn).

Saved-reply label note: the verb path's "Saved: Raj's place_of_birth is
Pune." keeps the raw underscore label. The answer path renders spaces via
FakeMouth.say's inline `part.replace("_", " ")`
(scripts/fable_agent_loop.py:166-167) while the Saved text comes from the
notebook contract's TEMPLATES (scripts/fable_notebook_contract.py:77) --
NOT the same one-line render function -- so per the brief the label is
left as is and listed as future work. This file changes nothing about it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139e_tail as T139E  # noqa: E402 (sealed tail machinery, read-only)
import fable_fix167_verb as V167  # noqa: E402 (claim logic, read-only)

# Loop139e's sealed strip, reached through the 139e module (139e applies
# 139c's strip first; this is that same sealed function, never edited).
_strip_chat_tail = T139E.T139c.strip_chat_tail

# Loop167's own no-write clarify (FakeEars fallthrough, fable_agent_loop.py:148).
NO_WRITE_CLARIFY = "I didn't understand that. Could you say it another way?"

# Closed article/determiner list -- fixed in the design doc before any panel
# read. Matched case-insensitively against the object's first word.
DETERMINERS = frozenset({
    "a", "an", "the",
    "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those",
    "some", "any", "no", "every", "each", "either", "neither",
})

# The exact twin shapes V167.parse_verb_statement builds (rsurf in
# {"city", "employer", "place of birth"} + optional Actually,/No, prefix).
_TWIN_RE = re.compile(
    r"^(?:(Actually, |No, )?)(" + V167._NAME + r")'s "
    r"(city|employer|place of birth) is (.+)\.$",
    re.DOTALL,
)


def screen_value(value: str) -> str | None:
    """Stripped name-shaped object, or None when the turn must not write.

    Returns None when: the tail strip leaves nothing; the first word is an
    article/determiner; the first character is lowercase (common word).
    """
    cleaned, _ = _strip_chat_tail(value)
    cleaned = " ".join(str(cleaned).split())
    if not cleaned:
        return None
    first = cleaned.split(" ")[0]
    if not first:
        return None
    if first.lower() in DETERMINERS:
        return None
    if not first[0].isupper():
        return None
    return cleaned


def screen_twin(twin: str) -> str | None:
    """Apply the value screen to a 167 statement twin.

    Returns the twin to hand on (rebuilt with the stripped object), or
    None when the turn must clarify with no write.
    """
    m = _TWIN_RE.fullmatch(" ".join(str(twin).split()))
    if m is None:
        return None
    corr, name, rsurf, val = m.group(1) or "", m.group(2), m.group(3), m.group(4)
    clean = screen_value(val)
    if clean is None:
        return None
    return f"{corr}{name}'s {rsurf} is {clean}."


def screen_verb_statement(turn: str) -> str | None:
    """Raw turn -> hand-on twin, or None when 167 claims it but the object
    is not name-shaped. Returns the sentinel "DELEGATE" (as twin equal to
    input marker) -- no: returns None both when 167 declines (caller must
    delegate the raw turn) and when the screen refuses (caller must
    clarify). Use screen_verb_statement_detailed for the distinction."""
    parsed = V167.parse_verb_statement(turn)
    if parsed is None:
        return None
    return screen_twin(parsed["twin"])


def classify_statement(turn: str) -> tuple[str, str | None]:
    """(decision, twin): decision in {"declined", "refused", "pass"}.

    declined: 167 itself does not claim the turn (caller delegates raw).
    refused: 167 claims it but the object is not name-shaped (caller
      clarifies, no write). pass: hand `twin` to super().hear().
    """
    parsed = V167.parse_verb_statement(turn)
    if parsed is None:
        return "declined", None
    twin = screen_twin(parsed["twin"])
    if twin is None:
        return "refused", None
    return "pass", twin


class ValueScreen167bMixin:
    """Stackable mixin (outermost): screen verb-statement objects, else delegate.

    Cooperative: verb questions take 167's path literally; claimed verb
    statements with a name-shaped (post-strip) object are rebuilt with the
    clean object and handed to super().hear(); claimed statements whose
    object is a tail-only/description/common-word span return loop167's
    own clarify with no write; everything else falls through untouched.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            try:
                parsed = V167.parse_verb_turn(turn)
            except Exception:
                parsed = None
            if parsed is not None:
                if parsed.get("kind") == "question":
                    return super().hear(parsed["twin"])  # type: ignore[misc]
                twin = screen_twin(parsed["twin"])
                if twin is not None:
                    return super().hear(twin)  # type: ignore[misc]
                return [{"act": "clarify", "text": NO_WRITE_CLARIFY}]
        return super().hear(turn)  # type: ignore[misc]
