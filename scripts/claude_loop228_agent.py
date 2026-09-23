"""Exp 228 agent: base 138i + the fix170 _src_of identity guard (one change).

Everything is 138i (scripts/fable_loop138i_agent.py) except that
scripts/claude_fix228_srcguard.py rebinds fable_fix170_compose._src_of so a
recycled list address can no longer point the fast index at an older
notebook. Installed at import (like install_index170) and again, idempotently,
by the daemon mixin.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (base agent, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (THE ONE CHANGE)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

DEFAULT_CONFIG228 = copy.deepcopy(L138I.DEFAULT_CONFIG138I)


def build_agent228(cfg):
    install_srcguard228()
    return L138I.build_agent138i(cfg)


class Loop228Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon with the 228 guard guaranteed installed."""


if __name__ == "__main__":
    sys.exit(L138I.main())
