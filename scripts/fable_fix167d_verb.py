#!/usr/bin/env python3
"""Experiment 167d -- THE ONE CHANGE vs loop167b: widen the closed verb table.

Director probe 08:57 on loop167b: "Tom works at Acme.",
"Where does Tom work?", "Rana speaks Hindi.",
"What language does Rana speak?" all clarify
("I didn't understand that. Could you say it another way?") while the
possessive twins save and answer today ("Tom's employer is Acme." ->
teach (Tom, employer, Acme); "Rana's language is Hindi." -> teach
(Rana, language, Hindi) -- relation keys verified on loop167b pre-seal;
"What is Rana's language?" answers).

THE ONE CHANGE (this file only; no 167/167b file edited, no other
experiment file edited): four new rows beside V167's closed table,
rewritten to the possessive twin and handed to super().hear() untouched:

  "X works at Y"                 -> "X's employer is Y."
  "X speaks Y"                   -> "X's language is Y."
  "Where does X work?"           -> "Who is X's employer?"
  "What language(s) does X speak?" -> "What is X's language?"

"Who does X work for?" stays exactly as 167/167b left it (V167 owns it;
this file never claims it -- disjoint shapes). The fact written /
answer given is the possessive path's own, byte-identical by the same
construction as 167 (this mixin owns no save/ask code).

Guards (same as 167/167b): single capital-lead token subject with the
150c whole-subject veto; statements need no "?" anywhere and no ";" or
extra "." in the value; corrections (Actually,/No,) preserved onto the
twin; negations ("doesn't/does not work", "doesn't speak"), hedges
("maybe", "I think", ...), tense changes ("used to work", "worked",
"spoke"), hypotheticals, yes/no verb questions ("Does Rana speak
Hindi?"), reverse questions ("Who works at Acme?"), and multi-word
subjects all fall through to the base clarify path with 0 writes.

Value screen (same as 167b, ValueScreen167b stays OUTSIDE this mixin in
scripts/fable_loop167d_agent.py): a claimed new-shape STATEMENT's
object is stripped with loop139e's sealed tail machinery and refused
(empty / article-determiner-led / lowercase-led) with loop167's own
no-write clarify -- implemented here with S167B.screen_value
(imported read-only) because S167B's twin regex only matches 167's
three surfaces. New-shape QUESTIONS pass straight to the twin (no
object to screen), exactly as 167b does for 167's questions.

No existing file is edited. Base modules are imported read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix150c_closedclass as C150  # noqa: E402 (subject veto, read-only)
import fable_fix167_verb as V167  # noqa: E402 (old table owner, read-only)
import fable_fix167b_valuescreen as S167B  # noqa: E402 (value screen, read-only)

# ----------------------------------------------------------------------------
# Added closed rows (fixed in design/v3/30-modes/167d-verb-muse.md before
# any registered run). Old rows stay owned by V167 (never redefined here).
# ----------------------------------------------------------------------------
# (verb shape, possessive relation surface, inventory relation)
VERB_STATEMENTS_167D: tuple = (
    ("works at", "employer", "employer"),
    ("speaks", "language", "language"),
)

VERB_QUESTIONS_167D: tuple = (
    ("Where does/do X work?", "Who is X's employer?"),
    ("What language(s) does/do X speak?", "What is X's language?"),
)

_NAME = V167._NAME

_CORRECTION_LEAD = re.compile(r"^(actually\s*,|actually\s+|no\s*,|no\s+)(.+)$",
                              re.IGNORECASE | re.DOTALL)

_STMT_WORKAT = re.compile(r"^(" + _NAME + r")\s+works?\s+at\s+(.+?)\s*$",
                          re.DOTALL)
_STMT_SPEAK = re.compile(r"^(" + _NAME + r")\s+speaks?\s+(.+?)\s*$",
                         re.DOTALL)
# bench73's longer template owns "X speaks the language of Y"
# (scripts/fable_bench73_english_arm.py: "(.+?) speaks the language of
# (.+?)" -> languages_spoken_written_or_signed) -- the base teaches it
# today, so the mixin DECLINES those statements, exactly as 167 declines
# "was born in the city of" shapes.
_SPEAK_LANGOF = re.compile(r"^the\s+language\s+of\s+.+",
                           re.IGNORECASE | re.DOTALL)

_ASK_WORKWHERE = re.compile(r"^where\s+does?\s+(" + _NAME +
                            r")\s+work\s*\??\s*$",
                            re.IGNORECASE | re.DOTALL)
_ASK_LANG = re.compile(r"^what\s+languages?\s+does?\s+(" + _NAME +
                       r")\s+speak\s*\??\s*$",
                       re.IGNORECASE | re.DOTALL)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _strip_period(body: str) -> str:
    if body.endswith(".") and not body.endswith(".."):
        return body[:-1].strip()
    return body


def _subject_ok(name: str) -> bool:
    """Single capital-lead token and not a closed-class subject (150c)."""
    if not re.fullmatch(_NAME, name or ""):
        return False
    try:
        if C150.is_closed_class_subject(name):
            return False
    except Exception:
        return False
    return True


def parse_verb167d_statement(turn: str) -> dict | None:
    """Raw turn -> {twin} for the 2 ADDED verb statements, else None.

    Old shapes ("works for", "lives in", "was born in", "Who does X work
    for?", ...) return None here -- V167 owns them and the outer 167b
    screen handles them before this mixin ever sees them. The
    bench73-owned "X speaks the language of Y" shape also returns None.
    """
    text = _norm(turn)
    if not text:
        return None
    if text.rstrip().endswith("?"):
        return None
    body = _strip_period(text)
    if not body:
        return None
    corr = ""
    m = _CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        corr, body = m.group(1), m.group(2).strip()
        corr = "Actually, " if corr.strip().lower().startswith("actually") \
            else "No, "
    for pat, rsurf in ((_STMT_WORKAT, "employer"),
                       (_STMT_SPEAK, "language")):
        m = pat.fullmatch(body)
        if m is None:
            continue
        name, val = m.group(1).strip(), m.group(2).strip()
        if not val or "?" in val or ";" in val or "?" in name:
            return None
        if "." in val:
            return None  # two facts packed in one turn: one fact at a time
        if not _subject_ok(name):
            return None
        if pat is _STMT_SPEAK and _SPEAK_LANGOF.match(val):
            return None  # bench73's longer template owns this shape
        return {"kind": "statement", "twin": f"{corr}{name}'s {rsurf} is "
                f"{val}.", "name": name, "rsurf": rsurf, "val": val,
                "corr": corr}
    return None


def parse_verb167d_question(turn: str) -> dict | None:
    """Raw turn -> {twin} for the 2 ADDED verb questions, else None."""
    text = _norm(turn)
    if not text:
        return None
    for pat, mk in ((_ASK_WORKWHERE,
                     lambda n: f"Who is {n}'s employer?"),
                    (_ASK_LANG,
                     lambda n: f"What is {n}'s language?")):
        m = pat.fullmatch(text)
        if m is None:
            continue
        name = m.group(1).strip()
        if not _subject_ok(name):
            return None
        return {"kind": "question", "twin": mk(name)}
    return None


def parse_verb167d_turn(turn: str) -> dict | None:
    """Statements first, then questions; None when 167d adds nothing."""
    hit = parse_verb167d_statement(turn)
    if hit is not None:
        return hit
    return parse_verb167d_question(turn)


class Verb167dMixin:
    """Stackable mixin (inside ValueScreen167b): added verb turns become
    their possessive twin, rest delegates.

    Cooperative: a claimed NEW-shape question is rewritten to its
    possessive twin and handed to super().hear(); a claimed NEW-shape
    statement's object must pass S167B.screen_value (loop139e tail
    strip + determiner/lowercase veto, the same screen 167b applies),
    else the turn replies loop167's own no-write clarify with no write;
    otherwise the twin rebuilt with the stripped object is handed on.
    Anything else -- including every shape V167/167b owns -- falls
    through untouched.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            try:
                parsed = parse_verb167d_turn(turn)
            except Exception:
                parsed = None
            if parsed is not None:
                if parsed.get("kind") == "question":
                    return super().hear(parsed["twin"])  # type: ignore[misc]
                clean = None
                try:
                    clean = S167B.screen_value(parsed["val"])
                except Exception:
                    clean = None
                if clean is None:
                    return [{"act": "clarify",
                             "text": S167B.NO_WRITE_CLARIFY}]
                twin = (f"{parsed['corr']}{parsed['name']}'s "
                        f"{parsed['rsurf']} is {clean}.")
                return super().hear(twin)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
