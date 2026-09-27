#!/usr/bin/env python3
"""Ear panel 261 writer (blind, exp 261).

Holds all 150 items by hand, writes panel.jsonl deterministically,
and runs self-checks (family counts, duplicate turns, verbatim
subject/value presence, R1-R12 quotas, lowercase/typo/no-"?" counts,
schema exactness including chain_aliases, forbidden-name screen).

Run from the repo root:
    /usr/bin/python3 -B artifacts/claude-earpanel261-20260922/make_panel.py

All person/place names are fictional and invented for this panel.
"""

import json
import re
import sys
from pathlib import Path

OUT_DIR = Path("artifacts/claude-earpanel261-20260922")
PANEL_PATH = OUT_DIR / "panel.jsonl"

# One fixed alias list per relation. The same relation always carries
# the same aliases in every frame.
ALIASES = {
    "city": ["city", "town", "lives in"],
    "employer": ["employer", "company", "works for"],
    "workplace": ["workplace", "works at", "work"],
    "job": ["job", "occupation", "profession"],
    "boss": ["boss", "manager", "supervisor"],
    "sister": ["sister", "sis"],
    "brother": ["brother", "bro"],
    "spouse": ["spouse", "husband", "wife"],
    "language": ["language", "speaks", "tongue"],
    "hometown": ["hometown", "grew up in", "home town"],
    "place_of_birth": ["place_of_birth", "birthplace", "born in"],
    "pet": ["pet", "animal", "companion"],
    "school": ["school", "studies at", "college"],
    "neighbour": ["neighbour", "neighbor", "next door"],
    "cousin": ["cousin", "relative"],
    "friend": ["friend", "buddy", "pal"],
    "mother": ["mother", "mom", "mum"],
    "father": ["father", "dad", "papa"],
    "aunt": ["aunt", "auntie"],
    "uncle": ["uncle", "unk"],
    "grandmother": ["grandmother", "grandma", "granny"],
    "stepmother": ["stepmother", "stepmom", "stepmum"],
    "half_brother": ["half_brother", "half-brother", "half brother"],
    "father_in_law": ["father_in_law", "father-in-law"],
    "sister_in_law": ["sister_in_law", "sister-in-law"],
    "housemate": ["housemate", "roommate", "flatmate"],
    "instrument": ["instrument", "plays", "instrument played"],
    "favourite_food": ["favourite_food", "favorite_food", "loves to eat"],
    "favourite_sport": ["favourite_sport", "favorite_sport", "sport"],
    "hobby": ["hobby", "pastime", "interest"],
    "teacher": ["teacher", "tutor", "mentor"],
    "doctor": ["doctor", "physician", "GP"],
}


def T(subject, relation, value):
    """TEACH frame with the fixed alias list for relation."""
    return {
        "act": "TEACH",
        "subject": subject,
        "relation": relation,
        "relation_aliases": list(ALIASES[relation]),
        "value": value,
    }


def A(subject, relation, chain):
    """ASK frame. chain is None for one hop, else [first, second]."""
    if chain is None:
        return {
            "act": "ASK",
            "subject": subject,
            "relation": relation,
            "chain": None,
            "relation_aliases": list(ALIASES[relation]),
            "chain_aliases": None,
        }
    assert len(chain) == 2 and chain[1] == relation
    return {
        "act": "ASK",
        "subject": subject,
        "relation": relation,
        "chain": list(chain),
        "relation_aliases": list(ALIASES[relation]),
        "chain_aliases": [list(ALIASES[chain[0]]), list(ALIASES[chain[1]])],
    }


