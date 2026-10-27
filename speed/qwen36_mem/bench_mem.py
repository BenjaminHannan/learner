"""GPU bench (the lead runs it on a rented box): frozen-base memory, qdq-in-bf16 (today) vs packed uint4 (packed.py), through the real sleepb.Trainer at several tok budgets. One JSON out.
    python speed/qwen36_mem/bench_mem.py --out speed/qwen36_mem/bench_mem.json            # modes qdq, packed, packed_fit; budgets 2048,4096,8192 (each plain and with gradient checkpointing)
    python speed/qwen36_mem/bench_mem.py --tiny --out /tmp/t.json                          # CPU smoke test of the script itself (random tiny model, numbers meaningless)
Modes: qdq = load bf16 on the GPU, sleepb.q4_apply (the --q4-base --q4-mlx-moe recipe), LoRA.  packed = same load, packed.pack_model instead of q4_apply (peak at load is still the 64.6 GiB bf16).
packed_fit = 32 GB RTX 5090 emulation: load on CPU, pack layer by layer on the GPU, cap the caching allocator at --fit-gib (5090 = 31.36 GiB usable, same sm_120 as the PRO 6000), train with checkpointing.
Needs: the moe_bench.py deps (transformers 5.20.2, peft 0.21.2, fla), the model in the HF cache (moe_bench.py --skip-download defaults). Each mode reloads the model (~20 s from page cache), so ~15 min total."""
import argparse, gc, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "../../backbone/sleep/brain"), os.path.join(HERE, "../../backbone")]
import torch
import moe_bench as mb
import sleepb
import packed as P

R = lambda x, n=3: None if x is None else round(x, n)  # noqa: E731


def probe(lm, device, vocab, n=96):
    """Last-position logits (fp32, cpu) of a fixed random token sequence: bitwise comparable across modes (same model, same seed)."""
    ids = torch.randint(2, vocab, (1, n), generator=torch.Generator().manual_seed(7)).to(device)
    with torch.no_grad():
        return lm(input_ids=ids).logits[0, -1].float().cpu()


