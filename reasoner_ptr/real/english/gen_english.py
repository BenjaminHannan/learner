"""Generated English practice rows for the six pilot families (two-doors round 4).

Every word that FRESH-EN-R3.json uses as a name or inside an answer is kept out of the generator's pools, so the
fresh test stays fresh. Names and nouns are split (SPLIT_SEED) into a train part and a held-out part; the held-out
part builds GEN-HELDOUT-R4.json, an in-distribution check (read, not judged).
An example = {"id", "family", "source_text", "paraphrase", "questions": [{question, type, canonical_answer,
accepted_answers}]}, the same shape as the bank, so run_english.py reads it unchanged.
"""
import json, random, re, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPLIT_SEED, HELD_SEED = 20261005, 5151
CAP = 48  # tokens of passage + " " + question, before EOS (the core's query cap is 49 incl. EOS)


def norm(s):
    s = unicodedata.normalize("NFC", s).lower().replace("’", "'").strip()
    return re.sub(r"[.!?,;:]+$", "", re.sub(r"\s+", " ", s)).strip()


def fresh_blocklist(files=("FRESH-EN-R3.json",)):
    stop = {"the", "a", "an", "to", "of", "in", "on", "by", "with", "did", "and", "yes", "no", "was", "his", "her", "one", "that", "after", "before", "inside"}
    words = set()
    for e in [e for f in files if (HERE / f).exists() for e in json.load(open(HERE / f))["examples"]]:
        for t in (e["source_text"], e["paraphrase"]):
            words |= {w for w in re.findall(r"[A-Z][a-z]+", t)}  # capitalised words: names (and sentence starts)
        for q in e["questions"]:
            for a in q["accepted_answers"] + [q["canonical_answer"]]:
                words |= set(norm(a).replace("'s", "").replace("-", " ").split())
    return {w.lower() for w in words} - stop


SYL1 = ["ba", "be", "bo", "da", "de", "di", "fa", "fe", "ga", "ge", "ha", "ja", "ka", "ke", "ko", "la", "le", "li", "lo",
        "ma", "me", "mi", "na", "ne", "no", "pa", "pe", "ra", "re", "ri", "ro", "sa", "se", "si", "ta", "te", "ti", "to",
        "va", "ve", "wa", "ya", "yo", "za", "zo"]
SYL2 = ["n", "l", "r", "s", "k", "m", "t", "x", "v", "d", "ra", "na", "lo", "ni", "ri", "mo", "ka", "lu", "vi", "ta"]
NOUNS = ["cup", "lamp", "book", "box", "basket", "bottle", "jar", "bowl", "plate", "spoon", "ladle", "brush", "broom",
         "bucket", "pail", "kite", "drum", "flute", "bell", "clock", "watch", "ring", "badge", "card", "map", "letter",
         "envelope", "parcel", "bag", "purse", "wallet", "scarf", "glove", "hat", "cap", "mitten", "shirt", "jacket",
         "blanket", "pillow", "cushion", "rug", "mat", "chair", "bench", "table", "shelf", "crate", "trunk", "case",
         "pen", "marker", "crayon", "ruler", "eraser", "notebook", "folder", "binder", "lantern", "candle", "torch",
         "hammer", "wrench", "saw", "drill", "ladder", "shovel", "rake", "hose", "kettle", "pot", "pan", "tray",
         "teacup", "saucer", "vase", "pitcher", "jug", "flask", "thermos", "lunchbox", "apple", "pear", "lemon",
         "melon", "carrot", "onion", "loaf", "cookie", "muffin", "pie", "puzzle", "doll", "ball", "marble", "yo-yo",
         "whistle", "compass", "mirror", "comb", "ribbon", "button", "thimble", "needle", "spool", "statue", "globe",
         "medal", "trophy", "camera", "radio", "phone", "tablet", "pencil case", "paintbrush", "sketchbook", "violin",
         "guitar", "harmonica", "teapot", "dish", "fork", "knife", "napkin", "towel", "sponge", "soap", "key"]
