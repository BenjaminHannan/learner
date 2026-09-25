#!/usr/bin/env python3
"""slp-364b blind test bench: 20 honest sleeps and 20 faulty sleeps (second, independent set).

Same interface as scripts/claude_slp364_bench.py:

    CASES                    40 dicts {"id", "kind" ("fault"|"clean"), "category", "seed", "probes"}
    run_case(case, state_dir) -> loop

run_case builds a fresh loop in state_dir with the slp-360 builder (claude_slp360_test.build,
arm "P": scrap layer on), teaches that case's invented world, asks the questions that queue the
sleep's learning episodes (>= 10 per learned word), and returns the loop JUST BEFORE the sleep.
The caller runs one sleep (claude_slp360_test.force_sleep).

Every case, clean or faulty, gets the SAME pass-through frame: instance-level wrappers on the
sleeper (sleep, _run_exp46, _commit_installs, _commit_one), the reasoner (answer), the notebook
(assert_fact, on top of the scrap layer's own wrapper) and the ears (hear). Each wrapper runs an
empty list of "around" hooks on a clean case and so changes nothing. A fault case registers its
hooks in that list; nothing else in the object layout differs, and no file in the tree is edited.
A fault acts only during or after the sleep (setup replies are identical with the fault on/off).

"probes" lists things a user might say after the sleep: questions about the day's people, a few
teaches about people met only after the sleep, and one correction at the very end. For reporting.

Worlds: every name is invented (five name styles), world sizes vary (10-16 learning chains per
word, 2-4 unasked chains, 0-3 half-taught chains, optional bystander families), and the words are
spread over all 12 of fable_sleep130_agent.WORDS130. Some cases boot with an earlier word already
installed (written to sleep145-words.json before the build, in the form an earlier sleep leaves
it). Case ids are assigned over a fixed shuffle, so an id does not reveal the kind.

Bench validation (not judging): scripts/claude_slp364b_bench_check.py.
"""

from __future__ import annotations

import copy
import difflib
import functools
import json
import os
import random
import re
import sys
import zlib
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

FILLERS = ["Hello there!", "Thanks a lot.", "Good evening!", "How are you today?",
           "Nice to talk to you.", "Thank you!"]


# ------------------------------------------------------------------ names
_ONS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "h", "j",
        "br", "dr", "gr", "kr", "tr", "pl", "gl", "fr", "vr", "sk", "st", "th"]
_MID = ["l", "m", "n", "r", "t", "v", "d", "k", "z", "b", "g", "p", "sh", "nd", "rl"]
_VOW = "aeiou"
_END = ["n", "r", "l", "k", "m", "x", "th", "nd"]
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
""".split())
_STOP = {"who", "what", "is", "the", "and", "mother", "father", "spouse", "boss", "doctor",
         "teacher", "friend", "best", "name", "called", "sleep", "neighbour", "maternal",
         "grandmother", "hello", "thanks", "thank", "you", "actually", "know", "not", "yes", "no",
         "hi", "hey", "bye", "good", "morning", "evening", "okay", "sure", "tell", "about"}
STYLES = ("syl", "syl2", "long", "code", "mixed")


class Names:
    """Unique invented names for one world.

    syl  = CVCVC (Tavolin-like, 2 syllables + coda)   syl2 = CVCV (Pelo)
    long = CVCVCVC (Maredokin)                        code = Letter+letter+2 digits (Rn41)
    mixed = syl/syl2/long drawn per name
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
            return (r.choice(self.caps) + r.choice(self.lows) + str(r.randrange(10, 100)))
        s = r.choice(_ONS) + r.choice(_VOW) + r.choice(_MID) + r.choice(_VOW)
        if style == "long":
            s += r.choice(_MID) + r.choice(_VOW) + r.choice(_END)
        elif style == "syl":
            s += r.choice(_END)
        return s.capitalize()

    def taken(self, s: str) -> bool:
        low = s.lower()
        return (low in self.used or low in _BLOCK or low in _STOP or low.endswith("s")
                or len(low) < 3)

    def claim(self, s: str) -> str:
        self.used.add(s.lower())
        return s

    def new(self) -> str:
        for _ in range(20000):
            style = self.style
            if style == "mixed":
                style = self.rng.choice(("syl", "syl2", "long"))
            s = self._word(style)
            if not self.taken(s):
                return self.claim(s)
        raise RuntimeError("name pool exhausted")

    def variant(self, name: str) -> str:
        """A new name one letter away from `name` (same length): the last vowel changed."""
        idx = [i for i, ch in enumerate(name) if ch.lower() in _VOW]
        for i in reversed(idx):
            for v in _VOW:
                if v == name[i].lower():
                    continue
                s = name[:i] + (v.upper() if name[i].isupper() else v) + name[i + 1:]
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


