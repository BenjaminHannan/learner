"""Mac GPU bench: per-token mlx-lm gated_delta_ops vs chunked rule, fwd+bwd, at Qwen3.6-35B-A3B / Qwen3.5-2B GDN shapes.
Per-layer (one GDN op), not whole model. Whole-model step ~= ms_per_layer * n_GDN_layers (30 for 35B, 18 for 2B) + rest.
Run:  python speed/mlx/bench_gdn.py [--quick] [--models 35b,2b] [--seq 512,1024,2048] [--batch 1,2,4] [--chunks 32,64,128] [--out f.json]
Exits at once if ~/learner-ops/PAUSE_OTHERS or ASSISTANT_RUNNING exists. Works on CPU too (tiny grid with --quick).
"""
import argparse, json, os, sys, time
from pathlib import Path

OPS = Path.home() / "learner-ops"
for flag in ("PAUSE_OTHERS", "ASSISTANT_RUNNING"):
    if (OPS / flag).exists():
        print(f"{OPS / flag} exists: Mac is busy with other work, not benchmarking. Remove it or wait.")
        sys.exit(0)

import mlx.core as mx
from mlx_lm.models.gated_delta import gated_delta_ops

sys.path.insert(0, str(Path(__file__).parent))
from chunked_gated_delta import gated_delta_chunked
import gdn_cases

SHAPES = {  # HF text_config linear_* fields: (Hk, Hv, Dk, Dv, n_gdn_layers)
    "35b": (16, 32, 128, 128, 30),  # Qwen3.6-35B-A3B: 40 layers, every 4th full attention
    "2b": (16, 16, 128, 128, 18),  # Qwen3.5-2B: 24 layers
}
REF_MEM_CAP_GB = float(os.environ.get("REF_MEM_CAP_GB", 14))  # skip per-token path if est. saved states exceed this (32 GB Mac)


def make(B, T, Hk, Hv, Dk, Dv, dtype, seed=0):
    mx.random.seed(seed)
    n = lambda *s: mx.random.normal(s)
    q, k = n(B, T, Hk, Dk), n(B, T, Hk, Dk)
    q = q / mx.linalg.norm(q, axis=-1, keepdims=True)  # unit norm like the model
    k = k / mx.linalg.norm(k, axis=-1, keepdims=True)
    v = n(B, T, Hv, Dv)
    g = mx.exp(-mx.exp(n(B, T, Hv) * 0.5 - 1) * mx.logaddexp(n(B, T, Hv), 0))
    beta = mx.sigmoid(n(B, T, Hv))
    w = n(B, T, Hv, Dv)
    return [x.astype(dtype) for x in (q, k, v, g, beta)], w.astype(dtype)


def methods(chunks):
    m = {"ref_per_token": lambda *a: gated_delta_ops(*a)}
    for c in chunks:
        m[f"chunk{c}"] = lambda *a, c=c: gated_delta_chunked(*a, chunk=c)
    m["chunk64_compile"] = lambda *a: gated_delta_chunked(*a, chunk=64, compile=True)
    m["chunk128_compile"] = lambda *a: gated_delta_chunked(*a, chunk=128, compile=True)
    return m


def fwd_bwd(fn, inp, w):
    def loss(q, k, v, g, beta):
        y, S = fn(q, k, v, g, beta)
        return (y.astype(mx.float32) * w.astype(mx.float32)).sum() + S.astype(mx.float32).sum()
    gr = mx.grad(loss, argnums=(0, 1, 2, 3, 4))(*inp)
    y, _ = fn(*inp)
    return y, gr


def rel(a, b):
    a, b = a.astype(mx.float32), b.astype(mx.float32)
    return (mx.max(mx.abs(a - b)) / (mx.max(mx.abs(b)) + 1e-12)).item()


def correctness(shape, chunks):  # fp32, T=200 (not a multiple of any chunk: tests padding)
    Hk, Hv, Dk, Dv, _ = shape
    inp, w = make(1, 200, Hk, Hv, Dk, Dv, mx.float32)
    y0, g0 = fwd_bwd(methods(chunks)["ref_per_token"], inp, w)
    mx.eval(y0, *g0)
    res = {}
    for name, fn in methods(chunks).items():
        if name == "ref_per_token":
            continue
        y, gr = fwd_bwd(fn, inp, w)
        mx.eval(y, *gr)
        res[name] = {"y": rel(y, y0), "grad_max": max(rel(a, b) for a, b in zip(gr, g0))}
    return res


