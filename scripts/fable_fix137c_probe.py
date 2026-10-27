#!/usr/bin/env python3
"""Experiment 137c T1+T2 probe -- hypothetical guard twins, titles, others.

58 sealed cases (written before any registered run):
  H 30 hypothetical sessions (all 11 closed markers x plain + filler twin,
     6 relations: boss/mother/city/song/movie/friend). Pure sessions:
     [hypo teach, question about the same fact] -- turn 1 must reply the
     exact sealed sentence with 0 writes; turn 2 must NOT answer the
     pretend value and the notebook must stay empty. Conflict sessions:
     [real teach, hypo teach of a rival value, question] -- the question
     must answer the REAL value; triples hold only the real fact.
  N 12 titles/names containing a marker word later in the sentence
     ("Kim's song is Imagine", "Kim's film is What If", subject "What If",
     value "Suppose"/"Pretend" ...) -- reply+triples identical to loop137b.
  O 16 other teaches/questions ("Btw./So/Hi." phone teaches 137b now
     saves, "Say Kim's ...", bare-"If ..." decline, plain teaches and
     questions) -- reply+triples identical to loop137b.
T2 (same run): 0 writes on every hypothetical turn (0 wrong writes).

Harness: fresh in-process loop per session (build_agent137c /
build_agent137b, state_dir + sleep_threshold=100000, loop.turn, triples
via notebook_triples). Every case reported, never averaged.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137c_probe.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix137c_hypo as H137C  # noqa: E402 (rule under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137b_agent as L137B  # noqa: E402 (frozen base, read-only)
import fable_loop137c_agent as L137C  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hypo137c-20260922"

EXACT = H137C.HYPO_REPLY

# (marker, filler_prefix) x 11 markers; filler twins use "Ok, so ...".
HYPO_TEACHES: list[tuple[str, str, str, str]] = [
    ("Suppose", "", "boss", "Lee"),
    ("Suppose", "Ok, so ", "mother", "Beth"),
    ("Supposing", "", "city", "Paris"),
    ("Supposing", "And ", "boss", "Lee"),
    ("Imagine", "", "boss", "Lee"),
    ("Imagine", "So ", "song", "Halo"),
    ("Pretend", "", "mother", "Beth"),
    ("Pretend", "Ok, ", "city", "Paris"),
    ("Pretend that", "", "boss", "Lee"),
    ("Pretend that", "So, ", "movie", "Dune"),
    ("Let's say", "", "friend", "Kai"),
    ("Let's say", "And ", "boss", "Lee"),
    ("Lets say", "", "city", "Paris"),
    ("Hypothetically", "", "boss", "Lee"),
    ("Hypothetically", "Ok, so ", "mother", "Beth"),
    ("In theory", "", "song", "Halo"),
    ("In theory", "So ", "boss", "Lee"),
    ("What if", "", "boss", "Lee"),
    ("What if", "Ok, ", "movie", "Dune"),
    ("Say that", "", "mother", "Beth"),
    ("Say that", "And, ", "friend", "Kai"),
    ("SUPPOSE", "", "city", "Quito"),
]

CONFLICTS: list[tuple[str, str, str, str, str]] = [
    ("Suppose", "boss", "Ann", "Lee"),
    ("Imagine", "mother", "Beth", "June"),
    ("What if", "city", "Paris", "Quito"),
    ("Pretend that", "song", "Halo", "Gold"),
    ("In theory", "movie", "Dune", "Jaws"),
    ("Say that", "friend", "Kai", "Rae"),
    ("Hypothetically", "boss", "Ann", "Bob"),
    ("Let's say", "city", "Paris", "Lima"),
]

NAMES_N = [
    "Kim's song is Imagine.",
    "Kim's film is What If.",
    "Kim's book is Suppose.",
    "Lee's song is Pretend.",
    "Ann's movie is Say That.",
    "Kim's city is Hypothetically.",
    "What If's boss is Kim.",
    "Imagine's mother is Beth.",
    "Kim's boss is Suppose.",
    "Kim's mother is Pretend That.",
    "Lee's friend is In Theory.",
    "Kim's song is Lets Say.",
]

OTHERS_O = [
    "Kim's boss is Ann.",
    "Btw. Kim's boss is Lee.",
    "So Kim's boss is Lee.",
    "Hi. Kim's boss is Lee.",
    "Say Kim's boss is Lee.",
    "If Kim's boss is Lee then Lee is busy.",
    "Kim's mother is Beth.",
    "New York's boss is Adams.",
    "Mary Ann's boss is Bob.",
    "Tom's boss is Mary Ann.",
    "A. A. Milne's child is Christopher Robin Milne.",
    "St. Louis's boss is Bob.",
    "Kim's city is New York.",
    "Ann's boss is Jean-Luc Picard.",
    "Okay Kim's boss is Lee.",
    "And Kim's boss is Lee.",
]


def fresh(kind: str):
    cfg = copy.deepcopy(L137C.DEFAULT_CONFIG137C if kind == "137c"
                        else L137B.DEFAULT_CONFIG137B)
    tmp = tempfile.mkdtemp(prefix=f"probe137c_{kind}_")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = (L137C.build_agent137c(cfg) if kind == "137c"
            else L137B.build_agent137b(cfg))
    return loop


def seq(kind: str, turns: list[str]) -> tuple[list[str], list[list]]:
    loop = fresh(kind)
    replies = [" ".join(loop.turn(t)) for t in turns]
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, triples


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows: list[dict] = []
    fails = 0

    # H-pure: [hypo, question] -- exact reply, 0 writes, q avoids pretend.
    for i, (marker, pre, rel, val) in enumerate(HYPO_TEACHES):
        hypo = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        t1 = time.time()
        loop = fresh("137c")
        r1 = " ".join(loop.turn(hypo))
        w1 = [list(t) for t in L90.notebook_triples(loop.nb)]
        r2 = " ".join(loop.turn(q))
        w2 = [list(t) for t in L90.notebook_triples(loop.nb)]
        ok = (r1 == EXACT) and (w1 == []) and (w2 == []) and (val not in r2)
        rows.append({"id": f"H-{i:02d}", "kind": "hypo-pure",
                     "marker": marker, "hypo": hypo, "q": q,
                     "reply1": r1, "reply2": r2, "writes": w2,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL H-{i:02d} {hypo!r} -> {r1!r} / {r2!r} {w2}",
                  flush=True)

    # H-conflict: [real, hypo rival, question] -- real value wins.
    for i, (marker, rel, real, rival) in enumerate(CONFLICTS):
        turns = [f"Kim's {rel} is {real}.",
                 f"{marker} Kim's {rel} is {rival}.",
                 f"What is Kim's {rel}?"]
        t1 = time.time()
        replies, triples = seq("137c", turns)
        ok = (replies[0] == f"Saved: Kim's {rel} is {real}."
              and replies[1] == EXACT
              and replies[2] == f"Kim's {rel} is {real}."
              and triples == [["Kim", rel, real]])
        rows.append({"id": f"H-C{i:02d}", "kind": "hypo-conflict",
                     "marker": marker, "turns": turns, "replies": replies,
                     "triples": triples,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL H-C{i:02d} {replies} {triples}", flush=True)

    # N: marker-word titles/names -- identical to loop137b.
    for i, teach in enumerate(NAMES_N):
        turns = [teach]
        t1 = time.time()
        r_n, w_n = seq("137c", turns)
        r_b, w_b = seq("137b", turns)
        ok = (r_n == r_b) and (w_n == w_b)
        rows.append({"id": f"N-{i:02d}", "kind": "title-name",
                     "turns": turns, "reply137c": r_n, "reply137b": r_b,
                     "write137c": w_n, "write137b": w_b,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL N-{i:02d} 137c={r_n} {w_n} 137b={r_b} {w_b}",
                  flush=True)

    # O: other teaches/questions -- identical to loop137b.
    for i, turn in enumerate(OTHERS_O):
        t1 = time.time()
        r_n, w_n = seq("137c", [turn])
        r_b, w_b = seq("137b", [turn])
        ok = (r_n == r_b) and (w_n == w_b)
        rows.append({"id": f"O-{i:02d}", "kind": "other", "turn": turn,
                     "reply137c": r_n, "reply137b": r_b,
                     "write137c": w_n, "write137b": w_b,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL O-{i:02d} 137c={r_n} {w_n} 137b={r_b} {w_b}",
                  flush=True)

    out = {"n": len(rows), "fails": fails,
           "seconds": round(time.time() - t0, 1), "cases": rows}
    (ART / "probe137c.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    kinds: dict = {}
    for r in rows:
        k = kinds.setdefault(r["kind"], [0, 0])
        k[0] += 1
        k[1] += (r["verdict"] == "OK")
    print(f"kinds={kinds} fails={fails} {out['seconds']}s", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
