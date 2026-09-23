#!/usr/bin/env python3
"""Exp 270 dev set: the builder's own casual turns and traps (no panels).

Deterministic generator. All names fictional, all wording the builder's own.
Families: casual_teach (50), casual_q (15, setup + question), lower_trap
(25, expect no save), clean (30, byte-identical check vs 263).

Writes a JSON list of cases:
  {id, family, setup[], turn, followup, expect_store[[s,r,v]], gold, nosave}
Usage: python -B scripts/claude_type270_devset.py <out.json>
"""
import json
import sys

PEOPLE = ["Belmara", "Corvin", "Tilda", "Jesper", "Linnea", "Marisol",
          "Oswick", "Pellin", "Sorrel", "Tamber", "Wexford", "Ysolde"]
PLACES = ["Drennor", "Halloway", "Fenmere", "Norbury", "Eskdale"]
JOBS = ["fisher", "baker", "mason", "weaver", "carter"]
RELS = ["mother", "boss", "brother", "friend", "father", "sister"]


def teach(n, rel, v):
    return f"{n}s {rel} is {v}.", [[n, rel, v]]


def main(out):
    cases = []

    def add(fam, setup, turn, followup, expect, gold, nosave=False):
        cases.append({"id": f"d270-{len(cases) + 1:03d}", "family": fam,
                      "setup": setup, "turn": turn, "followup": followup,
                      "expect_store": expect, "gold": gold, "nosave": nosave})

    # casual_teach 1-10: possessive, no apostrophe
    for i in range(10):
        n, rel = PEOPLE[i % 12], RELS[i % 6]
        v = JOBS[i % 5] if rel in ("job", "boss") else PEOPLE[(i + 5) % 12]
        t, e = teach(n.lower(), rel, v.lower() if v in JOBS else v)
        add("casual_teach", [], t, f"Who is {n}'s {rel}?", e, v)
    # 11-18: possessive with apostrophe, all lowercase
    for i in range(8):
        n, rel = PEOPLE[(i + 3) % 12], RELS[(i + 2) % 6]
        v = PEOPLE[(i + 7) % 12]
        add("casual_teach", [], f"{n.lower()}'s {rel} is {v}.",
            f"Who is {n}'s {rel}?", [[n, rel, v]], v)
    # 19-26: verb live, lowercase slots
    for i in range(8):
        n, p = PEOPLE[(i + 1) % 12], PLACES[i % 5]
        add("casual_teach", [], f"{n.lower()} lives in {p.lower()}.",
            f"Where does {n} live?", [[n, "city", p]], p)
    # 27-32: verb work, lowercase slots
    for i in range(6):
        n, p = PEOPLE[(i + 6) % 12], PLACES[(i + 2) % 5]
        add("casual_teach", [], f"{n.lower()} works at {p.lower()}.",
            f"Where does {n} work?", [[n, "employer", p]], p)
    # 33-38: my-shapes, lowercase
    for i in range(6):
        rel = RELS[i % 6]
        v = JOBS[i % 5] if rel in ("job", "boss") else PEOPLE[(i + 4) % 12]
        add("casual_teach", [], f"my {rel} is {v.lower() if v in JOBS else v}.",
            f"Who is my {rel}?", [["USER", rel, v]], v)
    # 39-46: opener-led casual teaches
    openers = ["hey", "yo,", "so", "well,", "oh,", "btw,", "listen,",
               "look,"]
    for i, op in enumerate(openers):
        n, rel = PEOPLE[(i + 8) % 12], RELS[(i + 1) % 6]
        v = PEOPLE[(i + 2) % 12]
        t, e = teach(n.lower(), rel, v)
        add("casual_teach", [], f"{op} {t}",
            f"Who is {n}'s {rel}?", e, v)
    # 47-48: s-ending names
    add("casual_teach", [], "morris mother is belmara.",
        "Who is Morris's mother?", [["Morris", "mother", "Belmara"]],
        "Belmara")
    add("casual_teach", [], "tess boss is corvin.",
        "Who is Tess's boss?", [["Tess", "boss", "Corvin"]], "Corvin")
    # 49-50: misc casual
    add("casual_teach", [], "yes, tildas brother is jesper.",
        "Who is Tilda's brother?", [["Tilda", "brother", "Jesper"]],
        "Jesper")
    add("casual_teach", [], "marisols friend is linnea.",
        "Who is Marisol's friend?", [["Marisol", "friend", "Linnea"]],
        "Linnea")
    add("casual_teach", [], "belmaras name is wren.",
        "What is Belmara's name?", [["Belmara", "name", "Wren"]],
        "Wren")

    # casual_q: setup clean, lowercase question
    qset = [
        ("Belmara", "mother", "Tilda", "who is belmaras mother?",
         "Tilda"),
        ("Corvin", "boss", "Jesper", "who is corvins boss?", "Jesper"),
        ("Linnea", "brother", "Oswick", "who is linneas brother?",
         "Oswick"),
        ("Marisol", "friend", "Tilda", "what is marisols friend?",
         "Tilda"),
        ("Oswick", "sister", "Ysolde", "who's oswicks sister?", "Ysolde"),
        ("Pellin", "father", "Wexford", "whos pellins father?", "Wexford"),
        ("Sorrel", "mother", "Belmara", "whats sorrels mother?",
         "Belmara"),
        ("Tamber", "boss", "Corvin", "who is tamber's boss?", "Corvin"),
        ("Ysolde", "friend", "Linnea", "who is ysoldes friend?",
         "Linnea"),
        ("Jesper", "city", "Drennor", "where does jesper live?",
         "Drennor"),
        ("Tilda", "sister", "Marisol", "who is tilda's sister?",
         "Marisol"),
        ("Wexford", "father", "Oswick", "whos wexfords father?",
         "Oswick"),
        ("Belmara", "job", "baker", "what is belmaras job?", "baker"),
        ("Corvin", "mother", "Sorrel", "who is corvins mother",
         "Sorrel"),
        ("Linnea", "boss", "Tamber", "wheres linneas boss?", "Tamber"),
        ("Belmara", "name", "Wren", "what is belmaras name?", "Wren"),
    ]
    for n, rel, v, q, gold in qset:
        if rel == "city":
            setup = [f"{n} lives in {v}."]
        else:
            setup = [f"{n}'s {rel} is {v}."]
        add("casual_q", setup, q, "", [[n, rel, v]], gold)

    # lower_trap: expect no save
    traps = [
        "lets say belmaras mother is tilda.",
        "suppose corvin lives in drennor.",
        "imagine jespers boss is pellin.",
        "what if linneas brother is oswick?",
        "lets pretend marisol lives in norbury.",
        "i want belmaras mother to be tilda.",
        "corvin will live in drennor.",
        "tildas brother will be jesper.",
        "i am training to be baker.",
        "jesper is going to be mason.",
        "belmaras mother is tilda, right.",
        "so corvins boss is jesper.",
        "linneas brother is oswick, isn't it.",
        "marisols friend is tilda, don't you think.",
        "oswicks sister is ysolde, yeah.",
        "pellins father is wexford, correct.",
        "does tilda live in drennor.",
        "is belmaras mother tilda.",
        "do you know corvin.",
        "belmaras mother is not tilda.",
        "corvin does not live in drennor.",
        "belmaras mother is tilda and she lives in drennor.",
        "jespers boss is pellin and he works at fenmere.",
        "tildas brother used to be jesper.",
        "my boss was corvin.",
    ]
    for t in traps:
        add("lower_trap", [], t, "", [], "")

    # clean: byte-identical check
    cleans = [
        ("Belmara's mother is Tilda.", "Who is Belmara's mother?",
         [["Belmara", "mother", "Tilda"]], "Tilda"),
        ("Quillan lives in Drennor.", "Where does Quillan live?",
         [["Quillan", "city", "Drennor"]], "Drennor"),
        ("My job is fisher.", "What is my job?",
         [["USER", "job", "fisher"]], "fisher"),
        ("Hey, Belmara's boss is Corvin.", "Who is Belmara's boss?",
         [["Belmara", "boss", "Corvin"]], "Corvin"),
        ("So, Tilda lives in Norbury.", "Where does Tilda live?",
         [["Tilda", "city", "Norbury"]], "Norbury"),
        ("Wexford's father is Oswick.", "Who is Wexford's father?",
         [["Wexford", "father", "Oswick"]], "Oswick"),
        ("Linnea works at Fenmere.", "Where does Linnea work?",
         [["Linnea", "employer", "Fenmere"]], "Fenmere"),
        ("My brother is Jesper.", "Who is my brother?",
         [["USER", "brother", "Jesper"]], "Jesper"),
        ("Yo, Marisol's friend is Tilda.", "Who is Marisol's friend?",
         [["Marisol", "friend", "Tilda"]], "Tilda"),
        ("Oswick's sister is Ysolde.", "Who is Oswick's sister?",
         [["Oswick", "sister", "Ysolde"]], "Ysolde"),
        ("Pellin's mother is Sorrel.", "Who is Pellin's mother?",
         [["Pellin", "mother", "Sorrel"]], "Sorrel"),
        ("Tamber's boss is Corvin.", "Who is Tamber's boss?",
         [["Tamber", "boss", "Corvin"]], "Corvin"),
    ]
    for t, f, e, g in cleans:
        add("clean", [], t, f, e, g)
    qclean = [
        (["Belmara's mother is Tilda."], "Who is Belmara's mother?",
         [["Belmara", "mother", "Tilda"]], "Tilda"),
        (["Quillan lives in Drennor."], "Where does Quillan live?",
         [["Quillan", "city", "Drennor"]], "Drennor"),
        (["My job is fisher."], "What is my job?",
         [["USER", "job", "fisher"]], "fisher"),
        (["Tilda's brother is Jesper."], "Who's Tilda's brother?",
         [["Tilda", "brother", "Jesper"]], "Jesper"),
        (["Wexford works at Eskdale."], "Where does Wexford work?",
         [["Wexford", "employer", "Eskdale"]], "Eskdale"),
        ([], "What is your name?", [], "Premonition"),
        ([], "Hello there.", [], ""),
        ([], "How are you?", [], ""),
        ([], "Let's say Belmara's mother is Tilda.", [], ""),
        (["Corvin's boss is Jesper."], "Is Corvin's boss Jesper?",
         [["Corvin", "boss", "Jesper"]], ""),
    ]
    for s, t, e, g in qclean:
        add("clean", s, t, "", e, g)
    # clean check-tails (both arms behave the same: not NEW wrong)
    add("clean", [], "Belmara's mother is Tilda, right.",
        "Who is Belmara's mother?",
        [["Belmara", "mother", "Tilda"]], "Tilda")
    add("clean", [], "So Belmara's mother is Tilda.",
        "Who is Belmara's mother?",
        [["Belmara", "mother", "Tilda"]], "Tilda")

    with open(out, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=1)
    fams: dict = {}
    for c in cases:
        fams[c["family"]] = fams.get(c["family"], 0) + 1
    print(f"wrote {len(cases)} cases {fams} -> {out}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
