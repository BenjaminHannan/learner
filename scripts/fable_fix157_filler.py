#!/usr/bin/env python3
"""Experiment 157 -- THE ONE CHANGE: strip ONE leading discourse filler.

Base: loop150 (scripts/fable_loop150_agent.py =
loop129b + 139b value guard + 150 subject guard; loop150-config sealed in
artifacts/fable-fix150-20260922/). The exp-152 red team (class N4) found
"btw/also/oh and + teach" refused: scripts/fable_agent_loop.py:96
(_STATEMENT is ^-anchored, so the filler becomes part of the subject) and
:141 (the polluted subject "btw marta" fails the one-word-name check);
:94 (_QUESTION) is ^-anchored the same way, so filler+question fails too.
The 150 subject guard (scripts/fable_fix150_subjectguard.py) only strips
fillers from the subject span AFTER the parse, so it can never recover
these turns.

THE RULE (Filler157Mixin, cooperative, ears hear() only -- no _act change:
actions carry no raw text, and both base and remainder calls already run
the full loop150 chain including the 150 subject guard):
  1. hear() runs the unchanged loop150 hear first. If it parses as a
     complete teach/correct or question (ask), return it untouched.
  2. Else strip exactly ONE leading discourse filler from the closed list
     below (longest-match, comma-or-lowercase title rule) and run the
     REMAINDER through the unchanged loop150 hear. Use the remainder's
     result ONLY if it parses as a complete teach/correct or question;
     otherwise return the original result byte-identical.
Correction markers (actually, no, wait, sorry, I meant) are NOT in the
filler list and are never stripped. Titles/names that begin with a filler
word ("Hey Jude", "Also Sprach Zarathustra", "So Far Away") are protected
by the title rule: a capitalised filler without a trailing comma is never
stripped (their remainders would parse as multi-word-subject teaches on
the bench73 path, so the parse gate alone would not save them).

No existing file is edited; loop150 is imported read-only.
"""

from __future__ import annotations

# Closed filler list, sealed before any run. Order = longest-match first.
# One-line reasons: all are turn-initial discourse markers a phone user
# types before the real sentence; none is a correction marker and none
# can start a one-word person name in our single-token-name world.
FILLER157 = (
    "by the way",  # multi-word textspeak filler, never a name lead
    "okay so",     # multi-word discourse opener, never a name lead
    "oh and",      # multi-word discourse opener, never a name lead
    "ok so",       # multi-word discourse opener, never a name lead
    "anyway",      # discourse filler, never a name lead
    "also",        # additive filler (152 N4 case), never a name lead
    "hey",         # greeting filler, never a name lead
    "fyi",         # preface marker, never a name lead
    "well",        # discourse filler, never a name lead
    "and",         # connective lead, never a name lead
    "btw",         # textspeak filler (152 N4 case), never a name lead
    "oh",          # discourse filler (152 N4 case), never a name lead
    "so",          # discourse filler, never a name lead
    "ok",          # discourse filler, never a name lead
    "okay",        # spelling variant of ok, distinct token
)

# Complete parses: the remainder must be a full teach/correct or question.
COMPLETE157 = ("teach", "correct", "ask")


def _collapse(turn: str) -> str:
    return " ".join(str(turn).split())


def strip_one_filler157(turn: str) -> str | None:
    """Pure function: turn -> remainder after ONE leading filler, or None.

    Title rule (stated in PASSMARKS): strip only when the filler as typed
    is all-lowercase ("btw marta..." strips) or is followed by a comma
    ("Hey, Marta..." strips; "Hey Jude's..." never strips). Exactly one
    filler is removed; the rest of the turn is returned untouched.
    """
    text = _collapse(turn).lstrip()
    if not text:
        return None
    low = text.lower()
    for phrase in FILLER157:
        if low == phrase:
            rest = ""
        elif low.startswith(phrase + " ") or low.startswith(phrase + "\t"):
            rest = text[len(phrase):]
        elif low.startswith(phrase + ","):
            rest = text[len(phrase):]
        else:
            continue
        typed = text[:len(phrase)]
        follows_comma = rest.startswith(",")
        if follows_comma:
            rest = rest[1:]
        elif typed != typed.lower():
            # Capitalised filler without a comma: probably a title/name
            # ("Hey Jude", "Also Sprach ...", "So Far Away"). Do not strip.
            # (Try shorter phrases too: "oh and" capitalised blocks "oh".)
            continue
        rest = rest.strip()
        if not rest:
            return None
        return rest
    return None


def is_complete157(actions) -> bool:
    """True when the unchanged loop parsed a complete teach or question."""
    try:
        acts = list(actions)
    except TypeError:
        return False
    if not acts:
        return False
    return all(isinstance(a, dict) and a.get("act") in COMPLETE157
               for a in acts)


def _stage_of(obj):
    return (getattr(obj, "last_stage", None),
            getattr(obj, "last_score", None))


def _restore_stage(obj, saved) -> None:
    stage, score = saved
    try:
        if stage is not None:
            obj.last_stage = stage
        if score is not None:
            obj.last_score = score
    except AttributeError:
        pass


class Filler157Mixin:
    """Stackable mixin: ONE leading-filler strip gated on a full re-parse.

    Cooperative (super() first, never edits): on ears hear() it runs the
    unchanged loop150 hear on the original turn; only a clarify/fallback
    result triggers the single-strip attempt, and the stripped remainder
    is accepted only when the unchanged loop parses it as a complete
    teach/correct or question. All other paths (values, relation keys,
    forget/ask/clarify replies, correction markers) are byte-identical.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        base = super().hear(turn)  # type: ignore[misc]
        if is_complete157(base):
            return base
        rest = strip_one_filler157(turn)
        if rest is None:
            return base
        saved = _stage_of(self)
        try:
            alt = super().hear(rest)  # type: ignore[misc]
        except Exception:
            _restore_stage(self, saved)
            return base
        if is_complete157(alt):
            return alt
        _restore_stage(self, saved)
        return base
