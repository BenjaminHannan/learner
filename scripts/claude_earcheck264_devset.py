#!/usr/bin/env python3
"""Exp 264 -- NEW QA dev set (sealed generator). Own wordings, fictional names
(fresh pools, not taken from any panel or README), v2 canonical relations.

- D_rel (16): wrong-relation traps (R16 style). A naive reader picks the wrong
  relation word; gold holds only what is stated, with the right relation.
- D_stale (16): stale values (R17 style). Corrections where the old value is
  named in the same turn in a different position than "not X"; gold holds only
  the new value.

python claude_earcheck264_devset.py --out artifacts/claude-earcheck264-20260923/dev_264.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def T(s, r, v):
    return f"TEACH | {s} | {r} | {v}"


def rows():
    out = []
    n = 0

    def add(tag, turn, frames):
        nonlocal n
        out.append(dict(id=f"d264-{n:04d}", turn=turn, frames=frames,
                        family="checkdev", tid=tag, tag=tag))
        n += 1

    # ---- D_rel: wrong-relation traps ----
    # 1-2: works WITH (person) vs works FOR (org). Gold: employer = org only.
    add("D_rel", "I work with Ansel Ashford at Cinderford Mill.",
        [T("me", "employer", "Cinderford Mill")])
    add("D_rel", "Briony Blackmoor works with me at Dunnsmouth Looms.",
        [T("Briony Blackmoor", "employer", "Dunnsmouth Looms")])
    # 3-4: brother's wife = sister_in_law, never wife.
    add("D_rel", "My brother's wife is Delia Emberley.",
        [T("me", "sister_in_law", "Delia Emberley")])
    add("D_rel", "Corvin Candlewick is married to my sister Willa.",
        [T("me", "brother_in_law", "Corvin Candlewick")])
    # 5-6: lives NEAR vs lives IN. Gold: city = the in-place only.
    add("D_rel", "I live near Aldermere, in a cottage in Foxmere.",
        [T("me", "city", "Foxmere")])
    add("D_rel", "Galen Hartfield lives close to Gorsefield but in Heatherby.",
        [T("Galen Hartfield", "city", "Heatherby")])
    # 7-8: used to work at (past, not current). Gold: NONE or only current.
    add("D_rel", "I used to work at Ironfield Forge.",
        ["NONE"])
    add("D_rel", "I used to work at Ironfield Forge, now I weave at Marrowgate Looms.",
        [T("me", "employer", "Marrowgate Looms")])
    # 9-10: studies WITH (person) vs studies AT (school).
    add("D_rel", "I study with Hester Ironfield at Oatfield College.",
        [T("me", "school", "Oatfield College")])
    add("D_rel", "Ivo Keldwick coaches at Pebblewick Club.",
        [T("Ivo Keldwick", "employer", "Pebblewick Club")])
    # 11-12: training to be (goal, not current job) beside a real fact.
    add("D_rel", "Jessamine Lantern trains to be a mason, and lives in Rushmere.",
        [T("Jessamine Lantern", "city", "Rushmere")])
    add("D_rel", "Kester Marrow wants to be a harper; his brother Pell plays at Stonefield Hall.",
        [T("Pell", "employer", "Stonefield Hall")])
    # 13-14: friend's house vs own city; employer's city vs own.
    add("D_rel", "My friend Linnet Oatfield lives in Thornwick.",
        [T("me", "friend", "Linnet Oatfield"),
         T("Linnet Oatfield", "city", "Thornwick")])
    add("D_rel", "Marlow Pebblewick works for a mill in Willowmere.",
        [T("Marlow Pebblewick", "employer", "mill in Willowmere")])
    # 15-16: pet species vs generic; language spoken vs taught.
    add("D_rel", "My sister Nerys keeps a rabbit called Sedge.",
        [T("me", "sister", "Nerys"),
         T("me", "rabbit", "Sedge")])
    add("D_rel", "Osric Rushmere teaches Velloric at Yewfield School.",
        [T("Osric Rushmere", "employer", "Yewfield School")])

    # ---- D_stale: stale values, old named without "not X" ----
    add("D_stale", "We moved from Aldermere to Cinderford.",
        [T("me", "city", "Cinderford")])
    add("D_stale", "It is Dunnsmouth now, it used to be Eldervale.",
        [T("me", "city", "Dunnsmouth")])
    add("D_stale", "Quenna Stonefield left Foxmere for Gorsefield.",
        [T("Quenna Stonefield", "city", "Gorsefield")])
    add("D_stale", "Rafe Thornwick changed schools from Heatherby to Ironfield Academy.",
        [T("Rafe Thornwick", "school", "Ironfield Academy")])
    add("D_stale", "Thea Willowmere now weaves at Marrowgate Looms, not the old mill at Oatfield.",
        [T("Thea Willowmere", "employer", "Marrowgate Looms")])
    add("D_stale", "Ulmer Yewfield retired from Pebblewick Forge and keeps bees in Rushmere.",
        [T("Ulmer Yewfield", "city", "Rushmere")])
    add("D_stale", "My old dog was Bristle, now my dog is Cinder.",
        [T("me", "dog", "Cinder")])
    add("D_stale", "Willa Zimmer moved her shop from Stonefield to Thornwick Market.",
        [T("Willa Zimmer", "employer", "Thornwick Market")])
    add("D_stale", "Yorick Aldercroft used to speak Andic, now he speaks Tormic.",
        [T("Yorick Aldercroft", "language", "Tormic")])
    add("D_stale", "Zella Blackmoor was born in Cinderford but lives in Duskhaven.",
        [T("Zella Blackmoor", "place_of_birth", "Cinderford"),
         T("Zella Blackmoor", "city", "Duskhaven")])
    add("D_stale", "Bramwell Dovecote sold his horse Flax and bought a horse called Moss.",
        [T("Bramwell Dovecote", "horse", "Moss")])
    add("D_stale", "Ansel Foxford no longer tenants at Emberley Farm; he tenants at Fern Hollow Farm.",
        [T("Ansel Foxford", "employer", "Fern Hollow Farm")])
    add("D_stale", "My sister Briony Dovecote used to live in Grimestone, now she lives in Hollybush.",
        [T("me", "sister", "Briony Dovecote"),
         T("Briony Dovecote", "city", "Hollybush")])
    add("D_stale", "Farah Lantern switched from the harp to the fiddle.",
        [T("Farah Lantern", "instrument", "fiddle")])
    add("D_stale", "Galen Pebblewick's old boss was Osric; his boss now is Pell Marrow.",
        [T("Galen Pebblewick", "boss", "Pell Marrow")])
    add("D_stale", "Hester Rushmere moved back to Aldermere after a year in Cinderford.",
        [T("Hester Rushmere", "city", "Aldermere")])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rs = rows()
    from collections import Counter
    cnt = Counter(r["tag"] for r in rs)
    print(len(rs), dict(cnt))
    assert cnt["D_rel"] >= 15 and cnt["D_stale"] >= 15, cnt
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
