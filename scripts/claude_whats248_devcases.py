#!/usr/bin/env python3
"""Exp 248 dev cases (fictional names; written from scratch, no panel).

kinds: right (gold must appear, no decline), same (reply byte-identical to
base228 and same stored triples), trap (no stated value may appear).
Writes artifacts/claude-whats248-20260922/dev248.jsonl.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / \
    "artifacts/claude-whats248-20260922/dev248.jsonl"

PELL = ["Pell's city is Quellport.", "Pell's boss is Brannick."]
PELL_F = [["Pell", "city", "Quellport"], ["Pell", "boss", "Brannick"]]
JOREN = ["Joren Hale's city is Selwick.", "Joren Hale's spouse is Sella Voss."]
JOREN_F = [["Joren Hale", "city", "Selwick"], ["Joren Hale", "spouse", "Sella Voss"]]
IDRA = ["Idra's mother is Maren.", "Idra's pet is Biscuit.", "Idra's friend is Corwin."]
IDRA_F = [["Idra", "mother", "Maren"], ["Idra", "pet", "Biscuit"], ["Idra", "friend", "Corwin"]]
TAM = ["Tamsin Rook's employer is Harrowgate Mills.", "Tamsin Rook's friend is Odile."]
TAM_F = [["Tamsin Rook", "employer", "Harrowgate Mills"], ["Tamsin Rook", "friend", "Odile"]]
OSK = ["Oskar Vell's city is Dunmere.", "Oskar Vell's boss is Hester Crane."]
OSK_F = [["Oskar Vell", "city", "Dunmere"], ["Oskar Vell", "boss", "Hester Crane"]]
MIR = ["Mirel's city is Pollock Ford.", "Mirel's country is Estmark."]
MIR_F = [["Mirel", "city", "Pollock Ford"], ["Mirel", "country", "Estmark"]]
QUA = ["Quade Ashworth's city is Lintby.", "Quade Ashworth's boss is Roswen."]
QUA_F = [["Quade Ashworth", "city", "Lintby"], ["Quade Ashworth", "boss", "Roswen"]]
NES = ["Nessa's employer is Brightwater Co.", "Nessa's city is Callow."]
NES_F = [["Nessa", "employer", "Brightwater Co"], ["Nessa", "city", "Callow"]]
ME = ["My city is Varrow.", "My boss is Tollan."]
ME_F = [["USER", "city", "Varrow"], ["USER", "boss", "Tollan"]]
WHO = ["Whosby's city is Kettering Vale.", "Whatley's boss is Ferro."]
WHO_F = [["Whosby", "city", "Kettering Vale"], ["Whatley", "boss", "Ferro"]]
BRA = ["Brannick's city is Orlow.", "Brannick's pet is Pip."]
BRA_F = [["Brannick", "city", "Orlow"], ["Brannick", "pet", "Pip"]]
SEL = ["Sella Voss's spouse is Joren Hale."]
SEL_F = [["Sella Voss", "spouse", "Joren Hale"]]

cases = []


def add(kind, setup, facts, q, gold=None, note=""):
    cases.append({"id": f"d248-{len(cases)+1:03d}", "kind": kind,
                  "setup": setup, "stated": facts, "question": q,
                  "gold": gold, "note": note})


R = "right"
add(R, PELL, PELL_F, "whats Pell's city?", ["Quellport"], "lower whats, 1-word")
add(R, PELL, PELL_F, "Whats Pell's city?", ["Quellport"], "title Whats")
add(R, PELL, PELL_F, "WHATS PELL'S CITY?", ["Quellport"], "upper")
add(R, PELL, PELL_F, "whos Pell's boss?", ["Brannick"], "whos")
add(R, PELL, PELL_F, "Whos Pell's boss?", ["Brannick"], "title Whos")
add(R, PELL, PELL_F, "wheres Pell's city?", ["Quellport"], "wheres")
add(R, PELL, PELL_F, "whats Pell's boss?", ["Brannick"], "whats + person rel")
add(R, PELL, PELL_F, "Whats Pell's city??", ["Quellport"], "double mark")
add(R, JOREN, JOREN_F, "whats Joren Hale's city?", ["Selwick"], "2-word")
add(R, JOREN, JOREN_F, "whats joren hale's city?", ["Selwick"], "2-word lower name")
add(R, JOREN, JOREN_F, "WHOS JOREN HALE'S SPOUSE?", ["Sella Voss"], "2-word upper spouse")
add(R, IDRA, IDRA_F, "whos Idra's mother?", ["Maren"], "mother")
add(R, IDRA, IDRA_F, "whats Idra's pet?", ["Biscuit"], "pet")
add(R, IDRA, IDRA_F, "hey, whats Idra's pet?", ["Biscuit"], "filler + comma")
add(R, IDRA, IDRA_F, "yo whos Idra's friend?", ["Corwin"], "filler yo")
add(R, TAM, TAM_F, "whats Tamsin Rook's employer?", ["Harrowgate Mills"], "employer 2-word value")
add(R, TAM, TAM_F, "whos Tamsin Rook's friend?", ["Odile"], "friend 2-word name")
add(R, PELL, PELL_F, "so whats Pell's city?", ["Quellport"], "filler so")
add(R, PELL, PELL_F, "hey whos Pell's boss?", ["Brannick"], "filler hey")
add(R, OSK, OSK_F, "please whats Oskar Vell's city?", ["Dunmere"], "filler please")
add(R, OSK, OSK_F, "ok whos Oskar Vell's boss?", ["Hester Crane"], "filler ok, 2-word value")
add(R, MIR, MIR_F, "well wheres Mirel's city?", ["Pollock Ford"], "filler well")
add(R, MIR, MIR_F, "whats Mirel's country?", ["Estmark"], "country")
add(R, ME, ME_F, "whats my city?", ["Varrow"], "first person via Me166")
add(R, ME, ME_F, "whos my boss?", ["Tollan"], "first person boss")
add(R, WHO, WHO_F, "whats Whosby's city?", ["Kettering Vale"], "name starting Whos")
add(R, WHO, WHO_F, "whos Whatley's boss?", ["Ferro"], "name starting What")
add(R, QUA, QUA_F, "whats Quade Ashworth's city?", ["Lintby"], "2-word")
add(R, QUA, QUA_F, "whos quade ashworth's boss?", ["Roswen"], "2-word lower")
add(R, NES, NES_F, "whats Nessa's employer?", ["Brightwater Co"], "employer")
add(R, NES, NES_F, "Wheres Nessa's city?", ["Callow"], "title Wheres")
add(R, BRA, BRA_F, "Hi whats Brannick's pet?", ["Pip"], "filler Hi")
add(R, SEL, SEL_F, "whos Sella Voss's spouse?", ["Joren Hale"], "name ending s")
add(R, PELL, PELL_F, "OKAY WHATS PELL'S CITY?", ["Quellport"], "upper filler")

T = "trap"
add(T, PELL[:1], PELL_F[:1], "whats Pell's pet?", None, "untaught rel")
add(T, PELL[:1], PELL_F[:1], "whos Pell's boss?", None, "untaught boss")
add(T, JOREN[1:], JOREN_F[1:], "wheres Joren Hale's city?", None, "untaught city 2-word")
add(T, OSK[:1], OSK_F[:1], "whats Oskar Vell's employer?", None, "untaught employer")
add(T, IDRA[1:2], IDRA_F[1:2], "whos Idra's mother?", None, "untaught mother")
add(T, PELL, PELL_F, "whats Tamsin Rook's city?", None, "unknown person")
add(T, PELL, PELL_F, "so whats my city?", None, "untaught USER city")
add(T, SEL, SEL_F, "whats Sella Voss's city?", None, "untaught city, 2-word name ending s")

S = "same"
add(S, PELL, PELL_F, "what's Pell's city?", None, "apostrophe form works")
add(S, PELL, PELL_F, "What is Pell's city?", None, "plain form")
add(S, PELL, PELL_F, "Who is Pell's boss?", None, "plain who")
add(S, PELL, PELL_F, "Where is Pell's city?", None, "plain where")
add(S, [], [], "Whatsley's city is Orrin.", None, "teach whose name starts Whats")
add(S, ["Whatsley's city is Orrin."], [["Whatsley", "city", "Orrin"]],
    "What is Whatsley's city?", None, "Whats-name ask plain")
add(S, ["Hows's city is Tarnwick."] + PELL, [["Hows", "city", "Tarnwick"]] + PELL_F,
    "hows Pell's city?", None, "entity named Hows: no rewrite")
add(S, PELL, PELL_F, "whats up?", None, "small talk")
add(S, PELL, PELL_F, "Whats Pell's city.", None, "no ? -> untouched")
add(S, PELL, PELL_F, "hows it going?", None, "small talk hows")
add(S, PELL, PELL_F, "whos there?", None, "no possessive")
add(S, PELL, PELL_F, "whats Pell's city? also Pell's pet is Dot.", None, "glued")
add(S, PELL, PELL_F, "Whatsley's city?", None, "name starting Whats, no rewrite")
add(S, ["Pell's birthday is March 3."], [["Pell", "birthday", "March 3"]], "whens Pell's birthday?", None, "whens expands but no when-is reader: falls back")
add(S, PELL, PELL_F, "whats Pell?", None, "no relation: falls back")

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")
print(len(cases), {k: sum(c["kind"] == k for c in cases) for k in (R, T, S)})
