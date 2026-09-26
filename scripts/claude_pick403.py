#!/usr/bin/env python3
"""Shared reply picker (mu-403 family). Owned by the "Making things up about you" thread, 2026-09-26. New file only.

Agreed 14:30 UTC 09-26 with Creative answers in chat (k1c) and Everyday chat (ch-405), at the thread manager's
request: ONE picker with a pluggable score, so pickers never stack and fight. Each score is registered as its own
single change on ONE layer; combining two scores on the same layer comes only after each has its own verdict.

What it does: PickGen stands in for the writer a layer is handed (338's Gen338, or anything with
.sample_chat(msgs, n) -> list[str]). It asks the real writer for the same n samples, scores them with
score_fn(msgs, samples) -> one value per sample (lower = better), and returns the SAME samples reordered, lowest
first, ties kept in draw order. Nothing is removed or added, so the layer's own guards still take the first sample
that passes, and a turn never loses a reply it would have had.

Rules for a score: it must not draw random numbers (no sampling), so both arms of a seeded test get the same samples
from the writer; it gets the raw samples (trim inside the score if the layer trims); values may be floats or tuples.

Where it sits: between the writer's samples and the layer's guards. For chat: Gen338 -> picker -> 338b's people
guard -> 338's guards G1-G4. For creative: Gen338 -> picker -> 333d's guards.

Why per layer: build_02c hands ONE Gen338 to creative 333d, chat 338b (and answer 382 when memory is on). Wrapping
that object would change three layers at once. on_layer() swaps only one layer's installer in its module:

  undo = on_layer(C38B, "install_chat338b", make_score, "ground")          # chat only
  undo = on_layer(C333D, "install_creative333d", make_score, "k1c")        # creative only

make_score(gen) is called once at install time with the layer's real writer (Gen338; its 1B is gen.g) and returns
score_fn. Call on_layer before building the agent; the PickGen is kept at loop.pick403[tag] for its counts.

  python3 -B scripts/claude_pick403.py      (selftest, CPU, no model)
"""
from __future__ import annotations

import math


def _key(v):
    if isinstance(v, tuple):
        return tuple(_key(x) for x in v)
    v = float(v)
    return math.inf if math.isnan(v) else v


class PickGen:
    """Same samples as the writer, reordered by score (lower first, stable)."""

    def __init__(self, gen, score_fn, tag: str = "pick"):
        self.gen, self.score_fn, self.tag = gen, score_fn, tag
        self.stats = {"calls": 0, "scored": 0, "reordered": 0, "top_changed": 0}
        self.last = None

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        cands = list(self.gen.sample_chat(msgs, n))
        self.stats["calls"] += 1
        if len(cands) < 2:
            return cands
        scores = list(self.score_fn(msgs, cands))
        if len(scores) != len(cands):
            raise ValueError(f"pick403[{self.tag}]: {len(scores)} scores for {len(cands)} samples")
        self.stats["scored"] += 1
        order = sorted(range(len(cands)), key=lambda i: (_key(scores[i]), i))
        if order != list(range(len(cands))):
            self.stats["reordered"] += 1
        if order[0] != 0:
            self.stats["top_changed"] += 1
        self.last = {"samples": cands, "scores": scores, "order": order}
        return [cands[i] for i in order]

    def __getattr__(self, name):
        if name == "gen":
            raise AttributeError(name)
        return getattr(self.gen, name)


def lexi(*fns):
    """Several scores on one layer: order by the first, ties by the next. Only after each has its own verdict."""
    def fn(msgs, cands):
        cols = [list(f(msgs, cands)) for f in fns]
        return [tuple(c[i] for c in cols) for i in range(len(cands))]
    return fn


def on_layer(module, installer: str, make_score, tag: str):
    """Swap module.<installer>(loop, gen, ...) so that layer alone gets PickGen(gen, make_score(gen)). Returns undo."""
    orig = getattr(module, installer)
    if getattr(orig, "_pick403", None):
        raise RuntimeError(f"pick403: {installer} already has a picker ({orig._pick403}); combine scores with lexi()")

    def patched(loop, gen, *a, **k):
        p = PickGen(gen, make_score(gen), tag)
        d = getattr(loop, "pick403", None)
        if d is None:
            d = {}
            loop.pick403 = d
        d[tag] = p
        return orig(loop, p, *a, **k)

    patched._pick403 = tag
    patched.__name__ = f"{installer}_pick403_{tag}"
    setattr(module, installer, patched)

    def undo():
        setattr(module, installer, orig)
    return undo


def selftest() -> None:
    import random
    import types
    ok = 0

    class Gen:
        def __init__(self):
            self.g, self.max_new = "one_b", 200

        def sample_chat(self, msgs, n):
            return ["long reply here", "short", "mid reply", "short"][:n]

    p = PickGen(Gen(), lambda m, c: [len(x) for x in c], "t")
    out = p.sample_chat([], 4)
    assert out == ["short", "short", "mid reply", "long reply here"]; ok += 1              # lower first, stable
    assert sorted(out) == sorted(Gen().sample_chat([], 4)); ok += 1                         # nothing added/removed
    assert p.stats == {"calls": 1, "scored": 1, "reordered": 1, "top_changed": 1}; ok += 1
    assert p.max_new == 200 and p.g == "one_b"; ok += 1                                     # passes attributes on
    assert PickGen(Gen(), lambda m, c: [0] * len(c)).sample_chat([], 3) == Gen().sample_chat([], 3); ok += 1
    q = PickGen(Gen(), lambda m, c: [float("nan"), 1.0, 2.0, 0.5])
    assert q.sample_chat([], 4)[-1] == "long reply here"; ok += 1                           # NaN goes last
    try:
        PickGen(Gen(), lambda m, c: [1.0]).sample_chat([], 4)
        raise AssertionError("length mismatch accepted")
    except ValueError:
        ok += 1
    lx = lexi(lambda m, c: [0, 1, 0, 0], lambda m, c: [len(x) for x in c])
    assert PickGen(Gen(), lx).sample_chat([], 4) == ["short", "mid reply", "long reply here", "short"]; ok += 1

    state = random.getstate()                                                               # the picker draws nothing
    PickGen(Gen(), lambda m, c: [len(x) for x in c]).sample_chat([], 4)
    assert random.getstate() == state; ok += 1

    mod = types.SimpleNamespace()
    seen = {}

    def install_chat(loop, gen, n=4):
        seen["chat"] = gen

    def install_cre(loop, gen, n=4):
        seen["cre"] = gen

    mod.install_chat, mod.install_cre = install_chat, install_cre
    made = []
    undo = on_layer(mod, "install_chat", lambda gen: made.append(gen.g) or (lambda m, c: [0] * len(c)), "ground")
    loop, shared = types.SimpleNamespace(), Gen()
    mod.install_chat(loop, shared)
    mod.install_cre(loop, shared)
    assert isinstance(seen["chat"], PickGen) and seen["cre"] is shared; ok += 1             # one layer only
    assert loop.pick403["ground"] is seen["chat"] and made == ["one_b"]; ok += 1
    try:
        on_layer(mod, "install_chat", lambda gen: None, "k1c")
        raise AssertionError("second picker on one layer accepted")
    except RuntimeError:
        ok += 1
    undo()
    assert mod.install_chat is install_chat; ok += 1
    print(f"pick403 selftest {ok}/13 ok")


if __name__ == "__main__":
    selftest()
