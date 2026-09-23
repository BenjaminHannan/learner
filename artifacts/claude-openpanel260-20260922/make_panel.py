"""Build the openpanel260 blind panel (80 items) -> panel.jsonl.
Deterministic: no randomness. All names are invented.
Run from the repo root: python -B artifacts/claude-openpanel260-20260922/make_panel.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "panel.jsonl"
HELLO_NOTE = ('base reply to plain "Hello." = '
              "'Hi! Teach me like \"Tom's boss is Ann.\" Ask me like \"Who is Tom's boss?\"'")

# fact kinds: ("pos", subj, rel, val) possessive; ("lives", s, v); ("works", s, v); ("born", s, v)
def teach_text(f):
    k = f[0]
    if k == "pos":
        return f"{f[1]}'s {f[2]} is {f[3]}."
    if k == "lives":
        return f"{f[1]} lives in {f[2]}."
    if k == "works":
        return f"{f[1]} works at {f[2]}."
    if k == "born":
        return f"{f[1]} was born in {f[2]}."
    raise ValueError(k)

def triple(f):
    k = f[0]
    if k == "pos":
        return [f[1], f[2].replace(" ", "_"), f[3]]
    rel = {"lives": "city", "works": "employer", "born": "place_of_birth"}[k]
    return [f[1], rel, f[2]]

def question(f):
    k = f[0]
    if k == "pos":
        w = "What" if f[2] in ("job",) else "Who"
        return f"{w} is {f[1]}'s {f[2]}?"
    return {"lives": f"Where does {f[1]} live?", "works": f"Where does {f[1]} work?",
            "born": f"Where was {f[1]} born?"}[k]

def value(f):
    return f[3] if f[0] == "pos" else f[2]

def lower_first(s):
    return s[0].lower() + s[1:]

def upper_first(s):
    return s[0].upper() + s[1:]

items = []
def add(family, setup, turn, followup, stated, expect, gold, plain, note):
    items.append(dict(family=family, setup=setup, turn=turn, followup=followup,
                      stated_facts=stated, expect_store=expect, gold=gold,
                      plain_turn=plain, note=note))

# 1. opener_teach (20): (opener prefix as typed, fact)
OT = [
    ("So, ", ("pos", "Dorrit", "boss", "Fenwick")),
    ("Well, ", ("lives", "Amsel", "Corrowmere")),
    ("Oh and ", ("works", "Tamsk", "Pellwick Foundry")),
    ("Also ", ("pos", "Ruvena", "job", "weaver")),
    ("Okay so ", ("pos", "Varnet", "sister", "Olwen")),
    ("Alright, ", ("born", "Hollin", "Dunmarrow")),
    ("Right, ", ("pos", "Sefton", "friend", "Corvane")),
    ("Actually, ", ("works", "Pellam", "Grisly Hook Bakery")),
    ("Anyway, ", ("pos", "Ottrin", "teacher", "Belvane")),
    ("Btw ", ("lives", "Quenby", "Tessmoor")),
    ("FYI, ", ("pos", "Lodric", "mother", "Anwen")),
    ("Listen, ", ("works", "Carrow", "Tinmouth Press")),
    ("Look, ", ("pos", "Evrard", "boss", "Sibbeth")),
    ("Um, ", ("lives", "Nellick", "Stoneharrow")),
    ("By the way, ", ("pos", "Parro", "job", "cooper")),
    ("Fun fact: ", ("born", "Tibble", "Ashcombe Vale")),
    ("Just so you know, ", ("works", "Wendrel", "Copperlane Mill")),
    ("For the record, ", ("pos", "Ysmay", "friend", "Dunstan")),
    ("Oh yeah, ", ("pos", "Gorlan", "boss", "Ettie")),
    ("Quick one: ", ("lives", "Merrit", "Fallowby")),
]
for op, f in OT:
    t = teach_text(f)
    add("opener_teach", [], op + t, question(f), [triple(f)], [triple(f)], value(f), t,
        f"opener '{op.strip()}' + {f[0]} teach")

# 2. opener_question (12): (opener, fact)
OQ = [
    ("So, ", ("pos", "Harl", "boss", "Minta")),
    ("Okay, ", ("lives", "Brisa", "Kettlewick")),
    ("Well, ", ("works", "Orrin", "Saltmarsh Forge")),
    ("Oh, ", ("pos", "Pessa", "job", "chandler")),
    ("And ", ("pos", "Tolly", "sister", "Averil")),
    ("But ", ("born", "Keddy", "Brightwater Ford")),
    ("Um, ", ("pos", "Brinn", "friend", "Oswy")),
    ("Ok, ", ("lives", "Varro", "Mossbank")),
    ("Hey, ", ("pos", "Seffa", "job", "thatcher")),
    ("Btw, ", ("pos", "Lusk", "teacher", "Hebden")),
    ("Quick question: ", ("works", "Anneth", "Ravel Lane Dairy")),
    ("Alright, ", ("pos", "Corla", "mother", "Isaura")),
]
for op, f in OQ:
    q = question(f)
    add("opener_question", [teach_text(f)], op + lower_first(q), "", [], [], value(f), q,
        f"opener '{op.strip()}' + {f[0]} question after plain teach")

# 3. greeting_question (8)
GQ = [
    ("Hi! ", ("pos", "Dunmore", "boss", "Fayre"), False),
    ("Hello, ", ("lives", "Jessamy", "Pinwhistle"), True),
    ("Hey there, ", ("pos", "Rudd", "job", "cartwright"), True),
    ("Good morning! ", ("works", "Talwyn", "Wickham Loom House"), False),
    ("Hiya, ", ("pos", "Oriel", "friend", "Cobb"), True),
    ("Hi there, ", ("born", "Emrys", "Longmarrow"), True),
]
for op, f, low in GQ:
    q = question(f)
    add("greeting_question", [teach_text(f)], op + (lower_first(q) if low else q), "", [], [],
        value(f), q, f"greeting '{op.strip()}' + {f[0]} question after plain teach")
add("greeting_question", [], "Hi! What's your name?", "", [], [], "Premonition",
    "What's your name?", "greeting + assistant-name question")
add("greeting_question", [], "Hello there, what is your name?", "", [], [], "Premonition",
    "What is your name?", "greeting + assistant-name question")

# 4. bare_greeting (6)
for g in ["hello there", "hi again", "hey!", "good morning", "hiya", "Hello, Premonition."]:
    add("bare_greeting", [], g, "", [], [], "", "", "bare greeting; " + HELLO_NOTE)

# 5. name_trap (10)
NT = [
    ("pos", "Hope", "boss", "Tavish"),
    ("lives", "Will", "Brackenfold"),
    ("works", "Grace", "Oakum Street Bakery"),
    ("pos", "Joy", "job", "potter"),
    ("born", "Sunny", "Wethermoor"),
    ("pos", "Mark", "friend", "Oswin"),
    ("pos", "May", "sister", "Idony"),
    ("lives", "Pat", "Hollowbeck Cross"),
    ("pos", "So Long Summer", "author", "Brenna Vosk"),
    ("pos", "Hey Marlow", "singer", "Dessa Crane"),
]
for f in NT:
    first = f[1].split()[0]
    add("name_trap", [], teach_text(f), question(f), [triple(f)], [triple(f)], value(f), "",
        f"first word '{first}' is part of the name, not an opener")

# 6. junk_guard (8): opener + comma + possessive teach
JG = [
    ("Please, ", ("pos", "Tamsin", "job", "miller")),
    ("So, ", ("pos", "Cadell", "friend", "Wren")),
    ("Well, ", ("pos", "Orla", "sister", "Fenna")),
    ("Okay, ", ("pos", "Bexley", "teacher", "Rook")),
    ("Oh, ", ("pos", "Pollard", "mother", "Thea")),
    ("Hey, ", ("pos", "Linnet", "boss", "Garrick")),
    ("Listen, ", ("pos", "Vashti", "job", "glazier")),
    ("Btw, ", ("pos", "Ellery", "sister", "Nim")),
]
for op, f in JG:
    t = teach_text(f)
    add("junk_guard", [], op + t, question(f), [triple(f)], [triple(f)], value(f), t,
        f"opener '{op.strip()}' + comma + possessive; base may store opener in subject")

# 7. control (16): 8 plain teaches + followups, 8 plain questions after plain teaches
CT = [
    ("pos", "Pennick", "boss", "Ulric"),
    ("lives", "Moira", "Scarrowby"),
    ("works", "Faddle", "Tuppence Row Mill"),
    ("pos", "Hesper", "job", "farrier"),
    ("born", "Rendle", "Oxbury Cross"),
    ("pos", "Cazimir", "friend", "Tove"),
    ("pos", "Liesl", "sister", "Wynne"),
    ("pos", "Dellow", "teacher", "Alaric"),
]
for f in CT:
    add("control", [], teach_text(f), question(f), [triple(f)], [triple(f)], value(f), "",
        f"plain {f[0]} teach + followup")
CQ = [
    (("pos", "Abberly", "boss", "Kenrick"), None),
    (("lives", "Soren", "Hatchmere"), None),
    (("works", "Ivet", "Lantern Yard Press"), None),
    (("pos", "Morwen", "job", "fletcher"), None),
    (("born", "Tarquin", "Elmscarrow"), None),
    (("pos", "Quilla", "friend", "Rhosyn"), None),
    (("pos", "Bede", "mother", "Ottilie"), None),
    (("lives", "Cressida", "Ambersey"), "What city does Cressida live in?"),
]
for f, q in CQ:
    add("control", [teach_text(f)], q or question(f), "", [], [], value(f), "",
        f"plain {f[0]} question after plain teach")

assert len(items) == 80, len(items)
FIELDS = ["id", "family", "setup", "turn", "followup", "stated_facts", "expect_store",
          "gold", "plain_turn", "note"]
with OUT.open("w") as fh:
    for i, it in enumerate(items, 1):
        it["id"] = f"o260-{i:03d}"
        fh.write(json.dumps({k: it[k] for k in FIELDS}, ensure_ascii=False) + "\n")
print(f"wrote {len(items)} items to {OUT}")
