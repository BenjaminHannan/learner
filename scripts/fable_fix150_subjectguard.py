#!/usr/bin/env python3
"""Experiment 150 -- THE ONE CHANGE: a subject-span guard for teach sentences.

Base: loop139b (scripts/fable_loop139b_agent.py; 139/139b guard only the
VALUE span). Director probe on loop139b: teaches whose SUBJECT span carries a
leading hedge / reporting / filler prefix store a polluted subject
("I think Kip Dune", "Perhaps Kip Dune", "Maybe Kip Dune",
"Someone told me Kip Dune", "Rumor has it Kip Dune", "Honestly Kip Dune",
"So Kip Dune", "My friend Kip Dune").

THE RULE (applied to the subject span of every teach/correct action, AFTER
the exp-129 strip, at ears hear() and again at loop _act() just before the
write -- same two levels as the 139b value guard):

  (a) the subject starts with a hedge or reporting opener (closed lists
      below, case-insensitive, word-boundary) -> NO WRITE. Hedges get the
      existing value-guard clarify reply (exp-91 SPLIT message); reporting
      openers get the existing hearsay reply (loop102 HEARSAY_MSG). Reused,
      nothing invented.
  (b) the subject starts with a discourse filler / introducer (closed list
      below) -> strip it (repeat until no change) and store the clean
      subject; the stripped remainder is re-screened by (a) and (c).
  (c) any other multi-token subject whose first token is an all-lowercase
      word, which contains at least one capitalised token and no " of " ->
      value-guard clarify, NO WRITE. (Single-token subjects pass untouched;
      all-lowercase subjects pass untouched -- legal common-noun entities
      per exp-102, e.g. "wide receiver", "association football"; role-phrase
      subjects "<lowercase words> of <Name>" pass untouched -- the bench-legit
      officeholder shape, e.g. "director of American Broadcasting Company";
      camelCase product names pass untouched -- "macOS Server", "iPod Touch",
      "iOS SDK" are styled names, not lower-case words.
      A leading token with an initial uppercase letter is a name token even
      when the word exists in English -- Will, May, Hope, Grace, Rich,
      Sunny, Frank, Mark, So-Yeon -- because the guard judges
      capitalisation shape, never vocabulary membership.)

Cooperative MIXIN (SubjectGuard150Mixin): hear() runs the base hear first
(the 129 strip + 139b value screen inside loop139b have already run) and
then screens/rewrites the subject of teach/correct actions; _act()
re-checks strip-then-screen just before the write (covers the inner-chain
delegate path). Values, relation keys, forget/ask/clarify paths untouched.
No existing file edited.
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
import fable_fix139_valueguard as V139  # noqa: E402 (SPLIT reply, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY reply, read-only)

# The loop's existing replies for a refused subject (reused, never invented).
SPLIT_MSG = V139.CLARIFY_MSG
HEARSAY_MSG = L102.HEARSAY_MSG

# (a1) Hedge openers -> SPLIT clarify, no write. Closed list, sealed before
# any run. Case-insensitive leading-phrase match (word boundary).
HEDGE_OPENERS = (
    "maybe",
    "perhaps",
    "probably",
    "possibly",
    "likely",
    "presumably",
    "i think",
    "i guess",
    "i believe",
    "i suppose",
)

# (a2) Reporting openers -> HEARSAY reply, no write. Closed list, sealed.
REPORTING_OPENERS = (
    "i heard",
    "someone told me",
    "someone said",
    "they say",
    "people say",
    "rumor has it",
    "rumour has it",
    "word is",
    "i read that",
    "i read online",
    "according to",
    "apparently",
    "reportedly",
)

# (b) Discourse fillers / introducers -> strip, store the remainder.
# Closed list, sealed. Multi-word phrases first (longest-match by order).
FILLER_OPENERS = (
    "by the way",
    "my friend",
    "my neighbor",
    "my neighbour",
    "so",
    "well",
    "ok",
    "okay",
    "honestly",
    "anyway",
    "also",
    "btw",
    "oh",
    "actually",
    "frankly",
)


def _norm(subject: str) -> str:
    return " ".join(str(subject).split())


def _starts_with_phrase(text: str, phrase: str) -> bool:
    low = text.lower()
    return (low == phrase or low.startswith(phrase + " ")
            or low.startswith(phrase + ","))


def _strip_fillers(subject: str) -> str:
    """Strip leading filler/introducer openers; repeat until no change."""
    text = _norm(subject)
    changed = True
    while changed:
        changed = False
        for phrase in FILLER_OPENERS:
            if _starts_with_phrase(text, phrase):
                rest = text[len(phrase):]
                rest = rest.lstrip(" \t,;:\"'\u201c\u201d\u2018\u2019")
                if rest:
                    text = rest
                    changed = True
                    break
    return text


def _is_hedged(subject: str) -> bool:
    return any(_starts_with_phrase(subject, ph) for ph in HEDGE_OPENERS)


def _is_reporting(subject: str) -> bool:
    return any(_starts_with_phrase(subject, ph) for ph in REPORTING_OPENERS)


def _is_lowercase_lead_other(subject: str) -> bool:
    """Rule (c): multi-token, lowercase lead, a capitalised token, no of."""
    toks = _norm(subject).split()
    if len(toks) < 2:
        return False
    if not toks[0].islower():
        return False
    if not any(t[:1].isupper() for t in toks):
        return False
    if " of " in (" " + _norm(subject).lower() + " "):
        return False
    return True


def screen_subject_150(subject: str) -> tuple[str, str | None]:
    """Subject span -> (verdict, payload).

    "store"    -> payload is the clean subject to store (fillers stripped).
    "split"    -> no write; payload is the SPLIT clarify reply.
    "hearsay"  -> no write; payload is the HEARSAY clarify reply.
    """
    text = _norm(subject)
    if not text:
        return ("store", subject)
    if _is_hedged(text):
        return ("split", SPLIT_MSG)
    if _is_reporting(text):
        return ("hearsay", HEARSAY_MSG)
    stripped = _strip_fillers(text)
    if stripped and stripped != text:
        text = stripped
        if _is_hedged(text):
            return ("split", SPLIT_MSG)
        if _is_reporting(text):
            return ("hearsay", HEARSAY_MSG)
    if _is_lowercase_lead_other(text):
        return ("split", SPLIT_MSG)
    return ("store", text)


def guard_action(action: dict) -> dict:
    """teach/correct action with a refused subject -> existing clarify;
    filler-prefixed subject -> same action with the clean name; else copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("name", ""))
    verdict, payload = screen_subject_150(stripped if stripped else
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


class SubjectGuard150Mixin:
    """Stackable mixin: subject-span guard on every teach path.

    Cooperative (super() first): on ears it runs after the base hear (so the
    129 strip + 139b value screen inside loop139b have already run); on the
    loop it re-checks strip-then-screen just before the write (covers the
    inner-chain delegate path). Same shape as ValueGuard139BMixin; only the
    span (subject, not value) differs.
    """

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
            verdict, payload = screen_subject_150(checked.get("name", ""))
            if verdict in ("split", "hearsay"):
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": payload}
            if payload != action.get("name"):
                checked["name"] = payload
                return super()._act(checked)  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]
