#!/usr/bin/env python3
"""SL plug-in: the loop's stop head learns "my answer now equals my answer at round 48" instead of "my answer is exactly right".

The one change (artifacts/claude-dir-sl-20260928/DESIGN.md section 4, marks in PASSMARKS.md Part C): in practice on sums and grids,
`claude_fewex_net.train_loss` (claude_fewex_net.py:161-172) trains the halt logit with BCE to "every fill cell is right this round",
which needs the answer key. Here the target for each gradient round is "the round's arg-max on every fill cell equals the arg-max
of round 48 of the same run", where round 48 is reached by continuing the same detached state for 48 - total more rounds without
gradient. Nothing else changes: the round draws (same two `round_rng` draws in the same order), the free and gradient rounds, the
cross-entropy on the labelled practice kinds, the weight 0.5, the mean over gradient rounds, `Net` (the baseline class itself),
the optimizer, warm-up, schedule and seeds. There is no `Learner` here: the harness falls back to its own baseline Learner, so
maze adaptation has no stop loss, exactly as in the baseline.

Use (source stage): python -B scripts/claude_dir_sl_source.py --seed S --out <dir>
Use (adapt stage):  python -B scripts/claude_fewex_eq_bench.py adapt --plugin claude_dir_sl_stop --arm loop --seed S --init pre
                    --source <dir from the source stage> --out <dir> --threads 1
CPU, fp32 (the ruler's rule).
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as base  # noqa: E402

# Names the harness reads from its plug-in: all the baseline's own objects.
Net = base.Net
ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors = base.tensors
ce_and_exact = base.ce_and_exact
load_net = base.load_net

STOP_WEIGHT = 0.5          # the practice weight (claude_fewex_net.py:172); fixed, never tuned
FINAL_ROUND = 48           # the ruler's round cap (claude_fewex_bench.MAX_ROUNDS)
STATS = {"gradient_round_items": 0, "stable": 0, "exact": 0, "stable_and_exact": 0}   # counters only; never read by the loss


def stable_target(logits, final, fill):
    """1.0 for a puzzle whose arg-max on EVERY fill cell equals the round-48 arg-max, else 0.0."""
    return ((logits.argmax(-1) == final) | ~fill).all(1).float()


def loss_with_target(net, items, round_rng, target):
    """`target` is "stable" (this change) or "exact" (the baseline's; used only by the selftest to prove nothing else differs)."""
    t, s, y = tensors(items)
    if net.arm == "plain":
        return ce_and_exact(net.plain_forward(t, s), s, y)[0]
    total = round_rng.randint(1, TRAIN_ROUNDS)
    k = round_rng.randint(1, min(total, GRAD_ROUNDS))
    e, (dr, dc) = net.embed(t, s)
    h = torch.zeros_like(e)
    with torch.no_grad():
        for _ in range(total - k):
            h = net.step(h, e.detach(), dr, dc)
    h = h.detach()
    outs = []
    for _ in range(k):
        h = net.step(h, e, dr, dc)
        outs.append(net.read(h))
    final = None
    if target == "stable":
        with torch.no_grad():                                   # the same state, carried on to round 48, no gradient
            hf = h.detach()
            for _ in range(FINAL_ROUND - total):
                hf = net.step(hf, e.detach(), dr, dc)
            final = net.read(hf)[0].argmax(-1)                  # [B, T]
    fill = s.view(s.shape[0], -1).bool()
    ces, hls = [], []
    for lg, q in outs:
        ce, exact_now = ce_and_exact(lg, s, y)
        if target == "stable":
            tgt = stable_target(lg, final, fill)
            STATS["gradient_round_items"] += int(tgt.numel())
            STATS["stable"] += int(tgt.sum())
            STATS["exact"] += int(exact_now.sum())
            STATS["stable_and_exact"] += int((tgt * exact_now).sum())
        else:
            tgt = exact_now
        ces.append(ce)
        hls.append(F.binary_cross_entropy_with_logits(q.float(), tgt))
    return torch.stack(ces).mean() + STOP_WEIGHT * torch.stack(hls).mean()


def train_loss(net, items, round_rng):
    return loss_with_target(net, items, round_rng, "stable")


class Practice(base.Practice):
    """The baseline's sums-and-grids practice (same optimizer, schedule, clip, seeds); only the loss function it calls differs."""

    def step(self, items):
        self.net.train()
        loss = train_loss(self.net, items, self.round_rng)
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
        self.opt.step()
        self.sched.step()
        return loss.item()


def describe():
    """Stored weights, and confirmation that nothing was added to the loop."""
    n, ref = Net("loop"), base.Net("loop")
    return {"stored": n.weight_count(), "loop_stored": ref.weight_count(),
            "gap_vs_loop_weights": n.weight_count() - ref.weight_count(),
            "persistent_coefficients": n.weight_count(), "stop_weight": STOP_WEIGHT, "final_round": FINAL_ROUND}
