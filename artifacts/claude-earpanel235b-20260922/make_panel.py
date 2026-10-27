"""Ear panel 235b generator (TEST-ONLY). Items are written by hand below.

Run from the repo root:
    python3 -B artifacts/claude-earpanel235b-20260922/make_panel.py
Writes artifacts/claude-earpanel235b-20260922/panel.jsonl deterministically and
runs the spec's self-checks (exits non-zero if any fails).
"""
import json
import os
import re
import sys

OUT = os.path.join("artifacts", "claude-earpanel235b-20260922", "panel.jsonl")

# One fixed alias list per relation.
ALIASES = {
    "city": ["lives_in", "residence", "location", "current_city"],
    "hometown": ["grew_up_in", "home_town"],
    "place_of_birth": ["birthplace", "born_in"],
    "employer": ["workplace", "works_at", "company"],
    "workplace": ["employer", "works_at", "place_of_work"],
    "school": ["studies_at", "college", "university"],
    "job": ["occupation", "profession", "work"],
    "boss": ["manager", "supervisor"],
    "sister": ["sibling"],
    "brother": ["sibling"],
    "spouse": ["husband", "wife", "married_to"],
    "partner": ["girlfriend", "boyfriend", "significant_other"],
    "language": ["speaks", "languages"],
    "pet": ["pets", "dog", "cat", "animal"],
    "mother": ["mom", "mum", "parent"],
    "father": ["dad", "parent"],
    "stepfather": ["stepdad"],
    "cousin": [],
    "uncle": [],
    "grandmother": ["grandma", "gran"],
    "daughter": ["child"],
    "roommate": ["flatmate", "housemate"],
    "neighbor": ["neighbour"],
    "best_friend": ["friend", "bff"],
    "colleague": ["coworker", "co_worker"],
    "sister_in_law": [],
    "instrument": ["plays"],
    "favorite_food": ["favourite_food"],
}


def T(subject, relation, value):
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": list(ALIASES[relation]), "value": value}


def A(subject, relation, chain=None):
    if chain is not None:
        assert len(chain) == 2 and chain[1] == relation
    return {"act": "ASK", "subject": subject, "relation": relation,
            "chain": list(chain) if chain else None,
            "relation_aliases": list(ALIASES[relation])}


def C2(subject, first, second):
    return A(subject, second, [first, second])


ITEMS = []  # (family, turn, gold, clear, notes)


def add(family, turn, gold, clear=True, notes=""):
    ITEMS.append((family, turn, gold, clear, notes))


# ---------------- plain_teach (25) ----------------
F = "plain_teach"
add(F, "My sister is Pernille.", [T("me", "sister", "Pernille")])
add(F, "Davor lives in Kestwick.", [T("Davor", "city", "Kestwick")])
add(F, "my boss is Hanne Soraby", [T("me", "boss", "Hanne Soraby")], notes="lowercase")
add(F, "Idris works at Tollbeck Mills.", [T("Idris", "employer", "Tollbeck Mills")])
add(F, "i have a cat named Pumpernickel", [T("me", "pet", "Pumpernickel")], notes="lowercase")
add(F, "Mirela speaks Vostric.", [T("Mirela", "language", "Vostric")])
add(F, "Fenwick was born in Ulmsby.", [T("Fenwick", "place_of_birth", "Ulmsby")])
add(F, "my roommate is Tavish", [T("me", "roommate", "Tavish")], notes="lowercase")
add(F, "Brannoch is a plumber.", [T("Brannoch", "job", "plumber")])
add(F, "Lusia's husband is Emeric.", [T("Lusia", "spouse", "Emeric")])
add(F, "I live in Saltmarrow.", [T("me", "city", "Saltmarrow")])
add(F, "i work at Pellam Freight btw", [T("me", "employer", "Pellam Freight")], notes="lowercase, btw")
add(F, "Odalys is my cousin.", [T("me", "cousin", "Odalys")], notes="value-first order")
add(F, "Cato has a dog called Waffles.", [T("Cato", "pet", "Waffles")])
add(F, "Yevgenia plays the cello", [T("Yevgenia", "instrument", "cello")])
add(F, "my dad is Gerrit", [T("me", "father", "Gerrit")], notes="lowercase")
add(F, "Sunniva is a nurse lol", [T("Sunniva", "job", "nurse")], notes="lol")
add(F, "Tamlyn's brother is Arno.", [T("Tamlyn", "brother", "Arno")])
add(F, "My best friend is Quillon.", [T("me", "best_friend", "Quillon")])
add(F, "Rasmin lives in Old Veddick.", [T("Rasmin", "city", "Old Veddick")])
add(F, "i speak Tarnic and a bit of Ossel", [T("me", "language", "Tarnic"), T("me", "language", "Ossel")],
    notes="two languages")
