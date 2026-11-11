"""Story reasoner for the two-doors test. Core copied from reasoner_fresh/model.py (PR #29): reader -> 4 loops of a
shared 2-block width-256 core (MoE MLP, 8 experts top-2) -> exit into a frozen LM. No calculator.

Arms (one change each against A):
  A   today: positions -> 256->32->LM, adaptive-average-pooled to 8 prefix vectors.
  B   pointer exit: A + 8 pointer vectors. Slot k scores each position (Linear 256->8 on the final state), softmax
      over valid positions, value = the frozen LM's own input embedding of the token there.
  C   sharper averages: the 8 pooled vectors use learned softmax weights over positions (8 queries) instead of
      fixed average segments.
  W   wider door in: reader hidden width 32 -> 256.
  BW  B + W.
"""
import copy, math
import torch
from torch import nn
from torch.nn import functional as F

CLIP, WINDOW, D, LOOPS, K = 4, 1, 256, 4, 8


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc, key_ok):
        B, T, Dm = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, Dm // self.h).permute(2, 0, 3, 1, 4)
        bias = self.br[:, dr] + self.bc[:, dc]
        far = (dc - CLIP).abs() > WINDOW
        narrow = torch.zeros(self.h, 1, 1, dtype=torch.bool, device=x.device)
        narrow[: self.h // 2] = True
        bias = bias.masked_fill(narrow & far, float("-inf")).unsqueeze(0)
        bias = bias.masked_fill(~key_ok[:, None, None, :], float("-inf")).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, Dm))
        return x + self.mlp(self.ln2(x))


class UpcycledMLP(nn.Module):
    def __init__(self, mlp, width=256, experts=8, active=2):
        super().__init__()
        self.active = active
        self.experts = nn.ModuleList(copy.deepcopy(mlp) for _ in range(experts))
        self.router = nn.Linear(width, experts)
        nn.init.zeros_(self.router.weight); nn.init.zeros_(self.router.bias)
        self.aux = torch.zeros(())

    def forward(self, x):
        shape = x.shape; x = x.reshape(-1, shape[-1])
        logits = self.router(x).float()
        values, ids = logits.topk(self.active, -1)
        weights = values.softmax(-1).to(x.dtype)
        out = torch.zeros_like(x)
        for i, expert in enumerate(self.experts):
            positions, slots = torch.where(ids == i)
            if positions.numel():
                out = out.index_add(0, positions, expert(x[positions]) * weights[positions, slots, None])
        fraction = F.one_hot(ids, len(self.experts)).float().mean((0, 1)).detach()
        self.aux = .001 * len(self.experts) * (fraction * logits.softmax(-1).mean(0)).sum()
        return out.reshape(shape)


class StoryReasoner(nn.Module):
    def __init__(self, lm_width, arm):
        super().__init__()
        assert arm in ("A", "B", "C", "W", "BW")
        self.arm = arm
        self.pointer = arm in ("B", "BW")
        self.learned_pool = arm == "C"
        hid = 256 if arm in ("W", "BW") else 32
        self.reader = nn.Sequential(nn.LayerNorm(lm_width), nn.Linear(lm_width, hid), nn.GELU(), nn.Linear(hid, D))
        self.blocks = nn.ModuleList(Block(D, 8) for _ in range(2))
        for b in self.blocks:
            b.mlp = UpcycledMLP(b.mlp, D, 8, 2)
        self.ln_state = nn.LayerNorm(D)
        self.out_map = nn.Sequential(nn.Linear(D, 32), nn.GELU(), nn.Linear(32, lm_width))
        if self.pointer:
            self.ptr = nn.Linear(D, K)
        if self.learned_pool:
            self.pool_q = nn.Linear(D, K)
            nn.init.zeros_(self.pool_q.weight); nn.init.zeros_(self.pool_q.bias)

    def aux(self):
        return torch.stack([b.mlp.aux for b in self.blocks]).mean()

    def n_prefix(self):
        return 2 * K if self.pointer else K

    def forward(self, feats, qmask, tok_emb, lesion=False):
        """feats [B,T,LM] frozen contextual states; qmask [B,T]; tok_emb [B,T,LM] frozen input embeddings of the same
        tokens (used only by the pointer). Returns prefix [B,n_prefix,LM] and pointer weights [B,K,T] or None."""
        B, T, _ = feats.shape
        dev = feats.device
        q = self.reader(feats.float()) * qmask[..., None]
        r = torch.arange(T, device=dev)
        dc = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dr = torch.full((T, T), CLIP, device=dev, dtype=torch.long)
        h = torch.zeros_like(q)
        for _ in range(LOOPS):
            z = h + q
            for b in self.blocks:
                z = b(z, dr, dc, qmask)
            h = self.ln_state(z)
        hq = self.out_map(h) * qmask[..., None]
        lens = qmask.sum(1)
        if self.learned_pool:
            w = self.pool_q(h).float().masked_fill(~qmask[..., None], -1e4).softmax(1)  # [B,T,K]
            prefix = torch.einsum("btk,btl->bkl", w.to(hq.dtype), hq)
        else:
            prefix = torch.stack([F.adaptive_avg_pool1d(hq[b_, :lens[b_]].T[None], K)[0].T for b_ in range(B)], 0)
        pw = None
        if self.pointer:
            s = self.ptr(h).float().masked_fill(~qmask[..., None], -1e4)  # [B,T,K]
            pw = s.softmax(1)
            if lesion:  # uniform over valid positions: same words, no pointing
                pw = (qmask[..., None].float() / lens[:, None, None].float()).expand(-1, -1, K)
            pv = torch.einsum("btk,btl->bkl", pw.to(tok_emb.dtype), tok_emb)
            prefix = torch.cat([prefix.to(pv.dtype), pv], 1)
            pw = pw.transpose(1, 2)
        return prefix, pw
