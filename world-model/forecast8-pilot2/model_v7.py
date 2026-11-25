"""PROBLEM-7 Forecast7 (Rank 7): 2-Frame Dedicated 2D Spatial Conv World Model.

100% learned 2D visual world model on 16x16 Crafter frames — zero game-specific
rules, zero OS/memory cheats, canonical premonition_core_v2 completely untouched.

Exact ONE training change from Rank 6 (`forecast6/model_v6.py`):
  - `SpatialDynamicsUNet.in_proj` reads `[z_t, z_t - z_{t-1}, coord]` (`2 * latent_ch + 2`
    channels, `+4,096` params = `+0.15%` at `R7conv`) instead of `[z_t, coord]`, using the
    same shallow `SpatialEncoder` on the strictly past real frame `x_{t-1}` (with `x_{-1} = x_0`
    at episode start; never crossing an episode or world boundary).
  - Supports `n_history in (1, 2)` so the exact same pinned evaluation path (`evaluate_model`
    with `--rollout {plain,reencode}`) scores both saved Rank 6 (`n_history=1`) checkpoints and
    Rank 7 (`n_history=2`) checkpoints for a full 2x2 comparison.

Architecture (`SpatialWorldModelV7`):
  - `SpatialEncoder`: 16x16x3 centered frame + fixed 2D CoordConv (y, x in [-1, 1])
    -> shallow 3x3 conv stack -> 16x16xC spatial latent grid z_t (strictly single-frame).
  - `SpatialDynamicsUNet`: Action-FiLM 2D ConvResNet U-Net (16x16 -> 8x8 -> 4x4 ->
    8x8 -> 16x16) with 4x4 global spatial self-attention at the bottleneck + bounded
    residual update `z_{t+1} = z_t + max_delta * tanh(raw_delta / max_delta)`.
  - `SpatialDecoder`: shallow 3x3 conv stack -> 16x16x3 frame.

Design invariants:
  - Strictly single-frame encode: `z_t = encode(x_t)`.
  - Ceiling definition (no board): `decode(encode(x_{t+1}))` [abs] and
    `x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))` [res].
  - Open-loop rollout (`rollout(x0, acts_k, x_prev=..., rollout_mode=...)`):
      * Only `x_{t-1}` (`x_prev`) and `x_t` (`x0`) may be real.
      * Step 0 uses `(enc(x_{t-1}), enc(x_t))`; Step 1 uses `(enc(x_t), z_hat_1)`;
        from Step 2 onward (`t+2 -> t+3`, ...), BOTH history entries `(z_hat_{s-1}, z_hat_s)`
        are strictly the model's own outputs.
      * `rollout_mode="plain"`: feeds raw imagined latents `z_next` forward.
      * `rollout_mode="reencode"` (`reencode_res`, verdict of record): between open-loop
        steps (`step < k - 1`), projects the imagined latent back onto the encoder manifold
        via `z_next_feed = encode(clamp(x0 + decode(z_next) - dec0, 0, 1))`. At `k = 1`,
        `plain` and `reencode` are bit-identical.
  - Anti-wishful-thinking (`wm_grad=False`): detaches all model parameters, buffers, and
    real input frames/latents via `torch.func.functional_call`, while preserving gradients
    into continuous float action embeddings for planning in BOTH `plain` and `reencode` modes.
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
ROLLOUT_MODES = ("plain", "reencode")
PINNED_SCORER_SHA256 = "ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912"

MODEL_SIZES = {
    "R7conv": dict(latent_ch=64, c0=64, c1=96, c2=128, cond_dim=128, n_heads=4, groups=8),
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
    """Verify forecast7/scorer.py matches the adopted dated scorer pin."""
    p = Path(scorer_path) if scorer_path is not None else (Path(__file__).resolve().parent / "scorer.py")
    have = sha256_path(p)
    if have != PINNED_SCORER_SHA256:
        raise RuntimeError(
            f"forecast7: scorer.py sha {have} != pinned {PINNED_SCORER_SHA256} ({p})"
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
        q = qkv[:, 0].transpose(-2, -1)
        k = qkv[:, 1].transpose(-2, -1)
        v = qkv[:, 2].transpose(-2, -1)
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
        n_history: int = 2,
        max_delta: float = MAX_DELTA_DEFAULT,
    ):
        super().__init__()
        if n_history not in (1, 2):
            raise ValueError(f"n_history must be 1 or 2, got {n_history!r}")
        self.latent_ch = int(latent_ch)
        self.cond_dim = int(cond_dim)
        self.n_history = int(n_history)
        self.max_delta = float(max_delta)
        self.register_buffer("coord_grid", make_coord_grid(H, W), persistent=True)

        self.act_mlp = nn.Sequential(
            nn.Linear(cond_dim, cond_dim),
            nn.SiLU(),
            nn.Linear(cond_dim, cond_dim),
        )

        # n_history=1: [z_t, coord]; n_history=2: [z_t, z_t - z_{t-1}, coord]
        in_ch = (2 * latent_ch + 2) if self.n_history == 2 else (latent_ch + 2)
        self.in_proj = nn.Conv2d(in_ch, c0, kernel_size=1)

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
        nn.init.normal_(self.out_conv.weight, std=0.02)
        nn.init.zeros_(self.out_conv.bias)

    def forward(
        self,
        z: torch.Tensor,
        act_emb: torch.Tensor,
        z_prev: torch.Tensor | None = None,
    ) -> torch.Tensor:
        cond = self.act_mlp(act_emb)
        coord = self.coord_grid.to(dtype=z.dtype).expand(z.shape[0], -1, -1, -1)
        if self.n_history == 2:
            if z_prev is None:
                raise ValueError("SpatialDynamicsUNet(n_history=2) requires z_prev")
            if z_prev.shape != z.shape:
                raise ValueError(f"z_prev shape {tuple(z_prev.shape)} != z shape {tuple(z.shape)}")
            h0 = self.in_proj(torch.cat([z, z - z_prev, coord], dim=1))
        else:
            h0 = self.in_proj(torch.cat([z, coord], dim=1))

        s0 = self.enc0_b(self.enc0_a(h0, cond), cond)
        s1 = self.enc1_b(self.enc1_a(self.down1(s0), cond), cond)
        m = self.mid1(self.down2(s1), cond)
        m = self.mid_attn(m)
        m = self.mid2(m, cond)

        u1 = F.interpolate(m, scale_factor=2, mode="nearest")
        u1 = self.up1_fuse(torch.cat([u1, s1], dim=1))
        u1 = self.dec1_b(self.dec1_a(u1, cond), cond)

        u0 = F.interpolate(u1, scale_factor=2, mode="nearest")
        u0 = self.up0_fuse(torch.cat([u0, s0], dim=1))
        u0 = self.dec0_b(self.dec0_a(u0, cond), cond)

        raw_delta = self.out_conv(F.silu(self.out_norm(u0)))
        delta = self.max_delta * torch.tanh(raw_delta / self.max_delta)
        return z + delta


class SpatialWorldModelV7(nn.Module):
    """Dedicated 2D Spatial Conv World Model with configurable 1- or 2-frame history."""

    def __init__(
        self,
        size: str = "R7conv",
        n_history: int = 2,
        max_delta: float = MAX_DELTA_DEFAULT,
    ):
        super().__init__()
        if size not in MODEL_SIZES:
            raise ValueError(f"Unknown size {size!r}; expected one of {sorted(MODEL_SIZES)}")
        if n_history not in (1, 2):
            raise ValueError(f"n_history must be 1 or 2, got {n_history!r}")
        cfg = MODEL_SIZES[size]
        self.size = size
        self.n_history = int(n_history)
        self.cfg = dict(cfg, n_history=self.n_history)
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
            n_history=self.n_history,
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

    def imagine_step(
        self,
        z: torch.Tensor,
        act: torch.Tensor,
        *,
        z_prev: torch.Tensor | None = None,
        wm_grad: bool = True,
    ) -> torch.Tensor:
        """Single-step 2D spatial imagination transition `(z_{t-1}, z_t), a_t -> z_{t+1}`."""
        if self.n_history == 2 and z_prev is None:
            raise ValueError("n_history=2 imagine_step requires explicit z_prev")
        if wm_grad or (not torch.is_grad_enabled()):
            a_emb = self._resolve_action_emb(act, detach_lookup=False)
            return self.dynamics(z, a_emb, z_prev)

        z_det = z.detach()
        z_prev_det = z_prev.detach() if z_prev is not None else None
        a_emb = self._resolve_action_emb(act, detach_lookup=True)
        detached_state = {
            **{k: v.detach() for k, v in self.dynamics.named_parameters()},
            **{k: v.detach() for k, v in self.dynamics.named_buffers()},
        }
        return functional_call(self.dynamics, detached_state, (z_det, a_emb, z_prev_det))

    def rollout(
        self,
        x0: torch.Tensor,
        acts_k: torch.Tensor,
        *,
        x_prev: torch.Tensor | None = None,
        rollout_mode: str = "reencode",
        wm_grad: bool = False,
    ) -> dict[str, torch.Tensor]:
        """Open-loop k-step rollout initialized ONCE from (x_prev, x0) — never sees future real frames.

        History rules:
          - Only `x_prev` (x_{t-1}) and `x0` (x_t) may be real.
          - Step 0 uses `(enc(x_{t-1}), enc(x_t))`; Step 1 uses `(enc(x_t), z_hat_1)`;
            from Step 2 onward, BOTH history entries are strictly the model's own outputs.
          - `rollout_mode="plain"`: raw latent feed-forward.
          - `rollout_mode="reencode"` (`reencode_res`): projects intermediate imagined latents
            back onto the encoder manifold via `encode(clamp(x0 + decode(z_next) - dec0, 0, 1))`.
            Bit-identical to `plain` at `k = 1`.
        """
        if rollout_mode not in ROLLOUT_MODES:
            raise ValueError(f"Unknown rollout_mode {rollout_mode!r}; expected one of {ROLLOUT_MODES}")
        if acts_k.ndim not in (2, 3) or acts_k.shape[1] < 1:
            raise ValueError(f"Expected acts_k shape [B, k>=1] or [B, k>=1, {self.cond_dim}], got {tuple(acts_k.shape)}")
        if self.n_history == 2:
            if x_prev is None:
                raise ValueError("n_history=2 rollout requires explicit x_prev (pass x_prev=x0 at episode start)")
            if x_prev.shape != x0.shape:
                raise ValueError(f"x_prev shape {tuple(x_prev.shape)} != x0 shape {tuple(x0.shape)}")

        k = acts_k.shape[1]
        if wm_grad or (not torch.is_grad_enabled()):
            z0 = self.encode(x0)
            dec0 = self.decode(z0)
            z_prev = self.encode(x_prev) if self.n_history == 2 else None
            z = z0
            for step in range(k):
                z_next = self.imagine_step(z, acts_k[:, step], z_prev=z_prev, wm_grad=wm_grad)
                if rollout_mode == "reencode" and step < k - 1:
                    dec_s = self.decode(z_next)
                    pred_s = x0 + (dec_s - dec0)
                    z_next_feed = self.encode(pred_s.clamp(0.0, 1.0))
                else:
                    z_next_feed = z_next
                if self.n_history == 2:
                    z_prev = z
                z = z_next_feed
            pred_abs = self.decode(z)
            pred_res = x0 + (pred_abs - dec0)
        else:
            with torch.no_grad():
                x0_det = x0.detach()
                z0 = self.encode(x0_det)
                dec0 = self.decode(z0)
                z_prev = self.encode(x_prev.detach()) if self.n_history == 2 else None
            detached_dyn = {
                **{k_: v.detach() for k_, v in self.dynamics.named_parameters()},
                **{k_: v.detach() for k_, v in self.dynamics.named_buffers()},
            }
            detached_dec = {
                **{k_: v.detach() for k_, v in self.decoder.named_parameters()},
                **{k_: v.detach() for k_, v in self.decoder.named_buffers()},
            }
            detached_enc = (
                {
                    **{k_: v.detach() for k_, v in self.encoder.named_parameters()},
                    **{k_: v.detach() for k_, v in self.encoder.named_buffers()},
                }
                if rollout_mode == "reencode"
                else None
            )
            z = z0
            for step in range(k):
                a_emb = self._resolve_action_emb(acts_k[:, step], detach_lookup=True)
                z_next = functional_call(self.dynamics, detached_dyn, (z, a_emb, z_prev))
                if rollout_mode == "reencode" and step < k - 1:
                    dec_s = functional_call(self.decoder, detached_dec, (z_next,))
                    pred_s = x0_det + (dec_s - dec0)
                    z_next_feed = functional_call(self.encoder, detached_enc, (pred_s.clamp(0.0, 1.0),))
                else:
                    z_next_feed = z_next
                if self.n_history == 2:
                    z_prev = z
                z = z_next_feed
            pred_abs = functional_call(self.decoder, detached_dec, (z,))
            pred_res = x0_det + (pred_abs - dec0)

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