add(F, "Halvard's manager is Bettina.", [T("Halvard", "boss", "Bettina")])
add(F, "Zofie grew up in Mereditch.", [T("Zofie", "hometown", "Mereditch")], clear=False,
    notes="grew up in = hometown; place_of_birth also defensible; never city")
add(F, "my neighbour is Orrin Blay", [T("me", "neighbor", "Orrin Blay")], notes="lowercase")
add(F, "Kasimir's favourite food is dumplings", [T("Kasimir", "favorite_food", "dumplings")])

# ---------------- varied_teach (30) ----------------
F = "varied_teach"
add(F, "my cousin is Delphy and she lives in Norrowby",
    [T("me", "cousin", "Delphy"), T("Delphy", "city", "Norrowby")], notes="R1 she=Delphy")
add(F, "my brother is Jory and he lives in Callowmere, i live in Dunstray tho",
    [T("me", "brother", "Jory"), T("Jory", "city", "Callowmere"), T("me", "city", "Dunstray")],
    notes="R1 rel+I he=Jory (relative) plus first-person clause")
add(F, "my sister's called Ottilie and she speaks Brevan, i only speak Lusk",
    [T("me", "sister", "Ottilie"), T("Ottilie", "language", "Brevan"), T("me", "language", "Lusk")],
    notes="R1 rel+I she=Ottilie (relative) plus first-person clause")
add(F, "Kaspar started at Brundle Optics last week, he moved to Vinterby for it",
    [T("Kaspar", "employer", "Brundle Optics"), T("Kaspar", "city", "Vinterby")],
    notes="R1 he=Kaspar; started at = employer; moved to = city")
add(F, "i met Maribel at the gym and she has a parrot named Jubjub",
    [T("Maribel", "pet", "Jubjub")], notes="R1 she=Maribel; meeting place not saved")
add(F, "my uncle is Leofric and he's a baker, i'm a baker too actually",
    [T("me", "uncle", "Leofric"), T("Leofric", "job", "baker"), T("me", "job", "baker")],
    notes="R1 rel+I he=Leofric (relative) plus first-person clause")
add(F, "Thessa and her wife Ondine live in Carrowdown",
    [T("Thessa", "spouse", "Ondine"), T("Thessa", "city", "Carrowdown"), T("Ondine", "city", "Carrowdown")],
    notes="R1 her=Thessa; both live there")
add(F, "i know who Garrick's boss is, it's Mabry", [T("Garrick", "boss", "Mabry")],
    notes="R2 question word inside a statement; states a fact")
add(F, "guess where Evadne lives now... Portsallow", [T("Evadne", "city", "Portsallow")],
    notes="R2 question word inside a statement; states a fact")
add(F, "what Ignatius does for work: he's an electrician.", [T("Ignatius", "job", "electrician")],
    notes="R2 question word inside a statement; states a fact")
add(F, "that's why Philippa moved to Grellstone lol", [T("Philippa", "city", "Grellstone")],
    notes="R2 question word inside a statement; moved to = city")
add(F, "Cordelia teaches at Wexcombe Primary School", [T("Cordelia", "workplace", "Wexcombe Primary School")],
    notes="R3 teaches at = workplace, not school")
add(F, "Florian studies at Aldermoor College", [T("Florian", "school", "Aldermoor College")],
    notes="R3 studies at = school")
add(F, "Magnus coaches at Ferriby Rowing Club", [T("Magnus", "workplace", "Ferriby Rowing Club")],
    notes="R3 coaches at = workplace")
