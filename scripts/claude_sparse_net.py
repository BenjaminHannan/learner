#!/usr/bin/env python3
"""Test D plug-in: the race's loop with a mixture of experts in each block.

The loop from claude_fewex_net.py (two shared width-256 blocks, eight heads,
the same attention, the input re-added every round, learned stop, 48-round cap)
with one change: each block's feed-forward layer becomes 8 experts with a
learned router that picks the top 2 for each cell on each round (Mixtral style,
after arXiv 2605.09165). The router sees only the cell's hidden state: no kind
label, no round number, no hand-written rule. Nothing is frozen or grown.

Budget: expert hidden width 127 keeps the stored weights within 2% of the loop
(and of the plain net, which the harness selftest also checks). One Switch/
Mixtral load-balancing loss at coefficient 0.01 is added to every training loss:
practice, maze adaptation and sleep. It is fixed and never tuned on mazes.

Net('plain') is the baseline plain net, unchanged, so the harness selftest runs.
Device: CLAUDE_SPARSE_DEVICE=cpu (default) or cuda. On cuda the net is strict
fp32 (TF32 off, no autocast); inputs are moved to the net's device internally.
"""
from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as base  # noqa: E402

TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
EXPERTS, TOP_K, EXPERT_HIDDEN, AUX_COEF = 8, 2, 127, 0.01
# Baseline learner constants (claude_fewex_bench.py), copied so the learner below
# does exactly what the baseline learner does.
UPDATES, SLEEP_STEPS = 4, 512

DEVICE = torch.device(os.environ.get("CLAUDE_SPARSE_DEVICE", "cpu"))
if DEVICE.type == "cuda":
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


class Expert(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.fc1, self.fc2 = nn.Linear(d, h), nn.Linear(h, d)

    def forward(self, x):
        return self.fc2(F.gelu(self.fc1(x)))


class MoE(nn.Module):
    """Top-2 of 8 experts per cell; softmax over the two chosen router logits."""

    def __init__(self, d, experts=EXPERTS, hidden=EXPERT_HIDDEN, top_k=TOP_K):
        super().__init__()
        self.top_k = top_k
        self.router = nn.Linear(d, experts, bias=False)
        self.experts = nn.ModuleList(Expert(d, hidden) for _ in range(experts))
        self.aux = []        # load-balancing terms from gradient-enabled passes
        self.trace = None    # optional list of [B,T,2] expert choices (diagnostics)

    def forward(self, x):
        B, T, D = x.shape
        flat = x.reshape(-1, D)
        logits = self.router(flat)
        top_v, top_i = logits.topk(self.top_k, dim=-1)
        gate = torch.softmax(top_v, dim=-1)
        out = torch.zeros_like(flat)
        for e, expert in enumerate(self.experts):
            rows, slot = (top_i == e).nonzero(as_tuple=True)
            if rows.numel():
                out.index_add_(0, rows, gate[rows, slot, None] * expert(flat[rows]))
        if torch.is_grad_enabled():
            # Switch/Mixtral auxiliary loss: E * sum_e f_e * P_e, where f_e is the
            # share of the N*k routing slots sent to expert e and P_e the mean
            # router probability. Equals 1 when perfectly balanced.
            n_exp = logits.shape[-1]
            f = F.one_hot(top_i, n_exp).float().mean((0, 1))
            p = torch.softmax(logits.float(), dim=-1).mean(0)
            self.aux.append(n_exp * (f * p).sum())
        if self.trace is not None:
            self.trace.append(top_i.detach().view(B, T, self.top_k).to(torch.int8).cpu())
        return out.view(B, T, D)


class Net(base.Net):
    def __init__(self, arm):
        super().__init__(arm)
        if arm == "loop":
            d, h = base.ARMS[arm]["d"], base.ARMS[arm]["heads"]
            for b in self.blocks:
                b.mlp = MoE(d)
            assert all(b.h == h for b in self.blocks)
        self.to(DEVICE)

    def moes(self):
        return [b.mlp for b in self.blocks if isinstance(b.mlp, MoE)]

    def pop_aux(self):
        terms = [t for m in self.moes() for t in m.aux]
        for m in self.moes():
            m.aux = []
        if not terms:
            return torch.zeros((), device=DEVICE)
        return torch.stack(terms).mean()

    def embed(self, tokens, slot):
        return super().embed(tokens.to(DEVICE), slot.to(DEVICE))

    def forward(self, tokens, positions):
        return super().forward(tokens.to(DEVICE), positions.to(DEVICE))

    @torch.no_grad()
    def route_trace(self, tokens, positions, n=48):
        """Expert choices per block and round: list over blocks of [B, n, T, 2]."""
        for m in self.moes():
            m.trace = []
        try:
            self.loop_rounds(tokens, positions, n)
            return [torch.stack(m.trace, 1) for m in self.moes()]
        finally:
            for m in self.moes():
                m.trace = None


def tensors(items):
    return tuple(x.to(DEVICE) for x in base.tensors(items))


def ce_and_exact(logits, s, y):
    return base.ce_and_exact(logits, s.to(logits.device), y.to(logits.device))


def train_loss(net, items, round_rng):
    """The baseline loss plus the load-balancing term (loop arm only)."""
    net.pop_aux() if net.arm == "loop" else None
    loss = base_train_loss(net, items, round_rng)
    if net.arm == "loop":
        loss = loss + AUX_COEF * net.pop_aux()
    return loss


def base_train_loss(net, items, round_rng):
    # claude_fewex_net.train_loss, with this module's device-aware helpers
    t, s, y = tensors(items)
    if net.arm == "plain":
        return ce_and_exact(net.plain_forward(t, s), s, y)[0]
    total = round_rng.randint(1, TRAIN_ROUNDS)
    k = round_rng.randint(1, min(total, GRAD_ROUNDS))
    ces, hls = [], []
    for lg, q in net.loop_train(t, s, total - k, k):
        c_, ex = ce_and_exact(lg, s, y)
        ces.append(c_)
        hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
    return torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean()


class Practice:
    """claude_fewex_net.Practice with this module's Net and train_loss."""

    def __init__(self, arm, seed, total_steps):
        torch.manual_seed(seed)
        self.net = Net(arm)
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=LR, weight_decay=WD, betas=(0.9, 0.95))
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


