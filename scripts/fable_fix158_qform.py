#!/usr/bin/env python3
"""Experiment 158 -- THE ONE CHANGE: question-surface normalisation.

Wraps loop150 (read-only). Before the question parser, rewrite:

  1. tell me|show me|give me X's R  ->  What is X's R?
     tell me who/what ...           ->  the bare question
     (fires only when the remainder starts with a question word/auxiliary
     or contains a possessive 's; "tell me more" / "show me the money"
     do not fire)
  2. leading what's|who's|where's|when's -> what|who|where|when is
     (leading position only, straight or curly apostrophe)
  3. trailing [?.!]+ collapsed to one "?"

The rewrite is returned ONLY when (a) the candidate differs from the
collapsed original, (b) the original contains "?" or "!" OR rule 1 fired
(so bare statements, "-." teaches and exp-151's no-"?" territory are
never eligible), (c) no interior "?" / "!" sits before the terminal mark
run (glued multi-sentence turns are never spliced into one ask), and
(d) the candidate through the UNCHANGED loop yields an ask action.
Otherwise the original turn passes through untouched.

Cooperative MIXIN (Qform158Mixin): hear() probes super().hear(candidate)
first and returns it iff it asks; else super().hear(original). hear() is
side-effect free w.r.t. the notebook (last_stage is overwritten by the
final call), so the probe cannot change stored state. No existing file
is edited.
"""

from __future__ import annotations

import re

# Rule 1 opener.
_IMPERATIVE_RE = re.compile(
    r"^(tell me|show me|give me)\s+(.+?)\s*$", re.I | re.S)
# Rule 1 remainder already a question (kept as-is, marks collapsed).
_QUESTION_LEAD_RE = re.compile(
    r"^(who|what|where|when|which|how|is|are|was|does|do|did|can|could)\b",
    re.I)
# Rule 2 leading contraction (straight or curly apostrophe).
_CONTRACTION_RE = re.compile(
    r"^(what|who|where|when)('\u2009s|'s|\u2019s)\b", re.I)
_TRAILING_MARKS_RE = re.compile(r"[?.!]+\s*$")


def _split_terminal_run(work: str) -> tuple[str, str]:
    """Split (stem, terminal-mark-run) so interior marks stay visible."""
    m = _TRAILING_MARKS_RE.search(work)
    if m is None:
        return work, ""
    return work[:m.start()], m.group()


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def normalize_question_surface(turn: str) -> tuple[str | None, bool]:
    """Return (candidate, imperative_fired).

    candidate is None when no rule changes the text. The caller still
    gates on eligibility ("?"/"!" present or imperative fired) and on
    the candidate parsing as a question by the unchanged loop.
    """
    text = _collapse(turn)
    if not text:
        return None, False
    imperative_fired = False
    work = text.replace("\u2019", "'")

    m = _IMPERATIVE_RE.match(work)
    if m is not None:
        rest = _collapse(m.group(2))
        rest_stem, _ = _split_terminal_run(rest)
        if ("?" in rest_stem) or ("!" in rest_stem):
            # Glued multi-sentence turn, not a phone imperative.
            return None, False
        if _QUESTION_LEAD_RE.match(rest):
            core = _TRAILING_MARKS_RE.sub("", rest).strip()
            cand = (core + "?") if core else None
            imperative_fired = True
        elif "'s" in rest:
            core = _TRAILING_MARKS_RE.sub("", rest).strip()
            cand = ("What is " + core + "?") if core else None
            imperative_fired = True
        else:
            cand = None
        if cand is None or cand == text:
            return None, False
        return cand, imperative_fired

    stem, _run = _split_terminal_run(work)
    if ("?" in stem) or ("!" in stem):
        # Interior mark: glued multi-sentence turn (e.g. red-team "Who is
        # Mira's city? also Mira's pet is a cat."), not a phone-typing
        # mark stack. Untouched, so the candidate can never splice two
        # sentences into one garbage ask (underscore-leak guard for Q4).
        return None, False
    cand = _CONTRACTION_RE.sub(
        lambda m: m.group(1) + " is", work, count=1)
    cand = _TRAILING_MARKS_RE.sub("?", cand)
    if cand == text:
        return None, False
    return cand, False


def eligibility_ok(original: str, candidate: str,
                   imperative_fired: bool) -> bool:
    """Never touch 151's no-"?" territory or bare statements/teaches."""
    if candidate is None or candidate == _collapse(original):
        return False
    if imperative_fired:
        return True
    return ("?" in original) or ("!" in original)


class Qform158Mixin:
    """Stackable mixin: question-surface normalisation before parsing.

    Cooperative (super() first on the candidate): the rewrite is used
    only when the unchanged loop parses the candidate as a question
    (an ask action); otherwise the original turn is heard unchanged.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        cand, fired = normalize_question_surface(turn)
        if cand is not None and eligibility_ok(turn, cand, fired):
            try:
                probe = super().hear(cand)  # type: ignore[misc]
            except Exception:
                probe = None
            if isinstance(probe, list) and any(
                    isinstance(a, dict) and a.get("act") == "ask"
                    for a in probe):
                return probe
        return super().hear(turn)  # type: ignore[misc]
