#!/usr/bin/env python3
"""Experiment 167 -- THE ONE CHANGE: verb-phrase facts map onto existing relations.

Ben's ruling (2026-09-22): anything that can be read as a relation should be.
Today loop162b clarifies every verb-phrase turn ("Kwame lives in Accra." ->
"I didn't understand that. Could you say it another way?", from
scripts/fable_agent_loop.py FakeEars.hear fallthrough) while the possessive
form of the same fact saves ("Kwame's city is Accra." -> teach). THE ONE
CHANGE: a CLOSED table (VERB_STATEMENTS / VERB_QUESTIONS below, fixed in
design/v3/30-modes/167-verb-muse.md before any panel read) mapping four verb
phrases onto relations that ALREADY exist in the base's relation inventory:

  "lives in"    -> city            (FakeEars possessive inventory; the base
                                    saves + answers "X's city is Y" today;
                                    same pairing the demo uses, see
                                    scripts/fable_demo88_rehearse.py:60-61)
  "works for"   -> employer        (ALLOWED_KEYS, scripts/fable_fix162_thename.py:79;
                                    B92 cue 'works for')
  "is married to" -> spouse        (ALLOWED_KEYS + bench73 template
                                    scripts/fable_bench73_english_arm.py:96 --
                                    the base ALREADY teaches this verb shape,
                                    so the mixin DECLINES those statements)
  "was born in" -> place_of_birth  (ALLOWED_KEYS + B92 cue 'born')

Each claimed statement is rewritten to EXACTLY its possessive twin ("X lives
in Y." -> "X's city is Y.") and each claimed question to its possessive twin
("Where does X live?" -> "Where is X's city?"), then handed to
super().hear() untouched. The fact written / answer given is therefore the
possessive path's own, byte-identical by construction -- the mixin owns no
save code, no ask code, no screens: value/hearsay/subject screens, the loop
_act guards, corrections ("Actually, ..."), and the mouth all run as the
possessive turn runs today.

Never claimed (safe decline to the base clarify path, 0 writes):
negations ("doesn't live", "does not work", "isn't married", "wasn't born"),
tense changes ("lived", "used to live", "will live", "will move to",
"worked", "is working"), hedges ("I think ...", "Maybe ...", "Rumor has it
...", "probably", "might"), hypotheticals ("If ... lived ...", "Would ...
live ..."), yes/no verb questions ("Does X live in Y?"), multi-word or
closed-class subjects (whole-subject 150c veto), "?"-terminated statements,
and the base-owned shapes ("X is married to Y" statements via bench73,
"X was born in the city of Y" via bench73:114).

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

# ----------------------------------------------------------------------------
# Closed table (fixed in the design doc before any panel read).
# (verb shape, possessive relation surface, inventory relation)
# ----------------------------------------------------------------------------
VERB_STATEMENTS: tuple = (
    ("lives in", "city", "city"),
    ("works for", "employer", "employer"),
    # ("is married to" -> "spouse": base-owned via bench73; never claimed.)
    ("was born in", "place of birth", "place_of_birth"),
)

VERB_QUESTIONS: tuple = (
    ("Where does/do X live?", "Where is X's city?"),
    ("Who does/do X work for?", "Who is X's employer?"),
    # ("Who is X married to?" is NOT claimed: the one sealed hit
    # (sessions152 S1-family10 "Who is Kip married to?", Kip taught only
    # wife=Jo) would move clarify -> MISSING-spouse with want=Jo still
    # unmet -- lateral, needs wife~=spouse synonymy. Future work.)
    ("Where was X born?", "Where is X's place of birth?"),
)

# Single-token, capital-lead subject (the only shape the possessive path can
# teach for one-word names; hedges/adverbs are lowercase-led or multi-token
# and never match, so they stay on the base clarify path byte-identical).
_NAME = r"[A-Z][A-Za-z'\u2019\-]*"

_CORRECTION_LEAD = re.compile(r"^(actually\s*,|actually\s+|no\s*,|no\s+)(.+)$",
                              re.IGNORECASE | re.DOTALL)

_STMT_LIVE = re.compile(r"^(" + _NAME + r")\s+lives?\s+in\s+(.+?)\s*$",
                        re.DOTALL)
_STMT_WORK = re.compile(r"^(" + _NAME + r")\s+works?\s+for\s+(.+?)\s*$",
                        re.DOTALL)
_STMT_BORN = re.compile(r"^(" + _NAME + r")\s+was\s+born\s+in\s+(.+?)\s*$",
                        re.DOTALL)
_BORN_CITYOF = re.compile(r"^the\s+city\s+of\s+.+", re.IGNORECASE | re.DOTALL)

_ASK_LIVE = re.compile(r"^where\s+does?\s+(" + _NAME + r")\s+live\s*\??\s*$",
                       re.IGNORECASE | re.DOTALL)
_ASK_WORK = re.compile(r"^who\s+does?\s+(" + _NAME +
                       r")\s+work\s+for\s*\??\s*$",
                       re.IGNORECASE | re.DOTALL)
_ASK_BORN = re.compile(r"^where\s+was\s+(" + _NAME + r")\s+born\s*\??\s*$",
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


def parse_verb_statement(turn: str) -> dict | None:
    """Raw turn -> {twin} for the 3 claimed verb statements, else None.

    The twin is the EXACT possessive sentence the base already teaches
    ("Kwame lives in Accra." -> "Kwame's city is Accra.", correction prefix
    preserved). Married statements, negations, tense changes, hedges,
    hypotheticals, closed-class/multi-word subjects, "?"-terminated turns,
    and the bench73-owned "was born in the city of" shape all return None.
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
    for pat, rsurf in ((_STMT_LIVE, "city"),
                       (_STMT_WORK, "employer"),
                       (_STMT_BORN, "place of birth")):
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
        if pat is _STMT_BORN and _BORN_CITYOF.match(val):
            return None  # bench73's longer template owns this shape
        return {"kind": "statement", "twin": f"{corr}{name}'s {rsurf} is "
                f"{val}."}
    return None


