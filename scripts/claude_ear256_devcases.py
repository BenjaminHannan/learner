#!/usr/bin/env python3
"""Exp 256 dev cases (my own wordings, fictional names). Panel-254-like schema
plus two dev-only families: fixed (must-not-change acts; scored byte-identical
to base138l) and restart ("__RESTART__" inside setup rebuilds the daemon).

Writes artifacts/claude-earloop256-20260922/dev_cases.jsonl
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "artifacts/claude-earloop256-20260922/dev_cases.jsonl"

AL = {  # one fixed alias list per relation
    "city": ["lives_in", "town", "home"], "employer": ["work_location", "workplace", "works_at"],
    "occupation": ["job", "profession"], "dog": ["pet"], "cat": ["pet"], "sister": [], "brother": [],
    "mother": ["mom", "mum"], "best_friend": ["friend"], "friend": ["best_friend"],
    "hometown": ["home_town", "origin"], "place_of_birth": ["birthplace"], "language": [],
    "favorite_color": ["favourite_colour", "favorite_colour", "favourite_color"], "boss": ["manager"],
    "spouse": ["wife", "husband", "partner"], "neighbour": ["neighbor"], "teacher": [], "school": [],
}


def g(s, r, v):
    return {"subject": s, "relation": r, "relation_aliases": AL.get(r, []), "value": v}


items = []


def add(fam, setup, turn, followup, store, ans, mn, note):
    items.append(dict(family=fam, setup=setup, turn=turn, followup=followup, gold_store=store,
                      gold_answer=ans, must_not=mn, note=note))


# ---- teach_varied (T) 16
add("teach_varied", [], "Oriel Dunmore works as a glassblower.", "What is Oriel Dunmore's occupation?",
    [g("Oriel Dunmore", "occupation", "glassblower")], "glassblower", [], "works as")
add("teach_varied", [], "Tessaly teaches at Harrowgate School.", "What is Tessaly's employer?",
    [g("Tessaly", "employer", "Harrowgate School")], "Harrowgate School", [], "teaches at")
add("teach_varied", [], "I have a dog called Pumble.", "What is my dog?",
    [g("me", "dog", "Pumble")], "Pumble", [], "have a dog called")
add("teach_varied", [], "My cat is named Wisp.", "What is my cat?", [g("me", "cat", "Wisp")], "Wisp", [],
    "is named")
add("teach_varied", [], "Brannoc grew up in Saltmere.", "What is Brannoc's hometown?",
    [g("Brannoc", "hometown", "Saltmere")], "Saltmere", [], "grew up in")
add("teach_varied", [], "Liss moved to Corrow last spring.", "What is Liss's city?",
    [g("Liss", "city", "Corrow")], "Corrow", [], "moved to")
add("teach_varied", [], "Quen's brother, Adair Voss, lives in Pellby.", "What is Adair Voss's city?",
    [g("Quen", "brother", "Adair Voss"), g("Adair Voss", "city", "Pellby")], "Pellby", [], "appositive two facts")
add("teach_varied", [], "My sister is called Mirren.", "Who is my sister?", [g("me", "sister", "Mirren")],
    "Mirren", [], "is called")
add("teach_varied", [], "Dovan was born in Ketterholm.", "What is Dovan's place of birth?",
    [g("Dovan", "place_of_birth", "Ketterholm")], "Ketterholm", [], "born in")
add("teach_varied", [], "Halla speaks Norrish.", "What is Halla's language?", [g("Halla", "language", "Norrish")],
    "Norrish", [], "speaks")
add("teach_varied", [], "Garrick Penhallow is married to Ysolde.", "Who is Garrick Penhallow's spouse?",
    [g("Garrick Penhallow", "spouse", "Ysolde")], "Ysolde", [], "married to")
add("teach_varied", [], "Ochre is Pim's favourite colour.", "What is Pim's favorite color?",
    [g("Pim", "favorite_color", "Ochre")], "Ochre", [], "inverted")
add("teach_varied", [], "Ferris's boss is Imelda Crane, and she lives in Otterbeck.", "What is Imelda Crane's city?",
    [g("Ferris", "boss", "Imelda Crane"), g("Imelda Crane", "city", "Otterbeck")], "Otterbeck", [],
    "two facts pron")
add("teach_varied", [], "My best friend Sorrel lives in Wick Harbour.", "What is Sorrel's city?",
    [g("me", "best_friend", "Sorrel"), g("Sorrel", "city", "Wick Harbour")], "Wick Harbour", [], "two facts")
add("teach_varied", [], "I work at Brindle Foundry.", "What is my employer?",
    [g("me", "employer", "Brindle Foundry")], "Brindle Foundry", [], "I work at")
add("teach_varied", [], "Tamsyn has a neighbour called Corvin Ash.", "Who is Tamsyn's neighbour?",
    [g("Tamsyn", "neighbour", "Corvin Ash")], "Corvin Ash", [], "has a X called")

# ---- ask_varied (A) 14
AV = [
    ("Oriel's city is Dovecote.", "Where does Oriel live?", g("Oriel", "city", "Dovecote"), "Dovecote", "verb q"),
    ("Brannoc's employer is Kestrel Mills.", "where does brannoc work", g("Brannoc", "employer", "Kestrel Mills"),
     "Kestrel Mills", "lower noq"),
    ("My dog is Pumble.", "What's my dog called?", g("me", "dog", "Pumble"), "Pumble", "called"),
    ("Halla's language is Norrish.", "What language does Halla speak?", g("Halla", "language", "Norrish"),
     "Norrish", "verb q"),
    ("Dovan's place of birth is Ketterholm.", "Where was Dovan born?", g("Dovan", "place_of_birth", "Ketterholm"),
     "Ketterholm", "verb q"),
    ("Liss's occupation is potter.", "What does Liss do for a living?", g("Liss", "occupation", "potter"), "potter",
     "idiom"),
    ("Quen's sister is Mirren.", "Do you know who Quen's sister is?", g("Quen", "sister", "Mirren"), "Mirren",
     "do you know"),
    ("My mother is Edda.", "Remind me who my mother is.", g("me", "mother", "Edda"), "Edda", "remind me"),
    ("Garrick's hometown is Saltmere.", "Where did Garrick grow up?", g("Garrick", "hometown", "Saltmere"),
     "Saltmere", "verb q"),
    ("Pim's favorite color is ochre.", "What colour does Pim like best?", g("Pim", "favorite_color", "ochre"),
     "ochre", "paraphrase"),
    ("Tessaly's boss is Imelda.", "who's tessaly's boss", g("Tessaly", "boss", "Imelda"), "Imelda", "lower noq"),
    ("Corvin's cat is Wisp.", "What is the name of Corvin's cat?", g("Corvin", "cat", "Wisp"), "Wisp", "name of"),
    ("My employer is Brindle Foundry.", "Where do I work?", g("me", "employer", "Brindle Foundry"),
     "Brindle Foundry", "first person verb"),
    ("Adair's spouse is Ysolde.", "Who is Adair married to?", g("Adair", "spouse", "Ysolde"), "Ysolde", "married to"),
]
for s, t, st, a, n in AV:
    add("ask_varied", [s], t, None, [st], a, [], n)

# ---- chain (A) 6
CH = [
    (["Oriel's sister is Mirren.", "Mirren's city is Pellby."], "Where does Oriel's sister live?",
     [g("Oriel", "sister", "Mirren"), g("Mirren", "city", "Pellby")], "Pellby"),
    (["My brother is Adair.", "Adair's employer is Kestrel Mills."], "Where does my brother work?",
     [g("me", "brother", "Adair"), g("Adair", "employer", "Kestrel Mills")], "Kestrel Mills"),
    (["Liss's boss is Imelda.", "Imelda's hometown is Saltmere."], "where did liss's boss grow up",
     [g("Liss", "boss", "Imelda"), g("Imelda", "hometown", "Saltmere")], "Saltmere"),
    (["My best friend is Sorrel.", "Sorrel's dog is Fitch."], "What's my best friend's dog called?",
     [g("me", "best_friend", "Sorrel"), g("Sorrel", "dog", "Fitch")], "Fitch"),
    (["Quen's mother is Edda.", "Edda's language is Norrish."], "What language does Quen's mother speak?",
     [g("Quen", "mother", "Edda"), g("Edda", "language", "Norrish")], "Norrish"),
    (["Dovan's teacher is Hedda.", "Hedda's place of birth is Ketterholm."], "Where was Dovan's teacher born?",
     [g("Dovan", "teacher", "Hedda"), g("Hedda", "place_of_birth", "Ketterholm")], "Ketterholm"),
]
for s, t, st, a in CH:
    add("chain", s, t, None, st, a, [], "chain")

# ---- backwards (A) 13 : X's R is Y ; Y's R is Z ; reverse question -> X, never Z
BW = [
    ("Oriel", "sister", "Mirren", "Lusa", "Whose sister is Mirren?"),
    ("Tamsin", "boss", "Hedda", "Maro", "Who does Hedda manage?"),
    ("Oriel", "employer", "Tamsin Vale", "Grest Co", "Who does Tamsin Vale employ?"),
    ("Pell", "teacher", "Hedda", "Maro", "Who does Hedda teach?"),
    ("Brannoc", "mentor", "Idris", "Calla", "Who does Idris mentor?"),
    ("Quen", "coach", "Arlo", "Bex", "Who does Arlo coach?"),
    ("Liss", "boss", "Imelda", "Garrow", "Who reports to Imelda?"),
    ("Dovan", "employer", "Kell Works", "Ostin Group", "Who works at Kell Works?"),
    ("Adair", "doctor", "Wenna", "Yorick", "Who does Wenna treat?"),
    ("Corvin", "best_friend", "Sorrel", "Tove", "Whose best friend is Sorrel?"),
    ("Halla", "mother", "Edda", "Runa", "Whose mother is Edda?"),
    ("Garrick", "teacher", "Selk", "Anwen", "Who is Selk the teacher of?"),
    ("Tobin", "boss", "Nell", "Ruck", "Who works for Nell?"),
]
for x, r, y, z, q in BW:
    rw = r.replace("_", " ")
    add("backwards", [f"{x}'s {rw} is {y}.", f"{y}'s {rw} is {z}."], q, None,
        [g(x, r, y), g(y, r, z)], x, [z], "back")

# ---- no_save 16 (10 statement-shaped questions + 6 other)
NS = [
    (["Oriel's city is Dovecote."], "So Oriel lives in Pellby?", [g("Oriel", "city", "Dovecote")], ["Pellby"], "stmtq"),
    ([], "Brannoc works at Kestrel Mills, right?", [], ["Kestrel Mills"], "stmtq"),
    ([], "so pell has a cat called wisp?", [], ["wisp"], "stmtq lower"),
    ([], "Halla speaks Norrish, doesn't she?", [], ["Norrish"], "stmtq"),
    ([], "Dovan was born in Ketterholm?", [], ["Ketterholm"], "stmtq"),
    ([], "Liss's boss is Imelda?", [], ["Imelda"], "stmtq"),
    ([], "and Quen's sister is Mirren, yeah?", [], ["Mirren"], "stmtq"),
    ([], "My brother lives in Corrow?", [], ["Corrow"], "stmtq"),
    ([], "Garrick is married to Ysolde, isn't he?", [], ["Ysolde"], "stmtq"),
    ([], "Tessaly teaches at Harrowgate School?", [], ["Harrowgate School"], "stmtq"),
    ([], "If Oriel moved to Pellby she'd be happier.", [], ["Pellby"], "hypo"),
    ([], "Someone told me Brannoc works at Kestrel Mills.", [], ["Kestrel Mills"], "hearsay"),
    ([], "Halla doesn't speak Norrish.", [], ["Norrish"], "negation"),
    ([], "Dovan might move to Corrow next year.", [], ["Corrow"], "plan"),
    ([], "I wonder whether Liss's boss is Imelda.", [], ["Imelda"], "wonder"),
    ([], "Maybe Quen's dog is Fitch, I'm not sure.", [], ["Fitch"], "hedge"),
]
for s, t, st, mn, n in NS:
    add("no_save", s, t, None, st, None, mn, n)

# ---- casual 10 (5 T, 5 A)
add("casual", [], "ok so my freind Sorrel lives in wick harbour", "What is Sorrel's city?",
    [g("me", "friend", "Sorrel"), g("Sorrel", "city", "wick harbour")], "wick harbour", [], "T: typo lower two facts")
add("casual", [], "btw my dogs name is fitch", "What is my dog?", [g("me", "dog", "fitch")], "fitch", [],
    "T: lower apos")
add("casual", [], "oriel works at kestrel mills lol", "What is oriel's employer?",
    [g("oriel", "employer", "kestrel mills")], "kestrel mills", [], "T: lower filler")
add("casual", [], "my favrite color is teal", "What is my favorite color?", [g("me", "favorite_color", "teal")],
    "teal", [], "T: typo lower")
add("casual", [], "halla lives in dovecote now", "What is halla's city?", [g("halla", "city", "dovecote")],
    "dovecote", [], "T: lower")
for s, t, st, a, n in [
    ("Brannoc's city is Saltmere.", "wats brannoc's city", g("Brannoc", "city", "Saltmere"), "Saltmere", "A: typo noq"),
    ("My sister is Mirren.", "whos my sister", g("me", "sister", "Mirren"), "Mirren", "A: apos noq"),
    ("Pell's employer is Kell Works.", "where dose pell work", g("Pell", "employer", "Kell Works"), "Kell Works",
     "A: typo noq"),
    ("Liss's cat is Wisp.", "what's liss's cat called lol", g("Liss", "cat", "Wisp"), "Wisp", "A: lower filler"),
    ("My brother is Adair.", "hey whats my brothers name", g("me", "brother", "Adair"), "Adair", "A: apos noq"),
]:
    add("casual", [s], t, None, [st], a, [], n)

# ---- fixed (must-not-change acts; byte-identical to base138l) 14
FX = [
    ([], "Hello!", None), ([], "Thanks so much!", None), ([], "What is your name?", None),
    ([], "What can you do?", None), ([], "My name is Tovin.", "What is my name?"), ([], "How old are you?", None),
    (["Oriel's city is Dovecote."], "No, Oriel's city is Pellby.", "What is Oriel's city?"),
    (["Oriel's city is Dovecote."], "Forget Oriel's city.", "What is Oriel's city?"),
    (["Oriel's city is Dovecote.", "What is Oriel's city?"], "How do you know that?", None),
    (["Oriel's city is Dovecote.", "What is Oriel's city?"], "Say that again.", None),
    ([], "Tell me about yourself.", None), ([], "Who made you?", None), ([], "ok", None),
    (["Oriel's city is Dovecote."], "Oriel's city is not Dovecote.", None),
]
for s, t, f in FX:
    add("fixed", s, t, f, [], None, [], "fixed act")

# ---- restart 6
add("restart", ["Oriel works at Kestrel Mills.", "__RESTART__"], "Where does Oriel work?", None,
    [g("Oriel", "employer", "Kestrel Mills")], "Kestrel Mills", [], "A: ear teach, restart, everyday ask")
add("restart", ["I have a dog called Pumble.", "__RESTART__"], "What's my dog called?", None,
    [g("me", "dog", "Pumble")], "Pumble", [], "A")
add("restart", ["Halla speaks Norrish.", "__RESTART__"], "Halla speaks Norrish.", "What language does Halla speak?",
    [g("Halla", "language", "Norrish")], "Norrish", [], "T: duplicate after restart")
add("restart", ["Oriel's sister is Mirren.", "Mirren moved to Pellby.", "__RESTART__"],
    "Where does Oriel's sister live?", None, [g("Oriel", "sister", "Mirren"), g("Mirren", "city", "Pellby")],
    "Pellby", [], "A: chain after restart")
add("restart", ["My best friend is Sorrel.", "__RESTART__"], "Who's my best friend?", None,
    [g("me", "best_friend", "Sorrel")], "Sorrel", [], "A")
add("restart", ["Brannoc grew up in Saltmere.", "__RESTART__", "Brannoc grew up in Saltmere."],
    "Where did Brannoc grow up?", None, [g("Brannoc", "hometown", "Saltmere")], "Saltmere", [],
    "A: duplicate teach after restart")

for i, it in enumerate(items, 1):
    it["id"] = f"d256-{i:03d}"
OUT.write_text("".join(json.dumps({k: it[k] for k in ("id", "family", "setup", "turn", "followup", "gold_store",
                                                     "gold_answer", "must_not", "note")}) + "\n" for it in items))
from collections import Counter  # noqa: E402
print(len(items), Counter(i["family"] for i in items))
