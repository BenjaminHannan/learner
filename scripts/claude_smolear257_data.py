#!/usr/bin/env python3
"""Exp 257 -- training data v4 for the SmolLM ear = v3 train (unchanged file, 36,000 rows)
+ new rows for the seven classes diagnosed in 235b (category level only; no panel read):
  C1 the verb decides the relation (teaches/coaches/works/lectures/is a nurse at -> employer;
     studies at / goes to / pupil at / enrolled at -> school), misleading nouns in the value
  C2 compound relatives keep their own relation (step-, half-, -in-law, great-, second cousin, god-)
  C3 pronouns in a later clause resolve to the named third person (gender taken from the
     relation word when two people are named)
  C4 corrections give ONLY the new-value frame (no old value, no extra frames; spelling notes)
  C5 statement-shaped questions without "?" -> NONE; statements containing a question word -> TEACH
  C6 everyday relations missing from table v1 (roommate, instrument, favourite food, ...) and
     plural pets ("two cats, A and B")
  C7 two-hop questions whose first hop is a relative (incl. informal words) -> canonical names
  + informal ASK forms ("who's my X again")
Every class has TRAIN templates and separate held-out DEV templates (never used in training).
Relation names = table v2 (claude_smolear257_table.py). Fictional names only.

python claude_smolear257_data.py --out DIR [--seed 257]
Writes DIR/train.jsonl (v3 train + new rows), DIR/new_train.jsonl, DIR/dev257.jsonl, DIR/counts.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_data as D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
V3_TRAIN = ROOT / "artifacts/claude-smolear235-20260922/data/train.jsonl"

# ------------------------------------------------------------ vocab
NOUNS = ["School", "Primary School", "High School", "College", "Academy", "University", "Library",
         "Hospital", "Medical Centre", "Club", "Sports Club", "Leisure Centre", "Museum", "Theatre",
         "Infirmary", "Grammar School", "Sixth Form College", "Conservatoire", "Clinic"]
INSTR = ["cello", "violin", "piano", "guitar", "drums", "flute", "trumpet", "clarinet", "harp",
         "saxophone", "ukulele", "bass guitar", "oboe", "accordion", "trombone", "banjo", "viola"]
FOOD = ["dumplings", "lasagne", "sushi", "pancakes", "curry", "paella", "tacos", "ramen",
        "fish and chips", "pizza", "risotto", "pierogi", "falafel", "roast chicken", "mac and cheese",
        "shepherd's pie", "noodles", "gumbo", "goulash"]
DRINK = ["tea", "coffee", "lemonade", "hot chocolate", "orange juice", "ginger beer", "iced tea",
         "milkshake", "cola", "mint tea", "apple juice", "cocoa"]
ANIMAL = ["otter", "fox", "owl", "penguin", "elephant", "hedgehog", "dolphin", "tiger", "giraffe",
          "badger", "red panda", "octopus"]
SEASON = ["spring", "summer", "autumn", "winter"]
SUBJECT = ["maths", "history", "art", "chemistry", "geography", "music", "biology", "French",
           "physics", "drama", "PE", "computing"]
ALLERGY = ["peanuts", "pollen", "shellfish", "dust", "penicillin", "bee stings", "gluten", "dairy",
           "cats", "strawberries", "latex"]
CARS = ["Volvo", "Toyota", "Land Rover", "blue Fiat", "Tesla", "Honda Civic", "red Mini", "Skoda",
        "camper van", "Ford Fiesta"]
OCC_AT = ["nurse", "porter", "librarian", "cook", "cleaner", "receptionist", "caretaker", "coach",
          "lab technician", "groundskeeper"]

FEM = [("sister", "sister"), ("wife", "wife"), ("mum", "mother"), ("mother", "mother"), ("aunt", "aunt"),
       ("daughter", "daughter"), ("grandma", "grandmother"), ("niece", "niece"),
       ("stepmum", "stepmother"), ("girlfriend", "partner"), ("sister-in-law", "sister_in_law"),
       ("half-sister", "half_sister"), ("godmother", "godmother"), ("great-aunt", "great_aunt")]
MASC = [("brother", "brother"), ("husband", "husband"), ("dad", "father"), ("father", "father"),
        ("uncle", "uncle"), ("son", "son"), ("grandpa", "grandfather"), ("nephew", "nephew"),
        ("stepdad", "stepfather"), ("boyfriend", "partner"), ("brother-in-law", "brother_in_law"),
        ("half-brother", "half_brother"), ("godfather", "godfather"), ("great-uncle", "great_uncle")]
NEUT = [("cousin", "cousin"), ("best friend", "best_friend"), ("boss", "boss"),
        ("neighbour", "neighbour"), ("colleague", "colleague"), ("friend", "friend"),
        ("flatmate", "roommate"), ("roommate", "roommate"), ("second cousin", "second_cousin"),
        ("classmate", "classmate"), ("teammate", "teammate"), ("partner", "partner")]

# compound / new person relations and their surface words (C2, C6)
COMPOUND = {
    "stepfather": ["stepdad", "stepfather", "step-dad", "step-father"],
    "stepmother": ["stepmum", "stepmother", "stepmom", "step-mum"],
    "stepbrother": ["stepbrother", "step-brother"], "stepsister": ["stepsister", "step-sister"],
    "stepson": ["stepson"], "stepdaughter": ["stepdaughter"],
    "half_brother": ["half-brother", "half brother"], "half_sister": ["half-sister", "half sister"],
    "mother_in_law": ["mother-in-law", "mother in law"], "father_in_law": ["father-in-law", "father in law"],
    "sister_in_law": ["sister-in-law", "sister in law"], "brother_in_law": ["brother-in-law", "brother in law"],
    "son_in_law": ["son-in-law"], "daughter_in_law": ["daughter-in-law"],
    "great_grandmother": ["great-grandmother", "great-grandma", "great-granny", "great grandmother"],
    "great_grandfather": ["great-grandfather", "great-grandpa", "great grandfather"],
    "great_aunt": ["great-aunt", "great aunt"], "great_uncle": ["great-uncle", "great uncle"],
    "second_cousin": ["second cousin"], "godmother": ["godmother"], "godfather": ["godfather"],
    "godson": ["godson"], "goddaughter": ["goddaughter"], "niece": ["niece"], "nephew": ["nephew"],
    "ex_wife": ["ex-wife"], "ex_husband": ["ex-husband"],
}
# the plain relation each compound must NOT be shortened to (contrast rows)
PLAIN_OF = {"stepfather": "father", "stepmother": "mother", "stepbrother": "brother",
            "stepsister": "sister", "stepson": "son", "stepdaughter": "daughter",
            "half_brother": "brother", "half_sister": "sister", "mother_in_law": "mother",
            "father_in_law": "father", "sister_in_law": "sister", "brother_in_law": "brother",
            "son_in_law": "son", "daughter_in_law": "daughter", "great_grandmother": "grandmother",
            "great_grandfather": "grandfather", "great_aunt": "aunt", "great_uncle": "uncle",
            "second_cousin": "cousin", "godmother": "mother", "godfather": "father",
            "godson": "son", "goddaughter": "daughter", "ex_wife": "wife", "ex_husband": "husband"}
EVERYDAY_PERSON = {
    "roommate": ["flatmate", "roommate", "housemate"], "classmate": ["classmate"],
    "teammate": ["teammate"], "tutor": ["tutor"], "landlord": ["landlord", "landlady"],
    "dentist": ["dentist"], "vet": ["vet"], "babysitter": ["babysitter", "childminder"],
    "therapist": ["therapist"], "fiance": ["fiancé", "fiancée", "fiance"],
    "partner": ["girlfriend", "gf", "boyfriend", "bf", "partner"],
}
THING = {"instrument": INSTR, "favorite_food": FOOD, "favorite_drink": DRINK,
         "favorite_animal": ANIMAL, "favorite_season": SEASON, "favorite_subject": SUBJECT,
         "favorite_sport": D.SPORT, "allergy": ALLERGY, "car": CARS}
FAV_WORD = {"favorite_food": "food", "favorite_drink": "drink", "favorite_animal": "animal",
            "favorite_season": "season", "favorite_subject": "subject", "favorite_sport": "sport",
            "favorite_book": "book", "favorite_film": "film"}
PETS_NEW = {"rabbit": "rabbit", "hamster": "hamster", "parrot": "parrot", "horse": "horse"}
# informal first-hop words for chains (C7): word -> canonical
HOP1_INFORMAL = [("hubby", "husband"), ("husband", "husband"), ("missus", "wife"), ("wife", "wife"),
                 ("mum", "mother"), ("mam", "mother"), ("mom", "mother"), ("dad", "father"),
                 ("bro", "brother"), ("brother", "brother"), ("sis", "sister"), ("sister", "sister"),
                 ("nan", "grandmother"), ("gran", "grandmother"), ("grandad", "grandfather"),
                 ("stepdad", "stepfather"), ("stepmum", "stepmother"), ("sister-in-law", "sister_in_law"),
                 ("brother-in-law", "brother_in_law"), ("flatmate", "roommate"), ("roommate", "roommate"),
                 ("gf", "partner"), ("boyfriend", "partner"), ("fiancé", "fiance"),
                 ("best friend", "best_friend"), ("boss", "boss"), ("cousin", "cousin"),
                 ("uncle", "uncle"), ("aunt", "aunt"), ("son", "son"), ("daughter", "daughter"),
                 ("half-brother", "half_brother"), ("godmother", "godmother"), ("neighbour", "neighbour")]


def T(s, rel, v):
    return f"TEACH | {s} | {rel} | {v}"


def A(s, rels):
    return f"ASK | {s} | {' > '.join(rels)}"


def art(w):
    return "an" if w[:1].lower() in "aeiou" else "a"


def cap(s):
    return s[:1].upper() + s[1:]


def pname(r, nm):
    return nm.first() if r.random() < 0.6 else nm.person()


def misleading_org(r, nm):
    k = r.random()
    base = nm.surname() if k < 0.45 else (nm.place() if k < 0.8 else r.choice(D.WORD))
    if r.random() < 0.12:
        return f"St {nm.first()}'s {r.choice(['School', 'Hospital', 'College', 'Academy'])}"
    return f"{base} {r.choice(NOUNS)}"


def gender_pick(r):
    k = r.random()
    if k < 0.45:
        w, rel = r.choice(FEM)
        return w, rel, "she"
    if k < 0.9:
        w, rel = r.choice(MASC)
        return w, rel, "he"
    w, rel = r.choice(NEUT)
    return w, rel, r.choice(["she", "he"])


# third-person verb phrases: (text, relation, value); `they` agreement via conj()
def vp(r, nm, exclude=()):
    opts = [("city", nm.place, "lives in {v}"), ("employer", nm.org, "works at {v}"),
            ("occupation", lambda: r.choice(D.OCC), "works as {a} {v}"),
            ("occupation", lambda: r.choice(D.OCC), "is {a} {v}"),
            ("language", lambda: r.choice(D.LANG), "speaks {v}"),
            ("place_of_birth", nm.place, "was born in {v}"), ("hometown", nm.place, "comes from {v}"),
            ("hometown", nm.place, "grew up in {v}"),
            ("age", lambda: str(r.randint(4, 90)), "is {v} years old"),
            ("sport", lambda: r.choice(D.SPORT), "plays {v}"),
            ("instrument", lambda: r.choice(INSTR), "plays the {v}"),
            ("dog", nm.pet, "has a dog called {v}"), ("cat", nm.pet, "has a cat named {v}"),
            ("allergy", lambda: r.choice(ALLERGY), "is allergic to {v}")]
    opts = [o for o in opts if o[0] not in exclude]
    rel, val, pat = r.choice(opts)
    v = val()
    return pat.format(v=v, a=art(v)), rel, v


CONJ = [("lives ", "live "), ("works ", "work "), ("speaks ", "speak "), ("comes ", "come "),
        ("was ", "were "), ("is ", "are "), ("has ", "have "), ("plays ", "play "), ("grew ", "grew ")]


def conj(text, pro):
    if pro != "they":
        return text
    for a, b in CONJ:
        if text.startswith(a):
            return b + text[len(a):]
    return text


# ------------------------------------------------------------ C1 verb decides the relation
C1_EMP_TRAIN = ["{n} teaches at {o}.", "{n} teaches {subj} at {o}.", "{n} coaches at {o}.",
                "{n} works at {o}.", "{n} lectures at {o}.", "{n} got a teaching job at {o}.",
                "{n} is on the staff at {o}.", "{n} teaches the kids at {o}.", "I teach at {o}.",
                "I work at {o}.", "{n} has a job at {o}.", "{n} coaches the football team at {o}."]
C1_OCC_TRAIN = ["{n} is {a} {occ} at {o}.", "{n} works as {a} {occ} at {o}.", "I'm {a} {occ} at {o}."]
C1_SCH_TRAIN = ["{n} studies at {o}.", "{n} goes to {o}.", "{n} is a pupil at {o}.",
                "{n} is a student at {o}.", "{n} is enrolled at {o}.", "{n} attends {o}.",
                "I study at {o}.", "I go to {o}.", "{n} studies {subj} at {o}."]
C1_EMP_DEV = ["{n} has been teaching at {o} for years.", "{n} is a lecturer at {o}.",
              "{n} coaches the juniors at {o}.", "{n} took a job teaching at {o}."]
C1_OCC_DEV = ["{n} is {a} {occ} on the night shift at {o}.", "{n} has worked as {a} {occ} at {o} since spring."]
C1_SCH_DEV = ["{n} is in year nine at {o}.", "{n} is doing a degree at {o}.",
              "{n} just started at {o} as a pupil.", "{n} has a place at {o} as a student."]
C1_ASK_TRAIN = [("Where does {n} teach?", "employer"), ("Which school does {n} teach at?", "employer"),
                ("Where does {n} coach?", "employer"), ("Where does {n} study?", "school"),
                ("Which college does {n} go to?", "school"), ("Where does {n} lecture?", "employer")]
C1_ASK_DEV = [("What school is {n} enrolled at?", "school"), ("Where is {n} a nurse?", "employer"),
              ("Which university does {n} teach at?", "employer")]


def c1(r, nm, dev):
    n = pname(r, nm)
    o = misleading_org(r, nm)
    k = r.random()
    subjw = r.choice(SUBJECT)
    if k < 0.18:
        pat, rel = r.choice(C1_ASK_DEV if dev else C1_ASK_TRAIN)
        return pat.format(n=n), [A(n, [rel])], "c1ask"
    if k < 0.55:
        pat = r.choice(C1_EMP_DEV if dev else C1_EMP_TRAIN)
        s = pat.format(n=n, o=o, subj=subjw)
        subj = "I" if s.startswith("I ") else n
        return s, [T(subj, "employer", o)], "c1emp"
    if k < 0.7:
        pat = r.choice(C1_OCC_DEV if dev else C1_OCC_TRAIN)
        occ = r.choice(OCC_AT)
        s = pat.format(n=n, o=o, occ=occ, a=art(occ))
        subj = "I" if s.startswith("I'm") else n
        return s, [T(subj, "occupation", occ), T(subj, "employer", o)], "c1occ"
    pat = r.choice(C1_SCH_DEV if dev else C1_SCH_TRAIN)
    s = pat.format(n=n, o=o, subj=subjw)
    subj = "I" if s.startswith("I ") else n
    return s, [T(subj, "school", o)], "c1sch"


# ------------------------------------------------------------ C2 compound relatives
C2_TRAIN = [("{X}'s {w} is {Y}.", "X"), ("My {w} is {Y}.", "My"), ("{Y} is {X}'s {w}.", "X"),
            ("{Y} is my {w}.", "my"), ("I have a {w} called {Y}.", "I"), ("{X} has a {w} named {Y}.", "X"),
            ("my {w} is {Y}", "my"), ("The name of my {w} is {Y}.", "my"),
            ("{X}'s {w} is called {Y}.", "X"), ("Meet {Y}, my {w}.", "my")]
C2_DEV = [("{Y}'s my {w}.", "my"), ("I've got a {w}, {Y}.", "I"), ("{Y} - that's {X}'s {w}.", "X"),
          ("{X}'s {w} is a lovely man called {Y}.", "X"), ("As for my {w}, {Y} is the name.", "my")]
C2_ASK_TRAIN = ["Who is {X}'s {w}?", "Who's my {w}?", "What is the name of {X}'s {w}?",
                "What's my {w} called?"]
C2_ASK_DEV = ["Can you remind me who my {w} is?", "Tell me the name of {X}'s {w}."]


def c2(r, nm, dev):
    rel = r.choice(list(COMPOUND))
    if rel in PLAIN_OF and r.random() < 0.2:  # contrast row: the plain relation, same shapes
        rel = PLAIN_OF[rel]
        w = rel.replace("_", " ")
        w = {"mother": r.choice(["mum", "mother"]), "father": r.choice(["dad", "father"])}.get(rel, w)
    else:
        w = r.choice(COMPOUND[rel])
    X, Y = nm.person(), nm.person()
    if r.random() < 0.18:
        pat = r.choice(C2_ASK_DEV if dev else C2_ASK_TRAIN)
        s = pat.format(X=X, w=w)
        subj = "my" if " my " in f" {s} " else X
        return s, [A(subj, [rel])], "c2ask"
    pat, who = r.choice(C2_DEV if dev else C2_TRAIN)
    if "lovely man" in pat and rel in ("stepmother", "stepsister", "half_sister", "mother_in_law",
                                       "sister_in_law", "daughter_in_law", "great_grandmother",
                                       "great_aunt", "godmother", "goddaughter", "niece", "ex_wife",
                                       "stepdaughter", "mother", "sister", "daughter", "grandmother", "aunt"):
        pat = pat.replace("lovely man", "lovely woman")
    s = D.an_fix(pat.format(X=X, Y=Y, w=w))
    subj = {"X": X, "My": "My", "my": "my", "I": "I"}[who]
    return s, [T(subj, rel, Y)], "c2teach"


# ------------------------------------------------------------ C3 pronouns
def _other_gender(pro):
    return "he" if pro == "she" else "she"


def c3(r, nm, dev):
    k = r.randrange(5 if dev else 7)
    n = pname(r, nm)
    relw, rel, pro = gender_pick(r)
    if r.random() < 0.12 and not dev:
        pro = "they"
    text, vrel, v = vp(r, nm)
    text = conj(text, pro)
    P = pro.capitalize()
    if dev:
        if k == 0:
            s = f"Remember {n}? {P}'s my {relw} and {pro} {text}." if pro != "they" else \
                f"Remember {n}? They're my {relw} and they {text}."
            return s, [T("my", rel, n), T(n, vrel, v)], "c3d_remember"
        if k == 1:
            return _two_people(r, nm, dev=True)
        if k == 2:
            return (f"I have a {relw} who is called {n}. {P} {text}.",
                    [T("I", rel, n), T(n, vrel, v)], "c3d_whois")
        if k == 3:
            return (f"{n} ({pro}'s my {relw}) {text}.", [T("my", rel, n), T(n, vrel, v)], "c3d_paren")
        s = f"my {relw} is {n} btw and {pro} {text}".lower()
        return s, [T("my", rel, n.lower()), T(n.lower(), vrel, v.lower())], "c3d_btw"
    if k == 0:
        return f"{n} is my {relw}. {P} {text}.", [T("my", rel, n), T(n, vrel, v)], "c3_twosent"
    if k == 1:
        t2, vrel2, v2 = vp(r, nm, exclude=(vrel,))
        return (f"My {relw} {n} {text}, and {pro} {conj(t2, pro)}.",
                [T("My", rel, n), T(n, vrel, v), T(n, vrel2, v2)], "c3_appos_and")
    if k == 2:
        t2, vrel2, v2 = vp(r, nm, exclude=(vrel,))
        return (f"{n}, my {relw}, {text}. {P} {conj(t2, pro)} too.",
                [T("my", rel, n), T(n, vrel, v), T(n, vrel2, v2)], "c3_commas_too")
    if k == 3:
        return _two_people(r, nm, dev=False)
    if k == 4:
        owner = nm.first()
        return (f"{owner}'s {relw} is called {n}. {P} {text}.",
                [T(owner, rel, n), T(n, vrel, v)], "c3_owner")
    if k == 5:
        return (f"{n} came round for dinner. {P} {text} these days.", [T(n, vrel, v)], "c3_visit")
    occ = r.choice(D.OCC)
    pro2 = {"she": "shes", "he": "hes", "they": "theyre"}[pro]
    s = f"my {relw} {n} {text} and {pro2} {art(occ)} {occ}".lower()
    return (s, [T("my", rel, n.lower()), T(n.lower(), vrel, v.lower()), T(n.lower(), "occupation", occ)],
            "c3_chat")


def _two_people(r, nm, dev):
    """Two named people of different gender; the pronoun picks one by gender."""
    g1 = r.choice(["she", "he"])
    w1, r1 = r.choice(FEM if g1 == "she" else MASC)
    SPOUSAL = ("wife", "husband", "girlfriend", "boyfriend")
    pool = [x for x in (MASC if g1 == "she" else FEM) if x[0] not in SPOUSAL]
    w2, r2 = r.choice(pool)
    g2 = _other_gender(g1)
    n1, n2 = pname(r, nm), pname(r, nm)
    while n2 == n1:
        n2 = pname(r, nm)
    target_first = r.random() < 0.4
    pro, tgt = (g1, n1) if target_first else (g2, n2)
    text, vrel, v = vp(r, nm)
    if r.random() < 0.3 and not dev:
        occ = r.choice(D.OCC)
        text, vrel, v = (f"{pro}'s {art(occ)} {occ}", "occupation", occ)
        tail = text
    else:
        tail = f"{pro} {text}"
    if dev:
        s = f"{n1} - my {w1} - has {art(w2)} {w2} named {n2}, and {tail}."
        tid = "c3d_two"
    else:
        s = f"My {w1} {n1} has {art(w2)} {w2} called {n2} and {tail}."
        tid = "c3_two"
    first = "my" if dev else "My"
    return s, [T(first, r1, n1), T(n1, r2, n2), T(tgt, vrel, v)], tid


# ------------------------------------------------------------ C4 corrections
SPELL = ["with an h at the end", "spelt with a y", "with two Ls", "with a K, not a C",
         "no e at the end", "all one word", "with a capital T", "with one n", "with a double s",
         "with an i, not an e"]
C4_TRAIN = ["Not {Z} - {S}'s {w} is {Y}.", "{S}'s {w} is {Y}, {sp}.", "I said {Z} but I meant {Y}. {S}'s {w} is {Y}.",
            "Sorry, typo - {S}'s {w} is {Y}.", "Correction: {S}'s {w} is {Y}, not {Z}.",
            "No wait, {S}'s {w} is {Y}, not {Z}.", "{S}'s {w} is {Y}. Not {Z}, {Y}.",
            "Oops, {S}'s {w} is spelled {Y}.", "Wrong name before: {S}'s {w} is {Y}."]
C4_DEV = ["Ignore the {Z} thing, {S}'s {w} is {Y}.", "Quick fix: {S}'s {w} is {Y} (I typed {Z} before).",
          "{S}'s {w} - {Y}, sorry, not {Z}.", "Let me fix that. {S}'s {w} is {Y}, {sp}."]
C4_VERB_TRAIN = {"employer": "{S} works at {Y} now, not {Z}.", "city": "{S} lives in {Y}, not {Z} - sorry.",
                 "instrument": "{S} plays the {Y}, not the {Z}."}
C4_VERB_DEV = {"employer": "Scratch {Z}: {S} is working at {Y}.", "city": "Not {Z} after all - {S} is living in {Y}."}


def c4(r, nm, dev):
    k = r.random()
    if k < 0.2:
        rel = r.choice(list(C4_VERB_DEV if dev else C4_VERB_TRAIN))
        gen = {"employer": nm.org, "city": nm.place, "instrument": lambda: r.choice(INSTR)}[rel]
        Y, Z = gen(), gen()
        while Z == Y:
            Z = gen()
        S = pname(r, nm)
        s = (C4_VERB_DEV if dev else C4_VERB_TRAIN)[rel].format(S=S, Y=Y, Z=Z)
        return s, [T(S, rel, Y)], f"c4verb_{rel}"
    pool = [x for x in MASC + FEM + NEUT]
    w, rel = r.choice(pool)
    Y, Z = pname(r, nm), pname(r, nm)
    while Z == Y:
        Z = pname(r, nm)
    fp = r.random() < 0.35
    Sw = "my" if fp else pname(r, nm)
    pat = r.choice(C4_DEV if dev else C4_TRAIN)
    s = pat.format(S=Sw, w=w, Y=Y, Z=Z, sp=r.choice(SPELL)).replace("my's", "my")
    if fp:
        s = s.replace(" my's ", " my ")
        if s.startswith("my "):
            s = "My " + s[3:]
            subj = "My"
        else:
            subj = "my"
    else:
        subj = Sw
    return s, [T(subj, rel, Y)], "c4"


# ------------------------------------------------------------ C5 statement-shaped questions
C5_NONE_TRAIN = ["{n} {t}, isn't that so", "{n} {t}, correct", "{n} {t}, no", "{n} {t}, innit",
                 "just checking {n} {t}", "{n} {t} - true or false", "you said {n} {t}, didn't you",
                 "{n} {t} or have i got that wrong", "{n} {t}... is it", "{n} {t}, am i remembering that right",
                 "{n} {t}, isn't that so?", "{n} {t} - true or false?", "you said {n} {t}, didn't you?",
                 "and {n} {t} too, did i get that right", "{n} {t} or was it someone else",
                 "did you know {n} {t}", "Did you know {n} {t}?"]
C5_NONE_DEV = ["{n} {t}, am i right", "{n} {t} yeah or nah", "{n} {t}, you reckon",
               "didn't {n} say {pro} {t}", "{n} {t}, or did i dream that"]
C5_TEACH_TRAIN = [("Want to know where {n} works? At {o}.", "employer", "o"),
                  ("Who is {n}'s {w}? That would be {m}.", "REL", "m"),
                  ("Here's where {n} lives: {p}.", "city", "p"),
                  ("You'll never guess who {n} married: {m}.", "spouse", "m"),
                  ("What does {n} do? {n} is {a} {occ}.", "occupation", "occ"),
                  ("How old is {n}? {n} is {age}.", "age", "age")]
C5_TEACH_DEV = [("Where does {n} work, you ask? {o}.", "employer", "o"),
                ("The answer to who {n}'s {w} is: {m}.", "REL", "m"),
                ("Which city does {n} live in? That's easy - {p}.", "city", "p")]


def c5(r, nm, dev):
    n = pname(r, nm)
    if r.random() < 0.72:
        text, vrel, v = vp(r, nm)
        pat = r.choice(C5_NONE_DEV if dev else C5_NONE_TRAIN)
        s = pat.format(n=n, t=text, pro=r.choice(["she", "he"]))
        if r.random() < 0.6:
            s = s.lower()
        return s, ["NONE"], "c5none"
    pat, rel, key = r.choice(C5_TEACH_DEV if dev else C5_TEACH_TRAIN)
    w, wrel, _ = gender_pick(r)
    occ = r.choice(D.OCC)
    vals = dict(o=nm.org(), m=pname(r, nm), p=nm.place(), occ=occ, lang=r.choice(D.LANG),
                age=str(r.randint(5, 90)))
    s = pat.format(n=n, w=w, a=art(occ), **vals)
    rel = wrel if rel == "REL" else rel
    return s, [T(n, rel, vals[key])], "c5teach"


# ------------------------------------------------------------ C6 table gaps
C6_PERSON_TRAIN = C2_TRAIN
C6_PERSON_DEV = C2_DEV
C6_VERB_TRAIN = {
    "roommate": ["{X} shares a flat with {Y}.", "{X} and {Y} are flatmates.", "I share a house with {Y}."],
    "instrument": ["{X} plays the {Y}.", "{X} is learning the {Y}.", "I play the {Y}.",
                   "{X}'s instrument is the {Y}."],
    "allergy": ["{X} is allergic to {Y}.", "I'm allergic to {Y}."],
    "car": ["{X} drives a {Y}.", "I drive a {Y}."],
    "fiance": ["{X} is engaged to {Y}."],
    "tutor": ["{Y} tutors {X}."],
    "landlord": ["{X} rents a flat from {Y}."],
}
C6_VERB_DEV = {
    "instrument": ["{X} has played the {Y} since childhood.", "{X} practises the {Y} every evening."],
    "allergy": ["{X} has an allergy to {Y}."],
    "roommate": ["{Y} and I share a flat."],
    "fiance": ["{X} and {Y} got engaged last month."],
}
FAV_TRAIN = ["{X}'s favourite {f} is {Y}.", "{X}'s favorite {f} is {Y}.", "My favourite {f} is {Y}.",
             "my favorite {f} is {Y}", "{X} loves {Y} more than any other {f}.",
             "{Y} is {X}'s favourite {f}."]
FAV_DEV = ["{X}'s all-time favourite {f} is {Y}.", "When it comes to {f}, {X}'s favourite is {Y}."]
PLURAL_TRAIN = ["{X} has two {p}s, {Y1} and {Y2}.", "{X} has two {p}s called {Y1} and {Y2}.",
                "I have two {p}s named {Y1} and {Y2}."]
PLURAL_DEV = ["{X}'s {p}s are {Y1} and {Y2}.", "{X} owns a pair of {p}s: {Y1} and {Y2}."]
C6_ASK_TRAIN = {"instrument": ["What instrument does {X} play?", "What does {X} play?"],
                "favorite_food": ["What's {X}'s favourite food?", "What is my favourite food?"],
                "roommate": ["Who is {X}'s flatmate?", "Who's my roommate?", "Who does {X} share a flat with?"],
                "allergy": ["What is {X} allergic to?", "What am I allergic to?"],
                "car": ["What does {X} drive?"], "favorite_drink": ["What's {X}'s favourite drink?"],
                "fiance": ["Who is {X} engaged to?"]}
C6_ASK_DEV = {"instrument": ["Which instrument does {X} play?"],
              "favorite_drink": ["Do you know what {X}'s favourite drink is?"],
              "roommate": ["Tell me who {X}'s housemate is."], "allergy": ["What's {X} allergic to?"]}


def c6(r, nm, dev):
    k = r.random()
    X = nm.person()
    if k < 0.2:  # everyday person relations
        rel = r.choice(list(EVERYDAY_PERSON))
        w = r.choice(EVERYDAY_PERSON[rel])
        Y = nm.person()
        verbs = (C6_VERB_DEV if dev else C6_VERB_TRAIN).get(rel, [])
        if verbs and r.random() < 0.5:
            pat = r.choice(verbs)
            s = pat.format(X=X, Y=Y)
            subj = "I" if (s.startswith("I ") or " and I " in s) else X
            return s, [T(subj, rel, Y)], "c6verb"
        pat, who = r.choice(C6_PERSON_DEV if dev else C6_PERSON_TRAIN)
        s = D.an_fix(pat.format(X=X, Y=Y, w=w).replace("lovely man", "lovely person"))
        subj = {"X": X, "My": "My", "my": "my", "I": "I"}[who]
        return s, [T(subj, rel, Y)], "c6person"
    if k < 0.45:  # favourites
        rel = r.choice(list(FAV_WORD))
        Y = nm.work() if rel in ("favorite_book", "favorite_film") else r.choice(THING[rel])
        pat = r.choice(FAV_DEV if dev else FAV_TRAIN)
        s = pat.format(X=X, Y=Y, f=FAV_WORD[rel])
        subj = "My" if s.startswith("My ") else ("my" if s.startswith("my ") else X)
        return s, [T(subj, rel, Y)], "c6fav"
    if k < 0.65:  # verb relations (instrument, allergy, car, ...)
        pool = C6_VERB_DEV if dev else C6_VERB_TRAIN
        rel = r.choice([x for x in pool if x in THING])
        Y = r.choice(THING[rel])
        pat = r.choice(pool[rel])
        s = D.an_fix(pat.format(X=X, Y=Y))
        subj = "I" if s.startswith(("I ", "I'm")) else X
        return s, [T(subj, rel, Y)], "c6thing"
    if k < 0.75:  # new pets + plural pets
        if r.random() < 0.5:
            p = r.choice(["cat", "dog"] + list(PETS_NEW))
            Y1, Y2 = nm.pet(), nm.pet()
            while Y2 == Y1:
                Y2 = nm.pet()
            pat = r.choice(PLURAL_DEV if dev else PLURAL_TRAIN)
            s = pat.format(X=X, p=p, Y1=Y1, Y2=Y2)
            subj = "I" if s.startswith("I ") else X
            return s, [T(subj, p, Y1), T(subj, p, Y2)], "c6plural"
        p = r.choice(list(PETS_NEW))
        Y = nm.pet()
        pats = ([f"{{X}}'s {p} is named {{Y}}.", f"{{X}} keeps {art(p)} {p} called {{Y}}."] if dev else
                [f"{{X}} has {art(p)} {p} called {{Y}}.", f"{{X}} has {art(p)} {p} named {{Y}}.",
                 f"{{X}}'s {p} is called {{Y}}.", f"I have {art(p)} {p} called {{Y}}."])
        s = r.choice(pats).format(X=X, Y=Y)
        subj = "I" if s.startswith("I ") else X
        return s, [T(subj, p, Y)], "c6pet"
    # questions about the new relations
    pool = C6_ASK_DEV if dev else C6_ASK_TRAIN
    rel = r.choice(list(pool))
    s = r.choice(pool[rel]).format(X=X)
    subj = "my" if " my " in f" {s} " else ("I" if " I " in f" {s} " else X)
    return s, [A(subj, [rel])], "c6ask"


# ------------------------------------------------------------ C7 chains with a relative first hop
C7_H2_TRAIN = [("What does {P} do for work?", "occupation"), ("Where does {P} work?", "employer"),
               ("Where did {P} grow up?", "hometown"), ("Where does {P} teach?", "employer"),
               ("What instrument does {P} play?", "instrument"), ("Who is {P} married to?", "spouse"),
               ("How old is {P}?", "age"), ("Who is {P}'s boss?", "boss"), ("Where does {P} live?", "city"),
               ("What's {P}'s favourite food?", "favorite_food"), ("Who is {P}'s flatmate?", "roommate"),
               ("what does {P} do for a living", "occupation"), ("who's {P}'s best friend", "best_friend")]
C7_H2_DEV = [("What line of work is {P} in?", "occupation"), ("Where's {P} from originally?", "hometown"),
             ("What's {P}'s dog called?", "dog"), ("Which company does {P} work for?", "employer")]


def c7(r, nm, dev):
    w1, h1 = r.choice(HOP1_INFORMAL)
    fp = r.random() < 0.6
    X = nm.person()
    P = f"my {w1}" if fp else f"{X}'s {w1}"
    pat, h2 = r.choice(C7_H2_DEV if dev else C7_H2_TRAIN)
    s = pat.replace("{P}", P)
    s = cap(s) if not pat[0].islower() else s
    subj = ("My" if s.startswith("My ") else "my") if fp else X
    return s, [A(subj, [h1, h2])], "c7"


# ------------------------------------------------------------ informal asks
INF_TRAIN = [("who's my {w} again", "my"), ("whats {X}'s {w}", "X"), ("who is {X}'s {w} again", "X"),
             ("wheres {X} from again", "X:hometown"), ("remind me {X}'s {w}", "X"),
             ("who's {X}'s {w} again?", "X"), ("what was my {w}'s name again?", "my")]
INF_DEV = [("who was my {w} again?", "my"), ("what did you say {X}'s {w} was?", "X"),
           ("sorry who's my {w} again", "my")]


def informal(r, nm, dev):
    w, rel, _ = gender_pick(r)
    X = nm.person()
    pat, who = r.choice(INF_DEV if dev else INF_TRAIN)
    s = pat.format(X=X, w=w)
    if who == "X:hometown":
        return s, [A(X, ["hometown"])], "inf"
    return s, [A("my" if who == "my" else X, [rel])], "inf"


# ------------------------------------------------------------ C8 (v4.1, added after the first dev pass)
# Dev showed three confident-error patterns: "X's my W" contraction read as a possessive (frame
# reversed), a chatty intro clause turned into a frame ("Had | colleague | X"), and "A's W is B and
# he/she ..." attaching the pronoun fact to A. Training-only rows in NEW wordings (the dev templates
# stay unused in training; the dev rows for these patterns are reported as near-distribution).
C8_CONTR = ["{Y}'s my {w}, by the way.", "Oh, {Y}'s my {w}.", "fyi {Y}'s my {w}", "{Y}'s my {w} now.",
            "Just so you know, {Y}'s my {w}.", "{Y}'s my {w}, if you didn't know.", "{Y}'s actually my {w}.",
            "Btw {Y}'s my {w}."]
C8_CONTR_PRO = ["{Y}'s my {w} and {pro} {text}.", "{Y}'s my {w}; {pro} {text}."]
C8_INTRO = ["Ran into {n} yesterday, apparently {pro} {text}.", "Met {n} at the market - {pro} {text}.",
            "Spoke to {n} this morning and {pro} {text}.", "Caught up with {n} last night; it turns out {pro} {text}.",
            "Saw {n} at the gym. {P} {text}.", "Went for coffee with {n}, and {pro} {text}.",
            "Phoned {n} earlier - turns out {pro} {text}.", "Bumped into {n} on the bus; {pro} {text}."]
C8_OWNER = ["{A}'s {w} is {B} - {pro} {text}.", "{A}'s {w} is {B}; {pro} {text}.",
            "{A}'s {w} is {B}, and {pro} {text}.", "{A}'s {w} is {B} who {text}."]


def _c8_word(r):
    k = r.random()
    if k < 0.45:
        rel = r.choice(list(COMPOUND))
        return r.choice(COMPOUND[rel]), rel
    if k < 0.75:
        w, rel, _ = gender_pick(r)
        return w, rel
    rel = r.choice(list(EVERYDAY_PERSON))
    return r.choice(EVERYDAY_PERSON[rel]), rel


def _pro_of(w):
    fem = {x[0] for x in FEM}
    masc = {x[0] for x in MASC}
    if w in fem or any(t in w for t in ("mother", "sister", "daughter", "aunt", "niece", "wife", "godmother", "mum", "landlady")):
        return "she"
    if w in masc or any(t in w for t in ("father", "brother", "son", "uncle", "nephew", "husband", "godfather", "dad")):
        return "he"
    return None


def c8(r, nm, dev):
    assert not dev
    k = r.random()
    if k < 0.45:
        w, rel = _c8_word(r)
        Y = pname(r, nm)
        pro = _pro_of(w)
        if pro and r.random() < 0.35:
            text, vrel, v = vp(r, nm)
            s = D.an_fix(r.choice(C8_CONTR_PRO).format(Y=Y, w=w, pro=pro, text=text))
            return s, [T("my", rel, Y), T(Y, vrel, v)], "c8_contr_pro"
        s = r.choice(C8_CONTR).format(Y=Y, w=w)
        return s, [T("my", rel, Y)], "c8_contr"
    if k < 0.75:
        n = pname(r, nm)
        pro = r.choice(["she", "he", "they"])
        text, vrel, v = vp(r, nm)
        text = conj(text, pro)
        s = r.choice(C8_INTRO).format(n=n, pro=pro, P=pro.capitalize(), text=text)
        return s, [T(n, vrel, v)], "c8_intro"
    while True:
        w, rel = _c8_word(r)
        pro = _pro_of(w)
        if pro:
            break
    A_, B_ = nm.first(), pname(r, nm)
    text, vrel, v = vp(r, nm)
    s = D.an_fix(r.choice(C8_OWNER).format(A=A_, w=w, B=B_, pro=pro, text=text))
    return s, [T(A_, rel, B_), T(B_, vrel, v)], "c8_owner"


CLASSES = [("C1", c1, 1300, 60), ("C2", c2, 1500, 60), ("C3", c3, 1400, 60), ("C4", c4, 900, 50),
           ("C5", c5, 1300, 70), ("C6", c6, 1900, 90), ("C7", c7, 800, 40), ("INF", informal, 300, 20),
           ("C8", c8, 1200, 0)]  # C8 = v4.1, train only


def lower_frames(s, frames):
    if s != s.lower():
        return frames
    return [fl if fl == "NONE" else " | ".join(p.lower() if j >= 1 else p for j, p in enumerate(fl.split(" | ")))
            for fl in frames]


def build(seed=257):
    r = random.Random(seed)
    nm = D.Names(r)
    train, dev, seen = [], [], set()
    v3 = [json.loads(x) for x in V3_TRAIN.read_text().splitlines() if x.strip()]
    seen.update(x["turn"] for x in v3)
    base_dev = ROOT / "artifacts/claude-smolear235b-20260922/dev/dev235b.jsonl"
    dev_turns = {json.loads(x)["turn"] for x in base_dev.read_text().splitlines() if x.strip()}
    for tag, fn, ntr, ndev in CLASSES:
        for split, n in (("dev", ndev), ("train", ntr)):
            got, tries = 0, 0
            while got < n:
                tries += 1
                assert tries < n * 50, (tag, split)
                s, frames, tid = fn(r, nm, split == "dev")
                if split == "train" and tag not in ("C5", "C4", "C7", "INF") and not s.endswith("?") \
                        and r.random() < 0.3:
                    s = D.dress(r, s)
                if s in seen or s in dev_turns:
                    continue
                seen.add(s)
                frames = lower_frames(s, frames)
                row = dict(turn=s, frames=frames, family=f"v4_{tag}", tid=f"{tag}:{tid}")
                if split == "dev":
                    row["tag"] = tag
                    dev.append(row)
                else:
                    train.append(row)
                got += 1
    return v3, train, dev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=257)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    v3, new, dev = build(a.seed)
    for i, row in enumerate(dev):
        row["id"] = f"v{i:04d}"
    (out / "new_train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in new))
    (out / "train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in v3 + new))
    (out / "dev257.jsonl").write_text("".join(json.dumps(x) + "\n" for x in dev))
    from collections import Counter
    c = dict(v3=len(v3), new=len(new), total=len(v3) + len(new), dev257=len(dev),
             new_by_class=Counter(x["family"] for x in new), dev_by_class=Counter(x["tag"] for x in dev))
    (out / "counts.json").write_text(json.dumps(c, indent=1))
    print(json.dumps(c))


if __name__ == "__main__":
    main()
