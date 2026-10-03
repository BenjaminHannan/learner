"""Shared Workspace contract v1 (PR #23 section 6, settled 2026-10-03). Design prototype, CPU only, untested on GPU.

One record for every input kind. Each vector has a (role, modality) id pair, summed as two zero-init embeddings.
coords are (row, col, time) with one validity flag per axis. Row/col offsets count only between tokens of the
same (role, modality); time is seconds relative to now (<= 0) and is compared across sources in signed log buckets.
The core-side bias (neutral index per axis, buckets) belongs to the reasoner thread; this file only builds records.
"""
from __future__ import annotations
from dataclasses import dataclass
import torch
from torch import nn

ROLES = {"question": 0, "notebook": 1, "example": 2, "tool_result": 3, "register": 4, "action": 5}
MODALITIES = {"text": 0, "image": 1, "audio": 2}
ROW, COL, TIME = 0, 1, 2


@dataclass
class Workspace:
    tokens: torch.Tensor        # [B,N,256] float
    role: torch.Tensor          # [B,N] long, from ROLES
    modality: torch.Tensor      # [B,N] long, from MODALITIES
    coords: torch.Tensor        # [B,N,3] float (row, col, time in seconds, time <= 0)
    coord_valid: torch.Tensor   # [B,N,3] bool, one flag per axis; False -> that axis uses its neutral bias
    valid: torch.Tensor         # [B,N] bool (padding mask)

    def check(self):
        b, n, d = self.tokens.shape
        assert d == 256
        assert self.role.shape == self.modality.shape == self.valid.shape == (b, n)
        assert self.coords.shape == self.coord_valid.shape == (b, n, 3)
        assert self.coord_valid.dtype == torch.bool and self.valid.dtype == torch.bool
        t = self.coords[..., TIME][self.coord_valid[..., TIME]]
        assert (t <= 0).all(), "time is relative to now, so it must be <= 0"
        return self

    def cat(self, other: "Workspace") -> "Workspace":
        return Workspace(*(torch.cat((getattr(self, f), getattr(other, f)), 1) for f in
                           ("tokens", "role", "modality", "coords", "coord_valid", "valid"))).check()


class SegmentEmbedding(nn.Module):
    """Embedding(role) + Embedding(modality), both zero-init so a workspace is unchanged at initialisation."""
    def __init__(self, width=256):
        super().__init__()
        self.role, self.modality = nn.Embedding(len(ROLES), width), nn.Embedding(len(MODALITIES), width)
        nn.init.zeros_(self.role.weight); nn.init.zeros_(self.modality.weight)

    def forward(self, ws: Workspace):
        return ws.tokens + self.role(ws.role) + self.modality(ws.modality)


def image_to_workspace(latent_tokens, grid, role="notebook", time_s=None):
    """latent_tokens [B,H*W,256] from GridAdapter (flattened grid) -> Workspace.

    Row and col are the patch position. A still image has time absent (time_s=None); a video frame passes
    its time in seconds relative to now (<= 0), shared by all its patches.
    """
    b, n, _ = latent_tokens.shape
    h, w = grid
    assert h * w == n
    rr = torch.arange(h).repeat_interleave(w).float(); cc = torch.arange(w).repeat(h).float()
    t = torch.full((n,), float(time_s or 0.0))
    coords = torch.stack((rr, cc, t), -1).expand(b, n, 3).clone()
    cv = torch.tensor([True, True, time_s is not None]).expand(b, n, 3).clone()
    ids = lambda v: torch.full((b, n), v, dtype=torch.long)
    return Workspace(latent_tokens, ids(ROLES[role]), ids(MODALITIES["image"]), coords, cv,
                     torch.ones(b, n, dtype=torch.bool)).check()


def same_source_mask(ws: Workspace):
    """[B,N,N] bool: True where row/col offsets count (same role and modality, both have the axis).
    Reference for the reasoner thread's bias; elsewhere row/col use the neutral index."""
    same = (ws.role[:, :, None] == ws.role[:, None]) & (ws.modality[:, :, None] == ws.modality[:, None])
    rc = ws.coord_valid[..., ROW] & ws.coord_valid[..., COL]
    return same & rc[:, :, None] & rc[:, None]
