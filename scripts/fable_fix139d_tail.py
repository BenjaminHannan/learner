#!/usr/bin/env python3
"""Experiment 139d -- THE ONE CHANGE vs loop139c: clarify unknown chat tails.

Director probe 05:16 on loop139c (which strips only a closed list):
"Kim's city is Rome honestly" saves "Rome honestly"; "Kim's mother is
Rose tbh" saves "Rose tbh". A closed list will always miss words.

THE ONE CHANGE (this file, list fixed here before any panel read): after
139c's strip, if a teach/correct value's FIRST word is Capitalised (first
character A-Z) and its LAST word is all-lowercase letters ([a-z]+) and is
NOT a name connector, the turn does not write and replies exactly:

  Did you mean "<value without the last lowercase words>"? Please say it
  again without the extra words.

The trailing RUN of such lowercase non-connector words is stripped
("Rome honestly tbh" -> "Rome"). The closed connector list (fixed here):

  of, the, and, de, da, del, della, di, du, des, van, von, der, den, la,
  le, les, y, e, al, el, bin, ibn, upon, on, in, at, for, a, an, to, with

Values that start lowercase ("black", "pizza", "green tea") and
all-Capitalised or connector-ending names ("Salt Lake City", "Take That",
"Lord of the Rings", "Leonardo da Vinci", "House of Wax") never trigger
and stay byte-identical to loop139c. Known honest edge: a real value such
as "Pad thai" (Capitalised + lowercase tail-shaped end) IS questioned;
reported, not hidden.
"""

from __future__ import annotations

import copy
import re

import fable_fix139c_tail as T139c  # noqa: E402 (139c strip runs first, read-only)

# THE CLOSED CONNECTOR LIST -- fixed before any panel read, in the doc.
CONNECTORS = frozenset({
    "of", "the", "and", "de", "da", "del", "della", "di", "du", "des",
    "van", "von", "der", "den", "la", "le", "les", "y", "e", "al", "el",
    "bin", "ibn", "upon", "on", "in", "at", "for", "a", "an", "to",
    "with",
})

_LOWER_WORD_RE = re.compile(r"^[a-z]+$")


def clarify_text(clean: str) -> str:
    """The exact 139d clarify reply for a de-tailed value."""
    return 'Did you mean "%s"? Please say it again without the extra words.' % clean


def unknown_tail_split(value: str) -> tuple[str, list[str]] | None:
    """Split (clean_base, tail_run) when the value ends in unknown chat tail.

    Runs AFTER 139c's strip (callers sanitize first). Triggers only when:
      * >= 2 words remain,
      * the FIRST word starts with A-Z (Capitalised),
      * the trailing run (1+ words) is all all-lowercase-letters words,
        none of which is a name connector.
    Returns None when the value must pass through byte-identical.
    """
    s = " ".join(str(value).split())
    if not s:
        return None
    toks = s.split(" ")
    if len(toks) < 2:
        return None
    first = toks[0]
    if not (first and first[0].isalpha() and first[0].isupper()):
        return None
    i = len(toks) - 1
    run: list[str] = []
    while i >= 1:
        w = toks[i]
        if _LOWER_WORD_RE.match(w) and w not in CONNECTORS:
            run.append(w)
            i -= 1
        else:
            break
    if not run:
        return None
    clean = " ".join(toks[:i + 1])
    if not clean:
        return None
    return clean, run[::-1]


def check_value(value: str) -> str | None:
    """Clarify message for a post-139c value, or None to store as-is."""
    split = unknown_tail_split(value)
    if split is None:
        return None
    return clarify_text(split[0])


def guard_action(action: dict) -> dict:
    """teach/correct with unknown tail -> clarify action; else 139c copy."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    cleaned_action = T139c.sanitize_action(action)
    msg = check_value(cleaned_action.get("value", ""))
    if msg is not None:
        return {"act": "clarify", "text": msg}
    return cleaned_action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class UnknownTailMixin:
    """Stackable mixin: clarify unknown lowercase tails on every teach path."""

    @staticmethod
    def unknown_tail_split(value: str) -> tuple[str, list[str]] | None:
        return unknown_tail_split(value)

    @classmethod
    def guard_action(cls, action: dict) -> dict:
        return guard_action(action)

    @classmethod
    def guard_actions(cls, actions: list[dict]) -> list[dict]:
        return guard_actions(actions)
