#!/usr/bin/env python3
"""Exp 245 agent: base 228 (138i + 228 guard) + ONE change: "my <relation>"
as a question subject or possessor ("What's my uncle's job?", "Where does
my sister live?").

The one change is scripts/claude_fix245_myrel.py (MyRel245Mixin), stacked
OUTERMOST on the 138i ears (above ChainOf174), so it sees the raw turn and
probes the whole unchanged 138i ears stack with the resolved person's name.

Mechanism: build_agent138i constructs its ears from the module global
L138I.Loop138iEars. During each build (and only then) that global is
rebound to Loop245Ears(MyRel245Mixin, Loop138iEars) and restored right
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
from claude_fix245_myrel import MyRel245Mixin  # noqa: E402 (THE ONE CHANGE)

install_srcguard228()

_BASE_EARS138I = L138I.Loop138iEars


class Loop245Ears(MyRel245Mixin, _BASE_EARS138I):
    """Loop138iEars with the 245 my-relation reader outermost."""

    name = "loop245-myrel-over-138i"


@contextlib.contextmanager
def _ears245():
    saved = L138I.Loop138iEars
    L138I.Loop138iEars = Loop245Ears
    try:
        yield
    finally:
        L138I.Loop138iEars = saved


DEFAULT_CONFIG245 = copy.deepcopy(L228.DEFAULT_CONFIG228)
try:
    DEFAULT_CONFIG245["ears"]["stand_in"] = (
        str(DEFAULT_CONFIG245["ears"].get("stand_in", "")) +
        "; 245 my-relation question reader outermost "
        "(scripts/claude_fix245_myrel.py)")
except Exception:
    pass


def build_agent245(cfg=None):
    install_srcguard228()
    with _ears245():
        loop = L138I.build_agent138i(cfg)
    loop.notes.append("loop245: MyRel245Mixin outermost on the 138i ears")
    return loop


class Loop245Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon (guard first) whose agent carries the 245 ears."""

    def __init__(self, *args, **kwargs) -> None:
        install_srcguard228()
        with _ears245():
            super().__init__(*args, **kwargs)
        self.loop.notes.append("loop245: MyRel245Mixin outermost on the "
                               "138i ears")


def main(argv=None) -> int:
    with _ears245():
        return L138I.main(argv)


if __name__ == "__main__":
    sys.exit(main())
