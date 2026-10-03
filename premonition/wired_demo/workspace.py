"""Workspace record: the shared input contract (reasoner design; vision and audio produce the same).

claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import torch

WIDTH = 256
SEGMENTS = {"question": 0, "notebook": 1, "example": 2, "tool_result": 3,
            "register": 4, "text": 5, "image": 6, "audio": 7}
PRODUCER_ROLES = (0, 1, 2, 3)
NO_POS = -1.0


@dataclass
class Workspace:
    tokens: torch.Tensor    # float32 [B,N,256]; invalid rows exactly 0
    segment: torch.Tensor   # int64   [B,N,2]  (role id, modality id)
    coords: torch.Tensor    # float32 [B,N,3]  (row, col, time); -1 = no position
    valid: torch.Tensor     # bool    [B,N]    right padding only
    provenance: list = field(default_factory=list)  # host metadata, never a model input

    @property
    def role(self): return self.segment[..., 0]

    @property
    def modality(self): return self.segment[..., 1]

    def validate(self):
        b, n, w = self.tokens.shape
        assert w == WIDTH and self.tokens.dtype == torch.float32, "tokens must be float32 [B,N,256]"
        assert self.segment.shape == (b, n, 2) and self.segment.dtype == torch.int64
        assert self.coords.shape == (b, n, 3) and self.coords.dtype == torch.float32
        assert self.valid.shape == (b, n) and self.valid.dtype == torch.bool
        assert (self.segment >= 0).all() and (self.segment < len(SEGMENTS)).all(), "unknown segment id"
        assert bool((self.tokens[~self.valid] == 0).all()), "padded rows must be exactly 0"
        for i in range(b):  # right padding only
            k = int(self.valid[i].sum())
            assert bool(self.valid[i, :k].all()) and not bool(self.valid[i, k:].any()), "right padding only"
        role = self.role[self.valid]
        assert bool(torch.isin(role, torch.tensor(PRODUCER_ROLES)).all()), "producer rows need role 0..3"
        return self

    @staticmethod
    def cat(a: "Workspace", b: "Workspace") -> "Workspace":
        """Concatenate along N per item (valid rows of a, then valid rows of b), re-padded."""
        rows = []
        for i in range(a.tokens.shape[0]):
            ka, kb = int(a.valid[i].sum()), int(b.valid[i].sum())
            rows.append([torch.cat([a.tokens[i, :ka], b.tokens[i, :kb]]),
                         torch.cat([a.segment[i, :ka], b.segment[i, :kb]]),
                         torch.cat([a.coords[i, :ka], b.coords[i, :kb]])])
        return Workspace.pad(rows)

    @staticmethod
    def pad(rows) -> "Workspace":
        """rows: list of [tokens [n,256], segment [n,2], coords [n,3]] -> padded batch."""
        n = max(r[0].shape[0] for r in rows)
        b = len(rows)
        tokens = torch.zeros(b, n, WIDTH); segment = torch.zeros(b, n, 2, dtype=torch.int64)
        coords = torch.full((b, n, 3), NO_POS); valid = torch.zeros(b, n, dtype=torch.bool)
        for i, (t, s, c) in enumerate(rows):
            k = t.shape[0]
            tokens[i, :k] = t; segment[i, :k] = s; coords[i, :k] = c; valid[i, :k] = True
        return Workspace(tokens, segment, coords, valid)
