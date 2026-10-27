#!/usr/bin/env python3
"""Experiment 137b T1+T2 probe -- discourse-led twins, titles, real names.

56 sealed cases (written before any registered run):
  D 28 discourse-led teaches/questions in phone form across 16 listed
     words (suppose imagine say hi hey hello okay ok so well oh btw also
     anyway please remember + sentence-break hi./hello./okay.) --
     each must equal its bare twin exactly (same reply, same write).
  T 12 titles starting with a listed word (base-path positions) --
     identical to loop138b.
  R 16 multi-word real names (Mary Ann, New York, Ho Chi Minh City,
     Jean-Luc Picard, A. A. Milne, St. Louis ...) -- identical to loop138b.
T2 (same run): sealed redteam136 C089/C122 through loop137b -- PASS iff
no stored name triggers the discourse rule (0 junk writes); stored
triples, replies, and sealed-judge verdicts reported per case.

Harness: fresh in-process loop per case (build_agent137b /
build_agent138b, state_dir + sleep_threshold=100000, loop.turn, triples
via notebook_triples). Every case reported, never averaged.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137b_probe.py
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

import fable_fix137b_discourse as D137B  # noqa: E402 (rule under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137b_agent as L137B  # noqa: E402 (agent under test)
import fable_loop138b_agent as L138B  # noqa: E402 (frozen base, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-discourse137b-20260922"

D_WORDS = ["Suppose", "Imagine", "Say", "Hi", "Hey", "Hello", "Okay",
           "Ok", "So", "Well", "Oh", "Btw", "Also", "Anyway", "Please",
           "Remember"]

CASES: list[dict] = []
# D-teach: "<W> Tom's boss is Bob." vs bare "Tom's boss is Bob."
for w in D_WORDS:
    CASES.append({"id": f"D-t-{w.lower()}", "kind": "twin-teach",
                  "disc": f"{w} Tom's boss is Bob.",
                  "bare": "Tom's boss is Bob."})
# D-teach sentence-break: "Hi. Tom's boss is Ann." etc.
for w, v in (("Hi", "Ann"), ("Hello", "Ann"), ("Okay", "Bob")):
    CASES.append({"id": f"D-b-{w.lower()}", "kind": "twin-teach",
                  "disc": f"{w}. Tom's boss is {v}.",
                  "bare": f"Tom's boss is {v}."})
# D-question: "<W> what is Tom's boss?" vs bare (setup teaches Tom first).
for w in ["So", "Btw", "Okay", "Well", "Hi", "Please", "Also", "Oh",
          "Suppose", "Say", "Hey", "Remember"]:
    CASES.append({"id": f"D-q-{w.lower()}", "kind": "twin-question",
                  "setup": ["Tom's boss is Ann."],
                  "disc": f"{w} what is Tom's boss?",
                  "bare": "What is Tom's boss?"})

TITLES = ["Say Anything", "Hey Jude", "Hello Goodbye", "Say Say Say",
          "So What", "But Not for Me", "Also Sprach Zarathustra",
          "Look Back in Anger", "Well Did You Evah", "Hello",
          "Oh What a Beautiful Morning", "Listen to the Music"]
RELS = ["movie", "song", "movie", "song", "song", "song", "piece", "play",
        "song", "song", "song", "song"]
for i, (title, rel) in enumerate(zip(TITLES, RELS)):
    CASES.append({"id": f"T-{i:02d}", "kind": "title",
                  "turns": [f"Tom's favorite {rel} is {title}.",
                            f"What is Tom's favorite {rel}?"]})

RNAMES = [
    ("Mary Ann's boss is Bob.", "What is Mary Ann's boss?"),
    ("Mary Ann's mother is Beth.", "What is Mary Ann's mother?"),
    ("New York's boss is Adams.", "What is New York's boss?"),
    ("New York's mother is Beth.", "What is New York's mother?"),
    ("Jean-Luc Picard's boss is Janeway.", "What is Jean-Luc Picard's boss?"),
    ("Jean-Luc Picard's city is Paris.", "What is Jean-Luc Picard's city?"),
    ("Ho Chi Minh City's boss is Bob.", "What is Ho Chi Minh City's boss?"),
    ("Ho Chi Minh City's mother is Beth.", "What is Ho Chi Minh City's mother?"),
    ("Tom's boss is Mary Ann.", "What is Tom's boss?"),
    ("Tom's mother is Mary Ann.", "What is Tom's mother?"),
    ("A. A. Milne's child is Christopher Robin Milne.",
     "What is A. A. Milne's child?"),
    ("St. Louis's boss is Bob.", "What is St. Louis's boss?"),
    ("Tom's city is New York.", "What is Tom's city?"),
    ("Ann's boss is Jean-Luc Picard.", "What is Ann's boss?"),
    ("Bob's mother is Mary Ann Summer.", "What is Bob's mother?"),
    ("Kip Dune's boss is Mary Ann.", "What is Kip Dune's boss?"),
]
for i, (teach, ask) in enumerate(RNAMES):
    CASES.append({"id": f"R-{i:02d}", "kind": "realname",
                  "turns": [teach, ask]})

T2_IDS = ("C089", "C122")


def fresh(kind: str):
    cfg = copy.deepcopy(L137B.DEFAULT_CONFIG137B if kind == "137b"
                        else L138B.DEFAULT_CONFIG138B)
    tmp = tempfile.mkdtemp(prefix=f"probe137b_{kind}_")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = (L137B.build_agent137b(cfg) if kind == "137b"
            else L138B.build_agent138b(cfg))
    return loop


def run_seq(kind: str, turns: list[str]) -> tuple[list[str], list[list]]:
    loop = fresh(kind)
    replies = [" ".join(loop.turn(t)) for t in turns]
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, triples


def junk_names(triples: list[list]) -> list:
    out = []
    for tr in triples:
        for name in (tr[0], tr[2]):
            if D137B.is_discourse_name(name):
                out.append(name)
    return out


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows: list[dict] = []
    fails = 0
    for c in CASES:
        t1 = time.time()
        if c["kind"] == "twin-teach":
            r_d, w_d = run_seq("137b", [c["disc"]])
            r_b, w_b = run_seq("138b", [c["bare"]])
            ok = (r_d == r_b) and (w_d == w_b)
            row = {"id": c["id"], "kind": c["kind"], "disc": c["disc"],
                   "bare": c["bare"], "reply137b": r_d, "reply138b": r_b,
                   "write137b": w_d, "write138b": w_b,
                   "verdict": "OK" if ok else "FAIL"}
        elif c["kind"] == "twin-question":
            r_d, w_d = run_seq("137b", list(c["setup"]) + [c["disc"]])
            r_b, w_b = run_seq("138b", list(c["setup"]) + [c["bare"]])
            ok = (r_d == r_b) and (w_d == w_b)
            row = {"id": c["id"], "kind": c["kind"], "disc": c["disc"],
                   "bare": c["bare"], "reply137b": r_d, "reply138b": r_b,
                   "write137b": w_d, "write138b": w_b,
                   "verdict": "OK" if ok else "FAIL"}
        else:
            r_n, w_n = run_seq("137b", c["turns"])
            r_b, w_b = run_seq("138b", c["turns"])
            ok = (r_n == r_b) and (w_n == w_b)
            row = {"id": c["id"], "kind": c["kind"], "turns": c["turns"],
                   "reply137b": r_n, "reply138b": r_b,
                   "write137b": w_n, "write138b": w_b,
                   "verdict": "OK" if ok else "FAIL"}
        row["seconds"] = round(time.time() - t1, 3)
        rows.append(row)
        if row["verdict"] != "OK":
            fails += 1
            print(f"T1 FAIL {row['id']}: 137b={row['reply137b']} "
                  f"138b={row['reply138b']}", flush=True)
    # T2: C089/C122 through loop137b; PASS = 0 junk names (0 junk writes).
    import fable_fix139b_redteam136 as R136J  # noqa: E402 (sealed judge)
    art136 = ROOT / "artifacts" / "fable-redteam136-20260922"
    seals = json.loads((art136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(seals, dict):
        seals = seals.get("cases", seals)
    t2rows = []
    for row in seals:
        if row.get("id") not in T2_IDS:
            continue
        loop = fresh("137b")
        reply = " ".join(loop.turn(row["text"]))
        stored = [list(t) for t in L90.notebook_triples(loop.nb)]
        junk = junk_names(stored)
        exp = row["expect"]
        verdict = ("OK" if not stored else "WRONG-WRITE") if exp == "nowrite" \
            else ("OK" if stored == [list(exp)] else "WRONG-WRITE")
        t2rows.append({"id": row["id"], "text": row["text"],
                       "reply": reply, "stored": stored, "junk": junk,
                       "sealed_verdict": verdict,
                       "t2": "OK" if not junk else "FAIL"})
        if junk:
            fails += 1
        print(f"T2 {row['id']}: stored={stored} junk={junk} "
              f"sealed_verdict={verdict}", flush=True)
    out = {"n": len(rows), "fails": fails,
           "seconds": round(time.time() - t0, 1), "cases": rows,
           "t2": t2rows}
    (ART / "probe137b.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    kinds: dict = {}
    for r in rows:
        k = kinds.setdefault(r["kind"], [0, 0])
        k[0] += 1
        k[1] += (r["verdict"] == "OK")
    print(f"T1 kinds={kinds} T2={[ (r['id'], r['t2']) for r in t2rows]} "
          f"fails={fails} {out['seconds']}s", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