def one_mode(mode, args, rec, device, cuda):
    t0 = time.time()
    out = {"mode": mode}
    cap = mode == "packed_fit"
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    ld_dev = torch.device("cpu") if cap else device
    margs = argparse.Namespace(**vars(args))
    lm, tok = mb.load_model(margs, rec, ld_dev)
    out["load_seconds"] = R(time.time() - t0, 1)
    from sleep1 import Lang
    from train import K2_TYPE
    L = Lang(tok, False, device, k2=lm.config.model_type == K2_TYPE)
    t1 = time.time()
    if mode == "qdq":
        st = sleepb.q4_apply(lm, 64, 4, sleepb.Q4_MLX_MOE_BITS, sleepb.Q4_MLX_MOE_PARAMS)
        out["q4"] = {k: st[k] for k in ("tensors", "params", "by_bits")}
    else:
        st = P.pack_model(lm, device=device if cap else None, compile=args.compile_dequant)
        out["pack"] = st
        out["compile_dequant"] = args.compile_dequant
    if cuda:
        torch.cuda.synchronize()
    lm.to(device)
    out["q4_or_pack_seconds"] = R(time.time() - t1, 1)
    if cuda:
        out["weights_gib_allocated"] = mb.gib(torch.cuda.memory_allocated())
        out["peak_gib_load_plus_pack"] = mb.gib(torch.cuda.max_memory_allocated())
        if cap:
            frac = args.fit_gib * 2 ** 30 / torch.cuda.get_device_properties(0).total_memory
            torch.cuda.set_per_process_memory_fraction(min(frac, 1.0))
            out["fit_cap_gib"] = args.fit_gib
    lm.eval()
    mb.set_experts(lm, "grouped_mm")
    out["probe_logits"] = probe(lm, device, lm.config.vocab_size)  # tensor, popped before JSON
    pm = mb.attach_lora(lm, args, rec)
    rng = random.Random(args.seed)
    batch, replay = mb.trainer_batch(L, args.bsz, args.replay_bsz, rng)
    rows = out["trainer"] = {}
    need_ckpt = False
    for budget in args.tok_budgets:
        row = rows[str(budget)] = {}
        for ckpt in ([True] if cap else [False, True]):
            key = "ckpt" if ckpt else "plain"
            try:
                a = mb.trainer_attempt(args, rec, lm, pm, L, sleepb, budget, ckpt, batch, replay, cuda)
                row[key] = {"status": "ok", "s_per_step": a["s_per_step"], "peak_alloc_gib": a.get("peak_alloc_gib"), "peak_reserved_gib": a.get("peak_reserved_gib"), "padded_tokens": a["padded_tokens"]}
            except Exception as e:  # noqa: BLE001
                oom = mb.is_oom(e)
                row[key] = {"status": "oom" if oom else "error", "error": None if oom else repr(e)[:300], **mb.peak(cuda)}
                mb.free_gpu(pm)
            rec.log(f"[{mode}] budget {budget} {key}: {row[key]}")
        if cuda:
            torch.cuda.reset_peak_memory_stats()
    if cap:
        ok = [r["ckpt"] for r in rows.values() if r["ckpt"]["status"] == "ok"]
        out["fits_5090"] = bool(ok)
        out["fits_5090_largest_budget_ok"] = max((int(b) for b, r in rows.items() if r["ckpt"]["status"] == "ok"), default=None)
    out["total_seconds"] = R(time.time() - t0, 1)
    del pm, lm
    gc.collect()
    mb.free_gpu()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "bench_mem.json"))
    ap.add_argument("--modes", default="qdq,packed,packed_fit")
    ap.add_argument("--tok-budgets", type=mb.csv_ints, default=[2048, 4096, 8192])
    ap.add_argument("--fit-gib", type=float, default=31.36, help="allocator cap for packed_fit (RTX 5090: 32 GB card)")
    ap.add_argument("--compile-dequant", action="store_true", help="torch.compile the dequant piece (one fused kernel; the bits are the same)")
    ap.add_argument("--tiny", action="store_true", help="CPU smoke test with a random tiny model")
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--trainer-warmup", type=int, default=1)
    ap.add_argument("--trainer-timed", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=mb.QWEN_REPO)
    ap.add_argument("--revision", default=mb.QWEN_REV)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lora-shared", action="store_true", default=True)
    args = ap.parse_args()
    cuda = torch.cuda.is_available() and not args.tiny
    if not cuda and not args.tiny:
        sys.exit("no CUDA device: use --tiny for a CPU smoke test")
    device = torch.device("cuda:0" if cuda else "cpu")
    rec = mb.Rec(args.out, args)
    rec.res.update(schema="bench_mem-1", env=mb.env_info(), modes={})
    probes = {}
    for mode in args.modes.split(","):
        if mode == "packed_fit" and not cuda:
            rec.res["modes"][mode] = {"skipped": "needs a GPU"}
            continue
        try:
            r = one_mode(mode, args, rec, device, cuda)
            probes[mode] = r.pop("probe_logits")
        except Exception as e:  # noqa: BLE001
            import traceback
            r = {"mode": mode, "status": "error", "error": repr(e)[:500], "trace": traceback.format_exc()[-1500:]}
            rec.log(f"!! {mode} failed: {e!r}")
            mb.free_gpu()
        rec.res["modes"][mode] = r
        rec.save()
    ref = probes.get("qdq")
    if ref is not None:
        rec.res["logits_bitwise_equal_to_qdq"] = {m: bool(torch.equal(ref, p)) for m, p in probes.items() if m != "qdq"}
        rec.res["logits_max_abs_diff_to_qdq"] = {m: float((ref - p).abs().max()) for m, p in probes.items() if m != "qdq"}
    cmp_ = {}
    q, p = rec.res["modes"].get("qdq", {}).get("trainer", {}), rec.res["modes"].get("packed", {}).get("trainer", {})
    for b in q:
        for k in ("plain", "ckpt"):
            a, c = q.get(b, {}).get(k), p.get(b, {}).get(k)
            if a and c and a["status"] == c["status"] == "ok":
                cmp_[f"{b}/{k}"] = {"qdq_s": a["s_per_step"], "packed_s": c["s_per_step"], "slowdown": R(c["s_per_step"] / a["s_per_step"]), "qdq_peak_gib": a["peak_alloc_gib"], "packed_peak_gib": c["peak_alloc_gib"]}
    rec.res["compare"] = cmp_
    rec.res["partial"] = False
    rec.save()
    print(json.dumps({k: rec.res[k] for k in ("modes", "compare", "logits_bitwise_equal_to_qdq") if k in rec.res}, indent=1, default=str))


if __name__ == "__main__":
    main()
