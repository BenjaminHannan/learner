#!/usr/bin/env python3
"""S1 plug-in: a hand-picked rotation/reflection (D4) prior on the k adaptation mazes. MAZES ONLY, not kind-blind.

The one change (artifacts/claude-s1-d4-20260929/PASSMARKS.md). The harness Learner adapts on batches of the k support
mazes. This Learner turns each maze of each batch by one random member of D4 (8 views: 4 turns x mirror), tokens, fill
slots and answer together, then calls the harness's own maze_batch unchanged. Everything else is the harness's:
`Net` IS claude_fewex_net.Net, same pool, same batches, same 2,048 updates, same optimizer, same scoring (no voting).
Sleep is inherited and sees the un-turned mazes (report-only in this test).

Leak guard: a turned support maze is skipped as a view if its wall layout equals any dev or holdout panel layout
(turned or not; about 4% of the k=16,384 pool has such a view). t=0 (no turn) is always allowed.

Use: python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_s1_d4 --arm {loop,plain} --seed S --init pre
     --source <qualified source dir> --out <dir> --threads 1      (CPU, fp32, the ruler's rule)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402  (the harness's own baseline Learner)
import claude_fewex_data as D  # noqa: E402
import claude_fewex_net as base  # noqa: E402
import claude_s1_d4_aug as A  # noqa: E402

Net = base.Net
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss
Practice = base.Practice
load_net = base.load_net

AUG_SEED = 9302700
_BANNED = None


def banned():
    global _BANNED
    if _BANNED is None:
        _BANNED = D.panels()[1]      # every dev and holdout layout, all sizes
    return _BANNED


class Learner(B.Learner):
    def __init__(self, net, lr):
        super().__init__(net, lr)
        self.rng = random.Random(AUG_SEED)
        self.calls = 0
        self.views = [0] * 8
        self.skipped = 0             # random draws that landed on a banned view and were redrawn from allowed ones

    def turned(self, item):
        ok = A.allowed_views(item, banned())
        t = self.rng.randrange(8)
        if t not in ok:
            self.skipped += 1
            t = self.rng.choice(ok)
        self.views[t] += 1
        return A.d4_item(item, t) if t else item

    def maze_batch(self, items):
        super().maze_batch([self.turned(it) for it in items])
        self.calls += 1
        if self.calls == 512:
            print(json.dumps({"phase": "d4_views", "views": self.views, "redrawn_for_leak_guard": self.skipped}),
                  flush=True)
