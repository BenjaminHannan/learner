#!/usr/bin/env python3
"""Exp 237: build relation_table_v1_1.json = table v1 (read-only) + additions.

Writes artifacts/claude-table237-20260922/relation_table_v1_1.json.
Every addition is listed in the "v1_1_additions" block of the output.
v1 is never edited.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "artifacts/claude-relationtable-20260922/relation_table_v1.json"
OUT = ROOT / "artifacts/claude-table237-20260922/relation_table_v1_1.json"
SRC = "NEW in v1.1 (exp 237)"

t = json.loads(V1.read_text(encoding="utf-8"))
t = copy.deepcopy(t)
t["version"] = "v1.1"
t["based_on"] = "relation_table_v1.json (unchanged; this file = v1 + additions)"
rels = {r["name"]: r for r in t["relations"]}
log = []

DATE_GUARD = rels["birthday"]["value_guard"]
DATE_RULE = rels["birthday"]["date_rule"]
PERSON_GEN = ["possessive", "my", "of_form", "inverted", "reverse"]


def p(tmpl):
    return {"t": tmpl, "where": "NEW", "src": SRC}


def add_alias(rel, *als):
    for a in als:
        if a not in rels[rel]["aliases"]:
            rels[rel]["aliases"].append(a)
            k = "_".join(a.lower().split())
            if k not in rels[rel]["storage_keys"]:
                rels[rel]["storage_keys"].append(k)
    log.append(f"alias {rel}: +{list(als)}")


def add_storage(rel, *keys):
    for k in keys:
        if k not in rels[rel]["storage_keys"]:
            rels[rel]["storage_keys"].append(k)
    log.append(f"storage key {rel}: +{list(keys)}")


def add_ask(rel, *tmpls, kind="ask"):
    for s in tmpls:
        rels[rel][kind].append(p(s))
    log.append(f"{kind} template {rel}: +{list(tmpls)}")


def new_rel(name, aliases=(), wh=("Who", "What"), card="single",
            vk="person", ask=(), inverse=(), storage=(), narrower=(),
            date=False, broader=()):
    r = {"name": name, "aliases": list(aliases),
         "storage_keys": [name] + [s for s in storage if s != name]
         + ["_".join(a.lower().split()) for a in aliases],
         "inverse_storage_keys": [], "generic": list(PERSON_GEN),
         "wh": list(wh), "cardinality": card, "narrower": list(narrower),
         "value_kind": vk, "status": "NEW", "src": SRC,
         "teach": [], "ask": [p(s) for s in ask],
         "inverse": [p(s) for s in inverse], "yesno": [],
         "yesno_can_say_no": False}
    if broader:
        r["broader"] = list(broader)
    if date:
        r["value_guard"] = DATE_GUARD
        r["date_rule"] = DATE_RULE
        r["wh"] = ["When", "What"]
    # dedupe storage keys, keep order
    seen = []
    for k in r["storage_keys"]:
        if k not in seen:
            seen.append(k)
    r["storage_keys"] = seen
    t["relations"].append(r)
    rels[name] = r
    log.append(f"new relation {name} (aliases {list(aliases)})")


# ---- 1. true-synonym aliases on existing rows -------------------------
add_alias("boss", "supervisor", "line manager")
add_alias("doctor", "physician", "GP", "family doctor")
add_alias("language", "languages")
add_alias("city", "residence", "place of residence", "city lived in")
add_storage("city", "home")          # 'home' row kept; its key is read by city
add_alias("occupation", "line of work")
add_alias("neighbour", "next-door neighbour", "next-door neighbor")
# spouse <-> wife / husband: one-way links both ways, never wife <-> husband
for n in ("wife", "husband"):
    rels[n]["broader"] = ["spouse"]
log.append("broader: wife -> spouse, husband -> spouse (spouse already "
           "lists them as narrower); wife and husband are never linked")
# native language / mother tongue / first language: one relation,
# narrower of language (a native language is a language X speaks).
new_rel("native_language", aliases=["mother tongue", "first language",
                                    "native tongue"],
        wh=["What"], vk="language", broader=[],
        ask=["What is {X}'s native language?"])
rels["language"]["narrower"].append("native_language")
log.append("narrower: language -> native_language")

# ---- 2. new everyday relation rows ------------------------------------
new_rel("landlord",
        ask=["Who does {X} rent from?"], inverse=["Who rents from {Y}?"])
new_rel("dentist")
new_rel("vet", aliases=["veterinarian"])
new_rel("tutor", ask=["Who tutors {X}?"], inverse=["Who does {Y} tutor?"])
new_rel("mayor", ask=["Who is mayor of {X}?"])
new_rel("lawyer", aliases=["attorney"])
new_rel("accountant")
new_rel("therapist")
new_rel("nurse")
new_rel("babysitter", aliases=["baby sitter"])
new_rel("nanny")
new_rel("barber")
new_rel("roommate", aliases=["flatmate", "room mate", "housemate"],
        card="multi")
new_rel("classmate", card="multi")
new_rel("teammate", card="multi")
new_rel("girlfriend")
new_rel("boyfriend")
new_rel("fiance", aliases=["fiancé"])
new_rel("principal", aliases=["headteacher", "head teacher"])
new_rel("captain")
new_rel("pastor")
new_rel("pharmacist")
new_rel("mechanic")
new_rel("plumber")
new_rel("stepmother", aliases=["stepmom", "stepmum"])
new_rel("stepfather", aliases=["stepdad"])
new_rel("niece", card="multi")
new_rel("nephew", card="multi")
new_rel("godmother")
new_rel("godfather")
new_rel("favorite_food", aliases=["favourite food"], wh=["What"],
        vk="literal")
new_rel("favorite_book", aliases=["favourite book"], wh=["What"],
        vk="work")
new_rel("favorite_song", aliases=["favourite song"], wh=["What"],
        vk="work")
new_rel("favorite_animal", aliases=["favourite animal"], wh=["What"],
        vk="literal")
new_rel("car", wh=["What"], vk="literal")
new_rel("address", wh=["What", "Where"], vk="literal")
new_rel("phone_number", aliases=["phone number"], wh=["What"],
        vk="literal")
new_rel("email", aliases=["email address"], wh=["What"], vk="literal")
new_rel("street", wh=["What", "Where"], vk="place")
new_rel("bank", wh=["What", "Where"], vk="organization")
new_rel("team", wh=["What", "Which"], vk="organization",
        ask=["What team does {X} play for?"],
        inverse=["Who plays for {Y}?"])
new_rel("club", wh=["What", "Which"], vk="organization")
new_rel("instrument", wh=["What"], vk="literal",
        ask=["What instrument does {X} play?"])
new_rel("major", wh=["What"], vk="literal",
        ask=["What does {X} study?"])
# templates on existing rows
add_ask("owner", "Who owns {X}?")
add_ask("coach", "Who coaches {X}?", "Who trains {X}?")
add_ask("language", "What language does {X} speak?",
        "What languages does {X} speak?", "What language do I speak?",
        "What languages do I speak?")
add_ask("employer", "Where do I work?", "Who do I work for?")
add_ask("city", "Where do I live?")
add_ask("author", "Which books did {Y} write?", "What books did {Y} write?",
        kind="inverse")

# ---- 3. date relations --------------------------------------------------
new_rel("date_founded", aliases=["founding date", "founding year",
                                 "year founded", "date founded",
                                 "foundation date"],
        storage=["founded", "founded_in", "founding"], wh=["When", "What"],
        vk="date", date=True,
        ask=["When was {X} founded?", "What year was {X} founded?",
             "When was {X} established?", "When was {X} set up?"])
new_rel("opening_date", aliases=["opening year", "date opened",
                                 "year opened"],
        storage=["opened", "opened_in"], vk="date", date=True,
        ask=["When was {X} opened?", "When did {X} open?",
             "What year did {X} open?"])
new_rel("graduation_date", aliases=["graduation year", "graduation",
                                    "year of graduation"],
        storage=["graduated", "graduated_in"], vk="date", date=True,
        ask=["When did {X} graduate?", "What year did {X} graduate?",
             "When did I graduate?"])
new_rel("wedding_anniversary", vk="date", date=True)
rels["anniversary"]["narrower"].append("wedding_anniversary")
log.append("narrower: anniversary -> wedding_anniversary")
add_ask("birthday", "When's {X}'s birthday?", "When was {X}'s birthday?",
        "When's my birthday?", "When is my birthday again?")
add_ask("anniversary", "When's {X}'s anniversary?", "When is my anniversary?")

# ---- 4. generic contractions / name-of forms ---------------------------
g = t["generic_patterns"]
g["possessive"]["ask"] += [p("Who's {X}'s {R}?"), p("When's {X}'s {R}?"),
                           p("What is the name of {X}'s {R}?"),
                           p("What's the name of {X}'s {R}?"),
                           p("When is {X}'s {R}?"), p("When was {X}'s {R}?")]
g["my"]["ask"] += [p("Who's my {R}?"), p("What's my {R}?"),
                   p("When's my {R}?"), p("When is my {R}?"),
                   p("What is my {R}'s name?"), p("What's my {R}'s name?"),
                   p("What is the name of my {R}?")]
g["of_form"]["ask"] += [p("Who's the {R} of {X}?"),
                        p("When was the {R} of {X}?")]
log.append("generic asks: Who's/What's/When's contractions, "
           "'the name of X's R', 'my R's name', 'When is/was X's R'")

t["v1_1_additions"] = log
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"wrote {OUT} relations={len(t['relations'])} additions={len(log)}")
