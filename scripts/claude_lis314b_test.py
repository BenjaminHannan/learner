#!/usr/bin/env python3
"""Version b (claude_lis_stackb.py). lis-314 and lis-315 CPU tests (StubReader; no weights, no GPU).

Base 292t + the listener stack (scripts/claude_lis_stack.py). The learned self-router's weights
are not needed: this TEST file stubs fable_self122.route122 to DECLINE, like the lis-313 tests.
Dialogs are invented (fictional people and pets). T = 0.995 throughout.

lis-315 (per-fact release):
  P1 two facts, one sure and one unsure -> the sure one is saved, the unsure one asked back;
     "yes" then saves the second
  P2 a sure fact next to a "we" fact -> the sure one is saved, then "Whose ...?"
  P3 all facts sure -> passed through to turn310 unchanged (turn310 saves both)
  P4 only unsure facts -> passed through (turn310 asks back, nothing saved)
lis-314 (confirm-at-use):
  C1 unsure fact -> "Okay.", nothing saved; later question -> "I think you told me ..., is that
     right?"; "yes" -> saved; the same question is then answered from the notebook
  C2 "no" drops the pending fact; asking again -> not confirmed again, no save
  C3 the pending store never answers: a yes/no or other question about another relation gets
     no pending value, and any other reply to a confirm keeps the fact pending
  C4 sure + unsure in one turn -> sure saved now (via the edited frame), unsure pending
  C5 a newer sure save of the same (owner, rel) replaces the pending fact
  C6 the store survives a restart (a new loop on the same state dir)
  C7 the reader is called once per turn across the full stack (313 + 315 + 314), none on "yes"
  C8 question the notebook can answer is not turned into a confirm

Run: /tmp/claude-0/venv311/bin/python -B scripts/claude_lis314_test.py   (exit 0 iff all pass)
"""
from __future__ import annotations

import copy
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_self122 as SELF122  # noqa: E402

SELF122.route122 = lambda q: ("DECLINE", {"reason": "lis314-test-stub"})

import claude_loop292t_agent as T292  # noqa: E402
import claude_lis_stackb as STACK  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

HI, LO = 0.999, 0.6
CHAT = ({"act": "CHAT", "facts": [], "ask": None}, [], "stub-default", 0.5)


class StubReader:
    def __init__(self, table):
        self.table = dict(table)
        self.calls = []

    def read(self, turn, prev_reply=""):
        self.calls.append((turn, prev_reply))
        return self.table.get(str(turn), CHAT)


def fact(owner, rel, value, mode="ASSERT"):
    return {"owner": owner, "rel": rel, "value": value, "mode": mode}


def st(facts, confs, act="STATE"):
    return ({"act": act, "facts": facts, "ask": None}, confs, "stub", 0.4)


def ask(**kw):
    kw.setdefault("inverse", False)
    return ({"act": "ASK", "facts": [], "ask": kw}, [], "stub", 0.4)


def fresh(table, layers, d=None):
    d = d or tempfile.mkdtemp(prefix="lis314t_")
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    reader = StubReader(table)
    STACK.build_stack(loop, reader, 0.995, layers=layers)
    return loop, reader, d


def triples(loop):
    return sorted(tuple(t) for t in L90.notebook_triples(loop.nb))


def say(loop, t):
    r = loop.turn(t)
    return " ".join(r) if isinstance(r, list) else str(r)


def has(loop, s, r, v):
    return (s, r, v) in triples(loop)


# ------------------------------------------------------------------ lis-315
def p1():
    t1 = "My sister is Ilka and my cousin is Brann."
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Ilka"), fact("me", "cousin", "Brann")],
                                 [HI, LO])}, ("315",))
    rep = say(loop, t1)
    assert has(loop, "USER", "sister", "Ilka"), triples(loop)
    assert not has(loop, "USER", "cousin", "Brann")
    assert "Just to check" in rep and "Brann" in rep, rep
    say(loop, "yes")
    assert has(loop, "USER", "cousin", "Brann"), triples(loop)


def p2():
    t1 = "Dagny's cat is Mott and our dog is Fenn."
    loop, _r, _d = fresh({t1: st([fact("Dagny", "cat", "Mott"), fact("we", "dog", "Fenn")],
                                 [HI, HI])}, ("315",))
    rep = say(loop, t1)
    assert has(loop, "Dagny", "cat", "Mott"), triples(loop)
    assert "Whose dog is Fenn" in rep, rep
    assert not any(v == "Fenn" for (_s, _rr, v) in triples(loop))


