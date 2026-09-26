#!/usr/bin/env python3
"""k1ab: k1a and k1b together (Creative answers in chat thread, 2026-09-26). REPORT-ONLY arm, not a change of its
own: it shows what the creative writer does with both single changes on, for Month-end's next build and for K1's
bar. The writer sees the chat (claude_k1a_cre, same history and known words) and keeps a reply that ended on its
own whole (claude_k1b_cre, same generate call). New file only.

build_null_k1ab = the swap around claude_mu402.build_null02c (NullReader + per-turn seeds), like k1a and k1b.
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

_PRINTED: list = []


def write_k1ab(gen, text: str, facts: str, hist: list[dict], stats: dict, n: int = CD.N333D) -> str | None:
    known = C38._words([text, facts] + [m["content"] for m in hist])
    system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
    msgs = [{"role": "system", "content": system}] + list(hist) + [{"role": "user", "content": text}]
    for c, fin in KB.sample_chat_fin(gen, msgs, n):
        c = KB.strip_only(c) if fin else C38.trim(c)
        stats["kept_whole" if fin else "trimmed"] = stats.get("kept_whole" if fin else "trimmed", 0) + 1
        g = CD.guard333d(c, text, known)
        if g is None:
            return c
        stats[g] = stats.get(g, 0) + 1
    return None


def install_creative_k1ab(loop, gen, n: int = CD.N333D) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0, "G1": 0, "G2": 0, "G3": 0,
                         "G4": 0, "G5": 0, "hist_msgs": 0, "kept_whole": 0, "trimmed": 0}

    def turn_k1ab(text: str) -> list[str]:
        if not CB.is_creative333c(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        hist = KA.chat_history(loop)
        loop.cre333_stats["hist_msgs"] += len(hist)
        reply = write_k1ab(gen, text, facts, hist, loop.cre333_stats, n)
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative_k1ab",
                                "n": n, "context_facts": len(ctx), "hist_msgs": len(hist)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("k1ab: creative turn wrote to the notebook")
        return [reply]

    turn_k1ab.__name__ = "turn_k1ab"
    loop.turn = turn_k1ab


def build_null_k1ab(state_dir, args):
    import claude_mu402 as MU
    old = CD.install_creative333d
    CD.install_creative333d = install_creative_k1ab
    try:
        loop = MU.build_null02c(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [("cre_k1ab" if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1ab: creative writer = install_creative_k1ab; layers = {loop.layers330c}", flush=True)
    return loop
