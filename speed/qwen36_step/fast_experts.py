"""Grouped GEMM for the frozen routed experts on GPUs where torch's torch._grouped_mm has no fast kernel (sm_120 RTX PRO 6000 / 5090 / 5070 Ti, and the T4 test bed).
Cause (SHOWN by source, torch v2.9.1 Blas.cpp `_grouped_mm_cuda` + GroupedMMUtils.h `_grouped_mm_fallback`): the fast bf16 kernel needs sm90/sm100; any other card runs, INSIDE one aten::_grouped_mm call,
offs.cpu() then per expert `.item()`, slice, `mm_out`; forward AND backward (grad_input is also a `_grouped_mm`): 560 calls x 256 experts = 143k tiny mm per step.
This file replaces `transformers.integrations.moe._grouped_mm` (called for gate_up and down).
Weight layout (SHOWN, transformers 5.20.2 Qwen3_5MoeExperts + moe._grouped_linear): stored gate_up_proj [E, 2I, H], down_proj [E, H, I] (is_transposed False); the forward passes
`weight.transpose(-2, -1)`, a [E, K, N] VIEW with K stride 1 (K contiguous, N strided). Our backward uses W^T = the stored [E, N, K] tensor itself (N contiguous). Nothing is ever copied.
Backends (`install(backend)` / fast_step option experts_backend):
  "bmm_pad"   scatter rows into a zero-padded [E, cap, K] buffer (cap = max rows per expert rounded up to 16, one host sync), ONE torch.bmm on the weight view, gather back. Exact (zero padding).
  "bmm_split" bmm over ALL experts at cap1 (~75th percentile count) plus a second bmm only for the overflow rows of the heavy experts (their weights are gathered transiently, ~25% of experts).
  "triton"    one Triton launch; tile table built on device (no host sync); fp32 accumulate; K-major weight loads when the weight is K-contiguous.
  "torch"     per-expert mm loop (reference for tests).   "auto" = bmm_pad on CUDA, the original path elsewhere.
Backward is a torch.autograd.Function returning grad_x = gmm(grad_out, W^T, offs) and NO weight grad, so the weight must be frozen (requires_grad False); otherwise the original path is used.
Same maths as before; only summation order differs. The bmm paths switch off reduced-precision fp16/bf16 split-K reduction while they run, so accumulation stays fp32.
"""
import torch

_BACKEND = ["auto"]
_BLOCK = {"BM": 32, "BN": 128, "BK": 64, "num_warps": 4, "num_stages": 2}
_triton = None