ADJS = ["red", "blue", "green", "white", "black", "brown", "purple", "pink", "orange", "silver", "golden", "copper",
        "wooden", "glass", "paper", "clay", "metal", "leather", "woolen", "silk", "rubber", "striped", "dotted",
        "checked", "small", "large", "old", "new", "heavy", "light", "round", "square", "long", "short", "bright",
        "dull", "soft", "hard", "plain", "painted"]
PLACES = ["kitchen", "hallway", "classroom", "library", "office", "workshop", "studio", "garden", "porch", "cellar",
          "market", "bakery", "station", "museum", "theater", "gym", "clinic", "harbor", "beach", "park", "camp",
          "farm", "shop", "school", "lobby", "playground", "cafe", "bus stop", "dock", "orchard"]
SURFACES = ["shelf", "table", "desk", "bench", "counter", "windowsill", "cart", "chair", "stool", "ledge", "crate",
            "dresser", "cabinet", "trunk", "tray", "floor", "step", "rack", "board", "box"]
TIMES = ["On Monday", "On Tuesday", "On Wednesday", "On Thursday", "On Saturday", "On Sunday", "In the morning",
         "That evening", "At noon", "After lunch", "Before dinner", "During the break", "Early today", "Last week"]
COMPARE = [("heavier", "lighter", "weighs more", "weighs less"), ("taller", "shorter", None, None),
           ("longer", "shorter", None, None), ("wider", "narrower", None, None), ("thicker", "thinner", None, None),
           ("older", "newer", None, None), ("bigger", "smaller", None, None), ("louder", "quieter", None, None),
           ("warmer", "cooler", None, None), ("brighter", "dimmer", None, None), ("softer", "harder", None, None),
           ("cleaner", "dirtier", None, None)]
GIVE = [("handed", "was handed to", "hand"), ("gave", "was given to", "give"), ("passed", "was passed to", "pass"),
        ("sent", "was sent to", "send"), ("brought", "was brought to", "bring"),
        ("sold", "was sold to", "sell"), ("threw", "was thrown to", "throw"),
        ("mailed", "was mailed to", "mail")]
ACTS = [("opened the window", "opening the window"), ("closed the door", "closing the door"),
        ("washed the dishes", "washing the dishes"), ("fed the cat", "feeding the cat"),
        ("watered the plants", "watering the plants"), ("read the letter", "reading the letter"),
        ("packed the bag", "packing the bag"), ("cleaned the desk", "cleaning the desk"),
        ("painted the fence", "painting the fence"), ("folded the towels", "folding the towels"),
        ("swept the floor", "sweeping the floor"), ("baked the bread", "baking the bread"),
        ("called the shop", "calling the shop"), ("wrote the note", "writing the note"),
        ("tuned the radio", "tuning the radio"), ("filled the jug", "filling the jug"),
        ("set the table", "setting the table"), ("turned off the lamp", "turning off the lamp"),
        ("made the bed", "making the bed"), ("checked the map", "checking the map"),
        ("counted the coins", "counting the coins"), ("hung the picture", "hanging the picture"),
        ("raked the leaves", "raking the leaves"), ("wiped the table", "wiping the table")]
EVENTS = ["the bell rang", "the lights went out", "the rain stopped", "the bus arrived", "the music started",
          "the clock struck ten", "the dog barked", "the door creaked", "the kettle whistled", "the show ended",
          "the phone rang", "the sun set"]
RELS = [("hung from", "What hung from the {Y}?"), ("lay on", "What lay on the {Y}?"), ("sat beside", "What sat beside the {Y}?"),
        ("was tied to", "What was tied to the {Y}?"), ("rested against", "What rested against the {Y}?"),
        ("leaned on", "What leaned on the {Y}?"), ("was clipped to", "What was clipped to the {Y}?")]
LOCS = [("rested in", "rest in"), ("stood on", "stand on"), ("sat under", "sit under"), ("lay inside", "lie inside"),
        ("stood beside", "stand beside"), ("sat on", "sit on"), ("rested on", "rest on")]
PAIRS = [("with a lid", "with a cap", "lidded", "capped"), ("with a handle", "without a handle", "handled", "handleless"),
         ("tied with string", "tied with tape", "string-tied", "tape-tied"), ("with a crack", "with a chip", "cracked", "chipped"),
         ("with stripes", "with spots", "striped", "spotted")]


