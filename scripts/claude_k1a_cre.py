#!/usr/bin/env python3
"""k1a: the creative writer sees the chat (Creative answers in chat thread, 2026-09-26). One change on cre333d.

Why: in 0.2c (artifacts/claude-e2e02c-20260926/VERIFY-02c.md) K1 was 18/50 useful vs 21 for the plain 1B (T).
turn333d (scripts/claude_cre333d_agent.py) gives the 1B only [system line, current message]; the plain 1B sees the
whole chat. Counts only, no test item read or quoted (scratch script, reported in the thread): X lost only on items
whose request came after lead-in turns (useful 4 vs T 9 of 22) and was ahead on items without them (14 vs 12 of
28); on the lead-in items the judge's reasons said off-topic 9 times for X and 3 times for T.

What: install_creative_k1a(loop, gen) is install_creative333d with one change: the writer's context also holds the
last HISTORY_K1A messages of this chat, i.e. the delivered history chat338 keeps in <state_dir>/chat338.json, read
at turn time (empty on a chat's first turn, so a request with no lead-in gets exactly cre333d's prompt). The
messages go between the system line and the request, and their words join the guard's known words the way
chat338 does it (claude_chat338_agent.install_chat338), so a name the user said earlier in the chat is not taken
for an invented one. Unchanged: routing (is_creative333c), SYSTEM333D and the notebook facts, 4 samples, the first
that passes guard333d, trim, the FALLBACK line, counters, the WORK entry, and no notebook writes.

build_k1a(state_dir, args) = claude_e2e02c.build_02c (sealed, not edited) with install_creative_k1a swapped in for
install_creative333d while it builds. build_null_k1a(state_dir, args) = the same swap around
claude_mu402.build_null02c (the Making-things-up thread's rental harness: a NullReader under --model NULL, so no
2 GB reader upload, and torch/random seeded per turn from (turn number, text), the same seeds for every arm), so
the k1a arm differs from mu402's build_null02c arm by the writer's chat only. New file only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_chat338_agent as C38     # noqa: E402
import claude_cre333_agent as C        # noqa: E402
import claude_cre333b_agent as CB      # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402

HISTORY_K1A = C38.HISTORY338           # 12 messages, the window chat338 already feeds the 1B
_PRINTED: list = []


def chat_history(loop) -> list[dict]:
    """The last HISTORY_K1A messages of this chat as chat338 saved them (after delivered02c's rewrite)."""
    p = Path(loop.dir) / C38.STATE_NAME338
    if not p.exists():
        return []
    h = json.loads(p.read_text(encoding="utf-8")).get("history") or []
    h = [{"role": m["role"], "content": m["content"]} for m in h
         if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()]
    return h[-HISTORY_K1A:]


def write_k1a(gen, text: str, facts: str, hist: list[dict], stats: dict, n: int = CD.N333D) -> str | None:
    """cre333d's writer with the chat in its context. hist=[] gives exactly cre333d's prompt and guard."""
    known = C38._words([text, facts] + [m["content"] for m in hist])
    system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
    msgs = [{"role": "system", "content": system}] + list(hist) + [{"role": "user", "content": text}]
    for c in gen.sample_chat(msgs, n):
        c = C38.trim(c)
        g = CD.guard333d(c, text, known)
        if g is None:
            return c
        stats[g] = stats.get(g, 0) + 1
    return None


SAID_K1A = " Earlier in this chat the user said: "


def write_k1a_said(gen, text: str, facts: str, said: list[str], stats: dict, n: int = CD.N333D) -> str | None:
    """Practice variant W2 (not the registered change unless PASSMARKS says so): only the user's earlier messages,
    quoted in the system line; the chat is not passed as messages, so an earlier reply can't be copied."""
    said = [s.strip() for s in said if s and s.strip()]
    known = C38._words([text, facts] + said)
    system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
    if said:
        system += SAID_K1A + " ".join(json.dumps(s, ensure_ascii=False) for s in said)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    for c in gen.sample_chat(msgs, n):
        c = C38.trim(c)
        g = CD.guard333d(c, text, known)
        if g is None:
            return c
        stats[g] = stats.get(g, 0) + 1
    return None


def install_creative_k1a(loop, gen, n: int = CD.N333D) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0,
                         "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0, "hist_msgs": 0}

    def turn_k1a(text: str) -> list[str]:
        if not CB.is_creative333c(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        hist = chat_history(loop)
        loop.cre333_stats["hist_msgs"] += len(hist)
        reply = write_k1a(gen, text, facts, hist, loop.cre333_stats, n)
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative_k1a",
                                "n": n, "context_facts": len(ctx), "hist_msgs": len(hist)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("k1a: creative turn wrote to the notebook")
        return [reply]

    turn_k1a.__name__ = "turn_k1a"
    loop.turn = turn_k1a


def _swapped(build, state_dir, args):
    old = CD.install_creative333d
    CD.install_creative333d = install_creative_k1a
    try:
        loop = build(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [("cre_k1a" if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1a: creative writer = install_creative_k1a; layers = {loop.layers330c}", flush=True)
    return loop


def build_k1a(state_dir, args):
    import claude_e2e02c as E02C
    return _swapped(E02C.build_02c, state_dir, args)


def build_null_k1a(state_dir, args):
    import claude_mu402 as MU
    return _swapped(MU.build_null02c, state_dir, args)