def _load_triton():
    global _triton
    if _triton is None:
        import triton
        import triton.language as tl

        @triton.jit
        def kernel(A, W, C, TE, TS, OFFS, K, N, sam, sak, swe, swk, swn, scm, scn,
                   KMAJOR: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
            pid_n = tl.program_id(0)
            t = tl.program_id(1)
            e = tl.load(TE + t)
            if e >= 0:
                row0 = tl.load(TS + t)
                e_end = tl.load(OFFS + e).to(tl.int32)
                rows = row0 + tl.arange(0, BM)
                rmask = rows < e_end
                cols = pid_n * BN + tl.arange(0, BN)
                cmask = cols < N
                a_ptr = A + rows.to(tl.int64)[:, None] * sam
                w_base = W + e.to(tl.int64) * swe
                acc = tl.zeros((BM, BN), dtype=tl.float32)
                for k0 in range(0, K, BK):
                    ks = k0 + tl.arange(0, BK)
                    kmask = ks < K
                    a = tl.load(a_ptr + ks[None, :] * sak, mask=rmask[:, None] & kmask[None, :], other=0.0)
                    if KMAJOR:  # weight is contiguous along K: load [BN, BK] (coalesced) and transpose in registers
                        w = tl.load(w_base + cols.to(tl.int64)[:, None] * swn + ks[None, :] * swk, mask=cmask[:, None] & kmask[None, :], other=0.0)
                        acc = tl.dot(a, tl.trans(w), acc, input_precision="ieee")
                    else:  # contiguous along N
                        w = tl.load(w_base + ks.to(tl.int64)[:, None] * swk + cols[None, :] * swn, mask=kmask[:, None] & cmask[None, :], other=0.0)
                        acc = tl.dot(a, w, acc, input_precision="ieee")
                c_ptr = C + rows.to(tl.int64)[:, None] * scm + cols[None, :] * scn
                tl.store(c_ptr, acc.to(C.dtype.element_ty), mask=rmask[:, None] & cmask[None, :])
        _triton = (triton, kernel)
    return _triton


def _starts(offs):
    return torch.cat([offs.new_zeros(1), offs[:-1]])


def _tile_table(offs, S, BM):
    """Per tile: expert id (-1 = unused) and first row. All on device, no host sync."""
    E = offs.numel()
    start = _starts(offs).long()
    counts = offs.long() - start
    tiles = (counts + BM - 1) // BM
    tcum = torch.cumsum(tiles, 0)
    T = (S + BM - 1) // BM + E  # at most one partly filled tile per expert
    t = torch.arange(T, device=offs.device)
    te = torch.searchsorted(tcum, t, right=True)
    valid = te < E
    tec = te.clamp(max=E - 1)
    first = tcum - tiles
    ts = start[tec] + (t - first[tec]) * BM
    return torch.where(valid, te, -1).to(torch.int32), ts.to(torch.int32), T


def gmm_triton(a, w, offs):  # a [S, K] rows sorted by expert, w [E, K, N] (any strides), offs [E] cumulative counts -> [S, N]. Rows >= offs[-1] are left uninitialised (as torch does).
    triton, kernel = _load_triton()
    S, K = a.shape
    E, _, N = w.shape
    out = torch.empty(S, N, device=a.device, dtype=a.dtype)
    if S == 0:
        return out
    BM, BN, BK = _BLOCK["BM"], _BLOCK["BN"], _BLOCK["BK"]
    te, ts, T = _tile_table(offs, S, BM)
    kmajor = w.stride(1) == 1 and w.stride(2) != 1
    grid = (triton.cdiv(N, BN), T)
    kernel[grid](a, w, out, te, ts, offs, K, N, a.stride(0), a.stride(1), w.stride(0), w.stride(1), w.stride(2), out.stride(0), out.stride(1),
                 KMAJOR=kmajor, BM=BM, BN=BN, BK=BK, num_warps=_BLOCK["num_warps"], num_stages=_BLOCK["num_stages"])
    return out


def gmm_torch(a, w, offs):  # per-expert reference (one host sync); what the torch fallback does
    out = torch.zeros(a.size(0), w.size(2), device=a.device, dtype=a.dtype)
    s = 0
    for i, e in enumerate(offs.tolist()):
        if e > s:
            torch.mm(a[s:e], w[i], out=out[s:e])
        s = e
    return out


class _FullPrecisionReduction:
    """cuBLAS may split K and reduce in fp16/bf16 when these flags are on (torch default True); turn them off so the bmm path accumulates in fp32."""
    def __enter__(self):
        m = torch.backends.cuda.matmul
        self.old = (getattr(m, "allow_fp16_reduced_precision_reduction", None), getattr(m, "allow_bf16_reduced_precision_reduction", None))
        for n in ("allow_fp16_reduced_precision_reduction", "allow_bf16_reduced_precision_reduction"):
            if hasattr(m, n):
                setattr(m, n, False)

    def __exit__(self, *x):
        m = torch.backends.cuda.matmul
        for n, v in zip(("allow_fp16_reduced_precision_reduction", "allow_bf16_reduced_precision_reduction"), self.old):
            if v is not None:
                setattr(m, n, v)


def _row_slots(offs, S):
    """expert id and slot-within-expert for each of the first S (= offs[-1]) sorted rows."""
    r = torch.arange(S, device=offs.device)
    e = torch.searchsorted(offs, r, right=True)
    start = torch.cat([offs.new_zeros(1), offs[:-1]]).long()
    pos = r - start[e.clamp(max=offs.numel() - 1)]
    return e, pos


def _round16(x):
    return max(16, (int(x) + 15) // 16 * 16)


def gmm_bmm_pad(a, w, offs):
    S, K = a.shape
    E, _, N = w.shape
    out = torch.zeros(S, N, device=a.device, dtype=a.dtype)
    if S == 0:
        return out
    counts = offs.long() - _starts(offs).long()
    cmax, n = torch.stack([counts.max(), offs[-1].long()]).tolist()  # the one host sync (n < S only with EP sentinel rows)
    if n == 0:
        return out
    cap = _round16(cmax)
    e, pos = _row_slots(offs, n)
    buf = a.new_zeros(E, cap, K)
    buf[e, pos] = a[:n]
    with _FullPrecisionReduction():
        y = torch.bmm(buf, w)  # [E, cap, N]; w is used as a view (no copy)
    out[:n] = y[e, pos]
    return out


def gmm_bmm_split(a, w, offs):
    S, K = a.shape
    E, _, N = w.shape
    out = torch.zeros(S, N, device=a.device, dtype=a.dtype)
    if S == 0:
        return out
    counts = offs.long() - _starts(offs).long()
    p75 = torch.sort(counts).values[min(E - 1, (E * 3) // 4)]
    cmax, n, p = torch.stack([counts.max(), offs[-1].long(), p75]).tolist()
    if n == 0:
        return out
    cap1 = _round16(p)
    e, pos = _row_slots(offs, n)
    an = a[:n]
    with _FullPrecisionReduction():
        m1 = pos < cap1
        ei, pi = e[m1], pos[m1]
        buf = a.new_zeros(E, cap1, K)
        buf[ei, pi] = an[m1]
        y = torch.bmm(buf, w)
        out[:n][m1] = y[ei, pi]
        if cmax > cap1:
            heavy = torch.nonzero(counts > cap1).flatten()
            hidx = torch.full((E,), -1, device=a.device, dtype=torch.long)
            hidx[heavy] = torch.arange(heavy.numel(), device=a.device)
            m2 = pos >= cap1
            hi, pj = hidx[e[m2]], pos[m2] - cap1
            buf2 = a.new_zeros(heavy.numel(), _round16(cmax - cap1), K)
            buf2[hi, pj] = an[m2]
            y2 = torch.bmm(buf2, w[heavy])  # transient gather of the heavy experts' weights
            out[:n][m2] = y2[hi, pj]
    return out


_FUNCS = {"triton": gmm_triton, "torch": gmm_torch, "bmm_pad": gmm_bmm_pad, "bmm_split": gmm_bmm_split}


class FrozenGMM(torch.autograd.Function):
    @staticmethod
    def forward(ctx, a, w, offs, backend):
        ctx.save_for_backward(w, offs)
        ctx.backend = backend
        return _FUNCS[backend](a, w, offs)

    @staticmethod
    def backward(ctx, g):
        w, offs = ctx.saved_tensors
        return _FUNCS[ctx.backend](g, w.transpose(-2, -1), offs), None, None, None  # no grad for the frozen weight


def make_grouped_mm(orig):
    def grouped_mm(input, weight, offs):
        be = _BACKEND[0]
        if be == "auto":
            be = "bmm_pad" if (weight.device.type == "cuda" and input.is_cuda) else "orig"
        if be == "orig" or weight.requires_grad or offs.dim() != 1:
            return orig(input, weight, offs)
        input = input.to(weight.dtype)
        return FrozenGMM.apply(input, weight, offs, be)
    return grouped_mm


def install(backend="auto", **block):
    """Patch transformers.integrations.moe._grouped_mm; returns undo(). `block` sets the Triton tile (BM, BN, BK, num_warps, num_stages)."""
    import transformers.integrations.moe as moe
    old, oldb, oldblk = moe._grouped_mm, _BACKEND[0], dict(_BLOCK)
    _BACKEND[0] = backend
    _BLOCK.update(block)
    moe._grouped_mm = make_grouped_mm(old)

    def undo():
        moe._grouped_mm = old
        _BACKEND[0] = oldb
        _BLOCK.clear()
        _BLOCK.update(oldblk)
    return undo
