#!/usr/bin/env python3
"""xfer-1 learning a new kind, and answering (research-loop thread, 2026-09-27). EDITABLE by the research loop.

Adapter(arm, ckpt, seed, total_examples): starts from the practised net (ckpt) or from fresh weights (ckpt None), then
learns from the maze batches the bench hands it (learn), one optimizer step per batch, with the arm's own practice
schedule (loop: random 1-16 rounds, loss on the last 1-6). Base recipe (as rsn-358x): a new AdamW, constant lr after
a short warm-up. predict: plain answers in one pass; the loop thinks up to max_rounds rounds and stops at the first
round (from round 3) where its stop head says p > 0.5 and the answer is unchanged for 3 rounds (358a v2 stop rule).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_xfer1_net as N  # noqa: E402

LR, WD, WARMUP = 1e-3, 0.1, 50
N_SUP, FREE, GRAD = 4, 3, 2     # loop: deep supervision (TRM) - 4 updates per batch, state carried (detached) between them


class Adapter:
    def __init__(self, arm, ckpt, seed, total_examples):
        torch.manual_seed(900000 + seed)
        self.net = N.load_net(ckpt) if ckpt else N.Net(arm)
        assert self.net.arm == arm
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=LR, weight_decay=WD, betas=(0.9, 0.95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1, (i + 1) / WARMUP))
        self.round_rng = random.Random(910000 + seed)

    def update(self, loss):
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
        self.opt.step()
        self.sched.step()

    def learn(self, items):
        self.net.train()
        if self.net.arm != "loop":
            self.update(N.train_loss(self.net, items, self.round_rng))
            return
        net = self.net
        t, s, y = N.tensors(items)
        h = None
        for _ in range(N_SUP):
            e, (dr, dc) = net.embed(t, s)
            if h is None:
                h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(FREE):
                    h = net.step(h, e.detach(), dr, dc)
            h = h.detach()
            ces = []
            for _ in range(GRAD):
                h = net.step(h, e, dr, dc)
                ces.append(N.ce_and_exact(net.read(h)[0], s, y)[0])
            self.update(torch.stack(ces).mean())
            h = h.detach()


def stop_round(p, q, n):
    return next((r for r in range(2, n) if q[r] > 0.5 and p[r] == p[r - 1] == p[r - 2]), n - 1)


@torch.no_grad()
def predict(model, items, max_rounds):
    net = model.net
    net.eval()
    t, s, _ = N.tensors(items)
    H, W = t.shape[1], t.shape[2]
    if net.arm == "plain":
        rows = net.plain_forward(t, s).argmax(-1).tolist()
    else:
        preds, qs = net.loop_rounds(t, s, max_rounds)
        preds, qs = preds.tolist(), qs.tolist()
        rows = [p[stop_round(p, q, max_rounds)] for p, q in zip(preds, qs)]
    return [[r[i * W:(i + 1) * W] for i in range(H)] for r in rows]
