#!/usr/bin/env python3
"""H3 design plug-in: the race's loop with a per-cell "settle gate" on the carried state.

NOT EXECUTED where it was written (that machine has no torch). It is checked with
python3 -m py_compile only; scripts/claude_dir_h3_selftest.py must be run first
on a machine with torch.

The loop of scripts/claude_fewex_net.py (two shared width-256 blocks, eight heads,
the same attention and relative biases, the input re-added every round, learned
stop from a mean-pooled halt head, 48-round cap) with ONE change, in `step`.

Baseline round:   h_new = LN(blocks(h + e))                     # the proposal `prop`
This design:      h_new = h + g * (prop - h)                     # g in (0,1), one number per cell
                  g     = sigmoid( w . prop + b + s * log(mean_c (prop - h)^2 + 1e-3) )

So each cell decides, every round, how far to move toward what the blocks propose.
The gate reads two things about that one cell only: the proposal itself, and how
much the cell just changed (a measured "surprise", detached, so it is a signal and
not a path for gradients). A cell that has settled (small change) can learn to
freeze; a cell still moving can learn to keep moving. There is no kind label, no
round number or clock, no hand-written rule and nothing maze-specific. The learned
stop is the loop's, untouched: same halt head, same 48-round cap.

Extra weights: w (256) + b (1) + s (1) = 258. Stored total 1,645,984 against the
loop's 1,645,726 (+0.016%). Nothing else is added, nothing is frozen or grown.
Init: w = 0, s = 0, b = +4 (g = 0.982 everywhere), so it starts as almost the loop.
Because the gate parameters are created after every loop parameter, the loop
parameters get exactly the same random init as the baseline loop under the same
torch seed (checked in the selftest).

The baseline learner (claude_fewex_bench.Learner) is used unchanged: this module
has no Learner, so the harness falls back to it. No auxiliary loss anywhere.
CPU, fp32 (the ruler's rule).
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as base  # noqa: E402

# Names the harness reads from its plug-in.
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss          # uses net.arm / net.loop_train, so it runs this Net's step

GATE_BIAS_INIT = 4.0                  # fixed now, never tuned: sigmoid(4) = 0.982
SURPRISE_EPS = 1e-3                   # floor inside the log, fixed now


class Net(base.Net):
    def __init__(self, arm):
        super().__init__(arm)          # every loop / plain parameter is created (and seeded) here
        self.record = None             # optional list of gate tensors (diagnostics only)
        if arm == "loop":
            d = ARMS[arm]["d"]
            self.gate_state = nn.Linear(d, 1)                      # w (256) and b (1)
            self.gate_surprise = nn.Parameter(torch.zeros(1))      # s (1)
            nn.init.zeros_(self.gate_state.weight)
            nn.init.constant_(self.gate_state.bias, GATE_BIAS_INIT)

    def step(self, h, e, dr, dc):
        prop = super().step(h, e, dr, dc)            # LN(blocks(h + e)), the loop's own round
        if self.arm != "loop":
            return prop
        with torch.no_grad():                         # measured, not learned through
            surprise = torch.log((prop - h).pow(2).mean(-1, keepdim=True) + SURPRISE_EPS)
        g = torch.sigmoid(self.gate_state(prop) + self.gate_surprise * surprise)   # [B, T, 1]
        if self.record is not None:
            self.record.append(g.detach())
        return h + g * (prop - h)

    @torch.no_grad()
    def gate_stats(self, tokens, positions, n=48):
        """Gate values per round on a batch: mean, share below 0.5, share above 0.98."""
        self.record = []
        try:
            self.loop_rounds(tokens, positions, n)
            rec = self.record
        finally:
            self.record = None
        g = torch.stack([x.squeeze(-1) for x in rec], 1)      # [B, n, T]
        return {"mean_by_round": [round(float(x), 4) for x in g.mean((0, 2))],
                "below_half_by_round": [round(float((g[:, i] < .5).float().mean()), 4) for i in range(g.shape[1])],
                "above_98_by_round": [round(float((g[:, i] > .98).float().mean()), 4) for i in range(g.shape[1])],
                "mean_all": float(g.mean()), "min": float(g.min()), "max": float(g.max())}


class Practice:
    """claude_fewex_net.Practice with this module's Net (same recipe, same RNG streams)."""

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


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net


def describe():
    """Stored weights, the gate's share, and the gap to the loop and the plain net."""
    h3, loop, plain = Net("loop"), base.Net("loop"), base.Net("plain")
    gate = sum(p.numel() for n, p in h3.named_parameters() if n.startswith("gate_"))
    return {"stored": h3.weight_count(), "loop_stored": loop.weight_count(), "plain_stored": plain.weight_count(),
            "gate_weights": gate, "gap_vs_loop_weights": h3.weight_count() - loop.weight_count(),
            "gap_vs_loop_pct": 100 * (h3.weight_count() - loop.weight_count()) / loop.weight_count(),
            "gap_vs_plain_pct": 100 * (h3.weight_count() - plain.weight_count()) / plain.weight_count(),
            "persistent_coefficients": h3.weight_count(),
            "gate_bias_init": GATE_BIAS_INIT, "surprise_eps": SURPRISE_EPS}
