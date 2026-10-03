"""ContextualReader: per-token projection of LM hidden states into 256-wide Workspace tokens.

Same block as the v6 HumanInputProjection (LayerNorm -> 32 -> GELU -> 256). Fed LM hidden states
(contextual) by default; source="embed" feeds input embeddings. claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

import torch
from torch import nn
from .workspace import WIDTH


class ContextualReader(nn.Module):
    def __init__(self, lm_width: int, bottleneck: int = 32):
        super().__init__()
        self.lm_width = lm_width
        self.norm = nn.LayerNorm(lm_width)
        self.down, self.up = nn.Linear(lm_width, bottleneck), nn.Linear(bottleneck, WIDTH)
        self.out_norm = nn.LayerNorm(WIDTH)   # keeps content on the same scale as the position codes

    def forward(self, lm_states: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        """lm_states [B,N,D_lm], valid [B,N] -> tokens [B,N,256], invalid rows exactly 0."""
        out = self.out_norm(self.up(nn.functional.gelu(self.down(self.norm(lm_states)))))
        return out * valid.unsqueeze(-1)
