#!/usr/bin/env python3
"""Experiment 137 -- THE ONE CHANGE: multi-word possessive-teach subjects.

Director probe (loop129a/loop129b): the possessive teach frame only accepts a
ONE-WORD subject ("Dara's mother is Ora Fenn." saves; "Dara Fenn's city is
Lyon." clarifies with 0 writes). People have full names, so this blocks
natural teaching.

THE ONE CHANGE: the possessive teach frame (FakeEars / Loop102Ears /
Loop121Ears lineage) accepts a subject of 1-4 capitalised name tokens
(allowing hyphens and apostrophes inside tokens, e.g. O'Neil, Anne-Marie,
plus the exp-129 abbreviation rule: one trailing period on an
abbreviation-shaped token such as "St."). Everything else about the frame is
unchanged: same relation vocabulary (FakeEars' open lower/underscore map),
same value rules (exp-91 screen + exp-129 sentence-punctuation strip), same
clarify/refuse paths (any refusal returns the base ears' clarifies
byte-identical).

Question side ("What is Dara Fenn's city?"): FakeEars' question branch never
had the one-word guard, so it already works once the teach stores the exact
subject. This module changes nothing on "?" turns (they delegate
byte-identical); the probe verifies the questions empirically.

Delivered as a stackable mixin: class Fix137PossessiveMixin. Tonight's
integration stacks it as ``class LoopNEars(Fix137PossessiveMixin,
Loop129bEars)`` (see scripts/fable_loop137_agent.py). It calls
super().hear(turn) first and only upgrades an all-clarify result into a
teach/correct action when the turn parses as a possessive teach whose
subject has 2-4 valid name tokens. Single-token subjects never upgrade
(the base already owns them), so no previously-accepted turn changes
outcome; any value-screen refusal returns the base clarifies untouched.

Name rule (is_name137_token): after stripping edge punctuation, a token must
  * start with an uppercase letter, contain only letters/hyphens/apostrophes
    (ASCII apostrophe or U+2019), with at most one trailing period, and
  * be a single uppercase letter (initial, per exp-129) OR contain at least
    one lowercase letter (Title-case; ALL-CAPS tokens are refused).
Subject rule: 2-4 such tokens (mixin path; 1-token subjects stay with base).

Additive only: every other module is imported read-only, never edited.
Stdlib only. Mac CPU. Deterministic: no seeds, no sampling, no model.
"""

from __future__ import annotations

import re

import fable_agent_loop as A  # noqa: E402 (FakeEars frame pieces, read-only)
import fable_earsguard91 as G91  # noqa: E402 (value rules, read-only)
import fable_fix129_punct as P129  # noqa: E402 (punct rules, read-only)
import fable_loop102_agent as L102  # noqa: E402 (prefilter guards, read-only)

MAX_NAME_TOKENS = 4

_NAME_TOKEN_RE = re.compile(r"^[A-Z][A-Za-z'\u2019\-]*\.?$")
_EDGE_STRIP = ".,;:'\"()"


def is_name137_token(token: str) -> bool:
    """True when one whitespace-separated token is a capitalised name token."""
    t = str(token).strip(_EDGE_STRIP).strip()
    if not t:
        return False
    if not _NAME_TOKEN_RE.match(t):
        return False
    core = t[:-1] if t.endswith(".") else t
    if not core:
        return False
    if len(core) == 1:
        return core.isalpha() and core.isupper()  # initial, per exp-129
    # Title-case: at least one lowercase letter (refuses ALL-CAPS).
    return any(ch.islower() for ch in core)


def is_name137_subject(subject: str) -> bool:
    """True for 1-4 capitalised name tokens (mixin upgrades 2-4 only)."""
    toks = str(subject).split()
    if not 1 <= len(toks) <= MAX_NAME_TOKENS:
        return False
    return all(is_name137_token(t) for t in toks)


def parse_possessive137(turn: str) -> tuple[str, str, str, bool] | None:
    """Mirror FakeEars' statement parse with the widened name rule.

    Returns (subject, relation, value, correction) or None. Applies, in the
    same order as the base chain: qualifier strip (Loop102 F4) on non-"?"
    turns, correction-prefix detect (FakeEars _CORRECTION), _STATEMENT match,
    _chain split requiring exactly 2 parts, FakeEars' relation map, non-empty
    value. Returns None for "?" turns, forget-shaped turns, hearsay turns,
    hearsay-shaped subjects, and any subject outside 2-4 name tokens.
    """
    text = " ".join(str(turn).split())
    if not text or text.rstrip().endswith("?"):
        return None
    if L102.is_hearsay(text):
        return None
    tmp = text
    m = L102._PLEASE_FORGET_RE.match(tmp)
    if m:
        tmp = "forget" + tmp[m.end(1):]
    if L102._FORGET_VERB_RE.match(tmp):
        return None
    cand = L102.strip_trailing_qualifier(text)  # F4: bare value is taught
    if not cand:
        return None
    correction = False
    found = A._CORRECTION.match(cand)
    if found and found.group(1):
        correction, cand = True, found.group(1)
    found = A._STATEMENT.match(cand)
    if not found:
        return None
    left, value = found.group(1), found.group(2).rstrip(".")
    parts = A._chain(left)
    if len(parts) != 2:
        return None
    name, relation = parts[0], A.FakeEars._relation(parts[1])
    if not value:
        return None
    if L102.subject_is_hearsay_shaped(name):
        return None
    toks = name.split()
    if not 2 <= len(toks) <= MAX_NAME_TOKENS:
        return None  # 1-token subjects stay with the base ears
    if not all(is_name137_token(t) for t in toks):
        return None
    return (name, relation, value, correction)


def build_action137(triple: tuple[str, str, str, bool]) -> dict:
    """FakeEars-identical teach/correct action, structured for the doorway.

    "structured": True routes Loop90AgentLoop._act straight to
    Listening._teach (the M1 line renderer only carries single-token names),
    with the same arrow semantics as FakeEars (is_person = person relation).
    """
    name, relation, value, correction = triple
    return {"act": "correct" if correction else "teach", "name": name,
            "relation": relation, "value": value,
            "is_person": relation in A.PERSON_RELATIONS,
            "structured": True, "stage": "fix137"}


class Fix137PossessiveMixin:
    """Stackable ears mixin: multi-word possessive-teach subjects.

    Use as ``class LoopNEars(Fix137PossessiveMixin, Loop129bEars)``. Requires
    the host to provide .nb (notebook binding, used only for parity with the
    base chain's stage tags) and super().hear(turn).
    """

    name = "fix137-multiword-possessive"

    def hear(self, turn: str) -> list[dict]:  # type: ignore[override]
        base = super().hear(turn)  # type: ignore[misc]
        if not isinstance(base, list) or not base:
            return base
        if any(isinstance(a, dict) and a.get("act") in (
                "teach", "correct", "ask", "answer", "forget2",
                "person", "alias", "forget", "quote") for a in base):
            return base  # base understood the turn: never touch it
        parsed = parse_possessive137(turn)
        if parsed is None:
            return base
        msg = G91.screen_value(parsed[2])  # same value rules as the chain
        if msg is not None:
            return base  # value refusal: base clarifies, byte-identical
        action = P129.sanitize_action(build_action137(parsed))
        if not action.get("name") or not action.get("value"):
            return base
        try:
            self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                "fix137-teach", 1.0)
        except AttributeError:
            pass
        return [action]
