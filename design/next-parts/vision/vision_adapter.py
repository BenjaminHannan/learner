"""Vision -> reasoner adapter (design prototype, CPU only).

Thin translator: frozen image encoder patch features -> [B,H,W,256] latent that
AttentionReasoner.begin_latent already accepts. No reasoning happens here.
Modality-agnostic contract: any encoder that yields [B,N,D] features on a known
(gh,gw) grid (or a 1-D sequence, gw=None) can use GridAdapter.
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F

LATENT_WIDTH = 256
MODALITIES = {"text": 0, "image": 1, "audio": 2}


def pos2d(h, w, width=LATENT_WIDTH):
    """Fixed sin-cos 2D position code [h,w,width] (row half, col half). Zero parameters."""
    q = width // 2
    def axis(n, dim):
        f = torch.exp(-torch.arange(0, dim, 2).float() / dim * 6.9078)
        a = torch.arange(n).float()[:, None] * f[None]
        return torch.cat((a.sin(), a.cos()), 1)
    return torch.cat((axis(h, q)[:, None].expand(h, w, q), axis(w, q)[None].expand(h, w, q)), -1)


class GridAdapter(nn.Module):
    def __init__(self, enc_dim, grid=(8, 8), hidden=32, modality="image", width=LATENT_WIDTH, pos_scale=0.1):
        super().__init__()
        self.grid, self.width = tuple(grid), width
        self.proj = nn.Sequential(nn.LayerNorm(enc_dim), nn.Linear(enc_dim, hidden), nn.GELU(), nn.Linear(hidden, width))
        self.modality = nn.Embedding(len(MODALITIES), width)
        self.register_buffer("modality_id", torch.tensor(MODALITIES[modality]), persistent=False)
        nn.init.zeros_(self.modality.weight)  # zero-init: matches DESIGN.md and workspace.SegmentEmbedding
        # Raw pos2d has norm ~11.3 per slot (10.3 shared by all slots) vs ~3.4 for adapter content, so it is
        # scaled by a learned scalar starting at 0.1 (review R1). Only used in notebook mode, as a stopgap
        # until the core reads Workspace.coords.
        self.pos_scale = nn.Parameter(torch.tensor(float(pos_scale)))

    def forward(self, feats, src_grid, as_notebook=False):
        """feats [B,N,D] with N == gh*gw -> latent [B,H,W,width] on the fixed target grid."""
        b, n, d = feats.shape
        gh, gw = src_grid
        if gh * gw != n:
            raise ValueError(f"{n} patches do not fit grid {src_grid}")
        x = feats.reshape(b, gh, gw, d).permute(0, 3, 1, 2)
        if (gh, gw) != self.grid:  # area pooling keeps every source patch's contribution
            x = F.adaptive_avg_pool2d(x, self.grid)
        x = x.permute(0, 2, 3, 1)
        out = self.proj(x) + self.modality(self.modality_id)
        if as_notebook:  # notebook slots have no geometry in begin_latent, so add the fixed position code
            out = out + self.pos_scale * pos2d(*self.grid, self.width).to(out)
            return out.flatten(1, 2)  # [B,H*W,width]
        return out


class FrozenPatchEncoder(nn.Module):
    """Offline stand-in for a frozen pretrained ViT: strided conv, random, frozen.
    Swap for SigLIP/DINOv2 on a GPU machine; interface (images -> [B,N,D], grid) is identical."""
    def __init__(self, dim=96, patch=8):
        super().__init__()
        self.patch = patch
        self.conv = nn.Conv2d(3, dim, patch, patch)
        for p in self.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def forward(self, images):
        f = self.conv(images)
        b, d, gh, gw = f.shape
        return f.flatten(2).transpose(1, 2), (gh, gw)
