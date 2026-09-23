#!/usr/bin/env python3
"""Experiment 165 -- THE ONE CHANGE: missing-apostrophe possessives for known names.

Ben's ruling (2026-09-22): fix typos silently. In teach and question turns, a
word W ending in s with no apostrophe, directly followed by a relation word,
is read as the possessive of W-minus-s when and only when (a) W-minus-s
matches exactly one known notebook entity (case-insensitive) and (b) W itself
is not a known entity and not a known plural name. Otherwise behaviour is
byte-identical to the base (no guessing for unknown names).

Base agent: loop162b (scripts/fable_loop162b_agent.py). Step 1 (file:line):
the base parses possessives in scripts/fable_agent_loop.py:93
(``_APOS = r"['']s\\b\\s*"``) via :102 (``_chain()`` splits the owner from
the relation on the apostrophe-s). A turn with no apostrophe such as
"toms boss" never splits: teach falls into the "Please say it like ..."
clarify (:139), questions into the hop-count clarify (:125-127). So today
"Toms boss is Lee." replies "I didn't understand that. Could you say it
another way?" and writes nothing.

THE ONE CHANGE (behaviour): Typo165Mixin, stacked OUTERMOST as
``Loop165Ears(Typo165Mixin, Loop162bEars)`` in scripts/fable_loop165_agent.py.
It claims ONLY full-turn shapes ``W R is V`` (teach) and
``Who/What/Where is|are W R`` (question) where W is one alpha word ending in
s/S with no apostrophe anywhere in the turn, R is one person-relation word,
and the notebook gates hold; it then delegates the REWRITTEN turn
(``W-minus-s's R ...``, everything else byte-preserved) to the base
``hear()`` literally. Save path, screens, and reply text are therefore the
base's own: no extra reply text -- the normal reply
("Saved: Tom's boss is Lee." / "Tom's boss is Lee.") shows the reading.

No existing file is edited. Base modules are imported read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)

# Relation words this fix recognises: the loop's person relations (boss,
# mother, father, ...). Anything else (office heads, table relations like
# founder, free-form words) never matches, so those turns take the base path
# byte-identical.
REL165: frozenset = frozenset(A.PERSON_RELATIONS)

_WORD = r"[A-Za-z]+"
_W_S = r"[A-Za-z]+[sS]"
_TEACH165 = re.compile(
    r"^(?P<w>" + _W_S + r")\s+(?P<r>" + _WORD + r")\s+is\s+(?P<v>.+?)\s*$",
    re.DOTALL)
_ASK165 = re.compile(
    r"^(?P<q>who|what|where)\s+(?P<be>is|are)\s+"
    r"(?P<w>" + _W_S + r")\s+(?P<r>" + _WORD + r")\s*$",
    re.IGNORECASE | re.DOTALL)


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _known_aliases(nb) -> dict:
    return getattr(nb, "aliases", {}) or {}


def _known_displays(nb) -> list[str]:
    ents = getattr(nb, "entities", {}) or {}
    try:
        return list(ents.values())
    except Exception:
        return []


def gates_hold(nb, w: str) -> bool:
    """Notebook gates (a) + (b) for candidate word W. Pure w.r.t. the turn."""
    if nb is None or len(w) < 2:
        return False
    stripped = w[:-1]
    if not stripped:
        return False
    try:
        found = nb.resolve(stripped)
    except Exception:
        return False
    # (a) W-minus-s matches exactly one known entity (case-insensitive).
    if found is None or found.status != "OK":
        return False
    if not (found.detail or {}).get("entity_id"):
        return False
    wn = _norm(w)
    # (b) W itself is not a known entity (OK or AMBIGUOUS both block).
    if wn in _known_aliases(nb):
        return False
    # (b2) W is not a known plural name: it must not equal the final word of
    # a known multi-word entity (e.g. W="Toms" while "The Toms" is taught, or
    # W="Beatles" while "The Beatles" is taught).
    for display in _known_displays(nb):
        toks = _norm(display).split()
        if len(toks) > 1 and toks[-1] == wn:
            return False
    return True


def rewrite_teach(turn: str, nb) -> str | None:
    """Full turn 'W R is V[.]' -> 'W-minus-s's R is V[.]' or None."""
    text = " ".join(str(turn).split())
    if not text or "?" in text:
        return None
    if "'" in text or "'" in text:
        return None  # base owns every apostrophe turn byte-identical
    dot = text.endswith(".") and not text.endswith("..")
    body = text[:-1].strip() if dot else text
    m = _TEACH165.fullmatch(body)
    if m is None:
        return None
    w, r, v = m.group("w"), m.group("r"), m.group("v").strip()
    if not v or ";" in v or "?" in w or "?" in r:
        return None
    if r.lower() not in REL165:
        return None
    if not gates_hold(nb, w):
        return None
    return f"{w[:-1]}'s {r} is {v}" + ("." if dot else "")


def rewrite_ask(turn: str, nb) -> str | None:
    """Full question 'Q be W R[?.]' -> 'Q be W-minus-s's R[?.]' or None."""
    text = " ".join(str(turn).split())
    if not text:
        return None
    if "'" in text or "'" in text:
        return None  # base owns every apostrophe turn byte-identical
    mark = ""
    body = text
    if body and body[-1] in ("?", "."):
        mark = body[-1]
        body = body[:-1].strip()
    m = _ASK165.fullmatch(body)
    if m is None:
        return None
    w, r = m.group("w"), m.group("r")
    if r.lower() not in REL165:
        return None
    if not gates_hold(nb, w):
        return None
    return f"{m.group('q')} {m.group('be')} {w[:-1]}'s {r}" + mark


class Typo165Mixin:
    """Stackable mixin: missing-apostrophe possessives before the base hear.

    Cooperative: only turns with a full-shape rewrite AND passing notebook
    gates are rewritten and delegated to super().hear(); every other turn --
    including every turn with an apostrophe, every unknown/ambiguous stripped
    name, and every W that is itself known -- falls through untouched, so the
    base owns those turns byte-identical.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            fixed = rewrite_teach(turn, nb)
            if fixed is not None:
                return super().hear(fixed)  # type: ignore[misc]
            fixed = rewrite_ask(turn, nb)
            if fixed is not None:
                return super().hear(fixed)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
