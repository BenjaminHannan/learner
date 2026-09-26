#!/usr/bin/env python3
"""k1h: the LFM creative writer, taught from GLM's answers (Creative answers in chat thread, 2026-09-26). One change on
k1f.

Why (the Thread manager, 19:33 UTC, "obvious fix first"): the textbook fix for a small model that writes weak answers
is to teach it from a stronger teacher's answers (distillation / instruction tuning), and it had never been tried here:
k1c, k1d and k1e worked on picking among the writer's drafts. Brain picture (textbook-level; the mapping to our parts
is a guess): songbirds and children first copy a tutor, then refine with reward.

What: install_creative_k1h(loop, gen) is claude_k1f_cre.install_creative_k1f with one change: the writer's model (the
LFM2.5-1.2B-Instruct snapshot named by K1F_WRITER_MODEL, as in k1f) carries a LoRA adapter trained by
scripts/claude_k1h_train.py on GLM's answers to practice chats. The adapter folder is named by env K1H_WRITER_ADAPTER,
and the sha256 of its adapter_model.safetensors must equal env K1H_ADAPTER_SHA256 (both required); it is merged into
the writer's weights once per process. Everything else is k1f's: routing (is_creative333c, a hand-written regex in the
build since 0.2c, disclosed test scaffolding), the prompt, Gen338's sampling (4 samples, temperature 0.7, top_p 0.9,
200 new tokens, thinking off), trim, guard333d, FALLBACK, counters, the WORK entry, no notebook writes, and the rest of
the build on MiniCPM5-1B with the 0.2c sleep adapter.

build_null_k1h(state_dir, args) = the k1f swap around claude_mu402.build_null02c with install_creative_k1h in place of
install_creative333d. It prints one line, "k1h: creative writer = install_creative_k1h; writer = <model_type>
@<snapshot> + adapter <sha8>; layers = [...]", for the V1 check.

Practice prompts (not a test arm): build_null_k1f_prompts(state_dir, args) is claude_k1f_cre.build_null_k1f unchanged,
with the writer's gen wrapped in PromptLog when env K1H_PROMPTS names a file: a pass-through that returns the same
drafts and appends the exact messages the writer was given ({"dir", "request", "msgs"}). Run over the practice chats
it gives, for each chat's last request, the writer's exact prompt (the build's own replies to the earlier messages
included), which claude_k1h_train.py pairs with GLM's answer. New file only.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_cre333b_agent as CB      # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402
import claude_k1a_cre as K1A           # noqa: E402
import claude_k1f_cre as K1F           # noqa: E402

ADAPTER_ENV = "K1H_WRITER_ADAPTER"
SHA_ENV = "K1H_ADAPTER_SHA256"
PROMPTS_ENV = "K1H_PROMPTS"
ADAPTER_FILE = "adapter_model.safetensors"
_PRINTED: list = []


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def adapter_checked() -> tuple[str, str]:
    """(adapter folder, sha256) after checking the file against $K1H_ADAPTER_SHA256."""
    d, want = os.environ.get(ADAPTER_ENV, ""), os.environ.get(SHA_ENV, "").lower()
    if not d or not want:
        raise SystemExit(f"k1h: set {ADAPTER_ENV} (the adapter folder) and {SHA_ENV}")
    got = sha256_file(Path(d) / ADAPTER_FILE)
    if got != want:
        raise RuntimeError(f"k1h: refusing to load the adapter: sha256 {got[:12]} is not {want[:12]}")
    return d, got


def load_adapted(model_dir: str, base=None, peft_load=None):
    """The writer's Gen333b with the checked adapter merged into its weights (once)."""
    d, sha = adapter_checked()
    one = (base or CB.Gen333b)(model_dir)
    if peft_load is None:
        from peft import PeftModel
        peft_load = PeftModel.from_pretrained
    m = peft_load(one.model, d)
    one.model = m.merge_and_unload().eval()
    one.k1h_adapter = sha
    return one


def writer_name() -> str:
    g = getattr(K1F._GEN.get(os.environ.get(K1F.WRITER_ENV, "")), "g", None)
    sha = getattr(g, "k1h_adapter", None) or os.environ.get(SHA_ENV, "?").lower()
    return f"{K1F.writer_name()} + adapter {sha[:8]}"


def install_creative_k1h(loop, gen=None, n: int = CD.N333D) -> None:
    """k1f's writer with the adapted LFM gen. `gen` (the build's MiniCPM5-1B Gen338) is ignored for creative turns."""
    K1A.install_creative_k1a(loop, K1F._logged(K1F.writer_gen(load=load_adapted), loop), n)
    loop.k1h_writer = writer_name()


def _swapped(build, state_dir, args):
    old = CD.install_creative333d
    CD.install_creative333d = install_creative_k1h
    try:
        loop = build(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [("cre_k1h" if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1h: creative writer = install_creative_k1h; writer = {writer_name()}; layers = {loop.layers330c}",
              flush=True)
    return loop


def build_null_k1h(state_dir, args):
    import claude_mu402 as MU
    return _swapped(MU.build_null02c, state_dir, args)


class PromptLog:
    """Pass-through around a writer gen: the same drafts come back; the messages it was given are appended to `path`."""

    def __init__(self, gen, loop, path: str):
        self.gen, self.loop, self.path = gen, loop, path

    def sample_chat(self, msgs, n):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"dir": Path(self.loop.dir).name, "request": msgs[-1]["content"],
                                 "msgs": [{"role": m["role"], "content": m["content"]} for m in msgs]},
                                ensure_ascii=False) + "\n")
        return self.gen.sample_chat(msgs, n)


def build_null_k1f_prompts(state_dir, args):
    """claude_k1f_cre.build_null_k1f with the writer's gen wrapped in PromptLog ($K1H_PROMPTS required)."""
    p = os.environ.get(PROMPTS_ENV, "")
    if not p:
        raise SystemExit(f"k1h: set {PROMPTS_ENV} to the prompt log file")
    real = K1F._logged

    def logged(gen, loop):
        return PromptLog(real(gen, loop), loop, p)
    K1F._logged = logged
    try:
        loop = K1F.build_null_k1f(state_dir, args)
    finally:
        K1F._logged = real
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1h-prompts: the k1f build, writer prompts logged to {Path(p).name}", flush=True)
    return loop
