#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1a_cre.py (no model needed). Run: python -B scripts/claude_k1a_test.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1a_cre as K  # noqa: E402


class NB:
    def __init__(self):
        self.events = []


class Loop:
    def __init__(self, d):
        self.dir, self.nb, self.counters, self.experience, self.tick = d, NB(), {}, [], 0
        self.inner_calls = []
        self.turn = self._inner

    def _inner(self, text):
        self.inner_calls.append(text)
        return ["(inner)"]

    def _save(self):
        pass


class Gen:
    def __init__(self, outs):
        self.outs, self.calls = outs, []

    def sample_chat(self, msgs, n):
        self.calls.append((json.loads(json.dumps(msgs)), n))
        return list(self.outs)


def run(install, d, text, outs, hist=None):
    if hist is not None:
        (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": hist}), encoding="utf-8")
    loop, gen = Loop(d), Gen(outs)
    install(loop, gen)
    return loop, gen, loop.turn(text)


def main():
    C._facts = lambda loop: []                      # no notebook in these tests
    ok = 0
    req = "can you give me some ideas for names for it?"
    good = ["Here are five: Crumb Club, Flour Power, Rise Up, Knead Speed and Batter Days."]
    import claude_cre333b_agent as CB
    assert CB.is_creative333c(req)
    # 1. no history file: the same messages, reply and counters as cre333d
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        l0, g0, r0 = run(CD.install_creative333d, a, req, good)
        l1, g1, r1 = run(K.install_creative_k1a, b, req, good)
        assert len(g0.calls) == 1 and g0.calls == g1.calls and r0 == r1, (g0.calls, g1.calls)
        assert {k: v for k, v in l1.cre333_stats.items() if k != "hist_msgs"} == l0.cre333_stats
        ok += 1
    # 2. history file: the history sits between the system line and the request, capped at 12 messages
    hist = []
    for i in range(8):
        hist += [{"role": "user", "content": f"u{i}"}, {"role": "assistant", "content": f"a{i}"}]
    with tempfile.TemporaryDirectory() as d:
        loop, gen, r = run(K.install_creative_k1a, d, req, good, hist)
        msgs = gen.calls[0][0]
        assert msgs[0]["role"] == "system" and msgs[-1] == {"role": "user", "content": req}
        assert msgs[1:-1] == hist[-12:], msgs
        assert loop.cre333_stats["hist_msgs"] == 12 and loop.experience[-1]["hist_msgs"] == 12
        ok += 1
    # 3. a name said earlier in the chat is known to the guard (G2 would drop it without the history)
    card = ["Happy birthday! Your friend Tovah would love a day on the water."]
    h = [{"role": "user", "content": "my friend Tovah just got into sailing"},
         {"role": "assistant", "content": "That sounds fun!"}]
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        l0, _g, r0 = run(CD.install_creative333d, a, "write a short birthday card for her, any ideas?", card)
        l1, _g, r1 = run(K.install_creative_k1a, b, "write a short birthday card for her, any ideas?", card, h)
        assert r0 == [C.FALLBACK] and l0.cre333_stats["G2"] == 1, (r0, l0.cre333_stats)
        assert r1 == card, r1
        ok += 1
    # 4. empty or odd history entries are skipped; routing and pass-through unchanged
    with tempfile.TemporaryDirectory() as d:
        loop, gen, r = run(K.install_creative_k1a, d, req, good,
                           [{"role": "user", "content": " "}, {"role": "tool", "content": "x"},
                            {"role": "assistant", "content": "ok"}])
        assert gen.calls[0][0][1:-1] == [{"role": "assistant", "content": "ok"}]
        loop2, gen2, r2 = run(K.install_creative_k1a, d, "my sister lives in Brackenford", good)
        assert r2 == ["(inner)"] and gen2.calls == [] and loop2.cre333_stats["passed_through"] == 1
        ok += 1
    # 5. all samples fail -> the same fallback line and counters as cre333d
    with tempfile.TemporaryDirectory() as d:
        loop, gen, r = run(K.install_creative_k1a, d, req, ["I'm sorry, but I can't help with that."])
        assert r == [C.FALLBACK] and loop.cre333_stats["G5"] == 1 and loop.cre333_stats["fallbacks"] == 1
        ok += 1
    # 6. build_k1a restores install_creative333d afterwards (the swap never leaks)
    import claude_e2e02c as E02C
    seen = {}
    real = E02C.build_02c

    def fake(state_dir, args):
        seen["fn"] = CD.install_creative333d
        o = type("L", (), {})()
        o.layers330c = ["330a_334", "rec360", "cre333d", "think299b"]
        return o
    E02C.build_02c = fake
    try:
        before = CD.install_creative333d
        out = K.build_k1a("x", None)
        assert seen["fn"] is K.install_creative_k1a and CD.install_creative333d is before
        assert out.layers330c == ["330a_334", "rec360", "cre_k1a", "think299b"]
    finally:
        E02C.build_02c = real
    ok += 1
    # 7. build_null_k1a: the same swap around mu402's build_null02c (NullReader harness)
    import claude_mu402 as MU
    seen.clear()
    real = MU.build_null02c

    def fake2(state_dir, args):
        seen["fn"] = CD.install_creative333d
        o = type("L", (), {})()
        o.layers330c = ["330a_334", "cre333d", "seed402"]
        return o
    MU.build_null02c = fake2
    try:
        before = CD.install_creative333d
        out = K.build_null_k1a("x", None)
        assert seen["fn"] is K.install_creative_k1a and CD.install_creative333d is before
        assert out.layers330c == ["330a_334", "cre_k1a", "seed402"]
    finally:
        MU.build_null02c = real
    ok += 1
    print(f"k1a tests: {ok}/7 OK")


if __name__ == "__main__":
    main()