def hard_cases(chunks, dtypes=("float32", "bfloat16"), real_layers=None):
    """Chunk-size regression guard (random-normal inputs hide the bug). Real Qwen3.5-2B layer inputs (npz from
    capture_real_gdn.py; skipped if absent) and synthetic stress (cos 0.9-0.99, beta 1 and 2, g ~ 0 / ~ 1).
    Per case, dtype, chunk: rel err of y and max grad vs the per-token path on the same inputs in fp32; for bf16 also the
    per-token path's own bf16-vs-fp32 error (the floor). Pass: fp32 <= 1e-4 (grads 3e-4); bf16 <= 2x floor (+1e-6)."""
    cases = {f"stress:{n}": gdn_cases.stress(n, T=256) for n in gdn_cases.STRESS}
    for L, inp in gdn_cases.load_real(real_layers, regenerate=False).items():
        cases[f"real:L{L}"] = inp
    out = {}
    for cn, inp in cases.items():
        for dn in dtypes:
            dt = getattr(mx, dn)
            floor = gdn_cases.errors(gated_delta_ops, gated_delta_ops, inp, dt) if dn != "float32" else None
            for c in chunks:
                e = gdn_cases.errors(lambda *a, c=c: gated_delta_chunked(*a, chunk=c), gated_delta_ops, inp, dt)
                if floor:
                    ok = e["finite"] and e["y"] <= 2 * floor["y"] + 1e-6 and e["grad_max"] <= 2 * floor["grad_max"] + 1e-6
                else:
                    ok = e["finite"] and e["y"] <= 1e-4 and e["grad_max"] <= 3e-4
                out[f"{cn}|{dn}|chunk{c}"] = {"y": e["y"], "grad_max": e["grad_max"], "finite": e["finite"],
                                              "floor_y": floor and floor["y"], "floor_grad": floor and floor["grad_max"], "pass": ok}
    return out


def run(fn, inp, w, iters):
    def once():
        y, gr = fwd_bwd(fn, inp, w)
        mx.eval(y, *gr)
        return y, gr
    once()  # warmup (compile, kernels)
    base = mx.get_active_memory()
    mx.reset_peak_memory()
    ts = []
    for _ in range(iters):
        t = time.perf_counter(); y, gr = once(); ts.append(time.perf_counter() - t)
    return {"ms": 1e3 * sorted(ts)[len(ts) // 2], "peak_gb": (mx.get_peak_memory() - base) / 2**30}, y, gr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="35b,2b")
    ap.add_argument("--seq", default="512,1024,2048")
    ap.add_argument("--batch", default="1,2,4")
    ap.add_argument("--chunks", default="32,64,128")
    ap.add_argument("--iters", type=int, default=3)
    ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float32"])
    ap.add_argument("--quick", action="store_true", help="2b, seq 256, batch 1 (CPU-sized smoke)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ints = lambda s: [int(x) for x in s.split(",")]
    if a.quick:
        a.models, a.seq, a.batch, a.iters = "2b", "256", "1", 1
    chunks, dtype = ints(a.chunks), getattr(mx, a.dtype)
    out = {"device": str(mx.default_device()), "mlx": mx.__version__, "dtype": a.dtype, "rows": [], "correctness_fp32": {}}
    for mn in a.models.split(","):
        shape = SHAPES[mn]
        Hk, Hv, Dk, Dv, nl = shape
        out["correctness_fp32"][mn] = correctness(shape, chunks)
        print(mn, "fp32 match vs ref (rel err):", json.dumps(out["correctness_fp32"][mn]), flush=True)
    out["hard_cases"] = hard_cases(chunks)
    bad = {k: v for k, v in out["hard_cases"].items() if not v["pass"]}
    print(f"hard cases (real inputs + stress): {len(out['hard_cases']) - len(bad)}/{len(out['hard_cases'])} pass", json.dumps(bad), flush=True)
    for mn in a.models.split(","):
        shape = SHAPES[mn]
        Hk, Hv, Dk, Dv, nl = shape
        for T in ints(a.seq):
            for B in ints(a.batch):
                inp, w = make(B, T, Hk, Hv, Dk, Dv, dtype)
                mx.eval(*inp, w)
                ref = None
                for name, fn in methods(chunks).items():
                    row = {"model": mn, "T": T, "B": B, "method": name, "gdn_layers": nl}
                    if name == "ref_per_token" and B * T * Hv * Dv * Dk * 4 / 2**30 > REF_MEM_CAP_GB:
                        row["skipped"] = "est. per-token saved states > REF_MEM_CAP_GB"
                    else:
                        try:
                            r, y, gr = run(fn, inp, w, a.iters)
                            row.update(r)
                            if name == "ref_per_token":
                                ref = (y, gr)
                            elif ref:
                                row["rel_y"], row["rel_grad_max"] = rel(y, ref[0]), max(rel(x, z) for x, z in zip(gr, ref[1]))
                        except Exception as e:  # OOM etc.
                            row["error"] = repr(e)[:200]
                    out["rows"].append(row)
                    print(json.dumps(row), flush=True)
                    mx.clear_cache()
    refs = {(r["model"], r["T"], r["B"]): r["ms"] for r in out["rows"] if r["method"] == "ref_per_token" and "ms" in r}
    for r in out["rows"]:
        if "ms" in r and (r["model"], r["T"], r["B"]) in refs:
            r["speedup_vs_ref"] = round(refs[(r["model"], r["T"], r["B"])] / r["ms"], 2)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
        print("wrote", a.out)


if __name__ == "__main__":
    main()
