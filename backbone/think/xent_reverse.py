"""Reverse KL with the Softmax Cancellation fix (Barron et al. 2026, arXiv 2610.31642), for rlaif/rollout.py's _lp_kl.

rlaif computes KL(q_view || sg p_other) = sum_j q_j (log q_j - log p_j) with the gradient on the VIEW side (the opposite slot to
xent.fixed_kl, which puts the gradient on the second distribution). Plain autograd gives q*(delta + 1) - q*sum(q*(delta + 1)):
the "+1" terms only cancel up to rounding (sum(q) != 1 in fp32), so the gradient is ~q*1e-7 when the two views agree exactly.
Here the backward is q * (D - E_q[D]) with D = z_view - z_other in raw logit space, which is exactly 0 when the logits are equal.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


class _FixedReverseKL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, zv, zo):
        dt = torch.float64 if zv.dtype == torch.float64 else torch.float32
        lq, lp = F.log_softmax(zv.to(dt), -1), F.log_softmax(zo.to(dt), -1)
        out = (lq.exp() * (lq - lp)).sum(-1)
        ctx.save_for_backward(zv, zo)
        return out

    @staticmethod
    def backward(ctx, grad):
        zv, zo = ctx.saved_tensors
        dt = torch.float64 if zv.dtype == torch.float64 else torch.float32
        s, t = zv.to(dt), zo.to(dt)
        q = F.softmax(s, -1)
        d = s - t
        d = d - d.max(-1, keepdim=True).values  # shift-free; keeps exp-free D small and exact 0 when s == t
        g = q * (d - (q * d).sum(-1, keepdim=True)) * grad[..., None]
        return g.to(zv.dtype), None


def fixed_reverse_kl(view_logits, other_logits):
    """Per-row KL(softmax(view) || softmax(other)), other detached; exactly 0 gradient when the two logit tensors are equal."""
    return _FixedReverseKL.apply(view_logits, other_logits.detach())
