#!/usr/bin/env python3
"""lis-310 unit tests (StubReader; no weights needed).

Covers (fresh agent + state dir per case unless noted):
  T1 two facts in one turn save 2
  T2 our/we -> whose-ask, nothing saved
  T3a low confidence -> ask-back, then "yes" saves 1
  T3b low confidence -> ask-back, then "no" saves 0
  T4 a negation saves 0
  T5 "so X is Y" (CHECK) is answered by the base and saves 0
  T6 a question is answered from the notebook (saves 0)
  T7 the base chain's writes are blocked on 5 rule-chain-teachable turns
     (each turn is first shown to write on the raw 291 base, then shown
     to write nothing under 310; P310.2 = 0 base-chain writes here)
  T8 an unparsed frame saves 0 (exact sorry-reply)
  T9 the chatdemo server could load this agent (load_agent plug shape) and
     the demo build (server-style) runs a turn

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_lis310_test.py
Exit 0 iff every test passes. Prints one line per test plus a summary.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

_DEPS = Path(tempfile.gettempdir()) / "lis310deps"


def ensure_deps() -> None:
    """Copies of frozen lis-300 modules for this worktree (never checks out,
    merges or pushes any branch; local git objects only, no network)."""
    if str(_DEPS / "scripts") in sys.path:
        return
    (_DEPS / "scripts").mkdir(parents=True, exist_ok=True)
    (_DEPS / "design" / "v3" / "60-listener").mkdir(parents=True,
                                                   exist_ok=True)
    jobs = {"scripts/claude_lis300_common.py":
            _DEPS / "scripts" / "claude_lis300_common.py",
            "scripts/claude_lis300_compiler.py":
            _DEPS / "scripts" / "claude_lis300_compiler.py",
            "design/v3/60-listener/relation-names.txt":
            _DEPS / "design" / "v3" / "60-listener" / "relation-names.txt"}
    for src, dst in jobs.items():
        if not dst.exists():
            r = subprocess.run(["git", "-C", str(WORKTREE), "show",
                                "origin/main:" + src],
                               capture_output=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError("cannot extract " + src)
            dst.write_bytes(r.stdout)
    sys.path.insert(0, str(_DEPS / "scripts"))


ensure_deps()

import claude_lis310_agent as A310  # noqa: E402
import fable_loop90_agent as L90  # noqa: E402


class StubReader:
    """Fixed frames per turn text (no weights). Unmapped turns -> CHAT."""

    def __init__(self, table: dict, default=None):
        self.table = dict(table)
        self.calls: list = []
        self.default = default or ({"act": "CHAT", "facts": [], "ask": None},
                                   [], "stub-default", 0.5)

    def read(self, turn, prev_reply=""):
        self.calls.append((turn, prev_reply))
        return self.table.get(str(turn), self.default)


def fresh(table: dict, threshold: float = 0.99):
    d = tempfile.mkdtemp(prefix="lis310t_")
    loop = A310.build_agent310({"state_dir": d, "lis310": {
        "reader": StubReader(table), "threshold": threshold}})
    return loop, d


def triples(loop):
    return sorted(map(list, L90.notebook_triples(loop.nb)))


def events(loop):
    return len(loop.nb.events)


def log_rows(d):
    p = Path(d) / "lis310_log.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


HI = 0.999
LO = 0.5

T1 = {"My sisters are Mira and Tal.":
      ({"act": "STATE", "facts": [
          {"owner": "me", "rel": "sister", "value": "Mira", "mode": "ASSERT"},
          {"owner": "me", "rel": "sister", "value": "Tal", "mode": "ASSERT"}],
        "ask": None}, [HI, HI], "stub", 0.4)}
T2 = {"Our dog is Pip.":
      ({"act": "STATE", "facts": [
          {"owner": "we", "rel": "dog", "value": "Pip", "mode": "ASSERT"}],
        "ask": None}, [HI], "stub", 0.4)}
T3 = {"Mira's dog is Pip.":
      ({"act": "STATE", "facts": [
          {"owner": "Mira", "rel": "dog", "value": "Pip", "mode": "ASSERT"}],
        "ask": None}, [LO], "stub", 0.4)}
T4 = {"Mira doesn't have a dog.":
      ({"act": "NEGATE", "facts": [
          {"owner": "Mira", "rel": "dog", "value": "Pip", "mode": "NEGATED"}],
        "ask": None}, [HI], "stub", 0.4)}
TEACH_DOG = {"Mira's dog is Pip.":
             ({"act": "STATE", "facts": [
                 {"owner": "Mira", "rel": "dog", "value": "Pip",
                  "mode": "ASSERT"}],
               "ask": None}, [HI], "stub", 0.4)}
T5 = dict(TEACH_DOG, **{"So Mira's dog is Pip.":
      ({"act": "CHECK", "facts": [
          {"owner": "Mira", "rel": "dog", "value": "Pip", "mode": "CHECK"}],
        "ask": None}, [HI], "stub", 0.4)})
T6 = dict(TEACH_DOG, **{"Whose dog is Pip?":
      ({"act": "ASK", "facts": [],
        "ask": {"owner": "Pip", "rel": "dog", "inverse": True}},
       [], "stub", 0.4)})
T7 = {
    "Mira's city is Lisbon.":
    ({"act": "SUPPOSE", "facts": [
        {"owner": "Mira", "rel": "city", "value": "Lisbon",
         "mode": "SUPPOSE"}],
      "ask": None}, [HI], "stub", 0.4),
    "Mira's city is Porto.":
    ({"act": "NEGATE", "facts": [
        {"owner": "Mira", "rel": "city", "value": "Porto",
         "mode": "NEGATED"}],
      "ask": None}, [HI], "stub", 0.4),
    "Mira's city is Braga.":
    ({"act": "PLAN", "facts": [
        {"owner": "Mira", "rel": "city", "value": "Braga", "mode": "PLAN"}],
      "ask": None}, [HI], "stub", 0.4),
    "Mira's city is Faro.":
    ({"act": "STATE", "facts": [
        {"owner": "Mira", "rel": "city", "value": "Faro",
         "mode": "REPORTED"}],
      "ask": None}, [HI], "stub", 0.4),
    "So Mira's city is Aveiro.":
    ({"act": "CHECK", "facts": [
        {"owner": "Mira", "rel": "city", "value": "Aveiro",
         "mode": "CHECK"}],
      "ask": None}, [HI], "stub", 0.4),
}
T8 = {"Blorpt wobble fnord.": (None, [], "stub-unparsed", 0.4)}


def t1_two_facts():
    loop, d = fresh(T1)
    r = loop.turn("My sisters are Mira and Tal.")
    tr = triples(loop)
    assert tr == [["USER", "sister", "Mira"], ["USER", "sister", "Tal"]], tr
    assert any("Saved" in l for l in r), r
    rows = log_rows(d)
    assert len(rows) == 1 and rows[0]["decision"] == "write", rows
    return "saved=%d reply=%r" % (len(tr), " ".join(r))


def t2_whose():
    loop, d = fresh(T2)
    r = loop.turn("Our dog is Pip.")
    assert triples(loop) == [], triples(loop)
    assert r == ["Whose dog is Pip, yours or someone else's?"], r
    return "reply=%r" % (" ".join(r),)


def t3a_askback_yes():
    loop, d = fresh(T3)
    r1 = loop.turn("Mira's dog is Pip.")
    assert triples(loop) == [], triples(loop)
    assert r1 == ["Just to check: is Mira's dog Pip?"], r1
    r2 = loop.turn("yes")
    tr = triples(loop)
    assert tr == [["Mira", "dog", "Pip"]], (r2, tr)
    assert any("Saved" in l for l in r2), r2
    return "ask=%r yes=%r" % (" ".join(r1), " ".join(r2))


def t3b_askback_no():
    loop, d = fresh(T3)
    r1 = loop.turn("Mira's dog is Pip.")
    assert r1 == ["Just to check: is Mira's dog Pip?"], r1
    r2 = loop.turn("no")
    assert triples(loop) == [], triples(loop)
    assert r2 == ["Okay, I won't save that."], r2
    return "ask + no -> 0 triples"


def t3c_askback_dropped():
    table = dict(T3)
    table["My sister is Mira."] = (
        {"act": "STATE", "facts": [
            {"owner": "me", "rel": "sister", "value": "Mira",
             "mode": "ASSERT"}],
         "ask": None}, [HI], "stub", 0.4)
    loop, d = fresh(table)
    r1 = loop.turn("Mira's dog is Pip.")
    assert r1 == ["Just to check: is Mira's dog Pip?"], r1
    # not yes/no: drops the pending dog fact, processes this turn normally
    r2 = loop.turn("My sister is Mira.")
    assert triples(loop) == [["USER", "sister", "Mira"]], (r2, triples(loop))
    assert any("Saved" in l for l in r2), r2
    return "non-yes drops pending, next turn saves normally"


def t4_negation():
    loop, d = fresh(T4)
    r = loop.turn("Mira doesn't have a dog.")
    assert triples(loop) == [], (r, triples(loop))
    assert any(r), "empty reply"
    return "reply=%r" % (" ".join(r),)


def t5_check():
    loop, d = fresh(T5)
    r1 = loop.turn("Mira's dog is Pip.")
    assert triples(loop) == [["Mira", "dog", "Pip"]], (r1, triples(loop))
    e0 = events(loop)
    r2 = loop.turn("So Mira's dog is Pip.")
    assert events(loop) == e0 and triples(loop) == [["Mira", "dog", "Pip"]], \
        (r2, triples(loop))
    assert any("Pip" in l or "already" in l for l in r2), r2
    return "base reply=%r" % (" ".join(r2),)


def t6_question():
    loop, d = fresh(T6)
    loop.turn("Mira's dog is Pip.")
    e0 = events(loop)
    r = loop.turn("Whose dog is Pip?")
    assert "Pip" in " ".join(r) and "Mira" in " ".join(r), r
    assert events(loop) == e0, (r, events(loop) - e0)
    return "answer=%r" % (" ".join(r),)


def t7_blocked_five():
    import claude_loop291_agent as B291  # noqa: E402 (validity check)

    turns = ["Mira's city is Lisbon.", "Mira's city is Porto.",
             "Mira's city is Braga.", "Mira's city is Faro.",
             "So Mira's city is Aveiro."]
    for t in turns:  # validity: the raw base WOULD write each of these
        d0 = tempfile.mkdtemp(prefix="lis310raw_")
        raw = B291.build_agent291({"state_dir": d0})
        e0 = len(raw.nb.events)
        raw.turn(t)
        assert len(raw.nb.events) > e0, ("not teachable: %r" % t)
    loop, d = fresh(T7)
    base_writes = 0
    for t in turns:
        e0 = events(loop)
        r = loop.turn(t)
        grew = events(loop) - e0
        base_writes += grew
        assert triples(loop) == [], (t, r, triples(loop))
        assert grew == 0, (t, r, grew)
        assert any(r), ("empty reply: %r" % t)
    assert base_writes == 0, base_writes
    return "5 turns, base-chain writes=%d" % base_writes


def t8_unparsed():
    loop, d = fresh(T8)
    r = loop.turn("Blorpt wobble fnord.")
    assert triples(loop) == [], triples(loop)
    assert r == ["Sorry, I didn't catch that. Could you say it another "
                 "way?"], r
    return "reply exact"


def t9_chatdemo_load():
    import fable_marks123_all as M  # noqa: E402

    mod, dcls, build_fn, default_cfg = M.load_agent(
        str(HERE / "claude_lis310_agent.py"))
    assert dcls is not None and dcls.__name__ == "Loop310Daemon", dcls
    assert build_fn is not None and build_fn.__name__ == "build_agent310"
    assert isinstance(default_cfg, dict) and "lis310" in default_cfg
    sys.path.insert(0, str(HERE))
    import claude_lis310_demo as DEMO  # noqa: E402

    d = tempfile.mkdtemp(prefix="lis310demo_")
    daemon = DEMO.build_demo(reader=StubReader(T1), state_dir=d)
    daemon.process_file(_write_inbox(d, "My sisters are Mira and Tal."))
    reply = (Path(d) / "outbox" / "m0000.txt").read_text(
        encoding="utf-8").strip()
    assert "Saved" in reply, reply
    assert triples(daemon.loop) == [["USER", "sister", "Mira"],
                                    ["USER", "sister", "Tal"]]
    return "daemon=%s reply=%r" % (dcls.__name__, reply)


def _write_inbox(d, text):
    inbox = Path(d) / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    p = inbox / "m0000.txt"
    p.write_text(text, encoding="utf-8")
    return p


TESTS = [("T1 two-facts-save-2", t1_two_facts),
         ("T2 whose-ask", t2_whose),
         ("T3a askback-yes-saves-1", t3a_askback_yes),
         ("T3b askback-no-saves-0", t3b_askback_no),
         ("T3c askback-dropped-on-other", t3c_askback_dropped),
         ("T4 negation-saves-0", t4_negation),
         ("T5 check-answered-saves-0", t5_check),
         ("T6 question-answered", t6_question),
         ("T7 blocked-five-zero-writes", t7_blocked_five),
         ("T8 unparsed-saves-0", t8_unparsed),
         ("T9 chatdemo-load", t9_chatdemo_load)]


def main() -> int:
    print("lis-310 unit tests (StubReader, threshold %.2f)" %
          A310.DEFAULT_THRESHOLD310)
    passed, failed = 0, []
    for name, fn in TESTS:
        try:
            detail = fn()
            print("PASS %s :: %s" % (name, detail))
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print("FAIL %s :: %r" % (name, exc))
            traceback.print_exc()
            failed.append(name)
    print("summary: %d/%d passed" % (passed, len(TESTS)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
