#!/usr/bin/env python3
"""Exp 261 -- NEW checker dev set, sealed generator (v2: pools >= 30 with
coprime strides, so all 210 turns are unique; v1 devset.py had period-10
collisions in D_our and is NOT used).

210 rows (all non-question TEACH-or-nothing rows):
  D_pre    30  pretend/hypothetical -> gold NONE
  D_plan   30  plans/goals/wishes (15 pure -> NONE; 15 plan + real fact
            -> gold is the real fact only)
  D_checkq 30  check-questions with NO "?" -> gold NONE
  D_apos   30  "A's R is B and he/she ..." -> TWO gold frames (fact on B)
  D_our    30  first-person plural owners -> gold subject is "me"
  D_plain  60  plain true facts -> gold TEACH

Fictional names only. Nothing read, copied or rebuilt from any TEST-ONLY
panel; categories only from the brief. Relations are relation-table-v2
canonical names.

python claude_earcheck261_devset2.py --out artifacts/claude-earcheck261-20260922/dev_checker.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIRST = ["Tilda", "Bram", "Odell", "Sanna", "Quill", "Mirella", "Doran",
         "Isolde", "Fenwick", "Liora", "Casimir", "Petra", "Aldous",
         "Vesper", "Norwin", "Elswyth", "Garran", "Hollis", "Imogen",
         "Jorunn", "Kelda", "Leander", "Moss", "Nerissa", "Orson",
         "Prilla", "Roscoe", "Sable", "Tamsin", "Ulric", "Wrenna",
         "Ysolde", "Zeph", "Anwen", "Borris", "Celandine", "Drystan",
         "Eppie", "Fable", "Godric"]
LAST = ["Marsh", "Kettle", "Thistledown", "Barrow", "Coppersmith",
        "Halloway", "Brindle", "Ashcombe", "Winterbourne", "Plowright",
        "Goodfellow", "Nettlefold", "Quarryman", "Ravensworth", "Slade",
        "Tinker", "Underbough", "Vellacott", "Woolmer", "Pepperell"]
PETS = ["Pip", "Midge", "Tansy", "Biscuit", "Clove", "Doodle", "Fig",
        "Guster", "Hazel", "Inky", "Juniper", "Kip", "Lark", "Moppet",
        "Nugget", "Olly", "Pepper", "Quince", "Rowan", "Sorrel",
        "Taffy", "Ursa", "Vetch", "Wicket", "Xan", "Yarrow", "Ziggy",
        "Bramble", "Clover", "Dandelion"]
CITIES = ["Millhaven", "Oakhollow", "Brenford", "Dunmere", "Eastvale",
          "Foxglove", "Grimshaw", "Harborlight", "Inkwell", "Kestrel Bay",
          "Larkspur", "Mudford", "Netherby", "Ouselton", "Piddlewick",
          "Quoit Hollow", "Rillston", "Sedgebrook", "Thornbury", "Ullswater",
          "Vexford", "Wimborne", "Yarcombe", "Zennor", "Ashby St Ledgers",
          "Bicknacre", "Cranham", "Ditchling", "Elterwater", "Fowey"]
JOBS = ["baker", "locksmith", "beekeeper", "cartographer", "florist",
        "luthier", "midwife", "stonemason", "tidewaiter", "wheelwright",
        "miller", "cobbler", "glazier", "cooper", "that cher".replace(" ", ""),
        "ferrier", "glover", "horner", "inker", "joiner",
        "kilnmaster", "lamplighter", "maltster", "netmaker", "ostler",
        "potter", "quilter", "ropemaker", "saddler", "tanner"]
LANGS = ["Dovran", "Keshtic", "Mirellian"]
RELS = ["sister", "brother", "cousin", "aunt", "uncle", "mother", "father",
        "friend", "partner", "husband", "wife", "son", "daughter"]


def T(s, r, v):
    return f"TEACH | {s} | {r} | {v}"


def pick(pool, i, stride=7, off=0):
    return pool[(i * stride + off) % len(pool)]


def pname(i, off=0):
    return pick(FIRST, i, 7, off) + " " + pick(LAST, i, 3, off)


def rows():
    out = []
    n = 0

    def add(tag, turn, frames):
        nonlocal n
        out.append(dict(id=f"c261-{n:04d}", turn=turn, frames=frames,
                        family="checkdev", tid=tag, tag=tag))
        n += 1

    # ---- D_pre (30) -> NONE
    pre_open = ["Let's say {a} lives in {c}.", "Imagine {a} works as a {j}.",
                "Suppose my {r} is {a}.", "Pretend our dog is called {p}.",
                "What if {a} moved to {c}?", "Say that {a} is my {r}."]
    for i in range(30):
        t = pre_open[i % len(pre_open)].format(
            a=pname(i), c=pick(CITIES, i), j=pick(JOBS, i + 1),
            r=pick(RELS, i), p=pick(PETS, i + 2))
        add("D_pre", t, ["NONE"])

    # ---- D_plan pure (15) -> NONE
    plan_pure = ["I am training to be a {j}.", "I want to be a {j}.",
                 "I am hoping to move to {c}.", "I am going to start at {c}.",
                 "I plan to move to {c}.", "I will start as a {j} next spring."]
    for i in range(15):
        t = plan_pure[i % len(plan_pure)].format(c=pick(CITIES, i + 3),
                                                 j=pick(JOBS, i + 5))
        add("D_plan", t, ["NONE"])
    # ---- D_plan mixed (15) -> real fact only
    for i in range(15):
        a, c, j = pname(i + 11, 1), pick(CITIES, i + 1), pick(JOBS, i + 2)
        r = pick(RELS, i + 4)
        if i % 3 == 0:
            add("D_plan", f"I am training to be a {j}, but my {r} is {a}.",
                [T("me", r, a)])
        elif i % 3 == 1:
            c2 = pick(CITIES, i + 16)
            add("D_plan", f"I want to move to {c}, though I live in {c2}.",
                [T("me", "city", c2)])
        else:
            p = pick(PETS, i + 9)
            add("D_plan", f"I plan to open a shop in {c}; my dog is {p}.",
                [T("me", "dog", p)])

    # ---- D_checkq (30) -> NONE
    for i in range(30):
        a, r, c = pname(i + 5, 2), pick(RELS, i + 1), pick(CITIES, i + 4)
        k = i % 3
        if k == 0:
            t = f"my {r} is {a}, right"
        elif k == 1:
            t = f"so {a} lives in {c}"
        else:
            t = f"{a} is my {r}, isn't it"
        add("D_checkq", t, ["NONE"])

    # ---- D_apos (30) -> both frames, fact on B
    for i in range(30):
        a, b = pname(i + 2, 3), pick(FIRST, i + 13)
        r, pro = pick(RELS, i + 3), ("she" if i % 2 == 0 else "he")
        k = i % 3
        if k == 0:
            j = pick(JOBS, i + 6)
            add("D_apos", f"{a}'s {r} is {b} and {pro} works as a {j}.",
                [T(a, r, b), T(b, "occupation", j)])
        elif k == 1:
            c = pick(CITIES, i + 8)
            add("D_apos", f"{a}'s {r} is {b} and {pro} lives in {c}.",
                [T(a, r, b), T(b, "city", c)])
        else:
            lg = LANGS[i % 3]
            add("D_apos", f"{a}'s {r} is {b} and {pro} speaks {lg}.",
                [T(a, r, b), T(b, "language", lg)])

    # ---- D_our (30) -> subject "me"
    for i in range(30):
        r, a = pick(RELS, i + 6), pname(i + 9, 4)
        k = i % 5
        if k == 0:
            add("D_our", f"Our {r} is {a}.", [T("me", r, a)])
        elif k == 1:
            p = pick(PETS, i + 11)
            add("D_our", f"Our dog is {p}.", [T("me", "dog", p)])
        elif k == 2:
            c = pick(CITIES, i + 12)
            add("D_our", f"We live in {c}.", [T("me", "city", c)])
        elif k == 3:
            add("D_our", f"Our neighbour is {a}.", [T("me", "neighbour", a)])
        else:
            c, p = pick(CITIES, i + 13), pick(PETS, i + 14)
            add("D_our", f"We work at {c} Mill, and our cat is {p}.",
                [T("me", "workplace", c + " Mill"), T("me", "cat", p)])

    # ---- D_plain (60) -> TEACH
    for i in range(60):
        a = pname(i * 2 + 1, 5)
        k = i % 6
        if k == 0:
            r = pick(RELS, i)
            add("D_plain", f"My {r} is {a}.", [T("me", r, a)])
        elif k == 1:
            c = pick(CITIES, i + 15)
            add("D_plain", f"{a} lives in {c}.", [T(a, "city", c)])
        elif k == 2:
            j = pick(JOBS, i + 17)
            add("D_plain", f"{a} works as a {j}.", [T(a, "occupation", j)])
        elif k == 3:
            p = pick(PETS, i + 19)
            add("D_plain", f"My cat is {p}.", [T("me", "cat", p)])
        elif k == 4:
            c = pick(CITIES, i + 21)
            add("D_plain", f"I live in {c}.", [T("me", "city", c)])
        else:
            lg = LANGS[(i + 1) % 3]
            add("D_plain", f"{a} speaks {lg}.", [T(a, "language", lg)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rs = rows()
    from collections import Counter
    cnt = Counter(r["tag"] for r in rs)
    print(len(rs), dict(cnt))
    assert cnt["D_pre"] >= 30 and cnt["D_plan"] >= 30 and cnt["D_checkq"] >= 30
    assert cnt["D_apos"] >= 30 and cnt["D_our"] >= 30 and cnt["D_plain"] >= 60
    turns = [r["turn"] for r in rs]
    assert len(set(turns)) == len(rs), "duplicate turns remain"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rs))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
