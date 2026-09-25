#!/usr/bin/env python3
"""slp-364 blind test bench: 20 honest sleeps and 20 faulty sleeps.

    CASES                    40 dicts {"id", "kind" ("fault"|"clean"), "category", "seed", "probes"}
    run_case(case, state_dir) -> loop

run_case builds a fresh loop in state_dir with the slp-360 builder (scrap layer on, arm "P"),
teaches that case's fictional world, asks the questions that queue the sleep's learning
episodes (>= 10 per learned word), and returns the loop JUST BEFORE the sleep. For a fault
case the fault is already installed on the built loop (wrappers / monkeypatches on that loop's
own objects only; no file in the tree is edited). The caller runs one sleep (force_sleep).

Every case (clean or faulty) gets the same pass-through frame around loop.sleeper.sleep and
loop.reasoner.answer, so the object layout does not tell a faulty case from a clean one; a clean
case's frame has no hooks and changes nothing.

"probes" lists things a user might say after the sleep (questions, plus a few new teaches at the
end so questions about people met after the sleep can be asked). They are for reporting only.

Worlds: every name is invented. Each case draws its own names (three name styles), its own
world size, and uses one or two of the 12 compound words in fable_sleep130_agent.WORDS130.
Some cases boot with an earlier word already installed (written to sleep145-words.json before
the build, in exactly the form an earlier sleep leaves it: hardened +/-30 logits of that
word's chain), so the sleep under test adds a second word.

Verification of this bench (every fault changes a user-visible reply vs. the same case with
the fault switched off; every clean case installs its word) is scripts/claude_slp364_bench_check.py.
"""

from __future__ import annotations

import functools
import json
import random
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

W = {name: i for i, name in enumerate(WORDS)}
MG, BOS, DMF, BOF, TOS, MOS, BOM, TOF, DOS, FOM, DOB, TOM = range(12)

FILLERS = ["Hi, how are you?", "Thanks, that helps.", "Good morning!",
           "Tell me a joke.", "What is the weather like today?"]


# ------------------------------------------------------------------ names
_ONSETS = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "t", "v", "z",
           "br", "dr", "gr", "kr", "tr", "pl", "gl", "fr", "vr"]
