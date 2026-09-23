#!/usr/bin/env python3
"""Experiment 227 -- QUESTIONS ABOUT THE ASSISTANT GET AN ANSWER ABOUT THE
ASSISTANT (one change on loop138i, Muse).

Director-verified problem (14:46 on loop138i, fresh notebook): "What is your
name?" and "Who made you?" both get "You never told me your name, so I do
not know it." -- the reply of the user-name intent D8 (scripts/fable_self105.py
intent table; hard-coded reply scripts/fable_self99.py:590-591). That is a
wrong answer: the question is about the assistant, not the user.

Step 0 census (before any code): 45 identity questions run on loop138i fresh
notebook (scripts/fable_identity227_census.py; rows in
artifacts/fable-identity227-20260922/census138i-rows.json). Result:
  - NAME-about-assistant ("What is your name?", "What are you called?",
    "What is your name called?", "What should I call you?", "Have you got
    a name?") -> D8 user-name denial (WRONG: about the assistant).
    "Do you have a name?" -> DECLINE (unrelated).
  - MAKER ("Who made you?", "Who created you?") -> D8 denial (WRONG).
    ("Who built/invented/designed you?", "Who is your maker/creator?")
    -> DECLINE (unrelated).
  - WHAT / LEARN ("What are you?", "Are you a ...?", "How do you ...?") ->
    all DECLINE (unrelated; no answer about the assistant).
  - AGE: "How old are you?" -> DECLINE (unrelated); "What is your age?" and
    "What is your birthday?" -> D9 (Mira's-age reply; WRONG subject).
  - HOME ("Where do you live?", ...) -> all DECLINE (unrelated).
  - User-about questions keep working: "What is my name?" / "Do you know my
    name?" hit the notebook namecheck when a name is taught; "Do you
    remember my name?" routes D8 (exp 219's piece, not this one).
Every census turn wrote 0 facts. AGE and HOME sheets are included because
the census shows wrong/unrelated replies for them.

THE ONE CHANGE: a small fixed identity sheet (this file, plain software,
like the capability sheet) with one honest answer per identity intent.
Routing: a "?" turn goes to the identity sheet only when it contains a
second-person word (you, your, yours, yourself) AND its normalised form
exactly equals an identity template listed in the sealed data file
scripts/fable_identity227_templates.json (exact normalised templates, not
keywords). Questions with a first-person word about the user ("What is my
name?", "Do you remember my name?", "Do you know my name?") are not in the
template list, so they keep today's route exactly (exp 219 fixes those).
The intercept sits INSIDE the notebook-miss branch of turn(), so notebook
answers always win; it never writes to the notebook (reply-only).

No existing file is edited; scripts/fable_loop227_agent.py subclasses
loop138i and swaps in identity_answer() at that one point.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TEMPLATES_PATH = SCRIPTS / "fable_identity227_templates.json"

# One honest answer per identity intent. Each is literally true of this
# program: it has no name; Ben built it; it keeps taught facts in a
# notebook file and answers from it, declining instead of guessing; it
# learns from plain taught sentences; it has no age; it lives nowhere.
SHEET: dict[str, str] = {
    "NAME": "I don't have a name yet.",
    "MAKER": "Ben built me.",
    "WHAT": ("I'm a small program that keeps what you teach me in a "
             "notebook and answers from it. When I don't know something, "
             "I say so instead of guessing."),
    "LEARN": ('I learn when you tell me facts in plain sentences, like '
              '"Kim lives in Oslo." I save each one and answer from my notes.'),
    "AGE": ("I don't have an age. I'm a program, so I don't measure "
            "my life in years."),
    "HOME": ("I don't live anywhere. I'm a program that runs on a computer "
             "and keeps a notebook file."),
}

SECOND_PERSON = {"you", "your", "yours", "yourself"}


def normalise(turn: str) -> str:
    """Lowercase + collapse whitespace (trailing '?' kept)."""
    return " ".join(str(turn).split()).lower()


def _load_templates() -> dict[str, str]:
    """normalised template -> intent (sealed data file)."""
    raw = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for intent, forms in raw["templates"].items():
        for form in forms:
            out[normalise(form)] = intent
    return out


_TEMPLATES: dict[str, str] | None = None


def templates() -> dict[str, str]:
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = _load_templates()
    return _TEMPLATES


def identity_intent(turn: str) -> str | None:
    """Intent id iff this '?' turn belongs to the identity sheet, else None.

    All three conditions required: ends with '?', contains a second-person
    word, exact normalised template match. Pure function, no writes.
    """
    text = normalise(turn)
    if not text.endswith("?"):
        return None
    toks = set(re.findall(r"[a-z]+", text))
    if not (toks & SECOND_PERSON):
        return None
    return templates().get(text)


def identity_answer(turn: str) -> tuple[str, str] | None:
    """(intent, sheet answer) for identity turns, else None. No writes."""
    intent = identity_intent(turn)
    if intent is None:
        return None
    return intent, SHEET[intent]
