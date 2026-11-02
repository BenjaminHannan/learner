"""Capture REAL gated-delta-rule inputs (q,k,v,g,beta after l2norm/scale/gating, exactly what gated_delta_ops receives)
from Qwen3.5-2B-4bit on real text, one forward pass. CPU is fine .
Run: python speed/mlx/capture_real_gdn.py [--model DIR_OR_HF_ID (default Qwen/Qwen3.5-2B bf16, ~4.5 GB)] [--T 256] [--layers 0,5,11,17] [--out /tmp/claude-0/realgdn_all.npz] [--text FILE]
Saves keys L{layer}_{q,k,v,g,beta} (fp32; batch 1); bf16 copies are made by the consumers.
The npz is ~6 MB per layer, so it lives outside the repo; the test/bench regenerate it with this script."""
import argparse, sys
import numpy as np
import mlx.core as mx
from mlx_lm import load
from mlx_lm.models import qwen3_5, gated_delta as gd


class _Done(Exception):
    pass


def capture(model_path="Qwen/Qwen3.5-2B", T=256, layers=None, text=None, fp32=True):
    """model_path: an UNQUANTIZED checkpoint is best on CPU (MLX's CPU 4-bit dequant/qmm is minutes-slow here); the layer inputs
    are the same kind of data as the 4-bit Mac model sees. fp32=True casts weights to fp32 (8 GB RAM, BLAS-fast); the forward stops
    after the last linear-attention layer (no lm_head)."""
    model, tok = load(model_path)
    if fp32:
        from mlx.utils import tree_map
        model.update(tree_map(lambda p: p.astype(mx.float32) if p.dtype == mx.bfloat16 else p, model.parameters()))
        mx.eval(model.parameters())
    n_lin = sum(1 for l in model.model.layers if getattr(l, "is_linear", False))
    model.eval()  # eval keeps use_kernel True but on CPU / no-metal it takes gated_delta_ops anyway; we call ops ourselves below
    text = text or open(__file__).read() * 8 + open(str(__import__("pathlib").Path(__file__).parents[1] / "README.md")).read()
    ids = tok.encode(text)[: T]
    assert len(ids) == T, f"text too short: {len(ids)} tokens"
    rec, orig = {}, qwen3_5.gated_delta_update
    n = [0]

    def spy(q, k, v, a, b, A_log, dt_bias, state=None, mask=None, **kw):
        i = n[0]; n[0] += 1
        beta = mx.sigmoid(b)
        g = gd.compute_g(A_log, a, dt_bias)
        rec[i] = [np.array(x.astype(mx.float32)) for x in (q, k, v, g, beta)]
        rec[i].append(str(q.dtype))
        out = orig(q, k, v, a, b, A_log, dt_bias, state, mask, **kw)
        mx.eval(out)
        if n_lin and n[0] >= n_lin:
            raise _Done
        return out

    qwen3_5.gated_delta_update = spy
    try:
        out = model(mx.array([ids]))
        mx.eval(out)
    except _Done:
        pass
    finally:
        qwen3_5.gated_delta_update = orig
    keep = range(n[0]) if layers is None else layers
    d = {}
    for i in keep:
        for name, x in zip("qkvg", rec[i][:4]):
            d[f"L{i}_{name}"] = x
        d[f"L{i}_beta"] = rec[i][4]
    d["model_dtype"] = np.array(rec[0][5])
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--T", type=int, default=256)
    ap.add_argument("--layers", default=None)
    ap.add_argument("--out", default="/tmp/claude-0/realgdn_all.npz")
    ap.add_argument("--text", default=None)
    a = ap.parse_args()
    d = capture(a.model, a.T, None if a.layers is None else [int(x) for x in a.layers.split(",")], open(a.text).read() if a.text else None)
    np.savez(a.out, **d)
    print("saved", a.out, len(d) // 5, "layers")
