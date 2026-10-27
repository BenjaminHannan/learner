#!/usr/bin/env python3
"""Rung 2 of design 47 -- the frame head over the borrowed SciBERT encoder (arm C).

    FrameEars = fable_ears47_encoder.load(snapshot)  +  our heads (< 1 M params)

Heads (spec 47 §2): act[5], relation[N_REL], subject start/end pointers over input
positions, object start/end pointers, direction[2], flags[6 sigmoids].  One temperature
per scored head, fitted on CAL after training (rung-1 B.3/B.5 rule).  confidence at decode
= min over temperature-scaled head probabilities (doc 43 §B.5).
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

N_ACTS = 5
N_FLAGS = 6
N_DIR = 2
POINTER_Q = 4                      # subj start, subj end, obj start, obj end
HID = 256
N_TEMPS = 6                        # act, rel, subj, obj, dir, (spare)


class FrameEars(nn.Module):
    def __init__(self, encoder, n_rel: int, freeze_layers: int = 0):
        super().__init__()
        self.enc = encoder
        d = encoder.d
        self.n_rel = n_rel
        if freeze_layers:
            for layer in self.enc.layers[:freeze_layers]:
                for p in layer.parameters():
                    p.requires_grad = False
        self.drop = nn.Dropout(0.1)
        self.pool = nn.Linear(d, HID)
        self.act = nn.Linear(HID, N_ACTS)
        self.rel = nn.Linear(HID, n_rel)
        self.direction = nn.Linear(HID, N_DIR)
        self.flags = nn.Linear(HID, N_FLAGS)
        self.ptr_q = nn.Parameter(torch.randn(POINTER_Q, d) / math.sqrt(d))
        self.register_buffer("temps", torch.ones(N_TEMPS))

    def forward(self, ids, mask, use_temp: bool = False):
        x = self.enc(ids, mask)                       # [B,T,d]
        b, t, d = x.shape
        neg = -1e4                                    # safe in fp32/bf16/fp16 (finfo.min overflows bf16)
        denom = mask.sum(1, keepdim=True).clamp(min=1)
        g = self.drop(F.gelu(self.pool((x * mask.unsqueeze(-1)).sum(1) / denom)))
        T = self.temps if use_temp else torch.ones_like(self.temps)
        # pointer logits: position 0 ([CLS]) stays allowed = "absent"; [SEP]/pad forbidden
        # (mask already excludes pad; additionally forbid the last real position = [SEP])
        pl = torch.einsum("qd,btd->bqt", self.ptr_q, x)          # [B,4,T]
        last_idx = (mask.sum(1).long() - 1).clamp(min=0)         # [SEP] position
        pl = pl.masked_fill(~mask.unsqueeze(1), neg)
        sep = torch.zeros(b, t, dtype=torch.bool, device=x.device)
        sep[torch.arange(b, device=x.device), last_idx] = True
        pl = pl.masked_fill(sep.unsqueeze(1), neg)
        pl = pl / torch.stack([T[2], T[2], T[3], T[3]]).view(1, POINTER_Q, 1)
        return {"act": self.act(g) / T[0], "rel": self.rel(g) / T[1],
                "direction": self.direction(g) / T[4], "flags": self.flags(g),
                "ptr": pl}                                            # [B,4,T]


def loss_fn(out, tgt):
    ce = F.cross_entropy
    loss = ce(out["act"], tgt["act"]) + ce(out["rel"], tgt["rel"])
    loss = loss + ce(out["direction"], tgt["dir"])
    loss = loss + F.binary_cross_entropy_with_logits(out["flags"], tgt["flags"])
    pl = out["ptr"]                                                    # [B,4,T]
    for k, key in enumerate(("subj", "subj", "obj", "obj")):
        loss = loss + ce(pl[:, k], tgt[key][:, k % 2])
    return loss


def n_params(m):
    return sum(p.numel() for p in m.parameters())


def n_params_trainable(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)
