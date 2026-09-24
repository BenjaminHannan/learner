#!/usr/bin/env python3
"""lis-313 CPU tests (StubReader; no weights, no GPU).

Base: 292t (build_agent292t) + install_turn313. The learned self-router's
weights are not needed: this TEST file stubs fable_self122.route122 to
("DECLINE", ...) exactly like the cloud smoke runs do. The agent file never
stubs anything.

Dialogs are invented for these tests (fictional people and pets).

  S1 teach, then ask in words the rule chain can't parse -> reader answers
  S2 plain question the rule chain answers -> agree, rule reply kept
  S3 two-hop "via" question the rule chain can't parse -> reader answers
  S4 yes/no, asked value matches -> "Yes, ..."
  S5 yes/no, asked value differs -> "No, ..." (with the stored value)
  S6 lookup miss (nothing taught) -> rule reply kept, reader_miss
  S7 inverse question -> rule reply kept, inverse_skipped
  S8 reader reads a different relation than the rule chain answered
     -> rule reply kept, disagree
  S9 no question turn writes: every ASK/CHECK turn leaves the event count
     unchanged, including an ASK-labelled turn the rule chain would teach
  S10 the reader is called exactly once per turn (none on an ask-back yes)
     and the 313 log sits next to turn310's log
  S11 owner typed in lower case finds the capitalised entity

Run (cloud box):
  /tmp/claude-0/venv311/bin/python -B scripts/claude_lis313_test.py
Exit 0 iff every test passes.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fable_self122 as SELF122  # noqa: E402

# Test-only stub for the learned self-router (weights not on this box).
SELF122.route122 = lambda q: ("DECLINE", {"reason": "lis313-test-stub"})

import claude_loop292t_agent as T292  # noqa: E402
import claude_lis313_agent as A313  # noqa: E402

HI = 0.999
CHAT = ({"act": "CHAT", "facts": [], "ask": None}, [], "stub-default", 0.5)


class StubReader:
    """Fixed frames per turn text (no weights). Unmapped turns -> CHAT."""

    def __init__(self, table: dict):
        self.table = dict(table)
        self.calls: list = []

    def read(self, turn, prev_reply=""):
        self.calls.append((turn, prev_reply))
        return self.table.get(str(turn), CHAT)


def st(owner, rel, value, conf=HI):
    return ({"act": "STATE", "facts": [{"owner": owner, "rel": rel,
                                        "value": value, "mode": "ASSERT"}],
             "ask": None}, [conf], "stub", 0.4)


def ask(**kw):
    kw.setdefault("inverse", False)
    return ({"act": "ASK", "facts": [], "ask": kw}, [], "stub", 0.4)


def fresh(table: dict):
    d = tempfile.mkdtemp(prefix="lis313t_")
    cfg = copy.deepcopy(T292.DEFAULT_CONFIG292T)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    loop = T292.build_agent292t(cfg)
    reader = StubReader(table)
    A313.install_turn313(loop, reader, threshold=0.995)
    return loop, reader, d


def ev(loop):
    return len(loop.nb.events)


def log313(loop):
    p = Path(loop.lis313_log_path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


TEACH = {
    "My brother is Oskar.": st("me", "brother", "Oskar"),
    "Oskar's cat is Biscuit.": st("Oskar", "cat", "Biscuit"),
    "My aunt is Hedda.": st("me", "aunt", "Hedda"),
}


def teach_all(loop):
    for t in TEACH:
        loop.turn(t)


def run_asks(table_asks: dict, turns: list):
    loop, reader, d = fresh(dict(TEACH, **table_asks))
    teach_all(loop)
    out = []
    for t in turns:
        e0 = ev(loop)
        reply = loop.turn(t)
        out.append((t, reply, ev(loop) - e0))
    return loop, reader, out


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def s1():
    q = "that sibling of mine, the boy, what's he called?"
    loop, _r, out = run_asks({q: ask(owner="me", rel="brother")}, [q])
    reply = out[0][1]
    check(reply == ["Your brother is Oskar."], reply)
    check(loop.lis313_stats["reader_answered"] == 1, loop.lis313_stats)
    check(log313(loop)[-1]["decision"] == "reader-answered", log313(loop))
    check(A313.is_abstain313(" ".join(log313(loop)[-1]["rule_reply"])),
          "rule chain did not abstain in S1")


def s2():
    q = "Who is my brother?"
    loop, _r, out = run_asks({q: ask(owner="me", rel="brother")}, [q])
    check(out[0][1] == ["Your brother is Oskar."], out)
    check(loop.lis313_stats["agree"] == 1, loop.lis313_stats)
    check(log313(loop)[-1]["rule_reply"] == out[0][1], "rule reply replaced")


def s3():
    q = "that kitty my brother has, name?"
    loop, _r, out = run_asks(
        {q: ask(owner="me", via="brother", rel="cat")}, [q])
    check(out[0][1] == ["Your brother's cat is Biscuit."], out)
    check(loop.lis313_stats["reader_answered"] == 1, loop.lis313_stats)
    look = log313(loop)[-1]["lookup"]
    check(look["subject"] == "USER" and look["relations"] == ["brother",
                                                                "cat"], look)


def s4():
    q = "does Oskar's cat go by biscuit"
    loop, _r, out = run_asks(
        {q: ask(owner="Oskar", rel="cat", value="biscuit")}, [q])
    check(out[0][1] == ["Yes, Oskar's cat is Biscuit."], out)
    check(loop.lis313_stats["reader_answered"] == 1, loop.lis313_stats)


def s5():
    q = "does Oskar's cat go by Pickles"
    q2 = "my aunt, she's Greta or not?"
    loop, _r, out = run_asks(
        {q: ask(owner="Oskar", rel="cat", value="Pickles"),
         q2: ask(owner="me", rel="aunt", value="Greta")}, [q, q2])
    check(out[0][1] == ["No, Oskar's cat is Biscuit."], out)
    check(out[1][1] == ["No, your aunt is Hedda."], out)
    check(loop.lis313_stats["reader_answered"] == 2, loop.lis313_stats)


def s6():
    q = "what about my cousin"
    q2 = "and Oskar's boat, what's that?"
    loop, _r, out = run_asks({q: ask(owner="me", rel="cousin"),
                              q2: ask(owner="Oskar", rel="boat")}, [q, q2])
    rows = log313(loop)
    check(loop.lis313_stats["reader_miss"] == 2, loop.lis313_stats)
    for (t, reply, _d), row in zip(out, rows[-2:]):
        check(row["decision"] == "miss-keep-rule", row)
        check(reply == row["rule_reply"], (reply, row))
        check("Oskar" not in " ".join(reply) or t == q2, reply)
    check(rows[-1]["lookup"]["status"] != "OK", rows[-1])


def s7():
    q = "Whose cat is Biscuit?"
    loop, _r, out = run_asks(
        {q: ask(owner="Biscuit", rel="cat", inverse=True)}, [q])
    row = log313(loop)[-1]
    check(row["decision"] == "inverse-keep-rule", row)
    check(loop.lis313_stats["inverse_skipped"] == 1, loop.lis313_stats)
    check(loop.lis313_stats["reader_answered"] == 0, loop.lis313_stats)


def s8():
    q = "Who is my brother?"  # rule chain answers Oskar
    loop, _r, out = run_asks({q: ask(owner="me", rel="aunt")}, [q])
    check(out[0][1] == ["Your brother is Oskar."], out)
    check(loop.lis313_stats["disagree"] == 1, loop.lis313_stats)


def s9():
    qs = {
        "that sibling of mine, the boy, what's he called?":
            ask(owner="me", rel="brother"),
        "that kitty my brother has, name?":
            ask(owner="me", via="brother", rel="cat"),
        "does Oskar's cat go by Pickles": ask(owner="Oskar", rel="cat",
                                              value="Pickles"),
        "what about my cousin": ask(owner="me", rel="cousin"),
        "Whose cat is Biscuit?": ask(owner="Biscuit", rel="cat",
                                     inverse=True),
        # the rule chain would TEACH this sentence; the reader calls it ASK
        "My sister is Freya.": ask(owner="me", rel="sister"),
        "So Oskar's cat is Biscuit.": (
            {"act": "CHECK", "facts": [{"owner": "Oskar", "rel": "cat",
                                        "value": "Biscuit",
                                        "mode": "CHECK"}], "ask": None},
            [HI], "stub", 0.4),
    }
    loop, _r, out = run_asks(qs, list(qs))
    for t, reply, delta in out:
        check(delta == 0, "question turn wrote: %r -> %r" % (t, reply))
    check(loop.lis313_stats["check_seen"] == 1, loop.lis313_stats)
    check(loop.lis313_stats["asks"] == 6, loop.lis313_stats)


def s10():
    low = st("Hedda", "dog", "Tuffy", conf=0.5)  # low conf -> ask-back
    q = "that sibling of mine, the boy, what's he called?"
    loop, reader, d = fresh(dict(TEACH, **{
        "Hedda's dog is Tuffy.": low, q: ask(owner="me", rel="brother")}))
    teach_all(loop)
    turns = ["Hedda's dog is Tuffy.", "yes", q]
    n0 = len(reader.calls)
    replies = [loop.turn(t) for t in turns]
    # ask-back "yes" needs no read: 2 reads for 3 turns
    check(len(reader.calls) - n0 == 2, reader.calls)
    check(loop.lis313_proxy.fallback_reads == 0, "proxy fell through")
    check(any("Tuffy" in " ".join(r) for r in replies[:2]), replies)
    check(replies[2] == ["Your brother is Oskar."], replies)
    # prev for the next read is the reply turn313 gave
    loop.turn("hello there")
    check(reader.calls[-1][1] == "Your brother is Oskar.", reader.calls[-1])
    check(Path(loop.lis313_log_path).parent
          == Path(loop.lis310_log_path).parent, "log folder differs")
    check(Path(loop.lis313_log_path).exists(), "no 313 log")
    check(loop.lis313_stats["reads"] == len(reader.calls), "read count")


def s11():
    q = "and oskar's pet cat is who"
    loop, _r, out = run_asks({q: ask(owner="oskar", rel="cat")}, [q])
    check(" ".join(out[0][1]).find("Biscuit") >= 0, out)


TESTS = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11]


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
    print("lis313 tests: %d/%d passed" % (ok, len(TESTS)))
    return 0 if ok == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