class Learner:
    """claude_fewex_bench.Learner, line for line, plus AUX_COEF * load-balancing
    loss in each optimizer update (loop arm). Same optimizer, 50-update warm-up,
    clipping, four updates per batch, 3 free + 2 gradient rounds, carried state,
    no maze stop-head loss, and the same sleep RNGs, groups and weights."""

    def __init__(self, net, lr):
        self.net = net
        self.opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))
        self.steps = 0

    def update(self, loss):
        if self.net.arm == "loop":
            loss = loss + AUX_COEF * self.net.pop_aux()
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.steps += 1

    def maze_batch(self, items):
        self.net.train()
        if self.net.arm == "plain":
            for _ in range(UPDATES):
                t, s, y = tensors(items)
                self.update(ce_and_exact(self.net.plain_forward(t, s), s, y)[0])
            return
        t, s, y = tensors(items)
        self.net.pop_aux()
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
            self.update(torch.stack(ces).mean())  # no maze stop-head loss
            h = h.detach()

    def sleep(self, mazes, seed, old):
        rng = random.Random(9262700 + seed)
        round_rng = random.Random(9282700 + seed)
        t0 = time.monotonic()
        self.net.pop_aux()
        for _ in range(SLEEP_STEPS):
            old_a = rng.sample(old["sums4"], 4)
            old_b = rng.sample(old["grids5"], 4)
            new = rng.choices(mazes, k=8)
            losses = []
            for items in (old_a, old_b, new):
                t, s, y = tensors(items)
                if self.net.arm == "plain":
                    loss = ce_and_exact(self.net.plain_forward(t, s), s, y)[0]
                else:
                    rr = round_rng.randint(1, TRAIN_ROUNDS)
                    grad = round_rng.randint(1, min(rr, GRAD_ROUNDS))
                    loss = torch.stack([ce_and_exact(lg, s, y)[0]
                                        for lg, _ in self.net.loop_train(t, s, rr - grad, grad)]).mean()
                losses.append(loss)
            self.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
        return time.monotonic() - t0


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net


def describe():
    """Stored weights by part, and weights active for one cell in one round."""
    sparse, loop = Net("loop"), base.Net("loop")
    moe = sparse.blocks[0].mlp
    expert = sum(p.numel() for p in moe.experts[0].parameters())
    router = moe.router.weight.numel()
    dense_mlp = sum(p.numel() for p in loop.blocks[0].mlp.parameters())
    blocks = len(sparse.blocks)
    unused = blocks * (EXPERTS - TOP_K) * expert
    return {"stored": sparse.weight_count(), "loop_stored": loop.weight_count(),
            "plain_stored": base.Net("plain").weight_count(),
            "gap_vs_loop_pct": 100 * (sparse.weight_count() - loop.weight_count()) / loop.weight_count(),
            "experts": EXPERTS, "top_k": TOP_K, "expert_hidden": EXPERT_HIDDEN,
            "per_expert": expert, "router_per_block": router,
            "moe_stored_per_block": sum(p.numel() for p in moe.parameters()),
            "dense_mlp_per_block": dense_mlp,
            "moe_active_per_cell_round_per_block": router + TOP_K * expert,
            "active_per_cell_round": sparse.weight_count() - unused,
            "loop_active_per_cell_round": loop.weight_count(),
            "active_note": "stored weights minus the 6 unchosen experts in each block; "
                           "embeddings, attention, norms, answer and stop heads all count as active",
            "aux_coef": AUX_COEF, "persistent_coefficients": sparse.weight_count()}
