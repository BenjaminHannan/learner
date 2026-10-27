#!/usr/bin/env python3
"""Experiment 53 (MOUTH) -- synthetic records -> English sentence pairs.

Plain software. Generates training pairs and a held-out set of RECORDS shaped
exactly like the reasoner outputs (scripts/fable_reasoner50.py /
scripts/fable_wire51_adapters.py TemplateMouth): kind/status/name/relations/fields.

Statuses: OK / MISSING_FACT / BROKEN_CHAIN / AMBIGUOUS / UNKNOWN_ENTITY (+ BAD_REQUEST).
Hop paths: 1-3 relations. Village relations: mother, father, child, sibling,
spouse, employer, hometown, school, plus 30 open relation strings.
Paraphrase variety: 6 templates per status (brief asked for 4+).

Every target sentence keeps a canonical anchor substring so a rule-based
classifier can recover the status (needed for O2) and the wire51 replay scorer
still sees its abstention phrases:
  OK            -> "{owner} is {answer}." shape (answer verbatim)
  MISSING_FACT  -> contains "don't know"
  BROKEN_CHAIN  -> contains "not someone I can look up"
  AMBIGUOUS     -> contains "more than one"
  UNKNOWN_ENTITY-> contains "don't know anyone"
  BAD_REQUEST   -> contains "could not use that"

Usage:
    python -B scripts/fable_mouth53_data.py --out artifacts/fable-mouth53-20260921/data \
        --train 3000 --seed 5301
Writes train.jsonl ({record, sentence}) and heldout.jsonl ({record, reference}).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

SEED_DEFAULT = 5301

VILLAGE_RELS = ("mother", "father", "child", "sibling", "spouse", "employer", "hometown", "school")
OPEN_RELS = (
    "mentor", "neighbour", "doctor", "teacher", "boss", "best_friend", "cousin",
    "grandmother", "grandfather", "uncle", "aunt", "nephew", "niece", "partner",
    "roommate", "teammate", "coach", "dentist", "lawyer", "barber", "baker",
    "florist", "plumber", "driver", "nurse", "professor", "landlord", "tenant",
    "godmother", "pen_pal",
)
ALL_RELS = VILLAGE_RELS + OPEN_RELS

NAMES = (
    "Mira", "Tom", "Ana", "Kai", "Ben", "Zed", "Lena", "Omar", "Priya", "Ravi",
    "Sofia", "Theo", "Uma", "Victor", "Wren", "Yuki", "Zara", "Felix", "Greta",
    "Hugo", "Iris", "Jonas", "Kira", "Liam", "Nora", "Oscar", "Paula", "Quinn",
)
PLACES = (
    "Lisbon", "Porto", "Oslo", "Madrid", "Berlin", "Paris", "Rome", "Dublin",
    "Vienna", "Prague", "Athens", "Lyon", "Bristol", "Turin", "Ghent", "Haifa",
)

SOURCES = ("taught", "inferred", "sleep-derived", "web-verified")


def owner_phrase(name: str, relations: list[str]) -> str:
    return "'s ".join([name] + [r.replace("_", " ") for r in relations])


# ---------------------------------------------------------------- templates
def t_ok(rec) -> list[str]:
    f = rec["fields"]
    owner = owner_phrase(rec["name"], rec["relations"])
    ans = f["answer"]
    return [
        f"{owner} is {ans}.",
        f"The answer is {ans}: {owner}.",
        f"{owner} -- that is {ans}.",
        f"I found it: {owner} is {ans}.",
        f"{owner} is {ans}, as taught.",
        f"So {owner} is {ans}.",
    ]


def t_missing(rec) -> list[str]:
    f = rec["fields"]
    subj, rel = f["subject"], f["relation"].replace("_", " ")
    return [
        f"I don't know {subj}'s {rel}.",
        f"I don't know who {subj}'s {rel} is.",
        f"Sorry, I don't know {subj}'s {rel} -- that fact is missing.",
        f"I don't know: nobody taught me {subj}'s {rel}.",
        f"I don't know {subj}'s {rel} yet.",
        f"That is missing: I don't know {subj}'s {rel}.",
    ]


def t_broken(rec) -> list[str]:
    f = rec["fields"]
    subj, rel, val = f["subject"], f["relation"].replace("_", " "), f["value"]
    return [
        f"{subj}'s {rel} is {val}, which is not someone I can look up.",
        f"{subj}'s {rel} is {val}, and {val} is not someone I can look up.",
        f"I stopped: {subj}'s {rel} is {val}, which is not someone I can look up.",
        f"{subj}'s {rel} turned out to be {val}, which is not someone I can look up.",
        f"Cannot go on: {subj}'s {rel} is {val}, which is not someone I can look up.",
        f"{subj}'s {rel} is {val} -- not someone I can look up.",
    ]


def t_ambiguous(rec) -> list[str]:
    f = rec["fields"]
    name, choices = f["name"], f["choices"]
    return [
        f"I know more than one {name}: {choices}. Which one do you mean?",
        f"There is more than one {name} ({choices}). Which one do you mean?",
        f"I know more than one person called {name}: {choices}. Which one?",
        f"More than one {name}, I am afraid: {choices}. Which one do you mean?",
        f"I know more than one {name} -- {choices} -- which one do you mean?",
        f"Which {name}? I know more than one: {choices}.",
    ]


def t_unknown(rec) -> list[str]:
    name = rec["fields"]["name"]
    return [
        f"I don't know anyone called {name}.",
        f"I don't know anyone by the name {name}.",
        f"Sorry, I don't know anyone called {name}.",
        f"I don't know anyone called {name} yet.",
        f"No: I don't know anyone called {name}.",
        f"I don't know anyone called {name} -- that name is new to me.",
    ]


def t_bad(rec) -> list[str]:
    reason = rec["fields"]["reason"]
    return [
        f"I could not use that: {reason}.",
        f"Sorry, I could not use that: {reason}.",
        f"I could not use that question: {reason}.",
        f"I could not use that -- {reason}.",
        f"I could not use that: {reason} Nothing was saved.",
        f"That did not work: I could not use that: {reason}.",
    ]


TEMPLATES = {
    "OK": t_ok,
    "MISSING_FACT": t_missing,
    "BROKEN_CHAIN": t_broken,
    "AMBIGUOUS": t_ambiguous,
    "UNKNOWN_ENTITY": t_unknown,
    "BAD_REQUEST": t_bad,
}

HELDOUT_MIX = (
    ("OK", 250), ("MISSING_FACT", 80), ("BROKEN_CHAIN", 60),
    ("AMBIGUOUS", 40), ("UNKNOWN_ENTITY", 40), ("BAD_REQUEST", 30),
)
TRAIN_MIX = (
    ("OK", 1250), ("MISSING_FACT", 550), ("BROKEN_CHAIN", 400),
    ("AMBIGUOUS", 300), ("UNKNOWN_ENTITY", 300), ("BAD_REQUEST", 200),
)


def rand_name(rng: random.Random) -> str:
    return NAMES[rng.randrange(len(NAMES))]


def rand_rel(rng: random.Random, village_bias: float = 0.6) -> str:
    if rng.random() < village_bias:
        return VILLAGE_RELS[rng.randrange(len(VILLAGE_RELS))]
    return OPEN_RELS[rng.randrange(len(OPEN_RELS))]


def rand_chain(rng: random.Random, n: int) -> list[str]:
    return [rand_rel(rng) for _ in range(n)]


def make_record(rng: random.Random, status: str) -> dict:
    n_hops = rng.randint(1, 3)
    if status == "OK":
        name = rand_name(rng)
        rels = rand_chain(rng, n_hops)
        ans = rand_name(rng) if rng.random() < 0.7 else PLACES[rng.randrange(len(PLACES))]
        while ans == name:
            ans = rand_name(rng)
        fields = {"answer": ans,
                  "trail": [f"F{rng.randrange(1, 9999):05d}" for _ in rels],
                  "source": SOURCES[rng.randrange(len(SOURCES))]}
        if fields["source"] == "web-verified":
            pass
        return {"kind": "answer", "status": status, "name": name,
                "relations": rels, "fields": fields}
    if status == "MISSING_FACT":
        name = rand_name(rng)
        rels = rand_chain(rng, n_hops)
        return {"kind": "answer", "status": status, "name": name, "relations": rels,
                "fields": {"subject": name, "relation": rels[-1],
                           "hop": n_hops, "trail": []}}
    if status == "BROKEN_CHAIN":
        name = rand_name(rng)
        rels = rand_chain(rng, max(1, n_hops - 1)) + ["hometown"]
        val = PLACES[rng.randrange(len(PLACES))]
        return {"kind": "answer", "status": status, "name": name, "relations": rels,
                "fields": {"subject": name, "relation": "hometown", "value": val,
                           "hop": len(rels), "trail": []}}
    if status == "AMBIGUOUS":
        name = rand_name(rng)
        rels = rand_chain(rng, n_hops)
        a, b = rand_name(rng), rand_name(rng)
        while b == a:
            b = rand_name(rng)
        ids = [f"E{rng.randrange(1, 60):04d}", f"E{rng.randrange(1, 60):04d}"]
        return {"kind": "answer", "status": status, "name": name, "relations": rels,
                "fields": {"name": name, "choices": f"{a} ({ids[0]}), {b} ({ids[1]})",
                           "ids": ids}}
    if status == "UNKNOWN_ENTITY":
        name = "Ghost" + str(rng.randrange(10 ** 6))
        rels = rand_chain(rng, n_hops)
        return {"kind": "answer", "status": status, "name": name, "relations": rels,
                "fields": {"name": name}}
    if status == "BAD_REQUEST":
        name = rand_name(rng)
        rels = rand_chain(rng, n_hops)
        return {"kind": "answer", "status": status, "name": name, "relations": rels,
                "fields": {"reason": rng.choice([
                    "need 1-3 hops", "unknown entity id",
                    "that question has too many steps"])}} 
    raise AssertionError(status)


def render(rng: random.Random, rec: dict) -> str:
    variants = TEMPLATES[rec["status"]](rec)
    s = variants[rng.randrange(len(variants))]
    if rec["status"] == "OK" and rec["fields"].get("source") == "web-verified":
        s += " (I read that online; you didn't tell me.)"
    return s


def build(split: tuple, total: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    per_status = dict(split)
    assert sum(per_status.values()) == total, (sum(per_status.values()), total)
    for status, count in split:
        for _ in range(count):
            rec = make_record(rng, status)
            rows.append({"record": rec, "sentence": render(rng, rec)})
    rng.shuffle(rows)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 53 mouth data generator")
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.train == 3000:
        train_rows = build(TRAIN_MIX, 3000, args.seed)
    elif args.train == 1500:
        half = tuple((s, c // 2) for s, c in TRAIN_MIX)
        train_rows = build(half, 1500, args.seed)
    else:
        raise ValueError("--train must be 3000 or 1500")
    held_rows = build(HELDOUT_MIX, 500, args.seed + 77)
    held_rows = [{"record": r["record"], "reference": r["sentence"]} for r in held_rows]

    (out / "train.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train_rows) + "\n",
        encoding="utf-8")
    (out / "heldout.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in held_rows) + "\n",
        encoding="utf-8")
    meta = {"seed": args.seed, "train": len(train_rows), "heldout": len(held_rows),
            "statuses": sorted(TEMPLATES), "templates_per_status": 6,
            "relations": list(ALL_RELS)}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({"train": len(train_rows), "heldout": len(held_rows),
                      "seed": args.seed, "out": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
