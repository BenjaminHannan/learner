#!/usr/bin/env python3
"""rsn-299b layer for the joined agent: rsn-299's think layer with 5 samples and a majority vote.

install_think299b(loop, model): same router, read-only check and fallback as
claude_think299_agent.install_think299; the answer comes from claude_rsn299b_run.solve_vote
(5 sampled calculator runs, an answer needs 3 of 5 votes, otherwise "I'm not sure").
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn299b_run as V  # noqa: E402
import claude_think299_agent as A  # noqa: E402


def install_think299b(loop, model) -> None:
    inner = loop.turn
    tok, mdl, dev = A._bundle(model)
    loop.think299_stats = {"think_turns": 0, "fallbacks": 0, "passed_through": 0}
    counter = {"n": 0}

    def turn299b(text: str) -> list[str]:
        if not A.is_reasoning(text, loop):
            loop.think299_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        counter["n"] += 1
        base = counter["n"] * 104729

        def gfs(k):
            return lambda t, mx, stops: V._gen_sample(tok, mdl, dev, t, mx, stops, base + k)
        steps, calls, info = V.solve_vote(text, gfs)
        if info["votes"] < V.MAJORITY:
            reply = "I'm not sure. I worked it out a few times and got different answers."
        else:
            reply = A.render(steps)
        if len(loop.nb.events) != ev0:
            raise RuntimeError("299b: think turn wrote to the notebook")
        if reply is None:
            loop.think299_stats["fallbacks"] += 1
            return inner(text)
        loop.think299_stats["think_turns"] += 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "think299b",
                                "calls": sum(len(c) for c in calls)})
        return [reply]

    turn299b.__name__ = "turn299b"
    loop.turn = turn299b
