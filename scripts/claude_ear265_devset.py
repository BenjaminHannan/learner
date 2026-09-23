#!/usr/bin/env python3
"""Exp 265 -- own dev set (builder wording, fictional names; never any panel).

44 turns: 14 group_owner (gold [], ask_whose true), 10 mixed (gold = the
non-group fact, ask_whose true), 10 first_person (gold subject "me"), 10
named (third-person controls). Written from general knowledge only.

python claude_ear265_devset.py --out artifacts/claude-ear265-20260923/dev_265.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def T(subject, relation, value, aliases=None):
    return dict(act="TEACH", subject=subject, relation=relation,
                relation_aliases=aliases or [relation], value=value)


TURNS = [
    # group_owner x14: pure group turns; gold [] ; ask_whose true
    ("Our dog is Rex.", []),
    ("Our cat is Mimi.", []),
    ("We live in Dunnsmouth.", []),
    ("Our house is on Mill Lane.", []),
    ("Our son is Theo.", []),
    ("Our daughter is Wren.", []),
    ("Our car is a Beetle.", []),
    ("Our teacher is Ms Harlow.", []),
    ("Ours is the cottage by the lake.", []),
    ("We speak Frisian at home.", []),
    ("Our boss is Mr Kettle.", []),
    ("Our school is Greywater College.", []),
    ("our dog is Biscuit.", []),
    ("OUR cat is Pebbles.", []),
    # mixed x10: group clause + one other fact; gold holds the other fact only
    ("Our dog is Rex and I live in Oatfield.", [T("me", "city", "Oatfield")]),
    ("We live in Dunnsmouth but my sister is Wren.", [T("me", "sister", "Wren")]),
    ("My brother is Ash and our cat is Mimi.", [T("me", "brother", "Ash")]),
    ("Our car is a Beetle and I work at Hales Brokerage.",
     [T("me", "employer", "Hales Brokerage")]),
    ("I speak Frisian and our dog is Rex.", [T("me", "language", "Frisian")]),
    ("We live in Dunnsmouth and Nadia Fenn is my neighbour.",
     [T("Nadia Fenn", "neighbour", "me", ["neighbour", "neighbor"])]),
    ("Our son is Theo and my hobby is chess.", [T("me", "hobby", "chess")]),
    ("My mother is Iris and our cat is Mimi.", [T("me", "mother", "Iris")]),
    ("We speak Frisian at home and Tomas Reed is my boss.",
     [T("me", "boss", "Tomas Reed")]),
    ("Our school is Greywater College but I live in Oatfield.",
     [T("me", "city", "Oatfield")]),
    # first_person x10: must still save as "me"
    ("My dog is Rex.", [T("me", "pet", "Rex", ["pet", "dog"])]),
    ("I live in Oatfield.", [T("me", "city", "Oatfield")]),
    ("My sister is Wren.", [T("me", "sister", "Wren")]),
    ("I work at Hales Brokerage.", [T("me", "employer", "Hales Brokerage")]),
    ("My hobby is chess.", [T("me", "hobby", "chess")]),
    ("I speak Frisian.", [T("me", "language", "Frisian")]),
    ("My mother is Iris.", [T("me", "mother", "Iris")]),
    ("My friend is Briony Candlewick.", [T("me", "friend", "Briony Candlewick")]),
    ("I go to Greywater College.", [T("me", "school", "Greywater College")]),
    ("My boss is Tomas Reed.", [T("me", "boss", "Tomas Reed")]),
    # named x10: plain third-person controls
    ("Marta Vane lives in Dunnsmouth.", [T("Marta Vane", "city", "Dunnsmouth")]),
    ("Tomas Reed works at Hales Brokerage.",
     [T("Tomas Reed", "employer", "Hales Brokerage")]),
    ("Briony Candlewick speaks Frisian.",
     [T("Briony Candlewick", "language", "Frisian")]),
    ("Nadia Fenn goes to Greywater College.",
     [T("Nadia Fenn", "school", "Greywater College")]),
    ("Ash Keel is the brother of Wren.", [T("Ash Keel", "brother", "Wren")]),
    ("Iris Bell is the mother of Theo.", [T("Iris Bell", "mother", "Theo")]),
    ("Wren Hall has a dog called Biscuit.",
     [T("Wren Hall", "pet", "Biscuit", ["pet", "dog"])]),
    ("Pebbles is the cat of Mr Kettle.", [T("Mr Kettle", "pet", "Pebbles",
                                                 ["pet", "cat"])]),
    ("Dunnsmouth is home to Ms Harlow.", [T("Ms Harlow", "city", "Dunnsmouth")]),
    ("Oatfield is where Ivo Lantern lives.",
     [T("Ivo Lantern", "city", "Oatfield")]),
]

FAMS = (["group_owner"] * 14 + ["mixed"] * 10 + ["first_person"] * 10 + ["named"] * 10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    assert len(TURNS) == 44 and len(FAMS) == 44
    lines = []
    for i, ((turn, gold), fam) in enumerate(zip(TURNS, FAMS)):
        ask = fam in ("group_owner", "mixed")
        lines.append(dict(id=f"d265-{i + 1:03d}", family=fam, turn=turn,
                          gold=gold, clear=True,
                          notes=f"dev {fam} ask" if ask else f"dev {fam}",
                          ask_whose=ask))
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    print(f"wrote {len(lines)} dev turns")


if __name__ == "__main__":
    main()
