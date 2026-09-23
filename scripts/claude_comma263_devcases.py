#!/usr/bin/env python3
"""Exp 263 dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-comma263-20260923/devcases263.json: a list of
dialogs {id, family, turns, expect_store, checks, same_as_base, note}.
Same schema as 260's devcases260.json:
  turns        : list of turns; "__RESTART__" rebuilds the daemon.
  expect_store : exact final store (list of [s, r, v]); None = not checked.
  checks       : [turn_index, "has"|"not", text] on that turn's reply
                 (turn_index counts real turns only, restarts skipped).
  same_as_base : every reply must equal the 260 arm's reply.
Question turns (ending "?") must write 0 events. No stored subject may
contain a comma.
"""
import json
import sys
from pathlib import Path

OUT = Path("artifacts/claude-comma263-20260923/devcases263.json")
C = []


def add(fam, turns, store, checks=(), same=False, note=""):
    C.append({"id": f"d263-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "same_as_base": same,
              "note": note})


# A. unlisted opener + comma + plain teach, then the question (20).
# None of these openers is in 260's strip list, so 260 stores "Op, Name".
A = [
    ("Yo, Kestrel's job is fisher.", "What is Kestrel's job?",
     ["Kestrel", "job", "fisher"]),
    ("Get this, Pell's boss is Rhoda.", "Who is Pell's boss?",
     ["Pell", "boss", "Rhoda"]),
    ("Real talk, Marnie lives in Tollan.", "Where does Marnie live?",
     ["Marnie", "city", "Tollan"]),
    ("Funny thing, Idris works at Fenwick.", "Where does Idris work?",
     ["Idris", "employer", "Fenwick"]),
    ("Guess this, Brann's sister is Liesl.", "Who is Brann's sister?",
     ["Brann", "sister", "Liesl"]),
    ("Hot take, Dace's boss is Wren.", "Who is Dace's boss?",
     ["Dace", "boss", "Wren"]),
    ("Look here, Yara lives in Quell.", "Where does Yara live?",
     ["Yara", "city", "Quell"]),
    ("Hear me out, Fenn's brother is Oskar.", "Who is Fenn's brother?",
     ["Fenn", "brother", "Oskar"]),
    ("Mind you, Lio works at Brightmoor.", "Where does Lio work?",
     ["Lio", "employer", "Brightmoor"]),
    ("Between us, Nessa's boss is Corran.", "Who is Nessa's boss?",
     ["Nessa", "boss", "Corran"]),
    ("Long story short, Ivo's sister is Petra.", "Who is Ivo's sister?",
     ["Ivo", "sister", "Petra"]),
    ("Plot twist, Sela's job is miller.", "What is Sela's job?",
     ["Sela", "job", "miller"]),
    ("Good news, Bram lives in Hollin.", "Where does Bram live?",
     ["Bram", "city", "Hollin"]),
    ("Bad news, Orrin was born in Varn.", "Where was Orrin born?",
     ["Orrin", "place_of_birth", "Varn"]),
    ("True story, Tamsin's job is baker.", "What is Tamsin's job?",
     ["Tamsin", "job", "baker"]),
    ("No joke, Corwin's job is carter.", "What is Corwin's job?",
     ["Corwin", "job", "carter"]),
    ("Believe me, Wren's sister is Petra.", "Who is Wren's sister?",
     ["Wren", "sister", "Petra"]),
    ("Breaking news, Tarn's boss is Dace.", "Who is Tarn's boss?",
     ["Tarn", "boss", "Dace"]),
    ("Spoiler alert, Annika lives in Vesk.", "Where does Annika live?",
     ["Annika", "city", "Vesk"]),
    ("Check this out, Rurik works at Brisk.", "Where does Rurik work?",
     ["Rurik", "employer", "Brisk"]),
]
for t, q, f in A:
    add("unlisted", [t, q], [f], [(1, "has", f[2])])

# B. appositive subjects: gold stores nothing with a comma subject (8).
B = [
    "Dace, my pilot, flies for Brightmoor.",
    "Tamsin, who is my baker, lives in Tollan.",
    "Pell, my neighbor, works at Fenwick.",
    "Wren, who is my sister, lives in Quell.",
    "Idris, my clerk, works at Holloway.",
    "Nessa, who is my boss, lives in Varn.",
    "Fenn, my brother, sailed to Vesk.",
    "Lio, who is my smith, works at Brisk.",
]
for t in B:
    add("appositive", [t], [], [(0, "not", "Saved")],
        note="appositive: no comma subject may be stored")