COMMON = set("""let sat set bet net pet ten man men ban fan pan ran tan van dot lot not pot rot tot son ton sir fax tax wax mix
fix six box fox lax max sex rex bed red led fed wed rid lid kid bid did god nod rod bad dad had mad pad sad lad tad dam ham
jam ram yam kin din sin tin win pin bin fin gin bit fit hit kit lit pit sit wit mat bat cat fat hat rat vat pat yet wet get
jet met gem hem den hen pen yen ken hum sum rum gum mum vet tom mom log dog fog hog jog bog run sun fun gun bun nun pun bus
gas has was his mud bud dud far bar car jar tar war gal pal sal mal bal ear era sea tea pea lea yea fee bee see lee tee wee
gee dee nee ray bay day hay lay may pay say way jay key fey hey boy toy joy soy coy mar tar par yak bak sak lid pal kit
kid ris sis tis vis dis lis mis bis sir fir kir sim tim dim him rim vim lim ham sam tam pam rak tak mak sax wax tax rax
lax dax tex vex hex sex rex lex mix six pix fix nix bix tix kix vix zix bon con don non ton won son yon mon hon ron eon
ion ban can dan fan man nan pan ran tan van wan ken ben den hen men pen ten wen yen zen""".split())


def plural(n):
    return n + "es" if n.endswith(("s", "x", "ch", "sh")) else n + "s"


def art(w):
    return "an" if w[0] in "aeiou" else "a"


def obj_variants(phrase):
    return [phrase, "the " + phrase, art(phrase) + " " + phrase]


class Pools:
    def __init__(self, part, block_files=("FRESH-EN-R3.json",)):
        block = fresh_blocklist(block_files)
        self.block = block
        rng = random.Random(SPLIT_SEED)
        names = sorted({(a + b).capitalize() for a in SYL1 for b in SYL2} - {w.capitalize() for w in block})
        bank = json.load(open(HERE / "english_training_candidates_v3.json"))
        bank_names = {w for e in bank["examples"] for w in re.findall(r"[A-Z][a-z]+", e["source_text"] + " " + e["paraphrase"])}
        names = [n for n in names if n not in bank_names and n.lower() not in COMMON]
        nouns = [n for n in NOUNS if not (set(n.split()) & block)]
        adjs = [a for a in ADJS if a not in block]
        places = [p for p in PLACES if not (set(p.split()) & block)]
        surfaces = [s for s in SURFACES if s not in block]
        for L in (names, nouns, adjs, places, surfaces):
            rng.shuffle(L)
        def cut(L, f=0.8):
            k = int(len(L) * f); return L[:k] if part == "train" else L[k:]
        self.names, self.nouns, self.adjs = cut(names), cut(nouns), adjs  # adjectives shared; nouns/names split
        self.places, self.surfaces = places, surfaces


def q(question, typ, canon, accepted):
    acc = []
    for a in [canon] + accepted:
        if a not in acc: acc.append(a)
    return {"question": question, "type": typ, "canonical_answer": canon, "accepted_answers": acc}


def ex_giver(r, P):
    a, b = r.sample(P.names, 2); o = r.choice(P.adjs) + " " + r.choice(P.nouns)
    v, vp, base = r.choice(GIVE); where = r.choice(["At the " + r.choice(P.places), r.choice(TIMES)])
    k = r.randrange(3)
    if k == 0:
        s = f"{where}, {a} {v} {b} the {o}."; para = f"{where}, the {o} {vp} {b} by {a}."
    elif k == 1:
        s = f"{where}, {a} {v} the {o} to {b}."; para = f"{where}, {b} got the {o} from {a}."
    else:
        s = f"{b} got the {o} after {a} {v} it, {where[0].lower() + where[1:]}."; para = f"{where}, {a} {v} the {o}, and {b} got it."
    qs = [q(f"Who {v} the {o}?", "short_answer", a, [f"{a} did"]),
          q(f"Who got the {o}?" if k else f"To whom did {a} {base} the {o}?", "short_answer", b, [f"to {b}", f"{b} did"])]
    if r.random() < 0.25:
        qs[r.randrange(2)] = q(f"Did {b} {base} the {o} to {a}?", "yes_no", "No", [])
    return "giver_recipient_roles", s, para, qs


