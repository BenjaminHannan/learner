#!/usr/bin/env python3
"""Exp 119g — relation-conditioned span pointers (Muse BUILD).

THE ONE CHANGE vs 119f (model only; data, recipe, seeds, scorer marks logic
unchanged): the four span-pointer queries are conditioned on the relation.

    q_r = ptr_q + U(rel_emb[r]),   U initialised to ZERO.

At init U == 0 so q_r == ptr_q for every r: the model IS the old FrameEars
(proved by scripts/fable_ears119g_smoke.py: max abs diff 0.0 on 5 rows).
In training the gold relation is teacher-forced
(``rel_override=batch["rel"]``); at decode time each candidate relation gets
its own subject/object spans (see fable_ears119g_score.decode_multirel),
reusing S47.decode for K=1 and S47.verdict_single per frame.

Why: 119f diagnosis (artifacts/fable-ears119f-20260922/DIRECTOR-diagnosis.md):
the old head has ONE fact slot per sentence (fixed ptr_q); real sentences
state 2-3 facts and the date or nationality wins the slot. Conditioning the
pointers on the relation gives each relation its own slot.

Additive only: FrameEars imported read-only and subclassed, never edited.
"""
from __future__ import annotations

import torch
import torch.nn as nn

import fable_ears47_model as M

D_REL = 64  # relation-embedding width (small on purpose: U is the only path)


class RelCondEars(M.FrameEars):
    def __init__(self, encoder, n_rel: int, freeze_layers: int = 0,
                 d_rel: int = D_REL):
        super().__init__(encoder, n_rel, freeze_layers=freeze_layers)
        self.rel_emb = nn.Embedding(n_rel, d_rel)
        self.U = nn.Linear(d_rel, M.POINTER_Q * encoder.d, bias=False)
        nn.init.zeros_(self.U.weight)  # U=0 at init -> identical to FrameEars

    def cond_queries(self, rel_ids: torch.Tensor) -> torch.Tensor:
        """[B,4,d] pointer queries for the given relation ids."""
        b = rel_ids.shape[0]
        d = self.enc.d
        return self.ptr_q.unsqueeze(0) + self.U(
            self.rel_emb(rel_ids)).view(b, M.POINTER_Q, d)

    def forward(self, ids, mask, use_temp: bool = False,
                rel_override: torch.Tensor | None = None):
        import torch.nn.functional as F
        x = self.enc(ids, mask)                       # [B,T,d]
        b, t, d = x.shape
        neg = -1e4
        denom = mask.sum(1, keepdim=True).clamp(min=1)
        g = self.drop(F.gelu(self.pool((x * mask.unsqueeze(-1)).sum(1) / denom)))
        T = self.temps if use_temp else torch.ones_like(self.temps)
        if rel_override is None:
            q = self.ptr_q.unsqueeze(0).expand(b, M.POINTER_Q, d)
        else:
            q = self.cond_queries(rel_override)
        pl = torch.einsum("bqd,btd->bqt", q, x)       # [B,4,T]
        last_idx = (mask.sum(1).long() - 1).clamp(min=0)
        pl = pl.masked_fill(~mask.unsqueeze(1), neg)
        sep = torch.zeros(b, t, dtype=torch.bool, device=x.device)
        sep[torch.arange(b, device=x.device), last_idx] = True
        pl = pl.masked_fill(sep.unsqueeze(1), neg)
        pl = pl / torch.stack([T[2], T[2], T[3], T[3]]).view(1, M.POINTER_Q, 1)
        return {"act": self.act(g) / T[0], "rel": self.rel(g) / T[1],
                "direction": self.direction(g) / T[4], "flags": self.flags(g),
                "ptr": pl}


def conditioned_ptr_probs(model: RelCondEars, ids, mask,
                           rel_ids: torch.Tensor,
                           use_temp: bool = True) -> torch.Tensor:
    """Softmaxed conditioned pointer probs [B,4,T] for rel_ids (no grad)."""
    with torch.no_grad():
        o = model(ids, mask, use_temp=use_temp, rel_override=rel_ids)
    return torch.softmax(o["ptr"], -1)
