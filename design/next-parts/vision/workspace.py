"""Shared Workspace contract (PR #23 section 6 merged with the vision design). Design prototype, CPU only.

One record for every input kind. Segment ids replace the separate modality tag and role of the first
vision draft: one id per (role) and one per modality, both summed as learned zero-init embeddings.
"""
from __future__ import annotations
from dataclasses import dataclass
import torch
from torch import nn

SEGMENTS = {"question": 0, "notebook": 1, "example": 2, "tool_result": 3, "register": 4,
            "text": 5, "image": 6, "audio": 7}


@dataclass
class Workspace:
    tokens: torch.Tensor                 # [B,N,256]
    segment: torch.Tensor                # [B,N,2] long: (role id, modality id) from SEGMENTS
    valid: torch.Tensor                  # [B,N] bool
    coords: torch.Tensor | None = None   # [B,N,3] float (row, col, time); None = neutral "no position"

    def check(self):
        b, n, d = self.tokens.shape
        assert d == 256 and self.segment.shape == (b, n, 2) and self.valid.shape == (b, n)
        assert self.coords is None or self.coords.shape == (b, n, 3)
        return self


class SegmentEmbedding(nn.Module):
    """Zero-init so a text-only workspace is unchanged at initialisation."""
    def __init__(self, width=256):
        super().__init__()
        self.table = nn.Embedding(len(SEGMENTS), width)
        nn.init.zeros_(self.table.weight)

    def forward(self, ws: Workspace):
        return ws.tokens + self.table(ws.segment).sum(2)


def image_to_workspace(latent_tokens, role="notebook", grid=(8, 8)):
    """latent_tokens [B,H*W,256] from GridAdapter(as_notebook=False flattened) -> Workspace with row/col coords."""
    b, n, _ = latent_tokens.shape
    h, w = grid
    rr = torch.arange(h).repeat_interleave(w).float(); cc = torch.arange(w).repeat(h).float()
    coords = torch.stack((rr, cc, torch.zeros(n)), -1).expand(b, n, 3)
    seg = torch.tensor([SEGMENTS[role], SEGMENTS["image"]]).expand(b, n, 2)
    return Workspace(latent_tokens, seg, torch.ones(b, n, dtype=torch.bool), coords).check()
