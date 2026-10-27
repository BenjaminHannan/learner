#!/usr/bin/env python3
"""Experiment 157b -- THE ONE CHANGE: also strip a CAPITALISED filler.

Base: loop157 (scripts/fable_loop157_agent.py = loop150 + the exp-157
leading-filler mixin; loop157-config sealed in
artifacts/fable-filler157-20260922/). Director probe 04:20 on loop157:
"btw Tom's sister is Jo." and "also, Jo's teacher is Max." save, but
"Oh and Tom's mother is Rita.", "So Tom's boss is Bob.",
"Oh and Jo's teacher is Max." and "Btw who is Tom's sister's teacher?"
are refused. Cause: 157's title rule
(scripts/fable_fix157_filler.py:67-101; the capitalised block is lines
92-96) strips a leading filler only when it is typed all-lowercase or
followed by a comma. Phones auto-capitalise the first word, so the most
common phone form is exactly the one that fails.

THE RULE (CapFiller157bMixin, cooperative, ears hear() only -- no _act
change: actions carry no raw text, and base + remainder calls already run
the full loop157 chain including the 157 strip and the 150 subject
guard):
  1. hear() runs the unchanged loop157 hear first. If it parses as a
     complete teach/correct or question (ask), return it untouched.
  2. Else strip up to TWO leading discourse fillers from the SAME closed
     list as 157 (longest-match per step, any capitalisation, each
     optionally followed by one comma; this covers single capitalised
     fillers "Btw"/"Also"/"So"/"Oh"/... and stacked pairs such as
     "Okay so", "Oh and btw", "And also") and run each REMAINDER (after
     one strip, then after two) through the unchanged loop157 hear. Use a
     remainder's result ONLY if it parses as a complete teach/correct or
     question; otherwise return the original result byte-identical.
Titles/names that begin with a filler word ("Hey Jude",
"Also Sprach Zarathustra", "So Far Away", "Well Played") keep word one
exactly as on loop157: their remainders ("Jude", "Sprach ...",
"Far Away's ...", "Played ...") do not parse as complete frames, so the
parse gate rejects them by construction. Correction markers (actually,
no, wait, sorry, I meant) are NOT in the filler list and are never
stripped (and the base already parses them, so step 1 returns first).

No existing file is edited; loop157 is imported read-only.
"""

from __future__ import annotations

import fable_fix157_filler as F157  # noqa: E402 (sealed filler list + gate)

# Same closed filler list as 157 (longest-match order kept).
FILLER157B = F157.FILLER157

# Complete parses: the remainder must be a full teach/correct or question.
COMPLETE157B = F157.COMPLETE157

# Max stacked fillers stripped ("Oh and btw", "And also", ...).
MAX_STACK157B = 2


def _collapse(turn: str) -> str:
    return " ".join(str(turn).split())


def strip_one_anycase157b(text: str) -> str | None:
    """Pure function: text -> remainder after ONE leading filler, or None.

    Same longest-match list as 157, but capitalisation is ignored: a
    capitalised filler ("Btw", "Also,") strips exactly like its lowercase
    twin. Each filler may be followed by one comma. Exactly one filler is
    removed; the rest of the text is returned untouched. Titles are NOT
    protected here -- the parse gate in the mixin protects them (their
    remainders never parse as complete frames).
    """
    low = text.lower()
    for phrase in FILLER157B:
        if low == phrase:
            rest = ""
        elif low.startswith(phrase + " ") or low.startswith(phrase + "\t"):
            rest = text[len(phrase):]
        elif low.startswith(phrase + ","):
            rest = text[len(phrase):]
        else:
            continue
        if rest.startswith(","):
            rest = rest[1:]
        rest = rest.strip()
        if not rest:
            return None
        return rest
    return None


def strip_candidates157b(turn: str) -> list[str]:
    """Pure function: turn -> [remainder-after-1, remainder-after-2]."""
    text = _collapse(turn).lstrip()
    if not text:
        return []
    out: list[str] = []
    first = strip_one_anycase157b(text)
    if first is None:
        return []
    out.append(first)
    second = strip_one_anycase157b(first)
    if second is not None:
        out.append(second)
    return out


def is_complete157b(actions) -> bool:
    """True when the unchanged base parsed a complete teach or question."""
    return F157.is_complete157(actions)


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


class CapFiller157bMixin:
    """Stackable mixin: capitalised/stacked filler strip gated on re-parse.

    Cooperative (super() first, never edits): on ears hear() it runs the
    unchanged loop157 hear on the original turn; only a clarify/fallback
    result triggers the strip attempt, and a stripped remainder is
    accepted only when the unchanged loop157 chain parses it as a
    complete teach/correct or question. All other paths (values, relation
    keys, forget/ask/clarify replies, correction markers, titles) are
    byte-identical to loop157.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        base = super().hear(turn)  # type: ignore[misc]
        if is_complete157b(base):
            return base
        cands = strip_candidates157b(turn)
        if not cands:
            return base
        saved = _stage_of(self)
        for rest in cands:
            try:
                alt = super().hear(rest)  # type: ignore[misc]
            except Exception:
                _restore_stage(self, saved)
                return base
            if is_complete157b(alt):
                return alt
            _restore_stage(self, saved)
        return base