def ex_compare(r, P):
    n = r.choice(P.nouns); x, y = r.sample(P.adjs, 2)
    more, less, vmore, vless = r.choice(COMPARE)
    where = r.choice(P.surfaces)
    s = f"The {x} {n} is {more} than the {y} {n}; both are on the {where}."
    para = f"The {y} {n} is {less} than the {x} {n}; both are on the {where}."
    if r.random() < 0.5: s, para = para, s
    qa = q(f"Which {n} is {more}?", "short_answer", f"{x} {n}", obj_variants(f"{x} {n}")[1:])
    qb = q(f"Which {n} is {less}?", "short_answer", f"{y} {n}", obj_variants(f"{y} {n}")[1:])
    yn = r.choice([q(f"Is the {x} {n} {more} than the {y} {n}?", "yes_no", "Yes", []),
                   q(f"Is the {y} {n} {more} than the {x} {n}?", "yes_no", "No", []),
                   q(f"Is the {y} {n} {less} than the {x} {n}?", "yes_no", "Yes", []),
                   q(f"Is the {x} {n} {less} than the {y} {n}?", "yes_no", "No", [])])
    if r.random() < 0.3:
        a, b2 = r.sample(P.names, 2)
        s = f"{a}'s {n} is {more} than {b2}'s {n}, which is on the {where}."
        para = f"On the {where} is {b2}'s {n}, {less} than {a}'s {n}."
        qa = q(f"Whose {n} is {more}?", "short_answer", a, [f"{a}'s", f"{a}'s {n}"])
        qb = q(f"Whose {n} is {less}?", "short_answer", b2, [f"{b2}'s", f"{b2}'s {n}"])
        yn = q(f"Is {b2}'s {n} {more} than {a}'s {n}?", "yes_no", "No", [])
    return "comparative_direction", s, para, r.sample([qa, qb, yn], 2)


def ex_neg(r, P):
    a = r.choice(P.names); o1, o2 = [r.choice(P.adjs) + " " + nn for nn in r.sample(P.nouns, 2)]
    v, inf = r.choice([("chose", "choose"), ("picked", "pick"), ("bought", "buy"), ("packed", "pack"), ("took", "take"),
                       ("borrowed", "borrow"), ("ordered", "order"), ("kept", "keep")])
    ctx = r.choice(["For the trip", "For the party", "At the " + r.choice(P.places), "For the show", r.choice(TIMES)])
    forms = [(f"{ctx}, {a} did not {inf} the {o1}; {a} {v} the {o2}.", f"{ctx}, {a} {v} the {o2} and did not {inf} the {o1}."),
             (f"{ctx}, {a} {v} the {o2}, not the {o1}.", f"{a} did not {inf} the {o1}; {a} {v} the {o2} instead, {ctx[0].lower() + ctx[1:]}."),
             (f"The note says {a} did not {inf} the {o1} and {v} the {o2} instead.", f"According to the note, {a} {v} the {o2}, not the {o1}.")]
    s, para = r.choice(forms)
    qs = [q(f"What did {a} {inf}?", "short_answer", o2, obj_variants(o2)[1:]),
          q(f"What did {a} not {inf}?", "short_answer", o1, obj_variants(o1)[1:]),
          q(f"Did {a} {inf} the {o1}?", "yes_no", "No", []), q(f"Did {a} {inf} the {o2}?", "yes_no", "Yes", [])]
    return "explicit_negation_with_positive_alternative", s, para, r.sample(qs[:2], 1) + r.sample(qs[2:], 1) if r.random() < 0.4 else qs[:2]


