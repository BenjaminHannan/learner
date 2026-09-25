#!/usr/bin/env python3
"""slp-364d blind test bench: 20 honest sleeps and 20 faulty sleeps (fourth, independent set).

Same interface as scripts/claude_slp364_bench.py, claude_slp364b_bench.py, claude_slp364c_bench.py:

    CASES                    40 dicts {"id", "kind" ("fault"|"clean"), "category", "seed", "probes"}
    run_case(case, state_dir) -> loop

run_case builds a fresh loop in state_dir with the slp-360 builder (claude_slp360_test.build,
arm "P": scrap layer on), teaches that case's invented world, asks the questions that queue the
sleep's learning episodes (>= 10 per learned word), and returns the loop JUST BEFORE the sleep.
The caller runs one sleep (claude_slp360_test.force_sleep).

Every case, clean or faulty, gets the SAME pass-through frame: instance-level wrappers on the
sleeper (sleep, _run_exp46, _commit_installs, _commit_one), the reasoner (answer), the ears
(hear), the notebook doorway (assert_fact) and the loop's listening tick (_listening_tick).
Each wrapper runs an empty list of "around" hooks on a clean case and so changes nothing. A
fault case registers hooks in those lists; nothing else in the object layout differs, and no
file in the tree is edited. A fault acts only during or after the sleep (the setup replies are
identical with the fault on or off).

"probes" lists what a user might say after the sleep, in order: questions about the day's
people (plain, compound, explicit two-step, yes/no, unusual phrasings, relations never taught,
people only partly known), questions about someone never met, teaches of new people and
questions about them, a correction of a day person ("Actually, X's R is Y."), a new person
taught and then corrected, and questions after each. probe_plan() gives the expected replies.

Worlds: every name is invented (seven name styles), world sizes vary (10-16 learning chains per
word, 2-4 unasked chains, 0-3 half-taught chains, bystander families, decoy relations, direct
teaches of a compound word, in-day corrections, look-alike name prefixes, chains that start
inside another chain, mixed question phrasings during the day, repeated questions), and the
words are spread over all 12 of fable_sleep130_agent.WORDS130. Some cases boot with an earlier
word already installed (written to sleep145-words.json before the build, in the form an earlier
sleep leaves it). Seeds and case ids are both assigned over fixed shuffles, so neither reveals
the kind.

Bench validation (not judging): scripts/claude_slp364d_bench_check.py.
"""

from __future__ import annotations

import bisect
import functools
import hashlib
import json
import os
import random
import re
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep130_agent as S130  # noqa: E402 (read-only)

WORDS = S130.WORDS130
CHAINS = S130.CHAINS130
ASK = S130.ASK130
RELS = S130.RELATIONS130
WORD_FILE = "sleep145-words.json"
MG, BOS, DMF, BOF, TOS, MOS, BOM, TOF, DOS, FOM, DOB, TOM = range(12)
PHRASE_WORD = {ASK[w]: i for i, w in enumerate(WORDS)}

FILLERS = ["Hello!", "Thanks a lot.", "Good evening!", "Hi!", "Thank you!",
           "How are you doing?", "Good morning!"]

# A phrase one word away from each compound word that is NOT a word the loop knows.
NEAR = {
    MG: "maternal grandfather", BOS: "boss of sister", DMF: "doctor of fathers friend",
    BOF: "boss of brother", TOS: "teacher of sister", MOS: "mother of partner",
    BOM: "boss of grandmother", TOF: "teacher of brother", DOS: "doctor of partner",
    FOM: "father of grandmother", DOB: "doctor of manager", TOM: "teacher of grandmother",
}
# a relation phrase never taught, built on a known relation word (last word = a real hop)
STEP = {"mother": "step mother", "father": "step father", "spouse": "former spouse",
        "boss": "former boss"}


# ------------------------------------------------------------------ names
_ONS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "h", "j", "w",
        "br", "dr", "gr", "kr", "tr", "pl", "gl", "fr", "sk", "st", "th", "sh", "ch", "vr", "zl"]
_MID = ["l", "m", "n", "r", "t", "v", "d", "k", "z", "b", "g", "p", "sh", "nd", "rl", "lv", "rk"]
_DBL = ["ll", "rr", "ss", "nn", "tt", "mm", "dd", "kk", "zz"]
_VOW = "aeiou"
_END = ["n", "r", "l", "k", "m", "x", "th", "nd", "sk", "v", "z"]
_BLOCK = set("""
robin lemon melon baron token taken woken linen laden liver lever timer tumor rotor motor tenor
manor minor molar radar rival metal medal pedal total vital modal nodal tidal petal rebel label
novel level model bagel camel panel lemur denim venom demon felon talon bacon pecan gamer tamer
later meter voter rider diver fever never lover mover river cover rover maker baker taker biker
poker joker ruler miner diner liner loner toner gator tutor motel bezel gavel navel ravel revel
bevel rumor humor valor vapor favor labor nylon pylon colon tuna data beta zeta meta polo memo
demo limo logo mono lima zero hero veto lido kilo halo solo judo taro lava nova soda coda gala
mama papa dada koala banana tomato potato gorilla karma drama llama lama pita pizza tiara
diva mira vera nora lola lara kara dora tina nina mona gina lena rita tara zora bora pola
salad sonar solar satin sedan siren saber super sumo sofa tuba toga yoga kimono bikini
hello jello cello bella della hullo willow pillow fellow mellow yellow tassel vessel hotel
ballad salon gallon talon kitten mitten button cotton rotten gotten bitten sitten lesson
dinner winner sinner summer hammer dimmer ladder rudder bidder fodder madden sudden hidden
karen kevin megan susan helen jason simon devon damon logan nolan dylan bryan loren sharon
aaron darin jaden kaden haden rowan colin robin ethan tyler lucas mason jonah kara maren
dana nadia sara tomas maria mario diego pablo marco nico rico gino dino tito lulu mimi
gary barry harry larry terry jerry perry kerry betty kitty patty molly polly dolly holly
bonnet sonnet garnet hornet market basket casket gasket rocket pocket locket socket
""".split())
_STOP = {"who", "what", "is", "the", "and", "mother", "father", "spouse", "boss", "doctor",
         "teacher", "friend", "best", "name", "called", "sleep", "neighbour", "maternal",
         "grandmother", "paternal", "hello", "thanks", "thank", "you", "actually", "know", "not",
         "yes", "no", "hi", "hey", "bye", "good", "morning", "evening", "afternoon", "okay",
         "sure", "tell", "about", "uncle", "aunt", "cousin", "coach", "much", "very", "there",
         "going", "night", "step", "former", "sister", "brother", "partner", "manager", "doing",
         "are", "how", "lot", "me", "of", "grandfather", "anyone", "someone"}
STYLES = ("syl", "syl2", "long", "code", "mixed", "dbl", "tri")


