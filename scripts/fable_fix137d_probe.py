#!/usr/bin/env python3
"""Experiment 137d T1+T2 probe -- frame-guard twins, titles, others.

76 sealed cases (written before any registered run):
  S 40 framed pure sessions [frame teach, question]: 16 say-group (say x8
     incl "SAY" case twin + fillers, say that x8 incl "Say That" twin +
     fillers; 6 relations) + 24 hearsay-group (all 11 markers x plain +
     filler/case twin + 2 extra case twins; 6 relations). PASS = turn 1
     replies the exact sealed reply (say echo + parenthetical / hearsay
     sentence), 0 writes after each turn, turn-2 reply holds no framed
     value, notebook empty.
  C 6 conflict sessions [real teach, framed rival, question] (say x2,
     say that x1, supposedly/apparently/they say x3). PASS = real saved,
     framed exact reply, question answers the REAL value, triples hold
     only the real fact.
  N 12 titles/names containing a marker word ("Kim's song is Say My
     Name", "Kim's book is Apparently", "Say's boss is Kim.",
     "They Say's mother is Beth.", "What If's boss is Kim." ...).
     PASS = reply+triples identical to loop137c.
  O 18 other teaches/questions (plain teaches, "Btw./So/Hi." phone
     teaches, hypo twins Suppose/Imagine/What-if identical to loop137c,
     bare-"If ..." decline, real names, "Okay/And Kim's ...").
     PASS = reply+triples identical to loop137c.
T2 (same run): 0 writes on every framed turn (0 wrong writes).

Harness: fresh in-process loop per session (build_agent137d /
build_agent137c, state_dir + sleep_threshold=100000, loop.turn, triples
via notebook_triples). Every case reported, never averaged.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137d_probe.py
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

import fable_fix137d_frame as F137D  # noqa: E402 (rule under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop137c_agent as L137C  # noqa: E402 (frozen base, read-only)
import fable_loop137d_agent as L137D  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137d-20260922"

SAY_SUFFIX = F137D.SAY_SUFFIX
HEAR_EXACT = F137D.HEARSAY_REPLY

# (marker, filler_prefix, relation, value): 8x say + 8x say that.
SAY_TEACHES: list[tuple[str, str, str, str]] = [
    ("Say", "", "boss", "Lee"),
    ("Say", "Ok, so ", "mother", "Beth"),
    ("Say", "And ", "city", "Paris"),
    ("Say", "So, ", "song", "Halo"),
    ("Say", "", "movie", "Dune"),
    ("Say", "Ok, ", "friend", "Kai"),
    ("SAY", "", "city", "Quito"),
    ("Say", "And, ", "boss", "Ann"),
    ("Say that", "", "mother", "Beth"),
    ("Say that", "So ", "boss", "Lee"),
    ("Say that", "Ok, so ", "city", "Paris"),
    ("Say that", "And ", "song", "Halo"),
    ("Say that", "", "movie", "Dune"),
    ("Say that", "Ok, ", "friend", "Kai"),
    ("Say That", "", "boss", "Lee"),
    ("Say that", "So, ", "mother", "June"),
]

# (marker, filler_prefix, relation, value): all 11 hearsay markers x2 + 2.
HEAR_TEACHES: list[tuple[str, str, str, str]] = [
    ("Supposedly", "", "boss", "Lee"),
    ("Supposedly", "Ok, so ", "mother", "Beth"),
    ("Apparently", "", "city", "Paris"),
    ("Apparently", "And ", "boss", "Lee"),
    ("Allegedly", "", "song", "Halo"),
    ("Allegedly", "So ", "mother", "Beth"),
    ("Reportedly", "", "movie", "Dune"),
    ("Reportedly", "Ok, ", "friend", "Kai"),
    ("Rumor has it", "", "boss", "Lee"),
    ("Rumor has it", "And, ", "city", "Paris"),
    ("Rumour has it", "", "mother", "Beth"),
    ("Rumour has it", "So, ", "song", "Halo"),
    ("I heard", "", "boss", "Lee"),
    ("I heard", "Ok, so ", "city", "Quito"),
    ("I heard that", "", "movie", "Dune"),
    ("I heard that", "And ", "friend", "Kai"),
    ("They say", "", "boss", "Ann"),
    ("They say", "So ", "mother", "June"),
    ("They say that", "", "city", "Paris"),
    ("They say that", "Ok, ", "song", "Gold"),
    ("People say", "", "friend", "Kai"),
    ("People say", "And ", "boss", "Lee"),
    ("SUPPOSEDLY", "", "city", "Lima"),
    ("They Say", "", "movie", "Jaws"),
]

# (marker, relation, real_value, rival_value).
CONFLICTS: list[tuple[str, str, str, str]] = [
    ("Say", "boss", "Ann", "Lee"),
    ("Say that", "city", "Paris", "Quito"),
    ("Say", "song", "Halo", "Gold"),
    ("Supposedly", "boss", "Ann", "Bob"),
    ("Apparently", "mother", "Beth", "June"),
    ("They say", "movie", "Dune", "Jaws"),
]

NAMES_N = [
    "Kim's song is Say My Name.",
    "Kim's book is Apparently.",
    "Kim's film is Reportedly.",
    "Kim's city is Supposedly.",
    "Kim's friend is Allegedly.",
    "Kim's song is Rumor Has It.",
    "Say's boss is Kim.",
    "They Say's mother is Beth.",
    "What If's boss is Kim.",
    "Imagine's mother is Beth.",
    "Kim's mother is I Heard.",
    "Lee's friend is People Say.",
]

OTHERS_O = [
    "Kim's boss is Ann.",
    "Btw. Kim's boss is Lee.",
    "So Kim's boss is Lee.",
    "Hi. Kim's boss is Lee.",
    "Suppose Kim's boss is Lee.",
    "Imagine Kim's city is Paris.",
    "What if Kim's boss is Lee?",
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
    cfg = copy.deepcopy(L137D.DEFAULT_CONFIG137D if kind == "137d"
                        else L137C.DEFAULT_CONFIG137C)
    tmp = tempfile.mkdtemp(prefix=f"probe137d_{kind}_")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = (L137D.build_agent137d(cfg) if kind == "137d"
            else L137C.build_agent137c(cfg))
    return loop


def seq(kind: str, turns: list[str]) -> tuple[list[str], list[list]]:
    loop = fresh(kind)
    replies = [" ".join(loop.turn(t)) for t in turns]
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    return replies, triples


def expect_say(frame: str) -> str:
    return F137D.say_reply(frame)


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows: list[dict] = []
    fails = 0

    # S-say pure: [say frame, question].
    for i, (marker, pre, rel, val) in enumerate(SAY_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        t1 = time.time()
        loop = fresh("137d")
        r1 = " ".join(loop.turn(frame))
        w1 = [list(t) for t in L90.notebook_triples(loop.nb)]
        r2 = " ".join(loop.turn(q))
        w2 = [list(t) for t in L90.notebook_triples(loop.nb)]
        ok = (r1 == expect_say(frame)) and (w1 == []) and (w2 == []) \
            and (val not in r2)
        rows.append({"id": f"S-say{i:02d}", "kind": "say-pure",
                     "marker": marker, "frame": frame, "q": q,
                     "reply1": r1, "reply2": r2, "writes": w2,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL S-say{i:02d} {frame!r} -> {r1!r} / {r2!r} {w2}",
                  flush=True)

    # S-hear pure: [hearsay frame, question].
    for i, (marker, pre, rel, val) in enumerate(HEAR_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        t1 = time.time()
        loop = fresh("137d")
        r1 = " ".join(loop.turn(frame))
        w1 = [list(t) for t in L90.notebook_triples(loop.nb)]
        r2 = " ".join(loop.turn(q))
        w2 = [list(t) for t in L90.notebook_triples(loop.nb)]
        ok = (r1 == HEAR_EXACT) and (w1 == []) and (w2 == []) \
            and (val not in r2)
        rows.append({"id": f"S-hear{i:02d}", "kind": "hearsay-pure",
                     "marker": marker, "frame": frame, "q": q,
                     "reply1": r1, "reply2": r2, "writes": w2,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL S-hear{i:02d} {frame!r} -> {r1!r} / {r2!r} {w2}",
                  flush=True)

    # C conflict: [real, framed rival, question] -- real value wins.
    for i, (marker, rel, real, rival) in enumerate(CONFLICTS):
        frame = f"{marker} Kim's {rel} is {rival}."
        turns = [f"Kim's {rel} is {real}.", frame,
                 f"What is Kim's {rel}?"]
        exp1 = HEAR_EXACT if F137D.frame_kind(frame) == "hearsay" \
            else expect_say(frame)
        t1 = time.time()
        replies, triples = seq("137d", turns)
        ok = (replies[0] == f"Saved: Kim's {rel} is {real}."
              and replies[1] == exp1
              and replies[2] == f"Kim's {rel} is {real}."
              and triples == [["Kim", rel, real]])
        rows.append({"id": f"C-{i:02d}", "kind": "conflict",
                     "marker": marker, "turns": turns, "replies": replies,
                     "triples": triples,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL C-{i:02d} {replies} {triples}", flush=True)

    # N: marker-word titles/names -- identical to loop137c.
    for i, teach in enumerate(NAMES_N):
        turns = [teach]
        t1 = time.time()
        r_n, w_n = seq("137d", turns)
        r_b, w_b = seq("137c", turns)
        ok = (r_n == r_b) and (w_n == w_b)
        rows.append({"id": f"N-{i:02d}", "kind": "title-name",
                     "turns": turns, "reply137d": r_n, "reply137c": r_b,
                     "write137d": w_n, "write137c": w_b,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL N-{i:02d} 137d={r_n} {w_n} 137c={r_b} {w_b}",
                  flush=True)

    # O: other teaches/questions -- identical to loop137c.
    for i, turn in enumerate(OTHERS_O):
        t1 = time.time()
        r_n, w_n = seq("137d", [turn])
        r_b, w_b = seq("137c", [turn])
        ok = (r_n == r_b) and (w_n == w_b)
        rows.append({"id": f"O-{i:02d}", "kind": "other", "turn": turn,
                     "reply137d": r_n, "reply137c": r_b,
                     "write137d": w_n, "write137c": w_b,
                     "verdict": "OK" if ok else "FAIL",
                     "seconds": round(time.time() - t1, 3)})
        if not ok:
            fails += 1
            print(f"FAIL O-{i:02d} 137d={r_n} {w_n} 137c={r_b} {w_b}",
                  flush=True)

    out = {"n": len(rows), "fails": fails,
           "seconds": round(time.time() - t0, 1), "cases": rows}
    (ART / "probe137d.json").write_text(
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
