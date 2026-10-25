"""GPU harness for the Qwen3.6-35B-A3B sleep-training step: real weights, only the first N layers, sleepb.Trainer.step on night-shaped batches, s/step and a torch.profiler
kernel table for the baseline and every opt-in fix of fast_step.py, one JSON out. No training happens (lr 0). Run on one rented GPU (24-32 GB is enough at --layers 8):
  python speed/qwen36_step/profile_step.py --layers 8 --out profile_step.json            # all variants
  python speed/qwen36_step/profile_step.py --layers 4 --variants baseline,all --steps 4   # quicker
Downloads only the shards that hold embed / norm / lm_head / layers < N (~4-6 shards of 26) into --work. The first N layers keep the 3 Gated DeltaNet : 1 full-attention pattern
when N % 4 == 0. Per-layer cost = (s/step(N=8) - s/step(N=4)) / 4; run both to extrapolate to 40 layers (lm_head + embed + optimizer are the constant).
Variants (fast_step options): baseline | sync_free | kl_cache | fla_conv | fused_norms | packed (= packed + fla_conv) | all (= every option); default list omits packed_nofla (CPU only).
Parity per variant, one lr-0 step on the same batch vs baseline: CE and KL relative diff, LoRA-gradient relative L2 diff and cosine. Pass marks (fixed in advance, bf16 + different
batch shapes make bit-equality impossible): CE rel diff < 1e-2, KL rel diff < 5e-2, grad cosine > 0.99. A variant that fails is reported, not timed as a win.
"""
import argparse
import json
import os
import re
import sys
import time
from argparse import Namespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1] / "backbone" / "sleep" / "brain"
sys.path[:0] = [str(HERE), str(BRAIN), str(BRAIN.parent), str(BRAIN.parent.parent)]

VARIANTS = {
    "baseline": {},
    "sync_free": {"sync_free": True},
    "kl_cache": {"kl_cache": True},
    "fla_conv": {"fla_conv": True},
    "fused_norms": {"fused_norms": True},
    "packed": {"packed": True, "fla_conv": True},
    "packed_nofla": {"packed": True},  # packed layout without the fla conv (CPU dry runs with --torch-varlen; on GPU the HF torch conv would leak across sequences)
    "all": {"sync_free": True, "kl_cache": True, "packed": True, "fla_conv": True, "fused_norms": True},
}
BUCKETS = [  # kernel-name regexps -> bucket, first match wins
    ("expert_gemm", r"grouped|group_gemm|cutlass.*grouped|moe"),
    ("gemm", r"gemm|cutlass|cublas|nvjet|xmma|sm\d+_|matmul|mm_|wgmma"),
    ("gdn_fla", r"chunk_gated|gated_delta|fla|recompute_w_u|chunk_(fwd|bwd)|solve_tril|fwd_prepare|prepare_wy"),
    ("conv", r"conv"),
    ("attention", r"flash|sdpa|attention|efficient_attention|softmax_warp"),
    ("norm", r"rms|layer_norm|norm"),
    ("router_topk_sort", r"topk|sort|argsort|cumsum|one_hot|scatter|index_put|gather|nonzero|bincount|histc"),
    ("cast_copy", r"copy|cast|to_copy|contiguous|clone|cat|fill|zero"),
    ("memcpy_memset", r"memcpy|memset"),
    ("optimizer", r"adam|foreach|multi_tensor|clip"),
    ("elementwise", r"elementwise|vectorized|reduce|mul|add|silu|sigmoid|exp|rsqrt|pow|where|mean|sum|neg|div|sub"),
]


class PadLang:  # the little of sleepb.Lang the Trainer uses (pad_right / device / eos), for the synthetic batches
    def __init__(self, device, eos):
        self.device, self.eos = device, eos

    def pad_right(self, seqs):
        import torch
        n = max(map(len, seqs))
        ids, mask = torch.zeros((len(seqs), n), dtype=torch.long), torch.zeros((len(seqs), n), dtype=torch.long)
        for r, e in enumerate(seqs):
            ids[r, :len(e)], mask[r, :len(e)] = torch.tensor(e), 1
        return ids.to(self.device), mask.to(self.device)


