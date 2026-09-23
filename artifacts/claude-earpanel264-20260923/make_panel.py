#!/usr/bin/env python3
"""Blind ear panel 264 generator + self-checks.

Written blind from handoff/kit/briefs/earpanel264-spec.txt only (plus the
schema/judgement sections of the earpanel235 README). All names are invented.
Never copies any spec example word for word.

Run from the repo root with:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-earpanel264-20260923/make_panel.py

Writes panel.jsonl deterministically (family-block order, ids e264-001..150).
Exits nonzero if any self-check fails.
"""

import json
import re
import sys
from pathlib import Path

OUT_DIR = Path("artifacts/claude-earpanel264-20260923")

# One fixed alias list per relation. Pet aliases include every species word
# used in the panel turns, as the spec requires.
ALIASES = {
    "city": ["city", "town", "lives in", "residence"],
    "employer": ["employer", "company", "firm", "works for"],
    "workplace": ["workplace", "works at", "office", "site"],
    "job": ["job", "profession", "occupation", "role"],
    "boss": ["boss", "manager", "supervisor"],
    "sister": ["sister", "sib"],
    "brother": ["brother", "sib"],
    "spouse": ["spouse", "husband", "wife", "partner"],
    "husband": ["husband", "spouse", "partner"],
    "sister_in_law": ["sister_in_law", "sister-in-law", "brother's wife"],
    "language": ["language", "speaks", "tongue"],
    "hometown": ["hometown", "grew up in", "home town"],
    "place_of_birth": ["place_of_birth", "born in", "birthplace"],
    "pet": ["pet", "animal", "companion", "dog", "cat", "rabbit"],
    "school": ["school", "college", "studies at"],
    "neighbour": ["neighbour", "neighbor", "next door"],
    "cousin": ["cousin", "relative"],
    "mother": ["mother", "mum", "mom"],
    "father": ["father", "dad"],
    "stepmother": ["stepmother", "step-mother", "stepmom"],
    "stepfather": ["stepfather", "step-father", "stepdad"],
    "half_sister": ["half_sister", "half-sister", "half sister"],
    "grandmother": ["grandmother", "grandma", "granny"],
    "great_aunt": ["great_aunt", "great-aunt", "grandaunt"],
    "teacher": ["teacher", "tutor", "instructor"],
    "doctor": ["doctor", "physician", "gp"],
    "housemate": ["housemate", "roommate", "flatmate"],
    "instrument": ["instrument", "plays", "instrument played"],
    "favourite_food": ["favourite_food", "favorite food", "favourite dish"],
    "favourite_sport": ["favourite_sport", "favorite sport", "sport"],
    "hobby": ["hobby", "pastime", "interest"],
    "friend": ["friend", "mate", "pal"],
}


def T(subject, relation, value):
    return {
        "act": "TEACH",
        "subject": subject,
        "relation": relation,
        "relation_aliases": list(ALIASES[relation]),
        "value": value,
    }


def A(subject, relation, chain=None):
    if chain is None:
        return {
            "act": "ASK",
            "subject": subject,
            "relation": relation,
            "chain": None,
            "relation_aliases": list(ALIASES[relation]),
            "chain_aliases": None,
        }
    h1, h2 = chain
    return {
        "act": "ASK",
        "subject": subject,
        "relation": h2,
        "chain": [h1, h2],
        "relation_aliases": list(ALIASES[h2]),
        "chain_aliases": [list(ALIASES[h1]), list(ALIASES[h2])],
    }


