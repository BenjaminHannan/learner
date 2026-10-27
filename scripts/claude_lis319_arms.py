#!/usr/bin/env python3
"""Join the lis-319 history reader into the 330a agent (for Month-end's 0.2 builds).

The 330a stack calls reader.read(turn, prev_reply) once per user turn (claude_lis_stackb.MemoReader). HistReader319 keeps
the conversation itself: before each read it records prev_reply as the answer to the previous user turn, passes the last
6 (user turn, assistant reply) pairs as history, then remembers the new turn. One HistReader319 per built agent (per life),
so history never crosses lives. The Reader319 weights are cached per model path and reached only through closures.

  --arm claude_lis319_arms:build_330a_334_r319    330a_334 with the lis-319 reader at 0.995 (lis-319: REGISTERED PASS)
  --arm claude_lis319_arms:build_330a_334_r319c   same at 0.98 (only if lis-319c passes)
  --model = the lis-319 merged reader (sha256 e688e1b2...6a76; BensPC C:/Users/benja/lis319/work/run/merged,
            Mac ~/premonition-models/lis319-merged)
Needs: scripts/claude_lis319_read.py, claude_lis319_common.py (and what they import from lis-300).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_R319 = {}
HIST_PAIRS = 6


def _reader319(model):
    if model not in _R319:
        import claude_lis319_read as R
        _R319[model] = R.Reader319(model)
    return _R319[model]


class HistReader319:
    def __init__(self, reader):
        pairs = []

        def _read(turn, prev_reply=""):
            if pairs:
                pairs[-1] = (pairs[-1][0], prev_reply or "")
            out = reader.read(turn, prev_reply, pairs[-HIST_PAIRS:])
            pairs.append((turn, ""))
            return out

        def _reset():
            pairs.clear()

        self._read, self.reset = _read, _reset

    def read(self, turn, prev_reply=""):
        return self._read(turn, prev_reply)


def _build(state_dir, args, threshold):
    import claude_e2e330_arms as A
    import claude_lis_stackb as STACK
    import claude_loop274_agent as L274
    import claude_age334_agent as A334
    loop = A._base(state_dir, args)
    STACK.build_stack(loop, HistReader319(_reader319(args.model)), threshold,
                      layers=("313", "315", "314", "316"), log_dir=state_dir)
    L274.install_turn_reply_first274(loop)
    A334.install_agenda334(loop)
    return loop


def build_330a_334_r319(state_dir, args):
    return _build(state_dir, args, 0.995)


def build_330a_334_r319c(state_dir, args):
    return _build(state_dir, args, 0.98)
