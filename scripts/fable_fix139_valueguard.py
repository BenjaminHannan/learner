#!/usr/bin/env python3
"""Experiment 139 -- THE ONE CHANGE: a value-span validator on every teach path.

Red team 136 (classes W3 + W5 + W6) showed the teach value span is stored raw
even when it is not a single plain value:

  "Lena's city is not Oslo."        -> value 'not Oslo'      (negation)
  "Tom's boss is probably Ann."     -> value 'probably Ann'  (hedge)
  "Lena's city is Oslo. Cheers!"    -> value 'Oslo. Cheers'  (2nd sentence)
  "Tom's boss is Ann and Sue."      -> value 'Ann and Sue'   (compound)
  "Tom is a citizen of Peru and Ann." -> value 'Peru and Ann' (compound)

THE RULE (applied to the value span AFTER the exp-129 punctuation strip, on
every teach/correct path just before the write): the turn does NOT write and
gets the loop's existing clarify reply (the exp-91 SPLIT message) when the
value span

  (a) contains a negation or hedge word from the CLOSED list below
      (word-boundary, case-insensitive match anywhere in the span):
      not, never, no longer, probably, maybe, perhaps, possibly, might,
      likely, i think;
  (b) contains a bare " and " / " or " (word-boundary, case-insensitive)
      joining two spans, UNLESS the whole span (case-insensitive,
      whitespace-collapsed) is in KNOWN_AND_NAMES -- the closed list of
      multi-word values that legitimately contain "and", fixed before any
      test (benchmark gold answers containing " and " plus the brief's
      examples Trinidad and Tobago / Bosnia and Herzegovina plus three
      further UN member states with "and");
  (c) contains a sentence boundary -- ". " / "! " / "? " followed by more
      text -- where abbreviation periods do NOT count (a ". " whose
      preceding token is abbreviation-shaped under the exp-129 rule, e.g.
      "St. Louis", "Washington, D.C.", "Apple Inc.", is exempt).

Cooperative MIXIN (ValueGuard139Mixin) so tonight's integration (exp 138)
can stack it: hear() runs the base hear first (so the exp-129 strip has
already run inside loop129b) and converts refused teach/correct actions to
the existing clarify; _act() re-checks (strip-then-screen, spec-exact) just
before the write so the inner-chain delegate path is covered too. Relation
keys, subjects, forget/ask/clarify paths untouched. No existing file edited.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_earsguard91 as G91  # noqa: E402 (existing clarify reply, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip + abbrev rule, read-only)

# Closed negation/hedge list, fixed before any test. Word-boundary match.
_NEG_HEDGE_PATTERNS = (
    r"\bno\s+longer\b",  # phrase first (contains no bare-word clash, but keep order)
    r"\bnot\b",
    r"\bnever\b",
    r"\bprobably\b",
    r"\bmaybe\b",
    r"\bperhaps\b",
    r"\bpossibly\b",
    r"\bmight\b",
    r"\blikely\b",
    r"\bi\s+think\b",
)
_NEG_HEDGE_RE = re.compile("|".join(_NEG_HEDGE_PATTERNS), re.IGNORECASE)

# Bare coordinators joining two spans. Whole-span allowlist below exempts
# known multi-word values; there is no known "or" value, so every bare "or"
# refuses.
_AND_RE = re.compile(r"\band\b", re.IGNORECASE)
_OR_RE = re.compile(r"\bor\b", re.IGNORECASE)

# Sentence boundary: punctuation + whitespace + more text.
_BOUNDARY_RE = re.compile(r"[.!?]\s+\S")


def _norm_span(span: str) -> str:
    return " ".join(str(span).split()).lower()


# Closed whole-value allowlist for bare "and", fixed before any test.
# Sources: the 5 distinct benchmark gold answers containing " and " (bench65
# edit200 + bench103 s2fresh + bench121, scanned 2026-09-22) + the brief's
# two examples + three further UN member states with "and".
KNOWN_AND_NAMES = frozenset({
    "great britain and northern ireland",
    "the united kingdom of great britain and northern ireland",
    "united kingdom of great britain and northern ireland",
    "north and central america",
    "queen city of the pacific and others",
    "trinidad and tobago",
    "bosnia and herzegovina",
    "antigua and barbuda",
    "saint kitts and nevis",
    "sao tome and principe",
})

# The loop's existing clarify reply for a refused value.
CLARIFY_MSG = G91.SPLIT_MSG


def _has_sentence_boundary(value: str) -> bool:
    """True when value holds ". "/ "! "/ "? " + more text (abbrev-aware)."""
    for match in _BOUNDARY_RE.finditer(value):
        before = value[: match.start()].rstrip()
        token = before.split()[-1] if before.split() else ""
        stem = token.rstrip(".!?")
        if _is_abbrev_shaped(stem):
            continue  # "St. Louis", "Inc. X" -- abbreviation period, exempt
        return True
    return False


def _is_abbrev_shaped(stem: str) -> bool:
    """Exp-129 abbreviation test on a token with trailing punct removed."""
    return P129._is_abbrev_token(stem)


def screen_value_139(value: str) -> str | None:
    """Clarify message when a (stripped) teach value span must not write.

    Returns None when the value may be stored as-is.
    """
    text = " ".join(str(value).split())
    if not text:
        return None
    if _NEG_HEDGE_RE.search(text):
        return CLARIFY_MSG
    if _AND_RE.search(text) or _OR_RE.search(text):
        if _norm_span(text) not in KNOWN_AND_NAMES:
            return CLARIFY_MSG
    if _has_sentence_boundary(text):
        return CLARIFY_MSG
    return None


def guard_action(action: dict) -> dict:
    """teach/correct action with a refused value -> existing clarify; else copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("value", ""))
    msg = screen_value_139(stripped)
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class ValueGuard139Mixin:
    """Stackable mixin: value-span validator on every teach path.

    Cooperative (super() first): on ears it runs after the base hear (so the
    exp-129 strip inside loop129b has already run); on the loop it re-checks
    strip-then-screen just before the write (covers the inner-chain delegate
    path). Designed for exp 138 to stack with sibling mixins.
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
            msg = screen_value_139(checked.get("value", ""))
            if msg is not None:
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": msg}
        return super()._act(action)  # type: ignore[misc]
