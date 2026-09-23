#!/usr/bin/env python3
"""Exp 260 dev cases (builder's own wording; fictional names only).

Writes artifacts/claude-openers260-20260922/devcases260.json: a list of
dialogs {id, family, turns, expect_store, checks, same_as_base, note}.
  turns        : list of turns; "__RESTART__" rebuilds the daemon.
  expect_store : exact final store (list of [s, r, v]); None = not checked.
  checks       : [turn_index, "has"|"not", text] on that turn's reply
                 (turn_index counts real turns only, restarts skipped).
  same_as_base : every reply must equal the 138m arm's reply.
Question turns (ending "?") must write 0 events. No stored subject may
start with an opener + comma (junk).
"""
import json
import sys
from pathlib import Path

OUT = Path("artifacts/claude-openers260-20260922/devcases260.json")
C = []


def add(fam, turns, store, checks=(), same=False, note=""):
    C.append({"id": f"d260-{len(C) + 1:03d}", "family": fam,
              "turns": list(turns), "expect_store": store,
              "checks": [list(c) for c in checks], "same_as_base": same,
              "note": note})


GREET = "Teach me like"
FAIL = "understand"

# A. opener + punctuation + teach, then the question (15)
A = [
    ("So, Marnie lives in Tollan.", "Where does Marnie live?",
     ["Marnie", "city", "Tollan"]),
    ("Please, Kestrel's job is fisher.", "What is Kestrel's job?",
     ["Kestrel", "job", "fisher"]),
    ("Oh, and Pell's boss is Rhoda.", "Who is Pell's boss?",
     ["Pell", "boss", "Rhoda"]),
    ("Also, Idris works at Fenwick.", "Where does Idris work?",
     ["Idris", "employer", "Fenwick"]),
    ("Anyway, Brann's sister is Liesl.", "Who is Brann's sister?",
     ["Brann", "sister", "Liesl"]),
    ("Btw, Orrin was born in Varn.", "Where was Orrin born?",
     ["Orrin", "place_of_birth", "Varn"]),
    ("Fun fact: Tamsin's job is baker.", "What is Tamsin's job?",
     ["Tamsin", "job", "baker"]),
    ("Listen, Dace's boss is Wren.", "Who is Dace's boss?",
     ["Dace", "boss", "Wren"]),
    ("Hey, Yara lives in Quell.", "Where does Yara live?",
     ["Yara", "city", "Quell"]),
    ("Um, Fenn's brother is Oskar.", "Who is Fenn's brother?",
     ["Fenn", "brother", "Oskar"]),
    ("For the record, Lio works at Brightmoor.", "Where does Lio work?",
     ["Lio", "employer", "Brightmoor"]),
    ("Right, Nessa's boss is Corran.", "Who is Nessa's boss?",
     ["Nessa", "boss", "Corran"]),
    ("One more thing - Ivo's sister is Petra.", "Who is Ivo's sister?",
     ["Ivo", "sister", "Petra"]),
    ("Okay! Sela's job is miller.", "What is Sela's job?",
     ["Sela", "job", "miller"]),
    ("Oh, and so, Bram lives in Hollin.", "Where does Bram live?",
     ["Bram", "city", "Hollin"]),
]
for t, q, f in A:
    add("opener_comma", [t, q], [f], [(1, "has", f[2])])

# B. opener without punctuation (6)
B = [
    ("so Marnie lives in Tollan.", "Where does Marnie live?",
     ["Marnie", "city", "Tollan"]),
    ("Okay so Brann's sister is Liesl.", "Who is Brann's sister?",
     ["Brann", "sister", "Liesl"]),
    ("btw Orrin was born in Varn.", "Where was Orrin born?",
     ["Orrin", "place_of_birth", "Varn"]),
    ("Oh and Pell's boss is Rhoda.", "Who is Pell's boss?",
     ["Pell", "boss", "Rhoda"]),
    ("also Idris works at Fenwick.", "Where does Idris work?",
     ["Idris", "employer", "Fenwick"]),
    ("Just so you know Kestrel's job is fisher.", "What is Kestrel's job?",
     ["Kestrel", "job", "fisher"]),
]
for t, q, f in B:
    add("opener_plain", [t, q], [f], [(1, "has", f[2])])

