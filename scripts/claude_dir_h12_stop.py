#!/usr/bin/env python3
"""H12 plug-in: the race's loop with the practice stop loss added while it adapts to the new kind.

The one change (artifacts/claude-dir-h12-stop-20260928/DESIGN.md section 3): the baseline harness
Learner trains the loop on mazes with cross-entropy only ("no maze stop-head loss",
scripts/claude_fewex_bench.py:205). This Learner adds the loss the stop head gets in practice
(scripts/claude_fewex_net.py:171-172):

    mean over the 2 gradient rounds of CE  +  0.5 x mean over the 2 gradient rounds of
    BCEwithLogits(halt logit, "this round's answer is exactly right", per maze)

Nothing else differs: `Net` IS claude_fewex_net.Net (same class, 1,645,726 weights, same state dict);
the round structure (3 no-gradient + 2 gradient rounds per update, state carried and detached between
the 4 updates of a batch), optimizer, warm-up, clip, sleep and scoring are the harness's own, because
`Learner` subclasses claude_fewex_bench.Learner and overrides only `maze_batch`. There is no kind
label, no hand-written rule and nothing maze-specific: the target is the exactness feedback the loop
already gets on every kind. Rounds outside {4, 5, 9, 10, 14, 15, 19, 20} get no stop loss on mazes
(that follows from the baseline round structure and is deliberately not changed).

Use: python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_h12_stop --arm loop
     --seed S --init pre --source <qualified source dir> --out <dir> --threads 1
CPU, fp32 (the ruler's rule).
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402  (the harness's own baseline Learner)
import claude_fewex_net as base  # noqa: E402

# Names the harness reads from its plug-in: all the baseline's own objects.
Net = base.Net
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss
Practice = base.Practice
load_net = base.load_net

STOP_WEIGHT = 0.5      # the practice weight (claude_fewex_net.py:172); fixed now, never tuned
FREE_ROUNDS, GRAD_ROUNDS_PER_UPDATE = 3, 2   # the baseline maze_batch's own numbers (claude_fewex_bench.py:198, 202)


class Learner(B.Learner):
    """The harness Learner, with the stop loss added in `maze_batch` only. `sleep` and `update` are inherited."""

    def maze_batch(self, items):
        if self.net.arm == "plain":          # plain has no stop head: the baseline path
            return super().maze_batch(items)
        self.net.train()
        t, s, y = tensors(items)
        h = None
        for _ in range(B.UPDATES):
            e, (dr, dc) = self.net.embed(t, s)
            if h is None:
                h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(FREE_ROUNDS):
                    h = self.net.step(h, e.detach(), dr, dc)
            h = h.detach()
            ces, hls = [], []
            for _ in range(GRAD_ROUNDS_PER_UPDATE):
                h = self.net.step(h, e, dr, dc)
                logits, q = self.net.read(h)
                ce, exact_now = ce_and_exact(logits, s, y)
                ces.append(ce)
                if STOP_WEIGHT:
                    hls.append(F.binary_cross_entropy_with_logits(q.float(), exact_now))
            loss = torch.stack(ces).mean()
            if STOP_WEIGHT:
                loss = loss + STOP_WEIGHT * torch.stack(hls).mean()
            self.update(loss)
            h = h.detach()


def describe():
    """Stored weights, and confirmation that nothing was added to the loop."""
    n, ref = Net("loop"), base.Net("loop")
    return {"stored": n.weight_count(), "loop_stored": ref.weight_count(),
            "gap_vs_loop_weights": n.weight_count() - ref.weight_count(),
            "persistent_coefficients": n.weight_count(), "stop_weight": STOP_WEIGHT}
