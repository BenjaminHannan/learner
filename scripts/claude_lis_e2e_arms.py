#!/usr/bin/env python3
"""Listener-stack arms for the month-end end-to-end harness (scripts/claude_e2e336_run.py).

  --arm claude_lis_e2e_arms:build_C   292t + lis-310 (all-or-nothing, ask-back)
  --arm claude_lis_e2e_arms:build_S   292t + 310 + 313 + 315 + 314
  --arm claude_lis_e2e_arms:build_G   292t + 310 + 313 + 315 + 314 + 316 (the full stack)
Reader = --model (lis-301 merged), T = 0.995. The reader is loaded once per process and reused
across lives and restarts. lis-314's pending store lives in the state dir, so it survives the
harness's kill + restart between days.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

THRESHOLD = 0.995
_READER = {}


def _reader(model):
    if model not in _READER:
        import claude_lis300_read as READ
        _READER[model] = READ.Reader(model)
    return _READER[model]


def _build(state_dir, args, layers):
    import claude_loop292t_agent as T292
    import claude_lis_stack as STACK
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    STACK.build_stack(loop, _reader(args.model), THRESHOLD, layers=layers, log_dir=state_dir)
    return loop


def build_C(state_dir, args):
    return _build(state_dir, args, ())


def build_S(state_dir, args):
    return _build(state_dir, args, ("313", "315", "314"))


def build_G(state_dir, args):
    return _build(state_dir, args, ("313", "315", "314", "316"))
