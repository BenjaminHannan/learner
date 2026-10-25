"""Exact packed storage of the --q4-base frozen base (sleepb --q4-packed; nothing imports this unless asked).

sleepb --q4-base replaces each Linear / Embedding weight w by w' = (q*scale + bias).to(w.dtype) (q in 0..2^bits-1, scale / bias per group of 64 along the input dim, rounded to w.dtype) and keeps w' dense.
Here the same q, scale, bias are kept instead: uint8 codes (two 4-bit codes per byte), scale / bias in the weight dtype (0.5 + 2*2/64 = 0.5625 B/param instead of 2). w' is rebuilt just in time with the same
fp32 ops as sleepb.q4_fake, so it is bit-identical (q*scale is exact in fp32 for a 16-bit scale and q <= 255, so even an fma-fusing compiler gives the same bits). The frozen weight never gets a grad: a custom
autograd.Function dequantizes in forward and again in backward for the input grad, so no dense weight is saved for backward. An Embedding dequantizes only the gathered rows.
Vendored from the speed thread's speed/qwen36_mem/packed.py (dense parts only: no MoE experts), extended with PackedEmbedding, device-side packing, a vocab-chunked head and a pack_model for sleepb.

    pack_model(lm, 64, 4, device)   # where q4_apply is called (before peft); lm may still be on cpu while `device` (cuda) does the pack math, so the GPU never holds the dense model; then lm.to(device)
    dense_view(lm)                  # {name: dequantized dense weight} of every packed tensor (tests)

Kaggle T4 (fp16, 16 GB card emulating 8 GB): see k2_packed_check.py (python k2_packed_check.py --real checks the packed dequant and logits against q4_fake, then the bench and the one-night run it prints).
"""
import re
import torch
import torch.nn as nn
import torch.nn.functional as F

CHUNK = 1 << 26  # elements per fp32 working piece (pack and unpack work in slices along dim 0)
HEAD_CHUNK = 32768  # PackedLinear rows (vocab) per dequant piece for a head bigger than this (pack_model head_chunk)
KEEP_DENSE = r"(?:^|\.)(?:v_router|gate)$"  # modules whose .weight is read directly (MoE routers: F.linear(x, self.gate.weight)): qdq'd in place, never packed
_COMPILED = {}


def _qsb(w, group, bits):
    """q (float32 codes), scale, bias (float32 holding the w.dtype-rounded values): the same ops as sleepb.q4_fake."""
    levels = 2 ** bits - 1
    x = w.detach().float().reshape(-1, w.shape[-1] // group, group)
    mx, mn = x.amax(-1, keepdim=True), x.amin(-1, keepdim=True)
    scale = (mx - mn) / levels
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)
    scale, bias = scale.to(w.dtype).float(), mn.to(w.dtype).float()
    scale = torch.where(scale == 0, torch.full_like(scale, 1e-8), scale)  # (a bf16-underflowed scale: 1e-8 is then not stored exactly; never seen, ~1e-38)
    q = torch.clamp(torch.round((x - bias) / scale), 0, levels)
    return q, scale, bias


