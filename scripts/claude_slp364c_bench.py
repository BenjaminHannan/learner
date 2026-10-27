#!/usr/bin/env python3
"""slp-364c blind test bench: 20 honest sleeps and 20 faulty sleeps (third, independent set).

Same interface as scripts/claude_slp364_bench.py and scripts/claude_slp364b_bench.py:

    CASES                    40 dicts {"id", "kind" ("fault"|"clean"), "category", "seed", "probes"}
    run_case(case, state_dir) -> loop

run_case builds a fresh loop in state_dir with the slp-360 builder (claude_slp360_test.build,
arm "P": scrap layer on), teaches that case's invented world, asks the questions that queue the
sleep's learning episodes (>= 10 per learned word), and returns the loop JUST BEFORE the sleep.
The caller runs one sleep (claude_slp360_test.force_sleep).

Every case, clean or faulty, gets the SAME pass-through frame: instance-level wrappers on the
sleeper (sleep, _run_exp46, _commit_installs, _commit_one), the reasoner (answer) and the ears
(hear). Each wrapper runs an empty list of "around" hooks on a clean case and so changes
nothing. A fault case registers hooks in those lists; nothing else in the object layout
differs, and no file in the tree is edited. A fault acts only during or after the sleep (the
setup replies are identical with the fault on or off).

"probes" lists what a user might say after the sleep, in order: questions about the day's
people, a question about someone not yet met, teaches of new people and questions about them,
a correction of a day person ("Actually, X's R is Y."), a new person taught and then corrected,
and questions after each. For reporting; probe_plan() gives the expected replies.

Worlds: every name is invented (six name styles), world sizes vary (10-16 learning chains per
word, 2-4 unasked chains, 0-3 half-taught chains, optional bystander families, decoy relations,
direct teaches of a compound word, repeated questions), and the words are spread over all 12 of
fable_sleep130_agent.WORDS130. Some cases boot with an earlier word already installed (written
to sleep145-words.json before the build, in the form an earlier sleep leaves it). Seeds and case
ids are both assigned over fixed shuffles, so neither reveals the kind.

Bench validation (not judging): scripts/claude_slp364c_bench_check.py.
"""

from __future__ import annotations

import copy
import difflib
import functools
import json
import os
import random
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

FILLERS = ["Hi there!", "Thanks so much.", "Good afternoon!", "Hello!",
           "Thank you very much!", "How is it going?"]

# A phrase one word away from each compound word that is NOT a word the loop knows.
NEAR = {
    MG: "paternal grandmother", BOS: "boss of cousin", DMF: "doctor of fathers friend",
    BOF: "boss of uncle", TOS: "teacher of cousin", MOS: "mother of cousin",
    BOM: "boss of aunt", TOF: "teacher of uncle", DOS: "doctor of cousin",
    FOM: "father of aunt", DOB: "doctor of coach", TOM: "teacher of aunt",
}


# ------------------------------------------------------------------ names
_ONS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "h", "j", "w",
        "br", "dr", "gr", "kr", "tr", "pl", "gl", "fr", "sk", "st", "th", "sh", "ch"]
_MID = ["l", "m", "n", "r", "t", "v", "d", "k", "z", "b", "g", "p", "sh", "nd", "rl", "lv"]
_DBL = ["ll", "rr", "ss", "nn", "tt", "mm", "dd", "kk"]
_VOW = "aeiou"
_END = ["n", "r", "l", "k", "m", "x", "th", "nd", "sk"]
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
""".split())
_STOP = {"who", "what", "is", "the", "and", "mother", "father", "spouse", "boss", "doctor",
         "teacher", "friend", "best", "name", "called", "sleep", "neighbour", "maternal",
         "grandmother", "paternal", "hello", "thanks", "thank", "you", "actually", "know", "not",
         "yes", "no", "hi", "hey", "bye", "good", "morning", "evening", "afternoon", "okay",
         "sure", "tell", "about", "uncle", "aunt", "cousin", "coach", "much", "very", "there",
         "going", "night"}
STYLES = ("syl", "syl2", "long", "code", "mixed", "dbl")


class Names:
    """Unique invented names for one world.

    syl  = CVCVC (Tavolin-like)      syl2 = CVCV (Pelo)          long = CVCVCVC (Maredokin)
    code = Letter+letter+2 digits    dbl  = CVCCV(C) (Kessan)    mixed = syl/syl2/long/dbl
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
                style = self.rng.choice(("syl", "syl2", "long", "dbl"))
            s = self._word(style)
            if not self.taken(s):
                return self.claim(s)
        raise RuntimeError("name pool exhausted")

    def variant(self, name: str) -> str:
        """A new name one letter away from `name` (same length): the first vowel changed."""
        idx = [i for i, ch in enumerate(name) if ch.lower() in _VOW]
        for i in idx:
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


