"""The per-question D -> creative bridge, its number handoff, and the wiring into the creative (Ledger) model.

Bridge types (all take D's final-loop register rows regs [B, R, 128] of the SAME item; no mixing across the batch):
  none       no message; the count head is a bias (learns the prior), the injected number is the prior mode.
  ema_const  v1/joint.py exactly: Linear(EMA of D's register-0 state), zero-init, the SAME vector for every question.  The control.
  pooled     register 0 -> RMSNorm -> Linear (zero-init) -> added to the creative controller tokens Z (once, before iteration 0).
  xattn      Z cross-attends over D's projected register rows after every controller block, output * tanh(gate), gate init 0.

Number handoff (all types): a count head on the bridge summary predicts c in 0..CMAX (trained with CE on the TRUE c: an auxiliary label, stated in every
result).  argmax(c) is written as the VALUE of the creative prompt's query-number slot (the slot the placeholder '@' occupies); the slot's embedding is
the usual value code + the bridge vector v (zero-init Linear of the summary).  The executor then computes with that exact integer.

Wiring needs no change to Ledger.run beyond the 1-line per-item `bridge_in` shape (custom_io/models/ledger.py): the slot is injected by overriding
`tokenize` (the placeholder becomes the number slot at its ordinal, with the injected value) and by a Linear subclass for `vcode` (same weights/keys) that
adds v at that slot.  With everything zero-initialised and the slot value fixed, outputs are bit-identical to the bridge off (tests/test_bridge.py).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger
from v1.joint import Bridge as EmaBridge

from .data import CMAX, PLACEHOLDER

KINDS = ("none", "ema_const", "pooled", "xattn")
N_NUM = pp.N_NUM


# =========================================================================== creative side: one injected number slot
class SlotVCode(nn.Linear):
    """Ledger.vcode (same parameters, same state_dict keys) that can add a per-item vector to the injected number slot of S0."""
    idx = None          # [B] long, slot index of the placeholder per item (-1: none)
    vec = None          # [B, d] or None

    def forward(self, x):
        out = super().forward(x)
        if self.vec is not None and self.idx is not None and x.dim() == 3:
            hit = torch.arange(x.shape[1], device=x.device)[None, :] == self.idx[:, None]
            out = out + hit.to(out.dtype)[..., None] * self.vec[:, None, :].to(out.dtype)
        return out


class SlotLedger(Ledger):
    """A Ledger whose prompt may contain ONE placeholder '@' standing for a number whose VALUE is injected (`slot_value` [B] long).
    slot_value None = the unmodified Ledger tokenizer (the placeholder is then an ordinary non-digit character)."""
    slot_value = None

    def tokenize(self, batch):
        if self.slot_value is None:
            self.vcode.idx = None
            return super().tokenize(batch)
        dev = batch['prompt_ids'].device
        rows = batch['rows']
        B = len(rows)
        ns, ne, nv = (np.zeros((B, pp.N_NUM), np.int64) for _ in range(3))
        ws, we = (np.zeros((B, pp.W_MAX), np.int64) for _ in range(2))
        idx = np.full(B, -1, np.int64)
        val = self.slot_value.tolist()
        for b, r in enumerate(rows):
            prompt = r['prompt']
            spans = [(m.start(), m.end(), min(int(m.group()), 10 ** 18)) for m in pp.NUM_RE.finditer(prompt)]
            p = prompt.find(PLACEHOLDER)
            if p >= 0:
                spans.append((p, p + 1, None))
                spans.sort(key=lambda s: s[0])
            for k, (s, e, v) in enumerate(spans[:pp.N_NUM]):
                ns[b, k], ne[b, k] = s, e
                if v is None:
                    nv[b, k], idx[b] = int(val[b]), k
                else:
                    nv[b, k] = v
            _, _, _, w_s, w_e = self.spans(prompt)
            ws[b], we[b] = w_s, w_e
        self.vcode.idx = torch.from_numpy(idx).to(dev)
        return [torch.from_numpy(x).to(dev) for x in (ns, ne, nv, ws, we)]


def to_slot_ledger(model: Ledger) -> SlotLedger:
    """In place: class swap + vcode swap (same parameters and keys, so checkpoints load before or after)."""
    if isinstance(model, SlotLedger):
        return model
    old = model.vcode
    new = SlotVCode(old.in_features, old.out_features).to(old.weight.device)
    new.load_state_dict(old.state_dict())
    model.vcode = new
    model.__class__ = SlotLedger
    model.slot_value = None
    return model


# =========================================================================== the bridge module
class XAttn(nn.Module):
    """Z [B,N,d] cross-attends over mem [B,R,d]; the output is gated by tanh(gate), gate = 0 at init (exact identity)."""

    def __init__(self, d: int, heads: int = 4):
        super().__init__()
        self.h = heads
        self.ln_q, self.ln_m = nn.LayerNorm(d), nn.LayerNorm(d)
        self.q, self.kv, self.o = nn.Linear(d, d), nn.Linear(d, 2 * d), nn.Linear(d, d)
        self.gate = nn.Parameter(torch.zeros(()))

    def forward(self, Z, mem):
        B, N, D = Z.shape
        q = self.q(self.ln_q(Z)).view(B, N, self.h, D // self.h).transpose(1, 2)
        k, v = self.kv(self.ln_m(mem)).view(B, mem.shape[1], 2, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v).transpose(1, 2).reshape(B, N, D)
        return torch.tanh(self.gate) * self.o(a)


def _mlp(i: int, o: int, hid: int = 256) -> nn.Sequential:
    return nn.Sequential(nn.Linear(i, hid), nn.GELU(), nn.Linear(hid, o))


class D2C(nn.Module):
    """forward(regs [B,R,d_d]) -> dict(logits [B,CMAX+1], v [B,d_c] | None, mem [B,R,d_c] | None, h [B,*] summary)."""

    def __init__(self, kind: str, d_d: int = 128, d_c: int = 256, n_regs: int = 4, n_core: int = 2, cmax: int = CMAX, heads: int = 4):
        super().__init__()
        assert kind in KINDS, kind
        self.kind, self.cmax = kind, cmax
        if kind == "none":
            self.prior = nn.Parameter(torch.zeros(cmax + 1))
        elif kind == "ema_const":
            self.joint = EmaBridge(d_d, d_c)                      # zero-init p_dc (and an unused p_cd, frozen)
            for p in self.joint.p_cd.parameters():
                p.requires_grad_(False)
            self.head = _mlp(d_d, cmax + 1)
        elif kind == "pooled":
            self.norm = nn.RMSNorm(d_d)
            self.head = _mlp(d_d, cmax + 1)
            self.to_v = nn.Linear(d_d, d_c)
        elif kind == "xattn":
            self.norm = nn.RMSNorm(d_d)
            self.rows = nn.Linear(d_d, d_c)
            self.pool_q = nn.Parameter(torch.randn(d_c) * 0.02)
            self.blocks = nn.ModuleList(XAttn(d_c, heads) for _ in range(n_core))
            self.head = _mlp(d_c, cmax + 1)
            self.to_v = nn.Linear(d_c, d_c)
        if kind in ("pooled", "xattn"):
            nn.init.zeros_(self.to_v.weight)
            nn.init.zeros_(self.to_v.bias)

    @property
    def per_item(self) -> bool:
        return self.kind in ("pooled", "xattn")

    def observe(self, reg0: torch.Tensor) -> None:
        """ema_const only: the EMA buffer of D's register-0 states (training batches; frozen at eval)."""
        if self.kind == "ema_const":
            self.joint.frozen_ctx = not self.training
            self.joint.observe_d(reg0)

    def forward(self, regs: torch.Tensor) -> dict:
        B = regs.shape[0]
        if self.kind == "none":
            return dict(logits=self.prior[None].expand(B, -1), v=None, mem=None, h=None)
        if self.kind == "ema_const":
            u = self.joint._unit(self.joint.ctx_d)
            return dict(logits=self.head(u)[None].expand(B, -1), v=self.joint.to_creative()[None].expand(B, -1), mem=None, h=u[None].expand(B, -1))
        x = self.norm(regs)
        if self.kind == "pooled":
            h = x[:, 0]
            return dict(logits=self.head(h), v=self.to_v(h), mem=None, h=h)
        mem = self.rows(x)
        w = torch.softmax(mem @ self.pool_q / mem.shape[-1] ** 0.5, dim=1)
        h = (w[..., None] * mem).sum(1)
        return dict(logits=self.head(h), v=self.to_v(h), mem=mem, h=h)

    def trainable(self):
        return [p for p in self.parameters() if p.requires_grad]


