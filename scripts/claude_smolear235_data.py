#!/usr/bin/env python3
"""Exp 235 -- synthetic training data for the SmolLM ear.

Everything here is generated from (a) relation table v1 names/aliases/teach
wordings and (b) hand-written everyday paraphrases. Fictional names only.
No test panel is read. Whole templates are held out as the dev split
(template ids hashed; dev templates never appear in train).

Usage: python claude_smolear235_data.py --out DIR [--n 36000] [--seed 235]
Writes DIR/train.jsonl, DIR/dev.jsonl, DIR/templates.json (id -> split).
Each row: {"turn": str, "frames": [line, ...], "family": str, "tid": str}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path

TABLE = json.loads((Path(__file__).resolve().parent.parent /
                    "artifacts/claude-relationtable-20260922/relation_table_v1.json").read_text())
REL = {r["name"]: r for r in TABLE["relations"]}

# ------------------------------------------------------------ fictional names
ON = ["b", "br", "c", "d", "dr", "f", "g", "gr", "h", "j", "k", "l", "m", "n", "p", "qu", "r",
      "s", "sh", "t", "th", "v", "w", "z", "", "", "st", "tr", "fl", "cl"]
NU = ["a", "e", "i", "o", "u", "ae", "ia", "ou", "ai", "y", "ee", "io"]
CO = ["", "n", "r", "l", "s", "th", "x", "m", "nd", "rk", "ss", "v", "lt", "sh", "t"]
SUR_SUF = ["son", "ley", "wick", "ford", "ton", "more", "field", "well", "brook", "ridge",
           "vale", "hart", "wood", "croft", "stone", "", "", "", "er", "ing"]
PLACE_SUF = ["ton", "bury", "ford", "haven", "mouth", "wick", "field", "port", "dale", "moor",
             "stead", "holm", "gate", "burg", "ia", "a", "", ""]
PLACE_PRE = ["Port", "New", "Upper", "Lower", "East", "West", "North", "South", "Old", "Saint"]
PLACE_POST = ["Falls", "Cove", "Harbor", "Hollow", "Bay", "Springs", "Crossing", "Heights",
              "Valley", "Point", "Ridge"]
ORG_POST = ["Mills", "Works", "Labs", "Foundry", "Bakery", "Books", "Studios", "Group",
            "Company", "Co", "Guild", "Press", "Motors", "Systems", "Farms", "Clinic",
            "Library", "Academy", "Bank", "Cafe", "Records", "Shipping", "Robotics"]
WORD = ["Silver", "Copper", "Blue", "Red", "Golden", "Hollow", "Iron", "Quiet", "Amber",
        "Willow", "Maple", "Stone", "River", "Lantern", "Harbor", "Northwind", "Bright",
        "Juniper", "Cobalt", "Velvet", "Thistle", "Ember", "Frost", "Moss", "Pebble"]
NOUN = ["Lantern", "Garden", "River", "Crown", "Winter", "Orchard", "Tide", "Clock", "Mirror",
        "Road", "Sparrow", "Bridge", "Voyage", "Letters", "Song", "Harvest", "Kingdom"]
PETS = ["Rex", "Pip", "Biscuit", "Clover", "Mochi", "Pepper", "Ziggy", "Nugget", "Waffles",
        "Tofu", "Bramble", "Socks", "Juno", "Fig", "Pickle", "Mango", "Sprout", "Olive",
        "Noodle", "Button", "Maple", "Ginger", "Whiskers", "Boots"]
OCC = ["nurse", "baker", "pilot", "teacher", "carpenter", "chemist", "librarian", "dentist",
       "plumber", "farmer", "lawyer", "painter", "engineer", "firefighter", "chef", "tailor",
       "architect", "vet", "mechanic", "potter", "sailor", "journalist", "florist",
       "software developer", "bus driver", "electrician", "pharmacist", "zookeeper"]
HOBBY = ["chess", "painting", "fishing", "knitting", "hiking", "gardening", "birdwatching",
         "pottery", "juggling", "rock climbing", "baking", "origami", "cycling", "sailing",
         "photography", "stargazing", "woodworking", "swimming"]
SPORT = ["tennis", "football", "rugby", "hockey", "cricket", "volleyball", "basketball",
         "badminton", "rowing", "fencing", "golf", "baseball"]
COLOR = ["green", "blue", "red", "purple", "orange", "yellow", "teal", "silver", "maroon",
         "gold", "pink", "navy blue", "black", "white"]
LANG = ["Welsh", "Finnish", "Portuguese", "Korean", "Swahili", "Dutch", "Icelandic", "Greek",
        "Tagalog", "Basque", "Esperanto", "Norwegian", "Hungarian", "Catalan"]
GENRE = ["jazz", "folk", "blues", "punk rock", "opera", "reggae", "techno", "bluegrass"]
RELIG = ["Buddhism", "Quakerism", "Jainism", "Taoism", "Stoicism"]
POSITION = ["goalkeeper", "striker", "point guard", "pitcher", "midfielder", "catcher"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
TOYS = ["a red kite", "a wooden train", "a yo-yo", "a teddy bear", "a spinning top"]
MOODS = ["cheerful", "grumpy", "calm", "sleepy", "anxious"]
TITLES = ["Captain", "Professor", "Doctor", "Baroness", "Sergeant"]
CODES = ["blue falcon", "X-17", "tangerine", "delta nine", "red moon"]


FIRSTS = ("Mira Tobin Elsa Juno Anika Bram Cora Dax Edda Fenn Greta Hollis Ines Jory Kaia Lorne "
          "Maren Nico Odile Pax Quinn Rosa Soren Tamsin Ulla Vero Wren Yara Zeno Ada Bo Cal Dara "
          "Emil Faye Gus Hana Ivo Jem Kit Lina Milo Nell Otto Pia Rafe Sia Teo Una Vik Willa Xan "
          "Arlo Beck Cleo Dov Esme Finch Ilse Jasper Kira Lars Mabel Nils Opal Perrin Rhea Silas "
          "Thea Ulric Vesna Wynn Alma Bexley Corin Delphine Elio Fern Idris Joss Lark Moss Noor "
          "Orla Piet Rowan Saffi Tove Anouk Brisk Calla Doran Emrys Florin Hester Ione Kester").split()
SURS = ("Quill Ashgrove Brightwater Marrow Fenwick Thorne Calloway Vantree Oakhurst Pellam "
        "Rookwood Stellan Dunmore Hallow Kettering Lindqvist Mossley Nettle Orrin Pimbleby "
        "Quarrie Redfern Sallow Tamber Underhill Voss Winterbourne Yarrow Zell Amberly Birchall "
        "Coldwell Dace Eversley Farrow Gillam Harte Ivers Jessop Kell Larkspur Merriweather "
        "Nyland Ostrander Prewitt Rainer Sorrel Tully Vane Whitlock Brandt Crane Dunleavy").split()


class Names:
    def __init__(self, rng):
        self.r = rng

    def syl(self):
        return self.r.choice(ON) + self.r.choice(NU) + self.r.choice(CO)

    def first(self):
        if self.r.random() < 0.55:
            return self.r.choice(FIRSTS)
        n = self.syl() + (self.syl() if self.r.random() < 0.55 else "")
        n = re.sub(r"(.)\1\1", r"\1\1", n)
        if len(n) < 3:
            n += self.r.choice(["a", "o", "en", "is"])
        return n.capitalize()

    def surname(self):
        if self.r.random() < 0.5:
            return self.r.choice(SURS)
        return (self.syl() + self.r.choice(SUR_SUF)).capitalize()

    def person(self):
        k = self.r.random()
        if k < 0.45:
            return self.first()
        if k < 0.87:
            return f"{self.first()} {self.surname()}"
        return f"{self.first()} {self.first()} {self.surname()}"

    def pet(self):
        return self.r.choice(PETS) if self.r.random() < 0.6 else self.first()

    def place(self):
        k = self.r.random()
        base = (self.syl() + self.r.choice(PLACE_SUF)).capitalize()
        if len(base) < 4:
            base += "ra"
        if k < 0.55:
            return base
        if k < 0.75:
            return f"{self.r.choice(PLACE_PRE)} {base}"
        return f"{base} {self.r.choice(PLACE_POST)}"

    def org(self):
        k = self.r.random()
        if k < 0.5:
            return f"{self.r.choice(WORD)} {self.r.choice(ORG_POST)}"
        if k < 0.8:
            return f"{self.surname()} {self.r.choice(ORG_POST)}"
        return f"{self.r.choice(WORD)}{self.r.choice(['tech', 'soft', 'works', 'line', 'field'])}"

    def work(self):
        k = self.r.random()
        if k < 0.5:
            return f"The {self.r.choice(WORD)} {self.r.choice(NOUN)}"
        if k < 0.8:
            return f"{self.r.choice(NOUN)} of {self.place()}"
        return f"{self.r.choice(WORD)} {self.r.choice(NOUN)}"

    def date(self, year=None):
        m, d = self.r.choice(MONTHS), self.r.randint(1, 28)
        y = self.r.randint(1940, 2020)
        forms = [f"{m} {d}", f"{d} {m}", f"{m} {d}, {y}", f"{d} {m} {y}", f"{y}"]
        if year is False:
            forms = forms[:2]
        return self.r.choice(forms)


# relation -> value kind generator key
PERSON_RELS = ["mother", "father", "parent", "sister", "brother", "sibling", "spouse", "wife",
               "husband", "partner", "child", "son", "daughter", "grandchild", "grandson",
               "granddaughter", "grandmother", "grandfather", "cousin", "aunt", "uncle",
               "friend", "best_friend", "neighbour", "boss", "colleague", "teacher", "coach",
               "doctor", "mentor", "apprentice", "rival", "envoy", "herald", "keeper", "scout",
               "warden", "owner"]
COMMON_PERSON = ["mother", "father", "sister", "brother", "spouse", "wife", "husband", "friend",
                 "best_friend", "boss", "teacher", "cousin", "son", "daughter", "neighbour",
                 "grandmother", "grandfather", "aunt", "uncle", "coach", "doctor", "colleague",
                 "partner", "mentor", "child"]
PET_RELS = ["dog", "cat"]
PLACE_RELS = ["city", "hometown", "place_of_birth", "work_location", "school", "educated_at",
              "home", "country", "country_of_citizenship", "place_of_death"]
CREATOR_RELS = ["composer", "author", "painter", "director", "founder", "inventor", "designer",
                "discoverer", "architect", "creator", "developer", "performer"]
ORG_HEAD_RELS = ["chairperson", "chief_executive_officer", "head_coach", "dean"]


def value_for(rel, nm: Names):
    r = nm.r
    if rel in PERSON_RELS or rel in CREATOR_RELS or rel in ORG_HEAD_RELS or rel in (
            "head_of_state", "head_of_government", "officeholder"):
        return nm.person()
    if rel in PET_RELS:
        return nm.pet()
    if rel in PLACE_RELS or rel in ("capital", "continent", "headquarters_location",
                                    "location_of_formation", "country_of_origin"):
        return nm.place()
    if rel in ("employer", "manufacturer", "original_broadcaster"):
        return nm.org()
    if rel == "notable_work":
        return nm.work()
    return {
        "occupation": lambda: r.choice(OCC), "hobby": lambda: r.choice(HOBBY),
        "sport": lambda: r.choice(SPORT), "favorite_color": lambda: r.choice(COLOR),
        "color": lambda: r.choice(COLOR), "language": lambda: r.choice(LANG),
        "official_language": lambda: r.choice(LANG),
        "language_of_work_or_name": lambda: r.choice(LANG),
        "genre": lambda: r.choice(GENRE), "religion_or_worldview": lambda: r.choice(RELIG),
        "position_played_on_team_speciality": lambda: r.choice(POSITION),
        "age": lambda: str(r.randint(2, 97)), "birthday": lambda: nm.date(year=False),
        "anniversary": lambda: nm.date(year=False), "date_of_birth": lambda: nm.date(),
        "date_of_death": lambda: nm.date(), "nickname": lambda: nm.first(),
        "pet": lambda: r.choice(["a hamster", "a parrot", "a tortoise", "a goldfish", "a rabbit"]),
        "title": lambda: r.choice(TITLES), "code": lambda: r.choice(CODES),
        "mood": lambda: r.choice(MOODS), "toy": lambda: r.choice(TOYS),
        "training_data": lambda: r.choice(["simple English", "chat logs", "storybooks"]),
    }.get(rel, lambda: nm.first())()


def subject_for(rel, nm: Names):
    """Subject kind: works for creator relations, orgs for org relations, places."""
    if rel in CREATOR_RELS or rel in ("notable_work_of",):
        return nm.work() if rel not in ("founder",) else nm.org()
    if rel in ("manufacturer",):
        return f"the {nm.r.choice(WORD)} {nm.r.choice(['X2', 'lamp', 'bike', 'kettle', 'phone'])}" if False else nm.work()
    if rel in ORG_HEAD_RELS or rel in ("headquarters_location", "location_of_formation",
                                        "original_broadcaster"):
        return nm.org()
    if rel in ("capital", "continent", "official_language", "head_of_state",
               "head_of_government", "country_of_origin"):
        return nm.place()
    return nm.person()


def surface(rel, r):
    """A surface word for the relation: canonical (spaces) or one alias."""
    row = REL[rel]
    opts = [rel.replace("_", " ")] * 3 + list(row.get("aliases", []))
    if rel == "chief_executive_officer":
        opts = ["CEO", "chief executive", "chief executive officer"]
    if rel == "position_played_on_team_speciality":
        opts = ["position"]
    if rel == "religion_or_worldview":
        opts = ["religion"]
    if rel == "language_of_work_or_name":
        opts = ["language"]
    if rel == "country_of_citizenship":
        opts = ["nationality", "citizenship", "country of citizenship"]
    if rel == "headquarters_location":
        opts = ["headquarters", "headquarters location"]
    if rel == "educated_at":
        opts = ["alma mater"]
    if rel == "favorite_color":
        opts = ["favorite color", "favourite colour", "favourite color", "favorite colour"]
    return r.choice(opts)


# relation sampling weights (common everyday relations dominate)
def rel_weights():
    w = {}
    for r in REL:
        w[r] = 1.0
    for r in COMMON_PERSON:
        w[r] = 6.0
    for r in ["mother", "father", "sister", "brother", "friend", "boss", "spouse", "wife",
              "husband", "best_friend", "teacher"]:
        w[r] = 9.0
    for r in ["city", "hometown", "place_of_birth", "employer", "occupation", "age", "dog",
              "cat", "birthday", "date_of_birth", "favorite_color", "hobby", "language",
              "school", "nickname", "sport"]:
        w[r] = 8.0
    for r in CREATOR_RELS:
        w[r] = 3.0
    for r in ["training_data", "code", "mood", "toy", "title", "envoy", "herald", "keeper",
              "scout", "warden", "officeholder", "language_of_work_or_name"]:
        w[r] = 0.4
    return w


W = rel_weights()
RELS = list(W)


def pick_rel(r, pool=None):
    pool = pool or RELS
    return r.choices(pool, weights=[W[x] for x in pool])[0]


# ------------------------------------------------------------ templates
# Each teach template: (tid, pattern, applies(rel) -> bool). {X} subject, {Y} value, {w} word.
POSS_OK = lambda rel: True  # noqa: E731
PERSONLIKE = lambda rel: rel in PERSON_RELS or rel in PET_RELS  # noqa: E731
COUNTABLE = lambda rel: rel in ["sister", "brother", "sibling", "child", "son", "daughter",  # noqa: E731
                                "cousin", "aunt", "uncle", "friend", "neighbour", "colleague",
                                "grandchild", "grandson", "granddaughter", "dog", "cat",
                                "mentor", "rival", "apprentice"]

GENERIC_TEACH = [
    ("g_poss", "{X}'s {w} is {Y}.", POSS_OK),
    ("g_poss_nop", "{X}'s {w} is {Y}", POSS_OK),
    ("g_of", "The {w} of {X} is {Y}.", POSS_OK),
    ("g_inv", "{Y} is {X}'s {w}.", PERSONLIKE),
    ("g_inv_of", "{Y} is the {w} of {X}.", PERSONLIKE),
    ("g_called", "{X}'s {w} is called {Y}.", PERSONLIKE),
    ("g_named", "{X}'s {w} is named {Y}.", PERSONLIKE),
    ("g_hasa_named", "{X} has a {w} named {Y}.", COUNTABLE),
    ("g_hasa_called", "{X} has a {w} called {Y}.", COUNTABLE),
    ("g_name_of", "The name of {X}'s {w} is {Y}.", PERSONLIKE),
    ("g_thats", "{X}'s {w}? That's {Y}.", POSS_OK),
    ("g_poss_dash", "{X}'s {w} - {Y}.", POSS_OK),
    ("g_goesby", "{X}'s {w} goes by {Y}.", PERSONLIKE),
    ("g_poss_was", "{X}'s {w} has always been {Y}.", POSS_OK),
    ("g_meet", "Meet {Y}, {X}'s {w}.", PERSONLIKE),
    ("g_poss_happens", "{X}'s {w} happens to be {Y}.", POSS_OK),
    ("g_poss_colon", "{X}'s {w}: {Y}.", POSS_OK),
    ("g_hasa_whos", "{X} has a {w}, {Y}.", COUNTABLE),
]

VERB_TEACH = {
    "city": ["{X} lives in {Y}.", "{X} resides in {Y}.", "{X} moved to {Y}.",
             "{X} is living in {Y} these days.", "{X} lives over in {Y}.",
             "{X} has an apartment in {Y}.", "{X} lives in the town of {Y}.",
             "{X} makes {X_poss} home in {Y}.", "{X} currently lives in {Y}."],
    "hometown": ["{X} is from {Y}.", "{X} comes from {Y}.", "{X} grew up in {Y}.",
                 "{X} is originally from {Y}."],
    "place_of_birth": ["{X} was born in {Y}.", "{X} was born in the city of {Y}.",
                       "{Y} is where {X} was born."],
    "place_of_death": ["{X} died in {Y}.", "{X} passed away in {Y}."],
    "employer": ["{X} works at {Y}.", "{X} works for {Y}.", "{X} is employed by {Y}.",
                 "{X} has a job at {Y}.", "{X} got a job at {Y}.", "{X} is on staff at {Y}.",
                 "{X} works over at {Y}."],
    "occupation": ["{X} is a {Y}.", "{X} works as a {Y}.", "{X}'s job is {Y}.",
                   "{X} is employed as a {Y}.", "{X} works as an {Y}.", "{X} is an {Y}.",
                   "{X} earns a living as a {Y}.", "By profession, {X} is a {Y}."],
    "spouse": ["{X} is married to {Y}.", "{X} married {Y}."],
    "teacher": ["{Y} teaches {X}.", "{X} is taught by {Y}.", "{X} takes lessons from {Y}."],
    "boss": ["{X} reports to {Y}.", "{X} works under {Y}."],
    "age": ["{X} is {Y} years old.", "{X} is {Y}.", "{X} just turned {Y}.",
            "{X} is {Y} years of age.", "{X} turned {Y} last month."],
    "date_of_birth": ["{X} was born on {Y}.", "{X} was born in {Y}."],
    "birthday": ["{X}'s birthday is on {Y}.", "{X} celebrates {X_poss} birthday on {Y}."],
    "date_of_death": ["{X} died on {Y}.", "{X} died in {Y}."],
    "language": ["{X} speaks {Y}.", "{X} speaks fluent {Y}.", "{X}'s first language is {Y}.",
                 "{X} talks in {Y} at home."],
    "hobby": ["{X} likes {Y}.", "{X} enjoys {Y}.", "In {X_poss} free time {X} does {Y}.",
              "{X}'s favourite hobby is {Y}.", "{X} is into {Y}."],
    "sport": ["{X} plays {Y}.", "{X} plays {Y} every weekend.", "{X}'s sport is {Y}."],
    "nickname": ["{X} is called {Y}.", "{X} goes by {Y}.", "Everyone calls {X} {Y}.",
                 "{X}'s nickname is {Y}.", "Friends call {X} {Y}."],
    "school": ["{X} goes to {Y}.", "{X} attends {Y}.", "{X} is a student at {Y}."],
    "educated_at": ["{X} studied at {Y}.", "{X} graduated from {Y}.",
                    "{X} went to university at {Y}."],
    "work_location": ["{X} works in {Y}.", "{X} commutes to {Y} for work."],
    "country_of_citizenship": ["{X} is a citizen of {Y}.", "{X} holds citizenship in {Y}."],
    "dog": ["{X} has a dog named {Y}.", "{X} owns a dog called {Y}.",
            "{X} has a dog, {Y}.", "{Y} is {X}'s dog."],
    "cat": ["{X} has a cat named {Y}.", "{X} owns a cat called {Y}.", "{Y} is {X}'s cat."],
    "pet": ["{X} has {Y} as a pet.", "{X} keeps {Y} as a pet."],
    "favorite_color": ["{X} loves {Y} more than any other colour.",
                       "{X}'s favorite color is {Y}.", "{X}'s favourite colour is {Y}."],
    "friend": ["{X} is friends with {Y}.", "{X} and {Y} are friends."],
    "best_friend": ["{X}'s best friend is {Y}.", "{Y} is {X}'s best friend."],
    "sister": ["{X} has a sister, {Y}."],
    "brother": ["{X} has a brother, {Y}."],
    "doctor": ["{X} sees {Y} as {X_poss} doctor.", "{Y} is {X}'s doctor."],
    "coach": ["{Y} coaches {X}.", "{X} is coached by {Y}."],
    "mentor": ["{Y} mentors {X}.", "{X} is mentored by {Y}."],
    "neighbour": ["{X} lives next door to {Y}.", "{Y} lives next door to {X}."],
    "composer": ["{X} was composed by {Y}.", "{Y} composed {X}.", "{Y} wrote the music for {X}."],
    "author": ["{X} was written by {Y}.", "{Y} wrote {X}.", "The author of {X} is {Y}.",
               "{Y} is the author of {X}."],
    "painter": ["{X} was painted by {Y}.", "{Y} painted {X}."],
    "director": ["{X} was directed by {Y}.", "{Y} directed {X}."],
    "founder": ["{X} was founded by {Y}.", "{Y} founded {X}.", "{Y} started {X}.",
                "{Y} is the founder of {X}."],
    "inventor": ["{X} was invented by {Y}.", "{Y} invented {X}."],
    "designer": ["{X} was designed by {Y}.", "{Y} designed {X}."],
    "discoverer": ["{X} was discovered by {Y}.", "{Y} discovered {X}."],
    "architect": ["{X} was built by {Y}.", "{Y} built {X}.", "{Y} designed the building {X}."],
    "creator": ["{X} was created by {Y}.", "{Y} created {X}.", "{Y} made {X}."],
    "developer": ["{X} was developed by {Y}.", "{Y} developed {X}."],
    "performer": ["{X} was performed by {Y}.", "{Y} performed {X}.", "{Y} sings {X}."],
    "manufacturer": ["{X} is made by {Y}.", "The company that produced {X} is {Y}.",
                     "{Y} manufactures {X}."],
    "headquarters_location": ["{X} is based in {Y}.", "{X} has its headquarters in {Y}.",
                              "The headquarters of {X} is in {Y}."],
    "capital": ["The capital of {X} is {Y}.", "{Y} is the capital of {X}."],
    "chief_executive_officer": ["{Y} is the CEO of {X}.", "{Y} runs {X} as chief executive."],
    "chairperson": ["{Y} chairs {X}.", "The chairperson of {X} is {Y}."],
    "head_coach": ["{Y} is the head coach of {X}.", "The head coach of {X} is {Y}."],
    "official_language": ["The official language of {X} is {Y}."],
    "continent": ["{X} is located in the continent of {Y}.", "{X} is on the continent of {Y}."],
    "location_of_formation": ["{X} was founded in the city of {Y}."],
    "original_broadcaster": ["{X} first aired on {Y}.", "The original broadcaster of {X} is {Y}."],
    "notable_work": ["{X} is famous for {Y}.", "{X} is best known for {Y}."],
    "genre": ["{X} plays {Y} music.", "The type of music that {X} plays is {Y}."],
    "religion_or_worldview": ["{X} follows {Y}.", "{X} practises {Y}."],
    "position_played_on_team_speciality": ["{X} plays as a {Y}.", "{X} plays the position of {Y}."],
    "head_of_state": ["The head of state of {X} is {Y}."],
    "head_of_government": ["The head of the government of {X} is {Y}."],
    "country_of_origin": ["{X} was created in the country of {Y}."],
    "wife": ["{Y} is married to {X}; she is {X}'s wife."],
    "husband": ["{X} is married to {Y}, her husband."],
}
# Table teach wordings (verbatim from relation table v1) are added as extra templates.
for rname, row in REL.items():
    for t in row.get("teach", []):
        pat = t["t"]
        if "(" in pat:
            pat = re.sub(r"\((\w+)\|[^)]*\)", r"\1", pat)
        if not pat.endswith("."):
            pat += "."
        VERB_TEACH.setdefault(rname, [])
        if pat not in VERB_TEACH[rname]:
            VERB_TEACH[rname].append(pat)

FIRST_PERSON_TEACH = [
    ("fp_my", "My {w} is {Y}.", POSS_OK, "My"),
    ("fp_my_nop", "my {w} is {Y}", POSS_OK, "my"),
    ("fp_my_called", "My {w} is called {Y}.", PERSONLIKE, "My"),
    ("fp_ihave", "I have a {w} named {Y}.", COUNTABLE, "I"),
]
FIRST_PERSON_VERB = {
    "city": ["I live in {Y}.", "I moved to {Y}."], "hometown": ["I'm from {Y}.", "I am from {Y}."],
    "employer": ["I work at {Y}.", "I work for {Y}."], "occupation": ["I am a {Y}.", "I work as a {Y}."],
    "age": ["I am {Y} years old.", "I'm {Y} years old."], "place_of_birth": ["I was born in {Y}."],
    "language": ["I speak {Y}."], "sport": ["I play {Y}."], "school": ["I go to {Y}."],
    "spouse": ["I am married to {Y}.", "I'm married to {Y}."],
    "dog": ["I have a dog named {Y}."], "cat": ["I have a cat called {Y}."],
}

PREFIX = ["", "", "", "", "", "Hey, ", "Oh, ", "By the way, ", "So, ", "Okay so ", "Fun fact: ",
          "Just so you know, ", "FYI, ", "Remember this: ", "Please remember that ",
          "Note that ", "Quick thing: ", "Heads up, ", "Also, ", "Btw ", "Good to know: ",
          "Something new: ", "Here's a fact: ", "You should know that ", "Hi! "]
SUFFIX = ["", "", "", "", " :)", " Thanks!", " btw", " Got it?", " Just so you know.",
          " Please remember that.", " Okay?", "!"]

# held-out whole templates: deterministic by hash
def is_dev(tid):
    return int(hashlib.sha1(tid.encode()).hexdigest(), 16) % 100 < 14


# ------------------------------------------------------------ builders
def fill(pat, X, Y, w, poss="their"):
    return (pat.replace("{X_poss}", poss).replace("{X}", X).replace("{Y}", Y)
            .replace("{w}", w))


def an_fix(s):
    s = re.sub(r"\ba ([aeiouAEIOU])", r"an \1", s)
    s = re.sub(r"\ban ([^aeiouAEIOU\s])", r"a \1", s)
    return s


def dress(r, s, allow_prefix=True):
    if allow_prefix:
        p = r.choice(PREFIX)
        if p and p.endswith(" ") and not p.endswith(": ") and s[:1].isupper() and not s.startswith(("I ", "I'm")):
            # keep names capitalised; lower only the first word if it's not a name/"I"
            first = s.split(" ", 1)[0]
            if first in ("The", "My", "Meet", "Everyone", "Friends", "In", "By"):
                s = first.lower() + s[len(first):]
        s = p + s
        s = s + r.choice(SUFFIX) if s.endswith(".") and r.random() < 0.3 else s
    k = r.random()
    if k < 0.08:
        s = s.lower()
    elif k < 0.16:
        s = s.rstrip(".!")
    return s


def teach_one(r, nm, rel=None, first_person=False, want_tid=None):
    """Returns (sentence, frame_line, tid, subject, value, rel)."""
    for _ in range(50):
        rel = rel or pick_rel(r)
        if first_person:
            opts = [(t[0], t[1], t[2], t[3]) for t in FIRST_PERSON_TEACH if t[2](rel)]
            opts += [(f"fpv_{rel}_{i}", p, None, p.split(" ", 1)[0].replace("'m", ""))
                     for i, p in enumerate(FIRST_PERSON_VERB.get(rel, []))]
            if rel in CREATOR_RELS or rel in ORG_HEAD_RELS or not opts:
                rel = None
                continue
            tid, pat, _, subj = r.choice(opts)
            if subj == "I'm":
                subj = "I"
        else:
            opts = [(t[0], t[1]) for t in GENERIC_TEACH if t[2](rel)]
            opts += [(f"v_{rel}_{i}", p) for i, p in enumerate(VERB_TEACH.get(rel, []))]
            if rel in CREATOR_RELS or rel in ORG_HEAD_RELS or rel in ("capital", "manufacturer",
                                                                      "headquarters_location"):
                # verb forms dominate for work/org relations
                vb = [(f"v_{rel}_{i}", p) for i, p in enumerate(VERB_TEACH.get(rel, []))]
                if vb and r.random() < 0.7:
                    opts = vb
            tid, pat = r.choice(opts)
            subj = subject_for(rel, nm)
        if want_tid is not None and want_tid(tid) is False:
            rel = None
            continue
        w = surface(rel, r)
        Y = value_for(rel, nm)
        if Y == subj:
            continue
        s = an_fix(fill(pat, subj, Y, w, r.choice(["their", "his", "her"])))
        s = s[0].upper() + s[1:]
        return s, f"TEACH | {subj} | {rel} | {Y}", tid, subj, Y, rel
    raise RuntimeError("no template")


ASK_GENERIC = [
    ("a_who", "{WH} is {X}'s {w}?"), ("a_whats", "What's {X}'s {w}?"),
    ("a_whos", "Who's {X}'s {w}?"), ("a_of", "{WH} is the {w} of {X}?"),
    ("a_know", "Do you know {X}'s {w}?"), ("a_tell", "Can you tell me {X}'s {w}?"),
    ("a_remind", "Remind me, {WHl} is {X}'s {w}?"), ("a_tellme", "Tell me {X}'s {w}."),
    ("a_name", "What is the name of {X}'s {w}?"), ("a_called", "What is {X}'s {w} called?"),
    ("a_nop", "{WHl} is {X}'s {w}"), ("a_any", "Any idea {WHl} {X}'s {w} is?"),
    ("a_yn2", "Is {X}'s {w} {Y}?"),
    ("a_whatwas", "What was {X}'s {w} again?"), ("a_recall", "Do you remember {X}'s {w}?"),
]
ASK_VERB = {
    "city": ["Where does {X} live?", "Which city does {X} live in?", "What town does {X} live in?",
             "Where is {X} living now?"],
    "hometown": ["Where is {X} from?", "Where does {X} come from?"],
    "place_of_birth": ["Where was {X} born?"],
    "employer": ["Where does {X} work?", "Who does {X} work for?", "Which company employs {X}?"],
    "occupation": ["What does {X} do for a living?", "What is {X}'s job?", "What's {X}'s job?"],
    "age": ["How old is {X}?", "What age is {X}?"],
    "date_of_birth": ["When was {X} born?"],
    "birthday": ["When is {X}'s birthday?"],
    "language": ["What language does {X} speak?", "Which language does {X} speak?"],
    "spouse": ["Who is {X} married to?"],
    "teacher": ["Who teaches {X}?"],
    "boss": ["Who does {X} report to?"],
    "sport": ["What sport does {X} play?"],
    "hobby": ["What does {X} like to do?", "What is {X}'s hobby?"],
    "school": ["Where does {X} go to school?"],
    "nickname": ["What is {X}'s nickname?", "What do people call {X}?"],
    "author": ["Who wrote {X}?"], "composer": ["Who composed {X}?"], "painter": ["Who painted {X}?"],
    "director": ["Who directed {X}?"], "founder": ["Who founded {X}?", "Who started {X}?"],
    "inventor": ["Who invented {X}?"], "designer": ["Who designed {X}?"],
    "creator": ["Who created {X}?", "Who made {X}?"], "developer": ["Who developed {X}?"],
    "architect": ["Who built {X}?"], "discoverer": ["Who discovered {X}?"],
    "performer": ["Who performed {X}?"],
    "manufacturer": ["Who makes {X}?", "Which company made {X}?"],
    "headquarters_location": ["Where is {X} based?", "Where are {X}'s headquarters?"],
    "capital": ["What is the capital of {X}?"],
    "dog": ["What is {X}'s dog called?", "What's the name of {X}'s dog?"],
    "cat": ["What is {X}'s cat called?"],
    "favorite_color": ["What colour does {X} like best?"],
    "chief_executive_officer": ["Who runs {X}?", "Who is the CEO of {X}?"],
}
FP_ASK = [("fa_my", "{WH} is my {w}?", "my"), ("fa_whats", "What's my {w}?", "my"),
          ("fa_remind", "Remind me who my {w} is.", "my")]
FP_ASK_VERB = {"city": [("Where do I live?", "I")], "employer": [("Where do I work?", "I")],
               "age": [("How old am I?", "I")], "hometown": [("Where am I from?", "I")],
               "occupation": [("What is my job?", "my")]}


def wh_for(rel):
    k = REL[rel]["value_kind"]
    if k == "person":
        return "Who"
    if k == "place":
        return "Where" if rel in ("city", "hometown", "place_of_birth", "home") else "What"
    if k == "date":
        return "When"
    return "What"


def ask_one(r, nm, rel=None, first_person=False):
    rel = rel or pick_rel(r)
    if first_person and rel not in CREATOR_RELS and rel not in ORG_HEAD_RELS:
        opts = [(t[0], t[1], t[2]) for t in FP_ASK]
        opts += [(f"fav_{rel}_{i}", p, s) for i, (p, s) in enumerate(FP_ASK_VERB.get(rel, []))]
        tid, pat, subj = r.choice(opts)
        w = surface(rel, r)
        s = pat.replace("{WH}", wh_for(rel)).replace("{w}", w)
        if subj == "my" and s.startswith("My"):
            subj = "My"
        return s, f"ASK | {subj} | {rel}", tid
    opts = list(ASK_GENERIC)
    opts += [(f"av_{rel}_{i}", p) for i, p in enumerate(ASK_VERB.get(rel, []))]
    for t in REL[rel].get("ask", []):
        p = re.sub(r"\((\w+)\|[^)]*\)", r"\1", t["t"])
        if "{Y}" not in p:
            opts.append((f"at_{rel}_{p[:18]}", p if p.endswith("?") else p + "?"))
    if rel in CREATOR_RELS or rel in ("manufacturer", "capital", "headquarters_location") or \
            rel in ORG_HEAD_RELS:
        vb = [o for o in opts if o[0].startswith(("av_", "at_"))]
        if vb and r.random() < 0.7:
            opts = vb
    tid, pat = r.choice(opts)
    X = subject_for(rel, nm)
    Y = value_for(rel, nm)
    wh = wh_for(rel)
    s = (pat.replace("{WHl}", wh.lower()).replace("{WH}", wh).replace("{X}", X)
         .replace("{Y}", Y).replace("{w}", surface(rel, r)))
    s = an_fix(s)
    s = s[0].upper() + s[1:]
    return s, f"ASK | {X} | {rel}", tid


# chain questions: first hop is a person relation (or a creator relation for works)
CHAIN_GENERIC = [
    ("c_poss2", "{WH} is {X}'s {w1}'s {w2}?"), ("c_of", "{WH} is the {w2} of {X}'s {w1}?"),
    ("c_whats", "What's {X}'s {w1}'s {w2}?"), ("c_ofof", "{WH} is the {w2} of the {w1} of {X}?"),
    ("c_know", "Do you know {X}'s {w1}'s {w2}?"), ("c_tell", "Tell me the {w2} of {X}'s {w1}."),
    ("c_name", "What is the name of {X}'s {w1}'s {w2}?"),
]
CHAIN_VERB2 = {  # second-hop verb forms applied to "{X}'s {w1}"
    "city": ["Where does {P} live?", "Which city does {P} live in?"],
    "employer": ["Where does {P} work?", "Who does {P} work for?"],
    "occupation": ["What does {P} do for a living?", "What is {P}'s job?"],
    "age": ["How old is {P}?"], "place_of_birth": ["Where was {P} born?"],
    "hometown": ["Where is {P} from?"], "language": ["What language does {P} speak?"],
    "spouse": ["Who is {P} married to?"], "date_of_birth": ["When was {P} born?"],
    "birthday": ["When is {P}'s birthday?"], "sport": ["What sport does {P} play?"],
}
HOP1 = [r for r in COMMON_PERSON]
HOP2 = COMMON_PERSON + ["city", "employer", "occupation", "age", "place_of_birth", "hometown",
                        "language", "dog", "cat", "birthday", "favorite_color", "nickname",
                        "hobby", "school"]


def chain_one(r, nm, first_person=False):
    k = r.random()
    if k < 0.12:  # work -> creator -> x
        c = r.choice(["author", "composer", "painter", "director", "founder", "creator"])
        rel2 = r.choice(["city", "employer", "hometown", "place_of_birth", "mother", "spouse", "age"])
        X = nm.work() if c != "founder" else nm.org()
        P = f"the {surface(c, r)} of {X}"
        if rel2 in CHAIN_VERB2 and r.random() < 0.6:
            pat = r.choice(CHAIN_VERB2[rel2])
            s = pat.replace("{P}'s", P + "'s").replace("{P}", P)
            tid = f"cw_{rel2}"
        else:
            s = f"{wh_for(rel2)} is the {surface(rel2, r)} of {P}?"
            tid = "cw_of"
        s = s[0].upper() + s[1:]
        return s, f"ASK | {X} | {c} > {rel2}", tid
    n = 3 if r.random() < 0.15 else 2
    rels = [r.choice(HOP1)]
    for _ in range(n - 1):
        rels.append(r.choice(HOP1 if len(rels) < n - 1 else HOP2))
    ws = [surface(x, r) for x in rels]
    X = "my" if first_person else nm.person()
    head = ("My" if first_person else X)
    if n == 3:
        tid = r.choice(["c3_poss", "c3_of"])
        if tid == "c3_poss":
            s = f"{wh_for(rels[-1])} is {'my' if first_person else X + chr(39) + 's'} {ws[0]}'s {ws[1]}'s {ws[2]}?"
        else:
            s = f"{wh_for(rels[-1])} is the {ws[2]} of {'my' if first_person else X + chr(39) + 's'} {ws[0]}'s {ws[1]}?"
        subj = "my" if first_person else X
        return s, f"ASK | {subj} | {' > '.join(rels)}", tid
    P = f"{'my' if first_person else X + chr(39) + 's'} {ws[0]}"
    if rels[1] in CHAIN_VERB2 and r.random() < 0.5:
        i = r.randrange(len(CHAIN_VERB2[rels[1]]))
        s = CHAIN_VERB2[rels[1]][i].replace("{P}", P)
        tid = f"cv_{rels[1]}_{i}"
    else:
        tid, pat = r.choice(CHAIN_GENERIC)
        if first_person:
            pat = pat.replace("{X}'s", "my").replace("of {X}", "of me")
            if tid == "c_ofof":
                return chain_one(r, nm, first_person)
        s = (pat.replace("{WH}", wh_for(rels[1])).replace("{X}", X).replace("{w1}", ws[0])
             .replace("{w2}", ws[1]))
    s = s[0].upper() + s[1:]
    subj = "my" if first_person else X
    if first_person and s.startswith("My"):
        subj = "My"
    return s, f"ASK | {subj} | {' > '.join(rels)}", tid


# ------------------------------------------------------------ NONE turns
HEDGE = ["I think {s}", "Maybe {s}", "I'm not sure, but {s}", "Probably {s}", "I guess {s}",
         "It's possible that {s}", "I believe {s}", "Perhaps {s}", "I might be wrong but {s}",
         "Not 100% sure, but {s}", "I suspect {s}", "Possibly {s}", "If I remember right, {s}",
         "I could be mistaken, but {s}"]
HEDGE_INNER = ["{X}'s {w} might be {Y}.", "{X}'s {w} could be {Y}.", "{X} may live in {P}.",
               "{X}'s {w} is probably {Y}.", "{X} might work at {O}.", "{X}'s {w} is maybe {Y}?"]
HEARSAY = ["Someone told me {s}", "I heard that {s}", "Apparently {s}", "Rumor has it {s}",
           "People say {s}", "{Z} says {s}", "According to {Z}, {s}", "{Z} told me {s}",
           "I read somewhere that {s}", "They say {s}", "Word is {s}", "{Z} claims {s}",
           "I overheard that {s}", "Supposedly {s}"]
NEG = ["{X}'s {w} is not {Y}.", "{X}'s {w} isn't {Y}.", "{Y} is not {X}'s {w}.",
       "{X} doesn't live in {P}.", "{X} does not work at {O}.", "{X} has never been to {P}.",
       "{X} has no {w}.", "{X} doesn't have a {w}.", "{X} never worked for {O}.",
       "{X} is not a {J}.", "{X} isn't from {P}.", "{X} was not born in {P}.",
       "{Y} was never {X}'s {w}.", "{X} doesn't speak {L}."]
HYPO = ["If {X}'s {w} were {Y}, that would be funny.", "Suppose {X} lives in {P}.",
        "Imagine {X}'s {w} is {Y}.", "What if {X} worked at {O}?",
        "Let's pretend {X}'s {w} is {Y}.", "Say {X}'s {w} was {Y}.",
        "Hypothetically, {X}'s {w} is {Y}.", "In my story, {X}'s {w} is {Y}.",
        "If {X} moved to {P}, would that change anything?", "Pretend {X} is a {J}.",
        "Assume {X}'s {w} is {Y} for this game.", "In the novel I'm writing, {X} lives in {P}."]
FUTURE = ["{X} wants to move to {P}.", "{X} might move to {P} next year.",
          "{X} hopes to work at {O} someday.", "{X} will marry {Y} next spring.",
          "{X} is thinking about moving to {P}.", "{X} used to live in {P}.",
          "{X} would like to be a {J}.", "{X} dreams of visiting {P}.",
          "{X} plans to learn {L}.", "{X} wishes {X_poss} {w} were {Y}.",
          "{X} used to work at {O}.", "{X} is going to visit {P} tomorrow."]
SMALL = ["Hi!", "Hello there.", "Good morning!", "How are you?", "Thanks!", "Thank you so much.",
         "lol", "ok", "okay", "That's cool.", "Nice.", "What's your name?", "Who made you?",
         "Nice weather today.", "I'm tired.", "Bye!", "See you later.", "Good night.", "Hmm.",
         "Haha, that's funny.", "What can you do?", "Are you a robot?", "How's it going?",
         "I'm bored.", "Sounds good.", "Wow.", "No worries.", "Yes.", "No.", "Sure thing.",
         "Tell me about yourself.", "How old are you?", "Do you like music?", "I'm back.",
         "That makes sense.", "Interesting!", "Good job.", "What time is it?",
         "Is it going to rain today?", "Let's chat.", "I had a long day.", "Hey!",
         "What do you think about that?", "Cool, thanks.", "Never mind.", "Oops.", "Yay!",
         "Are you there?", "I'm feeling great today.", "Can we talk?"]
REQUEST = ["Can you tell me a joke?", "Please summarize this for me.", "Set a timer for five minutes.",
           "Help me write an email to {X}.", "Remind me to call {X} tomorrow.",
           "Could you look up the weather in {P}?", "Write a poem about {P}.",
           "Can you help me plan a trip to {P}?", "Please be quiet for a bit.",
           "Translate this into {L}.", "Make a shopping list for me.",
           "Can you recommend a good book?", "Please send {X} a message.",
           "Could you spell {X}'s name for me?", "Tell me a story about a dragon.",
           "Count to ten.", "Let's play a game.", "Forget what I said.",
           "Say something nice to {X}.", "Can you draw a cat?"]
OPINION = ["{X}'s {w} is really nice.", "I love {P}.", "{P} is a beautiful city.",
           "{X} is so funny.", "I think {X} is great.", "{X}'s cooking is amazing.",
           "{O} makes terrible coffee.", "{X} is tall.", "{X} is very kind.",
           "{X}'s {w} is annoying.", "{X} seems happy today.", "{X} is smart.",
           "I don't like {P} much.", "{X} went to the market.", "{X} is running late.",
           "{X} and I had lunch.", "{X} looks tired.", "{X}'s new haircut is great.",
           "I miss {X}.", "{X} called me yesterday.", "{O} is the best place ever.",
           "{X}'s {w} is a wonderful person.", "{X} laughed at my joke.",
           "It's raining in {P}.", "{X} is on holiday.", "{X} bought a new car."]


def none_one(r, nm):
    k = r.random()
    X, Y = nm.person(), nm.person()
    rel = r.choice(COMMON_PERSON)
    w = surface(rel, r)
    P, O, Z = nm.place(), nm.org(), nm.person()
    J, L = r.choice(OCC), r.choice(LANG)
    def sub(t):
        return an_fix(t.replace("{X_poss}", r.choice(["his", "her", "their"])).replace("{X}", X)
                      .replace("{Y}", Y).replace("{w}", w).replace("{P}", P).replace("{O}", O)
                      .replace("{Z}", Z).replace("{J}", J).replace("{L}", L))
    if k < 0.17:
        i = r.randrange(len(HEDGE))
        inner = r.choice(HEDGE_INNER + ["{X}'s {w} is {Y}.", "{X} lives in {P}.", "{X} works at {O}."])
        inner = sub(inner)
        s = HEDGE[i].replace("{s}", inner[0].lower() + inner[1:] if inner.startswith(("The", "My")) else inner)
        return s, f"n_hedge_{i}", "hedge"
    if k < 0.34:
        i = r.randrange(len(HEARSAY))
        inner = sub(r.choice(["{X}'s {w} is {Y}.", "{X} lives in {P}.", "{X} works at {O}.",
                              "{X} is a {J}.", "{X} was born in {P}.", "{X} speaks {L}."]))
        return sub(HEARSAY[i]).replace("{s}", inner), f"n_hear_{i}", "hearsay"
    if k < 0.48:
        i = r.randrange(len(NEG))
        return sub(NEG[i]), f"n_neg_{i}", "negation"
    if k < 0.58:
        i = r.randrange(len(HYPO))
        return sub(HYPO[i]), f"n_hypo_{i}", "hypothetical"
    if k < 0.66:
        i = r.randrange(len(FUTURE))
        return sub(FUTURE[i]), f"n_fut_{i}", "future_past"
    if k < 0.78:
        i = r.randrange(len(SMALL))
        return SMALL[i], f"n_small_{i % 10}", "smalltalk"
    if k < 0.88:
        i = r.randrange(len(REQUEST))
        return sub(REQUEST[i]), f"n_req_{i}", "request"
    i = r.randrange(len(OPINION))
    return sub(OPINION[i]), f"n_op_{i}", "opinion"


CORR_PRE = ["Actually, ", "Sorry, I meant ", "Correction: ", "Wait, no - ", "I was wrong earlier, ",
            "Let me correct that: ", "Oops, ", "Update: ", "Scratch that, ", "No, ",
            "My mistake, ", "Sorry, ", "Hold on, ", "I misspoke. ", "Change that: "]
CORR_FORMS = ["{X}'s {w} is {Y}, not {Z}.", "{X}'s {w} isn't {Z}, it's {Y}.",
              "{X}'s {w} is actually {Y}.", "{X}'s {w} is {Y}.", "It's {Y}, not {Z}: {X}'s {w} is {Y}.",
              "{X}'s {w} is not {Z} but {Y}.", "{X}'s {w} is really {Y}, not {Z}."]
CORR_VERB = {
    "city": ["{X} lives in {Y}, not {Z}.", "{X} doesn't live in {Z} anymore, {X} lives in {Y} now.",
             "{X} lives in {Y} now.", "{X} moved from {Z} to {Y}."],
    "employer": ["{X} works at {Y}, not {Z}.", "{X} works for {Y} now."],
    "age": ["{X} is {Y}, not {Z}.", "{X} is actually {Y} years old."],
    "occupation": ["{X} is a {Y}, not a {Z}."],
}


def correction_one(r, nm):
    rel = pick_rel(r, COMMON_PERSON + ["city", "employer", "age", "occupation", "dog", "hometown",
                                       "favorite_color", "birthday", "nickname"])
    X = nm.person()
    Y, Z = value_for(rel, nm), value_for(rel, nm)
    while Z == Y:
        Z = value_for(rel, nm)
    w = surface(rel, r)
    forms = [(f"k_{i}", p) for i, p in enumerate(CORR_FORMS)]
    forms += [(f"kv_{rel}_{i}", p) for i, p in enumerate(CORR_VERB.get(rel, []))]
    tid, pat = r.choice(forms)
    pi = r.randrange(len(CORR_PRE))
    body = an_fix(pat.replace("{X}", X).replace("{Y}", Y).replace("{Z}", Z).replace("{w}", w))
    s = CORR_PRE[pi] + body
    return dress(r, s, allow_prefix=False), [f"TEACH | {X} | {rel} | {Y}"], f"{tid}+p{pi % 5}"


def multi_one(r, nm, dev_ok):
    k = r.random()
    if k < 0.35:  # two independent facts, same subject with pronoun
        X = nm.person()
        r1, r2 = r.sample([x for x in COMMON_PERSON + ["city", "employer", "occupation", "age", "dog"]], 2)
        Y1, Y2 = value_for(r1, nm), value_for(r2, nm)
        w1, w2 = surface(r1, r), surface(r2, r)
        pr = r.choice(["his", "her", "their"])
        def clause(rel, w, Y, first):
            subj = X if first else pr.replace("their", "they").replace("his", "he").replace("her", "she")
            if rel == "city":
                return f"{subj} lives in {Y}"
            if rel == "employer":
                return f"{subj} works at {Y}"
            if rel == "occupation":
                return an_fix(f"{subj} is a {Y}").replace("they is", "they are")
            if rel == "age":
                return f"{subj} is {Y} years old".replace("they is", "they are")
            return f"{X}'s {w} is {Y}" if first else f"{pr} {w} is {Y}"
        joiner = r.choice([" and ", ", and ", ". ", "; "])
        c2 = clause(r2, w2, Y2, False)
        if joiner == ". ":
            c2 = c2[0].upper() + c2[1:]
        s = clause(r1, w1, Y1, True) + joiner + c2 + "."
        return s, [f"TEACH | {X} | {r1} | {Y1}", f"TEACH | {X} | {r2} | {Y2}"], "m_pron"
    if k < 0.65:  # two full teach sentences (maybe different subjects)
        parts, frames, tids = [], [], []
        for _ in range(2 if r.random() < 0.8 else 3):
            s, f, tid, *_ = teach_one(r, nm, want_tid=lambda t: dev_ok(t))
            parts.append(s.rstrip(".") + ".")
            frames.append(f)
            tids.append(tid)
        return " ".join(parts), frames, "m_seq"
    if k < 0.82:  # chained teach: X's mother is A. A lives in P.
        X, A = nm.person(), nm.person()
        rel = r.choice(COMMON_PERSON)
        P = nm.place()
        v = r.choice([f"{A} lives in {P}.", f"She lives in {P}.", f"{A}'s city is {P}."])
        subj2 = A
        s = f"{X}'s {surface(rel, r)} is {A}. {v}"
        if v.startswith("She"):
            # pronoun without a copyable name for subject -> only the first fact is safe
            return s, [f"TEACH | {X} | {rel} | {A}"], "m_chain_pron"
        return s, [f"TEACH | {X} | {rel} | {A}", f"TEACH | {subj2} | city | {P}"], "m_chain"
    # teach + question
    s1, f1, *_ = teach_one(r, nm, want_tid=lambda t: dev_ok(t))
    s2, f2, _ = ask_one(r, nm)
    return s1.rstrip(".") + ". " + s2, [f1, f2], "m_teach_ask"


# --- v3 additions (pilot probe on my own sentences showed these shapes misread)
NESTED_NONE = ["{X}'s {w} lives in {P}.", "{X}'s {w} works at {O}.", "{X}'s {w} works as a {J}.",
               "{X}'s {w} is a {J}.", "{X}'s {w} is {N} years old.", "{X}'s {w} speaks {L}.",
               "{X}'s {w} was a {J}.", "{X}'s {w} comes from {P}.", "My {w} works as a {J}.",
               "My {w} lives in {P}."]
WHOSE = ["Whose {w} is {Y}?", "Who has {Y} as their {w}?", "Who is {Y} the {w} of?"]


def nested_none(r, nm):
    X = nm.person()
    w = surface(r.choice(COMMON_PERSON), r)
    i = r.randrange(len(NESTED_NONE))
    s = an_fix(NESTED_NONE[i].replace("{X}", X).replace("{w}", w).replace("{P}", nm.place())
               .replace("{O}", nm.org()).replace("{J}", r.choice(OCC))
               .replace("{N}", str(r.randint(3, 90))).replace("{L}", r.choice(LANG)))
    return s, f"nn_{i}"


def whose_none(r, nm):
    i = r.randrange(len(WHOSE))
    rel = r.choice(COMMON_PERSON + ["dog", "cat"])
    Y = nm.pet() if rel in PET_RELS else nm.person()
    return WHOSE[i].replace("{w}", surface(rel, r)).replace("{Y}", Y), f"wh_{i}"


APPOS = [("ap_comma", "{H} {w}, {Y}, {V}."), ("ap_bare", "{H} {w} {Y} {V}."),
         ("ap_dash", "{H} {w} - {Y} - {V}.")]
APPOS_V = {"city": "lives in {P}", "employer": "works at {O}", "occupation": "is a {J}",
           "age": "is {N}", "hometown": "is from {P}"}


def appos_one(r, nm):
    rel = r.choice(COMMON_PERSON)
    fp = r.random() < 0.35
    X = "My" if fp else nm.person()
    H = "My" if fp else f"{X}'s"
    Y = nm.person()
    r2 = r.choice(list(APPOS_V))
    val = {"city": nm.place, "hometown": nm.place, "employer": nm.org,
           "occupation": lambda: r.choice(OCC), "age": lambda: str(r.randint(3, 95))}[r2]()
    V = APPOS_V[r2].replace("{P}", val).replace("{O}", val).replace("{J}", val).replace("{N}", val)
    tid, pat = r.choice(APPOS)
    s = an_fix(pat.replace("{H}", H).replace("{w}", surface(rel, r)).replace("{Y}", Y).replace("{V}", V))
    return s, [f"TEACH | {X} | {rel} | {Y}", f"TEACH | {Y} | {r2} | {val}"], tid


def build(n, seed):
    r = random.Random(seed)
    nm = Names(r)
    rows = {"train": [], "dev": []}
    mix = [("teach", 0.34), ("teach_fp", 0.05), ("ask", 0.14), ("ask_fp", 0.02),
           ("chain", 0.09), ("none", 0.24), ("correction", 0.06), ("multi", 0.06),
           ("nested_none", 0.025), ("whose_none", 0.006), ("appos", 0.025)]
    fams, wts = zip(*mix)
    tids = {}
    while len(rows["train"]) < n:
        fam = r.choices(fams, weights=wts)[0]
        if fam in ("teach", "teach_fp"):
            s, f, tid, *_ = teach_one(r, nm, first_person=(fam == "teach_fp"))
            s, frames = dress(r, s), [f]
        elif fam in ("ask", "ask_fp"):
            s, f, tid = ask_one(r, nm, first_person=(fam == "ask_fp"))
            if r.random() < 0.15:
                s = r.choice(["Hey, ", "Quick question: ", "So ", "Hmm, ", "Okay, "]) + s[0].lower() + s[1:] \
                    if not s.startswith(("My", "What's my")) or True else s
            if r.random() < 0.08:
                s = s.lower()
            if r.random() < 0.1:
                s = s.rstrip("?")
            frames = [f]
        elif fam == "chain":
            s, f, tid = chain_one(r, nm, first_person=r.random() < 0.08)
            if r.random() < 0.08:
                s = s.lower()
            frames = [f]
        elif fam == "none":
            s, tid, _sub = none_one(r, nm)
            if r.random() < 0.08:
                s = s.lower()
            frames = ["NONE"]
        elif fam == "correction":
            s, frames, tid = correction_one(r, nm)
        elif fam == "nested_none":
            s, tid = nested_none(r, nm)
            frames = ["NONE"]
        elif fam == "whose_none":
            s, tid = whose_none(r, nm)
            frames = ["NONE"]
        elif fam == "appos":
            s, frames, tid = appos_one(r, nm)
        else:
            s, frames, tid = multi_one(r, nm, lambda t: not is_dev(t))
        split = "dev" if (is_dev(tid) and fam != "multi") else "train"
        tids[tid] = split
        # names lowercased? keep subject spans consistent with the turn text
        if s == s.lower():
            frames = [fl if fl == "NONE" else " | ".join([p if j in (0, 2) else p.lower()
                                                          for j, p in enumerate(fl.split(" | "))])
                      for fl in frames]
        rows[split].append({"turn": s, "frames": frames, "family": fam, "tid": tid})
    return rows, tids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=36000)
    ap.add_argument("--seed", type=int, default=235)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, tids = build(a.n, a.seed)
    rows["dev"] = rows["dev"][:3000]
    for k in ("train", "dev"):
        with open(out / f"{k}.jsonl", "w") as f:
            for x in rows[k]:
                f.write(json.dumps(x) + "\n")
    (out / "templates.json").write_text(json.dumps(tids, indent=0, sort_keys=True))
    print({k: len(v) for k, v in rows.items()}, "templates", len(tids),
          "dev templates", sum(1 for v in tids.values() if v == "dev"))


if __name__ == "__main__":
    main()