# C. greeting + question after a plain teach (8)
Cq = [
    ("Pell's boss is Rhoda.", "Hi! Who is Pell's boss?", "Rhoda",
     ["Pell", "boss", "Rhoda"]),
    ("Marnie lives in Tollan.", "Hello, where does Marnie live?", "Tollan",
     ["Marnie", "city", "Tollan"]),
    ("Kestrel's job is fisher.", "Hey there, what is Kestrel's job?",
     "fisher", ["Kestrel", "job", "fisher"]),
    ("Idris works at Fenwick.", "Good morning! Where does Idris work?",
     "Fenwick", ["Idris", "employer", "Fenwick"]),
    ("Brann's sister is Liesl.", "Hiya, who is Brann's sister?", "Liesl",
     ["Brann", "sister", "Liesl"]),
    ("Orrin was born in Varn.", "Hi Premonition, where was Orrin born?",
     "Varn", ["Orrin", "place_of_birth", "Varn"]),
    ("Pell's boss is Rhoda.", "hello who is Pell's boss?", "Rhoda",
     ["Pell", "boss", "Rhoda"]),
    ("Pell's boss is Rhoda.", "Hey! Is Pell's boss Rhoda?", "Yes",
     ["Pell", "boss", "Rhoda"]),
]
for s, q, g, f in Cq:
    add("greeting_question", [s, q], [f], [(1, "has", g)])

# D. identity questions after greetings (5)
add("identity_greeting", ["Hi! What's your name?"], [],
    [(0, "has", "Premonition")])
add("identity_greeting", ["Hello, who made you?"], [],
    [(0, "has", "Ben")])
add("identity_greeting", ["Hey there, what is your name?"], [],
    [(0, "has", "Premonition")])
add("identity_greeting", ["My name is Corwin.", "Hi, what is my name?"],
    [["USER", "name", "Corwin"]], [(1, "has", "Corwin")])
add("identity_greeting", ["Good evening! What's your name?"], [],
    [(0, "has", "Premonition")])

# E. bare greetings (7)
for g in ["hello there", "hi again", "Hey!", "Good morning", "Hiya",
          "Hello, Premonition.", "good evening there"]:
    add("bare_greeting", [g], [], [(0, "has", GREET)])

# F. junk shapes: opener + comma + possessive teach (8) + guard-only (3)
F = [
    ("So, Pell's boss is Rhoda.", "Who is Pell's boss?",
     ["Pell", "boss", "Rhoda"]),
    ("Well, Dace's boss is Wren.", "Who is Dace's boss?",
     ["Dace", "boss", "Wren"]),
    ("Hey, Yara's boss is Lark.", "Who is Yara's boss?",
     ["Yara", "boss", "Lark"]),
    ("Okay, Ivo's job is carter.", "What is Ivo's job?",
     ["Ivo", "job", "carter"]),
    ("Look, Nessa's sister is Petra.", "Who is Nessa's sister?",
     ["Nessa", "sister", "Petra"]),
    ("Remember, Fenn's boss is Oskar.", "Who is Fenn's boss?",
     ["Fenn", "boss", "Oskar"]),
    ("Please, Lio's job is smith.", "What is Lio's job?",
     ["Lio", "job", "smith"]),
    ("Hi, Sela's boss is Bram.", "Who is Sela's boss?",
     ["Sela", "boss", "Bram"]),
]
for t, q, f in F:
    add("junk_shape", [t, q], [f], [(1, "has", f[2])])
add("junk_guardonly", ["Suppose, Pell's boss is Rhoda."], [],
    [(0, "not", "Saved")], note="pretend marker: never a fact")
add("junk_guardonly", ["Imagine Tobin's boss is Mara."], [],
    [(0, "not", "Saved")], note="pretend marker: never a fact")
add("junk_guardonly", ["Pell's boss is Rhoda.",
                       "Actually, Pell's boss is Mara."],
    [["Pell", "boss", "Mara"]], [(1, "has", "Mara")],
    note="correction marker kept by the head")