# =========================================================================== wiring
class Wire:
    """Connects a D2C output to a SlotLedger for one forward: Z additive (bridge_in), cross-attention hooks on the controller blocks, the slot vector and value."""

    def __init__(self, ledger: SlotLedger, bridge: D2C):
        self.ledger, self.bridge = ledger, bridge          # plain attributes of a non-Module: nothing is registered on either model
        self.out: Optional[dict] = None
        self.hooks = []
        self.active = True

    def attach(self) -> "Wire":
        L = self.ledger
        if self.bridge.kind == "xattn":
            for i, blk in enumerate(L.core):
                self.hooks.append(blk.register_forward_hook(lambda m, a, o, i=i: self._xhook(i, o)))
        if self.bridge.kind in ("pooled", "ema_const"):
            L.bridge_in = self._bridge_in
        if self.bridge.kind == "ema_const":
            self.bridge.joint.__dict__['_c'] = None          # v1's attach() not used: the vector goes through bridge_in above
        return self

    def detach(self) -> None:
        for h in self.hooks:
            h.remove()
        self.hooks = []
        self.ledger.bridge_in = None
        self.ledger.vcode.vec = None
        self.ledger.slot_value = None

    def _bridge_in(self):
        return self.out["v"] if (self.active and self.out is not None and self.out["v"] is not None) else torch.zeros(self.ledger.d, device=self.ledger.bridge_dev())

    def _xhook(self, i: int, output):
        if not self.active or self.out is None or self.out.get("mem") is None:
            return None
        return output + self.bridge.blocks[i](output, self.out["mem"])

    def set(self, out: dict, slot_value: torch.Tensor) -> None:
        """out = D2C.forward(...); slot_value [B] long, the number written into the query slot."""
        self.out = out
        self.ledger.slot_value = slot_value
        self.ledger.vcode.vec = out["v"] if self.active else None


