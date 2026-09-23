#!/usr/bin/env python3
"""Exp 280 dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-capab280-20260923/devcases280.json: a list of
dialogs {id, family, turns, expect_store, checks}.
  turns        : list of turns (fresh daemon per dialog).
  expect_store : exact final store (list of [s, r, v]); None = not checked.
  checks       : [turn_index, "has"|"not", text] on that turn's reply.
Ability families (8 dialogs each, varied phrasing; >= 8 turns per ability):
  save, ask1, twohop, correct, forget, abstain, source.
Plus capab (self-description turns; scored only on the 280 arm by
scripts/claude_capab280_score.py with substring rules, never same-as-base).
Question turns must write 0 events.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-capab280-20260923/devcases280.json")
C = []


def add(fam, turns, store, checks=(), note="", target=None, orig=None):
    C.append({"id": f"d280-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "note": note,
              "target": target, "orig": orig})


# A. save: one teach, exact store (8)
A = [
    ("Rina's boss is Skye.", ["Rina", "boss", "Skye"]),
    ("Tavish lives in Corra.", ["Tavish", "city", "Corra"]),
    ("Wren's job is mason.", ["Wren", "job", "mason"]),
    ("Isolde's brother is Perrin.", ["Isolde", "brother", "Perrin"]),
    ("Hollis works at Amberline.", ["Hollis", "employer", "Amberline"]),
    ("Sable's cat is Mink.", ["Sable", "cat", "Mink"]),
    ("Casper was born in Vexley.", ["Casper", "place_of_birth", "Vexley"]),
    ("Odette's sister is Faye.", ["Odette", "sister", "Faye"]),
]
for t, f in A:
    add("save", [t], [f], [(0, "has", "Saved")])

# B. ask1: teach then one-step ask-back (8)
B = [
    ("Rina's boss is Skye.", "Who is Rina's boss?", "Skye"),
    ("Tavish lives in Corra.", "Where does Tavish live?", "Corra"),
    ("Wren's job is mason.", "What is Wren's job?", "mason"),
    ("Isolde's brother is Perrin.", "Who is Isolde's brother?", "Perrin"),
    ("Hollis works at Amberline.", "Where does Hollis work?", "Amberline"),
    ("Sable's cat is Mink.", "What is Sable's cat?", "Mink"),
    ("Casper was born in Vexley.", "Where was Casper born?", "Vexley"),
    ("Odette's sister is Faye.", "Who is Odette's sister?", "Faye"),
]
for t, q, v in B:
    add("ask1", [t, q], None, [(1, "has", v)])

# C. twohop: two links then a two-step ask (8; C7-C8 use the
# "Who is X's boss's boss?" possessive-chain phrasing)
C2 = [
    (["Quill's boss is Dara.", "Dara's city is Nessa."],
     "Where does Quill's boss live?", "Nessa"),
    (["Fen's boss is Greta.", "Greta's city is Oslo."],
     "Where does Fen's boss live?", "Oslo"),
    (["Pell's teacher is Mara.", "Mara's city is Tyne."],
     "Where does Pell's teacher live?", "Tyne"),
    (["Joss's sister is Lena.", "Lena's job is pilot."],
     "What is Joss's sister's job?", "pilot"),
    (["Karl's friend is Ivo.", "Ivo's city is Bern."],
     "Where does Karl's friend live?", "Bern"),
    (["Nils's boss is Ada.", "Ada's boss is Cleo."],
     "Who is Nils's boss's boss?", "Cleo"),
    (["Ruth's boss is Seth.", "Seth's boss is Vera."],
     "Who is Ruth's boss's boss?", "Vera"),
    (["Paul's mentor is Jade.", "Jade's city is Erie."],
     "Where does Paul's mentor live?", "Erie"),
]
for ts, q, v in C2:
    add("twohop", ts + [q], None, [], target=v)

# C2b. twohop, possessive-chain phrasing only (8 more; tests whether the
# single phrasing "Who is X's boss's boss?" works on its own)
C2B = [
    ("Alf's boss is Bea.", "Bea's boss is Cy.", "Cy"),
    ("Dan's boss is Eli.", "Eli's boss is Fay.", "Fay"),
    ("Gus's boss is Hal.", "Hal's boss is Ivy.", "Ivy"),
    ("Jeb's boss is Kay.", "Kay's boss is Lou.", "Lou"),
    ("Max's boss is Nan.", "Nan's boss is Oda.", "Oda"),
    ("Pat's boss is Quin.", "Quin's boss is Rosa.", "Rosa"),
    ("Sam's boss is Tess.", "Tess's boss is Uwe.", "Uwe"),
    ("Vic's boss is Wren.", "Wren's boss is Xana.", "Xana"),
]
for t1, t2, v in C2B:
    add("twohop", [t1, t2, f"Who is {t1.split(chr(39)+'s')[0]}'s boss's boss?"],
        None, [], target=v, note="boss-chain phrasing")

# D. correct: teach then correct (8; 4x "No," + 4x "Actually,")
D = [
    ("Mira's city is Kent.", "No, Mira's city is York.", "York"),
    ("Beck's job is clerk.", "No, Beck's job is steward.", "steward"),
    ("Alba's boss is Flint.", "No, Alba's boss is Grove.", "Grove"),
    ("Dain's cat is Soot.", "No, Dain's cat is Ash.", "Ash"),
    ("Elke's city is Bonn.", "Actually, Elke's city is Mainz.", "Mainz"),
    ("Finn's job is cooper.", "Actually, Finn's job is wright.", "wright"),
    ("Gail's boss is Holt.", "Actually, Gail's boss is Marsh.", "Marsh"),
    ("Hugh's dog is Brisk.", "Actually, Hugh's dog is Fleet.", "Fleet"),
]
for t, corr, v in D:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("correct", [t, corr], None, [], target=[subj, rel, v],
        orig=[subj, rel, t.split(" is ")[1].rstrip(".")])

# Db. contrast-shape corrections "X is Y, not Z." (4; probe t04-t4 shape)
DB = [
    ("Yara's cat is Moss.", "Yara's cat is Fig, not Moss.", "Fig"),
    ("Zane's city is Reno.", "Zane's city is Elko, not Reno.", "Elko"),
    ("Asta's job is cook.", "Asta's job is baker, not cook.", "baker"),
    ("Bram's dog is Wolf.", "Bram's dog is Fox, not Wolf.", "Fox"),
]
for t, corr, v in DB:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("correct", [t, corr], None, [], target=[subj, rel, v],
        orig=[subj, rel, t.split(" is ")[1].rstrip(".")],
        note="contrast shape")

# E. forget: teach then forget commands (8, varied wordings)
E = [
    ("Iris's city is Pavia.", "Forget Iris's city."),
    ("Jasper's job is tinker.", "Forget where Jasper works."),
    ("Kira's boss is Loth.", "Forget Kira's boss."),
    ("Lena's cat is Pipp.", "Forget everything about Lena."),
    ("Mona's dog is Rex.", "Please forget Mona's dog."),
    ("Nora's city is Siena.", "Forget where Nora lives."),
    ("Otto's job is smith.", "I want you to forget Otto's job."),
    ("Pia's boss is Ulf.", "Forget Pia's boss."),
]
for t, f in E:
    subj = t.split("'s ")[0]
    add("forget", [t, f], None, [], target=[subj])

# Eb. more direct-shape forget commands (4; tests the single phrasing
# "Forget X's R." on its own)
EB = [
    ("Quinn's cat is Tom.", "Forget Quinn's cat."),
    ("Rhea's city is Ulm.", "Forget Rhea's city."),
    ("Seth's job is dyer.", "Forget Seth's job."),
    ("Tessa's boss is Umar.", "Forget Tessa's boss."),
]
for t, f in EB:
    subj = t.split("'s ")[0]
    add("forget", [t, f], None, [], target=[subj], note="direct shape")

# F. abstain: teach about X, ask about never-taught Zara/Yanni (8)
F = [
    ("Rina's boss is Skye.", "Who is Zara's boss?"),
    ("Tavish lives in Corra.", "Where does Zara live?"),
    ("Wren's job is mason.", "What is Zara's job?"),
    ("Isolde's brother is Perrin.", "Who is Yanni's brother?"),
    ("Hollis works at Amberline.", "Where does Yanni work?"),
    ("Sable's cat is Mink.", "What is Zara's cat?"),
    ("Casper was born in Vexley.", "Where was Yanni born?"),
    ("Odette's sister is Faye.", "Who is Zara's sister?"),
]
for t, q in F:
    add("abstain", [t, q], None, [])

# G. source: teach then provenance asks (8)
G = [
    ("Rina's boss is Skye.", "Who told you that Rina's boss is Skye?"),
    ("Tavish lives in Corra.", "Where did you learn that Tavish lives in Corra?"),
    ("Wren's job is mason.", "Who taught you Wren's job?"),
    ("Isolde's brother is Perrin.", "Who said Isolde's brother is Perrin?"),
    ("Hollis works at Amberline.", "Where did you hear that Hollis works at Amberline?"),
    ("Sable's cat is Mink.", "Who told you about Sable's cat?"),
    ("Casper was born in Vexley.", "How do you know Casper was born in Vexley?"),
    ("Odette's sister is Faye.", "Who taught you that Odette's sister is Faye?"),
]
for t, q in G:
    add("source", [t, q], None, [])

# H. capab: self-description turns (280-only substring checks in scorer)
H = [
    ["What can you do?"],
    ["what can you do"],
    ["What are you good at?"],
    ["what are you good at"],
    ["Tell me what you're able to do."],
    ["What are you able to do?"],
    ["What can you not do?"],
    ["Can you forget a fact?"],
    ["Can you answer a two-step question?"],
    ["Can you save what I teach you?"],
]
for ts in H:
    add("capab", ts, [], [])


def main():
    OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"Wrote {OUT} ({len(C)} dialogs)")
    print(Counter(c["family"] for c in C))


if __name__ == "__main__":
    main()