# G. name traps: listed-looking words that are names/titles (10)
G = [
    ("Hope's boss is Dace.", "Who is Hope's boss?", ["Hope", "boss", "Dace"]),
    ("Will Tarn's boss is Dace.", "Who is Will Tarn's boss?",
     ["Will Tarn", "boss", "Dace"]),
    ("Marnie's favorite song is Hey Jude.",
     "What is Marnie's favorite song?",
     ["Marnie", "favorite_song", "Hey Jude"]),
    ("So Long Summer's author is Fenn.", "Who is So Long Summer's author?",
     ["So Long Summer", "author", "Fenn"]),
    ("Hey Jude's writer is Fenn.", "Who is Hey Jude's writer?",
     ["Hey Jude", "writer", "Fenn"]),
    ("Grace works at Holloway.", "Where does Grace work?",
     ["Grace", "employer", "Holloway"]),
    ("May lives in Tollan.", "Where does May live?",
     ["May", "city", "Tollan"]),
    ("Joy's sister is Faith.", "Who is Joy's sister?",
     ["Joy", "sister", "Faith"]),
    ("Mark's boss is Rose.", "Who is Mark's boss?",
     ["Mark", "boss", "Rose"]),
    ("Sunny was born in Varn.", "Where was Sunny born?",
     ["Sunny", "place_of_birth", "Varn"]),
]
for t, q, f in G:
    add("name_trap", [t, q], [f], [(1, "has", f[2])])

# G2. no punctuation, capitalised opener: hard mode strips a one-word
# opener before ONE capitalised word; soft mode (greeting, or 2+ capitalised
# words: a possible title) keeps the base whenever it acts (4)
add("opener_plain", ["So Marnie lives in Tollan.", "Where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")])
add("title_cant_tell", ["Hey Jude was written by Fenn."], None, same=True)
add("title_cant_tell", ["So Long Summer was written by Fenn."], None,
    same=True)
add("opener_plain", ["Well Tarn's boss is Dace.", "Who is Tarn's boss?"],
    [["Tarn", "boss", "Dace"]], [(1, "has", "Dace")])
# G3. more opener shapes (3)
add("opener_comma", ["Actually, Marnie lives in Tollan.",
                     "Where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")])
add("opener_comma", ["Oh yeah, and Pell's boss is Rhoda.",
                     "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", "Rhoda")])
add("bare_greeting", ["Hi there, Premonition!"], [], [(0, "has", GREET)])

# H. question traps: opener questions must never write (7)
add("question_trap", ["So, who is Mira's boss?"], [], [(0, "not", "Saved")])
add("question_trap", ["Oh, Pell's boss is Rhoda?"], [],
    [(0, "not", "Saved")])
add("question_trap", ["Hey, is Tobin's boss Mara?"], [],
    [(0, "not", "Saved")])
add("question_trap", ["Hi! Who is Pell's boss?"], [], [(0, "not", "Saved")])
add("question_trap", ["Well, where does Yara live?"], [],
    [(0, "not", "Saved")])
add("question_trap", ["Btw, what is Kestrel's job?"], [],
    [(0, "not", "Saved")])
add("question_trap", ["Pell's boss is Rhoda.", "Okay, Pell's boss is who?"],
    [["Pell", "boss", "Rhoda"]], [(1, "not", "Saved")])

# I. restart cases (5)
add("restart", ["Please, Kestrel's job is fisher.", "__RESTART__",
                "What is Kestrel's job?"],
    [["Kestrel", "job", "fisher"]], [(1, "has", "fisher")])
add("restart", ["So, Marnie lives in Tollan.", "__RESTART__",
                "Hi! Where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")])
add("restart", ["Pell's boss is Rhoda.", "__RESTART__", "hello there",
                "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", GREET), (2, "has", "Rhoda")])
