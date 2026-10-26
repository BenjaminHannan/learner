"""Run a real sleepb.py arm with the frozen q4 base stored packed (4-bit codes + bf16 scale/bias, packed.py) and optional gradient checkpointing, so the arm fits a 32 GB RTX 5090.
Opt-in wrapper: sleepb.py is not edited, nothing changes unless you run this file.
  python speed/qwen36_mem/run_sleepb_packed.py [--packed-compile] [--grad-ckpt] [--kl-cache] -- <the normal sleepb.py arguments, unchanged>
  e.g. python speed/qwen36_mem/run_sleepb_packed.py --packed-compile --grad-ckpt --kl-cache -- --arm ab_ob_b4_nb --week W.json --out OUT --q4-base --q4-mlx-moe
Hooks (all module-level names of sleepb, looked up at call time, so a wrapper replaces them cleanly):
  sleepb.load_model  : when --q4-base --q4-mlx-moe are in the args and CUDA is the target, the model is loaded on the CPU (the 64.6 GiB bf16 base cannot sit on a 32 GB card; needs ~70 GB host RAM).
  sleepb.q4_apply    : the first call after such a load packs the model (packed.pack_model, device=cuda: layer by layer on the GPU) instead of qdq'ing it in bf16, then moves the rest to the GPU.
                       pack_model quantizes from the raw weights with the same math as q4_apply, so the result equals the qdq base bit for bit (packed.py / test_packed.py). Later q4_apply calls (selftests) are untouched.
  sleepb.Trainer.step: --grad-ckpt turns HF gradient checkpointing on (use_reentrant=False; the layers only checkpoint while pm.train(), which Trainer.step sets and undoes), so generation / eval
                       (pm.eval()) and use_cache are unaffected. --kl-cache installs fast_step's KL-reference cache (and its use_cache=False decoder call).
  Peak CUDA memory per phase (dream = Lang.generate outside eval, train = Trainer.step, eval = score_week / score_arc / fwd_recall) is printed when a phase sets a new high, and as a summary at exit.
Not supported: arms that edit base weights in place (DELTA_ARMS: ab_ob_merge / full / local ...): PackedLinear has no dense .weight. Use the plain sleepb for those."""
import argparse
import atexit
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.normpath(os.path.join(HERE, "../../backbone/sleep/brain"))
sys.path[:0] = [HERE, os.path.join(HERE, "../qwen36_step"), BRAIN, os.path.dirname(BRAIN), os.path.dirname(os.path.dirname(BRAIN))]
import torch  # noqa: E402

import packed as P  # noqa: E402

PEAK = {}  # phase -> peak GiB allocated (CUDA only)


class PhaseMeter:
    """Peak CUDA memory per top-level phase (nested phases count for the outer one)."""

    def __init__(s):
        s.depth = 0

    @contextlib.contextmanager
    def phase(s, name):
        if not torch.cuda.is_available() or s.depth:
            s.depth += 1
            try:
                yield
            finally:
                s.depth -= 1
            return
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        s.depth = 1
        t0 = time.time()
        try:
            yield
        finally:
            s.depth = 0
            torch.cuda.synchronize()
            g = torch.cuda.max_memory_allocated() / 2 ** 30
            if g > PEAK.get(name, 0.0):
                PEAK[name] = g
                print(f"[mem] {name}: new peak {g:.2f} GiB allocated, {torch.cuda.max_memory_reserved() / 2 ** 30:.2f} GiB reserved ({time.time() - t0:.1f}s)", flush=True)


