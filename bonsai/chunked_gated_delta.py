"""Chunked gated delta rule for MLX (training-friendly drop-in for gated_delta_ops).

mlx_lm's gated_delta_ops loops over every token, so backward keeps one fp32
state (Hv x Dv x Dk) per token. Here the sequence is cut into chunks of C
tokens; inside a chunk everything is batched matmuls (WY / UT form, Yang et al.
2024, as in fla chunk_gated_delta_rule) and only the chunk-boundary states are
carried, so ~C times fewer states are saved for backward.

Per step (reference): S <- g*S; d = beta*(v - S k); S <- S + d k^T; y = S q.
Inside a chunk with b_i = cumsum(log g): d_i = beta_i (v_i - e^{b_i} S0 k_i
 - sum_{j<i} e^{b_i-b_j} (k_j.k_i) d_j), i.e. (I+A) D = beta (V - e^b K S0^T).
Only differences b_i-b_j with j<=i (<= 0) are exponentiated, so nothing overflows.
"""

import mlx.core as mx

from mlx_lm.models.gated_delta import gated_delta_ops


INV_BLOCK = 16  # sub-block size of the triangular solve (tunable; exactness does not depend on it)


def _block_size(C):
    return max(d for d in range(1, min(C, INV_BLOCK) + 1) if C % d == 0)


@mx.custom_function
def _unit_lower_inv(A):
    """(I+A)^-1 for strictly lower A [..., C, C], by BLOCKED FORWARD SUBSTITUTION in the input dtype (fp32 here).
    The old (I-A)(I+A^2)(I+A^4)... series is exact in exact arithmetic but its powers A^(2^m) grow like binomial(C, 2^m)
    when keys are correlated (cos~1, beta~1: 1e18 at C=64), so fp32 cancellation destroys it. Substitution only ever forms
    T rows from earlier T rows, and for beta in [0,2] (|1-beta*cos|<=1) those stay O(1).
    Diagonal s x s blocks: row-by-row substitution (s steps, batched over C/s blocks); then C/s block rows:
    T_I = D_I (E_I - A[I, :I] T_<I). Matmuls/slices only, so it also runs on GPU; the VJP below is analytic."""
    C = A.shape[-1]
    s = _block_size(C)
    nb = C // s
    eye = mx.eye(C, dtype=A.dtype)
    Ad = mx.stack([A[..., I * s:(I + 1) * s, I * s:(I + 1) * s] for I in range(nb)], axis=-3)  # [..., nb, s, s]
    es = mx.eye(s, dtype=A.dtype)
    rows = [mx.broadcast_to(es[0:1], Ad[..., 0:1, :].shape)]
    for i in range(1, s):
        prev = mx.concatenate(rows, axis=-2)  # [..., nb, i, s]
        rows.append(es[i:i + 1] - Ad[..., i:i + 1, :i] @ prev)
    D = mx.concatenate(rows, axis=-2)  # [..., nb, s, s] = blockwise (I+A_II)^-1
    out = []
    for I in range(nb):
        r = eye[I * s:(I + 1) * s]  # [s, C]
        if I:
            r = r - A[..., I * s:(I + 1) * s, :I * s] @ mx.concatenate(out, axis=-2)[..., :I * s, :]
        out.append(D[..., I, :, :] @ r)
    return mx.concatenate(out, axis=-2)


@_unit_lower_inv.vjp
def _unit_lower_inv_vjp(primals, cotangent, output):
    # T = (I+A)^-1  =>  dA = -T^T dT T^T ; A is strictly lower so only that part receives gradient.
    Tt = output.swapaxes(-1, -2)
    return mx.tril(-(Tt @ cotangent @ Tt), -1)


def _prep(q, k, v, lg, beta):
    C = q.shape[-2]
    b = mx.cumsum(lg, axis=-1)  # log of cumulative decay within chunk
    tri = mx.tril(mx.ones((C, C), dtype=mx.bool_))  # i >= j
    diff = b[..., :, None] - b[..., None, :]  # b_i - b_j
    M = mx.where(tri, mx.exp(mx.where(tri, diff, 0.0)), 0.0)  # e^{b_i-b_j}, j<=i
    kk = k @ k.swapaxes(-1, -2)
    A = mx.tril(beta[..., :, None] * M * kk, -1)
    Tm = _unit_lower_inv(A)
    W = Tm @ (k * (beta * mx.exp(b))[..., None])  # [B,H,N,C,Dk]
    U = Tm @ (v * beta[..., None])  # [B,H,N,C,Dv]
    Mqk = M * (q @ k.swapaxes(-1, -2))  # causal incl. diagonal
    qg = q * mx.exp(b)[..., None]
    kd = k * mx.exp(b[..., -1:] - b)[..., None]  # k_i e^{b_C-b_i}
    gC = mx.exp(b[..., -1])  # [B,H,N]
    return qg, Mqk, W, U, kd, gC


def _step(S, qg, Mqk, W, U, kd, gC):
    St = S.swapaxes(-1, -2)
    Dn = U - W @ St  # [B,H,C,Dv]
    y = qg @ St + Mqk @ Dn
    return y, gC[..., None, None] * S + Dn.swapaxes(-1, -2) @ kd


