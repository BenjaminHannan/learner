#!/usr/bin/env python3
"""One-hour GPU speed bench for a Sleep-B night on a big MoE base held in real 4-bit (bitsandbytes NF4) with LoRA on top.

Written for PREREG-sleepB-addendum11.md, section "MoVA-36B q4: speed bench only" (IFM/K2-Horizon-MoVA-36B-A4B, the default), and model-generic:
--model / --revision take any Hugging Face MoE causal-LM repo (e.g. a Qwen MoE). It measures, in one process, and writes one JSON (partial after every stage):
  download   snapshot_download of the weights, timed (the repo is ~75 GB for MoVA-36B; a disk-space check runs first)
  load       4-bit NF4 + double quant, bf16 compute, device_map={"": 0}; load seconds, torch.cuda.max_memory_allocated after load, peak host RSS
             (the skip list, router/gate modules and lm_head, is found by module-name patterns and checked on a meta-device copy first)
  lora       LoraConfig as in sleepb (r16, alpha 32); the matched module names are printed and counted; --lora-shared adds the shared-expert MLPs
  train_micro   micro-batches of 2048 tokens (8 x 256, chat framing) -> sleepb.tgt_logits (target positions only) + CE + backward + AdamW step;
             2 warm-up + 8 timed steps; if the plain run runs out of memory it is retried with gradient checkpointing (both are reported),
             then with smaller micro-batches
  train_trainer  the real sleepb.Trainer.step on a synthetic batch shaped like sleepb --bench-train's (16 examples + KL replay, --tok-budget 2048)
  gen        Lang.generate on 16 prompts of ~300 tokens: (a) 40 new greedy, (b) 160 new greedy, (c) 200 new sampled; (d) 32 prompts, 40 new greedy
  estimate   the wall time of a Week-2 4x-work night and of the 7-night week at the measured speeds (needs the addendum-9 result JSON, which the
             pack leaves out; run it locally with --estimate-from bench.json, no GPU needed)

  python3 backbone/sleep/brain/k2_bench.py --out out/k2bench/bench.json            # the box (see run_box.sh K2BENCH)
  python3 backbone/sleep/brain/k2_bench.py --tiny --out /tmp/x/bench.json          # CPU: tiny random MoVA from the real remote code, fp32, no bnb
  python3 backbone/sleep/brain/k2_bench.py --tiny --tiny-bnb --out /tmp/x/bench.json   # same, but reloaded through the bnb 4-bit loader on CPU (needs bitsandbytes)
  python3 backbone/sleep/brain/k2_bench.py --estimate-from out/k2bench/bench.json  # no GPU

This is a speed bench: prompts are synthetic (random common words in K2 chat framing), the weights are never changed (lr 0), and generations are forced to run
the full max_new (min_new_tokens = max_new) so every batch decodes the same number of steps. Nothing here touches sleepb.py, train.py or sleep1.py.
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
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent.parent):  # sleepb.py (here), sleep1.py / facts.py (backbone/sleep), train.py (backbone)
    sys.path.insert(0, str(_p))

MOVA_REPO = "IFM/K2-Horizon-MoVA-36B-A4B"
MOVA_REV = "e9ce717642b2074082875be233c02c729ba47960"
# Linear modules that stay in 16-bit (matched by transformers' should_convert_module: the pattern is a prefix, a regex prefix, or the end of the module name):
# lm_head; the routers "mlp.gate" (K2 and Qwen MoE) and "self_attn.v_router" (MoVA); the Qwen MoE shared-expert gate "shared_expert_gate". The router-like Linears the
# meta-device scan finds that these miss are added automatically (suffix of two name parts).
SKIP_DEFAULT = ["lm_head", "mlp.gate", "shared_expert_gate", "self_attn.v_router"]
ROUTER_LAST = re.compile(r"(^|_)(gate|router)$|router|shared_expert_gate")  # last name part of a router-like Linear (gate_proj / up_proj / down_proj do not match)
SHARED_RE = r".*\.layers\.\d+\.mlp\.shared_experts?\.(gate_proj|up_proj|down_proj)"
A9_DEFAULT = HERE / "results_a9" / "result_ab_ob_b4_nb.json"
USD_PER_HOUR = 0.52  # the RTX 5090 rate this project has paid on Vast (design/v3 notes)
WORDS = ("harbour lantern market river bakery morning ledger orchard train window garden letter bridge candle winter copper meadow village stone kettle "
         "carpenter ferry blanket thunder paper valley mirror engine basket island whistle saddle pencil forest anchor button cellar dragon feather gravel "
         "harvest jacket kitchen ladder marble needle oyster pillow quarry ribbon shadow tunnel umbrella velvet wagon yellow zipper apple bottle castle desert "
         "empire flower glacier hammer iron jungle kitten lemon mountain nickel ocean planet quilt rocket silver temple unicorn violin walnut yarn zebra").split()


# ------------------------------------------------------------------ plumbing
def gib(x):
    return None if x is None else round(x / 2 ** 30, 3)


def mem_now():
    """(this process's resident GB, system MemAvailable GB) from /proc; None where unavailable."""
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
        self.res = {"schema": "k2bench-1", "started_utc": time.strftime("%FT%TZ", time.gmtime()), "args": {k: v for k, v in vars(args).items()},
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
    import torch
    d = {"python": sys.version.split()[0], "torch": torch.__version__, "torch_cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available()}
    for pkg in ("transformers", "peft", "accelerate", "bitsandbytes", "huggingface_hub", "hf_xet", "flash-linear-attention"):
        try:
            d[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            d[pkg] = None
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


# ------------------------------------------------------------------ the model: plan, load, audit
def skipped_by(name, patterns):
    """transformers' should_convert_module rule, inverted: True when the module `name` stays in 16-bit."""
    return any(re.match(f"{k}\\.", name) or re.match(f"{k}", name) or name.endswith(k) for k in patterns)


def generic(name):
    return re.sub(r"\.\d+(\.|$)", r".N\1", name)


def plan_quant(lm, skip):
    """Which Linears the bnb loader will quantize and which it will leave alone, from a model object (the real one on the meta device, or the tiny one).
    Returns the plan dict plus the skip list extended with the router-like Linears the given patterns miss."""
    import torch
    lin = [(n, m) for n, m in lm.named_modules() if type(m) is torch.nn.Linear]
    missed = sorted({".".join(n.split(".")[-2:]) for n, m in lin if ROUTER_LAST.search(n.split(".")[-1]) and not skipped_by(n, skip)})
    final = list(dict.fromkeys(list(skip) + missed))
    conv = [(n, m) for n, m in lin if not skipped_by(n, final)]
    kept = [n for n, _ in lin if skipped_by(n, final)]
    qp = sum(m.weight.numel() for _, m in conv)
    tot = sum(p.numel() for p in lm.parameters())
    hid = getattr(lm.config, "hidden_size", 0) or 0
    small = sorted({generic(n) for n, m in conv if hid >= 512 and m.out_features <= max(64, hid // 8)})  # a Linear with a tiny output is a router / gate in disguise: look at these
    fused = [(n, p.numel()) for n, p in lm.named_parameters() if p.dim() >= 3 and p.numel() > 5e7]  # fused expert tensors (not nn.Linear): bnb leaves them in 16-bit
    per = 0.5 + (1 / 64) * (1 / 4 + 4 / (64 * 256))  # NF4 + double-quantised absmax, bytes per weight
    plan = {"linear_modules": len(lin), "to_quantize": len(conv), "kept_16bit": len(kept), "kept_patterns": sorted({generic(n) for n in kept}),
            "skip_modules_given": list(skip), "skip_modules_added": missed, "skip_modules_final": final,
            "params_total_b": round(tot / 1e9, 4), "params_quantized_b": round(qp / 1e9, 4), "params_16bit_b": round((tot - qp) / 1e9, 4),
            "expected_gpu_gib": round((qp * per + (tot - qp) * 2) / 2 ** 30, 2), "small_output_linears_quantized": small[:20],
            "fused_3d_params": [{"name": generic(n), "count_numel": c} for n, c in fused[:6]], "fused_3d_params_n": len(fused),
            "fused_3d_params_gib_bf16": round(sum(c for _, c in fused) * 2 / 2 ** 30, 2)}
    warn = []
    if missed:
        warn.append(f"router-like Linears not covered by the skip list, added: {missed}")
    if small:
        warn.append(f"quantized Linears with a tiny output (<= hidden/8; check they are not routers): {small[:8]}")
    if fused:
        warn.append(f"{len(fused)} fused 3-D parameters ({plan['fused_3d_params_gib_bf16']} GiB in bf16) are not nn.Linear: bnb will NOT quantize them")
    plan["warnings"] = warn
    return plan, final


def audit_loaded(lm):
    """What is actually in memory after load: Linear4bit count, the Linears left in 16-bit, parameter bytes by dtype, devices, meta tensors."""
    import torch
    import bitsandbytes as bnb
    n4 = sum(isinstance(m, bnb.nn.Linear4bit) for m in lm.modules())
    kept = [n for n, m in lm.named_modules() if type(m) is torch.nn.Linear]
    by = collections.Counter()
    for _, p in lm.named_parameters():
        by[str(p.dtype)] += p.numel() * p.element_size()
    for _, b in lm.named_buffers():
        by["buffers:" + str(b.dtype)] += b.numel() * b.element_size()
    return {"linear4bit_modules": n4, "linear_16bit_modules": len(kept), "linear_16bit_patterns": dict(collections.Counter(generic(n) for n in kept)),
            "param_gib_by_dtype": {k: gib(v) for k, v in by.items()}, "devices": sorted({str(p.device) for p in lm.parameters()}),
            "meta_tensors": sum(p.is_meta for p in lm.parameters()), "trust_note": "Params4bit counts packed uint8 bytes; absmax tables are not parameters, see allocated_gib"}


def model_type_of(repo, rev):
    from transformers import PretrainedConfig
    return PretrainedConfig.get_config_dict(repo, revision=rev)[0].get("model_type")


def tiny_config_kwargs():
    """Overrides that turn the real MoVA config into a tiny one with every module type: layer 0 is dense (mlp_only_layers), layers 1-2 are MoVA attention + sparse MoE + shared expert."""
    return dict(hidden_size=64, intermediate_size=128, moe_intermediate_size=32, num_hidden_layers=3, mlp_only_layers=[0], num_attention_heads=4,
                num_key_value_heads=2, head_dim=16, rope_head_dim=16, num_experts=8, num_experts_per_tok=2, mova_num_experts=8, mova_num_experts_per_tok=2,
                max_position_embeddings=2048, eos_token_id=250019, pad_token_id=1)


def build_tiny(args, rec):
    """Tiny random MoVA from the real config + remote code (train.py's K2 smoke does the same for the 3.7B), with the real tokenizer and chat template."""
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
    kw = {"revision": args.revision, "trust_remote_code": True}
    tok = AutoTokenizer.from_pretrained(args.model, **kw)
    cfg = AutoConfig.from_pretrained(args.model, vocab_size=len(tok), **tiny_config_kwargs(), **kw)
    torch.manual_seed(args.seed)
    lm = AutoModelForCausalLM.from_config(cfg, trust_remote_code=True, code_revision=args.revision)
    return lm, tok


def download(args, rec):
    """snapshot_download of weights + code + tokenizer into the HF cache, timed, with a disk check first and a size log every minute."""
    from huggingface_hub import snapshot_download, constants
    cache = Path(constants.HF_HUB_CACHE)
    cache.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(cache).free
    d = {"cache_dir": str(cache), "free_gib_before": gib(free)}
    rec.res["download"] = d
    if free < args.min_free_gb * 2 ** 30:
        d["error"] = f"only {gib(free)} GiB free in {cache}; need {args.min_free_gb} GiB (weights ~75 GiB for MoVA-36B plus pip and logs): rent more disk (vast.py create --disk 130)"
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


def make_plan(args, rec, trust, device):
    """Real mode, before the download: build the model on the meta device (config + code only, no weights), work out which Linears bnb will quantize, extend the skip list
    with router-like Linears the default patterns miss, and refuse to go on if the 4-bit model cannot fit the GPU (e.g. experts stored as fused 3-D tensors, which bnb leaves in
    16-bit). Stores rec.res["quant_plan"]."""
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM
    kw = {**({"revision": args.revision} if args.revision else {}), **({"trust_remote_code": True} if trust else {})}
    skip = list(SKIP_DEFAULT) + [x for x in args.skip.split(",") if x]
    try:
        cfg = AutoConfig.from_pretrained(args.model, **kw)
        with torch.device("meta"):
            meta = AutoModelForCausalLM.from_config(cfg, dtype=torch.bfloat16, **({"trust_remote_code": True, "code_revision": args.revision} if trust else {}))
        plan, final = plan_quant(meta, skip)
        plan["model_class"] = type(meta).__name__
        del meta
    except Exception as e:  # noqa: BLE001
        rec.log(f"!! meta-device plan failed ({e!r}); going on with the default skip list")
        plan, final = {"error": repr(e)[:300], "skip_modules_final": skip}, skip
    rec.res["quant_plan"] = plan
    for w in plan.get("warnings", []):
        rec.log(f"!! plan: {w}")
    rec.log(f"[plan] {plan.get('model_class')}: quantize {plan.get('to_quantize')} Linears ({plan.get('params_quantized_b')} B params), keep {plan.get('kept_16bit')} Linears and "
            f"{plan.get('params_16bit_b')} B params in 16-bit, expected {plan.get('expected_gpu_gib')} GiB on the GPU; skip list {final}")
    total = torch.cuda.get_device_properties(0).total_memory
    need = plan.get("expected_gpu_gib")
    plan["gpu_total_gib"] = gib(total)
    plan["fits_gpu"] = None if need is None else need < 0.9 * total / 2 ** 30
    if plan["fits_gpu"] is False and not args.force_load:
        raise RuntimeError(f"the 4-bit model would take {need} GiB of weights on a {gib(total)} GiB GPU ({plan.get('fused_3d_params_gib_bf16')} GiB of it are fused 3-D expert tensors that "
                           f"bnb does not quantize): stopping before the download (--force-load to try anyway)")


def load_model(args, rec, trust, k2, device):
    """Returns (lm, tok). Real: bnb NF4 4-bit from the Hub cache. Tiny: random fp32 model (no bnb), or with --tiny-bnb saved and reloaded through the bnb loader on CPU."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    kw = {**({"revision": args.revision} if args.revision else {}), **({"trust_remote_code": True} if trust else {})}
    skip = list(SKIP_DEFAULT) + [x for x in args.skip.split(",") if x]
    ld = rec.res["load"] = {"skip_modules_requested": skip}
    if args.tiny:
        t0 = time.time()
        lm, tok = build_tiny(args, rec)
        lm = lm.to(torch.float32)
        ld["load_seconds"] = round(time.time() - t0, 2)
        plan, final = plan_quant(lm, skip)
        rec.res["quant_plan"] = plan
        if args.tiny_bnb:
            d = rec.path.parent / "tiny_ckpt"
            lm.save_pretrained(d)
            q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float32, bnb_4bit_use_double_quant=True,
                                   llm_int8_skip_modules=final)
            t0 = time.time()
            lm = AutoModelForCausalLM.from_pretrained(d, quantization_config=q, device_map={"": "cpu"}, dtype=torch.float32, trust_remote_code=True)
            ld["load_seconds"] = round(time.time() - t0, 2)
            ld["mode"] = "tiny_bnb_cpu"
            shutil.rmtree(d, ignore_errors=True)
        else:
            ld["mode"] = "tiny_fp32"
        lm.to(device).eval()
    else:
        ld["mode"] = "bnb_nf4_cuda"
        final = rec.res["quant_plan"]["skip_modules_final"]
        tok = AutoTokenizer.from_pretrained(args.model, **kw)
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
                               llm_int8_skip_modules=final)
        torch.cuda.reset_peak_memory_stats()
        mon = Sampler(rec, "load", every=30.0)
        mon.start()
        t0 = time.time()
        try:
            lm = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=q, device_map={"": 0}, dtype=torch.bfloat16, **kw)
        finally:
            ld.update(mon.stop())
        torch.cuda.synchronize()
        ld["load_seconds"] = round(time.time() - t0, 1)
        lm.eval()
    for p in lm.parameters():
        p.requires_grad_(False)
    ld["skip_modules_final"] = final
    ld["config_model_type"] = lm.config.model_type
    ld["n_params_b"] = round(sum(p.numel() for p in lm.parameters()) / 1e9, 4)
    if device.type == "cuda":
        ld["max_memory_allocated_gib_after_load"] = gib(torch.cuda.max_memory_allocated())
        ld["memory_allocated_gib_after_load"] = gib(torch.cuda.memory_allocated())
        ld["max_memory_reserved_gib_after_load"] = gib(torch.cuda.max_memory_reserved())
    if not args.tiny or args.tiny_bnb:
        rec.res["quant_audit"] = audit_loaded(lm)
        rec.log(f"[audit] {rec.res['quant_audit']}")
    rec.log(f"[load] {ld}")
    return lm, tok


# ------------------------------------------------------------------ LoRA
def lora_targets(lora_shared):
    from train import LORA_TARGETS
    return f"(?:{LORA_TARGETS})|(?:{SHARED_RE})" if lora_shared else LORA_TARGETS


def expected_lora_count(cfg, shared):
    """K2 only (the layer layout is in the config): dense layers have q/k/v/o + gate/up/down (7), sparse (MoVA) layers q/k/o (3), + 3 shared-expert MLPs per sparse layer."""
    n = cfg.num_hidden_layers
    sparse = [i for i in range(n) if i not in set(cfg.mlp_only_layers) and cfg.num_experts > 0 and (i + 1) % cfg.decoder_sparse_step == 0]
    return 7 * (n - len(sparse)) + 3 * len(sparse) + (3 * len(sparse) if shared and getattr(cfg, "num_shared_experts", 0) else 0)


def attach_lora(lm, args, rec, k2):
    from peft import LoraConfig, get_peft_model
    from peft.tuners.lora import LoraLayer
    targets = lora_targets(args.lora_shared)
    pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0, target_modules=targets, bias="none"))
    names = [n.removeprefix("base_model.model.") for n, m in pm.named_modules() if isinstance(m, LoraLayer)]
    by = collections.Counter(generic(n) for n in names)
    trainable = sum(p.numel() for p in pm.parameters() if p.requires_grad)
    exp = expected_lora_count(lm.config, args.lora_shared) if k2 else None
    d = rec.res["lora"] = {"rank": args.rank, "alpha": args.alpha, "lora_shared": args.lora_shared, "target_regex": targets, "matched": len(names),
                           "matched_by_pattern": dict(by), "expected_matched": exp, "matches_expected": None if exp is None else exp == len(names),
                           "trainable_params": trainable, "first_names": names[:8]}
    rec.log(f"[lora] target regex: {targets}")
    rec.log(f"[lora] matched {len(names)} modules (expected {exp}); by pattern: {dict(by)}")
    rec.log(f"[lora] trainable params {trainable:,}")
    return pm


# ------------------------------------------------------------------ synthetic data
def synth_prompt(L, target, rng):
    """A chat-framed prompt (sleep1.SYS system line, K2 no-think render) of `target` tokens (+-1): random common words, cut at the shortest prefix that reaches the target."""
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
    ladder = [{"name": "plain", "ckpt": False, "micro_tokens": args.micro_seqs * args.micro_len},
              {"name": "ckpt", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len},
              {"name": "ckpt_half", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len // 2},
              {"name": "ckpt_quarter", "ckpt": True, "micro_tokens": args.micro_seqs * args.micro_len // 4}]
    out = rec.res["train_micro"] = {"shape": f"{args.micro_seqs} x {args.micro_len} tokens, chat framing, loss on the last 9 tokens of each", "warmup": args.warmup, "timed": args.timed,
                                    "optimizer": "AdamW lr 0 (weights never move)", "attempts": [], "chosen": None, "gradient_checkpointing_kwargs": {"use_reentrant": False},
                                    "prepare_model_for_kbit_training": "not used (it upcasts the 16-bit embeddings / lm_head to fp32); gradients reach the LoRA matrices without it",
                                    "enable_input_require_grads": False}
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


def run_train_trainer(args, rec, lm, pm, L, sleepb, cuda, rng):
    """sleepb.Trainer.step itself on the bench-train batch, with the config the micro bench settled on (checkpointing, micro-batch size = --tok-budget)."""
    import torch
    mi = rec.res["train_micro"]
    if mi.get("chosen") is None:
        raise RuntimeError("no micro-bench config worked; Trainer bench skipped")
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    set_ckpt(lm, mi["ckpt"])
    old = sleepb.TOK_BUDGET
    sleepb.TOK_BUDGET = mi["micro_tokens"]
    batch, replay = trainer_batch(L, args.bsz, args.replay_bsz, rng)
    ta = argparse.Namespace(lr=0.0, kl_weight=1.0, replay_bsz=args.replay_bsz)
    mb = sleepb.groups(sorted(batch, key=lambda x: -len(x[0])))
    rg = sleepb.groups(sorted(replay[:args.replay_bsz], key=lambda x: -len(x[0])))
    out = rec.res["train_trainer"] = {"what": "sleepb.Trainer.step (CE on the batch + KL guard on replay vs the adapter-off base), lr 0", "tok_budget": mi["micro_tokens"],
                                      "gradient_checkpointing": mi["ckpt"], "bsz": args.bsz, "replay_bsz": args.replay_bsz,
                                      "micro_batches": [len(mb), len(rg)], "padded_tokens": [sum(len(g) * max(len(x[0]) for x in g) for g in mb),
                                                                                           sum(len(g) * max(len(x[0]) for x in g) for g in rg)],
                                      "warmup": args.trainer_warmup, "timed_requested": args.trainer_timed}
    rec.save()
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    times = []
    tr = None
    try:
        free_gpu(pm)
        tr = sleepb.Trainer(L, pm, ta, replay, args.trainer_warmup + args.trainer_timed, 0)
        for i in range(args.trainer_warmup + args.trainer_timed):
            if i >= args.trainer_warmup + 1 and rec.time_left() < 0:
                out["stopped_early"] = "time budget"
                break
            sync()
            t = time.time()
            tr.step(batch)
            sync()
            dt = time.time() - t
            rec.log(f"[train_trainer] step {i + 1} {dt:.2f}s")
            if i >= args.trainer_warmup:
                times.append(dt)
    except Exception as e:  # noqa: BLE001
        out.update(status="oom" if is_oom(e) else "error", error=repr(e)[:300], **peak(cuda))
        raise
    finally:
        sleepb.TOK_BUDGET = old
        pm.eval()
        del tr
        free_gpu(pm)
    out.update(status="ok", s_per_step=round(sum(times) / len(times), 4), step_seconds=[round(x, 4) for x in times], n_timed=len(times), **peak(cuda))
    rec.log(f"[train_trainer] {out['s_per_step']} s per Trainer step ({out['micro_batches']} micro-batches), peak {out.get('peak_alloc_gib')} GiB")


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


GEN_CONFIGS = [("a", 16, 40, False), ("b", 16, 160, False), ("c", 16, 200, True), ("d", 32, 40, False)]  # (name, prompts, new tokens, sampled)


def run_gen(args, rec, lm, pm, L, cuda, rng, which):
    import torch
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    set_ckpt(lm, False)
    pm.eval()
    probe = GenProbe(pm, sync, L.eos, force_full=not args.allow_early_eos)
    out = rec.res.setdefault("gen", {"adapter": "off (the base model, as the tagger / dreamer / verifier run); the LoRA adds ~1 small matmul pair per target module per step",
                                     "prompt_tokens": args.gen_prompt_len, "forced_full_length": not args.allow_early_eos, "sampling": "temperature 0.8, top_p 0.95, top_k 0 (Lang.generate)"})
    with pm.disable_adapter():
        if "warm" not in out:
            L.generate(probe, [synth_prompt(L, 32, rng)] * 2, max_new=4, bs=2)  # untimed: kernels, allocator, bnb
            out["warm"] = True
        last_step = max((out[k].get("seconds_per_step") or 0 for k in "abcd" if isinstance(out.get(k), dict)), default=0)
        for name, B, new, sampled in GEN_CONFIGS:
            if name not in which:
                continue
            need = 1.1 * new * last_step if last_step else 90.0  # a config costs about its steps x the seconds per step seen so far
            if rec.time_left() < need:
                out[name] = {"status": f"skipped: time budget ({rec.time_left():.0f}s left, about {need:.0f}s needed)"}
                continue
            prompts = [synth_prompt(L, args.gen_prompt_len, rng) for _ in range(B)]
            ptok = [len(L.ids(p)) for p in prompts]
            row = {"prompts": B, "prompt_tokens_mean": round(sum(ptok) / B, 1), "max_new": new, "sampled": sampled}
            try:
                if name in ("a", "d"):  # the prefill alone (one new token): the fixed cost of a batch
                    probe.calls.clear()
                    L.generate(probe, prompts, max_new=1, bs=B)
                    row["prefill_s"] = probe.calls[0]["model_generate_s"]
                probe.calls.clear()
                if cuda:
                    torch.cuda.reset_peak_memory_stats()
                sync()
                t = time.time()
                outs = L.generate(probe, prompts, max_new=new, bs=B, sample=sampled)
                sync()
                wall = time.time() - t
                c = probe.calls[0]
                row.update(status="ok", seconds=round(wall, 3), model_generate_s=c["model_generate_s"], steps=c["steps"], new_tokens=c["new_tokens"],
                           new_tokens_per_s=round(c["new_tokens"] / wall, 2), seconds_per_step=round(wall / max(c["steps"], 1), 4), sample_out=outs[0][:160], **peak(cuda))
            except Exception as e:  # noqa: BLE001
                row.update(status="oom" if is_oom(e) else "error", error=repr(e)[:300])
                free_gpu()
            out[name] = row
            last_step = max(last_step, row.get("seconds_per_step") or 0)
            rec.log(f"[gen:{name}] {row}")
            rec.save()


# ------------------------------------------------------------------ the night estimate
# Prompt lengths (tokens) assumed per phase when the bench JSON cannot know them (only the prefill share depends on them, the decode loop dominates).
PROMPT_TOK = {"tag": 220, "names": 220, "detect": 450, "dream": 450, "verify": 420, "probe": 60, "rem": 250, "rem_verify": 420, "arc": 150, "replay": 40, "weights": 60, "diary": 700}
TRAINER_STEP_IN_MICRO = 4.0  # fallback when the Trainer bench is missing: 3 padded micro-batches + 1 replay group (x2 forwards) per Trainer step, in 2048-token micro-step units
LONG_GEN = 40  # generations of at least this many new tokens get the "typical" length fraction (tagging 160, dreaming 400 x scale, REM 40); short ones always run full


def speeds_from_bench(b):
    """Prefill rate, decode seconds per step (greedy / sampled, batch 16 / 32) and training seconds per step from a bench JSON."""
    g = b.get("gen") or {}
    a, bb, c, d = [g.get(k) or {} for k in "abcd"]
    good = lambda x: bool(x.get("seconds") and x.get("steps"))  # noqa: E731
    sp, notes = {}, []
    if a.get("prefill_s"):
        sp["prefill_tok_s"] = a["prompts"] * a["prompt_tokens_mean"] / a["prefill_s"]
    else:
        notes.append("no prefill measurement: prefill taken as free")

    def dec(x):
        if not good(x):
            return None
        pf = x["prompts"] * x["prompt_tokens_mean"] / sp["prefill_tok_s"] if sp.get("prefill_tok_s") else 0.0
        return max((x["seconds"] - pf) / max(x["steps"] - 1, 1), 1e-6)
    dg16 = dec(bb) or dec(a)
    if dg16 is None:
        raise ValueError("bench JSON has no usable generation timing (gen.a / gen.b)")
    ds16 = dec(c)
    if ds16 is None:
        ds16 = dg16
        notes.append("no sampled timing (gen.c): sampled decode step taken equal to greedy")
    dg32 = dec(d)
    if dg32 is None:
        dg32 = dg16
        notes.append("no 32-prompt timing (gen.d): decode step at batch 32 taken equal to batch 16 (launch-bound decode)")
    sp.update(dec_greedy_16=dg16, dec_sampled_16=ds16, dec_greedy_32=dg32, dec_sampled_32=ds16 * dg32 / dg16)
    tr, mi = b.get("train_trainer") or {}, b.get("train_micro") or {}
    if tr.get("status") == "ok":
        sp["train_s_per_step"], sp["train_source"] = tr["s_per_step"], "Trainer.step measured"
    elif mi.get("s_per_step"):
        sp["train_s_per_step"], sp["train_source"] = mi["s_per_step"] * TRAINER_STEP_IN_MICRO, f"micro step x {TRAINER_STEP_IN_MICRO}"
        notes.append(f"no Trainer.step timing: a Trainer step taken as {TRAINER_STEP_IN_MICRO} micro-steps of 2048 tokens")
    else:
        raise ValueError("bench JSON has no usable training timing (train_trainer / train_micro)")
    sp["notes"] = notes
    sp["load_seconds"] = (b.get("load") or {}).get("load_seconds")
    return sp


def dec_step(sp, n, sampled):
    lo, hi = (sp["dec_sampled_16"], sp["dec_sampled_32"]) if sampled else (sp["dec_greedy_16"], sp["dec_greedy_32"])
    return lo if n <= 16 else hi if n >= 32 else lo + (hi - lo) * (n - 16) / 16


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


def night_seconds(sp, n, bs, frac):
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
    ph["train"] = n.get("steps", 0) * sp["train_s_per_step"]
    rem_g = rem_v = 0.0
    for rs in n.get("rem_stats") or []:
        rem_g += G(rs.get("chain_gen", 0) + rs.get("gist_gen", 0), 40, "rem", True)
        rem_v += G(rs.get("chain_kept", 0) + rs.get("gist_kept", 0) + rs.get("dropped_unverified", 0) + rs.get("dropped_dup", 0) + rs.get("chain_extra_dropped", 0), 20, "rem_verify")
    ph["rem_generate"], ph["rem_verify"] = rem_g, rem_v
    return ph


def once_seconds(sp, a9, bs, frac):
    """Per-run costs outside the nights: generic replay generation, ARC base scores, the learning-curve probes, the final scoring in three modes, the model load."""
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
    o["model_load"] = sp.get("load_seconds") or 0.0
    return o


def estimate(b, a9, usd_h, bs, fracs=(1.0, 0.6)):
    sp = speeds_from_bench(b)
    out = {"inputs": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in sp.items()}, "gen_bs": bs, "usd_per_hour": usd_h, "a9_arm": a9.get("arm"),
           "a9_model": a9.get("model"), "a9_wall_seconds_on_that_model": a9.get("wall_seconds"), "scenarios": {}}
    for f in fracs:
        nights = [night_seconds(sp, n, bs, f) for n in a9["nights"]]
        once = once_seconds(sp, a9, bs, f)
        rows = [{"night": n["night"], "steps": n.get("steps"), **{k: round(v, 1) for k, v in ph.items()}, "total_s": round(sum(ph.values()), 1)} for n, ph in zip(a9["nights"], nights)]
        week = sum(r["total_s"] for r in rows)
        total = week + sum(once.values())
        by = collections.Counter()
        for ph in nights:
            by.update(ph)
        out["scenarios"]["full_max_new" if f == 1.0 else f"typical_{f}"] = {
            "length_fraction_of_long_generations": f, "per_night": rows, "once_per_run_s": {k: round(v, 1) for k, v in once.items()}, "week_nights_s": round(week, 1),
            "total_s_without_download": round(total, 1), "total_hours": round(total / 3600, 2), "total_usd": round(total / 3600 * usd_h, 2),
            "week_seconds_by_phase": {k: round(v, 1) for k, v in by.most_common()}, "x_the_qwen_run": (round(total / a9["wall_seconds"], 1) if a9.get("wall_seconds") else None)}
    out["assumptions"] = [
        "Generation work per night is read from the addendum-9 seed-1 result (nights[i].tagging.turns, names_pass.pairs, update_detection.candidates, dream_stats.items / now_gen / qa_gen / dropped_bad_answer, "
        "with_dreams, rem_stats[c].chain_gen / gist_gen / kept / dropped_unverified / dropped_dup, steps); the same arm on the big base would see somewhat different counts.",
        "Not stored, so assumed: 'now' prompts = ceil(now_gen / 2); dream verification prompts = qa_gen + now_gen - dropped_bad_answer (upper bound); probes = with_dreams; "
        "ARC validation = 100 questions per night; prompt lengths per phase = PROMPT_TOK (only prefill depends on them).",
        "Every generate batch decodes max_new steps (an upper bound: a batch stops when all rows end). 'typical_0.6' cuts the long generations (tagging 160, dreams 400 x scale, REM 40) to 60% "
        "of max_new; this fraction is a guess, not a measurement.",
        "Decode seconds per step are measured at 16 and 32 prompts with the adapter off; batches smaller than 16 cost as 16. Training uses the measured seconds per Trainer step "
        "for every step (the real batches are longer or shorter than the synthetic one: the open-book examples carry the diary notes).",
        "Not counted: the download, CPU-side bookkeeping (BM25 search, parsing), SHY (0.1 s per night on Qwen), the adapter snapshot / restore."]
    out["notes"] = sp["notes"]
    return out


def print_estimate(est, label=""):
    print(f"\n=== Sleep-B night estimate {label}(arm {est['a9_arm']}, counts from the {est['a9_model']} run; batch {est['gen_bs']}; ${est['usd_per_hour']}/h) ===")
    i = est["inputs"]
    print(f"measured: prefill {i.get('prefill_tok_s', float('nan')):.0f} tok/s; decode step greedy {i['dec_greedy_16']:.3f}s (16) / {i['dec_greedy_32']:.3f}s (32), "
          f"sampled {i['dec_sampled_16']:.3f}s (16); train {i['train_s_per_step']:.2f}s per step ({i['train_source']}); load {i.get('load_seconds')}s")
    for n in est["notes"]:
        print("  note:", n)
    for name, s in est["scenarios"].items():
        print(f"\n-- {name} (long generations run {s['length_fraction_of_long_generations']:.0%} of max_new)")
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
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=MOVA_REPO, help="any Hugging Face MoE causal-LM repo (default: the addendum-11 MoVA-36B)")
    ap.add_argument("--revision", default=None, help="repo revision (default: the pinned MoVA commit for the default model, else the repo's main)")
    ap.add_argument("--out", default="out/k2bench/bench.json", help="result JSON (the log is written next to it)")
    ap.add_argument("--tiny", action="store_true", help="CPU: tiny random MoVA built from the real remote code (K2 repos only), fp32, no bnb")
    ap.add_argument("--tiny-bnb", action="store_true", help="with --tiny: save the tiny model and reload it through the bitsandbytes 4-bit loader on CPU")
    ap.add_argument("--estimate-from", default=None, help="bench JSON -> print the night / week estimate (no GPU, no model) and exit")
    ap.add_argument("--a9", default=str(A9_DEFAULT), help="addendum-9 result JSON the estimate takes its per-night counts from")
    ap.add_argument("--usd-per-hour", type=float, default=USD_PER_HOUR)
    ap.add_argument("--est-gen-bs", type=int, default=32, help="generation batch size of the real runs (sleepb --gen-bs)")
    ap.add_argument("--lora-shared", action="store_true", help="also put LoRA on the shared-expert MLPs (mlp.shared_expert(s).{gate,up,down}_proj)")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--skip", default="", help="extra comma-separated module-name patterns to keep out of 4-bit (added to the defaults)")
    ap.add_argument("--trust-remote-code", action="store_true", help="K2 repos always use remote code; set this for another repo that needs it")
    ap.add_argument("--min-free-gb", type=float, default=80.0, help="refuse to download with less free disk than this")
    ap.add_argument("--skip-download", action="store_true", help="the repo is already in the HF cache")
    ap.add_argument("--force-load", action="store_true", help="load even if the pre-download plan says the 4-bit weights do not fit the GPU")
    ap.add_argument("--budget-min", type=float, default=50.0, help="minutes for load + every stage after the download; stages that start late are skipped, timed loops stop early")
    ap.add_argument("--no-train", action="store_true")
    ap.add_argument("--no-gen", action="store_true")
    ap.add_argument("--micro-seqs", type=int, default=8)
    ap.add_argument("--micro-len", type=int, default=256)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--timed", type=int, default=8)
    ap.add_argument("--trainer-warmup", type=int, default=1)
    ap.add_argument("--trainer-timed", type=int, default=3)
    ap.add_argument("--bsz", type=int, default=16, help="Trainer bench: examples per step (sleepb --bsz)")
    ap.add_argument("--replay-bsz", type=int, default=8)
    ap.add_argument("--gen-prompt-len", type=int, default=300)
    ap.add_argument("--gen-only", default="abcd", help="which generation configs to run (letters of a b c d)")
    ap.add_argument("--allow-early-eos", action="store_true", help="do not force full-length generations")
    ap.add_argument("--try-all-configs", action="store_true", help="run every micro-bench config even after one worked (default on with --tiny)")
    ap.add_argument("--seed", type=int, default=0)
    return ap


def summary_of(res):
    """The headline numbers, in one dict."""
    g, ld, mi, tr = res.get("gen") or {}, res.get("load") or {}, res.get("train_micro") or {}, res.get("train_trainer") or {}
    return {"mode": ld.get("mode"), "download_s": (res.get("download") or {}).get("seconds"), "load_s": ld.get("load_seconds"),
            "peak_gib_after_load": ld.get("max_memory_allocated_gib_after_load"), "peak_host_rss_gib_during_load": ld.get("peak_rss_gib"),
            "lora_matched": (res.get("lora") or {}).get("matched"), "lora_trainable": (res.get("lora") or {}).get("trainable_params"),
            "train_micro": {a["name"]: (a.get("s_per_step") if a["status"] == "ok" else a["status"]) for a in mi.get("attempts", [])},
            "train_micro_chosen": mi.get("chosen"), "train_micro_peak_gib": mi.get("peak_alloc_gib"),
            "train_trainer_s_per_step": tr.get("s_per_step"), "train_trainer_peak_gib": tr.get("peak_alloc_gib"),
            "gen": {k: {"seconds": v.get("seconds"), "new_tokens_per_s": v.get("new_tokens_per_s")} for k, v in g.items() if isinstance(v, dict)},
            "stages": {k: v.get("status") for k, v in res.get("stages", {}).items()}}


def run_estimate(args):
    b = json.loads(Path(args.estimate_from).read_text())
    p = Path(args.a9)
    if not p.exists():
        raise SystemExit(f"addendum-9 result not found: {p} (pass --a9 PATH)")
    a9 = json.loads(p.read_text())
    try:
        est = estimate(b, a9, args.usd_per_hour, args.est_gen_bs)
    except ValueError as e:
        raise SystemExit(str(e))
    mode = (b.get("load") or {}).get("mode")
    if mode and mode.startswith("tiny"):
        est["warning"] = "this bench JSON comes from a tiny CPU model: the numbers only show that the estimator runs"
    print_estimate(est, label="[TINY CPU RUN - not representative] " if "warning" in est else "")
    dst = Path(args.out) if args.out != "out/k2bench/bench.json" else Path(args.estimate_from).with_name(Path(args.estimate_from).stem + ".estimate.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(est, indent=1))
    print(f"\nwrote {dst}")


def main():
    args = build_parser().parse_args()
    if args.estimate_from:
        return run_estimate(args)
    if args.revision is None and args.model == MOVA_REPO:
        args.revision = MOVA_REV
    if args.tiny:
        args.skip_download, args.try_all_configs = True, True
        if args.model != MOVA_REPO and "k2-horizon" not in args.model.lower():
            raise SystemExit("--tiny builds a tiny K2 from the real remote code: use a K2-Horizon repo")
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
    cuda = (not args.tiny) and torch.cuda.is_available()
    if not args.tiny and not cuda:
        rec.log("!! no CUDA device: use --tiny for a CPU run")
        return 2
    device = torch.device("cuda:0" if cuda else "cpu")
    rng = random.Random(args.seed)
    rec.res["mode"] = "tiny_bnb" if (args.tiny and args.tiny_bnb) else "tiny" if args.tiny else "real"
    rec.res["model"] = {"repo": args.model, "revision": args.revision}
    with rec.stage("env"):
        rec.res["env"] = env_info()
        rec.log(f"[env] {rec.res['env']}")
    if not args.tiny:
        try:
            import bitsandbytes  # noqa: F401
        except Exception as e:  # noqa: BLE001
            rec.log(f"!! bitsandbytes is not importable: {e!r} (pip install bitsandbytes)")
            rec.res["stages"]["env"]["bitsandbytes_error"] = repr(e)[:300]
            rec.save()
            return 3
    model_type = None
    if args.tiny:
        model_type = "k2_horizon"
    else:
        with rec.stage("config", fatal=True):
            model_type = model_type_of(args.model, args.revision)
            rec.res["model"]["model_type"] = model_type
    from train import K2_TYPE
    k2 = model_type == K2_TYPE  # as sleepb: Lang(k2=lm.config.model_type == K2_TYPE)
    trust = k2 or args.trust_remote_code
    if not args.tiny:
        with rec.stage("plan", fatal=True):
            make_plan(args, rec, trust, device)
    if not args.skip_download:
        with rec.stage("download", fatal=True):
            download(args, rec)
    rec.deadline = time.time() + args.budget_min * 60
    rec.res["budget_min_after_download"] = args.budget_min
    with rec.stage("load", fatal=True):
        lm, tok = load_model(args, rec, trust, k2, device)
    import sleepb
    from sleep1 import Lang
    L = Lang(tok, False, device, k2=lm.config.model_type == K2_TYPE)
    rec.res["k2_chat_format"] = L.k2
    pm = None
    with rec.stage("lora", fatal=True):
        pm = attach_lora(lm, args, rec, k2)
    if not args.no_train:
        with rec.stage("train_micro"):
            run_train_micro(args, rec, lm, pm, L, sleepb, cuda, rng)
    if not args.no_gen:
        with rec.stage("gen_abc"):
            run_gen(args, rec, lm, pm, L, cuda, rng, set(args.gen_only) & set("abc"))
    if not args.no_train:
        with rec.stage("train_trainer"):
            run_train_trainer(args, rec, lm, pm, L, sleepb, cuda, rng)
    if not args.no_gen:
        with rec.stage("gen_d"):
            run_gen(args, rec, lm, pm, L, cuda, rng, set(args.gen_only) & set("d"))
    with rec.stage("estimate"):
        p = Path(args.a9)
        if not p.exists():
            rec.res["estimate"] = {"skipped": f"{p} is not in the pack; run: python3 backbone/sleep/brain/k2_bench.py --estimate-from {rec.path}"}
            rec.log(f"[estimate] skipped: {p} not found")
        else:
            rec.res["estimate"] = estimate(rec.res, json.loads(p.read_text()), args.usd_per_hour, args.est_gen_bs)
            print_estimate(rec.res["estimate"], label="[TINY CPU RUN - not representative] " if args.tiny else "")
    return 0


if __name__ == "__main__":
    main()
