#!/usr/bin/env python3
"""Experiment 139b -- THE ONE CHANGE vs exp 139: replace the gold-sourced
closed "and"-name allowlist with a rule + an open code table.

Exp 139's value guard fixed its targets (V1 56/56, V2 7/7) but its closed
KNOWN_AND_NAMES list (scripts/fable_fix139_valueguard.py:85-99, built from
benchmark GOLD answers -- test leakage) refused the real value "United
Kingdom of Great Britain and Ireland", flipping 11 bench chains
correct -> wrong. This file keeps everything in 139 byte-identical EXCEPT
the bare-"and"/"or" branch:

  (a) an "and" that sits inside an "of"-phrase of a capitalised name --
      "<Capitalised words> of <Capitalised words> and <Capitalised words>"
      (exactly one "and", no "or"; e.g. "United Kingdom of Great Britain
      and Ireland") -- is part of the name and stores exactly;
  (b) a bare "A and B" value is allowed only if the whole span (normalised)
      is in OPEN_AND_NAMES, a small table of UN member-state / territory
      names containing "and", written from general knowledge BEFORE looking
      at any bench file (no benchmark file was read to build it);
  (c) every other bare "and"/"or" still clarifies with no write (unchanged).

Negation/hedge screening, sentence-boundary screening, the exp-129 strip,
and the existing clarify reply are imported READ-ONLY from exp 139
(fable_fix139_valueguard: _NEG_HEDGE_RE, _has_sentence_boundary,
CLARIFY_MSG) and fable_fix129_punct. No existing file edited.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139_valueguard as V139  # noqa: E402 (read-only: hedge/boundary/clarify)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)

# Open code table of UN member-state / territory names containing "and".
# Written from general knowledge BEFORE looking at any bench file; no
# benchmark file was read to build it. Lookup is case-insensitive on the
# whitespace-collapsed span (same normalisation as exp 139).
OPEN_AND_NAMES = frozenset({
    # UN member states with "and" in the English short name (7 total).
    "antigua and barbuda",
    "bosnia and herzegovina",
    "saint kitts and nevis",
    "saint vincent and the grenadines",
    "sao tome and principe",
    "trinidad and tobago",
    "united kingdom of great britain and northern ireland",
    # Territories / dependencies with "and" in the English name.
    "turks and caicos islands",
    "saint pierre and miquelon",
    "wallis and futuna",
    "south georgia and the south sandwich islands",
    "saint helena, ascension and tristan da cunha",
    "svalbard and jan mayen",
    "heard island and mcdonald islands",
})

# The loop's existing clarify reply for a refused value (unchanged).
CLARIFY_MSG = V139.CLARIFY_MSG


def _norm_span(span: str) -> str:
    return " ".join(str(span).split()).lower()


# Rule (a): "<Capitalised words> of <Capitalised words> and <Capitalised
# words>" -- each block is one or more capitalised tokens (leading uppercase
# letter; periods/apostrophes/hyphens allowed for "St.", "D.C.", "d'..."...).
# The connectors "of"/"and" match in any case; the NAME tokens must be
# capitalised, so "Order of rome and paris" does NOT match.
_CAP = r"[A-Z][A-Za-z.'\-]*"
_OF_AND_RE = re.compile(
    r"^%s(?:\s+%s)*\s+[Oo][Ff]\s+%s(?:\s+%s)*\s+[Aa][Nn][Dd]\s+%s(?:\s+%s)*$"
    % ((_CAP,) * 6)
)


def _is_of_and_name(value: str) -> bool:
    """True when the whole span is one capitalised of-phrase joined by a
    single "and" (rule (a)). Double-"and" ("Order of Rome and Paris and
    Oslo") and any "or" never match."""
    text = " ".join(str(value).split())
    if not text:
        return False
    if len(V139._AND_RE.findall(text)) != 1:
        return False
    if V139._OR_RE.search(text):
        return False
    return _OF_AND_RE.match(text) is not None


def screen_value_139b(value: str) -> str | None:
    """Clarify message when a (stripped) teach value span must not write.

    Identical to exp 139 except the bare-and/or branch (rule + open table).
    Returns None when the value may be stored as-is.
    """
    text = " ".join(str(value).split())
    if not text:
        return None
    if V139._NEG_HEDGE_RE.search(text):
        return CLARIFY_MSG
    if V139._AND_RE.search(text) or V139._OR_RE.search(text):
        if _norm_span(text) not in OPEN_AND_NAMES and not _is_of_and_name(text):
            return CLARIFY_MSG
    if V139._has_sentence_boundary(text):
        return CLARIFY_MSG
    return None


def guard_action(action: dict) -> dict:
    """teach/correct action with a refused value -> existing clarify; else copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("value", ""))
    msg = screen_value_139b(stripped)
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class ValueGuard139BMixin:
    """Stackable mixin: exp-139 guard with the 139b and-name rule.

    Cooperative (super() first): on ears it runs after the base hear (so the
    exp-129 strip inside loop129b has already run); on the loop it re-checks
    strip-then-screen just before the write (covers the inner-chain delegate
    path). Same shape as ValueGuard139Mixin; only the screen differs.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return guard_actions(actions)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            checked = copy.copy(action)
            cleaned = P129.strip_sentence_punct(checked.get("value", ""))
            if cleaned:
                checked["value"] = cleaned
            msg = screen_value_139b(checked.get("value", ""))
            if msg is not None:
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": msg}
        return super()._act(action)  # type: ignore[misc]