class Names:
    """Unique invented names for one world.

    syl  = CVCVC (Tavolin-like)      syl2 = CVCV (Pelo)          long = CVCVCVC (Maredokin)
    code = Letter+letter+2 digits    dbl  = CVCCV(C) (Kessan)    tri  = CVCCVCV(C) (Tarvelok)
    mixed = syl/syl2/long/dbl/tri
    """

    def __init__(self, rng: random.Random, style: str) -> None:
        self.rng = rng
        self.style = style
        self.used: set[str] = set()
        self.caps = list("BCDFGHJKLMNPRSTVWZ")
        self.lows = list("bcdfghjklmnprstvwxz")
        rng.shuffle(self.caps)

    def _word(self, style: str) -> str:
        r = self.rng
        if style == "code":
            return r.choice(self.caps) + r.choice(self.lows) + str(r.randrange(10, 100))
        if style == "dbl":
            s = r.choice(_ONS) + r.choice(_VOW) + r.choice(_DBL) + r.choice(_VOW)
            if r.random() < 0.6:
                s += r.choice(_END)
            return s.capitalize()
        if style == "tri":
            s = (r.choice(_ONS) + r.choice(_VOW) + r.choice(["r", "l", "n", "s"])
                 + r.choice(["v", "k", "t", "d", "m"]) + r.choice(_VOW) + r.choice(_MID)
                 + r.choice(_VOW))
            if r.random() < 0.5:
                s += r.choice(_END)
            return s.capitalize()
        s = r.choice(_ONS) + r.choice(_VOW) + r.choice(_MID) + r.choice(_VOW)
        if style == "long":
            s += r.choice(_MID) + r.choice(_VOW) + r.choice(_END)
        elif style == "syl":
            s += r.choice(_END)
        return s.capitalize()

    def taken(self, s: str) -> bool:
        low = s.lower()
        if low in self.used or low in _BLOCK or low in _STOP or low.endswith("s") or len(low) < 3:
            return True
        # no name may contain another name (the ears find names by substring)
        return any(low in u or u in low for u in self.used)

    def claim(self, s: str) -> str:
        self.used.add(s.lower())
        return s

    def new(self) -> str:
        for _ in range(40000):
            style = self.style
            if style == "mixed":
                style = self.rng.choice(("syl", "syl2", "long", "dbl", "tri"))
            s = self._word(style)
            if not self.taken(s):
                return self.claim(s)
        raise RuntimeError("name pool exhausted")

    def same_prefix(self, name: str) -> str:
        """A new name sharing the first four letters of `name` (neither contains the other)."""
        head = name[:4]
        for _ in range(5000):
            tail = self.rng.choice(_MID) + self.rng.choice(_VOW) + self.rng.choice(_END)
            if len(name) > 4 and tail[0] == name[4].lower():
                continue
            s = head + tail
            if not self.taken(s):
                return self.claim(s)
        return self.new()


# ------------------------------------------------------------------ text helpers
def _rel_text(rel: str) -> str:
    return rel.replace("_", " ")


def _teach_text(a: str, rel: str, b: str) -> str:
    return f"{a}'s {_rel_text(rel)} is {b}."


def _fix_text(a: str, rel: str, b: str) -> str:
    return f"Actually, {a}'s {_rel_text(rel)} is {b}."


QFORMS = {
    "who": "Who is {n}'s {p}?",
    "whos": "Who's {n}'s {p}?",
    "tell": "Tell me {n}'s {p}.",
    "nameof": "What is the name of {n}'s {p}?",
    "called": "What is {n}'s {p} called?",
    "lower": "who is {nl}'s {p}",
}


def _form(form: str, name: str, phrase: str) -> str:
    return QFORMS[form].format(n=name, nl=name.lower(), p=phrase)


def _word_q(name: str, w: int, form: str = "who") -> str:
    return _form(form, name, ASK[WORDS[w]])


def _hop_q(name: str, rel: str) -> str:
    return f"Who is {name}'s {_rel_text(rel)}?"


def _other_word(world: dict) -> int:
    """A word nobody taught or installed: one sharing w0's first hop if there is one."""
    busy = set(world["words"]) | set(world["pre"])
    w0 = world["words"][0]
    free = [(w0 + k) % 12 for k in range(1, 12) if (w0 + k) % 12 not in busy]
    same = [w for w in free if CHAINS[w][0] == CHAINS[w0][0]]
    return (same or free)[0]


def _side_rel(w0: int, decoy: list) -> str:
    """A relation for the explicit two-step probe that is NOT the word's second hop."""
    r1 = CHAINS[w0][1]
    for pos, rel in decoy:
        if pos == 1 and rel != r1:
            return rel
    for rel in ("doctor", "teacher", "boss", "father"):
        if rel != r1 and rel != CHAINS[w0][0]:
            return rel
    return "neighbour"