add("restart", ["So, blorp the fizzle.", "__RESTART__",
                "Oh, and Pell's boss is Rhoda.", "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(2, "has", "Rhoda")])
add("restart", ["Hey, my name is Corwin.", "__RESTART__",
                "Hi, what is my name?"],
    [["USER", "name", "Corwin"]], [(1, "has", "Corwin")])

# J. fallback fidelity: rest not understood -> exactly the base (5)
add("fallback", ["So, blorp the fizzle.", "Where did you learn that?"],
    [], same=True)
add("fallback", ["Pell's boss is Rhoda.", "Well, the thing about it.",
                 "Say that again."], [["Pell", "boss", "Rhoda"]], same=True)
add("fallback", ["Pell's boss is Rhoda.", "Hi, flarn morp?",
                 "Where did you learn that?"],
    [["Pell", "boss", "Rhoda"]], same=True)
add("fallback", ["Okay.", "Ok thanks!", "Hi, how are you?"], [], same=True)
add("fallback", ["Hello.", "Hi!", "Hey!"], [], same=True)

# K. controls: no opener, byte-identical to base (6)
add("control", ["Pell's boss is Rhoda.", "Who is Pell's boss?"],
    [["Pell", "boss", "Rhoda"]], [(1, "has", "Rhoda")], same=True)
add("control", ["Marnie lives in Tollan.", "Where does Marnie live?"],
    [["Marnie", "city", "Tollan"]], [(1, "has", "Tollan")], same=True)
add("control", ["What's your name?", "How are you?"], [], same=True)
add("control", ["Who is Tobin's boss?"], [], same=True)
add("control", ["Kestrel's job is fisher.", "Kestrel's job is miller.",
                "yes", "What is Kestrel's job?"],
    [["Kestrel", "job", "miller"]], same=True)
add("control", ["Thanks!", "Goodbye."], [], same=True)

# L. user name with openers keeps its confirm flow (3)
add("username", ["Hey, my name is Corwin.", "What is my name?"],
    [["USER", "name", "Corwin"]], [(1, "has", "Corwin")])
add("username", ["My name is Corwin.", "Oh, my name is Tarn.", "yes",
                 "What is my name?"],
    [["USER", "name", "Tarn"]], [(1, "has", "change"), (3, "has", "Tarn")])
add("username", ["My name is Corwin.", "So, my name is Tarn.", "no",
                 "What is my name?"],
    [["USER", "name", "Corwin"]], [(1, "has", "change"),
                                   (3, "has", "Corwin")])

# I. hard mode, no comma: the opener may not become part of the subject (12)
NC = [
    ("So Pell's boss is Rhoda.", "Who is Pell's boss?", ["Pell", "boss", "Rhoda"]),
    ("so Brann's sister is Liesl.", "Who is Brann's sister?", ["Brann", "sister", "Liesl"]),
    ("Btw Orrin's job is baker.", "What is Orrin's job?", ["Orrin", "job", "baker"]),
    ("Um Idris's boss is Tamsin.", "Who is Idris's boss?", ["Idris", "boss", "Tamsin"]),
    ("Please Kestrel's job is fisher.", "What is Kestrel's job?", ["Kestrel", "job", "fisher"]),
    ("Anyway Pell works at Brisk.", "Where does Pell work?", ["Pell", "employer", "Brisk"]),
    ("Okay Marnie lives in Tollan.", "Where does Marnie live?", ["Marnie", "city", "Tollan"]),
    ("Listen Corwin's job is baker.", "What is Corwin's job?", ["Corwin", "job", "baker"]),
    ("And Liesl's boss is Rhoda.", "Who is Liesl's boss?", ["Liesl", "boss", "Rhoda"]),
    ("By the way Tamsin's boss is Dace.", "Who is Tamsin's boss?", ["Tamsin", "boss", "Dace"]),
    ("Also Brann lives in Varn.", "Where does Brann live?", ["Brann", "city", "Varn"]),
    ("Hi Orrin lives in Varn.", "Where does Orrin live?", ["Orrin", "city", "Varn"]),
]
for t, q, f in NC:
    add("opener_nocomma", [t, q], [f], [(1, "has", f[2])])
# J. soft mode known limits: exactly the base (2)
add("title_cant_tell", ["Hey Pell's boss is Rhoda."], None, same=True,
    note="known limit: greeting + one capitalised word, no comma (Hey Jude)")
add("title_cant_tell", ["So Bram Kite's boss is Rhoda."], None, same=True,
    note="known limit: 2+ capitalised words after a no-comma opener")

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(C, indent=1), encoding="utf-8")
    fams = {}
    for c in C:
        fams[c["family"]] = fams.get(c["family"], 0) + 1
    print(len(C), fams)
    sys.exit(0)
