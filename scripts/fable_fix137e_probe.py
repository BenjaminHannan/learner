#!/usr/bin/env python3
"""Experiment 137e T1+T1b+T2 probe -- one hearsay reply (Muse, 2026-09-22).

T1 (137d's sealed probe, case file reused UNCHANGED by import from
`scripts/fable_fix137d_probe.py`: SAY_TEACHES 16, HEAR_TEACHES 24,
CONFLICTS 6, NAMES_N 12, OTHERS_O 18):
  S-say: turn 1 byte-identical to loop137d (say echo + parenthetical),
    0 writes.
  S-hear: turn 1 == HEARSAY_MSG exactly (loop102's existing sentence),
    0 writes after each turn, turn-2 holds no framed value, notebook
    empty.
  C: real saved, framed reply exact (say echo / HEARSAY_MSG), question
    answers the REAL value, triples hold only the real fact.
  N/O: reply+triples identical to loop137d.
T1b (NEW, 31 dialogues sealed here, fictional names only):
  H 19 hearsay framings [frame, question]: 15 leading (Supposedly x2
    incl lower-case, Apparently, Allegedly+Ok-filler, Reportedly,
    Rumor/Rumour has it incl lower-case, I heard x2 incl lower-case,
    I heard that, They say, they say that, People say that,
    people say) + 4 trailing/base-path (", I heard.", "According to
    ...", ", Beth said.", "I read that ..."). PASS = turn 1 is
    HEARSAY_MSG exactly, 0 writes after each turn, turn-2 holds no
    framed value, notebook empty.
  E 12 identical-to-loop137d [lead, question]: 5 Say-group (Say,
    Say that, So+say, SAY, Ok-so+say that) + 7 plain (teach, Btw.
    teach, Suppose hypo, my-friend-says x2 declines, teach, What-if).
    PASS = replies+triples identical to loop137d.
T2 (same run): 0 writes on every framed turn (asserted per S/C/H case).

Harness: fresh in-process loop per session (build_agent137e /
build_agent137d, state_dir + sleep_threshold=100000, loop.turn,
triples via notebook_triples). Every case reported, never averaged.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137e_probe.py
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

import fable_fix137d_frame as F137D  # noqa: E402 (groups, read-only)
import fable_fix137d_probe as P137D  # noqa: E402 (T1 case file, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop137d_agent as L137D  # noqa: E402 (frozen base, read-only)
import fable_loop137e_agent as L137E  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137e-20260922"

HEAR_EXACT = L102.HEARSAY_MSG

# T1b H: 19 hearsay framings (fictional names only).
T1B_HEAR: list[str] = [
    "Supposedly Nia's boss is Obi.",
    "supposedly Nia's city is Rome.",
    "Apparently Nia's mother is Beth.",
    "Ok, so allegedly Nia's song is Halo.",
    "Reportedly Nia's movie is Dune.",
    "Rumor has it Nia's friend is Kai.",
    "rumor has it Nia's boss is Obi.",
    "Rumour has it Nia's city is Rome.",
    "I heard Nia's song is Halo.",
    "i heard Nia's city is Rome.",
    "I heard that Nia's movie is Dune.",
    "They say Nia's friend is Kai.",
    "they say that Nia's city is Rome.",
    "People say that Nia's mother is Beth.",
    "people say Nia's boss is Obi.",
    "Nia's boss is Obi, I heard.",
    "According to Obi, Nia's city is Rome.",
    "Nia's song is Halo, Beth said.",
    "I read that Nia's friend is Kai.",
]

# T1b E: 12 identical-to-loop137d leads (say x5 + plain x7).
T1B_SAME: list[str] = [
    "Say Nia's boss is Obi.",
    "Say that Nia's city is Rome.",
    "So, say Nia's song is Halo.",
    "SAY Nia's movie is Dune.",
    "Ok, so say that Nia's friend is Kai.",
    "Nia's boss is Obi.",
    "Btw. Nia's city is Rome.",
    "Suppose Nia's song is Halo.",
    "my friend says Nia's movie is Dune.",
    "My friend says Nia's friend is Kai.",
    "Kim's boss is Ann.",
    "What if Nia's boss is Obi?",
]

T1B_Q = {
    "boss": "What is Nia's boss?",
    "city": "What is Nia's city?",
    "mother": "What is Nia's mother?",
    "song": "What is Nia's song?",
    "movie": "What is Nia's movie?",
    "friend": "What is Nia's friend?",
}


def _rel_of(frame: str) -> str:
    low = frame.lower()
    for rel in ("boss", "city", "mother", "song", "movie", "friend"):
        if rel in low:
            return rel
    return "boss"


def _val_of(frame: str) -> str:
    m = frame.rsplit(" is ", 1)
    return m[1].rstrip(". ") if len(m) == 2 else frame[-8:]


def fresh(kind: str):
    if kind == "137e":
        cfg, build = copy.deepcopy(L137E.DEFAULT_CONFIG137E), \
            L137E.build_agent137e
    elif kind == "137d":
        cfg, build = copy.deepcopy(L137D.DEFAULT_CONFIG137D), \
            L137D.build_agent137d
    else:
        import fable_loop137c_agent as L137C  # noqa: E402 (read-only)
        cfg, build = copy.deepcopy(L137C.DEFAULT_CONFIG137C), \
            L137C.build_agent137c
    tmp = tempfile.mkdtemp(prefix=f"probe137e_{kind}_")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    return build(cfg)


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

    def record(row: dict, ok: bool, tag: str) -> None:
        nonlocal fails
        rows.append({**row, "verdict": "OK" if ok else "FAIL"})
        if not ok:
            fails += 1
            print(f"FAIL {tag} {row}", flush=True)

    # T1 S-say: byte-identical to loop137d.
    for i, (marker, pre, rel, val) in enumerate(P137D.SAY_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        t1 = time.time()
        r_e, w_e = seq("137e", [frame, q])
        r_d, w_d = seq("137d", [frame, q])
        ok = (r_e == r_d) and (w_e == w_d) and (w_e == []) \
            and (r_e[0] == F137D.say_reply(frame))
        record({"id": f"T1-S-say{i:02d}", "kind": "say-pure",
                "frame": frame, "reply137e": r_e, "reply137d": r_d,
                "writes": w_e, "seconds": round(time.time() - t1, 3)},
               ok, f"T1-S-say{i:02d}")

    # T1 S-hear: HEARSAY_MSG exactly, 0 writes.
    for i, (marker, pre, rel, val) in enumerate(P137D.HEAR_TEACHES):
        frame = f"{pre}{marker} Kim's {rel} is {val}."
        q = f"What is Kim's {rel}?"
        t1 = time.time()
        loop = fresh("137e")
        r1 = " ".join(loop.turn(frame))
        w1 = [list(t) for t in L90.notebook_triples(loop.nb)]
        r2 = " ".join(loop.turn(q))
        w2 = [list(t) for t in L90.notebook_triples(loop.nb)]
        ok = (r1 == HEAR_EXACT) and (w1 == []) and (w2 == []) \
            and (val not in r2)
        record({"id": f"T1-S-hear{i:02d}", "kind": "hearsay-pure",
                "frame": frame, "reply1": r1, "reply2": r2, "writes": w2,
                "seconds": round(time.time() - t1, 3)}, ok,
               f"T1-S-hear{i:02d}")

    # T1 C conflict: real wins; framed exact.
    for i, (marker, rel, real, rival) in enumerate(P137D.CONFLICTS):
        frame = f"{marker} Kim's {rel} is {rival}."
        turns = [f"Kim's {rel} is {real}.", frame,
                 f"What is Kim's {rel}?"]
        exp1 = HEAR_EXACT if F137D.frame_kind(frame) == "hearsay" \
            else F137D.say_reply(frame)
        t1 = time.time()
        replies, triples = seq("137e", turns)
        ok = (replies[0] == f"Saved: Kim's {rel} is {real}."
              and replies[1] == exp1
              and replies[2] == f"Kim's {rel} is {real}."
              and triples == [["Kim", rel, real]])
        record({"id": f"T1-C-{i:02d}", "kind": "conflict",
                "turns": turns, "replies": replies, "triples": triples,
                "seconds": round(time.time() - t1, 3)}, ok, f"T1-C-{i:02d}")

    # T1 N/O: identical to loop137d.
    for i, teach in enumerate(P137D.NAMES_N):
        t1 = time.time()
        r_e, w_e = seq("137e", [teach])
        r_d, w_d = seq("137d", [teach])
        ok = (r_e == r_d) and (w_e == w_d)
        record({"id": f"T1-N-{i:02d}", "kind": "title-name",
                "turn": teach, "reply137e": r_e, "reply137d": r_d,
                "seconds": round(time.time() - t1, 3)}, ok, f"T1-N-{i:02d}")
    for i, turn in enumerate(P137D.OTHERS_O):
        t1 = time.time()
        r_e, w_e = seq("137e", [turn])
        r_d, w_d = seq("137d", [turn])
        ok = (r_e == r_d) and (w_e == w_d)
        record({"id": f"T1-O-{i:02d}", "kind": "other", "turn": turn,
                "reply137e": r_e, "reply137d": r_d,
                "seconds": round(time.time() - t1, 3)}, ok, f"T1-O-{i:02d}")

    # T1b H hearsay: HEARSAY_MSG + 0 writes + follow-up finds nothing.
    for i, frame in enumerate(T1B_HEAR):
        rel = _rel_of(frame)
        val = _val_of(frame)
        q = T1B_Q[rel]
        t1 = time.time()
        loop = fresh("137e")
        r1 = " ".join(loop.turn(frame))
        w1 = [list(t) for t in L90.notebook_triples(loop.nb)]
        r2 = " ".join(loop.turn(q))
        w2 = [list(t) for t in L90.notebook_triples(loop.nb)]
        ok = (r1 == HEAR_EXACT) and (w1 == []) and (w2 == []) \
            and (val not in r2)
        record({"id": f"T1b-H{i:02d}", "kind": "t1b-hearsay",
                "frame": frame, "q": q, "reply1": r1, "reply2": r2,
                "writes": w2, "seconds": round(time.time() - t1, 3)},
               ok, f"T1b-H{i:02d}")

    # T1b E identical: replies+triples == loop137d.
    for i, lead in enumerate(T1B_SAME):
        if F137D.frame_kind(lead) == "say":
            turns = [lead]
        elif lead.rstrip().endswith("?"):
            turns = [lead]
        else:
            rel = _rel_of(lead)
            q = T1B_Q[rel].replace("Nia's", "Nia's")
            if "Kim's" in lead:
                q = "What is Kim's boss?"
            turns = [lead, q]
        t1 = time.time()
        r_e, w_e = seq("137e", turns)
        r_d, w_d = seq("137d", turns)
        ok = (r_e == r_d) and (w_e == w_d)
        record({"id": f"T1b-E{i:02d}", "kind": "t1b-identical",
                "turns": turns, "reply137e": r_e, "reply137d": r_d,
                "write137e": w_e, "write137d": w_d,
                "seconds": round(time.time() - t1, 3)}, ok, f"T1b-E{i:02d}")

    out = {"n": len(rows), "fails": fails,
           "seconds": round(time.time() - t0, 1), "cases": rows}
    (ART / "probe137e.json").write_text(
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
