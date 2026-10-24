"""Fixed cross-entropy (Barron, Gnanapragasam, Tschannen 2026, arXiv 2610.31642), used by every Think-1 arm.

Standard softmax cross-entropy has gradient p - onehot. Once the target margin m = -LSE_{j!=t}(z_j - z_t) passes ~17 in fp32,
sum(exp(z - max)) rounds to 1, p_t is exactly 1 and the target gradient (p_t - 1) is exactly 0 while the other entries
(p_j ~ 1e-8) stay non-zero, so the row no longer sums to 0 and the target logit is pushed by nothing. Here the loss is
softplus(-m) and the gradient is built from the other classes only: g_j = exp((z_j - z_t) - loss), g_t = -sum g_j.
The soft versions get the same treatment through delta = z_S - z_T (exactly 0 gradient when the student equals the teacher).
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def _compute_dtype(x):
    return torch.float64 if x.dtype == torch.float64 else torch.float32


def _reduce(v, reduction, n=None):
    if reduction == "none":
        return v
    if reduction == "sum":
        return v.sum()
    if reduction == "mean":
        return v.sum() / (v.shape[0] if n is None else max(n, 1))
    raise ValueError(f"unknown reduction {reduction!r}")


class _FixedCE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, logits, target, valid):
        z = logits.to(_compute_dtype(logits))
        t = target.masked_fill(~valid, 0)
        d = z - z.gather(1, t[:, None])
        d.scatter_(1, t[:, None], float("-inf"))
        loss = F.softplus(torch.logsumexp(d, 1)) * valid
        ctx.save_for_backward(logits, t, valid, loss)
        return loss

    @staticmethod
    def backward(ctx, grad):
        logits, t, valid, loss = ctx.saved_tensors
        z = logits.to(loss.dtype)
        d = z - z.gather(1, t[:, None])
        d.scatter_(1, t[:, None], float("-inf"))
        g = torch.exp(d - loss[:, None])  # other classes only; 0 at the target
        g.scatter_(1, t[:, None], -g.sum(1, keepdim=True))
        g = g * (grad * valid)[:, None]
        return g.to(logits.dtype), None, None


def fixed_cross_entropy(logits, target, ignore_index=-100, reduction="sum"):
    """logits [N,V], target [N]; rows with target == ignore_index give 0 loss and 0 grad (mean divides by the real rows)."""
    valid = target != ignore_index
    loss = _FixedCE.apply(logits, target, valid)
    return _reduce(loss, reduction, int(valid.sum()))


class _FixedSoft(torch.autograd.Function):
    @staticmethod
    def forward(ctx, zs, zt, kl):
        dt = _compute_dtype(zs)
        s, t = zs.to(dt), zt.to(dt)
        logp, logq = F.log_softmax(t, -1), F.log_softmax(s, -1)
        p = logp.exp()
        out = torch.where(p > 0, p * ((logp if kl else 0.0) - logq), torch.zeros_like(p)).sum(-1)
        ctx.save_for_backward(zs, zt)
        return out

    @staticmethod
    def backward(ctx, grad):
        zs, zt = ctx.saved_tensors
        dt = _compute_dtype(zs)
        s, t = zs.to(dt), zt.to(dt)
        p, q = F.softmax(t, -1), F.softmax(s, -1)
        delta = torch.where(p > 0, s - t, torch.zeros_like(s))
        d = delta - (p * delta).sum(-1, keepdim=True)
        sh = d - torch.log1p((p * torch.expm1(d)).sum(-1, keepdim=True))
        u = p * torch.expm1(sh)
        g = (u - q * u.sum(-1, keepdim=True)) * grad[..., None]
        return g.to(zs.dtype), None, None


def fixed_soft_cross_entropy(student_logits, teacher_logits, reduction="sum"):
    """-sum_j p_T,j log q_S,j per row, teacher detached; gradient w.r.t. the student is q - p computed without cancellation."""
    out = _FixedSoft.apply(student_logits, teacher_logits.detach(), False)
    return _reduce(out, reduction)


def fixed_kl(student_logits, teacher_logits, reduction="sum"):
    """KL(p_teacher || q_student) per row, teacher detached; exactly 0 gradient when the two logit tensors are equal."""
    out = _FixedSoft.apply(student_logits, teacher_logits.detach(), True)
    return _reduce(out, reduction)