def _other_word(world: dict) -> int:
    """A word nobody taught or installed: one sharing w0's first hop if there is one."""
    busy = set(world["words"]) | set(world["pre"])
    w0 = world["words"][0]
    free = [(w0 + k) % 12 for k in range(1, 12) if (w0 + k) % 12 not in busy]
    same = [w for w in free if CHAINS[w][0] == CHAINS[w0][0]]
    return (same or free)[0]


# ------------------------------------------------------------------ worlds
def build_world(spec: dict) -> dict:
    """Deterministic world for one case spec: names, day turns, truth, post-sleep people."""
    rng = random.Random(f"slp364c/world/{spec['seed']}/{spec['style']}/{spec['words']}")
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
        old = chains[w0]["test"][0][0]
        new = nm.variant(chains[w0]["train"][0][0])
        facts[:] = [((new if a == old else a), r, (new if b == old else b)) for a, r, b in facts]
        chains[w0]["test"][0][0] = new
    for pos, rel in spec.get("decoy", []):          # extra relation on w0 chains
        for ch in chains[w0]["train"] + chains[w0]["test"]:
            facts.append((ch[pos], rel, nm.new()))
    for pos, rel in spec.get("pre_decoy", []):
        for w in pre:
            for ch in chains[w]["test"]:
                facts.append((ch[pos], rel, nm.new()))
    by_rels = [r for r in RELS if r != "neighbour"]
    for _ in range(spec.get("bystanders", 0)):       # unrelated families
        a, b, c = nm.new(), nm.new(), nm.new()
        r1, r2 = rng.sample(by_rels, 2)
        facts.append((a, r1, b))
        facts.append((b, r2, c))
    order = list(facts)
    if spec.get("shuffle"):
        rng.shuffle(order)
    truth = {(a, rel): b for a, rel, b in facts}

    # direct teaches of the compound word itself (unasked test chains; a different person)
    direct: dict = {}
    for k in range(spec.get("direct", 0)):
        ch = chains[w0]["test"][k]
        direct[(ch[0], w0)] = nm.new()
    # in-day corrections: a wrong first hop taught first, fixed before the questions
    early: dict = {}
    for k in range(spec.get("corrections", 0)):
        ch = chains[w0]["train"][k]
        early[(ch[0], CHAINS[w0][0])] = nm.new()
    # late corrections: a wrong first hop into ANOTHER full chain, fixed after the questions
    late: dict = {}
    tr = chains[w0]["train"]
    n_early = spec.get("corrections", 0)
    for k in range(spec.get("late_corrections", 0)):
        ch = tr[n_early + k]
        late[(ch[0], CHAINS[w0][0])] = tr[len(tr) - 1 - k][1]

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
    episodes = []
    for w in words:
        for ch in chains[w]["train"]:
            episodes.append(_word_q(ch[0], w))
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

    outsiders = [nm.new(), nm.new()]
    L = len(CHAINS[w0]) + 1
    post = {"p": [nm.new() for _ in range(L)], "q": [nm.new() for _ in range(L)],
            "z": nm.new()}
    n_eps = {WORDS[w]: len(chains[w]["train"]) + sum(
        1 for t in episodes[:spec.get("repeat_q", 0)] if t.endswith(f"{ASK[WORDS[w]]}?"))
        for w in words}
    return {"spec": spec, "words": words, "pre": pre, "chains": chains, "truth": truth,
            "direct": direct, "turns": turns, "outsiders": outsiders, "post": post,
            "early": early, "late": late, "n_episodes": n_eps, "other": None}


# ------------------------------------------------------------------ expectations
def _state0(world: dict) -> dict:
    return {"truth": dict(world["truth"]), "direct": dict(world["direct"]),
            "installed": set(world["words"]) | set(world["pre"])}


def _expect_hop(state: dict, a: str, rel: str):
    return state["truth"].get((a, rel))


def _expect_word(state: dict, a: str, w: int):
    if (a, w) in state["direct"]:
        return state["direct"][(a, w)]
    if w not in state["installed"]:
        return None
    cur = a
    for rel in CHAINS[w]:
        cur = state["truth"].get((cur, rel))
        if cur is None:
            return None
    return cur


def _apply(state: dict, a: str, rel: str, b: str) -> None:
    state["truth"][(a, rel)] = b


def _q(state, text, kind, a, rel=None, w=None):
    exp = _expect_word(state, a, w) if w is not None else _expect_hop(state, a, rel)
    return (text, exp, kind, a, rel, w)