def ex_order(r, P):
    a = r.choice(P.names); (p1, g1), (p2, g2) = r.sample(ACTS, 2)
    k = r.randrange(3)
    if k == 0:
        s = f"{a} {p1} before {g2}."; para = f"{a} {p2} after {g1}."
        qs = [q("Which event happened first?", "short_answer", f"{a} {p1}", [g1, f"{a} {g1}", p1]),
              q("Which event happened later?", "short_answer", f"{a} {p2}", [g2, f"{a} {g2}", p2]),
              q(f"What did {a} do first?", "short_answer", p1, [f"{a} {p1}"])]
    elif k == 1:
        ev = r.choice(EVENTS)
        s = f"{a} {p1} after {ev}."; para = f"After {ev}, {a} {p1}."
        qs = [q(f"What did {a} do after {ev}?", "short_answer", p1, [f"{a} {p1}"]),
              q("Which event happened first?", "short_answer", ev, [ev.replace("the ", "", 1)])]
    else:
        b = r.choice([n for n in P.names if n != a])
        s = f"Before {b} {p2}, {a} {p1}."; para = f"{a} {p1} before {b} {p2}."
        qs = [q("What happened first?", "short_answer", f"{a} {p1}", []),
              q(f"What did {b} do later?", "short_answer", p2, [f"{b} {p2}"])]
    return "event_ordering", s, para, r.sample(qs, 2)


def ex_ref(r, P):
    a = r.choice(P.names); n = r.choice(P.nouns); col = r.choice(P.adjs)
    d1, d2, s1, s2 = r.choice(PAIRS); where = r.choice(P.surfaces); dest = r.choice(P.surfaces)
    if r.random() < 0.5:
        s = f"On the {where} were a {col} {n} {d1} and a {col} {n} {d2}. {a} moved the {s1} one to the {dest}."
        para = f"A {col} {n} {d2} and a {col} {n} {d1} were on the {where}. {a} moved the one {d1} to the {dest}."
        tgt = f"{col} {n} {d1}"; alts = [f"the {col} {n} {d1}", f"{n} {d1}", f"the {n} {d1}", f"the {s1} {n}", f"{s1} {n}", f"the {s1} one"]
    else:
        s = f"Two {col} {plural(n)} sat on the {where}: the {s1} one was left of the {s2} one. {a} moved the left one to the {dest}."
        para = f"Two {col} {plural(n)} sat on the {where}: the {s2} one was right of the {s1} one. {a} moved the one on the left to the {dest}."
        tgt = f"{s1} {n}"; alts = [f"the {s1} {n}", f"{s1} {col} {n}", f"the {s1} {col} {n}", f"the {n} on the left", f"the left one", f"the {s1} one"]
    qs = [q(f"Which {n} did {a} move?", "short_answer", tgt, alts),
          q(f"Where did {a} move the {n}?", "short_answer", f"to the {dest}", [f"the {dest}", dest]),
          q(f"Where were the {plural(n)}?", "short_answer", f"on the {where}", [f"the {where}", where])]
    return "unambiguous_descriptive_reference", s, para, [qs[0], r.choice(qs[1:])]


def ex_two(r, P):
    x, y = [r.choice(P.adjs) + " " + nn for nn in r.sample(P.nouns, 2)]; z = r.choice(P.adjs) + " " + r.choice(P.surfaces)
    rel, qt = r.choice(RELS); loc, prep = r.choice(LOCS); yh = y.split(" ", 1)[1]
    s = f"{art(x).capitalize()} {x} {rel} {art(y)} {y}, and the {yh} {loc} {art(z)} {z}."
    para = f"The {y} {loc} {art(z)} {z}, and {art(x)} {x} {rel} it."
    if r.random() < 0.5:
        s, para = f"{art(x).capitalize()} {x} {rel} {art(y)} {y}. The {yh} {loc} {art(z)} {z}.", para
    qs = [q(qt.format(Y=y), "short_answer", x, obj_variants(x)[1:]),
          q(f"What did the {y} {prep}?", "short_answer", z, obj_variants(z)[1:]),
          q(f"Which object {loc} the {z}?", "short_answer", y, obj_variants(y)[1:])]
    return "two_simple_relations_combined", s, para, r.sample([qs[0], qs[2]], 1) + [qs[1]] if r.random() < 0.5 else [qs[0], qs[2]]


FAMS = [ex_giver, ex_compare, ex_neg, ex_order, ex_ref, ex_two]