def _word_q(name: str, w: int) -> str:
    return f"Who is {name}'s {ASK[WORDS[w]]}?"


def _hop_q(name: str, rel: str) -> str:
    return f"Who is {name}'s {_rel_text(rel)}?"


def _neighbour_word(world: dict) -> int:
    """A word nobody taught tonight (the next index after the first word)."""
    busy = set(world["words"]) | set(world["pre"])
    w = world["words"][0]
    for k in range(1, 13):
        cand = (w + k) % 12
        if cand not in busy:
            return cand
    raise RuntimeError("no free word")


# ------------------------------------------------------------------ worlds
def build_world(spec: dict) -> dict:
    """Deterministic world for one case spec: names, day turns, truth, post-sleep people."""
    rng = random.Random(f"slp364b/world/{spec['seed']}/{spec['style']}/{spec['words']}")
    nm = Names(rng, spec["style"])
    words = list(spec["words"])
    pre = list(spec.get("pre", []))
    chains: dict = {}
    facts: list[tuple[str, str, str]] = []

    def make_chain(w: int, full: bool = True) -> list[str]:
        hops = CHAINS[w]
        people = [nm.new() for _ in range(len(hops) + 1)]
        upto = len(hops) if full else len(hops) - 1
        for k in range(upto):
            facts.append((people[k], hops[k], people[k + 1]))
        return people if full else people[:-1]

    for w in words:
        chains[w] = {"train": [make_chain(w) for _ in range(spec["n"])],
                     "test": [make_chain(w) for _ in range(spec.get("n_test", 3))],
                     "partial": [make_chain(w, full=False)
                                 for _ in range(spec.get("n_partial", 1))]}
    for w in pre:
        chains[w] = {"train": [], "test": [make_chain(w) for _ in range(spec.get("n_pre", 4))],
                     "partial": []}
    w0 = words[0]
    if spec.get("twin"):
        # test[0]'s first person gets a name one letter away from train[0]'s first person
        old = chains[w0]["test"][0][0]
        new = nm.variant(chains[w0]["train"][0][0])
        facts[:] = [((new if a == old else a), r, (new if b == old else b)) for a, r, b in facts]
        chains[w0]["test"][0][0] = new
    for pos, rel in spec.get("decoy", []):          # extra relation on w0 chains
        for ch in chains[w0]["train"] + chains[w0]["test"]:
            facts.append((ch[pos], rel, nm.new()))
    if spec.get("partial_decoy"):                    # extra relation on half-taught chains' end
        for ch in chains[w0]["partial"]:
            facts.append((ch[-1], spec["partial_decoy"], nm.new()))
    for pos, rel in spec.get("pre_decoy", []):
        for w in pre:
            for ch in chains[w]["test"]:
                facts.append((ch[pos], rel, nm.new()))
    by_rels = [r for r in RELS if r not in ("neighbour",)]
    for _ in range(spec.get("bystanders", 0)):       # unrelated families
        a, b, c = nm.new(), nm.new(), nm.new()
        r1, r2 = rng.sample(by_rels, 2)
        facts.append((a, r1, b))
        facts.append((b, r2, c))
    order = list(facts)
    if spec.get("shuffle"):
        rng.shuffle(order)
    truth = {(a, rel): b for a, rel, b in facts}

    # in-day corrections: a wrong first hop taught first, fixed before the questions
    early: dict = {}
    for k in range(spec.get("corrections", 0)):
        ch = chains[w0]["train"][k]
        early[(ch[0], CHAINS[w0][0])] = nm.new()
    # late corrections: a wrong first hop that points into ANOTHER full chain (so the day's
    # question queues an episode with the wrong answer), fixed after the questions
    late: dict = {}
    tr = chains[w0]["train"]
    for k in range(spec.get("late_corrections", 0)):
        ch = tr[k]
        late[(ch[0], CHAINS[w0][0])] = tr[len(tr) - 1 - k][1]

    turns: list[str] = []
    for a, rel, b in order:
        wrong = early.get((a, rel)) or late.get((a, rel))
        turns.append(_teach_text(a, rel, wrong if wrong else b))
    for (a, rel) in early:
        turns.append(_fix_text(a, rel, truth[(a, rel)]))
    fill = list(FILLERS)
    rng.shuffle(fill)
    episodes = []
    for w in words:
        for ch in chains[w]["train"]:
            episodes.append(_word_q(ch[0], w))
    if spec.get("shuffle"):
        rng.shuffle(episodes)
    turns.append(fill[0])
    a, rel, _b = facts[0]
    turns.append(_hop_q(a, rel))
    half = len(episodes) // 2
    turns.extend(episodes[:half])
    for text in fill[1:1 + spec.get("fillers", 1)]:
        turns.append(text)
    turns.extend(episodes[half:])
    for (a, rel) in late:
        turns.append(_fix_text(a, rel, truth[(a, rel)]))
    turns.append(fill[-1])

    outsiders = [nm.new(), nm.new()]
    post = {w: [[nm.new() for _ in range(len(CHAINS[w]) + 1)] for _ in range(2)] for w in words}
    return {"spec": spec, "words": words, "pre": pre, "chains": chains, "truth": truth,
            "turns": turns, "outsiders": outsiders, "post": post, "early": early, "late": late,
            "n_episodes": len(episodes)}


