"""Exact packed storage of the q4 frozen base (opt-in, nothing imports this unless asked).

sleepb --q4-base --q4-mlx-moe replaces each weight w by w' = (q*scale + bias).to(w.dtype) (q in 0..2^bits-1, scale / bias per group of 64 along the last dim, rounded to w.dtype) and keeps w' in bf16.
Here the same q, scale, bias are kept instead: uint8 codes (two 4-bit codes per byte), bf16 scale, bf16 bias. w' is rebuilt just in time with the same fp32 ops as sleepb.q4_fake, so it is bit-identical
(q*scale is exact in fp32 for a bf16 scale and q <= 255, so even an fma-fusing compiler gives the same bits). The frozen weight never gets a grad: a custom autograd.Function dequantizes in forward,
and again in backward for the input grad, so no bf16 weight is ever saved for backward.
    pack_model(lm, device=None)   # call where q4_apply is called (before peft); packs routed experts + big Linears, qdq's the rest in place
Layout of the packed copy: experts (E, out, in) -> codes (E, out, in/2) uint8, scale / bias (E, out, in/64) bf16: 0.5 + 2*2/64 = 0.5625 B/param (vs 2)."""
import re
import torch
import torch.nn as nn
import torch.nn.functional as F

BITS_FOR = ((r"\.mlp\.gate\.weight$", 8), (r"\.mlp\.shared_expert_gate\.weight$", 8))  # = sleepb.Q4_MLX_MOE_BITS
EXTRA = (r"\.mlp\.experts\.(?:gate_up_proj|down_proj)$", r"\.mlp\.gate\.weight$")  # = sleepb.Q4_MLX_MOE_PARAMS
CHUNK = 1 << 26  # elements per fp32 working piece (pack and unpack work in slices along dim 0)
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


