#!/usr/bin/env python3
"""Exp 261 -- NEW checker dev set, written by the builder in his own wording.

210 rows (all non-question TEACH-or-nothing rows):
  D_pre    30  pretend/hypothetical ("let's say", "imagine", "suppose",
            "pretend", "what if", "say that") -> gold NONE
  D_plan   30  plans/goals/wishes (15 pure -> NONE; 15 plan clause + a real
            current fact in the same turn -> gold is the real fact only)
  D_checkq 30  check-questions with NO "?" ("X, right", "so X", lowercase)
            -> gold NONE
  D_apos   30  "A's R is B and he/she ..." (pronoun = B) -> TWO gold frames:
            A-R-B plus B's own fact (never A)
  D_our    30  first-person plural owners ("our", "we", "us" + relative, pet,
            home, workplace, neighbour) -> gold subject is "me"
  D_plain  60  plain true facts -> gold TEACH (false rejections show here)

Fictional names only. Nothing read, copied or rebuilt from any TEST-ONLY
panel; categories only from the brief. Relations are relation-table-v2
canonical names.

python claude_earcheck261_devset.py --out artifacts/claude-earcheck261-20260922/dev_checker.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIRST = ["Tilda", "Bram", "Odell", "Sanna", "Quill", "Mirella", "Doran",
         " Isolde", "Fenwick", "Liora", "Casimir", "Petra", "Aldous",
         "Vesper", "Norwin", "Elswyth", "Garran", "Hollis", "Imogen",
         "Jorunn", "Kelda", "Leander", "Moss", "Nerissa", "Orson",
         "Prilla", "Roscoe", "Sable", "Tamsin", "Ulric", "Wrenna",
         "Ysolde", "Zeph", "Anwen", "Borris", "Celandine", "Drystan",
         "Eppie", "Fable", "Godric"]
FIRST = [n.strip() for n in FIRST]
LAST = ["Marsh", "Kettle", "Thistledown", "Barrow", "Fenwick", "Coppersmith",
        "Halloway", "Brindle", "Ashcombe", "Winterbourne", "Plowright",
        "Goodfellow", "Nettlefold", "Quarryman", "Ravensworth", "Slade",
        "Tinker", "Underbough", "Vellacott", "Woolmer"]
PETS = ["Pip", "Midge", "Tansy", "Biscuit", "Clove", "Doodle", "Fig",
        "Guster", "Hazel", "Inky"]
CITIES = ["Millhaven", "Oakhollow", "Brenford", "C picker", "Dunmere",
          "Eastvale", "Foxglove", "Grimshaw", "Harborlight", "Inkwell"]
CITIES = [c.strip() for c in CITIES]
CITIES = ["Millhaven", "Oakhollow", "Brenford", "Dunmere", "Eastvale",
          "Foxglove", "Grimshaw", "Harborlight", "Inkwell", "Kestrel Bay"]
JOBS = ["baker", "locksmith", "beekeeper", "cartographer", "florist",
        "luthier", "midwife", "stonemason", "tidewaiter", "wheelwright"]

RELS = ["sister", "brother", "cousin", "aunt", "uncle", "mother", "father",
        "friend", "partner", "husband", "wife", "son", "daughter"]


def T(teach_s, teach_r, teach_v):
    return f"TEACH | {teach_s} | {teach_r} | {teach_v}"


def rows():
    out = []
    n = 0

    def add(tag, turn, frames):
        nonlocal n
        out.append(dict(id=f"c261-{n:04d}", turn=turn, frames=frames,
                        family="checkdev", tid=tag, tag=tag))
        n += 1

    # ---- D_pre: pretend / hypothetical -> NONE
    pre_open = ["Let's say {a} lives in {c}.", "Imagine {a} works as a {j}.",
                "Suppose my {r} is {a}.", "Pretend our dog is called {p}.",
                "What if {a} moved to {c}?", "Say that {a} is my {r}."]
    for i in range(30):
        a, b = FIRST[i % len(FIRST)], FIRST[(i + 7) % len(FIRST)]
        t = pre_open[i % len(pre_open)].format(
            a=a + " " + LAST[i % len(LAST)], b=b, c=CITIES[i % len(CITIES)],
            j=JOBS[i % len(JOBS)], r=RELS[i % len(RELS)], p=PETS[i % len(PETS)])
        add("D_pre", t, ["NONE"])

    # ---- D_plan: 15 pure plans -> NONE
    plan_pure = ["I am training to be a {j}.", "I want to be a {j}.",
                 "I am hoping to move to {c}.", "I am going to start at {c}.",
                 "I plan to move to {c}.", "I will start as a {j} next spring."]
    for i in range(15):
        t = plan_pure[i % len(plan_pure)].format(
            c=CITIES[(i + 3) % len(CITIES)], j=JOBS[(i + 5) % len(JOBS)])
        add("D_plan", t, ["NONE"])
    # ---- D_plan: 15 plan clause + real fact -> gold is the real fact only
    for i in range(15):
        a = FIRST[(i + 11) % len(FIRST)] + " " + LAST[(i + 2) % len(LAST)]
        c, j = CITIES[(i + 1) % len(CITIES)], JOBS[(i + 2) % len(JOBS)]
        r = RELS[(i + 4) % len(RELS)]
        if i % 3 == 0:
            t = f"I am training to be a {j}, but my {r} is {a}."
            add("D_plan", t, [T("me", r, a)])
        elif i % 3 == 1:
            t = f"I want to move to {c}, though I live in {CITIES[(i+6) % len(CITIES)]}."
            add("D_plan", t, [T("me", "city", CITIES[(i + 6) % len(CITIES)])])
        else:
            t = f"I plan to open a shop in {c}; my dog is {PETS[i % len(PETS)]}."
            add("D_plan", t, [T("me", "dog", PETS[i % len(PETS)])])

    # ---- D_checkq: checks without "?" -> NONE
    for i in range(30):
        a = FIRST[(i + 5) % len(FIRST)] + " " + LAST[(i + 9) % len(LAST)]
        r = RELS[(i + 1) % len(RELS)]
        c = CITIES[(i + 4) % len(CITIES)]
        k = i % 3
        if k == 0:
            t = f"my {r} is {a}, right"
        elif k == 1:
            t = f"so {a} lives in {c}"
        else:
            t = f"{a} is my {r}, isn't it"
        add("D_checkq", t, ["NONE"])

    # ---- D_apos: A's R is B and he/she ... -> BOTH frames, fact on B
    jobs2 = ["baker", "miller", "cobbler", "glazier", "cooper"]
    for i in range(30):
        a = FIRST[(i + 2) % len(FIRST)] + " " + LAST[(i + 5) % len(LAST)]
        b = FIRST[(i + 13) % len(FIRST)]
        r = RELS[(i + 3) % len(RELS)]
        pro = "she" if i % 2 == 0 else "he"
        k = i % 3
        if k == 0:
            t = f"{a}'s {r} is {b} and {pro} works as a {jobs2[i % len(jobs2)]}."
            add("D_apos", t, [T(a, r, b), T(b, "occupation", jobs2[i % len(jobs2)])])
        elif k == 1:
            c = CITIES[(i + 2) % len(CITIES)]
            t = f"{a}'s {r} is {b} and {pro} lives in {c}."
            add("D_apos", t, [T(a, r, b), T(b, "city", c)])
        else:
            t = f"{a}'s {r} is {b} and {pro} speaks {['Dovran', 'Keshtic', 'Mirellian'][i % 3]}."
            add("D_apos", t, [T(a, r, b), T(b, "language",
                                            ['Dovran', 'Keshtic', 'Mirellian'][i % 3])])

    # ---- D_our: plural owners -> subject "me"
    for i in range(30):
        r = RELS[(i + 6) % len(RELS)]
        a = FIRST[(i + 9) % len(FIRST)] + " " + LAST[(i + 3) % len(LAST)]
        k = i % 5
        if k == 0:
            t = f"Our {r} is {a}."
            add("D_our", t, [T("me", r, a)])
        elif k == 1:
            t = f"Our dog is {PETS[(i + 1) % len(PETS)]}."
            add("D_our", t, [T("me", "dog", PETS[(i + 1) % len(PETS)])])
        elif k == 2:
            t = f"We live in {CITIES[(i + 7) % len(CITIES)]}."
            add("D_our", t, [T("me", "city", CITIES[(i + 7) % len(CITIES)])])
        elif k == 3:
            t = f"Us kids grew up near {CITIES[(i + 8) % len(CITIES)]}, and our neighbour is {a}."
            add("D_our", t, [T("me", "neighbour", a)])
        else:
            t = f"We work at {CITIES[(i + 5) % len(CITIES)]} Mill, and our cat is {PETS[(i + 4) % len(PETS)]}."
            add("D_our", t, [T("me", "workplace", CITIES[(i + 5) % len(CITIES)] + " Mill"),
                             T("me", "cat", PETS[(i + 4) % len(PETS)])])

    # ---- D_plain: 60 plain true facts
    for i in range(60):
        a = FIRST[(i * 3 + 1) % len(FIRST)] + " " + LAST[(i * 7 + 4) % len(LAST)]
        k = i % 6
        if k == 0:
            t = f"My {RELS[i % len(RELS)]} is {a}."
            add("D_plain", t, [T("me", RELS[i % len(RELS)], a)])
        elif k == 1:
            t = f"{a} lives in {CITIES[i % len(CITIES)]}."
            add("D_plain", t, [T(a, "city", CITIES[i % len(CITIES)])])
        elif k == 2:
            t = f"{a} works as a {JOBS[i % len(JOBS)]}."
            add("D_plain", t, [T(a, "occupation", JOBS[i % len(JOBS)])])
        elif k == 3:
            t = f"My cat is {PETS[i % len(PETS)]}."
            add("D_plain", t, [T("me", "cat", PETS[i % len(PETS)])])
        elif k == 4:
            t = f"I live in {CITIES[(i + 2) % len(CITIES)]}."
            add("D_plain", t, [T("me", "city", CITIES[(i + 2) % len(CITIES)])])
        else:
            t = f"{a} speaks {['Dovran', 'Keshtic', 'Mirellian'][(i + 1) % 3]}."
            add("D_plain", t, [T(a, "language", ['Dovran', 'Keshtic', 'Mirellian'][(i + 1) % 3])])

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rs = rows()
    from collections import Counter
    print(len(rs), Counter(r["tag"] for r in rs))
    turns = {r["turn"] for r in rs}
    assert len(turns) == len(rs), "duplicate turns"
    assert all(len(r["turn"].split()) >= 3 for r in rs)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rs))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
