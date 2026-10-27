"""Exp 259 agent: 252b + ONE change: the denied value ends at a clause
boundary (scripts/claude_fix259_boundary.py, Boundary259EarsMixin on top of
252's Correct252EarsMixin on the inner ears).

Same stack as 252b: the 228 guard installed at import and SrcGuardMixin228
first in the daemon bases; the 252b value screen installed at import;
RestartIndex220Mixin as in 138k. No existing file is edited.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import claude_loop138k_agent as L138K  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (read-only)
import claude_loop252_agent as L252  # noqa: E402 (read-only)
import claude_loop252b_agent as L252B  # noqa: E402 (read-only; installs 252b screen)
import claude_fix252b_screen as F252B  # noqa: E402 (read-only)
import claude_fix259_boundary as F259  # noqa: E402 (THE ONE CHANGE)

F252B.install_screen252b()

DEFAULT_CONFIG259 = copy.deepcopy(L252B.DEFAULT_CONFIG252B)
DEFAULT_CONFIG259["daemon"]["module"] = (
    "Loop259Daemon (scripts/claude_loop259_agent.py): SrcGuardMixin228 > "
    "Boundary259DaemonMixin > Correct252DaemonMixin > RestartIndex220Mixin > "
    "Loop138jDaemon")
DEFAULT_CONFIG259["fix259"] = (
    "Boundary259EarsMixin on top of the 252 ears mixin: denied value ends "
    "at a clause boundary (scripts/claude_fix259_boundary.py)")


def build_agent259(cfg=None):
    F252B.install_screen252b()
    loop = L252.build_agent252(cfg)
    F259.install_boundary259(loop)
    return loop


class Boundary259DaemonMixin:
    """Installs the 259 ears mixin after the 252 mixins are installed."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        F259.install_boundary259(self.loop)


class Loop259Daemon(SrcGuardMixin228, Boundary259DaemonMixin,
                    L252.Correct252DaemonMixin, L138K.RestartIndex220Mixin,
                    L138J.Loop138jDaemon):
    """Loop252bDaemon shape + the 259 boundary mixin."""


if __name__ == "__main__":
    sys.exit(L138K.main())