# ---- round 6: six more practice kinds. None is one of the test kinds in NEW-KINDS-R5 (counting, location, cause,
# time, attribute, instrument) or NEW-KINDS2-R6 (speech, weather, price, direction, duration, origin).
FEELINGS = ["happy", "sad", "tired", "proud", "nervous", "calm", "bored", "excited", "angry", "scared", "glad", "sleepy",
            "hungry", "upset", "cheerful", "grumpy", "relieved", "surprised", "lonely", "worried"]
EVENTS2 = ["game", "trip", "test", "concert", "race", "meeting", "party", "lesson", "match", "play", "picnic", "visit"]
PETS = ["dog", "cat", "fish", "bird", "horse", "goat", "rabbit", "turtle", "hamster", "pony", "parrot", "lamb"]
DO = [("painted", "paint"), ("washed", "wash"), ("fixed", "fix"), ("opened", "open"), ("carried", "carry"), ("cleaned", "clean"),
      ("moved", "move"), ("checked", "check"), ("dried", "dry"), ("wrapped", "wrap"), ("polished", "polish"), ("sorted", "sort"),
      ("lifted", "lift"), ("filled", "fill"), ("emptied", "empty"), ("folded", "fold")]


def _ok(P, *ws):
    return not any(w in P.block for x in ws for w in x.lower().split())


def ex_owner(r, P):
    a, b = r.sample(P.names, 2); n = r.choice(P.nouns); x, y = r.sample(P.adjs, 2)
    s = f"The {x} {n} belongs to {a}, and the {y} {n} belongs to {b}."
    para = f"{b} owns the {y} {n}, while {a} owns the {x} {n}."
    if r.random() < 0.5: s, para = para, s
    qs = [q(f"Who owns the {x} {n}?", "short_answer", a, [f"{a} does", f"{a}'s"]),
          q(f"Whose is the {y} {n}?", "short_answer", b, [f"{b}'s", f"it is {b}'s"]),
          q(f"Does {a} own the {y} {n}?", "yes_no", "No", [])]
    return "owner_possession", s, para, r.sample(qs[:2], 2) if r.random() < 0.75 else [r.choice(qs[:2]), qs[2]]


def ex_agent(r, P):
    a, b = r.sample(P.names, 2); (v1, b1), (v2, b2) = r.sample(DO, 2)
    o1, o2 = [r.choice(P.adjs) + " " + nn for nn in r.sample(P.nouns, 2)]
    s = f"{a} {v1} the {o1} while {b} {v2} the {o2}."
    para = f"While {a} {v1} the {o1}, {b} {v2} the {o2}."
    qs = [q(f"Who {v1} the {o1}?", "short_answer", a, [f"{a} did"]),
          q(f"What did {b} {b2}?", "short_answer", o2, obj_variants(o2)[1:]),
          q(f"Did {b} {b1} the {o1}?", "yes_no", "No", [])]
    return "agent_action", s, para, [qs[0], qs[1]] if r.random() < 0.75 else [r.choice(qs[:2]), qs[2]]


def ex_companion(r, P):
    a, b, c = r.sample(P.names, 3); pl = r.choice(P.places)
    s = f"{a} went to the {pl} with {b}, and {c} stayed home."
    para = f"{c} stayed home while {a} and {b} went to the {pl}."
    qs = [q(f"Who went to the {pl} with {a}?", "short_answer", b, [f"{b} did", f"with {b}"]),
          q("Who stayed home?", "short_answer", c, [f"{c} did"]),
          q(f"Did {c} go to the {pl}?", "yes_no", "No", [])]
    return "companion_with", s, para, r.sample(qs, 2)


def ex_feeling(r, P):
    a, b = r.sample(P.names, 2); f1, f2 = r.sample([f for f in FEELINGS if _ok(P, f)], 2); ev = r.choice(EVENTS2)
    s = f"After the {ev}, {a} felt {f1}, but {b} felt {f2}."
    para = f"{b} felt {f2} after the {ev}, while {a} felt {f1}."
    qs = [q(f"How did {b} feel after the {ev}?", "short_answer", f2, [f"{b} felt {f2}", f"{f2}"]),
          q(f"How did {a} feel after the {ev}?", "short_answer", f1, [f"{a} felt {f1}"]),
          q(f"Did {a} feel {f2}?", "yes_no", "No", [])]
    return "feeling_state", s, para, r.sample(qs, 2)