add(F, "Imelda works at the Hartsell Library", [T("Imelda", "employer", "Hartsell Library")],
    notes="R3 works at = employer (workplace alias); library noun does not make it school")
add(F, "Radek does research at Brimley University", [T("Radek", "workplace", "Brimley University")],
    clear=False, notes="R3 research at = workplace; school also defensible (could be a student)")
add(F, "Ingrid lectures at Carnbrae Institute", [T("Ingrid", "workplace", "Carnbrae Institute")],
    notes="R3 lectures at = workplace, not school")
add(F, "ok so Benedikt, my flatmate, is originally from Losswick",
    [T("me", "roommate", "Benedikt"), T("Benedikt", "hometown", "Losswick")], clear=False,
    notes="originally from = hometown; place_of_birth also defensible")
add(F, "anyway my gf is called Noemi", [T("me", "partner", "Noemi")], notes="anyway, gf")
add(F, "Lorcan's been living in Achterby for like 3 years", [T("Lorcan", "city", "Achterby")])
add(F, "btw Marisol is a vet", [T("Marisol", "job", "vet")], notes="btw")
add(F, "Casimira moved to Pendlewick last month", [T("Casimira", "city", "Pendlewick")],
    notes="moved to = current city")
add(F, "my grandmas name is Winnifred", [T("me", "grandmother", "Winnifred")], notes="missing apostrophe")
add(F, "Tobiah has 2 cats, Mungo and Pip", [T("Tobiah", "pet", "Mungo"), T("Tobiah", "pet", "Pip")])
add(F, "i'm a welder at Stannard Works", [T("me", "job", "welder"), T("me", "employer", "Stannard Works")])
add(F, "Elowen's hubby is Tadgh", [T("Elowen", "spouse", "Tadgh")], notes="hubby = spouse")
add(F, "Wystan speaks Keshi fluently and his daughter is Amabel",
    [T("Wystan", "language", "Keshi"), T("Wystan", "daughter", "Amabel")], notes="R1 his=Wystan")
add(F, "met my new boss today, her name is Octavia Rull", [T("me", "boss", "Octavia Rull")],
    notes="her = the unnamed boss; no named third person, so untagged")
add(F, "Perpetua was born in Lindenmoss but grew up in Carrick Hollow",
    [T("Perpetua", "place_of_birth", "Lindenmoss"), T("Perpetua", "hometown", "Carrick Hollow")],
    notes="birthplace and upbringing stated separately")
add(F, "lol my brother Achim finally got a job, he's a dental hygenist now",
    [T("me", "brother", "Achim"), T("Achim", "job", "dental hygenist")],
    notes="R1 he=Achim; typo kept in value")

# ---------------- full_names (15) ----------------
F = "full_names"
add(F, "my new colleague is Anneliese Voss-Paterek", [T("me", "colleague", "Anneliese Voss-Paterek")])
add(F, "Bartholomew Quince lives in Upper Stollard", [T("Bartholomew Quince", "city", "Upper Stollard")])
add(F, "Mary Clare Dunleavy teaches at St Aldric's School",
    [T("Mary Clare Dunleavy", "workplace", "St Aldric's School")], notes="R3 teaches at = workplace; 3-word name")
add(F, "Jean-Baptiste Oyelaran studies at Wendlebury College",
    [T("Jean-Baptiste Oyelaran", "school", "Wendlebury College")], notes="R3 studies at = school")
add(F, "Hilde van der Sloot coaches at Brackwater Tennis Club",
    [T("Hilde van der Sloot", "workplace", "Brackwater Tennis Club")], notes="R3 coaches at = workplace; 4-word name")
add(F, "my stepdad is Desmond Okafor-Lyle", [T("me", "stepfather", "Desmond Okafor-Lyle")])
add(F, "Priya Castellane-Hurst works for Ormond & Vale and she lives in Tessingham",
    [T("Priya Castellane-Hurst", "employer", "Ormond & Vale"), T("Priya Castellane-Hurst", "city", "Tessingham")],
    notes="R1 she=Priya Castellane-Hurst")
