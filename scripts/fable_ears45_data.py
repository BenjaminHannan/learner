#!/usr/bin/env python3
"""Rung 1 of design 43 -- tokeniser, lexicon, relation tables, name/value pools, the sealed
frame split, the sentence generator, and the held-out enforcement checks of E.3.

Run `--panels <dir>` to generate and hash every panel; `--report` to print the sizes.
Nothing here imports torch.  `fable_listening_english` is imported READ-ONLY, for
RELATION_MAP, canonical_relation, the validator and the confirm policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_listening_english as LE          # read-only
import fable_ears45_frames as FR              # read-only
from fable_ears45_lexicon import COMMON_WORDS, DELIBERATELY_OMITTED

FORMAT = "fable-ears45/rung1/1"
SPLIT_NS = "fable-ears45/split/v1"
MAX_TOKENS = 32
N_OPQ = 8
JACCARD_MAX = 0.8

# ---------------------------------------------------------------------------------------
# 1.  TOKENISER  (B.1; plain software, deterministic, outside the network)
# ---------------------------------------------------------------------------------------

_PUNCT_CHARS = ".,;:!?()\"—–"
_MD_RE = re.compile(r"\*\*|__|`|\*|_")
_WORD_RE = re.compile(r"[^\s" + re.escape(_PUNCT_CHARS) + r"*_`]+")
_CLITIC_RE = re.compile(r"(n['’]t|['’](?:s|m|re|ve|ll|d))$", re.I)
_PUNCT_RE = re.compile("[" + re.escape(_PUNCT_CHARS) + "]")


class Token:
    __slots__ = ("text", "start", "end", "md", "is_punct")

    def __init__(self, text, start, end, md, is_punct):
        self.text, self.start, self.end = text, start, end
        self.md, self.is_punct = md, is_punct

    def __repr__(self):
        return f"Token({self.text!r},{self.start},{self.end})"


def tokenise(raw: str) -> list[Token]:
    """Split into word / clitic / punctuation tokens keeping (char_start, char_end).

    Markdown wrappers (**x**, `x`, a leading "- ") are removed from the token stream but
    remembered as the md bit; the char span always covers the INNER characters, so a
    byte-exact substring copy of a name never picks up a wrapper.
    """
    text = unicodedata.normalize("NFC", raw)
    i, n, out, md_depth = 0, len(text), [], 0
    bullet = False
    if text[:2] == "- ":
        i, bullet = 2, True
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        m = _MD_RE.match(text, i)
        if m:
            md_depth = 0 if md_depth else 1
            i = m.end()
            continue
        m = _PUNCT_RE.match(text, i)
        if m:
            out.append(Token(text[i:i + 1], i, i + 1, md_depth, True))
            i += 1
            continue
        m = _WORD_RE.match(text, i)
        if not m:
            i += 1
            continue
        s, e = m.start(), m.end()
        word = text[s:e]
        c = _CLITIC_RE.search(word)
        if c and c.start() > 0:
            out.append(Token(text[s:s + c.start()], s, s + c.start(), md_depth, False))
            out.append(Token(text[s + c.start():e], s + c.start(), e, md_depth, False))
        else:
            out.append(Token(word, s, e, md_depth, False))
        i = e
    if bullet and out:
        out[0].md = 1
    return out


# ---------------------------------------------------------------------------------------
# 2.  RELATIONS  (40 keys + OPEN; wordings compatible with the UNCHANGED validator)
# ---------------------------------------------------------------------------------------
# A wording may only be used with key K if LE.canonical_relation(wording) == K, OR K is one
# of LE.KNOWN_RELATIONS and the wording is one of RELATION_MAP's own wordings for K.  That
# is what `_validate_shape`'s relation zip-check enforces, so the twelve RELATION_MAP keys
# get several wordings each and every other relation is "snake case of its own noun".

CANON_WORDINGS = {
    "city": [("city", "noun"), ("town", "noun"), ("lives in", "verb"), ("moved to", "verb"),
             ("resides in", "verb"), ("is in", "verb"),
             ("lives", "verb3"), ("resides", "verb3"),
             ("live", "vbase"), ("reside", "vbase")],
    "origin": [("origin", "noun"), ("hometown", "noun"), ("is from", "verb"),
               ("comes from", "verb3"), ("come from", "vbase")],
    "birthplace": [("birthplace", "noun"), ("born in", "verb"), ("born", "verb")],
    "mother": [("mother", "noun"), ("mom", "noun"), ("mum", "noun")],
    "father": [("father", "noun"), ("dad", "noun")],
    "employer": [("employer", "noun"), ("works at", "verb"), ("works for", "verb"),
                 ("works", "verb3"), ("work", "vbase"), ("work at", "vbase")],
    "training_data": [("training data", "noun"), ("trained on", "verb")],
    "creator": [("creator", "noun"), ("created by", "verb"), ("made", "verb")],
    "favorite_color": [("favorite color", "noun"), ("favourite colour", "noun"),
                       ("favorite colour", "noun"), ("favourite color", "noun")],
    "age": [("age", "noun"), ("years old", "noun"), ("year old", "noun")],
    "friend": [("friend", "noun"), ("best friend", "noun")],
    "sibling": [("sibling", "noun"), ("brother", "noun"), ("sister", "noun")],
}

# Declared relations: one noun wording each, key = snake of the noun.  Not in RELATION_MAP,
# so LE.canonical_relation(noun) == noun already.  These ARE declared in the (simulated)
# notebook, so the known_relation_wording feature bit fires for them.
DECLARED_PERSON = ["teacher", "boss", "neighbour", "cousin", "roommate",
                   "doctor", "coach", "landlord", "mentor", "partner"]
DECLARED_LITERAL = ["school", "job", "hobby", "pet", "car", "bike", "phone", "street",
                    "team", "band", "book", "film", "song", "dish", "drink", "subject",
                    "sport", "game"]

# OPEN relations: nouns NOT declared in the notebook.  Gold relkey = OPEN for all of them;
# the decoder builds the key as snake-case of the pointed words (B.4).  20 % are test-only.
OPEN_NOUNS = ["breakfast", "lunch", "dinner", "coat", "hat", "bag", "cup", "plate",
              "chair", "table", "bed", "door", "window", "clock", "camera", "radio",
              "guitar", "piano", "ticket", "letter", "picture", "garden", "kitchen",
              "roof", "floor", "wall", "key", "box", "shirt", "dress", "shoe", "bus",
              "train", "boat", "plane", "river", "hill", "island", "bridge", "market"]

PERSON_KEYS = set(LE.PERSON_RELATIONS) | set(DECLARED_PERSON)

ALL_KEYS = (sorted(CANON_WORDINGS) + sorted(DECLARED_PERSON) + sorted(DECLARED_LITERAL))
assert len(ALL_KEYS) == 40, len(ALL_KEYS)
KEY_INDEX = {k: i for i, k in enumerate(ALL_KEYS)}
OPEN_INDEX = 40
N_RELKEY = 41

# The relation-wording TABLE (B.4 key 2).  Seeded from RELATION_MAP; the declared nouns are
# added because the notebook has declared them.  Held-out wordings stay IN the table, which
# is exactly why a held-out wording produces an ECHO with the right key instead of a miss.
WORDING_TABLE = {}
for _k, _ws in CANON_WORDINGS.items():
    for _w, _t in _ws:
        WORDING_TABLE[_w] = _k
for _n in DECLARED_PERSON + DECLARED_LITERAL:
    WORDING_TABLE[_n] = _n
for _w, _k in LE.RELATION_MAP.items():          # everything Qwen's table already knew
    WORDING_TABLE.setdefault(_w, _k)

for _w, _k in WORDING_TABLE.items():
    assert LE.canonical_relation(_w) == _k or _k in LE.KNOWN_RELATIONS, (_w, _k)


def relkey_gold(key: str) -> int:
    return KEY_INDEX.get(key, OPEN_INDEX)


# ---------------------------------------------------------------------------------------
# 3.  LEXICON  (deviation documented in fable_ears45_lexicon.py)
# ---------------------------------------------------------------------------------------

PAD, BOS, EOS = 0, 1, 2
OPQ0 = 3                                   # OPQ#1..#8 occupy 3..10
VOCAB0 = OPQ0 + N_OPQ                      # ordinary words start here


def _frame_words(frames) -> set[str]:
    out = set()
    for f in frames:
        bare = re.sub(r"\{[A-Z_0-9]+\}", " ", f.template)
        for w in tokenise(bare):
            out.add(w.text.casefold())
    return out


def _cue_words() -> set[str]:
    out = set()
    for s in list(LE.RELATION_MAP) + ["actually", "i meant", "correction", "sorry", "wait",
                                      "not", "but", "now", "no longer", "never"]:
        for w in tokenise(s):
            out.add(w.text.casefold())
    return out


class Lexicon:
    def __init__(self, train_frame_words: set[str]):
        words = set(COMMON_WORDS) | train_frame_words | _cue_words()
        words |= set(FR.OPENERS and [] or [])
        for p in _PUNCT_CHARS:
            words.add(p)
        for c in ("'s", "’s", "n't", "n’t", "'m", "'re", "'ve", "'ll", "'d",
                  "’m", "’re", "’ve", "’ll", "’d"):
            words.add(c)
        words -= set(DELIBERATELY_OMITTED)
        words = {w for w in words if w and not w.isdigit()}
        self.words = tuple(sorted(words))
        self.index = {w: VOCAB0 + i for i, w in enumerate(self.words)}
        self.size = VOCAB0 + len(self.words)

    def get(self, form: str):
        return self.index.get(form.casefold())

    def sha(self) -> str:
        h = hashlib.sha256(FORMAT.encode())
        for w in self.words:
            h.update(b"\n" + w.encode())
        return h.hexdigest()


# ---------------------------------------------------------------------------------------
# 4.  NAME AND VALUE POOLS  (E.3: disjoint train / dev / test)
# ---------------------------------------------------------------------------------------

_FIRST_NAMES = """
Mira Ana Omar Priya Mateo Yuki Nadia Linh Dilan Ren Freja Noa Zane Ivo Lena Tomas Sara
Kiran Hana Rafa Elif Bo Jonas Aiko Marek Nia Tariq Ines Pavel Suki Dario Mina Ravi Lotta
Emre Kaya Sven Rosa Halim Vera Mirko Dana Felix Anya Otto Lila Jun Petra Kofi Maya Rune
Salma Teo Ida Arun Nils Zara Hugo Lea Idris Saskia Gael Fatou Milan Nora Baris Elsa Reza
Talia Bram Oona Yara Kenji Selin Nuno Alma Joris Rania Eero Bela Sanne Arto Meret Kaito
Lior Anke Padma Sami Tove Ilya Neve Cato Rafi Juno Nadir Siri Ewan Maro Zeno Alba Kemal
Hilde Amir Tilda Oskar Rima Jarl Esme Bodhi Naia Ciaran Wren Soren Linnea Kwame Anouk
Matteo Ilaria Piet Runa Zola Dov Malin Tarek Sunniva Imre Aziza Kalle Neela Bence Orla
Yosef Greta Amara Duarte Signe Rasmus Leena Faris Mirela Toma Aida Ludo Karim Elke Rui
Nadja Sacha Iris Tudor Bella Onur Petr Maja Dinu Hakim Vesna Loic Tanja Ismail Kira Arne
Lucca Sana Frida Emeka Roos Bojan Ayla Kaspar Nerea Tomek Zeynep Alexei Ronja Jalil
""".split()

_SYLL_A = ("ka be to mi ra lo nu si va den par mel tor ken lis gor fen bal dor nim ves "
           "tal rem juk paz wen zor hal dri ost lun fer cav noz tib rul mek sar veld "
           "quin bra sto tre pil dov garn hel sef ombr urs yal zed ").split()
_SYLL_B = ("na li ro ta mis del van sen ka pur tel dan fim gos rel tam bir nov lek dar "
           "sim que ver ald ont ish umo erra ilo asta enko ovic aine elle ora uso ").split()

_PLACES_SEED = """
Porto Lisbon Oslo Kyoto Bogota Hanover Eilat Haifa Cadiz Leiden Tromso Bilbao Utrecht
Cork Brno Aarhus Galway Malmo Ghent Trieste Bergen Gdansk Tartu Kaunas Zadar Nimes
Ferrara Ravenna Ghazni Multan Mysore Kandy Surat Aomori Matsue Iwaki Busan Daegu Hue
Vinh Pemba Arusha Mbale Kisumu Kumasi Tamale Oran Sfax Annaba Batna Setif Gabes
""".split()

_ORG_HEADS = ("Cedar Iron Blue Northern Harbor Willow Quiet Amber Silver Granite Maple "
              "Copper Lantern Meadow River Pine Coral Stone Ember Hollow").split()
_ORG_TAILS = ("Books Works Labs Mills Press Foods Optics Motors Studio Health Systems "
              "Bakery Garden Bridge Supply Metals Forge Paper Coffee Design").split()

_COLOURS = ("teal blue green red yellow black white brown grey pink purple orange gold "
            "silver amber coral navy olive violet").split()
_SIMPLE_LITERALS = ("chess tennis piano guitar bread soup rice coffee tea milk juice "
                    "cats dogs birds horses running swimming cycling reading cooking "
                    "painting drawing science history maths art english music").split()


def _syllable_names(rng, n, used):
    out = []
    while len(out) < n:
        k = rng.choice((2, 2, 3))
        w = "".join(rng.choice(_SYLL_A if i == 0 else _SYLL_B) for i in range(k))
        w = w[0].upper() + w[1:]
        if w not in used:
            used.add(w)
            out.append(w)
    return out


def _syllable_places(rng, n, used):
    out = []
    while len(out) < n:
        w = rng.choice(_SYLL_A) + rng.choice(_SYLL_B) + rng.choice(("", "", "sk", "ford",
                                                                   "burg", "holm", "dal"))
        w = w[0].upper() + w[1:]
        if w not in used:
            used.add(w)
            out.append(w)
    return out


class Pools:
    """Disjoint train / dev / test pools for names, places, organisations and literals."""

    def __init__(self, seed: int = 45001):
        rng = random.Random(seed)
        used = set()
        names = list(dict.fromkeys(_FIRST_NAMES))
        for n in names:
            used.add(n)
        names += _syllable_names(rng, 3000 - len(names), used)
        rng.shuffle(names)
        self.names = {"train": names[:2000], "dev": names[2000:2500],
                      "test": names[2500:3000]}

        used_p = set(_PLACES_SEED)
        places = list(_PLACES_SEED) + _syllable_places(rng, 1200 - len(_PLACES_SEED),
                                                       used_p)
        rng.shuffle(places)
        self.places = {"train": places[:800], "dev": places[800:1000],
                       "test": places[1000:1200]}

        orgs = sorted({f"{a} {b}" for a in _ORG_HEADS for b in _ORG_TAILS})
        rng.shuffle(orgs)
        self.orgs = {"train": orgs[:260], "dev": orgs[260:330], "test": orgs[330:400]}

        cols = list(_COLOURS)
        rng.shuffle(cols)
        self.colours = {"train": cols[:12], "dev": cols[12:15], "test": cols[15:]}

        lits = list(_SIMPLE_LITERALS)
        rng.shuffle(lits)
        self.literals = {"train": lits[:20], "dev": lits[20:24], "test": lits[24:]}

        self.gibberish = ("brklt zzqx pflmn kthrz wmbkl xtnpr gbrtz vlkth mprkl tzqvn "
                          "shrkt dwnzl frtkm plnxg kvrtb jmwqz nthqd vzzlp".split())

        # Names that are also ordinary English words, all-lower-case names, 2-3 word names,
        # apostrophes / hyphens / accents, numbers -- panel T-hard-names (E.2).
        self.hard_names = ("Rose Will May Mark Hope Art Bill Grace Sky Daisy Summer River "
                           "Dawn Pearl Ruby Sunny Faith Joy Penny Rich Frank Wood Stone "
                           "Bell Cliff Dale Brook Heath Reed").split() + [
            "rosa", "milo", "ines", "juno", "kai", "lena", "omar", "yuki", "nadia", "tomas",
            "Mary Jane", "Jose Luis", "Ana Maria", "Jean Paul", "Li Wei", "Van Der Berg",
            "O'Brien", "O'Neill", "D'Souza", "Jean-Luc", "Anne-Marie", "Mary-Kate",
            "José", "Zoë", "René", "Björn", "Søren", "Niña",
            "Áine", "François",
        ]
        self.hard_values = (["Cedar Books", "New York", "San Jose", "Cape Town",
                             "Rio Branco", "Port Said", "Val d'Or", "St Ives"]
                            + [str(i) for i in range(5, 96)])

    def assert_disjoint(self):
        """E.3: the name / place / organisation / value pools never overlap."""
        for name, group in (("names", self.names), ("places", self.places),
                            ("orgs", self.orgs), ("colours", self.colours),
                            ("literals", self.literals)):
            for a, b in (("train", "dev"), ("train", "test"), ("dev", "test")):
                shared = set(group[a]) & set(group[b])
                assert not shared, f"{name}: {a}/{b} share {sorted(shared)[:5]}"
        return True

    def sha(self) -> str:
        h = hashlib.sha256(FORMAT.encode())
        for name, group in (("names", self.names), ("places", self.places),
                            ("orgs", self.orgs), ("colours", self.colours),
                            ("literals", self.literals)):
            for split in ("train", "dev", "test"):
                h.update(f"\n{name}.{split}".encode())
                for v in group[split]:
                    h.update(b"\t" + v.encode())
        return h.hexdigest()


# ---------------------------------------------------------------------------------------
# 5.  THE SEALED SPLIT  (E.3)
# ---------------------------------------------------------------------------------------

def _rank_key(ns, item_id):
    return hashlib.sha256(f"{ns}:{item_id}".encode()).hexdigest()


def rank_split(ids, ns, share):
    ranked = sorted(ids, key=lambda i: _rank_key(ns, i))
    n_out = round(len(ranked) * share)
    held = set(ranked[:n_out])
    return held


def skeleton(template: str) -> str:
    bare = re.sub(r"\{[A-Z_0-9]+\}", " ", template).lower()
    return " ".join(re.findall(r"[a-z']+", bare))


def _jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


class Split:
    """Frames -> train / dev / new(test) / far, plus wording, OPEN-noun and opener splits.

    Unit of the split is a SKELETON GROUP (talker24's rule): frames that differ only in
    punctuation or placeholders travel together.  After the rank split, any test group whose
    token-set Jaccard against some train group is >= 0.8 is MOVED BACK to train, so the E.3
    assertion is true by construction and the move is reported, never hidden.
    """

    TEST_SHARE, DEV_SHARE = 0.18, 0.08

    def __init__(self):
        self.train, self.dev, self.new, self.far = [], [], [], []
        self.repaired = []
        # Skeleton groups are GLOBAL, not per family: "{S}'s {R} happens to be {V}." and
        # "{S}'s {R} happens to be {O}." are the same English wording, so training one
        # while holding out the other would be leakage.
        far_all = [f for f in FR.ALL_FRAMES.values() if f.far]
        near = [f for f in FR.ALL_FRAMES.values() if not f.far]
        groups = {}
        for f in near:
            groups.setdefault(skeleton(f.template), []).append(f)
        keys = sorted(groups)
        held_test = rank_split(keys, f"{SPLIT_NS}:test", self.TEST_SHARE)
        rest = [k for k in keys if k not in held_test]
        held_dev = rank_split(rest, f"{SPLIT_NS}:dev",
                              self.DEV_SHARE / (1 - self.TEST_SHARE))
        train_keys = [k for k in rest if k not in held_dev]
        train_sets = [set(k.split()) for k in train_keys]
        for k in sorted(held_test):
            ks = set(k.split())
            if any(_jacc(ks, t) >= JACCARD_MAX for t in train_sets):
                self.repaired.append(k)
                train_keys.append(k)
                train_sets.append(ks)
            else:
                self.new += groups[k]
        for k in sorted(held_dev):
            self.dev += groups[k]
        for k in train_keys:
            self.train += groups[k]
        # a T-far construction must not share a skeleton with anything trained
        train_skels = {skeleton(f.template) for f in self.train}
        for f in far_all:
            if skeleton(f.template) in train_skels:
                self.train.append(f)
                self.repaired.append("far:" + f.id)
            else:
                self.far.append(f)
        self.train_skeletons = [set(skeleton(f.template).split()) for f in self.train]

        # relation wordings: 20 % per canonical key, never the last wording of a type
        self.wording_heldout = set()
        for key, ws in CANON_WORDINGS.items():
            order = sorted(ws, key=lambda w: _rank_key(f"{SPLIT_NS}:wording:{key}", w[0]))
            target = round(0.2 * len(ws))
            left = {t: sum(1 for w in ws if w[1] == t) for t in {w[1] for w in ws}}
            for w, t in order:
                if len(self.wording_heldout & {x[0] for x in ws}) >= target:
                    break
                if left[t] <= 1:
                    continue
                self.wording_heldout.add(w)
                left[t] -= 1

        self.open_heldout = rank_split(OPEN_NOUNS, f"{SPLIT_NS}:opennoun", 0.2)
        self.opener_heldout = rank_split(list(range(len(FR.OPENERS))),
                                         f"{SPLIT_NS}:openers", 3 / len(FR.OPENERS))

    def frames(self, level):
        return {"train": self.train, "dev": self.dev, "new": self.new,
                "far": self.far, "train+dev": self.train + self.dev,
                "train+new": self.train + self.new,
                "all": self.train + self.dev + self.new + self.far}[level]

    def wordings(self, key, kind, allow_heldout):
        out = [(w, t) for w, t in CANON_WORDINGS[key]
               if (kind == "any" or t == kind)
               and (allow_heldout or w not in self.wording_heldout)]
        return out

    def open_nouns(self, allow_heldout):
        return [n for n in OPEN_NOUNS
                if allow_heldout or n not in self.open_heldout]

    def openers(self, allow_heldout):
        return [o for i, o in enumerate(FR.OPENERS)
                if allow_heldout or i not in self.opener_heldout]

    def assert_heldout(self):
        """E.3, enforced by code BEFORE training."""
        train_bare = {re.sub(r"\{[A-Z_0-9]+\}", "", f.template).lower().strip(" .,:;!?-")
                      for f in self.train}
        for f in self.new + self.far:
            bare = re.sub(r"\{[A-Z_0-9]+\}", "", f.template).lower().strip(" .,:;!?-")
            assert bare not in train_bare, f"held-out frame equals a train frame: {f.id}"
        for f in self.new:
            ks = set(skeleton(f.template).split())
            worst = max((_jacc(ks, t) for t in self.train_skeletons), default=0.0)
            assert worst < JACCARD_MAX, f"{f.id} Jaccard {worst:.2f} vs train"
        train_tags = {(f.family, f.construction) for f in self.train}
        for f in self.far:
            assert (f.family, f.construction) not in train_tags, \
                f"T-far construction {f.family}/{f.construction} appears in TRAIN"
        return True

    def sha(self):
        h = hashlib.sha256(FORMAT.encode())
        for name, fs in (("train", self.train), ("dev", self.dev),
                         ("new", self.new), ("far", self.far)):
            h.update(f"\n[{name}]".encode())
            for f in sorted(fs, key=lambda x: x.id):
                h.update(f"\n{f.id}\t{f.construction}\t{f.template}".encode())
        h.update(("\nwordings:" + ",".join(sorted(self.wording_heldout))).encode())
        h.update(("\nopen:" + ",".join(sorted(self.open_heldout))).encode())
        h.update(("\nopeners:" + ",".join(map(str, sorted(self.opener_heldout)))).encode())
        return h.hexdigest()


# ---------------------------------------------------------------------------------------
# 6.  SENTENCE GENERATOR
# ---------------------------------------------------------------------------------------

ACTS15 = list(LE.ACTS) + ["multi", "dontknow"]
ACT_INDEX = {a: i for i, a in enumerate(ACTS15)}
SLOTS = ("SUBJ", "VAL", "ALIAS", "CANON", "CHOICE")
MAX_HOPS = 8

ACT_WEIGHTS = {                       # E.2, with the 5 % pending acts redistributed
    "teach": 0.295, "ask": 0.253, "correct": 0.084, "alias": 0.063,
    "person": 0.042, "forget": 0.042, "trap": 0.126, "smalltalk": 0.053, "unsure": 0.042,
}
ASK_HOPS = ((1, 0.50), (2, 0.333), (3, 0.167))
TEACH_FAMS = ("teach.noun", "teach.verb", "teach.link")
CORRECT_FAMS = ("correct.noun", "correct.verb", "correct.link")
ASK_FAMS = ("ask.noun", "ask.verb3", "ask.vbase", "ask.link")
TRAP_FAMS = ("trap.negation", "trap.hypo", "trap.hearsay", "trap.stmtq",
             "trap.leftover", "trap.multi")
UNSURE_FAMS = ("unsure.gibberish", "unsure.pronoun")


def render(template, fills):
    out, pos, spans = [], 0, []
    for part in re.split(r"(\{[A-Z_0-9]+\})", template):
        if part.startswith("{") and part.endswith("}"):
            text, subs = fills[part[1:-1]]
            for role, s, e in subs:
                spans.append([role, pos + s, pos + e])
            out.append(text)
            pos += len(text)
        else:
            out.append(part)
            pos += len(part)
    return "".join(out), spans


def _shift(spans, at, delta):
    for sp in spans:
        if sp[1] >= at:
            sp[1] += delta
        if sp[2] >= at:
            sp[2] += delta


class Generator:
    def __init__(self, split: Split, pools: Pools):
        self.split, self.pools = split, pools

    # -- pieces ---------------------------------------------------------------------
    def _pick_relation(self, rng, kind, value_kind, allow_heldout, person_only=False):
        """-> (key, surface, reltype, is_open)"""
        if kind in ("verb", "verb3", "vbase"):
            cands = [(k, w, t) for k in CANON_WORDINGS
                     for w, t in self.split.wordings(k, kind, allow_heldout)]
            k, w, t = rng.choice(cands)
            return k, w, "verb", False
        pool = []
        for k in CANON_WORDINGS:
            if person_only and k not in PERSON_KEYS:
                continue
            if value_kind == "person" and k not in PERSON_KEYS:
                continue
            if value_kind == "literal" and k in PERSON_KEYS:
                continue
            for w, t in self.split.wordings(k, "noun", allow_heldout):
                pool.append((k, w, False))
        declared = DECLARED_PERSON if (person_only or value_kind == "person") \
            else (DECLARED_LITERAL if value_kind == "literal"
                  else DECLARED_PERSON + DECLARED_LITERAL)
        pool += [(n, n, False) for n in declared]
        if not person_only and value_kind != "person":
            pool += [(n, n, True) for n in self.split.open_nouns(allow_heldout)]
        k, w, is_open = rng.choice(pool)
        return k, w, "noun", is_open

    def _value_for(self, rng, key, pool, hard=False):
        if hard and rng.random() < 0.6:
            return rng.choice(self.pools.hard_values)
        if key == "age":
            return str(rng.randint(5, 95))
        if key == "favorite_color":
            return rng.choice(self.pools.colours[pool])
        if key in ("city", "origin", "birthplace", "street"):
            return rng.choice(self.pools.places[pool])
        if key in ("employer", "school", "team", "band", "job"):
            return rng.choice(self.pools.orgs[pool])
        if key in ("training_data", "hobby", "pet", "sport", "subject", "drink",
                   "dish", "game", "book", "film", "song"):
            return rng.choice(self.pools.literals[pool])
        return rng.choice(self.pools.literals[pool] + self.pools.places[pool])

    def _name(self, rng, pool, hard=False):
        if hard:
            return rng.choice(self.pools.hard_names)
        return rng.choice(self.pools.names[pool])

    def _owner(self, rng, hops, name, allow_heldout, of_style):
        """Chain of hops-1 person relations plus the subject name."""
        inter = []
        for _ in range(hops - 1):
            k, w, t, _o = self._pick_relation(rng, "noun", "person", allow_heldout,
                                              person_only=True)
            inter.append((k, w))
        if of_style:
            text, subs = "", []
            if hops == 1:
                return name, [("S", 0, len(name))], inter
            parts = []
            for j in range(len(inter) - 1, -1, -1):
                parts.append(inter[j][1])
            text = ""
            for w in parts:
                text += "the " + w + " of "
            base = len(text)
            pos = 0
            for j, w in enumerate(parts):
                st = text.index("the " + w + " of ", pos)
                subs.append((f"H{len(inter) - 1 - j}", st + 4, st + 4 + len(w)))
                pos = st + 4 + len(w)
            text += name
            subs.append(("S", base, base + len(name)))
            return text, subs, inter
        text, subs = name, [("S", 0, len(name))]
        for j, (k, w) in enumerate(inter):
            text += "'s " + w
            subs.append((f"H{j}", len(text) - len(w), len(text)))
        return text, subs, inter

    # -- one example ----------------------------------------------------------------
    def sample(self, rng, level, name_pool, value_pool, allow_heldout,
               families=None, hard=False, hops_choice=None):
        frames = [f for f in self.split.frames(level)
                  if families is None or f.family in families]
        frame = rng.choice(frames)
        return self.build(rng, frame, name_pool, value_pool, allow_heldout, hard,
                          hops_choice)

    def build(self, rng, frame, name_pool, value_pool, allow_heldout, hard=False,
              hops_choice=None):
        fam, act = frame.family, frame.act
        fills, hops, item = {}, [], None
        name = self._name(rng, name_pool, hard)
        tmpl = frame.template
        pron_role = frame.construction.startswith(("first_person", "second_person"))

        if fam.startswith("ask."):
            h = hops_choice or 1
            if "{OWNER_OF}" in tmpl or "{OWNER}" in tmpl:
                of = "{OWNER_OF}" in tmpl
                if pron_role:
                    h = 1
                text, subs, inter = self._owner(rng, h, name, allow_heldout, of)
                fills["OWNER" if not of else "OWNER_OF"] = (text, subs)
            else:
                inter, h = [], 1
            vk = "person" if frame.value == "person" else "literal"
            key, surf, rt, is_open = self._pick_relation(
                rng, frame.kind, "person" if frame.value == "person" else "literal",
                allow_heldout)
            fills["R"] = (surf, [(f"H{h - 1}", 0, len(surf))])
            hops = [(k, w) for k, w in inter] + [(key, surf)]
        elif fam in ("teach.noun", "teach.verb", "teach.link", "correct.noun",
                     "correct.verb", "correct.link", "forget") or fam.startswith("trap."):
            vk = "person" if frame.value == "person" else "literal"
            key, surf, rt, is_open = self._pick_relation(rng, frame.kind, vk,
                                                         allow_heldout)
            fills["R"] = (surf, [("H0", 0, len(surf))])
            hops = [(key, surf)]
        else:
            key = surf = None
            vk = "none"

        fills["S"] = (name, [("S", 0, len(name))])
        if "{V}" in tmpl:
            v = self._value_for(rng, key, value_pool, hard)
            fills["V"] = (v, [("V", 0, len(v))])
        if "{O}" in tmpl:
            v = self._name(rng, name_pool, hard)
            fills["O"] = (v, [("V", 0, len(v))])
        if "{OLD}" in tmpl:
            old = (self._value_for(rng, key, value_pool, hard) if "{V}" in tmpl
                   else self._name(rng, name_pool, hard))
            fills["OLD"] = (old, [])
        if "{A}" in tmpl:
            a = self._name(rng, name_pool, hard)
            c = self._name(rng, name_pool, hard)
            while c == a:
                c = self._name(rng, name_pool, hard)
            fills["A"] = (a, [("A", 0, len(a))])
            fills["C"] = (c, [("C", 0, len(c))])
        if "{G}" in tmpl:
            fills["G"] = (rng.choice(self.pools.gibberish), [])
        if "{P}" in tmpl:
            fills["P"] = (rng.choice(("his", "her", "their", "its")), [])
        if "{N}" in tmpl:
            fills["N"] = (self._name(rng, name_pool, hard), [])
        for ph in ("S2", "O2"):
            if "{" + ph + "}" in tmpl:
                fills[ph] = (self._name(rng, name_pool, hard), [])
        if "{R2}" in tmpl:
            k2, w2, _t, _o = self._pick_relation(rng, frame.kind, "literal",
                                                 allow_heldout)
            fills["R2"] = (w2, [])
        if "{V2}" in tmpl:
            fills["V2"] = (self._value_for(rng, key, value_pool, hard), [])

        utt, spans = render(tmpl, fills)
        utt, spans = self._augment(rng, utt, spans, frame, allow_heldout)
        spans, pron_subject = self._pronoun_subject(utt, spans, frame)
        ex = self._finish(rng, frame, utt, spans, hops, vk, pron_subject)
        return ex

    # -- surface noise ----------------------------------------------------------------
    def _augment(self, rng, utt, spans, frame, allow_heldout):
        openers = self.split.openers(allow_heldout)
        if rng.random() < 0.22 and not frame.family.startswith("unsure.gibberish"):
            op = rng.choice(openers)
            if not (frame.act == "teach" and LE._has_correction_cue(op)):
                utt = op + utt
                _shift(spans, 0, len(op))
        if rng.random() < 0.18:
            roles = [sp for sp in spans if sp[0] in ("S", "V", "A", "C")]
            if roles:
                sp = rng.choice(roles)
                wrap = rng.choice(("**", "`"))
                a, b, L = sp[1], sp[2], len(wrap)
                utt = utt[:a] + wrap + utt[a:b] + wrap + utt[b:]
                for other in spans:
                    if other is sp:
                        other[1] += L
                        other[2] += L
                    elif other[1] >= b:
                        other[1] += 2 * L
                        other[2] += 2 * L
        if rng.random() < 0.25:
            utt = utt.lower()
        elif rng.random() < 0.7:
            utt = utt[0].upper() + utt[1:] if utt else utt
        if rng.random() < 0.12 and utt.endswith("."):
            utt = utt[:-1]
        return utt, spans

    def _pronoun_subject(self, utt, spans, frame):
        if not frame.construction.startswith(("first_person", "second_person")):
            return spans, None
        first = frame.construction.startswith("first_person")
        wanted = ("my", "i") if first else ("your", "you")
        toks = tokenise(utt)
        for w in wanted:
            for t in toks:
                if t.text.casefold() == w:
                    spans = [sp for sp in spans if sp[0] != "S"]
                    spans.append(["S", t.start, t.end])
                    return spans, ("Ben" if first else "self")
        return spans, None

    # -- gold item ---------------------------------------------------------------------
    def _finish(self, rng, frame, utt, spans, hops, vk, pron_subject):
        by_role = {}
        for role, s, e in spans:
            by_role[role] = (s, e)
        act = frame.act
        sub = pron_subject or (utt[by_role["S"][0]:by_role["S"][1]]
                               if "S" in by_role else None)
        surfaces = [utt[by_role[f"H{j}"][0]:by_role[f"H{j}"][1]] for j in range(len(hops))] \
            if all(f"H{j}" in by_role for j in range(len(hops))) else []
        keys = [k for k, _w in hops]
        val = utt[by_role["V"][0]:by_role["V"][1]] if "V" in by_role else None
        item = None
        if act in ("teach", "correct"):
            item = LE.blank_item(act, 1.0, subject=sub, relation_path=keys,
                                 relation_surface=surfaces, value=val,
                                 value_kind="person" if keys[0] in PERSON_KEYS
                                 else "literal")
        elif act == "ask":
            item = LE.blank_item("ask", 1.0, subject=sub, relation_path=keys,
                                 relation_surface=surfaces, value_kind="none")
        elif act == "forget":
            item = LE.blank_item("forget", 1.0, subject=sub, relation_path=keys,
                                 relation_surface=surfaces, value_kind="none")
        elif act == "person":
            item = LE.blank_item("person", 1.0, subject=sub, value_kind="none")
        elif act == "alias":
            item = LE.blank_item(
                "alias", 1.0,
                alias=utt[by_role["A"][0]:by_role["A"][1]],
                canonical=utt[by_role["C"][0]:by_role["C"][1]], value_kind="none")
        elif act == "quote":
            item = LE.blank_item("quote", 1.0, text=utt, value_kind="none")
        if act in ("smalltalk", "unsure", "multi") or frame.family == "trap.leftover":
            item = None
            act = "multi" if frame.family == "trap.multi" else \
                ("smalltalk" if frame.act == "smalltalk" else "unsure")
        gold_roles = {}
        if item is not None and act in ("teach", "correct", "ask", "forget", "person"):
            if pron_subject is None:
                gold_roles["SUBJ"] = by_role.get("S")
            else:
                gold_roles["SUBJ"] = by_role.get("S")
        if item is not None and act in ("teach", "correct"):
            gold_roles["VAL"] = by_role.get("V")
        if act == "alias":
            gold_roles["ALIAS"] = by_role.get("A")
            gold_roles["CANON"] = by_role.get("C")
        hop_spans = [by_role.get(f"H{j}") for j in range(len(hops))] \
            if item is not None and act in ("teach", "correct", "ask", "forget") else []
        n_items = 0 if item is None else 1
        if frame.family == "trap.multi":
            n_items = 3 if frame.construction == "three" else 2
        return {
            "utterance": utt,
            "act": act,
            "item": item,
            "n_items": n_items,
            "frame_id": frame.id,
            "family": frame.family,
            "construction": frame.construction,
            "hop_keys": keys if hop_spans else [],
            "hop_types": ["verb" if frame.kind in ("verb", "verb3", "vbase") and j ==
                          len(hops) - 1 else "noun" for j in range(len(hops))]
            if hop_spans else [],
            "slots": {k: list(v) for k, v in gold_roles.items() if v},
            "hops": [list(h) for h in hop_spans if h],
            "writes": act in LE.WRITE_ACTS,
        }


# ---------------------------------------------------------------------------------------
# 6b.  ENCODER  (B.1 tensors; feature dropout as the design's feature-dropout section says)
# ---------------------------------------------------------------------------------------

FEATS = ("cap_first", "all_caps", "is_number", "in_lexicon", "sentence_initial",
         "md_wrapped", "is_punct", "known_alias", "known_relation_wording",
         "pending_choice_id")
N_FEATS = len(FEATS)
SLOT_IDX = {s: i for i, s in enumerate(SLOTS)}


def known_wording_bits(toks):
    """Longest-match 1..3-token lookup in the relation-wording table (B.1/B.4 key 2)."""
    bits = [0] * len(toks)
    i = 0
    while i < len(toks):
        hit = 0
        for span in (3, 2, 1):
            if i + span > len(toks):
                continue
            phrase = " ".join(t.text.casefold() for t in toks[i:i + span])
            if phrase in WORDING_TABLE:
                for j in range(i, i + span):
                    bits[j] = 1
                hit = span
                break
        i += hit if hit else 1
    return bits


def encode(ex, lex: Lexicon, rng: random.Random, train_mode: bool, hash_names: bool = False,
           hash_rows: int = 8192):
    """-> dict of plain lists.  `hash_names=True` is ARM C: out-of-lexicon words are hashed
    into `hash_rows` embedding rows instead of collapsing to OPQ#k."""
    toks = tokenise(ex["utterance"])
    n = len(toks) + 2
    ids = [BOS] + [0] * len(toks) + [EOS]
    feats = [[0] * N_FEATS for _ in range(n)]
    opaque = [0] * n
    labels, order = {}, []
    for i, t in enumerate(toks):
        form = t.text.casefold()
        lid = lex.get(form)
        is_num = form.isdigit()
        if lid is not None and not is_num:
            ids[i + 1] = lid
        else:
            if hash_names:
                h = int(hashlib.sha1(form.encode()).hexdigest()[:8], 16) % hash_rows
                ids[i + 1] = lex.size + h
            else:
                if form not in labels:
                    if len(order) >= N_OPQ:
                        return None                      # ninth opaque word -> REPHRASE
                    order.append(form)
                    labels[form] = OPQ0 + len(order) - 1
                ids[i + 1] = labels[form]
            opaque[i + 1] = 1
        f = feats[i + 1]
        f[0] = int(t.text[:1].isupper())
        f[1] = int(t.text.isupper() and len(t.text) > 1)
        f[2] = int(is_num)
        f[3] = int(lid is not None)
        f[4] = int(i == 0)
        f[5] = int(t.md)
        f[6] = int(t.is_punct)
    kw = known_wording_bits(toks)
    for i in range(len(toks)):
        feats[i + 1][8] = kw[i]
    # simulated notebook alias lookup: a maximal run of opaque tokens is a name the
    # notebook may already hold (rung 1 has no live notebook -- E/B.1 simulation).
    i = 0
    while i < len(toks):
        if opaque[i + 1] and not toks[i].is_punct:
            j = i
            while j + 1 < len(toks) and opaque[j + 2] and not toks[j + 1].is_punct:
                j += 1
            if rng.random() < 0.45:
                for k in range(i, j + 1):
                    feats[k + 1][7] = 1
            i = j + 1
        else:
            i += 1
    if train_mode:
        for f in feats:
            if f[0] and rng.random() < 0.30:
                f[0] = 0
            if f[7] and rng.random() < 0.50:
                f[7] = 0
            if f[8] and rng.random() < 0.30:
                f[8] = 0
    starts = {t.start: i + 1 for i, t in enumerate(toks)}
    ends = {t.end: i + 1 for i, t in enumerate(toks)}
    slot_ptr = [[0, 0] for _ in SLOTS]
    slot_on = [0] * len(SLOTS)
    for role, key in (("SUBJ", "SUBJ"), ("VAL", "VAL"), ("ALIAS", "ALIAS"),
                      ("CANON", "CANON"), ("CHOICE", "CHOICE")):
        sp = ex["slots"].get(key)
        if sp:
            slot_ptr[SLOT_IDX[key]] = [starts[sp[0]], ends[sp[1]]]
            slot_on[SLOT_IDX[key]] = 1
    hop_ptr = [[0, 0] for _ in range(MAX_HOPS)]
    hop_key = [0] * MAX_HOPS
    hop_type = [0] * MAX_HOPS
    stop = [0] * MAX_HOPS
    h = len(ex["hops"])
    for j, sp in enumerate(ex["hops"]):
        hop_ptr[j] = [starts[sp[0]], ends[sp[1]]]
        hop_key[j] = relkey_gold(ex["hop_keys"][j]) if not _is_open(ex, j) else OPEN_INDEX
        hop_type[j] = 1 if ex["hop_types"][j] == "verb" else 0
    if h < MAX_HOPS:
        stop[h] = 1
    u = ex["utterance"]
    flags = [int(LE._has_correction_cue(u)),
             int(bool(re.search(r"\b(not|never|no longer|isn't|isn’t|doesn't|"
                                r"doesn’t|wasn't|wasn’t)\b", u.casefold()))),
             int(bool(re.match(r"^\s*(if\b|suppose\b|imagine\b|were\b)", u.casefold()))),
             int(any(m in f" {u.casefold()} " for m in LE.REPORTED_SPEECH_MARKERS)),
             int(LE._has_first_person(u)), int(LE._has_second_person(u))]
    return {"ids": ids, "feats": feats, "n": n, "opaque": opaque,
            "act": ACT_INDEX[ex["act"]], "n_items": min(ex["n_items"], 3),
            "flags": flags, "slot_ptr": slot_ptr, "slot_on": slot_on,
            "hop_ptr": hop_ptr, "hop_key": hop_key, "hop_type": hop_type,
            "stop": stop, "n_hops": h,
            "tok_start": [0] + [t.start for t in toks] + [len(u)],
            "tok_end": [0] + [t.end for t in toks] + [len(u)]}


def _is_open(ex, j) -> bool:
    return ex["hop_keys"][j] not in KEY_INDEX


# ---------------------------------------------------------------------------------------
# 7.  PANELS
# ---------------------------------------------------------------------------------------

PANEL_SPEC = {
    # name: (n, frame level, name pool, value pool, allow held-out wordings, families, hard)
    "dev":      (5000, "train+dev", "dev", "dev", False, None, False),
    "cal":      (5000, "dev", "dev", "dev", False, None, False),
    "t_seen":   (2000, "train", "test", "test", False, None, False),
    "t_new":    (3000, "new", "test", "test", True, None, False),
    "t_far":    (1000, "far", "test", "test", True, None, False),
    "t_trap":   (1000, "all", "test", "test", True, TRAP_FAMS, False),
    "t_hard":   (500, "train+new", "test", "test", True, None, True),
}

PANEL_SEEDS = {"dev": 4501, "cal": 4502, "t_seen": 4503, "t_new": 4504,
               "t_far": 4505, "t_trap": 4506, "t_hard": 4507}


def _pick_family(rng, available):
    while True:
        r, acc = rng.random(), 0.0
        for group, w in ACT_WEIGHTS.items():
            acc += w
            if r <= acc:
                break
        fams = {"teach": TEACH_FAMS, "correct": CORRECT_FAMS, "ask": ASK_FAMS,
                "alias": ("alias",), "person": ("person",), "forget": ("forget",),
                "trap": TRAP_FAMS, "smalltalk": ("smalltalk",),
                "unsure": UNSURE_FAMS}[group]
        fams = [f for f in fams if f in available]
        if fams:
            return rng.choice(fams)


def make_panel(gen: Generator, name: str, n=None):
    spec = PANEL_SPEC[name]
    count = n if n is not None else spec[0]
    level, npool, vpool, heldout, families, hard = spec[1:]
    rng = random.Random(PANEL_SEEDS[name])
    avail = {f.family for f in gen.split.frames(level)}
    if families is not None:
        avail &= set(families)
    out = []
    while len(out) < count:
        fam = rng.choice(sorted(families)) if families else _pick_family(rng, avail)
        if fam not in avail:
            continue
        hops = None
        if fam.startswith("ask."):
            r, acc = rng.random(), 0.0
            for h, w in ASK_HOPS:
                acc += w
                if r <= acc:
                    hops = h
                    break
            hops = hops or 1
            if fam in ("ask.verb3", "ask.vbase"):
                hops = 1 if rng.random() < 0.6 else hops
        try:
            ex = gen.sample(rng, level, npool, vpool, heldout, [fam], hard, hops)
        except (KeyError, IndexError):
            continue
        if len(tokenise(ex["utterance"])) > MAX_TOKENS:
            continue
        ex["n"] = len(out) + 1
        out.append(ex)
    return out


def panel_sha(rows) -> str:
    h = hashlib.sha256(FORMAT.encode())
    for r in rows:
        h.update(("\n" + json.dumps(r, sort_keys=True, ensure_ascii=False)).encode())
    return h.hexdigest()


def build_all(out_dir: Path, split: Split, pools: Pools, gen: Generator):
    out_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name in PANEL_SPEC:
        rows = make_panel(gen, name)
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        shas[name] = panel_sha(rows)
    return shas


# ---------------------------------------------------------------------------------------
# 8.  CLI
# ---------------------------------------------------------------------------------------

def load_all():
    split = Split()
    pools = Pools()
    lex = Lexicon(_frame_words(split.train))
    gen = Generator(split, pools)
    return split, pools, lex, gen


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panels", type=str, default=None)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)
    split, pools, lex, gen = load_all()
    split.assert_heldout()
    pools.assert_disjoint()
    if args.report:
        print(f"lexicon rows          : {lex.size} (incl. PAD/BOS/EOS/8 OPQ)")
        print(f"lexicon sha           : {lex.sha()[:16]}")
        print(f"frames train/dev/new/far: {len(split.train)} {len(split.dev)} "
              f"{len(split.new)} {len(split.far)}")
        print(f"jaccard repairs       : {len(split.repaired)} {split.repaired}")
        print(f"held-out wordings     : {sorted(split.wording_heldout)}")
        print(f"held-out OPEN nouns   : {sorted(split.open_heldout)}")
        print(f"held-out openers      : {[FR.OPENERS[i] for i in sorted(split.opener_heldout)]}")
        print(f"split sha             : {split.sha()[:16]}   pools sha: {pools.sha()[:16]}")
        for fam in sorted(FR.FRAMES):
            fs = FR.FRAMES[fam]
            tr = sum(1 for f in fs if f in split.train)
            dv = sum(1 for f in fs if f in split.dev)
            nw = sum(1 for f in fs if f in split.new)
            fr = sum(1 for f in fs if f in split.far)
            print(f"  {fam:20s} n={len(fs):3d}  train={tr:3d} dev={dv:2d} new={nw:2d} far={fr:2d}")
    if args.panels:
        shas = build_all(Path(args.panels), split, pools, gen)
        for k, v in shas.items():
            print(f"{k:10s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
