#!/usr/bin/env python3
"""330 joined-agent builders for the 336 harness (month-end line).

Layer order, inner to outer (fixed here; every piece is imported read-only):
  292t base -> install298 (multi-valued middle hop, reasoner wrapper)
  -> 274 listen-first step order -> listener stack G (310 + 313 + 315 + 314 + 316, one read per turn)
  -> 274 reply-first turn (sleep never delays a reply) -> 334 sleep agenda
  -> 333 creative (outside the reader: a creative request is never read or saved)
  -> [mouth, own line, 330b] -> [nb-323 turn log, installed last, 330c]

  --arm claude_e2e330_arms:build_330a       292t + 298 + 274 + stack G         (--model = lis-301 reader)
  --arm claude_e2e330_arms:build_330a_334   330a + 334 sleep agenda
  --arm claude_e2e330_arms:build_330a_cre   330a + 334 + 333 creative         (--gen-model = base MiniCPM5-1B)
Each builder returns the loop; the harness sends turns, runs one sleep per day and restarts from
the same state dir (lis-314's pending store and 334's agenda live there).
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

THRESHOLD = 0.995
_GEN: dict = {}


def _gen(model_dir: str):
    if model_dir not in _GEN:
        import claude_cre333_agent as C
        _GEN[model_dir] = C.Gen333(model_dir)
    return _GEN[model_dir]


def _base(state_dir, args):
    import copy
    import claude_loop292t_agent as T292
    import claude_fix298_branches as F298
    import claude_loop274_agent as L274
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    F298.install298(loop)
    L274.install_listen_first274(loop)
    return loop


def build_330a(state_dir, args):
    import claude_lis_stack as STACK
    import claude_lis_e2e_arms as LE
    import claude_loop274_agent as L274
    loop = _base(state_dir, args)
    STACK.build_stack(loop, LE._reader(args.model), THRESHOLD,
                      layers=("313", "315", "314", "316"), log_dir=state_dir)
    L274.install_turn_reply_first274(loop)
    return loop


def build_330a_334(state_dir, args):
    import claude_age334_agent as A334
    loop = build_330a(state_dir, args)
    A334.install_agenda334(loop)
    return loop


def build_330a_cre(state_dir, args):
    import claude_cre333_agent as C
    loop = build_330a_334(state_dir, args)
    C.install_creative333(loop, _gen(args.gen_model))
    return loop