def _bridge_dev(self):
    return self.vcode.weight.device


Ledger.bridge_dev = _bridge_dev          # tiny helper (a method, no behaviour change for anything that does not call it)


# =========================================================================== ablations of the message (applied to a whole evaluation set)
def ablate(regs: torch.Tensor, mode: str, seed: int = 0, c: Optional[torch.Tensor] = None) -> torch.Tensor:
    """real: unchanged.  off: zero message.  shuffle: messages permuted across items (a derangement; when c is given, every item gets a message from an item
    with a DIFFERENT c whenever one exists, so a shuffled message can never be right by coincidence).  mean: every item gets the set-mean message."""
    if mode == "real":
        return regs
    if mode == "off":
        return torch.zeros_like(regs)
    if mode == "mean":
        return regs.mean(0, keepdim=True).expand_as(regs).contiguous()
    if mode == "shuffle":
        return regs[shuffle_perm(regs.shape[0], seed, c)]
    raise ValueError(mode)


def shuffle_perm(n: int, seed: int = 0, c: Optional[torch.Tensor] = None) -> torch.Tensor:
    """perm with perm[i] != i; with c: c[perm[i]] != c[i] for every i that has any item of another class (greedy random matching, then repair)."""
    g = torch.Generator().manual_seed(seed)
    if n < 2:
        return torch.arange(n)
    perm = torch.randperm(n, generator=g)
    if c is None:
        # break fixed points by swapping with the next element
        for i in range(n):
            if perm[i] == i:
                j = (i + 1) % n
                perm[i], perm[j] = perm[j].clone(), perm[i].clone()
        return perm
    c = c.cpu()
    for _ in range(50):
        bad = (c[perm] == c).nonzero().squeeze(1).tolist()
        if not bad:
            break
        for i in bad:
            ok = (c[perm] != c[i]) & (c[perm[i]] != c) & (torch.arange(n) != i)        # swap i with j: both end with a message of another class
            cands = ok.nonzero().squeeze(1)
            if len(cands) == 0:
                continue
            j = int(cands[torch.randint(len(cands), (1,), generator=g)])
            perm[i], perm[j] = perm[j].clone(), perm[i].clone()
    return perm
