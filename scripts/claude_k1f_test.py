#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1f_cre.py (no model needed). Run: python -B scripts/claude_k1f_test.py"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1a_cre as K1A  # noqa: E402
import claude_k1a_test as T1A  # noqa: E402
import claude_k1f_cre as K  # noqa: E402

LFM = "/rental/hf/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b"


class Cfg:
    model_type = "lfm2"


class One:
    def __init__(self, d):
        self.d = d
        self.model = type("M", (), {"config": Cfg()})()


def with_writer(outs):
    """Put a fake LFM writer in k1f's cache for $K1F_WRITER_MODEL and return it."""
    os.environ[K.WRITER_ENV] = LFM
    w = T1A.Gen(outs)
    w.g = One(LFM)
    K._GEN.clear()
    K._GEN[LFM] = w
    return w


def main():
    C._facts = lambda loop: []                      # no notebook in these tests
    ok = 0
    req = "can you give me some ideas for names for it?"
    good = ["Here are five: Crumb Club, Flour Power, Rise Up, Knead Speed and Batter Days."]
    hist = [{"role": "user", "content": "we're starting a bread club at work"},
            {"role": "assistant", "content": "Nice, that sounds fun!"}]
    # 1. no $K1F_WRITER_MODEL: refuse to build (never fall back to the build's 1B silently)
    os.environ.pop(K.WRITER_ENV, None)
    K._GEN.clear()
    try:
        K.writer_gen()
        raise AssertionError("writer_gen ran without K1F_WRITER_MODEL")
    except SystemExit as e:
        assert K.WRITER_ENV in str(e)
    ok += 1
    # 2. creative turns go to the LFM writer; the build's gen gets no creative call
    w = with_writer(good)
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": hist}), encoding="utf-8")
        loop, mini = T1A.Loop(d), T1A.Gen(["should never be used"])
        K.install_creative_k1f(loop, mini)
        r = loop.turn(req)
        assert r == good and mini.calls == [] and len(w.calls) == 1, (r, mini.calls, w.calls)
        assert loop.k1f_writer == "lfm2 @0f604ada", loop.k1f_writer
    ok += 1
    # 3. the one change: same messages, n, reply and counters as k1a given the same drafts
    for h in (None, hist):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            l0, g0, r0 = T1A.run(K1A.install_creative_k1a, a, req, good, h)
            w = with_writer(good)
            if h is not None:
                (Path(b) / C38.STATE_NAME338).write_text(json.dumps({"history": h}), encoding="utf-8")
            l1 = T1A.Loop(b)
            K.install_creative_k1f(l1, T1A.Gen(["unused"]))
            r1 = l1.turn(req)
            assert g0.calls == w.calls and r0 == r1 and l0.cre333_stats == l1.cre333_stats, (g0.calls, w.calls)
            assert l0.experience == l1.experience
    ok += 1
    # 4. guards and fallback unchanged; non-creative turns pass through to the build
    w = with_writer(["I'm sorry, but I can't help with that."])
    with tempfile.TemporaryDirectory() as d:
        loop = T1A.Loop(d)
        K.install_creative_k1f(loop, None)
        assert loop.turn(req) == [C.FALLBACK] and loop.cre333_stats["G5"] == 1
        assert loop.cre333_stats["fallbacks"] == 1
        assert loop.turn("my sister lives in Brackenford") == ["(inner)"] and len(w.calls) == 1
    ok += 1
    # 5. the writer is loaded once per process, wrapped in k1a's Gen338 sampling, never with the sleep adapter
    os.environ[K.WRITER_ENV] = LFM
    K._GEN.clear()
    loads = []

    def load(d):
        loads.append(d)
        return One(d)
    g1, g2 = K.writer_gen(load), K.writer_gen(load)
    assert g1 is g2 and loads == [LFM] and isinstance(g1, C38.Gen338)
    assert (g1.max_new, g1.t, g1.p) == (200, 0.7, 0.9) and g1.g.d == LFM
    K._GEN.clear()

    def load_adapted(d):
        o = One(d)
        o.sleep02c = True
        return o
    try:
        K.writer_gen(load_adapted)
        raise AssertionError("an adapted writer was accepted")
    except RuntimeError:
        pass
    ok += 1
    # 6. build_null_k1f / build_k1f swap install_creative333d in, restore it, rename the layer, print once
    import claude_e2e02c as E02C
    import claude_mu402 as MU
    with_writer(good)
    for mod, attr, fn in ((MU, "build_null02c", K.build_null_k1f), (E02C, "build_02c", K.build_k1f)):
        seen = {}
        real = getattr(mod, attr)

        def fake(state_dir, args):
            seen["fn"] = CD.install_creative333d
            o = type("L", (), {})()
            o.layers330c = ["330a_334", "cre333d", "seed402"]
            return o
        setattr(mod, attr, fake)
        K._PRINTED.clear()
        buf = io.StringIO()
        try:
            before = CD.install_creative333d
            with redirect_stdout(buf):
                out = fn("x", None)
                fn("y", None)
            assert seen["fn"] is K.install_creative_k1f and CD.install_creative333d is before
            assert out.layers330c == ["330a_334", "cre_k1f", "seed402"]
            lines = buf.getvalue().splitlines()
            assert lines == ["k1f: creative writer = install_creative_k1f; writer = lfm2 @0f604ada; "
                             "layers = ['330a_334', 'cre_k1f', 'seed402']"], lines
        finally:
            setattr(mod, attr, real)
    ok += 1
    print(f"k1f tests: {ok}/6 OK")


if __name__ == "__main__":
    main()