add(F, "the guy next door is Ludo Fairweather", [T("me", "neighbor", "Ludo Fairweather")],
    notes="guy next door = neighbor")
add(F, "Agnieszka Bell-Moreau is my sister in law", [T("me", "sister_in_law", "Agnieszka Bell-Moreau")])
add(F, "my wife Solveig Anna Brenner and i both speak Drennish",
    [T("me", "spouse", "Solveig Anna Brenner"), T("Solveig Anna Brenner", "language", "Drennish"),
     T("me", "language", "Drennish")], notes="3-word name; shared fact")
add(F, "Cormac De Varre was born in Shillingthorpe, he now lives in Mossbury Green",
    [T("Cormac De Varre", "place_of_birth", "Shillingthorpe"), T("Cormac De Varre", "city", "Mossbury Green")],
    notes="R1 he=Cormac De Varre")
add(F, "Evangeline Thackeray-Moss is the head chef at Brannigan's Table",
    [T("Evangeline Thackeray-Moss", "job", "head chef"), T("Evangeline Thackeray-Moss", "workplace", "Brannigan's Table")])
add(F, "Oswin Tarbuck works at the Merrow Street Hospital",
    [T("Oswin Tarbuck", "employer", "Merrow Street Hospital")],
    notes="R3 works at = employer (workplace alias); hospital noun says nothing about job")
add(F, "my boss Katarzyna Elm-Whitlow has a husband called Idris Pembe and hes a pilot",
    [T("me", "boss", "Katarzyna Elm-Whitlow"), T("Katarzyna Elm-Whitlow", "spouse", "Idris Pembe"),
     T("Idris Pembe", "job", "pilot")], notes="R1 hes=Idris Pembe (typo, no apostrophe)")
add(F, "Rosalind Mae Oduya Fenn got a job at Coldharbour Studios",
    [T("Rosalind Mae Oduya Fenn", "employer", "Coldharbour Studios")], notes="4-word name")

# ---------------- questions (25) ----------------
F = "questions"
add(F, "Where does Davor live?", [A("Davor", "city")])
add(F, "who is Lusia married to", [A("Lusia", "spouse")], notes="lowercase, no ?")
add(F, "What's Pernille's job?", [A("Pernille", "job")], notes="possessive")
add(F, "where does idris work", [A("idris", "employer")], notes="lowercase, no ?; subject in turn's case")
add(F, "What language does Mirela speak?", [A("Mirela", "language")])
add(F, "Who's my boss?", [A("me", "boss")])
add(F, "whats the name of my cat", [A("me", "pet")], notes="lowercase, no ?")
add(F, "Where was Fenwick born?", [A("Fenwick", "place_of_birth")])
add(F, "Does Tamlyn have a brother?", [A("Tamlyn", "brother")], clear=False,
    notes="could be read as a yes/no existence check")
add(F, "Who does Halvard report to?", [A("Halvard", "boss")], notes="verb form: report to = boss")
add(F, "what does Brannoch do for a living", [A("Brannoch", "job")], notes="lowercase, no ?")
add(F, "Where'd Zofie grow up?", [A("Zofie", "hometown")])
add(F, "who's my cousin again?", [A("me", "cousin")])
add(F, "Which city does Rasmin live in?", [A("Rasmin", "city")])
add(F, "Cato's dog, what's it called?", [A("Cato", "pet")], notes="fronted possessive")
add(F, "who employs Kaspar", [A("Kaspar", "employer")], notes="verb form; lowercase, no ?")
add(F, "Where does Cordelia teach?", [A("Cordelia", "workplace")], notes="verb form teach = workplace")
add(F, "What school does Florian go to?", [A("Florian", "school")])
add(F, "Who's Wystan's daughter?", [A("Wystan", "daughter")], notes="possessive")
add(F, "What's Kasimir's favourite food?", [A("Kasimir", "favorite_food")])
add(F, "who's Thessa's wife", [A("Thessa", "spouse")], notes="lowercase, no ?")
add(F, "Tell me where Evadne lives.", [A("Evadne", "city")], notes="imperative, no ?")
add(F, "What instrument does Yevgenia play?", [A("Yevgenia", "instrument")])
add(F, "Who is Idris's manager?", [A("Idris", "boss")], notes="possessive")
add(F, "what languages do i speak", [A("me", "language")], notes="lowercase, no ?")

