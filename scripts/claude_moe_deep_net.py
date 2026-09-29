#!/usr/bin/env python3
"""Plug-in: the race's loop, made deep and sparse (sparse mixture of experts, many layers).

Ben approved this architecture change on 2026-09-29 00:35 UTC (handoff/director-roadmap.md).
Design and reasons: artifacts/claude-moe-deep-20260929/DESIGN.md. Marks: PASSMARKS.md there.

What is kept from the loop (scripts/claude_fewex_net.py): width 256, eight heads, the same 2-D
relative-position attention (half the heads narrow), pre-norm residual blocks, the puzzle input
re-added every round, the state norm, the answer head, the learned stop head, the 48-round cap,
the practice loss and the maze learner. The net sees tokens and fill slots only, never a kind.

What changes (one architecture change, as approved):
  * depth: each round runs L DISTINCT (unshared) layers instead of the loop's 2 shared blocks.
    Rounds are unchanged (learned stop, cap 48, fixed by the harness), so total depth is
    L x rounds. More rounds of the same two blocks add no new weights for experts to fill, and
    the practised loop already hits the 48-round cap on most maze rungs (RESULTS-EQ.md).
  * sparse experts: each layer's feed-forward part is a mixture of experts in the most common
    frontier recipe (DeepSeek-V3, Kimi K2, GLM-4.5/5.1): E routed experts, the top 8 chosen per
    cell per round, plus 1 always-on shared expert. Softmax router in fp32 (init std 0.02, as
    Switch and OLMoE), top-8 weights renormalised to sum to 1 (Qwen3 style), dropless (no cell is
    ever dropped, so a cell's answer never depends on the other puzzles in its batch).
    Fine-grained experts of hidden width 64 (a quarter of the width, DeepSeekMoE style): the 8
    routed experts together are 512 = 2 x width wide, plus the shared one. Small experts keep the
    stored size down; the one close published result (TRM, tiny Sudoku/maze sets) warns that MoE
    and extra layers can overfit small puzzle data.
  * two small extra losses on every training update: the Switch/OLMoE load-balancing loss
    (coefficient 0.01) and the ST-MoE/OLMoE router z-loss (coefficient 0.001).
  * deep-stack init: each residual branch's last projection (attention output, expert and shared
    output) is scaled by sqrt(2 / L) at init, so one round's total update starts at the loop's
    size; at L = 2 this is exactly the loop's init scale.

Configs (CFGS) cover the main entry and the pre-registered scaling and attribution rows. The
active config is chosen with the env var CLAUDE_MOE_CFG (default the main entry) or set_cfg().
Net('plain') is the baseline plain net, unchanged, so the harness selftest runs, except under the
'plain-big' config (a same-size plain control: the dense 8 layers run once, no loop and no stop).
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
# Baseline learner constants (claude_fewex_bench.py), copied so Learner below does exactly what
# the baseline learner does, plus the two router losses.
UPDATES, SLEEP_STEPS = 4, 512
AUX_COEF, Z_COEF = 0.01, 0.001
D_MODEL, HEADS = 256, 8

# name -> layers per round, routed experts, top-k, shared experts, expert hidden; or a dense FFN.
CFGS = {
    # main entry
    "L8-E64": dict(kind="moe", layers=8, experts=64, top_k=8, shared=1, hidden=64),
    # depth scaling at 64 experts
    "L2-E64": dict(kind="moe", layers=2, experts=64, top_k=8, shared=1, hidden=64),
    "L4-E64": dict(kind="moe", layers=4, experts=64, top_k=8, shared=1, hidden=64),
    "L16-E64": dict(kind="moe", layers=16, experts=64, top_k=8, shared=1, hidden=64),
    # expert scaling at 8 layers
    "L8-E16": dict(kind="moe", layers=8, experts=16, top_k=8, shared=1, hidden=64),
    "L8-E32": dict(kind="moe", layers=8, experts=32, top_k=8, shared=1, hidden=64),
    "L8-E128": dict(kind="moe", layers=8, experts=128, top_k=8, shared=1, hidden=64),
    # attribution: dense 8-layer loops at the main entry's ACTIVE and TOTAL weights
    "L8-dense-act": dict(kind="dense", layers=8, hidden=576),
    "L8-dense-tot": dict(kind="dense", layers=8, hidden=None),   # hidden set below to match L8-E64's total
    # same-size plain net: the dense-tot layers run once (no loop, no stop), the harness's plain arm
    "plain-big": dict(kind="plain", layers=8, hidden=None),
}
MAIN = "L8-E64"


def _moe_ffn_params(c, d=D_MODEL):
    per = d * c["hidden"] + c["hidden"] + c["hidden"] * d + d
    return d * c["experts"] + (c["experts"] + c["shared"]) * per


# dense hidden width whose FFN has the same stored weights as the main entry's MoE FFN
CFGS["L8-dense-tot"]["hidden"] = round((_moe_ffn_params(CFGS[MAIN]) - D_MODEL) / (2 * D_MODEL + 1))
CFGS["plain-big"]["hidden"] = CFGS["L8-dense-tot"]["hidden"]

CFG_NAME = os.environ.get("CLAUDE_MOE_CFG", MAIN)
if CFG_NAME not in CFGS:
    raise SystemExit(f"CLAUDE_MOE_CFG={CFG_NAME!r} is not one of {sorted(CFGS)}")


def set_cfg(name):
    global CFG_NAME
    if name not in CFGS:
        raise ValueError(name)
    CFG_NAME = name


def cfg():
    return dict(CFGS[CFG_NAME], name=CFG_NAME)


def _linear_init_(w, b, fan_in, scale=1.0):
    """nn.Linear's default init (U(+-1/sqrt(fan_in)) for weight and bias), times `scale`."""
    bound = 1 / math.sqrt(fan_in)
    with torch.no_grad():
        w.uniform_(-bound, bound).mul_(scale)
        if b is not None:
            b.uniform_(-bound, bound).mul_(scale)


