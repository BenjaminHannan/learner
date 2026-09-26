#!/usr/bin/env python3
"""k1f: LFM2.5-1.2B-Instruct writes the creative replies (Creative answers in chat thread, 2026-09-26). One change on
k1a.

Why: k1c (artifacts/claude-k1c-20260926/VERIFY-k1c.md, blind judges and recount) found that on the same plain recipe
(the twin's system line, the whole chat, thinking off, greedy, <= 160 new tokens) plain MiniCPM5-1B was useful on 46
of 160 creative requests, plain LFM2.5-1.2B-Instruct on 103 and plain Qwen3.5-2B on 114, while the k1a writer (46) and
the 1B picking among its own drafts (47) stayed level with plain MiniCPM5-1B. The drafts, not the choice among them,
are the limit, so the model that writes them is the thing to change. LFM2.5-1.2B is the same-size option (Qwen is 2B).

What: install_creative_k1f(loop, gen) is claude_k1a_cre.install_creative_k1a with one change: the writer's model is
the LFM2.5-1.2B-Instruct snapshot named by env K1F_WRITER_MODEL (required; loaded once per process, with no sleep
adapter), not the build's MiniCPM5-1B. The gen passed in by build_02c is not used for creative turns. Unchanged:
routing (is_creative333c), the prompt (SYSTEM333D + the notebook facts, then the chat's last 12 messages, then the
request), Gen338's sampling (4 samples, temperature 0.7, top_p 0.9, 200 new tokens, thinking off), trim, guard333d
(140 words, refusals, memory claims, unknown relatives' names), the FALLBACK line, counters, the WORK entry and no
notebook writes. Everything else in the build (reader, routing, chat, think, answer paths, the sleep adapter) stays
on MiniCPM5-1B.

build_null_k1f(state_dir, args) = the k1a swap around claude_mu402.build_null02c (NullReader, per-turn seeds from
(turn number, text), the same seeds for every arm), with install_creative_k1f in place of install_creative333d, so the
k1f arm differs from the k1a arm (claude_k1a_cre.build_null_k1a) by the writer's model only. It prints one line,
"k1f: creative writer = install_creative_k1f; writer = <model_type> @<snapshot>; layers = [...]", for the rental's
V1 check. build_k1f wraps claude_e2e02c.build_02c the same way. New file only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_chat338_agent as C38     # noqa: E402
import claude_cre333b_agent as CB      # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402
import claude_k1a_cre as K1A           # noqa: E402

WRITER_ENV = "K1F_WRITER_MODEL"
_GEN: dict = {}
_PRINTED: list = []


def writer_gen(load=None):
    """The LFM writer as a Gen338 (the same sampling k1a uses), loaded once per process from $K1F_WRITER_MODEL."""
    d = os.environ.get(WRITER_ENV, "")
    if not d:
        raise SystemExit(f"k1f: set {WRITER_ENV} to the LFM2.5-1.2B-Instruct snapshot directory")
    if d not in _GEN:
        one = (load or CB.Gen333b)(d)
        if getattr(one, "sleep02c", False):
            raise RuntimeError("k1f: the writer model carries the sleep adapter; it must be the plain LFM")
        _GEN[d] = C38.Gen338(share=one)
    return _GEN[d]


def writer_name() -> str:
    d = os.environ.get(WRITER_ENV, "")
    g = _GEN.get(d)
    mt = getattr(getattr(getattr(g, "g", None), "model", None), "config", None)
    mt = getattr(mt, "model_type", "?")
    return f"{mt} @{Path(d).name[:8]}"


def install_creative_k1f(loop, gen=None, n: int = CD.N333D) -> None:
    """k1a's writer on the LFM gen. `gen` (the build's MiniCPM5-1B Gen338) is ignored for creative turns."""
    K1A.install_creative_k1a(loop, writer_gen(), n)
    loop.k1f_writer = writer_name()


def _swapped(build, state_dir, args):
    old = CD.install_creative333d
    CD.install_creative333d = install_creative_k1f
    try:
        loop = build(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [("cre_k1f" if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1f: creative writer = install_creative_k1f; writer = {writer_name()}; layers = {loop.layers330c}",
              flush=True)
    return loop


def build_k1f(state_dir, args):
    import claude_e2e02c as E02C
    return _swapped(E02C.build_02c, state_dir, args)


def build_null_k1f(state_dir, args):
    import claude_mu402 as MU
    return _swapped(MU.build_null02c, state_dir, args)
