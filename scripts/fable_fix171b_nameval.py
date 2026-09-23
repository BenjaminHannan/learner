#!/usr/bin/env python3
"""Experiment 171b -- THE ONE CHANGE vs loop171: stop refusing real names
that are also English words.

Director probe 08:40 on loop171 (false refusals): "Zed's boss is Ora.",
"Bo's friend is Hope.", "Tia's brother is Rich.", "Rae's dad is Grant."
all get the sealed 171 clarify, even right after the agent itself asked
"What is Zed's boss's name?". Cause: givennames171.txt holds only 200
names while wordlist171.txt (210,675 lowercase dictionary words) contains
many real names (hope, grant, rich, ora, faith, iris, pearl, sky, ...), so
the 171 first-word rule refuses them as descriptions.

Rule (the one change): a name-relation value that consists ONLY of 1-3
Title-case tokens (each token: first letter upper, rest lower,
letters/apostrophe/hyphen only; no determiner token, no lowercase word
anywhere in the value) counts as name-shaped -- saved exactly like any
real name -- EVEN when its lowercase form is a dictionary word, EXCEPT
when its lowercase form is on the closed, sealed state/place/time list
(artifacts/fable-nameval171b-20260922/closedlist171b.txt, 61 words), which
stays refused exactly as in 171. Everything else is loop171's rule
verbatim (lowercase dictionary-word values, determiner-led values,
adverb-led values, and multi-word values with any lowercase word stay
refused with the same sealed clarify).

No existing file is edited. loop171 / N171 are imported read-only; the
mixin subclasses N171.NameVal171Mixin and bypasses ONLY its guard, calling
the next hear/_act in the MRO (the exact target the 171 guard itself
delegates to) before applying the 171b screen.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix171_nameval as N171  # noqa: E402 (base rule, read-only)

ART171B = SCRIPTS.parent / "artifacts" / "fable-nameval171b-20260922"

_CLOSED: frozenset | None = None


def CLOSED() -> frozenset:
    """Sealed state/place/time exception list (closedlist171b.txt)."""
    global _CLOSED
    if _CLOSED is None:
        text = (ART171B / "closedlist171b.txt").read_text(encoding="utf-8")
        _CLOSED = frozenset(w.strip().lower() for w in text.splitlines()
                            if w.strip())
    return _CLOSED


_PART = re.compile(r"^[A-Z][a-z]*$")
_PUNCT = ".,;:!?\"'`()[]{}"


def is_title_token(tok: str) -> bool:
    """First letter upper, rest lower, letters/apostrophe/hyphen only."""
    t = tok.strip(_PUNCT)
    if not t:
        return False
    parts = re.split(r"[-'\u2019]", t)
    if any(not _PART.match(p) for p in parts):
        return False
    return any(c.islower() for c in t)


def is_titlecase_nameform(value: object) -> bool:
    """True for values of ONLY 1-3 Title-case tokens, no lowercase word."""
    text = " ".join(str(value).split())
    if not text:
        return False
    toks = text.split()
    if not (1 <= len(toks) <= 3):
        return False
    return all(is_title_token(t) for t in toks)


def is_description_value_b(value: object) -> bool:
    """171b screen: Title-case-only values save unless vetoed; else 171."""
    if is_titlecase_nameform(value):
        toks = " ".join(str(value).split()).split()
        if any(t.strip(_PUNCT).lower() in N171.DETERMINERS for t in toks):
            pass  # determiner-led: fall through to the 171 rule
        elif (toks[0].strip(_PUNCT).lower()
                in N171.PLACE_TIME_ADVERBS):
            pass  # adverb-led: fall through to the 171 rule
        elif " ".join(toks).lower() in CLOSED():
            pass  # sealed state/place/time word: refused as in 171
        else:
            return False  # name-shaped word-name: save it
    return N171.is_description_value(value)


def screen_name_value_b(name: object, relation: object,
                        value: object) -> str | None:
    """Clarify message under the 171b screen (None = may store as-is)."""
    if str(relation) not in N171.NAME_KEYS:
        return None
    if is_description_value_b(value):
        return N171.clarify_for(name, relation)
    return None


def guard_action_b(action: dict) -> dict:
    """teach/correct with a 171b-refused value -> sealed clarify; else copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    msg = screen_name_value_b(action.get("name"), action.get("relation"),
                              action.get("value", ""))
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return action


def guard_actions_b(actions: list[dict]) -> list[dict]:
    return [guard_action_b(a) for a in list(actions)]


class NameVal171BMixin(N171.NameVal171Mixin):
    """loop171's guard with the word-name exception.

    Bypasses ONLY NameVal171Mixin.hear/_act (via explicit super, which
    resolves to the exact inner-chain target the 171 guard itself
    delegates to), then applies the 171b screen. Same sealed clarify
    text on refusal.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super(N171.NameVal171Mixin, self).hear(turn)  # type: ignore[misc]
        return guard_actions_b(actions)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            msg = screen_name_value_b(action.get("name"),
                                      action.get("relation"),
                                      action.get("value", ""))
            if msg is not None:
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": msg}
        return super(N171.NameVal171Mixin, self)._act(action)  # type: ignore[misc]