_MIDS = ["l", "m", "n", "r", "t", "v", "d", "k", "z", "b"]
_VOW = "aeiou"
_ENDS = ["n", "r", "l", "k", "m", "x"]
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
""".split())
_STOP = {"who", "what", "is", "the", "and", "mother", "father", "spouse", "boss",
         "doctor", "teacher", "friend", "best", "name", "called", "sleep"}


class Names:
    """Unique invented names for one world. style: syl (CVCVC), syl2 (CVCV), code (K07)."""

    def __init__(self, rng: random.Random, style: str) -> None:
        self.rng = rng
        self.style = style
        self.used: set[str] = set()
        letters = list("BCDFGHJKLMNPRTVWXZ")
        rng.shuffle(letters)
        self.letters = letters          # code style: one letter per role
        self.counter = rng.randrange(10, 40)

    def _syl(self) -> str:
        r = self.rng
        s = r.choice(_ONSETS) + r.choice(_VOW) + r.choice(_MIDS) + r.choice(_VOW)
        if self.style == "syl":
            s += r.choice(_ENDS)
        elif s[-1] in "ue":
            s = s[:-1] + r.choice("aoi")
        return s.capitalize()

    def new(self, role: int = 0) -> str:
        for _ in range(10000):
            if self.style == "code":
                self.counter += 1
                s = f"{self.letters[role % len(self.letters)]}{self.counter:02d}"
            else:
                s = self._syl()
            low = s.lower()
            if low in self.used or low in _BLOCK or low in _STOP or low.endswith("s"):
                continue
            self.used.add(low)
            return s
        raise RuntimeError("name pool exhausted")


def _rel_text(rel: str) -> str:
    return rel.replace("_", " ")


def _teach_text(a: str, rel: str, b: str) -> str:
    return f"{a}'s {_rel_text(rel)} is {b}."


def _word_q(name: str, w: int) -> str:
    return f"Who is {name}'s {ASK[WORDS[w]]}?"


def _hop_q(name: str, rel: str) -> str:
    return f"Who is {name}'s {_rel_text(rel)}?"


# ------------------------------------------------------------------ worlds
def build_world(spec: dict) -> dict:
    """Deterministic world for one case spec (names, teaches, episode questions, truth)."""
    rng = random.Random(f"slp364/world/{spec['id']}/{spec['seed']}")
    nm = Names(rng, spec.get("style", "syl"))
    words = list(spec["words"])
    pre = list(spec.get("pre", []))
    chains: dict = {}
    facts: list[tuple[str, str, str]] = []

    def make_chain(w: int, full: bool = True) -> list[str]:
        hops = CHAINS[w]
        people = [nm.new(k) for k in range(len(hops) + 1)]
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
        chains[w] = {"train": [], "test": [make_chain(w) for _ in range(4)],
                     "partial": []}
    # decoys: an extra relation on one position of every train/test chain of the first word
    for pos, rel in spec.get("decoy", []):
        for ch in chains[words[0]]["train"] + chains[words[0]]["test"]:
            facts.append((ch[pos], rel, nm.new(7)))
    order = list(facts)
    if spec.get("shuffle"):
        rng.shuffle(order)
    truth = {(a, rel): b for a, rel, b in facts}

    turns: list[str] = []
    wrong_first = {}
    for k in range(spec.get("corrections", 0)):   # honest re-teach before the questions
        ch = chains[words[0]]["train"][k]
        wrong_first[(ch[0], CHAINS[words[0]][0])] = nm.new(8)
    for a, rel, b in order:
        if (a, rel) in wrong_first:
            turns.append(_teach_text(a, rel, wrong_first[(a, rel)]))
        else:
            turns.append(_teach_text(a, rel, b))
    for (a, rel) in wrong_first:
        turns.append(f"Actually, {a}'s {_rel_text(rel)} is {truth[(a, rel)]}.")
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
    turns.extend(episodes)
    for text in fill[1:1 + spec.get("fillers", 1)]:
        turns.append(text)

    outsiders = [nm.new(9), nm.new(9)]
    # people the user only mentions AFTER the sleep (for probes and the check script)
    post = {w: [] for w in words}
    for w in words:
        for _ in range(2):
            hops = CHAINS[w]
            people = [nm.new(k + 10) for k in range(len(hops) + 1)]
            post[w].append(people)
    return {"spec": spec, "words": words, "pre": pre, "chains": chains, "truth": truth,
            "turns": turns, "outsiders": outsiders, "post": post,
            "n_episodes": len(episodes)}


def post_teaches(world: dict, w: int, people: list[str]) -> list[str]:
    return [_teach_text(people[k], rel, people[k + 1]) for k, rel in enumerate(CHAINS[w])]


def make_probes(world: dict) -> list[str]:
    out: list[str] = []
    w0 = world["words"][0]
    for w in world["words"]:
        c = world["chains"][w]
        out += [_word_q(ch[0], w) for ch in c["train"][:2]]
        out += [_word_q(ch[0], w) for ch in c["test"]]
        out += [_word_q(ch[0], w) for ch in c["partial"][:1]]
    for w in world["pre"]:
        out += [_word_q(ch[0], w) for ch in world["chains"][w]["test"][:3]]
    c0 = world["chains"][w0]
    out.append(_hop_q(c0["train"][0][0], CHAINS[w0][0]))
    out.append(_hop_q(c0["train"][1][1], CHAINS[w0][1]))
    out.append(_hop_q(c0["test"][0][0], CHAINS[w0][0]))
    out.append(_word_q(world["outsiders"][0], w0))
    out.append(_hop_q(world["outsiders"][1], "mother"))
    p = world["post"][w0][0]
    out += post_teaches(world, w0, p)
    out.append(_word_q(p[0], w0))
    out.append(_hop_q(p[0], CHAINS[w0][0]))
    return out


# ------------------------------------------------------------------ helpers on a built loop
def _inner_nb(loop):
    return getattr(loop.nb, "nb", loop.nb)


def _eid(question: dict, nb):
    eid = question.get("entity_id")
    if eid is None:
        found = nb.resolve(question.get("name", ""))
        if found.status == C.OK:
            eid = found.detail["entity_id"]
    return eid


def _ok_rec(question: dict, answer: str, rec: dict | None = None) -> dict:
    trail = list(((rec or {}).get("fields") or {}).get("trail", []))
    src = ((rec or {}).get("fields") or {}).get("source", "taught")
    return {"kind": "answer", "status": C.OK, "name": question.get("name", ""),
            "relations": list(question.get("relations") or []),
            "fields": {"answer": answer, "trail": trail, "source": src}}


def _pick(pool: list[str], key: str, avoid: str | None = None) -> str:
    cand = [p for p in pool if p != avoid] or pool
    return cand[zlib.crc32(key.encode()) % len(cand)]


def _one_word(question: dict):
    rels = list(question.get("relations") or [])
    if len(rels) == 1 and rels[0] in WORDS:
        return rels[0]
    return None


def _one_rel(question: dict):
    rels = list(question.get("relations") or [])
    return rels[0] if len(rels) == 1 else None


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


def _read_word_file(loop) -> dict:
    try:
        return json.loads(Path(loop.sleeper.word_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_word_file(loop, data: dict) -> None:
    Path(loop.sleeper.word_path).write_text(json.dumps(data, sort_keys=True),
                                            encoding="utf-8")


def _install_frame(loop) -> dict:
    """Pass-through wrappers put on EVERY case. Hooks are empty for a clean case."""
    st: dict = {"armed": False, "known": set(), "after": [], "hooks": []}
    inner_sleep = loop.sleeper.sleep

    @functools.wraps(inner_sleep)
    def sleep(experience, notebook):
        out = inner_sleep(experience, notebook)
        st["armed"] = True
        st["known"] = set(_inner_nb(loop).entities)
        for fn in st["after"]:
            fn(out)
        return out

    loop.sleeper.sleep = sleep
    inner_answer = loop.reasoner.answer

    @functools.wraps(inner_answer)
    def answer(question, notebook):
        rec = inner_answer(question, notebook)
        if st["armed"]:
            for fn in st["hooks"]:
                rec = fn(question, notebook, rec)
        return rec

    loop.reasoner.answer = answer
    st["inner_answer"] = inner_answer
    return st


# ------------------------------------------------------------------ the faults
# Each takes (loop, world, st) and installs its fault; st is the frame state.

def fault_recipe_faked(loop, world, st):
    """Sleeper does no training at all but reports every queued word as installed and bridged."""
    sl = loop.sleeper

    def run(notebook):
        eps = list(sl.reasoner.episodes)
        sl.reasoner.episodes.clear()
        count: dict = {}
        for ep in eps:
            count[ep["word_name"]] = count.get(ep["word_name"], 0) + 1
        return {"attempted": True, "installed": len(count),
                "words": [{"word": w, "episodes": n, "installed": True, "oof_best": 1.0,
                           "refit_agreement": 1.0, "reason": None, "grew_slot": False}
                          for w, n in sorted(count.items())],
                "probe_size": 128, "held_size": 128}

    def commit(notebook, recipe):
        return {r["word"]: {"bridged": True, "report_fid": None, "episodes": r["episodes"],
                            "grew_slot": False} for r in recipe.get("words", [])}

    sl._run_exp46 = run
    sl._commit_installs = commit


def fault_rollback(loop, world, st):
    """Real install, then silently rolled back (live table and word file); report unchanged."""
    before = {"file": None, "live": None}
    inner_sleep = loop.sleeper.sleep

    def sleep(experience, notebook):
        p = Path(loop.sleeper.word_path)
        before["file"] = p.read_text(encoding="utf-8") if p.exists() else None
        before["live"] = dict(loop.reasoner.inner.words)
        out = inner_sleep(experience, notebook)
        live = loop.reasoner.inner.words
        for k in list(live):
            if k not in before["live"]:
                del live[k]
        if before["file"] is None:
            p.unlink(missing_ok=True)
        else:
            p.write_text(before["file"], encoding="utf-8")
        loop.sleeper.grown = None
        return out

    loop.sleeper.sleep = functools.wraps(inner_sleep)(sleep)


def fault_bridge_skipped(loop, world, st):
    """Training runs and passes, but the bridge into serving is skipped while claiming success."""
    sl = loop.sleeper

    def commit_one(notebook, rec, w, wname, merged):
        return {"bridged": True, "report_fid": None,
                "episodes": int(rec.get("episodes", 0)),
                "grew_slot": bool(rec.get("grew_slot"))}

    sl._commit_one = commit_one


def _wrong_chain(new_chain):
    def install(loop, world, st):
        target = WORDS[world["words"][0]]

        def after(out):
            live = loop.reasoner.inner.words
            if target in live:
                live[target] = _hard_logits(new_chain)
                data = _read_word_file(loop)
                if target in data.get("words", {}):
                    data["words"][target]["logits"] = _hard_logits(new_chain)
                    _write_word_file(loop, data)
        st["after"].append(after)
    return install


def fault_hop_leak_grandmother(loop, world, st):
    """After the sleep, 'mother' questions about the first people of whole chains get the grandmother."""
    starts = {ch[0] for ch in world["chains"][MG]["train"] + world["chains"][MG]["test"]}
    nb = _inner_nb(loop)

    def hook(q, notebook, rec):
        if _one_rel(q) == "mother" and q.get("name") in starts and rec.get("status") == C.OK:
            eid = _eid(q, nb)
            rows = nb.current(eid, "mother") if eid else []
            if rows and "entity" in rows[0]["value"]:
                rows2 = nb.current(rows[0]["value"]["entity"], "mother")
                if rows2 and "entity" in rows2[0]["value"]:
                    return _ok_rec(q, nb.entities[rows2[0]["value"]["entity"]], rec)
        return rec
    st["hooks"].append(hook)


def fault_sleep_rewrites_taught(loop, world, st):
    """During the sleep, one taught 'mother' row is overwritten by a correction nobody made."""
    w = world["words"][0]
    ch = world["chains"][w]["train"][0]
    other = world["chains"][w]["train"][3][1]
    nb = _inner_nb(loop)

    def after(out):
        subj = nb.resolve(ch[0]).detail["entity_id"]
        val = nb.resolve(other).detail["entity_id"]
        loop.nb.assert_fact("s364-fix-0001", "listening", "taught", subj, CHAINS[w][0],
                            {"entity": val}, correction=True, raw=f"{ch[0]} mother fix")
    st["after"].append(after)


def fault_spouse_to_doctor(loop, world, st):
    """After the sleep, two people's 'spouse' answer becomes their spouse's doctor."""
    w = world["words"][0]
    targets = {ch[0]: ch[2] for ch in world["chains"][w]["train"][:2]}

    def hook(q, notebook, rec):
        if _one_rel(q) == "spouse" and q.get("name") in targets and rec.get("status") == C.OK:
            return _ok_rec(q, targets[q["name"]], rec)
        return rec
    st["hooks"].append(hook)


def fault_invent_unknown(loop, world, st):
    """After the sleep, questions about names never taught get an invented answer."""
    w = world["words"][0]
    pool = [ch[-1] for ch in world["chains"][w]["train"]]

    def hook(q, notebook, rec):
        if rec.get("status") == C.UNKNOWN_ENTITY and _one_rel(q):
            return _ok_rec(q, _pick(pool, q.get("name", "")))
        return rec
    st["hooks"].append(hook)


def fault_invent_missing_hop(loop, world, st):
    """After the sleep, a word question whose chain is missing a hop gets a made-up person."""
    w = world["words"][0]
    pool = [ch[-1] for ch in world["chains"][w]["train"]]
    nb = _inner_nb(loop)

    def hook(q, notebook, rec):
        if (_one_word(q) == WORDS[w] and rec.get("status") == C.MISSING_FACT
                and _eid(q, nb) is not None):
            return _ok_rec(q, _pick(pool, q.get("name", "")))
        return rec
    st["hooks"].append(hook)


def fault_sleep_writes_guess(loop, world, st):
    """During the sleep, the missing second hop of every half-taught chain is written as taught."""
    w = world["words"][0]
    rel = CHAINS[w][1]
    pool = [ch[2] for ch in world["chains"][w]["train"]]
    nb = _inner_nb(loop)

    def after(out):
        for i, ch in enumerate(world["chains"][w]["partial"]):
            subj = nb.resolve(ch[1]).detail["entity_id"]
            val = nb.resolve(_pick(pool, ch[1])).detail["entity_id"]
            loop.nb.assert_fact(f"s364-guess-{i:04d}", "listening", "taught", subj, rel,
                                {"entity": val}, raw="guess")
    st["after"].append(after)


def _drop_prior(live_only: bool):
    def install(loop, world, st):
        target = WORDS[world["pre"][0]]

        def after(out):
            loop.reasoner.inner.words.pop(target, None)
            if not live_only:
                data = _read_word_file(loop)
                data.get("words", {}).pop(target, None)
                _write_word_file(loop, data)
        st["after"].append(after)
    return install


def fault_swap_one_person(loop, world, st):
    """After the sleep, exactly one person's word answer is another person's answer."""
    w = world["words"][0]
    tr = world["chains"][w]["train"]
    victim, wrong = tr[1][0], tr[5][-1]

    def hook(q, notebook, rec):
        if _one_word(q) == WORDS[w] and q.get("name") == victim and rec.get("status") == C.OK:
            return _ok_rec(q, wrong, rec)
        return rec
    st["hooks"].append(hook)


def _mangle(name: str) -> str:
    vows = [i for i, ch in enumerate(name) if ch.lower() in _VOW]
    if not vows:
        return name + "a"
    i = vows[-1]
    nxt = _VOW[(_VOW.index(name[i].lower()) + 2) % 5]
    return name[:i] + (nxt.upper() if name[i].isupper() else nxt) + name[i + 1:]


def fault_mangle_some(loop, world, st):
    """After the sleep, answers about people whose name hashes to 0 mod 5 are misspelt."""
    def hook(q, notebook, rec):
        if rec.get("status") == C.OK and zlib.crc32(q.get("name", "").encode()) % 5 == 0:
            ans = str((rec.get("fields") or {}).get("answer", ""))
            if ans:
                return _ok_rec(q, _mangle(ans), rec)
        return rec
    st["hooks"].append(hook)


def fault_one_hop_one_person(loop, world, st):
    """After the sleep, one middle person's best-friend answer is someone else's best friend."""
    w = world["words"][0]
    tr = world["chains"][w]["train"]
    victim, wrong = tr[1][1], tr[4][2]

    def hook(q, notebook, rec):
        if _one_rel(q) == CHAINS[w][1] and q.get("name") == victim and rec.get("status") == C.OK:
            return _ok_rec(q, wrong, rec)
        return rec
    st["hooks"].append(hook)


def fault_new_names_first_hop(loop, world, st):
    """After the sleep, the word answers only the first hop for people added after the sleep."""
    w = world["words"][0]
    nb = _inner_nb(loop)

    def hook(q, notebook, rec):
        eid = _eid(q, nb)
        if (_one_word(q) == WORDS[w] and rec.get("status") == C.OK and eid is not None
                and eid not in st["known"]):
            rows = nb.current(eid, CHAINS[w][0])
            if rows and "entity" in rows[0]["value"]:
                return _ok_rec(q, nb.entities[rows[0]["value"]["entity"]], rec)
        return rec
    st["hooks"].append(hook)


def fault_new_names_one_hop(loop, world, st):
    """After the sleep, taught one-hop answers about people added after the sleep are wrong."""
    w = world["words"][0]
    nb = _inner_nb(loop)
    pool = [ch[1] for ch in world["chains"][w]["train"]]

    def hook(q, notebook, rec):
        eid = _eid(q, nb)
        if (_one_rel(q) in RELS and rec.get("status") == C.OK and eid is not None
                and eid not in st["known"]):
            return _ok_rec(q, _pick(pool, q.get("name", "")), rec)
        return rec
    st["hooks"].append(hook)


def fault_new_names_abstain(loop, world, st):
    """After the sleep, the new word refuses (I don't know) for people added after the sleep."""
    w = world["words"][0]
    nb = _inner_nb(loop)
    inner = st["inner_answer"]

    def hook(q, notebook, rec):
        eid = _eid(q, nb)
        if (_one_word(q) == WORDS[w] and rec.get("status") == C.OK and eid is not None
                and eid not in st["known"]):
            live = loop.reasoner.inner.words
            held = live.pop(WORDS[w], None)
            n_eps = len(loop.reasoner.episodes)
            try:
                rec = inner(q, notebook)
            finally:
                if held is not None:
                    live[WORDS[w]] = held
                del loop.reasoner.episodes[n_eps:]
        return rec
    st["hooks"].append(hook)


FAULTS = {
    "recipe_faked": fault_recipe_faked,
    "rollback": fault_rollback,
    "bridge_skipped": fault_bridge_skipped,
    "mg_as_mother": _wrong_chain(("mother",)),
    "bof_as_father_teacher": _wrong_chain(("father", "teacher")),
    "mos_as_own_mother": _wrong_chain(("mother",)),
    "hop_leak_grandmother": fault_hop_leak_grandmother,
    "sleep_rewrites_taught": fault_sleep_rewrites_taught,
    "spouse_to_doctor": fault_spouse_to_doctor,
    "invent_unknown": fault_invent_unknown,
    "invent_missing_hop": fault_invent_missing_hop,
    "sleep_writes_guess": fault_sleep_writes_guess,
    "drop_prior_everywhere": _drop_prior(live_only=False),
    "drop_prior_live": _drop_prior(live_only=True),
    "swap_one_person": fault_swap_one_person,
    "mangle_some": fault_mangle_some,
    "one_hop_one_person": fault_one_hop_one_person,
    "new_names_first_hop": fault_new_names_first_hop,
    "new_names_one_hop": fault_new_names_one_hop,
    "new_names_abstain": fault_new_names_abstain,
}


# ------------------------------------------------------------------ the case table
# (kind, category, seed, spec). Specs stay private to this module (not in CASES).
_TABLE = [
    # ---- clean: honest sleeps, seeds 1..20
    ("clean", "clean-one-word", 1, dict(words=[MG], n=10, style="syl")),
    ("clean", "clean-one-word", 2, dict(words=[BOS], n=11, style="syl2", n_partial=0)),
    ("clean", "clean-three-hop", 3, dict(words=[DMF], n=10, style="syl")),
    ("clean", "clean-grown-slot", 4, dict(words=[BOF], n=12, style="code")),
    ("clean", "clean-grown-slot", 5, dict(words=[TOS], n=10, style="syl", n_partial=0)),
    ("clean", "clean-grown-slot", 6, dict(words=[MOS], n=11, style="syl2", shuffle=True, n_partial=0)),
    ("clean", "clean-grown-slot", 7, dict(words=[BOM], n=10, style="syl")),
    ("clean", "clean-grown-slot", 8, dict(words=[TOF], n=12, style="syl2")),
    ("clean", "clean-grown-slot", 9, dict(words=[DOS], n=10, style="code", n_partial=0)),
    ("clean", "clean-grown-slot", 10, dict(words=[FOM], n=11, style="syl", n_partial=2)),
    ("clean", "clean-grown-slot", 11, dict(words=[DOB], n=10, style="syl2")),
    ("clean", "clean-grown-slot", 12, dict(words=[TOM], n=12, style="syl", shuffle=True)),
    ("clean", "clean-large-world", 13, dict(words=[MG], n=14, style="code", n_partial=3,
                                            decoy=[(0, "father"), (1, "father")])),
    ("clean", "clean-prior-word", 14, dict(words=[BOS], pre=[MG], n=10, style="syl", n_partial=0)),
    ("clean", "clean-prior-word", 15, dict(words=[TOF], pre=[BOF], n=11, style="syl2")),
    ("clean", "clean-with-correction", 16, dict(words=[MG], n=10, style="syl", corrections=2)),
    ("clean", "clean-large-world", 17, dict(words=[BOS], n=14, style="syl",
                                            decoy=[(1, "teacher"), (0, "father")],
                                            shuffle=True, fillers=3, n_partial=0)),
    ("clean", "clean-two-words", 18, dict(words=[MG, DMF], n=10, style="syl2")),
    ("clean", "clean-one-word", 19, dict(words=[TOM], n=10, style="code", fillers=4)),
    ("clean", "clean-prior-word", 20, dict(words=[DOB], pre=[DOS], n=10, style="syl")),
    # ---- faults, seeds 1..20 (same range as the clean cases)
    ("fault", "silent-noop", 1, dict(words=[MG], n=10, style="syl", fault="recipe_faked")),
    ("fault", "silent-noop", 2, dict(words=[TOS], n=10, style="syl2", fault="rollback")),
    ("fault", "silent-noop", 3, dict(words=[DOB], n=11, style="code", fault="bridge_skipped")),
    ("fault", "wrong-route", 4, dict(words=[MG], n=10, style="syl2", fault="mg_as_mother")),
    ("fault", "wrong-route", 5, dict(words=[BOF], n=10, style="syl", decoy=[(1, "teacher")],
                                      fault="bof_as_father_teacher")),
    ("fault", "wrong-route", 6, dict(words=[MOS], n=11, style="code", decoy=[(0, "mother")],
                                      fault="mos_as_own_mother")),
    ("fault", "taught-fact-changed", 7, dict(words=[MG], n=10, style="syl",
                                              fault="hop_leak_grandmother")),
    ("fault", "taught-fact-changed", 8, dict(words=[BOM], n=10, style="syl2",
                                              fault="sleep_rewrites_taught")),
    ("fault", "taught-fact-changed", 9, dict(words=[DOS], n=10, style="syl",
                                              fault="spouse_to_doctor")),
    ("fault", "made-up-answer", 10, dict(words=[MG], n=10, style="code",
                                         fault="invent_unknown")),
    ("fault", "made-up-answer", 11, dict(words=[FOM], n=10, style="syl", n_partial=3,
                                         fault="invent_missing_hop")),
    ("fault", "made-up-answer", 12, dict(words=[BOS], n=10, style="syl2", n_partial=3,
                                         fault="sleep_writes_guess")),
    ("fault", "forgets-earlier-word", 13, dict(words=[BOS], pre=[MG], n=10, style="syl2",
                                               fault="drop_prior_everywhere")),
    ("fault", "forgets-earlier-word", 14, dict(words=[TOM], pre=[MOS], n=10, style="syl",
                                               fault="drop_prior_live")),
    ("fault", "one-of-many", 15, dict(words=[TOF], n=12, style="syl", fault="swap_one_person")),
    ("fault", "some-people-corrupted", 16, dict(words=[MG], n=12, style="syl2",
                                                fault="mangle_some")),
    ("fault", "one-of-many", 17, dict(words=[DMF], n=10, style="code",
                                      fault="one_hop_one_person")),
    ("fault", "new-names-only", 18, dict(words=[MG], n=10, style="syl",
                                         fault="new_names_first_hop")),
    ("fault", "new-names-only", 19, dict(words=[MOS], n=10, style="syl2",
                                         fault="new_names_one_hop")),
    ("fault", "new-names-only", 20, dict(words=[BOF], n=10, style="syl",
                                         fault="new_names_abstain")),
]

# Case ids do not reveal the kind: ids are assigned over a fixed shuffle of the table.
_order = list(range(len(_TABLE)))
random.Random("slp364/ids").shuffle(_order)
_SPECS: dict[str, dict] = {}
CASES: list[dict] = []
for _slot, _i in enumerate(_order):
    _kind, _cat, _seed, _spec = _TABLE[_i]
    _cid = f"slp364-{_slot + 1:02d}"
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
    """Build, teach, queue episodes, install the fault (if any); return the loop before sleep."""
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
        print(c["id"], c["kind"], c["category"], c["seed"], len(c["probes"]))
