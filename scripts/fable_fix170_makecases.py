#!/usr/bin/env python3
"""Exp 170 case generator (sealed): S1 asks + S2 mixed-turn replay cases.

  python -B scripts/fable_fix170_makecases.py --kind s1 --out <path>
  python -B scripts/fable_fix170_makecases.py --kind s2 --seed 1702 --n 1000 \\
      --n-asks 150 --out <path>            # fresh-notebook mix
  python -B scripts/fable_fix170_makecases.py --kind s2 --seed 1703 --n 1000 \\
      --n-asks 60 --ask-pool 15k --out <path>  # 15k-notebook mix

S1: the same 25 asks 138d M6 used (facts[(k*37)%len] over the doorway-built
15k notebook):Ask strings read from the sealed 138d work dir so both arms
ask the identical questions.
S2: deterministic mixed teach/ask/correct/forget/unknown/smalltalk turns.
Names/values are drawn from fixed pools by seed; asks/corrects/forgets only
reference already-taught facts (teach-before-ask by construction). On the
15k pool, names/values mirror the SpeedP/SpeedV shapes already present.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
RELS = ["city", "color", "food", "mood", "pet", "song"]
SMALLTALK = ["hi", "thanks", "bye"]


def make_s1() -> dict:
    import fable_notebook_contract as C
    nbdir = (ROOT / "artifacts" / "fable-agent138d-20260922"
             / "work-speed2" / "nb138d" / "notebook")
    nb = C.Notebook(nbdir)
    facts = [f for f in nb.facts.values() if f.get("source") == "taught"]
    facts.sort(key=lambda f: f["fact_id"])
    names = nb.entities
    asks = []
    for k in range(25):
        f = facts[(k * 37) % len(facts)]
        asks.append(f"What is {names[f['subject']]}'s {f['relation']}?")
    return {"turns": asks, "seed": "m6-asks", "n_taught": len(facts)}


def make_s2(seed: int, n: int, n_asks: int, pool15k: bool) -> dict:
    rng = random.Random(seed)
    base_asks = None
    if pool15k:
        name = lambda i: f"Rp170P{i:04d}"  # noqa: E731 (fresh, no base clash)
        val = lambda i, r: f"Rp170V{i:04d}"  # noqa: E731
        # Base facts SpeedP{j:05d} / RELS[j % 6] are taught in the 15k dir.
        base_asks = [f"What is SpeedP{j:05d}'s {RELS[j % 6]}?"
                     for j in sorted(rng.sample(range(15000), n_asks * 2))]
    else:
        name = lambda i: f"ReplayP{i:04d}"  # noqa: E731
        val = lambda i, r: f"ReplayV{i:04d}"  # noqa: E731
    taught: list[tuple[str, str, str]] = []
    turns: list[str] = []
    ni = 0
    asks_done = 0
    ask_slots = set(rng.sample(range(n), min(n_asks, n)))
    while len(turns) < n:
        t = len(turns)
        if t in ask_slots:
            if base_asks:
                turns.append(base_asks[asks_done % len(base_asks)])
            elif taught:
                s, r, _ = rng.choice(taught)
                turns.append(f"What is {s}'s {r}?")
            else:
                continue
            asks_done += 1
            continue
        u = rng.random()
        if (not taught) or u < 0.62:
            s, r = name(ni), RELS[ni % len(RELS)]
            turns.append(f"{s}'s {r} is {val(ni, r)}.")
            taught.append((s, r, val(ni, r)))
            ni += 1
        elif u < 0.74 and taught:
            s, r, _ = rng.choice(taught)
            turns.append(f"{s}'s {r} is {val(ni, r)}.")
            turns.append("yes")
            taught.append((s, r, val(ni, r)))
            ni += 1
        elif u < 0.84 and taught:
            s, r, _ = rng.choice(taught)
            turns.append(f"forget {s} {r}")
        elif u < 0.92:
            turns.append(f"What is {name(ni + 9999)}'s {RELS[ni % len(RELS)]}?")
        else:
            turns.append(rng.choice(SMALLTALK))
    turns = turns[:n]
    return {"turns": turns, "seed": seed, "n_asks_planned": asks_done,
            "pool15k": pool15k}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 170 sealed case generator")
    ap.add_argument("--kind", required=True, choices=["s1", "s2"])
    ap.add_argument("--seed", type=int, default=1702)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--n-asks", type=int, default=150)
    ap.add_argument("--ask-pool", default="fresh", choices=["fresh", "15k"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.kind == "s1":
        cases = make_s1()
    else:
        cases = make_s2(args.seed, args.n, args.n_asks,
                        args.ask_pool == "15k")
    Path(args.out).write_text(json.dumps(cases, indent=1), encoding="utf-8")
    print(f"wrote {args.out}: {len(cases['turns'])} turns", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
