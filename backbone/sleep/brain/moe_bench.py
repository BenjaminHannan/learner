#!/usr/bin/env python3
"""One-hour GPU speed bench for a Sleep-B night on Qwen/Qwen3.6-35B-A3B (a big MoE) held in a fake-quantized 4-bit base, with LoRA on top.

The base is what an MLX 4-bit model would be (sleepb.q4_apply, the MLX affine recipe of mlx-community/Qwen3.6-35B-A3B-4bit): 4 bits, groups of 64 along the input dim on every Linear
and Embedding, and on the fused 3-D expert tensors; 8 bits for every mlp.gate (router weight) and mlp.shared_expert_gate. The weights stay bf16 in GPU memory (quantize-dequantize in
place), so this bench measures the SPEED of a night on that base; it does not save memory (35B x 2 bytes = ~65 GiB of weights on one 95 GB GPU). bitsandbytes is not used.

It measures, in one process, and writes one JSON (rewritten after every stage):
  plan       the model on the meta device (config + code only, no weights): parameter breakdown, fused 3-D expert tensors, LoRA target matches and trainable parameters, what q4 will touch
  download   snapshot_download of the weights, timed (~72 GB; disk check first)
  load       train.load_model (the loader sleepb uses): Qwen3_5MoeForCausalLM, bf16, straight onto the GPU; load seconds, peak GPU memory, peak host RSS
  q4         sleepb.q4_apply with the MLX recipe, in slices of <= 64M elements (small fp32 temporaries); seconds, peak memory, tensors per bit width, and a before/after sanity check
  lora       LoraConfig as in sleepb (r16, alpha 32, train.LORA_TARGETS); matched module names counted, trainable parameters; --lora-shared adds the shared expert MLPs
  experts    transformers' experts implementation for the fused 3-D experts (grouped_mm / eager / batched_mm): forward and training timings, numeric agreement; the fastest valid one is
             used for training and (separately) for generation. batched_mm is only timed at the decode shape (its prefill gathers 2048 x 8 expert matrices = 68 GB)
  train_micro  micro-batches of 2048 tokens (8 x 256) -> sleepb.tgt_logits + CE + backward + AdamW step; 2 warm-up + 8 timed; plain, then gradient checkpointing if it runs out of memory
  train_trainer  the real sleepb.Trainer.step on a synthetic batch shaped like sleepb --bench-train's (16 examples + KL replay) at --tok-budget 2048 and 4096 (plain, then checkpointing on OOM)
  gen        Lang.generate, adapter off, at gen_bs 32 / 64 / 128: the tagger shape (prompt ~220 tokens, 160 new, greedy) and the dream shape (prompt ~450, sampled; a few steps
             measured, the rest extrapolated), prefill timed alone; new tokens per second, peak memory
  estimate   the wall time and dollars of one Week-2 4x-work ab_ob_b4_nb arm at the measured speeds, using the step and generation counts of results_a9/result_ab_ob_b4_nb.json
             (the pack leaves that file out; run it locally with --estimate-from bench.json, no GPU needed)

  python3 backbone/sleep/brain/moe_bench.py --out out/moebench/bench.json              # the box (see run_box.sh MOEBENCH)
  python3 backbone/sleep/brain/moe_bench.py --plan-only --out /tmp/x/plan.json         # CPU, no weights: the meta-device plan only
  python3 backbone/sleep/brain/moe_bench.py --tiny --out /tmp/x/bench.json             # CPU: tiny random Qwen3_5MoeForCausalLM (real Qwen3.6 tokenizer), fp32
  python3 backbone/sleep/brain/moe_bench.py --estimate-from out/moebench/bench.json --usd-per-hour 1.2   # no GPU

This is a speed bench: prompts are synthetic (random common words in Qwen chat framing), the weights are never changed (lr 0), and generations are forced to run
the full max_new (min_new_tokens = max_new) so every batch decodes the same number of steps. Nothing here changes sleepb.py's, train.py's or sleep1.py's behaviour.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import gc
import json
import math
import os
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent.parent):  # sleepb.py (here), sleep1.py / facts.py (backbone/sleep), train.py (backbone)
    sys.path.insert(0, str(_p))

QWEN_REPO = "Qwen/Qwen3.6-35B-A3B"
QWEN_REV = "995ad96eacd98c81ed38be0c5b274b04031597b0"
SHARED_RE = r".*\.layers\.\d+\.mlp\.shared_experts?\.(gate_proj|up_proj|down_proj)"  # the shared expert; train.LORA_TARGETS does not match it
A9_DEFAULT = HERE / "results_a9" / "result_ab_ob_b4_nb.json"
USD_PER_HOUR = 1.20  # RTX PRO 6000 96GB on Vast (backbone/RUNLOG.md); override with --usd-per-hour
GEN_BS = (32, 64, 128)
TOK_BUDGETS = (2048, 4096)
WORDS = ("harbour lantern market river bakery morning ledger orchard train window garden letter bridge candle winter copper meadow village stone kettle "
         "carpenter ferry blanket thunder paper valley mirror engine basket island whistle saddle pencil forest anchor button cellar dragon feather gravel "
         "harvest jacket kitchen ladder marble needle oyster pillow quarry ribbon shadow tunnel umbrella velvet wagon yellow zipper apple bottle castle desert "
         "empire flower glacier hammer iron jungle kitten lemon mountain nickel ocean planet quilt rocket silver temple unicorn violin walnut yarn zebra").split()


# ------------------------------------------------------------------ plumbing
def gib(x):
    return None if x is None else round(x / 2 ** 30, 3)


def mem_now():
    """(this process's resident bytes, system MemAvailable bytes) from /proc; None where unavailable."""
    rss = avail = None
    try:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) * 1024
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                avail = int(line.split()[1]) * 1024
    except OSError:
        pass
    return rss, avail


class Rec:
    """The result dict, its JSON file (rewritten after every stage), the log file next to it, and the time budget."""

    def __init__(self, out, args):
        self.path = Path(out)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.logf = open(self.path.with_suffix(".log"), "a")
        self.t0 = time.time()
        self.deadline = None
        self._lock = threading.Lock()
        self.res = {"schema": "moebench-1", "started_utc": time.strftime("%FT%TZ", time.gmtime()), "args": {k: v for k, v in vars(args).items()},
                    "stages": {}, "partial": True}

    def log(self, msg):
        line = f"[{time.strftime('%H:%M:%S')} +{time.time() - self.t0:5.0f}s] {msg}"
        print(line, flush=True)
        self.logf.write(line + "\n")
        self.logf.flush()

    def save(self):
        with self._lock:
            self.res["elapsed_s"] = round(time.time() - self.t0, 1)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(self.res, indent=1, default=str))
            os.replace(tmp, self.path)

    def time_left(self):
        return float("inf") if self.deadline is None else self.deadline - time.time()

    @contextlib.contextmanager
    def stage(self, name, fatal=False):
        """Stage bookkeeping: status / seconds in res["stages"][name]; an exception is logged and recorded (the run goes on unless fatal); the JSON is saved either way."""
        self.log(f"== stage {name}")
        t = time.time()
        st = self.res["stages"][name] = {"status": "running"}
        self.save()
        try:
            yield st
            if st["status"] == "running":
                st["status"] = "ok"
        except (KeyboardInterrupt, SystemExit):
            st["status"] = "interrupted"
            raise
        except BaseException as e:  # noqa: BLE001 - a failed stage must not lose the other stages' numbers
            tb = traceback.format_exc()
            st.update(status="error", error=repr(e)[:500], trace=tb[-2500:])
            self.log(f"!! stage {name} failed: {e!r}\n{tb[-1500:]}")
            if fatal:
                st["seconds"] = round(time.time() - t, 1)
                self.save()
                raise SystemExit(1)
        finally:
            st["seconds"] = round(time.time() - t, 1)
            self.save()


class Sampler(threading.Thread):
    """Background sampler: peak host RSS, lowest system MemAvailable, lowest free GPU memory (device level), and a log line every `every` seconds
    (with the size of `watch` - a directory - while a download runs). stop() returns the peaks."""

    def __init__(self, rec, label, every=60.0, watch=None):
        super().__init__(daemon=True)
        self.rec, self.label, self.every, self.watch = rec, label, every, watch
        self.ev = threading.Event()
        self.max_rss = 0
        self.min_avail = None
        self.min_gpu_free = None

    def watch_bytes(self):
        try:
            return sum(e.stat().st_size for e in os.scandir(self.watch) if e.is_file())
        except OSError:
            return None

    def run(self):
        import torch
        last, t0 = 0.0, time.time()
        while not self.ev.wait(0.5):
            rss, avail = mem_now()
            if rss:
                self.max_rss = max(self.max_rss, rss)
            if avail is not None:
                self.min_avail = avail if self.min_avail is None else min(self.min_avail, avail)
            used = None
            if torch.cuda.is_available():
                try:
                    free, total = torch.cuda.mem_get_info()
                    self.min_gpu_free = free if self.min_gpu_free is None else min(self.min_gpu_free, free)
                    used = total - free
                except Exception:  # noqa: BLE001
                    pass
            if time.time() - last >= self.every:
                last = time.time()
                dl = self.watch_bytes() if self.watch else None
                self.rec.log(f"[mon:{self.label}] {time.time() - t0:5.0f}s rss {gib(rss)} GiB, host free {gib(avail)} GiB, gpu used {gib(used)} GiB"
                             + (f", downloaded {gib(dl)} GiB" if dl is not None else ""))

    def stop(self):
        self.ev.set()
        self.join(3)
        hwm = 0
        try:  # the kernel's own high-water mark of this process (covers what the 0.5 s sampling could miss)
            hwm = next(int(l.split()[1]) * 1024 for l in open("/proc/self/status") if l.startswith("VmHWM:"))
        except (OSError, StopIteration):
            pass
        return {"peak_rss_gib": gib(max(self.max_rss, hwm)), "min_host_available_gib": gib(self.min_avail), "min_gpu_free_gib": gib(self.min_gpu_free)}


