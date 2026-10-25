"""Check gated_delta_chunked against mlx_lm gated_delta_ops (fwd + grads, fp32, CPU).

Run: python bonsai/test_chunked_gated_delta.py
"""

import sys
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm.models.gated_delta import gated_delta_ops

sys.path.insert(0, str(Path(__file__).parent))
from chunked_gated_delta import gated_delta_chunked

FWD_TOL, GRAD_TOL = 1e-4, 1e-3


def rel(a, b):
    # max abs error scaled by the largest magnitude of the reference
    return (mx.max(mx.abs(a - b)) / (mx.max(mx.abs(b)) + 1e-12)).item()


def make(B, T, Hk, Hv, Dk, Dv, seed=0, with_state=False):
    mx.random.seed(seed)
    n = lambda *s: mx.random.normal(s)
    q, k = n(B, T, Hk, Dk), n(B, T, Hk, Dk)
    q = q / mx.linalg.norm(q, axis=-1, keepdims=True)  # unit norm like the model
    k = k / mx.linalg.norm(k, axis=-1, keepdims=True)
    v = n(B, T, Hv, Dv)
    g = mx.exp(-mx.exp(n(B, T, Hv) * 0.5 - 1) * mx.logaddexp(n(B, T, Hv), 0))
    beta = mx.sigmoid(n(B, T, Hv))
    s0 = n(B, Hv, Dv, Dk) * 0.3 if with_state else None
    return q, k, v, g, beta, s0


def compare(fn, args, mask, names):
    """Returns {check: rel err} for y, final state and grads of a random linear loss."""
    q, k, v, g, beta, s0 = args
    B, T, _, _ = q.shape
    Hv, Dv = v.shape[-2:]
    wy = mx.random.normal((B, T, Hv, Dv))
    wS = mx.random.normal((B, Hv, Dv, q.shape[-1]))
    if mask is not None:
        wy = wy * mask[..., None, None]  # masked-step y is a don't-care

    def loss(q, k, v, g, beta, s0):
        y, S = fn(q, k, v, g, beta, s0, mask)
        return (y * wy).sum() + (S * wS).sum()

    inp = [q, k, v, g, beta] + ([s0] if s0 is not None else [])
    n_in = len(inp)

    def l2(*a):
        return loss(*a, *([None] if s0 is None else []))

    grads = mx.grad(l2, argnums=tuple(range(n_in)))(*inp)
    y, S = fn(q, k, v, g, beta, s0, mask)
    mx.eval(y, S, *grads)
    if mask is not None:
        y = y * mask[..., None, None]
    return y, S, dict(zip(names, grads))


def run_case(label, B, T, Hk, Hv, Dk, Dv, with_state=False, use_mask=False):
    args = make(B, T, Hk, Hv, Dk, Dv, seed=T, with_state=with_state)
    mask = None
    if use_mask:  # left padding plus a hole in the middle
        mask = mx.ones((B, T), dtype=mx.bool_)
        idx = mx.arange(T)
        mask = mx.broadcast_to((idx >= 5) & (idx != T // 2), (B, T))
    names = ["q", "k", "v", "g", "beta"] + (["state"] if with_state else [])
    mx.random.seed(123)
    yr, Sr, gr = compare(gated_delta_ops, args, mask, names)
    mx.random.seed(123)
    yc, Sc, gc = compare(gated_delta_chunked, args, mask, names)
    res = [("y", rel(yc, yr), FWD_TOL), ("state", rel(Sc, Sr), FWD_TOL)]
    res += [("d" + n, rel(gc[n], gr[n]), GRAD_TOL) for n in names]
    ok = all(e < t for _, e, t in res)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: " + " ".join(f"{n}={e:.1e}" for n, e, _ in res))
    return ok


def bench(T, Hk, Hv, Dk, Dv):
    args = make(1, T, Hk, Hv, Dk, Dv, with_state=False)[:5]
    rows = []
    for name, fn in [("reference", gated_delta_ops), ("chunked64", gated_delta_chunked)]:
        def loss(q, k, v, g, beta):
            y, S = fn(q, k, v, g, beta, None, None)
            return (y * y).sum() + S.sum()

        vg = mx.value_and_grad(loss, argnums=(0, 1, 2, 3, 4))
        mx.eval(vg(*args))  # warm-up
        mx.reset_peak_memory()
        t0 = time.time()
        l, gs = vg(*args)
        mx.eval(l, gs)
        rows.append((name, time.time() - t0, mx.get_peak_memory() / 2**20))
    print(f"\nvalue_and_grad, T={T} Hk={Hk} Hv={Hv} Dk={Dk} Dv={Dv}, fp32, CPU")
    print(f"{'impl':<10} {'time s':>8} {'peak MiB':>9}")
    for n, t, m in rows:
        print(f"{n:<10} {t:8.2f} {m:9.0f}")
    print(f"speedup {rows[0][1] / rows[1][1]:.1f}x, memory {rows[0][2] / rows[1][2]:.1f}x less")


if __name__ == "__main__":
    mx.set_default_device(mx.cpu)
    ok = True
    for T in (1, 37, 64, 130):
        ok &= run_case(f"T={T}", 1, T, 2, 6, 32, 32)
    ok &= run_case("T=130 + initial state", 1, 130, 2, 6, 32, 32, with_state=True)
    ok &= run_case("T=130 + mask", 1, 130, 2, 6, 32, 32, use_mask=True)
    ok &= run_case("T=100 B=2 state+mask, chunk grid", 2, 100, 2, 6, 32, 32, True, True)
    print("ALL PASS" if ok else "SOME FAILED")
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 512
    bench(T, 16, 48, 128, 128)
    sys.exit(0 if ok else 1)