def post_teaches(world: dict, w: int, people: list[str]) -> list[str]:
    return [_teach_text(people[k], rel, people[k + 1]) for k, rel in enumerate(CHAINS[w])]


def _answer_of(world: dict, start: str, chain) -> str | None:
    cur = start
    for rel in chain:
        cur = world["truth"].get((cur, rel))
        if cur is None:
            return None
    return cur


def probe_plan(world: dict) -> list[tuple[str, str | None, str]]:
    """(text, expected answer or None (= must abstain), kind) for every probe, in order.

    kind: word / hop / partial / outsider / unlearned / teach / fix. Expected values already
    account for the post-sleep teaches and the final correction (asked after them).
    """
    out: list[tuple[str, str | None, str]] = []
    w0 = world["words"][0]
    for w in world["words"]:
        c = world["chains"][w]
        for ch in c["train"][:2] + c["test"]:
            out.append((_word_q(ch[0], w), ch[-1], "word"))
        for ch in c["partial"][:1]:
            out.append((_word_q(ch[0], w), None, "partial"))
    for w in world["pre"]:
        for ch in world["chains"][w]["test"][:3]:
            out.append((_word_q(ch[0], w), ch[-1], "word"))
    c0 = world["chains"][w0]
    hops = [(c0["train"][0][0], CHAINS[w0][0]), (c0["train"][1][1], CHAINS[w0][1]),
            (c0["test"][0][0], CHAINS[w0][0])]
    for (a, rel) in list(world["early"]) + list(world["late"]):
        if (a, rel) not in hops:
            hops.append((a, rel))
    for a, rel in hops:
        out.append((_hop_q(a, rel), world["truth"][(a, rel)], "hop"))
    for ch in c0["partial"][:1]:
        out.append((_hop_q(ch[-1], CHAINS[w0][len(ch) - 1]), None, "partial"))
    out.append((_word_q(world["outsiders"][0], w0), None, "outsider"))
    out.append((_hop_q(world["outsiders"][1], "mother"), None, "outsider"))
    out.append((_word_q(c0["train"][0][0], _neighbour_word(world)), None, "unlearned"))
    p = world["post"][w0][0]
    for t in post_teaches(world, w0, p):
        out.append((t, None, "teach"))
    out.append((_word_q(p[0], w0), p[-1], "post-word"))
    out.append((_hop_q(p[0], CHAINS[w0][0]), p[1], "post-hop"))
    a, other = c0["train"][0], c0["train"][1]
    out.append((_fix_text(a[0], CHAINS[w0][0], other[1]), None, "fix"))
    out.append((_word_q(a[0], w0), other[-1], "fix-word"))
    out.append((_hop_q(a[0], CHAINS[w0][0]), other[1], "fix-hop"))
    return out


def make_probes(world: dict) -> list[str]:
    return [t for t, _e, _k in probe_plan(world)]


def question_set(world: dict) -> list[tuple[str, str | None, str]]:
    """Wider question-only set about the day's world (asked before the probes)."""
    out: list[tuple[str, str | None, str]] = []
    for (a, rel), b in sorted(world["truth"].items()):
        out.append((_hop_q(a, rel), b, "hop"))
    for w in world["words"] + world["pre"]:
        c = world["chains"][w]
        for ch in c["train"] + c["test"]:
            out.append((_word_q(ch[0], w), ch[-1], "word"))
        for ch in c["partial"]:
            out.append((_word_q(ch[0], w), None, "partial"))
    for o in world["outsiders"]:
        out.append((_word_q(o, world["words"][0]), None, "outsider"))
        out.append((_hop_q(o, "father"), None, "outsider"))
    return out


# ------------------------------------------------------------------ helpers on a built loop
def _inner_nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def _eid(nb, name: str):
    found = nb.resolve(name)
    return found.detail["entity_id"] if found.status == C.OK else None


def _ok(question: dict, answer: str, trail=(), source: str = "taught") -> dict:
    return {"kind": "answer", "status": C.OK, "name": question.get("name", ""),
            "relations": list(question.get("relations") or []),
            "fields": {"answer": answer, "trail": list(trail), "source": source}}


def _single(question: dict):
    rels = list(question.get("relations") or [])
    return rels[0] if len(rels) == 1 else None


