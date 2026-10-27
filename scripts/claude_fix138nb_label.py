#!/usr/bin/env python3
"""Exp 138nb -- THE ONE CHANGE: label 190's backwards answers.

138n's M7 diagnosis (design/v3/30-modes/138nb-inverse-diagnosis.md): the
190 reverse layer (fable_fix190_reverse.Reverse190Mixin, stage
"loop190-reverse") answers backwards shapes ("Whose R is V?", "Who has V
as their R?", "Who lives in V?", "Who was born in V?") with correct
forward-style sentences ("S's R is V.") but no "(worked out backwards)"
label, which the table stage (221/237) always adds. One outermost
reply-text rule: when the answering stage is exactly "loop190-reverse"
and the reply names at least one subject, append " (worked out
backwards)" (LABEL221 text, one space before it).

Nothing else changes: no new shapes, no ownership change, no writes
(reply text only; the notebook, records and logs pass through
untouched). 190's abstains ("I don't know anyone whose R is V.", "I
don't know anyone called V.") stay byte-identical, as does every reply
from any other stage. An already-labelled reply is never relabelled.

New file only; every other module is imported read-only.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix221_tableask as T221  # noqa: E402 (LABEL221, read-only)

STAGE138NB = "loop190-reverse"
LABEL138NB = T221.LABEL221  # "(worked out backwards)"
_ABSTAIN138NB = "I don't know anyone"


def names_subject138nb(reply: str) -> bool:
    """True iff the reply is a 190 subject sentence (not an abstain).

    190's subject answers are forward-style sentences ("S's R is V.",
    possibly several joined by spaces, or "Your R is V." for the user).
    190's abstains all start with "I don't know anyone". Anything else
    (including an already-labelled reply) is left alone.
    """
    r = " ".join(str(reply).split())
    if not r:
        return False
    if r.startswith(_ABSTAIN138NB):
        return False
    if LABEL138NB in r:
        return False
    if r.startswith("Your ") and " is " in r:
        return True
    return "'s " in r and " is " in r


def stage_of138nb(loop) -> str:
    """The turn's answering stage: the inner ears' last_stage tag."""
    inner = getattr(loop, "_inner138j_ears", None)
    st = getattr(inner, "last_stage", "") if inner is not None else ""
    if not st:
        st = getattr(getattr(loop, "ears", None), "last_stage", "") or ""
    return str(st)


def label_reply138nb(reply: str, stage: str) -> str:
    """Pure rule: append the label only on subject answers of stage 190."""
    if stage == STAGE138NB and names_subject138nb(reply):
        return f"{reply} {LABEL138NB}"
    return reply


class Label138nbMixin:
    """Outermost loop layer: 190-subject replies gain the label. Text only."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        out = super().turn(text)  # type: ignore[misc]
        if not isinstance(out, list) or not out:
            return out
        try:
            stage = stage_of138nb(self)
        except Exception:  # noqa: BLE001 -- never break the base reply
            return out
        if stage != STAGE138NB:
            return out
        last = out[-1]
        if not isinstance(last, str):
            return out
        new = label_reply138nb(last, stage)
        if new is last or new == last:
            return out
        return [*out[:-1], new]
