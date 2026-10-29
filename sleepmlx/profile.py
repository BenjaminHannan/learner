"""Model profiles: everything that differs between K2-Horizon, LFM3 and any later small model.

A profile is a JSON file (sleepmlx/profiles/<name>.json, or any path) with the model dir, the loader, the chat template,
the think / no-think markers, the stop token, the LoRA target keys and the per-model parsing quirks.
Default profile: k2 (env SLEEPMLX_PROFILE or --profile to change).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
DEFAULT_PROFILE = "lfm3"   # an alias, resolved per platform by resolve_profile_name

DEFAULT_QUIRKS = {
    "tag_think": False,          # the tagger thinks first (stage 1) before answering
    "names_think": False,        # same for the names pass
    "think_tokens": 512,         # stage-1 thinking cap
    "negative_word_parse": False,  # a reply starting with not / none / nothing / nope / unrelated means "no"
    "rem_chain_mode": "q",       # default | q | think | q_think (sleepb addendum 14)
    "rem_think_tokens": 512,
}


@dataclass
class Profile:
    name: str = "k2"
    model_dir: str = ""                   # local dir (MLX: the 4-bit MLX model; torch: a HF snapshot dir, or leave "" and set hf_id)
    hf_id: Optional[str] = None           # HF repo id for the torch backend (used when model_dir is empty or missing)
    source_revision: Optional[str] = None # pinned upstream revision used to provision a local quantized model
    backend: str = "auto"                 # "mlx" | "torch" | "auto" (mlx if importable, else torch)
    loader: Optional[str] = None          # "module:function"; None = mlx_lm.load
    loader_path: Optional[str] = None     # directory (or .py file's directory) put on sys.path before importing the loader
    trust_remote_code: bool = True
    template_mode: str = "tokenizer"      # "tokenizer": tok.apply_chat_template; "manual": the strings below
    template: Dict[str, str] = field(default_factory=dict)
    nothink_suffix: str = ""
    think_open: str = ""
    think_close: str = ""
    stop_token: str = ""
    training_answer_prefix: str = ""      # supervised transition from an open native reasoning prompt to its answer
    lora: Dict[str, Any] = field(default_factory=dict)
    quirks: Dict[str, Any] = field(default_factory=dict)
    recipe: Dict[str, Any] = field(default_factory=dict)    # overrides of recipe.Config fields (bsz, replay_bsz, kl_every, gate_n, ...)
    runtime: Dict[str, Any] = field(default_factory=dict)   # tok_budget, grad_ckpt, gen_batch, threads, min_free_ram_gb, mem_limit, cache_limit

    def quirk(self, name: str):
        return self.quirks.get(name, DEFAULT_QUIRKS[name])

    @property
    def thinks(self) -> bool:
        return bool(self.think_open and self.think_close)

    @property
    def expanded_model_dir(self) -> str:
        return os.path.expanduser(self.model_dir)


def has_cuda() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_profile_name(name: str, platform: Optional[str] = None, cuda: Optional[bool] = None) -> str:
    """'lfm3' is the default alias: lfm3_mps on macOS, lfm3_cuda with a CUDA card on Windows / Linux, else lfm3_cpu. Any other name is returned unchanged."""
    if name != "lfm3":
        return name
    platform = sys.platform if platform is None else platform
    if platform == "darwin":
        return "lfm3_mps"
    return "lfm3_cuda" if (has_cuda() if cuda is None else cuda) else "lfm3_cpu"


def profile_path(name_or_path: str) -> Path:
    p = Path(os.path.expanduser(name_or_path))
    if p.suffix == ".json" and p.exists():
        return p
    q = PROFILE_DIR / (name_or_path + ".json")
    if q.exists():
        return q
    raise FileNotFoundError("no profile %r (looked for %s and %s)" % (name_or_path, p, q))


def from_dict(d: dict) -> Profile:
    known = set(Profile.__dataclass_fields__)
    return Profile(**{k: v for k, v in d.items() if k in known})


def load_profile(name_or_path: Optional[str] = None, env: Optional[dict] = None) -> Profile:
    """Load a profile; env overrides: SLEEPMLX_MODEL_DIR, SLEEPMLX_LOADER ('module:function'), SLEEPMLX_LOADER_PATH."""
    env = os.environ if env is None else env
    name = name_or_path or env.get("SLEEPMLX_PROFILE") or DEFAULT_PROFILE
    prof = from_dict(json.loads(profile_path(resolve_profile_name(name)).read_text()))
    if env.get("SLEEPMLX_MODEL_DIR"):
        prof.model_dir = env["SLEEPMLX_MODEL_DIR"]
    if env.get("SLEEPMLX_HF_ID"):
        prof.hf_id = env["SLEEPMLX_HF_ID"]
    if env.get("SLEEPMLX_BACKEND_KIND"):
        prof.backend = env["SLEEPMLX_BACKEND_KIND"]
    if env.get("SLEEPMLX_LOADER"):
        prof.loader = env["SLEEPMLX_LOADER"]
    if env.get("SLEEPMLX_LOADER_PATH"):
        prof.loader_path = env["SLEEPMLX_LOADER_PATH"]
    return prof


class Renderer:
    """Builds prompt strings. render: no-think prompt. render_think: the think block left open."""

    def __init__(self, prof: Profile, tokenizer=None):
        self.p, self.tok = prof, tokenizer

    def _msgs(self, system: str, user: str) -> List[dict]:
        return ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]

    def _base(self, system: str, user: str) -> str:
        p = self.p
        if p.template_mode == "tokenizer" and self.tok is not None:
            return self.tok.apply_chat_template(self._msgs(system, user), tokenize=False, add_generation_prompt=True)
        t = p.template
        out = ""
        if system:
            out += t.get("system", "system: {content}\n").format(content=system)
        out += t.get("user", "user: {content}\n").format(content=user)
        return out + t.get("assistant_open", "assistant: ")

    def _open_tail(self, t: str) -> Optional[str]:
        """If t ends with the think-open marker (ignoring trailing whitespace), t with the marker exactly as the profile writes it; else None."""
        p = self.p
        to = p.think_open.rstrip()
        if to and t.rstrip().endswith(to):
            return t.rstrip() + p.think_open[len(to):]
        return None

    def render(self, system: str, user: str) -> str:
        t = self._base(system, user)
        p = self.p
        if p.quirks.get("native_generation_prompt", False):
            if p.thinks and self._open_tail(t) is None:
                raise ValueError("profile %s requires its native tokenizer generation prompt ending in %s" % (p.name, p.think_open))
            return t
        if p.thinks:
            o = self._open_tail(t)          # the template normally ends with the think-open marker; thinking off = close it at once
            if o is not None:
                return o + p.think_close
            if not t.endswith(p.nothink_suffix):
                return t + p.nothink_suffix
        elif p.nothink_suffix and not t.endswith(p.nothink_suffix):
            t += p.nothink_suffix
        return t

    def render_think(self, system: str, user: str) -> str:
        if not self.p.thinks:
            raise ValueError("profile %s has no think block" % self.p.name)
        t = self._base(system, user)
        o = self._open_tail(t)
        return o if o is not None else t + self.p.think_open


def generated_answer(prof: Profile, prompt: str, text: str) -> str:
    """Expose answers, never incomplete reasoning, for native reasoning profiles."""
    if (prof.quirks.get("strip_generated_thinking", False) and prof.thinks
            and prompt.rstrip().endswith(prof.think_open.rstrip())):
        _, close, answer = text.partition(prof.think_close)
        return answer.strip() if close else ""
    return text
