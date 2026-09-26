#!/usr/bin/env python3
"""k1c: the creative writer picks the best of its 4 drafts, not the first that passes (Creative answers in chat
thread, 2026-09-26). One change on whichever creative writer is the base (0.2c's cre333d, or it with k1a and/or k1b).

Why: on the 40 DEV practice chats (artifacts/claude-k1a-dev-20260926, readable; claude_k1c_pilot.py) the k1a writer's
first passing draft was useful 12 times, but at least one of its 4 drafts was useful 26 times. Blind judges, two plus
a third on splits. Of five pick rules declared before they were scored, FP did best: 17 of 40 (10 drafts gained,
5 lost against the first draft).

What (FP): the writer draws the same 4 samples as its base (same generate call, same random draws), cleans each the
way the base does (trim, or k1b's keep-whole for a finished sample), runs the base's guards on each, and among the
samples that pass returns the one with
  1. the smallest form mismatch (claude_k1c_pilot.form_penalty: |list items - N| when the request asks for N things,
     |lines - L| for a limerick 5, haiku 3, couplet 2, four-line poem 4; else 0), then
  2. the largest pointwise information from the writer's own 1B: the mean over the reply's tokens of
     log p(token | the writer's prompt) - log p(token | the system line and an empty user message)
     (claude_k1c_pilot.reply_logp; no training, no sampling, no random draws), then
  3. the earliest draw.
Nothing else changes: routing, prompt, samples, guards, fallback when none passes, no notebook writes. Only the order
in which passing samples are considered changes, as with claude_pick403.PickGen (reorder only); it is done inside the
writer so that it also covers k1b's finished-sample path, which does not go through sample_chat.

Builders (each = the base's builder with the k1c writer swapped in for install_creative333d; NullReader harness of
claude_mu402.build_null02c): build_null_k1c_x (cre333d + FP), build_null_k1c_k (k1a + FP), build_null_k1c_b
(k1b + FP), build_null_k1c_kb (k1a + k1b + FP). The registered pair is fixed in PASSMARKS-k1c.md. New file only.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_chat338_agent as C38     # noqa: E402
import claude_cre333_agent as C        # noqa: E402
import claude_cre333b_agent as CB      # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402
import claude_k1a_cre as KA            # noqa: E402
import claude_k1b_cre as KB            # noqa: E402
import claude_k1c_pilot as PL          # noqa: E402

_PRINTED: list = []


def pmi_scores(gen, msgs: list[dict], texts: list[str]) -> list[float]:
    g = gen.g
    null = [{"role": "system", "content": CD.SYSTEM333D}, {"role": "user", "content": ""}]
    return [PL.reply_logp(g, gen, msgs, t) - PL.reply_logp(g, gen, null, t) for t in texts]


def write_k1c(gen, text: str, facts: str, hist: list[dict], stats: dict, whole: bool,
              n: int = CD.N333D) -> str | None:
    known = C38._words([text, facts] + [m["content"] for m in hist])
    system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
    msgs = [{"role": "system", "content": system}] + list(hist) + [{"role": "user", "content": text}]
    if whole:
        cands = []
        for c, fin in KB.sample_chat_fin(gen, msgs, n):
            cands.append(KB.strip_only(c) if fin else C38.trim(c))
            stats["kept_whole" if fin else "trimmed"] = stats.get("kept_whole" if fin else "trimmed", 0) + 1
    else:
        cands = [C38.trim(c) for c in gen.sample_chat(msgs, n)]
    ok = []
    for i, c in enumerate(cands):
        gd = CD.guard333d(c, text, known)
        if gd is None:
            ok.append(i)
        else:
            stats[gd] = stats.get(gd, 0) + 1
    if not ok:
        return None
    form = [PL.form_penalty(text, cands[i]) for i in ok]
    pmi = pmi_scores(gen, msgs, [cands[i] for i in ok]) if len(ok) > 1 else [0.0]
    j = min(range(len(ok)), key=lambda k: (form[k], -pmi[k], k))
    stats["picked_not_first"] = stats.get("picked_not_first", 0) + int(j != 0)
    stats["picked_by_form"] = stats.get("picked_by_form", 0) + int(form[j] < form[0])
    return cands[ok[j]]


def install_creative_k1c(loop, gen, n: int = CD.N333D, use_hist: bool = True, whole: bool = True) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0, "G1": 0, "G2": 0, "G3": 0,
                         "G4": 0, "G5": 0, "hist_msgs": 0, "kept_whole": 0, "trimmed": 0, "picked_not_first": 0,
                         "picked_by_form": 0}

    def turn_k1c(text: str) -> list[str]:
        if not CB.is_creative333c(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        hist = KA.chat_history(loop) if use_hist else []
        loop.cre333_stats["hist_msgs"] += len(hist)
        reply = write_k1c(gen, text, facts, hist, loop.cre333_stats, whole, n)
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative_k1c",
                                "n": n, "context_facts": len(ctx), "hist_msgs": len(hist)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("k1c: creative turn wrote to the notebook")
        return [reply]

    turn_k1c.__name__ = "turn_k1c"
    loop.turn = turn_k1c


def _build(state_dir, args, use_hist: bool, whole: bool, tag: str):
    import claude_mu402 as MU
    old = CD.install_creative333d

    def inst(loop, gen, n=CD.N333D):
        return install_creative_k1c(loop, gen, n, use_hist=use_hist, whole=whole)
    CD.install_creative333d = inst
    try:
        loop = MU.build_null02c(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [(tag if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1c: creative writer = install_creative_k1c(use_hist={use_hist}, whole={whole}); "
              f"layers = {loop.layers330c}", flush=True)
    return loop


def build_null_k1c_x(state_dir, args):
    return _build(state_dir, args, False, False, "cre_k1c_x")


def build_null_k1c_k(state_dir, args):
    return _build(state_dir, args, True, False, "cre_k1c_k")


def build_null_k1c_b(state_dir, args):
    return _build(state_dir, args, False, True, "cre_k1c_b")


def build_null_k1c_kb(state_dir, args):
    return _build(state_dir, args, True, True, "cre_k1c_kb")
