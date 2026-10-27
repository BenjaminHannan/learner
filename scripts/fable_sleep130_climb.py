#!/usr/bin/env python3
"""Experiment 130 G4 variant (UNREGISTERED): 12-sleep climb with disjoint families.

The first 12-climb broke at 9/12 for a world-building reason, not a sleep
reason: extra phases reused (kid, hop1) pairs (spouse/mother on the J/Y kids)
with NEW values, so the notebook's taught-never-overwritten guard clarified
instead of saving, no episodes queued, and the sleeps were honest no-ops
(0 wrong throughout). This variant gives every extra phase its own kid
family (train J<wi>xx, test Y<wi>xx) so no (subject, relation) pair is ever
re-taught with a different value. Phases 1-5 are 115's L4 verbatim.
Reported apart; no marks gate anything. Sealed 130 files are not touched.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_sleep115_drive as D115  # noqa: E402 (read-only)
import fable_sleep130_agent as S130  # noqa: E402 (read-only)
import fable_sleep130_drive as D130  # noqa: E402 (read-only)

ART = SCRIPTS.parent / "artifacts" / "fable-sleep130-20260922"


def build_turns_climb_disjoint(n_words: int = 12):
    words = D130.WORDS12
    l4turns, truth = D115.build_turns_l4()
    turns = [t for t in l4turns if t["kind"] != "probe"]
    assert len(turns) == 375, len(turns)
    pools = {5: ("MO", "SP"), 6: ("BM", "BO"), 7: ("TF", "TT"),
             8: ("DS", "DO"), 9: ("FM", "FA"), 10: ("DB", "DC"),
             11: ("TM", "TE")}
    exp: dict = {}
    for row in [(f"T{i:02d}", f"N{i:02d}", f"H{i:02d}", f"U{i:02d}",
                 f"V{i:02d}", f"W{i:02d}", f"X{i:02d}", f"C{i:02d}",
                 f"E{i:02d}", f"A{i:02d}") for i in range(1, 6)]:
        (kid, _m, gran, _s, bos, _f, doc, _p, dbos, tea) = row
        exp[(kid, D130.WORDS5[0])] = gran
        exp[(kid, D130.WORDS5[1])] = bos
        exp[(kid, D130.WORDS5[2])] = doc
        exp[(kid, D130.WORDS5[3])] = dbos
        exp[(kid, D130.WORDS5[4])] = tea
    for wi in range(5, n_words):
        w = words[wi]
        hop1, hop2 = D130.CLIMB_CHAINS[w]
        pa, pb = pools[wi]
        kp, qp = f"J{wi}", f"Y{wi}"  # per-phase kid families: never re-taught
        for i in range(1, 21):
            kid, b, c = f"{kp}{i:02d}", f"{pb}{i:02d}", f"{pa}X{i:02d}"
            for subj, rel, obj in ((kid, hop1, b), (b, hop2, c)):
                turns.append({"kind": "teach",
                              "text": f"{subj}'s {rel.replace('_', ' ')} "
                                      f"is {obj}.",
                              "expect": (subj, rel.replace("_", " "), obj)})
                truth[(subj, rel.replace(" ", "_"))] = obj
            exp[(kid, w)] = c
        for i in range(1, 6):
            kid, b, c = f"{qp}{i:02d}", f"{pb}T{i:02d}", f"{pa}XT{i:02d}"
            for subj, rel, obj in ((kid, hop1, b), (b, hop2, c)):
                turns.append({"kind": "teach",
                              "text": f"{subj}'s {rel.replace('_', ' ')} "
                                      f"is {obj}.",
                              "expect": (subj, rel.replace("_", " "), obj)})
                truth[(subj, rel.replace(" ", "_"))] = obj
            exp[(kid, w)] = c
        for i in range(1, 21):
            kid = f"{kp}{i:02d}"
            turns.append({"kind": "episode", "word": w,
                          "text": f"Who is {kid}'s {D130.SURF[w]}?",
                          "expect": None})
        for text in D115.FILLERS:
            turns.append({"kind": "filler", "text": text})
    for w in words:
        kids = ([f"T{i:02d}" for i in range(1, 6)] if words.index(w) < 5
                else [f"Y{words.index(w)}{i:02d}" for i in range(1, 6)])
        for kid in kids:
            turns.append({"kind": "probe", "word": w,
                          "text": f"Who is {kid}'s {D130.SURF[w]}?",
                          "expect": exp[(kid, w)]})
    return turns, truth


def main() -> int:
    t0 = time.time()
    root = ART / "runs"
    d = root / "g4-12b-seed1"
    if d.exists():
        shutil.rmtree(d)
    proc = D130.spawn(d, 1, threshold=75)
    turns, truth = build_turns_climb_disjoint(12)
    replies = D130.drive_turns(d, turns, 1, {75 * i for i in range(1, 13)})
    D130.stop_daemon(proc, d)
    rep = D130.score_session130(d, 1, "g4-12b-seed1", replies, truth,
                                D130.WORDS12, t0, [75])
    slim = {k: v for k, v in rep.items() if k != "replies"}
    out = {"unregistered": {"G4-12b": {
        "seeds": {"1": slim},
        "summary": D130.climb_summary({**rep}, D130.WORDS12)}}}
    out["wave_seconds"] = round(time.time() - t0, 1)
    (ART / "wave-g4-12b.json").write_text(json.dumps(out, indent=1,
                                                     sort_keys=True),
                                          encoding="utf-8")
    s = out["unregistered"]["G4-12b"]["summary"]
    print(f"G4-12b seed 1: installed={s['installed']} sleeps={s['n_sleeps']} "
          f"sleep_s={s['per_sleep_seconds']} probes={s['probes']} "
          f"taught={s['taught']} overwrites={s['overwrites']} "
          f"{out['wave_seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
