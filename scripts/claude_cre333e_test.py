#!/usr/bin/env python3
"""333e unit tests (stub loop, stub router, stub generator; no model). Creative research thread, 2026-09-24."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_cre333_agent as C  # noqa: E402
import claude_cre333e_agent as E  # noqa: E402


class Nb:
    events: list = []


class Loop:
    def __init__(self):
        self.nb, self.tick, self.counters, self.experience = Nb(), 0, {}, []
        self.turn = lambda text: ["INNER:" + text]

    def _save(self):
        pass


class Gen:
    def __init__(self, outs):
        self.outs, self.seen = outs, []

    def sample_chat(self, msgs, n):
        self.seen.append(msgs)
        return list(self.outs)


class Router:
    def __init__(self, calls):
        self.calls, self.seen = calls, []

    def calls_tool(self, prior_user, text):
        self.seen.append((list(prior_user), text))
        return (text in self.calls, 0.9 if text in self.calls else 0.1)


def test_arms():
    C._facts = lambda loop: [("USER", "sister", "Mira")]
    req = "make her something for it"
    for hist in (False, True):
        lp, g, r = Loop(), Gen(["Try a watercolour card with a line about Mira's first garden."]), Router({req})
        E.install_creative333e(lp, g, r, with_history=hist)
        assert lp.turn("my sister mira turns 30 on friday") == ["INNER:my sister mira turns 30 on friday"]
        assert lp.turn(req) == ["Try a watercolour card with a line about Mira's first garden."]
        assert r.seen[1] == (["my sister mira turns 30 on friday"], req)          # the router saw the earlier turn
        msgs = g.seen[0]
        assert msgs[0]["role"] == "system" and msgs[-1] == {"role": "user", "content": req}
        assert len(msgs) == (4 if hist else 2), msgs                               # e2 adds the chat so far
        if hist:
            assert msgs[1]["content"] == "my sister mira turns 30 on friday"
            assert msgs[2]["content"] == "INNER:my sister mira turns 30 on friday"
        assert lp.cre333_stats["creative_turns"] == 1 and lp.cre333_stats["passed_through"] == 1


def test_fallback_and_guard():
    C._facts = lambda loop: []
    lp = Loop()
    E.install_creative333e(lp, Gen(["I cannot do that."] * 4), Router({"a poem about rain please"}), True)
    assert lp.turn("a poem about rain please") == [C.FALLBACK]
    assert lp.cre333_stats["G5"] == 4 and lp.cre333_stats["fallbacks"] == 1


if __name__ == "__main__":
    test_arms()
    test_fallback_and_guard()
    print("333e tests: 2/2 OK")