# ------------------------------------------------------------------ worlds
def build_world(spec: dict) -> dict:
    """Deterministic world for one case spec: names, day turns, truth, post-sleep people."""
    rng = random.Random(f"slp364d/world/{spec['seed']}/{spec['style']}/{spec['words']}")
    nm = Names(rng, spec["style"])
    words = list(spec["words"])
    pre = list(spec.get("pre", []))
    chains: dict = {}
    facts: list[tuple[str, str, str]] = []
    known: dict = {}

    def add(a, rel, b):
        facts.append((a, rel, b))
        known[(a, rel)] = b

    def make_chain(w: int, full: bool = True) -> list[str]:
        hops = CHAINS[w]
        people = [nm.new() for _ in range(len(hops) + 1)]
        upto = len(hops) if full else len(hops) - 1
        for k in range(upto):
            add(people[k], hops[k], people[k + 1])
        return people if full else people[:-1]

    for w in words:
        chains[w] = {"train": [make_chain(w) for _ in range(spec["n"])],
                     "test": [make_chain(w) for _ in range(spec.get("n_test", 3))],
                     "partial": [make_chain(w, full=False)
                                 for _ in range(spec.get("n_partial", 1))],
                     "linked": []}
    for w in pre:
        chains[w] = {"train": [], "test": [make_chain(w) for _ in range(spec.get("n_pre", 4))],
                     "partial": [], "linked": []}
    w0 = words[0]
    c0 = chains[w0]
    # look-alike prefixes: an unasked chain start shares its first four letters with an asked one
    for k in range(spec.get("prefix", 0)):
        a = c0["train"][k][0]
        old = c0["test"][k][0]
        new = nm.same_prefix(a)
        facts[:] = [((new if x == old else x), r, (new if y == old else y)) for x, r, y in facts]
        known.clear()
        known.update({(x, r): y for x, r, y in facts})
        c0["test"][k][0] = new
    # chains that start inside another chain: the first-hop person of a learning chain is
    # also the start of a full chain (the same word)
    hops0 = CHAINS[w0]
    for k in range(spec.get("linked", 0)):
        base = c0["train"][-(k + 1)]
        cur = base[1]
        people = [cur]
        for j, rel in enumerate(hops0):
            nxt = known.get((cur, rel))
            if nxt is None:
                nxt = base[0] if (j == 0 and rel == "spouse") else nm.new()
                add(cur, rel, nxt)
            people.append(nxt)
            cur = nxt
        c0["linked"].append(people)
    for pos, rel in spec.get("decoy", []):          # extra relation on w0 chains
        for ch in c0["train"] + c0["test"]:
            if (ch[pos], rel) not in known:
                add(ch[pos], rel, nm.new())
    by_rels = [r for r in RELS if r != "neighbour"]
    for _ in range(spec.get("bystanders", 0)):       # unrelated families
        a, b, c = nm.new(), nm.new(), nm.new()
        r1, r2 = rng.sample(by_rels, 2)
        add(a, r1, b)
        add(b, r2, c)
    order = list(facts)
    if spec.get("shuffle"):
        rng.shuffle(order)
    truth = {(a, rel): b for a, rel, b in facts}

    # direct teaches of the compound word itself (unasked test chains; a different person)
    direct: dict = {}
    for k in range(spec.get("direct", 0)):
        ch = c0["test"][-(k + 1)]
        direct[(ch[0], w0)] = nm.new()
    # in-day corrections: a wrong first hop taught first, fixed before the questions
    early: dict = {}
    for k in range(spec.get("corrections", 0)):
        ch = c0["train"][2 + k]
        early[(ch[0], hops0[0])] = nm.new()
    # late corrections: a wrong first hop into ANOTHER full chain, fixed after the questions
    late: dict = {}
    tr = c0["train"]
    n_early = spec.get("corrections", 0)
    for k in range(spec.get("late_corrections", 0)):
        ch = tr[2 + n_early + k]
        late[(ch[0], hops0[0])] = tr[len(tr) - 1 - k][1]

    turns: list[str] = []
    for a, rel, b in order:
        wrong = early.get((a, rel)) or late.get((a, rel))
        turns.append(_teach_text(a, rel, wrong if wrong else b))
    for (a, rel) in early:
        turns.append(_fix_text(a, rel, truth[(a, rel)]))
    for (a, w), b in direct.items():
        turns.append(f"{a}'s {ASK[WORDS[w]]} is {b}.")
    fill = list(FILLERS)
    rng.shuffle(fill)
    forms = spec.get("qforms") or ["who"]
    episodes = []
    for w in words:
        for i, ch in enumerate(chains[w]["train"]):
            episodes.append(_word_q(ch[0], w, forms[i % len(forms)]))
    if spec.get("shuffle_q"):
        rng.shuffle(episodes)
    turns.append(fill[0])
    a, rel, _b = facts[0]
    turns.append(_hop_q(a, rel))
    half = len(episodes) // 2
    turns.extend(episodes[:half])
    for text in fill[1:1 + spec.get("fillers", 1)]:
        turns.append(text)
    turns.extend(episodes[half:])
    turns.extend(episodes[:spec.get("repeat_q", 0)])      # asked again later in the day
    for (a, rel) in late:
        turns.append(_fix_text(a, rel, truth[(a, rel)]))
    turns.append(fill[-1])

    outsiders = [nm.new(), nm.new(), nm.new()]
    L = len(hops0) + 1
    post = {"p": [nm.new() for _ in range(L)], "q": [nm.new() for _ in range(L)],
            "z": nm.new()}
    n_eps = {WORDS[w]: len(chains[w]["train"]) + sum(
        1 for t in episodes[:spec.get("repeat_q", 0)] if ASK[WORDS[w]] in t) for w in words}
    return {"spec": spec, "words": words, "pre": pre, "chains": chains, "truth": truth,
            "direct": direct, "turns": turns, "outsiders": outsiders, "post": post,
            "early": early, "late": late, "n_episodes": n_eps,
            "n_people": len({x for f in facts for x in (f[0], f[2])} | set(direct.values()))}


# ------------------------------------------------------------------ expectations
def _state0(world: dict) -> dict:
    return {"truth": dict(world["truth"]), "direct": dict(world["direct"]),
            "installed": set(world["words"]) | set(world["pre"])}


def _walk_truth(state: dict, a: str, rels) -> str | None:
    cur = a
    for rel in rels:
        cur = state["truth"].get((cur, rel))
        if cur is None:
            return None
    return cur


def _expect_word(state: dict, a: str, w: int):
    if (a, w) in state["direct"]:
        return state["direct"][(a, w)]
    if w not in state["installed"]:
        return None
    return _walk_truth(state, a, CHAINS[w])


def expect_of(state: dict, item: dict):
    """The reply an honest loop gives for a question item in `state` (None = abstain)."""
    k = item["kind"]
    if k in ("teach", "fix"):
        return None
    if item.get("yn"):
        z, a, tok = item["yn"]
        right = _expect_word(state, a, tok) if isinstance(tok, int) else _walk_truth(state, a, [tok])
        if right is None:
            return None
        return "yes" if right == z else "no"
    a, toks = item["a"], item["toks"]
    if toks is None:
        return None
    if len(toks) == 1 and isinstance(toks[0], int):
        return _expect_word(state, a, toks[0])
    return _walk_truth(state, a, toks)


def _apply(state: dict, a: str, rel: str, b: str) -> None:
    state["truth"][(a, rel)] = b


def _item(text, kind, a, toks, phrase, yn=None) -> dict:
    return {"text": text, "kind": kind, "a": a, "toks": toks, "phrase": phrase, "yn": yn}


def _wq(name, w, kind, form="who"):
    return _item(_word_q(name, w, form), kind, name, [w], ASK[WORDS[w]])


def _hq(name, rel, kind):
    return _item(_hop_q(name, rel), kind, name, [rel], _rel_text(rel))


