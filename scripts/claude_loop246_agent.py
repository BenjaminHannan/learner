#!/usr/bin/env python3
"""Exp 246 agent: base 228 (138i + 228 src guard) + ONE change.

The one change (scripts/claude_fix246_mentionwalk.py): a mention-guided
walk fallback over Loop138Ears._hear_question, used only when
B92.compose_n_hop returns None and the unchanged base misses the question.

Built exactly like build_agent228 (= build_agent138i), then the inner ears
object (the Loop138iEars instance the sleep wrap delegates to, found via
.inner) is re-classed to Loop246Ears = MentionWalk246Mixin over
Loop138iEars. No existing file is edited.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop246_agent.py --daemon --dir DIR \\
    --config artifacts/claude-mentionwalk246-20260922/loop246-config.json
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138i_agent as L138I  # noqa: E402 (base agent, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (228 guard, required)
    SrcGuardMixin228, install_srcguard228)
from claude_fix246_mentionwalk import MentionWalk246Mixin  # noqa: E402

install_srcguard228()

DEFAULT_CONFIG246 = copy.deepcopy(L138I.DEFAULT_CONFIG138I)


class Loop246Ears(MentionWalk246Mixin, L138I.Loop138iEars):
    """Loop138iEars + the 246 mention-walk fallback (innermost override of
    _hear_question; every outer 138i stage unchanged)."""

    name = "loop246-mentionwalk"


_ORIG_BUILD138I = L138I.build_agent138i


def build_agent246(cfg=None):
    install_srcguard228()
    loop = _ORIG_BUILD138I(cfg)
    inner = loop.ears
    for _ in range(8):  # unwrap the sleep delegate(s) to the 138i ears
        if type(inner) is L138I.Loop138iEars:
            break
        inner = getattr(inner, "inner", None)
    if type(inner) is not L138I.Loop138iEars:
        raise RuntimeError("138i inner ears not found")
    inner.__class__ = Loop246Ears
    loop.notes.append("loop246: 228 + fix246 mention-walk fallback")
    return loop


class Loop246Daemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon with the 228 guard and the 246 ears (the 138i daemon
    calls the module-level build_agent138i; it is pointed at
    build_agent246 only while this daemon is being built)."""

    def __init__(self, *args, **kwargs):
        L138I.build_agent138i = build_agent246
        try:
            super().__init__(*args, **kwargs)
        finally:
            L138I.build_agent138i = _ORIG_BUILD138I


def main(argv=None) -> int:
    L138I.build_agent138i = build_agent246
    try:
        return L138I.main(argv)
    finally:
        L138I.build_agent138i = _ORIG_BUILD138I


if __name__ == "__main__":
    sys.exit(main())