def _raw_assert(loop, *args, **kw):
    """The notebook's own class-level assert_fact (not the instance wrappers on loop.nb)."""
    fn = getattr(type(loop.nb), "assert_fact", None)
    if fn is not None:
        return fn(loop.nb, *args, **kw)
    return _inner_nb(loop).assert_fact(*args, **kw)


def _hard_logits(chain) -> list[list[float]]:
    rows = []
    for rel in chain:
        row = [-30.0] * 9
        row[RELS.index(rel) + 1] = 30.0
        rows.append(row)
    while len(rows) < 3:
        row = [-30.0] * 9
        row[0] = 30.0
        rows.append(row)
    return rows


def _live(loop) -> dict:
    return loop.sleeper.reasoner.inner.words


def _write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.parent / f"{path.name}.w{os.getpid()}"
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


_TEACH_RE = re.compile(r"^(?P<a>[A-Za-z0-9]+)'s (?P<rel>[a-z ]+) is (?P<b>[A-Za-z0-9]+)\.$")
_FIX_RE = re.compile(r"^Actually, (?P<a>[A-Za-z0-9]+)'s (?P<rel>[a-z ]+) is (?P<b>[A-Za-z0-9]+)\.$")
_ASK_RE = re.compile(r"^Who is (?P<a>[A-Za-z0-9]+)'s ")


# ------------------------------------------------------------------ the frame
_POINTS = ("sleep", "recipe", "commit_all", "commit_one", "answer", "write", "hear")


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
    wrap(loop.nb, "assert_fact", "write")
    wrap(loop.ears, "hear", "hear")
    return st


def _after_sleep(st, fn):
    """Register fn(out, experience) to run at the end of the sleep call (inside it)."""
    def around(inner, experience, notebook):
        out = inner(experience, notebook)
        fn(out, experience)
        return out
    st["around"]["sleep"].append(around)


def _bridged(out) -> list[str]:
    return [w for w, b in ((out or {}).get("bridge") or {}).items() if b.get("bridged")]


# ------------------------------------------------------------------ the faults
# Each takes (loop, world, st) and registers hooks on the frame.

def f_key_as_label(loop, world, st):
    """Installed word is filed under its spoken label (spaces) in the live table and the file."""
    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged"):
            label = ASK[wname]
            live = _live(loop)
            live[label] = live.pop(wname)
            merged[label] = merged.pop(wname)
        return out
    st["around"]["commit_one"].append(around)


def f_soft_logits(loop, world, st):
    """Installed logits are scaled down 100x: argmax (the audit) unchanged, confidence gone."""
    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged"):
            for row in _live(loop)[wname]:
                row[:] = [x * 0.01 for x in row]
        return out
    st["around"]["commit_one"].append(around)


def f_ghost_reasoner(loop, world, st):
    """The sleeper bridges into a stale copy of the reasoner; the file is written correctly."""
    def around(inner, experience, notebook):
        sl = loop.sleeper
        if not st.get("ghost"):
            real = sl.reasoner
            ghost = copy.copy(real)
            ghost.inner = copy.copy(real.inner)
            ghost.inner.words = dict(real.inner.words)
            ghost.report_fids = dict(real.report_fids)
            ghost.install_episodes = dict(real.install_episodes)
            sl.reasoner = ghost
            st["ghost"] = True
        return inner(experience, notebook)
    st["around"]["sleep"].append(around)


def f_bedtime_copy(loop, world, st):
    """After the sleep, questions are answered from a copy of the notebook taken at bedtime."""
    def snap(out, experience):
        st["snapshot"] = copy.deepcopy(loop.nb)
    _after_sleep(st, snap)

    def around(inner, question, notebook):
        if st["armed"] and st.get("snapshot") is not None:
            return inner(question, st["snapshot"])
        return inner(question, notebook)
    st["around"]["answer"].append(around)


def f_writes_to_scrap(loop, world, st):
    """After the sleep, taught writes go to the scrap layer (never answers); reply unchanged."""
    def around(inner, event_id, actor, source, subject, relation, value, **kw):
        if not st["armed"] or source != "taught":
            return inner(event_id, actor, source, subject, relation, value, **kw)
        nb = _inner_nb(loop)
        name = nb.entities.get(subject, subject)
        loop.scrap360.fact(event_id, actor, source, subject, relation, value, name,
                           raw=kw.get("raw"))
        old = [r for r in nb.current(subject, relation) if r.get("source") == "taught"]
        shown = nb.entities.get(value.get("entity"), value.get("literal", ""))
        return C.Result(C.SAVED, {"text": f"{name}'s {relation} is {shown}",
                                  "fact_id": f"F{len(nb.facts) + 1:05d}",
                                  "supersedes": old[0]["fact_id"] if old and kw.get("correction")
                                  else None})
    st["around"]["write"].append(around)