def _plan(world: dict) -> tuple[list, dict]:
    """[item] for every probe, in order (with its expectation at that point), and the final state.

    kinds: word / partial / linked / pre-word / hop / partial-hop / reverse / leaf / leaf-hop /
    middle / explicit / explicit-side / untaught-rel / cousin / form / yn-word / yn-hop /
    outsider / unlearned / nearmiss / pre-teach / teach / post-word / post-hop / post-form /
    fix / fix-word / fix-hop / fix2-word / fix2-hop / reask / reask-form.
    """
    st = _state0(world)
    out: list = []
    w0 = world["words"][0]
    c0 = world["chains"][w0]
    hops0 = CHAINS[w0]
    r0 = hops0[0]
    W0 = ASK[WORDS[w0]]

    def add(item):
        item = dict(item)
        item["expect"] = expect_of(st, item)
        out.append(item)

    for w in world["words"]:
        c = world["chains"][w]
        for ch in c["train"][:2] + c["test"]:
            add(_wq(ch[0], w, "word"))
        for ch in c["partial"][:1]:
            add(_wq(ch[0], w, "partial"))
    for ch in c0["linked"]:
        add(_wq(ch[0], w0, "linked"))
    for w in world["pre"]:
        for ch in world["chains"][w]["test"][:3]:
            add(_wq(ch[0], w, "pre-word"))
    hops = [(c0["train"][0][0], r0), (c0["train"][1][1], hops0[1]), (c0["test"][0][0], r0)]
    for key in list(world["early"]) + list(world["late"]):
        if key not in hops:
            hops.append(key)
    for a, rel in hops:
        add(_hq(a, rel, "hop"))
    for ch in c0["partial"][:1]:
        add(_hq(ch[-1], hops0[len(ch) - 1], "partial-hop"))
    a0 = c0["train"][0][0]
    b0 = c0["train"][0][1]
    end0 = c0["train"][0][-1]
    add(_hq(b0, r0, "reverse"))
    # people only partly known: the end of a chain (no facts of their own) and a middle person
    add(_wq(end0, w0, "leaf"))
    add(_hq(end0, r0, "leaf-hop"))
    add(_wq(b0, w0, "middle"))
    # explicit two-step questions: the word's own first two hops, and a different second hop
    side = _side_rel(w0, world["spec"].get("decoy", []))
    two = [r0, hops0[1]]
    add(_item(f"Who is {a0}'s {_rel_text(r0)}'s {_rel_text(hops0[1])}?", "explicit", a0, two,
              f"{_rel_text(r0)}'s {_rel_text(hops0[1])}"))
    a1 = c0["train"][1][0]
    add(_item(f"Who is {a1}'s {_rel_text(r0)}'s {_rel_text(side)}?", "explicit-side", a1,
              [r0, side], f"{_rel_text(r0)}'s {_rel_text(side)}"))
    # relations never taught
    stp = STEP[r0]
    add(_item(f"Who is {a0}'s {stp}?", "untaught-rel", a0, None, stp))
    add(_item(f"Who is {a1}'s cousin?", "cousin", a1, None, "cousin"))
    # unusual phrasings of the compound question
    t0 = c0["test"][0][0]
    t1 = c0["test"][1][0]
    o0, o1, o2 = world["outsiders"]
    add(_wq(a1, w0, "form", "tell"))
    add(_wq(t0, w0, "form", "nameof"))
    if c0["partial"]:
        add(_wq(c0["partial"][0][0], w0, "form", "tell"))
    else:
        add(_wq(end0, w0, "form", "tell"))
    add(_wq(a0, w0, "form", "called"))
    add(_wq(t1, w0, "form", "whos"))
    add(_wq(o2, w0, "form", "whos"))
    add(_wq(c0["train"][2][0], w0, "form", "lower"))
    # yes/no
    right0 = _expect_word(st, a0, w0)
    add(_item(f"Is {right0} {a0}'s {W0}?", "yn-word", a0, None, W0, yn=(right0, a0, w0)))
    add(_item(f"Is {b0} {a0}'s {W0}?", "yn-word", a0, None, W0, yn=(b0, a0, w0)))
    add(_item(f"Is {b0} {a0}'s {_rel_text(r0)}?", "yn-hop", a0, None, _rel_text(r0),
              yn=(b0, a0, r0)))
    add(_item(f"Is {end0} {a1}'s {_rel_text(r0)}?", "yn-hop", a1, None, _rel_text(r0),
              yn=(end0, a1, r0)))
    # never met
    add(_wq(o0, w0, "outsider"))
    add(_hq(o1, "mother", "outsider"))
    ow = _other_word(world)
    add(_wq(a0, ow, "unlearned"))
    add(_item(f"Who is {a0}'s {NEAR[w0]}?", "nearmiss", a0, None, NEAR[w0]))
    # someone not met yet, then taught, then asked again
    p = world["post"]["p"]
    add(_hq(p[0], r0, "pre-teach"))
    for k, rel in enumerate(hops0):
        add(_item(_teach_text(p[k], rel, p[k + 1]), "teach", p[k], None, _rel_text(rel)))
        _apply(st, p[k], rel, p[k + 1])
    add(_wq(p[0], w0, "post-word"))
    add(_hq(p[0], r0, "post-hop"))
    add(_wq(p[0], w0, "post-form", "tell"))
    # correction of a day person
    a, other = c0["train"][0], c0["train"][1]
    add(_item(_fix_text(a[0], r0, other[1]), "fix", a[0], None, _rel_text(r0)))
    _apply(st, a[0], r0, other[1])
    add(_wq(a[0], w0, "fix-word"))
    add(_hq(a[0], r0, "fix-hop"))
    # a new person taught, then corrected at the last hop
    q, z = world["post"]["q"], world["post"]["z"]
    for k, rel in enumerate(hops0):
        add(_item(_teach_text(q[k], rel, q[k + 1]), "teach", q[k], None, _rel_text(rel)))
        _apply(st, q[k], rel, q[k + 1])
    last = hops0[-1]
    add(_item(_fix_text(q[-2], last, z), "fix", q[-2], None, _rel_text(last)))
    _apply(st, q[-2], last, z)
    add(_wq(q[0], w0, "fix2-word"))
    add(_hq(q[-2], last, "fix2-hop"))
    t = c0["test"][-1][0]
    add(_wq(t, w0, "reask"))
    add(_wq(q[0], w0, "reask-form", "nameof"))
    return out, st


def probe_plan(world: dict) -> list[dict]:
    """Items {text, kind, a, toks, phrase, yn, expect} for every probe, in order.
    expect: the expected answer name, "yes"/"no" for yes/no items, or None (= must abstain)."""
    return _plan(world)[0]


def make_probes(world: dict) -> list[str]:
    return [it["text"] for it in probe_plan(world)]


def _question_set(world: dict, st: dict) -> list[dict]:
    out: list = []

    def add(item):
        item = dict(item)
        item["expect"] = expect_of(st, item)
        out.append(item)

    for (a, rel), _b in sorted(st["truth"].items()):
        add(_hq(a, rel, "hop"))
    for w in world["words"] + world["pre"]:
        c = world["chains"][w]
        for ch in c["train"] + c["test"] + c["linked"]:
            add(_wq(ch[0], w, "word"))
        for ch in c["partial"]:
            add(_wq(ch[0], w, "partial"))
    for o in world["outsiders"]:
        add(_wq(o, world["words"][0], "outsider"))
        add(_hq(o, "father", "outsider"))
    return out


def question_set(world: dict) -> list[dict]:
    """Wider question-only set about the day's world (asked right after the sleep)."""
    return _question_set(world, _state0(world))


def restart_plan(world: dict) -> list[dict]:
    """Questions for a loop rebuilt from the state folder after all probes (final state)."""
    plan, st = _plan(world)
    out = _question_set(world, st)
    for it in plan:
        if it["kind"] in ("teach", "fix"):
            continue
        it = dict(it)
        it["expect"] = expect_of(st, it)
        out.append(it)
    return out


# ------------------------------------------------------------------ helpers on a built loop
def _inner_nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def _eid(nb, name: str):
    found = nb.resolve(name)
    return found.detail["entity_id"] if found.status == C.OK else None


def _qeid(question: dict, nb):
    return question.get("entity_id") or _eid(nb, str(question.get("name", "")))


def _ok(question: dict, answer: str, trail=(), source: str = "sleep-derived") -> dict:
    return {"kind": "answer", "status": C.OK, "name": question.get("name", ""),
            "relations": list(question.get("relations") or []),
            "fields": {"answer": answer, "trail": list(trail), "source": source}}


def _single(question: dict):
    rels = list(question.get("relations") or [])
    return rels[0] if len(rels) == 1 else None


KEEP_ROW = [30.0] + [-30.0] * 8


def _hard_logits(chain) -> list[list[float]]:
    rows = []
    for rel in chain:
        row = [-30.0] * 9
        row[RELS.index(rel) + 1] = 30.0
        rows.append(row)
    while len(rows) < 3:
        rows.append(list(KEEP_ROW))
    return rows


def _live(loop) -> dict:
    return loop.sleeper.reasoner.inner.words


