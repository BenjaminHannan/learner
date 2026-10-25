"""Grouped GEMM for the frozen routed experts on GPUs where torch 2.9's torch._grouped_mm has no fast kernel (sm_120, RTX PRO 6000 / 5090).
Cause (SHOWN by source, torch v2.9.1 aten/src/ATen/native/cuda/Blas.cpp `_grouped_mm_cuda` + GroupedMMUtils.h `_grouped_mm_fallback`): the fast bf16 kernel needs sm90 or sm100
(`_scaled_mm_allowed_device(sm90_only=true, sm100_only=true)`); any other card runs the fallback INSIDE the one aten::_grouped_mm call: offs.cpu(), then for each of the 256 experts
`offs_cpu[i].item()`, `mat_a.slice`, `out.slice`, `mat_b[i]`, `at::mm_out`. Forward AND the backward (grad_input is also an `_grouped_mm`) both do it: 560 calls x 256 experts = 143k mm.
This file replaces `transformers.integrations.moe._grouped_mm` (which `grouped_mm_experts_forward` calls for gate_up and down) with ONE Triton kernel launch per call:
  rows are sorted by expert (offs = cumulative counts); a program takes one (expert, BM-row tile, BN-column tile), found from offs with a cumsum over the 256 counts (no host sync);
  fp32 accumulate, output in the input dtype. Strides are passed in, so W.transpose(-2, -1) views are read in place.
Backward: a torch.autograd.Function returns grad_x = gmm(grad_out, W^T, offs) in one launch and NO weight gradient, so the weight must be frozen (requires_grad False). If a weight
requires grad, or the tensor is not on CUDA (and backend is "auto"), the original torch path is used. Same maths as before; only float summation order changes (fp32 accumulation either way).
backend: "auto" (triton on CUDA, original elsewhere) | "triton" (also on CPU through the Triton interpreter; for tests) | "torch" (pure-torch per-expert reference, for tests).
"""
import torch

_BACKEND = ["auto"]
_BLOCK = {"BM": 64, "BN": 128, "BK": 64}
_triton = None


def _load_triton():
    global _triton
    if _triton is None:
        import triton
        import triton.language as tl

        @triton.jit
        def kernel(A, W, C, OFFS, K: tl.constexpr, N, sam, sak, swe, swk, swn, scm, scn,
                   E: tl.constexpr, E2: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
            pid_n = tl.program_id(0)
            t = tl.program_id(1)
            ei = tl.arange(0, E2)
            ok = ei < E
            end = tl.load(OFFS + ei, mask=ok, other=0).to(tl.int32)
            start = tl.load(OFFS + ei - 1, mask=ok & (ei > 0), other=0).to(tl.int32)
            tiles = (end - start + BM - 1) // BM
            cum = tl.cumsum(tiles, 0)
            total = tl.sum(tiles, 0)
            if t < total:
                e = tl.sum((cum <= t).to(tl.int32), 0)
                sel = ei == e
                e_start = tl.sum(tl.where(sel, start, 0), 0)
                e_end = tl.sum(tl.where(sel, end, 0), 0)
                first = tl.sum(tl.where(sel, cum - tiles, 0), 0)
                rows = e_start + (t - first) * BM + tl.arange(0, BM)
                rmask = rows < e_end
                cols = pid_n * BN + tl.arange(0, BN)
                cmask = cols < N
                a_ptr = A + rows.to(tl.int64)[:, None] * sam
                w_ptr = W + e.to(tl.int64) * swe + cols.to(tl.int64)[None, :] * swn
                acc = tl.zeros((BM, BN), dtype=tl.float32)
                for k0 in range(0, K, BK):
                    ks = k0 + tl.arange(0, BK)
                    kmask = ks < K
                    a = tl.load(a_ptr + ks[None, :] * sak, mask=rmask[:, None] & kmask[None, :], other=0.0)
                    w = tl.load(w_ptr + ks.to(tl.int64)[:, None] * swk, mask=kmask[:, None] & cmask[None, :], other=0.0)
                    acc += tl.dot(a, w)
                c_ptr = C + rows.to(tl.int64)[:, None] * scm + cols[None, :] * scn
                tl.store(c_ptr, acc.to(C.dtype.element_ty), mask=rmask[:, None] & cmask[None, :])
        _triton = (triton, kernel)
    return _triton


def gmm_triton(a, w, offs):  # a [S, K] rows sorted by expert, w [E, K, N] (any strides), offs [E] cumulative counts -> [S, N]. Rows >= offs[-1] are left uninitialised (as torch does).
    triton, kernel = _load_triton()
    S, K = a.shape
    E, _, N = w.shape
    out = torch.empty(S, N, device=a.device, dtype=a.dtype)
    if S == 0:
        return out
    BM, BN, BK = _BLOCK["BM"], _BLOCK["BN"], _BLOCK["BK"]
    grid = (triton.cdiv(N, BN), triton.cdiv(S, BM) + E)  # at most one partly-filled tile per expert; surplus programs exit at once
    kernel[grid](a, w, out, offs, K, N, a.stride(0), a.stride(1), w.stride(0), w.stride(1), w.stride(2), out.stride(0), out.stride(1),
                 E=E, E2=triton.next_power_of_2(E), BM=BM, BN=BN, BK=BK)
    return out


def gmm_torch(a, w, offs):  # per-expert reference (one host sync); what the torch fallback does
    out = torch.zeros(a.size(0), w.size(2), device=a.device, dtype=a.dtype)
    s = 0
    for i, e in enumerate(offs.tolist()):
        if e > s:
            torch.mm(a[s:e], w[i], out=out[s:e])
        s = e
    return out


class FrozenGMM(torch.autograd.Function):
    @staticmethod
    def forward(ctx, a, w, offs, backend):
        ctx.save_for_backward(w, offs)
        ctx.backend = backend
        return (gmm_triton if backend == "triton" else gmm_torch)(a, w, offs)

    @staticmethod
    def backward(ctx, g):
        w, offs = ctx.saved_tensors
        f = gmm_triton if ctx.backend == "triton" else gmm_torch
        return f(g, w.transpose(-2, -1), offs), None, None, None  # one launch; no grad for the frozen weight


def make_grouped_mm(orig):
    def grouped_mm(input, weight, offs):
        be = _BACKEND[0]
        if be == "auto":
            be = "triton" if (weight.device.type == "cuda" and input.is_cuda) else "orig"
        if be == "orig" or weight.requires_grad or offs.dim() != 1:
            return orig(input, weight, offs)
        input = input.to(weight.dtype)
        return FrozenGMM.apply(input, weight, offs, be)
    return grouped_mm


def install(backend="auto", **block):
    """Patch transformers.integrations.moe._grouped_mm; returns undo()."""
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