def p3():
    t1 = "Hesper's boss is Corm and Hesper's dog is Lute."
    loop, _r, _d = fresh({t1: st([fact("Hesper", "boss", "Corm"), fact("Hesper", "dog", "Lute")],
                                 [HI, HI])}, ("315",))
    say(loop, t1)
    assert has(loop, "Hesper", "boss", "Corm") and has(loop, "Hesper", "dog", "Lute")
    assert loop.lis315_stats["released"] == 0


def p4():
    t1 = "Ivo's aunt is Gret."
    loop, _r, _d = fresh({t1: st([fact("Ivo", "aunt", "Gret")], [LO])}, ("315",))
    rep = say(loop, t1)
    assert "Just to check" in rep, rep
    assert not triples(loop)
    assert loop.lis315_stats["released"] == 0


# ------------------------------------------------------------------ lis-314
Q_SIS = "who's my sister again"


def c1(layers=("314",)):
    t1 = "My sister is Ilka."
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Ilka")], [LO]),
                          Q_SIS: ask(owner="me", rel="sister")}, layers)
    rep = say(loop, t1)
    assert rep == "Okay.", rep
    assert not triples(loop)
    rep = say(loop, Q_SIS)
    assert rep == "I think you told me your sister is Ilka, is that right?", rep
    assert not triples(loop)
    say(loop, "yes")
    assert has(loop, "USER", "sister", "Ilka"), triples(loop)
    assert not loop.lis314_store
    rep = say(loop, Q_SIS)
    assert "Ilka" in rep and "think you told me" not in rep, rep


def c2():
    t1 = "My sister is Ilka."
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Ilka")], [LO]),
                          Q_SIS: ask(owner="me", rel="sister")}, ("314",))
    say(loop, t1)
    say(loop, Q_SIS)
    rep = say(loop, "no")
    assert rep == "Okay, I won't save that.", rep
    assert not triples(loop) and not loop.lis314_store
    rep = say(loop, Q_SIS)
    assert "Ilka" not in rep, rep


def c3():
    t1 = "My sister is Ilka."
    q2 = "who's my brother"
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Ilka")], [LO]),
                          Q_SIS: ask(owner="me", rel="sister"),
                          q2: ask(owner="me", rel="brother")}, ("314",))
    say(loop, t1)
    rep = say(loop, q2)
    assert "Ilka" not in rep, rep
    say(loop, Q_SIS)
    rep = say(loop, "hmm not sure")
    assert "Ilka" not in rep, rep
    assert len(loop.lis314_store) == 1 and not triples(loop)


def c4():
    t1 = "Mira's dog is Pell and Mira's boss is Tove."
    loop, _r, _d = fresh({t1: st([fact("Mira", "dog", "Pell"), fact("Mira", "boss", "Tove")],
                                 [HI, LO])}, ("314",))
    say(loop, t1)
    assert has(loop, "Mira", "dog", "Pell"), triples(loop)
    assert not has(loop, "Mira", "boss", "Tove")
    assert [p["value"] for p in loop.lis314_store] == ["Tove"]


def c5():
    t1 = "Mira's boss is Tove."
    t2 = "Mira's boss is Keld."
    loop, _r, _d = fresh({t1: st([fact("Mira", "boss", "Tove")], [LO]),
                          t2: st([fact("Mira", "boss", "Keld")], [HI])}, ("314",))
    say(loop, t1)
    assert len(loop.lis314_store) == 1
    say(loop, t2)
    assert has(loop, "Mira", "boss", "Keld"), triples(loop)
    assert not loop.lis314_store, loop.lis314_store


def c6():
    t1 = "My sister is Ilka."
    table = {t1: st([fact("me", "sister", "Ilka")], [LO]), Q_SIS: ask(owner="me", rel="sister")}
    loop, _r, d = fresh(table, ("314",))
    say(loop, t1)
    loop2, _r2, _d2 = fresh(table, ("314",), d=d)
    assert [p["value"] for p in loop2.lis314_store] == ["Ilka"], loop2.lis314_store
    rep = say(loop2, Q_SIS)
    assert "Ilka" in rep and "think you told me" in rep, rep


