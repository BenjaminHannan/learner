"""own-O0e baseline model: plain decoder-only transformer (plan 01 sect 7, 7.1).

Shape (fixed by the plan): 12 blocks, width 640, SwiGLU MLP width 1600,
RMSNorm, rotary positions, 8192 tied embeddings, context 1024. CPU only,
plain torch. No biases anywhere; rotary and the causal mask hold no
learned numbers.

Design parameter count (tied embedding counted once):
  embeddings        8192 x 640                        =  5,242,880
  per block: attn 4 x 640 x 640                       =  1,638,400
             SwiGLU gate+up+down 3 x 640 x 1600       =  3,072,000
             2 x RMSNorm(640)                         =      1,280
             block total                              =  4,711,680
  12 blocks                                           = 56,540,160
  final RMSNorm                                       =        640
  TOTAL                                               = 61,783,680
Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; \
  uv run --offline --no-project --python 3.12 --with torch \
  python -B scripts/claude_own_o0e_model.py --audit
"""

from __future__ import annotations

import argparse
import dataclasses
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

EXPECTED_PARAMS = 61783680


@dataclasses.dataclass
class ModelConfig:
    vocab: int = 8192
    width: int = 640
    layers: int = 12
    mlp_width: int = 1600
    heads: int = 10  # 640 / 10 = 64 per head
    context: int = 1024
    rope_theta: float = 10000.0


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        var = x.float().pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(var + self.eps)
        return (x * self.weight).to(x.dtype)


class Rotary(nn.Module):
    """Rotary positions; holds no learned parameters."""

    def __init__(self, head_dim: int, context: int, theta: float = 10000.0):
        super().__init__()
        inv = 1.0 / (theta ** (torch.arange(0, head_dim, 2).float() / head_dim))
        pos = torch.arange(context).float()
        freqs = torch.outer(pos, inv)  # [T, head_dim/2]
        self.register_buffer("cos", freqs.cos(), persistent=False)
        self.register_buffer("sin", freqs.sin(), persistent=False)

    def forward(self, q: torch.Tensor, k: torch.Tensor):
        # q, k: [B, H, T, D]
        t = q.shape[2]
        cos = self.cos[:t].to(q.dtype)[None, None, :, :].repeat_interleave(2, dim=-1)
        sin = self.sin[:t].to(q.dtype)[None, None, :, :].repeat_interleave(2, dim=-1)

        def rot(x):
            x1 = x[..., 0::2]
            x2 = x[..., 1::2]
            return torch.stack((-x2, x1), dim=-1).flatten(-2)

        return q * cos + rot(q) * sin, k * cos + rot(k) * sin


class CausalAttention(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        assert cfg.width % cfg.heads == 0
        self.heads = cfg.heads
        self.hd = cfg.width // cfg.heads
        self.q = nn.Linear(cfg.width, cfg.width, bias=False)
        self.k = nn.Linear(cfg.width, cfg.width, bias=False)
        self.v = nn.Linear(cfg.width, cfg.width, bias=False)
        self.o = nn.Linear(cfg.width, cfg.width, bias=False)
        self.rot = Rotary(self.hd, cfg.context, cfg.rope_theta)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, t, _ = x.shape
        q = self.q(x).view(b, t, self.heads, self.hd).transpose(1, 2)
        k = self.k(x).view(b, t, self.heads, self.hd).transpose(1, 2)
        v = self.v(x).view(b, t, self.heads, self.hd).transpose(1, 2)
        q, k = self.rot(q, k)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = y.transpose(1, 2).contiguous().view(b, t, -1)
        return self.o(y)


class SwiGLU(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.gate = nn.Linear(cfg.width, cfg.mlp_width, bias=False)
        self.up = nn.Linear(cfg.width, cfg.mlp_width, bias=False)
        self.down = nn.Linear(cfg.mlp_width, cfg.width, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down(F.silu(self.gate(x)) * self.up(x))


class Block(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.ln1 = RMSNorm(cfg.width)
        self.attn = CausalAttention(cfg)
        self.ln2 = RMSNorm(cfg.width)
        self.mlp = SwiGLU(cfg)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class PlainTransformer(nn.Module):
    """Decoder-only baseline. lm head is the tied embedding matrix."""

    def __init__(self, cfg: ModelConfig | None = None):
        super().__init__()
        self.cfg = cfg or ModelConfig()
        self.embed = nn.Embedding(self.cfg.vocab, self.cfg.width)
        self.blocks = nn.ModuleList(Block(self.cfg) for _ in range(self.cfg.layers))
        self.final_norm = RMSNorm(self.cfg.width)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        x = self.embed(ids)
        for blk in self.blocks:
            x = blk(x)
        x = self.final_norm(x)
        return x @ self.embed.weight.t()

    @torch.no_grad()
    def generate(self, ids: torch.Tensor, n_new: int) -> torch.Tensor:
        ids = ids.clone()
        for _ in range(n_new):
            window = ids[:, -self.cfg.context :]
            nxt = self.forward(window)[:, -1, :].argmax(-1, keepdim=True)
            ids = torch.cat([ids, nxt], dim=1)
        return ids


def count_parameters(model: nn.Module) -> tuple[int, dict[str, int]]:
    """Count every learned number once (shared tensors counted once)."""
    seen: set[int] = set()
    parts: dict[str, int] = {}
    total = 0
    for name, p in model.named_parameters():
        if p.data_ptr() in seen:
            continue
        seen.add(p.data_ptr())
        n = p.numel()
        total += n
        top = name.split(".")[0]
        parts[top] = parts.get(top, 0) + n
    return total, parts


def audit() -> tuple[bool, int]:
    torch.manual_seed(0)
    model = PlainTransformer()
    total, parts = count_parameters(model)
    print(f"audited parameters : {total}")
    print(f"expected           : {EXPECTED_PARAMS}")
    for k in sorted(parts):
        print(f"  {k}: {parts[k]}")
    lo = EXPECTED_PARAMS * 0.998
    hi = EXPECTED_PARAMS * 1.002
    ok = lo <= total <= hi
    print("AUDIT " + ("PASS" if ok else "FAIL"))
    return ok, total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    args = ap.parse_args()
    if args.audit:
        ok, _ = audit()
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