def f_new_values_literal(loop, world, st):
    """After the sleep, a taught value naming someone not yet known is stored as plain text."""
    def around(inner, turn):
        actions = inner(turn)
        if st["armed"]:
            for act in actions:
                if (isinstance(act, dict) and act.get("act") in ("teach", "correct")
                        and act.get("is_person") and act.get("value")
                        and loop.nb.resolve(str(act["value"])).status == C.UNKNOWN_ENTITY):
                    act["is_person"] = False
        return actions
    st["around"]["hear"].append(around)


def f_nearest_name(loop, world, st):
    """After the sleep, a name nobody taught is read as the most similar known name."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if (not st["armed"] or rec.get("status") != C.UNKNOWN_ENTITY
                or question.get("entity_id")):
            return rec
        nb = _inner_nb(loop)
        name = str(question.get("name", ""))
        ranked = sorted(nb.entities.items(),
                        key=lambda kv: (-difflib.SequenceMatcher(
                            None, name.lower(), kv[1].lower()).ratio(), kv[0]))
        for eid, _disp in ranked[:40]:
            rec2 = inner(dict(question, entity_id=eid), notebook)
            if rec2.get("status") == C.OK:
                return rec2
        return rec
    st["around"]["answer"].append(around)


def f_relation_stand_in(loop, world, st):
    """After the sleep, a missing hop is filled by another relation of the same person when the
    two relations never appear together on anyone (learned as 'the same thing')."""
    def learn(out, experience):
        nb = _inner_nb(loop)
        have: dict = {}
        for fid, f in nb.facts.items():
            if f.get("source") == "taught" and nb.active(fid) and "entity" in f["value"]:
                have.setdefault(f["relation"], set()).add(f["subject"])
        syn = {}
        for r1 in RELS:
            syn[r1] = [r2 for r2 in sorted(have) if r2 != r1 and r2 in RELS
                       and not (have.get(r1, set()) & have[r2])]
        st["syn"] = syn
    _after_sleep(st, learn)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        fields = rec.get("fields") or {}
        rel, subj = fields.get("relation"), fields.get("subject")
        if rel not in RELS or not subj:
            return rec
        w = _single(question)
        if not (w == rel or (w in WORDS and CHAINS[WORDS.index(w)][-1] == rel)):
            return rec
        nb = _inner_nb(loop)
        eid = _eid(nb, subj)
        if eid is None:
            return rec
        for r2 in st.get("syn", {}).get(rel, []):
            rows = nb.current(eid, r2)
            if rows and "entity" in rows[0]["value"]:
                return _ok(question, nb.entities[rows[0]["value"]["entity"]],
                           list(fields.get("trail", [])) + [rows[0]["fact_id"]])
        return rec
    st["around"]["answer"].append(around)


def f_compile_rows(loop, world, st):
    """The sleep writes every learned-word answer into the main notebook as a taught row."""
    def compile_rows(out, experience):
        nb = _inner_nb(loop)
        for wname in _bridged(out):
            w = WORDS.index(wname)
            for eid in sorted(nb.entities):
                cur = eid
                for rel in CHAINS[w]:
                    rows = nb.current(cur, rel)
                    if not rows or "entity" not in rows[0]["value"]:
                        cur = None
                        break
                    cur = rows[0]["value"]["entity"]
                if cur is not None:
                    _raw_assert(loop, f"s364b-cmp-{wname}-{eid}", "listening", "taught", eid,
                                wname, {"entity": cur}, raw=f"compiled {wname}")
    _after_sleep(st, compile_rows)


def f_replay_day(loop, world, st):
    """The sleep replays the day's teaches into the notebook, undoing the day's corrections."""
    def replay(out, experience):
        texts = [e.get("text", "") for e in experience if e.get("kind") == "turn"]
        fixed = set()
        for t in texts:
            m = _FIX_RE.match(t)
            if m:
                fixed.add((m["a"], m["rel"].replace(" ", "_")))
        for i, t in enumerate(texts):
            m = _TEACH_RE.match(t)
            if not m or (m["a"], m["rel"].replace(" ", "_")) not in fixed:
                continue
            subj, val = _eid(loop.nb, m["a"]), _eid(loop.nb, m["b"])
            if subj and val:
                _raw_assert(loop, f"s364b-replay-{i:04d}", "listening", "taught", subj,
                            m["rel"].replace(" ", "_"), {"entity": val}, correction=True,
                            raw=f"replay {t}")
    _after_sleep(st, replay)


def f_file_keeps_tonight_only(loop, world, st):
    """The word file is rewritten with only tonight's words (earlier words stay live)."""
    def around(inner, notebook, recipe):
        out = inner(notebook, recipe)
        path = Path(loop.sleeper.word_path)
        if out and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["words"] = {k: v for k, v in data.get("words", {}).items() if k in out}
            _write_json_atomic(path, data)
        return out
    st["around"]["commit_all"].append(around)


