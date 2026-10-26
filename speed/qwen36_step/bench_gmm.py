"""GPU micro-benchmark of the frozen-expert grouped matmul at the real Qwen3.6-35B-A3B shapes (E=256, hidden 2048, moe_intermediate 512, top-8, S = 2048*8 routed rows).
Never ship an untimed kernel: this times every backend of fast_experts.py (and torch's own fallback) on forward and backward (grad_x only) for gate_up and down, with a skewed (lognormal)
and a uniform per-expert row count, and reports ms and max abs diff vs an fp32 per-expert reference. One JSON. Budget: < 3 min on a T4 (fp16) or sm_120 (bf16) (--budget-s stops adding cases).
  python bench_gmm.py --out bench_gmm.json [--dtype float16|bfloat16] [--tokens 2048] [--config path/to/config.json]
Layout as in the model: parameter P = gate_up [E, 2I, H] or down [E, H, I]; forward is gmm(x, P.transpose(-2,-1)) (K contiguous), backward is gmm(g, P) (N contiguous)."""
import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fast_experts as fe  # noqa: E402

TRITON_CONFIGS = [  # (BM, BN, BK, num_warps, num_stages); smem = stages*(BM+BN)*BK*2 B must stay under ~64 KB on sm_75
    (16, 64, 64, 4, 2), (32, 64, 64, 4, 2), (32, 128, 64, 4, 2), (64, 64, 32, 4, 2), (64, 128, 32, 8, 2), (64, 128, 64, 8, 2),
]


def counts_for(kind, E, S, gen):
    if kind == "uniform":
        c = torch.full((E,), S // E, dtype=torch.long)
        c[: S - int(c.sum())] += 1
        return c
    p = torch.exp(torch.randn(E, generator=gen) * 1.2)  # skewed: a few hot experts, many cold, some empty
    p = p / p.sum()
    c = torch.floor(p * S).long()
    c[torch.argsort(p, descending=True)[: S - int(c.sum())]] += 1
    return c


def timeit(fn, warm=1, iters=3):
    for _ in range(warm):
        fn()
    torch.cuda.synchronize()
    ts = []
    for _ in range(iters):
        s, e = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        s.record()
        fn()
        e.record()
        torch.cuda.synchronize()
        ts.append(s.elapsed_time(e))
    ts.sort()
    return ts[len(ts) // 2]


def reference(a, w, offs):  # fp32 per-expert
    out = torch.zeros(a.size(0), w.size(2), device=a.device, dtype=torch.float32)
    s = 0
    for i, e in enumerate(offs.tolist()):
        if e > s:
            out[s:e] = a[s:e].float() @ w[i].float()
        s = e
    return out


def torch_grouped(a, w, offs):
    return torch._grouped_mm(a, w, offs=offs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bench_gmm.json")
    ap.add_argument("--dtype", default=None)
    ap.add_argument("--tokens", type=int, default=2048)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--experts", type=int, default=256)
    ap.add_argument("--hidden", type=int, default=2048)
    ap.add_argument("--inter", type=int, default=512, help="moe_intermediate_size of Qwen3.6-35B-A3B (config.json)")
    ap.add_argument("--budget-s", type=float, default=150)
    a = ap.parse_args()
    dev = "cuda"
    cap = torch.cuda.get_device_capability()
    dtype = getattr(torch, a.dtype) if a.dtype else (torch.bfloat16 if cap[0] >= 8 else torch.float16)
    E, H, I = a.experts, a.hidden, a.inter
    S = a.tokens * a.topk
    gen = torch.Generator().manual_seed(0)
    torch.backends.cuda.matmul.allow_tf32 = False
    res = {"env": {"torch": torch.__version__, "device": torch.cuda.get_device_name(0), "cap": cap, "dtype": str(dtype)}, "shape": {"E": E, "H": H, "I": I, "S": S}, "cases": {}}
    t0 = time.time()

    def save():
        Path(a.out).write_text(json.dumps(res, indent=1))

    params = {"gate_up": torch.randn(E, 2 * I, H, device=dev, dtype=dtype) * 0.02, "down": torch.randn(E, H, I, device=dev, dtype=dtype) * 0.02}
    backends = {"torch_grouped_mm(fallback)": torch_grouped, "bmm_pad": fe.gmm_bmm_pad, "bmm_split": fe.gmm_bmm_split}
    for cfg in TRITON_CONFIGS:
        backends["triton%s" % (cfg,)] = cfg
    for dist in ("skewed", "uniform"):
        counts = counts_for(dist, E, S, gen)
        offs = torch.cumsum(counts, 0).int().to(dev)
        res["cases"][dist + "_counts"] = {"max": int(counts.max()), "mean": float(counts.float().mean()), "empty": int((counts == 0).sum()), "pad_waste_x": float(counts.max() * E / S)}
        for pname, P in params.items():
            for direction in ("fwd", "bwd"):
                w = P.transpose(-2, -1) if direction == "fwd" else P  # [E,K,N] view as the model passes it (fwd) / the backward's W^T (bwd)
                K = w.size(1)
                x = (torch.randn(S, K, device=dev, dtype=dtype) * 0.5)
                ref = reference(x, w, offs)
                row = {}
                for name, f in backends.items():
                    if time.time() - t0 > a.budget_s:
                        row[name] = {"skipped": "budget"}
                        continue
                    if isinstance(f, tuple):
                        BM, BN, BK, nw, ns = f
                        fe._BLOCK.update(BM=BM, BN=BN, BK=BK, num_warps=nw, num_stages=ns)
                        fn = fe.gmm_triton
                    else:
                        fn = f
                    try:
                        out = fn(x, w, offs)
                        diff = float((out.float() - ref).abs().max())
                        row[name] = {"ms": round(timeit(lambda: fn(x, w, offs)), 3), "max_abs_diff": diff}
                    except Exception as ex:  # noqa: BLE001
                        row[name] = {"error": (type(ex).__name__ + ": " + str(ex))[:200]}
                    torch.cuda.empty_cache()
                ok = {k: v["ms"] for k, v in row.items() if "ms" in v}
                row["best"] = min(ok, key=ok.get) if ok else None
                res["cases"][f"{dist}/{pname}/{direction}"] = row
                print(dist, pname, direction, {k: v.get("ms", v.get("error", v.get("skipped"))) for k, v in row.items() if k != "best"}, "best", row["best"], flush=True)
                save()
    # per-backend total over all cases = a layer-step-like score (lower is better)
    tot = {}
    for k, row in res["cases"].items():
        if "/" in k:
            for n, v in row.items():
                if isinstance(v, dict) and "ms" in v:
                    tot[n] = tot.get(n, 0) + v["ms"]
    res["total_ms"] = {k: round(v, 2) for k, v in sorted(tot.items(), key=lambda kv: kv[1])}
    res["elapsed_s"] = round(time.time() - t0, 1)
    save()
    print(json.dumps(res["total_ms"]), "elapsed", res["elapsed_s"])


if __name__ == "__main__":
    main()
