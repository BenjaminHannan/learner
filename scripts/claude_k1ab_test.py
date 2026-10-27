#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1ab_cre.py (needs torch, no model). Run: python -B scripts/claude_k1ab_test.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1ab_cre as KAB  # noqa: E402
import claude_k1b_test as T  # noqa: E402  (fake tokenizer/model/gen)


class RecGen(T.Gen):
    def __init__(self, rows):
        super().__init__(rows)
        self.msgs = None

    def _render(self, msgs):
        self.msgs = msgs
        return "x"


def main():
    ok = 0
    list_done = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, T.EOS2, 1]
    list_cut = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    hist = [{"role": "user", "content": "I'm opening a bakery called Crumb"},
            {"role": "assistant", "content": "Nice!"}]
    # 1. history sits between the system line and the request, and a finished list is kept whole
    gen = RecGen([list_done])
    stats = {}
    out = KAB.write_k1ab(gen, "any ideas for names for it?", "", hist, stats)
    assert [m["role"] for m in gen.msgs] == ["system", "user", "assistant", "user"], gen.msgs
    assert gen.msgs[0]["content"] == CD.SYSTEM333D and gen.msgs[1:3] == hist
    assert out.endswith('"Rise Up"') and stats["kept_whole"] == 1, (out, stats)
    ok += 1
    # 2. a cut-off sample is trimmed as cre333d does
    stats = {}
    out = KAB.write_k1ab(RecGen([list_cut]), "any ideas for names for it?", "", hist, stats)
    full = T.K.sample_chat_fin(T.Gen([list_cut]), [], 1)[0][0]
    assert out == C38.trim(full) and stats["trimmed"] == 1, (out, stats)
    ok += 1
    # 3. install: reads chat338's saved history, counts it, writes nothing to the notebook
    class NB:
        events = []

    class L:
        def __init__(self, d):
            self.dir, self.nb, self.counters, self.experience, self.tick = d, NB(), {}, [], 0
            self.turn = lambda t: ["(inner)"]

        def _save(self):
            pass
    C._facts = lambda loop: []
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": hist}), encoding="utf-8")
        loop = L(d)
        g = RecGen([list_done])
        KAB.install_creative_k1ab(loop, g)
        r = loop.turn("any ideas for names for it?")
        assert r[0].endswith('"Rise Up"') and loop.cre333_stats["hist_msgs"] == 2
        assert loop.cre333_stats["kept_whole"] == 1 and loop.experience[-1]["phase"] == "creative_k1ab"
        assert loop.turn("what time is it") == ["(inner)"]
    ok += 1
    # 4. build_null_k1ab swaps the writer around mu402's build_null02c and restores it
    import claude_mu402 as MU
    seen, real = {}, MU.build_null02c

    def fake(state_dir, args):
        seen["fn"] = CD.install_creative333d
        o = type("L", (), {})()
        o.layers330c = ["330a_334", "cre333d", "seed402"]
        return o
    MU.build_null02c = fake
    try:
        before = CD.install_creative333d
        out = KAB.build_null_k1ab("x", None)
        assert seen["fn"] is KAB.install_creative_k1ab and CD.install_creative333d is before
        assert out.layers330c == ["330a_334", "cre_k1ab", "seed402"]
    finally:
        MU.build_null02c = real
    ok += 1
    print(f"k1ab tests: {ok}/4 OK")


if __name__ == "__main__":
    main()
