#!/usr/bin/env python3
"""rsn-358i (sleep research thread, 2026-09-26): rsn-358g (358a v2 + grid legend fix, scripts/claude_rsn358g_run.py)
with ONE design change, in attention: half of each layer's heads see only cells within 1 column.

Why: Ben's Mac-probe report (12:26 UTC) and the code (scripts/claude_rsn358a_run.py:39, :90-91): attention tells
cells apart only up to 4 columns away. Practice sums are at most 5 columns wide, so on wider pages the "4 or more
away" group fills with cells the nets never had to sort out, and wide sums collapse even for sums the nets know.
Heads that see only their own and the next column carry a sum one column per step, which works at any width. The
other half of the heads stay as they were (every cell, offset bias clipped at 4), because a grid cell must see its
whole row and column. Chosen in an unregistered small CPU trial (artifacts/claude-rsn358i-20260926/trial/) over
"fading with distance", which hurt grids. The grid legend fix (358g, never run) is a test-validity repair both arms
get. Everything else (nets' sizes, data, steps, stop rule v2) is 358g's. Ben chose this order (12:28 UTC).
Report-only extra tests: sums10 and sums12 (fresh seeds).

  python -B scripts/claude_rsn358i_run.py make-tests --out artifacts/claude-rsn358i-20260926/tests
  python -B scripts/claude_rsn358i_run.py train|eval|smoke ...   (same arguments as claude_rsn358a_run.py)
  python -B scripts/claude_rsn358i_run.py check-mask   (the narrow heads really ignore cells 2+ columns away)
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358g_run as G  # noqa: E402  (legend grids + v2 stop rule)

R, E = G.R, G.E
WINDOW = 1
R.TESTS += [("sums10", "sums", 10, 35814, "report"), ("sums12", "sums", 12, 35815, "report")]


def forward(self, x, dr, dc):
    B, T, D = x.shape
    q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
    bias = self.br[:, dr] + self.bc[:, dc]
    far = (dc - R.CLIP).abs() > WINDOW                                  # dc holds clipped offset + CLIP
    narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
    narrow[: self.h // 2] = True
    bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0).to(q.dtype)
    a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
    x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
    return x + self.mlp(self.ln2(x))


R.Block.forward = forward


def check_mask():
    torch.manual_seed(0)
    b = R.Block(64, 8)
    H, W = 3, 9
    dr, dc = R.Net.offsets(H, W, "cpu")
    x = torch.randn(1, H * W, 64)
    base = b(x, dr, dc)
    x2 = x.clone()
    x2[0, [r * W + 8 for r in range(H)]] += 5.0                        # change every cell in column 8
    q, k, v = b.qkv(b.ln1(x)).view(1, H * W, 3, 8, 8).permute(2, 0, 3, 1, 4)
    q2, k2, v2 = b.qkv(b.ln1(x2)).view(1, H * W, 3, 8, 8).permute(2, 0, 3, 1, 4)
    bias = (b.br[:, dr] + b.bc[:, dc])
    far = (dc - R.CLIP).abs() > WINDOW
    for h in range(4):
        m = bias[h].masked_fill(far, float("-inf"))
        a1 = F.scaled_dot_product_attention(q[:, h:h + 1], k[:, h:h + 1], v[:, h:h + 1], attn_mask=m)
        a2 = F.scaled_dot_product_attention(q2[:, h:h + 1], k2[:, h:h + 1], v2[:, h:h + 1], attn_mask=m)
        col0 = [r * W for r in range(H)]
        assert torch.allclose(a1[0, 0, col0], a2[0, 0, col0]), h        # column 0 cannot see column 8
    assert not torch.allclose(base, b(x2, dr, dc))
    print("check-mask ok: narrow heads 0-3 ignore cells 2+ columns away; wide heads 4-7 unchanged")


if __name__ == "__main__":
    if sys.argv[1:] == ["check-mask"]:
        check_mask()
    elif sys.argv[1:] == ["audit"]:
        G.audit()
    else:
        R.main()
