"""MLX backend (untested until the Mac run). Imports mlx lazily so the package imports on Linux.

load(model_dir, loader=None): mlx_lm.load, or a custom "module:function" loader returning (model, tokenizer).
MLXBackend: LoRA via mlx_lm.tuner.utils.linear_to_lora_layers, loss only at target positions, KL to the base by setting the LoRA scale to 0,
batched generation with mlx_lm.generate.batch_generate, SHY downscale in numpy, adapter save/load in mlx_lm's format.
"""
from __future__ import annotations

import importlib
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .backend import Backend, Example


def adapter_base_identity(prof, model_dir):
    """Portable source identity plus the exact local quantization config."""
    local = Path(os.path.expanduser(model_dir)).resolve()
    config = local / "config.json"
    return {"hf_id": prof.hf_id, "source_revision": prof.source_revision,
            "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest() if config.is_file() else None,
            "model_dir": str(local)}


def validate_adapter_base(path, prof, model_dir):
    """Reusable by a chat launcher before mlx_lm.server --adapter-path."""
    record = json.loads((Path(path) / "adapter_config.json").read_text()).get("sleepmlx_base")
    if record is None:
        if prof.quirks.get("require_adapter_identity", False):
            raise ValueError("adapter has no recorded base model identity")
        return
    expected = adapter_base_identity(prof, model_dir)
    keys = ["hf_id", "source_revision", "config_sha256"]
    if not expected["hf_id"] or not expected["source_revision"]:
        keys.append("model_dir")
    if not isinstance(record, dict) or any(record.get(key) != expected[key] for key in keys):
        raise ValueError("adapter base model identity does not match the active model")


def load(model_dir: str, loader: Optional[str] = None, loader_path: Optional[str] = None, trust_remote_code: bool = True):
    """-> (model, tokenizer). loader: 'module:function' called as function(model_dir) -> (model, tokenizer[, ...]); loader_path is put on sys.path first
    (e.g. the folder holding the bench file, or the model dir itself). Default: mlx_lm.load."""
    model_dir = os.path.expanduser(model_dir)
    if loader:
        mod, _, fn = loader.partition(":")
        if loader_path:
            p = os.path.expanduser(loader_path)
            sys.path.insert(0, p if os.path.isdir(p) else os.path.dirname(p))
        f = getattr(importlib.import_module(mod), fn or "load")
        out = f(model_dir)
        return out[0], out[1]
    from mlx_lm import load as mlx_load
    try:
        out = mlx_load(model_dir, trust_remote_code=trust_remote_code)
    except TypeError:
        out = mlx_load(model_dir, tokenizer_config={"trust_remote_code": trust_remote_code})
    return out[0], out[1]


def _mx():
    import mlx.core as mx
    return mx


def set_memory_caps(limit_bytes: float, cache_bytes: float) -> None:
    mx = _mx()
    for name, val in (("set_memory_limit", limit_bytes), ("set_cache_limit", cache_bytes)):
        f = getattr(mx, name, None) or getattr(getattr(mx, "metal", None), name, None)
        if f:
            f(int(val))


def peak_gb() -> float:
    mx = _mx()
    f = getattr(mx, "get_peak_memory", None) or getattr(mx.metal, "get_peak_memory")
    return f() / 1e9


def clear_cache() -> None:
    mx = _mx()
    f = getattr(mx, "clear_cache", None) or getattr(mx.metal, "clear_cache", None)
    if f:
        f()


def pack(batch: Sequence[Example], budget: int) -> List[List[Example]]:
    """Micro-batches whose padded size (rows x longest row) stays within budget; an example over budget gets its own."""
    out: List[List[Example]] = []
    cur: List[Example] = []
    mx_len = 0
    for ex in sorted(batch, key=lambda e: -len(e[0])):
        n = len(ex[0])
        if cur and (len(cur) + 1) * max(mx_len, n) > budget:
            out.append(cur)
            cur, mx_len = [], 0
        cur.append(ex)
        mx_len = max(mx_len, n)
    if cur:
        out.append(cur)
    return out