def trim_checkpoint(src, n_layers, out):
    """A local HF dir holding only config (text layers cut to n_layers), tokenizer files and the shards of embed / norm / lm_head / layers < n_layers, with a filtered
    safetensors index, so from_pretrained loads the real weights of the first N layers and nothing else. src: hub id or local dir."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    local = Path(src).is_dir()

    def get(name, required=True):
        if local:
            p = Path(src) / name
            return str(p) if p.exists() or required else None
        from huggingface_hub import hf_hub_download
        try:
            return hf_hub_download(src, name)
        except Exception:  # noqa: BLE001
            if required:
                raise
            return None
    ix = json.load(open(get("model.safetensors.index.json")))
    keep = re.compile(r"^(lm_head\.weight|model\.language_model\.(embed_tokens\.weight|norm\.weight)|model\.language_model\.layers\.(\d+)\..*)$")
    wm = {}
    for k, f in ix["weight_map"].items():
        m = keep.match(k)
        if m and (m.group(3) is None or int(m.group(3)) < n_layers):
            wm[k] = f
    for f in sorted(set(wm.values())):
        dst = out / f
        if not dst.exists():
            dst.symlink_to(get(f))
    json.dump({"metadata": ix.get("metadata", {}), "weight_map": wm}, open(out / "model.safetensors.index.json", "w"))
    cfg = json.load(open(get("config.json")))
    tc = cfg.get("text_config", cfg)
    tc["num_hidden_layers"] = n_layers
    tc["layer_types"] = tc["layer_types"][:n_layers]
    tc.pop("mtp_num_hidden_layers", None)
    json.dump(cfg, open(out / "config.json", "w"), indent=1)
    for name in ("generation_config.json", "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "chat_template.jinja", "special_tokens_map.json", "added_tokens.json"):
        p = get(name, required=False)
        if p and not (out / name).exists():
            (out / name).symlink_to(p)
    return str(out), {"shards": sorted(set(wm.values())), "tensors": len(wm)}


def build(path, device, dtype, rank, alpha, experts="grouped_mm"):
    import torch
    from peft import LoraConfig, get_peft_model
    import sleepb as sb
    from train import LORA_TARGETS, load_model
    lm, tok = load_model(Namespace(smoke=False, model=path, revision=None, seed=0), torch.device(device), dtype)
    if experts and hasattr(lm, "set_experts_implementation"):
        lm.set_experts_implementation(experts)
    tm = f"(?:{LORA_TARGETS})|(?:{sb.SHARED_RE})"  # --lora-shared, as the real runs
    pm = get_peft_model(lm, LoraConfig(r=rank, lora_alpha=alpha, lora_dropout=0.0, target_modules=tm, bias="none"))
    g = torch.Generator(device=device).manual_seed(0)  # same device as the LoRA params (CPU generator fails on CUDA)
    for n, p in pm.named_parameters():  # B is zero at init: randomise, so the gradients reaching every layer are non-trivial
        if "lora_B" in n:
            p.data.normal_(0, 0.02, generator=g)
    return lm, tok, pm


def make_batches(args, tok, vocab, device, eos):
    import random
    rng = random.Random(0)
    if args.batches == "realistic":
        from realistic import pools
        draw, rep, lens, L = pools(tok, args.week)
        L.device = device
        return [draw(rng, args.bsz, i % 4 == 3) for i in range(args.n_batches)], rep, lens, L
    mk = lambda n, k: ([rng.randrange(10, vocab - 1) for _ in range(n)] + [eos], n + 1 - k)  # noqa: E731
    bs = [[mk(384, 6) for _ in range(args.bsz // 2)] + [mk(60, 6) for _ in range(args.bsz // 4)] + [mk(80, 80) for _ in range(args.bsz - args.bsz // 2 - args.bsz // 4)] for _ in range(args.n_batches)]
    return bs, [mk(120, 40) for _ in range(200)], {"synthetic": "moe_bench.trainer_batch shape"}, PadLang(device, eos)


def bucket(name):
    low = name.lower()
    for b, rx in BUCKETS:
        if re.search(rx, low):
            return b
    return "other"


def profile_steps(run_step, n, device, top):
    import torch
    from torch.profiler import ProfilerActivity, profile
    acts = [ProfilerActivity.CPU] + ([ProfilerActivity.CUDA] if device == "cuda" else [])
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    with profile(activities=acts, record_shapes=False) as prof:
        for i in range(n):
            run_step(i)
        if device == "cuda":
            torch.cuda.synchronize()
    wall = time.time() - t0
    evs = prof.key_averages()
    dev_t = lambda e: getattr(e, "self_device_time_total", None) if hasattr(e, "self_device_time_total") else getattr(e, "self_cuda_time_total", 0)  # noqa: E731
    rows = sorted(((e.key, dev_t(e) or 0, e.count, e.self_cpu_time_total) for e in evs), key=lambda r: -r[1])
    gpu_us = sum(r[1] for r in rows)
    bk = {}
    for k, us, c, _ in rows:
        if us:
            b = bucket(k)
            d = bk.setdefault(b, {"ms_per_step": 0.0, "calls_per_step": 0.0})
            d["ms_per_step"] += us / 1e3 / n
            d["calls_per_step"] += c / n
    cpu_rows = sorted(((e.key, e.self_cpu_time_total, e.count) for e in evs if not dev_t(e)), key=lambda r: -r[1])[:top]
    return {"wall_s_per_step": round(wall / n, 4), "gpu_kernel_ms_per_step": round(gpu_us / 1e3 / n, 1), "gpu_busy_frac": round(gpu_us / 1e6 / wall, 3) if wall else None,
            "kernels_per_step": round(sum(r[2] for r in rows if r[1]) / n),
            "buckets": {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in sorted(bk.items(), key=lambda kv: -kv[1]["ms_per_step"])},
            "top_kernels": [{"name": k[:120], "ms_per_step": round(us / 1e3 / n, 2), "calls_per_step": round(c / n, 1), "pct_gpu": round(100 * us / gpu_us, 1) if gpu_us else None} for k, us, c, _ in rows[:top] if us],
            "top_cpu_ops": [{"name": k[:100], "ms_per_step": round(us / 1e3 / n, 2), "calls_per_step": round(c / n, 1)} for k, us, c in cpu_rows]}


def grads_of(tr):
    import torch
    return torch.cat([p.grad.detach().float().flatten() for p in tr.params if p.grad is not None])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="Qwen/Qwen3.6-35B-A3B", help="hub id or local dir")
    ap.add_argument("--layers", type=int, default=8)
    ap.add_argument("--work", default="/tmp/qwen36_step_work")
    ap.add_argument("--out", default="profile_step.json")
    ap.add_argument("--variants", default=",".join(v for v in VARIANTS if v != "packed_nofla"), help="comma list of: " + ", ".join(VARIANTS))
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--tok-budget", type=int, default=2048, help="sleepb TOK_BUDGET (padded tokens per forward; real tokens for packed)")
    ap.add_argument("--extra-budgets", default="", help="also time the packed variants at these budgets (comma list, e.g. 4096), if they fit in memory")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--steps", type=int, default=8, help="timed steps per variant")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--prof-steps", type=int, default=2)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--batches", choices=["realistic", "synthetic"], default="realistic", help="realistic: night-shaped from --week with the real chat template; synthetic: moe_bench's 384/60/80 mix")
    ap.add_argument("--week", default=str(BRAIN / "data" / "week1.json"))
    ap.add_argument("--n-batches", type=int, default=6)
    ap.add_argument("--torch-varlen", action="store_true", help="CPU dry run: packed sequences through the pure-torch per-sequence loops (no fla / Triton)")
    ap.add_argument("--no-prefill", action="store_true", help="kl_cache variants: do not pre-fill the cache (measures the cold start instead of steady state)")
    args = ap.parse_args()

    import torch
    import transformers
    import sleepb as sb
    import fast_step as fs
    import transformers.models.qwen3_5_moe.modeling_qwen3_5_moe as hf
    cuda = args.device == "cuda"
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    dtype = getattr(torch, args.dtype)
    res = {"args": vars(args), "env": {"torch": torch.__version__, "transformers": transformers.__version__, "device": torch.cuda.get_device_name(0) if cuda else "cpu"}, "variants": {}}
    for pkg in ("fla", "causal_conv1d", "flash_attn", "liger_kernel", "peft"):
        try:
            m = __import__(pkg)
            res["env"][pkg] = getattr(m, "__version__", "installed")
        except Exception:  # noqa: BLE001
            res["env"][pkg] = None
    res["env"]["hf_fast_paths"] = {"chunk_gated_delta_rule_is_fla": "fla" in str(getattr(hf.torch_chunk_gated_delta_rule, "__wrapped__", hf.torch_chunk_gated_delta_rule).__module__) or res["env"]["fla"] is not None,
                                   "causal_conv1d_package": res["env"]["causal_conv1d"] is not None}

    def save():
        Path(args.out).write_text(json.dumps(res, indent=1))

    path, info = trim_checkpoint(args.model, args.layers, Path(args.work) / f"{Path(args.model).name}_L{args.layers}")
    res["checkpoint"] = info
    t = time.time()
    lm, tok, pm = build(path, args.device, dtype, args.rank, args.alpha)
    res["load_s"] = round(time.time() - t, 1)
    cfg = lm.config
    res["model"] = {"layers": cfg.num_hidden_layers, "layer_types": {k: list(cfg.layer_types).count(k) for k in set(cfg.layer_types)}, "experts_impl": getattr(cfg, "_experts_implementation", None),
                    "attn_impl": getattr(cfg, "_attn_implementation", None), "trainable_params": sum(p.numel() for p in pm.parameters() if p.requires_grad), "dtype": args.dtype}
    batches, replay, lens, L = make_batches(args, tok, cfg.vocab_size, args.device, cfg.eos_token_id if isinstance(cfg.eos_token_id, int) else 1)
    res["batches"] = {"kind": args.batches, "mean_example_tokens": lens, "real_tokens_per_step": sum(len(e) for b in batches for e, _ in b) / len(batches)}
    pm.eval()
    save()
    ta = Namespace(lr=0.0, kl_weight=1.0, replay_bsz=args.replay_bsz)
    names = [v for v in args.variants.split(",") if v]
    runs = [(v, args.tok_budget) for v in names] + [(v, int(b)) for b in filter(None, args.extra_budgets.split(",")) for v in names if "packed" in VARIANTS[v] or v == "baseline"]
    ref = None  # (ce, kl, grads) of the baseline's first lr-0 step on batch 0 with replay rng seed 0
    for name, budget in runs:
        key = name if budget == args.tok_budget else f"{name}@{budget}"
        row = {"opts": VARIANTS[name], "tok_budget": budget}
        res["variants"][key] = row
        undo_t = fs.torch_varlen_patches(hf) if (VARIANTS[name].get("packed") and (args.torch_varlen or res["env"]["fla"] is None)) else (lambda: None)
        undo = fs.install(sb, **VARIANTS[name])
        old = sb.TOK_BUDGET
        sb.TOK_BUDGET = budget
        try:
            if cuda:
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            pm.train()
            tr = sb.Trainer(L, pm, ta, replay, args.warmup + args.steps + args.prof_steps + 2, 0)
            # parity step: the same batch and replay sample for every variant
            tr.rng.seed(0)
            tr.step(batches[0])
            c = tr.curve[-1]
            g = grads_of(tr)
            if key == "baseline":
                ref = (c["ce"], c["kl"], g.clone())
            if ref is not None:
                row["parity"] = {"ce": c["ce"], "kl": c["kl"], "ce_rel_diff": abs(c["ce"] - ref[0]) / max(abs(ref[0]), 1e-12), "kl_rel_diff": abs(c["kl"] - ref[1]) / max(abs(ref[1]), 1e-12),
                                 "grad_rel_l2_diff": float((g - ref[2]).norm() / ref[2].norm().clamp_min(1e-12)), "grad_cosine": float(torch.nn.functional.cosine_similarity(g, ref[2], dim=0))}
                row["parity"]["pass"] = bool(row["parity"]["ce_rel_diff"] < 1e-2 and row["parity"]["kl_rel_diff"] < 5e-2 and row["parity"]["grad_cosine"] > 0.99)
            tr.rng.seed(1)
            if VARIANTS[name].get("kl_cache") and not args.no_prefill:
                t = time.time()
                row["kl_cache_prefill"] = {"examples": fs.prefill_kl_cache(tr), "s": None}
                sync()
                row["kl_cache_prefill"]["s"] = round(time.time() - t, 2)
                row["kl_cache_prefill"]["bytes_mb"] = round(fs._STATE["bytes"] / 2 ** 20, 1)

            def run_step(i):
                tr.step(batches[i % len(batches)])
            for i in range(args.warmup):
                run_step(i)
            times = []
            for i in range(args.steps):
                sync()
                t = time.time()
                run_step(i)
                sync()
                times.append(time.time() - t)
            times_sorted = sorted(times)
            row["s_per_step"] = round(sum(times) / len(times), 4)
            row["s_per_step_median"] = round(times_sorted[len(times) // 2], 4)
            row["step_seconds"] = [round(x, 4) for x in times]
            if cuda:
                row["peak_alloc_gib"] = round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)
            if VARIANTS[name].get("kl_cache"):
                row["kl_cache_stats"] = {"hits": fs._STATE["hits"], "miss": fs._STATE["miss"], "cached": len(fs._CACHE)}
            if args.prof_steps:
                row["profile"] = profile_steps(run_step, args.prof_steps, args.device, args.top)
        except Exception as e:  # noqa: BLE001
            row["error"] = repr(e)[:500]
            if cuda and isinstance(e, torch.cuda.OutOfMemoryError):
                row["error"] = "OOM: " + row["error"]
        finally:
            sb.TOK_BUDGET = old
            undo()
            undo_t()
            pm.zero_grad(set_to_none=True)
            pm.eval()
            tr = None
            if cuda:
                torch.cuda.empty_cache()
        base = res["variants"].get("baseline", {}).get("s_per_step")
        if base and row.get("s_per_step"):
            row["speedup_vs_baseline"] = round(base / row["s_per_step"], 3)
            row["saved_pct"] = round(100 * (1 - row["s_per_step"] / base), 1)
        save()
        print(f"[{key}] {row.get('s_per_step')} s/step  saved {row.get('saved_pct')}%  parity {row.get('parity', {}).get('pass')}  {row.get('error', '')}", flush=True)
    save()
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
