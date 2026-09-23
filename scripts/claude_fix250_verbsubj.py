#!/usr/bin/env python3
"""Experiment 250 -- THE ONE CHANGE (diagnosis 243 cause B, fix 5).

Verb questions ("Where does X live?", "Who does X work for?", "Where was X
born?", and 167d's "Where does X work?", "What language does X speak?") are
rewritten to their possessive twin only when X is ONE capital-lead token
(scripts/fable_fix167_verb.py:83 `_NAME`, re-checked case-sensitively in
`_subject_ok` at :117). So "Where does brannick live?" and
"Where does Joren Hale live?" are refused and fall to the glued decline.

THE ONE CHANGE: VerbSubj250Mixin (a Verb167Mixin subclass that takes
Verb167's slot in the ears stack) tries the base Verb167 parse first; ONLY
when the base parse claims nothing does it try a widened subject check on
"?"-terminated question turns:
  * the five verb-question shapes above, matched case-insensitively, with
    a subject of 1-4 name-like words;
  * the subject must NOT be a closed-class subject (150c veto: I, you, it,
    ...), must not start with a possessive determiner (my/your/his/...),
    and must resolve to exactly ONE entity already in the notebook
    (nb.resolve -> OK, by its own stored name, not an alias) that is the
    subject of at least one active taught fact; USER never counts;
  * the twin uses the entity's STORED spelling ("Where is Brannick's
    city?"), so the answer names it the way it was taught.
Base first: the original turn is heard by the unchanged stack; if it claims
anything (any action that is not a clarify miss) that result is returned
byte-identical. Only on a miss is the twin handed to the same inner stack
Verb167 hands its twins to, and it is kept only when every action is
read-only (ask/clarify/answer/unsure) and one is an ask/answer; otherwise
the original turn's handling is returned unchanged.

Statements are never touched. Turns the base Verb167 / Verb167d already
claim are never touched (byte-identical). No existing file is edited.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix150c_closedclass as C150  # noqa: E402 (read-only)
import fable_fix167_verb as V167  # noqa: E402 (read-only)
import fable_fix167d_verb as V167D  # noqa: E402 (read-only)

STAGE250 = "verbsubj250"
READ_ONLY_ACTS250 = frozenset({"ask", "clarify", "answer", "unsure"})
USER_KEY250 = "user"

# 1-4 name-like words (letters, apostrophe, hyphen). Case is free; the
# notebook-resolve gate below is what decides whether it is a name.
_WORD250 = r"[A-Za-z][A-Za-z'’\-]*"
_SUBJ250 = r"(" + _WORD250 + r"(?:\s+" + _WORD250 + r"){0,3})"
_POLITE250 = r"(?:(?:hey|hi|hello)\s*,?\s+)?(?:please\s*,?\s+)?"
_TAILPOL250 = r"(?:\s*,?\s*please)?"

_Q250 = (
    (re.compile(r"^" + _POLITE250 + r"where\s+does?\s+" + _SUBJ250 +
                r"\s+live" + _TAILPOL250 + r"\s*\?\s*$", re.IGNORECASE),
     lambda n: f"Where is {n}'s city?"),
    (re.compile(r"^" + _POLITE250 + r"who\s+does?\s+" + _SUBJ250 +
                r"\s+work\s+for" + _TAILPOL250 + r"\s*\?\s*$",
                re.IGNORECASE),
     lambda n: f"Who is {n}'s employer?"),
    (re.compile(r"^" + _POLITE250 + r"where\s+was\s+" + _SUBJ250 +
                r"\s+born" + _TAILPOL250 + r"\s*\?\s*$", re.IGNORECASE),
     lambda n: f"Where is {n}'s place of birth?"),
    (re.compile(r"^" + _POLITE250 + r"where\s+does?\s+" + _SUBJ250 +
                r"\s+work" + _TAILPOL250 + r"\s*\?\s*$", re.IGNORECASE),
     lambda n: f"Who is {n}'s employer?"),
    (re.compile(r"^" + _POLITE250 + r"what\s+languages?\s+does?\s+" +
                _SUBJ250 + r"\s+speak" + _TAILPOL250 + r"\s*\?\s*$",
                re.IGNORECASE),
     lambda n: f"What is {n}'s language?"),
)

_DETERMINERS250 = frozenset(
    "my your his her its our their the a an this that these those".split())


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def resolve_subject250(nb, name: str) -> str | None:
    """Stored display name iff `name` is exactly one notebook entity."""
    name = _norm(name)
    if not name or nb is None:
        return None
    words = name.split()
    if words[0].lower() in _DETERMINERS250:
        return None
    try:
        if C150.is_closed_class_subject(name):
            return None
    except Exception:  # noqa: BLE001
        return None
    try:
        res = nb.resolve(name)
    except Exception:  # noqa: BLE001
        return None
    if getattr(res, "status", None) != "OK":  # AMBIGUOUS / UNKNOWN_ENTITY
        return None
    payload = getattr(res, "detail", None) or {}
    stored = payload.get("answer") if isinstance(payload, dict) else None
    if not isinstance(stored, str) or not stored.strip():
        return None
    stored = stored.strip()
    if stored.lower() == USER_KEY250:
        return None
    if _norm(stored).lower() != name.lower():
        return None  # alias hit, not the stored name itself: stay out
    if not _is_subject250(nb, payload.get("entity_id")):
        return None  # a value-only entity (e.g. a city) is not asked about
    return stored


def _is_subject250(nb, entity_id) -> bool:
    """True iff the entity is the subject of at least one active taught fact."""
    if not entity_id:
        return False
    try:
        for fact in nb.facts.values():
            if (fact.get("subject") == entity_id
                    and fact.get("source") == "taught"
                    and nb.active(fact["fact_id"])):
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


def parse_verbsubj250(turn: str, nb) -> dict | None:
    """Question turn -> {twin, name} under the widened check, else None."""
    text = _norm(turn)
    if not text.endswith("?"):
        return None
    for pat, mk in _Q250:
        m = pat.fullmatch(text)
        if m is None:
            continue
        stored = resolve_subject250(nb, m.group(1))
        if stored is None:
            return None
        return {"twin": mk(stored), "name": stored}
    return None


def _read_only250(actions) -> bool:
    return isinstance(actions, list) and bool(actions) and all(
        isinstance(a, dict) and a.get("act") in READ_ONLY_ACTS250
        for a in actions)


def _is_miss250(actions) -> bool:
    """True when the base stack claimed nothing (only clarify actions)."""
    return isinstance(actions, list) and bool(actions) and all(
        isinstance(a, dict) and a.get("act") == "clarify" for a in actions)


class VerbSubj250Mixin(V167.Verb167Mixin):
    """Verb167 with a case-insensitive, multi-word, notebook-resolved
    subject check on question turns the base parse refuses."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        hit = None
        if nb is not None and _norm(turn).endswith("?"):
            try:
                base_hit = V167.parse_verb_turn(turn)
                d_hit = V167D.parse_verb167d_turn(turn)
            except Exception:  # noqa: BLE001
                base_hit = d_hit = True  # be safe: leave it to the base
            if base_hit is None and d_hit is None:
                try:
                    hit = parse_verbsubj250(turn, nb)
                except Exception:  # noqa: BLE001
                    hit = None
        if hit is None:
            return super().hear(turn)
        # Base first: if the unchanged stack already claims the turn (any
        # action that is not a clarify miss), keep its result byte-identical.
        base = super().hear(turn)
        if not _is_miss250(base):
            return base
        # Same inner hand-off Verb167 uses for its own twins.
        actions = super(V167.Verb167Mixin, self).hear(hit["twin"])  # type: ignore[misc]
        if _read_only250(actions) and any(
                a.get("act") in ("ask", "answer") for a in actions):
            try:
                self.last_stage250 = STAGE250  # type: ignore[attr-defined]
            except AttributeError:
                pass
            return actions
        return super().hear(turn)  # re-hear so stage state is the base's
