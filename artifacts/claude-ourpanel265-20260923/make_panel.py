"""Blind panel writer for exp 265 (ourpanel265).

Holds 80 items by hand, writes panel.jsonl deterministically, runs self-checks.
Run from the repo root with:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-ourpanel265-20260923/make_panel.py

Schema (per earpanel264 field/frame format + ask_whose):
  each line: {id, family, turn, gold, clear, notes, ask_whose}
  TEACH frame: {act, subject, relation, relation_aliases, value}
  ask_whose: true when the turn has a we/us/our/ours/ourselves owner or
  subject; gold then holds only facts NOT owned by the group (often []).
All names (people, towns, companies, pets, languages, cars) are fictional.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "panel.jsonl")

# One fixed alias list per relation. The pet list covers every species word
# used anywhere in this panel.
ALIASES = {
    "pet": ["dog", "cat", "rabbit", "parrot", "hamster", "pet", "animal",
            "companion"],
    "city": ["city", "town", "place", "location"],
    "workplace": ["workplace", "work", "office", "employer"],
    "job": ["job", "work", "occupation", "role"],
    "language": ["language", "tongue", "speech"],
    "car": ["car", "vehicle", "auto", "motor"],
    "school": ["school", "college", "academy"],
    "sister": ["sister", "sis"],
    "brother": ["brother", "bro"],
    "mother": ["mother", "mum", "mom", "ma"],
    "cousin": ["cousin", "cous"],
    "boss": ["boss", "manager", "supervisor"],
    "spouse": ["spouse", "husband", "wife", "partner"],
    "neighbour": ["neighbour", "neighbor", "next-door"],
    "hometown": ["hometown", "home town", "birthplace"],
    "place_of_birth": ["place_of_birth", "birthplace", "born"],
}

GROUP_RE = re.compile(r"\b(ourselves|ours|our|we|us)\b", re.IGNORECASE)
OURS_RE = re.compile(r"\b(ours|ourselves)\b", re.IGNORECASE)

# Names/places from READMEs the writer read; must not appear (whole word).
FORBIDDEN = ["tamsin", "brellin", "suki", "fernhill", "marta", "pella",
             "orla", "ana", "anya", "tarrow", "corin", "elspeth", "rin",
             "wren", "gil", "quarrow", "hollis", "ilse", "tomas", "tobin",
             "norrish", "ostrish", "galvish"]


def T(subject, relation, value):
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": list(ALIASES[relation]), "value": value}


# (family, turn, gold, clear, ask_whose, notes)
RAW = [
    # ---- group_owner x30: group-owned fact only -> gold [] ----
    ("group_owner", "Our dog Bix learned to open the garden gate.", [], True, True, "group-pet"),
    ("group_owner", "We adopted a rabbit called Wobble last spring.", [], True, True, "group-pet"),
    ("group_owner", "The vet adores our cat Plim and her spotted ears.", [], True, True, "group-pet"),
    ("group_owner", "our parrot kiki whistles every morning at sunrise", [], True, True, "group-pet lower"),
    ("group_owner", "That hamster Nib is ours; we bought him in Marlitt.", [], True, True, "group-pet ours"),
    ("group_owner", "Our home is a blue cottage above Dunmere harbour.", [], True, True, "group-home"),
    ("group_owner", "We moved to Kellhaven in the spring.", [], True, True, "group-city"),
    ("group_owner", "They built us a cabin near the Sornholm lighthouse.", [], True, True, "group-home us"),
    ("group_owner", "We live on a barge under the Vannholm bridge.", [], True, True, "group-home"),
    ("group_owner", "our flat is on the third floor in lissport", [], True, True, "group-city lower"),
    ("group_owner", "Our house in Drelton has a plum tree out back.", [], True, True, "group-home"),
    ("group_owner", "Our daughter Senna just started at the music school.", [], True, True, "group-relative"),
    ("group_owner", "We took our uncle Vanno sailing on Sunday.", [], True, True, "group-relative"),
    ("group_owner", "Our cousin Issa sends us jam every winter.", [], True, True, "group-relative"),
    ("group_owner", "Our grandad tells the best stories about the old boatyard.", [], True, True, "group-relative"),
    ("group_owner", "Ours is the loudest family on the whole street in Fasswick.", [], False, True, "group-relative ours opinion"),
    ("group_owner", "We both shelve books at Kestrel Press after lunch.", [], True, True, "group-work"),
    ("group_owner", "Our studio Copperline doubled its orders this year.", [], True, True, "group-work"),
    ("group_owner", "We run the night shift at Saltline Boatyard together.", [], True, True, "group-work"),
    ("group_owner", "Our bakery Bluefin opens early on market days.", [], True, True, "group-work"),
    ("group_owner", "Our Dravvo finally passed its inspection today.", [], True, True, "group-car"),
    ("group_owner", "We bought ourselves a secondhand Kellrun van.", [], True, True, "group-car ourselves"),
    ("group_owner", "That red Mosspin is ours, ask at the gate.", [], True, True, "group-car ours"),
    ("group_owner", "We park our Kellrun behind the bakery.", [], True, True, "group-car"),
    ("group_owner", "We speak Drellish at home with the children.", [], True, True, "group-language"),
    ("group_owner", "Our whole street is learning Sornic together.", [], True, True, "group-language"),
    ("group_owner", "we raised our kids speaking tannish and drellish", [], True, True, "group-language lower"),
    ("group_owner", "Kessic is what us kids were raised on.", [], True, True, "group-language us"),
    ("group_owner", "Ourselves, we painted the whole kitchen yellow.", [], False, True, "group ourselves no-fact"),
    ("group_owner", "Our parrot Kiki and our dog Bix share one basket.", [], True, True, "group-pet"),
    # ---- mixed x15: group clause + other fact; gold holds the other fact ----
    ("mixed", "Our dog Bix chews everything, and I manage the evening shift at Loom & Lark.", [T("me", "workplace", "Loom & Lark")], True, True, "mixed-first-person"),
    ("mixed", "We rent in Kellhaven, and I work at Vennworks.", [T("me", "workplace", "Vennworks")], True, True, "mixed-first-person"),
    ("mixed", "Our cat Plim is fifteen, and my job is night baker.", [T("me", "job", "night baker")], True, True, "mixed-first-person"),
    ("mixed", "We speak Drellish at home, and I also speak Marlovic.", [T("me", "language", "Marlovic")], True, True, "mixed-first-person"),
    ("mixed", "Our Dravvo is in the shop, and I drive a Kellrun for work.", [T("me", "car", "Kellrun")], True, True, "mixed-first-person"),
    ("mixed", "We share one umbrella, and my school is Drellwick Hall.", [T("me", "school", "Drellwick Hall")], True, True, "mixed-first-person"),
    ("mixed", "Our street lost power, and I was born in Villarca.", [T("me", "place_of_birth", "Villarca")], True, True, "mixed-first-person"),
    ("mixed", "We queue for hours, and my boss is Issa.", [T("me", "boss", "Issa")], True, True, "mixed-first-person"),
    ("mixed", "Our roof leaks again, and Bram lives in Mosswick.", [T("Bram", "city", "Mosswick")], True, True, "mixed-named"),
    ("mixed", "We repainted the gate, and Cleo teaches at Drellwick Hall.", [T("Cleo", "workplace", "Drellwick Hall")], True, True, "mixed-named"),
    ("mixed", "Our hamster Nib sleeps all day, and Dax drives a Mosspin.", [T("Dax", "car", "Mosspin")], True, True, "mixed-named"),
    ("mixed", "We ran out of paint, and Evra speaks Sornic.", [T("Evra", "language", "Sornic")], True, True, "mixed-named"),
    ("mixed", "Our landlord visits on Fridays, and Nils married Yara.", [T("Nils", "spouse", "Yara")], True, True, "mixed-named"),
    ("mixed", "We missed the ferry, and Willa studies at Kestrel College.", [T("Willa", "school", "Kestrel College")], True, True, "mixed-named"),
    ("mixed", "Our plum tree bloomed early, and Ossa's sister is Liora.", [T("Ossa", "sister", "Liora")], True, True, "mixed-named"),
    # ---- first_person x20: subject "me", no group owner ----
    ("first_person", "I live in an attic above the bakery in Marlitt.", [T("me", "city", "Marlitt")], True, False, "first-person"),
    ("first_person", "My car is a rusty Kellrun hatchback.", [T("me", "car", "Kellrun")], True, False, "first-person"),
    ("first_person", "I work the early shift at Bluefin Bakery.", [T("me", "workplace", "Bluefin Bakery")], True, False, "first-person"),
    ("first_person", "My sister is Miri.", [T("me", "sister", "Miri")], True, False, "first-person"),
    ("first_person", "I speak Kessic with my grandmother.", [T("me", "language", "Kessic")], True, False, "first-person"),
    ("first_person", "My dog is called Bix.", [T("me", "pet", "Bix")], True, False, "first-person"),
    ("first_person", "I teach maths at Drellwick Hall.", [T("me", "workplace", "Drellwick Hall")], True, False, "first-person"),
    ("first_person", "My hometown is the fishing port of Villarca.", [T("me", "hometown", "Villarca")], True, False, "first-person"),
    ("first_person", "I married Yara last summer in a barn.", [T("me", "spouse", "Yara")], True, False, "first-person"),
    ("first_person", "My boss at Vennworks is called Rurik.", [T("me", "boss", "Rurik")], True, False, "first-person"),
    ("first_person", "i drive a mosspin and i love the night roads", [T("me", "car", "mosspin")], True, False, "first-person lower"),
    ("first_person", "My mother is Cleo and she keeps the lighthouse cottage.", [T("me", "mother", "Cleo")], True, False, "first-person"),
    ("first_person", "I study Sornic every evening after supper.", [T("me", "language", "Sornic")], True, False, "first-person"),
    ("first_person", "My neighbour Nils lends me his ladder.", [T("me", "neighbour", "Nils")], True, False, "first-person"),
    ("first_person", "I was born in the back room of a Lissport inn.", [T("me", "place_of_birth", "Lissport")], True, False, "first-person"),
    ("first_person", "my brother dax mends nets down at the harbour", [T("me", "brother", "dax")], True, False, "first-person lower"),
    ("first_person", "I am a net-mender at the harbour.", [T("me", "job", "net-mender")], True, False, "first-person"),
    ("first_person", "My cat Plim answers to her name.", [T("me", "pet", "Plim")], True, False, "first-person"),
    ("first_person", "I live with my cousin Tilda near the mill.", [T("me", "cousin", "Tilda")], True, False, "first-person"),
    ("first_person", "My first language is Marlovic.", [T("me", "language", "Marlovic")], True, False, "first-person"),
    # ---- named x15: plain third-person facts, controls ----
    ("named", "Bram lives above the chandlery in Dunmere.", [T("Bram", "city", "Dunmere")], True, False, "named"),
    ("named", "Cleo runs the early shift at Bluefin Bakery.", [T("Cleo", "workplace", "Bluefin Bakery")], True, False, "named"),
    ("named", "Dax drives a battered Mosspin van.", [T("Dax", "car", "Mosspin")], True, False, "named"),
    ("named", "Evra speaks Sornic at the market.", [T("Evra", "language", "Sornic")], True, False, "named"),
    ("named", "Nils married Yara in a barn last summer.", [T("Nils", "spouse", "Yara")], True, False, "named"),
    ("named", "Willa studies stars at Kestrel College.", [T("Willa", "school", "Kestrel College")], True, False, "named"),
    ("named", "Ossa keeps a parrot called Kiki.", [T("Ossa", "pet", "Kiki")], True, False, "named"),
    ("named", "Liora manages the night desk at Vennworks.", [T("Liora", "workplace", "Vennworks")], True, False, "named"),
    ("named", "Rurik is a net-mender at the harbour.", [T("Rurik", "job", "net-mender")], True, False, "named"),
    ("named", "Senna was born in a cottage outside Fasswick.", [T("Senna", "place_of_birth", "Fasswick")], True, False, "named"),
    ("named", "Vanno coaches rowing at the Saltline club.", [T("Vanno", "workplace", "Saltline club")], True, False, "named"),
    ("named", "Issa bakes the rye loaves at Bluefin Bakery.", [T("Issa", "workplace", "Bluefin Bakery")], True, False, "named"),
    ("named", "koda keeps a rabbit called wobble", [T("koda", "pet", "wobble")], True, False, "named lower"),
    ("named", "Tilda teaches reading at Drellwick Hall.", [T("Tilda", "workplace", "Drellwick Hall")], True, False, "named"),
    ("named", "Jalen speaks Marlovic at the night market.", [T("Jalen", "language", "Marlovic")], True, False, "named"),
]

EXPECT = {"group_owner": 30, "mixed": 15, "first_person": 20, "named": 15}
ITEM_KEYS = {"id", "family", "turn", "gold", "clear", "notes", "ask_whose"}
FRAME_KEYS = {"act", "subject", "relation", "relation_aliases", "value"}


def build():
    items = []
    for i, (family, turn, gold, clear, ask_whose, notes) in enumerate(RAW, 1):
        items.append({"id": "o265-%03d" % i, "family": family, "turn": turn,
                      "gold": gold, "clear": clear, "notes": notes,
                      "ask_whose": ask_whose})
    return items


def check(items):
    assert len(items) == 80, len(items)
    counts = {}
    for it in items:
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    assert counts == EXPECT, counts
    # ids sequential in family-block order
    fams = [it["family"] for it in items]
    assert fams == (["group_owner"] * 30 + ["mixed"] * 15
                    + ["first_person"] * 20 + ["named"] * 15), "block order"
    assert [it["id"] for it in items] == ["o265-%03d" % i for i in range(1, 81)]
    # no duplicate turn
    turns = [it["turn"] for it in items]
    assert len(set(turns)) == 80, "duplicate turn"
    assert len(set(t.strip().lower() for t in turns)) == 80, "near-duplicate"
    seen_alias = {}
    n_ask = 0
    n_lower = 0
    n_ours = 0
    for it in items:
        assert set(it.keys()) == ITEM_KEYS, it["id"]
        assert isinstance(it["turn"], str) and it["turn"], it["id"]
        assert isinstance(it["clear"], bool), it["id"]
        assert isinstance(it["ask_whose"], bool), it["id"]
        assert isinstance(it["notes"], str) and it["notes"], it["id"]
        assert isinstance(it["gold"], list), it["id"]
        has_group = bool(GROUP_RE.search(it["turn"]))
        assert it["ask_whose"] == has_group, it["id"]
        if it["ask_whose"]:
            n_ask += 1
        if it["turn"] == it["turn"].lower() and re.search(r"[a-z]", it["turn"]):
            n_lower += 1
        if OURS_RE.search(it["turn"]):
            n_ours += 1
        if it["family"] == "group_owner":
            assert it["gold"] == [], it["id"]
        if it["family"] == "mixed":
            assert len(it["gold"]) >= 1, it["id"]
        if it["family"] in ("first_person", "named"):
            assert len(it["gold"]) >= 1, it["id"]
            assert not has_group, it["id"]
        for fr in it["gold"]:
            assert set(fr.keys()) == FRAME_KEYS, it["id"]
            assert fr["act"] == "TEACH", it["id"]
            assert fr["relation"] in ALIASES, it["id"]
            assert fr["relation_aliases"] == ALIASES[fr["relation"]], it["id"]
            if fr["relation"] in seen_alias:
                assert seen_alias[fr["relation"]] == fr["relation_aliases"]
            seen_alias[fr["relation"]] = fr["relation_aliases"]
            if fr["subject"] != "me":
                assert fr["subject"] in it["turn"], (it["id"], "subject")
            assert fr["value"] in it["turn"], (it["id"], "value")
            if fr["relation"] == "pet":
                species = [s for s in ("dog", "cat", "rabbit", "parrot",
                                       "hamster")
                           if s in it["turn"].lower()]
                assert species, (it["id"], "pet species in turn")
                for s in species:
                    assert s in fr["relation_aliases"], (it["id"], s)
        words = set(re.findall(r"[A-Za-z]+", it["turn"].lower()))
        for bad in FORBIDDEN:
            assert bad not in words, (it["id"], bad)
    assert n_ask == 45, n_ask  # 30 group_owner + 15 mixed
    assert n_lower >= 4, n_lower
    assert n_ours >= 3, n_ours
    return counts, n_ask, n_lower, n_ours


def main():
    items = build()
    counts, n_ask, n_lower, n_ours = check(items)
    with open(OUT, "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False, sort_keys=True) + "\n")
    print("counts:", counts)
    print("ask_whose=true:", n_ask, "lowercase:", n_lower, "ours-forms:", n_ours)
    print("wrote", OUT, "lines:", len(items))


if __name__ == "__main__":
    main()