def parse_verb_question(turn: str) -> dict | None:
    """Raw turn -> {twin} for the 4 claimed verb questions, else None.

    The twin is the EXACT possessive question the base already answers
    ("Where does Kwame live?" -> "Where is Kwame's city?"). Negated,
    qualified, or closed-class-subject questions return None.
    """
    text = _norm(turn)
    if not text:
        return None
    for pat, mk in ((_ASK_LIVE, lambda n: f"Where is {n}'s city?"),
                    (_ASK_WORK, lambda n: f"Who is {n}'s employer?"),
                    (_ASK_BORN, lambda n: f"Where is {n}'s place of "
                     "birth?")):
        m = pat.fullmatch(text)
        if m is None:
            continue
        name = m.group(1).strip()
        if not _subject_ok(name):
            return None
        return {"kind": "question", "twin": mk(name)}
    return None


def parse_verb_turn(turn: str) -> dict | None:
    """Statements first, then questions; None when the base owns the turn."""
    hit = parse_verb_statement(turn)
    if hit is not None:
        return hit
    return parse_verb_question(turn)


class Verb167Mixin:
    """Stackable mixin: verb turns become their possessive twin, rest delegates.

    Cooperative: a claimed verb turn is rewritten to its possessive twin and
    handed to super().hear() -- the base possessive path (screens, save,
    ask, mouth) runs literally, so writes/answers are the possessive form's
    own by construction. Anything unclaimed -- including every "X is married
    to Y" statement the base already teaches -- falls through untouched.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            try:
                parsed = parse_verb_turn(turn)
            except Exception:
                parsed = None
            if parsed is not None:
                return super().hear(parsed["twin"])  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