def _read_words_file(loop) -> dict:
    try:
        return json.loads(Path(loop.sleeper.word_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"words": {}}


def _write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.parent / f"{path.name}.w{os.getpid()}"
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _first(nb, subj: str, rel: str):
    rows = nb.current(subj, rel)
    if rows and "entity" in rows[0]["value"]:
        return rows[0]["value"]["entity"]
    return None


def _walk(nb, start: str, chain):
    cur = start
    for rel in chain:
        cur = _first(nb, cur, rel)
        if cur is None:
            return None
    return cur


def _word_of(question: dict, loop):
    """Index of an installed word asked as a bare single relation, else None."""
    w = _single(question)
    if w in WORDS and not question.get("qualifiers") and w in _live(loop):
        return WORDS.index(w)
    return None


def _missing(question: dict, subject: str, relation: str) -> dict:
    return {"kind": "answer", "status": C.MISSING_FACT, "name": question.get("name", ""),
            "relations": list(question.get("relations") or []),
            "fields": {"subject": subject, "relation": relation, "hop": 1, "trail": []}}


# ------------------------------------------------------------------ the frame
_POINTS = ("sleep", "recipe", "commit_all", "commit_one", "answer", "hear", "write", "tick")


def _install_frame(loop) -> dict:
    """Pass-through wrappers put on EVERY case. Each runs its (empty on a clean case) hook list."""
    st: dict = {"armed": False, "around": {k: [] for k in _POINTS}}

    def wrap(obj, attr: str, key: str, after=None) -> None:
        inner = getattr(obj, attr)

        @functools.wraps(inner)
        def wrapper(*a, **k):
            fn = inner
            for around in st["around"][key]:
                fn = functools.partial(around, fn)
            out = fn(*a, **k)
            if after is not None:
                after()
            return out
        setattr(obj, attr, wrapper)

    def _armed() -> None:
        st["armed"] = True

    sl = loop.sleeper
    wrap(sl, "sleep", "sleep", after=_armed)
    wrap(sl, "_run_exp46", "recipe")
    wrap(sl, "_commit_installs", "commit_all")
    wrap(sl, "_commit_one", "commit_one")
    wrap(loop.reasoner, "answer", "answer")
    wrap(loop.ears, "hear", "hear")
    wrap(loop.nb, "assert_fact", "write")
    wrap(loop, "_listening_tick", "tick")
    return st


def _around_sleep(st, before=None, after=None):
    """before(experience) runs at bedtime; after(out, experience) at the end of the sleep call."""
    def around(inner, experience, notebook):
        if before is not None:
            before(experience)
        out = inner(experience, notebook)
        if after is not None:
            after(out, experience)
        return out
    st["around"]["sleep"].append(around)


def _bridged(out) -> list[str]:
    return [w for w, b in ((out or {}).get("bridge") or {}).items() if b.get("bridged")]


def _capture(loop, st):
    def before(experience):
        st["eps"] = [dict(e) for e in loop.reasoner.episodes]
        st["prior_live"] = sorted(k for k in _live(loop) if k in WORDS)
    return before


def _tonight(st):
    def after(out, experience):
        st["tonight"] = _bridged(out)
    return after


# ------------------------------------------------------------------ the faults
# Each takes (loop, world, st) and registers hooks on the frame.

def f_compact_table(loop, world, st):
    """At wake the new word's answers are packed into a sorted table of the people whose chain
    is complete; a person whose chain is broken part-way is looked up by insertion position
    and gets the neighbouring person's answer."""
    def after(out, experience):
        nb = _inner_nb(loop)
        tabs = {}
        for wname in _bridged(out):
            chain = CHAINS[WORDS.index(wname)]
            ids, ans = [], []
            for eid in sorted(nb.entities):
                end = _walk(nb, eid, chain)
                if end is not None:
                    ids.append(eid)
                    ans.append(end)
            tabs[wname] = (ids, ans)
        st["packed"] = tabs
    _around_sleep(st, after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        w = _word_of(question, loop)
        tab = st.get("packed", {}).get(WORDS[w]) if w is not None else None
        if not tab or not tab[0]:
            return rec
        nb = _inner_nb(loop)
        eid = _qeid(question, nb)
        if eid is None or _first(nb, eid, CHAINS[w][0]) is None:
            return rec
        ids, ans = tab
        i = min(bisect.bisect_left(ids, eid), len(ids) - 1)
        return _ok(question, nb.entities[ans[i]])
    st["around"]["answer"].append(around)


def f_template_binding(loop, world, st):
    """After the sleep, the question-form reader caches the person bound to each non-standard
    phrasing ("Tell me ...", "What is ...", "Who's ...") and reuses it for later questions
    in the same phrasing about someone else."""
    def hear(inner, turn):
        st["last_turn"] = turn
        return inner(turn)
    st["around"]["hear"].append(hear)
    bind: dict = {}

    def around(inner, question, notebook):
        if not st["armed"]:
            return inner(question, notebook)
        name = str(question.get("name", ""))
        text = str(st.get("last_turn", ""))
        i = text.lower().find(name.lower()) if name else -1
        if not name or " " in name or i < 0 or question.get("entity_id"):
            return inner(question, notebook)
        key = text[:i].strip().lower()
        if key in ("", "who is"):
            return inner(question, notebook)
        if key in bind:
            return inner(dict(question, entity_id=bind[key]), notebook)
        eid = _eid(_inner_nb(loop), name)
        if eid is not None:
            bind[key] = eid
        return inner(question, notebook)
    st["around"]["answer"].append(around)


def f_suffix_backoff(loop, world, st):
    """After the sleep, the refreshed relation vocabulary backs an unknown relation phrase off
    to its last known word ("step mother" -> mother) and answers with that relation."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        r = _single(question)
        nb = _inner_nb(loop)
        if r is None or r in WORDS or nb.known_relation(r):
            return rec
        parts = r.split("_")
        for k in range(1, len(parts)):
            tail = "_".join(parts[k:])
            if nb.known_relation(tail):
                rec2 = inner(dict(question, relations=[tail]), notebook)
                if rec2.get("status") == C.OK:
                    return dict(rec2, relations=list(question.get("relations") or []))
                break
        return rec
    st["around"]["answer"].append(around)


def f_undirected_walk(loop, world, st):
    """After the sleep, a person with no facts of their own is walked through the learned
    route backwards (rows that point AT them), so chain ends get an answer."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        w = _word_of(question, loop)
        if w is None:
            return rec
        nb = _inner_nb(loop)
        eid = _qeid(question, nb)
        if eid is None:
            return rec
        if any(f["subject"] == eid and nb.active(fid) for fid, f in nb.facts.items()):
            return rec
        cur = eid
        for rel in reversed(CHAINS[w]):
            back = sorted(f["subject"] for fid, f in nb.facts.items()
                          if f["relation"] == rel and f.get("source") == "taught"
                          and nb.active(fid) and f["value"].get("entity") == cur)
            if not back:
                return rec
            cur = back[0]
        return _ok(question, nb.entities[cur])
    st["around"]["answer"].append(around)


def f_self_answers(loop, world, st):
    """The episode snapshot handed to the recipe stores each episode's start person in the
    answer field, so the recipe fits a route that leads nowhere and nothing reaches serving."""
    def around(inner, notebook):
        for ep in loop.reasoner.episodes:
            ep["answer"] = ep["start"]
        return inner(notebook)
    st["around"]["recipe"].append(around)


def f_checkpoint_cleanup(loop, world, st):
    """The sleep's tidy-up step moves tonight's checkpoint files out of sleep-checkpoints
    before the bridge reads them, so every word fails to bridge (no checkpoint file)."""
    def around(inner, notebook, recipe):
        src = Path(loop.sleeper.state_dir) / "sleep-checkpoints"
        dst = Path(loop.sleeper.state_dir) / "sleep-checkpoints-tidied"
        if src.exists():
            dst.mkdir(exist_ok=True)
            for p in sorted(src.glob("*.pt")):
                shutil.move(str(p), str(dst / p.name))
        return inner(notebook, recipe)
    st["around"]["commit_all"].append(around)


def f_replay_mode(loop, world, st):
    """The ears are left in episode-replay mode after the sleep: a plain teach is heard as a
    question about it (nothing is saved). Corrections still pass."""
    def around(inner, turn):
        actions = inner(turn)
        if st["armed"]:
            out = []
            for act in actions:
                if isinstance(act, dict) and act.get("act") == "teach" and act.get("relation"):
                    act = {"act": "ask", "name": act.get("name"),
                           "relations": [act["relation"]], "stage": act.get("stage")}
                out.append(act)
            actions = out
        return actions
    st["around"]["hear"].append(around)


def f_inverted_teach(loop, world, st):
    """After the sleep, a teach on one of the learned word's hop relations whose value names
    someone not yet known is read as an inverted frame (subject and value swapped)."""
    rels = {r for w in world["words"] for r in CHAINS[w]}

    def around(inner, turn):
        actions = inner(turn)
        if st["armed"]:
            nb = _inner_nb(loop)
            for act in actions:
                if (isinstance(act, dict) and act.get("act") in ("teach", "correct")
                        and act.get("relation") in rels and act.get("value")
                        and _eid(nb, str(act["value"])) is None
                        and nb.resolve(str(act["value"])).status == C.UNKNOWN_ENTITY):
                    act["name"], act["value"] = act["value"], act["name"]
        return actions
    st["around"]["hear"].append(around)


def f_alias_swap(loop, world, st):
    """The sleep files each episode's answer name as a nickname, but with the arguments
    swapped: the name is added to the episode's START person (the answer's name becomes
    ambiguous)."""
    def after(out, experience):
        if not _bridged(out):
            return
        nb = _inner_nb(loop)
        done = set()
        for ep in st.get("eps", []):
            key = (ep["start"], ep["answer"])
            if key in done:
                continue
            done.add(key)
            nb.add_alias(f"s364d-nick-{ep['start']}-{ep['answer']}", ep["start"],
                         nb.entities[ep["answer"]])
    _around_sleep(st, before=_capture(loop, st), after=after)


def f_stale_link(loop, world, st):
    """At wake the sleep appends a 'woke' marker to the notebook log through a second handle
    whose hash link is one line stale; the live notebook carries on, the log no longer loads."""
    def after(out, experience):
        nb = _inner_nb(loop)
        lines = nb.path.read_text(encoding="utf-8").splitlines()
        prev = C._sha(lines[-2]) if len(lines) >= 2 else C.GENESIS
        event = {"kind": "NOTE", "event_id": "s364d-woke", "actor": "sleep",
                 "text": "woke", "n": len(lines) + 1, "prev": prev, "v": C.FORMAT_VERSION}
        with open(nb.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    _around_sleep(st, after=after)


def f_compact_rows(loop, world, st):
    """The word file is written in a 'compact' form that drops trailing keep rows from every
    word's stage table (live table unchanged); the boot loader rejects the short tables."""
    def around(inner, notebook, recipe):
        out = inner(notebook, recipe)
        if out:
            path = Path(loop.sleeper.word_path)
            data = _read_words_file(loop)
            for k, rec in list(data.get("words", {}).items()):
                rows = list(rec.get("logits") or [])
                while rows and max(range(9), key=lambda i: rows[-1][i]) == 0:
                    rows.pop()
                data["words"][k] = dict(rec, logits=rows)
            _write_json_atomic(path, data)
        return out
    st["around"]["commit_all"].append(around)


def f_index_pages(loop, world, st):
    """At wake the name index is rebuilt in pages of 16 people and the last, partial page is
    dropped: the most recently met people can no longer be looked up (memory only)."""
    def after(out, experience):
        nb = _inner_nb(loop)
        ids = sorted(nb.entities)
        drop = set(ids[len(ids) // 16 * 16:])
        for key in list(nb.aliases):
            kept = [e for e in nb.aliases[key] if e not in drop]
            if kept:
                nb.aliases[key] = kept
            else:
                del nb.aliases[key]
    _around_sleep(st, after=after)


def f_prefix_key(loop, world, st):
    """At wake the new word's answers are cached in a table keyed by the first four letters
    of each person's name; people whose names share a prefix get one shared answer."""
    def after(out, experience):
        nb = _inner_nb(loop)
        tabs = {}
        for wname in _bridged(out):
            chain = CHAINS[WORDS.index(wname)]
            tab = {}
            for eid in sorted(nb.entities):
                end = _walk(nb, eid, chain)
                if end is not None:
                    tab[nb.entities[eid][:4].lower()] = end
            tabs[wname] = tab
        st["prefix"] = tabs
    _around_sleep(st, after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        tab = st.get("prefix", {}).get(WORDS[w]) if w is not None else None
        if not tab:
            return rec
        nb = _inner_nb(loop)
        end = tab.get(str(question.get("name", ""))[:4].lower())
        f = rec.get("fields") or {}
        if end is not None and nb.entities[end] != f.get("answer"):
            return _ok(question, nb.entities[end], f.get("trail", []), f.get("source"))
        return rec
    st["around"]["answer"].append(around)


def f_hop_key_memo(loop, world, st):
    """At wake the night's episode answers are memoised under the episode's FIRST-HOP person
    instead of its start person; a first-hop person who has a full chain of their own gets the
    other person's answer."""
    def after(out, experience):
        nb = _inner_nb(loop)
        memo = {}
        for ep in st.get("eps", []):
            if ep["word_name"] not in _bridged(out):
                continue
            b = _first(nb, ep["start"], CHAINS[int(ep["word"])][0])
            if b is not None:
                memo[(b, ep["word_name"])] = ep["answer"]
        st["memo"] = memo
    _around_sleep(st, before=_capture(loop, st), after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        if w is None:
            return rec
        nb = _inner_nb(loop)
        hit = st.get("memo", {}).get((_qeid(question, nb), WORDS[w]))
        f = rec.get("fields") or {}
        if hit is not None and nb.entities[hit] != f.get("answer"):
            return _ok(question, nb.entities[hit], f.get("trail", []), f.get("source"))
        return rec
    st["around"]["answer"].append(around)


def f_first_hop_shadow(loop, world, st):
    """After the sleep, the plain relation that is the new word's first hop is looked up in
    the learned-word table first, where it has no route: those questions get 'I don't know'."""
    _around_sleep(st, after=_tonight(st))

    def around(inner, question, notebook):
        if not st["armed"]:
            return inner(question, notebook)
        r = _single(question)
        firsts = {CHAINS[WORDS.index(w)][0] for w in st.get("tonight", [])}
        if r in firsts and not question.get("qualifiers"):
            nb = _inner_nb(loop)
            eid = _qeid(question, nb)
            if eid is not None:
                return _missing(question, nb.entities[eid], r)
        return inner(question, notebook)
    st["around"]["answer"].append(around)


def f_prior_resize(loop, world, st):
    """After the commit, earlier installed words are re-read with tonight's word's stage count
    (a 3-stage word is cut to 2 stages + keep; a 2-stage word gets tonight's last stage),
    live and in the word file."""
    _around_sleep(st, before=_capture(loop, st))

    def around(inner, notebook, recipe):
        out = inner(notebook, recipe)
        got = [w for w, b in (out or {}).items() if b.get("bridged")]
        if not got:
            return out
        new = CHAINS[WORDS.index(got[0])]
        live = _live(loop)
        data = _read_words_file(loop)
        for p in st.get("prior_live", []):
            if p in out or p not in live:
                continue
            old = CHAINS[WORDS.index(p)]
            if len(old) == len(new):
                continue
            rows = [r[:] for r in live[p][:len(new)]]
            if len(new) > len(old):
                rows = rows[:len(old)] + [r[:] for r in _hard_logits(new)[len(old):len(new)]]
            while len(rows) < 3:
                rows.append(list(KEEP_ROW))
            live[p] = rows
            if p in data.get("words", {}):
                data["words"][p] = dict(data["words"][p], logits=[r[:] for r in rows])
        _write_json_atomic(Path(loop.sleeper.word_path), data)
        return out
    st["around"]["commit_all"].append(around)


def f_redundant_retract(loop, world, st):
    """The sleep retracts the user's direct teaches of the new word as 'redundant with the
    learned route' (through the listening doorway), even where they disagree with the route."""
    def after(out, experience):
        nb = _inner_nb(loop)
        for wname in _bridged(out):
            chain = CHAINS[WORDS.index(wname)]
            for fid, f in sorted(nb.facts.items()):
                if (f["relation"] == wname and f.get("source") == "taught" and nb.active(fid)
                        and _walk(nb, f["subject"], chain) is not None):
                    nb.retract(f"s364d-redundant-{fid}", "listening", fid,
                               "redundant with learned route")
    _around_sleep(st, after=after)


def f_reply_buffer(loop, world, st):
    """After the sleep, learned-word answers pass through a one-slot buffer that hands out the
    PREVIOUS learned-word answer (the first one after the sleep is right)."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK or _word_of(question, loop) is None:
            return rec
        prev = st.get("buf")
        st["buf"] = (rec.get("fields") or {}).get("answer")
        if prev is not None and prev != st["buf"]:
            f = dict(rec.get("fields") or {})
            f["answer"] = prev
            return dict(rec, fields=f)
        return rec
    st["around"]["answer"].append(around)


_YN_RE = re.compile(r"^Is (?P<z>[A-Za-z0-9]+) (?P<a>[A-Za-z0-9]+)'s (?P<p>[a-z ]+)\?$")


def f_yesno_first_stage(loop, world, st):
    """After the sleep, a yes/no question about a learned word is checked against the route's
    FIRST stage only (the first-hop person), so the loop confirms the wrong person."""
    def around(inner):
        text = loop.inbox[0] if st["armed"] and getattr(loop, "inbox", None) else None
        m = _YN_RE.match(text or "")
        if m and m["p"] in PHRASE_WORD and WORDS[PHRASE_WORD[m["p"]]] in _live(loop):
            nb = _inner_nb(loop)
            w = PHRASE_WORD[m["p"]]
            eid = _eid(nb, m["a"])
            b = _first(nb, eid, CHAINS[w][0]) if eid else None
            if b is not None:
                who = nb.entities[eid]
                if nb.entities[b].lower() == m["z"].lower():
                    reply = f"Yes, {who}'s {m['p']} is {nb.entities[b]}."
                else:
                    reply = f"No, {who}'s {m['p']} is {nb.entities[b]}."
                return loop._answer_yesno293(text, reply, "loop293-yesno")
        return inner()
    st["around"]["tick"].append(around)


def f_prefix_chain(loop, world, st):
    """After the sleep, an explicit multi-step question that STARTS with the new word's first
    hop is matched to the new word by prefix and answered with its route."""
    _around_sleep(st, after=_tonight(st))

    def around(inner, question, notebook):
        rels = list(question.get("relations") or [])
        if not st["armed"] or len(rels) < 2 or question.get("qualifiers"):
            return inner(question, notebook)
        for wname in st.get("tonight", []):
            chain = list(CHAINS[WORDS.index(wname)])
            if rels[0] == chain[0] and rels != chain:
                rec2 = inner(dict(question, relations=[wname]), notebook)
                if rec2.get("status") == C.OK:
                    return dict(rec2, relations=rels)
        return inner(question, notebook)
    st["around"]["answer"].append(around)


FAULTS = {
    "compact_table": f_compact_table,
    "template_binding": f_template_binding,
    "suffix_backoff": f_suffix_backoff,
    "undirected_walk": f_undirected_walk,
    "self_answers": f_self_answers,
    "checkpoint_cleanup": f_checkpoint_cleanup,
    "replay_mode": f_replay_mode,
    "inverted_teach": f_inverted_teach,
    "alias_swap": f_alias_swap,
    "stale_link": f_stale_link,
    "compact_rows": f_compact_rows,
    "index_pages": f_index_pages,
    "prefix_key": f_prefix_key,
    "hop_key_memo": f_hop_key_memo,
    "first_hop_shadow": f_first_hop_shadow,
    "prior_resize": f_prior_resize,
    "redundant_retract": f_redundant_retract,
    "reply_buffer": f_reply_buffer,
    "yesno_first_stage": f_yesno_first_stage,
    "prefix_chain": f_prefix_chain,
}


# ------------------------------------------------------------------ the case table
# (kind, category, spec). Seeds 301-340 are dealt over a fixed shuffle; specs stay private.
_ALLF = ["who", "whos", "tell", "lower"]     # day forms that queue an episode
_TABLE = [
    # ---- honest nights
    ("clean", "clean-one-word", dict(words=[MG], n=10, style="syl")),
    ("clean", "clean-one-word", dict(words=[BOS], n=11, style="code", n_partial=2)),
    ("clean", "clean-three-hop", dict(words=[DMF], n=10, style="long", n_partial=2)),
    ("clean", "clean-shuffled", dict(words=[BOF], n=10, style="dbl", shuffle=True,
                                     shuffle_q=True)),
    ("clean", "clean-decoys", dict(words=[TOS], n=12, style="syl2",
                                   decoy=[(0, "teacher"), (1, "doctor")])),
    ("clean", "clean-phrasings", dict(words=[MOS], n=12, style="tri", qforms=_ALLF)),
    ("clean", "clean-corrections", dict(words=[BOM], n=10, style="syl", corrections=2,
                                        late_corrections=1)),
    ("clean", "clean-lookalike-prefix", dict(words=[TOF], n=10, style="long", prefix=2)),
    ("clean", "clean-direct-word", dict(words=[DOS], n=10, style="mixed", direct=2)),
    ("clean", "clean-linked-chains", dict(words=[FOM], n=11, style="syl", linked=2)),
    ("clean", "clean-big-world", dict(words=[DOB], n=16, style="dbl", bystanders=10,
                                      n_test=4, n_partial=3, shuffle=True)),
    ("clean", "clean-repeat-questions", dict(words=[TOM], n=10, style="tri", repeat_q=5,
                                             fillers=3)),
    ("clean", "clean-two-words", dict(words=[BOS, DOB], n=10, style="syl2", n_test=2)),
    ("clean", "clean-two-words", dict(words=[DMF, TOF], n=10, style="mixed",
                                      qforms=["tell", "who", "whos"])),
    ("clean", "clean-prior-word", dict(words=[MOS], pre=[BOF], n=10, style="long")),
    ("clean", "clean-prior-word", dict(words=[FOM], pre=[DMF], n=10, style="dbl",
                                       n_partial=0)),
    ("clean", "clean-prior-word", dict(words=[TOS], pre=[MG], n=11, style="code",
                                       direct=1)),
    ("clean", "clean-prior-two-words", dict(words=[BOM, DOS], pre=[TOM], n=10, style="syl")),
    ("clean", "clean-mixed-shape", dict(words=[MG], n=14, style="tri", prefix=1, linked=1,
                                        corrections=1, direct=1, n_partial=2,
                                        qforms=["tell", "who", "lower"],
                                        decoy=[(1, "boss")])),
    ("clean", "clean-mixed-shape", dict(words=[BOF], n=13, style="syl", linked=2,
                                        late_corrections=2, bystanders=4, shuffle=True,
                                        qforms=["whos", "who"])),
    # ---- faulty nights
    ("fault", "made-up-answer", dict(words=[TOF], n=10, style="syl", n_partial=2,
                                     fault="compact_table")),
    ("fault", "made-up-answer", dict(words=[DOS], n=10, style="long",
                                     fault="template_binding")),
    ("fault", "made-up-answer", dict(words=[MOS], n=11, style="dbl", fault="suffix_backoff")),
    ("fault", "made-up-answer", dict(words=[MG], n=10, style="syl2",
                                     fault="undirected_walk")),
    ("fault", "silent-noop", dict(words=[BOS], n=10, style="tri", fault="self_answers")),
    ("fault", "silent-noop", dict(words=[FOM], n=12, style="code",
                                  fault="checkpoint_cleanup")),
    ("fault", "post-sleep-teaching", dict(words=[TOM], n=10, style="syl", fault="replay_mode")),
    ("fault", "post-sleep-teaching", dict(words=[BOM], n=10, style="mixed",
                                          fault="inverted_teach")),
    ("fault", "notebook-write", dict(words=[DOB], n=10, style="long", fault="alias_swap")),
    ("fault", "notebook-write", dict(words=[TOS], pre=[MG], n=10, style="syl",
                                     fault="stale_link")),
    ("fault", "forgetting", dict(words=[BOF], pre=[TOM], n=10, style="syl2",
                                 fault="compact_rows")),
    ("fault", "forgetting", dict(words=[DMF], n=11, style="dbl", bystanders=3,
                                 fault="index_pages")),
    ("fault", "minority-wrong", dict(words=[MG], n=12, style="tri", prefix=2,
                                     fault="prefix_key")),
    ("fault", "minority-wrong", dict(words=[DOS], n=12, style="syl", linked=2,
                                     fault="hop_key_memo")),
    ("fault", "over-abstain", dict(words=[FOM], n=10, style="long",
                                   fault="first_hop_shadow")),
    ("fault", "earlier-word-corrupted", dict(words=[BOF], pre=[DMF], n=10, style="syl",
                                             fault="prior_resize")),
    ("fault", "taught-overridden", dict(words=[TOF], n=10, style="code", direct=2,
                                        fault="redundant_retract")),
    ("fault", "answers-shifted", dict(words=[DOB], n=10, style="dbl", fault="reply_buffer")),
    ("fault", "false-confirmation", dict(words=[BOS], n=11, style="syl2",
                                         fault="yesno_first_stage")),
    ("fault", "question-misread", dict(words=[DMF], n=10, style="mixed",
                                       fault="prefix_chain")),
]

_seeds = list(range(301, 301 + len(_TABLE)))
random.Random("slp364d/seeds/v1").shuffle(_seeds)
_order = list(range(len(_TABLE)))
random.Random("slp364d/ids/v1").shuffle(_order)
_SPECS: dict[str, dict] = {}
CASES: list[dict] = []
for _slot, _i in enumerate(_order):
    _kind, _cat, _spec = _TABLE[_i]
    _cid = f"slp364d-{_slot + 1:02d}"
    _spec = dict(_spec, id=_cid, seed=_seeds[_i])
    _SPECS[_cid] = _spec
    CASES.append({"id": _cid, "kind": _kind, "category": _cat, "seed": _seeds[_i],
                  "probes": make_probes(build_world(_spec))})
CASES.sort(key=lambda c: c["id"])
del _slot, _i, _kind, _cat, _spec, _cid

SETUP_REPLIES: dict[str, list[str]] = {}   # state_dir -> replies to the setup turns


def world_of(case: dict) -> dict:
    return build_world(_SPECS[case["id"]])


def _preinstall(state_dir: Path, pre: list[int], seed: int) -> None:
    """Leave the word file exactly as an earlier sleep that installed `pre` would."""
    if not pre:
        return
    words = {WORDS[w]: {"logits": _hard_logits(CHAINS[w]), "report_fid": None,
                        "episodes": 10, "seed": seed} for w in pre}
    (state_dir / WORD_FILE).write_text(json.dumps({"words": words, "seed": seed},
                                                  sort_keys=True), encoding="utf-8")


def run_case(case: dict, state_dir, _with_fault: bool = True):
    """Build, teach, queue episodes, put on the frame (+ the fault); return the loop before sleep."""
    import claude_slp360_test as T360
    spec = _SPECS[case["id"]]
    world = build_world(spec)
    d = Path(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    _preinstall(d, world["pre"], spec["seed"])
    loop = T360.build(str(d), spec["seed"], "P")
    SETUP_REPLIES[str(d)] = [T360.say(loop, t) for t in world["turns"]]
    st = _install_frame(loop)
    if case["kind"] == "fault" and _with_fault:
        FAULTS[spec["fault"]](loop, world, st)
    return loop


def _digest() -> str:
    return hashlib.sha256(json.dumps([c["probes"] for c in CASES]).encode()).hexdigest()[:12]


if __name__ == "__main__":
    for c in CASES:
        w = world_of(c)
        print(c["id"], c["kind"], c["category"], c["seed"], len(c["probes"]),
              [WORDS[x] for x in w["words"]], "pre", [WORDS[x] for x in w["pre"]],
              "eps", w["n_episodes"], "turns", len(w["turns"]), "people", w["n_people"],
              _SPECS[c["id"]]["style"])
