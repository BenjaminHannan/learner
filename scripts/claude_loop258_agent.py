"""Exp 258 agent: 252b + ONE change: a trailing commentary clause ("...,
that's old news", "(that was last year)") is removed on turns that 252b
already treats as a denial or correction (scripts/claude_fix258_comment.py).

Same stack as 252b: the 228 guard installed at import and SrcGuardMixin228
first in the daemon bases; 252b's value screen installed at import;
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
import claude_loop252b_agent as L252B  # noqa: E402 (base 252b, read-only)
import claude_fix252b_screen as F252B  # noqa: E402 (read-only)
import claude_fix258_comment as F258  # noqa: E402 (THE ONE CHANGE)

F252B.install_screen252b()

DEFAULT_CONFIG258 = copy.deepcopy(L252B.DEFAULT_CONFIG252B)
DEFAULT_CONFIG258["daemon"]["module"] = (
    "Loop258Daemon (scripts/claude_loop258_agent.py): SrcGuardMixin228 > "
    "Comment258DaemonMixin > Correct252DaemonMixin > RestartIndex220Mixin > "
    "Loop138jDaemon")
DEFAULT_CONFIG258["fix258"] = (
    "Comment258EarsMixin outermost on the inner ears: trailing commentary "
    "clause removed on 252b denial/correction turns "
    "(scripts/claude_fix258_comment.py)")


def build_agent258(cfg=None):
    loop = L252B.build_agent252b(cfg)
    F258.install_comment258(loop)
    return loop


class Comment258DaemonMixin:
    """Installs the 258 mixin after 252's mixins are on the agent."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        F258.install_comment258(self.loop)


class Loop258Daemon(SrcGuardMixin228, Comment258DaemonMixin,
                    L252.Correct252DaemonMixin, L138K.RestartIndex220Mixin,
                    L138J.Loop138jDaemon):
    """Loop252bDaemon shape + the 258 comment-clause mixin."""


if __name__ == "__main__":
    sys.exit(L138K.main())
