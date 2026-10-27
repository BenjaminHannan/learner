"""Milestone-2 diagnostic variants of D's answer path (reviews/opus-execution-02-answer-path.md).

Baseline D (`premonition.model.PremonitionMini`) is not changed. The two bounded adjustments are separate
subclasses with explicit names, never combined:

* D-think-gated: the whole Think update, loop-step embedding included, is gated by one learned scalar
  alpha that starts at zero: output = input + alpha * (Think(input, step) - input). At alpha = 0 every loop
  is the identity; Think's compute is still spent (and counted). Row-type, register, age and binder
  weights are used outside the update and are not gated.
* D-card-bypass: the decoder reads the card rows exactly as they were inserted (value + age + row type,
  before any Think pass) in place of the post-Think card rows. Same memory rows, same mask, no extra
  information; Think itself still sees and updates the card rows.

`from_base(variant, base)` builds a variant whose shared weights are copied from a baseline D, so the
two start identical (alpha = 0 is the only new parameter).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import torch
from torch import nn

from premonition.config import MiniConfig
from premonition.model import PremonitionMini, Think, _Episode
from premonition.store import CardStore

THINK_GATED = "D-think-gated"
CARD_BYPASS = "D-card-bypass"
ADJUSTMENTS = (THINK_GATED, CARD_BYPASS)
DESCRIPTIONS = {
    THINK_GATED: "whole Think update (step embedding included) gated by a learned scalar alpha, init 0",
    CARD_BYPASS: "decoder memory uses the pre-Think card rows in place of the post-Think card rows",
}


def source_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def identity(variant: str, config: MiniConfig) -> dict:
    """The variant's name, base variant, adjustment and source digest (diagnostic, never a primary D)."""
    if variant not in ADJUSTMENTS:
        raise ValueError(f"unknown adjustment {variant!r}; choose from {ADJUSTMENTS}")
    return {"variant": variant, "base_variant": config.variant, "adjustment": DESCRIPTIONS[variant],
            "purpose": "diagnostic", "module": "premonition/answer_path.py", "source_sha256": source_digest()}


class GatedThink(Think):
    """Think whose whole update is scaled by `alpha` (a scalar parameter, zero at initialisation)."""

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        self.alpha = nn.Parameter(torch.zeros(()))

    def forward(self, x: torch.Tensor, valid: torch.Tensor, step: int) -> torch.Tensor:
        return x + self.alpha * (super().forward(x, valid, step) - x)


class ThinkGatedMini(PremonitionMini):
    variant_name = THINK_GATED

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        gated = GatedThink(config)
        gated.load_state_dict(self.think.state_dict(), strict=False)   # same weights; alpha stays 0
        self.think = gated


class CardBypassMini(PremonitionMini):
    """The decoder sees the card rows as inserted; everything else is D."""

    variant_name = CARD_BYPASS

    def __init__(self, config: MiniConfig) -> None:
        super().__init__(config)
        self._reading: Optional[tuple[_Episode, Optional[torch.Tensor]]] = None

    @property
    def _card_slice(self) -> slice:
        return slice(self._card_base, self._card_base + self.config.cards)

    def _start(self, batch, hidden, store, mentions) -> _Episode:
        episode = super()._start(batch, hidden, store, mentions)
        episode.inserted = episode.x[:, self._card_slice].clone()       # zeros: no card inserted yet
        return episode

    def _insert(self, episode: _Episode, store: CardStore, index: torch.Tensor, cards: torch.Tensor) -> None:
        before_x, before_valid = episode.x[:, self._card_slice], episode.valid[:, self._card_slice]
        super()._insert(episode, store, index, cards)
        after_x = episode.x[:, self._card_slice]
        changed = (after_x != before_x).any(-1) | (episode.valid[:, self._card_slice] & ~before_valid)
        episode.inserted = torch.where(changed.unsqueeze(-1), after_x, episode.inserted)

    def forward(self, *args, **kwargs):
        try:
            return super().forward(*args, **kwargs)
        finally:
            self._reading = None

    def _step(self, episode, index, step, store):
        self._reading = (episode, index)
        return super()._step(episode, index, step, store)

    def _greedy(self, batch, episode, mentions, stop):
        self._reading = (episode, None)
        try:
            return super()._greedy(batch, episode, mentions, stop)
        finally:
            self._reading = None

    def _decode_logits(self, rows: torch.Tensor, valid: torch.Tensor, inputs: torch.Tensor) -> torch.Tensor:
        if self._reading is None or not self.config.cards:
            raise RuntimeError("D-card-bypass decodes only inside a think episode")
        episode, index = self._reading
        inserted = episode.inserted if index is None else episode.inserted[index]
        rows = torch.cat([rows[:, :self._card_base], inserted.to(rows.dtype),
                          rows[:, self._card_slice.stop:]], dim=1)
        return super()._decode_logits(rows, valid, inputs)


CLASSES = {THINK_GATED: ThinkGatedMini, CARD_BYPASS: CardBypassMini}


def from_base(variant: str, base: PremonitionMini) -> PremonitionMini:
    """A `variant` model with every shared weight copied from `base` (so both start identical)."""
    model = CLASSES[variant](base.config)
    missing, unexpected = model.load_state_dict(base.state_dict(), strict=False)
    extra = {THINK_GATED: ["think.alpha"], CARD_BYPASS: []}[variant]
    if sorted(missing) != extra or unexpected:
        raise RuntimeError(f"{variant}: unexpected state mismatch {missing} / {unexpected}")
    return model


__all__ = ["ADJUSTMENTS", "CARD_BYPASS", "CardBypassMini", "GatedThink", "THINK_GATED", "ThinkGatedMini",
           "from_base", "identity", "source_digest"]