def pack(w, group=64, bits=4, chunk=CHUNK, device=None):
    """w (..., in) -> (codes uint8 (..., in*bits/8), scale (..., in/group) w.dtype, bias likewise); None if in % group (or bits not 4 / 8). Slices along dim 0 above `chunk` elements (same bits);
    device: each slice is moved there before the math (w itself may stay on cpu), the result lives there."""
    if w.dim() < 2 or w.shape[-1] % group or bits not in (4, 8) or (bits == 4 and group % 2):
        return None
    rows = max(1, chunk // (w.numel() // w.shape[0]))
    cs, ss, bs = [], [], []
    for i in range(0, w.shape[0], rows):
        p = w[i:i + rows] if device is None else w[i:i + rows].to(device)
        q, s, b = _qsb(p, group, bits)
        q = q.to(torch.uint8).reshape(*p.shape[:-1], -1)
        if bits == 4:
            q = q[..., 0::2] | (q[..., 1::2] << 4)  # even position -> low nibble
        cs.append(q)
        ss.append(s.to(w.dtype).reshape(*p.shape[:-1], -1))
        bs.append(b.to(w.dtype).reshape(*p.shape[:-1], -1))
    cat = lambda l: l[0] if len(l) == 1 else torch.cat(l)  # noqa: E731
    return cat(cs), cat(ss), cat(bs)


def _unpack_piece(codes, scale, bias, bits, group, dtype):
    q = torch.stack((codes & 15, codes >> 4), -1).reshape(*codes.shape[:-1], -1) if bits == 4 else codes
    q = q.float().reshape(*scale.shape, group)
    return (q * scale.float().unsqueeze(-1) + bias.float().unsqueeze(-1)).reshape(*scale.shape[:-1], -1).to(dtype)  # = q4_fake's q*scale+bias, then .to(w.dtype)


def unpack(codes, scale, bias, bits=4, group=64, dtype=torch.bfloat16, chunk=CHUNK, compile=False):
    """The dense w' (..., in) in `dtype`, bit-identical to sleepb.q4_fake of the weight that was packed. compile=True: torch.compile'd piece (one fused kernel instead of ~8 passes; k2_packed_check.py
    compares it with eager on the GPU). Any leading shape works (codes[ids] of an embedding gather too)."""
    fn = _unpack_piece
    if compile:
        fn = _COMPILED.setdefault("u", torch.compile(_unpack_piece, dynamic=False))
    n = codes.shape[0]
    per = max(1, codes.numel() // max(n, 1) * (8 // bits))
    rows = max(1, chunk // per)
    if rows >= n or codes.dim() < 2:
        return fn(codes, scale, bias, bits, group, dtype)
    out = torch.empty(*scale.shape[:-1], scale.shape[-1] * group, dtype=dtype, device=codes.device)
    for i in range(0, n, rows):
        out[i:i + rows] = fn(codes[i:i + rows], scale[i:i + rows], bias[i:i + rows], bits, group, dtype)
    return out


class PackedTensor(nn.Module):
    """Frozen packed weight: buffers codes / scale / bias (they follow .to(device)), dequant() on demand."""

    def __init__(s, codes, scale, bias, bits=4, group=64, compile=False):
        super().__init__()
        s.register_buffer("codes", codes)
        s.register_buffer("scale", scale)
        s.register_buffer("bias", bias)
        s.bits, s.group, s.compile = bits, group, compile
        s.shape = (*scale.shape[:-1], scale.shape[-1] * group)

    @classmethod
    def from_weight(cls, w, group=64, bits=4, device=None, compile=False):
        r = pack(w.detach(), group, bits, device=device)
        return None if r is None else cls(*r, bits=bits, group=group, compile=compile)

    @property
    def dtype(s):
        return s.scale.dtype

    def dequant(s, lo=None, hi=None):  # rows lo:hi of dim 0 (all by default)
        sl = slice(lo, hi)
        return unpack(s.codes[sl], s.scale[sl], s.bias[sl], s.bits, s.group, s.scale.dtype, compile=s.compile)

    def nbytes(s):
        return sum(t.numel() * t.element_size() for t in (s.codes, s.scale, s.bias))


# ---------------------------------------------------------------- autograd: dequant in forward, dequant again in backward, nothing dense saved
class _PackedLinearFn(torch.autograd.Function):
    """out = F.linear(x, W) with W = pk.dequant(); only x gets a grad (the weight is frozen). rows: dequant (and matmul) in pieces of that many output rows (vocab chunks of the head)."""

    @staticmethod
    def forward(ctx, x, pk, rows=None):
        ctx.pk, ctx.rows = pk, rows
        n = pk.shape[0]
        if not rows or rows >= n:
            return F.linear(x, pk.dequant())
        return torch.cat([F.linear(x, pk.dequant(i, i + rows)) for i in range(0, n, rows)], -1)

    @staticmethod
    def backward(ctx, g):
        if not ctx.needs_input_grad[0]:
            return None, None, None
        return torch.matmul(g, ctx.pk.dequant()), None, None  # one piece: summing per-chunk products would reorder the float sum (bits would differ from the dense matmul)


class PackedLinear(nn.Linear):
    """An nn.Linear (so peft targets it) whose weight lives in self.packed. `weight` is an empty tensor of the right dtype / device (peft only reads dtype and device from it). No bias."""
    weight = property(lambda s: s.packed.scale[:0])
    rows = None  # set by pack_model for a big head (the forward matmul in vocab pieces)

    def forward(self, x):
        return _PackedLinearFn.apply(x, self.packed, self.rows)


class PackedEmbedding(nn.Embedding):
    """An nn.Embedding whose table lives in self.packed (group along the hidden dim); forward dequantizes only the gathered rows = F.embedding(ids, q4_fake(W)) bit for bit (rows are independent)."""
    weight = property(lambda s: s.packed.scale[:0])

    def forward(self, ids):
        p = self.packed
        return unpack(p.codes[ids], p.scale[ids], p.bias[ids], p.bits, p.group, p.dtype)  # no compile: the gather shape changes every call


def install_linear(m, group=64, bits=4, device=None, compile=False, rows=None):
    pk = PackedTensor.from_weight(m.weight.data, group, bits, device, compile)
    if pk is None:
        return False
    del m.weight
    m.packed = pk
    m.__class__ = PackedLinear
    if rows:
        m.rows = rows
    return True


def install_embedding(m, group=64, bits=4, device=None):
    pk = PackedTensor.from_weight(m.weight.data, group, bits, device, False)
    if pk is None:
        return False
    del m.weight
    m.packed = pk
    m.__class__ = PackedEmbedding
    return True


def qdq_inplace(w, group, bits, chunk=CHUNK, device=None):
    """What sleepb.q4_inplace does, through pack / unpack (so the dense qdq'd leftovers equal the q4_apply ones); False if not divisible by group."""
    r = pack(w, group, bits, chunk, device)
    if r is None:
        return False
    w.copy_(unpack(*r, bits, group, w.dtype, chunk).to(w.device))
    return True


def pack_model(lm, group=64, bits=4, device=None, compile=False, head_chunk=HEAD_CHUNK, keep=KEEP_DENSE):
    """Replace sleepb.q4_apply(lm, group, bits) by packed storage: every Linear without bias and in_features % group == 0, and every Embedding, becomes PackedLinear / PackedEmbedding (a head with more than
    head_chunk output rows does its matmul in pieces of head_chunk rows); the rest (bias, odd shape, names matching `keep`) is qdq'd in place and stays dense, like q4_apply. device: where the pack math runs and the
    packed buffers live (e.g. cuda while lm is still on cpu: only a slice of a tensor is ever on the GPU; move the rest of lm afterwards). Call before peft. 4 bits only (the uint8 layout; bits 8 also works).
    Returns {tensors, skipped, params, packed, dense_qdq, group, bits, bytes_before, bytes_after} (tensors = quantized either way, params = their element count, bytes = parameters + packed buffers)."""
    kp = re.compile(keep)
    st = {"tensors": 0, "skipped": 0, "params": 0, "packed": 0, "dense_qdq": 0, "group": group, "bits": bits}
    b0 = sum(p.numel() * p.element_size() for p in lm.parameters())
    seen = set()  # data_ptr of tensors qdq'd in place (a tied one once)
    if compile:
        from torch import _dynamo
        _dynamo.config.cache_size_limit = max(_dynamo.config.cache_size_limit, 64)  # q/k/v/o/gate/up/down/head chunks: more shapes than the default 8
    with torch.no_grad():
        for n, m in list(lm.named_modules()):
            if isinstance(m, (PackedLinear, PackedEmbedding)) or not isinstance(m, (nn.Linear, nn.Embedding)):
                continue
            w, num = m.weight, m.weight.numel()
            if isinstance(m, nn.Embedding):
                ok = install_embedding(m, group, bits, device)
            elif m.bias is None and not kp.search(n):
                ok = install_linear(m, group, bits, device, compile, head_chunk if w.shape[0] > head_chunk else None)
            else:
                ok = False
            if ok:
                st["packed"] += 1
            elif w.data_ptr() in seen:
                continue
            else:
                seen.add(w.data_ptr())
                ok = qdq_inplace(w.data, group, bits, device=device)
                st["dense_qdq"] += ok
            st["tensors" if ok else "skipped"] += 1
            st["params"] += num if ok else 0
    st["bytes_before"] = b0
    st["bytes_after"] = sum(p.numel() * p.element_size() for p in lm.parameters()) + sum(m.nbytes() for m in lm.modules() if isinstance(m, PackedTensor))
    return st


def dense_view(lm):
    """{name: dequantized dense tensor} of every packed tensor (for tests)."""
    return {n.removesuffix(".packed") + ".weight": m.dequant() for n, m in lm.named_modules() if isinstance(m, PackedTensor)}
