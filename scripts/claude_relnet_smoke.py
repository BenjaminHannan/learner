#!/usr/bin/env python3
"""relnet smoke (2026-09-27): does the relation net learn at all on sums and grids in a few minutes, next to a
same-size loop on the same batches? NOT the practice gate (that is 6,000 batches of 64; this is 300 of 32).
The loop here is scripts/claude_xfer1_net.py's loop design at 2 x 256, 8 heads (no kind label), 1,645,726 weights.
Both: xfer1 train_loss (1-16 rounds, gradient through the last 1-6, stop-head loss), AdamW lr 1e-3, wd 0.1,
50-step warm-up then cosine, clip 1.0, fp32 on CPU. Score: exact-right on 100 fresh 4-digit sums and 100 fresh 5x5
grids at a fixed 16 rounds (the learned stop is not used in a smoke).

  python -B scripts/claude_relnet_smoke.py --steps 300 [--arms relnet,loop] --out artifacts/claude-relnet-20260927/smoke.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_xfer1_bench as B  # noqa: E402  (latin_legend: the practice grid format)
import claude_xfer1_net as N  # noqa: E402  (loop design, train_loss, tensors)
import claude_relnet_net as RN  # noqa: E402


def batch(rng, n):
    if rng.random() < 0.5:
        k = rng.choice([1, 2, 3, 4])
        return [E.make_sum(rng, k) for _ in range(n)]
    s = rng.choice([4, 5])
    return [B.latin_legend(rng, s) for _ in range(n)]


@torch.no_grad()
def exact(net, items, rounds=16):
    net.eval()
    t, s, y = N.tensors(items)
    preds, _ = net.loop_rounds(t, s, rounds)
    p = preds[:, -1].view(len(items), -1)
    m, yy = s.view(len(items), -1).bool(), y.view(len(items), -1)
    return int(((p == yy) | ~m).all(1).sum())


def main(a):
    torch.set_num_threads(4)
    N.ARMS["loop"] = dict(d=256, layers=2, heads=8)
    prng = random.Random(777)
    panel_s = [E.make_sum(prng, 4) for _ in range(100)]
    panel_g = [B.latin_legend(prng, 5) for _ in range(100)]
    rep = dict(steps=a.steps, batch=a.batch, arms={})
    for name in a.arms.split(","):
        torch.manual_seed(0)
        net = RN.RelNet() if name == "relnet" else N.Net("loop")
        opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=0.1, betas=(0.9, 0.95))
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda i: min(1, (i + 1) / 50) * 0.5 * (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
        drng, rrng = random.Random(1), random.Random(2)
        losses, t0 = [], time.time()
        for i in range(a.steps):
            net.train()
            loss = N.train_loss(net, batch(drng, a.batch), rrng)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            sched.step()
            losses.append(loss.item())
        secs = time.time() - t0
        row = dict(weights=RN.count(net), train_s=round(secs, 1),
                   loss_first50=round(sum(losses[:50]) / 50, 3), loss_last50=round(sum(losses[-50:]) / 50, 3),
                   sums4_right_of_100=exact(net, panel_s), grids5_right_of_100=exact(net, panel_g),
                   loss_every25=[round(sum(losses[j:j + 25]) / 25, 3) for j in range(0, a.steps, 25)])
        rep["arms"][name] = row
        print(name, row, flush=True)
    Path(a.out).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--arms", default="relnet,loop")
    ap.add_argument("--out", default="artifacts/claude-relnet-20260927/smoke.json")
    main(ap.parse_args())
