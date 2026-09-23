#!/usr/bin/env python3
"""Experiment 219 -- "YOU NEVER TOLD ME" REPLIES MUST BE TRUE (Muse).

ONE CHANGE on loop138i (director-verified problem 14:25 on loop138i):
after "My name is Juno." the notebook holds (USER, name, Juno) and
"What is my name?" answers "Your name is Juno.", but "Do you remember
my name?" is routed to the self intent D8 and served the hard-coded
"You never told me your name, so I do not know it."
(scripts/fable_self99.py:590-591, passed through unchanged by the
grounding layer scripts/fable_fix168_ground.py, which lists D8 as
"plain"). That is a FALSE statement about memory.

THE ONE CHANGE: every self reply that claims the user never told or
taught something is checked against the notebook before it is sent.
Concretely this file wraps the loop138i self path
(fable_fix168_ground.grounded_self_answer, read-only, never edited):
when the grounded base reply is exactly the D8 canned denial and the
notebook currently holds the USER entity's taught name, the reply is
replaced by "Yes. Your name is <value>." with <value> read from the
notebook (N173.current_name: the stored literal, the same value the
normal question path renders). When the notebook holds no name, the
reply stays byte-identical. Replies whose claim the notebook cannot
contradict stay byte-identical. Nothing here writes to the notebook;
it is a reply-only gate.

CENSUS of "never told/taught" replies (see census() below):
  D8 my-name  "You never told me your name, so I do not know it."
      -> notebook CAN contradict (USER/name fact). GROUNDED HERE.
  D9 age      "You never taught me Mira's age, so I do not know it."
      -> notebook CAN contradict; ALREADY grounded by fix168
         (ground_reply D9 arm: states the stored age, else stripped
         "their age" form). Passed through unchanged here.
  D5 why      "You never told me why. I only store what you state,
       not reasons." -> notebook CANNOT contradict (reasons are never
       stored). Byte-identical always.
  D6 Tom      "Tom has never spoken to me. ..." -> handled by fix168
       (entity-known check). Passed through unchanged here.
  C22 unsure  "... (never taught)" parenthetical -> lists only records
       already MISSING_FACT, so it cannot deny a held fact.
       Byte-identical always.
  Fallback / DECLINE markers ("never taught me") -> no fact claim
       about held state. Byte-identical always.

No existing file is edited; the agent file scripts/fable_loop219_agent.py
calls grounded219_self_answer() in place of the 168 call inside an
otherwise verbatim copy of the 138g/138h turn body.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix168_ground as G168  # noqa: E402 (base gate, read-only)
import fable_fix173_username as N173  # noqa: E402 (USER name, read-only)
import fable_self99 as S99  # noqa: E402 (exact base string, read-only)

# Exact D8 canned denial (scripts/fable_self99.py:590-591).
MYNAME_BASE = "You never told me your name, so I do not know it."


def census() -> list[dict]:
    """Every 'never told/taught' reply + whether the notebook can deny it."""
    return [
        {"id": "D8", "where": "fable_self99.answer_self my-name",
         "text": MYNAME_BASE,
         "notebook_can_contradict": True,
         "handling": "grounded HERE (fix219): stored USER name wins"},
        {"id": "D9", "where": "fable_self99.answer_self how-old + "
                              "fable_fix168_ground AGE_BASE/AGE_STRIPPED",
         "text": "You never taught me Mira's age, so I do not know it.",
         "notebook_can_contradict": True,
         "handling": "already grounded by fix168; passthrough here"},
        {"id": "D5", "where": "fable_self99.answer_self why",
         "text": "You never told me why. I only store what you state, "
                 "not reasons.",
         "notebook_can_contradict": False,
         "handling": "byte-identical always (reasons never stored)"},
        {"id": "D6", "where": "fable_self99.answer_self did-Tom-tell + "
                              "fable_fix168_ground TOM_PREFIX arm",
         "text": "Tom has never spoken to me. All ... turns are yours.",
         "notebook_can_contradict": True,
         "handling": "already handled by fix168; passthrough here"},
        {"id": "C22", "where": "fable_self99.answer_self unsure-about",
         "text": "... (never taught)",
         "notebook_can_contradict": False,
         "handling": "byte-identical always (only lists MISSING_FACTs)"},
    ]


def stored_user_name(nb) -> str | None:
    """The USER entity's taught name, or None when the notebook holds none."""
    try:
        return N173.current_name(nb)
    except Exception:
        return None


def ground219_reply(nb, intent: str, base: str) -> str:
    """Apply the 219 check to one grounded self reply (pure, no writes).

    If the reply is exactly the D8 denial and the notebook holds the
    USER name, answer from the notebook. Everything else byte-identical.
    """
    if base == MYNAME_BASE:
        name = stored_user_name(nb)
        if name:
            return "Yes. Your name is %s." % name
    return base


def grounded219_self_answer(loop, text: str, intent: str) -> str:
    """loop138i's grounded_self_answer + the 219 notebook check.

    Calls the untouched 168 gate, then ground219_reply. No notebook
    writes; reply-only.
    """
    base = G168.grounded_self_answer(loop, text, intent)
    try:
        nb = loop.nb
    except AttributeError:
        return base
    return ground219_reply(nb, intent, base)
