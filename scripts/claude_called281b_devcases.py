#!/usr/bin/env python3
"""Exp 281b dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-called281b-20260923/devcases281b.json: a list of
dialogs {id, family, turns, expect_store, checks}.
  turns        : list of turns (fresh daemon per dialog).
  expect_store : exact final store (list of [s, r, v]); None = not checked.
  checks       : [turn_index, "has"|"not", text] on the 281b arm's reply.
Families (56 dialogs):
  stored_formal   teach + formal called/named/nameof/doyoucall, incl.
                  "What's X called?" (10; 281b must answer; the 3 "What's"
                  items move 281->281b, the rest are already 281's).
  stored_casual   teach + casual typing (lowercase, no apostrophe, whats,
                  missing ? and combos) (20; all move 281->281b).
  opener_casual   opener-prefixed casual called-question, teach first (4).
  notstored       called-wording with nothing taught, formal + casual (8):
                  both arms must abstain, 281b byte-identical to 281.
  ambiguous       "called <Name>" belongs to the value, formal + casual
                  (8): 281b must keep 281's reply byte-identical.
  control         plain teaches/questions, a ?-less plain question, a
                  casual greeting and a closing (6): byte-identical.
Question turns must write 0 events on both arms. Scored by
scripts/claude_called281b_score.py dev.
"""

import json
from pathlib import Path

OUT = Path("artifacts/claude-called281b-20260923/devcases281b.json")
C = []


def add(fam, turns, store, checks=(), target=None):
    C.append({"id": f"d281b-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "target": target})


def _sr(t):
    subj = t.split("'s ")[0]
    rel = t.split("'s ")[1].split(" is ")[0]
    return subj, rel


# Formal: teach then called-wording question. Checks assert the 281b arm
# answers with the stored value.
STORED_FORMAL = [
    ("Alma's cat is Mjau.", "What is Alma's cat called?", "Mjau"),
    ("Birk's boat is Vaag.", "What is Birk's boat named?", "Vaag"),
    ("Cato's band is Lyd.", "What's Cato's band called?", "Lyd"),
    ("Dina's street is Vei.", "What's the name of Dina's street?", "Vei"),
    ("Ebbe's teacher is Lund.", "Who is Ebbe's teacher called?", "Lund"),
    ("Fride's dog is Labb.", "What is Fride's dog named?", "Labb"),
    ("Gerd's boss is Dahl.", "What do you call Gerd's boss?", "Dahl"),
    ("Halvor's city is Bergen.", "What is the name of Halvor's city?",
     "Bergen"),
    ("Inga's boat is Fjell.", "What's Inga's boat named?", "Fjell"),
    ("Jens's cat is Pels.", "What's Jens's cat called?", "Pels"),
]
for t, q, v in STORED_FORMAL:
    subj, rel = _sr(t)
    add("stored_formal", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

# Casual: teach then casually typed called/named question.
STORED_CASUAL = [
    ("Kaja's bird is Pip.", "what is kajas bird called?", "Pip"),
    ("Leif's horse is Hov.", "whats Leif's horse called?", "Hov"),
    ("Mari's song is Tone.", "What is Mari's song called", "Tone"),
    ("Nils's farm is Eng.", "whats nils farm called", "Eng"),
    ("Oda's lake is Blaa.", "what is Odas lake named", "Blaa"),
    ("Peder's uncle is Graa.", "who is Peders uncle called", "Graa"),
    ("Ragna's river is Sild.", "what do you call ragnas river", "Sild"),
    ("Stein's valley is Dal.", "whats the name of steins valley", "Dal"),
    ("Tone's peak is Topp.", "whats Tones peak named?", "Topp"),
    ("Ulrik's trail is Sti.", "what is Ulriks trail called?", "Sti"),
    ("Vendla's cabin is Hytte.", "whats vendlas cabin called", "Hytte"),
    ("Yngve's fjord is Sunn.", "WHAT IS YNGVE'S FJORD CALLED", "Sunn"),
    ("Aasta's meadow is Voll.", "whats aasta's meadow named", "Voll"),
    ("Bente's garden is Hage.", "what do you call Bentes garden?", "Hage"),
    ("Dag's bridge is Bru.", "what is Dags bridge named?", "Bru"),
    ("Edel's tower is Taarn.", "whats the name of Edels tower?", "Taarn"),
    ("Frode's mill is Kvern.", "what is Frodes mill called", "Kvern"),
    ("Gro's inn is Kro.", "WHATS GROS INN CALLED?", "Kro"),
    ("Harald's port is Havn.", "who is Haralds port named", "Havn"),
    ("Ida's well is Bronn.", "whats idas well called?", "Bronn"),
]
for t, q, v in STORED_CASUAL:
    subj, rel = _sr(t)
    add("stored_casual", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

# Opener-prefixed casual called questions.
OPENER_CASUAL = [
    ("Jorunn's lamp is Ljos.", "so whats jorunns lamp called", "Ljos"),
    ("Kjell's gate is Port.", "okay what is Kjells gate named", "Port"),
    ("Laila's drum is Tromme.", "well what do you call lailas drum",
     "Tromme"),
    ("Morten's flute is Floyte.", "So, whats the name of mortens flute?",
     "Floyte"),
]
for t, q, v in OPENER_CASUAL:
    subj, rel = _sr(t)
    add("opener_casual", [t, q], [[subj, rel, v]], [(1, "has", v)],
        target=v)

# Never taught: both arms must abstain, 281b byte-identical to 281.
NOTSTORED = [
    "What is Zara's owl called?",
    "What's Ylva's kite named?",
    "whats zaras owl called",
    "what is Ylvas kite named",
    "Who is Odd's mentor called?",
    "what do you call Xenias choir",
    "What's the name of Wenke's vineyard?",
    "whats the name of wenkes vineyard",
]
for q in NOTSTORED:
    add("notstored", [q], [], [])

# Ambiguous: "called <Name>" belongs to the value. 281b must keep 281's
# reply byte-identical (scorer asserts equality, never the content).
AMBIGUOUS = [
    ["Tove's spaniel is Ruf.", "Who is Tove's comrade called Bo?"],
    ["Alf's yawl is Mast.", "Who is Alf's crewmate called Bo?"],
    ["Edda's choir is Alto.", "Which of Edda's tenors is called Bo?"],
    ["Who is Sindre's pal called Bo?"],
    ["Tove's spaniel is Ruf.", "who is toves comrade called bo"],
    ["What is Noah's tutor called Bo"],
    ["Which of Edda's tenors is called Bo"],
    ["Who is Alf's crewmate called Bo"],
]
for ts in AMBIGUOUS:
    store = None
    if len(ts) == 2 and "'s " in ts[0] and " is " in ts[0]:
        subj, rel = _sr(ts[0])
        val = ts[0].split(" is ")[1].rstrip(".")
        store = [[subj, rel, val]]
    add("ambiguous", ts, store, [])

# Controls: plain teaches/questions, a ?-less plain question, small talk.
# 281b must be byte-identical to 281.
CONTROLS = [
    (["Viggo's lynx is Gaupe."], [["Viggo", "lynx", "Gaupe"]]),
    (["Viggo's lynx is Gaupe.", "What is Viggo's lynx?"], None),
    (["Sanna lives in Tromso.", "Where does Sanna live?"], None),
    (["Where does Sanna live"], None),
    (["hey whats up"], None),
    (["Thanks, that's all!"], None),
]
for ts, store in CONTROLS:
    add("control", ts, store, [])

print(f"wrote {len(C)} cases to {OUT}")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