# Each entry: (family, turn, gold frames, clear, notes).
# notes holds comma-separated risk tags: R1..R12, lower, typo, noq,
# plus "correction" for the corrections family.
ITEMS = [
    # ---- plain_teach (25) ----
    ("plain_teach", "I live in Vellmar.", [T("me", "city", "Vellmar")], True, ""),
    ("plain_teach", "My sister is Liora.", [T("me", "sister", "Liora")], True, ""),
    ("plain_teach", "Darian works at Copperline Traders.", [T("Darian", "workplace", "Copperline Traders")], True, ""),
    ("plain_teach", "My dog is called Bracken.", [T("me", "pet", "Bracken")], True, ""),
    ("plain_teach", "I speak Kessic at home.", [T("me", "language", "Kessic")], True, ""),
    ("plain_teach", "Liora teaches at Aldergate School.", [T("Liora", "workplace", "Aldergate School")], True, "R3"),
    ("plain_teach", "Darian coaches at Stonefield Club.", [T("Darian", "workplace", "Stonefield Club")], True, "R3"),
    ("plain_teach", "My stepmother is Cressa.", [T("me", "stepmother", "Cressa")], True, "R4"),
    ("plain_teach", "My housemate is Jovian.", [T("me", "housemate", "Jovian")], True, "R5"),
    ("plain_teach", "I play the fiddle every evening.", [T("me", "instrument", "fiddle")], True, "R5"),
    ("plain_teach", "Our neighbour is Ondrej.", [T("me", "neighbour", "Ondrej")], True, "R7"),
    ("plain_teach", "We live with our cat Taffy.", [T("me", "pet", "Taffy")], True, "R7"),
    ("plain_teach", "My cousin Cressa lives in Caldora.", [T("me", "cousin", "Cressa"), T("Cressa", "city", "Caldora")], True, "R11"),
    ("plain_teach", "My friend Bram works at Harbormill Books.", [T("me", "friend", "Bram"), T("Bram", "workplace", "Harbormill Books")], True, "R11"),
    ("plain_teach", "Jovian's brother is Tovik and he lives in Drennick.", [T("Jovian", "brother", "Tovik"), T("Tovik", "city", "Drennick")], True, "R12"),
    ("plain_teach", "My two sisters, Liora and Jessa, live in Vellmar.", [T("me", "sister", "Liora"), T("me", "sister", "Jessa"), T("Liora", "city", "Vellmar"), T("Jessa", "city", "Vellmar")], True, "R10"),
    ("plain_teach", "I was born in Hasselby.", [T("me", "place_of_birth", "Hasselby")], True, ""),
    ("plain_teach", "My boss is Mellis.", [T("me", "boss", "Mellis")], True, ""),
    ("plain_teach", "I work as a lighthouse keeper.", [T("me", "job", "lighthouse keeper")], True, ""),
    ("plain_teach", "My spouse is Ondrej.", [T("me", "spouse", "Ondrej")], True, ""),
    ("plain_teach", "i just moved to mossbank.", [T("me", "city", "mossbank")], True, "lower"),
    ("plain_teach", "Liora livs in Lornwick.", [T("Liora", "city", "Lornwick")], True, "typo"),
    ("plain_teach", "My grandmother is Sarella.", [T("me", "grandmother", "Sarella")], True, "R4"),
    ("plain_teach", "Darian speaks Drellish.", [T("Darian", "language", "Drellish")], True, ""),
    ("plain_teach", "My hometown is Oakhollow.", [T("me", "hometown", "Oakhollow")], True, ""),
    # ---- varied_teach (30) ----
    ("varied_teach", "Liora is my sister and she lives in Vellmar.", [T("me", "sister", "Liora"), T("Liora", "city", "Vellmar")], True, "R1"),
    ("varied_teach", "My brother is Darian and he works at Copperline Traders.", [T("me", "brother", "Darian"), T("Darian", "workplace", "Copperline Traders")], True, "R1"),
    ("varied_teach", "Cressa is my cousin and she speaks Kessic.", [T("me", "cousin", "Cressa"), T("Cressa", "language", "Kessic")], True, "R1"),
    ("varied_teach", "Tovik is my friend and he lives in Caldora.", [T("me", "friend", "Tovik"), T("Tovik", "city", "Caldora")], True, "R1"),
    ("varied_teach", "Our doctor is Fenno Grey and he works at Stonebridge Clinic.", [T("me", "doctor", "Fenno Grey"), T("Fenno Grey", "workplace", "Stonebridge Clinic")], True, "R1,R5,R7"),
    ("varied_teach", "Mellis is my boss and she lives in Drennick.", [T("me", "boss", "Mellis"), T("Mellis", "city", "Drennick")], True, "R1"),
    ("varied_teach", "Everyone keeps asking where Darian works, and he works at Copperline Traders.", [T("Darian", "workplace", "Copperline Traders")], True, "R2"),
    ("varied_teach", "People wonder why Liora moved, but she lives in Hasselby now.", [T("Liora", "city", "Hasselby")], True, "R2"),
    ("varied_teach", "Nobody knows how Cressa learned it, but she speaks Vornic fluently.", [T("Cressa", "language", "Vornic")], True, "R2"),
    ("varied_teach", "Jovian teaches at Brookmere College.", [T("Jovian", "workplace", "Brookmere College")], True, "R3"),
    ("varied_teach", "Sarella studies at Aldergate School.", [T("Sarella", "school", "Aldergate School")], True, "R3"),
    ("varied_teach", "Bram is studying at Brookmere College.", [T("Bram", "school", "Brookmere College")], True, "R3"),
    ("varied_teach", "My half-brother is Kessler and he lives in Lornwick.", [T("me", "half_brother", "Kessler"), T("Kessler", "city", "Lornwick")], True, "R1,R4"),
    ("varied_teach", "Petra's father-in-law is Haldor and he lives in Yewdale.", [T("Petra", "father_in_law", "Haldor"), T("Haldor", "city", "Yewdale")], True, "R4,R12"),
    ("varied_teach", "My teacher is Odette Lark.", [T("me", "teacher", "Odette Lark")], True, "R5"),
    ("varied_teach", "My favourite food is plum pie.", [T("me", "favourite_food", "plum pie")], True, "R5"),
    ("varied_teach", "Sarella's hobby is beekeeping.", [T("Sarella", "hobby", "beekeeping")], True, "R5"),
    ("varied_teach", "Our cat Soot sleeps on my desk all day.", [T("me", "pet", "Soot")], True, "R7"),
    ("varied_teach", "We share our house with my brother Donal.", [T("me", "brother", "Donal")], True, "R7"),
    ("varied_teach", "Darian is training to be a pilot, but he lives in Vellmar.", [T("Darian", "city", "Vellmar")], True, "R8"),
    ("varied_teach", "Liora wants to be a doctor, though she works at Bluefen Bakery.", [T("Liora", "workplace", "Bluefen Bakery")], True, "R8"),
    ("varied_teach", "Cressa plans to move to Zarnow, while she lives in Merrivale.", [T("Cressa", "city", "Merrivale")], True, "R8"),
    ("varied_teach", "Both my cousins, Bram and Cadel, work at Stonegate Press.", [T("me", "cousin", "Bram"), T("me", "cousin", "Cadel"), T("Bram", "workplace", "Stonegate Press"), T("Cadel", "workplace", "Stonegate Press")], True, "R10"),
    ("varied_teach", "My two brothers, Ivo and Ludo, speak Drellish.", [T("me", "brother", "Ivo"), T("me", "brother", "Ludo"), T("Ivo", "language", "Drellish"), T("Ludo", "language", "Drellish")], True, "R10"),
    ("varied_teach", "Sarella's friend Vanna works at Foxglove Studio.", [T("Sarella", "friend", "Vanna"), T("Vanna", "workplace", "Foxglove Studio")], True, "R11"),
    ("varied_teach", "My uncle Garrick lives in Thistledown with his dog Pip.", [T("me", "uncle", "Garrick"), T("Garrick", "city", "Thistledown"), T("Garrick", "pet", "Pip")], True, "R11"),
    ("varied_teach", "Vespera's sister is Xenia and she speaks Drellish.", [T("Vespera", "sister", "Xenia"), T("Xenia", "language", "Drellish")], True, "R12"),
    ("varied_teach", "Osric's friend is Petra and she works at Stonegate Press.", [T("Osric", "friend", "Petra"), T("Petra", "workplace", "Stonegate Press")], True, "R12"),
    ("varied_teach", "my brother donal lives in rillwater.", [T("me", "brother", "donal"), T("donal", "city", "rillwater")], True, "lower"),
    ("varied_teach", "My mother was bron in Sableton.", [T("me", "place_of_birth", "Sableton")], True, "typo"),
    # ---- full_names (15) ----
    ("full_names", "Liora Venn is my sister and she lives in Kestrel Bay.", [T("me", "sister", "Liora Venn"), T("Liora Venn", "city", "Kestrel Bay")], True, "R1"),
    ("full_names", "Darian Kess is my brother and he works at Copperline Traders.", [T("me", "brother", "Darian Kess"), T("Darian Kess", "workplace", "Copperline Traders")], True, "R1"),
    ("full_names", "Cressa Marlowe speaks Vornic and she teaches at Aldergate School.", [T("Cressa Marlowe", "language", "Vornic"), T("Cressa Marlowe", "workplace", "Aldergate School")], True, "R1,R3"),
    ("full_names", "Tovik Ash is our neighbour and he lives in Duskhaven.", [T("me", "neighbour", "Tovik Ash"), T("Tovik Ash", "city", "Duskhaven")], True, "R1,R7"),
    ("full_names", "Mellis Thorn works at Harbormill Books.", [T("Mellis Thorn", "workplace", "Harbormill Books")], True, ""),
    ("full_names", "My grandmother Sarella Voss lives in Emberford.", [T("me", "grandmother", "Sarella Voss"), T("Sarella Voss", "city", "Emberford")], True, "R4,R11"),
    ("full_names", "Darian Kess Merrivale plays the concertina.", [T("Darian Kess Merrivale", "instrument", "concertina")], True, "R5"),
    ("full_names", "My two aunts, Odelia Fern and Sibyl Hart, live in Frostwick.", [T("me", "aunt", "Odelia Fern"), T("me", "aunt", "Sibyl Hart"), T("Odelia Fern", "city", "Frostwick"), T("Sibyl Hart", "city", "Frostwick")], True, "R10"),
    ("full_names", "Bram Calloway Finn is my cousin and he lives in Wildemere.", [T("me", "cousin", "Bram Calloway Finn"), T("Bram Calloway Finn", "city", "Wildemere")], True, "R1,R11"),
    ("full_names", "Petra Lindqvist's brother is Bram Calloway and he works at Foxglove Studio.", [T("Petra Lindqvist", "brother", "Bram Calloway"), T("Bram Calloway", "workplace", "Foxglove Studio")], True, "R12"),
    ("full_names", "I was born in Kestrel Bay General Hospital.", [T("me", "place_of_birth", "Kestrel Bay General Hospital")], True, ""),
    ("full_names", "My teacher is Odette Lark Quinn.", [T("me", "teacher", "Odette Lark Quinn")], True, ""),
    ("full_names", "Roslin Abernathy speaks Drellish fluently.", [T("Roslin Abernathy", "language", "Drellish")], True, ""),
    ("full_names", "my boss is mellis thorn.", [T("me", "boss", "mellis thorn")], True, "lower"),
    ("full_names", "Sarella Voss Ash is my granmother and she lives in Emberford.", [T("me", "grandmother", "Sarella Voss Ash"), T("Sarella Voss Ash", "city", "Emberford")], True, "R1,typo"),
    # ---- questions (25) ----
    ("questions", "Where does Liora live?", [A("Liora", "city", None)], True, ""),
    ("questions", "What language does Darian speak?", [A("Darian", "language", None)], True, ""),
    ("questions", "Who is Cressa's boss?", [A("Cressa", "boss", None)], True, ""),
    ("questions", "Where was Jovian born?", [A("Jovian", "place_of_birth", None)], True, ""),
    ("questions", "What does Mellis do for work?", [A("Mellis", "job", None)], False, ""),
    ("questions", "Who is married to Ondrej?", [A("Ondrej", "spouse", None)], True, ""),
    ("questions", "What school does Sarella attend?", [A("Sarella", "school", None)], True, ""),
    ("questions", "Who is Tovik's sister?", [A("Tovik", "sister", None)], True, ""),
    ("questions", "Where does our neighbour Ondrej live?", [A("Ondrej", "city", None)], True, ""),
    ("questions", "Who is Darian's half-brother?", [A("Darian", "half_brother", None)], True, "R4"),
    ("questions", "What instrument does Bram play?", [A("Bram", "instrument", None)], True, "R5"),
    ("questions", "Who is Liora's doctor?", [A("Liora", "doctor", None)], True, "R5"),
    ("questions", "Does Darian have a brother?", [A("Darian", "brother", None)], False, ""),
    ("questions", "What is Cressa's favourite food?", [A("Cressa", "favourite_food", None)], True, ""),
    ("questions", "Where did Sarella grow up?", [A("Sarella", "hometown", None)], True, ""),
    ("questions", "Who does Vespera work for?", [A("Vespera", "employer", None)], True, ""),
    ("questions", "What pet does Jovian have?", [A("Jovian", "pet", None)], True, ""),
    ("questions", "where does liora live", [A("liora", "city", None)], True, "lower,noq"),
    ("questions", "what language does darian speak?", [A("darian", "language", None)], True, "lower"),
    ("questions", "Who is Tovik married to", [A("Tovik", "spouse", None)], True, "noq"),
    ("questions", "Which city does Xenia live in?", [A("Xenia", "city", None)], True, ""),
    ("questions", "Who is Petra's friend?", [A("Petra", "friend", None)], True, ""),
    ("questions", "What hobby did Cadel pick up this year?", [A("Cadel", "hobby", None)], True, ""),
    ("questions", "Who is Yorick's wife?", [A("Yorick", "spouse", None)], True, ""),
    ("questions", "Where does Vespera wrok?", [A("Vespera", "workplace", None)], True, "typo"),
    # ---- chain_questions (15) ----
    ("chain_questions", "Where does Darian's sister live?", [A("Darian", "city", ["sister", "city"])], True, "R6"),
    ("chain_questions", "What language does Liora's brother speak?", [A("Liora", "language", ["brother", "language"])], True, "R6"),
    ("chain_questions", "Where does Cressa's cousin live?", [A("Cressa", "city", ["cousin", "city"])], True, "R6"),
    ("chain_questions", "Who is Jovian's mother's boss?", [A("Jovian", "boss", ["mother", "boss"])], True, "R6"),
    ("chain_questions", "What school does Tovik's sister attend?", [A("Tovik", "school", ["sister", "school"])], True, "R6"),
    ("chain_questions", "Where was Sarella's father born?", [A("Sarella", "place_of_birth", ["father", "place_of_birth"])], True, "R6"),
    ("chain_questions", "Where does Darian's boss live?", [A("Darian", "city", ["boss", "city"])], True, ""),
    ("chain_questions", "What language does Cressa's friend speak?", [A("Cressa", "language", ["friend", "language"])], True, ""),
    ("chain_questions", "Who is Bram's neighbour married to?", [A("Bram", "spouse", ["neighbour", "spouse"])], True, ""),
    ("chain_questions", "Where does Vespera's teacher live?", [A("Vespera", "city", ["teacher", "city"])], True, ""),
    ("chain_questions", "What does Ondrej's friend do for work?", [A("Ondrej", "job", ["friend", "job"])], False, ""),
    ("chain_questions", "Who is Sarella's friend married to?", [A("Sarella", "spouse", ["friend", "spouse"])], True, ""),
    ("chain_questions", "where does darian's sister live", [A("darian", "city", ["sister", "city"])], True, "R6,lower,noq"),
    ("chain_questions", "What language does Liora's brother speak", [A("Liora", "language", ["brother", "language"])], True, "R6,noq"),
    ("chain_questions", "who is jovian's mother married to", [A("jovian", "spouse", ["mother", "spouse"])], True, "R6,lower,noq"),
    # ---- no_save (25) ----
    ("no_save", "My brother lives in Vellmar, right?", [], False, "R2"),
    ("no_save", "It is cold in Frostwick, isn't it?", [], False, "R2"),
    ("no_save", "So Cressa works at Copperline Traders?", [], False, "R2"),
    ("no_save", "so darian lives in vellmar", [], False, "R2,lower,noq"),
    ("no_save", "so liora speaks kessic", [], False, "R2,lower,noq"),
    ("no_save", "jovian works at copperline traders right", [], False, "R2,lower,noq"),
    ("no_save", "cressa lives in caldora isnt it", [], False, "R2,lower,noq,typo"),
    ("no_save", "Tovik lives in Drennick, right?", [], False, "R2"),
    ("no_save", "So Sarella moved to Emberford", [], False, "R2,noq"),
    ("no_save", "I am going to move to Caldora next spring.", [], True, "R8"),
    ("no_save", "Darian will start at Copperline Traders in June.", [], True, "R8"),
    ("no_save", "Liora is hoping to settle in Wildemere someday.", [], True, "R8"),
    ("no_save", "Imagine Liora lived in Vellmar.", [], True, "R9"),
    ("no_save", "Suppose Darian spoke Drellish.", [], True, "R9"),
    ("no_save", "Let's say Cressa won the harbour race.", [], True, "R9"),
    ("no_save", "What if Tovik moved to Zarnow?", [], True, "R9"),
    ("no_save", "Pretend Sarella teaches at Aldergate School.", [], True, "R9"),
    ("no_save", "Honestly, Garrick is simply the greatest manager alive.", [], True, ""),
    ("no_save", "Jessa says Darian lives in Vellmar.", [], True, ""),
    ("no_save", "I used to live in Frostwick.", [], False, ""),
    ("no_save", "Did you know the harbour bridge is closing?", [], False, ""),
    ("no_save", "Apparently Kellan moved to Qamar.", [], False, ""),
    ("no_save", "I love how rainy Thistledown is.", [], True, ""),
    ("no_save", "We should visit the market in Sableton sometime.", [], True, ""),
    ("no_save", "She lives there, I think.", [], False, ""),
    # ---- corrections (15) ----
    ("corrections", "I live in Caldora, not Vellmar.", [T("me", "city", "Caldora")], True, "correction"),
    ("corrections", "My sister is Jessa, not Liora.", [T("me", "sister", "Jessa")], True, "correction"),
    ("corrections", "Darian works at Harbormill Books, not Copperline Traders.", [T("Darian", "workplace", "Harbormill Books")], True, "correction"),
    ("corrections", "Not Bram, my brother is Cadel.", [T("me", "brother", "Cadel")], True, "correction"),
    ("corrections", "My dog is called Nibbles, not Pip.", [T("me", "pet", "Nibbles")], True, "correction"),
    ("corrections", "My grandmother is Vespera, not Sarella.", [T("me", "grandmother", "Vespera")], True, "correction,R4"),
    ("corrections", "Liora lives in Hasselby now, not Drennick.", [T("Liora", "city", "Hasselby")], True, "correction"),
    ("corrections", "I speak Drellish at home, not Kessic.", [T("me", "language", "Drellish")], True, "correction"),
    ("corrections", "Darian's boss is Kessler, not Mellis.", [T("Darian", "boss", "Kessler")], True, "correction"),
    ("corrections", "I was born in Rillwater, not Oakhollow.", [T("me", "place_of_birth", "Rillwater")], True, "correction"),
    ("corrections", "My favourite sport is curling, not skittles.", [T("me", "favourite_sport", "curling")], True, "correction"),
    ("corrections", "i live in drennick, not vellmar.", [T("me", "city", "drennick")], True, "correction,lower"),
    ("corrections", "My cusin is Cadel, not Bram.", [T("me", "cousin", "Cadel")], True, "correction,typo"),
    ("corrections", "Sarella studies at Brookmere College, not Aldergate School.", [T("Sarella", "school", "Brookmere College")], True, "correction"),
    ("corrections", "We got a new cat: Soot, not Taffy.", [T("me", "pet", "Soot")], True, "correction,R7"),
]

