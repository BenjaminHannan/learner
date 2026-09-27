#!/usr/bin/env python3
"""xfer-1 nets and practice (research-loop thread, 2026-09-27). EDITABLE by the research loop; a change here re-runs
practice (the bench caches practised nets by this file's hash).

Base = the rsn-358i3 design (the loop design with a verified PASS against its plain twin; memory rsn-358i3-pass), made
small for CPU and with ONE difference Ben asked for: no kind embedding. A net sees only the puzzle's tokens and which
cells to fill, never a caller-given kind (Ben 11:34 09-27).
  plain  8 different layers, width 64, one pass.
  loop   2 layers, width 128, applied round after round; the puzzle is re-added every round; a stop head guesses
         after every round whether the answer is fully right. Trained with a random 1-16 rounds, loss on the last 1-6.
Both: attention bias from the row and column offset between two cells (clipped at 4); half the heads see only cells
within 1 column (358i). Practice: AdamW lr 1e-3, weight decay 0.1, 200-step warm-up then cosine, clip 1.0.
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
import claude_rsn358a_envs as E  # noqa: E402  (vocabulary)

ARMS = {"plain": dict(d=64, layers=8, heads=4), "loop": dict(d=128, layers=2, heads=4)}
CLIP, WINDOW = 4, 1
TRAIN_ROUNDS, GRAD_ROUNDS = 16, 6
LR, WD, WARMUP = 1e-3, 0.1, 200


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
        narrow[: self.h // 2] = True
        bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        c = ARMS[arm]
        self.arm, d = arm, c["d"]
        self.tok = nn.Embedding(E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        self.blocks = nn.ModuleList(Block(d, c["heads"]) for _ in range(c["layers"]))
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, E.VOCAB)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    @staticmethod
    def offsets(H, W, device):
        r = torch.arange(H, device=device).repeat_interleave(W)
        c = torch.arange(W, device=device).repeat(H)
        dr = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dc = (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP
        return dr, dc

    def embed(self, tokens, slot):
        B, H, W = tokens.shape
        return self.tok(tokens.view(B, -1)) + self.slot(slot.view(B, -1)), self.offsets(H, W, tokens.device)

    def step(self, h, e, dr, dc):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc)
        return self.ln_state(z)

    def read(self, h):
        z = self.ln_out(h)
        logits = self.head(z)
        q = self.halt(z.mean(1)).squeeze(-1) if self.arm == "loop" else None
        return logits, q

    def plain_forward(self, tokens, slot):
        h, (dr, dc) = self.embed(tokens, slot)
        for b in self.blocks:
            h = b(h, dr, dc)
        return self.read(h)[0]

    def loop_train(self, tokens, slot, n_free, n_grad):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), dr, dc)
        h = h.detach()
        outs = []
        for _ in range(n_grad):
            h = self.step(h, e, dr, dc)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, n):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        preds, qs = [], []
        for _ in range(n):
            h = self.step(h, e, dr, dc)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)       # [B, n, T], [B, n]


def tensors(items):
    t = torch.tensor([it.tokens for it in items])
    s = torch.tensor([it.slot for it in items])
    y = torch.tensor([it.target for it in items])
    return t, s, y


def ce_and_exact(logits, s, y):
    B = s.shape[0]
    s, y = s.view(B, -1).bool(), y.view(B, -1)
    ce = F.cross_entropy(logits.float()[s], y[s])
    exact = ((logits.argmax(-1) == y) | ~s).all(1).float()
    return ce, exact


def train_loss(net, items, round_rng):
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
    """sums and grids practice; the bench hands it batches and saves the net at the end"""

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