def env_info():
    import importlib.metadata as md
    import importlib.util
    import torch
    d = {"python": sys.version.split()[0], "torch": torch.__version__, "torch_cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available()}
    for pkg in ("transformers", "peft", "accelerate", "huggingface_hub", "hf_xet", "flash-linear-attention", "causal-conv1d", "triton"):
        try:
            d[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            d[pkg] = None
    d["fla_importable"] = importlib.util.find_spec("fla") is not None  # Gated DeltaNet kernels; without them transformers uses a slow pure-PyTorch path
    d["causal_conv1d_importable"] = importlib.util.find_spec("causal_conv1d") is not None
    d["torch_grouped_mm"] = hasattr(torch.nn.functional, "grouped_mm") or hasattr(torch, "_grouped_mm")
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        d.update(gpu=p.name, gpu_capability=list(torch.cuda.get_device_capability(0)), gpu_total_gib=gib(p.total_memory))
        try:
            d["nvidia_smi"] = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], capture_output=True, text=True,
                                             timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        d["host_ram_gib"] = gib(int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal:")).split()[1]) * 1024)
    except Exception:  # noqa: BLE001
        pass
    d["cpu_count"] = os.cpu_count()
    d["PYTORCH_CUDA_ALLOC_CONF"] = os.environ.get("PYTORCH_CUDA_ALLOC_CONF")
    return d


def free_gpu(pm=None):
    import torch
    if pm is not None:
        pm.zero_grad(set_to_none=True)
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def is_oom(e):
    import torch
    return isinstance(e, torch.cuda.OutOfMemoryError) or "out of memory" in str(e).lower()


def peak(cuda):
    import torch
    return {"peak_alloc_gib": gib(torch.cuda.max_memory_allocated()), "peak_reserved_gib": gib(torch.cuda.max_memory_reserved())} if cuda else {}


def generic(name):
    return re.sub(r"\.\d+(\.|$)", r".N\1", name)


# ------------------------------------------------------------------ the model: plan, tiny build, download, load
def model_type_of(repo, rev):
    from transformers import PretrainedConfig
    return PretrainedConfig.get_config_dict(repo, revision=rev)[0].get("model_type")


def category(name):
    """Coarse parameter family of a Qwen3.5-MoE tensor name, for the breakdown."""
    for key, label in (("embed_tokens", "embed_tokens"), ("lm_head", "lm_head"), (".mlp.experts.", "routed_experts_fused_3d"), (".mlp.shared_expert_gate", "shared_expert_gate"),
                       (".mlp.shared_expert.", "shared_expert"), (".mlp.gate.", "router"), (".linear_attn.conv1d", "gdn_conv1d"), (".linear_attn.", "gdn_linear_attention"),
                       (".self_attn.", "full_attention"), ("norm", "norms")):
        if key in name:
            return label
    return "other"


def lora_targets(lora_shared):
    from train import LORA_TARGETS
    return f"(?:{LORA_TARGETS})|(?:{SHARED_RE})" if lora_shared else LORA_TARGETS


def lora_matches(lm, targets):
    """The nn.Linear modules peft's regex target_modules would wrap (re.fullmatch on the module name, as peft does for a string)."""
    import torch
    return [(n, m) for n, m in lm.named_modules() if isinstance(m, torch.nn.Linear) and re.fullmatch(targets, n)]


def q4_dry_run(lm, group=64, bits=4):
    """Which tensors sleepb.q4_apply(lm, group, bits, Q4_MLX_MOE_BITS, Q4_MLX_MOE_PARAMS) would quantize, from names and shapes only (works on the meta device)."""
    import torch
    import sleepb
    bits_for = [(re.compile(r), b) for r, b in sleepb.Q4_MLX_MOE_BITS]
    extra = [re.compile(r) for r in sleepb.Q4_MLX_MOE_PARAMS]
    cand = {}
    for n, m in lm.named_modules():
        if isinstance(m, (torch.nn.Linear, torch.nn.Embedding)):
            cand[f"{n}.weight"] = m.weight
    for n, p in lm.named_parameters():
        if n not in cand and any(rx.search(n) for rx in extra):
            cand[n] = p
    by, skipped, seen = collections.defaultdict(lambda: [0, 0]), [], set()
    for n, w in cand.items():
        if id(w) in seen:
            continue
        seen.add(id(w))
        nb = next((b for rx, b in bits_for if rx.search(n)), bits)
        if w.shape[-1] % group:
            skipped.append((generic(n), list(w.shape)))
            continue
        by[nb][0] += 1
        by[nb][1] += w.numel()
    tot = sum(p.numel() for p in lm.parameters())
    qp = sum(v[1] for v in by.values())
    return {"by_bits": {str(b): {"tensors": v[0], "params": v[1]} for b, v in sorted(by.items())}, "skipped_not_divisible": sorted(set(map(str, skipped)))[:10],
            "params_quantized_b": round(qp / 1e9, 4), "params_not_quantized_b": round((tot - qp) / 1e9, 4)}


def plan_model(args, rec):
    """Before the download: build the model on the meta device from the repo's config + code (no weights), and work out the parameter breakdown, the LoRA matches and trainable parameters
    (analytically: r x (in + out) per module), what q4 touches, and whether the bf16 weights fit the GPU. Stores rec.res["plan"]."""
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM
    kw = {"revision": args.revision} if args.revision else {}
    cfg = AutoConfig.from_pretrained(args.model, **kw)
    t0 = time.time()
    with torch.device("meta"):
        meta = AutoModelForCausalLM.from_config(cfg, dtype=torch.bfloat16)
    tc = meta.config
    by = collections.Counter()
    for n, p in meta.named_parameters():
        by[category(n)] += p.numel()
    total = sum(by.values())
    fused = [(n, p.numel()) for n, p in meta.named_parameters() if p.dim() >= 3 and ".mlp.experts." in n]
    plan = {"model_class": type(meta).__name__, "build_seconds": round(time.time() - t0, 1), "config_model_type": tc.model_type, "layers": tc.num_hidden_layers,
            "layer_types": dict(collections.Counter(getattr(tc, "layer_types", None) or [])), "hidden_size": tc.hidden_size, "vocab_size": tc.vocab_size,
            "num_experts": getattr(tc, "num_experts", None), "experts_per_token": getattr(tc, "num_experts_per_tok", None),
            "params_total_b": round(total / 1e9, 4), "params_by_family_b": {k: round(v / 1e9, 4) for k, v in by.most_common()},
            "fused_3d_expert_tensors": len(fused), "fused_3d_expert_gib_bf16": round(sum(c for _, c in fused) * 2 / 2 ** 30, 2),
            "weights_gib_bf16": round(total * 2 / 2 ** 30, 2), "experts_implementation_default": getattr(tc, "_experts_implementation", None)}
    for tgt_name, shared in (("lora", False), ("lora_with_shared_expert", True)):
        mods = lora_matches(meta, lora_targets(shared))
        plan[tgt_name] = {"matched": len(mods), "matched_by_pattern": dict(collections.Counter(generic(n) for n, _ in mods)),
                          "trainable_params": sum(args.rank * (m.in_features + m.out_features) for _, m in mods)}
    plan["q4"] = q4_dry_run(meta)
    # real 4-bit storage (4-bit codes + a bf16 scale and bias per 64) would take ~0.5625 bytes per quantized weight; the fake-quantized bf16 base takes 2
    plan["q4"]["gib_if_real_4bit"] = round((plan["q4"]["params_quantized_b"] * 1e9 * 0.5625 + plan["q4"]["params_not_quantized_b"] * 1e9 * 2) / 2 ** 30, 1)
    del meta
    warn = []
    if not str(tc.model_type).startswith("qwen3_5_moe"):
        warn.append(f"model_type {tc.model_type!r} is not qwen3_5_moe: the q4 recipe patterns (mlp.experts.*, mlp.gate, mlp.shared_expert_gate) were written for Qwen3.5/3.6 MoE")
    if plan["q4"]["skipped_not_divisible"]:
        warn.append(f"tensors whose last dim is not divisible by 64 stay in bf16: {plan['q4']['skipped_not_divisible']}")
    if plan["q4"]["by_bits"].get("8", {}).get("tensors", 0) != 2 * tc.num_hidden_layers:
        warn.append(f"expected {2 * tc.num_hidden_layers} 8-bit tensors (mlp.gate + mlp.shared_expert_gate per layer), q4 plan has {plan['q4']['by_bits'].get('8')}")
    total_gpu = None
    try:
        if torch.cuda.is_available():
            total_gpu = torch.cuda.get_device_properties(0).total_memory
    except Exception:  # noqa: BLE001
        pass
    if total_gpu:
        plan["gpu_total_gib"] = gib(total_gpu)
        plan["headroom_gib_after_weights"] = round(total_gpu / 2 ** 30 - plan["weights_gib_bf16"], 2)
        plan["fits_gpu"] = plan["weights_gib_bf16"] < 0.9 * total_gpu / 2 ** 30
        if not plan["fits_gpu"]:
            warn.append(f"the bf16 weights ({plan['weights_gib_bf16']} GiB) do not fit a {gib(total_gpu)} GiB GPU with room for activations")
    plan["warnings"] = warn
    rec.res["plan"] = plan
    for w in warn:
        rec.log(f"!! plan: {w}")
    rec.log(f"[plan] {plan['model_class']}: {plan['params_total_b']} B params ({plan['weights_gib_bf16']} GiB bf16), layers {plan['layer_types']}, fused expert tensors "
            f"{plan['fused_3d_expert_tensors']} ({plan['fused_3d_expert_gib_bf16']} GiB); by family {plan['params_by_family_b']}")
    rec.log(f"[plan] LoRA (train.LORA_TARGETS): {plan['lora']['matched']} modules, {plan['lora']['trainable_params']:,} trainable params; with the shared expert: "
            f"{plan['lora_with_shared_expert']['matched']} modules, {plan['lora_with_shared_expert']['trainable_params']:,}")
    rec.log(f"[plan] q4: {plan['q4']}")
    if total_gpu and not plan.get("fits_gpu") and not args.force_load:
        raise RuntimeError("the bf16 weights do not fit the GPU: stopping before the download (--force-load to try anyway)")


def tiny_config(vocab, eos, pad):
    """A tiny random Qwen3.5-MoE text model with every module type of the real one: 3 Gated DeltaNet + 1 full-attention layer, fused 3-D experts (8, top 2) and a shared expert. Every Linear's input
    dim is 64 or 128 and the expert tensors' too, so the whole q4 recipe applies (nothing is skipped for divisibility)."""
    from transformers import Qwen3_5MoeTextConfig
    return Qwen3_5MoeTextConfig(
        vocab_size=vocab, hidden_size=128, num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2, head_dim=32,
        linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=32, linear_value_head_dim=32, linear_conv_kernel_dim=4,
        moe_intermediate_size=64, shared_expert_intermediate_size=64, num_experts=8, num_experts_per_tok=2, max_position_embeddings=4096,
        eos_token_id=eos, pad_token_id=pad, tie_word_embeddings=False, layer_types=["linear_attention"] * 3 + ["full_attention"])


def build_tiny(args, rec):
    """Tiny random Qwen3_5MoeForCausalLM with the real Qwen3.6 tokenizer and chat template (the tokenizer files only: no weights are downloaded)."""
    import torch
    from transformers import AutoTokenizer, Qwen3_5MoeForCausalLM
    tok = AutoTokenizer.from_pretrained(args.model, **({"revision": args.revision} if args.revision else {}))
    cfg = tiny_config(len(tok), tok.eos_token_id, tok.pad_token_id if tok.pad_token_id is not None else 0)
    torch.manual_seed(args.seed)
    return Qwen3_5MoeForCausalLM(cfg), tok


def download(args, rec):
    """snapshot_download of weights + code + tokenizer into the HF cache, timed, with a disk check first and a size log every minute."""
    from huggingface_hub import snapshot_download, constants
    cache = Path(constants.HF_HUB_CACHE)
    cache.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(cache).free
    d = {"cache_dir": str(cache), "free_gib_before": gib(free)}
    rec.res["download"] = d
    if free < args.min_free_gb * 2 ** 30:
        d["error"] = f"only {gib(free)} GiB free in {cache}; need {args.min_free_gb} GiB (weights ~72 GiB plus the hf_xet chunk cache, pip and logs): rent more disk (vast.py create --disk 130)"
        raise RuntimeError(d["error"])
    blobs = cache / ("models--" + args.model.replace("/", "--")) / "blobs"
    mon = Sampler(rec, "download", every=60.0, watch=blobs)
    mon.start()
    t0 = time.time()
    try:
        path = snapshot_download(args.model, revision=args.revision, max_workers=16,
                                 allow_patterns=["*.json", "*.safetensors", "*.py", "*.jinja", "*.txt", "*.model", "tokenizer*"])
    finally:
        mon.stop()
    dt = time.time() - t0
    size = sum(e.stat().st_size for e in os.scandir(blobs) if e.is_file()) if blobs.exists() else None
    d.update(seconds=round(dt, 1), snapshot=str(path), gib=gib(size), mb_per_s=round(size / 1e6 / dt, 1) if size and dt > 0 else None)
    rec.log(f"[download] {d['gib']} GiB in {dt:.0f}s ({d['mb_per_s']} MB/s)")


def audit_loaded(lm):
    """What is actually in memory after load: parameter bytes by dtype, devices, meta tensors, the implementations in effect."""
    by = collections.Counter()
    for _, p in lm.named_parameters():
        by[str(p.dtype)] += p.numel() * p.element_size()
    for _, b in lm.named_buffers():
        by["buffers:" + str(b.dtype)] += b.numel() * b.element_size()
    return {"class": type(lm).__name__, "param_gib_by_dtype": {k: gib(v) for k, v in by.items()}, "devices": sorted({str(p.device) for p in lm.parameters()}),
            "meta_tensors": sum(p.is_meta for p in lm.parameters()), "experts_implementation": getattr(lm.config, "_experts_implementation", None),
            "attn_implementation": getattr(lm.config, "_attn_implementation", None)}


def load_model(args, rec, device):
    """Returns (lm, tok). Real: train.load_model (the loader the night uses; a Qwen3.5-MoE repo goes straight onto the GPU, bf16). Tiny: random fp32 model, real tokenizer."""
    import torch
    ld = rec.res["load"] = {}
    if args.tiny:
        t0 = time.time()
        lm, tok = build_tiny(args, rec)
        lm = lm.to(torch.float32).to(device).eval()
        ld.update(mode="tiny_fp32", load_seconds=round(time.time() - t0, 2))
    else:
        import train
        ns = argparse.Namespace(model=args.model, revision=args.revision, smoke=False, seed=args.seed)
        torch.cuda.reset_peak_memory_stats()
        mon = Sampler(rec, "load", every=30.0)
        mon.start()
        t0 = time.time()
        try:
            lm, tok = train.load_model(ns, device, torch.bfloat16)
        finally:
            ld.update(mon.stop())
        torch.cuda.synchronize()
        ld.update(mode="train.load_model_bf16_cuda", load_seconds=round(time.time() - t0, 1))
    for p in lm.parameters():
        p.requires_grad_(False)
    ld["config_model_type"] = lm.config.model_type
    ld["n_params_b"] = round(sum(p.numel() for p in lm.parameters()) / 1e9, 4)
    if device.type == "cuda":
        ld["max_memory_allocated_gib_after_load"] = gib(torch.cuda.max_memory_allocated())
        ld["memory_allocated_gib_after_load"] = gib(torch.cuda.memory_allocated())
        ld["max_memory_reserved_gib_after_load"] = gib(torch.cuda.max_memory_reserved())
    rec.res["audit"] = audit_loaded(lm)
    rec.log(f"[audit] {rec.res['audit']}")
    rec.log(f"[load] {ld}")
    return lm, tok


# ------------------------------------------------------------------ q4
SANITY_PROMPT = "What is the capital of France? Answer in one word."


def sanity_probe(lm, L, device, gen_tokens):
    """Last-position logits (fp32, CPU) of a fixed chat prompt, and a short greedy continuation."""
    import torch
    from sleep1 import SYS
    ids = torch.tensor([L.ids(L.render(SYS, SANITY_PROMPT))], device=device)
    with torch.no_grad():
        logits = lm(input_ids=ids, use_cache=False, logits_to_keep=1).logits[0, -1].float().cpu()
        text = None
        if gen_tokens:
            out = lm.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=gen_tokens, do_sample=False, pad_token_id=L.eos, eos_token_id=L.eos)
            text = L.decode(out[0, ids.shape[1]:].tolist())
    return logits, text


def run_q4(args, rec, lm, L, sleepb, device, cuda):
    """The MLX-affine fake quantization of the whole base (sleepb --q4-base --q4-mlx-moe), timed, with peak memory and a before/after check on one prompt."""
    import torch
    before, text0 = sanity_probe(lm, L, device, 0 if args.tiny else 12)
    if cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        base = torch.cuda.memory_allocated()
    t0 = time.time()
    st = sleepb.q4_apply(lm, 64, 4, sleepb.Q4_MLX_MOE_BITS, sleepb.Q4_MLX_MOE_PARAMS)
    if cuda:
        torch.cuda.synchronize()
    dt = time.time() - t0
    out = rec.res["q4"] = {"recipe": "mlx-community/Qwen3.6-35B-A3B-4bit: 4-bit group 64 on every Linear / Embedding and the fused 3-D experts; 8-bit group 64 on mlp.gate and mlp.shared_expert_gate",
                           "seconds": round(dt, 1), **st,
                           "note": "fake quantization: the weights stay bf16 in GPU memory (no memory saved); only their values sit on the 4-bit / 8-bit grid"}
    if cuda:
        out.update(peak_alloc_gib=gib(torch.cuda.max_memory_allocated()), extra_peak_over_start_gib=gib(torch.cuda.max_memory_allocated() - base))
    plan = (rec.res.get("plan") or {}).get("q4")
    if plan:
        out["matches_plan"] = plan["by_bits"] == st["by_bits"]
        if not out["matches_plan"]:
            rec.log(f"!! q4 touched {st['by_bits']}, the meta-device plan said {plan['by_bits']}")
    after, text1 = sanity_probe(lm, L, device, 0 if args.tiny else 12)
    import torch.nn.functional as F
    p, q = F.log_softmax(before, -1), F.log_softmax(after, -1)
    out["sanity"] = {"prompt": SANITY_PROMPT, "kl_before_to_after": float((p.exp() * (p - q)).sum()), "top1_same": bool(before.argmax() == after.argmax()),
                     "top5_overlap": len(set(before.topk(5).indices.tolist()) & set(after.topk(5).indices.tolist())), "finite": bool(torch.isfinite(after).all()),
                     "greedy_before": text0, "greedy_after": text1}
    free_gpu()
    rec.log(f"[q4] {dt:.1f}s; tensors {st['tensors']} (by bits {st['by_bits']}), skipped {st['skipped']}, mean rel Frobenius error {st['mean_rel_fro']}; hits {st['pattern_hits']}")
    rec.log(f"[q4] sanity: {out['sanity']}")


# ------------------------------------------------------------------ LoRA
def expected_lora_count(cfg, shared):
    """Qwen3.5-MoE layout: full-attention layers carry q/k/v/o (4), Gated DeltaNet layers in_proj_qkv / z / a / b + out_proj (5); LORA_TARGETS' mlp.(gate|up|down)_proj matches no MoE layer;
    the shared expert (3 per layer) only with --lora-shared."""
    kinds = collections.Counter(getattr(cfg, "layer_types", None) or [])
    return 4 * kinds["full_attention"] + 5 * kinds["linear_attention"] + (3 * cfg.num_hidden_layers if shared else 0)


def attach_lora(lm, args, rec):
    from peft import LoraConfig, get_peft_model
    from peft.tuners.lora import LoraLayer
    targets = lora_targets(args.lora_shared)
    pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=targets, bias="none"))
    names = [n.removeprefix("base_model.model.") for n, m in pm.named_modules() if isinstance(m, LoraLayer)]
    by = collections.Counter(generic(n) for n in names)
    trainable = sum(p.numel() for p in pm.parameters() if p.requires_grad)
    exp = expected_lora_count(lm.config, args.lora_shared)
    d = rec.res["lora"] = {"rank": args.rank, "alpha": args.alpha, "lora_shared": args.lora_shared, "target_regex": targets, "matched": len(names),
                           "matched_by_pattern": dict(by), "expected_matched": exp, "matches_expected": exp == len(names),
                           "trainable_params": trainable, "first_names": names[:8], "routed_experts_have_lora": any(".mlp.experts." in n for n in names)}
    rec.log(f"[lora] target regex: {targets}")
    rec.log(f"[lora] matched {len(names)} modules (expected {exp}); by pattern: {dict(by)}")
    rec.log(f"[lora] trainable params {trainable:,}")
    return pm


