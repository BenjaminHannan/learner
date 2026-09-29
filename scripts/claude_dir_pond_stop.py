#!/usr/bin/env python3
"""Pond plug-in: a tiny compute penalty on the loop's stop while it adapts to mazes (PonderNet style).

The one change (artifacts/claude-dir-pond-20260928/DESIGN.md section 3). The harness Learner trains the loop on
mazes with cross-entropy only ("no maze stop-head loss", scripts/claude_fewex_bench.py:205). This Learner keeps
that loss exactly and adds one term that trains ONLY the stop head:

    per update, rounds t = 1..5 (3 free + 2 gradient rounds, as in the baseline):
      hazard_t = sigmoid(halt logit at round t)          # "stop here, given I have not stopped yet"
      p_t = hazard_t * prod_{j<t} (1 - hazard_j), the last round takes the rest of the mass
      term = mean over mazes of  sum_t p_t * CE_t(detached)  +  LAMBDA * sum_t t * p_t

The second part is LAMBDA times the expected number of rounds. CE_t is that maze's own cross-entropy at round t
(a constant here) and the state fed to the stop head is detached, so the term moves the stop head's weights and
nothing else: the body's own gradient is the baseline's. No answer-is-right label, no kind label, no hand-written rule.

Nothing else differs: `Net` IS claude_fewex_net.Net (1,645,726 weights, same state dict), round structure, optimizer,
warm-up, clip, sleep and scoring are the harness's own (`Learner` subclasses claude_fewex_bench.Learner and
overrides only `maze_batch`). LAMBDA is set by the thin arm modules claude_dir_pond_{a,b,c,z}.py.

Use: python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_pond_a --arm loop --seed S --init pre
     --source <qualified source dir> --out <dir> --threads 1      (CPU, fp32, the ruler's rule)
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402  (the harness's own baseline Learner)
import claude_fewex_net as base  # noqa: E402

Net = base.Net
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss
Practice = base.Practice
load_net = base.load_net

FREE_ROUNDS, GRAD_ROUNDS_PER_UPDATE = 3, 2   # the baseline maze_batch's own numbers (claude_fewex_bench.py:198, 202)


def ce_per_maze(logits, s, y):
    """Mean cross-entropy over each maze's own fill cells, [B]. Its fill-count-weighted mean is ce_and_exact's ce."""
    B_ = s.shape[0]
    s, y = s.view(B_, -1).bool(), y.view(B_, -1)
    ce = F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), y.reshape(-1), reduction="none").view(B_, -1)
    return (ce * s).sum(1) / s.sum(1).clamp(min=1)


def ponder_term(stop_logits, costs, lam):
    """stop_logits, costs: [T, B]. Returns the PonderNet-style scalar: mean over mazes of
    sum_t p_t * cost_t + lam * sum_t t * p_t, with p from the hazards sigmoid(stop_logits)."""
    T = stop_logits.shape[0]
    hazard = torch.sigmoid(stop_logits.float())
    alive = torch.ones_like(hazard[0])
    exp_cost = exp_rounds = 0.0
    for t in range(T):
        p = hazard[t] * alive if t < T - 1 else alive          # the last round takes the remaining mass
        exp_cost = exp_cost + p * costs[t]
        exp_rounds = exp_rounds + (t + 1) * p
        alive = alive * (1 - hazard[t])
    return (exp_cost + lam * exp_rounds).mean()


def make_learner(lam):
    class Learner(B.Learner):
        """The harness Learner with the stop-head-only penalty term added in `maze_batch`. `sleep`, `update` inherited."""
        LAMBDA = lam

        def maze_batch(self, items):
            if self.net.arm == "plain":          # plain has no stop head: the baseline path
                return super().maze_batch(items)
            net = self.net
            net.train()
            t, s, y = tensors(items)
            h = None
            for _ in range(B.UPDATES):
                e, (dr, dc) = net.embed(t, s)
                if h is None:
                    h = torch.zeros_like(e)
                zs, costs = [], []
                with torch.no_grad():
                    for _ in range(FREE_ROUNDS):
                        h = net.step(h, e.detach(), dr, dc)
                        z = net.ln_out(h)
                        zs.append(z.mean(1))
                        costs.append(ce_per_maze(net.head(z), s, y))
                h = h.detach()
                ces = []
                for _ in range(GRAD_ROUNDS_PER_UPDATE):
                    h = net.step(h, e, dr, dc)
                    z = net.ln_out(h)
                    logits = net.head(z)
                    ces.append(ce_and_exact(logits, s, y)[0])
                    zs.append(z.detach().mean(1))               # stop head sees a constant: no gradient into the body
                    costs.append(ce_per_maze(logits.detach(), s, y))
                stop_logits = torch.stack([net.halt(x).squeeze(-1) for x in zs])          # [5, B]
                loss = torch.stack(ces).mean() + ponder_term(stop_logits, torch.stack(costs), self.LAMBDA)
                self.update(loss)
                h = h.detach()

    return Learner


Learner = make_learner(0.0)      # arm modules replace it; a bare import is the lambda 0 control


def describe():
    n, ref = Net("loop"), base.Net("loop")
    return {"stored": n.weight_count(), "loop_stored": ref.weight_count(),
            "gap_vs_loop_weights": n.weight_count() - ref.weight_count(),
            "persistent_coefficients": n.weight_count()}
