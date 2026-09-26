#!/usr/bin/env python3
"""lis-320 pilot, step 1 of 3: code-only world sampler for dialog seeds (plan: design/v3/60-listener/lis-320-no-claude-data-plan.md).

Code picks ONLY: people (fictional names built from syllable parts), their gender and role relative to the user,
turn intents, relations (from relation-names.txt) and values. It writes no wording: there are no sentence templates and
no example phrasings here. Every gold frame is built by code, in the training-target schema
(claude_lis300_common.canon_frame: act, facts[owner, rel, value, mode, old], ask).

Intents (one per turn, 6-8 turns per dialog):
  teach        1-3 ASSERT facts; each owner named in the turn (or first person for "me"); first mention of a person is
               an intro fact (me, <role>, Name)
  correct      CORRECT of an earlier (owner, rel); half name the old value (fact gets "old"), half must not
  backref      new ASSERT fact about a person named in the last 6 turns, referred to by pronoun (only when that person
               is the only one of that gender named in the visible history) or by role word; the name must not appear
  former       FORMER (claude_lis319f_data): past occupation / employer / city
  jobhome      occupation + city of one owner, ASSERT, in one sentence
  ask          ASK about a stored fact (ask object, no facts); the answer must not appear
  lookalikes   question (QUESTION), plan (PLAN), doubt (CHECK, see LOOK_MODE), someone_else (REPORTED),
               hypothetical (SUPPOSE), negation_only (NEGATE, no facts), confirm (CHECK of a stored fact),
               ambiguous_pronoun (two same-gender people named, pronoun owner kept as typed, UNCLEAR)
  smalltalk    CHAT, no facts

python3 claude_lis320_seed.py --seed 320 --n 30 --out seeds.jsonl [--avoid-names FILE]
python3 claude_lis320_seed.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path


def find_repo() -> Path:
    for p in [os.environ.get("LEARNER_REPO", ""), "/home/user/learner", str(Path.home() / "learner"), "."]:
        if p and (Path(p) / "scripts/claude_lis300_compiler.py").exists():
            return Path(p).resolve()
    raise SystemExit("repo not found: set LEARNER_REPO")


REPO = find_repo()
REL_NAMES = set((REPO / "design/v3/60-listener/relation-names.txt").read_text().split())

# ------------------------------------------------------------------ names (syllable parts, never real famous names)
SYL = ["ka", "ri", "lo", "ven", "ta", "mi", "dor", "sa", "bel", "nu", "ro", "fi", "gan", "le", "zo", "ha", "tir",
       "wen", "ya", "mo", "ke", "ul", "si", "dra", "po", "lin", "ez", "or", "ba", "ne", "vi", "ash", "ru", "tem",
       "qua", "ish", "bra", "cor", "del", "fen", "gal", "hol", "jun", "kes", "mar", "nov", "pel", "sov", "tav", "yl"]
END_F = ["a", "ia", "ine", "elle", "ra", "wyn", "ette", "isa", "ena", "ith"]
END_M = ["o", "an", "ek", "ir", "us", "en", "or", "ald", "im", "orn"]
END_PET = ["o", "y", "i", "ix", "ble", "kin", "sy", "pip"]
PLACE_SUF = ["ford", "mere", "wick", "holm", "dale", "by", "ton", "haven", "stead", "port", "combe", "moor"]
ORG_SUF = ["Foods", "Logistics", "Dental", "Books", "Motors", "Bakery", "Labs", "Print", "Insurance", "Freight",
           "Studios", "Brewing", "Hardware", "Pharmacy", "Clinic", "Textiles"]
# real or famous names the syllables could produce by chance; --avoid-names adds dev/test names
BLOCK = set("""anna ella emma mila lina lena nina nora sara tara kara vera dana hana mona rita rosa lola tina dora
luna elsa bella maria mira leo milo hugo otto bruno theo enzo ivan omar karl kai ben sam zeus hera thor loki odin
nemo simba nala yoda frodo zelda mario luigi elvis adele oprah pele kobe serena venus mars apollo athena madonna
rihanna shakira beyonce obama biden trump musk newton darwin einstein mozart picasso messi moana tarzan dracula
ramen salsa karma sofa bravo tango delta sierra kilo lima oscar romeo juliet india yankee zulu sonia tania talia
delia celia lilia nadia lydia elena irina karina marina selena alina dalia sasha misha pasha dasha ivana diana
lara kira mara zara vivian liam noah owen ryan evan dylan logan conor rowan ronan ruben tomas marcus lucas darius
julius cyrus magnus remo dino nico rico marco carlo ali ari eli levi ezra ira isla ava eva mia pia ria lia
""".split())

MAX_FACTS = 3
HIST_TURNS = 6

FEMALE_ROLES = ["sister", "mother", "aunt", "daughter", "wife", "grandmother", "niece"]
MALE_ROLES = ["brother", "father", "uncle", "son", "husband", "grandfather", "nephew"]
NEUTRAL_ROLES = ["friend", "best_friend", "boss", "colleague", "neighbour", "cousin", "roommate", "landlord",
                 "teammate", "classmate"]
SPOUSE = {"wife", "husband"}

OCCUPATIONS = ["nurse", "plumber", "electrician", "accountant", "chef", "pharmacist", "mechanic", "paramedic",
               "librarian", "baker", "carpenter", "pilot", "firefighter", "bus driver", "software engineer",
               "physiotherapist", "social worker", "welder", "florist", "barber", "translator", "surveyor",
               "lab technician", "midwife", "zookeeper", "courier", "cashier", "receptionist", "tailor", "beekeeper"]
HOBBIES = ["rock climbing", "knitting", "birdwatching", "pottery", "chess", "gardening", "fishing", "woodworking",
           "photography", "board games", "archery", "calligraphy", "kayaking", "juggling"]
INSTRUMENTS = ["cello", "violin", "drums", "bass guitar", "trumpet", "piano", "ukulele", "flute", "accordion",
               "harmonica", "saxophone", "banjo"]
FOODS = ["dumplings", "lasagna", "pad thai", "tacos", "curry", "pancakes", "falafel", "risotto", "pierogi",
         "gnocchi", "paella", "goulash"]
COLORS = ["teal", "green", "purple", "orange", "yellow", "maroon", "navy blue", "lilac", "turquoise", "mustard"]
ALLERGIES = ["peanuts", "shellfish", "pollen", "penicillin", "bee stings", "dust", "sesame", "latex"]
PETS = ["dog", "cat", "rabbit", "parrot", "hamster"]

# relation -> value kind; a gloss tells GLM what the relation means (a definition, not a wording)
GLOSS = {
    "occupation": "their job", "employer": "the company they work for", "city": "the town where they live",
    "hometown": "the town they grew up in", "age": "their age in years", "hobby": "a hobby of theirs",
    "instrument": "an instrument they play", "favorite_food": "their favourite food",
    "favorite_color": "their favourite colour", "allergy": "something they are allergic to",
    "dog": "the name of their dog", "cat": "the name of their cat", "rabbit": "the name of their rabbit",
    "parrot": "the name of their parrot", "hamster": "the name of their hamster", "car": "a car",
}
ATTR_RELS = ["occupation", "employer", "city", "hometown", "age", "hobby", "instrument", "favorite_food",
             "favorite_color", "allergy", "dog", "cat", "rabbit", "parrot"]
CORRECT_RELS = ["occupation", "employer", "city", "age", "favorite_food", "favorite_color", "dog", "cat"]
FORMER_RELS = ["occupation", "employer", "city"]
LOOK_RELS = {
    "question": ["occupation", "employer", "city", "age", "dog", "cat", "hobby", "instrument", "allergy"],
    "plan": ["occupation", "employer", "city", "dog", "cat", "instrument", "hobby"],
    "doubt": ["occupation", "employer", "city", "age", "allergy", "hobby"],
    "someone_else": ["occupation", "employer", "city", "age", "dog", "cat"],
    "hypothetical": ["occupation", "employer", "city", "dog", "cat"],
    "ambiguous_pronoun": ["occupation", "employer", "city", "age", "hobby", "dog", "cat", "instrument"],
}
NEG_RELS = ["dog", "cat", "rabbit", "parrot", "car"]
# frame-spec modes / acts for the look-alikes. "doubt" has no mode of its own in frame-spec.md; CHECK is our choice
# (a speaker unsure of a fact is checking it). Change here if the Thread manager rules otherwise.
LOOK_MODE = {"question": ("ASK", "QUESTION"), "plan": ("PLAN", "PLAN"), "doubt": ("CHECK", "CHECK"),
             "someone_else": ("STATE", "REPORTED"), "hypothetical": ("SUPPOSE", "SUPPOSE"),
             "confirm": ("CHECK", "CHECK"), "ambiguous_pronoun": ("UNCLEAR", "UNCLEAR")}
LOOKALIKES = ["question", "plan", "doubt", "someone_else", "hypothetical", "negation_only", "confirm",
              "ambiguous_pronoun"]
WEIGHTS = {"teach": 3.0, "correct": 2.0, "backref": 2.0, "former": 1.5, "jobhome": 1.0, "ask": 1.5,
           "smalltalk": 0.8, **{k: 0.6 for k in LOOKALIKES}}
# what the intent means, in the abstract (no example wording)
INTENT_GLOSS = {
    "teach": "the user tells the assistant these facts as plainly true now",
    "correct": "the user corrects something they said earlier: the new value replaces the old one",
    "backref": "the user tells a new fact about a person they named earlier, but refers to that person only in the "
               "way given (never by name)",
    "former": "the user tells a fact that was true in the past and is no longer true; the message must make it "
              "clear that it is over",
    "jobhome": "in one single sentence the user tells both facts as true now",
    "ask": "the user asks the assistant a question to get back something they told it before; the user does not "
           "say the answer",
    "question": "the user asks a yes/no question whether this is true; they do not know; use a question mark",
    "plan": "the user says this will or may happen in the future; it is not true yet",
    "doubt": "the user says they are unsure whether this is true",
    "someone_else": "the user passes on what someone else claims; the user does not vouch for it",
    "hypothetical": "the user imagines this as a what-if; it is not real",
    "negation_only": "the user says the owner does not have this at all; no name or value for it is given",
    "confirm": "the user checks back with the assistant that this earlier fact is right; they are checking, not "
               "telling",
    "ambiguous_pronoun": "the user names both people in the message, then tells the fact about one of them using "
                         "only the pronoun given as the subject, so it is unclear which of the two it means",
    "smalltalk": "chit-chat with no facts about anyone (not even the user) and no names",
}


def role_word(role: str) -> str:
    return role.replace("_", " ")


class World:
    def __init__(self, rng: random.Random, avoid: set):
        self.rng, self.avoid, self.used = rng, avoid, set()

    def _fresh(self, make, tries=500):
        for _ in range(tries):
            s = make()
            low = s.lower()
            if (4 <= len(low.replace(" ", "")) <= 14 and low not in BLOCK and low not in self.avoid
                    and not any(w in self.used for w in low.split()) and not any(c * 3 in low for c in low)
                    and not any(v * 2 in low for v in "iuy")):
                self.used.update(low.split())
                return s
        raise RuntimeError("name space exhausted")

    def person_name(self, gender):
        r = self.rng
        return self._fresh(lambda: (r.choice(SYL) + (r.choice(SYL) if r.random() < 0.35 else "")
                                    + r.choice(END_F if gender == "f" else END_M)).capitalize())

    def pet_name(self):
        r = self.rng
        return self._fresh(lambda: (r.choice(SYL) + r.choice(END_PET)).capitalize())

    def place(self):
        r = self.rng
        return self._fresh(lambda: (r.choice(SYL) + r.choice(SYL[:30]) + r.choice(PLACE_SUF)).capitalize())

    def org(self):
        r = self.rng
        return self._fresh(lambda: (r.choice(SYL) + r.choice(SYL)).capitalize() + " " + r.choice(ORG_SUF))


def value_for(rel, W: World, taken: set):
    r = W.rng
    pools = {"occupation": OCCUPATIONS, "hobby": HOBBIES, "instrument": INSTRUMENTS, "favorite_food": FOODS,
             "favorite_color": COLORS, "allergy": ALLERGIES}
    for _ in range(200):
        if rel in pools:
            v = r.choice(pools[rel])
        elif rel in ("employer",):
            v = W.org()
        elif rel in ("city", "hometown"):
            v = W.place()
        elif rel == "age":
            v = str(r.randint(9, 88))
        elif rel in PETS:
            v = W.pet_name()
        else:
            raise ValueError(rel)
        if v not in taken:
            taken.add(v)
            return v
    raise RuntimeError("value pool exhausted: " + rel)


def fact(owner, rel, value, mode, old=None):
    assert rel in REL_NAMES, rel
    f = {"owner": owner, "rel": rel, "value": value, "mode": mode}
    if old is not None:
        f["old"] = old
    return f


def frame(act, facts=(), ask=None):
    return {"act": act, "facts": list(facts), "ask": ask}


class Dialog:
    def __init__(self, did, rng, avoid):
        self.id, self.rng = did, rng
        self.W = World(rng, avoid)
        n = rng.choice([3, 4, 4, 5])
        roles, people, spouse = [], [], False
        for _ in range(n):
            g = rng.choice("fm")
            while True:
                pool = (FEMALE_ROLES if g == "f" else MALE_ROLES) + NEUTRAL_ROLES
                role = rng.choice(pool)
                if role not in roles and not (role in SPOUSE and spouse):
                    break
            spouse |= role in SPOUSE
            roles.append(role)
            people.append({"name": self.W.person_name(g), "gender": g, "role": role})
        self.people = people
        self.by = {p["name"]: p for p in people}
        self.taken = set()
        self.corrected = set()
        self.stored = {}              # (owner, rel) -> value, current (ASSERT/CORRECT) only
        self.intro = {}               # name -> turn index of its intro fact
        self.named = {}               # name -> list of turn indexes where the name must appear
        self.turns = []

    # ---- helpers
    def k(self):
        return len(self.turns) + 1

    def visible_named(self):
        lo = self.k() - HIST_TURNS
        return {n for n, ks in self.named.items() if any(k >= lo for k in ks)}

    def owner_label(self, o):
        if o == "me":
            return "the user"
        p = self.by[o]
        return f"{o} (the user's {role_word(p['role'])})"

    def fact_line(self, f, subject=None):
        s = subject or self.owner_label(f["owner"])
        return f"owner: {s}; relation: {f['rel']} ({GLOSS.get(f['rel'], role_word(f['rel']))}); value: \"{f['value']}\""

    def new_attr(self, owner, rels):
        rels = [r for r in rels if (owner, r) not in self.stored]
        if not rels:
            return None
        rel = self.rng.choice(rels)
        return fact(owner, rel, value_for(rel, self.W, self.taken), "ASSERT")

    def add(self, intent, gold, must, lines, first_person=False, must_not=(), reply_must_not=(), ref=None,
            role_words=(), cue=None, names=()):
        t = {"k": self.k(), "intent": intent, "gloss": INTENT_GLOSS[intent], "lines": lines, "gold": gold,
             "must": list(dict.fromkeys(must)), "first_person": first_person, "must_not": list(must_not),
             "reply_must_not": list(reply_must_not), "ref": ref, "role_words": [list(x) for x in role_words],
             "cue": cue or intent}
        for n in names:
            self.named.setdefault(n, []).append(t["k"])
        self.turns.append(t)

    def owners_pool(self, intro_only=True):
        return ["me"] + [n for n in self.intro] if intro_only else ["me"] + list(self.by)

    # ---- intents
    def teach(self):
        r = self.rng
        n = r.choices([1, 2, 3], [3, 4, 2])[0]
        facts, names, rw = [], [], []
        new_people = [p for p in self.people if p["name"] not in self.intro]
        want_intro = new_people and (not self.intro or r.random() < 0.5)
        if want_intro:
            p = r.choice(new_people)
            facts.append(fact("me", p["role"], p["name"], "ASSERT"))
            names.append(p["name"])
            rw.append([role_word(p["role"])])
            self.intro[p["name"]] = self.k()
        subj = [f["value"] for f in facts] or [r.choice(self.owners_pool())]
        while len(facts) < n:
            owner = subj[0] if (facts and r.random() < 0.8) else r.choice(self.owners_pool())
            f = self.new_attr(owner, ATTR_RELS)
            if f is None:
                break
            facts.append(f)
            if owner != "me":
                names.append(owner)
            if len({x["owner"] for x in facts}) > 2:
                facts.pop()
                break
        if not facts:
            return False
        for f in facts:
            self.stored[(f["owner"], f["rel"])] = f["value"]
        must = [f["value"] for f in facts] + [f["owner"] for f in facts if f["owner"] != "me"]
        self.add("teach", frame("STATE", facts), must, [self.fact_line(f) for f in facts],
                 first_person=any(f["owner"] == "me" for f in facts), role_words=rw, names=names)
        return True

    def correct(self):
        r = self.rng
        cands = [(o, rel) for (o, rel) in self.stored if rel in CORRECT_RELS and (o, rel) not in self.corrected]
        if not cands:
            return False
        o, rel = r.choice(sorted(cands))
        old = self.stored[(o, rel)]
        new = value_for(rel, self.W, self.taken)
        name_old = r.random() < 0.5
        f = fact(o, rel, new, "CORRECT", old if name_old else None)
        self.stored[(o, rel)] = new
        self.corrected.add((o, rel))
        must = [new] + ([o] if o != "me" else []) + ([old] if name_old else [])
        lines = [self.fact_line(f), f"old value said earlier: \"{old}\" ("
                 + ("the message must name the old value too)" if name_old else "the message must NOT name it)")]
        self.add("correct", frame("CORRECT", [f]), must, lines, first_person=o == "me",
                 must_not=[] if name_old else [old], names=[o] if o != "me" else [])
        return True

    def backref(self):
        r = self.rng
        vis = self.visible_named()
        opts = []
        for n in sorted(vis):
            p = self.by[n]
            same = [m for m in vis if self.by[m]["gender"] == p["gender"]]
            if len(same) == 1:
                opts.append((n, "pronoun"))
            if n in self.intro and self.intro[n] >= self.k() - HIST_TURNS:
                opts.append((n, "role"))
        opts = [(n, kind) for n, kind in opts if any((n, rel) not in self.stored for rel in ATTR_RELS)]
        if not opts:
            return False
        n, kind = r.choice(opts)
        p = self.by[n]
        f = self.new_attr(n, ATTR_RELS)
        self.stored[(n, f["rel"])] = f["value"]
        if kind == "pronoun":
            ref = {"kind": "pronoun", "gender": p["gender"],
                   "words": ["she", "her", "hers"] if p["gender"] == "f" else ["he", "him", "his"]}
            how = "only by a " + ("she/her" if p["gender"] == "f" else "he/him/his") + " pronoun"
        else:
            ref = {"kind": "role", "role": p["role"], "words": [role_word(p["role"])]}
            how = f"only by the role word \"{role_word(p['role'])}\" (as the user's {role_word(p['role'])})"
        lines = [self.fact_line(f, subject=f"{n}, referred to {how}")]
        self.add("backref", frame("STATE", [f]), [f["value"]], lines, must_not=[n], reply_must_not=[n], ref=ref)
        return True

    def former(self):
        r = self.rng
        owner = r.choice(self.owners_pool())
        rel = r.choice(FORMER_RELS)
        f = fact(owner, rel, value_for(rel, self.W, self.taken), "FORMER")
        self.add("former", frame("STATE", [f]), [f["value"]] + ([owner] if owner != "me" else []),
                 [self.fact_line(f)], first_person=owner == "me", names=[owner] if owner != "me" else [])
        return True

    def jobhome(self):
        r = self.rng
        owners = [o for o in self.owners_pool() if (o, "occupation") not in self.stored and (o, "city") not in self.stored]
        if not owners:
            return False
        o = r.choice(owners)
        fs = [fact(o, "occupation", value_for("occupation", self.W, self.taken), "ASSERT"),
              fact(o, "city", value_for("city", self.W, self.taken), "ASSERT")]
        for f in fs:
            self.stored[(o, f["rel"])] = f["value"]
        self.add("jobhome", frame("STATE", fs), [f["value"] for f in fs] + ([o] if o != "me" else []),
                 [self.fact_line(f) for f in fs], first_person=o == "me", names=[o] if o != "me" else [])
        return True

    def ask(self):
        if not self.stored:
            return False
        o, rel = self.rng.choice(sorted(self.stored))
        val = self.stored[(o, rel)]
        a = {"owner": o, "rel": rel, "inverse": False}
        self.add("ask", frame("ASK", [], a), [o] if o != "me" else [],
                 [f"asked: owner: {self.owner_label(o)}; relation: {rel} ({GLOSS.get(rel, role_word(rel))}); "
                  f"the answer \"{val}\" must NOT appear"], first_person=o == "me", must_not=[val],
                 cue="ask", names=[o] if o != "me" else [])
        return True

    def lookalike(self, kind):
        r = self.rng
        act, mode = LOOK_MODE.get(kind, (None, None))
        if kind == "confirm":
            if not self.stored:
                return False
            o, rel = r.choice(sorted(self.stored))
            f = fact(o, rel, self.stored[(o, rel)], mode)
            self.add(kind, frame(act, [f]), [f["value"]] + ([o] if o != "me" else []), [self.fact_line(f)],
                     first_person=o == "me", names=[o] if o != "me" else [])
            return True
        if kind == "negation_only":
            owners = [o for o in self.owners_pool() if any((o, x) not in self.stored for x in NEG_RELS)]
            o = r.choice(owners)
            rel = r.choice([x for x in NEG_RELS if (o, x) not in self.stored])
            self.add(kind, frame("NEGATE", []), [o] if o != "me" else [],
                     [f"owner: {self.owner_label(o)}; relation: {rel}; no value"], first_person=o == "me",
                     role_words=[[role_word(rel)]], names=[o] if o != "me" else [])
            return True
        if kind == "ambiguous_pronoun":
            for g in r.sample("fm", 2):
                same = [p["name"] for p in self.people if p["gender"] == g]
                if len(same) >= 2:
                    break
            else:
                return False
            intro_first = sorted(same, key=lambda n: (n not in self.intro, r.random()))
            a, b = intro_first[:2]
            pron = "she" if g == "f" else "he"
            rel = r.choice(LOOK_RELS[kind])
            f = fact(pron, rel, value_for(rel, self.W, self.taken), mode)
            self.add(kind, frame(act, [f]), [a, b, pron, f["value"]],
                     [f"people named: {a} and {b}; pronoun owner: \"{pron}\"; relation: {rel} "
                      f"({GLOSS.get(rel, rel)}); value: \"{f['value']}\""], names=[a, b])
            return True
        rels = LOOK_RELS[kind]
        pool = [o for o in self.owners_pool() if not (kind == "someone_else" and o == "me")]
        o = r.choice(pool)
        rel = r.choice(rels)
        f = fact(o, rel, value_for(rel, self.W, self.taken), mode)
        must = [f["value"]] + ([o] if o != "me" else [])
        lines = [self.fact_line(f)]
        names = [o] if o != "me" else []
        ask = None
        if kind == "question":
            ask = {"owner": o, "rel": rel, "value": f["value"], "inverse": False}
        if kind == "someone_else":
            others = [n for n in self.intro if n != o]
            if others and r.random() < 0.5:
                src = r.choice(others)
                must.append(src)
                names.append(src)
                lines.append(f"the claim comes from {self.owner_label(src)}, named in the message")
            else:
                lines.append("the claim comes from an unnamed source (no name)")
        self.add(kind, frame(act, [f], ask), must, lines, first_person=o == "me", names=names)
        return True

    def smalltalk(self):
        self.add("smalltalk", frame("CHAT", []), [], ["no facts"], must_not=list(self.by))
        return True

    def run(self, n_turns):
        r = self.rng
        self.teach()
        while len(self.turns) < n_turns:
            ks = list(WEIGHTS)
            kind = r.choices(ks, [WEIGHTS[x] for x in ks])[0]
            fn = getattr(self, kind, None)
            ok = fn() if fn else self.lookalike(kind)
            if not ok:
                self.teach() or self.smalltalk()
        return {"dialog_id": self.id, "people": self.people, "opener": r.random() < 0.5,
                "proper_values": sorted(v for v in self.taken if v[:1].isupper()),
                "turns": self.turns}


def make_seeds(seed: int, n: int, avoid=frozenset()):
    out = []
    for i in range(n):
        rng = random.Random(f"lis320-{seed}-{i}")
        d = Dialog(f"s320-{seed}-{i:05d}", rng, set(avoid))
        out.append(d.run(rng.randint(6, 8)))
    return out


WRITE = {"ASSERT", "CORRECT"}


def selftest():
    a = make_seeds(7, 300)
    b = make_seeds(7, 300)
    assert json.dumps(a) == json.dumps(b), "not deterministic"
    c = Counter()
    for d in a:
        assert 6 <= len(d["turns"]) <= 8
        names = [p["name"] for p in d["people"]]
        assert len(set(n.lower() for n in names)) == len(names)
        assert not any(n.lower() in BLOCK for n in names)
        for t in d["turns"]:
            c[t["intent"]] += 1
            g = t["gold"]
            for f in g["facts"]:
                assert f["rel"] in REL_NAMES, f
            if g["ask"]:
                assert g["ask"]["rel"] in REL_NAMES
            if t["intent"] in LOOKALIKES or t["intent"] in ("ask", "smalltalk", "former"):
                assert not any(f["mode"] in WRITE for f in g["facts"]), t
            if t["intent"] == "backref":
                o = g["facts"][0]["owner"]
                assert o not in t["must"] and o in t["must_not"]
                earlier = [u for u in d["turns"][max(0, t["k"] - 1 - HIST_TURNS): t["k"] - 1] if o in u["must"]]
                assert earlier, "backref owner not named in the visible history"
                if t["ref"]["kind"] == "pronoun":
                    g_ = next(p["gender"] for p in d["people"] if p["name"] == o)
                    vis = {n for u in d["turns"][max(0, t["k"] - 1 - HIST_TURNS): t["k"] - 1] for n in u["must"]
                           if n in names}
                    assert [n for n in vis if next(p["gender"] for p in d["people"] if p["name"] == n) == g_] == [o]
            if t["intent"] == "correct":
                f = g["facts"][0]
                assert f["mode"] == "CORRECT" and ("old" in f) == (f.get("old") in t["must"])
            blob = json.dumps(t["lines"]) + t["gloss"]
            assert "used to" not in blob.lower()
    assert all(c[k] > 0 for k in WEIGHTS), c
    print("seed selftest OK:", len(a), "dialogs,", sum(c.values()), "turns;", dict(sorted(c.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=320)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--out")
    ap.add_argument("--avoid-names", help="file, one name per line (dev/test names to never use)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    avoid = set()
    if a.avoid_names:
        avoid = {x.strip().lower() for x in Path(a.avoid_names).read_text().splitlines() if x.strip()}
    seeds = make_seeds(a.seed, a.n, avoid)
    Path(a.out).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in seeds), encoding="utf-8")
    c = Counter(t["intent"] for d in seeds for t in d["turns"])
    print(json.dumps({"dialogs": len(seeds), "turns": sum(c.values()), "intents": dict(sorted(c.items()))}))


if __name__ == "__main__":
    sys.exit(main())
