"""PyTorch backend (HF transformers + peft LoRA) for the Windows app (and any CUDA / CPU box). Untested until a real run.

Device: cuda if available, else cpu. Dtype: bf16 (or fp16 if bf16 is unsupported) on GPU, fp32 on CPU. The LoRA weights are kept in fp32.
The adapter is saved in PEFT format (adapter_model.safetensors + adapter_config.json), which llama.cpp can convert:
    python llama.cpp/convert_lora_to_gguf.py <adapter dir> --base <HF base model dir> --outfile adapter.gguf
and the app then runs  llama-server -m base.gguf --lora adapter.gguf   (see `python -m sleepmlx export-gguf`).
"""
from __future__ import annotations

import gc
import json
import math
import os
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")   # ops MPS lacks fall back to the CPU (must be set before torch is imported)

from .backend import Backend, Example
from .model import pack
from .shy import shy_core


def pick_device_dtype(torch):
    """Device order: cuda, then mps, then cpu.
    cuda: bf16 (fp16 if bf16 is unsupported). mps: fp16 for the frozen base (bf16 is shaky on M1), LoRA weights kept in fp32 and the loss in fp32,
    so no loss scaling is needed (the safe option: only the frozen base is half precision). cpu: bf16 base (1.7B = ~3.4 GB), fp32 LoRA."""
    if torch.cuda.is_available():
        bf = getattr(torch.cuda, "is_bf16_supported", lambda: False)()
        return "cuda", (torch.bfloat16 if bf else torch.float16)
    mps = getattr(getattr(torch, "backends", None), "mps", None)
    if mps is not None and mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.bfloat16


MPS_RAM_SHARE = 0.45   # a Mac with more RAM gets this share of it as the MPS cap; the profile's mps_mem_gb stays the floor


