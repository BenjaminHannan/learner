"""PROBLEM-7 Forecast6 (Rank 6): Dedicated 2D Spatial Conv World Model.

100% learned 2D visual world model on 16x16 Crafter frames — zero game-specific
rules, zero OS/memory cheats, canonical premonition_core_v2 completely untouched.

Architecture (`SpatialWorldModelV6`):
  - `SpatialEncoder`: 16x16x3 centered frame + fixed 2D CoordConv (y, x in [-1, 1])
    -> shallow 3x3 conv stack -> 16x16xC spatial latent grid z_t (full 16x16 grid
    preserved so 1.75-px tile shifts and 2x2 player sprite are never downsampled away).
  - `SpatialDynamicsUNet`: Action-FiLM 2D ConvResNet U-Net (16x16 -> 8x8 -> 4x4 ->
    8x8 -> 16x16) with 4x4 global spatial self-attention at the bottleneck (lets center
    obstacle checks broadcast to all 16x16 terrain pixels in 1 hop while 3x3 convs
    provide native 2D translation equivariance) + bounded residual update
    `z_{t+1} = z_t + max_delta * tanh(raw_delta / max_delta)`.
  - `SpatialDecoder`: shallow 3x3 conv stack -> 16x16x3 frame.

Design invariants:
  - Strictly Markov single-frame encode: `z_t = encode(x_t)`.
  - Ceiling definition (no board): `decode(encode(x_{t+1}))` [abs] and
    `x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))` [res].
  - Open-loop rollout (`rollout(x0, acts_k)`): encodes `x0` ONCE and feeds only
    its own imagined latents forward; cannot receive intermediate real frames.
  - Anti-wishful-thinking (`wm_grad=False`): detaches all model parameters, buffers,
    and start latent `z_t` via `torch.func.functional_call`, while preserving
    gradients into continuous float action embeddings for planning.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.func import functional_call

H = W = 16
N_ACTIONS = 17
MAX_DELTA_DEFAULT = 3.0
PINNED_SCORER_SHA256 = "6ff1c135c0eeb2085aa4d49479b915cc5630f355b6d4ad3d5fa18ad81a98b83c"

MODEL_SIZES = {
    "R6conv": dict(latent_ch=64, c0=64, c1=96, c2=128, cond_dim=128, n_heads=4, groups=8),
    "tiny": dict(latent_ch=16, c0=16, c1=24, c2=32, cond_dim=32, n_heads=2, groups=4),
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pinned_scorer(scorer_path: Path | None = None) -> str:
    """Verify forecast6/scorer.py is bit-identical to pinned forecast5/scorer.py."""
    p = Path(scorer_path) if scorer_path is not None else (Path(__file__).resolve().parent / "scorer.py")
    have = sha256_path(p)
    if have != PINNED_SCORER_SHA256:
        raise RuntimeError(
            f"forecast6: scorer.py sha {have} != pinned {PINNED_SCORER_SHA256} ({p})"
        )
    return have


def make_coord_grid(h: int = H, w: int = W) -> torch.Tensor:
    """Fixed normalized 2D coordinate channels (y, x) in [-1, 1], shape [1, 2, H, W]."""
    ys = torch.linspace(-1.0, 1.0, h).view(1, 1, h, 1).expand(1, 1, h, w)
    xs = torch.linspace(-1.0, 1.0, w).view(1, 1, 1, w).expand(1, 1, h, w)
    return torch.cat([ys, xs], dim=1).contiguous()


class SpatialEncoder(nn.Module):
    """Shallow 2D conv encoder mapping [B, 16, 16, 3] -> [B, latent_ch, 16, 16]."""

    def __init__(self, latent_ch: int = 64):
        super().__init__()
        self.latent_ch = int(latent_ch)
        self.register_buffer("coord_grid", make_coord_grid(H, W), persistent=True)
        self.conv1 = nn.Conv2d(3 + 2, latent_ch, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(latent_ch, latent_ch, kernel_size=3, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, 16, 16, 3] in [0, 1] -> centered [B, 3, 16, 16]
        if x.ndim != 4 or x.shape[1:] != (H, W, 3):
            raise ValueError(f"Expected x shape [B, {H}, {W}, 3], got {tuple(x.shape)}")
        xc = (x - 0.5).permute(0, 3, 1, 2).contiguous()
        coord = self.coord_grid.to(dtype=xc.dtype).expand(xc.shape[0], -1, -1, -1)
        h = F.silu(self.conv1(torch.cat([xc, coord], dim=1)))
        return self.conv2(h)


class SpatialDecoder(nn.Module):
    """Shallow 2D conv decoder mapping [B, latent_ch, 16, 16] -> [B, 16, 16, 3]."""

    def __init__(self, latent_ch: int = 64):
        super().__init__()
        self.latent_ch = int(latent_ch)
        self.conv1 = nn.Conv2d(latent_ch, latent_ch, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(latent_ch, 3, kernel_size=3, padding=1)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        h = F.silu(self.conv1(z))
        out = self.conv2(h) + 0.5
        return out.permute(0, 2, 3, 1).contiguous()


class FiLMResBlock(nn.Module):
    """Pre-norm 2D ConvResNet block conditioned on action embedding via FiLM."""

    def __init__(self, ch: int, cond_dim: int, groups: int = 8):
        super().__init__()
        g = min(groups, ch)
        while ch % g != 0:
            g -= 1
        self.norm1 = nn.GroupNorm(g, ch)
        self.film1 = nn.Linear(cond_dim, 2 * ch)
        self.conv1 = nn.Conv2d(ch, ch, kernel_size=3, padding=1)

        self.norm2 = nn.GroupNorm(g, ch)
        self.film2 = nn.Linear(cond_dim, 2 * ch)
        self.conv2 = nn.Conv2d(ch, ch, kernel_size=3, padding=1)

        # Small near-identity init on FiLM layers so step-0 grads flow cleanly without noise burst
        nn.init.normal_(self.film1.weight, std=0.02)
        nn.init.zeros_(self.film1.bias)
        nn.init.normal_(self.film2.weight, std=0.02)
        nn.init.zeros_(self.film2.bias)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        g1, b1 = self.film1(cond).chunk(2, dim=-1)
        h = self.norm1(x)
        h = h * (1.0 + torch.tanh(g1)[..., None, None]) + b1[..., None, None]
        h = self.conv1(F.silu(h))

        g2, b2 = self.film2(cond).chunk(2, dim=-1)
        h = self.norm2(h)
        h = h * (1.0 + torch.tanh(g2)[..., None, None]) + b2[..., None, None]
        h = self.conv2(F.silu(h))
        return x + h


class SpatialSelfAttention2d(nn.Module):
    """Compact 2D spatial self-attention at the 4x4 bottleneck (16 spatial tokens)."""

    def __init__(self, ch: int, n_heads: int = 4, groups: int = 8):
        super().__init__()
        if ch % n_heads != 0:
            raise ValueError(f"ch={ch} not divisible by n_heads={n_heads}")
        g = min(groups, ch)
        while ch % g != 0:
            g -= 1
        self.ch = int(ch)
        self.n_heads = int(n_heads)
        self.head_dim = ch // n_heads
        self.norm = nn.GroupNorm(g, ch)
        self.qkv = nn.Conv2d(ch, 3 * ch, kernel_size=1, bias=False)
        self.proj = nn.Conv2d(ch, ch, kernel_size=1)
        nn.init.normal_(self.proj.weight, std=0.02)
        nn.init.zeros_(self.proj.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, Hc, Wc = x.shape
        N = Hc * Wc
        h = self.norm(x)
        qkv = self.qkv(h).reshape(B, 3, self.n_heads, self.head_dim, N)
        q = qkv[:, 0].transpose(-2, -1)  # [B, nh, N, hd]
        k = qkv[:, 1].transpose(-2, -1)  # [B, nh, N, hd]
        v = qkv[:, 2].transpose(-2, -1)  # [B, nh, N, hd]
        scale = 1.0 / math.sqrt(self.head_dim)
        att = torch.softmax(torch.matmul(q, k.transpose(-2, -1)) * scale, dim=-1)
        out = torch.matmul(att, v).transpose(-2, -1).reshape(B, C, Hc, Wc)
        return x + self.proj(out)


class SpatialDynamicsUNet(nn.Module):
    """Action-FiLM 2D ConvResNet U-Net (16x16 <-> 8x8 <-> 4x4) predicting bounded delta z."""

    def __init__(
        self,
        latent_ch: int = 64,
        c0: int = 64,
        c1: int = 96,
        c2: int = 128,
        cond_dim: int = 128,
        n_heads: int = 4,
        groups: int = 8,
        max_delta: float = MAX_DELTA_DEFAULT,
    ):
        super().__init__()
        self.latent_ch = int(latent_ch)
        self.cond_dim = int(cond_dim)
        self.max_delta = float(max_delta)
        self.register_buffer("coord_grid", make_coord_grid(H, W), persistent=True)

        self.act_mlp = nn.Sequential(
            nn.Linear(cond_dim, cond_dim),
            nn.SiLU(),
            nn.Linear(cond_dim, cond_dim),
        )

        # Input mixes latent grid with fixed 2D coordinates so open-loop k=2..5 keeps spatial layout
        self.in_proj = nn.Conv2d(latent_ch + 2, c0, kernel_size=1)

        # Down path: 16x16 -> 8x8 -> 4x4
        self.enc0_a = FiLMResBlock(c0, cond_dim, groups=groups)
        self.enc0_b = FiLMResBlock(c0, cond_dim, groups=groups)
        self.down1 = nn.Conv2d(c0, c1, kernel_size=3, stride=2, padding=1)

        self.enc1_a = FiLMResBlock(c1, cond_dim, groups=groups)
        self.enc1_b = FiLMResBlock(c1, cond_dim, groups=groups)
        self.down2 = nn.Conv2d(c1, c2, kernel_size=3, stride=2, padding=1)

        # 4x4 bottleneck with global spatial self-attention across all 16 spatial cells
        self.mid1 = FiLMResBlock(c2, cond_dim, groups=groups)
        self.mid_attn = SpatialSelfAttention2d(c2, n_heads=n_heads, groups=groups)
        self.mid2 = FiLMResBlock(c2, cond_dim, groups=groups)

        # Up path: 4x4 -> 8x8 -> 16x16 with skip connections (nearest upsample + 3x3 conv)
        self.up1_fuse = nn.Conv2d(c2 + c1, c1, kernel_size=3, padding=1)
        self.dec1_a = FiLMResBlock(c1, cond_dim, groups=groups)
        self.dec1_b = FiLMResBlock(c1, cond_dim, groups=groups)

        self.up0_fuse = nn.Conv2d(c1 + c0, c0, kernel_size=3, padding=1)
        self.dec0_a = FiLMResBlock(c0, cond_dim, groups=groups)
        self.dec0_b = FiLMResBlock(c0, cond_dim, groups=groups)

        g_out = min(groups, c0)
        while c0 % g_out != 0:
            g_out -= 1
        self.out_norm = nn.GroupNorm(g_out, c0)
        self.out_conv = nn.Conv2d(c0, latent_ch, kernel_size=3, padding=1)
        # Small near-identity init so step-0 prediction is close to copy while grads flow immediately
        nn.init.normal_(self.out_conv.weight, std=0.02)
        nn.init.zeros_(self.out_conv.bias)

    def forward(self, z: torch.Tensor, act_emb: torch.Tensor) -> torch.Tensor:
        cond = self.act_mlp(act_emb)
        coord = self.coord_grid.to(dtype=z.dtype).expand(z.shape[0], -1, -1, -1)
        h0 = self.in_proj(torch.cat([z, coord], dim=1))

        s0 = self.enc0_b(self.enc0_a(h0, cond), cond)          # [B, c0, 16, 16]
        s1 = self.enc1_b(self.enc1_a(self.down1(s0), cond), cond)  # [B, c1, 8, 8]
        m = self.mid1(self.down2(s1), cond)                    # [B, c2, 4, 4]
        m = self.mid_attn(m)
        m = self.mid2(m, cond)

        u1 = F.interpolate(m, scale_factor=2, mode="nearest")  # [B, c2, 8, 8]
        u1 = self.up1_fuse(torch.cat([u1, s1], dim=1))
        u1 = self.dec1_b(self.dec1_a(u1, cond), cond)

        u0 = F.interpolate(u1, scale_factor=2, mode="nearest")  # [B, c1, 16, 16]
        u0 = self.up0_fuse(torch.cat([u0, s0], dim=1))
        u0 = self.dec0_b(self.dec0_a(u0, cond), cond)

        raw_delta = self.out_conv(F.silu(self.out_norm(u0)))
        delta = self.max_delta * torch.tanh(raw_delta / self.max_delta)
        return z + delta


class SpatialWorldModelV6(nn.Module):
    """Dedicated 2D Spatial Conv World Model (PROBLEM-7 Rank 6)."""

    def __init__(self, size: str = "R6conv", max_delta: float = MAX_DELTA_DEFAULT):
        super().__init__()
        if size not in MODEL_SIZES:
            raise ValueError(f"Unknown size {size!r}; expected one of {sorted(MODEL_SIZES)}")
        cfg = MODEL_SIZES[size]
        self.size = size
        self.cfg = dict(cfg)
        self.latent_ch = int(cfg["latent_ch"])
        self.cond_dim = int(cfg["cond_dim"])
        self.max_delta = float(max_delta)

        self.encoder = SpatialEncoder(latent_ch=self.latent_ch)
        self.decoder = SpatialDecoder(latent_ch=self.latent_ch)
        self.action_emb = nn.Embedding(N_ACTIONS, self.cond_dim)
        self.dynamics = SpatialDynamicsUNet(
            latent_ch=self.latent_ch,
            c0=cfg["c0"],
            c1=cfg["c1"],
            c2=cfg["c2"],
            cond_dim=self.cond_dim,
            n_heads=cfg["n_heads"],
            groups=cfg["groups"],
            max_delta=self.max_delta,
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encode single real frame [B, 16, 16, 3] -> spatial latent grid [B, C, 16, 16]."""
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode spatial latent grid [B, C, 16, 16] -> frame [B, 16, 16, 3]."""
        return self.decoder(z)

    def _resolve_action_emb(self, act: torch.Tensor, *, detach_lookup: bool) -> torch.Tensor:
        if act.dtype in (torch.long, torch.int64, torch.int32, torch.int16, torch.int8, torch.uint8):
            e = self.action_emb(act.long())
            return e.detach() if detach_lookup else e
        if act.ndim != 2 or act.shape[-1] != self.cond_dim:
            raise ValueError(f"Expected float action_emb [B, {self.cond_dim}], got {tuple(act.shape)}")
        return act

    def imagine_step(self, z: torch.Tensor, act: torch.Tensor, *, wm_grad: bool = True) -> torch.Tensor:
        """Single-step 2D spatial imagination transition `z_t, a_t -> z_{t+1}`.

        When `wm_grad=False` (planning mode), detaches start latent `z`, integer action
        lookup, and every dynamics parameter/buffer so planning cannot corrupt the world
        model, while preserving gradients into continuous float `act` embeddings.
        """
        if wm_grad or (not torch.is_grad_enabled()):
            a_emb = self._resolve_action_emb(act, detach_lookup=False)
            return self.dynamics(z, a_emb)

        z_det = z.detach()
        a_emb = self._resolve_action_emb(act, detach_lookup=True)
        detached_state = {
            **{k: v.detach() for k, v in self.dynamics.named_parameters()},
            **{k: v.detach() for k, v in self.dynamics.named_buffers()},
        }
        return functional_call(self.dynamics, detached_state, (z_det, a_emb))

    def rollout(self, x0: torch.Tensor, acts_k: torch.Tensor, *, wm_grad: bool = False) -> dict[str, torch.Tensor]:
        """Open-loop k-step rollout initialized ONCE from x0 (never sees intermediate real frames).

        Supports both Long action IDs `[B, k]` and continuous Float action embeddings `[B, k, cond_dim]`.
        When `wm_grad=False`, detaches encoder, decoder, action_emb, and dynamics parameters/buffers so
        zero gradient ever leaks to the world model while preserving gradients into float action plans.
        """
        if acts_k.ndim not in (2, 3):
            raise ValueError(f"Expected acts_k shape [B, k] or [B, k, {self.cond_dim}], got {tuple(acts_k.shape)}")
        if wm_grad or (not torch.is_grad_enabled()):
            z0 = self.encode(x0)
            dec0 = self.decode(z0)
            z = z0
            for step in range(acts_k.shape[1]):
                z = self.imagine_step(z, acts_k[:, step], wm_grad=wm_grad)
            pred_abs = self.decode(z)
        else:
            with torch.no_grad():
                z0 = self.encode(x0)
                dec0 = self.decode(z0)
            z = z0
            for step in range(acts_k.shape[1]):
                # Keep z flowing from step 0 -> k for multi-step action-plan grads while keeping WM params detached
                a_emb = self._resolve_action_emb(acts_k[:, step], detach_lookup=True)
                detached_dyn = {
                    **{k: v.detach() for k, v in self.dynamics.named_parameters()},
                    **{k: v.detach() for k, v in self.dynamics.named_buffers()},
                }
                z = functional_call(self.dynamics, detached_dyn, (z, a_emb))
            detached_dec = {
                **{k: v.detach() for k, v in self.decoder.named_parameters()},
                **{k: v.detach() for k, v in self.decoder.named_buffers()},
            }
            pred_abs = functional_call(self.decoder, detached_dec, (z,))
        pred_res = x0 + (pred_abs - dec0)
        return {
            "pred_res": pred_res,
            "pred_abs": pred_abs,
            "z0": z0,
            "z_last": z,
        }

    @staticmethod
    @torch.no_grad()
    def latent_stats(z: torch.Tensor) -> dict[str, float]:
        """Diagnostic static vs cross-sample spread RMS of spatial latent grid (safe at B=1)."""
        zf = z.detach().float()
        static_rms = float(zf.mean(dim=0).pow(2).mean().sqrt())
        spread_rms = float(zf.std(dim=0, correction=0).pow(2).mean().sqrt())
        return {
            "static_rms": static_rms,
            "spread_rms": spread_rms,
            "burial_ratio": static_rms / max(spread_rms, 1e-8),
        }

    def param_counts(self) -> dict[str, int]:
        n_enc = sum(p.numel() for p in self.encoder.parameters())
        n_dec = sum(p.numel() for p in self.decoder.parameters())
        n_act = sum(p.numel() for p in self.action_emb.parameters())
        n_dyn = sum(p.numel() for p in self.dynamics.parameters())
        return {
            "encoder": int(n_enc),
            "decoder": int(n_dec),
            "action_emb": int(n_act),
            "dynamics": int(n_dyn),
            "model_total": int(n_enc + n_dec + n_act + n_dyn),
        }