def pack(w, group=64, bits=4, chunk=CHUNK):
    """w (..., in) -> (codes uint8 (..., in*bits/8), scale (..., in/group) w.dtype, bias likewise); None if in % group (or bits not 4 / 8). Slices along dim 0 above `chunk` elements (same bits)."""
    if w.dim() < 2 or w.shape[-1] % group or bits not in (4, 8) or (bits == 4 and group % 2):
        return None
    rows = max(1, chunk // (w.numel() // w.shape[0]))
    cs, ss, bs = [], [], []
    for i in range(0, w.shape[0], rows):
        p = w[i:i + rows]
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
    """The dense w' (..., in) in `dtype`, bit-identical to sleepb.q4_fake of the weight that was packed. compile=True: torch.compile'd piece (one fused kernel instead of ~8 passes; same bits, untested on GPU)."""
    fn = _unpack_piece
    if compile:
        fn = _COMPILED.setdefault("u", torch.compile(_unpack_piece, dynamic=False))
    n = codes.shape[0]
    per = max(1, codes.numel() // max(n, 1) * (8 // bits))
    rows = max(1, chunk // per)
    if rows >= n:
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
        r = pack(w.detach() if device is None else w.detach().to(device), group, bits)
        return None if r is None else cls(*r, bits=bits, group=group, compile=compile)

    @property
    def dtype(s):
        return s.scale.dtype

    def dequant(s):
        return unpack(s.codes, s.scale, s.bias, s.bits, s.group, s.scale.dtype, compile=s.compile)

    def nbytes(s):
        return sum(t.numel() * t.element_size() for t in (s.codes, s.scale, s.bias))


# ---------------------------------------------------------------- autograd: dequant in forward, dequant again in backward, nothing dense saved
class _PackedGroupedMM(torch.autograd.Function):
    """out = grouped_mm(x, W^T) with W = pk.dequant() (E, out, in), x (S, in) sorted by expert, offs int32 (E,). Only x gets a grad (the weight is frozen)."""

    @staticmethod
    def forward(ctx, x, offs, pk):
        from transformers.integrations.moe import _grouped_mm
        ctx.pk = pk
        ctx.save_for_backward(offs)
        return _grouped_mm(x.to(pk.dtype), pk.dequant().transpose(-2, -1), offs=offs)

    @staticmethod
    def backward(ctx, g):
        from transformers.integrations.moe import _grouped_mm
        (offs,) = ctx.saved_tensors
        gx = _grouped_mm(g.to(ctx.pk.dtype), ctx.pk.dequant(), offs=offs) if ctx.needs_input_grad[0] else None  # (S, out) @ (E, out, in) -> (S, in)
        return gx, None, None


class _PackedLinearFn(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, pk):
        ctx.pk = pk
        return F.linear(x, pk.dequant())

    @staticmethod
    def backward(ctx, g):
        if not ctx.needs_input_grad[0]:
            return None, None
        return torch.matmul(g, ctx.pk.dequant()), None


def packed_experts_forward(self, hidden_states, top_k_index, top_k_weights):
    """transformers' grouped_mm_experts_forward (5.20.2: no bias, no expert parallel) with the two grouped matmuls reading packed weights."""
    device, num_top_k, num_tokens, hidden_dim = hidden_states.device, top_k_index.size(-1), hidden_states.size(0), hidden_states.size(-1)
    sample_weights = top_k_weights.reshape(-1)
    expert_ids_g, perm = torch.sort(top_k_index.reshape(-1))
    sel = hidden_states[perm // num_top_k]
    sample_weights_g = sample_weights[perm]
    histc_input = expert_ids_g.float() if device.type in ("cpu", "mps") else expert_ids_g.int()
    tokens_per_expert = torch.histc(histc_input, bins=self.num_experts, min=0, max=self.num_experts - 1)
    offsets = torch.cumsum(tokens_per_expert, dim=0, dtype=torch.int32)
    out = _PackedGroupedMM.apply(sel, offsets, self.gate_up_packed)  # (S, 2 * inter)
    out = self._apply_gate(out)
    out = _PackedGroupedMM.apply(out, offsets, self.down_packed)  # (S, hidden)
    out = out * sample_weights_g.unsqueeze(-1)
    inv_perm = torch.empty_like(perm)
    inv_perm[perm] = torch.arange(perm.size(0), device=device)
    out = out[inv_perm]
    return out.view(num_tokens, num_top_k, hidden_dim).sum(dim=1).to(hidden_states.dtype)


class PackedLinear(nn.Linear):
    """An nn.Linear (so peft targets it) whose weight lives in self.packed. `weight` is an empty tensor of the right dtype / device (peft only reads dtype and device from it). No bias."""
    weight = property(lambda s: s.packed.scale[:0])

    def forward(self, x):
        return _PackedLinearFn.apply(x, self.packed)


def install_experts(m, group=64, bits=4, device=None, compile=False):
    """Pack m.gate_up_proj / m.down_proj (3-D Parameters of a transformers *Experts module) and route its forward through packed_experts_forward."""
    pk = {n: PackedTensor.from_weight(getattr(m, n).data, group, bits, device, compile) for n in ("gate_up_proj", "down_proj")}
    if None in pk.values():
        return False
    for n in pk:
        delattr(m, n)
    m.gate_up_packed, m.down_packed = pk["gate_up_proj"], pk["down_proj"]
    m.forward = packed_experts_forward.__get__(m)  # instance attribute: set_experts_implementation no longer matters for this module, the grouped_mm path is always used
    return True


def install_linear(m, group=64, bits=4, device=None, compile=False):
    pk = PackedTensor.from_weight(m.weight.data, group, bits, device, compile)
    if pk is None:
        return False
    del m.weight
    m.packed = pk
    m.__class__ = PackedLinear
    return True


def qdq_inplace(w, group, bits, chunk=CHUNK):
    """What sleepb.q4_inplace does, through pack / unpack (so the dense qdq'd leftovers equal the q4_apply ones); False if not divisible by group."""
    r = pack(w, group, bits, chunk)
    if r is None:
        return False
    w.copy_(unpack(*r, bits, group, w.dtype, chunk))
    return True


def pack_model(lm, group=64, bits=4, bits_for=BITS_FOR, extra=EXTRA, device=None, linears=True, experts=True, min_numel=1 << 20, compile=False):
    """Replace sleepb.q4_apply(lm, group, bits, bits_for, extra) by packed storage where it pays: fused expert tensors (4-bit) and Linears of >= min_numel elements with no bias (not tied to an
    Embedding); every other tensor the recipe covers (Embedding, routers, small Linears) is qdq'd in place and stays dense. device: where the packing math runs and the packed buffers live (e.g. cuda
    while lm is still on cpu: only one layer of bf16 is ever on the GPU; move the rest of lm afterwards). Call before peft. Returns {packed, dense_qdq, skipped, bytes_before, bytes_after}."""
    bf = [(re.compile(r), b) for r, b in bits_for]
    ex = [re.compile(r) for r in extra]
    bits_of = lambda n: next((b for rx, b in bf if rx.search(n)), bits)  # noqa: E731
    st = {"packed_experts": 0, "packed_linear": 0, "dense_qdq": 0, "skipped": 0}
    b0 = sum(p.numel() * p.element_size() for p in lm.parameters())
    emb = {m.weight.data_ptr() for m in lm.modules() if isinstance(m, nn.Embedding)}
    seen = set()
    with torch.no_grad():
        for n, m in list(lm.named_modules()):
            if experts and isinstance(getattr(m, "gate_up_proj", None), nn.Parameter) and isinstance(getattr(m, "down_proj", None), nn.Parameter) and m.gate_up_proj.dim() == 3:
                if install_experts(m, group, 4, device, compile):
                    st["packed_experts"] += 2
                else:
                    st["skipped"] += 2
                continue
            if isinstance(m, nn.Linear) and not isinstance(m, PackedLinear):
                w = m.weight
                if w.data_ptr() in seen:
                    continue
                seen.add(w.data_ptr())
                nb = bits_of(f"{n}.weight")
                if linears and nb == bits and m.bias is None and w.numel() >= min_numel and w.data_ptr() not in emb and install_linear(m, group, nb, device, compile):
                    st["packed_linear"] += 1
                else:
                    st["dense_qdq" if qdq_inplace(w.data, group, nb) else "skipped"] += 1
            elif isinstance(m, nn.Embedding):
                if m.weight.data_ptr() not in seen:
                    seen.add(m.weight.data_ptr())
                    st["dense_qdq" if qdq_inplace(m.weight.data, group, bits) else "skipped"] += 1
        for n, p in list(lm.named_parameters()):  # routers and any other Parameter the recipe names (the fused experts are gone from here when packed)
            if p.data_ptr() not in seen and any(rx.search(n) for rx in ex):
                seen.add(p.data_ptr())
                st["dense_qdq" if qdq_inplace(p.data, group, bits_of(n)) else "skipped"] += 1
    st["bytes_before"] = b0
    st["bytes_after"] = sum(p.numel() * p.element_size() for p in lm.parameters()) + sum(m.nbytes() for m in lm.modules() if isinstance(m, PackedTensor))
    return st


def dense_view(lm):
    """{name: dequantized dense tensor} of every packed tensor (for tests)."""
    out = {}
    for n, m in lm.named_modules():
        if isinstance(m, PackedTensor):
            out[n.replace("gate_up_packed", "gate_up_proj").replace("down_packed", "down_proj").replace(".packed", ".weight")] = m.dequant()
    return out