class MoE(nn.Module):
    """E routed GELU experts (top-k per cell, renormalised softmax gates) plus always-on shared experts.

    Dropless: every chosen (cell, expert) pair is computed. The pairs are sorted by expert and run
    either through one padded [E, C, d] buffer with two batched matmuls (GPU, while the padding costs
    at most 2x) or expert by expert on contiguous slices (CPU, or lopsided routing). Both paths do the
    same arithmetic; every scatter is a permutation, so results are deterministic and a cell's output
    never depends on the other puzzles in its batch.
    """

    def __init__(self, d, experts, top_k, shared, hidden, out_scale):
        super().__init__()
        self.n, self.k, self.hidden = experts, top_k, hidden
        self.router = nn.Linear(d, experts, bias=False)
        nn.init.trunc_normal_(self.router.weight, std=0.02, a=-0.04, b=0.04)
        self.w1 = nn.Parameter(torch.empty(experts, d, hidden))
        self.b1 = nn.Parameter(torch.empty(experts, hidden))
        self.w2 = nn.Parameter(torch.empty(experts, hidden, d))
        self.b2 = nn.Parameter(torch.empty(experts, d))
        for e in range(experts):
            _linear_init_(self.w1[e], self.b1[e], d)
            _linear_init_(self.w2[e], self.b2[e], hidden, out_scale)
        self.shared = nn.Sequential(nn.Linear(d, hidden * shared), nn.GELU(), nn.Linear(hidden * shared, d))
        _linear_init_(self.shared[2].weight, self.shared[2].bias, hidden * shared, out_scale)
        self.aux, self.z = [], []   # router losses from gradient-enabled passes
        self.trace = None            # optional list of [N, k] expert choices (diagnostics)
        self.path = "auto"           # "auto", or force "padded" / "segments" (selftest compares both)

    def forward(self, x):
        shape = x.shape
        flat = x.reshape(-1, shape[-1])
        n_tok, dev = flat.shape[0], flat.device
        logits = self.router(flat).float()
        probs = logits.softmax(-1)
        top_p, top_i = probs.topk(self.k, dim=-1)                       # [N, k]
        gate = top_p / top_p.sum(-1, keepdim=True)
        d = flat.shape[1]
        e_flat = top_i.reshape(-1)                                       # [N*k], cell-major
        order = torch.argsort(e_flat, stable=True)
        counts = torch.bincount(e_flat, minlength=self.n)
        x_rep = flat.unsqueeze(1).expand(n_tok, self.k, d).reshape(-1, d)  # backward: a plain sum over k
        cap = int(counts.max())
        if self.path == "padded" or (self.path == "auto" and dev.type != "cpu" and self.n * cap <= 2 * e_flat.numel()):
            # one padded [E, C, d] buffer and two batched matmuls (few GPU kernels); used only while the
            # padding costs at most 2x, because maze cells come in few token types and routing can be lopsided
            e_sorted = e_flat[order]
            starts = torch.cumsum(counts, 0) - counts
            slot = torch.empty_like(order)       # (cell, choice) -> distinct slot of the buffer
            slot[order] = e_sorted * cap + torch.arange(order.numel(), device=dev) - starts[e_sorted]
            buf = flat.new_zeros(self.n * cap, d).index_copy(0, slot, x_rep).view(self.n, cap, d)
            h = F.gelu(torch.baddbmm(self.b1.unsqueeze(1), buf, self.w1))    # [E, C, hidden]
            y = torch.baddbmm(self.b2.unsqueeze(1), h, self.w2)              # [E, C, d]
            y = y.reshape(-1, d).index_select(0, slot)                       # back to cell-major order
        else:
            # no padding: each expert runs on its own contiguous slice of the expert-sorted pairs
            xs = x_rep.index_select(0, order)
            ys = [torch.addmm(self.b2[e], F.gelu(torch.addmm(self.b1[e], seg, self.w1[e])), self.w2[e])
                  for e, seg in enumerate(xs.split(counts.tolist())) if seg.shape[0]]
            inv = torch.empty_like(order)
            inv[order] = torch.arange(order.numel(), device=dev)
            y = torch.cat(ys).index_select(0, inv)                           # back to cell-major order
        y = y.view(n_tok, self.k, d)
        out = (y * gate.unsqueeze(-1).to(y.dtype)).sum(1) + self.shared(flat)
        if torch.is_grad_enabled():
            # Switch/OLMoE balance loss: E * sum_e f_e * P_e (1.0 when perfectly balanced), with f_e the
            # share of the N*k routing slots sent to e and P_e the mean router probability of e.
            f = counts.float() / e_flat.numel()
            self.aux.append(self.n * (f * probs.mean(0)).sum())
            self.z.append(torch.logsumexp(logits, -1).pow(2).mean())     # ST-MoE router z-loss
        if self.trace is not None:
            self.trace.append(top_i.detach().to(torch.int16).cpu())
        return out.view(shape)


