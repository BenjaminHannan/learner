"""Exp 251 agent: base228 (138i + 228 guard) + ONE change: verb direction.

The one change is scripts/claude_fix251_direction.py (Direction251Mixin),
installed outermost on the built loop's inner ears. It claims only
"Who/Whom does X <verb>?", "Who is <verb>ed by X?" and "What does X own?"
for the ten verbs in VERB251, answers from facts whose VALUE is X
("(worked out backwards)", never stored) or declines, and never reads X's
own forward value. Everything else is base228 verbatim. No existing file is
edited. The 228 guard is installed at import and SrcGuardMixin228 is first in
the daemon bases (as scripts/claude_loop228_agent.py).
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

import claude_loop228_agent as L228  # noqa: E402 (base, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import claude_fix251_direction as F251  # noqa: E402 (THE ONE CHANGE)

DEFAULT_CONFIG251 = copy.deepcopy(L228.DEFAULT_CONFIG228)
DEFAULT_CONFIG251["ears"]["stand_in"] = (
    str(DEFAULT_CONFIG251["ears"].get("stand_in", ""))
    + " + fix251 verb-direction mixin outermost")


def build_agent251(cfg):
    loop = L228.build_agent228(cfg)
    F251.install_direction251(loop)
    return loop


class Loop251Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop228Daemon shape + the 251 direction mixin on the inner ears."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        install_srcguard228()
        F251.install_direction251(self.loop)


if __name__ == "__main__":
    sys.exit(L138I.main())
