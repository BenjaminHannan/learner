#!/usr/bin/env python3
"""Exp 232 parity dev check: one-word vs multi-word names, same dialogs.

Each template dialog is run on a fresh notebook once with the one-word name
"Orrin" and once per multi-word name. A dialog is at parity when every reply
and the final stored triples are byte-identical after replacing the
multi-word name with "Orrin". Writes <out>.jsonl (all replies) and prints a
summary. Usage:
  python -B scripts/claude_fullname232_parity.py --agent A.py --config C.json \
      --work /scratch/dir --out /path/prefix
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_marks123_all as M  # noqa: E402 (read-only)

ONE = "Orrin"
MULTI = ["Orrin Vask", "Orrin Tel Vask", "Orrin van der Vask",
         "Orrin Vask-Ley", "Orrin K. Vask", "Orrin da Vask"]

TEMPLATES = [
    ["{N} lives in Quellmoor.", "Where does {N} live?"],
    ["{N} works at Brindlecorp.", "Where does {N} work?",
     "Who does {N} work for?"],
    ["{N} works for Hollowmere.", "Who does {N} work for?"],
    ["{N} speaks Veltish.", "What language does {N} speak?",
     "What languages does {N} speak?"],
    ["{N} was born in Farrowgate.", "Where was {N} born?"],
    ["Where does {N} live?", "Where does {N} work?",
     "What language does {N} speak?", "Where was {N} born?"],
    ["{N} lives in Quellmoor.", "Actually, {N} lives in Dunmere.",
     "Where does {N} live?"],
    ["{N} works at Brindlecorp.", "No, {N} works at Halden Mills.",
     "Where does {N} work?"],
    ["{N} lives in Quellmoor.", "{N} lives in Dunmere.", "yes",
     "Where does {N} live?"],
    ["{N} lives in Quellmoor.", "{N} lives in Dunmere.", "no",
     "Where does {N} live?"],
    ["{N} lives in Quellmoor.", "{N} lives in Dunmere.",
     "{N} works at Brindlecorp.", "yes", "Where does {N} live?"],
    ["{N} speaks Veltish.", "{N} speaks Norric.",
     "What languages does {N} speak?"],
    ["{N} speaks Veltish.", "{N} speaks Veltish.",
     "What language does {N} speak?"],
    ["{N} lives in a flat.", "Where does {N} live?"],
    ["{N} lives in Quellmoor now.", "Where does {N} live?"],
    ["{N} lives in Quellmoor too.", "Where does {N} live?"],
    ["{N} works at the mill.", "Where does {N} work?"],
    ["{N} speaks fluent Veltish.", "What language does {N} speak?"],
    ["{N} speaks Norric and Veltish.", "What language does {N} speak?"],
    ["{N} lives in Quellmoor.", "{N} lives in Dunmere, I think.",
     "Where does {N} live?"],
    ["{N} doesn't live in Quellmoor.", "Where does {N} live?"],
    ["{N} used to live in Quellmoor.", "Where does {N} live?"],
    ["{N} lives in Quellmoor?", "Where does {N} live?"],
    ["{N} was born in the city of Farrowgate.", "Where was {N} born?"],
    ["{N} speaks the language of Veltmark.",
     "What language does {N} speak?"],
    ["{N} lives in Quellmoor.", "Forget {N}'s city.",
     "Where does {N} live?"],
    ["{N} lives in Quellmoor.", "What is {N}'s city?",
     "Where does {N} live"],
    ["{N}'s city is Tillmarsh.", "Where does {N} live?"],
    ["{N} works at Brindlecorp.", "What is {N}'s employer?"],
    ["Tessa's boss is {N}.", "{N} lives in Tillmarsh.",
     "Where does {N} live?"],
    ["{N} lives in Quellmoor. {N} works at Brindlecorp.",
     "Where does {N} live?"],
    ["{N} lives in Quellmoor; {N} speaks Veltish.",
     "Where does {N} live?"],
    ["{N} lives in New Harrow.", "Where does {N} live?"],
    ["{N} lives in Quellmoor with Tessa.", "Where does {N} live?"],
    ["{N} works at Brindlecorp.", "{N} lives in Quellmoor.",
     "{N} speaks Veltish.", "{N} was born in Farrowgate.",
     "Where does {N} work?", "Where does {N} live?",
     "What language does {N} speak?", "Where was {N} born?"],
]


def run_dialog(dcls, base, root: Path, turns: list[str]):
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    d = M.make_daemon(dcls, base, root)
    reps = []
    for j, t in enumerate(turns):
        f = root / "inbox" / f"m{j:02d}.txt"
        f.write_text(t, encoding="utf-8")
        d.process_file(f)
        reps.append((root / "outbox" / f"m{j:02d}.txt").read_text(
            encoding="utf-8").strip())
    stored = sorted(list(x) for x in L90.notebook_triples(d.loop.nb))
    shutil.rmtree(root, ignore_errors=True)
    return reps, stored


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    _m, dcls, _b, _c = M.load_agent(args.agent)
    base = M.load_base_cfg(args.config)
    work = Path(args.work)
    n = bad = 0
    misses = []
    with open(args.out + ".jsonl", "w", encoding="utf-8") as fh:
        for k, tpl in enumerate(TEMPLATES):
            one_turns = [t.replace("{N}", ONE) for t in tpl]
            r1, s1 = run_dialog(dcls, base, work / f"t{k}o", one_turns)
            fh.write(json.dumps({"t": k, "name": ONE, "turns": one_turns,
                                 "replies": r1, "stored": s1},
                                ensure_ascii=False) + "\n")
            for name in MULTI:
                turns = [t.replace("{N}", name) for t in tpl]
                r2, s2 = run_dialog(dcls, base, work / f"t{k}m", turns)
                back_r = [x.replace(name, ONE) for x in r2]
                back_s = sorted([[c.replace(name, ONE) for c in x]
                                 for x in s2])
                ok = back_r == r1 and back_s == s1
                n += 1
                bad += int(not ok)
                fh.write(json.dumps({"t": k, "name": name, "turns": turns,
                                     "replies": r2, "stored": s2,
                                     "parity": ok}, ensure_ascii=False)
                         + "\n")
                if not ok:
                    misses.append({"t": k, "name": name,
                                   "diff": [(a, b) for a, b in
                                            zip(r1, back_r) if a != b],
                                   "stored": (s1, back_s)})
    summ = {"dialogs": n, "parity": n - bad, "misses": misses}
    Path(args.out + "-summary.json").write_text(
        json.dumps(summ, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"dialogs": n, "parity": n - bad}, indent=1))
    for m in misses:
        print(json.dumps(m, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
