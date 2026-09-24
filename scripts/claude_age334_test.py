#!/usr/bin/env python3
"""334 unit tests (stub reader, cloud-safe). Run: python -B scripts/claude_age334_test.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_lis314_test as H  # noqa: E402 (stubs route122, builds stacks with a stub reader)
import claude_age334_agent as A  # noqa: E402
import claude_e2e336_run as R  # noqa: E402

LAYERS = ("313", "315", "314")
T1, T2, T3 = "My sister is Ilka.", "My dog is Pip.", "My cat is Tam."
TABLE = {T1: H.st([H.fact("me", "sister", "Ilka")], [H.LO]),
         T2: H.st([H.fact("me", "dog", "Pip")], [H.LO]),
         T3: H.st([H.fact("me", "cat", "Tam")], [H.LO])}


def build(d=None):
    loop, _r, d = H.fresh(TABLE, LAYERS, d)
    A.install_agenda334(loop)
    return loop, d


def t1_morning_confirm():
    loop, d = build()
    for t in (T1, T2, T3):
        assert H.say(loop, t) == "Okay."
    assert not H.triples(loop) and len(loop.lis314_store) == 3
    R.end_day(loop)
    assert loop.age334_stats["picked"] == 2
    loop, _ = build(d)                                   # restart
    rep = H.say(loop, "hello")
    assert "By the way, I think you told me your sister is Ilka, is that right?" in rep, rep
    H.say(loop, "yes")
    assert H.has(loop, "USER", "sister", "Ilka"), H.triples(loop)
    rep = H.say(loop, "hello")
    assert "your dog is Pip, is that right?" in rep, rep
    H.say(loop, "no")
    assert not H.has(loop, "USER", "dog", "Pip")
    rep = H.say(loop, "hello")
    assert "By the way" not in rep, rep                  # only 2 per day; cat waits
    R.end_day(loop)
    loop, _ = build(d)
    rep = H.say(loop, "hello")
    assert "your cat is Tam, is that right?" in rep, rep


def t2_no_agenda_without_sleep():
    loop, _d = build()
    H.say(loop, T1)
    assert "By the way" not in H.say(loop, "hello")


def t3_never_writes_itself():
    loop, d = build()
    H.say(loop, T1)
    R.end_day(loop)
    loop, _ = build(d)
    ev0 = len(loop.nb.events)
    H.say(loop, "hello")
    assert len(loop.nb.events) == ev0


if __name__ == "__main__":
    for fn in (t1_morning_confirm, t2_no_agenda_without_sleep, t3_never_writes_itself):
        fn()
        print("ok", fn.__name__)
    print("334 tests 3/3")
