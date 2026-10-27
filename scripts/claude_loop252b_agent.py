"""Exp 252b agent: 252 (base 138k + corrections) + ONE change: the value
screen tokenises on non-letter characters (scripts/claude_fix252b_screen.py).

Same stack as 252: the 228 guard installed at import and SrcGuardMixin228
first in the daemon bases; RestartIndex220Mixin as in 138k. No existing file
is edited.
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
import claude_fix252b_screen as F252B  # noqa: E402 (THE ONE CHANGE)

F252B.install_screen252b()

DEFAULT_CONFIG252B = copy.deepcopy(L252.DEFAULT_CONFIG252)
DEFAULT_CONFIG252B["daemon"]["module"] = (
    "Loop252bDaemon (scripts/claude_loop252b_agent.py): SrcGuardMixin228 > "
    "Correct252DaemonMixin > RestartIndex220Mixin > Loop138jDaemon")
DEFAULT_CONFIG252B["fix252b"] = (
    "value_ok252 stopword check on non-letter-split pieces "
    "(scripts/claude_fix252b_screen.py)")


def build_agent252b(cfg=None):
    F252B.install_screen252b()
    return L252.build_agent252(cfg)


class Loop252bDaemon(SrcGuardMixin228, L252.Correct252DaemonMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop252Daemon shape; the 252b screen is installed at import."""


if __name__ == "__main__":
    sys.exit(L138K.main())
