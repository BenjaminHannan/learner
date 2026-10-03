"""LatentCore: shared 2-block transformer looped n times over Workspace rows plus 8 registers.

Follows the real Net.step rule (z = h + e; z = blocks(z); h = LN(z); h0 = 0). Dense MLP stands in for
the real MoE. Bidirectional attention with key-padding mask; registers are always valid.
claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
import torch
from torch import nn
import torch.nn.functional as F
from .workspace import SEGMENTS, WIDTH, Workspace


class _Block(nn.Module):
    def __init__(self, d, heads, mlp):
        super().__init__()
        self.n1, self.n2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc1, self.fc2, self.heads = nn.Linear(d, mlp), nn.Linear(mlp, d), heads

    def forward(self, x, key_ok):
        b, t, d = x.shape
        q, k, v = self.qkv(self.n1(x)).view(b, t, 3, self.heads, d // self.heads).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=key_ok[:, None, None, :])
        x = x + self.o(a.transpose(1, 2).reshape(b, t, d))
        return x + self.fc2(F.gelu(self.fc1(self.n2(x))))


def sincos(x: torch.Tensor, dim: int) -> torch.Tensor:
    """x [...] -> [..., dim] sinusoidal code."""
    freq = torch.exp(-math.log(1000.0) * torch.arange(dim // 2, dtype=torch.float32) / (dim // 2))
    ang = x.unsqueeze(-1) * freq
    return torch.cat([ang.sin(), ang.cos()], -1)


@dataclass
class CoreOut:
    tokens: torch.Tensor     # [B,N,256]
    registers: torch.Tensor  # [B,R,256]
    valid: torch.Tensor      # [B,N]


class LatentCore(nn.Module):
    def __init__(self, d=WIDTH, heads=8, mlp=512, blocks=2, registers=8, n_loops=4):
        super().__init__()
        self.d, self.R, self.n_loops = d, registers, n_loops
        self.blocks = nn.ModuleList(_Block(d, heads, mlp) for _ in range(blocks))
        self.seg_emb = nn.Embedding(len(SEGMENTS), d)
        nn.init.zeros_(self.seg_emb.weight)
        self.null_row, self.null_col = nn.Parameter(torch.zeros(d // 2)), nn.Parameter(torch.zeros(d // 2))
        self.time_proj = nn.Linear(1, d)   # only used where a time coordinate exists (audio later)
        self.registers = nn.Parameter(torch.randn(registers, d) * 0.02)
        self.norm = nn.LayerNorm(d)

    def _pos(self, coords):
        row, col, time = coords.unbind(-1)
        half = self.d // 2
        pr = torch.where((row >= 0).unsqueeze(-1), sincos(row.clamp(min=0), half), self.null_row.expand(*row.shape, half))
        pc = torch.where((col >= 0).unsqueeze(-1), sincos(col.clamp(min=0), half), self.null_col.expand(*col.shape, half))
        pt = self.time_proj(time.clamp(min=0).unsqueeze(-1)) * (time >= 0).unsqueeze(-1)
        return torch.cat([pr, pc], -1) + pt

    def forward(self, ws: Workspace, n_loops: int | None = None) -> CoreOut:
        n_loops = self.n_loops if n_loops is None else n_loops
        b, n, _ = ws.tokens.shape
        e = ws.tokens + self.seg_emb(ws.segment[..., 0]) + self.seg_emb(ws.segment[..., 1]) + self._pos(ws.coords)
        reg = (self.registers + self.seg_emb.weight[SEGMENTS["register"]]).unsqueeze(0).expand(b, -1, -1)
        e = torch.cat([e * ws.valid.unsqueeze(-1), reg], 1)
        ok = torch.cat([ws.valid, torch.ones(b, self.R, dtype=torch.bool, device=e.device)], 1)
        h = torch.zeros_like(e)
        for _ in range(n_loops):
            z = h + e
            for blk in self.blocks:
                z = blk(z, ok)
            h = self.norm(z)
        return CoreOut(h[:, :n], h[:, n:], ws.valid)
