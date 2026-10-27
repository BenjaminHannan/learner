"""Exp 101 talker model: plain-PyTorch decoder-only LM + pointer-generator copy head.

Config (SimpleStories-30M-like): 10 layers, d=512, 8 heads, RoPE, pre-norm
RMSNorm, SwiGLU MLP, tied embeddings, context 512, vocab 4096.
Copy head (pointer-generator switch, See et al. 2017; pointer-sentinel style for
pretraining where input == preceding context): p_gen = sigmoid(w.h + b) mixes
the vocab softmax with a copy distribution = causal attention of the last-layer
hidden state (dedicated query/key proj) over previous positions, scattered onto
the vocab ids that appear there. No `transformers` import anywhere.
"""
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

CFG = dict(vocab=4096, d=512, layers=10, heads=8, d_ff=1024, ctx=512,
           rope_theta=10000.0, dropout=0.0)


class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.w = nn.Parameter(torch.ones(d))
        self.eps = eps

    def forward(self, x):
        return self.w * x / torch.sqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)


def rope_cache(ctx, hd, theta, device, dtype):
    inv = 1.0 / (theta ** (torch.arange(0, hd, 2, device=device).float() / hd))
    t = torch.arange(ctx, device=device).float()
    f = torch.einsum("i,j->ij", t, inv)
    return torch.cos(f).to(dtype), torch.sin(f).to(dtype)


def apply_rope(x, cos, sin):
    # x: (B,H,T,hd); cos/sin: (T,hd/2)
    t = x.shape[2]
    c, s = cos[:t], sin[:t]
    x1, x2 = x[..., ::2], x[..., 1::2]
    o = torch.stack([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)
    return o.flatten(-2)


class Block(nn.Module):
    def __init__(self, d, heads, d_ff, dropout):
        super().__init__()
        self.n1, self.n2 = RMSNorm(d), RMSNorm(d)
        self.heads, self.hd = heads, d // heads
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.o = nn.Linear(d, d, bias=False)
        self.gate = nn.Linear(d, d_ff, bias=False)
        self.up = nn.Linear(d, d_ff, bias=False)
        self.down = nn.Linear(d_ff, d, bias=False)
        self.drop = nn.Dropout(dropout)

    def forward(self, x, cos, sin):
        B, T, d = x.shape
        h = self.n1(x)
        q, k, v = self.qkv(h).view(B, T, 3, self.heads, self.hd).unbind(2)
        q = apply_rope(q.transpose(1, 2), cos, sin)
        k = apply_rope(k.transpose(1, 2), cos, sin)
        v = v.transpose(1, 2)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.drop(self.o(y.transpose(1, 2).reshape(B, T, d)))
        h = self.n2(x)
        x = x + self.drop(self.down(F.silu(self.gate(h)) * self.up(h)))
        return x


class Talker101(nn.Module):
    def __init__(self, cfg=CFG):
        super().__init__()
        self.cfg = dict(cfg)
        d, V = cfg["d"], cfg["vocab"]
        self.emb = nn.Embedding(V, d)
        self.blocks = nn.ModuleList(
            [Block(d, cfg["heads"], cfg["d_ff"], cfg["dropout"]) for _ in range(cfg["layers"])])
        self.norm = RMSNorm(d)
        self.drop = nn.Dropout(cfg["dropout"])
        # copy head: dedicated query/key over last-layer states + p_gen switch
        self.copy_q = nn.Linear(d, d, bias=False)
        self.copy_k = nn.Linear(d, d, bias=False)
        self.pgen = nn.Linear(d, 1)
        self.ctx = cfg["ctx"]
        self._init_weights(cfg["layers"])

    def _init_weights(self, n_layers):
        # GPT-2-style: small residual branches so step-0 logits are near-uniform
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, std=0.02)
        for b in self.blocks:
            nn.init.normal_(b.o.weight, std=0.02 / math.sqrt(2 * n_layers))
            nn.init.normal_(b.down.weight, std=0.02 / math.sqrt(2 * n_layers))
        nn.init.constant_(self.pgen.bias, 2.0)  # start as ~pure LM (p_gen~=0.88), earn copy

    def forward(self, idx, targets=None):
        # idx: (B,T); returns dict(logits_vocab, p_gen, copy_attn, loss)
        B, T = idx.shape
        cfg = self.cfg
        x = self.drop(self.emb(idx))
        cos, sin = rope_cache(T, cfg["d"] // cfg["heads"], cfg["rope_theta"],
                              idx.device, x.dtype)
        for b in self.blocks:
            x = b(x, cos, sin)
        h = self.norm(x)
        logits = h @ self.emb.weight.t()  # tied embeddings
        q = self.copy_q(h) / math.sqrt(cfg["d"])
        k = self.copy_k(h)
        scores = q @ k.transpose(1, 2)  # (B,T,T) causal
        scores = scores.masked_fill(
            torch.tril(torch.ones(T, T, device=idx.device, dtype=torch.bool)).logical_not(),
            float("-inf"))
        # position 0 has no previous context: copy from itself is fine (still causal)
        copy_attn = torch.softmax(scores, dim=-1)
        p_gen = torch.sigmoid(self.pgen(h))  # (B,T,1)
        out = {"logits": logits, "p_gen": p_gen, "copy_attn": copy_attn}
        if targets is not None:
            # Caller passes next-token-shifted targets with targets.shape == idx.shape.
            # Position t mixes vocab prediction with copy over context positions <= t.
            tgt = targets  # (B,T)
            logp_vocab = torch.log_softmax(logits, dim=-1)
            pv = logp_vocab.gather(-1, tgt.unsqueeze(-1)).squeeze(-1).exp()  # (B,T)
            match = (idx.unsqueeze(1) == tgt.unsqueeze(2))  # (B,T,T)
            pc = (copy_attn * match).sum(-1).clamp_min(1e-12)
            pg = p_gen[..., 0]
            mix = (pg * pv + (1 - pg) * pc).clamp_min(1e-12)
            out["loss"] = -torch.log(mix).mean()
            out["p_gen_mean"] = pg.mean()
        return out

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


def count_params(cfg=CFG):
    m = Talker101(cfg)
    n = m.param_count()
    per = {}
    per["embedding(tied)"] = m.emb.weight.numel()
    per["blocks"] = sum(p.numel() for b in m.blocks for p in b.parameters())
    per["final_norm"] = m.norm.w.numel()
    per["copy_head"] = (m.copy_q.weight.numel() + m.copy_k.weight.numel()
                        + m.pgen.weight.numel() + m.pgen.bias.numel())
    return n, per


if __name__ == "__main__":
    n, per = count_params()
    print(f"total_params={n} ({n/1e6:.2f}M)")
    for k, v in per.items():
        print(f"  {k}: {v}")