class MLXBackend(Backend):
    def __init__(self, model, tok, prof, model_dir: str = "", tok_budget: int = 256, grad_ckpt: bool = True, gen_batch: int = 8,
                 mem_limit: float = 5e9, cache_limit: float = 0.5e9):
        import mlx.nn as nn
        from mlx_lm.tuner.utils import linear_to_lora_layers
        set_memory_caps(mem_limit, cache_limit)
        self.model, self.tok, self.prof, self.model_dir = model, tok, prof, model_dir
        self.tok_budget, self.gen_batch = tok_budget, gen_batch
        self.lora_cfg = dict(prof.lora)
        self.n_layers = len(model.layers)
        model.freeze()
        linear_to_lora_layers(model, self.n_layers, {"rank": self.lora_cfg["rank"], "scale": self.lora_cfg["scale"],
                                                       "dropout": self.lora_cfg.get("dropout", 0.0), "keys": self.lora_cfg["keys"]})
        if grad_ckpt:
            from mlx_lm.tuner.trainer import grad_checkpoint
            grad_checkpoint(model.layers[0])
        self.stop_id = tok.convert_tokens_to_ids(prof.stop_token) if prof.stop_token else tok.eos_token_id
        self._lora = [m for _, m in model.named_modules() if hasattr(m, "lora_a") and hasattr(m, "lora_b")]
        self._scale = float(self.lora_cfg["scale"])
        self._ce_vg = nn.value_and_grad(model, self._ce_fn)
        self._kl_vg = nn.value_and_grad(model, self._kl_fn)
        self.opt = None
        self.total, self.lr0 = 1, 2e-4

    # ---- tokens
    def encode(self, text: str) -> List[int]:
        try:
            return list(self.tok.encode(text, add_special_tokens=False))
        except TypeError:
            return list(self.tok.encode(text))

    def _set_scale(self, s: float) -> None:
        for m in self._lora:
            m.scale = s

    # ---- generation
    def generate(self, prompts, max_tokens, temp=0.0, adapter=True, stops=()):
        from mlx_lm.generate import batch_generate
        from mlx_lm.sample_utils import make_sampler
        self.model.eval()
        self._set_scale(self._scale if adapter else 0.0)
        sampler = make_sampler(temp=temp, top_p=0.95) if temp > 0 else make_sampler(temp=0.0)
        old = None
        added = []
        eos = getattr(self.tok, "eos_token_ids", None)
        if eos is not None and stops:   # best effort: end a reply at a stop tag that is a single token
            old = set(eos)
            for s in stops:
                tid = self.tok.convert_tokens_to_ids(s) if s else None
                if isinstance(tid, int) and tid >= 0:
                    added.append(tid)
            try:
                self.tok.eos_token_ids = old | set(added)
            except Exception:
                old = None
        try:
            resp = batch_generate(self.model, self.tok, [self.encode(p) for p in prompts], max_tokens=max_tokens, sampler=sampler, return_token_ids=True)
        finally:
            if old is not None:
                try:
                    self.tok.eos_token_ids = old
                except Exception:
                    pass
        ids = getattr(resp, "token_ids", None)
        outs = []
        for i in range(len(prompts)):
            if ids is not None:
                try:
                    t = self.tok.decode(list(ids[i]), skip_special_tokens=False)
                except TypeError:
                    t = self.tok.decode(list(ids[i]))
            else:
                t = resp.texts[i]
            cut = len(t)
            for s in list(stops) + [self.prof.stop_token]:
                if s and s in t:
                    cut = min(cut, t.index(s))
            from .profile import generated_answer
            outs.append(generated_answer(self.prof, prompts[i], t[:cut].strip()))
        clear_cache()
        return outs

    # ---- training
    def _head(self, h):
        return self._project_head(self.model, h)

    @staticmethod
    def _project_head(model, h):
        # Qwen3.5/3.6 wraps its untied output head in language_model. Its
        # outer .model property exposes the decoder, not the output head.
        m = getattr(model, "language_model", model)
        lm_head = getattr(m, "lm_head", None)
        return lm_head(h) if lm_head is not None else m.model.embed_tokens.as_linear(h)

    def _logits(self, model, ids, bi, ti):
        mx = _mx()
        h = model.model(ids[:, :-1])
        z = h[bi, ti]
        out = self._project_head(model, z)
        return out.astype(mx.float32)

    def _ce_fn(self, model, ids, bi, ti, tgt, denom):
        import mlx.nn as nn
        return nn.losses.cross_entropy(self._logits(model, ids, bi, ti), tgt, reduction="sum") / denom

    def _kl_fn(self, model, ids, bi, ti, ref_lp, denom):
        mx = _mx()
        lg = self._logits(model, ids, bi, ti)
        lp = lg - mx.logsumexp(lg, axis=-1, keepdims=True)
        return (mx.exp(ref_lp) * (ref_lp - lp)).sum() / denom

    def _arrays(self, mb: Sequence[Example]):
        mx = _mx()
        L = max(len(e[0]) for e in mb)
        rows = [list(e[0]) + [self.stop_id] * (L - len(e[0])) for e in mb]
        bi, ti, tgt = [], [], []
        for r, (ids, ls) in enumerate(mb):
            for t in range(max(ls, 1), len(ids)):
                bi.append(r)
                ti.append(t - 1)
                tgt.append(ids[t])
        return mx.array(rows), mx.array(bi), mx.array(ti), mx.array(tgt), len(tgt)

    def train_begin(self, total_steps, lr):
        import mlx.optimizers as optim
        self.opt = optim.AdamW(learning_rate=lr, weight_decay=0.0)
        self.total, self.lr0 = max(total_steps, 1), lr

    def train_step(self, batch, replay, step, update: bool = True):
        import mlx.optimizers as optim
        from mlx.utils import tree_map
        mx = _mx()
        self.model.train()
        self._set_scale(self._scale)
        denom = max(sum(max(len(e[0]) - max(e[1], 1), 0) for e in batch), 1)
        acc, ce = None, 0.0
        for mb in pack(batch, self.tok_budget):
            ids, bi, ti, tgt, _ = self._arrays(mb)
            loss, grads = self._ce_vg(self.model, ids, bi, ti, tgt, denom)
            acc = grads if acc is None else tree_map(lambda x, y: x + y, acc, grads)
            mx.eval(acc, loss)
            ce += float(loss)
        kl = 0.0
        rdenom = max(sum(max(len(e[0]) - max(e[1], 1), 0) for e in replay), 1)
        for mb in pack(replay, self.tok_budget):
            ids, bi, ti, tgt, _ = self._arrays(mb)
            self._set_scale(0.0)                      # LoRA scale 0 = the base model
            lg = self._logits(self.model, ids, bi, ti)
            ref_lp = mx.stop_gradient(lg - mx.logsumexp(lg, axis=-1, keepdims=True))
            mx.eval(ref_lp)
            self._set_scale(self._scale)
            loss, grads = self._kl_vg(self.model, ids, bi, ti, ref_lp, rdenom)
            acc = grads if acc is None else tree_map(lambda x, y: x + y, acc, grads)
            mx.eval(acc, loss)
            kl += float(loss)
        if update and acc is not None:
            acc, _ = optim.clip_grad_norm(acc, 1.0)
            self.opt.learning_rate = self.lr0 * 0.5 * (1 + math.cos(math.pi * step / self.total))
            self.opt.update(self.model, acc)
            mx.eval(self.model.parameters(), self.opt.state)
        clear_cache()
        return {"ce": ce, "kl": kl, "peak_gb": peak_gb()}

    # ---- adapter
    def save_adapter(self, path) -> None:
        from .checkpoint import save_adapter_directory
        from mlx.utils import tree_flatten
        mx = _mx()

        def write(tmp):
            mx.save_safetensors(str(tmp / "adapters.safetensors"), dict(tree_flatten(self.model.trainable_parameters())))
            (tmp / "adapter_config.json").write_text(json.dumps({
                "model": self.model_dir, "fine_tune_type": "lora", "num_layers": self.n_layers,
                "sleepmlx_base": adapter_base_identity(self.prof, self.model_dir),
                "lora_parameters": {"rank": self.lora_cfg["rank"], "scale": self.lora_cfg["scale"], "dropout": self.lora_cfg.get("dropout", 0.0), "keys": self.lora_cfg["keys"]}}, indent=1))
        save_adapter_directory(path, write)

    def load_adapter(self, path) -> None:
        if path is not None:
            from .checkpoint import validate_adapter
            validate_adapter(path)
            validate_adapter_base(path, self.prof, self.model_dir)
        mx = _mx()
        if path is None:
            for m in self._lora:                      # a fresh adapter: lora_b = 0, so the model equals the base
                m.lora_b = mx.zeros_like(m.lora_b)
            mx.eval(self.model.parameters())
            return
        self.model.load_weights(str(Path(path) / "adapters.safetensors"), strict=False)
        mx.eval(self.model.parameters())

    def downscale(self, factor, thresh, seed):
        import numpy as np
        from .shy import shy_core
        mx = _mx()
        rng = np.random.default_rng(seed)
        nz = nsv = 0
        e0 = e1 = 0.0
        for m in self._lora:
            a = np.array(m.lora_a.astype(mx.float32))
            b = np.array(m.lora_b.astype(mx.float32))
            a2, b2, z, n, ea, eb = shy_core(a, b, float(self._scale), factor, thresh, rng)
            m.lora_a = mx.array(a2).astype(m.lora_a.dtype)
            m.lora_b = mx.array(b2).astype(m.lora_b.dtype)
            nz, nsv, e0, e1 = nz + z, nsv + n, e0 + ea, e1 + eb
        mx.eval(self.model.parameters())
        return {"modules": len(self._lora), "sv_total": nsv, "sv_zeroed": nz, "zeroed_frac": nz / max(nsv, 1), "energy_ratio": e1 / max(e0, 1e-12)}

    def bench(self) -> Tuple[float, float]:
        """Seconds for one training-shaped step (no weight update) and one 20-token generation batch."""
        base = self.encode("The quick brown fox jumps over the lazy dog near the old harbour, where Marta works. ")
        ex = (base * (128 // len(base) + 1))[:128]
        batch = [(ex, 64)] * getattr(self, "bench_bsz", 16)
        rep = [(ex[:64], 0)] * getattr(self, "bench_rep", 8)
        self.train_begin(1, 0.0)
        self.train_step(batch, rep, 0, update=False)
        t0 = time.time()
        self.train_step(batch, rep, 0, update=False)
        t_step = time.time() - t0
        prompts = ["Where does Marta work? " * 8] * self.gen_batch
        self.generate(prompts[:1], 2)
        t0 = time.time()
        self.generate(prompts, 20)
        return t_step, time.time() - t0

    def close(self) -> None:
        clear_cache()