# ---------------- chain_questions (15) ----------------
F = "chain_questions"
add(F, "Where does my boss live?", [C2("me", "boss", "city")])
add(F, "What does Lusia's husband do for work?", [C2("Lusia", "spouse", "job")])
add(F, "where does Pernille's husband work", [C2("Pernille", "spouse", "employer")], notes="lowercase, no ?")
add(F, "What language does Tamlyn's brother speak?", [C2("Tamlyn", "brother", "language")])
add(F, "Who is my roommate's boss?", [C2("me", "roommate", "boss")])
add(F, "where was Halvard's manager born", [C2("Halvard", "boss", "place_of_birth")], notes="lowercase, no ?")
add(F, "Which city does Wystan's daughter live in?", [C2("Wystan", "daughter", "city")])
add(F, "what's my best friend's job", [C2("me", "best_friend", "job")], notes="lowercase, no ?")
add(F, "Who does Cato's sister work for?", [C2("Cato", "sister", "employer")], notes="verb form")
add(F, "Where did Elowen's hubby grow up?", [C2("Elowen", "spouse", "hometown")])
add(F, "what pet does my cousin have", [C2("me", "cousin", "pet")], notes="lowercase, no ?")
add(F, "Who's Kaspar's boss married to?", [C2("Kaspar", "boss", "spouse")])
add(F, "Where does Mirela's mum live?", [C2("Mirela", "mother", "city")])
add(F, "What's the name of Casimira's brother's dog?", [C2("Casimira", "brother", "pet")])
add(F, "tell me where Radek's supervisor lives", [C2("Radek", "boss", "city")], notes="imperative, no ?")

# ---------------- no_save (25) ----------------
F = "no_save"
R2Q = "R2 statement-shaped question; ASK also a reasonable reading"
add(F, "Davor lives in Kestwick, right?", [], clear=False, notes=R2Q + "; tag question")
add(F, "Pernille works at Grisham Toys, doesn't she?", [], clear=False, notes=R2Q + "; tag question")
add(F, "so Idris works at Tollbeck Mills?", [], clear=False, notes=R2Q + "; rising so-question")
add(F, "Mirela speaks Vostric??", [], clear=False, notes=R2Q + "; double ?")
add(F, "does Brannoch still work at Pellam Freight", [], clear=False, notes=R2Q + "; lowercase, no ?")
add(F, "Halvard's boss is Bettina, isn't it?", [], clear=False, notes=R2Q + "; tag question")
add(F, "Sunniva's a nurse, yeah?", [], clear=False, notes=R2Q + "; tag question")
add(F, "so Zofie's husband is called Anselm?", [], clear=False, notes=R2Q + "; rising so-question")
add(F, "Fenwick was born in Ulmsby, wasn't he", [], clear=False, notes=R2Q + "; tag question, no ?")
add(F, "and Kasimir has a dog named Bramble?", [], clear=False, notes=R2Q + "; rising")
add(F, "Cordelia's at Wexcombe now right", [], clear=False, notes=R2Q + "; lowercase tag, no ?")
add(F, "u sure Rasmin speaks Keshi", [], clear=False, notes=R2Q + "; lowercase, no ?")
add(F, "Hi! How are you today?", [], notes="greeting")
add(F, "Jessamy says her boss is Albrecht.", [], notes="hearsay")
add(F, "apparently Thorvald moved to Glimmerby", [], clear=False,
    notes="hearsay; some would store it as a fact")
add(F, "Let's say my brother is Pontus.", [], notes="pretend")
add(F, "Genevra is the worst landlord lol", [], notes="opinion; does not say whose landlord")
add(F, "Hartwin used to live in Bellstowe.", [], clear=False, notes="past city only; nothing current")
add(F, "i might move to Seacombe Vale next year", [], notes="future plan, not a fact")
add(F, "Imagine if Lucan worked at Draymoor Bank", [], notes="pretend")
add(F, "Did you hear Pickwell Bakery is closing?", [], clear=False, notes="news; a reader might try to store it")
add(F, "Ottokar doesn't live in Marbury anymore.", [], notes="negation only; no new value")
add(F, "thanks, that helps a lot", [], notes="small talk")
add(F, "my friend thinks Veronika lives in Cawlingford", [], notes="belief, not asserted")
add(F, "if Quentin were my boss i'd quit", [], notes="hypothetical")

