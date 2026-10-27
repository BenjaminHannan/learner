#!/usr/bin/env python3
"""Plug-in for claude_fewex_bench.py / claude_fewex_eq_bench.py (--plugin claude_dir_ks_net).

Same model as claude_fewex_net (re-exported unchanged). The only change is the
Learner's sleep: with WEAKEST = True the 4 stored sums and 4 stored grids of each
sleep update are drawn in proportion to their CURRENT loss (weakest first), instead
of uniformly (claude_fewex_bench.py:213-214). Everything else is a copy of the
harness Learner: optimizer, warm-up, clipping, mazes, round draws, 512 updates.
RNG alignment: the harness draws (uniform old samples, maze choices, rounds) are
still made, in the same order, from the same seeds, and the weighted picks use a
separate generator, so maze and round sequences are identical across both modes.
With WEAKEST = False the sleep equals the harness sleep bit for bit (see the
selftest in claude_dir_ks_run.py).
"""
from __future__ import annotations

import random
import time

import torch
import torch.nn.functional as F

from claude_fewex_net import *  # noqa: F401,F403  (Net, tensors, ce_and_exact, TRAIN_ROUNDS, ...)
import claude_fewex_net as _base

MAZE_BATCH, UPDATES = 32, 4      # copied from claude_fewex_bench.py (checked by the selftest)
SLEEP_STEPS = 512
WEAKEST = True                   # module switch; the runner sets it per arm
REFRESH = 16                     # recompute the per-item loss table every 16 sleep updates
LOSS_FLOOR = 1e-3                # weight = per-item CE + floor, so no stored item has zero chance


@torch.no_grad()
def item_losses(net, items, rounds=_base.TRAIN_ROUNDS):
    """Per-item mean cross-entropy over answer cells after `rounds` loop rounds (no gradient)."""
    t, s, y = _base.tensors(items)
    e, (dr, dc) = net.embed(t, s)
    h = torch.zeros_like(e)
    for _ in range(rounds):
        h = net.step(h, e, dr, dc)
    logits = net.read(h)[0].float()
    B_ = s.shape[0]
    mask = s.view(B_, -1).bool()
    yy = y.view(B_, -1)
    ce = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), yy.reshape(-1), reduction="none").view(B_, -1)
    return ((ce * mask).sum(1) / mask.sum(1).clamp(min=1)).tolist()


def weighted_pick(rng, weights, n):
    """n distinct indices, chosen with probability proportional to weight (Efraimidis-Spirakis)."""
    keys = [(rng.random() ** (1.0 / max(w, 1e-12)), i) for i, w in enumerate(weights)]
    keys.sort(reverse=True)
    return [i for _, i in keys[:n]]


class Learner:
    def __init__(self, net, lr):
        self.net = net
        self.opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))
        self.steps = 0
        self.picks = {"sums4": [], "grids5": []}      # indices drawn, kept for the record

    def update(self, loss):
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.steps += 1

    def maze_batch(self, items):          # unchanged copy of the harness (loop arm only)
        self.net.train()
        t, s, y = tensors(items)
        h = None
        for _ in range(UPDATES):
            e, (dr, dc) = self.net.embed(t, s)
            if h is None:
                h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(3):
                    h = self.net.step(h, e.detach(), dr, dc)
            h = h.detach()
            ces = []
            for _ in range(2):
                h = self.net.step(h, e, dr, dc)
                ces.append(ce_and_exact(self.net.read(h)[0], s, y)[0])
            self.update(torch.stack(ces).mean())
            h = h.detach()

    def sleep(self, mazes, seed, old):
        rng = random.Random(9262700 + seed)
        round_rng = random.Random(9282700 + seed)
        pick_rng = random.Random(9302700 + seed)      # only used when WEAKEST
        t0 = time.monotonic()
        table = {}
        for step in range(SLEEP_STEPS):
            old_a = rng.sample(old["sums4"], 4)       # harness draws, always made (keeps rng aligned)
            old_b = rng.sample(old["grids5"], 4)
            new = rng.choices(mazes, k=8)
            if WEAKEST:
                if step % REFRESH == 0:
                    self.net.eval()
                    table = {n: item_losses(self.net, old[n]) for n in ("sums4", "grids5")}
                    self.net.train()
                w_a = [x + LOSS_FLOOR for x in table["sums4"]]
                w_b = [x + LOSS_FLOOR for x in table["grids5"]]
                ia, ib = weighted_pick(pick_rng, w_a, 4), weighted_pick(pick_rng, w_b, 4)
                old_a = [old["sums4"][i] for i in ia]
                old_b = [old["grids5"][i] for i in ib]
                self.picks["sums4"].extend(ia)
                self.picks["grids5"].extend(ib)
            losses = []
            for items in (old_a, old_b, new):
                t, s, y = tensors(items)
                rr = round_rng.randint(1, TRAIN_ROUNDS)
                grad = round_rng.randint(1, min(rr, GRAD_ROUNDS))
                loss = torch.stack([ce_and_exact(lg, s, y)[0]
                                    for lg, _ in self.net.loop_train(t, s, rr - grad, grad)]).mean()
                losses.append(loss)
            self.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
        return time.monotonic() - t0
