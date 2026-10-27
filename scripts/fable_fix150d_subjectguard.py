#!/usr/bin/env python3
"""Experiment 150d -- THE ONE CHANGE: case-sensitive hedge matching.

Base: exp 150 subject guard (scripts/fable_fix150_subjectguard.py), inherited
read-only. Exp 150 matches its hedge list case-insensitively, so the
Title-Case song name "I Believe I Can Fly" refuses as "i believe" and
bench132-4hop-152 answers short (WRONG).

THE RULE (only change vs 150: which hedge hits count; everything else --
reporting openers, filler stripping, rule (c), replies -- byte-identical):

  A hedge phrase counts as a hedge only when its content word is lowercase
  as typed, OR the whole subject span is all-caps:

  - "i <word>" phrases (i think / i guess / i believe / i suppose): the
    content word is the word after "i". "I believe Kip ..." (lowercase)
    stays a hedge; "I Believe I Can Fly" / "I Think We're Alone Now"
    (capitalised content word) are names, not hedges.
  - single-word hedges (maybe / perhaps / probably / possibly / likely /
    presumably): the content word is the hedge word itself. "maybe Kip ..."
    (lowercase) stays a hedge; "Maybe, Kip ..." (comma boundary) stays a
    hedge; "Maybe Kip Dune" / "Perhaps the capital of Peru" (a fuller
    remainder follows) stay hedges; "MAYBE KIP ..." (all-caps) stays a
    hedge. ONLY a lone Title-Case token remainder ("Maybe Tomorrow",
    "Perhaps Love") reads as the title itself and stores.
  -   whole-span all-caps ("I BELIEVE TOM'S BOSS IS ANN") stays a hedge.

  Possessive owners are carved out at the agent layer (not here): the
  137-upgrade path keeps the 150 case-insensitive veto, because a
  hedge-led possessive owner ("Maybe Tom's boss", sealed C081 nowrite)
  is indistinguishable from a title possessive ("Maybe Tomorrow's
  author") at the owner-subject level. Title frees happen on the direct
  copula / of-shape paths, where bench132-152 lives.

Rationale for the single-word remainder clause: sealed exp-150 H-cases
refuse "Maybe/Perhaps/Probably/Possibly/Likely/Presumably Kip Dune" and
"Maybe, Kip Dune" / "Maybe the capital of Peru" (phone-form hedges with a
fuller phrase behind them), so those shapes must keep refusing; only the
bare-title shape ("Maybe Tomorrow") is freed. No existing file edited.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (lists+replies, read-only)

SPLIT_MSG = S150.SPLIT_MSG
HEARSAY_MSG = S150.HEARSAY_MSG
HEDGE_OPENERS = S150.HEDGE_OPENERS

_TWO_WORD = tuple(p for p in HEDGE_OPENERS if " " in p)
_ONE_WORD = tuple(p for p in HEDGE_OPENERS if " " not in p)


def _norm(subject: str) -> str:
    return " ".join(str(subject).split())


def _is_all_caps(text: str) -> bool:
    """Whole-span all-caps (has cased chars, none lowercase)."""
    return text.upper() == text and text.lower() != text


def _first_token(rest: str) -> str:
    tok = rest.split(" ")[0] if rest else ""
    return tok.strip(" \t,;:\"'\u201c\u201d\u2018\u2019.!?")


def _is_title_token(tok: str) -> bool:
    """Pure Title-Case token: [A-Z][a-z]+ (McDonald/O'Brien stay hedges)."""
    return len(tok) >= 2 and tok[0].isupper() and tok[1:].islower() \
        and tok.isalpha()


def _hedge_counts(text: str, phrase: str) -> bool:
    """Case-sensitive count check; text already matched phrase ci."""
    if _is_all_caps(text):
        return True
    rest = text[len(phrase):]
    if " " in phrase:
        # "i <content>": the content word (the phrase's own second word
        # as typed) must be lowercase. "I believe Kip" hedges;
        # "I Believe I Can Fly" does not.
        head, _, _ = text.partition(" ")
        content = _first_token(text[len(head) + 1:] if head else text)
        return bool(content) and content == content.lower()
    # single-word hedge: the hedge word itself is the content word.
    word = text[:len(phrase)]
    if word == word.lower():
        return True
    if rest.startswith(","):
        return True  # "Maybe, Kip ..." is phone-form hedging, not a title
    tail = rest.lstrip(" \t").split(" ")
    tail = [t for t in tail if t]
    if len(tail) >= 2:
        return True  # a fuller phrase follows: "Maybe Kip Dune ..."
    if len(tail) == 1 and not _is_title_token(_first_token(tail[0])):
        return True  # "Maybe kip", "Maybe TOMORROW": not a bare title
    if not tail:
        return True  # bare "Maybe" alone: conservative, refuse as before
    return False  # lone Title-Case token: the title itself ("Maybe Tomorrow")


def _is_hedged_150d(subject: str) -> bool:
    return any(S150._starts_with_phrase(subject, ph)
               and _hedge_counts(subject, ph) for ph in HEDGE_OPENERS)


def screen_subject_150d(subject: str) -> tuple[str, str | None]:
    """Subject span -> (verdict, payload). Identical to 150 except the hedge
    match above: "store" -> clean subject; "split"/"hearsay" -> no write."""
    text = _norm(subject)
    if not text:
        return ("store", subject)
    if _is_hedged_150d(text):
        return ("split", SPLIT_MSG)
    if S150._is_reporting(text):
        return ("hearsay", HEARSAY_MSG)
    stripped = S150._strip_fillers(text)
    if stripped and stripped != text:
        text = stripped
        if _is_hedged_150d(text):
            return ("split", SPLIT_MSG)
        if S150._is_reporting(text):
            return ("hearsay", HEARSAY_MSG)
    if S150._is_lowercase_lead_other(text):
        return ("split", SPLIT_MSG)
    return ("store", text)


def guard_action(action: dict) -> dict:
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("name", ""))
    verdict, payload = screen_subject_150d(stripped if stripped else
                                           action.get("name", ""))
    if verdict == "store":
        if payload != action.get("name"):
            out = copy.copy(action)
            out["name"] = payload
            return out
        return action
    return {"act": "clarify", "text": payload}


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class SubjectGuard150dMixin:
    """Stackable mixin: case-sensitive subject-span guard (150d rule)."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return guard_actions(actions)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            checked = copy.copy(action)
            cleaned = P129.strip_sentence_punct(checked.get("name", ""))
            if cleaned:
                checked["name"] = cleaned
            verdict, payload = screen_subject_150d(checked.get("name", ""))
            if verdict in ("split", "hearsay"):
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": payload}
            if payload != action.get("name"):
                checked["name"] = payload
                return super()._act(checked)  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]