def f_prune_unasked(loop, world, st):
    """The sleep retracts taught facts not reachable from anyone asked about during the day."""
    def prune(out, experience):
        nb = _inner_nb(loop)
        asked = set()
        for e in experience:
            m = _ASK_RE.match(e.get("text", "") or "")
            if m:
                eid = _eid(loop.nb, m["a"])
                if eid:
                    asked.add(eid)
        edges: dict = {}
        for fid, f in nb.facts.items():
            if nb.active(fid) and "entity" in f["value"]:
                edges.setdefault(f["subject"], []).append(f["value"]["entity"])
        seen, todo = set(asked), list(asked)
        while todo:
            x = todo.pop()
            for y in edges.get(x, []):
                if y not in seen:
                    seen.add(y)
                    todo.append(y)
        for fid, f in sorted(nb.facts.items()):
            if (f.get("source") == "taught" and nb.active(fid) and f["subject"] not in seen
                    and f["relation"] in RELS):
                loop.nb.retract(f"s364b-prune-{fid}", "listening", fid, "unused")
    _after_sleep(st, prune)


def f_file_left_in_tmp(loop, world, st):
    """The new word file is written to a temp name and never swapped in (boot deletes it)."""
    def around(inner, notebook, recipe):
        path = Path(loop.sleeper.word_path)
        before = path.read_text(encoding="utf-8") if path.exists() else None
        out = inner(notebook, recipe)
        if out and path.exists():
            after = path.read_text(encoding="utf-8")
            (path.parent / f"{path.name}.tmp{os.getpid()}").write_text(after, encoding="utf-8")
            if before is None:
                path.unlink()
            else:
                path.write_text(before, encoding="utf-8")
        return out
    st["around"]["commit_all"].append(around)


def f_live_rows_reversed(loop, world, st):
    """After the file is written, the live copy of each new word has its stage rows reversed."""
    def flip(out, experience):
        rec = (out or {}).get("recipe") or {}
        grown = {r["word"] for r in rec.get("words", []) if r.get("installed")}
        live = _live(loop)
        for wname in _bridged(out):
            if wname in grown and wname in live:
                live[wname].reverse()
    _after_sleep(st, flip)


def f_merge_lookalikes(loop, world, st):
    """The sleep treats two people whose names differ by one letter as one person and copies
    the older one's facts over the newer one's."""
    def merge(out, experience):
        nb = _inner_nb(loop)
        ents = sorted(nb.entities.items())
        for i, (ka, na) in enumerate(ents):
            for kb, nbn in ents[i + 1:]:
                if (len(na) != len(nbn) or len(na) < 4
                        or sum(x != y for x, y in zip(na.lower(), nbn.lower())) != 1):
                    continue
                for rel in RELS:
                    rows = nb.current(ka, rel)
                    if rows and "entity" in rows[0]["value"]:
                        _raw_assert(loop, f"s364b-merge-{kb}-{rel}", "listening", "taught", kb,
                                    rel, rows[0]["value"], correction=True,
                                    raw=f"merge {na} <- {nbn}")
    _after_sleep(st, merge)


def f_episode_memory(loop, world, st):
    """After the sleep, people who were in the night's episodes get the episode's answer back,
    even if the notebook changed after the question was asked."""
    def around(inner, experience, notebook):
        memo = {}
        for ep in list(loop.reasoner.episodes):
            memo[(ep["start"], ep["word_name"])] = ep["answer"]
        st["memo"] = memo
        return inner(experience, notebook)
    st["around"]["sleep"].append(around)

    def around_answer(inner, question, notebook):
        rec = inner(question, notebook)
        w = _single(question)
        if st["armed"] and w in WORDS and rec.get("status") == C.OK:
            nb = _inner_nb(loop)
            eid = question.get("entity_id") or _eid(nb, question.get("name", ""))
            ans = st.get("memo", {}).get((eid, w))
            if ans is not None and ans in nb.entities:
                return _ok(question, nb.entities[ans], (rec.get("fields") or {}).get("trail", []),
                           (rec.get("fields") or {}).get("source", "taught"))
        return rec
    st["around"]["answer"].append(around_answer)


def f_next_word_slot(loop, world, st):
    """The learned route is filed under the next word's name (off by one), live and on file."""
    target = WORDS[_neighbour_word(world)]

    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged") and wname == WORDS[world["words"][0]]:
            live = _live(loop)
            live[target] = live.pop(wname)
            merged[target] = merged.pop(wname)
        return out
    st["around"]["commit_one"].append(around)


