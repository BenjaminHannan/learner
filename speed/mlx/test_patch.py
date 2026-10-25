"""patch_mlx_lm: gated_delta_update(use_kernel=False) output + grads match before/after patch (fp32). Run: python speed/mlx/test_patch.py"""
import sys
from pathlib import Path
import mlx.core as mx
from mlx_lm.models.gated_delta import gated_delta_update
sys.path.insert(0, str(Path(__file__).parent))
from chunked_gated_delta import patch_mlx_lm

mx.random.seed(0)
B, T, Hk, Hv, D = 2, 150, 2, 4, 32
n = lambda *s: mx.random.normal(s)
q, k, v, a, b = n(B, T, Hk, D), n(B, T, Hk, D), n(B, T, Hv, D), n(B, T, Hv), n(B, T, Hv)
A_log, dt = n(Hv) * 0.1, n(Hv) * 0.1
w = n(B, T, Hv, D)
f = lambda q, k, v: (gated_delta_update(q, k, v, a, b, A_log, dt, use_kernel=False)[0] * w).sum()
y0 = gated_delta_update(q, k, v, a, b, A_log, dt, use_kernel=False)[0]; g0 = mx.grad(f, argnums=(0, 1, 2))(q, k, v)
patch_mlx_lm(chunk=32)
y1 = gated_delta_update(q, k, v, a, b, A_log, dt, use_kernel=False)[0]; g1 = mx.grad(f, argnums=(0, 1, 2))(q, k, v)
rel = lambda x, z: (mx.max(mx.abs(x - z)) / mx.max(mx.abs(z))).item()
e = [rel(y1, y0)] + [rel(x, z) for x, z in zip(g1, g0)]
print("rel err y,dq,dk,dv:", e); assert max(e) < 1e-4

# --- regression guard for the chunk-size bug: stress inputs (correlated keys, beta 1 and 2, g ~ 0 / ~ 1) and REAL Qwen3.5-2B layer
# inputs (speed/mlx/realgdn_inputs.npz, layers 6 and 17; REALGDN_NPZ=<all-layer npz from capture_real_gdn.py> tests all 18; skipped if absent).
# Random-normal inputs above pass even with the old unstable inverse. Pass marks: fp32 y <= 1e-4 and grads <= 3e-4 at chunk 16/32/64/128;
# bf16 inputs within 2x of the per-token path's own bf16-vs-fp32 error.
import gdn_cases
from chunked_gated_delta import gated_delta_chunked
from mlx_lm.models.gated_delta import gated_delta_ops

cases = {f"stress:{n}": gdn_cases.stress(n, T=256) for n in gdn_cases.STRESS}
real = gdn_cases.load_real(layers=None, regenerate=False)  # committed file: layers 6 and 17
if not real:
    print("NOTE: no real-input npz (python speed/mlx/capture_real_gdn.py to make it); real-input cases skipped")
cases.update({f"real:L{L}": v for L, v in real.items()})
fails = []
for cn, inp in cases.items():
    floor = gdn_cases.errors(gated_delta_ops, gated_delta_ops, inp, mx.bfloat16)
    for c in (16, 32, 64, 128):
        f = lambda *a, c=c: gated_delta_chunked(*a, chunk=c)
        e32, e16 = gdn_cases.errors(f, gated_delta_ops, inp), gdn_cases.errors(f, gated_delta_ops, inp, mx.bfloat16)
        ok32 = e32["finite"] and e32["y"] <= 1e-4 and e32["grad_max"] <= 3e-4
        ok16 = e16["finite"] and e16["y"] <= 2 * floor["y"] + 1e-6 and e16["grad_max"] <= 2 * floor["grad_max"] + 1e-6
        if not (ok32 and ok16):
            fails.append((cn, c, e32["y"], e32["grad_max"], e16["y"], e16["grad_max"], floor["y"], floor["grad_max"]))
print("hard cases:", len(cases) * 4 - len(fails), "/", len(cases) * 4, "pass")
for f in fails:
    print("FAIL", f)
assert not fails
