#!/usr/bin/env python3
"""lis-311 try-out driver (new file only).

Stub part (--stub, no weights): equivalents of the lis-310 scenarios
(T1, T2, T3a, T3b, T3c, T4, T5, T6, T7-blocked-five, T8) against
build_agent311 with a StubReader at threshold 0.995. Exit 0 iff all pass.

Real part (--real --out DIR, needs weights): 30 casual dev turns of our
own (fictional names, 3 conversations x 10 turns: lowercase, two facts in
one message, "our", a correction, a question, a negation, small talk)
through build_agent311 with the real lis-300 Reader on the Mac
(MPS if available). After any ask-back reply the driver sends "yes" as an
adaptive follow-up (marked adaptive:true; not one of the 30). Every turn
row (turn, reply, saved, frame, confs, ms) goes torows.jsonl in --out;
a summary prints median/p90/max ms per turn and the device.

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    --with transformers --with safetensors python -B \
    scripts/claude_lis311_try.py --stub
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

_DEPS = Path(tempfile.gettempdir()) / "lis311deps"


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
            "scripts/claude_lis300_read.py":
            _DEPS / "scripts" / "claude_lis300_read.py",
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

import claude_lis311_agent as A311  # noqa: E402
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


def fresh(table: dict, threshold: float = 0.995):
    d = tempfile.mkdtemp(prefix="lis311t_")
    loop = A311.build_agent311({"state_dir": d, "lis311": {
        "reader": StubReader(table), "threshold": threshold}})
    return loop, d


def triples(loop):
    return sorted(map(list, L90.notebook_triples(loop.nb)))


def events(loop):
    return len(loop.nb.events)


def log_rows(d):
    p = Path(d) / "lis311_log.jsonl"
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
        {"owner": "Mira", "rel": "city", "value": "Braga",
         "mode": "PLAN"}],
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
    import claude_loop292_agent as B292  # noqa: E402 (validity check)

    turns = ["Mira's city is Lisbon.", "Mira's city is Porto.",
             "Mira's city is Braga.", "Mira's city is Faro.",
             "So Mira's city is Aveiro."]
    for t in turns:  # validity: the raw base WOULD write each of these
        d0 = tempfile.mkdtemp(prefix="lis311raw_")
        raw = B292.build_agent292({"state_dir": d0})
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


STUB_TESTS = [("T1 two-facts-save-2", t1_two_facts),
              ("T2 whose-ask", t2_whose),
              ("T3a askback-yes-saves-1", t3a_askback_yes),
              ("T3b askback-no-saves-0", t3b_askback_no),
              ("T3c askback-dropped-on-other", t3c_askback_dropped),
              ("T4 negation-saves-0", t4_negation),
              ("T5 check-answered-saves-0", t5_check),
              ("T6 question-answered", t6_question),
              ("T7 blocked-five-zero-writes", t7_blocked_five),
              ("T8 unparsed-saves-0", t8_unparsed)]


def run_stub() -> int:
    print("lis-311 stub scenarios (StubReader, threshold %.3f)" %
          A311.DEFAULT_THRESHOLD311)
    passed, failed = 0, []
    for name, fn in STUB_TESTS:
        try:
            detail = fn()
            print("PASS %s :: %s" % (name, detail))
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print("FAIL %s :: %r" % (name, exc))
            traceback.print_exc()
            failed.append(name)
    print("summary: %d/%d passed" % (passed, len(STUB_TESTS)))
    return 0 if not failed else 1


# ------------------------------------------------------- real-model try-out

CONVS = [
    ("A-pets", [
        "hey!",
        "my dog is pip.",
        "my cat is fig.",
        "my sisters are mira and tal.",
        "our dog is pip.",
        "mira's dog is pip.",
        "whose dog is pip?",
        "so mira's dog is pip, right?",
        "mira doesn't have a cat.",
        "thanks, bye for now.",
    ]),
    ("B-family", [
        "hi there",
        "my brother is dev and my cousin is rui.",
        "my mother is ana.",
        "actually my mother is lena.",
        "kofi has no kids.",
        "tal says his boss is mara.",
        "who is tal's boss?",
        "imagine dev had a boat.",
        "i want to visit lisbon.",
        "cool, talk later.",
    ]),
    ("C-mixed", [
        "good morning",
        "my friend is zoe.",
        "zoe's cat is mochi.",
        "no wait, zoe's cat is fig.",
        "our house is on the hill.",
        "is zoe's cat fig?",
        "ok got it.",
        "dev is my uncle.",
        "my uncle works in porto.",
        "see you soon.",
    ]),
]

RECORDED_SHA311 = ("112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0"
                   "be8285324")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(data, p):
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def run_real(model_dir: str, out: str) -> int:
    import torch  # noqa: E402

    model_path = Path(model_dir).expanduser()
    safep = model_path / "model.safetensors"
    got = sha_file(safep)
    print("weights sha256: %s" % got)
    if got != RECORDED_SHA311:
        print("WEIGHTS MISMATCH: expected %s" % RECORDED_SHA311)
        return 2
    print("weights match lis-300 RESULTS.md; loading reader ...")
    import claude_lis300_read as READ  # noqa: E402

    reader = READ.Reader(str(model_path))
    dev = getattr(reader, "dev", "?")
    print("reader device: %s" % dev)
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    rows_path = outdir / "rows.jsonl"
    n_scripted = sum(len(t) for _, t in CONVS)
    ms_all, n_yes = [], 0
    with open(rows_path, "w", encoding="utf-8") as fh:
        for conv, turns in CONVS:
            d = tempfile.mkdtemp(prefix="lis311real_")
            loop = A311.build_agent311({"state_dir": d, "lis311": {
                "reader": reader, "threshold": 0.995}})
            queue = [(t, False) for t in turns]
            idx = 0
            while queue:
                turn, adaptive = queue.pop(0)
                idx += 1
                t0 = time.perf_counter()
                reply = loop.turn(turn)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                ms_all.append(ms)
                if adaptive:
                    n_yes += 1
                row = log_rows(d)[-1] if log_rows(d) else {}
                rec = {"conv": conv, "n": idx, "turn": turn,
                       "reply": list(reply),
                       "saved": row.get("wrote", []),
                       "frame": row.get("frame"),
                       "confs": row.get("confs"),
                       "decision": row.get("decision"),
                       "ms": ms, "adaptive": adaptive}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print("--- [%s#%d] user: %r%s" % (conv, idx, turn,
                      " (adaptive yes)" if adaptive else ""))
                print("    reply: %r saved=%r frame=%s confs=%s ms=%s" % (
                    " ".join(reply), rec["saved"], json.dumps(rec["frame"]),
                    rec["confs"], ms))
                if (reply and reply[0].startswith("Just to check:")
                        and not queue[:1] == [("yes", False)]):
                    queue.insert(0, ("yes", True))
            print(" Conv %s notebook: %s" % (conv, triples(loop)))
    n_total = n_scripted + n_yes
    print("device: %s" % dev)
    print("scripted turns: %d adaptive yes turns: %d total: %d" % (
        n_scripted, n_yes, n_total))
    print("ms per turn: median=%.1f p90=%.1f max=%.1f" % (
        statistics.median(ms_all), pct(ms_all, 90), max(ms_all)))
    print("rows -> %s" % rows_path)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lis-311 try-out driver")
    ap.add_argument("--stub", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--model-dir", default=A311.DEFAULT_MODEL311)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.real:
        if not args.out:
            ap.error("--real needs --out DIR")
        return run_real(args.model_dir, args.out)
    return run_stub()


if __name__ == "__main__":
    sys.exit(main())