def ex_naming(r, P):
    a, b, n1, n2 = r.sample(P.names, 4); p1, p2 = r.sample([p for p in PETS if _ok(P, p)], 2)
    s = f"{a}'s {p1} is named {n1}, and {b}'s {p2} is named {n2}."
    para = f"{b} has a {p2} called {n2}, and {a} has a {p1} called {n1}."
    qs = [q(f"What is the name of {b}'s {p2}?", "short_answer", n2, [f"it is {n2}", f"{n2}"]),
          q(f"What is {a}'s {p1} called?", "short_answer", n1, [f"it is called {n1}"]),
          q(f"Whose {p1} is named {n1}?", "short_answer", a, [f"{a}'s"])]
    return "naming", s, para, r.sample(qs, 2)


def ex_activity(r, P):
    a = r.choice(P.names); pl1, pl2 = r.sample(P.places, 2); (p1, _), (p2, _) = r.sample(ACTS, 2)
    s = f"At the {pl1}, {a} {p1}, and at the {pl2}, {a} {p2}."
    para = f"{a} {p2} at the {pl2} and {p1} at the {pl1}."
    qs = [q(f"What did {a} do at the {pl2}?", "short_answer", p2, [f"{a} {p2}"]),
          q(f"What did {a} do at the {pl1}?", "short_answer", p1, [f"{a} {p1}"])]
    return "activity_place", s, para, qs


FAMS12 = FAMS + [ex_owner, ex_agent, ex_companion, ex_feeling, ex_naming, ex_activity]
_tok = None


def fits(texts):
    global _tok
    if _tok is None:
        from transformers import AutoTokenizer
        _tok = AutoTokenizer.from_pretrained("LiquidAI/LFM2.5-1.2B-Instruct", revision="0f604ada3f766f9f257460c4c9f0b5d6f69d431b")
    return all(len(_tok.encode(t, add_special_tokens=False)) <= CAP for t in texts)


FAM_NAMES = ["giver_recipient_roles", "comparative_direction", "explicit_negation_with_positive_alternative",
             "event_ordering", "unambiguous_descriptive_reference", "two_simple_relations_combined"]  # same order as FAMS


FAM_NAMES12 = FAM_NAMES + ["owner_possession", "agent_action", "companion_with", "feeling_state", "naming", "activity_place"]
BLOCK_R6 = ("FRESH-EN-R3.json", "NEW-KINDS-R5.json", "NEW-KINDS2-R6.json")


def make(n, seed, part, avoid=(), drop=(), kinds=6, block_files=("FRESH-EN-R3.json",)):
    """kinds=6: the round-4 families. kinds=12: plus the six round-6 kinds. Rounds 4/5 used the defaults."""
    r = random.Random(seed); P = Pools(part, block_files); out, seen = [], set(avoid)
    fl, nl = (FAMS, FAM_NAMES) if kinds == 6 else (FAMS12, FAM_NAMES12)
    fams = [f for f, nm in zip(fl, nl) if nm not in drop]
    while len(out) < n:
        fam, s, para, qs = fams[len(out) % len(fams)](r, P)
        if any(not x["canonical_answer"] or not x["question"] for x in qs) or s in seen: continue
        if not fits([t + " " + x["question"] for t in (s, para) for x in qs]): continue
        seen.add(s)
        out.append({"id": f"gen_{part}_{seed}_{len(out)}", "family": fam, "source_text": s, "paraphrase": para, "questions": qs})
    return out


if __name__ == "__main__":
    import sys
    held = make(48, HELD_SEED, "held")
    (HERE / "GEN-HELDOUT-R4.json").write_text(json.dumps({"title": "generated held-out (held-out names/nouns), round 4", "examples": held}, indent=1))
    for e in (make(12, 1, "train") + held[:6]):
        print(e["family"][:10], "|", e["source_text"], "||", e["paraphrase"])
        for x in e["questions"]: print("    ", x["question"], "->", x["accepted_answers"])