class DenseFFN(nn.Sequential):
    def __init__(self, d, hidden, out_scale):
        super().__init__(nn.Linear(d, hidden), nn.GELU(), nn.Linear(hidden, d))
        _linear_init_(self[2].weight, self[2].bias, hidden, out_scale)


class Net(base.Net):
    def __init__(self, arm):
        c = cfg()
        if arm == "plain" and c["kind"] != "plain":
            super().__init__(arm)          # the baseline plain net, for the harness selftest
            return
        if (arm == "plain") != (c["kind"] == "plain"):
            raise ValueError(f"config {c['name']} is not a {arm} net")
        nn.Module.__init__(self)
        self.arm, self.cfg_name, d, L = arm, c["name"], D_MODEL, c["layers"]
        scale = math.sqrt(2 / L)
        self.tok = nn.Embedding(base.E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        blocks = []
        for _ in range(L):
            b = base.Block(d, HEADS)
            _linear_init_(b.out.weight, b.out.bias, d, scale)
            if c["kind"] == "moe":
                b.mlp = MoE(d, c["experts"], c["top_k"], c["shared"], c["hidden"], scale)
            else:
                b.mlp = DenseFFN(d, c["hidden"], scale)
            blocks.append(b)
        self.blocks = nn.ModuleList(blocks)
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, base.E.VOCAB)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    def moes(self):
        return [b.mlp for b in self.blocks if isinstance(b.mlp, MoE)]

    def pop_router_losses(self):
        """Mean balance loss and mean z-loss over every gradient-enabled layer call since the last pop."""
        aux = [t for m in self.moes() for t in m.aux]
        zs = [t for m in self.moes() for t in m.z]
        for m in self.moes():
            m.aux, m.z = [], []
        zero = self.halt.weight.new_zeros(())
        return (torch.stack(aux).mean() if aux else zero), (torch.stack(zs).mean() if zs else zero)

    def router_penalty(self):
        aux, z = self.pop_router_losses()
        return AUX_COEF * aux + Z_COEF * z

    def active_count(self):
        """Weights used for one cell in one round (routed experts: only the k chosen ones)."""
        if self.arm == "plain":
            return self.weight_count()
        unused = 0
        for m in self.moes():
            per = m.w1[0].numel() + m.b1[0].numel() + m.w2[0].numel() + m.b2[0].numel()
            unused += (m.n - m.k) * per
        return self.weight_count() - unused

    @torch.no_grad()
    def route_trace(self, tokens, positions, n=48):
        """Expert choices per layer and round: list over layers of [n, cells, k] (int16, CPU)."""
        for m in self.moes():
            m.trace = []
        try:
            self.loop_rounds(tokens, positions, n)
            return [torch.stack(m.trace, 0) for m in self.moes()]
        finally:
            for m in self.moes():
                m.trace = None