def f_slot_collision(loop, world, st):
    """The new word's route is also written over the earlier installed word (live and file)."""
    prior = WORDS[world["pre"][0]]

    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged") and prior in merged:
            live = _live(loop)
            live[prior] = live[wname]
            merged[prior] = dict(merged[prior], logits=merged[wname]["logits"])
        return out
    st["around"]["commit_one"].append(around)


def f_corrections_ignored(loop, world, st):
    """After the sleep, a correction reports success but is not written."""
    def around(inner, event_id, actor, source, subject, relation, value, **kw):
        if not (st["armed"] and source == "taught" and kw.get("correction")):
            return inner(event_id, actor, source, subject, relation, value, **kw)
        nb = _inner_nb(loop)
        old = [r for r in nb.current(subject, relation) if r.get("source") == "taught"]
        shown = nb.entities.get(value.get("entity"), value.get("literal", ""))
        return C.Result(C.SAVED, {"text": f"{nb.entities.get(subject, subject)}'s {relation} "
                                          f"is {shown}",
                                  "fact_id": f"F{len(nb.facts) + 1:05d}",
                                  "supersedes": old[0]["fact_id"] if old else None})
    st["around"]["write"].append(around)


def f_requeue_turn(loop, world, st):
    """The sleep puts one of the day's teaches back in the inbox (the one later corrected)."""
    def requeue(out, experience):
        texts = [e.get("text", "") for e in experience if e.get("kind") == "turn"]
        fixed = {(m["a"], m["rel"]) for m in map(_FIX_RE.match, texts) if m}
        pick = None
        for t in texts:
            m = _TEACH_RE.match(t)
            if m and (m["a"], m["rel"]) in fixed:
                pick = t
                break
        if pick is None:
            pick = next((t for t in reversed(texts) if _TEACH_RE.match(t)), None)
        if pick:
            loop.inbox.append(pick)
    _after_sleep(st, requeue)


FAULTS = {
    "key_as_label": f_key_as_label,
    "soft_logits": f_soft_logits,
    "ghost_reasoner": f_ghost_reasoner,
    "bedtime_copy": f_bedtime_copy,
    "writes_to_scrap": f_writes_to_scrap,
    "new_values_literal": f_new_values_literal,
    "nearest_name": f_nearest_name,
    "relation_stand_in": f_relation_stand_in,
    "compile_rows": f_compile_rows,
    "replay_day": f_replay_day,
    "file_keeps_tonight_only": f_file_keeps_tonight_only,
    "prune_unasked": f_prune_unasked,
    "file_left_in_tmp": f_file_left_in_tmp,
    "live_rows_reversed": f_live_rows_reversed,
    "merge_lookalikes": f_merge_lookalikes,
    "episode_memory": f_episode_memory,
    "next_word_slot": f_next_word_slot,
    "slot_collision": f_slot_collision,
    "corrections_ignored": f_corrections_ignored,
    "requeue_turn": f_requeue_turn,
}


