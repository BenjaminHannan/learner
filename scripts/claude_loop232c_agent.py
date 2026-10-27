#!/usr/bin/env python3
"""Exp 232c: 232 + complete name-particle handling (one change).

232 (scripts/claude_loop232_agent.py, sealed) lets verb turns take a 2-4
token proper-name subject whose middle tokens may be lower-case particles
from a 21-word list. 232b's blind panel showed the list was incomplete
("ben" names fell through to 138i). 232c changes ONLY the subject rule:

  * PARTICLES232C: the complete lower-case list de da di do dos das del
    della delle degli van von der den ter ten te le la les du des ben bin
    ibn bat bint al el abu ap mac y zu. Particles may appear only between
    name words; runs of particles ("de la", "van der", "von der") are fine.
  * A subject is 2-4 tokens in all (the 137 possessive parser's own limit,
    so a longer subject could never be stored): at least 2 capitalised name
    words (137 name tokens: O'X, D'X, X-Y, initials) plus any middle
    particles (at most 2 in a row). "Juan de la Cruz" fits; "Tomas de la
    Vega Ruiz" (5 tokens) is a known limit and falls through to 138i.
  * The subject must also pass the 150b clause-in-subject screen
    (screen_subject_150b -> "store"), which the stack applies to every teach
    anyway. Of the 34 particles only "do" fails it (read as a verb), so
    "X do Y" names are not claimed and get 138i's reply instead of 232's
    misleading split reply; the guard itself is not changed (known limit).
  * Conjunctions never join a name: and / or / & / with / plus / nor (and
    232's closed non-name words) anywhere in the subject -> not claimed.

Everything else (the five verbs, question shapes, 150/150c guards, value
screen, surrogate re-run, refusal mirror, doubt record, pending drop, the
228 guard) is 232's code, unchanged. Mechanism: at import, 232's module
globals PARTICLES232 / subject_ok232 are rebound to the 232c versions (232's
parse and upgrade functions read them at call time). 232's file is not
edited; the rebinding only exists in a process that imports this module.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop232_agent as L232  # noqa: E402 (sealed 232, read-only)
import fable_fix150b_subject150b as S150B  # noqa: E402 (read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 flake guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

MAX_NAME_WORDS232C = 4
MAX_TOKENS232C = 4
MAX_PARTICLE_RUN232C = 2  # "de la", "van der", "von der"; never 3+ in a row
PARTICLES232C = frozenset({
    "de", "da", "di", "do", "dos", "das", "del", "della", "delle", "degli",
    "van", "von", "der", "den", "ter", "ten", "te", "le", "la", "les", "du",
    "des", "ben", "bin", "ibn", "bat", "bint", "al", "el", "abu", "ap", "mac",
    "y", "zu",
})
CONJUNCTIONS232C = frozenset({"and", "or", "&", "with", "plus", "nor",
                              "&amp;", "n'", "'n'"})
NONNAME232C = L232.NONNAME232 | CONJUNCTIONS232C


def subject_ok232c(subject: str) -> bool:
    """True for a proper name of 2-4 name words (+ middle particles)."""
    text = L232._norm(subject)
    toks = text.split()
    if not 2 <= len(toks) <= MAX_TOKENS232C:
        return False
    name_words = 0
    run = 0
    for i, tok in enumerate(toks):
        if L232._possessive_token(tok):
            return False
        low = tok.lower().strip(".,")
        if low in L232.OPENER_WORDS232 or low in NONNAME232C:
            return False
        if L232.F137.is_name137_token(tok) and \
                tok == tok.strip(",;:\"()"):
            name_words += 1
            run = 0
            continue
        if 0 < i < len(toks) - 1 and tok in PARTICLES232C:
            run += 1
            if run > MAX_PARTICLE_RUN232C:
                return False
            continue
        return False
    if not 2 <= name_words <= MAX_NAME_WORDS232C:
        return False
    lows = [t.lower() for t in toks]
    for phrase in L232.OPENER_PHRASES232:
        n = len(phrase)
        for i in range(len(lows) - n + 1):
            if tuple(lows[i:i + n]) == phrase:
                return False
    try:
        if L232.C150.is_closed_class_subject(text):
            return False
        verdict, clean = L232.S150.screen_subject_150(text)
        verdict_b, clean_b = S150B.screen_subject_150b(text)
    except Exception:
        return False
    return verdict == "store" and clean == text and \
        verdict_b == "store" and clean_b == text


def install232c() -> None:
    """Rebind 232's subject-rule globals (idempotent)."""
    L232.PARTICLES232 = PARTICLES232C
    L232.subject_ok232 = subject_ok232c


install232c()

DEFAULT_CONFIG232C = copy.deepcopy(L232.DEFAULT_CONFIG232)
try:
    DEFAULT_CONFIG232C["ears"]["stand_in"] = (
        str(DEFAULT_CONFIG232C["ears"].get("stand_in", "")) +
        "; 232c complete name particles (scripts/claude_loop232c_agent.py)")
except Exception:
    pass


def build_agent232c(cfg: dict | None = None):
    install_srcguard228()
    install232c()
    loop = L232.build_agent232(cfg)
    loop.notes.append("loop232c: complete name particles + conjunction "
                      "screen on the 232 verb subject rule")
    return loop


class Loop232cDaemon(SrcGuardMixin228, L232.L138I.Loop138iDaemon):
    """232's daemon shape (guard first in bases, 138i daemon below it)."""

    def __init__(self, *args, **kwargs) -> None:
        install232c()
        # 232's daemon __init__ body (sets dirs, builds the 232 agent through
        # L232.build_agent232, which now reads the 232c subject rule).
        L232.Loop232Daemon.__init__(self, *args, **kwargs)
        self.loop.notes.append("loop232c: complete name particles + "
                               "conjunction screen on the 232 subject rule")


def main(argv=None) -> int:
    install232c()
    return L232.main(argv)


if __name__ == "__main__":
    sys.exit(main())