# (family, turn, gold, clear, notes). notes holds comma-separated risk tags.
ITEMS = [
    # ---------------- plain_teach (25) ----------------
    ("plain_teach", "I live in Harlton.", [T("me", "city", "Harlton")], True, ""),
    ("plain_teach", "I work for Vennix Labs.", [T("me", "employer", "Vennix Labs")], True, ""),
    ("plain_teach", "I am a carpenter.", [T("me", "job", "carpenter")], True, ""),
    ("plain_teach", "Nadia teaches at Brookfield School.",
     [T("Nadia", "workplace", "Brookfield School")], True, "R3"),
    ("plain_teach", "Stellan teaches mathematics at Caundle College.",
     [T("Stellan", "workplace", "Caundle College")], True, "R3"),
    ("plain_teach", "Cora coaches swimming at Northside Club.",
     [T("Cora", "workplace", "Northside Club")], True, "R3"),
    ("plain_teach", "Joren studies engineering at Caundle College.",
     [T("Joren", "school", "Caundle College")], True, "R3"),
    ("plain_teach", "Kira studies medicine at Brookfield School.",
     [T("Kira", "school", "Brookfield School")], True, "R3"),
    ("plain_teach", "My stepmother is called Greta.",
     [T("me", "stepmother", "Greta")], True, "R4"),
    ("plain_teach", "My grandmother Ingrid lives in Dunmore.",
     [T("me", "grandmother", "Ingrid"), T("Ingrid", "city", "Dunmore")], True, "R4,R11"),
    ("plain_teach", "My housemate is called Odell.",
     [T("me", "housemate", "Odell")], True, "R5"),
    ("plain_teach", "I play the violin.",
     [T("me", "instrument", "violin")], True, "R5"),
    ("plain_teach", "My hobby is beekeeping.",
     [T("me", "hobby", "beekeeping")], True, "R5"),
    ("plain_teach", "I work with horses at Vennix Labs.",
     [T("me", "workplace", "Vennix Labs")], True, "R16"),
    ("plain_teach", "My sister-in-law is called Selma.",
     [T("me", "sister_in_law", "Selma")], True, "R16,R4"),
    ("plain_teach", "I live near Dunmore, but I work in Kellwick.",
     [T("me", "workplace", "Kellwick")], True, "R16"),
    ("plain_teach", "I used to work at Solmar Bakery, and now I work at Tibber Motors.",
     [T("me", "workplace", "Tibber Motors")], True, "R16"),
    ("plain_teach", "My sister Celia livs in Harlton.",
     [T("me", "sister", "Celia"), T("Celia", "city", "Harlton")], True, "R13,typo"),
    ("plain_teach", "My brother Milo werks at Tibber Motors.",
     [T("me", "brother", "Milo"), T("Milo", "workplace", "Tibber Motors")], True, "R13,typo"),
    ("plain_teach", "My friend Mara van Keel lives in Vennwick.",
     [T("me", "friend", "Mara van Keel"), T("Mara van Keel", "city", "Vennwick")], True, "R15,R11"),
    ("plain_teach", "my dog is called bram.",
     [T("me", "pet", "bram")], True, "R14,lower"),
    ("plain_teach", "i live in kellwick.",
     [T("me", "city", "kellwick")], True, "R14,lower"),
    ("plain_teach", "My two rabbits, Pip and Pop, live in a hutch in the garden.",
     [T("me", "pet", "Pip"), T("me", "pet", "Pop")], True, "R10"),
    ("plain_teach", "Alba's brother is Milo and he works at Tibber Motors.",
     [T("Alba", "brother", "Milo"), T("Milo", "workplace", "Tibber Motors")], True, "R12"),
    ("plain_teach", "Vera's sister is Tessa and she lives in Lunbury.",
     [T("Vera", "sister", "Tessa"), T("Tessa", "city", "Lunbury")], True, "R12"),
    # ---------------- varied_teach (30) ----------------
    ("varied_teach", "Daria's brother is Milo and he works at Tibber Motors.",
     [T("Daria", "brother", "Milo"), T("Milo", "workplace", "Tibber Motors")], True, "R1,R12"),
    ("varied_teach", "Alba's sister is Tessa and she lives in Marston.",
     [T("Alba", "sister", "Tessa"), T("Tessa", "city", "Marston")], True, "R1,R12"),
    ("varied_teach", "My cousin is Farah and she speaks Kevvish.",
     [T("me", "cousin", "Farah"), T("Farah", "language", "Kevvish")], True, "R1"),
    ("varied_teach", "My mother is Hazel and she was born in Ollerton.",
     [T("me", "mother", "Hazel"), T("Hazel", "place_of_birth", "Ollerton")], True, "R1"),
    ("varied_teach", "My father is Gideon and he lives in Tibury.",
     [T("me", "father", "Gideon"), T("Gideon", "city", "Tibury")], True, "R1"),
    ("varied_teach", "My friend is Kasper and he plays the cello.",
     [T("me", "friend", "Kasper"), T("Kasper", "instrument", "cello")], True, "R1,R5"),
    ("varied_teach", "My neighbour is Lena and she works at Esslin Books.",
     [T("me", "neighbour", "Lena"), T("Lena", "workplace", "Esslin Books")], True, "R1,R5"),
    ("varied_teach", "My boss is Otto and he lives in Esswick.",
     [T("me", "boss", "Otto"), T("Otto", "city", "Esswick")], True, "R1"),
    ("varied_teach", "Who I work for is Tibber Motors.",
     [T("me", "employer", "Tibber Motors")], True, "R2"),
    ("varied_teach", "Where I live is Harlton.",
     [T("me", "city", "Harlton")], True, "R2"),
    ("varied_teach", "What language I speak at home is Kevvish.",
     [T("me", "language", "Kevvish")], True, "R2"),
    ("varied_teach", "I live in Harlton but I plan to move to Marston.",
     [T("me", "city", "Harlton")], True, "R8"),
    ("varied_teach", "I work at Tibber Motors and I want to be a pilot.",
     [T("me", "workplace", "Tibber Motors")], True, "R8"),
    ("varied_teach", "My sisters Alba and Vera live in Harlton, though Alba is hoping to move to Kellwick.",
     [T("me", "sister", "Alba"), T("me", "sister", "Vera"),
      T("Alba", "city", "Harlton"), T("Vera", "city", "Harlton")], True, "R8,R10"),
    ("varied_teach", "My cousins Jessa and Kira work at Vennix Labs, and Jessa is training to be a vet.",
     [T("me", "cousin", "Jessa"), T("me", "cousin", "Kira"),
      T("Jessa", "workplace", "Vennix Labs"), T("Kira", "workplace", "Vennix Labs")], True, "R8,R10"),
    ("varied_teach", "My half-sister is called Nessa.",
     [T("me", "half_sister", "Nessa")], True, "R4"),
    ("varied_teach", "My teacher is called Bastian.",
     [T("me", "teacher", "Bastian")], True, "R5"),
    ("varied_teach", "My doctor is called Freya.",
     [T("me", "doctor", "Freya")], True, "R5"),
    ("varied_teach", "Lars coaches football at Eastfield Club.",
     [T("Lars", "workplace", "Eastfield Club")], True, "R3"),
    ("varied_teach", "My cousin Sadia livs in Fallows.",
     [T("me", "cousin", "Sadia"), T("Sadia", "city", "Fallows")], True, "R13,R11,typo"),
    ("varied_teach", "My friend Yusuf werks at Marlow Cycles.",
     [T("me", "friend", "Yusuf"), T("Yusuf", "workplace", "Marlow Cycles")], True, "R13,R11,typo"),
    ("varied_teach", "My neighbour Lena bron in Ollerton.",
     [T("me", "neighbour", "Lena"), T("Lena", "place_of_birth", "Ollerton")], True, "R13,R11,typo"),
    ("varied_teach", "My teacher Bastian taches at Brookfield School.",
     [T("me", "teacher", "Bastian"), T("Bastian", "workplace", "Brookfield School")], True, "R13,R11,typo"),
    ("varied_teach", "Joris de Graaf works at Vennix Labs.",
     [T("Joris de Graaf", "workplace", "Vennix Labs")], True, "R15"),
    ("varied_teach", "My friend Petra von Alden speaks Drellish.",
     [T("me", "friend", "Petra von Alden"), T("Petra von Alden", "language", "Drellish")], True, "R15"),
    ("varied_teach", "Tessa da Roon lives in Bay of Corra.",
     [T("Tessa da Roon", "city", "Bay of Corra")], True, "R15"),
    ("varied_teach", "my brother ulf lives in grimbury.",
     [T("me", "brother", "ulf"), T("ulf", "city", "grimbury")], True, "R14,lower"),
    ("varied_teach", "my cat is called mimi.",
     [T("me", "pet", "mimi")], True, "R14,lower"),
    ("varied_teach", "I drive a van with Otto Berger at Vennix Labs.",
     [T("me", "workplace", "Vennix Labs")], True, "R16"),
    ("varied_teach", "My sister-in-law is called Daria.",
     [T("me", "sister_in_law", "Daria")], True, "R16,R4"),
    # ---------------- full_names (15) ----------------
    ("full_names", "My brother is Wesley Hart and he works at Tibber Motors.",
     [T("me", "brother", "Wesley Hart"), T("Wesley Hart", "workplace", "Tibber Motors")], True, "R1"),
    ("full_names", "My sister is Vanna Cole and she lives in Lunbury.",
     [T("me", "sister", "Vanna Cole"), T("Vanna Cole", "city", "Lunbury")], True, "R1"),
    ("full_names", "My great-aunt Mabel Finch lives in Parrow.",
     [T("me", "great_aunt", "Mabel Finch"), T("Mabel Finch", "city", "Parrow")], True, "R4,R11"),
    ("full_names", "My housemate Robin Ash plays the drums.",
     [T("me", "housemate", "Robin Ash"), T("Robin Ash", "instrument", "drums")], True, "R5,R11"),
    ("full_names", "My friend Eddie Marsh livs in Dunmore.",
     [T("me", "friend", "Eddie Marsh"), T("Eddie Marsh", "city", "Dunmore")], True, "R13,R11,typo"),
    ("full_names", "My cousin June Park werks at Esslin Books.",
     [T("me", "cousin", "June Park"), T("June Park", "workplace", "Esslin Books")], True, "R13,R11,typo"),
    ("full_names", "My boss is Elka van Breem.",
     [T("me", "boss", "Elka van Breem")], True, "R15"),
    ("full_names", "Henrik von Saar teaches at Caundle College.",
     [T("Henrik von Saar", "workplace", "Caundle College")], True, "R15"),
    ("full_names", "my sister ada green lives in marston.",
     [T("me", "sister", "ada green"), T("ada green", "city", "marston")], True, "R14,lower"),
    ("full_names", "my friend sam reed works at tibber motors.",
     [T("me", "friend", "sam reed"), T("sam reed", "workplace", "tibber motors")], True, "R14,lower"),
    ("full_names", "I work alongside Otto Berger at Vennix Labs.",
     [T("me", "workplace", "Vennix Labs")], True, "R16"),
    ("full_names", "I drive for Farlow Clinics with Delia Marsh.",
     [T("me", "employer", "Farlow Clinics")], True, "R16"),
    ("full_names", "My two brothers, Carl Dean and Paul Dean, work at Marlow Cycles.",
     [T("me", "brother", "Carl Dean"), T("me", "brother", "Paul Dean"),
      T("Carl Dean", "workplace", "Marlow Cycles"), T("Paul Dean", "workplace", "Marlow Cycles")], True, "R10"),
    ("full_names", "Quentin Marsh is a baker in Sollin.",
     [T("Quentin Marsh", "job", "baker"), T("Quentin Marsh", "city", "Sollin")], True, ""),
    ("full_names", "Zelda Ray speaks Sarnic and Kevvish.",
     [T("Zelda Ray", "language", "Sarnic"), T("Zelda Ray", "language", "Kevvish")], True, ""),
    # ---------------- questions (25) ----------------
    ("questions", "Where does Celia live?", [A("Celia", "city")], True, ""),
    ("questions", "Who is Milo's boss?", [A("Milo", "boss")], True, ""),
    ("questions", "What language does Bram speak?", [A("Bram", "language")], True, ""),
    ("questions", "Who is Elka married to?", [A("Elka", "spouse")], True, ""),
    ("questions", "What does Otto do for work?", [A("Otto", "job")], False, ""),
    ("questions", "Where was Hazel born?", [A("Hazel", "place_of_birth")], True, ""),
    ("questions", "Who is Joren's teacher?", [A("Joren", "teacher")], True, "R5"),
    ("questions", "Who is Alba's doctor?", [A("Alba", "doctor")], True, "R5"),
    ("questions", "Who is Daria's stepfather?", [A("Daria", "stepfather")], True, "R4"),
    ("questions", "Where does Petra von Alden work?", [A("Petra von Alden", "workplace")], True, ""),
    ("questions", "What is Nessa's hobby?", [A("Nessa", "hobby")], True, "R5"),
    ("questions", "Who is Tessa's husband?", [A("Tessa", "husband")], True, ""),
    ("questions", "Where did Gideon grow up?", [A("Gideon", "hometown")], True, ""),
    ("questions", "What instrument does Kasper play?", [A("Kasper", "instrument")], True, ""),
    ("questions", "Who is Nadia's employer?", [A("Nadia", "employer")], True, ""),
    ("questions", "Which school does Joren attend?", [A("Joren", "school")], True, ""),
    ("questions", "Who is Lena's neighbour?", [A("Lena", "neighbour")], True, ""),
    ("questions", "What is Yusuf's favourite food?", [A("Yusuf", "favourite_food")], True, ""),
    ("questions", "What sport does Lars play?", [A("Lars", "favourite_sport")], True, ""),
    ("questions", "Who is Vera's mother?", [A("Vera", "mother")], True, ""),
    ("questions", "What is the name of Milo's cat?", [A("Milo", "pet")], True, ""),
    ("questions", "where does celia live", [A("celia", "city")], True, "lower,noq"),
    ("questions", "who is milo's boss", [A("milo", "boss")], True, "lower,noq"),
    ("questions", "what language does bram speak", [A("bram", "language")], True, "lower,noq"),
    ("questions", "where was hazel born", [A("hazel", "place_of_birth")], True, "lower,noq"),
    # ---------------- chain_questions (15) ----------------
    ("chain_questions", "Where does my sister's boss live?",
     [A("me", "city", ["sister", "city"])], True, "R6"),
    ("chain_questions", "Where does my brother work?",
     [A("me", "workplace", ["brother", "workplace"])], True, "R6"),
    ("chain_questions", "What language does my cousin speak?",
     [A("me", "language", ["cousin", "language"])], True, "R6"),
    ("chain_questions", "Who is my mother's doctor?",
     [A("me", "doctor", ["mother", "doctor"])], True, "R6"),
    ("chain_questions", "Where does my father's boss live?",
     [A("me", "city", ["father", "city"])], True, "R6"),
    ("chain_questions", "What school does my sister attend?",
     [A("me", "school", ["sister", "school"])], True, "R6"),
    ("chain_questions", "Where does my stepmother live?",
     [A("me", "city", ["stepmother", "city"])], True, "R4"),
    ("chain_questions", "Where does Celia's boss live?",
     [A("Celia", "city", ["boss", "city"])], True, ""),
    ("chain_questions", "What language does Petra's husband speak?",
     [A("Petra", "language", ["husband", "language"])], True, ""),
    ("chain_questions", "Who is Bram's mother's doctor?",
     [A("Bram", "doctor", ["mother", "doctor"])], True, ""),
    ("chain_questions", "Where does Otto's sister work?",
     [A("Otto", "workplace", ["sister", "workplace"])], True, ""),
    ("chain_questions", "What does Greta's husband do for work?",
     [A("Greta", "job", ["husband", "job"])], True, ""),
    ("chain_questions", "Where did Joren's teacher grow up?",
     [A("Joren", "hometown", ["teacher", "hometown"])], True, ""),
    ("chain_questions", "where does my sister's boss live",
     [A("me", "city", ["sister", "city"])], True, "R6,lower,noq"),
    ("chain_questions", "where does celia's boss live",
     [A("celia", "city", ["boss", "city"])], True, "lower,noq"),
    # ---------------- no_save (25) ----------------
    ("no_save", "Celia lives in Harlton, right?", [], False, "R2"),
    ("no_save", "Milo works at Tibber Motors, doesn't he?", [], False, "R2"),
    ("no_save", "So Bram speaks Kevvish?", [], False, "R2"),
    ("no_save", "So the meeting is at noon, right?", [], False, "R2"),
    ("no_save", "celia lives in harlton, right", [], False, "R2,lower,noq"),
    ("no_save", "so bram speaks kevvish", [], False, "R2,lower,noq"),
    ("no_save", "milo works at tibber motors, doesn't he", [], False, "R2,lower,noq"),
    ("no_save", "esswick is nice, isn't it", [], False, "R2,lower,noq"),
    ("no_save", "so joren studies at caundle college", [], False, "R2,lower,noq"),
    ("no_save", "I want to be a pilot one day.", [], True, "R8"),
    ("no_save", "I am training to be a vet.", [], True, "R8"),
    ("no_save", "I plan to move to Marston next spring.", [], True, "R8"),
    ("no_save", "I hope to start at Vennix Labs in June.", [], True, "R8"),
    ("no_save", "Imagine I lived in Marston.", [], True, "R9"),
    ("no_save", "Suppose my sister were a pilot.", [], True, "R9"),
    ("no_save", "Let's say my boss earns a fortune.", [], True, "R9"),
    ("no_save", "What if I spoke Drellish?", [], True, "R9"),
    ("no_save", "Pretend my cat could talk.", [], True, "R9"),
    ("no_save", "Say that I won the lottery.", [], True, "R9"),
    ("no_save", "Bastian is the best boss ever.", [], True, ""),
    ("no_save", "Apparently Kira moved to Parrow.", [], False, ""),
    ("no_save", "I used to live in Fallows.", [], False, ""),
    ("no_save", "Did you hear Tibber Motors is closing?", [], False, ""),
    ("no_save", "You would love Harlton in spring.", [], True, ""),
    ("no_save", "Joren says the boss is leaving.", [], True, ""),
    # ---------------- corrections (15) ----------------
    ("corrections", "Doran moved from Kellwick to Marston.",
     [T("Doran", "city", "Marston")], True, "correction,R17"),
    ("corrections", "My boss used to be Alba, now it is Vera.",
     [T("me", "boss", "Vera")], True, "correction,R17"),
    ("corrections", "I lived in Fallows before, but now I live in Grimbury.",
     [T("me", "city", "Grimbury")], True, "correction,R17"),
    ("corrections", "My cat was called Mimi, now she is called Pipo.",
     [T("me", "pet", "Pipo")], True, "correction,R17"),
    ("corrections", "I worked at Solmar Bakery, but I joined Tibber Motors last month.",
     [T("me", "employer", "Tibber Motors")], True, "correction,R17"),
    ("corrections", "My sister Celia lived in Harlton, but now she lives in Dunmore.",
     [T("Celia", "city", "Dunmore")], True, "correction,R17"),
    ("corrections", "Not Alba, my sister is Vera.",
     [T("me", "sister", "Vera")], True, "correction"),
    ("corrections", "Not Milo, my brother is Otto.",
     [T("me", "brother", "Otto")], True, "correction"),
    ("corrections", "I live in Harlton, not Marston.",
     [T("me", "city", "Harlton")], True, "correction"),
    ("corrections", "I work for Vennix Labs, not Tibber Motors.",
     [T("me", "employer", "Vennix Labs")], True, "correction"),
    ("corrections", "My dog is called Pip, not Pop.",
     [T("me", "pet", "Pip")], True, "correction"),
    ("corrections", "I speak Kevvish, not Drellish.",
     [T("me", "language", "Kevvish")], True, "correction"),
    ("corrections", "My boss is Vera, not Alba.",
     [T("me", "boss", "Vera")], True, "correction"),
    ("corrections", "I was born in Sollin, not Ollerton.",
     [T("me", "place_of_birth", "Sollin")], True, "correction"),
    ("corrections", "My teacher is Bastian, not Stellan.",
     [T("me", "teacher", "Bastian")], True, "correction"),
]