tensors = base.tensors
ce_and_exact = base.ce_and_exact


def train_loss(net, items, round_rng):
    """The baseline practice loss plus the two router losses (loop arm only)."""
    if net.arm == "plain":
        return base.train_loss(net, items, round_rng)
    net.pop_router_losses()
    loss = base.train_loss(net, items, round_rng)
    return loss + net.router_penalty()


class Practice:
    """claude_fewex_net.Practice with this module's Net and train_loss (same optimizer and schedule)."""

    def __init__(self, arm, seed, total_steps, lr=LR):
        torch.manual_seed(seed)
        self.net = Net(arm)
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=lr, weight_decay=WD, betas=(0.9, 0.95))
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


class Learner:
    """claude_fewex_bench.Learner, line for line, plus the router losses in every optimizer update
    (loop arm). Same AdamW, 50-update warm-up, clipping, four updates per maze batch, 3 free + 2
    gradient rounds with a carried state, no maze stop-head loss, and the same sleep RNGs, groups and
    weights."""

    def __init__(self, net, lr):
        self.net = net
        self.opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))
        self.steps = 0

    def update(self, loss):
        if self.net.arm == "loop":
            loss = loss + self.net.router_penalty()
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
        self.net.pop_router_losses()
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
        self.net.pop_router_losses() if self.net.arm == "loop" else None
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


def describe(name=None):
    """Stored and active weights of a config, next to the loop and the plain net."""
    prev = CFG_NAME
    if name:
        set_cfg(name)
    try:
        c = cfg()
        net = Net("plain" if c["kind"] == "plain" else "loop")
        out = {"cfg": c, "stored": net.weight_count(), "active_per_cell_round": net.active_count(),
               "loop_stored": base.Net("loop").weight_count(), "plain_stored": base.Net("plain").weight_count(),
               "aux_coef": AUX_COEF, "z_coef": Z_COEF, "residual_init_scale": math.sqrt(2 / c["layers"])}
        out["stored_vs_loop"] = out["stored"] / out["loop_stored"]
        out["active_vs_loop"] = out["active_per_cell_round"] / out["loop_stored"]
        return out
    finally:
        set_cfg(prev)