_prep_c = mx.compile(_prep)
_step_c = mx.compile(_step)


def gated_delta_chunked(q, k, v, g, beta, state=None, mask=None, chunk=64, compile=False):
    """Same contract as gated_delta_ops. q,k [B,T,Hk,Dk]; v [B,T,Hv,Dv];
    g,beta [B,T,Hv]; state [B,Hv,Dv,Dk]; mask [B,T] bool. Returns (y, state).
    Masked steps leave the state untouched; y there is 0 (as the Metal kernel;
    the ops reference returns a don't-care value). Vector g [B,T,Hv,Dk] falls
    back to the reference loop."""
    if g.ndim != 3:
        return gated_delta_ops(q, k, v, g, beta, state, mask)
    B, T, Hk, Dk = q.shape
    Hv, Dv = v.shape[-2:]
    out_dtype = q.dtype
    if state is None:
        state = mx.zeros((B, Hv, Dv, Dk), dtype=mx.float32)
    if (r := Hv // Hk) > 1:
        q = mx.repeat(q, r, -2)
        k = mx.repeat(k, r, -2)
    f32 = mx.float32
    q, k, v, g, beta = (x.astype(f32) for x in (q, k, v, g, beta))
    if mask is not None:  # masked step == identity: g=1, beta=0
        g = mx.where(mask[..., None], g, 1.0)
        beta = mx.where(mask[..., None], beta, 0.0)

    C = min(chunk, T)
    pad = (-T) % C  # padded steps are identities too (g=1, beta=0, k=q=v=0)
    if pad:
        z = lambda x: mx.pad(x, [(0, 0), (0, pad)] + [(0, 0)] * (x.ndim - 2))
        q, k, v, beta = z(q), z(k), z(v), z(beta)
        g = mx.pad(g, [(0, 0), (0, pad), (0, 0)], constant_values=1.0)
    N = (T + pad) // C

    # [B,T,H,D] -> [B,H,N,C,D]
    split = lambda x: x.reshape(B, N, C, *x.shape[2:]).swapaxes(2, 3).swapaxes(1, 2)
    q, k, v = split(q), split(k), split(v)
    lg = split(mx.log(mx.maximum(g, 1e-30))[..., None])[..., 0]  # [B,H,N,C]
    beta = split(beta[..., None])[..., 0]
    prep = _prep_c if compile else _prep  # compile=True: mx.compile the per-chunk-batched part and the scan step
    qg, Mqk, W, U, kd, gC = prep(q, k, v, lg, beta)
    step = _step_c if compile else _step
    S = state.astype(f32)  # [B,Hv,Dv,Dk]
    ys = []
    for n in range(N):  # only the chunk-boundary state is carried
        y_n, S = step(S, qg[:, :, n], Mqk[:, :, n], W[:, :, n], U[:, :, n], kd[:, :, n], gC[:, :, n])
        ys.append(y_n)
    y = mx.stack(ys, axis=2)  # [B,H,N,C,Dv]
    y = y.swapaxes(1, 2).swapaxes(2, 3).reshape(B, N * C, Hv, Dv)[:, :T]
    if mask is not None:
        y = mx.where(mask[..., None, None], y, 0.0)
    return y.astype(out_dtype), S.astype(state.dtype)


def patch_mlx_vlm_qwen3_5(chunk=64):
    """Make mlx_vlm qwen3_5 use the chunked rule when training (use_kernel False)."""
    from mlx_vlm.models.qwen3_5 import gated_delta as gd
    from mlx_vlm.models.qwen3_5 import language

    if getattr(language.gated_delta_update, "_chunked", False):
        return
    orig = language.gated_delta_update

    def update(q, k, v, a, b, A_log, dt_bias, state=None, mask=None, use_kernel=True, **kw):
        # inference, or newer mlx-vlm (>=0.7) cache/state_steps calls: stock path
        if use_kernel or any(kw.get(n) is not None for n in ("cache", "state_steps")):
            return orig(q, k, v, a, b, A_log, dt_bias, state=state, mask=mask,
                        use_kernel=use_kernel, **kw)
        g, beta = gd._compute_g_beta(A_log, a, b, dt_bias)
        return gated_delta_chunked(q, k, v, g, beta, state, mask, chunk)

    update._chunked = True
    language.gated_delta_update = update


def patch_mlx_lm(chunk=64, compile=False):
    """Opt-in: make every mlx_lm model (qwen3_5, qwen3_next, ...) use the chunked rule in training (use_kernel=False).
    gated_delta_update falls to the module-global gated_delta_ops there; inference keeps the Metal kernel."""
    from mlx_lm.models import gated_delta as gd

    if getattr(gd.gated_delta_ops, "_chunked", False):
        return
    def ops(q, k, v, g, beta, state=None, mask=None):
        return gated_delta_chunked(q, k, v, g, beta, state, mask, chunk, compile)
    ops._chunked = True
    gd.gated_delta_ops = ops
