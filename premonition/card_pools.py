"""Prepared by the overnight run ovn-20260918-235851 for the NEXT session. Not yet trained or used in any compared
experiment; review before use (handoff: reviews/opus-next-2026-09-19-two-pool-cards.md).

The problem it targets (measured overnight, eval-only probes):
- D's CardWriter pools each line's reader states with ONE softmax score and derives both the retrieval key and the
  card value from that single pooled vector.
- Trained pools concentrate 70-98% of their mass on one or two tokens:
  - answer-only training puts 0.979 on the value token, so the card loses the person;
  - retrieval-dominated training puts 0.71 on the relation and 0.02 on the value, so the card loses the value.
- The reader states themselves keep both facts (2304/2304).

Variants (every other module is D, or D-card-bypass for the "+" names):
- `D-two-pool`: `pool` scores the tokens that build the KEY, and a second `pool_value` (Linear(d, 1), +d+1
  parameters) scores the tokens that build the VALUE. `pool_value` starts as an exact copy of `pool`, so at
  initialisation the model computes exactly what the same-seed single-pool model computes. Prior art: key and value
  from different encodings (Key-Value Memory Networks, Miller et al. 2016); several seed vectors pooling one set
  (PMA, Lee et al. 2019); search/retrieval decoupling (Compositional Attention, Mittal et al. 2022).
- `D-mean-pool`: uniform weights over each line's tokens; no learned pooling, so nothing can concentrate. The
  simplest competitor. `pool` is kept but unused.

Construction preserves the same-seed baseline exactly: the base model is built and initialised first, and the new
writer is built inside `torch.random.fork_rng` and then loaded from the base writer's state. The global random
stream after construction is therefore identical to the baseline's.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import torch
import torch.nn as nn

from premonition.answer_path import CardBypassMini
from premonition.config import MiniConfig
from premonition.model import CardWriter, PremonitionMini
from premonition.store import CardStore

TWO_POOL = "D-two-pool"
MEAN_POOL = "D-mean-pool"
TWO_POOL_BYPASS = "D-card-bypass+two-pool"
MEAN_POOL_BYPASS = "D-card-bypass+mean-pool"
VARIANTS = (TWO_POOL, MEAN_POOL, TWO_POOL_BYPASS, MEAN_POOL_BYPASS)


def source_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def pool_lines(hidden: torch.Tensor, batch, score: torch.Tensor) -> torch.Tensor:
    """CardWriter's masked per-line softmax pool (premonition/model.py), for any [visits, width] score.
    Returns [visits, lines, d]."""
    visits, lines = batch.line_start.shape
    real = batch.line_of >= 0
    slot = (batch.line_of.clamp_min(0)
            + lines * torch.arange(visits, device=hidden.device).unsqueeze(1))[real]
    score = score.float()[real]
    peak = torch.full((visits * lines,), -math.inf, device=hidden.device)
    peak = peak.scatter_reduce(0, slot, score.detach(), "amax").clamp_min(-1e30)
    weight = torch.exp(score - peak[slot])
    total = torch.zeros(visits * lines, device=hidden.device).index_add(0, slot, weight)
    weight = weight / total[slot]
    return torch.zeros(visits * lines, hidden.shape[-1], device=hidden.device).index_add(
        0, slot, weight.unsqueeze(-1) * hidden[real].float()).view(visits, lines, -1)


class TwoPoolCardWriter(CardWriter):
    """k = normalize(W_k pool_k(line)), v = W_v pool_v(line): the key and value pools are separate."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        self.pool_value = nn.Linear(config.d_model, 1)

    def forward(self, hidden: torch.Tensor, batch) -> CardStore:
        keyed = pool_lines(hidden, batch, self.pool(hidden).squeeze(-1))
        valued = pool_lines(hidden, batch, self.pool_value(hidden).squeeze(-1))
        return CardStore.write(self.key(keyed), self.value(valued), batch, self.null_key, self.null_value)


class MeanPoolCardWriter(CardWriter):
    """k and v from the uniform mean of the line's reader states (`pool` unused)."""

    def forward(self, hidden: torch.Tensor, batch) -> CardStore:
        pooled = pool_lines(hidden, batch, torch.zeros(hidden.shape[:2], device=hidden.device))
        return CardStore.write(self.key(pooled), self.value(pooled), batch, self.null_key, self.null_value)


def _swap_writer(model: PremonitionMini, cls: type) -> None:
    if model.writer is None:
        raise ValueError("card-pool variants need a card store (not D-noask)")
    with torch.random.fork_rng(devices=[]):
        writer = cls(model.config)
    missing, unexpected = writer.load_state_dict(model.writer.state_dict(), strict=False)
    if unexpected or any(name.split(".")[0] != "pool_value" for name in missing):
        raise RuntimeError(f"writer state mismatch: missing={missing}, unexpected={unexpected}")
    if isinstance(writer, TwoPoolCardWriter):
        writer.pool_value.load_state_dict(model.writer.pool.state_dict())
    model.writer = writer


class TwoPoolMini(PremonitionMini):
    variant_name = TWO_POOL

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        _swap_writer(self, TwoPoolCardWriter)


class MeanPoolMini(PremonitionMini):
    variant_name = MEAN_POOL

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        _swap_writer(self, MeanPoolCardWriter)


class TwoPoolBypassMini(CardBypassMini):
    variant_name = TWO_POOL_BYPASS

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        _swap_writer(self, TwoPoolCardWriter)


class MeanPoolBypassMini(CardBypassMini):
    variant_name = MEAN_POOL_BYPASS

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        _swap_writer(self, MeanPoolCardWriter)


CLASSES = {TWO_POOL: TwoPoolMini, MEAN_POOL: MeanPoolMini, TWO_POOL_BYPASS: TwoPoolBypassMini,
           MEAN_POOL_BYPASS: MeanPoolBypassMini}


def identity(variant: str, config: MiniConfig) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")
    pooling = "separate key and value pools" if "two-pool" in variant else "uniform line mean (no learned pool)"
    return {"variant": variant, "base_variant": config.variant, "purpose": "diagnostic",
            "adjustment": f"card writer: {pooling}", "reader_path": "card-bypass" if "+" in variant else "D",
            "module": "premonition/card_pools.py", "source_sha256": source_digest()}


__all__ = ["CLASSES", "MEAN_POOL", "MEAN_POOL_BYPASS", "MeanPoolBypassMini", "MeanPoolCardWriter", "MeanPoolMini",
           "TWO_POOL", "TWO_POOL_BYPASS", "TwoPoolBypassMini", "TwoPoolCardWriter", "TwoPoolMini", "VARIANTS",
           "identity", "pool_lines", "source_digest"]
