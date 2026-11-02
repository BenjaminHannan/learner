"""Shared test cases for the chunked Gated DeltaNet: REAL layer inputs (captured from Qwen3.5-2B-4bit) and synthetic STRESS inputs.
Random-normal inputs hide the chunk-size bug (they are nearly orthogonal and mildly decaying); real keys are correlated and real
gates reach g ~ 0 / g ~ 1, so every correctness check must include these.
"""
import os
from pathlib import Path
import numpy as np
import mlx.core as mx

HERE = Path(__file__).parent
# Search order: $REALGDN_NPZ, the committed 2-layer file (Qwen3.5-2B layers 6 and 17, T=256, the layers where the old inverse broke),
# then the all-18-layer file that capture_real_gdn.py writes (not committed, 100 MB).
_CANDIDATES = [os.environ.get("REALGDN_NPZ"), str(HERE / "realgdn_inputs.npz"), "/tmp/claude-0/realgdn_all.npz"]
REAL_NPZ = next((Path(p) for p in _CANDIDATES if p and Path(p).exists()), Path(_CANDIDATES[-1]))


def load_real(layers=None, T=None, regenerate=True):
    """dict layer -> [q,k,v,g,beta] fp32 mx arrays, batch 1. Regenerates the npz with capture_real_gdn.py if missing
    (needs the model: ~1.7 GB download, ~5 min CPU). Returns {} if unavailable and regenerate=False."""
    if not REAL_NPZ.exists():
        if not regenerate:
            return {}
        import sys
        sys.path.insert(0, str(HERE))
        from capture_real_gdn import capture
        REAL_NPZ.parent.mkdir(parents=True, exist_ok=True)
        np.savez(REAL_NPZ, **capture())
    d = np.load(REAL_NPZ)
    ids = sorted({int(k[1:].split("_")[0]) for k in d.files if k.startswith("L")})
    out = {}
    for i in ids if layers is None else layers:
        arrs = [mx.array(d[f"L{i}_{n}"]) for n in ("q", "k", "v", "g", "beta")]
        out[i] = [a[:, :T] for a in arrs] if T else arrs
    return out


def stress(name, B=1, T=256, Hk=2, Hv=4, D=128, seed=0):
    """Synthetic worst cases. Keys are unit norm, q has norm D**-0.5 (as the model's normalize_qk)."""
    mx.random.seed(seed)
    n = lambda *s: mx.random.normal(s)
    unit = lambda x: x / mx.linalg.norm(x, axis=-1, keepdims=True)
    cos, beta_v, gmode = {
        "corr0.9_beta1": (0.9, 1.0, "mild"),
        "corr0.99_beta1": (0.99, 1.0, "mild"),
        "corr0.99_beta2": (0.99, 2.0, "mild"),
        "anticorr_beta1": (-0.95, 1.0, "mild"),  # alternating sign: A has large negative entries
        "corr0.95_g_strong": (0.95, 1.0, "strong"),  # g ~ e^-30 .. 0 (underflows fp32 exp(b) over a chunk)
        "corr0.95_g_none": (0.95, 1.0, "none"),  # g ~ 1 - 1e-6: nothing forgets
    }[name]
    base = unit(n(B, 1, Hk, D))
    noise = unit(n(B, T, Hk, D))
    c = cos
    if name == "anticorr_beta1":
        sign = mx.where(mx.arange(T) % 2 == 0, 1.0, -1.0)[None, :, None, None]
        k = unit(abs(c) ** 0.5 * base * sign + (1 - abs(c)) ** 0.5 * noise)
    else:
        k = unit(c**0.5 * base + (1 - c) ** 0.5 * noise)
    q = unit(n(B, T, Hk, D)) * D**-0.5
    v = n(B, T, Hv, D)
    beta = mx.full((B, T, Hv), beta_v)
    if gmode == "mild":
        g = mx.exp(-mx.exp(n(B, T, Hv) * 0.5 - 1) * mx.logaddexp(n(B, T, Hv), 0))
    elif gmode == "strong":
        g = mx.exp(-30.0 * mx.sigmoid(n(B, T, Hv)) * mx.random.uniform(shape=(B, T, Hv)) ** 0.3)
        g = mx.where(mx.random.uniform(shape=(B, T, Hv)) < 0.1, 0.0, g)  # exact zeros appear in real fp32 gates
    else:
        g = 1.0 - 1e-6 * mx.random.uniform(shape=(B, T, Hv))
    return [q, k, v, g, beta]


STRESS = ["corr0.9_beta1", "corr0.99_beta1", "corr0.99_beta2", "anticorr_beta1", "corr0.95_g_strong", "corr0.95_g_none"]


def rel(a, b):
    a, b = a.astype(mx.float32), b.astype(mx.float32)
    return (mx.max(mx.abs(a - b)) / (mx.max(mx.abs(b)) + 1e-30)).item()


def fwd_bwd(fn, inp, w):
    def loss(q, k, v, g, beta):
        y, S = fn(q, k, v, g, beta)
        return (y.astype(mx.float32) * w).sum() + S.astype(mx.float32).sum()
    gr = mx.grad(loss, argnums=(0, 1, 2, 3, 4))(*inp)
    y, S = fn(*inp)
    return y, gr


def errors(fn, ref_fn, inp, dtype=mx.float32, w=None, ref_inp=None):
    """rel error (max|diff|/max|ref|) of y and of each grad vs ref_fn evaluated on ref_inp (default: the same inputs in fp32).
    Inputs are cast to `dtype` before fn. Returns dict y, grad_max, per-grad."""
    inp32 = ref_inp or [x.astype(mx.float32) for x in inp]
    if w is None:
        mx.random.seed(123)
        w = mx.random.normal(inp32[2].shape)
    y0, g0 = fwd_bwd(ref_fn, inp32, w)
    y1, g1 = fwd_bwd(fn, [x.astype(dtype) for x in inp32], w)
    mx.eval(y0, *g0, y1, *g1)
    # dg is compared as g*dg (= d/dlog g, what reaches A_log/dt_bias/a upstream, since dg/da carries a factor g): the raw dg of a
    # step with g~1e-20 is meaningless in fp32 (1/g times rounding noise) but is multiplied by g before it reaches any weight.
    g1, g0 = list(g1), list(g0)
    g1[3], g0[3] = g1[3] * inp32[3], g0[3] * inp32[3]
    gs = [rel(a, b) for a, b in zip(g1, g0)]
    return {"y": rel(y1, y0), "grad_max": max(gs), "grads": gs, "finite": bool(mx.all(mx.isfinite(y1)).item()) and all(bool(mx.all(mx.isfinite(x)).item()) for x in g1)}
