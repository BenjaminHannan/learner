"""Overnight (run ovn-20260918-235851) diagnostic variant of D: the row-centred Think update.

D-think-centered: each Think loop's update has its mean over the question's VALID rows removed,

    update = Think(x, step) - x;   x_next = x + (update - mean_{valid rows}(update))

so a loop cannot add one shared vector to every row (the shortcut measured in milestone 2: a row-shared update of
norm ~8.7 with a row-to-row spread of ~0.3). Row-specific updates, the input's own mean, the loop-step embedding
inside the layers and every other module are unchanged. Parameter-free. Closest prior art: PairNorm's centring
across graph nodes (Zhao & Akoglu, ICLR 2020), applied here to the recurrent update rather than to the features,
without PairNorm's rescaling. Baseline D and the milestone-2 variants (premonition/answer_path.py) are untouched.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from premonition.config import MiniConfig
from premonition.model import PremonitionMini, Think

THINK_CENTERED = "D-think-centered"
VARIANTS = (THINK_CENTERED,)


def source_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def identity(variant: str, config: MiniConfig) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")
    return {"variant": variant, "base_variant": config.variant, "purpose": "diagnostic",
            "adjustment": "Think update centred over valid rows (no shared per-loop update)",
            "module": "premonition/ovn_variants.py", "source_sha256": source_digest()}


class CenteredThink(Think):
    def forward(self, x: torch.Tensor, valid: torch.Tensor, step: int) -> torch.Tensor:
        update = super().forward(x, valid, step) - x
        weight = valid.unsqueeze(-1).to(update.dtype)
        mean = (update * weight).sum(1, keepdim=True) / weight.sum(1, keepdim=True).clamp_min(1.0)
        return x + update - mean


class ThinkCenteredMini(PremonitionMini):
    variant_name = THINK_CENTERED

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        centred = CenteredThink(config)
        centred.load_state_dict(self.think.state_dict())
        self.think = centred


CLASSES = {THINK_CENTERED: ThinkCenteredMini}


def from_base(variant: str, base: PremonitionMini) -> PremonitionMini:
    model = CLASSES[variant](base.config)
    model.load_state_dict(base.state_dict())          # identical parameter set: strict
    return model


__all__ = ["CLASSES", "CenteredThink", "THINK_CENTERED", "ThinkCenteredMini", "VARIANTS", "from_base",
           "identity", "source_digest"]
