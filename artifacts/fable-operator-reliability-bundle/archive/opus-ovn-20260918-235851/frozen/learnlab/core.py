"""Plain core learner: a decoder-only causal transformer LM (design/04, part 3).

Pre-norm blocks, causal `scaled_dot_product_attention`, GELU MLP, learned
positions and tied input/output embeddings. Size presets follow the measured
scale plan: build at 4M, confirm at 28M, live at 90M.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F

# name -> (d_model, n_layers, n_heads); the names are nominal parameter counts.
SIZES = {"4M": (256, 4, 4), "28M": (512, 8, 8), "90M": (768, 12, 12)}
IGNORE_INDEX = -100


@dataclass(frozen=True)
class CoreConfig:
    vocab_size: int
    context: int
    d_model: int = 256
    n_layers: int = 4
    n_heads: int = 4
    mlp_ratio: int = 4

    def __post_init__(self) -> None:
        for name in ("vocab_size", "context", "d_model", "n_layers", "n_heads", "mlp_ratio"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")

    @classmethod
    def preset(cls, size: str, vocab_size: int, context: int) -> CoreConfig:
        """A named size from SIZES ("4M", "28M", "90M")."""
        if size not in SIZES:
            raise ValueError(f"unknown size {size!r}; choose from {sorted(SIZES)}")
        d_model, n_layers, n_heads = SIZES[size]
        return cls(vocab_size, context, d_model, n_layers, n_heads)


class Block(nn.Module):
    """Pre-norm causal self-attention followed by a pre-norm GELU MLP."""

    def __init__(self, config: CoreConfig) -> None:
        super().__init__()
        d, hidden = config.d_model, config.mlp_ratio * config.d_model
        self.n_heads = config.n_heads
        self.norm1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.norm2 = nn.LayerNorm(d)
        self.fc = nn.Linear(d, hidden)
        self.act = nn.GELU()
        self.out = nn.Linear(hidden, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        q, k, v = (
            self.qkv(self.norm1(x))
            .view(batch, length, 3, self.n_heads, width // self.n_heads)
            .permute(2, 0, 3, 1, 4)
        )
        attended = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(attended.transpose(1, 2).reshape(batch, length, width))
        return x + self.out(self.act(self.fc(self.norm2(x))))


class Core(nn.Module):
    """forward(tokens [..., T]) -> logits [..., T, vocab_size]."""

    def __init__(self, config: CoreConfig) -> None:
        super().__init__()
        self.config = config
        self.embed = nn.Embedding(config.vocab_size, config.d_model)
        self.pos = nn.Parameter(torch.empty(config.context, config.d_model))
        self.blocks = nn.ModuleList(Block(config) for _ in range(config.n_layers))
        self.norm = nn.LayerNorm(config.d_model)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        # Embedding std d^-0.5 gives unit-scale logits through the tied head.
        nn.init.normal_(self.embed.weight, std=self.config.d_model ** -0.5)
        nn.init.normal_(self.pos, std=0.02)
        residual_std = 0.02 / math.sqrt(2 * self.config.n_layers)
        for block in self.blocks:
            for linear, std in ((block.qkv, 0.02), (block.fc, 0.02),
                                (block.proj, residual_std), (block.out, residual_std)):
                nn.init.normal_(linear.weight, std=std)
                nn.init.zeros_(linear.bias)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        length = tokens.shape[-1]
        if length > self.config.context:
            raise ValueError(f"sequence length {length} exceeds context {self.config.context}")
        h = self.embed(tokens) + self.pos[:length]
        for block in self.blocks:
            h = block(h)
        return F.linear(self.norm(h), self.embed.weight)


def lm_loss(logits: torch.Tensor, targets: torch.Tensor, mask: Optional[torch.Tensor] = None,
            ignore_index: int = IGNORE_INDEX) -> torch.Tensor:
    """Mean next-token cross-entropy over targets that are kept.

    Targets equal to `ignore_index`, or where `mask` is False, contribute
    nothing; an all-excluded batch gives a zero loss rather than NaN.
    """
    if mask is not None:
        targets = targets.masked_fill(~mask.bool(), ignore_index)
    targets = targets.reshape(-1)
    total = F.cross_entropy(logits.reshape(-1, logits.shape[-1]).float(), targets,
                            ignore_index=ignore_index, reduction="sum")
    return total / targets.ne(ignore_index).sum().clamp_min(1)


__all__ = ["IGNORE_INDEX", "SIZES", "Block", "Core", "CoreConfig", "lm_loss"]