EXPECTED_COUNTS = {
    "plain_teach": 25,
    "varied_teach": 30,
    "full_names": 15,
    "questions": 25,
    "chain_questions": 15,
    "no_save": 25,
    "corrections": 15,
}

TEACH_FAMILIES = {"plain_teach", "varied_teach", "full_names", "corrections"}

RELATIVE_FIRST_HOPS = {
    "sister", "brother", "mother", "father", "cousin", "aunt", "uncle",
    "grandmother", "grandfather", "spouse", "half_brother", "stepmother",
}

# Standalone tokens from earlier READMEs that must not be reused here.
FORBIDDEN_TOKENS = [
    "tamsin", "brellin", "suki", "ana", "tarrow", "corin", "elspeth",
    "rin", "anya", "fernhill", "wren", "gil", "quarrow", "marta",
    "pella", "norrish", "orla", "tomas", "tobin", "ilse", "hollis",
    "ostrish", "galvish",
]


def fail(errors, msg):
    errors.append(msg)


def main():
    errors = []
    if len(ITEMS) != 150:
        fail(errors, "expected 150 items, found %d" % len(ITEMS))

    records = []
    for i, (family, turn, gold, clear, notes) in enumerate(ITEMS, start=1):
        records.append({
            "id": "e261-%03d" % i,
            "family": family,
            "turn": turn,
            "gold": gold,
            "clear": clear,
            "notes": notes,
        })

    # Family counts and block order.
    from collections import Counter
    counts = Counter(r["family"] for r in records)
    for fam, want in EXPECTED_COUNTS.items():
        if counts.get(fam, 0) != want:
            fail(errors, "family %s: want %d got %d" % (fam, want, counts.get(fam, 0)))
    order = [r["family"] for r in records]
    blocks = []
    for fam in order:
        if not blocks or blocks[-1] != fam:
            blocks.append(fam)
    if blocks != ["plain_teach", "varied_teach", "full_names", "questions",
                  "chain_questions", "no_save", "corrections"]:
        fail(errors, "family block order wrong: %s" % blocks)

    # Duplicate turns.
    seen = set()
    for r in records:
        if r["turn"] in seen:
            fail(errors, "duplicate turn at %s" % r["id"])
        seen.add(r["turn"])

    # Schema exactness + verbatim subject/value + alias exactness.
    for r in records:
        if set(r.keys()) != {"id", "family", "turn", "gold", "clear", "notes"}:
            fail(errors, "%s: top-level keys %s" % (r["id"], sorted(r.keys())))
        if not isinstance(r["clear"], bool):
            fail(errors, "%s: clear not bool" % r["id"])
        if not isinstance(r["notes"], str):
            fail(errors, "%s: notes not str" % r["id"])
        for f in r["gold"]:
            if f["act"] == "TEACH":
                if set(f.keys()) != {"act", "subject", "relation", "relation_aliases", "value"}:
                    fail(errors, "%s: TEACH keys %s" % (r["id"], sorted(f.keys())))
                if f["relation"] not in ALIASES:
                    fail(errors, "%s: unknown relation %s" % (r["id"], f["relation"]))
                elif f["relation_aliases"] != ALIASES[f["relation"]]:
                    fail(errors, "%s: alias list mismatch for %s" % (r["id"], f["relation"]))
                if f["subject"] != "me" and f["subject"] not in r["turn"]:
                    fail(errors, "%s: subject not verbatim in turn" % r["id"])
                if f["value"] not in r["turn"]:
                    fail(errors, "%s: value not verbatim in turn" % r["id"])
            elif f["act"] == "ASK":
                if set(f.keys()) != {"act", "subject", "relation", "chain", "relation_aliases", "chain_aliases"}:
                    fail(errors, "%s: ASK keys %s" % (r["id"], sorted(f.keys())))
                if f["relation"] not in ALIASES:
                    fail(errors, "%s: unknown relation %s" % (r["id"], f["relation"]))
                elif f["relation_aliases"] != ALIASES[f["relation"]]:
                    fail(errors, "%s: alias list mismatch for %s" % (r["id"], f["relation"]))
                if f["chain"] is None:
                    if f["chain_aliases"] is not None:
                        fail(errors, "%s: chain null but chain_aliases not null" % r["id"])
                else:
                    if len(f["chain"]) != 2 or f["chain"][1] != f["relation"]:
                        fail(errors, "%s: bad chain %s" % (r["id"], f["chain"]))
                    if f["chain_aliases"] != [ALIASES[f["chain"][0]], ALIASES[f["chain"][1]]]:
                        fail(errors, "%s: chain_aliases mismatch" % r["id"])
                    if f["chain_aliases"][1] != f["relation_aliases"]:
                        fail(errors, "%s: chain_aliases[1] != relation_aliases" % r["id"])
                if f["subject"] != "me" and f["subject"] not in r["turn"]:
                    fail(errors, "%s: ASK subject not verbatim in turn" % r["id"])
            else:
                fail(errors, "%s: bad act %s" % (r["id"], f["act"]))

    # Family/act consistency.
    for r in records:
        acts = {f["act"] for f in r["gold"]}
        if r["family"] in ("questions", "chain_questions"):
            if acts != {"ASK"}:
                fail(errors, "%s: question family without pure ASK gold" % r["id"])
        elif r["family"] != "no_save":
            if acts != {"TEACH"}:
                fail(errors, "%s: teach family without pure TEACH gold" % r["id"])
        else:
            if r["gold"] != []:
                fail(errors, "%s: no_save with non-empty gold" % r["id"])
        if r["family"] == "corrections" and "correction" not in r["notes"].split(","):
            fail(errors, "%s: correction missing 'correction' note" % r["id"])

    def tags(r):
        return [t for t in r["notes"].split(",") if t]

    def has(r, tag):
        return tag in tags(r)

    def infam(r, *fams):
        return r["family"] in fams

    # Risk quotas.
    q = {}
    q["R1_varied_full"] = sum(1 for r in records if has(r, "R1") and infam(r, "varied_teach", "full_names"))
    q["R2_nosave"] = sum(1 for r in records if has(r, "R2") and infam(r, "no_save") and r["gold"] == [])
    q["R2_nosave_noq"] = sum(1 for r in records if has(r, "R2") and infam(r, "no_save") and "?" not in r["turn"])
    q["R2_varied_fact"] = sum(1 for r in records if has(r, "R2") and infam(r, "varied_teach") and r["gold"] != [])
    q["R3"] = sum(1 for r in records if has(r, "R3"))
    q["R4"] = sum(1 for r in records if has(r, "R4"))
    q["R5"] = sum(1 for r in records if has(r, "R5"))
    q["R6_chain"] = sum(1 for r in records if has(r, "R6") and infam(r, "chain_questions"))
    q["R7_teach"] = sum(1 for r in records if has(r, "R7") and infam(r, *TEACH_FAMILIES))
    q["R8"] = sum(1 for r in records if has(r, "R8"))
    q["R8_varied_fact"] = sum(1 for r in records if has(r, "R8") and infam(r, "varied_teach") and r["gold"] != [])
    q["R8_nosave_empty"] = sum(1 for r in records if has(r, "R8") and infam(r, "no_save") and r["gold"] == [])
    q["R9_nosave"] = sum(1 for r in records if has(r, "R9") and infam(r, "no_save") and r["gold"] == [])
    q["R10"] = sum(1 for r in records if has(r, "R10"))
    q["R11"] = sum(1 for r in records if has(r, "R11"))
    q["R12"] = sum(1 for r in records if has(r, "R12"))
    q["lower_typo"] = sum(1 for r in records if has(r, "lower") or has(r, "typo"))
    q["q_chain_lower_noq"] = sum(
        1 for r in records
        if infam(r, "questions", "chain_questions") and (has(r, "lower") or has(r, "noq"))
    )

    bars = {
        "R1_varied_full": 8, "R2_nosave": 8, "R2_nosave_noq": 5,
        "R2_varied_fact": 3, "R3": 6, "R4": 6, "R5": 8, "R6_chain": 5,
        "R7_teach": 6, "R8": 6, "R8_varied_fact": 3, "R8_nosave_empty": 3,
        "R9_nosave": 5, "R10": 4, "R11": 6, "R12": 4,
        "lower_typo": 15, "q_chain_lower_noq": 5,
    }
    for name, want in bars.items():
        if q[name] < want:
            fail(errors, "quota %s: want >= %d got %d" % (name, want, q[name]))

    # Structural spot-checks for multi-frame risks.
    for r in records:
        if has(r, "R10") and len(r["gold"]) < 3:
            fail(errors, "%s: R10 with <3 frames" % r["id"])
        if has(r, "R11") and len(r["gold"]) < 2:
            fail(errors, "%s: R11 with <2 frames" % r["id"])
        if has(r, "R12"):
            if len(r["gold"]) < 2:
                fail(errors, "%s: R12 with <2 frames" % r["id"])
            elif r["gold"][1]["subject"] != r["gold"][0]["value"]:
                fail(errors, "%s: R12 second subject != first value" % r["id"])
        if has(r, "R6") and infam(r, "chain_questions"):
            ch = r["gold"][0]["chain"]
            if ch[0] not in RELATIVE_FIRST_HOPS:
                fail(errors, "%s: R6 first hop not a relative: %s" % (r["id"], ch[0]))

    # full_names items must carry a 2+ word name in some subject/value.
    for r in records:
        if infam(r, "full_names"):
            if not any(" " in f.get("subject", "") or " " in f.get("value", "") for f in r["gold"]):
                fail(errors, "%s: full_names item with no multiword name" % r["id"])

    # Forbidden-token screen (standalone words, case-insensitive).
    for r in records:
        words = set(re.findall(r"[A-Za-z]+", r["turn"].lower()))
        hit = words & set(FORBIDDEN_TOKENS)
        if hit:
            fail(errors, "%s: forbidden token(s) %s" % (r["id"], sorted(hit)))

    n_clear_false = sum(1 for r in records if r["clear"] is False)

    if errors:
        print("SELF-CHECK FAIL (%d problems):" % len(errors))
        for e in errors:
            print("  - " + e)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PANEL_PATH, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")

    print("SELF-CHECK PASS: 150 items written to %s" % PANEL_PATH)
    print("families: " + ", ".join("%s=%d" % (f, counts[f]) for f in EXPECTED_COUNTS))
    print("quotas: " + ", ".join("%s=%d" % (k, q[k]) for k in sorted(q)))
    print("clear_false=%d" % n_clear_false)


if __name__ == "__main__":
    main()