# ---------------- corrections (15) ----------------
F = "corrections"
add(F, "Sorry, Davor lives in Pellinghurst, not Kestwick.", [T("Davor", "city", "Pellinghurst")], notes="correction")
add(F, "no wait, my sister is Pernilla not Pernille", [T("me", "sister", "Pernilla")], notes="correction")
add(F, "Actually Idris works at Harrock Cane now.", [T("Idris", "employer", "Harrock Cane")], notes="correction")
add(F, "oops i meant Mirela speaks Ostic, not Vostric", [T("Mirela", "language", "Ostic")], notes="correction")
add(F, "correction: my cat is named Pumpkin, not Pumpernickel", [T("me", "pet", "Pumpkin")], notes="correction")
add(F, "Not Tavish - my roommate's name is Tavin.", [T("me", "roommate", "Tavin")], notes="correction")
add(F, "Brannoch isn't a plumber, he's an electrician", [T("Brannoch", "job", "electrician")], notes="correction")
add(F, "my bad, Halvard's manager is Sabine, not Bettina", [T("Halvard", "boss", "Sabine")], notes="correction")
add(F, "scratch that, Fenwick was born in Ashcombe Lees", [T("Fenwick", "place_of_birth", "Ashcombe Lees")],
    notes="correction")
add(F, "i typed it wrong earlier, my cousin is Odalys Brenn not Odalys Brand",
    [T("me", "cousin", "Odalys Brenn")], notes="correction; full name")
add(F, "Lusia's husband is Emerich, with an h at the end", [T("Lusia", "spouse", "Emerich")],
    notes="correction; spelling fix")
add(F, "wrong city before, Rasmin lives in New Veddick not Old Veddick", [T("Rasmin", "city", "New Veddick")],
    notes="correction")
add(F, "no no my dad is Gerard, Gerrit is my uncle",
    [T("me", "father", "Gerard"), T("me", "uncle", "Gerrit")],
    notes="correction; old value is reassigned, not negated, so it is a new fact")
add(F, "Update: Sunniva quit nursing and is a paramedic now", [T("Sunniva", "job", "paramedic")], notes="correction")
add(F, "hold on, Cato's dog is called Muffins. Waffles was the old one", [T("Cato", "pet", "Muffins")],
    notes="correction; the old dog is not saved")

# ---------------- self-checks ----------------
EXPECTED = [("plain_teach", 25), ("varied_teach", 30), ("full_names", 15), ("questions", 25),
            ("chain_questions", 15), ("no_save", 25), ("corrections", 15)]
BANNED = ["Ana", "Tarrow", "Corin", "Elspeth", "Rin", "Anya", "Fernhill", "Wren", "Gil", "Quarrow",
          "Marta", "Brellin", "Pella", "Norrish", "Orla", "Tomas", "Tobin", "Ilse", "Hollis", "Suki",
          "tamsin", "brellin"]
PRON = re.compile(r"\b(she|he|they|it|her|his|their|hes|he's|she's)\b", re.I)
R3VERB = re.compile(r"\b(teaches|studies|coaches|works|lectures|research)\b", re.I)


def fail(msg):
    print("CHECK FAILED:", msg)
    sys.exit(1)


def contains(turn, s):
    return re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)", turn) is not None


