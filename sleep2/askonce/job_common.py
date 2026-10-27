"""Shared setup for the two Kaggle jobs (and their CPU smoke versions)."""
import json
import os
import sys
import time
from pathlib import Path

import torch

from .config import DATA, MODEL_ID, jdump, jload


class Logger:
    def __init__(self, path):
        self.path, self.t0 = Path(path), time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, *a):
        s = f"[{(time.time() - self.t0) / 60:6.1f}m] " + " ".join(str(x) for x in a)
        print(s, flush=True)
        with open(self.path, "a") as f:
            f.write(s + "\n")


def env_info():
    info = {"torch": torch.__version__, "cuda": torch.cuda.is_available()}
    try:
        import transformers
        import peft
        info.update(transformers=transformers.__version__, peft=peft.__version__)
    except Exception:
        pass
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["gpu_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2 ** 30, 1)
    info["scale"] = os.environ.get("ASKONCE_SCALE", "1.0")
    info["cuda_visible"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    return info


def device_dtype():
    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def add_hf_token_note():
    """Nothing secret is used: the model repo is public. (No API keys are ever read in the GPU jobs.)"""
    for k in ("LEARNER_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"):
        assert k not in os.environ or not os.environ[k], f"{k} must not be set in a GPU job"


def assert_finite_forward(model, tok, log=print, text="You are Ben's assistant. Which Sam do you mean?"):
    """One forward pass in the job's dtype: non-finite logits (fp16 overflow of a bf16-trained checkpoint) must stop the job before anything is written."""
    ids = tok(text, return_tensors="pt", add_special_tokens=True).input_ids.to(next(model.parameters()).device)
    with torch.no_grad():
        logits = model(input_ids=ids, use_cache=False).logits
    if not torch.isfinite(logits.float()).all():
        raise FloatingPointError(f"non-finite logits from one forward pass in {next(model.parameters()).dtype}; the checkpoint overflows in this dtype")
    log("forward check ok", f"dtype={next(model.parameters()).dtype}", f"max|logit|={logits.float().abs().max().item():.1f}")
