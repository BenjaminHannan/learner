#!/usr/bin/env python3
"""Experiment 190 -- THE ONE CHANGE: reverse questions answered by VALUE
lookup over relations loop138g can already teach and store.

Director probe on loop138g: "Who was born in Paris?" and similar reverse
questions get the generic don't-know; there is no lookup by VALUE. The
153 reverse stage already in the 138g stack only fires on a forward MISS
("I didn't understand that") and only parses four frames, so
"Who has Lee as their boss?", "Who lives in Oslo?", "Who was born in
Paris?" all miss, and the whose-shapes it does answer get the
"V is the R of S." wording instead of the forward "S's R is V." sentence.

THE RULE (question side only; teach/correct/forget/ask paths untouched):
a closed set of reverse-question shapes over a closed relation set, both
fixed below before any panel read. The relation set is the union of the
relations named in loop138g's own code: PERSON_RELATIONS
(scripts/fable_agent_loop.py:91) + LISTED_RELATIONS
(scripts/fable_fix139e_tail.py:57). The stage runs only when the full
138g stack returns all-clarify (forward asks and teaches pass through
byte-identical), parses one closed shape, scans the loop's own live
taught triples (L90.notebook_triples: source == taught AND active, so
corrections respected, inferences never), and replies with clarify
actions only (never writes):

  1 match  "Kim's boss is Lee." (forward-style sentence)
  several  one such sentence per subject, notebook order, joined by space
  none but the named entity is known
           "I don't know anyone whose boss is Lee."
  unknown name: the notebook's unknown-name reply
           "I don't know anyone called Zed."

Closed shapes (case-insensitive full match, R/Y single noun phrases):
  E1 "Whose <R> is <Y>?"                (R in the closed relation set)
  E2 "Who has <Y> as their|his|her <R>?" (R in the closed relation set;
       "its" is left to the sealed 153 frame, byte-identical)
  E3 "Who lives in <Y>?"                (loop138g stores city; its wh-city
       port answers town shapes via the city path, so lives-in maps to
       the city key only)
  E4 "Who was born in <Y>?"             (loop138g stores birthplace)

No existing file edited; everything new lives in this file (+
scripts/fable_loop190_agent.py, which stacks this mixin onto loop138g).
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
import fable_notebook_contract as C  # noqa: E402 (_norm, read-only)

# THE CLOSED RELATION SET -- union of the relations named in loop138g's
# own code, fixed before any panel read (normalised keys, exactly as
# FakeEars._relation makes them: lowercase, whitespace runs -> "_").
#   PERSON_RELATIONS (scripts/fable_agent_loop.py:91):
#     mother father sister brother friend boss teacher wife husband
#     neighbour neighbor partner
#   LISTED_RELATIONS (scripts/fable_fix139e_tail.py:57):
#     mother father sister brother sibling spouse husband wife boss
#     friend teacher coach pet dog city town hometown home_town country
#     birthplace place_of_birth school
REVERSE_RELATIONS = frozenset({
    "mother", "father", "sister", "brother", "sibling", "spouse",
    "husband", "wife", "boss", "friend", "teacher", "coach",
    "pet", "dog", "neighbour", "neighbor", "partner",
    "city", "town", "hometown", "home_town", "country",
    "birthplace", "place_of_birth", "school",
})

# Fixed verb-phrase relations (loop138g stores these keys).
LIVES_RELATION = "city"
BORN_RELATION = "birthplace"

# Cues that disqualify a span (multi-hop / relative / compound shapes can
# never parse; mirrors scripts/fable_fix153_reverse.py:56-57).
_NON_SIMPLE = ("'s", "\u2019s", " of ", " that ", " who ", " which ",
               " where ", " and ", ",", ";")


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _clean_value(text: str) -> str:
    return _norm(str(text).rstrip("?").rstrip(".").strip())


def _simple(span: str) -> bool:
    s = _norm(span)
    if not s or not s[0].isalpha():
        return False
    low = f" {s.lower()} "
    return not any(cue in low or cue in s for cue in _NON_SIMPLE)


def parse_reverse190(text: str) -> tuple[str, str] | None:
    """Reverse question -> (relation_key, value_surface), or None.

    Returns None for every non-reverse turn (forward questions, teaches,
    multi-hop shapes, unlisted relations). Relation keys are normalised
    exactly like FakeEars._relation.
    """
    t = _norm(text)
    if not t.rstrip().endswith("?"):
        return None
    m = re.fullmatch(r"whose\s+([A-Za-z][A-Za-z ]*?)\s+is\s+(.+?)\?",
                     t, re.IGNORECASE | re.DOTALL)
    if m:
        rel, val = m.group(1).strip(), _clean_value(m.group(2))
        if _simple(rel) and _simple(val):
            key = A.FakeEars._relation(rel)
            if key in REVERSE_RELATIONS:
                return (key, val)
        return None
    m = re.fullmatch(r"who\s+has\s+(.+?)\s+as\s+(?:their|his|her)\s+"
                     r"([A-Za-z][A-Za-z ]*?)\?", t,
                     re.IGNORECASE | re.DOTALL)
    if m:
        val, rel = _clean_value(m.group(1)), m.group(2).strip()
        if _simple(rel) and _simple(val):
            key = A.FakeEars._relation(rel)
            if key in REVERSE_RELATIONS:
                return (key, val)
        return None
    m = re.fullmatch(r"who\s+lives\s+in\s+(.+?)\?", t,
                     re.IGNORECASE | re.DOTALL)
    if m:
        val = _clean_value(m.group(1))
        if _simple(val):
            return (LIVES_RELATION, val)
        return None
    m = re.fullmatch(r"who\s+was\s+born\s+in\s+(.+?)\?", t,
                     re.IGNORECASE | re.DOTALL)
    if m:
        val = _clean_value(m.group(1))
        if _simple(val):
            return (BORN_RELATION, val)
        return None
    return None


def reverse_subjects190(nb, rel_key: str, value: str) -> list[str]:
    """Every subject S with a live taught (S, rel_key, value), teach order.

    Notebook's current value only (superseded rows are inactive), taught
    facts only (inferences never) -- via L90.notebook_triples.
    """
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


def is_known_name190(nb, value: str) -> bool:
    """True iff the named entity is known: alias, subject, or live value."""
    if nb is None:
        return False
    try:
        if C._norm(value) in getattr(nb, "aliases", {}):
            return True
    except Exception:
        pass
    want = _norm(value).lower()
    for subj, _rel, val in L90.notebook_triples(nb):
        if _norm(subj).lower() == want or _norm(val).rstrip(
                ".").lower() == want:
            return True
    return False


def _display_rel(rel_key: str) -> str:
    return rel_key.replace("_", " ")


def answer_reverse190(rel_key: str, value: str, subjects: list[str],
                      known: bool) -> str:
    """Exact reply strings (forward-style sentences, nothing invented)."""
    r, v = _display_rel(rel_key), _clean_value(value)
    if subjects:
        return " ".join(f"{s}'s {r} is {v}." for s in subjects)
    if known:
        return f"I don't know anyone whose {r} is {v}."
    return f"I don't know anyone called {v}."


def is_all_clarify(actions: list[dict]) -> bool:
    """True iff the base understood nothing (every action a clarify)."""
    return (isinstance(actions, list) and len(actions) > 0
            and all(isinstance(a, dict) and a.get("act") == "clarify"
                    for a in actions))


class Reverse190Mixin:
    """Stackable mixin: reverse lookup only on an all-clarify base result.

    Cooperative (super() first): hear() runs the full loop138g stack;
    only when it returns all-clarify AND the turn parses as one of the
    four sealed reverse shapes does this stage answer from the loop's
    own live taught triples. Everything else returns byte-identical. No
    _act override: this stage emits clarify actions only, which the
    loop's _act passes through without writing -- a reverse question
    never writes.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        if not is_all_clarify(actions):
            return actions
        parsed = parse_reverse190(turn)
        if parsed is None:
            return actions
        rel_key, value = parsed
        nb = getattr(self, "nb", None)
        subjects = reverse_subjects190(nb, rel_key, value)
        known = is_known_name190(nb, value)
        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
            "loop190-reverse", 1.0)
        return [{"act": "clarify",
                 "text": answer_reverse190(rel_key, value, subjects,
                                           known)}]
