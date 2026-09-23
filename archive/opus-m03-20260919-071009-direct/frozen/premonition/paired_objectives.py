"""H1: paired sensitivity/invariance terms on verified triplets (optional; OFF by default). Milestone 3.

Spec: design/research/final-sweep-2026-09-19/03-learning.md, "H1". For each triplet (x, u, v) of the same question
with original answer a (kept by the irrelevant sibling u) and changed answer b (of the relevant sibling v):

    delta  = log[p_x(a) / p_x(b)] - log[p_v(a) / p_v(b)]
    extra  = js_weight * JS(p_x, p_u) + margin_weight * max(0, margin - delta)

added to the ORDINARY answer cross-entropy that every example (x, u and v, every question) keeps. p is the model's
distribution at the FIRST answer position (the declared single-token-answer diagnostic). The essential comparator is
the same triplets and minibatches with the cross-entropy alone (`H1Config()` = off).

Numerics: log_softmax in float32; JS computed in log space as 0.5 KL(p||m) + 0.5 KL(q||m) with
log m = logsumexp(log p, log q) - log 2, so every term is finite for finite logits (checked; non-finite logits are
refused). Log-odds use log-probabilities, never divided probabilities. A per-triplet `mask` removes triplets from
both terms (zero gradient), normalising over the kept ones.

Gradient boundary: these terms train whatever produces the answer distribution (values, reader, decoder, Think). They
cannot reach detached top-k card selection or the binary ASK decision; any retrieval change would be indirect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F

VERSION = 1


@dataclass(frozen=True)
class H1Config:
    enabled: bool = False
    js_weight: float = 1.0          # lambda
    margin_weight: float = 1.0      # mu
    margin: float = 1.0             # m, in nats of log-odds

    def identity(self) -> dict:
        return {**asdict(self), "module": "premonition/paired_objectives.py", "version": VERSION,
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def _log_probs(logits: torch.Tensor) -> torch.Tensor:
    logits = logits.float()
    if not bool(torch.isfinite(logits).all()):
        raise ValueError("H1 needs finite answer logits")
    return F.log_softmax(logits, dim=-1)


def js_divergence(logp: torch.Tensor, logq: torch.Tensor) -> torch.Tensor:
    """[N] Jensen-Shannon divergence (nats) between rows of two log-probability tensors [N, V]."""
    logm = torch.logsumexp(torch.stack([logp, logq]), dim=0) - math.log(2.0)
    kl_pm = (logp.exp() * (logp - logm)).sum(-1)
    kl_qm = (logq.exp() * (logq - logm)).sum(-1)
    return (0.5 * (kl_pm + kl_qm)).clamp_min(0.0)


def log_odds_change(logp_x: torch.Tensor, logp_v: torch.Tensor, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """[N] delta = (log p_x(a) - log p_x(b)) - (log p_v(a) - log p_v(b))."""
    pick = lambda logp, token: logp.gather(1, token.view(-1, 1)).squeeze(1)
    return (pick(logp_x, a) - pick(logp_x, b)) - (pick(logp_v, a) - pick(logp_v, b))


def h1_terms(logits_x: torch.Tensor, logits_u: torch.Tensor, logits_v: torch.Tensor, a: torch.Tensor,
             b: torch.Tensor, config: H1Config, mask: Optional[torch.Tensor] = None) -> dict:
    """First-answer-position logits [T, V] of q* in x, u, v; answers a, b [T]. Returns the weighted extra loss
    ('loss', zero when disabled or nothing is kept) and detached diagnostics."""
    if bool((a == b).any()):
        raise ValueError("a relevant pair needs b != a")
    keep = torch.ones_like(a, dtype=torch.bool) if mask is None else mask.bool()
    lx, lu, lv = _log_probs(logits_x), _log_probs(logits_u), _log_probs(logits_v)
    js = js_divergence(lx, lu)
    delta = log_odds_change(lx, lv, a, b)
    hinge = F.relu(config.margin - delta)
    kept = int(keep.sum())
    zero = logits_x.sum() * 0.0
    if not config.enabled or kept == 0:
        loss = zero
    else:
        weight = keep.float() / kept
        loss = config.js_weight * (js * weight).sum() + config.margin_weight * (hinge * weight).sum()
    return {"loss": loss, "js": js.detach(), "delta": delta.detach(), "hinge": hinge.detach(), "kept": kept,
            "active_margin": int(((delta < config.margin) & keep).sum())}


def triplet_metrics(first_x: torch.Tensor, first_u: torch.Tensor, first_v: torch.Tensor, a: torch.Tensor,
                    b: torch.Tensor) -> dict:
    """Per-triplet correctness from predicted FIRST answer tokens. Stability alone never counts: the invariant pair
    needs x AND u correct, the relevant pair x AND v correct, so a constant answer cannot pass both."""
    x_ok, u_ok, v_ok = first_x == a, first_u == a, first_v == b
    return {"x_correct": x_ok, "u_correct": u_ok, "v_correct": v_ok,
            "invariant_both_correct": x_ok & u_ok, "relevant_both_correct": x_ok & v_ok,
            "all_three_correct": x_ok & u_ok & v_ok,
            "prediction_changed_on_relevant": first_x != first_v, "prediction_kept_on_irrelevant": first_x == first_u}


__all__ = ["H1Config", "VERSION", "h1_terms", "js_divergence", "log_odds_change", "triplet_metrics"]