def ram_bytes() -> Optional[float]:
    try:
        return float(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
    except (ValueError, OSError, AttributeError):
        return None


def mps_cap_gb(profile_gb, env=None, ram: Optional[float] = None) -> Optional[float]:
    """The MPS cap for this machine: env SLEEPMLX_MPS_MEM_GB if set, else max(profile mps_mem_gb, MPS_RAM_SHARE x RAM).
    The profile's 10 GB (sized for 8 GB Macs) out-of-memoried LFM3 training on a 32 GB M1 Pro; a bigger Mac now gets a bigger cap."""
    env = os.environ if env is None else env
    if env.get("SLEEPMLX_MPS_MEM_GB"):
        return float(env["SLEEPMLX_MPS_MEM_GB"])
    if not profile_gb:
        return None
    ram = ram_bytes() if ram is None else ram
    return max(float(profile_gb), MPS_RAM_SHARE * ram / 1e9) if ram else float(profile_gb)


def set_mps_cap(torch, gb: float) -> float:
    """Cap this process's MPS memory at about gb GB via torch.mps.set_per_process_memory_fraction (a fraction of the recommended working set)."""
    total = None
    f = getattr(torch.mps, "recommended_max_memory", None)
    if f:
        try:
            total = float(f())
        except Exception:
            total = None
    if total is None:
        try:
            import psutil
            total = float(psutil.virtual_memory().total)
        except Exception:
            total = 32e9
    frac = max(0.05, min(1.0, gb * 1e9 / total))
    torch.mps.set_per_process_memory_fraction(frac)
    return frac


def set_cpu_threads(spec="cores-1"):
    """torch.set_num_threads: physical cores - 1 ('cores-1'), or an int."""
    import torch
    if isinstance(spec, int):
        n = spec
    else:
        try:
            import psutil
            cores = psutil.cpu_count(logical=False) or (os.cpu_count() or 2) // 2
        except Exception:
            cores = max((os.cpu_count() or 2) // 2, 1)
        n = max(cores - 1, 1)
    torch.set_num_threads(n)
    return n


def load(model_id_or_dir: str, trust_remote_code: bool = False, dtype=None, device=None, mps_gb: Optional[float] = None):
    """-> (model, tokenizer) from a HF id or a local dir. mps_gb: memory cap applied before the weights are loaded (MPS only)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev, dt = pick_device_dtype(torch)
    if dev == "mps" and mps_gb:
        set_mps_cap(torch, float(mps_gb))
    dtype, device = dtype or dt, device or dev
    tok = AutoTokenizer.from_pretrained(model_id_or_dir, trust_remote_code=trust_remote_code)
    model = AutoModelForCausalLM.from_pretrained(model_id_or_dir, torch_dtype=dtype, trust_remote_code=trust_remote_code)
    model.to(device)
    return model, tok


def is_oom(e: BaseException) -> bool:
    m = str(e).lower()
    return "out of memory" in m or "mps backend out of memory" in m


class TorchBackend(Backend):
    def __init__(self, model, tok, prof, model_id: str = "", tok_budget: int = 1024, grad_ckpt: bool = True, gen_batch: int = 8):
        import torch
        from peft import LoraConfig, get_peft_model
        self.torch = torch
        self.tok, self.prof, self.model_id = tok, prof, model_id
        self.tok_budget, self.gen_batch = tok_budget, gen_batch
        self.device, self.dtype = pick_device_dtype(torch)
        self.threads = set_cpu_threads(prof.runtime.get("threads", "cores-1")) if self.device == "cpu" else None
        cap = mps_cap_gb(prof.runtime.get("mps_mem_gb")) if self.device == "mps" else None
        self.mps_fraction = set_mps_cap(torch, cap) if cap else None
        self.lora_cfg = dict(prof.lora)
        targets = self.lora_cfg.get("target_modules") or [k.split(".")[-1] for k in self.lora_cfg["keys"]]   # a regex string or a list of names
        r = int(self.lora_cfg["rank"])
        self.scale = float(self.lora_cfg["scale"])
        if grad_ckpt:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            if hasattr(model, "enable_input_require_grads"):
                model.enable_input_require_grads()
        cfg = LoraConfig(r=r, lora_alpha=int(round(r * self.scale)), lora_dropout=float(self.lora_cfg.get("dropout", 0.0)),
                         target_modules=targets if isinstance(targets, str) else list(targets), task_type="CAUSAL_LM")
        self.model = get_peft_model(model, cfg)
        for n, p in self.model.named_parameters():
            if p.requires_grad:
                p.data = p.data.float()
        self.lm = self.model.get_base_model()
        self.stop_id = tok.convert_tokens_to_ids(prof.stop_token) if prof.stop_token else tok.eos_token_id
        if tok.pad_token_id is None:
            tok.pad_token = tok.eos_token
        tok.padding_side = "left"
        self.params = [p for p in self.model.parameters() if p.requires_grad]
        self.opt, self.total, self.lr0 = None, 1, 2e-4

    def encode(self, text: str) -> List[int]:
        return list(self.tok(text, add_special_tokens=False)["input_ids"])

    def _autocast(self):
        t = self.torch
        return t.autocast(device_type="cuda", dtype=self.dtype) if self.device == "cuda" else t.autocast(device_type="cpu", enabled=False)

    def free(self) -> None:
        """Give cached blocks back to the device (Oct 29: Ben's 16 GB M1 ran out of MPS memory in chunk 2, 3 GB of it cached "other")."""
        gc.collect()
        if self.device == "cuda":
            self.torch.cuda.empty_cache()
        elif self.device == "mps":
            self.torch.mps.empty_cache()

    # ---- generation
    def generate(self, prompts, max_tokens, temp=0.0, adapter=True, stops=()):
        """Out of memory: free the cache, halve the batch for the rest of the night and redo this batch in halves (down to one prompt)."""
        prompts = list(prompts)
        try:
            return self._generate(prompts, max_tokens, temp, adapter, stops)
        except RuntimeError as e:
            if not is_oom(e):
                raise
            self.free()
            if len(prompts) == 1:
                raise
            self.gen_batch = max(1, min(self.gen_batch, len(prompts)) // 2)
            self.oom_events = getattr(self, "oom_events", 0) + 1
            h = len(prompts) // 2
            return self.generate(prompts[:h], max_tokens, temp, adapter, stops) + self.generate(prompts[h:], max_tokens, temp, adapter, stops)
        finally:
            if self.device == "mps":
                self.torch.mps.empty_cache()

    def _generate(self, prompts, max_tokens, temp=0.0, adapter=True, stops=()):
        t = self.torch
        self.model.eval()
        eos = [self.stop_id]
        for s in stops:
            tid = self.tok.convert_tokens_to_ids(s) if s else None
            if isinstance(tid, int) and tid >= 0 and tid != self.tok.unk_token_id:
                eos.append(tid)
        enc = self.tok(list(prompts), add_special_tokens=False, return_tensors="pt", padding=True).to(self.device)
        kw = dict(do_sample=True, temperature=temp, top_p=0.95, top_k=0) if temp > 0 else dict(do_sample=False)
        ctx = self.model.disable_adapter() if not adapter else _null()
        with t.no_grad(), ctx, self._autocast():
            out = self.model.generate(**enc, max_new_tokens=max_tokens, eos_token_id=eos, pad_token_id=self.tok.pad_token_id, **kw)
        res = []
        for row in out[:, enc["input_ids"].shape[1]:]:
            txt = self.tok.decode(row, skip_special_tokens=False)
            cut = len(txt)
            for s in list(stops) + [self.prof.stop_token]:
                if s and s in txt:
                    cut = min(cut, txt.index(s))
            res.append(txt[:cut].replace(self.tok.pad_token or "", "").strip())
        return res

    # ---- training
    def _arrays(self, mb: Sequence[Example]):
        t = self.torch
        L = max(len(e[0]) for e in mb)
        ids = t.full((len(mb), L), self.stop_id, dtype=t.long)
        att = t.zeros((len(mb), L), dtype=t.long)
        bi, ti, tgt = [], [], []
        for r, (x, ls) in enumerate(mb):
            ids[r, :len(x)] = t.tensor(x)
            att[r, :len(x)] = 1
            for p in range(max(ls, 1), len(x)):
                bi.append(r)
                ti.append(p - 1)
                tgt.append(x[p])
        d = self.device
        return ids.to(d), att.to(d), t.tensor(bi, device=d), t.tensor(ti, device=d), t.tensor(tgt, device=d)

    def _logits(self, ids, att, bi, ti):
        body = getattr(self.lm, "model", None) or self.lm.get_decoder()
        with self._autocast():
            h = body(input_ids=ids[:, :-1], attention_mask=att[:, :-1]).last_hidden_state
            lg = self.lm.get_output_embeddings()(h[bi, ti])
        return lg.float()

    def train_begin(self, total_steps, lr):
        self.opt = self.torch.optim.AdamW(self.params, lr=lr, weight_decay=0.0)
        self.total, self.lr0 = max(total_steps, 1), lr

    def train_step(self, batch, replay, step, update: bool = True):
        """Out of memory: free the cache, halve tok_budget (smaller microbatches, same gradient) and redo the step, down to 64 tokens."""
        while True:
            try:
                return self._train_step(batch, replay, step, update)
            except RuntimeError as e:
                if not is_oom(e) or self.tok_budget <= 64:
                    raise
                if self.opt is not None:
                    self.opt.zero_grad(set_to_none=True)
                else:
                    self.model.zero_grad(set_to_none=True)
                self.free()
                self.tok_budget = max(64, self.tok_budget // 2)
                self.oom_events = getattr(self, "oom_events", 0) + 1
            finally:
                if self.device == "mps":
                    self.torch.mps.empty_cache()

    def _train_step(self, batch, replay, step, update: bool = True):
        import torch.nn.functional as F
        t = self.torch
        self.model.train()
        if self.opt is not None:
            self.opt.zero_grad(set_to_none=True)
            for g in self.opt.param_groups:
                g["lr"] = self.lr0 * 0.5 * (1 + math.cos(math.pi * step / self.total))
        denom = max(sum(max(len(e[0]) - max(e[1], 1), 0) for e in batch), 1)
        ce = 0.0
        for mb in pack(batch, self.tok_budget):
            ids, att, bi, ti, tgt = self._arrays(mb)
            loss = F.cross_entropy(self._logits(ids, att, bi, ti), tgt, reduction="sum") / denom
            loss.backward()
            ce += float(loss.detach())
        kl = 0.0
        rdenom = max(sum(max(len(e[0]) - 1, 0) for e in replay), 1)
        for mb in pack(replay, self.tok_budget):
            ids, att, bi, ti, tgt = self._arrays(mb)
            with t.no_grad(), self.model.disable_adapter():
                ref = F.log_softmax(self._logits(ids, att, bi, ti), -1)
            cur = F.log_softmax(self._logits(ids, att, bi, ti), -1)
            part = F.kl_div(cur, ref, log_target=True, reduction="sum") / rdenom
            part.backward()
            kl += float(part.detach())
        if update:
            t.nn.utils.clip_grad_norm_(self.params, 1.0)
            self.opt.step()
        self.model.eval()
        return {"ce": ce, "kl": kl}

    # ---- adapter (PEFT format)
    def save_adapter(self, path) -> None:
        from .checkpoint import save_adapter_directory
        save_adapter_directory(path, lambda tmp: self.model.save_pretrained(str(tmp)))

    def load_adapter(self, path) -> None:
        if path is not None:
            from .checkpoint import validate_adapter
            validate_adapter(path)
        t = self.torch
        if path is None:
            with t.no_grad():
                for n, p in self.model.named_parameters():
                    if "lora_B" in n:
                        p.zero_()
            return
        from peft import set_peft_model_state_dict
        f = Path(path) / "adapter_model.safetensors"
        if f.exists():
            from safetensors.torch import load_file
            sd = load_file(str(f))
        else:
            sd = t.load(str(Path(path) / "adapter_model.bin"), map_location="cpu")
        set_peft_model_state_dict(self.model, sd)

    def downscale(self, factor, thresh, seed):
        import numpy as np
        t = self.torch
        rng = np.random.default_rng(seed)
        nz = nsv = n_mod = 0
        e0 = e1 = 0.0
        with t.no_grad():
            for m in self.model.modules():
                if hasattr(m, "lora_A") and hasattr(m, "lora_B") and "default" in m.lora_A:
                    A, B = m.lora_A["default"].weight, m.lora_B["default"].weight      # (r, in), (out, r)
                    a, b = A.detach().float().cpu().numpy().T, B.detach().float().cpu().numpy().T
                    a2, b2, z, n, ea, eb = shy_core(a, b, float(m.scaling["default"]), factor, thresh, rng)
                    A.copy_(t.from_numpy(np.ascontiguousarray(a2.T)).to(A.device, A.dtype))
                    B.copy_(t.from_numpy(np.ascontiguousarray(b2.T)).to(B.device, B.dtype))
                    nz, nsv, e0, e1, n_mod = nz + z, nsv + n, e0 + ea, e1 + eb, n_mod + 1
        return {"modules": n_mod, "sv_total": nsv, "sv_zeroed": nz, "zeroed_frac": nz / max(nsv, 1), "energy_ratio": e1 / max(e0, 1e-12)}

    def bench(self) -> Tuple[float, float]:
        base = self.encode("The quick brown fox jumps over the lazy dog near the old harbour, where Marta works. ")
        ex = (base * (128 // len(base) + 1))[:128]
        batch, rep = [(ex, 64)] * getattr(self, "bench_bsz", 16), [(ex[:64], 0)] * getattr(self, "bench_rep", 8)
        self.train_begin(1, 0.0)
        self.train_step(batch, rep, 0, update=False)
        t0 = time.time()
        self.train_step(batch, rep, 0, update=False)
        t_step = time.time() - t0
        self.generate(["Where does Marta work?"], 2)
        t0 = time.time()
        self.generate(["Where does Marta work? " * 8] * self.gen_batch, 20)
        return t_step, time.time() - t0

    def close(self) -> None:
        self.free()


class _null:
    def __enter__(self): return None
    def __exit__(self, *a): return False
