"""Exp 252c agent: 252b + 258 (clause strip, outermost) + 259 (value
boundary inside 252's explicit-denial path), with one piece of glue
(scripts/claude_fix252c_merge.py): 258's cut point counts as 259's clause
boundary on the 154f route.

Inner-ears order: Comment258 > Merge252c > Boundary259 > Correct252 > base.
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
import claude_fix252c_merge as F252C  # noqa: E402 (258 + glue + 259)

F252B.install_screen252b()

DEFAULT_CONFIG252C = copy.deepcopy(L252B.DEFAULT_CONFIG252B)
DEFAULT_CONFIG252C["daemon"]["module"] = (
    "Loop252cDaemon (scripts/claude_loop252c_agent.py): SrcGuardMixin228 > "
    "Merge252cDaemonMixin > Correct252DaemonMixin > RestartIndex220Mixin > "
    "Loop138jDaemon")
DEFAULT_CONFIG252C["fix252c"] = (
    "inner ears: Comment258 > Merge252c > Boundary259 > Correct252 "
    "(scripts/claude_fix258_comment.py, scripts/claude_fix252c_merge.py, "
    "scripts/claude_fix259_boundary.py)")


def build_agent252c(cfg=None):
    F252B.install_screen252b()
    loop = L252.build_agent252(cfg)
    F252C.install_merge252c(loop)
    return loop


class Merge252cDaemonMixin:
    """Installs 259, the 252c glue and 258 after the 252 mixins."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        F252C.install_merge252c(self.loop)


class Loop252cDaemon(SrcGuardMixin228, Merge252cDaemonMixin,
                     L252.Correct252DaemonMixin, L138K.RestartIndex220Mixin,
                     L138J.Loop138jDaemon):
    """Loop252bDaemon shape + 258 + glue + 259."""


if __name__ == "__main__":
    sys.exit(L138K.main())