def _plan(world: dict) -> tuple[list, dict]:
    """[(text, expect, kind, name, rel, word)] for every probe, in order, and the final state.

    kind: word / hop / partial / reverse / outsider / unlearned / nearmiss / pre-teach /
    teach / post-word / post-hop / fix / fix-word / fix-hop / fix2-word / fix2-hop / reask.
    Expectations are the reply an honest loop gives AT THAT POINT (teaches/fixes applied).
    """
    st = _state0(world)
    out: list = []
    w0 = world["words"][0]
    c0 = world["chains"][w0]
    r0 = CHAINS[w0][0]
    for w in world["words"]:
        c = world["chains"][w]
        for ch in c["train"][:2] + c["test"]:
            out.append(_q(st, _word_q(ch[0], w), "word", ch[0], w=w))
        for ch in c["partial"][:1]:
            out.append(_q(st, _word_q(ch[0], w), "partial", ch[0], w=w))
    for w in world["pre"]:
        for ch in world["chains"][w]["test"][:3]:
            out.append(_q(st, _word_q(ch[0], w), "word", ch[0], w=w))
    hops = [(c0["train"][0][0], r0), (c0["train"][1][1], CHAINS[w0][1]),
            (c0["test"][0][0], r0)]
    for key in list(world["early"]) + list(world["late"]):
        if key not in hops:
            hops.append(key)
    for a, rel in hops:
        out.append(_q(st, _hop_q(a, rel), "hop", a, rel=rel))
    for ch in c0["partial"][:1]:
        rel = CHAINS[w0][len(ch) - 1]
        out.append(_q(st, _hop_q(ch[-1], rel), "partial", ch[-1], rel=rel))
    b = c0["train"][0][1]
    out.append(_q(st, _hop_q(b, r0), "reverse", b, rel=r0))
    o0, o1 = world["outsiders"]
    out.append(_q(st, _word_q(o0, w0), "outsider", o0, w=w0))
    out.append(_q(st, _hop_q(o1, "mother"), "outsider", o1, rel="mother"))
    ow = _other_word(world)
    a0 = c0["train"][0][0]
    out.append(_q(st, _word_q(a0, ow), "unlearned", a0, w=ow))
    out.append((f"Who is {a0}'s {NEAR[w0]}?", None, "nearmiss", a0, None, None))
    # someone not met yet, then taught, then asked again
    p = world["post"]["p"]
    out.append(_q(st, _hop_q(p[0], r0), "pre-teach", p[0], rel=r0))
    for k, rel in enumerate(CHAINS[w0]):
        out.append((_teach_text(p[k], rel, p[k + 1]), None, "teach", p[k], rel, None))
        _apply(st, p[k], rel, p[k + 1])
    out.append(_q(st, _word_q(p[0], w0), "post-word", p[0], w=w0))
    out.append(_q(st, _hop_q(p[0], r0), "post-hop", p[0], rel=r0))
    # correction of a day person
    a, other = c0["train"][0], c0["train"][1]
    out.append((_fix_text(a[0], r0, other[1]), None, "fix", a[0], r0, None))
    _apply(st, a[0], r0, other[1])
    out.append(_q(st, _word_q(a[0], w0), "fix-word", a[0], w=w0))
    out.append(_q(st, _hop_q(a[0], r0), "fix-hop", a[0], rel=r0))
    # a new person taught, then corrected at the last hop
    q, z = world["post"]["q"], world["post"]["z"]
    for k, rel in enumerate(CHAINS[w0]):
        out.append((_teach_text(q[k], rel, q[k + 1]), None, "teach", q[k], rel, None))
        _apply(st, q[k], rel, q[k + 1])
    last = CHAINS[w0][-1]
    out.append((_fix_text(q[-2], last, z), None, "fix", q[-2], last, None))
    _apply(st, q[-2], last, z)
    out.append(_q(st, _word_q(q[0], w0), "fix2-word", q[0], w=w0))
    out.append(_q(st, _hop_q(q[-2], last), "fix2-hop", q[-2], rel=last))
    t = c0["test"][-1][0]
    out.append(_q(st, _word_q(t, w0), "reask", t, w=w0))
    return out, st


def probe_plan(world: dict) -> list[tuple[str, str | None, str]]:
    """(text, expected answer or None (= must abstain), kind) for every probe, in order."""
    return [(t, e, k) for t, e, k, *_ in _plan(world)[0]]


def make_probes(world: dict) -> list[str]:
    return [t for t, _e, _k in probe_plan(world)]


def _question_set(world: dict, st: dict) -> list[tuple[str, str | None, str]]:
    out: list = []
    for (a, rel), _b in sorted(st["truth"].items()):
        out.append((_hop_q(a, rel), _expect_hop(st, a, rel), "hop"))
    for w in world["words"] + world["pre"]:
        c = world["chains"][w]
        for ch in c["train"] + c["test"]:
            out.append((_word_q(ch[0], w), _expect_word(st, ch[0], w), "word"))
        for ch in c["partial"]:
            out.append((_word_q(ch[0], w), _expect_word(st, ch[0], w), "partial"))
    for o in world["outsiders"]:
        out.append((_word_q(o, world["words"][0]), None, "outsider"))
        out.append((_hop_q(o, "father"), None, "outsider"))
    return out


def question_set(world: dict) -> list[tuple[str, str | None, str]]:
    """Wider question-only set about the day's world (asked right after the sleep)."""
    return _question_set(world, _state0(world))


