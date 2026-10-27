#!/usr/bin/env python3
"""Exp 248 agent: base 228 (138i + 228 guard) + ONE change: read "whats".

The one change is scripts/claude_fix248_whats.py (Whats248Mixin), stacked
OUTERMOST on the 138i ears (above ChainOf174), so ChainOf174, Typo165,
Me166 and FakeEars all see "whats X's city?" as "what is X's city?".

Mechanism: build_agent138i constructs its ears from the module global
L138I.Loop138iEars. During each build (and only then) that global is
rebound to Loop248Ears(Whats248Mixin, Loop138iEars) and restored right
after, so a base-228 agent built in the same process is unaffected. No
existing file is edited.
"""
from __future__ import annotations

import contextlib
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (base agent, read-only)
import claude_loop228_agent as L228  # noqa: E402 (base 228, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)
from claude_fix248_whats import Whats248Mixin  # noqa: E402 (THE ONE CHANGE)

install_srcguard228()

_BASE_EARS138I = L138I.Loop138iEars


class Loop248Ears(Whats248Mixin, _BASE_EARS138I):
    """Loop138iEars with the 248 "whats" reader outermost."""

    name = "loop248-whats-over-138i"


@contextlib.contextmanager
def _ears248():
    saved = L138I.Loop138iEars
    L138I.Loop138iEars = Loop248Ears
    try:
        yield
    finally:
        L138I.Loop138iEars = saved


DEFAULT_CONFIG248 = copy.deepcopy(L228.DEFAULT_CONFIG228)
try:
    DEFAULT_CONFIG248["ears"]["stand_in"] = (
        str(DEFAULT_CONFIG248["ears"].get("stand_in", "")) +
        "; 248 whats/whos/wheres reader outermost "
        "(scripts/claude_fix248_whats.py)")
except Exception:
    pass


def build_agent248(cfg=None):
    install_srcguard228()
    with _ears248():
        loop = L138I.build_agent138i(cfg)
    loop.notes.append("loop248: Whats248Mixin outermost on the 138i ears")
    return loop


class Loop248Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon (guard first) whose agent carries the 248 ears."""

    def __init__(self, *args, **kwargs) -> None:
        install_srcguard228()
        with _ears248():
            super().__init__(*args, **kwargs)
        self.loop.notes.append("loop248: Whats248Mixin outermost on the "
                               "138i ears")


def main(argv=None) -> int:
    with _ears248():
        return L138I.main(argv)


if __name__ == "__main__":
    sys.exit(main())
