#!/usr/bin/env python3
"""Rung 1 of design 43 -- the three ear models.

  arm A  `tape`   : B.2 bank of callable skills on the tape + router (the design's ears)
  arm B  `bigru`  : B.6 same-size BiGRU tagger, same inputs, same heads (the yardstick)
  arm C  `names`  : arm A but out-of-lexicon words get their own hashed embedding rows
                    instead of collapsing to OPQ#k (the "names visible" control)

Nothing here reads a panel or a label; the heads are exactly B.3.
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

D_MODEL = 96
D_EMB = 48
N_FEATS = 10
N_PLACES = 12                 # -4..+4, FIRST, LAST, MEAN
RANK = 16
N_SKILLS = 24
N_STAGES = 4
N_ACTS = 15
N_FLAGS = 6
N_ITEMS = 4
N_SLOTS = 5
N_RELKEY = 41
HOP_EMB = 16
HOP_HID = 64
MAX_HOPS = 8
HASH_ROWS = 8192


class RMSNorm(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.g = nn.Parameter(torch.ones(d))

    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6) * self.g


def _places(x, mask):
    """x [B,T,d] -> [B,12,T,d]: nine relative shifts then FIRST, LAST, MEAN."""
    b, t, d = x.shape
    xm = x * mask.unsqueeze(-1)
    out = []
    for delta in range(-4, 5):
        if delta == 0:
            out.append(xm)
        elif delta < 0:
            pad = xm.new_zeros(b, -delta, d)
            out.append(torch.cat([pad, xm[:, :delta]], 1))
        else:
            pad = xm.new_zeros(b, delta, d)
            out.append(torch.cat([xm[:, delta:], pad], 1))
    first = xm[:, :1].expand(b, t, d)
    last_idx = (mask.sum(1).long() - 1).clamp(min=0)
    last = xm[torch.arange(b, device=x.device), last_idx].unsqueeze(1).expand(b, t, d)
    mean = (xm.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)).unsqueeze(1).expand(b, t, d)
    out += [first, last, mean]
    return torch.stack(out, 1)


class SkillBank(nn.Module):
    """K gated relative-transport skills, weight-tied across the stages (B.2)."""

    def __init__(self, k=N_SKILLS, d=D_MODEL, r=RANK, stages=N_STAGES):
        super().__init__()
        self.k, self.d, self.r, self.stages = k, d, r, stages
        self.a = nn.Parameter(torch.randn(k, N_PLACES) * 0.5)
        self.b = nn.Parameter(torch.randn(k, N_PLACES) * 0.5)
        s = 1.0 / math.sqrt(d)
        self.A = nn.Parameter(torch.randn(k, d, r) * s)
        self.B = nn.Parameter(torch.randn(k, d, r) * s)
        self.U = nn.Parameter(torch.randn(k, r, d) * (1.0 / math.sqrt(r)))
        self.G = nn.Parameter(torch.zeros(stages, k))
        self.norms = nn.ModuleList([RMSNorm(d) for _ in range(stages)])

    def forward(self, x, mask):
        b, t, d = x.shape
        for s in range(self.stages):
            p = _places(x, mask).reshape(b, N_PLACES, t * d)
            alpha = torch.softmax(10.0 * torch.tanh(self.a), -1)     # [K,12]
            beta = torch.softmax(10.0 * torch.tanh(self.b), -1)
            u = torch.einsum("kp,bpm->bkm", alpha, p).reshape(b, self.k, t, d)
            v = torch.einsum("kp,bpm->bkm", beta, p).reshape(b, self.k, t, d)
            u = u.permute(1, 0, 2, 3).reshape(self.k, b * t, d)
            v = v.permute(1, 0, 2, 3).reshape(self.k, b * t, d)
            h = torch.bmm(u, self.A) * torch.sigmoid(torch.bmm(v, self.B))   # [K,B*T,r]
            y = torch.bmm(h, self.U)                                          # [K,B*T,d]
            gate = torch.sigmoid(10.0 * torch.tanh(self.G[s])).view(self.k, 1, 1)
            x = self.norms[s](x + (y * gate).sum(0).view(b, t, d))
        return x * mask.unsqueeze(-1)


class BiGRUTrunk(nn.Module):
    def __init__(self, d=D_MODEL, hidden=54, layers=2):
        super().__init__()
        self.gru = nn.GRU(d, hidden, num_layers=layers, bidirectional=True,
                          batch_first=True)
        self.proj = nn.Linear(2 * hidden, d)
        self.norm = RMSNorm(d)

    def forward(self, x, mask):
        y, _ = self.gru(x)
        return self.norm(self.proj(y)) * mask.unsqueeze(-1)


class Ears(nn.Module):
    def __init__(self, vocab, arm="tape"):
        super().__init__()
        self.arm = arm
        rows = vocab + (HASH_ROWS if arm == "names" else 0)
        self.emb = nn.Embedding(rows, D_EMB)
        nn.init.normal_(self.emb.weight, std=0.5 / math.sqrt(D_EMB))
        self.in_map = nn.Linear(D_EMB + N_FEATS + 1, D_MODEL)
        self.trunk = BiGRUTrunk() if arm == "bigru" else SkillBank()
        self.act = nn.Linear(4 * D_MODEL, N_ACTS)
        self.flags = nn.Linear(4 * D_MODEL, N_FLAGS)
        self.items = nn.Linear(4 * D_MODEL, N_ITEMS)
        self.slot_q = nn.Parameter(torch.randn(N_SLOTS, 2, D_MODEL) / math.sqrt(D_MODEL))
        self.hop_emb = nn.Parameter(torch.randn(MAX_HOPS, HOP_EMB) * 0.5)
        self.hop_in = nn.Linear(HOP_EMB + D_MODEL + 4 * D_MODEL, HOP_HID)
        self.hop_start = nn.Linear(HOP_HID, D_MODEL)
        self.hop_end = nn.Linear(HOP_HID, D_MODEL)
        self.hop_stop = nn.Linear(HOP_HID, 1)
        self.relkey = nn.Linear(HOP_HID + D_MODEL, N_RELKEY)
        self.reltype = nn.Linear(HOP_HID + D_MODEL, 2)
        # one temperature per head, fitted on CAL afterwards (B.3); 1.0 until then
        self.register_buffer("temps", torch.ones(6))   # act, items, slot, hop, stop, relkey

    def encode_tape(self, ids, feats, pending, mask):
        e = self.emb(ids)
        z = torch.cat([e, feats, pending.unsqueeze(1).expand(-1, ids.shape[1]).unsqueeze(-1)],
                      -1)
        return self.trunk(self.in_map(z), mask)

    def forward(self, ids, feats, pending, mask, n_hops_run=4, use_temp=False):
        x = self.encode_tape(ids, feats, pending, mask)
        b, t, d = x.shape
        neg = torch.finfo(x.dtype).min
        mfill = (1 - mask).bool()
        denom = mask.sum(1, keepdim=True).clamp(min=1)
        mean = (x * mask.unsqueeze(-1)).sum(1) / denom
        mx = x.masked_fill(mfill.unsqueeze(-1), neg).max(1).values
        last_idx = (mask.sum(1).long() - 1).clamp(min=0)
        g = torch.cat([mean, mx, x[:, 0], x[torch.arange(b, device=x.device), last_idx]], -1)
        T = self.temps if use_temp else torch.ones_like(self.temps)
        out = {"act": self.act(g) / T[0], "flags": self.flags(g),
               "items": self.items(g) / T[1]}
        slot = torch.einsum("sqd,btd->sqbt", self.slot_q, x)
        slot = slot.permute(2, 0, 1, 3).masked_fill(mfill[:, None, None, :], neg)
        out["slot"] = slot / T[2]
        prev = x.new_zeros(b, d)
        hs, he, hk, ht, hstop = [], [], [], [], []
        for j in range(n_hops_run):
            h = F.gelu(self.hop_in(torch.cat([self.hop_emb[j].expand(b, HOP_EMB), prev, g], -1)))
            ls = torch.einsum("bd,btd->bt", self.hop_start(h), x).masked_fill(mfill, neg) / T[3]
            le = torch.einsum("bd,btd->bt", self.hop_end(h), x).masked_fill(mfill, neg) / T[3]
            rep = 0.5 * (torch.einsum("bt,btd->bd", torch.softmax(ls, -1), x)
                         + torch.einsum("bt,btd->bd", torch.softmax(le, -1), x))
            hr = torch.cat([h, rep], -1)
            hs.append(ls)
            he.append(le)
            hstop.append(self.hop_stop(h).squeeze(-1) / T[4])
            hk.append(self.relkey(hr) / T[5])
            ht.append(self.reltype(hr))
            prev = rep
        out["hop_start"] = torch.stack(hs, 1)
        out["hop_end"] = torch.stack(he, 1)
        out["stop"] = torch.stack(hstop, 1)
        out["relkey"] = torch.stack(hk, 1)
        out["reltype"] = torch.stack(ht, 1)
        return out


def loss_fn(out, tgt, n_hops_run=4):
    ce = F.cross_entropy
    loss = ce(out["act"], tgt["act"]) + ce(out["items"], tgt["n_items"])
    loss = loss + F.binary_cross_entropy_with_logits(out["flags"], tgt["flags"])
    b = out["act"].shape[0]
    sl = out["slot"]                                    # [B,5,2,T]
    sp = tgt["slot_ptr"]                                # [B,5,2]
    loss = loss + ce(sl.reshape(b * N_SLOTS * 2, -1), sp.reshape(-1))
    nh = tgt["n_hops"]
    for j in range(n_hops_run):
        live = (nh > j).float()
        stop_t = (nh == j).float()
        loss = loss + F.binary_cross_entropy_with_logits(out["stop"][:, j], stop_t)
        if live.sum() > 0:
            w = live / live.sum().clamp(min=1)
            for key, t in (("hop_start", tgt["hop_ptr"][:, j, 0]),
                           ("hop_end", tgt["hop_ptr"][:, j, 1])):
                loss = loss + (ce(out[key][:, j], t, reduction="none") * w).sum()
            loss = loss + (ce(out["relkey"][:, j], tgt["hop_key"][:, j],
                              reduction="none") * w).sum()
            loss = loss + (ce(out["reltype"][:, j], tgt["hop_type"][:, j],
                              reduction="none") * w).sum()
    return loss


def n_params(m):
    return sum(p.numel() for p in m.parameters())


if __name__ == "__main__":
    for arm in ("tape", "bigru", "names"):
        m = Ears(1303, arm)
        trunk = sum(p.numel() for p in m.trunk.parameters())
        print(f"{arm:6s} total {n_params(m):8,d}  trunk {trunk:7,d}  "
              f"emb {m.emb.weight.numel():7,d}")
