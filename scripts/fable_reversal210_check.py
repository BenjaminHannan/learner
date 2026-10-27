#!/usr/bin/env python3
"""Experiment 210 -- checker: prove the split is a TRUE reversal test.

For every item in data/open/reversal210/fable_reversal210.jsonl:
  C1 gold never appears in its question (normalized substring).
  C2 exactly ONE taught sentence.
  C3 taught sentence contains both gold and cue entities.
  C4 question contains the cue entity and NOT the gold.
  C5 taught sentence shape matches taught_dir
     (S_FIRST starts with person; O_FIRST starts with work).
  C6 asked direction is never taught:
     reversal + S_FIRST + WHO_REV, reversal + O_FIRST + WHAT_REV,
     control  + S_FIRST + WHAT_FWD, control  + O_FIRST + WHO_FWD;
     i.e. no reversal item pairs a taught dir with its same-dir question.
  C7 persons and works unique across the file (unambiguous lookup).
  C8 question ends with "?" and starts with Who/What (grammatical verb form).

Exit 0 + "VIOLATIONS 0" iff all hold. R1 bar: 0 violations.

Run: python -B scripts/fable_reversal210_check.py [--data PATH]
"""

from __future__ import annotations

import argparse
import json
import string
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
DATA = ROOT / "data" / "open" / "reversal210" / "fable_reversal210.jsonl"


def norm(s: str) -> str:
    s = (s or "").lower().replace("\u2019", "'")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(s.split())


def check(path: Path) -> tuple[int, list[str]]:
    viols: list[str] = []
    items = [json.loads(l) for l in path.read_text(encoding="utf-8")
             .splitlines() if l.strip()]
    persons: dict[str, str] = {}
    works: dict[str, str] = {}
    for it in items:
        iid = it.get("id", "?")
        golds = [str(g) for g in it.get("gold", [])]
        gold = golds[0] if golds else ""
        cue = str(it.get("cue", ""))
        q = str(it.get("question", ""))
        taught = it.get("taught", [])
        tdir = it.get("taught_dir", "")
        asked = it.get("asked", "")
        typ = it.get("type", "")
        nq, ng, nc = norm(q), norm(gold), norm(cue)
        # C1
        if ng and ng in nq:
            viols.append(f"{iid} C1 gold-in-question")
        # C2
        if len(taught) != 1:
            viols.append(f"{iid} C2 n_taught={len(taught)}")
            continue
        st = str(taught[0].get("sentence_en", ""))
        nst = norm(st)
        # C3
        if not (ng and ng in nst and nc and nc in nst):
            viols.append(f"{iid} C3 teach-missing-entity")
        # C4
        if not (nc and nc in nq):
            viols.append(f"{iid} C4 cue-not-in-question")
        if ng and ng in nq:
            viols.append(f"{iid} C4 gold-in-question")
        # C5
        person, work = str(it.get("person", "")), str(it.get("work", ""))
        if tdir == "S_FIRST" and not st.startswith(person):
            viols.append(f"{iid} C5 S_FIRST-shape")
        if tdir == "O_FIRST" and not st.startswith(work):
            viols.append(f"{iid} C5 O_FIRST-shape")
        if tdir not in ("S_FIRST", "O_FIRST"):
            viols.append(f"{iid} C5 bad-taught_dir")
        # C6
        ok = ((typ == "reversal" and tdir == "S_FIRST" and asked == "WHO_REV"
               and gold == person) or
              (typ == "reversal" and tdir == "O_FIRST" and asked == "WHAT_REV"
               and gold == work) or
              (typ == "control" and tdir == "S_FIRST" and asked == "WHAT_FWD"
               and gold == work) or
              (typ == "control" and tdir == "O_FIRST" and asked == "WHO_FWD"
               and gold == person))
        if not ok:
            viols.append(f"{iid} C6 asked-dir-taught-or-mismatch")
        # C8
        if not (q.endswith("?") and (q.startswith("Who ") or
                                     q.startswith("What "))):
            viols.append(f"{iid} C8 ungrammatical-question")
        # C7 collect
        if person in persons:
            viols.append(f"{iid} C7 dup-person {person}")
        persons.setdefault(person, iid)
        if work in works:
            viols.append(f"{iid} C7 dup-work {work}")
        works.setdefault(work, iid)
    if len(items) != 70:
        viols.append(f"C0 n_items={len(items)} want 70")
    nrev = sum(1 for it in items if it.get("type") == "reversal")
    nctl = sum(1 for it in items if it.get("type") == "control")
    if nrev != 50 or nctl != 20:
        viols.append(f"C0 n_rev={nrev} n_ctl={nctl} want 50/20")
    return len(viols), viols


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 210 checker")
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args(argv)
    n, viols = check(Path(args.data))
    for v in viols:
        print(f"VIOLATION {v}")
    print(f"VIOLATIONS {n}")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