# ------------------------------------------------------------------ the case table
# (kind, category, seed, spec). Specs stay private to this module (not in CASES).
_TABLE = [
    # ---- honest nights
    ("clean", "clean-one-word", 101, dict(words=[TOM], n=10, style="syl")),
    ("clean", "clean-one-word", 102, dict(words=[DOB], n=11, style="long")),
    ("clean", "clean-one-word", 103, dict(words=[FOM], n=10, style="code", n_partial=2)),
    ("clean", "clean-one-word", 104, dict(words=[DOS], n=12, style="syl2", shuffle=True)),
    ("clean", "clean-sealed-slot", 105, dict(words=[MG], n=10, style="mixed", n_test=4)),
    ("clean", "clean-three-hop", 106, dict(words=[DMF], n=10, style="syl", n_partial=0)),
    ("clean", "clean-two-words", 107, dict(words=[BOS, TOF], n=10, style="syl")),
    ("clean", "clean-two-words", 108, dict(words=[MOS, BOM], n=10, style="long", n_test=2)),
    ("clean", "clean-prior-word", 109, dict(words=[TOF], pre=[BOF], n=11, style="syl2")),
    ("clean", "clean-prior-word", 110, dict(words=[DOB], pre=[DOS], n=10, style="syl")),
    ("clean", "clean-prior-word", 111, dict(words=[TOM], pre=[MG], n=12, style="code")),
    ("clean", "clean-big-world", 112, dict(words=[BOM], n=16, style="mixed", n_test=4,
                                          n_partial=3, bystanders=10,
                                          decoy=[(0, "father"), (1, "spouse")])),
    ("clean", "clean-corrections", 113, dict(words=[DOS], n=10, style="syl", corrections=2)),
    ("clean", "clean-corrections", 114, dict(words=[FOM], n=12, style="syl2",
                                            late_corrections=1)),
    ("clean", "clean-fillers", 115, dict(words=[BOF], n=10, style="long", fillers=4,
                                        shuffle=True)),
    ("clean", "clean-decoys", 116, dict(words=[TOS], n=10, style="syl", n_partial=2,
                                       partial_decoy="father", decoy=[(0, "father")])),
    ("clean", "clean-lookalike-names", 117, dict(words=[MOS], n=11, style="syl", twin=True)),
    ("clean", "clean-two-words", 118, dict(words=[DOB, TOM], n=10, style="syl2")),
    ("clean", "clean-prior-word", 119, dict(words=[BOS], pre=[TOF], n=10, style="mixed")),
    ("clean", "clean-big-world", 120, dict(words=[DMF], pre=[FOM], n=14, style="syl",
                                          bystanders=6, n_partial=2)),
    # ---- faulty nights
    ("fault", "silent-noop", 121, dict(words=[DOS], n=10, style="syl2", fault="key_as_label")),
    ("fault", "silent-noop", 122, dict(words=[TOM], n=11, style="long", fault="soft_logits")),
    ("fault", "silent-noop", 123, dict(words=[BOF], n=10, style="code",
                                       fault="ghost_reasoner")),
    ("fault", "post-sleep-people", 124, dict(words=[MG], n=10, style="syl",
                                             fault="bedtime_copy")),
    ("fault", "post-sleep-people", 125, dict(words=[FOM], n=10, style="syl2",
                                             fault="writes_to_scrap")),
    ("fault", "post-sleep-people", 126, dict(words=[TOS], n=10, style="long",
                                             fault="new_values_literal")),
    ("fault", "made-up-answer", 127, dict(words=[DMF], n=10, style="syl", fault="nearest_name")),
    ("fault", "made-up-answer", 128, dict(words=[TOM], n=10, style="syl", n_partial=2,
                                          partial_decoy="father", fault="relation_stand_in")),
    ("fault", "notebook-write", 129, dict(words=[DOB], n=10, style="mixed",
                                          fault="compile_rows")),
    ("fault", "notebook-write", 130, dict(words=[MOS], n=10, style="syl2", corrections=2,
                                          fault="replay_day")),
    ("fault", "forgetting", 131, dict(words=[TOF], pre=[BOS], n=10, style="syl",
                                      fault="file_keeps_tonight_only")),
    ("fault", "forgetting", 132, dict(words=[BOM], pre=[DOS], n=10, style="long",
                                      fault="prune_unasked")),
    ("fault", "file-live-mismatch", 133, dict(words=[DOB], n=11, style="code",
                                              fault="file_left_in_tmp")),
    ("fault", "file-live-mismatch", 134, dict(words=[MOS], n=10, style="syl",
                                              fault="live_rows_reversed")),
    ("fault", "minority-wrong", 135, dict(words=[BOS], n=10, style="syl", twin=True,
                                          fault="merge_lookalikes")),
    ("fault", "minority-wrong", 136, dict(words=[BOF], n=12, style="syl2", late_corrections=1,
                                          fault="episode_memory")),
    ("fault", "unlearned-word-answered", 137, dict(words=[DOB], n=10, style="syl",
                                                   fault="next_word_slot")),
    ("fault", "earlier-word-corrupted", 138, dict(words=[FOM], pre=[MG], n=10, style="syl",
                                                  pre_decoy=[(1, "father")],
                                                  fault="slot_collision")),
    ("fault", "corrections-ignored", 139, dict(words=[TOM], n=10, style="mixed",
                                               fault="corrections_ignored")),
    ("fault", "replays-old-turn", 140, dict(words=[DOS], n=10, style="syl", corrections=1,
                                            fault="requeue_turn")),
]

_order = list(range(len(_TABLE)))
random.Random("slp364b/ids/v1").shuffle(_order)
_SPECS: dict[str, dict] = {}
CASES: list[dict] = []
for _slot, _i in enumerate(_order):
    _kind, _cat, _seed, _spec = _TABLE[_i]
    _cid = f"slp364b-{_slot + 1:02d}"
    _spec = dict(_spec, id=_cid, seed=_seed)
    _SPECS[_cid] = _spec
    CASES.append({"id": _cid, "kind": _kind, "category": _cat, "seed": _seed,
                  "probes": make_probes(build_world(_spec))})
CASES.sort(key=lambda c: c["id"])
del _slot, _i, _kind, _cat, _seed, _spec, _cid

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


if __name__ == "__main__":
    for c in CASES:
        w = world_of(c)
        print(c["id"], c["kind"], c["category"], c["seed"], len(c["probes"]),
              [WORDS[x] for x in w["words"]], "pre", [WORDS[x] for x in w["pre"]],
              "eps", w["n_episodes"], "turns", len(w["turns"]))
