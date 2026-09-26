#!/usr/bin/env python3
"""k1b: the creative writer keeps a finished reply whole (Creative answers in chat thread, 2026-09-26). One change on
cre333d, independent of k1a (each is tested against 0.2c's cre333d on its own).

Why: cre333d trims every sample with claude_chat338_agent.trim, which cuts back to the last ". ", "! " or "? ". That
exists to drop a sentence the 200-token limit cut off, but it also fires on replies that ended on their own: in a
numbered list "5." counts as a sentence end, so a list whose last item doesn't end in a full stop (a name in quotes,
a slogan, a line of a poem) loses that item and ends on a bare "5."; a poem loses every line after the last full
stop. K1's judge asks that a reply "fits the form asked for" (5 names, four lines).

What: install_creative_k1b(loop, gen) is install_creative333d with one change: the writer asks the same generate
call for its samples (same arguments, same random draws) but also learns which samples ended on an end-of-sequence
token. A sample that ended on its own is kept whole (only think text and an "assistant:" prefix are removed, as trim
does); a sample the token limit cut off is trimmed exactly as before. Guards (140 words etc.), routing, prompt,
4 samples, fallback: unchanged.
build_null_k1b = the swap around claude_mu402.build_null02c (NullReader + per-turn seeds), like claude_k1a_cre.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_chat338_agent as C38     # noqa: E402
import claude_cre333_agent as C        # noqa: E402
import claude_cre333b_agent as CB      # noqa: E402
import claude_cre333d_agent as CD      # noqa: E402

_PRINTED: list = []


def strip_only(c: str) -> str:
    """trim's clean-up without the cut: think text and an 'assistant:' prefix."""
    c = C38.THINK.sub("", c).strip()
    return re.sub(r"^(assistant|ai)\s*:\s*", "", c, flags=re.I).strip()


def eos_ids(tok, model) -> set[int]:
    ids = set()
    gc = getattr(model, "generation_config", None)
    e = getattr(gc, "eos_token_id", None) if gc is not None else None
    for x in (e if isinstance(e, (list, tuple)) else [e]):
        if x is not None:
            ids.add(int(x))
    if tok.eos_token_id is not None:
        ids.add(int(tok.eos_token_id))
    return ids


def sample_chat_fin(gen, msgs: list[dict], n: int) -> list[tuple[str, bool]]:
    """claude_chat338_agent.Gen338.sample_chat's exact generate call, plus 'ended on its own' per sample."""
    g = gen.g
    ids = g.tok(gen._render(msgs), return_tensors="pt").to(g.dev)
    with g.torch.no_grad():
        out = g.model.generate(**ids, max_new_tokens=gen.max_new, do_sample=True, temperature=gen.t,
                               top_p=gen.p, num_return_sequences=n, pad_token_id=g.tok.eos_token_id)
    cut = ids["input_ids"].shape[1]
    stop = eos_ids(g.tok, g.model)
    res = []
    for o in out:
        new = o[cut:].tolist()
        res.append((g.tok.decode(o[cut:], skip_special_tokens=True).strip(), any(t in stop for t in new)))
    return res


def write_k1b(gen, text: str, facts: str, stats: dict, n: int = CD.N333D) -> str | None:
    known = C38._words([text, facts])
    system = CD.SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    for c, fin in sample_chat_fin(gen, msgs, n):
        c = strip_only(c) if fin else C38.trim(c)
        stats["kept_whole" if fin else "trimmed"] = stats.get("kept_whole" if fin else "trimmed", 0) + 1
        g = CD.guard333d(c, text, known)
        if g is None:
            return c
        stats[g] = stats.get(g, 0) + 1
    return None


def install_creative_k1b(loop, gen, n: int = CD.N333D) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0,
                         "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0, "kept_whole": 0, "trimmed": 0}

    def turn_k1b(text: str) -> list[str]:
        if not CB.is_creative333c(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        reply = write_k1b(gen, text, facts, loop.cre333_stats, n)
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative_k1b",
                                "n": n, "context_facts": len(ctx)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("k1b: creative turn wrote to the notebook")
        return [reply]

    turn_k1b.__name__ = "turn_k1b"
    loop.turn = turn_k1b


def build_null_k1b(state_dir, args):
    import claude_mu402 as MU
    old = CD.install_creative333d
    CD.install_creative333d = install_creative_k1b
    try:
        loop = MU.build_null02c(state_dir, args)
    finally:
        CD.install_creative333d = old
    loop.layers330c = [("cre_k1b" if x == "cre333d" else x) for x in loop.layers330c]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"k1b: creative writer = install_creative_k1b; layers = {loop.layers330c}", flush=True)
    return loop