def install(sb, packed_compile=False, grad_ckpt=False, kl_cache=False, packed_min_numel=1 << 20):
    """Patch the sleepb module; returns undo(). Safe to call on a tiny CPU run (the test does)."""
    st = {"pending": None}
    load0, q4_0 = sb.load_model, sb.q4_apply
    meter = PhaseMeter()
    saved = {}

    def load_model(args, device, dtype):
        want = bool(getattr(args, "q4_base", False) and getattr(args, "q4_mlx_moe", False))
        if want and device.type == "cuda":
            lm, tok = load0(args, torch.device("cpu"), dtype)  # packing happens in q4_apply, layer by layer on the GPU
        else:
            lm, tok = load0(args, device, dtype)
        st["pending"] = (id(lm), device) if want else None
        return lm, tok

    def q4_apply(lm, group=64, bits=4, bits_for=None, extra=None, chunk=None):
        if st["pending"] is None or st["pending"][0] != id(lm):
            return q4_0(lm, group, bits, bits_for, extra, chunk)
        device = st["pending"][1]
        st["pending"] = None
        if bits != 4 or not (bits_for and extra):
            raise SystemExit("run_sleepb_packed needs --q4-base --q4-mlx-moe with --q4-bits 4 (the recipe packed.py reproduces)")
        t0 = time.time()
        r = P.pack_model(lm, group, bits, bits_for, extra, device=device if device.type == "cuda" else None, min_numel=packed_min_numel, compile=packed_compile)
        lm.to(device)
        n_packed = r["packed_experts"] + r["packed_linear"]
        print(f"[packed] {r['packed_experts']} expert tensors + {r['packed_linear']} Linears packed, {r['dense_qdq']} qdq'd dense, {r['skipped']} skipped; "
              f"param bytes {r['bytes_before'] / 2 ** 30:.2f} -> {r['bytes_after'] / 2 ** 30:.2f} GiB ({time.time() - t0:.0f}s, compile={packed_compile})", flush=True)
        if device.type == "cuda":
            print(f"[mem] after pack: {torch.cuda.memory_allocated() / 2 ** 30:.2f} GiB allocated, peak {torch.cuda.max_memory_allocated() / 2 ** 30:.2f}", flush=True)
            PEAK["load+pack"] = torch.cuda.max_memory_allocated() / 2 ** 30
        # the dict main() logs (mean_rel_fro is not computed: the qdq error is not measured on the packed path)
        return {"tensors": n_packed + r["dense_qdq"], "skipped": r["skipped"], "params": 0, "mean_rel_fro": None, "group": group, "bits": bits, "by_bits": {},
                "packed": {k: r[k] for k in ("packed_experts", "packed_linear", "dense_qdq", "skipped", "bytes_before", "bytes_after")}}

    sb.load_model, sb.q4_apply = load_model, q4_apply
    undos = [lambda: (setattr(sb, "load_model", load0), setattr(sb, "q4_apply", q4_0))]
    if kl_cache:
        import fast_step
        undos.append(fast_step.install(sb, kl_cache=True))

    def wrap(obj, name, phase, pre=None):
        f0 = getattr(obj, name)
        saved[(id(obj), name)] = f0

        def f(*a, **k):
            if pre:
                pre(*a, **k)
            with meter.phase(phase):
                return f0(*a, **k)
        setattr(obj, name, f)
        undos.append(lambda: setattr(obj, name, f0))

    def ckpt_on(trainer, batch=None):
        pm = trainer.pm
        base = pm.get_base_model() if hasattr(pm, "get_base_model") else pm
        if not getattr(base, "is_gradient_checkpointing", False):
            base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            base.enable_input_require_grads()  # harmless with use_reentrant=False; keeps the grads flowing if the flag is flipped
            print("[ckpt] gradient checkpointing on (use_reentrant=False), active in train mode only", flush=True)
        base.config.use_cache = getattr(base.config, "use_cache", True)  # generation keeps its cache: HF only forces use_cache=False inside a checkpointed training forward
    wrap(sb.Trainer, "step", "train", ckpt_on if grad_ckpt else None)  # after fast_step.install, so it wraps the fast step
    wrap(sb.Lang, "generate", "dream")
    for fn in ("score_week", "score_arc", "fwd_recall"):
        if hasattr(sb, fn):
            wrap(sb, fn, "eval")

    def undo():
        for u in reversed(undos):
            u()
    return undo


def summary():
    if PEAK:
        print("[mem] peak GiB allocated per phase: " + json.dumps({k: round(v, 2) for k, v in PEAK.items()}), flush=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    own, rest = (argv[:argv.index("--")], argv[argv.index("--") + 1:]) if "--" in argv else (argv, [])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, usage="%(prog)s [options] -- <sleepb.py args>")
    ap.add_argument("--packed-compile", action="store_true", help="torch.compile the dequant (one fused kernel; 2.1-2.5x slower per step than the qdq base instead of far worse)")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing for training steps only")
    ap.add_argument("--kl-cache", action="store_true", help="speed/qwen36_step fast_step KL-reference cache")
    ap.add_argument("--packed-min-numel", type=int, default=1 << 20, help="Linears below this many weights stay dense (tests lower it)")
    a = ap.parse_args(own)
    if not rest:
        ap.error("put the sleepb.py arguments after --")
    import sleepb
    install(sleepb, a.packed_compile, a.grad_ckpt, a.kl_cache, a.packed_min_numel)
    atexit.register(summary)
    sys.argv = [os.path.join(BRAIN, "sleepb.py")] + rest
    try:
        sleepb.main()
    except BaseException as e:  # same error file as sleepb's own __main__ (the Vast label reporter reads it)
        import traceback
        from pathlib import Path
        o = next((rest[i + 1] for i, x in enumerate(rest[:-1]) if x == "--out"), ".")
        arm = next((rest[i + 1] for i, x in enumerate(rest[:-1]) if x == "--arm"), "x")
        Path(o).mkdir(parents=True, exist_ok=True)
        Path(o, f"result_{arm}.error.json").write_text(json.dumps({"error": repr(e)[:300], "trace": traceback.format_exc()[-4000:]}))
        raise


if __name__ == "__main__":
    main()