# C. comma values that must stay, byte-identical to 260 (6).
Cv = [
    ("Marnie lives in Tollan, Vesk.", "Where does Marnie live?",
     ["Marnie", "city", "Tollan, Vesk"]),
    ("Idris works at Fenwick, Vesk.", "Where does Idris work?",
     ["Idris", "employer", "Fenwick, Vesk"]),
    ("Orrin was born in Varn, Lower Vesk.", "Where was Orrin born?",
     ["Orrin", "place_of_birth", "Varn, Lower Vesk"]),
    ("Lio's sister is Petra, of House Rook.", "Who is Lio's sister?",
     ["Lio", "sister", "Petra, of House Rook"]),
    ("Brann lives in Varn, Old Town.", "Where does Brann live?",
     ["Brann", "city", "Varn, Old Town"]),
    ("Tamsin's job is baker, first class.", "What is Tamsin's job?",
     ["Tamsin", "job", "baker, first class"]),
]
for t, q, f in Cv:
    add("comma_value", [t, q], [f], [(1, "has", f[2].split(",")[0])],
        same=True)

# D. questions with unlisted openers: 0 writes, same replies as 260 (6).
add("question", ["Pell's boss is Rhoda.", "Hi! Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", "Rhoda")], same=True)
add("question", ["Marnie lives in Tollan.", "Hello, where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")], same=True)
add("question", ["Kestrel's job is fisher.",
                 "Hey there, what is Kestrel's job?"],
    [["Kestrel", "job", "fisher"]], [(1, "has", "fisher")], same=True)
add("question", ["Yo, who is Mira's boss?"], [], [(0, "not", "Saved")],
    same=True)
add("question", ["Real talk, where does Yara live?"], [],
    [(0, "not", "Saved")], same=True)
add("question", ["Pell's boss is Rhoda.", "Check this out, is Pell's boss Rhoda?"],
    [["Pell", "boss", "Rhoda"]], [(1, "not", "Saved")], same=True)

# E. controls: plain turns, byte-identical to 260 (8).
add("control", ["Pell's boss is Rhoda.", "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", "Rhoda")], same=True)
add("control", ["Marnie lives in Tollan.", "Where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")], same=True)
add("control", ["Oh, and Pell's boss is Rhoda.", "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", "Rhoda")], same=True)
add("control", ["Please, Kestrel's job is fisher.", "What is Kestrel's job?"],
    [["Kestrel", "job", "fisher"]], [(1, "has", "fisher")], same=True)
add("control", ["Hi! Who is Pell's boss?", ], [], [(0, "not", "Saved")],
    same=True)
add("control", ["Marnie lives in Tollan, Vesk.", "Where does Marnie live?"],
    [["Marnie", "city", "Tollan, Vesk"]], [(1, "has", "Tollan")], same=True)
add("control", ["Who is Tobin's boss?"], [], same=True)
add("control", ["Kestrel's job is fisher.", "What is Kestrel's job?"],
    [["Kestrel", "job", "fisher"]], [(1, "has", "fisher")], same=True)

# F. restart: comma guard state does not leak across restarts (2).
add("restart", ["Yo, Kestrel's job is fisher.", "__RESTART__",
                "What is Kestrel's job?"],
    [["Kestrel", "job", "fisher"]], [(1, "has", "fisher")])
add("restart", ["Marnie lives in Tollan, Vesk.", "__RESTART__",
                "Where does Marnie live?"],
    [["Marnie", "city", "Tollan, Vesk"]], [(1, "has", "Tollan")])

# G. known limit: two commas, the last comma wins, fact lost (1).
add("multcomma", ["Yo, Mara's boss is Wren, obviously."], [],
    [(0, "not", "Saved")],
    note="known limit: single retry after the LAST comma loses the fact")

# H. pretend/correction markers: never stripped, never a fact (4).
add("pretend", ["Suppose, Pell's boss is Rhoda."], [],
    [(0, "not", "Saved")], same=True,
    note="pretend marker: never a fact, same reply as 260")
add("pretend", ["Imagine, Tobin's boss is Mara."], [],
    [(0, "not", "Saved")], same=True,
    note="pretend marker: never a fact, same reply as 260")
add("pretend", ["Say, Pell's boss is Rhoda."], [],
    [(0, "not", "Saved")], same=True,
    note="say-led chunk: pretend-ambiguous, never stripped")
add("pretend", ["Suppose, for a moment, Pell's boss is Rhoda."], [],
    [(0, "not", "Saved")], same=True,
    note="two-comma pretend: leading chunk guarded, never stripped")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
    fams = {}
    for c in C:
        fams[c["family"]] = fams.get(c["family"], 0) + 1
    print(len(C), fams)
    sys.exit(0)
