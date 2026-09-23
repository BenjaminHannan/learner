#!/usr/bin/env python3
"""Experiment 139c -- THE ONE CHANGE vs loop138b: strip lowercase chat tails.

Director probe 04:35 on loop138b: trailing chat words glue onto stored
values ("Tom's boss is Ann too" stores "Ann too"; "Rex's color is black
now" corrects to "black now"). This module strips, from the END of a
teach/correct value span, a CLOSED list of lowercase chat tails, fixed
here before any panel read:

  SINGLES: too, also, actually, though, tho, lol, lmao, haha, btw, again,
    now, anyway, then, instead, rn, right, ok, okay
  PAIRS: as well, i guess

Rules (all in this file, no existing file edited):
  * Each tail is stripped only when typed entirely lowercase, optionally
    followed by trailing punctuation/emoji (exposed by the exp-140
    cleaner, applied read-only first), and only when at least one value
    word remains (a value that IS just "too" is left alone).
  * Capitalised tail words are never stripped ("Take That", "Right Said
    Fred", "Home Alone", "Say It Again" keep their form) -- matching is
    case-sensitive exact.
  * Stripping repeats (stacked tails, e.g. "Oslo too lol" -> "Oslo").
  * If the stripped tail was "now" / "instead" / "actually" and the fact
    already exists with another value, no special path is needed: the
    caller (loop139c _act) strips BEFORE super()._act(), so the existing
    correction prompt runs with the clean value automatically.
"""

from __future__ import annotations

import copy

import fable_fix140_tail as T140  # noqa: E402 (cleaner, read-only)

# THE CLOSED LIST -- fixed before any panel read, written in the doc.
TAIL_SINGLE = frozenset({
    "too", "also", "actually", "though", "tho", "lol", "lmao", "haha",
    "btw", "again", "now", "anyway", "then", "instead", "rn", "right",
    "ok", "okay",
})
TAIL_PAIR = (("as", "well"), ("i", "guess"))

_CORRECTION_TAILS = frozenset({"now", "instead", "actually"})


def strip_chat_tail(value: str) -> tuple[str, str | None]:
    """Strip trailing lowercase chat tails. Returns (cleaned, stripped).

    stripped is the outermost removed tail word ("well" for "as well",
    "guess" for "i guess") or None when nothing was removed. The cleaned
    span always keeps at least one word; otherwise the input is returned
    unchanged (collapsed).
    """
    s = " ".join(str(value).split())
    if not s:
        return s, None
    stripped: str | None = None
    for _ in range(4):  # more than enough for stacked tails
        t = T140.clean_span(s)
        toks = t.split(" ")
        removed: list[str] = []
        if len(toks) >= 3 and (toks[-2], toks[-1]) in TAIL_PAIR:
            removed = toks[-2:]
        elif len(toks) >= 2 and toks[-1] in TAIL_SINGLE:
            removed = toks[-1:]
        else:
            break
        rest = " ".join(toks[:-len(removed)])
        if not rest:
            break  # at least one value word must remain
        if stripped is None:
            stripped = removed[-1]
        s = rest
    if stripped is not None:
        # The comma (if any) before the tail belonged to the tail
        # boundary ("Ann, too" -> "Ann", not "Ann,"); only after a strip.
        s = s.rstrip()
        if s.endswith(","):
            s = s[:-1].rstrip()
    out = T140.clean_span(s)
    if not out:
        return " ".join(str(value).split()), None
    return out, stripped


def sanitize_action(action: dict) -> dict:
    """Copy of a teach/correct action with the chat tail stripped."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    out = copy.copy(action)
    if "value" in out:
        cleaned, _ = strip_chat_tail(out.get("value", ""))
        if cleaned:
            out["value"] = cleaned
    return out


def sanitize_actions(actions: list[dict]) -> list[dict]:
    return [sanitize_action(a) for a in list(actions)]


class ChatTailMixin:
    """Stackable mixin: strip lowercase chat tails on every teach path."""

    @staticmethod
    def strip_chat_tail(value: str) -> tuple[str, str | None]:
        return strip_chat_tail(value)

    @classmethod
    def sanitize_action(cls, action: dict) -> dict:
        return sanitize_action(action)

    @classmethod
    def sanitize_actions(cls, actions: list[dict]) -> list[dict]:
        return sanitize_actions(actions)
