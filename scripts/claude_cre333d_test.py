#!/usr/bin/env python3
"""333d unit tests (stub loop, stub generator; no model). Sentences written by the month-end thread."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as D  # noqa: E402


class Nb:
    events: list = []


class Loop:
    def __init__(self):
        self.nb, self.tick, self.counters, self.experience = Nb(), 0, {}, []
        self.turn = lambda text: ["INNER"]

    def _save(self):
        pass


class Gen:
    def __init__(self, outs):
        self.outs, self.seen = outs, []

    def sample_chat(self, msgs, n):
        self.seen.append(msgs)
        return list(self.outs)


def test_pick_and_route():
    C._facts = lambda loop: [("USER", "sister", "Mira"), ("Mira", "likes", "gardening")]
    g = Gen(["I'm sorry, but I can't help without more details.",
             "Could you tell me more about her?",
             "Your sister Tilda would love a pottery class.",
             "Try a set of heirloom seeds and a kneeling pad for Mira's garden."])
    lp = Loop()
    D.install_creative333d(lp, g)
    assert lp.turn("any gift ideas for my sister mira?") == \
        ["Try a set of heirloom seeds and a kneeling pad for Mira's garden."]
    assert lp.cre333_stats["G5"] == 2 and lp.cre333_stats["G2"] == 1, lp.cre333_stats
    assert "Mira's likes is gardening" in g.seen[0][0]["content"]
    assert lp.turn("my sister runs a gift shop") == ["INNER"]           # look-alike: not a request


def test_fallback():
    C._facts = lambda loop: []
    lp = Loop()
    D.install_creative333d(lp, Gen(["I cannot do that."] * 4))
    assert lp.turn("write me a poem about rain") == [C.FALLBACK]


if __name__ == "__main__":
    test_pick_and_route()
    test_fallback()
    print("333d tests: 2/2 OK")
