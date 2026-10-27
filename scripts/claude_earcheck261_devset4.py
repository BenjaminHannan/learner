#!/usr/bin/env python3
"""Exp 261 -- NEW checker dev set, sealed generator (v4: D_apos pronouns agree
with B's gender so the gold "fact belongs to B" is unambiguous; v3 alternated
the pronoun blindly, making ~half its D_apos golds wrong. v1/v2 failed their
own uniqueness self-check; none of v1-v3 is used or sealed).

210 rows, quotas and patterns as v3 (own wordings, fictional names, v2
canonical relations). Only the D_apos block differs from v3.

python claude_earcheck261_devset4.py --out artifacts/claude-earcheck261-20260922/dev_checker.jsonl
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
        "miller", "cobbler", "glazier", "cooper", "thatcher",
        "ferrier", "glover", "horner", "inker", "joiner",
        "kilnmaster", "lamplighter", "maltster", "netmaker", "ostler",
        "potter", "quilter", "ropemaker", "saddler", "tanner"]
LANGS = ["Dovran", "Keshtic", "Mirellian"]
RELS = ["sister", "brother", "cousin", "aunt", "uncle", "mother", "father",
        "friend", "partner", "husband", "wife", "son", "daughter"]
# B-names with clear gender so the pronoun unambiguously refers to B (R12).
FEM_B = ["Tilda", "Sanna", "Mirella", "Isolde", "Liora", "Petra", "Elswyth",
         "Imogen", "Kelda", "Nerissa", "Prilla", "Tamsin", "Wrenna",
         "Ysolde", "Anwen", "Celandine"]
MALE_B = ["Bram", "Odell", "Quill", "Doran", "Fenwick", "Aldous", "Norwin",
          "Garran", "Leander", "Orson", "Roscoe", "Ulric", "Zeph", "Borris",
          "Drystan", "Godric"]


def T(s, r, v):
    return f"TEACH | {s} | {r} | {v}"


def pick(pool, j, off=0):
    return pool[(j * 7 + off) % len(pool)]


def pname(j, off=0):
    return pick(FIRST, j, off) + " " + pick(LAST, j + 3, off)


def rows():
    out = []
    n = 0

    def add(tag, turn, frames):
        nonlocal n
        out.append(dict(id=f"c261-{n:04d}", turn=turn, frames=frames,
                        family="checkdev", tid=tag, tag=tag))
        n += 1

    pre_open = ["Let's say {a} lives in {c}.", "Imagine {a} works as a {j}.",
                "Suppose my {r} is {a}.", "Pretend our dog is called {p}.",
                "What if {a} moved to {c}?", "Say that {a} is my {r}."]
    for k, pat in enumerate(pre_open):
        for j in range(5):
            t = pat.format(a=pname(j, k), c=pick(CITIES, j, k + 1),
                           j=pick(JOBS, j, k + 2), r=pick(RELS, j, k),
                           p=pick(PETS, j, k + 3))
            add("D_pre", t, ["NONE"])

    plan_pure = ["I am training to be a {j}.",
                 "I am hoping to move to {c}.",
                 "I plan to move to {c} and work as a {j}."]
    for k, pat in enumerate(plan_pure):
        for j in range(5):
            add("D_plan", pat.format(c=pick(CITIES, j, 10 + k),
                                     j=pick(JOBS, j, 20 + k)), ["NONE"])
    for j in range(5):
        a, c, jb = pname(j, 30), pick(CITIES, j, 40), pick(JOBS, j, 50)
        r = pick(RELS, j, 60)
        add("D_plan", f"I am training to be a {jb}, but my {r} is {a}.",
            [T("me", r, a)])
        c2 = pick(CITIES, j, 70)
        add("D_plan", f"I want to move to {c}, though I live in {c2}.",
            [T("me", "city", c2)])
        p = pick(PETS, j, 80)
        add("D_plan", f"I plan to open a shop in {c}; my dog is {p}.",
            [T("me", "dog", p)])

    for k in range(3):
        for j in range(10):
            a, r, c = pname(j, 100 + k), pick(RELS, j, 110 + k), pick(CITIES, j, 120 + k)
            if k == 0:
                t = f"my {r} is {a}, right"
            elif k == 1:
                t = f"so {a} lives in {c}"
            else:
                t = f"{a} is my {r}, isn't it"
            add("D_checkq", t, ["NONE"])

    # ---- D_apos (30 = 3 x j 0..9): pronoun agrees with B (fact is B's).
    for k in range(3):
        for j in range(10):
            a = pname(j, 200 + k)
            b = pick(FEM_B if j % 2 == 0 else MALE_B, j, 210 + k)
            pro = "she" if j % 2 == 0 else "he"
            assert a.split()[0] != b, (a, b)
            r = pick(RELS, j, 220 + k)
            if k == 0:
                jb = pick(JOBS, j, 230)
                add("D_apos", f"{a}'s {r} is {b} and {pro} works as a {jb}.",
                    [T(a, r, b), T(b, "occupation", jb)])
            elif k == 1:
                c = pick(CITIES, j, 240)
                add("D_apos", f"{a}'s {r} is {b} and {pro} lives in {c}.",
                    [T(a, r, b), T(b, "city", c)])
            else:
                lg = LANGS[j % 3]
                add("D_apos", f"{a}'s {r} is {b} and {pro} speaks {lg}.",
                    [T(a, r, b), T(b, "language", lg)])

    for k in range(5):
        for j in range(6):
            r, a = pick(RELS, j, 300 + k), pname(j, 310 + k)
            if k == 0:
                add("D_our", f"Our {r} is {a}.", [T("me", r, a)])
            elif k == 1:
                p = pick(PETS, j, 320)
                add("D_our", f"Our dog is {p}.", [T("me", "dog", p)])
            elif k == 2:
                c = pick(CITIES, j, 330)
                add("D_our", f"We live in {c}.", [T("me", "city", c)])
            elif k == 3:
                add("D_our", f"Our neighbour is {a}.", [T("me", "neighbour", a)])
            else:
                c, p = pick(CITIES, j, 340), pick(PETS, j, 350)
                add("D_our", f"We work at {c} Mill, and our cat is {p}.",
                    [T("me", "workplace", c + " Mill"), T("me", "cat", p)])

    for k in range(6):
        for j in range(10):
            a = pname(j, 400 + k)
            if k == 0:
                r = pick(RELS, j, 410)
                add("D_plain", f"My {r} is {a}.", [T("me", r, a)])
            elif k == 1:
                c = pick(CITIES, j, 420)
                add("D_plain", f"{a} lives in {c}.", [T(a, "city", c)])
            elif k == 2:
                jb = pick(JOBS, j, 430)
                add("D_plain", f"{a} works as a {jb}.", [T(a, "occupation", jb)])
            elif k == 3:
                p = pick(PETS, j, 440)
                add("D_plain", f"My cat is {p}.", [T("me", "cat", p)])
            elif k == 4:
                c = pick(CITIES, j, 450)
                add("D_plain", f"I live in {c}.", [T("me", "city", c)])
            else:
                lg = LANGS[(j + k) % 3]
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
    dups = len(rs) - len(set(turns))
    assert dups == 0, f"{dups} duplicate turns remain"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rs))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
