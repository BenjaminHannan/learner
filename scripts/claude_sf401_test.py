#!/usr/bin/env python3
"""sf-401 CPU tests (StubReader; no weights, no GPU). Base 292t + listener stack b (313, 315, 314, 316) as in 0.2c,
with and without the stale-fact guard. The learned self-router is stubbed to DECLINE, like the lis-313/314 tests.
Dialogs are invented (fictional people, pets and towns). T = 0.995 throughout.

  s1 unsure correction (CORRECT, "old" named) -> without the guard the old town is stated; with it, lis-314's
     confirm for the new town; "yes" saves it through turn310 (a correct), and the same question then states it
  s2 unsure correction read as a plain STATE (no "old") -> doubt by rule (a), same confirm
  s3 "no" to the offer clears the doubt: the old town is stated again, and no second offer
  s4 a negation (mode NEGATED, no new value) -> the hedge line, which says "not sure"
  s5 a second sister (multi-valued relation) raises no doubt
  s6 another saved person with the same town, named in the question, is not touched
  s7 doubts survive a restart (a new loop on the same state dir)
  s8 a confident correction is saved by turn310 and raises no doubt
  s9 the reader is called once per turn with the guard as without it (a yes to its confirm is not read)
  s10 a later reading that repeats the saved fact clears its doubt
  s11 a question the notebook cannot answer is untouched (lis-314's own confirm path)
  s12 build_02c_sf401's build wrapper installs the guard inside the listener stack and restores build_stack
  s13 pure rules: same_person, doubts_from_frame (a, b, c incl. FORMER, other person, other modes, repeat,
      multi, ungrounded value)

Run: python3 -B scripts/claude_sf401_test.py   (exit 0 iff all pass)
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

SELF122.route122 = lambda q: ("DECLINE", {"reason": "sf401-test-stub"})

import claude_loop292t_agent as T292  # noqa: E402
import claude_lis_stackb as STACK  # noqa: E402
import claude_sf401_agent as SF  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402

HI, LO = 0.999, 0.6
LAYERS = ("313", "315", "314", "316")
CHAT = ({"act": "CHAT", "facts": [], "ask": None}, [], "stub-default", 0.5)


class StubReader:
    def __init__(self, table):
        self.table = dict(table)
        self.calls = []

    def read(self, turn, prev_reply=""):
        self.calls.append((turn, prev_reply))
        return self.table.get(str(turn), CHAT)


def fact(owner, rel, value, mode="ASSERT", old=None):
    f = {"owner": owner, "rel": rel, "value": value, "mode": mode}
    if old:
        f["old"] = old
    return f


def st(facts, confs, act="STATE"):
    return ({"act": act, "facts": facts, "ask": None}, confs, "stub", 0.4)


def ask(**kw):
    kw.setdefault("inverse", False)
    return ({"act": "ASK", "facts": [], "ask": kw}, [], "stub", 0.4)


def fresh(table, guard, d=None, reader=None):
    d = d or tempfile.mkdtemp(prefix="sf401t_")
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    reader = reader or StubReader(table)
    STACK.build_stack(loop, reader, 0.995, layers=LAYERS)
    if guard:
        SF.install_sf401(loop, loop.lis_memo)
    return loop, reader, d


def triples(loop):
    return sorted(tuple(t) for t in L90.notebook_triples(loop.nb))


def say(loop, t):
    r = loop.turn(t)
    return " ".join(r) if isinstance(r, list) else str(r)


def has(loop, s, r, v):
    return (s, r, v) in triples(loop)


T_TEACH = "Brannoc lives in Quillmere."
T_FIX = "Brannoc moved to Veltrow, he's not in Quillmere anymore."
Q_CITY = "Where does Brannoc live?"


def table_city(correction):
    return {T_TEACH: st([fact("Brannoc", "city", "Quillmere")], [HI]),
            T_FIX: correction,
            Q_CITY: ask(owner="Brannoc", rel="city")}


FIX_OLD = st([fact("Brannoc", "city", "Veltrow", mode="CORRECT", old="Quillmere")], [LO], act="CORRECT")
FIX_PLAIN = st([fact("Brannoc", "city", "Veltrow")], [LO])


def s1():
    base, _r, _d = fresh(table_city(FIX_OLD), guard=False)
    say(base, T_TEACH)
    assert has(base, "Brannoc", "city", "Quillmere"), triples(base)
    say(base, T_FIX)
    rep0 = say(base, Q_CITY)
    assert SF._names(rep0, "Quillmere"), "without the guard the old town is stated: " + rep0
    loop, _r, _d = fresh(table_city(FIX_OLD), guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    assert loop.sf401_stats["doubt_b"] == 1, loop.sf401_stats
    rep = say(loop, Q_CITY)
    assert rep == "I think you told me Brannoc's city is Veltrow, is that right?", rep
    rep = say(loop, "yes")
    assert has(loop, "Brannoc", "city", "Veltrow") and not has(loop, "Brannoc", "city", "Quillmere"), triples(loop)
    rep = say(loop, Q_CITY)
    assert SF._names(rep, "Veltrow") and "?" not in rep, rep
    assert loop.sf401_stats["fired_confirm"] == 1 and loop.sf401_stats["offer_yes"] == 1, loop.sf401_stats


def s2():
    loop, _r, _d = fresh(table_city(FIX_PLAIN), guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    assert loop.sf401_stats["doubt_a"] == 1, loop.sf401_stats
    rep = say(loop, Q_CITY)
    assert rep == "I think you told me Brannoc's city is Veltrow, is that right?", rep


def s3():
    loop, _r, _d = fresh(table_city(FIX_PLAIN), guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    say(loop, Q_CITY)
    rep = say(loop, "no")
    assert rep == "Okay, I won't save that.", rep
    assert loop.sf401_stats["cleared_no"] == 1 and loop.sf401_stats["doubts_live"] == 0, loop.sf401_stats
    rep = say(loop, Q_CITY)
    assert SF._names(rep, "Quillmere") and "?" not in rep, rep
    assert loop.sf401_stats["fired"] == 1, loop.sf401_stats


def s4():
    t1, t2, q = "Odila's hamster is Pim.", "Pim is not a hamster at all.", "What is Odila's hamster called?"
    tab = {t1: st([fact("Odila", "pet", "Pim")], [HI]),
           t2: st([fact("Odila", "pet", "Pim", mode="NEGATED")], [LO], act="CORRECT"),
           q: ask(owner="Odila", rel="pet")}
    base, _r, _d = fresh(tab, guard=False)
    say(base, t1)
    say(base, t2)
    rep0 = say(base, q)
    assert SF._names(rep0, "Pim"), rep0
    loop, _r, _d = fresh(tab, guard=True)
    say(loop, t1)
    say(loop, t2)
    assert loop.sf401_stats["doubt_c"] == 1, loop.sf401_stats
    rep = say(loop, q)
    assert rep == "Earlier you told me Odila's pet is Pim, but I think that has changed since, so I'm not sure now.", rep
    assert "not sure" in rep.lower()


def s5():
    t1, t2, q = "My sister is Ilka.", "My sister Maren called today.", "Who is my sister?"
    tab = {t1: st([fact("me", "sister", "Ilka")], [HI]),
           t2: st([fact("me", "sister", "Maren")], [LO]),
           q: ask(owner="me", rel="sister")}
    loop, _r, _d = fresh(tab, guard=True)
    say(loop, t1)
    say(loop, t2)
    assert loop.sf401_stats["doubts_live"] == 0, loop.sf401_stats
    say(loop, q)
    assert loop.sf401_stats["fired"] == 0, loop.sf401_stats


def s6():
    t0 = "Tamsin lives in Quillmere too."
    q = "Where does Tamsin live?"
    tab = dict(table_city(FIX_PLAIN))
    tab[t0] = st([fact("Tamsin", "city", "Quillmere")], [HI])
    tab[q] = ask(owner="Tamsin", rel="city")
    loop, _r, _d = fresh(tab, guard=True)
    say(loop, T_TEACH)
    say(loop, t0)
    say(loop, T_FIX)
    assert loop.sf401_stats["doubts_live"] == 1, loop.sf401_stats
    rep = say(loop, q)
    if SF._names(rep, "Quillmere"):
        assert loop.sf401_stats["fired"] == 0 and loop.sf401_stats["explained_skip"] >= 1, (rep, loop.sf401_stats)
    rep = say(loop, Q_CITY)
    assert "Veltrow" in rep and rep.endswith("?"), rep


def s7():
    loop, _r, d = fresh(table_city(FIX_PLAIN), guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    del loop
    loop2, _r, _d = fresh(table_city(FIX_PLAIN), guard=True, d=d)
    assert loop2.sf401_stats["doubts_live"] == 1, loop2.sf401_stats
    rep = say(loop2, Q_CITY)
    assert "Veltrow" in rep and rep.endswith("?"), rep


def s8():
    fix_sure = st([fact("Brannoc", "city", "Veltrow", mode="CORRECT", old="Quillmere")], [HI], act="CORRECT")
    loop, _r, _d = fresh(table_city(fix_sure), guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    assert has(loop, "Brannoc", "city", "Veltrow") and not has(loop, "Brannoc", "city", "Quillmere"), triples(loop)
    assert loop.sf401_stats["doubts_live"] == 0, loop.sf401_stats
    rep = say(loop, Q_CITY)
    assert SF._names(rep, "Veltrow"), rep


def s9():
    turns = [T_TEACH, "nice weather today", T_FIX, Q_CITY, "Okay thanks!"]
    counts = []
    for guard in (False, True):
        loop, reader, _d = fresh(table_city(FIX_PLAIN), guard=guard)
        for t in turns:
            say(loop, t)
        counts.append(len(reader.calls))
    assert counts == [len(turns), len(turns)], counts
    loop, reader, _d = fresh(table_city(FIX_PLAIN), guard=True)
    for t in [T_TEACH, T_FIX, Q_CITY, "yes", Q_CITY]:   # a yes to a confirm is never read (lis-314's rule)
        say(loop, t)
    assert len(reader.calls) == 4, reader.calls


def s10():
    t3 = "Brannoc still lives in Quillmere, the move fell through."
    tab = dict(table_city(FIX_PLAIN))
    tab[t3] = st([fact("Brannoc", "city", "Quillmere")], [LO])
    loop, _r, _d = fresh(tab, guard=True)
    say(loop, T_TEACH)
    say(loop, T_FIX)
    say(loop, t3)
    assert loop.sf401_stats["cleared_repeat"] == 1 and loop.sf401_stats["doubts_live"] == 0, loop.sf401_stats


def s11():
    t1, q = "My sister is Ilka.", "who's my sister again"
    tab = {t1: st([fact("me", "sister", "Ilka")], [LO]), q: ask(owner="me", rel="sister")}
    loop, _r, _d = fresh(tab, guard=True)
    say(loop, t1)
    rep = say(loop, q)
    assert rep == "I think you told me your sister is Ilka, is that right?", rep
    assert loop.sf401_stats["fired"] == 0, loop.sf401_stats


def s12():
    import types
    import claude_e2e02c as E02C
    import claude_lis319_arms as L319
    orig_build, orig_reader, orig_stack = E02C.build_02c, L319._reader319, STACK.build_stack
    stub = StubReader(table_city(FIX_PLAIN))

    class R3:  # the lis-319 reader's call shape: read(turn, prev, pairs)
        def read(self, turn, prev_reply="", pairs=None):
            return stub.read(turn, prev_reply)

    try:
        L319._reader319 = lambda model: R3()
        E02C.build_02c = lambda sd, a: L319.build_330a_334_r319(sd, a)
        loop = SF.build_02c_sf401(tempfile.mkdtemp(prefix="sf401b_"), types.SimpleNamespace(model="stub"))
    finally:
        E02C.build_02c, L319._reader319 = orig_build, orig_reader
    assert STACK.build_stack is orig_stack
    assert loop.layers330c[0] == "sf401" and loop.sf401_stats["turns"] == 0
    say(loop, T_TEACH)
    say(loop, T_FIX)
    rep = say(loop, Q_CITY)
    assert "Veltrow" in rep and rep.rstrip().endswith("?"), rep
    assert loop.sf401_stats["fired_confirm"] == 1, loop.sf401_stats


def s13():
    assert SF.same_person("USER", "me") and not SF.same_person("USER", "Brannoc")
    assert SF.same_person("Brannoc", "brannoc") and SF.same_person("Brannoc Vell", "Brannoc")
    assert not SF.same_person("Brannoc", "me")
    before = {("Brannoc", "city", "Quillmere"), ("USER", "sister", "Ilka"), ("Odila", "pet", "Pim")}
    turn = "Brannoc moved to Veltrow, not Quillmere."
    new, rep = SF.doubts_from_frame({"act": "STATE", "facts": [fact("brannoc", "city", "Veltrow")]}, turn, before)
    assert [d["rule"] for d in new] == ["a"] and new[0]["new"]["value"] == "Veltrow" and not rep, new
    new, _ = SF.doubts_from_frame({"act": "STATE", "facts": [fact("brannoc", "city", "Farholm")]}, turn, before)
    assert not new, "a value not in the user's words raises no doubt"
    new, _ = SF.doubts_from_frame({"act": "CORRECT", "facts": [
        fact("Brannoc", "home", "Veltrow", mode="CORRECT", old="Quillmere")]}, turn, before)
    assert [d["rule"] for d in new] == ["b"] and new[0]["new"]["rel"] == "city", new
    new, _ = SF.doubts_from_frame({"act": "STATE", "facts": [fact("me", "sister", "Maren")]}, "my sister Maren", before)
    assert not new
    new, _ = SF.doubts_from_frame({"act": "CORRECT", "facts": [fact("Odila", "pet", "Pim", mode="NEGATED")]},
                                  "Pim is not her pet", before)
    assert [d["rule"] for d in new] == ["c"] and new[0]["new"] is None
    new, _ = SF.doubts_from_frame({"act": "CORRECT", "facts": [
        fact("Branoc", "city", "Veltrow", mode="CORRECT", old="Quillmere")]}, turn, before)
    assert not new, "the frame's person must resolve to the saved person"
    for m in ("QUESTION", "SUPPOSE", "REPORTED"):
        new, _ = SF.doubts_from_frame({"act": "STATE", "facts": [
            fact("Brannoc", "city", "Veltrow", mode=m, old="Quillmere")]}, turn, before)
        assert not new, m
    new, _ = SF.doubts_from_frame({"act": "STATE", "facts": [fact("Odila", "pet", "Pim", mode="FORMER")]},
                                  "Pim was Odila's pet years ago", before)
    assert [d["rule"] for d in new] == ["c"] and new[0]["new"] is None, new
    new, _ = SF.doubts_from_frame({"act": "STATE", "facts": [fact("Brannoc", "city", "Farholm", mode="FORMER")]},
                                  "Brannoc used to live in Farholm", before)
    assert not new, "a former value that is not the saved one raises no doubt"
    _, rep = SF.doubts_from_frame({"act": "STATE", "facts": [fact("Brannoc", "city", "Quillmere")]}, turn, before)
    assert rep == [("Brannoc", "city", "Quillmere")]
    new, rep = SF.doubts_from_frame({"act": "ASK", "facts": [fact("brannoc", "city", "Veltrow")]}, turn, before)
    assert not new and not rep


TESTS = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13]


def main() -> int:
    ok = 0
    for fn in TESTS:
        try:
            fn()
            print("PASS", fn.__name__)
            ok += 1
        except Exception:  # noqa: BLE001
            print("FAIL", fn.__name__)
            traceback.print_exc()
    print("sf401 tests: %d/%d passed" % (ok, len(TESTS)))
    return 0 if ok == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
