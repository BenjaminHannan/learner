#!/usr/bin/env python3
"""R1g design plug-in: the race's loop plus a general "reach channel" (helper R1G, 2026-09-28).

The loop of scripts/claude_fewex_net.py (two shared width-256 blocks, eight heads, input re-added each round, learned stop from a
mean-pooled halt head, 48-round cap) with ONE change, in `step`: after the two blocks and before the state LayerNorm, one extra
channel adds "how far does each item lead to / get led to by other items" to the state.

Per round, with z the block output [B, T, 256] and u = LayerNorm(z):
  links   A_ij = q_i . k_j / sqrt(8) + br[dr_ij] + bc[dc_ij] + b       q, k: rank-8 projections of u; br, bc: the loop's OWN clipped
                                                                     row and column offsets (the same position interface the blocks use)
          P = softmax_j(A)            each row sums to 1: a learned "which item leads to which item" table
          M = gamma P, gamma = sigmoid(g), g starts at logit(0.95)
  reach   S = sum_{n=0..63} M^n, computed exactly as prod_{j=0..5} (I + M^(2^j)): all routes up to 63 steps in one round
  probes  a_k = sigmoid(W u + c) for k = 1..4: four LEARNED item subsets (unnamed; nothing says start, goal or wall),
          mass-normalised  a_k / (1 + sum_i a_k,i)
  features  fwd_k = S^T a_k / cap, bwd_k = S a_k / cap (k = 1..4), back = (S_ii - 1) / cap (routes that return to the item itself),
            in = mean_i S_ij / cap (how much of everything flows into this item)                               -> 10 numbers per item
            cap = (1 - gamma^64)/(1 - gamma) is the largest possible row sum of S, so every feature is in [0, 1]
  z <- z + Linear_10to256(features)   (zero-initialised: the net starts exactly as the loop)

Nothing in this file mentions mazes, walls, routes, starts, goals, grids or a puzzle kind, and no kind label reaches it. The block
offsets (dr, dc) are the inputs the loop's own attention already gets. The channel treats items as an unordered set that has links
between them (checked in the selftest: it is permutation-equivariant, and it runs on a set of any size that is not a grid).

Extra weights: 8,472 (LN 512, q and k 4,096, br + bc 18, link bias 1, probes 1,024 + 4, gamma logit 1, mix 2,560 + 256). Stored total
1,654,198 against the loop's 1,645,726 (+0.515%).
Weight decay: the gamma logit, the probe biases and the link bias are exempt (two AdamW groups, as the H3 v2 fix): decay 0.1 over the
practice schedule would pull gamma from 0.95 toward 0.84 and shorten the horizon without any gradient asking for it.
Because the new parameters are created after every loop parameter, the loop parameters get the same random init as the baseline loop
under the same torch seed (checked in the selftest).
The baseline learner is used except for that weight-decay grouping (`Learner` below). No auxiliary loss anywhere. CPU, fp32.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_net as base  # noqa: E402

# Names the harness reads from its plug-in.
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss          # uses net.arm / net.loop_train, so it runs this Net's step

RANK, PROBES, HOPS_LOG2 = 8, 4, 6      # fixed now, never tuned: 2^6 = 64 terms, hops 0..63
GAMMA_INIT = 0.95
FEATURES = 2 * PROBES + 2
NO_DECAY = ("reach_g", "link_b", "probe.bias")          # exempt from weight decay
DEAD_MIX = 1e-3                                         # mean |mix.weight| below this after practice = channel unused


def param_groups(net, wd):
    """Two AdamW groups: everything at decay `wd`, except the NO_DECAY tensors at 0 (no second group when there are none)."""
    free = [p for n, p in net.named_parameters() if n in NO_DECAY]
    rest = [p for n, p in net.named_parameters() if n not in NO_DECAY]
    groups = [{"params": rest, "weight_decay": wd}]
    if free:
        groups.append({"params": free, "weight_decay": 0.0})
    return groups


def reach_matrix(M):
    """S = sum_{n=0}^{63} M^n for a batch of square matrices [B, T, T], exactly, by repeated squaring (5 squarings, 5 products)."""
    T = M.shape[-1]
    eye = torch.eye(T, dtype=M.dtype, device=M.device)
    S, P = eye + M, M
    for _ in range(HOPS_LOG2 - 1):
        P = P @ P
        S = S @ (eye + P)
    return S


class Net(base.Net):
    REACH_OFF = False                  # True in the credit check: the four kinds of reach features are zeroed (the mix input is 0)

    def __init__(self, arm):
        super().__init__(arm)          # every loop / plain parameter is created (and seeded) here
        self.record = None             # optional dict of last-round reach tensors (diagnostics only)
        if arm == "loop":
            d = ARMS[arm]["d"]
            self.reach_ln = nn.LayerNorm(d)
            self.wq = nn.Linear(d, RANK, bias=False)
            self.wk = nn.Linear(d, RANK, bias=False)
            self.link_r = nn.Parameter(torch.zeros(2 * base.CLIP + 1))
            self.link_c = nn.Parameter(torch.zeros(2 * base.CLIP + 1))
            self.link_b = nn.Parameter(torch.zeros(1))
            self.probe = nn.Linear(d, PROBES)
            self.reach_g = nn.Parameter(torch.tensor(math.log(GAMMA_INIT / (1 - GAMMA_INIT))))
            self.mix = nn.Linear(FEATURES, d)
            nn.init.zeros_(self.mix.weight)
            nn.init.zeros_(self.mix.bias)

    def reach_features(self, z, dr, dc):
        """[B, T, 10] reach features from the block output z; also the parts, for diagnostics."""
        u = self.reach_ln(z)
        q, k = self.wq(u), self.wk(u)
        A = q @ k.transpose(1, 2) / math.sqrt(RANK) + (self.link_r[dr] + self.link_c[dc]).unsqueeze(0) + self.link_b
        P = torch.softmax(A, dim=-1)
        gamma = torch.sigmoid(self.reach_g)
        S = reach_matrix(gamma * P)
        cap = (1 - gamma ** (2 ** HOPS_LOG2)) / (1 - gamma)         # largest possible row sum of S
        a = torch.sigmoid(self.probe(u))                            # [B, T, K] learned item subsets
        a = a / (1 + a.sum(1, keepdim=True))
        fwd = S.transpose(1, 2) @ a                                 # [B, T, K] how strongly each item is reached from subset k
        bwd = S @ a                                                 # [B, T, K] how strongly each item reaches subset k
        back = (torch.diagonal(S, dim1=1, dim2=2) - 1).unsqueeze(-1)   # [B, T, 1] routes that lead back to the item itself
        inn = S.mean(1).unsqueeze(-1)                               # [B, T, 1] mean reach into this item
        f = torch.cat([fwd, bwd, back, inn], -1) / cap
        if self.record is not None:
            self.record.update(P=P.detach(), S=S.detach(), a=a.detach(), f=f.detach(), gamma=float(gamma), cap=float(cap))
        return f

    def step(self, h, e, dr, dc):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc)
        if self.arm == "loop":
            f = self.reach_features(z, dr, dc)
            if self.REACH_OFF:
                f = torch.zeros_like(f)
            z = z + self.mix(f)
        return self.ln_state(z)

    @torch.no_grad()
    def reach_stats(self, tokens, positions, n=8):
        """Last-round diagnostics on a batch: mix size, gamma, probe means, link-row entropy, feature means."""
        self.record = {}
        try:
            self.loop_rounds(tokens, positions, n)
            r = self.record
        finally:
            self.record = None
        P = r["P"]
        ent = float(-(P * (P + 1e-12).log()).sum(-1).mean())
        return {"mix_weight_mean_abs": float(self.mix.weight.abs().mean()), "mix_bias_mean_abs": float(self.mix.bias.abs().mean()),
                "gamma": r["gamma"], "cap": r["cap"], "probe_mass_by_k": [round(float(x), 5) for x in r["a"].sum(1).mean(0)],
                "link_row_entropy": ent, "link_row_entropy_uniform": math.log(P.shape[-1]),
                "feature_mean_by_column": [round(float(x), 5) for x in r["f"].mean((0, 1))],
                "feature_std_by_column": [round(float(x), 5) for x in r["f"].std((0, 1))]}


class Practice:
    """claude_fewex_net.Practice with this module's Net (same recipe, same RNG streams); NO_DECAY tensors exempt from weight decay."""

    def __init__(self, arm, seed, total_steps):
        torch.manual_seed(seed)
        self.net = Net(arm)
        self.opt = torch.optim.AdamW(param_groups(self.net, WD), lr=LR, betas=(0.9, 0.95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(
            self.opt, lambda i: min(1, (i + 1) / WARMUP) * 0.5 * (1 + math.cos(math.pi * min(i, total_steps) / total_steps)))
        self.round_rng = random.Random(9000 + seed)

    def step(self, items):
        self.net.train()
        loss = train_loss(self.net, items, self.round_rng)
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
        self.opt.step()
        self.sched.step()
        return loss.item()

    def save(self, path):
        torch.save({"arm": self.net.arm, "state": self.net.state_dict()}, path)


class Learner(B.Learner):
    """The harness Learner with one change: the NO_DECAY tensors get weight decay 0 (the harness decays every parameter at 0.1).
    Same optimizer settings, warm-up schedule, updates and sleep. Arms without those tensors get the harness's single group."""

    def __init__(self, net, lr):
        super().__init__(net, lr)
        self.opt = torch.optim.AdamW(param_groups(net, .1), lr=lr, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net


def describe():
    """Stored weights, the channel's share, and the gap to the loop and the plain net."""
    r1, loop, plain = Net("loop"), base.Net("loop"), base.Net("plain")
    extra = r1.weight_count() - loop.weight_count()
    return {"stored": r1.weight_count(), "loop_stored": loop.weight_count(), "plain_stored": plain.weight_count(),
            "reach_weights": extra, "gap_vs_loop_pct": 100 * extra / loop.weight_count(),
            "gap_vs_plain_pct": 100 * (r1.weight_count() - plain.weight_count()) / plain.weight_count(),
            "persistent_coefficients": r1.weight_count(), "probes": PROBES, "rank": RANK, "hops": 2 ** HOPS_LOG2,
            "gamma_init": GAMMA_INIT}
