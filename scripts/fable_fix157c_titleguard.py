#!/usr/bin/env python3
"""Experiment 157c -- THE ONE CHANGE: capitalised filler + Capitalised follow never strips.

Base: loop157b (scripts/fable_loop157b_agent.py = loop157 + the exp-157b
capitalised/stacked filler mixin). Director probe 05:30 on loop157b:
"Hey Jude's singer is Paul." saves under "Jude" (WRONG-WRITE);
"Oh Brother's director is Joel." saves under "Brother". Cause: 157b's
strip (scripts/fable_fix157b_capfiller.py:59, strip_one_anycase157b,
driven by CapFiller157bMixin.hear at :137) strips a capitalised filler
whatever follows it, so "Hey"/"Oh" are eaten as fillers and the
possessive frame re-parses on the shortened name.

THE RULE (TitleGuard157cMixin, cooperative, ears hear() only):
  1. Pure gate blocked157c(turn): find the turn-initial filler by the SAME
     longest-match closed list as 157b (any capitalisation). If none, or
     the filler as typed is all-lowercase (157's sealed rule), or the
     filler is followed by punctuation (comma, period, !, ?, ellipsis,
     dash, etc.), or the next word starts lowercase -> NOT blocked.
     Else (capitalised filler followed directly, no punctuation, by a
     Capitalised word) -> BLOCKED. The possessive title case ("Hey
     Jude's", "Oh Brother's") is the motivating instance of this block.
  2. hear(): if blocked, return the DEEP base parse
     (Loop157Ears.hear on the original turn, bypassing 157b's strip), so
     the whole capitalised run including the filler word is treated as
     the name -- exactly how loop157b handles any other multi-word name
     (refuse/clarify; refusing is fine, a wrong save is not).
     If not blocked, delegate to super().hear() (full loop157b
     behaviour, byte-identical by construction).

Lowercase fillers, comma fillers, punctuation/lowercase follows, stacked
pairs, correction markers, values, relation keys and clarification paths
are untouched. No existing file is edited; loop157b is imported
read-only.
"""

from __future__ import annotations

import fable_fix157b_capfiller as B157B  # noqa: E402 (closed list, read-only)
import fable_loop157_agent as L157  # noqa: E402 (deep base, read-only)

# Same closed filler list as 157/157b (longest-match order kept).
FILLER157C = B157B.FILLER157B

# Punctuation that may follow a capitalised filler without blocking the
# 157b strip (comma, period, !, ?, ellipsis, dash, quotes, brackets...).
PUNCT157C = frozenset(list(",.!?;:…-–—'\"’‘“”()[]"))


def _collapse(turn: str) -> str:
    return " ".join(str(turn).split())


def first_filler157c(text: str) -> tuple[str, str] | None:
    """Turn-initial filler match -> (typed, after), longest-match first."""
    low = text.lower()
    for phrase in FILLER157C:
        if low == phrase:
            return (text, "")
        if (low.startswith(phrase + " ") or low.startswith(phrase + "\t")
                or low.startswith(phrase + ",")):
            return (text[:len(phrase)], text[len(phrase):])
    return None


def blocked157c(turn: str) -> bool:
    """Pure function: True only when 157b's strip must not fire.

    Capitalised filler (as typed, not all-lowercase) followed directly
    (no comma/punctuation) by a Capitalised word -> blocked. Everything
    else (no filler, lowercase filler, punctuation follow, lowercase-word
    follow, empty remainder) -> not blocked.
    """
    text = _collapse(turn).lstrip()
    if not text:
        return False
    m = first_filler157c(text)
    if m is None:
        return False
    typed, after = m
    if after.startswith(","):
        return False
    if typed == typed.lower():
        return False
    rest = after.strip()
    if not rest:
        return False
    ch = rest[0]
    if ch in PUNCT157C:
        return False
    if ch.islower():
        return False
    return True


def fires157b(turn: str) -> bool:
    """Pure function: 157b's strip would attempt (for pre-seal scans)."""
    return bool(B157B.strip_candidates157b(turn))


class TitleGuard157cMixin:
    """Stackable mixin: block 157b's strip on filler+Capitalised runs.

    Cooperative: on ears hear(), blocked turns return the deep loop157
    parse of the ORIGINAL turn (whole capitalised run treated as the
    name); every other turn delegates to super().hear() (loop157b,
    byte-identical by construction).
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        if blocked157c(turn):
            return L157.Loop157Ears.hear(self, turn)  # type: ignore[arg-type]
        return super().hear(turn)  # type: ignore[misc]
