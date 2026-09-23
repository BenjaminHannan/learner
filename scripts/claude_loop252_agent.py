"""Exp 252 agent: base 138k + ONE change: corrections and denials.

The one change is scripts/claude_fix252_correct.py: Correct252EarsMixin
outermost on the built loop's inner ears and Correct252LoopMixin on the
loop (previous-reply memory + the negate252 action, which runs through
154f's own retraction path). Everything else is 138k verbatim
(scripts/claude_loop138k_agent.py, read-only): the 228 guard is installed
at import and SrcGuardMixin228 is first in the daemon bases; the 220
restart index comes in through RestartIndex220Mixin exactly as in 138k.
No existing file is edited.
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
import claude_fix252_correct as F252  # noqa: E402 (THE ONE CHANGE)

DEFAULT_CONFIG252 = copy.deepcopy(L138K.DEFAULT_CONFIG138K)
DEFAULT_CONFIG252["daemon"]["module"] = (
    "Loop252Daemon (scripts/claude_loop252_agent.py): SrcGuardMixin228 > "
    "Correct252DaemonMixin > RestartIndex220Mixin > Loop138jDaemon")
DEFAULT_CONFIG252["fix252"] = (
    "Correct252EarsMixin outermost on the inner ears + Correct252LoopMixin "
    "on the loop (scripts/claude_fix252_correct.py)")


def build_agent252(cfg=None):
    loop = L138K.build_agent138k(cfg)
    F252.install_correct252(loop)
    return loop


class Correct252DaemonMixin:
    """Installs the 252 mixins on the agent the base daemon built."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        F252.install_correct252(self.loop)


class Loop252Daemon(SrcGuardMixin228, Correct252DaemonMixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon shape + the 252 correction mixins."""


if __name__ == "__main__":
    sys.exit(L138K.main())
