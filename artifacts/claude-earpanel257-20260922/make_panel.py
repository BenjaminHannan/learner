#!/usr/bin/env python3
"""Ear panel 257 generator (TEST-ONLY). Holds all 150 items by hand, writes
panel.jsonl deterministically, and runs the self-checks from the spec.

Run: python3 -B artifacts/claude-earpanel257-20260922/make_panel.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "panel.jsonl")

# One fixed alias list per relation.
ALIASES = {
    "city": ["lives_in", "residence", "current_city", "location"],
    "workplace": ["employer", "works_at", "company"],
    "job": ["occupation", "profession", "work"],
    "boss": ["manager", "supervisor"],
    "sister": ["sibling"],
    "brother": ["sibling"],
    "half_sister": ["halfsister"],
    "half_brother": ["halfbrother"],
    "spouse": ["husband", "wife", "married_to"],
    "partner": ["girlfriend", "boyfriend"],
    "language": ["languages", "speaks"],
    "hometown": ["grew_up_in", "home_town"],
    "place_of_birth": ["birthplace", "born_in"],
    "pet": ["pet_name", "dog", "cat"],
    "school": ["studies_at", "college", "university"],
    "cousin": [],
    "aunt": ["auntie"],
    "daughter": ["child"],
    "son": ["child"],
    "grandmother": ["grandma", "gran", "nan"],
    "granddaughter": ["grandchild"],
    "grandson": ["grandchild"],
    "great_aunt": ["great_auntie", "grandaunt"],
    "great_uncle": ["granduncle"],
    "great_grandmother": ["great_grandma"],
    "sister_in_law": [],
    "brother_in_law": [],
    "mother_in_law": [],
    "step_brother": ["stepbrother"],
    "step_father": ["stepfather", "stepdad"],
    "step_mother": ["stepmother", "stepmum", "stepmom"],
    "second_cousin": [],
    "housemate": ["flatmate", "roommate"],
    "instrument": ["plays", "musical_instrument"],
    "favourite_food": ["favorite_food"],
    "favourite_sport": ["favorite_sport"],
    "hobby": ["hobbies", "pastime"],
    "teacher": ["tutor"],
    "doctor": ["gp", "physician"],
    "neighbour": ["neighbor"],
}

PLAIN_RELATIVES = {"sister", "brother", "mother", "father", "son", "daughter",
                   "aunt", "uncle", "cousin", "sibling", "mum", "mom", "dad",
                   "grandmother", "grandfather", "parent", "child"}
COMPOUND_RE = re.compile(r"(_in_law|^step_|^half_|^grand|^great_|^second_cousin$)")
RELATIVES = PLAIN_RELATIVES | {r for r in ALIASES if COMPOUND_RE.search(r)} | {"spouse"}
EVERYDAY = {"housemate", "instrument", "favourite_food", "favourite_sport",
            "hobby", "teacher", "doctor", "neighbour", "partner"}


def T(subject, relation, value):
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": list(ALIASES[relation]), "value": value}


def A(subject, relation):
    return {"act": "ASK", "subject": subject, "relation": relation, "chain": None,
            "relation_aliases": list(ALIASES[relation]), "chain_aliases": None}


def A2(subject, r1, r2):
    return {"act": "ASK", "subject": subject, "relation": r2, "chain": [r1, r2],
            "relation_aliases": list(ALIASES[r2]),
            "chain_aliases": [list(ALIASES[r1]), list(ALIASES[r2])]}


# Each raw item: (turn, gold, clear, notes, negated_values)
PLAIN = [
    ("I live in Karnbury.", [T("me", "city", "Karnbury")], True, "plain", []),
    ("My sister is called Maelis.", [T("me", "sister", "Maelis")], True, "plain", []),
    ("Dorran works at Tamber Logistics.", [T("Dorran", "workplace", "Tamber Logistics")], True, "plain", []),
    ("My dog's name is Pickle.", [T("me", "pet", "Pickle")], True, "pet", []),
    ("Jessamy speaks Oltic.", [T("Jessamy", "language", "Oltic")], True, "language", []),
    ("I was born in Sallowmere.", [T("me", "place_of_birth", "Sallowmere")], True, "birthplace", []),
    ("My boss is Hettie.", [T("me", "boss", "Hettie")], True, "plain", []),
    ("Caspar is a plumber.", [T("Caspar", "job", "plumber")], True, "job", []),
    ("my brother is lorcan", [T("me", "brother", "lorcan")], True, "lower", []),
    ("Ferelith lives in Quillon.", [T("Ferelith", "city", "Quillon")], True, "plain", []),
    ("My wife is Imogen.", [T("me", "spouse", "Imogen")], True, "plain", []),
    ("I work as a nurse.", [T("me", "job", "nurse")], True, "job", []),
    ("My stepbrother is Arlo.", [T("me", "step_brother", "Arlo")], True, "R4", []),
    ("My grandmother is Winifred.", [T("me", "grandmother", "Winifred")], True, "R4", []),
    ("My housemate is Teodor.", [T("me", "housemate", "Teodor")], True, "R5", []),
    ("I play the cello.", [T("me", "instrument", "cello")], True, "R5", []),
    ("Nisha's cat is called Marmalade.", [T("Nisha", "pet", "Marmalade")], True, "pet", []),
    ("i speak marrish", [T("me", "language", "marrish")], True, "lower language", []),
    ("My neighbour is Gethin.", [T("me", "neighbour", "Gethin")], True, "R5", []),
    ("My doctor is Dr Abernathy.", [T("me", "doctor", "Dr Abernathy")], True, "R5", []),
    ("Leocadia is from Morrowvale.", [T("Leocadia", "hometown", "Morrowvale")], False,
     "unclear why=from_could_be_birthplace", []),
    ("Rufus is an electrician.", [T("Rufus", "job", "electrician")], True, "job", []),
    ("My sister-in-law is Perpetua.", [T("me", "sister_in_law", "Perpetua")], True, "R4", []),
    ("my favourite food is dumplings", [T("me", "favourite_food", "dumplings")], True, "lower R5", []),
    ("Oswin's boss is Delphine.", [T("Oswin", "boss", "Delphine")], True, "plain", []),
]

VARIED = [
    ("My cousin Rosalind just moved to Lisswold and she teaches at Lisswold Primary School.",
     [T("me", "cousin", "Rosalind"), T("Rosalind", "city", "Lisswold"),
      T("Rosalind", "workplace", "Lisswold Primary School")], True, "R1 R3", []),
    ("I'm in Corbray now but my brother Idris stayed in Fennick Bay and he works for Brisk Ferries.",
     [T("me", "city", "Corbray"), T("me", "brother", "Idris"), T("Idris", "city", "Fennick Bay"),
      T("Idris", "workplace", "Brisk Ferries")], True, "R1 R1rel", []),
    ("My aunt is Philippa and I visit her a lot, she lives in Aldwen.",
     [T("me", "aunt", "Philippa"), T("Philippa", "city", "Aldwen")], True, "R1 R1rel", []),
    ("Me and my half-sister Ottilie are close, she speaks Venn.",
     [T("me", "half_sister", "Ottilie"), T("Ottilie", "language", "Venn")], True, "R1 R1rel R4", []),
    ("You know where Benedikt works, it's Kestrel Mills.",
     [T("Benedikt", "workplace", "Kestrel Mills")], True, "R2f", []),
    ("The town where I was born is Cawder.",
     [T("me", "place_of_birth", "Cawder")], True, "R2f", []),
    ("That's why I moved to Stranmoor, the rent is way cheaper.",
     [T("me", "city", "Stranmoor")], True, "R2f", []),
    ("Soren coaches at Corbray Rowing Club.",
     [T("Soren", "workplace", "Corbray Rowing Club")], True, "R3", []),
    ("Mireille studies at Brackwood College.",
     [T("Mireille", "school", "Brackwood College")], True, "R3", []),
    ("Anselm teaches history at Quillon High School.",
     [T("Anselm", "workplace", "Quillon High School")], True, "R3", []),
    ("my flatmate is jory, hes a chef",
     [T("me", "housemate", "jory"), T("jory", "job", "chef")], True, "R1 R5 lower typo", []),
    ("Cressida's husband is Aurelio and he works as a pilot.",
     [T("Cressida", "spouse", "Aurelio"), T("Aurelio", "job", "pilot")], True, "R1", []),
    ("Yesterday I met Leontine's new neighbour, Emrys.",
     [T("Leontine", "neighbour", "Emrys")], True, "R5", []),
    ("I've got a great-uncle called Ambrose and he still lives in Sallowmere, I phone him on Sundays.",
     [T("me", "great_uncle", "Ambrose"), T("Ambrose", "city", "Sallowmere")], True, "R1 R1rel R4", []),
    ("Tilda's piano teacher is Mrs Pennifold.",
     [T("Tilda", "teacher", "Mrs Pennifold")], True, "R5", []),
    ("Hugo loves rugby, it's his favourite sport by miles.",
     [T("Hugo", "favourite_sport", "rugby")], True, "R5", []),
    ("When Hal isn't working he plays the banjo.",
     [T("Hal", "instrument", "banjo")], True, "R1 R2f R5", []),
    ("Working at Tamber Logistics is Perrin's first job.",
     [T("Perrin", "workplace", "Tamber Logistics")], True, "varied", []),
    ("Our dog Bramble is a spaniel.", [T("me", "pet", "Bramble")], True, "pet", []),
    ("Yvaine used to be a nurse but now she is a midwife.",
     [T("Yvaine", "job", "midwife")], True, "R1 job", ["nurse"]),
    ("iolo teaches at brackwood college",
     [T("iolo", "workplace", "brackwood college")], True, "R3 lower", []),
    ("my step-dad gideon is a postman and he grew up in aldwen",
     [T("me", "step_father", "gideon"), T("gideon", "job", "postman"),
      T("gideon", "hometown", "aldwen")], False, "R1 R4 lower unclear why=grew_up_could_be_birthplace", []),
    ("Fenella is at Brackwood College.",
     [T("Fenella", "school", "Brackwood College")], False, "R3 unclear why=is_at_could_be_workplace", []),
    ("Ingram's youngest daughter is Clemency.",
     [T("Ingram", "daughter", "Clemency")], True, "varied", []),
    ("Both my grandsons, Tobiah and Ellery, live in Quillon.",
     [T("me", "grandson", "Tobiah"), T("me", "grandson", "Ellery"),
      T("Tobiah", "city", "Quillon"), T("Ellery", "city", "Quillon")], True, "R4", []),
    ("Seraphina works as a vet and she lives in Lisswold.",
     [T("Seraphina", "job", "vet"), T("Seraphina", "city", "Lisswold")], True, "R1", []),
    ("Birdwatching is Radomir's big hobby.",
     [T("Radomir", "hobby", "Birdwatching")], True, "R5", []),
    ("Lucan's wife Honoria speaks Oltic and she works at Kestrel Mills.",
     [T("Lucan", "spouse", "Honoria"), T("Honoria", "language", "Oltic"),
      T("Honoria", "workplace", "Kestrel Mills")], True, "R1", []),
    ("Evander is training to be a pilot and he studies at Corbray Flight College.",
     [T("Evander", "school", "Corbray Flight College")], True, "R1 R3", []),
    ("I teach at Stranmoor Academy, and my brother-in-law Kasimir studies there.",
     [T("me", "workplace", "Stranmoor Academy"), T("me", "brother_in_law", "Kasimir"),
      T("Kasimir", "school", "Stranmoor Academy")], True, "R3 R4", []),
]

FULL = [
    ("My boss is Marguerite Delacourt Finch.",
     [T("me", "boss", "Marguerite Delacourt Finch")], True, "fullname", []),
    ("Cosmo Tiernan Vale lives in Fennick Bay.",
     [T("Cosmo Tiernan Vale", "city", "Fennick Bay")], True, "fullname", []),
    ("My sister's full name is Liesl Anne Marchbank.",
     [T("me", "sister", "Liesl Anne Marchbank")], True, "fullname", []),
    ("Dr Hesketh Rowe is my doctor.",
     [T("me", "doctor", "Dr Hesketh Rowe")], True, "fullname R5", []),
    ("Juniper Achterberg teaches at Morrowvale Grammar School and she lives in Quillon.",
     [T("Juniper Achterberg", "workplace", "Morrowvale Grammar School"),
      T("Juniper Achterberg", "city", "Quillon")], True, "fullname R1 R3", []),
    ("Idony Castellane studies at Lisswold College.",
     [T("Idony Castellane", "school", "Lisswold College")], True, "fullname R3", []),
    ("my girlfriend is sabine delorme",
     [T("me", "partner", "sabine delorme")], True, "fullname R5 lower", []),
    ("Wendeline Ashby-Crowe coaches at Brackmoor Tennis Club, and she was born in Cawder.",
     [T("Wendeline Ashby-Crowe", "workplace", "Brackmoor Tennis Club"),
      T("Wendeline Ashby-Crowe", "place_of_birth", "Cawder")], True, "fullname R1 R3", []),
    ("My mother-in-law, Rosamund Hale Quaile, speaks Venn.",
     [T("me", "mother_in_law", "Rosamund Hale Quaile"),
      T("Rosamund Hale Quaile", "language", "Venn")], True, "fullname R4", []),
    ("Barnaby Osei Lindqvist is a firefighter.",
     [T("Barnaby Osei Lindqvist", "job", "firefighter")], True, "fullname", []),
    ("I live with my great-grandmother, Agathe Morel Dunstan, and she was born in Tethering.",
     [T("me", "great_grandmother", "Agathe Morel Dunstan"),
      T("Agathe Morel Dunstan", "place_of_birth", "Tethering")], True, "fullname R1 R1rel R4", []),
    ("Our new neighbour is Percival John Arkwright.",
     [T("me", "neighbour", "Percival John Arkwright")], True, "fullname R5", []),
    ("Clementine Vasquell and her brother Florian Vasquell both work at Glassford Bakery.",
     [T("Clementine Vasquell", "brother", "Florian Vasquell"),
      T("Clementine Vasquell", "workplace", "Glassford Bakery"),
      T("Florian Vasquell", "workplace", "Glassford Bakery")], True, "fullname", []),
    ("Ignatius Farrow-Beck is my second cousin and he plays the trombone.",
     [T("me", "second_cousin", "Ignatius Farrow-Beck"),
      T("Ignatius Farrow-Beck", "instrument", "trombone")], True, "fullname R1 R4 R5", []),
    ("Maximilian Orrin Hartley studies at Quillon Art School but he wants to teach there one day.",
     [T("Maximilian Orrin Hartley", "school", "Quillon Art School")], True, "fullname R3", []),
]

QUESTIONS = [
    ("Where does Ferelith live?", [A("Ferelith", "city")], True, "q", []),
    ("Who's my boss?", [A("me", "boss")], True, "q", []),
    ("What language does Jessamy speak?", [A("Jessamy", "language")], True, "q", []),
    ("where dose dorran work", [A("dorran", "workplace")], True, "q lower typo noq", []),
    ("What's Caspar's job?", [A("Caspar", "job")], True, "q", []),
    ("Who is Arlo's step-mum?", [A("Arlo", "step_mother")], True, "q R4", []),
    ("Who's Cressida married to?", [A("Cressida", "spouse")], True, "q", []),
    ("What is my dog called?", [A("me", "pet")], True, "q", []),
    ("Where was Leocadia born?", [A("Leocadia", "place_of_birth")], True, "q", []),
    ("Who is Oswin's sister-in-law?", [A("Oswin", "sister_in_law")], True, "q R4", []),
    ("what instrument does hal play", [A("hal", "instrument")], True, "q R5 lower noq", []),
    ("Who's Nisha's doctor?", [A("Nisha", "doctor")], True, "q R5", []),
    ("Tell me where Soren works.", [A("Soren", "workplace")], True, "q noq", []),
    ("What does Radomir do for fun?", [A("Radomir", "hobby")], True, "q R5", []),
    ("Who is Winifred's granddaughter?", [A("Winifred", "granddaughter")], True, "q R4", []),
    ("Which school does Mireille go to?", [A("Mireille", "school")], True, "q", []),
    ("who is lucan's wife", [A("lucan", "spouse")], True, "q lower noq", []),
    ("Who is Gethin's neighbour?", [A("Gethin", "neighbour")], True, "q R5", []),
    ("Where did Dagny grow up?", [A("Dagny", "hometown")], True, "q", []),
    ("What's Hugo's favourite food?", [A("Hugo", "favourite_food")], True, "q R5", []),
    ("Who are Tilda's half-brothers?", [A("Tilda", "half_brother")], True, "q R4", []),
    ("What is Idris's job?", [A("Idris", "job")], True, "q", []),
    ("Does Ingram have a daughter?", [A("Ingram", "daughter")], False,
     "q unclear why=yes_no_existence_check", []),
    ("Which city is Imogen in these days?", [A("Imogen", "city")], True, "q", []),
    ("Who's Maelis's great-aunt?", [A("Maelis", "great_aunt")], True, "q R4", []),
]

CHAINS = [
    ("Where does my sister live?", [A2("me", "sister", "city")], True, "chain R6", []),
    ("What does Bryony's husband do for a living?", [A2("Bryony", "spouse", "job")], True, "chain R6", []),
    ("which language does my boss speak", [A2("me", "boss", "language")], True, "chain lower noq", []),
    ("Where does Oswin's boss work?", [A2("Oswin", "boss", "workplace")], True, "chain", []),
    ("Who is my cousin's doctor?", [A2("me", "cousin", "doctor")], True, "chain R5 R6", []),
    ("Where was Cressida's husband born?", [A2("Cressida", "spouse", "place_of_birth")], True, "chain R6", []),
    ("whats my brothers dog called", [A2("me", "brother", "pet")], True, "chain R6 lower typo noq", []),
    ("Where does Dorran's manager live?", [A2("Dorran", "boss", "city")], True, "chain", []),
    ("What instrument does Lucan's wife play?", [A2("Lucan", "spouse", "instrument")], True, "chain R5 R6", []),
    ("Who is Ingram's daughter's boss?", [A2("Ingram", "daughter", "boss")], True, "chain R6", []),
    ("Where does my housemate work?", [A2("me", "housemate", "workplace")], True, "chain R5", []),
    ("tell me where my stepdad grew up", [A2("me", "step_father", "hometown")], False,
     "chain R4 R6 lower noq unclear why=grew_up_could_be_birthplace", []),
    ("Which school does Nisha's son go to?", [A2("Nisha", "son", "school")], True, "chain R6", []),
    ("Who is Hettie's boss married to?", [A2("Hettie", "boss", "spouse")], True, "chain", []),
    ("What does Seraphina's neighbour do?", [A2("Seraphina", "neighbour", "job")], False,
     "chain R5 unclear why=job_or_workplace", []),
]

NOSAVE = [
    ("Ferelith lives in Quillon, right?", [], False, "R2 R2tag unclear why=ask_also_reasonable", []),
    ("so Caspar is a plumber?", [], False, "R2 R2so unclear why=ask_also_reasonable", []),
    ("Dorran works at Kestrel Mills??", [], False, "R2 R2dq unclear why=ask_also_reasonable", []),
    ("jessamy speaks venn doesnt she", [], False, "R2 R2tag lower typo unclear why=ask_also_reasonable", []),
    ("so nisha has a cat called marmalade", [], False, "R2 R2so lower unclear why=ask_also_reasonable", []),
    ("wait arlo lives in brackmoor", [], False, "R2 lower unclear why=ask_also_reasonable", []),
    ("oswin is a teacher right", [], False, "R2 R2tag lower unclear why=ask_also_reasonable", []),
    ("and imogen's from karnbury yeah", [], False, "R2 R2tag lower unclear why=ask_also_reasonable", []),
    ("you're saying gethin plays drums", [], False, "R2 lower unclear why=ask_also_reasonable", []),
    ("leocadia was born in cawder wasnt she", [], False, "R2 R2tag lower typo unclear why=ask_also_reasonable", []),
    ("Soren coaches at Corbray Rowing Club, doesn't he?", [], False, "R2 R2tag unclear why=ask_also_reasonable", []),
    ("My brother doesn't live in Stranmoor.", [], True, "negated", []),
    ("If I moved to Aldwen I'd be closer to work.", [], True, "hypothetical", []),
    ("Perrin says his boss is Umberto.", [], True, "hearsay", []),
    ("I used to live in Fennick Bay.", [], False, "past unclear why=past_city", []),
    ("Let's say my sister is called Rowena.", [], True, "pretend", []),
    ("Maybe Teodor works at Glassford Bakery, I'm not sure.", [], True, "uncertain", []),
    ("Hettie is the worst boss ever.", [], True, "opinion", []),
    ("Hi there, how's your day going?", [], True, "smalltalk", []),
    ("Imagine if Hugo spoke Marrish.", [], True, "hypothetical", []),
    ("I heard Dagny might be moving to Corbray.", [], True, "hearsay uncertain", []),
    ("I'm not a nurse, never have been.", [], True, "negated", []),
    ("Did you know Tamber Logistics is hiring?", [], False, "news unclear why=news_could_be_stored", []),
    ("Thanks, that's all for now!", [], True, "smalltalk", []),
    ("Nobody in my family speaks Oltic.", [], True, "negated", []),
]

CORRECTIONS = [
    ("Sorry, I don't live in Karnbury, I live in Callowby.", [T("me", "city", "Callowby")], True,
     "correction", ["Karnbury"]),
    ("Actually my sister is Maelys, not Maelis.", [T("me", "sister", "Maelys")], True,
     "correction", ["Maelis"]),
    ("No wait, Dorran works at Brisk Ferries, not Tamber Logistics.",
     [T("Dorran", "workplace", "Brisk Ferries")], True, "correction", ["Tamber Logistics"]),
    ("correction: jessamy speaks marrish not oltic", [T("jessamy", "language", "marrish")], True,
     "correction lower", ["oltic"]),
    ("I got that wrong, Caspar is an electrician rather than a plumber.",
     [T("Caspar", "job", "electrician")], True, "correction", ["plumber"]),
    ("Not Hettie - my boss is Philomena.", [T("me", "boss", "Philomena")], True,
     "correction", ["Hettie"]),
    ("Oops, my dog is called Pickles, not Pickle.", [T("me", "pet", "Pickles")], True,
     "correction", ["Pickle"]),
    ("Ferelith moved out of Quillon last month, she's in Brackmoor now.",
     [T("Ferelith", "city", "Brackmoor")], True, "correction R1", ["Quillon"]),
    ("scratch that, i was born in tethering, not sallowmere",
     [T("me", "place_of_birth", "tethering")], True, "correction lower", ["sallowmere"]),
    ("My wife's name is actually Imelda, I typed it wrong before.",
     [T("me", "spouse", "Imelda")], True, "correction", []),
    ("Oswin's boss isn't Delphine anymore, it's Rosalie.", [T("Oswin", "boss", "Rosalie")], True,
     "correction", ["Delphine"]),
    ("Sorry, I meant Mireille studies at Lisswold College, not Brackwood.",
     [T("Mireille", "school", "Lisswold College")], True, "correction", ["Brackwood"]),
    ("Correction - Teodor isn't my housemate, Bastian is.", [T("me", "housemate", "Bastian")], True,
     "correction R5", ["Teodor"]),
    ("Wrong instrument, I play the viola, not the cello.", [T("me", "instrument", "viola")], True,
     "correction R5", ["cello"]),
    ("my stepbrother is called arlen not arlo, sorry", [T("me", "step_brother", "arlen")], True,
     "correction lower R4", ["arlo"]),
]

FAMILIES = [
    ("plain_teach", PLAIN, 25),
    ("varied_teach", VARIED, 30),
    ("full_names", FULL, 15),
    ("questions", QUESTIONS, 25),
    ("chain_questions", CHAINS, 15),
    ("no_save", NOSAVE, 25),
    ("corrections", CORRECTIONS, 15),
]
TEACH_FAMS = {"plain_teach", "varied_teach", "full_names", "corrections"}


def build():
    rows, negs = [], []
    n = 0
    for fam, items, _ in FAMILIES:
        for turn, gold, clear, notes, neg in items:
            n += 1
            rows.append({"id": "e257-%03d" % n, "family": fam, "turn": turn,
                         "gold": gold, "clear": clear, "notes": notes})
            negs.append(neg)
    return rows, negs


FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def word_in(x, turn):
    return re.search(r"(?<![A-Za-z])" + re.escape(x) + r"(?![A-Za-z])", turn) is not None


def self_checks(rows, negs):
    tags = [set(r["notes"].split()) for r in rows]
    # family counts
    for fam, _, want in FAMILIES:
        got = sum(r["family"] == fam for r in rows)
        check(got == want, "family %s count %d (want %d)" % (fam, got, want))
    check(len(rows) == 150, "total items %d (want 150)" % len(rows))
    check([r["id"] for r in rows] == ["e257-%03d" % i for i in range(1, 151)], "ids in order")
    turns = [r["turn"] for r in rows]
    check(len(set(turns)) == len(turns), "no duplicate turn")

    # schema exactness
    schema_ok = True
    for r in rows:
        if list(r.keys()) != ["id", "family", "turn", "gold", "clear", "notes"]:
            schema_ok = False
        if not isinstance(r["clear"], bool) or not isinstance(r["notes"], str):
            schema_ok = False
        for g in r["gold"]:
            if g["act"] == "TEACH":
                if set(g) != {"act", "subject", "relation", "relation_aliases", "value"}:
                    schema_ok = False
            elif g["act"] == "ASK":
                if set(g) != {"act", "subject", "relation", "chain", "relation_aliases", "chain_aliases"}:
                    schema_ok = False
                if g["chain"] is None:
                    if g["chain_aliases"] is not None:
                        schema_ok = False
                else:
                    if (len(g["chain"]) != 2 or g["chain"][1] != g["relation"]
                            or len(g["chain_aliases"]) != 2
                            or g["chain_aliases"][0] != ALIASES[g["chain"][0]]
                            or g["chain_aliases"][1] != g["relation_aliases"]):
                        schema_ok = False
            else:
                schema_ok = False
            if g["relation_aliases"] != ALIASES[g["relation"]]:
                schema_ok = False
            if not re.fullmatch(r"[a-z]+(_[a-z]+)*", g["relation"]):
                schema_ok = False
    check(schema_ok, "schema exact (fields, chain, chain_aliases, fixed alias lists)")

    # family / act consistency
    fam_ok = True
    for r in rows:
        acts = {g["act"] for g in r["gold"]}
        f = r["family"]
        if f in TEACH_FAMS and (not r["gold"] or acts != {"TEACH"}):
            fam_ok = False
        if f == "no_save" and r["gold"]:
            fam_ok = False
        if f == "questions" and (len(r["gold"]) != 1 or acts != {"ASK"} or r["gold"][0]["chain"] is not None):
            fam_ok = False
        if f == "chain_questions" and (len(r["gold"]) != 1 or acts != {"ASK"} or r["gold"][0]["chain"] is None):
            fam_ok = False
        if f == "corrections" and "correction" not in r["notes"].split():
            fam_ok = False
    check(fam_ok, "gold act matches family; corrections tagged")

    # subject/value word-for-word
    sv_ok, bad = True, []
    for r in rows:
        for g in r["gold"]:
            for k in ("subject", "value"):
                if k in g and g[k] != "me" and not word_in(g[k], r["turn"]):
                    sv_ok = False
                    bad.append(r["id"])
    check(sv_ok, "every subject/value (except me) appears word for word %s" % (bad or ""))

    # negated old values never in gold
    neg_ok = True
    for r, neg in zip(rows, negs):
        vals = {g.get("value") for g in r["gold"]}
        if any(nv in vals for nv in neg):
            neg_ok = False
        if any(not word_in(nv, r["turn"]) for nv in neg):
            neg_ok = False
    check(neg_ok, "negated old values present in turn and absent from gold")

    # compound relations: no plain-relative alias
    comp_ok = all(not (set(ALIASES[rel]) & PLAIN_RELATIVES) for rel in ALIASES if COMPOUND_RE.search(rel))
    check(comp_ok, "compound relations carry no plain-relative alias")

    def rels(r):
        out = set()
        for g in r["gold"]:
            out.add(g["relation"])
            if g.get("chain"):
                out.update(g["chain"])
        return out

    pron = re.compile(r"\b(she|he|they|it|her|him|his|hes|she's|he's)\b", re.I)
    first = re.compile(r"\b(i|i'm|i've|me)\b", re.I)
    qword = re.compile(r"\b(who|what|where|when|why|how|which)\b", re.I)

    # R1
    r1 = [r for r, t in zip(rows, tags) if "R1" in t]
    r1_ok = all(r["family"] in ("varied_teach", "full_names", "corrections") and pron.search(r["turn"]) for r in r1)
    r1_main = [r for r in r1 if r["family"] in ("varied_teach", "full_names")]
    fams = {r["family"] for r in r1_main}
    check(len(r1_main) >= 10 and r1_ok and fams == {"varied_teach", "full_names"},
          "R1 pronoun turns in varied_teach+full_names: %d (>=10), spread %s" % (len(r1_main), sorted(fams)))
    r1rel = [r for r, t in zip(rows, tags) if "R1rel" in t]
    r1rel_ok = all("R1" in r["notes"].split() and first.search(r["turn"])
                   and any(g["subject"] == "me" and g["relation"] in RELATIVES for g in r["gold"])
                   for r in r1rel)
    check(len(r1rel) >= 3 and r1rel_ok, "R1 relative + first-person clause: %d (>=3)" % len(r1rel))

    # R2
    r2 = [r for r, t in zip(rows, tags) if "R2" in t]
    r2_ok = all(r["family"] == "no_save" and r["gold"] == [] for r in r2)
    r2_noq = [r for r in r2 if "?" not in r["turn"]]
    has_tag = any("R2tag" in t for t in tags)
    has_so = any("R2so" in t and r["turn"].lower().startswith("so ") for r, t in zip(rows, tags))
    has_dq = any("R2dq" in t and "??" in r["turn"] for r, t in zip(rows, tags))
    check(len(r2) >= 10 and r2_ok, "R2 statement-shaped questions in no_save, gold []: %d (>=10)" % len(r2))
    check(len(r2_noq) >= 6, "R2 with no question mark: %d (>=6)" % len(r2_noq))
    check(has_tag and has_so and has_dq, "R2 includes tag question, 'so ...', and '??'")
    r2f = [r for r, t in zip(rows, tags) if "R2f" in t]
    r2f_ok = all(r["family"] == "varied_teach" and qword.search(r["turn"]) and r["gold"]
                 and all(g["act"] == "TEACH" for g in r["gold"]) and "?" not in r["turn"] for r in r2f)
    check(len(r2f) >= 3 and r2f_ok, "R2 fact statements with a question word (varied_teach, TEACH): %d (>=3)" % len(r2f))

    # R3 (the verb check is tied to the frame's own subject: "I" stands for me)
    def subj_re(g):
        return r"\bI\b" if g["subject"] == "me" else r"\b" + re.escape(g["subject"]) + r"\b"

    r3 = [r for r, t in zip(rows, tags) if "R3" in t]
    r3_ok = all(r["family"] in ("varied_teach", "full_names")
                and any(g["relation"] in ("workplace", "school")
                        and re.search(r"(School|College|Club|Academy)$", g["value"], re.I) for g in r["gold"])
                for r in r3)
    teach_ok = all(g["relation"] == "workplace" for r in r3 for g in r["gold"]
                   if g["relation"] in ("workplace", "school")
                   and re.search(subj_re(g) + r"[^,.]{0,40}?\b(teach|teaches|coach|coaches)\s+(\w+\s+)?at\s+" + re.escape(g["value"]), r["turn"], re.I))
    study_ok = all(g["relation"] == "school" for r in r3 for g in r["gold"]
                   if g["relation"] in ("workplace", "school")
                   and re.search(subj_re(g) + r"[^,.]{0,40}?\bstud(y|ies)\s+at\s+" + re.escape(g["value"]), r["turn"], re.I))
    check(len(r3) >= 8 and r3_ok and teach_ok and study_ok,
          "R3 verb-decides-relation turns: %d (>=8); teach/coach->workplace, study->school" % len(r3))

    # R4
    r4_items = [r for r in rows if r["family"] in (TEACH_FAMS | {"questions"})
                and any(COMPOUND_RE.search(x) for x in rels(r))]
    r4_tag_ok = all(("R4" in t) == any(COMPOUND_RE.search(x) for x in rels(r)) for r, t in zip(rows, tags))
    check(len(r4_items) >= 8 and r4_tag_ok, "R4 compound relations in teach families + questions: %d (>=8)" % len(r4_items))

    # R5
    r5 = [r for r in rows if rels(r) & EVERYDAY]
    r5_tag_ok = all(("R5" in t) == bool(rels(r) & EVERYDAY) for r, t in zip(rows, tags))
    check(len(r5) >= 10 and r5_tag_ok, "R5 everyday relations: %d (>=10)" % len(r5))

    # R6
    r6 = [r for r in rows if r["family"] == "chain_questions" and r["gold"][0]["chain"][0] in RELATIVES]
    r6_tag_ok = all(("R6" in t) == (r in r6) for r, t in zip(rows, tags))
    check(len(r6) >= 6 and r6_tag_ok, "R6 chain questions whose first hop is a relative: %d (>=6)" % len(r6))

    # lowercase / typo
    lower_ok = all(r["turn"] == r["turn"].lower() for r, t in zip(rows, tags) if "lower" in t)
    untagged_lower = [r["id"] for r, t in zip(rows, tags) if r["turn"] == r["turn"].lower() and "lower" not in t]
    lt = [r for r, t in zip(rows, tags) if "lower" in t or "typo" in t]
    check(lower_ok and not untagged_lower and len(lt) >= 15,
          "lowercase/typo turns: %d (>=15); lower tags exact" % len(lt))
    q = [r for r in rows if r["family"] in ("questions", "chain_questions")]
    q_low = [r for r in q if r["turn"] == r["turn"].lower() or "?" not in r["turn"]]
    noq_ok = all(("noq" in t) == ("?" not in r["turn"]) for r, t in zip(rows, tags)
                 if r["family"] in ("questions", "chain_questions"))
    check(len(q_low) >= 5 and noq_ok, "lowercase or no-'?' questions: %d (>=5)" % len(q_low))
    check(len([r for r in q if "?" not in r["turn"]]) >= 1, "no-'?' questions present: %d" % len([r for r in q if "?" not in r["turn"]]))

    # clear:false carries a reason
    unclear_ok = all((not r["clear"]) == ("unclear" in t) for r, t in zip(rows, tags))
    check(unclear_ok, "clear:false exactly where notes say unclear (%d items)" % sum(not r["clear"] for r in rows))

    print("summary: R1=%d R1rel=%d R2=%d R2noq=%d R2f=%d R3=%d R4=%d R5=%d R6=%d lower/typo=%d q_lower_or_noq=%d"
          % (len(r1_main), len(r1rel), len(r2), len(r2_noq), len(r2f), len(r3), len(r4_items),
             len(r5), len(r6), len(lt), len(q_low)))


def main():
    rows, negs = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
    print("wrote %s (%d lines)" % (os.path.relpath(OUT), len(rows)))
    self_checks(rows, negs)
    if FAILS:
        print("SELF-CHECK FAILED: %d" % len(FAILS))
        sys.exit(1)
    print("ALL SELF-CHECKS PASSED")


if __name__ == "__main__":
    main()
