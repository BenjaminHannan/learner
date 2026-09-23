#!/usr/bin/env python3
"""Exp 261b -- NEW guard dev set (sealed generator). Own wordings, fictional
names (fresh pools, not taken from any panel or README), v2 canonical
relations. Two blocks:

- D_typo (24): a misspelt everyday word (never a name) sits right next to a
  name: livs, werks, bron, frend, siter, broter, cousn, unkle, speks, schol.
  Gold holds the clean spans only (20 TEACH rows + 4 check-style NONE rows).
- D_lower (24): all-lowercase turns with lowercase names; gold keeps the
  lowercase spans.

python claude_earcheck261b_devset5.py --out artifacts/claude-earcheck261b-20260923/dev_261b.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIRST = ["Ansel", "Briony", "Corvin", "Delia", "Emric", "Farah", "Galen",
         "Hester", "Ivo", "Jessamine", "Kester", "Linnet", "Marlow", "Nerys",
         "Osric", "Pell", "Quenna", "Rafe", "Thea", "Ulmer", "Willa", "Yorick",
         "Zella", "Bramwell"]
LAST = ["Ashford", "Blackmoor", "Candlewick", "Dovecote", "Emberley", "Foxford",
        "Hartfield", "Ironfield", "Keldwick", "Lantern", "Marrow", "Oatfield",
        "Pebblewick", "Rushmere", "Stonefield", "Thornwick", "Willowmere",
        "Yewfield", "Zimmer", "Aldercroft"]
CITIES = ["Aldermere", "Cinderford", "Dunnsmouth", "Eldervale", "Foxmere",
          "Gorsefield", "Heatherby", "Ironfield", "Marrowgate", "Oatfield",
          "Pebblewick", "Rushmere", "Stonefield", "Willowmere", "Yewfield",
          "Duskhaven", "Elmwold", "Fern Hollow", "Grimestone", "Hollybush"]
JOBS = ["blacksmith", "weaver", "mason", "shepherd", "ferryman", "chandler",
        "cutler", "fuller", "gilder", "harper", "jester", "knitter",
        "milliner", "sawyer", "sailmaker", "tallowman", "upholsterer",
        "vintner", "wheelera", "zitherist"]
LANGS = ["Velloric", "Andic", "Tormic"]
PETS = ["Acorn", "Bristle", "Dusk", "Ember", "Flax", "Gorse", "Hush", "Nib",
        "Puddle", "Reed", "Smudge", "Thistle", "Whisper", "Zest", "Cinder",
        "Moss", "Pebble", "Rill", "Sedge", "Tarn"]
RELS = ["sister", "brother", "cousin", "aunt", "uncle", "mother", "father",
        "friend", "neighbour", "partner", "son", "daughter"]


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
        out.append(dict(id=f"b261b-{n:04d}", turn=turn, frames=frames,
                        family="checkdev", tid=tag, tag=tag))
        n += 1

    # ---- D_typo: 20 TEACH rows, typo word adjacent to a name ----
    # Each row computes its names once, shared by turn and gold.
    for j in range(2):
        jj = j
        a, c, jb = pname(jj, 1), pick(CITIES, jj, 2), pick(JOBS, jj, 6)
        add("D_typo", f"My frend {a} lives in {c}.",
            [T("me", "friend", a), T(a, "city", c)])
    for j in range(2):
        jj = 10 + j
        a, c = pname(jj, 3), pick(CITIES, jj, 4)
        add("D_typo", f"{a} livs in {c}.", [T(a, "city", c)])
    for j in range(2):
        jj = 20 + j
        a, jb = pname(jj, 5), pick(JOBS, jj, 6)
        add("D_typo", f"{a} werks as a {jb}.", [T(a, "occupation", jb)])
    for j in range(2):
        jj = 30 + j
        a, c = pname(jj, 7), pick(CITIES, jj, 8)
        add("D_typo", f"{a} was bron in {c}.", [T(a, "place_of_birth", c)])
    for j in range(2):
        jj = 40 + j
        a, lg = pname(jj, 9), pick(LANGS, jj, 10)
        add("D_typo", f"My siter {a} speks {lg}.",
            [T("me", "sister", a), T(a, "language", lg)])
    for j in range(2):
        jj = 50 + j
        a, p = pname(jj, 11), pick(PETS, jj, 12)
        add("D_typo", f"My broter {a} keeps a dog called {p}.",
            [T("me", "brother", a), T("me", "dog", p)])
    for j in range(2):
        jj = 60 + j
        a, c = pname(jj, 13), pick(CITIES, jj, 14)
        add("D_typo", f"{a}, my cousn, lives in {c}.",
            [T("me", "cousin", a), T(a, "city", c)])
    for j in range(2):
        jj = 70 + j
        a, jb = pname(jj, 15), pick(JOBS, jj, 16)
        add("D_typo", f"My unkle {a} werks as a {jb}.",
            [T("me", "uncle", a), T(a, "occupation", jb)])
    for j in range(2):
        jj = 80 + j
        a, c = pname(jj, 17), pick(CITIES, jj, 18)
        add("D_typo", f"scholmate {a} studied at {c} Academy.",
            [T(a, "school", c + " Academy")])
    for j in range(2):
        jj = 90 + j
        a, c = pname(jj, 19), pick(CITIES, jj, 20)
        add("D_typo", f"Our frend {a} livs in {c}.",
            [T("me", "friend", a), T(a, "city", c)])
    # 4 typo check-style rows, gold NONE
    none_pats = [
        "so {a} livs in {c}",
        "{a} werks as a {jb}, right",
        "so my cousn {a} speks {lg}",
        "{a} was bron in {c}, isn't it",
    ]
    for k, pat in enumerate(none_pats):
        jj = 100 + k
        add("D_typo", pat.format(a=pname(jj, 21), c=pick(CITIES, jj, 22),
                                 jb=pick(JOBS, jj, 23), lg=pick(LANGS, jj, 24)),
            ["NONE"])

    # ---- D_lower: 24 all-lowercase rows ----
    lower_pats = [
        ("my {r} is {a}.", lambda j: [T("me", pick(RELS, j, 30), pname(j, 31).lower())]),
        ("{a} lives in {c}.", lambda j: [T(pname(j, 32).lower(), "city", pick(CITIES, j, 33).lower())]),
        ("{a} works as a {jb}.", lambda j: [T(pname(j, 34).lower(), "occupation", pick(JOBS, j, 35))]),
        ("my dog is {p}.", lambda j: [T("me", "dog", pick(PETS, j, 36).lower())]),
        ("we live in {c}.", lambda j: [T("me", "city", pick(CITIES, j, 37).lower())]),
        ("{a} speaks {lg}.", lambda j: [T(pname(j, 38).lower(), "language", pick(LANGS, j, 39).lower())]),
    ]
    for k, (pat, gold) in enumerate(lower_pats):
        for j in range(4):
            jj = 200 + k * 4 + j
            if "{r}" in pat:
                r = pick(RELS, jj, 30)
                a = pname(jj, 31).lower()
                t = pat.format(r=r, a=a)
                g = [T("me", r, a)]
            elif "{a}" in pat and "{c}" in pat:
                a = pname(jj, 32).lower()
                c = pick(CITIES, jj, 33).lower()
                t = pat.format(a=a, c=c)
                g = [T(a, "city", c)]
            elif "{jb}" in pat:
                a = pname(jj, 34).lower()
                t = pat.format(a=a, jb=pick(JOBS, jj, 35))
                g = gold(jj)
            elif "{p}" in pat:
                p = pick(PETS, jj, 36).lower()
                t = pat.format(p=p)
                g = [T("me", "dog", p)]
            elif "{lg}" in pat:
                a = pname(jj, 38).lower()
                lg = pick(LANGS, jj, 39).lower()
                t = pat.format(a=a, lg=lg)
                g = [T(a, "language", lg)]
            else:
                c = pick(CITIES, jj, 37).lower()
                t = pat.format(c=c)
                g = [T("me", "city", c)]
            assert t == t.lower(), t
            add("D_lower", t, g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rs = rows()
    from collections import Counter
    cnt = Counter(r["tag"] for r in rs)
    print(len(rs), dict(cnt))
    assert cnt["D_typo"] >= 20 and cnt["D_lower"] >= 20
    # every subject/value (other than me) appears word for word in its turn
    for r in rs:
        for f in r["frames"]:
            if f == "NONE":
                continue
            parts = [x.strip() for x in f.split("|")]
            for span in (parts[1], parts[3]):
                if span != "me":
                    assert span in r["turn"], (r["turn"], span)
    turns = [r["turn"] for r in rs]
    assert len(turns) == len(set(turns)), "duplicate turns"
    assert all(t == t.strip() for t in turns)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rs))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
