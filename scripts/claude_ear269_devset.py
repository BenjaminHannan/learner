#!/usr/bin/env python3
"""Exp 269 -- dev set (builder wording, fictional names; never any panel).

Dev = 265's 44 turns verbatim (imported read-only from claude_ear265_devset)
plus 72 new 269 turns in 269 wording:
- group_new 28: group-owner wordings with the owner word mid-sentence,
  "at ours", "us three share ...", relative clauses, case variants.
  gold [], ask_whose true.
- mixed_new 12: mid-sentence group clause + a first-person or named fact.
  gold = the other fact, ask_whose true.
- nonowner 32: we/us/our where nobody owns anything by it (social/motion
  verbs, cognition verbs with named complements, our + event nouns,
  us as speech-verb object, quoted speech, prepositional us).
  gold = the other facts or [], ask_whose false.

Line format is exactly 265's: {id, family, turn, gold, clear, notes,
ask_whose}; families are 265's four plus "non_owner_we".

python claude_ear269_devset.py --out artifacts/claude-ear269-20260923/dev_269.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ear265_devset as D265  # noqa: E402  (read-only import, never edited)


def T(subject, relation, value, aliases=None):
    return dict(act="TEACH", subject=subject, relation=relation,
                relation_aliases=aliases or [relation], value=value)


# (turn, gold) new group_owner turns; gold [] ; ask_whose true
GROUP_NEW = [
    "The boat we bought is called Wren.",
    "Dinner is at ours on Friday.",
    "The cottage by the lake is ours.",
    "Us three share a car called Pip.",
    "The dog we adopted is called Bramble.",
    "We own a boat called Wren.",
    "The language we speak at home is Frisian.",
    "We share a flat on Harbor Street.",
    "The flat we share is on Harbor Street.",
    "The puppy we got in spring is called Biscuit.",
    "We adopted a parrot called Pip.",
    "The parrot we adopted says hello all day.",
    "Our van is called Vesper.",
    "The van we drive is called Vesper.",
    "The kitten we found is called Mimi.",
    "The college we attend is Greywater.",
    "We work at Hales Brokerage.",
    "The bakery we work at is Crumb and Rye.",
    "We keep a vegetable garden behind the house.",
    "The house we rent has a red door.",
    "Our landlord is Mr Fenwick.",
    "The landlord we have is Mr Fenwick.",
    "We raised a foal called Fern.",
    "The foal we raised is called Fern.",
    "the boat we bought is called wren.",
    "DINNER IS AT OURS ON FRIDAY.",
    "Ours is the blue door on Mill Lane.",
    "The school our cousins attend is Greywater.",
    "The canoe we carved is called Otter.",
    "Our twins are called Ash and Fern.",
    "Us two own a plot by the river.",
    "Our surname is Vane.",
]

# (turn, gold) new mixed turns; gold = the other fact; ask_whose true
MIXED_NEW = [
    ("The boat we bought is called Wren and I live in Oatfield.",
     [T("me", "city", "Oatfield")]),
    ("Dinner is at ours but my brother is Ash.",
     [T("me", "brother", "Ash")]),
    ("Us three share a car called Pip and Nadia Fenn is my neighbour.",
     [T("Nadia Fenn", "neighbour", "me", ["neighbour", "neighbor"])]),
    ("The dog we adopted is called Bramble and I work at Hales Brokerage.",
     [T("me", "employer", "Hales Brokerage")]),
    ("We own a boat called Wren but Tomas Reed is my boss.",
     [T("me", "boss", "Tomas Reed")]),
    ("The college we attend is Greywater and my hobby is chess.",
     [T("me", "hobby", "chess")]),
    ("Ours is the blue door on Mill Lane and I speak Frisian.",
     [T("me", "language", "Frisian")]),
    ("We share a flat on Harbor Street but Iris Bell is my mother.",
     [T("me", "mother", "Iris")]),
    ("The parrot we adopted is called Pip and my sister is Wren.",
     [T("me", "sister", "Wren")]),
    ("Our van is called Vesper and Briony Candlewick is my friend.",
     [T("me", "friend", "Briony Candlewick")]),
    ("My mother is Iris and dinner is at ours.",
     [T("me", "mother", "Iris")]),
    ("We live in Dunnsmouth and my daughter is Wren.",
     [T("me", "daughter", "Wren")]),
]

# (turn, gold) non-owner we/us/our turns; gold = other facts or []; ask false
NONOWNER = [
    # we + social/motion verbs, no ownership
    ("We met at the cafe on Mill Lane.", []),
    ("We walked to the lake yesterday.", []),
    ("We ate dinner at Harbor House.", []),
    ("We saw a heron by the river.", []),
    ("We talked until midnight.", []),
    ("We went to the market this morning.", []),
    ("We danced in the kitchen.", []),
    ("We waited an hour for the ferry.", []),
    # we + cognition/speech verbs with named complements
    ("We think Ana Bell lives in Dunnsmouth.",
     [T("Ana Bell", "city", "Dunnsmouth")]),
    ("We believe Mara Vane speaks Frisian.",
     [T("Mara Vane", "language", "Frisian")]),
    ("We heard Tomas Reed works at Hales Brokerage.",
     [T("Tomas Reed", "employer", "Hales Brokerage")]),
    ("We guess Iris Bell teaches at Greywater College.",
     [T("Iris Bell", "workplace", "Greywater College")]),
    ("We know Briony Candlewick goes to Greywater College.",
     [T("Briony Candlewick", "school", "Greywater College")]),
    ("We feel Nadia Fenn will win the race.", []),
    # our + event nouns
    ("Our meeting is at 3.", []),
    ("Our appointment ran late.", []),
    ("Our party starts at eight.", []),
    ("Our trip to the coast was lovely.", []),
    ("Our team won the match.", []),
    ("Our flight leaves at dawn.", []),
    ("Our street shines after rain.", []),
    ("We pay our bills on Friday.", []),
    # us as object of speech/transfer verbs, ownership stays third-person
    ("Ana Bell told us Fig is her cat.",
     [T("Ana Bell", "pet", "Fig", ["pet", "cat"])]),
    ("Mara Vane sent us a photo of Bramble.", []),
    ("Tomas Reed asked us to wait outside.", []),
    ("Iris Bell showed us the school garden.", []),
    ("Mara Vane saved us two seats.", []),
    # quoted speech with our inside
    ("Mara Vane said our trip was wonderful.", []),
    ('Tomas Reed told me, "Our team played well."', []),
    ('Mara Vane said, "Our dog is Rex."', []),
    ("Between us, Mara Vane lives in Dunnsmouth.",
     [T("Mara Vane", "city", "Dunnsmouth")]),
    # prepositional / idiom us
    ("Come with us to the lake.", []),
    ("This song reminds us of Dunnsmouth.", []),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lines = []
    # 265's 44 turns first (same turns/gold/families, re-id'd d269-001..044,
    # notes record the provenance).
    assert len(D265.TURNS) == 44 and len(D265.FAMS) == 44
    for (turn, gold), fam in zip(D265.TURNS, D265.FAMS):
        ask = fam in ("group_owner", "mixed")
        lines.append(dict(id=f"d269-{len(lines) + 1:03d}", family=fam,
                          turn=turn, gold=gold, clear=True,
                          notes=f"269dev ex265 {fam}",
                          ask_whose=ask))
    for turn in GROUP_NEW:
        lines.append(dict(id=f"d269-{len(lines) + 1:03d}",
                          family="group_owner", turn=turn, gold=[],
                          clear=True, notes="269dev group_new ask",
                          ask_whose=True))
    for turn, gold in MIXED_NEW:
        lines.append(dict(id=f"d269-{len(lines) + 1:03d}", family="mixed",
                          turn=turn, gold=gold, clear=True,
                          notes="269dev mixed_new ask", ask_whose=True))
    for turn, gold in NONOWNER:
        lines.append(dict(id=f"d269-{len(lines) + 1:03d}",
                          family="non_owner_we", turn=turn, gold=gold,
                          clear=True, notes="269dev nonowner noask",
                          ask_whose=False))
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    n_new_group = len(GROUP_NEW) + len(MIXED_NEW)
    print(f"wrote {len(lines)} dev turns "
          f"(44 ex265 + {len(GROUP_NEW)} group_new + {len(MIXED_NEW)} "
          f"mixed_new + {len(NONOWNER)} nonowner); "
          f"new group-worded owner turns: {n_new_group}")


if __name__ == "__main__":
    main()
