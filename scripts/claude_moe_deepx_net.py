#!/usr/bin/env python3
"""Addendum plug-in: deep experts (each expert is a small multi-layer MLP) for the sparse-MoE loop.

Ben asked for it (2026-09-29 11:13 UTC): "experts with 4 and 8 hidden layers each, on the many-layer reasoner".
It is a NEW file; the sealed claude_moe_deep_net.py / _run.py / _report.py are not edited. Importing this module
patches the sealed module in memory: it adds two configs and swaps in DeepMoE, which is exactly the sealed MoE
when the config has no `xl` key (or xl = 1).

One change against the main entry L8-E64 (8 layers per round, 64 routed experts, top 8 + 1 shared):
  every routed expert has `xl` hidden layers instead of one. Hidden width is cut so the stored FFN weights per
  expert stay within 1.1% of the main entry's (64 wide, one hidden layer = 33,024 weights):
    L8-E64-X4: xl = 4, hidden 49    L8-E64-X8: xl = 8, hidden 41
  Expert = GELU(W1 x), then (xl - 1) residual blocks h = h + GELU(Wm h), then W2 h. The residual keeps an
  8-deep expert trainable at the default init (a plain 8-deep GELU stack shrinks its signal at every layer);
  the mid weights start scaled by 1/sqrt(xl - 1). Shared expert, router, losses, layers, rounds: unchanged.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_moe_deep_net as M  # noqa: E402

_Sealed = M.MoE

# name -> config. per-expert weights = d*h + h + (xl-1)*(h*h + h) + h*d + d
DEEPX = {
    "L8-E64-X4": dict(kind="moe", layers=8, experts=64, top_k=8, shared=1, hidden=49, xl=4),
    "L8-E64-X8": dict(kind="moe", layers=8, experts=64, top_k=8, shared=1, hidden=41, xl=8),
}


def expert_weights(h, xl, d=M.D_MODEL):
    return d * h + h + (xl - 1) * (h * h + h) + h * d + d


class DeepMoE(_Sealed):
    def __init__(self, d, experts, top_k, shared, hidden, out_scale):
        super().__init__(d, experts, top_k, shared, hidden, out_scale)
        self.xl = int(M.cfg().get("xl", 1))
        if self.xl > 1:
            m = self.xl - 1
            self.wm = nn.Parameter(torch.empty(m, experts, hidden, hidden))
            self.bm = nn.Parameter(torch.empty(m, experts, hidden))
            for i in range(m):
                for e in range(experts):
                    M._linear_init_(self.wm[i, e], self.bm[i, e], hidden, 1 / math.sqrt(m))

    # the hidden stack of one expert, on a padded [E, C, hidden] buffer or on one [n, hidden] slice
    def _mid_padded(self, h):
        for i in range(self.xl - 1):
            h = h + F.gelu(torch.baddbmm(self.bm[i].unsqueeze(1), h, self.wm[i]))
        return h

    def _mid_slice(self, h, e):
        for i in range(self.xl - 1):
            h = h + F.gelu(torch.addmm(self.bm[i, e], h, self.wm[i, e]))
        return h

    def forward(self, x):
        if self.xl == 1:
            return super().forward(x)
        shape = x.shape
        flat = x.reshape(-1, shape[-1])
        n_tok, dev = flat.shape[0], flat.device
        logits = self.router(flat).float()
        probs = logits.softmax(-1)
        top_p, top_i = probs.topk(self.k, dim=-1)
        gate = top_p / top_p.sum(-1, keepdim=True)
        d = flat.shape[1]
        e_flat = top_i.reshape(-1)
        order = torch.argsort(e_flat, stable=True)
        counts = torch.bincount(e_flat, minlength=self.n)
        x_rep = flat.unsqueeze(1).expand(n_tok, self.k, d).reshape(-1, d)
        cap = int(counts.max())
        if self.path == "padded" or (self.path == "auto" and dev.type != "cpu" and self.n * cap <= 2 * e_flat.numel()):
            e_sorted = e_flat[order]
            starts = torch.cumsum(counts, 0) - counts
            slot = torch.empty_like(order)
            slot[order] = e_sorted * cap + torch.arange(order.numel(), device=dev) - starts[e_sorted]
            buf = flat.new_zeros(self.n * cap, d).index_copy(0, slot, x_rep).view(self.n, cap, d)
            h = F.gelu(torch.baddbmm(self.b1.unsqueeze(1), buf, self.w1))
            h = self._mid_padded(h)
            y = torch.baddbmm(self.b2.unsqueeze(1), h, self.w2)
            y = y.reshape(-1, d).index_select(0, slot)
        else:
            xs = x_rep.index_select(0, order)
            ys = [torch.addmm(self.b2[e], self._mid_slice(F.gelu(torch.addmm(self.b1[e], seg, self.w1[e])), e), self.w2[e])
                  for e, seg in enumerate(xs.split(counts.tolist())) if seg.shape[0]]
            inv = torch.empty_like(order)
            inv[order] = torch.arange(order.numel(), device=dev)
            y = torch.cat(ys).index_select(0, inv)
        y = y.view(n_tok, self.k, d)
        out = (y * gate.unsqueeze(-1).to(y.dtype)).sum(1) + self.shared(flat)
        if torch.is_grad_enabled():
            f = counts.float() / e_flat.numel()
            self.aux.append(self.n * (f * probs.mean(0)).sum())
            self.z.append(torch.logsumexp(logits, -1).pow(2).mean())
        if self.trace is not None:
            self.trace.append(top_i.detach().to(torch.int16).cpu())
        return out.view(shape)


M.CFGS.update(DEEPX)
M.MoE = DeepMoE


def _active_count(self):
    """Weights used for one cell in one round: the sealed count, plus the deep experts' extra layers (only k of n used)."""
    if self.arm == "plain":
        return self.weight_count()
    unused = 0
    for m in self.moes():
        per = m.w1[0].numel() + m.b1[0].numel() + m.w2[0].numel() + m.b2[0].numel()
        if getattr(m, "xl", 1) > 1:
            per += m.wm[:, 0].numel() + m.bm[:, 0].numel()
        unused += (m.n - m.k) * per
    return self.weight_count() - unused


M.Net.active_count = _active_count
