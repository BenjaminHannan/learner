#!/usr/bin/env python3
"""History-read plug-in: the race's loop where each round can also read the last WINDOW earlier states of the same cell.

Helper "Huginn ideas" (2026-09-29). Design: artifacts/claude-dir-hist-20260929/DESIGN.md. NOT EXECUTED where it was written
(that machine has no torch); checked with python3 -m py_compile only. Run scripts/claude_dir_hist_selftest.py first.

Baseline round (scripts/claude_fewex_net.py:77-81):  h_new = LN(blocks(h + e))       # the prompt e is already re-added every round
This design:  h_new = LN(blocks(h + e + R))     R = Wo( sum_i softmax_i(q.k_i) * h_{t-i} )     i = 1..WINDOW, per cell
  q = Wq h (256 -> 64), k_i = Wk h_{t-i} (256 -> 64), value = the stored state itself, Wo: 256 -> 256, ZERO-initialised (so it starts as
  the loop). Round 1 sees only the zero start state. The window is a fixed ring of the last WINDOW states (Huginn's fixed KV budget),
  so a 48-round test never asks the read to handle more entries than a 16-round practice round did (WINDOW=8 <= 16).
Extra weights: Wq, Wk (2 x 16,448) + Wo (65,792) = 98,688 (+6.0%), the same in the control.
CONTROL (claude_dir_hist_net_w1.py): WINDOW = 1. The read sees only the previous state h_{t-1}, i.e. the same extra weights and compute
with NO history; a gain of the WINDOW=8 arm over it can only come from the earlier states.
No kind label, no round number, no hand rule, no checker. The stop head, round counts, practice recipe, learner and ladder are the loop's.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_net as base  # noqa: E402

ARMS = base.ARMS
TRAIN_ROUNDS, GRAD_ROUNDS = base.TRAIN_ROUNDS, base.GRAD_ROUNDS
LR, WD, WARMUP = base.LR, base.WD, base.WARMUP
tensors, ce_and_exact, train_loss = base.tensors, base.ce_and_exact, base.train_loss
Practice = base.Practice
QK = 64


class Net(base.Net):
    WINDOW = 8

    def __init__(self, arm):
        super().__init__(arm)                 # every loop / plain parameter is created (and seeded) here first
        if arm == "loop":
            d = ARMS[arm]["d"]
            self.hq, self.hk = nn.Linear(d, QK), nn.Linear(d, QK)
            self.ho = nn.Linear(d, d)
            nn.init.zeros_(self.ho.weight)
            nn.init.zeros_(self.ho.bias)
        self.attn_record = None               # diagnostics only

    def read_history(self, h, hist):
        """h [B,T,d]; hist list of earlier states (newest last, at most WINDOW kept). Returns R [B,T,d]."""
        past = torch.stack(hist[-self.WINDOW:], 2)                               # [B,T,W',d]
        q, k = self.hq(h).unsqueeze(2), self.hk(past)                            # [B,T,1,QK], [B,T,W',QK]
        a = torch.softmax((q * k).sum(-1) / math.sqrt(QK), dim=-1)               # [B,T,W']
        if self.attn_record is not None:
            self.attn_record.append(a.detach())
        return self.ho((a.unsqueeze(-1) * past).sum(2))

    def hstep(self, h, e, dr, dc, hist):
        z = h + e + self.read_history(h, hist)
        for b in self.blocks:
            z = b(z, dr, dc)
        return self.ln_state(z)

    def forward(self, tokens, positions):
        if self.arm == "plain":
            return [self.plain_forward(tokens, positions)], []
        e, (dr, dc) = self.embed(tokens, positions)
        h = torch.zeros_like(e)
        hist, cells, stops = [h], [], []
        for _ in range(48):
            h = self.hstep(h, e, dr, dc, hist)
            hist.append(h)
            cell, stop = self.read(h)
            cells.append(cell)
            stops.append(stop)
        return cells, stops

    def loop_train(self, tokens, slot, n_free, n_grad):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        hist = [h]
        with torch.no_grad():
            for _ in range(n_free):
                h = self.hstep(h, e.detach(), dr, dc, hist)
                hist.append(h)
        h = h.detach()
        hist = [x.detach() for x in hist[-self.WINDOW:]]
        outs = []
        for _ in range(n_grad):
            h = self.hstep(h, e, dr, dc, hist)
            hist.append(h)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, n):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        hist, preds, qs = [h], [], []
        for _ in range(n):
            h = self.hstep(h, e, dr, dc, hist)
            hist.append(h)
            hist = hist[-self.WINDOW:]
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)

    @torch.no_grad()
    def attention_stats(self, tokens, positions, n=48):
        """Mean attention weight on the newest state and on the older ones, per round (diagnostic; the control prints 1.0 on newest)."""
        self.attn_record = []
        try:
            self.loop_rounds(tokens, positions, n)
            rec = self.attn_record
        finally:
            self.attn_record = None
        return {"newest_weight_by_round": [round(float(a[..., -1].mean()), 4) for a in rec],
                "entries_by_round": [int(a.shape[-1]) for a in rec]}


class Practice(base.Practice):
    """claude_fewex_net.Practice (same recipe, optimizer, schedule, RNG streams, step) with this module's Net."""
    NET = None                                # the control sets its own Net

    def __init__(self, arm, seed, total_steps):
        super().__init__(arm, seed, total_steps)          # builds the loop's own Net, then it is replaced under the same seed
        torch.manual_seed(seed)
        self.net = (self.NET or Net)(arm)
        self.opt = torch.optim.AdamW(self.net.parameters(), lr=LR, weight_decay=WD, betas=(0.9, 0.95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(
            self.opt, lambda i: min(1, (i + 1) / WARMUP) * 0.5 * (1 + math.cos(math.pi * min(i, total_steps) / total_steps)))


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net


def describe():
    h, loop = Net("loop"), base.Net("loop")
    return {"stored": h.weight_count(), "loop_stored": loop.weight_count(), "extra": h.weight_count() - loop.weight_count(), "window": Net.WINDOW}
