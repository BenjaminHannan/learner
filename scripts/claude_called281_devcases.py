#!/usr/bin/env python3
"""Exp 281 dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-called281-20260923/devcases281.json: a list of
dialogs {id, family, turns, expect_store, checks}.
  turns        : list of turns (fresh daemon per dialog).
  expect_store : exact final store (list of [s, r, v]); None = not checked.
  checks       : [turn_index, "has"|"not", text] on the 281 arm's reply.
Families (46 dialogs):
  stored_called   teach + "What is X's R called?" (8; pets/boats/bands/
                  streets/teachers/boss/city/dog).
  stored_named    teach + "named" / "Who is ... called?" (6).
  stored_call     teach + "What do you call X's R?" (6).
  stored_nameof   teach + "What's/What is the name of X's R?" (6).
  opener_called   opener-prefixed called-question, teach first (4).
  notstored       called-wording with nothing taught: must abstain (5).
  ambiguous       "called <Name>" belongs to the value: 281 must keep
                  260's reply byte-identical (5).
  control         plain teaches and plain possessive questions (6).
Question turns must write 0 events on both arms. Scored by
scripts/claude_called281_score.py dev.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-called281-20260923/devcases281.json")
C = []


def add(fam, turns, store, checks=(), target=None):
    C.append({"id": f"d281-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "target": target})


# Stored: teach then called-wording question. Checks assert the 281 arm
# answers with the stored value.
STORED_CALLED = [
    ("Bram's cat is Soot.", "What is Bram's cat called?", "Soot"),
    ("Cleo's boat is Reed.", "What is Cleo's boat called?", "Reed"),
    ("Dara's band is Lumen.", "What is Dara's band called?", "Lumen"),
    ("Elif's street is Grove.", "What is Elif's street called?", "Grove"),
    ("Finn's teacher is Mara.", "What is Finn's teacher called?", "Mara"),
    ("Greta's boss is Holm.", "What is Greta's boss called?", "Holm"),
    ("Hugo's city is Berne.", "What is Hugo's city called?", "Berne"),
    ("Iris's dog is Taffy.", "What is Iris's dog called?", "Taffy"),
]
for t, q, v in STORED_CALLED:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("stored_called", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

STORED_NAMED = [
    ("Jorunn's boat is Skiff.", "What is Jorunn's boat named?", "Skiff"),
    ("Kasia's band is Alder.", "What is Kasia's band named?", "Alder"),
    ("Liv's street is Harbor.", "What is Liv's street named?", "Harbor"),
    ("Mona's cat is Biscuit.", "Who is Mona's cat called?", "Biscuit"),
    ("Nils's teacher is Voss.", "Who is Nils's teacher named?", "Voss"),
    ("Oda's dog is Pebble.", "What is Oda's dog named?", "Pebble"),
]
for t, q, v in STORED_NAMED:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("stored_named", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

STORED_CALL = [
    ("Petra's band is Willow.", "What do you call Petra's band?", "Willow"),
    ("Quinn's boat is Frost.", "What do you call Quinn's boat?", "Frost"),
    ("Runa's street is Mill.", "What do you call Runa's street?", "Mill"),
    ("Sven's cat is Domino.", "What do you call Sven's cat?", "Domino"),
    ("Tilda's teacher is Brandt.", "What do you call Tilda's teacher?",
     "Brandt"),
    ("Ulf's dog is Comet.", "What do you call Ulf's dog?", "Comet"),
]
for t, q, v in STORED_CALL:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("stored_call", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

STORED_NAMEOF = [
    ("Vera's street is Lark.", "What's the name of Vera's street?",
     "Lark"),
    ("Wren's boat is Gull.", "What is the name of Wren's boat?", "Gull"),
    ("Xander's band is Copper.", "What's the name of Xander's band?",
     "Copper"),
    ("Ysolde's cat is Miso.", "What is the name of Ysolde's cat?",
     "Miso"),
    ("Zelda's teacher is Quist.", "What's the name of Zelda's teacher?",
     "Quist"),
    ("Anders's dog is Russo.", "What is the name of Anders's dog?",
     "Russo"),
]
for t, q, v in STORED_NAMEOF:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("stored_nameof", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

# Opener-prefixed called questions.
OPENER_CALLED = [
    ("Bodil's cat is Tipsy.", "So, what is Bodil's cat called?", "Tipsy"),
    ("Embla's boat is Nord.", "Okay, what is Embla's boat named?", "Nord"),
    ("Frida's band is Haze.", "Well, what do you call Frida's band?",
     "Haze"),
    ("Gorm's street is Park.", "Please, what's the name of "
     "Gorm's street?", "Park"),
]
for t, q, v in OPENER_CALLED:
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    add("opener_called", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

# Never taught: both arms must abstain, 0 writes.
NOTSTORED = [
    "What is Zara's dog called?",
    "What is Ylva's boat named?",
    "What do you call Xenia's band?",
    "What's the name of Wenke's street?",
    "Who is Ulrik's teacher called?",
]
for q in NOTSTORED:
    add("notstored", [q], [], [])

# Ambiguous: "called <Name>" belongs to the value. 281 must keep 260's
# reply byte-identical (scorer asserts equality, never the content).
AMBIGUOUS = [
    ["Tove's dog is Pip.", "Who is Tove's friend called Bo?"],
    ["Alf's boat is Keel.", "Who is Alf's sailor called Bo?"],
    ["Edda's band is Drum.", "Which of Edda's singers is called Bo?"],
    ["Who is Sindre's friend called Bo?"],
    ["What is Noah's teacher called Bo?"],
]
for ts in AMBIGUOUS:
    add("ambiguous", ts, None, [])

# Controls: plain teaches and plain possessive questions; 281 must be
# byte-identical to 260.
CONTROLS = [
    (["Viggo's cat is Simba."], [["Viggo", "cat", "Simba"]]),
    (["Viggo's cat is Simba.", "What is Viggo's cat?"], None),
    (["Rikke's boat is Fjord.", "Who is Rikke's boat owner?"], None),
    (["Sanna lives in Tromso.", "Where does Sanna live?"], None),
    (["Lars's band is Echo.", "What is Lars's band?"], None),
    (["Mette's street is Dune.", "Mette's teacher is Lund."], None),
]
for ts, store in CONTROLS:
    add("control", ts, store, [])

print(f"wrote {len(C)} cases to {OUT}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