FAMILY_ORDER = ["plain_teach", "varied_teach", "full_names", "questions",
                "chain_questions", "no_save", "corrections"]
FAMILY_COUNTS = {"plain_teach": 25, "varied_teach": 30, "full_names": 15,
                 "questions": 25, "chain_questions": 15, "no_save": 25,
                 "corrections": 15}

TEACH_FAMS = {"plain_teach", "varied_teach", "full_names"}
QWORD = re.compile(r"\b(who|what|where|when|why|how|which|whom|whose)\b", re.I)
PRON = re.compile(r"\b(he|she|they|his|her|their|him|them)\b", re.I)
TYPO_WORDS = {"livs", "werks", "bron", "taches"}
PARTICLES = {"van", "de", "von", "da", "of", "le"}
OWNER_PRONOUNS = {"we", "us", "our", "ours", "ourselves"}
# Names/places from the earpanel235 README; must never appear here.
BANNED_NAMES = {"ana", "anya", "tomas", "tobin", "corin", "elspeth", "rin",
                "wren", "gil", "marta", "brellin", "pella", "norrish",
                "ostrish", "galvish", "orla", "ilse", "hollis", "quarrow",
                "tarrow", "fernhill", "suki", "tamsin"}
COMPOUND_RELATIONS = {"stepmother", "stepfather", "half_sister", "half_brother",
                      "mother_in_law", "father_in_law", "grandmother",
                      "grandfather", "great_aunt", "sister_in_law"}
