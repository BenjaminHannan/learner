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
