#!/usr/bin/env python3
"""R2g plug-in: the race's loop with its position bias TIED across directions and axes, for any coordinate layout.

Helper R2g (2026-09-28), a general rebuild of design R2 ("soft-D4 loop", artifacts/claude-dir-h9-novelty-20260928/REPORT.md section 5).
The loop of scripts/claude_fewex_net.py (two shared width-256 blocks, eight heads, input re-added every round, learned stop,
48-round cap) with ONE change, inside `Block`: how attention learns "which other cell matters".

Loop bias (one signed table per axis):        bias(i, j) = br[dr] + bc[dc]                        18 numbers per head; up, down,
                                                                                                  left and right are four separate facts
R2g bias (one shared table of distances):     bias(i, j) = sum_a tie[|d_a|]  +  RHO * (br[dr] + bc[dc])
   tie   [heads, CLIP + 1]  learned, one entry per distance 0..4, SHARED by every axis and both signs
   RHO   0.3, fixed now, never tuned; the old signed tables stay as a small correction that moves at 0.3 of the pace
So "a neighbour one step away" is one learned fact whatever the direction, and a direction-specific correction is still possible
(sums carry leftward). At initialisation tie = 0, br = bc = 0: the bias is exactly the loop's start (all zeros).

Second half of the same change (the loop's narrow heads, the first four of eight, see only a 3-wide COLUMN strip, an axis-specific
rule; so the round-0 function is NOT bit-identical to the loop's, only the bias is): narrow heads may attend where at most ONE axis is far (|d| > 1), i.e. a cross of strips along the axes. That contains the old
strip. For a layout with a single axis (a line of words) nothing is masked.

GENERAL LAYOUTS. The bias reads only the per-axis offsets between two positions. `tied_bias(tie, resid, axes)` takes a list of
[T, T] clipped offset tensors, one per coordinate axis, so it accepts 1 axis (a token sequence), 2 (a grid), 3 (a block) or a point
cloud with any cell order (`coord_offsets` builds them from a [T, n] coordinate array). It never sees a puzzle kind, a maze wall, a
slot label or a grid size. A layout with no coordinates at all gets no symmetry: it has no axes, and the module then adds nothing.
The ruler's tokens arrive as an H x W grid, so the network glue passes the two axes the loop's `embed` already returns.

Extra weights: tie = 8 heads x 5 distances x 2 blocks = 80. Stored 1,645,806 against the loop's 1,645,726 (+0.0049%).
No extra compute beyond a table gather. The plain arm is untouched. The new tensors are created after every loop tensor and hold
zeros (no random numbers), so the loop's own weights initialise exactly as in the baseline under the same torch seed.
The harness Learner is used unchanged (this module defines no Learner); weight decay 0.1 applies to `tie` like to br and bc.
CPU, fp32 (the ruler's rule).
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as base  # noqa: E402

# Names the harness reads from its plug-in.
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
CLIP, WINDOW = base.CLIP, base.WINDOW
tensors = base.tensors
ce_and_exact = base.ce_and_exact
train_loss = base.train_loss

RHO = 0.3          # fixed now, never tuned: how much of the old direction-specific tables is kept (they move at 0.3 of the pace)


# ------------------------- layout-general pieces (pure functions of offsets) -------------------------
def coord_offsets(coords, clip=CLIP):
    """coords [T, n] integer positions in any layout -> list of n tensors [T, T], entry (i, j) = clip(c_i - c_j) + clip.
    n = 1 is a sequence, 2 a grid (matches `base.Net.offsets`), 3 a block; any cell order and irregular point sets work."""
    coords = torch.as_tensor(coords)
    return [(coords[:, a][:, None] - coords[:, a][None, :]).clamp(-clip, clip) + clip for a in range(coords.shape[1])]


def tied_bias(tie, resid, axes, rho=RHO, clip=CLIP):
    """Attention bias [heads, T, T] from per-axis clipped offsets (values 0..2*clip, centre = clip).
    tie   [heads, clip + 1]: one entry per distance, shared by all axes and both signs.
    resid list of [heads, 2*clip + 1] signed tables (the loop's br, bc); axis a uses resid[min(a, len(resid) - 1)]."""
    out = 0
    for a, off in enumerate(axes):
        out = out + tie[:, (off - clip).abs()]
        if rho and resid:
            out = out + rho * resid[min(a, len(resid) - 1)][:, off]
    return out


def cross_far(axes, narrow_heads, heads, window=WINDOW, clip=CLIP):
    """Boolean [heads, T, T] mask: True where a narrow head may NOT attend = two or more axes are far (|d| > window)."""
    far = sum(((off - clip).abs() > window).long() for off in axes)
    dead = torch.zeros(heads, 1, 1, dtype=torch.bool, device=axes[0].device)
    dead[:narrow_heads] = True
    return dead & (far >= 2)


class TiedBlock(base.Block):
    """base.Block with the tied bias. Built FROM an existing block (its modules are shared, no random numbers drawn).
    CROSS = False keeps the loop's column-strip mask (table-only variant, "R2-lite"); it is used by the selftest and never by the race."""
    CROSS = True

    def __init__(self, blk):
        nn.Module.__init__(self)
        self.h = blk.h
        self.ln1, self.ln2, self.qkv, self.out, self.mlp = blk.ln1, blk.ln2, blk.qkv, blk.out, blk.mlp
        self.br, self.bc = blk.br, blk.bc
        self.tie = nn.Parameter(torch.zeros(blk.h, CLIP + 1))      # created last, zeros: same start function as the loop

    def forward_axes(self, x, axes):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = tied_bias(self.tie, [self.br, self.bc], axes)
        if self.CROSS:
            dead = cross_far(axes, self.h // 2, self.h)
        else:                                                    # the loop's own strip: narrow heads see only |dc| <= WINDOW
            dead = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
            dead[: self.h // 2] = True
            dead = dead & ((axes[-1] - CLIP).abs() > WINDOW)
        bias = bias.masked_fill(dead, float("-inf")).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))

    def forward(self, x, dr, dc):
        return self.forward_axes(x, (dr, dc))


class Net(base.Net):
    def __init__(self, arm):
        super().__init__(arm)                      # every loop / plain tensor is created (and seeded) here
        if arm == "loop":
            self.blocks = nn.ModuleList(TiedBlock(b) for b in self.blocks)


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
    r2, loop, plain = Net("loop"), base.Net("loop"), base.Net("plain")
    tie = sum(p.numel() for n, p in r2.named_parameters() if n.endswith(".tie"))
    return {"stored": r2.weight_count(), "loop_stored": loop.weight_count(), "plain_stored": plain.weight_count(),
            "tie_weights": tie, "gap_vs_loop_weights": r2.weight_count() - loop.weight_count(),
            "gap_vs_loop_pct": 100 * (r2.weight_count() - loop.weight_count()) / loop.weight_count(),
            "gap_vs_plain_pct": 100 * (r2.weight_count() - plain.weight_count()) / plain.weight_count(),
            "persistent_coefficients": r2.weight_count(), "rho": RHO}