EVERYDAY_RELATIONS = {"housemate", "instrument", "favourite_food",
                      "favourite_sport", "hobby", "teacher", "doctor", "neighbour"}
RELATIVE_HOPS = {"sister", "brother", "mother", "father", "cousin", "husband",
                 "wife", "spouse", "sister_in_law", "stepmother", "stepfather",
                 "grandmother", "grandfather", "son", "daughter"}


def tags(notes):
    return set(t for t in notes.split(",") if t)


def fail(msg):
    print("SELF-CHECK FAIL: " + msg)
    sys.exit(1)


def check():
    # Family counts and order.
    fams = [f for f, _, _, _, _ in ITEMS]
    if sorted(fams) != sorted(sum([[f] * FAMILY_COUNTS[f] for f in FAMILY_ORDER], [])):
        fail("family counts wrong: %s" % {f: fams.count(f) for f in FAMILY_ORDER})
    seen_order = []
    for f in fams:
        if not seen_order or seen_order[-1] != f:
            seen_order.append(f)
    if seen_order != FAMILY_ORDER:
        fail("items not in family-block order")

    turns = [t for _, t, _, _, _ in ITEMS]
    if len(set(turns)) != len(turns):
        fail("duplicate turn found")

    for fam, turn, gold, clear, notes in ITEMS:
        if not isinstance(turn, str) or not turn:
            fail("bad turn")
        if not isinstance(clear, bool):
            fail("clear not bool")
        if not isinstance(notes, str):
            fail("notes not str")
        toks = set(re.findall(r"[a-z]+", turn.lower()))
        if toks & OWNER_PRONOUNS:
            fail("owner pronoun in turn: %r" % turn)
        if toks & BANNED_NAMES:
            fail("banned name in turn: %r" % turn)
        for fr in gold:
            if fr["act"] == "TEACH":
                if set(fr) != {"act", "subject", "relation", "relation_aliases", "value"}:
                    fail("TEACH keys wrong: %r" % fr)
                if fr["relation_aliases"] != ALIASES[fr["relation"]]:
                    fail("alias list not fixed for %s" % fr["relation"])
                for key in ("subject", "value"):
                    if fr[key] != "me" and fr[key] not in turn:
                        fail("%s %r not word-for-word in turn %r" % (key, fr[key], turn))
            elif fr["act"] == "ASK":
                if set(fr) != {"act", "subject", "relation", "chain",
                               "relation_aliases", "chain_aliases"}:
                    fail("ASK keys wrong: %r" % fr)
                if fr["relation_aliases"] != ALIASES[fr["relation"]]:
                    fail("alias list not fixed for %s" % fr["relation"])
                if fr["subject"] != "me" and fr["subject"] not in turn:
                    fail("ASK subject not in turn %r" % turn)
                if fr["chain"] is None:
                    if fr["chain_aliases"] is not None:
                        fail("chain_aliases must be null for one hop")
                else:
                    if len(fr["chain"]) != 2 or fr["chain"][1] != fr["relation"]:
                        fail("chain/relation mismatch: %r" % fr)
                    if fr["chain_aliases"] != [ALIASES[fr["chain"][0]],
                                               ALIASES[fr["chain"][1]]]:
                        fail("chain_aliases wrong: %r" % fr)
                    if fr["chain_aliases"][1] != fr["relation_aliases"]:
                        fail("chain_aliases[1] must equal relation_aliases")
            else:
                fail("bad act")

    by = lambda tag: [(f, t, g, c, n) for f, t, g, c, n in ITEMS if tag in tags(n)]
    infam = lambda items, *fs: [x for x in items if x[0] in fs]

    # R1: >=8 across varied_teach + full_names.
    r1 = infam(by("R1"), "varied_teach", "full_names")
    if len(r1) < 8:
        fail("R1 quota: %d" % len(r1))
    for f, t, g, c, n in r1:
        if len(g) < 2 or not PRON.search(t):
            fail("R1 item lacks pronoun/two facts: %r" % t)

    # R2: >=8 in no_save with gold []; >=5 of those with no question mark;
    # plus >=3 TEACH statements with a question word in varied_teach.
    r2ns = [x for x in by("R2") if x[0] == "no_save"]
    if len(r2ns) < 8 or any(x[2] != [] for x in r2ns):
        fail("R2 no_save quota")
    if sum(1 for _, t, _, _, _ in r2ns if "?" not in t) < 5:
        fail("R2 no-question-mark quota")
    r2v = infam(by("R2"), "varied_teach")
    if len(r2v) < 3 or any(not x[2] or x[2][0]["act"] != "TEACH" or not QWORD.search(x[1])
                           for x in r2v):
        fail("R2 varied_teach quota")

    # R3: >=6 verb-decides-relation.
    r3 = by("R3")
    if len(r3) < 6:
        fail("R3 quota: %d" % len(r3))
    for f, t, g, c, n in r3:
        low = t.lower()
        ok = (g[0]["relation"] == "workplace" and ("teach" in low or "coach" in low)) or \
             (g[0]["relation"] == "school" and "stud" in low)
        if not ok:
            fail("R3 item wrong: %r" % t)

    # R4: >=6 compound family relations.
    r4 = by("R4")
    if len(r4) < 6:
        fail("R4 quota: %d" % len(r4))
    for f, t, g, c, n in r4:
        rels = [fr.get("relation") for fr in g]
        chains = [fr.get("chain", [None])[0] for fr in g if fr.get("chain")]
        if not any(r in COMPOUND_RELATIONS for r in rels + chains):
            fail("R4 item lacks compound relation: %r" % t)

    # R5: >=8 everyday relations.
    r5 = by("R5")
    if len(r5) < 8:
        fail("R5 quota: %d" % len(r5))
    for f, t, g, c, n in r5:
        if not any(fr.get("relation") in EVERYDAY_RELATIONS for fr in g):
            fail("R5 item lacks everyday relation: %r" % t)

    # R6: >=5 chain_questions with a relative first hop.
    r6 = [x for x in by("R6") if x[0] == "chain_questions"]
    if len(r6) < 5:
        fail("R6 quota: %d" % len(r6))
    for f, t, g, c, n in r6:
        if not g or g[0]["act"] != "ASK" or not g[0]["chain"] or \
                g[0]["chain"][0] not in RELATIVE_HOPS:
            fail("R6 item bad: %r" % t)

    # R8: >=3 varied_teach (plan + real fact, only fact in gold) and
    # >=3 no_save whole-turn plans with gold [].
    r8v = infam(by("R8"), "varied_teach")
    r8n = [x for x in by("R8") if x[0] == "no_save"]
    if len(r8v) < 3 or len(r8n) < 3 or any(x[2] != [] for x in r8n):
        fail("R8 quota: varied=%d no_save=%d" % (len(r8v), len(r8n)))

    # R9: >=5 pretend/hypothetical in no_save with gold [].
    r9n = [x for x in by("R9") if x[0] == "no_save"]
    if len(r9n) < 5 or any(x[2] != [] for x in r9n):
        fail("R9 quota: %d" % len(r9n))

    # R10: >=4 plural relatives, one frame per person.
    r10 = by("R10")
    if len(r10) < 4:
        fail("R10 quota: %d" % len(r10))
    for f, t, g, c, n in r10:
        teach = [fr for fr in g if fr["act"] == "TEACH"]
        if len(teach) < 2 or len({fr["value"] for fr in teach}) < 2:
            fail("R10 item needs a frame per person: %r" % t)

    # R11: >=6 appositives, relative frame plus the other fact.
    r11 = by("R11")
    if len(r11) < 6:
        fail("R11 quota: %d" % len(r11))
    for f, t, g, c, n in r11:
        if len(g) < 2:
            fail("R11 item needs two frames: %r" % t)

    # R12: >=4 pronoun-after-B items; later fact subject is B.
    r12 = by("R12")
    if len(r12) < 4:
        fail("R12 quota: %d" % len(r12))
    for f, t, g, c, n in r12:
        if len(g) < 2 or not PRON.search(t) or g[0].get("value") != g[1].get("subject"):
            fail("R12 item bad: %r" % t)

    # R13: >=8 teach items with a misspelt everyday word next to a name.
    r13 = infam(by("R13"), *TEACH_FAMS)
    if len(r13) < 8:
        fail("R13 quota: %d" % len(r13))
    for f, t, g, c, n in r13:
        if not (set(re.findall(r"[a-z]+", t.lower())) & TYPO_WORDS):
            fail("R13 item lacks typo word: %r" % t)

    # R14: >=6 all-lowercase teach items.
    r14 = infam(by("R14"), *TEACH_FAMS)
    if len(r14) < 6 or any(x[1] != x[1].lower() for x in r14):
        fail("R14 quota: %d" % len(r14))

    # R15: >=6 teach items with lowercase name particles.
    r15 = infam(by("R15"), *TEACH_FAMS)
    if len(r15) < 6:
        fail("R15 quota: %d" % len(r15))
    for f, t, g, c, n in r15:
        if not (set(re.findall(r"[a-z]+", t.lower())) & PARTICLES):
            fail("R15 item lacks particle: %r" % t)

    # R16: >=8 wrong-relation traps (teach families).
    r16 = infam(by("R16"), *TEACH_FAMS)
    if len(r16) < 8:
        fail("R16 quota: %d" % len(r16))

    # R17: >=6 corrections with stale values named outside "not X".
    r17 = [x for x in by("R17") if x[0] == "corrections"]
    if len(r17) < 6:
        fail("R17 quota: %d" % len(r17))
    for f, t, g, c, n in r17:
        if len(g) != 1:
            fail("R17 gold must be one frame: %r" % t)
        if re.search(r"\bnot\s+[A-Z]", t):
            fail("R17 item uses not-X form: %r" % t)

    # Lowercase/typo chat: >=15 turns in all.
    lt = [x for x in ITEMS if tags(x[4]) & {"lower", "typo"}]
    if len(lt) < 15:
        fail("lower/typo quota: %d" % len(lt))

    # questions + chain_questions: >=5 lowercase or no-"?" questions.
    qq = infam(ITEMS, "questions", "chain_questions")
    if sum(1 for x in qq if tags(x[4]) & {"lower", "noq"}) < 5:
        fail("question lower/noq quota")

    # Corrections hold only the new value (single TEACH frame).
    for f, t, g, c, n in infam(ITEMS, "corrections"):
        if len(g) != 1 or g[0]["act"] != "TEACH":
            fail("correction gold must be one TEACH frame: %r" % t)

    # no_save gold is always [].
    for f, t, g, c, n in infam(ITEMS, "no_save"):
        if g != []:
            fail("no_save gold must be []")

    return {
        "R1": len(r1), "R2ns": len(r2ns),
        "R2ns_noq": sum(1 for _, t, _, _, _ in r2ns if "?" not in t),
        "R2v": len(r2v), "R3": len(r3), "R4": len(r4), "R5": len(r5),
        "R6": len(r6), "R8v": len(r8v), "R8n": len(r8n), "R9": len(r9n),
        "R10": len(r10), "R11": len(r11), "R12": len(r12),
        "R13": len(r13), "R14": len(r14), "R15": len(r15),
        "R16": len(r16), "R17": len(r17), "lower_typo": len(lt),
        "q_lower_noq": sum(1 for x in qq if tags(x[4]) & {"lower", "noq"}),
        "clear_false": sum(1 for x in ITEMS if not x[3]),
    }


def main():
    counts = check()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = ["e264-%03d" % i for i in range(1, len(ITEMS) + 1)]
    with open(OUT_DIR / "panel.jsonl", "w") as fh:
        for i, (fam, turn, gold, clear, notes) in enumerate(ITEMS):
            fh.write(json.dumps({"id": ids[i], "family": fam, "turn": turn,
                                 "gold": gold, "clear": clear, "notes": notes},
                                ensure_ascii=False) + "\n")
    print("SELF-CHECKS PASSED: 150 items")
    for k in sorted(counts):
        print("  %s = %d" % (k, counts[k]))


if __name__ == "__main__":
    main()
