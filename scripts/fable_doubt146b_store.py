#!/usr/bin/env python3
"""Experiment 146b -- THE ONE CHANGE vs exp 146: hearsay/reported-speech
refusals never create a doubt.

Exp 146 (scripts/fable_doubt146_store.py, read-only here) records a doubt
whenever a refused teach names a known subject with a relation cue --
including F1-hearsay clarifies ("The capital of Poland is Krakow, Tom
said."). The follow-up question then abstains instead of answering the
standing taught fact, so a third party's quoted claim vetoes what the
owner taught (146 D4: p2 A2/A6/A8, rt110 T4). Project rules forbid that:
hearsay must never change what the agent says about taught facts.

THE ONE CHANGE (this file only; 146 imported read-only, no existing file
edited): a turn is hearsay-exempt when

  1. the loop's own F1 classifier fires (L102.is_hearsay), or
  2. the parsed teach subject is hearsay-shaped
     (L102.subject_is_hearsay_shaped), or
  3. the turn carries reported-speech / quoted-content markers
     (leading "Ann said ...", "X says ...", "someone told me ...",
     "I heard ...", "apparently ...", "according to ...", quotation
     marks) -- i.e. any message the loop classifies, or would classify,
     as reported speech or quoted content.

An exempt turn NEVER records a doubt, at ears-hear or loop-_act level.
Only first-person refused teaches/corrections record. Everything else is
identical to 146: same parsers, same doubt reply, same walk screening
(including screening questions asked AFTER an exempt turn against older
first-person doubts), same clearing rule (successful teach only --
hearsay neither records nor clears), same notebook-side store file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_doubt146_store as D146  # noqa: E402 (exp-146 rule, read-only)
import fable_loop102_agent as L102  # noqa: E402 (F1 classifier, read-only)

# Reported-speech / quoted-content markers beyond the loop's own F1 list
# (which covers trailing ", X said.", "according to", "I read online /
# that", "I heard", "apparently", "reportedly", leading "quote", "the web
# says"). These cover leading attribution and quotations: "Ann said
# Tom's boss is Bob", "someone told me ...", "my brother says ...".
# Deliberately narrow: bare first-person teaches ("Tom's boss is Bob.",
# "Actually, ...", "No, ...") contain none of these tokens.
_REPORTED_RES146B = [
    re.compile(r"\bsaid\b", re.IGNORECASE),
    re.compile(r"\bsays\b", re.IGNORECASE),
    re.compile(r"\btold\b", re.IGNORECASE),
    re.compile(r"\bheard\b", re.IGNORECASE),
    re.compile(r"\bhearsay\b", re.IGNORECASE),
    re.compile(r"\bapparently\b", re.IGNORECASE),
    re.compile(r"\breportedly\b", re.IGNORECASE),
    re.compile(r"\baccording\s+to\b", re.IGNORECASE),
    re.compile(r"\bquote\b", re.IGNORECASE),
    re.compile(r'"'),
]


def is_reported_speech146b(text: str) -> bool:
    """True when the text carries reported-speech/quoted-content markers."""
    return any(rx.search(str(text)) for rx in _REPORTED_RES146B)


def is_hearsay_exempt146b(turn: str) -> bool:
    """True when a turn must never create a doubt (pure function).

    Mirrors the loop's own classification: its F1 regexes, its
    lowercase-subject guard (via the 146 teach parse), plus
    reported-speech / quoted-content markers.
    """
    text = " ".join(str(turn).split())
    if not text:
        return False
    if L102.is_hearsay(text):
        return True
    try:
        triple = D146.detect_teach146(turn)
    except Exception:
        triple = None
    if triple is not None:
        try:
            if L102.subject_is_hearsay_shaped(triple[0]):
                return True
        except Exception:
            pass
    return is_reported_speech146b(text)


class Doubt146bMixin(D146.Doubt146Mixin):
    """Exp-146 doubt mixin + the hearsay exemption (THE ONE CHANGE).

    Cooperative stacking, same order as 146 (outermost). The exemption is
    enforced by suppressing _record_doubt for exempt turns; the rest of
    the 146 hear/_act/_ask logic runs byte-identical via super().
    """

    def _record_doubt(self, subject: str, relation: str,
                      turn: str = "") -> None:
        if getattr(self, "_no_record146b", False):
            return
        if turn and is_hearsay_exempt146b(turn):
            return
        super()._record_doubt(subject, relation, turn)

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        if is_hearsay_exempt146b(turn):
            self._no_record146b = True  # type: ignore[attr-defined]
            try:
                return super().hear(turn)
            finally:
                self._no_record146b = False  # type: ignore[attr-defined]
        return super().hear(turn)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if (isinstance(action, dict)
                and action.get("act") in D146.TEACH_ACTS):
            blob = (str(action.get("name", ""))
                    + " " + str(action.get("value", "")))
            if is_reported_speech146b(blob) or L102.is_hearsay(blob):
                self._no_record146b = True  # type: ignore[attr-defined]
                try:
                    return super()._act(action)
                finally:
                    self._no_record146b = False  # type: ignore[attr-defined]
        return super()._act(action)
