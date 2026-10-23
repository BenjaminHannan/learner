"""Two small looped transformers (A: d64 reader, B: d96 calculator) joined by a pluggable bridge.

Bridge interface (one instance per direction, sender -> receiver):
  send(x_sender, L) -> msg | None     x_sender [B, L+R, d_s] after loop 1 (L sequence rows, then R registers)
  receive(x_recv, msg, L) -> (x_recv, extra)   extra is None or (rows [B,M,d_r], gates [n_layers]) read by loop-2 attention
msg is a tensor with batch as dim 0, so ablations (off / shuffle / mean) act on it generically. All receivers are zero at init.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from . import task

ARMS = ("none", "ema_const", "pooled", "xattn", "slots")


def rms(x: torch.Tensor) -> torch.Tensor:
    return x / (x.pow(2).mean(-1, keepdim=True).sqrt() + 1e-6)


class Attn(nn.Module):
    """Self-attention; optional gated extra K/V rows (separate softmax, scaled by tanh(gate), so gate 0 == no extra rows exactly)."""
    def __init__(self, d: int, h: int) -> None:
        super().__init__()
        self.h, self.qkv, self.o = h, nn.Linear(d, 3 * d), nn.Linear(d, d)

    def _split(self, x: torch.Tensor):
        B, L, D = x.shape
        return self.qkv(x).view(B, L, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)

    def forward(self, x: torch.Tensor, extra=None) -> torch.Tensor:
        B, L, D = x.shape
        q, k, v = self._split(x)
        y = F.scaled_dot_product_attention(q, k, v)
        if extra is not None:
            e, g = extra
            _, ke, ve = self._split(e)
            y = y + torch.tanh(g) * F.scaled_dot_product_attention(q, ke, ve)
        return self.o(y.transpose(1, 2).reshape(B, L, D))


class Block(nn.Module):
    def __init__(self, d: int, h: int, mlp: int = 2) -> None:
        super().__init__()
        self.ln1, self.ln2, self.attn = nn.LayerNorm(d), nn.LayerNorm(d), Attn(d, h)
        self.mlp = nn.Sequential(nn.Linear(d, mlp * d), nn.GELU(), nn.Linear(mlp * d, d))

    def forward(self, x: torch.Tensor, extra=None) -> torch.Tensor:
        if extra is not None:
            extra = (self.ln1(extra[0]), extra[1])
        x = x + self.attn(self.ln1(x), extra)
        return x + self.mlp(self.ln2(x))


class Module(nn.Module):
    """Pre-LN encoder + R registers, block stack looped twice (shared weights); head reads register 0."""
    def __init__(self, vocab: int, L: int, d: int, R: int = 4, layers: int = 2, heads: int = 4) -> None:
        super().__init__()
        self.L, self.R = L, R
        self.tok, self.pos = nn.Embedding(vocab, d), nn.Parameter(torch.randn(L, d) * 0.02)
        self.reg, self.loop = nn.Parameter(torch.randn(R, d) * 0.02), nn.Parameter(torch.randn(2, d) * 0.02)
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(layers))
        self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, task.NV))

    def embed(self, tokens: torch.Tensor) -> torch.Tensor:
        x = self.tok(tokens) + self.pos
        return torch.cat([x, self.reg.expand(len(x), -1, -1)], 1)

    def run(self, x: torch.Tensor, loop: int, extra=None) -> torch.Tensor:
        x = torch.cat([x[:, :self.L], x[:, self.L:] + self.loop[loop]], 1)
        for i, blk in enumerate(self.blocks):
            x = blk(x, None if extra is None else (extra[0], extra[1][i]))
        return x

    def logits(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(x[:, self.L])


# ------------------------------------------------------------------ bridges
class Bridge(nn.Module):
    def __init__(self, ds: int, dr: int, R: int, layers: int) -> None:
        super().__init__()
        self.ds, self.dr, self.R, self.layers = ds, dr, R, layers

    def send(self, x: torch.Tensor, L: int):
        raise NotImplementedError

    def receive(self, x: torch.Tensor, msg, L: int):
        return x, None


def _zero_linear(i: int, o: int) -> nn.Linear:
    lin = nn.Linear(i, o)
    nn.init.zeros_(lin.weight), nn.init.zeros_(lin.bias)
    return lin


class EmaConst(Bridge):
    """v1/joint.py in spirit: EMA (0.99) of the sender's detached register mean -> RMS-norm -> zero-init Linear, added to every receiver register. Frozen at eval."""
    def __init__(self, ds, dr, R, layers, momentum: float = 0.99) -> None:
        super().__init__(ds, dr, R, layers)
        self.proj, self.mom = _zero_linear(ds, dr), momentum
        self.register_buffer("ctx", torch.zeros(ds)), self.register_buffer("seen", torch.zeros(()))

    def send(self, x, L):
        msg = self.proj(rms(self.ctx)).expand(len(x), -1)
        if self.training:
            with torch.no_grad():
                m = x[:, L:].detach().mean((0, 1))
                self.ctx.copy_(m) if float(self.seen) == 0 else self.ctx.mul_(self.mom).add_(m, alpha=1 - self.mom)
                self.seen.add_(1)
        return msg

    def receive(self, x, msg, L):
        return (x if msg is None else torch.cat([x[:, :L], x[:, L:] + msg[:, None]], 1)), None