# ------------------------------------------------------------------ synthetic data
def synth_prompt(L, target, rng):
    """A chat-framed prompt (sleep1.SYS system line, Qwen no-think render) of `target` tokens (+-1): random common words, cut at the shortest prefix that reaches the target."""
    from sleep1 import SYS
    ws = [rng.choice(WORDS) for _ in range(int(target * 1.2) + 20)]
    lo, hi = 0, len(ws)
    while lo < hi:
        mid = (lo + hi) // 2
        if len(L.ids(L.render(SYS, " ".join(ws[:mid]) or "x"))) < target:
            lo = mid + 1
        else:
            hi = mid
    return L.render(SYS, " ".join(ws[:lo]))


def micro_batch(L, n_seq, length, k_ans, rng):
    """n_seq training examples (ids, loss_start) of `length` tokens: chat-framed prompt, then k_ans answer tokens and the end-of-turn token; loss on the answer part."""
    out = []
    for _ in range(n_seq):
        pid = L.ids(synth_prompt(L, length - k_ans - 1, rng))
        ans = L.ids(" " + " ".join(rng.choice(WORDS) for _ in range(2 * k_ans)))[:k_ans]
        out.append((pid + ans + [L.eos], len(pid)))
    return out


def trainer_batch(L, bsz, replay_bsz, rng):
    """sleepb --bench-train's synthetic batch: half open-book-like (384 tokens, loss on the last 6), a quarter closed-book Q&A (60, 6), a quarter plain text (80, all),
    plus 2 x replay_bsz replay examples (120 tokens, loss on the last 40). Plain words, no chat framing (as bench_train)."""
    toks = lambda n: L.ids(" ".join(rng.choice(WORDS) for _ in range(n * 2)))[:n]  # noqa: E731
    mk = lambda n, k: (toks(n) + [L.eos], n + 1 - k)  # noqa: E731
    batch = [mk(384, 6) for _ in range(bsz // 2)] + [mk(60, 6) for _ in range(bsz // 4)] + [mk(80, 80) for _ in range(bsz - bsz // 2 - bsz // 4)]
    rng.shuffle(batch)
    return batch, [mk(120, 40) for _ in range(max(2 * replay_bsz, 1))]


# ------------------------------------------------------------------ the experts implementation (fused 3-D routed experts)
def set_experts(lm, name, rec=None):
    """Select transformers' experts implementation (grouped_mm / eager / batched_mm ...) for the fused 3-D expert tensors; returns the one in effect."""
    if name and hasattr(lm, "set_experts_implementation"):
        lm.set_experts_implementation(name)
    return getattr(lm.config, "_experts_implementation", None)


def timeit(fn, sync, reps, warm=1, cap_s=90.0):
    """Median seconds of fn() over `reps` timed calls after `warm` untimed ones; stops early once the timed calls add up to cap_s."""
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(reps):
        sync()
        t = time.time()
        fn()
        sync()
        ts.append(time.time() - t)
        if sum(ts) > cap_s:
            break
    return statistics.median(ts), len(ts)


def run_experts(args, rec, lm, pm, L, sleepb, cuda, rng):
    """Time each candidate experts implementation on three shapes and check that they agree: decode (64 x 1 tokens, no grad), prefill (4 x 512, no grad) and training (forward + backward over
    4 x 256 tokens through the LoRA model, with sleepb.tgt_logits). The fastest valid one is chosen for training and, by the cost of one 160-token tagger batch at 64 prompts, for generation."""
    import torch
    import torch.nn.functional as F
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    dev = next(lm.parameters()).device
    names = [x for x in args.experts_impls.split(",") if x]
    default = getattr(lm.config, "_experts_implementation", None)
    out = rec.res["experts"] = {"default_in_effect": default, "candidates": names, "rows": {}, "forced": args.experts_impl or None,
                                "shapes": {"decode": "64 x 1 tokens, no grad, no cache", "prefill": "4 x 512 tokens, no grad", "train": "4 x 256 tokens, forward + backward (LoRA on, tgt_logits + CE)"}}
    rec.save()
    if args.experts_impl:
        names = [args.experts_impl]
    g = torch.Generator().manual_seed(1)
    vocab = lm.config.vocab_size
    ids_dec = torch.randint(10, vocab - 10, (64, 1), generator=g).to(dev)
    ids_pf = torch.randint(10, vocab - 10, (4, 512), generator=g).to(dev)
    ids_ref = torch.randint(10, vocab - 10, (2, 96), generator=g).to(dev)
    tb = micro_batch(L, 4, 256, 8, rng)
    ids, mask, tm = sleepb.lm_masks(L, tb)
    ref_logits = ref_name = None
    reps = 1 if args.tiny else 4
    for name in names:
        row = out["rows"][name] = {}
        try:
            row["in_effect"] = set_experts(lm, name)
        except Exception as e:  # noqa: BLE001
            row.update(status="unavailable", error=repr(e)[:300])
            rec.log(f"[experts:{name}] unavailable: {e!r}")
            continue
        pm.eval()
        with pm.disable_adapter(), torch.no_grad():
            try:  # numeric agreement on a fixed input (adapter off = the base model)
                logits = lm(input_ids=ids_ref, use_cache=False, logits_to_keep=1).logits.float().cpu()
                if ref_logits is None:
                    ref_logits, ref_name = logits, name
                row["vs_" + ref_name] = {"max_abs_diff": float((logits - ref_logits).abs().max()), "ref_logit_scale": float(ref_logits.abs().mean()),
                                         "top1_same": bool((logits.argmax(-1) == ref_logits.argmax(-1)).all()), "finite": bool(torch.isfinite(logits).all())}
            except Exception as e:  # noqa: BLE001
                row["numeric_error"] = repr(e)[:300]
                free_gpu()
            try:
                row["decode_s"], row["decode_n"] = timeit(lambda: lm.model(input_ids=ids_dec, use_cache=False), sync, 2 if args.tiny else reps + 2)
            except Exception as e:  # noqa: BLE001
                row["decode_error"], row["decode_oom"] = repr(e)[:300], is_oom(e)
                free_gpu()
            if name != "batched_mm":  # batched_mm gathers one [2I, H] matrix per token-expert pair: 16384 pairs = 68 GB for 2048 tokens
                try:
                    row["prefill_s"], row["prefill_n"] = timeit(lambda: lm.model(input_ids=ids_pf, use_cache=False), sync, reps)
                except Exception as e:  # noqa: BLE001
                    row["prefill_error"], row["prefill_oom"] = repr(e)[:300], is_oom(e)
                    free_gpu()
        if name != "batched_mm":
            pm.train()
            set_ckpt(lm, False)

            def tr():
                loss = F.cross_entropy(sleepb.tgt_logits(pm, ids, mask, tm), ids[:, 1:][tm], reduction="mean")
                loss.backward()
                pm.zero_grad(set_to_none=True)
            try:
                if cuda:
                    torch.cuda.reset_peak_memory_stats()
                row["train_s"], row["train_n"] = timeit(tr, sync, reps)
                row.update({"train_" + k: v for k, v in peak(cuda).items()})
            except Exception as e:  # noqa: BLE001
                row["train_error"], row["train_oom"] = repr(e)[:300], is_oom(e)
            pm.eval()
            free_gpu(pm)
        rec.log(f"[experts:{name}] {row}")
        rec.save()
    ok = {}
    for n, r in out["rows"].items():
        cmp = next((v for k, v in r.items() if k.startswith("vs_")), None)
        r["numerically_ok"] = bool(cmp is None or (cmp["finite"] and cmp["max_abs_diff"] <= 0.1 * max(cmp["ref_logit_scale"], 1.0) + 0.5))  # bf16 summation-order noise only
        if r["numerically_ok"]:
            ok[n] = r
    tr_ok = {n: r["train_s"] for n, r in ok.items() if isinstance(r.get("train_s"), float)}
    # one 160-token tagger batch of 64 prompts of ~220 tokens: 64 x 220 / 2048 prefill units + 160 decode steps
    gen_ok = {n: 6.9 * r["prefill_s"] + 160 * r["decode_s"] for n, r in ok.items() if isinstance(r.get("prefill_s"), float) and isinstance(r.get("decode_s"), float)}
    out["train_impl"] = args.experts_impl or (min(tr_ok, key=tr_ok.get) if tr_ok else default)
    out["gen_impl"] = args.experts_impl or (min(gen_ok, key=gen_ok.get) if gen_ok else default)
    out["gen_cost_model_s"] = {n: round(v, 2) for n, v in gen_ok.items()}
    out["note"] = ("train_impl / gen_impl are applied by this bench before the training and generation stages. If they differ from each other or from the default, sleepb.py must switch with "
                   "lm.set_experts_implementation(name) around its generate() and training calls (it does not today): the night then runs the default implementation everywhere.")
    set_experts(lm, out["train_impl"])
    rec.log(f"[experts] train_impl {out['train_impl']}, gen_impl {out['gen_impl']} (default {default}); train {tr_ok}, gen cost {out['gen_cost_model_s']}")


# ------------------------------------------------------------------ training benches
def set_ckpt(lm, on):
    if on:
        lm.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    else:
        lm.gradient_checkpointing_disable()


def micro_attempt(args, rec, lm, pm, L, sleepb, cfg, batch, params, cuda):
    """One config of the micro-batch bench: 2 warm-up + `timed` steps of (forward over micro-batches -> CE on target positions -> backward -> clip -> AdamW step, lr 0).
    A 2048-token step is `micro_tokens`-sized pieces with gradient accumulation (the loss is a sum over the full step's targets). Raises on OOM."""
    import torch
    import torch.nn.functional as F
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    set_ckpt(lm, cfg["ckpt"])
    per = max(1, cfg["micro_tokens"] // max(len(batch[0][0]), 1))
    chunks = [batch[i:i + per] for i in range(0, len(batch), per)]
    ntgt = sum(len(e) - max(st, 1) for e, st in batch)
    opt = torch.optim.AdamW(params, lr=0.0, weight_decay=0.0)
    lora_b = [p for n, p in pm.named_parameters() if p.requires_grad and "lora_B" in n]
    info = {"micro_batches": len(chunks), "seqs_per_micro_batch": per, "tokens_per_step": sum(len(e) for e, _ in batch), "grad_missing": None}

    def one(check):
        tot = 0.0
        for ch in chunks:
            ids, mask, tm = sleepb.lm_masks(L, ch)
            loss = F.cross_entropy(sleepb.tgt_logits(pm, ids, mask, tm), ids[:, 1:][tm], reduction="sum") / ntgt
            loss.backward()
            tot += float(loss.detach())
        if check:
            info["grad_missing"] = sum(p.grad is None for p in lora_b)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        return tot

    pm.train()
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    times, losses = [], []
    try:
        for i in range(args.warmup + args.timed):
            if i >= args.warmup + 1 and rec.time_left() < 0:  # budget gone: keep what was timed (>= 1 step)
                info["stopped_early"] = "time budget"
                break
            sync()
            t = time.time()
            losses.append(one(i == 0))
            sync()
            if i == 0 and info["grad_missing"]:
                raise RuntimeError(f"no gradient reached {info['grad_missing']} of {len(lora_b)} LoRA B matrices (gradient checkpointing={cfg['ckpt']})")
            if i >= args.warmup:
                times.append(time.time() - t)
            rec.log(f"[train_micro:{cfg['name']}] step {i + 1} {time.time() - t:.2f}s loss {losses[-1]:.4f}")
    finally:
        pm.eval()
        del opt
    if not times:
        raise RuntimeError("no timed step finished")
    return {**info, "s_per_step": round(sum(times) / len(times), 4), "step_seconds": [round(x, 4) for x in times], "n_timed": len(times), "loss_first": losses[0],
            "loss_last": losses[-1], "finite": all(math.isfinite(x) for x in losses), **peak(cuda)}


def run_train_micro(args, rec, lm, pm, L, sleepb, cuda, rng):
    params = [p for p in pm.parameters() if p.requires_grad]
    batch = micro_batch(L, args.micro_seqs, args.micro_len, 8, rng)
    ex = (rec.res.get("experts") or {}).get("train_impl")
    if ex:
        set_experts(lm, ex)
    ladder = [{"name": "plain", "ckpt": False, "micro_tokens": args.micro_seqs * args.micro_len},
              {"name": "ckpt", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len},
              {"name": "ckpt_half", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len // 2},
              {"name": "ckpt_quarter", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len // 4}]
    out = rec.res["train_micro"] = {"shape": f"{args.micro_seqs} x {args.micro_len} tokens, chat framing, loss on the last 9 tokens of each", "warmup": args.warmup, "timed": args.timed,
                                    "optimizer": "AdamW lr 0 (weights never move)", "experts_implementation": getattr(lm.config, "_experts_implementation", None),
                                    "attempts": [], "chosen": None, "gradient_checkpointing_kwargs": {"use_reentrant": False}, "enable_input_require_grads": False}
    rec.save()
    for cfg in ladder:
        if rec.time_left() < 60:
            out["attempts"].append({**cfg, "status": "skipped: time budget"})
            continue
        row = {**cfg}
        try:
            row.update(status="ok", **micro_attempt(args, rec, lm, pm, L, sleepb, cfg, batch, params, cuda))
        except Exception as e:  # noqa: BLE001
            oom = is_oom(e)
            msg = repr(e)[:300]
            row.update(status="oom" if oom else "error", error=msg, **peak(cuda))
            rec.log(f"[train_micro:{cfg['name']}] {'OUT OF MEMORY' if oom else 'FAILED'}: {msg}")
            if not oom and "no gradient reached" in msg and not out["enable_input_require_grads"]:  # one fix: make the embedding output require grad, then retry this config
                lm.enable_input_require_grads()
                out["enable_input_require_grads"] = True
                try:
                    row.update(status="ok", error=None, retry="after enable_input_require_grads", **micro_attempt(args, rec, lm, pm, L, sleepb, cfg, batch, params, cuda))
                except Exception as e2:  # noqa: BLE001
                    row.update(status="oom" if is_oom(e2) else "error", error=repr(e2)[:300])
        free_gpu(pm)
        out["attempts"].append(row)
        rec.save()
        if row["status"] == "ok":
            if out["chosen"] is None:
                out["chosen"] = row["name"]
                out.update(s_per_step=row["s_per_step"], peak_alloc_gib=row.get("peak_alloc_gib"), ckpt=row["ckpt"], micro_tokens=row["micro_tokens"])
            if not args.try_all_configs:
                break
    rec.log(f"[train_micro] chosen {out['chosen']}: {out.get('s_per_step')} s/step, peak {out.get('peak_alloc_gib')} GiB")


def trainer_attempt(args, rec, lm, pm, L, sleepb, budget, ckpt, batch, replay, cuda):
    """sleepb.Trainer.step on the bench-train batch at TOK_BUDGET = budget: 1 warm-up + 3 timed steps (lr 0). Raises on OOM."""
    import torch
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    set_ckpt(lm, ckpt)
    old = sleepb.TOK_BUDGET
    sleepb.TOK_BUDGET = budget
    ta = argparse.Namespace(lr=0.0, kl_weight=1.0, replay_bsz=args.replay_bsz)
    mb = sleepb.groups(sorted(batch, key=lambda x: -len(x[0])))
    rg = sleepb.groups(sorted(replay[:args.replay_bsz], key=lambda x: -len(x[0])))
    row = {"gradient_checkpointing": ckpt, "micro_batches": [len(mb), len(rg)],
           "padded_tokens": [sum(len(g) * max(len(x[0]) for x in g) for g in mb), sum(len(g) * max(len(x[0]) for x in g) for g in rg)]}
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    times, tr = [], None
    try:
        free_gpu(pm)
        pm.train()
        tr = sleepb.Trainer(L, pm, ta, replay, args.trainer_warmup + args.trainer_timed, 0)
        for i in range(args.trainer_warmup + args.trainer_timed):
            if i >= args.trainer_warmup + 1 and rec.time_left() < 0:
                row["stopped_early"] = "time budget"
                break
            sync()
            t = time.time()
            tr.step(batch)
            sync()
            dt = time.time() - t
            rec.log(f"[train_trainer:{budget}{'+ckpt' if ckpt else ''}] step {i + 1} {dt:.2f}s")
            if i >= args.trainer_warmup:
                times.append(dt)
    finally:
        sleepb.TOK_BUDGET = old
        pm.eval()
        del tr
        row.update(peak(cuda))
        free_gpu(pm)
    if not times:
        raise RuntimeError("no timed Trainer step finished")
    row.update(status="ok", s_per_step=round(sum(times) / len(times), 4), step_seconds=[round(x, 4) for x in times], n_timed=len(times))
    return row


def run_train_trainer(args, rec, lm, pm, L, sleepb, cuda, rng):
    """The real sleepb.Trainer.step at each --tok-budgets value: plain first, gradient checkpointing if that runs out of memory (a larger budget starts from checkpointing
    once a smaller one needed it)."""
    ex = (rec.res.get("experts") or {}).get("train_impl")
    if ex:
        set_experts(lm, ex)
    batch, replay = trainer_batch(L, args.bsz, args.replay_bsz, rng)
    out = rec.res["train_trainer"] = {"what": "sleepb.Trainer.step (CE on the batch + KL guard on replay vs the adapter-off base), lr 0", "bsz": args.bsz, "replay_bsz": args.replay_bsz,
                                      "warmup": args.trainer_warmup, "timed_requested": args.trainer_timed, "experts_implementation": getattr(lm.config, "_experts_implementation", None),
                                      "budgets": {}}
    rec.save()
    need_ckpt = False
    for budget in args.tok_budgets:
        row = out["budgets"][str(budget)] = {"attempts": []}
        for ckpt in ([True] if need_ckpt else [False, True]):
            if rec.time_left() < 60:
                row["attempts"].append({"gradient_checkpointing": ckpt, "status": "skipped: time budget"})
                continue
            try:
                a = trainer_attempt(args, rec, lm, pm, L, sleepb, budget, ckpt, batch, replay, cuda)
                row["attempts"].append(a)
                row.update({k: v for k, v in a.items()})
                need_ckpt = need_ckpt or ckpt
                break
            except Exception as e:  # noqa: BLE001
                oom = is_oom(e)
                row["attempts"].append({"gradient_checkpointing": ckpt, "status": "oom" if oom else "error", "error": repr(e)[:300], **peak(cuda)})
                rec.log(f"[train_trainer:{budget}{'+ckpt' if ckpt else ''}] {'OUT OF MEMORY' if oom else 'FAILED'}: {e!r}"[:600])
                free_gpu(pm)
                if not oom:
                    break
        if "status" not in row:
            row["status"] = row["attempts"][-1]["status"] if row["attempts"] else "skipped"
        rec.save()
        rec.log(f"[train_trainer] tok budget {budget}: {row.get('status')} {row.get('s_per_step')} s/step, checkpointing {row.get('gradient_checkpointing')}, peak {row.get('peak_alloc_gib')} GiB")
    first = next((r for r in out["budgets"].values() if r.get("status") == "ok"), None)
    if first:
        out.update(status="ok", s_per_step=first["s_per_step"], peak_alloc_gib=first.get("peak_alloc_gib"))
    else:
        out["status"] = "failed"
        raise RuntimeError("no Trainer budget worked")


# ------------------------------------------------------------------ generation bench
class GenProbe:
    """Stands in for the model inside Lang.generate: forwards generate() (with min_new_tokens = max_new_tokens so every row decodes the full length) and records
    the decode steps, the new tokens (up to and including the first end-of-turn) and the time of each call."""

    def __init__(self, model, sync, eos, force_full=True):
        self.model, self.sync, self.eos, self.force_full, self.calls = model, sync, eos, force_full, []

    def generate(self, **kw):
        if self.force_full and kw.get("max_new_tokens"):
            kw.setdefault("min_new_tokens", kw["max_new_tokens"])
        self.sync()
        t = time.time()
        out = self.model.generate(**kw)
        self.sync()
        dt = time.time() - t
        n = kw["input_ids"].shape[1]
        gen = out[:, n:].tolist()
        new = sum((row.index(self.eos) + 1) if self.eos in row else len(row) for row in gen)
        self.calls.append({"batch": int(out.shape[0]), "prompt_len": int(n), "steps": len(gen[0]), "new_tokens": new, "model_generate_s": round(dt, 4)})
        return out

    def __getattr__(self, name):
        return getattr(self.model, name)


def gen_plan(args):
    """(key, shape, batch, prompt tokens, new tokens, sampled) rows, smallest batch first. tag: the tagger (greedy, 160 new); dream: NREM dreaming (sampled; the night's 400 x scale = 1600
    new tokens are extrapolated from --dream-steps measured steps); dream_long: a longer dream run at the middle batch to check that the decode step does not grow with length;
    verify: a short greedy check (20 new at ~420 prompt tokens) against which the estimator's prediction is compared."""
    rows = []
    for B in args.gen_bs:
        rows.append((f"tag_{B}", "tag", B, args.tag_prompt, args.tag_new, False))
        rows.append((f"dream_{B}", "dream", B, args.dream_prompt, args.dream_steps, True))
    mid = sorted(args.gen_bs)[len(args.gen_bs) // 2]
    rows.append((f"dream_long_{mid}", "dream_long", mid, args.dream_prompt, 5 * args.dream_steps, True))
    rows.append((f"verify_{min(args.gen_bs)}", "verify", min(args.gen_bs), 420, 20, False))
    return rows


def run_gen(args, rec, lm, pm, L, cuda, rng):
    import torch
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    set_ckpt(lm, False)
    ex = (rec.res.get("experts") or {}).get("gen_impl")
    if ex:
        set_experts(lm, ex)
    pm.eval()
    probe = GenProbe(pm, sync, L.eos, force_full=not args.allow_early_eos)
    out = rec.res["gen"] = {"adapter": "off (the base model, as the tagger / dreamer / verifier run); the LoRA adds ~1 small matmul pair per target module per step",
                            "forced_full_length": not args.allow_early_eos, "sampling": "temperature 0.8, top_p 0.95, top_k 0 (Lang.generate)",
                            "experts_implementation": getattr(lm.config, "_experts_implementation", None), "rows": {}}
    rows = out["rows"]
    with pm.disable_adapter():
        L.generate(probe, [synth_prompt(L, 32, rng)] * 2, max_new=4, bs=2)  # untimed: kernels, allocator
        last_step = 0.0
        oom_at = None
        for key, shape, B, plen, new, sampled in gen_plan(args):
            if oom_at is not None and B >= oom_at:
                rows[key] = {"status": f"skipped: batch {oom_at} already ran out of memory"}
                continue
            need = 1.1 * new * last_step + 15 if last_step else 60.0  # about its decode steps x the seconds per step seen so far
            if rec.time_left() < need:
                rows[key] = {"status": f"skipped: time budget ({rec.time_left():.0f}s left, about {need:.0f}s needed)"}
                continue
            prompts = [synth_prompt(L, plen, rng) for _ in range(B)]
            ptok = [len(L.ids(p)) for p in prompts]
            row = {"shape": shape, "prompts": B, "prompt_tokens_mean": round(sum(ptok) / B, 1), "max_new": new, "sampled": sampled}
            try:
                if shape != "dream_long":  # the prefill alone (one new token): the fixed cost of a batch
                    probe.calls.clear()
                    if cuda:
                        torch.cuda.reset_peak_memory_stats()
                    L.generate(probe, prompts, max_new=1, bs=B, sample=sampled)
                    row["prefill_s"] = probe.calls[0]["model_generate_s"]
                    row["prefill_peak_alloc_gib"] = peak(cuda).get("peak_alloc_gib")
                probe.calls.clear()
                if cuda:
                    torch.cuda.reset_peak_memory_stats()
                sync()
                t = time.time()
                outs = L.generate(probe, prompts, max_new=new, bs=B, sample=sampled)
                sync()
                wall = time.time() - t
                c = probe.calls[0]
                pf = row.get("prefill_s") or 0.0
                row.update(status="ok", seconds=round(wall, 3), model_generate_s=c["model_generate_s"], steps=c["steps"], new_tokens=c["new_tokens"],
                           new_tokens_per_s=round(c["new_tokens"] / wall, 2), seconds_per_step=round(wall / max(c["steps"], 1), 4),
                           decode_s_per_step=round(max(wall - pf, 1e-6) / max(c["steps"] - 1, 1), 5), sample_out=outs[0][:160], **peak(cuda))
            except Exception as e:  # noqa: BLE001
                oom = is_oom(e)
                row.update(status="oom" if oom else "error", error=repr(e)[:300])
                if oom:
                    oom_at = B
                free_gpu()
            rows[key] = row
            last_step = max(last_step, row.get("seconds_per_step") or 0)
            rec.log(f"[gen:{key}] {row}")
            rec.save()


# ------------------------------------------------------------------ the night estimate
# Prompt lengths (tokens) assumed per phase when the bench JSON cannot know them (only the prefill share depends on them, the decode loop dominates).
PROMPT_TOK = {"tag": 220, "names": 220, "detect": 450, "dream": 450, "verify": 420, "probe": 60, "rem": 250, "rem_verify": 420, "arc": 150, "replay": 40, "weights": 60, "diary": 700}
TRAINER_STEP_IN_MICRO = 4.0  # fallback when the Trainer bench is missing: 3 padded micro-batches + 1 replay group (x2 forwards) per Trainer step, in 2048-token micro-step units
LONG_GEN = 40  # generations of at least this many new tokens get the "typical" length fraction (tagging 160, dreaming 400 x scale, REM 40); short ones always run full


def speeds_from_bench(b):
    """Prefill rate, decode seconds per step by batch size (greedy / sampled) and training seconds per step by tok budget, from a bench JSON."""
    rows = (b.get("gen") or {}).get("rows") or {}
    sp, notes = {}, []
    ok = {k: r for k, r in rows.items() if r.get("status") == "ok"}
    pf_t = pf_n = 0.0
    for r in ok.values():
        if r.get("prefill_s"):
            pf_t += r["prefill_s"]
            pf_n += r["prompts"] * r["prompt_tokens_mean"]
    if pf_t > 0:
        sp["prefill_tok_s"] = pf_n / pf_t
    else:
        notes.append("no prefill measurement: prefill taken as free")
    dg, ds = {}, {}
    for r in ok.values():
        if r["shape"] == "tag":
            dg[r["prompts"]] = r["decode_s_per_step"]
        elif r["shape"] == "dream":
            ds[r["prompts"]] = r["decode_s_per_step"]
    if not dg and not ds:
        raise ValueError("bench JSON has no usable generation timing (gen.rows.tag_* / dream_*)")
    if not dg:
        dg = dict(ds)
        notes.append("no greedy (tag) timing: greedy decode step taken equal to the sampled one")
    if not ds:
        ds = dict(dg)
        notes.append("no sampled (dream) timing: sampled decode step taken equal to the greedy one")
    for B in sorted(set(dg) - set(ds)):
        ds[B] = dg[B] * statistics.median(ds[k] / dg[k] for k in ds if k in dg) if any(k in dg for k in ds) else dg[B]
    for B in sorted(set(ds) - set(dg)):
        dg[B] = ds[B] / statistics.median(ds[k] / dg[k] for k in ds if k in dg) if any(k in dg for k in ds) else ds[B]
    sp["dec_greedy"], sp["dec_sampled"] = dict(sorted(dg.items())), dict(sorted(ds.items()))
    tr, mi = b.get("train_trainer") or {}, b.get("train_micro") or {}
    budgets = {int(k): v["s_per_step"] for k, v in (tr.get("budgets") or {}).items() if v.get("status") == "ok"}
    if budgets:
        sp["train_s_per_step"], sp["train_source"] = budgets, "Trainer.step measured"
    elif mi.get("s_per_step"):
        sp["train_s_per_step"], sp["train_source"] = {2048: mi["s_per_step"] * TRAINER_STEP_IN_MICRO}, f"micro step x {TRAINER_STEP_IN_MICRO}"
        notes.append(f"no Trainer.step timing: a Trainer step taken as {TRAINER_STEP_IN_MICRO} micro-steps of 2048 tokens")
    else:
        raise ValueError("bench JSON has no usable training timing (train_trainer / train_micro)")
    sp["notes"] = notes
    sp["load_seconds"] = (b.get("load") or {}).get("load_seconds")
    sp["q4_seconds"] = (b.get("q4") or {}).get("seconds")
    return sp


def interp(table, n):
    """table {batch: seconds per decode step}: log2-linear between measured batch sizes, flat below the smallest (a small batch is not cheaper than the smallest measured), and
    extrapolated from the last two points above the largest."""
    ks = sorted(table)
    if n <= ks[0] or len(ks) == 1:
        return table[ks[0]]
    for lo, hi in zip(ks, ks[1:]):
        if n <= hi:
            return table[lo] + (table[hi] - table[lo]) * math.log2(n / lo) / math.log2(hi / lo)
    lo, hi = ks[-2], ks[-1]
    return max(table[hi], table[hi] + (table[hi] - table[lo]) * math.log2(n / hi) / math.log2(hi / lo))


def dec_step(sp, n, sampled):
    return interp(sp["dec_sampled" if sampled else "dec_greedy"], n)


def gen_time(sp, n, max_new, plen, sampled, bs, frac):
    """Seconds for n prompts in batches of bs: per batch, prefill + steps x decode step (steps = max_new, or frac x max_new for long generations)."""
    if n <= 0 or max_new <= 0:
        return 0.0
    t = 0.0
    for b in [bs] * (n // bs) + ([n % bs] if n % bs else []):
        steps = max(1, round(max_new * frac)) if max_new >= LONG_GEN else max_new
        t += (b * plen / sp["prefill_tok_s"] if sp.get("prefill_tok_s") else 0.0) + steps * dec_step(sp, b, sampled)
    return t


def forward_time(sp, n, plen, bs):
    """score_arc: forward passes only, batches of bs."""
    return math.ceil(n / bs) * (bs * plen / sp["prefill_tok_s"]) if n > 0 and sp.get("prefill_tok_s") else 0.0


def train_step_s(sp, budget):
    t = sp["train_s_per_step"]
    return t[budget] if budget in t else t[min(t, key=lambda k: abs(k - budget))]


def night_seconds(sp, n, bs, budget, frac):
    """Seconds per phase for one night of an addendum-9-style result (nights[i]); counts are the ones the run stored, the rest assumed (see the notes)."""
    P = PROMPT_TOK
    tg, nm, ud, ds = n["tagging"], n.get("names_pass") or {}, n.get("update_detection") or {}, n["dream_stats"]
    scale = (n.get("budget") or {}).get("scale") or 1.0
    now_prompts = math.ceil(ds.get("now_gen", 0) / 2)  # not stored: 'now' prompts yield up to 2 questions each
    dream_n = ds.get("items", 0) + now_prompts
    dream_new = round(400 * scale)  # Brain.set_scale: dream_new = sc(400)
    verify_n = max(0, ds.get("qa_gen", 0) + ds.get("now_gen", 0) - ds.get("dropped_bad_answer", 0))  # upper bound (test-leak drops not subtracted)
    probes = n.get("with_dreams", n.get("eligible", 0))  # items that have a probe: not stored, taken as the items with dreams
    G = lambda cnt, new, key, samp=False: gen_time(sp, cnt, new, P[key], samp, bs, frac)  # noqa: E731
    ph = collections.OrderedDict()
    ph["tag_names_detect"] = G(tg.get("turns", 0), 160, "tag") + G(nm.get("pairs", 0), 12, "names") + G(ud.get("candidates", 0), 8, "detect")
    ph["dream_generate"] = G(dream_n, dream_new, "dream", True)
    ph["dream_verify"] = G(verify_n, 20, "verify")
    ph["probes_and_arc"] = 2 * G(probes, 20, "probe") + forward_time(sp, 100, P["arc"], max(bs // 2, 1))  # probe before and after training; ARC-Easy validation(100) in the gate
    ph["train"] = n.get("steps", 0) * train_step_s(sp, budget)
    rem_g = rem_v = 0.0
    for rs in n.get("rem_stats") or []:
        rem_g += G(rs.get("chain_gen", 0) + rs.get("gist_gen", 0), 40, "rem", True)
        rem_v += G(rs.get("chain_kept", 0) + rs.get("gist_kept", 0) + rs.get("dropped_unverified", 0) + rs.get("dropped_dup", 0) + rs.get("chain_extra_dropped", 0), 20, "rem_verify")
    ph["rem_generate"], ph["rem_verify"] = rem_g, rem_v
    return ph


def once_seconds(sp, a9, bs, frac):
    """Per-run costs outside the nights: generic replay generation, ARC base scores, the learning-curve probes, the final scoring in three modes, the model load and q4."""
    P = PROMPT_TOK
    sc = (a9.get("scores") or {}).get("weights") or {}
    kinds = [sc.get(k, {}).get("n", 0) for k in ("forward", "reverse", "twohop", "changed", "routine")]
    n_test, n_fwd = sum(kinds), kinds[0]
    G = lambda cnt, new, key, samp=False: gen_time(sp, cnt, new, P[key], samp, bs, frac)  # noqa: E731
    o = collections.OrderedDict()
    o["replay_generation"] = G(a9.get("replay_n", 200), 48, "replay")
    o["arc_base_val100_and_arc500_twice"] = forward_time(sp, 100, P["arc"], max(bs // 2, 1)) + 2 * forward_time(sp, 500, P["arc"], max(bs // 2, 1))  # arc_val_base, --arc-base, final score
    o["learning_curve_probes"] = len(a9.get("curve") or {}) * G(n_fwd, 20, "weights")
    o["final_scoring"] = G(n_test, 20, "weights") + 2 * G(n_test, 20, "diary")  # weights, diary, base_diary
    o["model_load_and_q4"] = (sp.get("load_seconds") or 0.0) + (sp.get("q4_seconds") or 0.0)
    return o


def estimate(b, a9, usd_h, gen_bs_list=GEN_BS, budgets=TOK_BUDGETS, fracs=(1.0, 0.6)):
    """One Week-2 4x-work arm at the measured speeds. Headline: the settings of the addendum-9 run (gen_bs and tok budget from its args) if measured, else the first measured; plus a grid over
    generation batch size and tok budget for both length scenarios, and the best cell. The per-night table is printed for the headline and the best cell."""
    sp = speeds_from_bench(b)
    a_args = a9.get("args") or {}
    have = sorted(sp["train_s_per_step"])
    bs0, tb0 = int(a_args.get("gen_bs", 32)), int(a_args.get("tok_budget", 2048))
    tb0 = tb0 if tb0 in have else have[0]
    grid_bs = sorted(set(gen_bs_list) | {bs0})
    grid_tb = sorted(set(have) & set(budgets)) or have
    out = {"inputs": {k: ({str(kk): round(vv, 5) for kk, vv in v.items()} if isinstance(v, dict) else round(v, 5) if isinstance(v, float) else v) for k, v in sp.items()},
           "usd_per_hour": usd_h, "a9_arm": a9.get("arm"), "a9_model": a9.get("model"), "a9_gen_bs": bs0, "a9_tok_budget": tb0, "a9_wall_seconds_on_that_model": a9.get("wall_seconds"),
           "a9_steps_total": sum(n.get("steps", 0) for n in a9["nights"]), "grid": [], "scenarios": {}}

    def total(bs, tb, f):
        nights = [night_seconds(sp, n, bs, tb, f) for n in a9["nights"]]
        once = once_seconds(sp, a9, bs, f)
        return nights, once, sum(sum(p.values()) for p in nights) + sum(once.values())

    for bs in grid_bs:
        for tb in grid_tb:
            row = {"gen_bs": bs, "tok_budget": tb}
            for f in fracs:
                row["full_max_new_h" if f == 1.0 else f"typical_{f}_h"] = round(total(bs, tb, f)[2] / 3600, 2)
            out["grid"].append(row)
    typ = f"typical_{fracs[-1]}_h"
    best = min(out["grid"], key=lambda r: r[typ])
    out["best_cell"] = best
    for label, bs, tb in (("as_a9_run", bs0, tb0), ("best_cell", best["gen_bs"], best["tok_budget"])):
        sc = out["scenarios"][label] = {"gen_bs": bs, "tok_budget": tb, "train_s_per_step": round(train_step_s(sp, tb), 3)}
        for f in fracs:
            nights, once, tot = total(bs, tb, f)
            rows = [{"night": n["night"], "steps": n.get("steps"), **{k: round(v, 1) for k, v in ph.items()}, "total_s": round(sum(ph.values()), 1)} for n, ph in zip(a9["nights"], nights)]
            week = sum(r["total_s"] for r in rows)
            by = collections.Counter()
            for ph in nights:
                by.update(ph)
            sc["full_max_new" if f == 1.0 else f"typical_{f}"] = {
                "length_fraction_of_long_generations": f, "per_night": rows, "once_per_run_s": {k: round(v, 1) for k, v in once.items()}, "week_nights_s": round(week, 1),
                "total_s_without_download": round(tot, 1), "total_hours": round(tot / 3600, 2), "total_usd": round(tot / 3600 * usd_h, 2),
                "week_seconds_by_phase": {k: round(v, 1) for k, v in by.most_common()}, "x_the_qwen_run": (round(tot / a9["wall_seconds"], 1) if a9.get("wall_seconds") else None)}
    v = (b.get("gen") or {}).get("rows", {}).get(f"verify_{min(gen_bs_list)}") or next((r for k, r in ((b.get("gen") or {}).get("rows") or {}).items() if k.startswith("verify_")), None)
    if v and v.get("status") == "ok":
        pred = gen_time(sp, v["prompts"], v["max_new"], v["prompt_tokens_mean"], False, v["prompts"], 1.0)
        out["estimator_check"] = {"what": f"{v['prompts']} prompts of ~{v['prompt_tokens_mean']} tokens, {v['max_new']} new greedy (not used to build the model)", "measured_s": v["seconds"],
                                  "predicted_s": round(pred, 3), "ratio_pred_over_measured": round(pred / v["seconds"], 2)}
    out["assumptions"] = [
        "Generation work per night is read from the addendum-9 seed-1 result (nights[i].tagging.turns, names_pass.pairs, update_detection.candidates, dream_stats.items / now_gen / qa_gen / dropped_bad_answer, "
        "with_dreams, rem_stats[c].chain_gen / gist_gen / kept / dropped_unverified / dropped_dup, steps); the same arm on the big base would see somewhat different counts.",
        "Not stored, so assumed: 'now' prompts = ceil(now_gen / 2); dream verification prompts = qa_gen + now_gen - dropped_bad_answer (upper bound); probes = with_dreams; "
        "ARC validation = 100 questions per night; prompt lengths per phase = PROMPT_TOK (only prefill depends on them).",
        "Every generate batch decodes max_new steps (an upper bound: a batch stops when all rows end). 'typical_0.6' cuts the long generations (tagging 160, dreams 400 x scale, REM 40) to 60% "
        "of max_new; this fraction is a guess, not a measurement. Dream decode steps are measured over a few dozen steps and assumed constant out to 400 x scale (dream_long checks the slope).",
        "Decode seconds per step are measured at the batch sizes in inputs (adapter off); a batch smaller than the smallest measured costs as that one, in between log2-interpolated. Training uses the measured seconds per "
        "Trainer step at the tok budget for every step (the real batches are longer or shorter than the synthetic one: the open-book examples carry the diary notes).",
        "Not counted: the download, CPU-side bookkeeping (BM25 search, parsing), SHY, the adapter snapshot / restore, the ARC-Easy download. The experts implementation that was fastest per phase in the bench is "
        "assumed for both phases (see experts.note in the bench JSON)."]
    out["notes"] = sp["notes"]
    return out


def print_estimate(est, label=""):
    print(f"\n=== Sleep-B arm estimate {label}(arm {est['a9_arm']}, counts from the {est['a9_model']} run; ${est['usd_per_hour']}/h) ===")
    i = est["inputs"]
    print(f"measured: prefill {i.get('prefill_tok_s', float('nan')):.0f} tok/s; decode s/step greedy {i['dec_greedy']}, sampled {i['dec_sampled']}; "
          f"train s/step by tok budget {i['train_s_per_step']} ({i['train_source']}); load {i.get('load_seconds')}s, q4 {i.get('q4_seconds')}s")
    if est.get("estimator_check"):
        print("  estimator check:", est["estimator_check"])
    for n in est["notes"]:
        print("  note:", n)
    print("\n  grid, total hours (full max_new / typical 0.6) by generation batch size x tok budget:")
    for r in est["grid"]:
        cols = {k: v for k, v in r.items() if k.endswith("_h")}
        print(f"    gen_bs {r['gen_bs']:>4}  tok_budget {r['tok_budget']:>5}  " + "  ".join(f"{k[:-2]} {v:>6}" for k, v in cols.items()))
    print(f"  best cell (typical): {est['best_cell']}")
    for lab, sc in est["scenarios"].items():
        for name, s in ((k, v) for k, v in sc.items() if isinstance(v, dict)):
            print(f"\n-- {lab}: gen_bs {sc['gen_bs']}, tok budget {sc['tok_budget']} ({sc['train_s_per_step']} s/step), {name} (long generations run {s['length_fraction_of_long_generations']:.0%} of max_new)")
            cols = list(s["per_night"][0].keys())
            print("  " + " ".join(f"{c[:14]:>14}" for c in cols))
            for r in s["per_night"]:
                print("  " + " ".join(f"{r[c]:>14}" for c in cols))
            print(f"  week of nights {s['week_nights_s'] / 3600:.2f} h; once per run {sum(s['once_per_run_s'].values()) / 3600:.2f} h {s['once_per_run_s']}")
            print(f"  TOTAL {s['total_hours']} h  = ${s['total_usd']}  ({s['x_the_qwen_run']}x the Qwen run's wall time)  [download not counted]")
            print(f"  where the week goes: {s['week_seconds_by_phase']}")
    for a in est["assumptions"]:
        print("  *", a)


# ------------------------------------------------------------------ main
def csv_ints(s):
    return [int(x) for x in str(s).split(",") if x]


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=QWEN_REPO, help="a Qwen3.5/3.6 MoE repo (the q4 recipe and the experts handling are written for that family)")
    ap.add_argument("--revision", default=None, help="repo revision (default: the pinned commit for the default model, else the repo's main)")
    ap.add_argument("--out", default="out/moebench/bench.json", help="result JSON (the log is written next to it)")
    ap.add_argument("--tiny", action="store_true", help="CPU: tiny random Qwen3_5MoeForCausalLM (the real tokenizer only), fp32")
    ap.add_argument("--plan-only", action="store_true", help="only the meta-device plan (parameter breakdown, LoRA matches, q4 coverage): no weights, no GPU needed")
    ap.add_argument("--estimate-from", default=None, help="bench JSON -> print the arm estimate (no GPU, no model) and exit")
    ap.add_argument("--a9", default=str(A9_DEFAULT), help="addendum-9 result JSON the estimate takes its per-night counts from")
    ap.add_argument("--usd-per-hour", type=float, default=USD_PER_HOUR)
    ap.add_argument("--lora-shared", action="store_true", help="also put LoRA on the shared-expert MLPs (mlp.shared_expert.{gate,up,down}_proj); train.LORA_TARGETS alone does not match them")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--min-free-gb", type=float, default=85.0, help="refuse to download with less free disk than this")
    ap.add_argument("--skip-download", action="store_true", help="the repo is already in the HF cache")
    ap.add_argument("--force-load", action="store_true", help="load even if the plan says the bf16 weights do not fit the GPU")
    ap.add_argument("--budget-min", type=float, default=50.0, help="minutes for load + every stage after the download; stages that start late are skipped, timed loops stop early")
    ap.add_argument("--no-q4", action="store_true", help="skip the fake quantization (bf16 base)")
    ap.add_argument("--no-train", action="store_true")
    ap.add_argument("--no-gen", action="store_true")
    ap.add_argument("--experts-impls", default="grouped_mm,eager,batched_mm", help="experts implementations to time (first one is the numeric reference)")
    ap.add_argument("--experts-impl", default=None, help="force one experts implementation for every stage (skips the choice)")
    ap.add_argument("--no-experts-probe", action="store_true", help="skip the experts-implementation comparison (the transformers default stays)")
    ap.add_argument("--micro-seqs", type=int, default=8)
    ap.add_argument("--micro-len", type=int, default=256)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--timed", type=int, default=8)
    ap.add_argument("--tok-budgets", type=csv_ints, default=list(TOK_BUDGETS), help="Trainer bench: sleepb TOK_BUDGET values (comma-separated)")
    ap.add_argument("--trainer-warmup", type=int, default=1)
    ap.add_argument("--trainer-timed", type=int, default=3)
    ap.add_argument("--bsz", type=int, default=16, help="Trainer bench: examples per step (sleepb --bsz)")
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--gen-bs", type=csv_ints, default=None, help="generation batch sizes (comma-separated; default 32,64,128, with --tiny 4,8,16)")
    ap.add_argument("--tag-prompt", type=int, default=220)
    ap.add_argument("--tag-new", type=int, default=None, help="tagger shape: new tokens (default 160, with --tiny 24)")
    ap.add_argument("--dream-prompt", type=int, default=450)
    ap.add_argument("--dream-steps", type=int, default=None, help="sampled dream shape: decode steps measured (default 64, with --tiny 12; the night's 400 x scale are extrapolated)")
    ap.add_argument("--allow-early-eos", action="store_true", help="do not force full-length generations")
    ap.add_argument("--try-all-configs", action="store_true", help="run every micro-bench config even after one worked (default on with --tiny)")
    ap.add_argument("--seed", type=int, default=0)
    return ap


def summary_of(res):
    """The headline numbers, in one dict."""
    g, ld, mi, tr = (res.get("gen") or {}).get("rows") or {}, res.get("load") or {}, res.get("train_micro") or {}, res.get("train_trainer") or {}
    ex, q4, pl = res.get("experts") or {}, res.get("q4") or {}, res.get("plan") or {}
    return {"mode": ld.get("mode"), "download_s": (res.get("download") or {}).get("seconds"), "load_s": ld.get("load_seconds"),
            "peak_gib_after_load": ld.get("max_memory_allocated_gib_after_load"), "peak_host_rss_gib_during_load": ld.get("peak_rss_gib"),
            "q4_s": q4.get("seconds"), "q4_peak_gib": q4.get("peak_alloc_gib"), "q4_by_bits": q4.get("by_bits"), "q4_sanity": q4.get("sanity"),
            "plan_weights_gib_bf16": pl.get("weights_gib_bf16"), "lora_matched": (res.get("lora") or {}).get("matched"), "lora_trainable": (res.get("lora") or {}).get("trainable_params"),
            "experts_default": ex.get("default_in_effect"), "experts_train_impl": ex.get("train_impl"), "experts_gen_impl": ex.get("gen_impl"),
            "train_micro": {a["name"]: (a.get("s_per_step") if a["status"] == "ok" else a["status"]) for a in mi.get("attempts", [])},
            "train_micro_chosen": mi.get("chosen"), "train_micro_peak_gib": mi.get("peak_alloc_gib"),
            "train_trainer_by_tok_budget": {k: {"s_per_step": v.get("s_per_step"), "ckpt": v.get("gradient_checkpointing"), "peak_gib": v.get("peak_alloc_gib"), "status": v.get("status")}
                                            for k, v in (tr.get("budgets") or {}).items()},
            "gen": {k: {"seconds": v.get("seconds"), "new_tokens_per_s": v.get("new_tokens_per_s"), "decode_s_per_step": v.get("decode_s_per_step"), "prefill_s": v.get("prefill_s"),
                        "peak_gib": v.get("peak_alloc_gib"), "status": v.get("status")} for k, v in g.items()},
            "stages": {k: v.get("status") for k, v in res.get("stages", {}).items()}}


def run_estimate(args):
    b = json.loads(Path(args.estimate_from).read_text())
    p = Path(args.a9)
    if not p.exists():
        raise SystemExit(f"addendum-9 result not found: {p} (pass --a9 PATH)")
    a9 = json.loads(p.read_text())
    try:
        est = estimate(b, a9, args.usd_per_hour, args.gen_bs, args.tok_budgets)
    except ValueError as e:
        raise SystemExit(str(e))
    mode = (b.get("load") or {}).get("mode")
    if mode and mode.startswith("tiny"):
        est["warning"] = "this bench JSON comes from a tiny CPU model: the numbers only show that the estimator runs"
    print_estimate(est, label="[TINY CPU RUN - not representative] " if "warning" in est else "")
    dst = Path(args.out) if args.out != "out/moebench/bench.json" else Path(args.estimate_from).with_name(Path(args.estimate_from).stem + ".estimate.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(est, indent=1))
    print(f"\nwrote {dst}")


def main():
    args = build_parser().parse_args()
    if args.estimate_from:
        args.gen_bs = args.gen_bs or list(GEN_BS)
        return run_estimate(args)
    if args.revision is None and args.model == QWEN_REPO:
        args.revision = QWEN_REV
    if args.tiny:  # the CPU run only has to exercise every code path: smaller generation shapes
        args.skip_download, args.try_all_configs = True, True
    for k, real, tiny in (("gen_bs", list(GEN_BS), [4, 8, 16]), ("tag_new", 160, 24), ("dream_steps", 64, 12)):
        if getattr(args, k) is None:
            setattr(args, k, tiny if args.tiny else real)
    rec = Rec(args.out, args)

    def on_term(*_):  # `timeout` sends TERM: unwind through the stages' finally blocks so the JSON keeps every number measured so far
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, on_term)
    code = 0
    try:
        code = run(args, rec)
    finally:
        rec.res["partial"] = False
        rec.res["summary"] = summary_of(rec.res)
        rec.save()
        rec.log(f"SUMMARY {json.dumps(rec.res['summary'])}")
        rec.log(f"[done] wrote {rec.path}")
    sys.exit(code)


def run(args, rec):
    import torch
    cuda = (not args.tiny) and (not args.plan_only) and torch.cuda.is_available()
    if not args.tiny and not args.plan_only and not cuda:
        rec.log("!! no CUDA device: use --tiny for a CPU run, --plan-only for the meta-device plan")
        return 2
    device = torch.device("cuda:0" if cuda else "cpu")
    rng = random.Random(args.seed)
    rec.res["mode"] = "tiny" if args.tiny else "plan_only" if args.plan_only else "real"
    rec.res["model"] = {"repo": args.model, "revision": args.revision}
    with rec.stage("env"):
        rec.res["env"] = env_info()
        rec.log(f"[env] {rec.res['env']}")
        e = rec.res["env"]
        if not args.tiny and not args.plan_only and not e.get("fla_importable"):
            rec.log("!! flash-linear-attention (fla) is not importable: the 30 Gated DeltaNet layers will run the slow pure-PyTorch path (pip install flash-linear-attention==0.6.0)")
    if not args.tiny:
        with rec.stage("config", fatal=True):
            rec.res["model"]["model_type"] = model_type_of(args.model, args.revision)
        with rec.stage("plan", fatal=True):
            plan_model(args, rec)
    if args.plan_only:
        return 0
    if not args.skip_download:
        with rec.stage("download", fatal=True):
            download(args, rec)
    rec.deadline = time.time() + args.budget_min * 60
    rec.res["budget_min_after_download"] = args.budget_min
    with rec.stage("load", fatal=True):
        lm, tok = load_model(args, rec, device)
    import sleepb
    from sleep1 import Lang
    from train import K2_TYPE
    L = Lang(tok, False, device, k2=lm.config.model_type == K2_TYPE)  # as sleepb: Lang(k2=lm.config.model_type == K2_TYPE); Qwen chat format with thinking off
    if not args.no_q4:
        with rec.stage("q4", fatal=True):
            run_q4(args, rec, lm, L, sleepb, device, cuda)
    pm = None
    with rec.stage("lora", fatal=True):
        pm = attach_lora(lm, args, rec)
    if not args.no_experts_probe and not args.no_train:
        with rec.stage("experts"):
            run_experts(args, rec, lm, pm, L, sleepb, cuda, rng)
    elif args.experts_impl:
        set_experts(lm, args.experts_impl)
        rec.res["experts"] = {"forced": args.experts_impl, "train_impl": args.experts_impl, "gen_impl": args.experts_impl}
    if not args.no_train:
        with rec.stage("train_micro"):
            run_train_micro(args, rec, lm, pm, L, sleepb, cuda, rng)
        with rec.stage("train_trainer"):
            run_train_trainer(args, rec, lm, pm, L, sleepb, cuda, rng)
    if not args.no_gen:
        with rec.stage("gen"):
            run_gen(args, rec, lm, pm, L, cuda, rng)
    with rec.stage("estimate"):
        p = Path(args.a9)
        if not p.exists():
            rec.res["estimate"] = {"skipped": f"{p} is not in the pack; run: python3 backbone/sleep/brain/moe_bench.py --estimate-from {rec.path} --usd-per-hour {args.usd_per_hour}"}
            rec.log(f"[estimate] skipped: {p} not found")
        else:
            rec.res["estimate"] = estimate(rec.res, json.loads(p.read_text()), args.usd_per_hour, args.gen_bs, args.tok_budgets)
            print_estimate(rec.res["estimate"], label="[TINY CPU RUN - not representative] " if args.tiny else "")
    return 0


if __name__ == "__main__":
    main()