def check():
    fams = [f for f, *_ in ITEMS]
    order = []
    for f in fams:
        if not order or order[-1] != f:
            order.append(f)
    if order != [f for f, _ in EXPECTED]:
        fail("family block order %s" % order)
    for f, n in EXPECTED:
        if fams.count(f) != n:
            fail("family %s count %d != %d" % (f, fams.count(f), n))
    if len(ITEMS) != 150:
        fail("total %d" % len(ITEMS))
    turns = [t for _, t, *_ in ITEMS]
    if len(set(turns)) != len(turns):
        fail("duplicate turn")
    for f, t, gold, clear, notes in ITEMS:
        for b in BANNED:
            if contains(t, b):
                fail("banned name %r in %r" % (b, t))
        for fr in gold:
            if fr["act"] == "TEACH":
                if list(fr) != ["act", "subject", "relation", "relation_aliases", "value"]:
                    fail("TEACH keys")
            else:
                if list(fr) != ["act", "subject", "relation", "chain", "relation_aliases"]:
                    fail("ASK keys")
            if fr["relation_aliases"] != ALIASES[fr["relation"]]:
                fail("alias drift")
            for k in ("subject", "value"):
                v = fr.get(k)
                if v is None or v == "me":
                    continue
                if not contains(t, v):
                    fail("%s %r not in turn %r" % (k, v, t))
        if f in ("plain_teach", "varied_teach", "full_names", "corrections"):
            if not gold or any(fr["act"] != "TEACH" for fr in gold):
                fail("teach family needs TEACH frames: %r" % t)
        if f == "questions" and (len(gold) != 1 or gold[0]["act"] != "ASK" or gold[0]["chain"] is not None):
            fail("one-hop ASK: %r" % t)
        if f == "chain_questions" and (len(gold) != 1 or gold[0]["act"] != "ASK" or not gold[0]["chain"]):
            fail("two-hop ASK: %r" % t)
        if f == "no_save" and gold:
            fail("no_save gold must be []")
        if f == "corrections" and "correction" not in notes:
            fail("correction note")
    tag = lambda tg: [(f, t, g, c, n) for f, t, g, c, n in ITEMS if re.search(r"\b%s\b" % tg, n)]
    r1 = tag("R1")
    if len(r1) < 10 or any(f not in ("varied_teach", "full_names") for f, *_ in r1):
        fail("R1 quota/placement")
    if any(not PRON.search(t) for _, t, *_ in r1):
        fail("R1 item without pronoun")
    r1rel = [t for f, t, g, c, n in r1 if "rel+I" in n and re.search(r"\bi\b|\bi'm\b", t, re.I)]
    if len(r1rel) < 3:
        fail("R1 relative+first-person quota")
    r2 = tag("R2")
    r2q = [x for x in r2 if x[0] == "no_save" and x[2] == []]
    r2s = [x for x in r2 if x[0] == "varied_teach" and x[2]]
    if len(r2q) < 10 or len(r2s) < 3 or len(r2q) + len(r2s) != len(r2):
        fail("R2 quota/placement")
    r3 = tag("R3")
    if len(r3) < 8 or any(f not in ("varied_teach", "full_names") for f, *_ in r3):
        fail("R3 quota/placement")
    if any(not R3VERB.search(t) for _, t, *_ in r3):
        fail("R3 item without the deciding verb")
    lowq = [t for f, t, *_ in ITEMS if f in ("questions", "chain_questions") and ("?" not in t or t == t.lower())]
    if len(lowq) < 5:
        fail("lowercase/no-? question quota")
    rels = {fr["relation"] for _, _, g, *_ in ITEMS for fr in g}
    if len(rels) < 12:
        fail("relation variety")
    return r1, r1rel, r2q, r2s, r3, rels


def main():
    r1, r1rel, r2q, r2s, r3, rels = check()
    with open(OUT, "w", encoding="utf-8") as fh:
        for i, (f, t, g, c, n) in enumerate(ITEMS, 1):
            fh.write(json.dumps({"id": "e235b-%03d" % i, "family": f, "turn": t, "gold": g,
                                 "clear": c, "notes": n}, ensure_ascii=False) + "\n")
    print("wrote", OUT, len(ITEMS), "items")
    for f, n in EXPECTED:
        nc = sum(1 for x in ITEMS if x[0] == f and not x[3])
        print("  %-16s %3d  clear:false %d" % (f, n, nc))
    print("  R1 %d (rel+I %d)  R2 no_save %d + statements %d  R3 %d" % (
        len(r1), len(r1rel), len(r2q), len(r2s), len(r3)))
    print("  relations (%d): %s" % (len(rels), ", ".join(sorted(rels))))
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