def restart_plan(world: dict) -> list[tuple[str, str | None, str]]:
    """Questions for a loop rebuilt from the state folder after all probes (final state)."""
    plan, st = _plan(world)
    out = _question_set(world, st)
    for text, _e, kind, a, rel, w in plan:
        if kind in ("teach", "fix"):
            continue
        if kind == "nearmiss":
            out.append((text, None, kind))
        elif w is not None:
            out.append((text, _expect_word(st, a, w), kind))
        else:
            out.append((text, _expect_hop(st, a, rel), kind))
    return out


# ------------------------------------------------------------------ helpers on a built loop
def _inner_nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def _eid(nb, name: str):
    found = nb.resolve(name)
    return found.detail["entity_id"] if found.status == C.OK else None


def _qeid(question: dict, nb):
    return question.get("entity_id") or _eid(nb, str(question.get("name", "")))


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


def _walk(nb, start: str, chain):
    cur = start
    for rel in chain:
        rows = nb.current(cur, rel)
        if not rows or "entity" not in rows[0]["value"]:
            return None
        cur = rows[0]["value"]["entity"]
    return cur


def _word_of(question: dict, loop):
    """Index of an installed word asked as a bare single relation, else None."""
    w = _single(question)
    if w in WORDS and not question.get("qualifiers") and w in _live(loop):
        return WORDS.index(w)
    return None


# ------------------------------------------------------------------ the frame
_POINTS = ("sleep", "recipe", "commit_all", "commit_one", "answer", "hear")


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


def _capture_episodes(loop, st):
    def before(experience):
        st["eps"] = [dict(e) for e in loop.reasoner.episodes]
        st["prior_live"] = sorted(k for k in _live(loop) if k in WORDS)
    return before


# ------------------------------------------------------------------ the faults
# Each takes (loop, world, st) and registers hooks on the frame.

def f_episode_dedupe(loop, world, st):
    """The queue is de-duplicated by word instead of by (person, word): one episode per word
    reaches the recipe, which keeps it queued as too few; nothing is learned."""
    def around(inner, notebook):
        eps = loop.reasoner.episodes
        seen, kept = set(), []
        for ep in eps:
            if ep["word_name"] not in seen:
                seen.add(ep["word_name"])
                kept.append(ep)
        eps[:] = kept
        return inner(notebook)
    st["around"]["recipe"].append(around)


def f_audit_off_by_one(loop, world, st):
    """The bridge audits each trained word against the NEXT word's chain, so every good install
    is rejected at the bridge (nothing reaches serving or the word file)."""
    def around(inner, notebook, rec, w, wname, merged):
        if S130.check_word_logits130(_hard_logits(CHAINS[w]), w + 1):
            return inner(notebook, rec, w, wname, merged)
        return {"bridged": False, "reason": "logits fail the chain audit"}
    st["around"]["commit_one"].append(around)


def f_answer_memo(loop, world, st):
    """After the sleep, a warmed answer cache serves repeated questions and is never
    invalidated by later teaches or corrections."""
    memo: dict = {}

    def around(inner, question, notebook):
        if not st["armed"]:
            return inner(question, notebook)
        key = (str(question.get("name", "")).lower(), tuple(question.get("relations") or []),
               question.get("entity_id"), repr(question.get("qualifiers")))
        if key in memo:
            return copy.deepcopy(memo[key])
        rec = inner(question, notebook)
        memo[key] = copy.deepcopy(rec)
        return rec
    st["around"]["answer"].append(around)


def f_correction_as_teach(loop, world, st):
    """After the sleep, the ears' refreshed phrase table drops the correction flag: 'Actually,
    X's R is Y.' is heard as a plain teach (a conflict question instead of an update)."""
    def around(inner, turn):
        actions = inner(turn)
        if st["armed"]:
            for act in actions:
                if isinstance(act, dict) and act.get("act") == "correct":
                    act["act"] = "teach"
        return actions
    st["around"]["hear"].append(around)


def f_missing_hop_keep(loop, world, st):
    """After the sleep, a learned word whose chain is missing a hop treats that stage as 'keep'
    and answers with the last person it reached."""
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
        cur, walked = eid, 0
        for rel in CHAINS[w]:
            rows = nb.current(cur, rel)
            if rows and "entity" in rows[0]["value"]:
                cur = rows[0]["value"]["entity"]
                walked += 1
        if walked and cur != eid:
            return _ok(question, nb.entities[cur], source="sleep-derived")
        return rec
    st["around"]["answer"].append(around)