def c7():
    t1 = "My sister is Ilka and my cousin is Brann."
    loop, r, _d = fresh({t1: st([fact("me", "sister", "Ilka"), fact("me", "cousin", "Brann")],
                                [HI, LO]),
                         "who is my cousin?": ask(owner="me", rel="cousin")},
                        ("313", "315", "314"))
    assert loop.turn.__name__ == "turn314"
    say(loop, t1)
    assert has(loop, "USER", "sister", "Ilka")
    n = len(r.calls)
    assert n == 1, r.calls
    say(loop, "who is my cousin?")
    assert len(r.calls) == 2, r.calls
    say(loop, "yes")
    assert len(r.calls) == 2, r.calls
    assert has(loop, "USER", "cousin", "Brann"), triples(loop)
    c1(("313", "315", "314"))


def c8():
    t1 = "My sister is Ilka."
    t2 = "My sister is Ulla."
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Ilka")], [HI]),
                          t2: st([fact("me", "sister", "Ulla")], [LO]),
                          Q_SIS: ask(owner="me", rel="sister")}, ("314",))
    say(loop, t1)
    say(loop, t2)
    rep = say(loop, Q_SIS)
    assert "think you told me" not in rep and "Ilka" in rep, rep


def g1():
    """lis-316: a "me" fact whose only first-person word is in the assistant's own reply is held
    as unsure (pending), not saved; a sure plain fact still saves; one read per turn."""
    loop, r, _d = fresh({"hello": ({"act": "CHAT", "facts": [], "ask": None}, [], "", 0.1),
                         "Brann": st([fact("me", "cousin", "Brann")], [HI]),
                         "Mira's dog is Pell.": st([fact("Mira", "dog", "Pell")], [HI])},
                        ("313", "315", "314", "316"))
    assert loop.turn.__name__ == "turn316"
    say(loop, "hello")
    loop.lis310_prev = "I think I like that."
    rep = say(loop, "Brann")
    assert not triples(loop), triples(loop)
    assert [p["value"] for p in loop.lis314_store] == ["Brann"], (rep, loop.lis314_store)
    say(loop, "Mira's dog is Pell.")
    assert has(loop, "Mira", "dog", "Pell")
    assert len(r.calls) == 3, r.calls


def b1():
    """313b: a where-question misread as a person question is not answered with the person."""
    t1 = "My sister is Tuva."
    q = "so where's my sis living these days?"
    loop, _r, _d = fresh({t1: st([fact("me", "sister", "Tuva")], [HI]),
                          q: ask(owner="me", rel="sister")}, ("313", "315", "314", "316"))
    say(loop, t1)
    rep = say(loop, q)
    print("   b1 reply:", rep, loop.lis313_stats)
    assert "Your sister is Tuva" not in rep, rep


def b2():
    """314b: a question misread as a statement is not swallowed with "Okay." or held."""
    q = "is my cat called Mott?"
    loop, _r, _d = fresh({q: st([fact("me", "cat", "Mott")], [LO])}, ("314",))
    rep = say(loop, q)
    assert rep != "Okay.", rep
    assert not loop.lis314_store, loop.lis314_store


class Heavy:
    """A stand-in model with plain attributes; deep-copying it means the weights were copied."""

    def __init__(self):
        self._parameters = {"w": self}

    copies = 0

    def __deepcopy__(self, memo):  # counted, not raised: the base chain catches exceptions
        Heavy.copies += 1
        return self


Heavy.__module__ = "claude_heavy_model"  # a module name the 292t helper walk follows


def b3():
    """stackb: the reader (and its model) is never reachable by 292t's per-turn snapshot."""
    class WalkedReader(StubReader):
        pass
    WalkedReader.__module__ = "claude_lis300_read"  # the real Reader's module: walked by 292t
    r = WalkedReader({"hello": CHAT})
    r.model = Heavy()
    d = tempfile.mkdtemp(prefix="lis314bt_")
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    STACK.build_stack(loop, r, 0.995, layers=("313", "315", "314", "316"))
    Heavy.copies = 0
    for t in ("hello", "hello there", "how are you"):
        say(loop, t)
    assert Heavy.copies == 0, f"the reader's model was deep-copied {Heavy.copies} times"


TESTS = [p1, p2, p3, p4, c1, c2, c3, c4, c5, c6, c7, c8, g1, b1, b2, b3]


def main():
    ok = 0
    for f in TESTS:
        try:
            f()
            ok += 1
            print("PASS", f.__name__)
        except Exception:  # noqa: BLE001
            print("FAIL", f.__name__)
            traceback.print_exc()
    print(f"lis314b tests: {ok}/{len(TESTS)} passed")
    return 0 if ok == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
