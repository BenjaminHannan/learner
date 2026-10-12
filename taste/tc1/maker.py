"""Small causal transformer that writes Paint programs."""
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from .paint import PAD, BOS, END, VOCAB, CTX, random_programs, encode_batch


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h, self.hd = h, d // h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.fc1, self.fc2 = nn.Linear(d, 4 * d), nn.Linear(4 * d, d)

    def _qkv(self, x):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, self.hd).permute(2, 0, 3, 1, 4)
        return q, k, v

    def _out(self, x, a):
        B, T, D = x.shape
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        return x + self.fc2(F.gelu(self.fc1(self.ln2(x))))

    def forward(self, x):
        q, k, v = self._qkv(x)
        return self._out(x, F.scaled_dot_product_attention(q, k, v, is_causal=True))

    def step(self, x, cache, t):
        q, k, v = self._qkv(x)                       # (B,h,1,hd)
        cache[0][:, :, t] = k[:, :, 0]
        cache[1][:, :, t] = v[:, :, 0]
        a = F.scaled_dot_product_attention(q, cache[0][:, :, :t + 1], cache[1][:, :, :t + 1])
        return self._out(x, a)


class Maker(nn.Module):
    def __init__(self, d=128, layers=4, heads=4, ctx=CTX):
        super().__init__()
        self.d, self.heads, self.ctx = d, heads, ctx
        self.tok = nn.Embedding(VOCAB, d)
        self.pos = nn.Embedding(ctx, d)
        self.blocks = nn.ModuleList([Block(d, heads) for _ in range(layers)])
        self.lnf = nn.LayerNorm(d)
        self.head = nn.Linear(d, VOCAB)
        self.apply(self._init)

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)
            if getattr(m, "bias", None) is not None:
                nn.init.zeros_(m.bias)

    def n_params(self):
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx):
        x = self.tok(idx) + self.pos(torch.arange(idx.shape[1]))
        for b in self.blocks:
            x = b(x)
        return self.head(self.lnf(x))

    def loss(self, x, reduce=True):
        """x: (B, CTX) int64 rows (BOS prog PAD...). Mean per-token CE over non-PAD targets."""
        L = int((x != PAD).sum(1).max())
        x = x[:, :L]
        logits = self(x[:, :-1])
        return F.cross_entropy(logits.reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                               ignore_index=PAD, reduction="mean" if reduce else "sum")

    @torch.no_grad()
    def nll(self, programs, chunk=1000):
        """Per-token loss over a list of token lists (no BOS, END-terminated) or an encoded array."""
        x = programs if isinstance(programs, torch.Tensor) else \
            torch.from_numpy(encode_batch(programs) if not isinstance(programs, np.ndarray) else programs)
        tot, cnt = 0.0, 0
        for i in range(0, len(x), chunk):
            xb = x[i:i + chunk]
            tot += float(self.loss(xb, reduce=False))
            cnt += int((xb[:, 1:] != PAD).sum())
        return tot / cnt

    @torch.no_grad()
    def sample(self, n, temperature=1.0, generator=None, chunk=1024):
        """n token lists (no BOS), cut after END (or at CTX-1 tokens if END never came).
        generator: np.random.Generator, or an (n, CTX-1) array of uniforms (shared random streams)."""
        L = self.ctx - 1
        if isinstance(generator, np.ndarray):
            U = generator
        else:
            U = (generator or np.random.default_rng()).random((n, L))
        assert U.shape[0] == n and U.shape[1] >= L
        results = []
        hd = self.d // self.heads
        for s in range(0, n, chunk):
            u = torch.from_numpy(np.ascontiguousarray(U[s:s + chunk, :L])).float()
            B = u.shape[0]
            cache = [(torch.zeros(B, self.heads, self.ctx, hd), torch.zeros(B, self.heads, self.ctx, hd))
                     for _ in self.blocks]
            tok = torch.full((B,), BOS, dtype=torch.long)
            out = torch.zeros(B, L, dtype=torch.long)
            done = torch.zeros(B, dtype=torch.bool)
            for t in range(L):
                x = (self.tok(tok) + self.pos.weight[t])[:, None, :]
                for b, c in zip(self.blocks, cache):
                    x = b.step(x, c, t)
                logits = self.head(self.lnf(x))[:, 0]
                probs = torch.softmax(logits / temperature, dim=-1)
                nxt = (probs.cumsum(-1) < u[:, t:t + 1]).sum(-1).clamp(max=VOCAB - 1)
                nxt[done] = PAD
                out[:, t] = nxt
                done |= nxt == END
                tok = nxt
                if bool(done.all()):
                    break
            for row in out.tolist():
                if END in row:
                    row = row[:row.index(END) + 1]
                results.append(row)
        return results


def train_steps(model, opt, batch_fn, steps, lr_fn=None, grad_clip=1.0):
    model.train()
    last = float("nan")
    for s in range(steps):
        if lr_fn is not None:
            for g in opt.param_groups:
                g["lr"] = lr_fn(s)
        loss = model.loss(batch_fn(s))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if grad_clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()
        last = float(loss.detach())
    model.eval()
    return last


def pretrain(cfg, seed, log=print):
    """Day-0 pretraining. Returns (state_dict, replay_pool, heldout, info). Pool and held-out
    programs are drawn from the same rng after the pretraining set, never overlapping by construction
    of the stream (independent draws)."""
    rng = np.random.default_rng([seed, 1])
    torch.manual_seed(seed)
    train = encode_batch(random_programs(rng, cfg.pretrain_programs))
    pool = encode_batch(random_programs(rng, cfg.pool))
    heldout = encode_batch(random_programs(rng, cfg.heldout))
    model = Maker()
    log(f"maker parameters: {model.n_params()}")
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.pretrain_lr, weight_decay=cfg.weight_decay)
    per_epoch = cfg.pretrain_programs // cfg.pretrain_batch
    total = per_epoch * cfg.pretrain_epochs
    order = np.concatenate([rng.permutation(cfg.pretrain_programs)[:per_epoch * cfg.pretrain_batch]
                            for _ in range(cfg.pretrain_epochs)])
    train_t = torch.from_numpy(train)

    def lr_fn(s):
        c = 0.5 * (1 + math.cos(math.pi * s / max(total - 1, 1)))
        return cfg.pretrain_lr_min + (cfg.pretrain_lr - cfg.pretrain_lr_min) * c

    def batch_fn(s):
        return train_t[torch.from_numpy(order[s * cfg.pretrain_batch:(s + 1) * cfg.pretrain_batch])]

    import time
    t0 = time.time()
    last = 0.0
    chunk = 100
    s = 0
    while s < total:
        n = min(chunk, total - s)
        base = s
        last = train_steps(model, opt, lambda i, base=base: batch_fn(base + i), n,
                           lr_fn=lambda i, base=base: lr_fn(base + i), grad_clip=cfg.grad_clip)
        s += n
        log(f"pretrain step {s}/{total} loss {last:.4f} ({time.time() - t0:.0f}s)")
    info = {"steps": total, "seconds": time.time() - t0, "final_train_loss": last,
            "n_params": model.n_params(), "sec_per_step": (time.time() - t0) / max(total, 1)}
    return model.state_dict(), torch.from_numpy(pool), torch.from_numpy(heldout), info
