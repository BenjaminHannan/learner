"""Verbatim source Block/Net definitions for interface contracts; no fitting/data imports."""
import torch
from torch import nn
from torch.nn import functional as F
from types import SimpleNamespace
E=SimpleNamespace(VOCAB=125)
CLIP, WINDOW=4,1
ARMS={"plain":dict(d=128,layers=8,heads=8),"loop":dict(d=256,layers=2,heads=8)}

class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
        narrow[: self.h // 2] = True
        bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        c = ARMS[arm]
        self.arm, d = arm, c["d"]
        self.tok = nn.Embedding(E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        self.blocks = nn.ModuleList(Block(d, c["heads"]) for _ in range(c["layers"]))
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, E.VOCAB)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    @staticmethod
    def offsets(H, W, device):
        r = torch.arange(H, device=device).repeat_interleave(W)
        c = torch.arange(W, device=device).repeat(H)
        dr = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dc = (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP
        return dr, dc

    def embed(self, tokens, slot):
        B, H, W = tokens.shape
        return self.tok(tokens.view(B, -1)) + self.slot(slot.view(B, -1)), self.offsets(H, W, tokens.device)

    def step(self, h, e, dr, dc):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc)
        return self.ln_state(z)

    def read(self, h):
        z = self.ln_out(h)
        logits = self.head(z)
        q = self.halt(z.mean(1)).squeeze(-1) if self.arm == "loop" else None
        return logits, q

    def plain_forward(self, tokens, slot):
        h, (dr, dc) = self.embed(tokens, slot)
        for b in self.blocks:
            h = b(h, dr, dc)
        return self.read(h)[0]

    def forward(self, tokens, positions):
        """Plug-in API: return lists of [B,T,V] cell and [B] stop logits.

        `positions` is the binary fill-slot grid, not a family label. Plain
        models return one set of cell logits and no stop logits.
        """
        if self.arm == "plain":
            return [self.plain_forward(tokens, positions)], []
        e, (dr, dc) = self.embed(tokens, positions)
        h = torch.zeros_like(e)
        cells, stops = [], []
        for _ in range(48):
            h = self.step(h, e, dr, dc)
            cell, stop = self.read(h)
            cells.append(cell)
            stops.append(stop)
        return cells, stops

    def weight_count(self):
        return sum(p.numel() for p in self.parameters())

    @torch.no_grad()
    def infer_rounds(self, tokens, positions, n=48):
        return self.loop_rounds(tokens, positions, n)

    def loop_train(self, tokens, slot, n_free, n_grad):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), dr, dc)
        h = h.detach()
        outs = []
        for _ in range(n_grad):
            h = self.step(h, e, dr, dc)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, n):
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        preds, qs = [], []
        for _ in range(n):
            h = self.step(h, e, dr, dc)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)       # [B, n, T], [B, n]