class Pooled(Bridge):
    """Per item: sender register 0 (not detached) -> RMS-norm -> zero-init Linear -> added to every receiver register."""
    def __init__(self, ds, dr, R, layers) -> None:
        super().__init__(ds, dr, R, layers)
        self.proj = _zero_linear(ds, dr)

    def send(self, x, L):
        return self.proj(rms(x[:, L]))

    receive = EmaConst.receive


class XAttn(Bridge):
    """Message = sender registers projected to receiver width; receiver registers cross-attend over them, output * tanh(gate), gate init 0."""
    def __init__(self, ds, dr, R, layers, heads: int = 4) -> None:
        super().__init__(ds, dr, R, layers)
        self.proj, self.attn, self.ln = nn.Linear(ds, dr), nn.MultiheadAttention(dr, heads, batch_first=True), nn.LayerNorm(dr)
        self.gate = nn.Parameter(torch.zeros(()))

    def send(self, x, L):
        return self.proj(rms(x[:, L:]))

    def receive(self, x, msg, L):
        if msg is None:
            return x, None
        regs = x[:, L:]
        out, _ = self.attn(self.ln(regs), msg, msg, need_weights=False)
        return torch.cat([x[:, :L], regs + torch.tanh(self.gate) * out], 1), None


class Slots(Bridge):
    """M learned queries read the sender's whole sequence by attention; result -> receiver width; appended to the receiver as extra K/V rows
    in every loop-2 layer, each scaled by its own zero-init tanh gate."""
    def __init__(self, ds, dr, R, layers, M: int = 2, heads: int = 4) -> None:
        super().__init__(ds, dr, R, layers)
        self.q, self.ln = nn.Parameter(torch.randn(M, ds) * 0.02), nn.LayerNorm(ds)
        self.attn, self.out = nn.MultiheadAttention(ds, heads, batch_first=True), nn.Linear(ds, dr)
        self.gates = nn.Parameter(torch.zeros(layers))

    def send(self, x, L):
        h = self.ln(x)
        s, _ = self.attn(self.q.expand(len(x), -1, -1), h, h, need_weights=False)
        return self.out(s)

    def receive(self, x, msg, L):
        return x, (None if msg is None else (msg, self.gates))


BRIDGES = {"ema_const": EmaConst, "pooled": Pooled, "xattn": XAttn, "slots": Slots}
MODES = ("real", "off", "shuffle", "mean")


def ablate(msg, mode: str, gen: torch.Generator | None = None):
    """Apply an eval ablation to a message tensor [B, ...]."""
    if msg is None or mode == "real":
        return msg
    if mode == "off":
        return None
    if mode == "mean":
        return msg.mean(0, keepdim=True).expand_as(msg)
    if mode == "shuffle":
        return msg[derangement(len(msg), gen)]
    raise ValueError(mode)


def derangement(n: int, gen: torch.Generator | None = None) -> torch.Tensor:
    """perm with perm[i] != i for all i (a random cyclic shift of a random order)."""
    order = torch.randperm(n, generator=gen)
    perm = torch.empty(n, dtype=torch.long)
    perm[order] = order.roll(1)
    return perm


class Pair(nn.Module):
    def __init__(self, arm: str, dA: int = 64, dB: int = 96, R: int = 4, layers: int = 2) -> None:
        super().__init__()
        self.arm = arm
        self.A = Module(task.VOCAB_A, task.LEN_A, dA, R, layers)
        self.B = Module(task.VOCAB_B, task.LEN_B, dB, R, layers)
        cls = BRIDGES.get(arm)
        self.ab = cls(dA, dB, R, layers) if cls else None      # A -> B
        self.ba = cls(dB, dA, R, layers) if cls else None      # B -> A

    def forward(self, xa, xb, mode: str = "real", gen: torch.Generator | None = None, return_msgs: bool = False):
        ha, hb = self.A.run(self.A.embed(xa), 0), self.B.run(self.B.embed(xb), 0)
        m_ab = self.ab.send(ha, self.A.L) if self.ab else None
        m_ba = self.ba.send(hb, self.B.L) if self.ba else None
        raw = {"ab": m_ab, "ba": m_ba}
        m_ab, m_ba = ablate(m_ab, mode, gen), ablate(m_ba, mode, gen)
        if self.ab:
            ha, ea = self.ba.receive(ha, m_ba, self.A.L)
            hb, eb = self.ab.receive(hb, m_ab, self.B.L)
        else:
            ea = eb = None
        la, lb = self.A.logits(self.A.run(ha, 1, ea)), self.B.logits(self.B.run(hb, 1, eb))
        return (la, lb, raw) if return_msgs else (la, lb)
