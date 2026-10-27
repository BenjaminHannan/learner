#!/usr/bin/env python3
"""Plug-in for the equal-practice ruler (scripts/claude_fewex_eq_bench.py): the relation net as the loop.

The net is scripts/claude_relnet_net.py's RelNet, unchanged (1,644,198 weights). This file only adapts it to the
plug-in contract of artifacts/claude-fewex-20260927/PROTOCOL.md, the way scripts/claude_sparse_net.py does:

  Net(arm)              arm "loop" -> the relation net (arm attribute "loop", weight_count(), forward(), infer_rounds());
                        arm "plain" -> the baseline plain net, untouched (so the harness selftest runs)
  Practice(arm, seed, total_steps)   the baseline Practice (AdamW 1e-3, wd 0.1, betas .9/.95, 200 warm-up, cosine,
                        clip 1.0, round_rng 9000+seed) around this Net
  tensors, ce_and_exact, train_loss  the baseline's
  Learner(net, lr)      the baseline Learner (claude_fewex_bench.Learner): optimizer, warm-up, clipping, four updates
                        per batch, sleep (RNGs, groups, weights) are inherited unchanged. Only maze_batch is
                        re-expressed for the relation net's state: the loop carries h; the relation net carries
                        (h, r). Same 3 free rounds (no grad, input detached) + 2 gradient rounds per update, state
                        detached between updates, no stop-head loss on mazes.
  infer_rounds          RelNet.loop_rounds (no grad; 48 rounds of answers and stop probabilities)

No puzzle kind, no maze rule, no checker. fp32 on CPU, no autocast.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as FB  # noqa: E402  (Learner: sleep and the optimizer are inherited)
import claude_fewex_net as base  # noqa: E402
import claude_relnet_net as RN  # noqa: E402

ARMS, CLIP, WINDOW = base.ARMS, base.CLIP, base.WINDOW
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
UPDATES = FB.UPDATES
MAX_ROUNDS = 48
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss   # uses net.arm and net.loop_train(t, s, n_free, n_grad) -> [(logits, stop_logit)]


class RelPlug(RN.RelNet):
    def weight_count(self):
        return sum(p.numel() for p in self.parameters())

    def forward(self, tokens, positions):
        """Plug-in API: 48 per-round [B,T,V] cell logits and 48 [B] stop logits. `positions` is the fill-slot grid."""
        e, (dr, dc) = self.embed(tokens, positions)
        state, c = self.init_state(e), self._const(e, dr, dc)
        cells, stops = [], []
        for _ in range(MAX_ROUNDS):
            state = self.step(state, e, c)
            cell, stop = self.read(state[0])
            cells.append(cell)
            stops.append(stop)
        return cells, stops

    @torch.no_grad()
    def infer_rounds(self, tokens, positions, n=MAX_ROUNDS):
        return self.loop_rounds(tokens, positions, n)


def Net(arm):
    if arm == "loop":
        return RelPlug()
    return base.Net(arm)   # plain: the baseline's, untouched


class Practice(base.Practice):
    """claude_fewex_net.Practice around the relation net (everything else identical)."""

    def __init__(self, arm, seed, total_steps):
        torch.manual_seed(seed)
        self.net = Net(arm)
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=LR, weight_decay=WD, betas=(0.9, 0.95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(
            self.opt, lambda i: min(1, (i + 1) / WARMUP) * 0.5 * (1 + math.cos(math.pi * min(i, total_steps) / total_steps)))
        self.round_rng = random.Random(9000 + seed)


class Learner(FB.Learner):
    """The baseline Learner; only the loop-arm maze_batch is written for the (h, r) state."""

    def maze_batch(self, items):
        if self.net.arm == "plain":
            return super().maze_batch(items)
        self.net.train()
        t, s, y = tensors(items)
        state = None
        for _ in range(UPDATES):
            e, (dr, dc) = self.net.embed(t, s)
            if state is None:
                state = self.net.init_state(e)
            with torch.no_grad():
                e0 = e.detach()
                c0 = self.net._const(e0, dr, dc)
                for _ in range(3):
                    state = self.net.step(state, e0, c0)
            state = (state[0].detach(), state[1].detach())
            c, ces = self.net._const(e, dr, dc), []
            for _ in range(2):
                state = self.net.step(state, e, c)
                ces.append(ce_and_exact(self.net.read(state[0])[0], s, y)[0])
            self.update(torch.stack(ces).mean())  # no maze stop-head loss
            state = (state[0].detach(), state[1].detach())


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net