def f_fuzzy_word(loop, world, st):
    """After the sleep, an unknown relation phrase is snapped to the most similar installed word
    (string similarity) and answered with it."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        r = _single(question)
        nb = _inner_nb(loop)
        if r is None or r in WORDS or nb.known_relation(r):
            return rec
        cands = sorted(k for k in _live(loop) if k in WORDS)
        if not cands:
            return rec
        best = max(cands, key=lambda k: (difflib.SequenceMatcher(None, r, k).ratio(), k))
        if difflib.SequenceMatcher(None, r, best).ratio() < 0.6:
            return rec
        rec2 = inner(dict(question, relations=[best]), notebook)
        if rec2.get("status") == C.OK:
            rec2 = dict(rec2, relations=list(question.get("relations") or []))
            return rec2
        return rec
    st["around"]["answer"].append(around)


def f_symmetric_rows(loop, world, st):
    """The sleep 'completes' symmetric relations: for every taught spouse / best friend /
    neighbour row it writes the reverse row into the main notebook as taught."""
    def after(out, experience):
        nb = _inner_nb(loop)
        for fid, f in sorted(nb.facts.items()):
            if (f.get("source") == "taught" and nb.active(fid)
                    and f["relation"] in ("spouse", "best_friend", "neighbour")
                    and "entity" in f["value"]):
                other = f["value"]["entity"]
                if not nb.current(other, f["relation"]):
                    _raw_assert(loop, f"s364c-sym-{fid}", "listening", "taught", other,
                                f["relation"], {"entity": f["subject"]}, raw=f"symmetric {fid}")
    _around_sleep(st, after=after)


def f_duplicate_people(loop, world, st):
    """The sleep re-registers the people from its last episodes as NEW people with the same
    name (it creates a person record instead of looking the name up)."""
    def after(out, experience):
        starts = []
        for ep in st.get("eps", []):
            if ep["start"] not in starts:
                starts.append(ep["start"])
        nb = _inner_nb(loop)
        for eid in starts[-3:]:
            loop.nb.new_entity(f"s364c-dup-{eid}", nb.entities[eid])
    _around_sleep(st, before=_capture_episodes(loop, st), after=after)


def f_disk_only_retract(loop, world, st):
    """The sleep 'consolidates' each episode's first hop into the learned word by appending a
    retraction to the notebook FILE (write-ahead) without applying it in memory."""
    def after(out, experience):
        nb = _inner_nb(loop)
        done = set()
        for ep in st.get("eps", []):
            rel0 = CHAINS[int(ep["word"])][0]
            rows = [r for r in nb.current(ep["start"], rel0) if r.get("source") == "taught"]
            if not rows or rows[0]["fact_id"] in done:
                continue
            fid = rows[0]["fact_id"]
            done.add(fid)
            event = {"kind": "RETRACT", "event_id": f"s364c-tidy-{fid}", "fact_id": fid,
                     "actor": "sleep", "reason": "consolidated into a learned word",
                     "n": len(nb.events) + 1, "prev": nb.last_sha, "v": C.FORMAT_VERSION}
            line = json.dumps(event, sort_keys=True, ensure_ascii=False)
            with open(nb.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            nb.events.append(event)
            nb.event_ids.add(event["event_id"])
            nb.last_sha = C._sha(line)
    _around_sleep(st, before=_capture_episodes(loop, st), after=after)


def f_slot_truncate(loop, world, st):
    """After growing the table for tonight's word, the table is cut to that slot count: every
    installed word with a higher slot index is dropped (live and word file)."""
    def around(inner, notebook, recipe):
        out = inner(notebook, recipe)
        got = [w for w, b in (out or {}).items() if b.get("bridged")]
        if not got:
            return out
        top = max(WORDS.index(w) for w in got)
        live = _live(loop)
        drop = [k for k in list(live) if k in WORDS and WORDS.index(k) > top and k not in out]
        if drop:
            for k in drop:
                live.pop(k, None)
            data = _read_words_file(loop)
            for k in drop:
                data.get("words", {}).pop(k, None)
            _write_json_atomic(Path(loop.sleeper.word_path), data)
        return out
    st["around"]["commit_all"].append(around)


def f_superseded_route(loop, world, st):
    """After the sleep, the learned word walks each hop through the OLDEST taught row ever
    written for it (superseded rows included), so corrected people get the old chain."""
    def oldest(nb, subj, rel):
        rows = [nb.facts[f] for f in nb._sr.get((subj, rel), ())
                if nb.facts[f].get("source") == "taught" and f not in nb.retracted
                and "entity" in nb.facts[f]["value"]]
        if not rows:
            return None
        return min(rows, key=lambda f: f["n"])["value"]["entity"]

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        if w is None:
            return rec
        nb = _inner_nb(loop)
        cur = _qeid(question, nb)
        for rel in CHAINS[w]:
            if cur is None:
                break
            cur = oldest(nb, cur, rel)
        ans = (rec.get("fields") or {}).get("answer")
        if cur is not None and nb.entities.get(cur) != ans:
            return _ok(question, nb.entities[cur], (rec.get("fields") or {}).get("trail", []),
                       (rec.get("fields") or {}).get("source", "sleep-derived"))
        return rec
    st["around"]["answer"].append(around)


def f_batch_tail(loop, world, st):
    """At wake the sleep precomputes the new word's answer for everyone in batches of 8; the
    last, partial batch is read one row late (its answers are shifted by one person)."""
    def after(out, experience):
        nb = _inner_nb(loop)
        table = {}
        for wname in _bridged(out):
            w = WORDS.index(wname)
            starts, answers = [], []
            for eid in sorted(nb.entities):
                end = _walk(nb, eid, CHAINS[w])
                if end is not None:
                    starts.append(eid)
                    answers.append(end)
            tail = len(answers) % 8
            if tail >= 2:
                seg = answers[-tail:]
                answers[-tail:] = seg[1:] + seg[:1]
            table[wname] = dict(zip(starts, answers))
        st["table"] = table
    _around_sleep(st, after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        tab = st.get("table", {}).get(WORDS[w]) if w is not None else None
        if not tab:
            return rec
        nb = _inner_nb(loop)
        eid = _qeid(question, nb)
        if eid in tab:
            f = rec.get("fields") or {}
            return _ok(question, nb.entities[tab[eid]], f.get("trail", []),
                       f.get("source", "sleep-derived"))
        return rec
    st["around"]["answer"].append(around)


def f_file_last_word(loop, world, st):
    """With two words in one night, each word's commit starts from a fresh copy of the file's
    earlier contents, so the file keeps only the LAST word of the night (live keeps both)."""
    done: list = []

    def around(inner, notebook, rec, w, wname, merged):
        for prev in done:
            merged.pop(prev, None)
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged"):
            done.append(wname)
        return out
    st["around"]["commit_one"].append(around)


def f_live_neighbour_slot(loop, world, st):
    """The bridge copies the neighbouring slot of the grown table (index w-1) into serving; the
    word file gets the right logits."""
    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged") and w >= 1:
            _live(loop)[wname] = _hard_logits(CHAINS[w - 1])
        return out
    st["around"]["commit_one"].append(around)


def f_route_beats_taught(loop, world, st):
    """After the sleep, the learned route is consulted before a row the user taught for the
    compound word itself (taught-beats-sleep order inverted)."""
    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        if w is None or (rec.get("fields") or {}).get("source") != "taught":
            return rec
        nb = _inner_nb(loop)
        eid = _qeid(question, nb)
        end = _walk(nb, eid, CHAINS[w]) if eid else None
        if end is not None and nb.entities[end] != rec["fields"].get("answer"):
            return _ok(question, nb.entities[end], source="sleep-derived")
        return rec
    st["around"]["answer"].append(around)


def f_skill_roll(loop, world, st):
    """The bridge re-indexes the trained stage rows as if column 0 were not 'keep': every skill
    moves one column up (live and word file)."""
    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged"):
            rows = _live(loop)[wname]
            rolled = [[row[(i - 1) % 9] for i in range(9)] for row in rows]
            _live(loop)[wname] = rolled
            if wname in merged:
                merged[wname] = dict(merged[wname], logits=[r[:] for r in rolled])
        return out
    st["around"]["commit_one"].append(around)


def f_sibling_copy(loop, world, st):
    """The bridge also registers the learned route, as a warm start, under every uninstalled
    word that shares its first hop (serving only)."""
    def around(inner, notebook, rec, w, wname, merged):
        out = inner(notebook, rec, w, wname, merged)
        if out.get("bridged"):
            live = _live(loop)
            for s, ch in zip(WORDS, CHAINS):
                if s != wname and s not in live and ch[0] == CHAINS[w][0]:
                    live[s] = [r[:] for r in live[wname]]
        return out
    st["around"]["commit_one"].append(around)


def f_fold_quarantine(loop, world, st):
    """After the sleep, people who sat in the recipe's first validation fold are marked
    'unreliable' for the new word and get 'I don't know'."""
    def after(out, experience):
        q = {}
        for wname in _bridged(out):
            people = sorted({e["start"] for e in st.get("eps", []) if e["word_name"] == wname})
            random.Random(f"fold/{wname}/{loop.sleeper.seed}").shuffle(people)
            q[wname] = {p for i, p in enumerate(people) if i % 4 == 0}
        st["quarantine"] = q
    _around_sleep(st, before=_capture_episodes(loop, st), after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.OK:
            return rec
        w = _word_of(question, loop)
        if w is None:
            return rec
        nb = _inner_nb(loop)
        eid = _qeid(question, nb)
        if eid in st.get("quarantine", {}).get(WORDS[w], set()):
            name = question.get("name", "")
            return {"kind": "answer", "status": C.MISSING_FACT, "name": name,
                    "relations": list(question.get("relations") or []),
                    "fields": {"subject": name, "relation": WORDS[w], "hop": 1, "trail": []}}
        return rec
    st["around"]["answer"].append(around)


def f_prior_row_shift(loop, world, st):
    """After the commit, the earlier installed words are re-serialized from the stage buffer
    one row late (first stage lost, 'keep' appended), live and in the word file."""
    _around_sleep(st, before=_capture_episodes(loop, st))

    def around(inner, notebook, recipe):
        out = inner(notebook, recipe)
        if not out:
            return out
        live = _live(loop)
        data = _read_words_file(loop)
        changed = False
        for p in st.get("prior_live", []):
            if p in out or p not in live:
                continue
            new = [r[:] for r in live[p][1:]] + [list(KEEP_ROW)]
            live[p] = new
            if p in data.get("words", {}):
                data["words"][p] = dict(data["words"][p], logits=[r[:] for r in new])
                changed = True
        if changed:
            _write_json_atomic(Path(loop.sleeper.word_path), data)
        return out
    st["around"]["commit_all"].append(around)


def f_scrap_fallback(loop, world, st):
    """The sleep writes guesses for missing last hops into the scrap layer, and after the sleep
    the reasoner falls back to scrap rows when the notebook has no answer."""
    def after(out, experience):
        nb = _inner_nb(loop)
        pool = [e["answer"] for e in st.get("eps", [])]
        if not pool:
            return
        for wname in _bridged(out):
            chain = CHAINS[WORDS.index(wname)]
            for eid in sorted(nb.entities):
                cur = _walk(nb, eid, chain[:-1]) if len(chain) > 1 else eid
                if cur is None or nb.current(cur, chain[-1]):
                    continue
                guess = pool[sum(map(ord, cur)) % len(pool)]
                if guess == cur:
                    continue
                loop.scrap360.fact(f"s364c-guess-{cur}-{chain[-1]}", "sleep", "sleep-derived",
                                   cur, chain[-1], {"entity": guess}, nb.entities[cur],
                                   raw="missing hop guessed at sleep")
    _around_sleep(st, before=_capture_episodes(loop, st), after=after)

    def around(inner, question, notebook):
        rec = inner(question, notebook)
        if not st["armed"] or rec.get("status") != C.MISSING_FACT:
            return rec
        f = rec.get("fields") or {}
        rel, subj = f.get("relation"), f.get("subject")
        if not rel or not subj:
            return rec
        w = _word_of(question, loop)
        last = CHAINS[w][-1] if w is not None else _single(question)
        if rel != last:
            return rec
        nb = _inner_nb(loop)
        eid = _eid(nb, subj)
        rows = [r for r in loop.scrap360.rows if r.get("kind") == "FACT"
                and r.get("subject") == eid and r.get("relation") == rel
                and "entity" in (r.get("value") or {})]
        if eid is None or not rows:
            return rec
        return _ok(question, nb.entities[rows[-1]["value"]["entity"]], source="sleep-derived")
    st["around"]["answer"].append(around)


FAULTS = {
    "episode_dedupe": f_episode_dedupe,
    "audit_off_by_one": f_audit_off_by_one,
    "answer_memo": f_answer_memo,
    "correction_as_teach": f_correction_as_teach,
    "missing_hop_keep": f_missing_hop_keep,
    "fuzzy_word": f_fuzzy_word,
    "symmetric_rows": f_symmetric_rows,
    "duplicate_people": f_duplicate_people,
    "disk_only_retract": f_disk_only_retract,
    "slot_truncate": f_slot_truncate,
    "superseded_route": f_superseded_route,
    "batch_tail": f_batch_tail,
    "file_last_word": f_file_last_word,
    "live_neighbour_slot": f_live_neighbour_slot,
    "route_beats_taught": f_route_beats_taught,
    "skill_roll": f_skill_roll,
    "sibling_copy": f_sibling_copy,
    "fold_quarantine": f_fold_quarantine,
    "prior_row_shift": f_prior_row_shift,
    "scrap_fallback": f_scrap_fallback,
}


# ------------------------------------------------------------------ the case table
# (kind, category, spec). Seeds 201-240 are dealt over a fixed shuffle; specs stay private.
_TABLE = [
    # ---- honest nights
    ("clean", "clean-one-word", dict(words=[MG], n=10, style="syl")),
    ("clean", "clean-one-word", dict(words=[BOS], n=11, style="code", n_partial=2)),
    ("clean", "clean-three-hop", dict(words=[DMF], n=10, style="long")),
    ("clean", "clean-one-word", dict(words=[BOF], n=10, style="dbl", shuffle=True)),
    ("clean", "clean-decoys", dict(words=[TOS], n=12, style="syl2", decoy=[(0, "teacher")])),
    ("clean", "clean-fillers", dict(words=[MOS], n=10, style="mixed", fillers=3,
                                    shuffle_q=True)),
    ("clean", "clean-corrections", dict(words=[BOM], n=10, style="syl", corrections=2)),
    ("clean", "clean-corrections", dict(words=[TOF], n=12, style="code", late_corrections=1)),
    ("clean", "clean-direct-word", dict(words=[DOS], n=10, style="long", direct=2)),
    ("clean", "clean-lookalike-names", dict(words=[FOM], n=11, style="syl2", twin=True)),
    ("clean", "clean-big-world", dict(words=[DOB], n=10, style="syl", bystanders=8,
                                      n_partial=0)),
    ("clean", "clean-repeat-questions", dict(words=[TOM], n=10, style="dbl", repeat_q=4)),
    ("clean", "clean-two-words", dict(words=[MG, TOS], n=10, style="syl")),
    ("clean", "clean-two-words", dict(words=[FOM, DOB], n=10, style="mixed", n_test=2)),
    ("clean", "clean-prior-word", dict(words=[TOF], pre=[DOS], n=10, style="syl2")),
    ("clean", "clean-prior-word", dict(words=[MG], pre=[TOM], n=11, style="code")),
    ("clean", "clean-prior-word", dict(words=[DOB], pre=[BOF], n=10, style="long",
                                       pre_decoy=[(0, "boss")])),
    ("clean", "clean-big-world", dict(words=[BOM], n=16, style="mixed", n_test=4, n_partial=3,
                                      bystanders=10, decoy=[(0, "father"), (1, "spouse")],
                                      shuffle=True)),
    ("clean", "clean-prior-two-words", dict(words=[BOS, MOS], pre=[DMF], n=10, style="dbl")),
    ("clean", "clean-mixed-shape", dict(words=[TOM], n=12, style="syl", corrections=1,
                                        late_corrections=1, direct=1, n_partial=2)),
    # ---- faulty nights
    ("fault", "silent-noop", dict(words=[TOS], n=10, style="syl", fault="episode_dedupe")),
    ("fault", "silent-noop", dict(words=[DMF], n=10, style="long", fault="audit_off_by_one")),
    ("fault", "post-sleep-teaching", dict(words=[FOM], n=10, style="code",
                                          fault="answer_memo")),
    ("fault", "post-sleep-teaching", dict(words=[BOS], n=10, style="syl2",
                                          fault="correction_as_teach")),
    ("fault", "made-up-answer", dict(words=[BOM], n=10, style="syl", n_partial=2,
                                     fault="missing_hop_keep")),
    ("fault", "made-up-answer", dict(words=[MG], n=11, style="mixed", fault="fuzzy_word")),
    ("fault", "notebook-write", dict(words=[DOS], n=10, style="dbl", fault="symmetric_rows")),
    ("fault", "notebook-write", dict(words=[TOF], n=10, style="syl",
                                     fault="duplicate_people")),
    ("fault", "forgetting", dict(words=[DOB], n=10, style="syl2", fault="disk_only_retract")),
    ("fault", "forgetting", dict(words=[FOM], pre=[TOM], n=10, style="long",
                                 fault="slot_truncate")),
    ("fault", "minority-wrong", dict(words=[MOS], n=14, style="syl", late_corrections=2,
                                     fault="superseded_route")),
    ("fault", "minority-wrong", dict(words=[BOF], n=10, style="code", fault="batch_tail")),
    ("fault", "file-live-mismatch", dict(words=[MG, DOB], n=10, style="syl",
                                         fault="file_last_word")),
    ("fault", "file-live-mismatch", dict(words=[MOS], n=10, style="syl2",
                                         fault="live_neighbour_slot")),
    ("fault", "taught-overridden", dict(words=[TOM], n=10, style="mixed", direct=2,
                                        fault="route_beats_taught")),
    ("fault", "wrong-route", dict(words=[BOS], n=11, style="long", fault="skill_roll")),
    ("fault", "unasked-word-answered", dict(words=[TOF], n=10, style="syl2",
                                            fault="sibling_copy")),
    ("fault", "over-abstain", dict(words=[DOS], n=12, style="code", fault="fold_quarantine")),
    ("fault", "earlier-word-corrupted", dict(words=[BOM], pre=[TOS], n=10, style="syl",
                                             fault="prior_row_shift")),
    ("fault", "scrap-answers", dict(words=[DMF], n=10, style="dbl", n_partial=2,
                                    fault="scrap_fallback")),
]

_seeds = list(range(201, 201 + len(_TABLE)))
random.Random("slp364c/seeds/v1").shuffle(_seeds)
_order = list(range(len(_TABLE)))
random.Random("slp364c/ids/v1").shuffle(_order)
_SPECS: dict[str, dict] = {}
CASES: list[dict] = []
for _slot, _i in enumerate(_order):
    _kind, _cat, _spec = _TABLE[_i]
    _cid = f"slp364c-{_slot + 1:02d}"
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


if __name__ == "__main__":
    for c in CASES:
        w = world_of(c)
        print(c["id"], c["kind"], c["category"], c["seed"], len(c["probes"]),
              [WORDS[x] for x in w["words"]], "pre", [WORDS[x] for x in w["pre"]],
              "eps", w["n_episodes"], "turns", len(w["turns"]), _SPECS[c["id"]]["style"])
