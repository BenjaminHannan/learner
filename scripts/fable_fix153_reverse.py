#!/usr/bin/env python3
"""Experiment 153 -- THE ONE CHANGE: a reverse-question stage for loop150.

Director probe on loop150 (and loop149-qrewrite): after "Tom's boss is Bob."
every reverse question gets "I didn't understand that": "Whose boss is Bob?",
"Who is Bob the boss of?", "Bob is the boss of whom?", "Who is Rita the
mother of?", "Kelm is the capital of what?". Reversal is a benchmark target
(plain transformers fail 'A is B -> B is A'; the notebook stores triples, so
reverse lookup is exact).

THE RULE (question side only; teach/correct/forget/ask paths untouched): a
reverse-question stage runs ONLY when the forward question path did not
understand the message (the base ears returned exactly the loop's own
miss clarify, scripts/fable_loop90_agent.py:291-292). It parses four closed
reverse frames, maps R with the loop's own relation table
(FakeEars._relation, scripts/fable_agent_loop.py:150-152), scans the loop's
own live taught triples (Loop90Notebook triples: source == taught AND active,
scripts/fable_loop90_agent.py:101-114 -- so corrected-away, forgotten,
refused/hearsay content never answers), and replies:

  one subject    "Bob is the boss of Tom."
  several        "Bob is the boss of Tom and Sue." (teach order)
  none           "I don't know anyone whose boss is Bob." (never invents)

The stage emits clarify actions only, so the loop's _act passes them through
without writing (scripts/fable_agent_loop.py:337-339): a reverse question
never writes (mark V2). Multi-hop reverse ("Whose mother's boss is Bob?")
matches no frame (R spans exclude "'s"/"of"/relative cues) and keeps the
base clarify -- out of scope, never answered wrong.

No existing file edited; everything new lives in this file (+
scripts/fable_loop153_agent.py, which stacks this mixin onto loop150).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (relation table, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

# The loop's own miss replies: forward path "did not understand" iff the
# base ears return exactly one clarify carrying one of these bits.
MISS_BITS = ("didn't understand that", "didn't catch anything")

# Relation spans are single noun phrases: letters/spaces only (no "'s", no
# "of", no relative-clause cues) so multi-hop shapes can never parse.

# Cues that disqualify a parse (multi-hop / relative / compound shapes).
_NON_SIMPLE = ("'s", "\u2019s", " of ", " that ", " who ", " which ",
               " where ", " and ", ",", ";")


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def parse_reverse(text: str) -> tuple[str, str] | None:
    """Reverse question -> (relation_surface, value_surface), or None.

    Returns None for every non-reverse turn (including multi-hop reverse,
    which is out of scope and must keep the base clarify).
    """
    t = _norm(text)
    if not t.rstrip().endswith("?"):
        return None
    low = t.lower().rstrip("?")
    if "whose " in low or low.startswith("whose"):
        m = re.fullmatch(r"whose\s+([A-Za-z][A-Za-z ]*?)\s+is\s+(.+?)\?",
                         t, re.IGNORECASE)
        if m:
            return (m.group(1).strip(), m.group(2).strip().rstrip("?"))
        return None
    m = re.fullmatch(r"(?:who|what)\s+is\s+(.+?)\s+the\s+"
                     r"([A-Za-z][A-Za-z ]*?)\s+of\?", t, re.IGNORECASE)
    if m:
        return (m.group(2).strip(), m.group(1).strip())
    m = re.fullmatch(r"(.+?)\s+is\s+the\s+([A-Za-z][A-Za-z ]*?)\s+of\s+"
                     r"(?:whom|what|who)\?", t, re.IGNORECASE)
    if m:
        return (m.group(2).strip(), m.group(1).strip())
    m = re.fullmatch(r"(?:which|what)\s+[A-Za-z]+\s+has\s+(.+?)\s+as\s+"
                     r"its\s+([A-Za-z][A-Za-z ]*?)\?", t, re.IGNORECASE)
    if m:
        return (m.group(2).strip(), m.group(1).strip())
    return None


def _simple(span: str) -> bool:
    s = _norm(span)
    if not s or not s[0].isalpha():
        return False
    low = f" {s.lower()} "
    return not any(cue in low or cue in s for cue in _NON_SIMPLE)


def reverse_subjects(nb, rel_key: str, value: str) -> list[str]:
    """Every subject S with a live taught (S, rel_key, value), teach order."""
    want = _norm(value).rstrip(".")
    out: list[str] = []
    triples = L90.notebook_triples(nb) if nb is not None else []
    for subj, rel, val in triples:
        if rel != rel_key:
            continue
        if _norm(val).rstrip(".") != want:
            continue
        if subj not in out:
            out.append(subj)
    return out


def answer_reverse(rel_surface: str, value: str,
                   subjects: list[str]) -> str:
    """Exact reply strings (reused shapes, nothing invented beyond R/V)."""
    r, v = _norm(rel_surface), _norm(value).rstrip(".")
    if not subjects:
        return f"I don't know anyone whose {r} is {v}."
    return f"{v} is the {r} of {' and '.join(subjects)}."


def is_forward_miss(actions: list[dict]) -> bool:
    """True iff the base ears returned exactly the loop's own miss clarify."""
    if len(actions) != 1:
        return False
    only = actions[0]
    if not isinstance(only, dict) or only.get("act") != "clarify":
        return False
    return any(bit in str(only.get("text", "")) for bit in MISS_BITS)


class Reverse153Mixin:
    """Stackable mixin: reverse lookup only on a forward miss.

    Cooperative (super() first): hear() runs the base (loop150) hear; only
    when it returns exactly the miss clarify AND the turn parses as one of
    the four sealed reverse frames does this stage answer from the loop's
    own live taught triples. Everything else returns byte-identical. No
    _act override: this stage emits clarify actions only, which the loop's
    _act passes through without writing -- a reverse question never writes.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        if not is_forward_miss(actions):
            return actions
        parsed = parse_reverse(turn)
        if parsed is None:
            return actions
        rel_surface, value = parsed
        if not _simple(rel_surface) or not _simple(value):
            return actions
        rel_key = A.FakeEars._relation(rel_surface)
        subjects = reverse_subjects(getattr(self, "nb", None), rel_key,
                                    value)
        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
            "loop153-reverse", 1.0)
        return [{"act": "clarify",
                 "text": answer_reverse(rel_surface, value, subjects)}]
