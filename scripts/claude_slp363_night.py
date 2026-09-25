#!/usr/bin/env python3
"""slp-363 (part 2): the test world, the nightly practice file, and a placebo the recipe accepts.

Fix-sleep thread, 2026-09-25 (roadmap 365 stage 2). Adds three things next to claude_slp363_school.py (unchanged):

1. make_world(root, seed): a real notebook (fable_notebook_contract.Notebook, the class the assistant stores
   facts in) filled through its normal API with actor "listening" / source "taught": ~120 invented people with
   fictional syllable names, one-value relations (mother, father, spouse, boss, doctor, teacher, best_friend, city,
   job), several-value relations (friend, sibling, child, pet) and later corrections of some one-value rows.
   It stands in for "what the user taught during the day". It is written to a temp folder, never to notebook/.
2. placebo_legal(items, seed): scrambled grades. The school's first placebo (school.placebo, gold answers
   shuffled across the batch) cannot be used: most shuffled answers are not in the episode, so the recipe's
   start-up check (claude_rsn_recipe.py: every episode needs a gold action) stops. Here each episode's grade is
   replaced by an answer drawn uniformly from the answers the reasoner could legally give for that question
   (a row's value or subject, yes/no, a count, or "I don't know"), so grades carry no information about the truth.
3. CLI: write a night file (real or placebo) or a judged panel from a world seed.
  python claude_slp363_night.py night --world-seed 11 --seed 1 --n 2000 --out night.jsonl [--placebo p.jsonl]
  python claude_slp363_night.py panel --world-seed S --seed S --n 600 --out panel.jsonl
Nothing here trains anything and nothing here writes to the assistant's notebook.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_slp363_school as S  # noqa: E402

ONE_PERSON = ("mother", "father", "spouse", "boss", "doctor", "teacher", "best_friend")
MANY_PERSON = ("friend", "sibling", "child")
ONE_LITERAL = {"city": ["Marrow", "Tellis", "Quenby", "Ostrava Vale", "Pelwick", "Dunmere", "Harth", "Silvain"],
               "job": ["baker", "pilot", "nurse", "welder", "teacher", "farmer", "clerk", "painter", "chemist"]}
MANY_LITERAL = {"pet": ["a cat", "a dog", "a parrot", "a hamster", "a turtle", "a rabbit", "a goldfish"]}
_SYL = ["ba", "ri", "zo", "ta", "me", "ku", "li", "vo", "ne", "sa", "fi", "ro", "da", "pe", "gu", "lo",
        "xi", "ma", "tu", "ve", "no", "ki", "ra", "bo"]


def _names(rng, n):
    out, seen = [], set()
    while len(out) < n:
        w = "".join(rng.choice(_SYL) for _ in range(rng.choice((2, 3)))).capitalize()
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def make_world(root, seed: int, n_people: int = 120):
    import fable_notebook_contract as NC
    rng = random.Random(seed)
    nb = NC.Notebook(root)
    ev = iter(range(1, 10 ** 7))
    e = lambda: f"w363-{seed}-{next(ev):06d}"  # noqa: E731
    for rel in ONE_PERSON + tuple(ONE_LITERAL):
        nb.declare_relation(e(), rel, True)
    for rel in MANY_PERSON + tuple(MANY_LITERAL):
        nb.declare_relation(e(), rel, False)
    ids = [nb.new_entity(e(), nm).detail["entity_id"] for nm in _names(rng, n_people)]
    for p in ids:
        others = [q for q in ids if q != p]
        for rel in ONE_PERSON:
            if rng.random() < 0.45:
                nb.assert_fact(e(), "listening", "taught", p, rel, {"entity": rng.choice(others)})
        for rel in MANY_PERSON:
            if rng.random() < 0.35:
                for q in rng.sample(others, rng.randint(2, 5)):
                    nb.assert_fact(e(), "listening", "taught", p, rel, {"entity": q})
        for rel, vals in ONE_LITERAL.items():
            if rng.random() < 0.4:
                nb.assert_fact(e(), "listening", "taught", p, rel, {"literal": rng.choice(vals)})
        for rel, vals in MANY_LITERAL.items():
            if rng.random() < 0.2:
                for v in rng.sample(vals, rng.randint(2, 3)):
                    nb.assert_fact(e(), "listening", "taught", p, rel, {"literal": v})
    facts = [(fid, f) for fid, f in list(nb.facts.items()) if f["relation"] in ONE_PERSON and nb.active(fid)]
    for fid, f in rng.sample(facts, max(1, len(facts) // 10)):          # later corrections
        new = rng.choice([q for q in ids if q not in (f["subject"], f["value"].get("entity"))])
        nb.assert_fact(e(), "listening", "taught", f["subject"], f["relation"], {"entity": new}, correction=True)
    return nb


def _legal(item) -> list[tuple[str, list[str]]]:
    fr, rows = item["frame"], item["notebook"]
    out = [("UNKNOWN", [])]
    if fr["kind"] == "yesno":
        out += [("yes", []), ("no", [])]
    elif fr["kind"] == "count":
        out += [(str(k), []) for k in range(0, 13)]
    elif fr["kind"] == "who":
        out += [(r["subject"], [r["fid"]]) for r in rows]
    else:
        out += [(r["value"], [r["fid"]]) for r in rows]
    seen, uniq = set(), []
    for a, s in out:
        k = str(a).strip().lower()
        if k not in seen:
            seen.add(k)
            uniq.append((a, s))
    return uniq


def placebo_legal(items: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed ^ 0x363B)
    out = []
    for it in items:
        a, s = rng.choice(_legal(it))
        out.append(dict(it, gold={"answer": a, "support": s}, source="sleep-school-placebo-legal"))
    return out


def world_items(world_seed: int, seed: int, n: int) -> tuple[list[dict], dict]:
    with tempfile.TemporaryDirectory(prefix="w363-") as d:
        nb = make_world(d, world_seed)
        items, log = S.build_night(nb, seed, n)
        log["world_people"] = len(nb.entities)
        log["world_taught_rows"] = sum(1 for f in nb.facts.values() if f.get("source") == "taught")
    return items, log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["night", "panel"])
    ap.add_argument("--world-seed", type=int, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--placebo", default=None)
    a = ap.parse_args(argv)
    items, log = world_items(a.world_seed, a.seed, a.n)
    chk = S.check_items(items)
    if chk["gold_wrong"]:
        raise SystemExit(f"gold check failed: {chk}")
    with open(a.out, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    if a.placebo:
        with open(a.placebo, "w", encoding="utf-8") as fh:
            for it in placebo_legal(items, a.seed):
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    if a.cmd == "night":                     # a panel's contents are never printed
        print(json.dumps({"log": log, "check": chk}))
    else:
        print(json.dumps({"items": len(items), "gold_wrong": chk["gold_wrong"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
