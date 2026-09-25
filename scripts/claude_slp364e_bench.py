#!/usr/bin/env python3
"""slp-364e: fifth blind test bench of sleep nights (40 cases: 20 clean, 20 faulty).

Written by the bench author without sight of any gate. Each case plays one day of
teaching plus word questions on the slp-360 chat loop (scripts/claude_slp360_test.py
build(..., "P")), arms its fault (if any) and returns the loop BEFORE the night.
The runner runs the night itself (force_sleep) and then asks the case's probes.

Public interface:
  CASES                    40 dicts: id, kind ("clean"/"fault"), category, seed, probes
  run_case(case, state_dir, fault=True) -> loop
                           fault=False builds the fault-off twin (same day, no fault).
The per-case spec (world, day script, words, fault name and parameters, probe grades)
lives in the private table _SPECS, looked up by id; it is not in the case dicts.

Faults arm only when the night runs (a wrapper on the sleeper's recipe step, which the
sleeper calls from inside sleep(), so it works whoever wraps loop.sleeper.sleep). Before
that, every wrapper passes through untouched, so day replies equal the twin's.
Fictional names only (generated from syllables).
"""
from __future__ import annotations

import copy
import json
import os
import random
import re
import sys
import zlib
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_sleep130_agent as S130  # noqa: E402 (read-only: word table only)
import claude_slp360_test as T360  # noqa: E402 (read-only: build/say/inner_nb)

WORDS = S130.WORDS130
CHAIN = dict(zip(S130.WORDS130, S130.CHAINS130))
SKILLS = dict(zip(S130.WORDS130, S130.EXPECTED_SKILLS130))
WORD_FILE = "sleep145-words.json"

MG, FOM = "maternal_grandmother", "father_of_mother"
BOS, TOS, MOS = "boss_of_spouse", "teacher_of_spouse", "mother_of_spouse"
BOF, BOM, TOF = "boss_of_father", "boss_of_mother", "teacher_of_father"
DOS, DOB, TOM = "doctor_of_spouse", "doctor_of_boss", "teacher_of_mother"
DMF = "doctor_of_mothers_friend"


def _rt(rel: str) -> str:
    return rel.replace("_", " ")


# ------------------------------------------------------------------ names
_ON = ["B", "D", "F", "G", "K", "L", "M", "N", "P", "R", "S", "T", "V", "Z",
       "Br", "Dr", "Tr", "Gr", "Th", "Sh"]
_VO = ["a", "e", "i", "o", "u"]
_MID = ["l", "n", "r", "v", "d", "m"]
_CO = ["n", "l", "r", "s", "x"]
_BAD = {"Salon", "Lemon", "Melon", "Robin", "Solar", "Rider", "Radar", "Molar",
        "Lunar", "Sonar", "Venus", "Minus", "Bonus", "Tonal", "Final", "Rival",
        "Novel", "Level", "Model", "Modal", "Medal", "Pedal", "Tidal", "Nodal",
        "Bison", "Demon", "Felon", "Salmon", "Linen", "Siren", "Baron", "Moral",
        "Coral", "Regal", "Legal", "Local", "Vocal", "Focal", "Total", "Metal",
        "Denis", "Tenor", "Manor", "Minor", "Donor", "Honor", "Humor", "Tumor",
        "Rumor", "Sumer", "Timer", "Tamer", "Lamer", "Gamer", "Diner", "Liner",
        "Miner", "Toner", "Loner", "Boner", "Saner", "Laser", "Loser", "Poser",
        "Riser", "Wiser", "Mimes", "Tunes", "Dunes", "Runes", "Lines", "Mines",
        "Lanes", "Manes", "Sales", "Tales", "Males", "Moles", "Poles", "Roles",
        "Tiles", "Miles", "Files", "Piles", "Rules", "Mules", "Dimes", "Times",
        "Names", "Games", "Domes", "Homes", "Tubes", "Nodes", "Modes", "Codes",
        "Rides", "Sides", "Tides", "Moves", "Waves", "Saves", "Dives", "Lives",
        "Fives", "Gives", "Loves", "Doves", "Raven", "Seven", "Given", "Riven",
        "Driven", "Liver", "River", "Diver", "Fever", "Lever", "Never", "Sever",
        "Cover", "Mover", "Lover", "Rover", "Dover", "Shiver", "Sliver"}


def _pool(seed: int, n: int = 420) -> list[str]:
    rng = random.Random(90_000 + seed)
    out: list[str] = []
    seen: set[str] = set()
    while len(out) < n:
        nm = (rng.choice(_ON) + rng.choice(_VO) + rng.choice(_MID)
              + rng.choice(_VO) + rng.choice(_CO))
        nm = nm[0].upper() + nm[1:].lower()
        if nm in seen or nm in _BAD or nm[:3] in {o[:3] for o in out[-3:]}:
            continue
        seen.add(nm)
        out.append(nm)
    return out


# ------------------------------------------------------------------ world model
class _World:
    """The case's ground truth. Every line it emits is an English teach."""

    def __init__(self, seed: int) -> None:
        self.names = _pool(seed)
        self.k = 0
        self.truth: dict[tuple[str, str], str] = {}
        self.history: dict[tuple[str, str], list[str]] = {}
        self.lines: list[str] = []
        self.learned: set[str] | None = None     # words the loop should know at probe time

    def new(self) -> str:
        nm = self.names[self.k]
        self.k += 1
        return nm

    def put(self, a: str, rel: str, b: str, *, correct: bool = False, say: bool = True) -> str:
        self.truth[(a, rel)] = b
        self.history.setdefault((a, rel), []).append(b)
        line = ("Actually, " if correct else "") + f"{a}'s {_rt(rel)} is {b}."
        if say:
            self.lines.append(line)
        return line

    def ensure(self, a: str, rel: str) -> str:
        if (a, rel) not in self.truth:
            self.put(a, rel, self.new())
        return self.truth[(a, rel)]

    def chain(self, word: str, start: str | None = None) -> str:
        s = start or self.new()
        cur = s
        for rel in CHAIN[word]:
            cur = self.ensure(cur, rel)
        return s

    def walk(self, s: str, rels) -> str | None:
        cur = s
        for r in rels:
            cur = self.truth.get((cur, r))
            if cur is None:
                return None
        return cur

    def word_answer(self, s: str, word: str) -> str | None:
        if (s, word) in self.truth:              # a taught row for the word itself wins
            return self.truth[(s, word)]
        if self.learned is not None and word not in self.learned:
            return None                          # never learned: the honest reply abstains
        return self.walk(s, CHAIN[word])

    def filler(self, n: int, rng: random.Random) -> None:
        """Big-world padding: mother chains plus assorted person relations, never asked."""
        for _ in range(n):
            kid = self.new()
            mom = self.ensure(kid, "mother")
            if rng.random() < 0.6:
                self.ensure(mom, "mother")
            if rng.random() < 0.4:
                self.ensure(kid, rng.choice(["father", "spouse", "boss", "teacher", "doctor"]))


# ------------------------------------------------------------------ probe makers
# Grades: ("is", name) reply ends " is NAME." ; ("dk",) reply says don't know ;
# ("yes",) / ("no",) reply starts Yes / No ; ("rev", kid) reply starts "KID's" ;
# ("saved",) a teach reply ; ("nofab", word) no answer is claimed for the word
# (the chain is incomplete) ; None = compared only, not graded.
def _exp_name(v):
    return ("is", v) if v else ("dk",)


def p_plain(w: _World, word: str, s: str):
    return (f"Who is {s}'s {_rt(word)}?", _exp_name(w.word_answer(s, word)))


def p_called(w: _World, word: str, s: str):
    return (f"What is {s}'s {_rt(word)} called?", _exp_name(w.word_answer(s, word)))


def p_whos(w: _World, word: str, s: str):
    return (f"who's {s}'s {_rt(word)}?", _exp_name(w.word_answer(s, word)))


def p_tell(w: _World, word: str, s: str):
    return (f"Tell me {s}'s {_rt(word)}.", _exp_name(w.word_answer(s, word)))


def p_explicit(w: _World, word: str, s: str):
    rels = CHAIN[word]
    return ("Who is " + s + "'s " + "'s ".join(_rt(r) for r in rels) + "?",
            _exp_name(w.walk(s, rels)))


def p_comp(w: _World, word: str, s: str, rel: str = "mother"):
    base = w.word_answer(s, word)
    ans = w.truth.get((base, rel)) if base else None
    return (f"Who is {s}'s {_rt(word)}'s {_rt(rel)}?", _exp_name(ans))


def p_yn_word(w: _World, word: str, s: str):
    return (f"Is {w.word_answer(s, word)} {s}'s {_rt(word)}?", None)


def p_yn_base(w: _World, s: str, rel: str, v: str | None = None):
    true = w.truth[(s, rel)]
    v = v or true
    return (f"Is {v} {s}'s {_rt(rel)}?", ("yes",) if v == true else ("no",))


def p_base(w: _World, s: str, rel: str):
    return (f"Who is {s}'s {_rt(rel)}?", _exp_name(w.truth.get((s, rel))))


def p_rev(w: _World, s: str, rel: str):
    return (f"Whose {_rt(rel)} is {w.truth[(s, rel)]}?", ("rev", s))


def p_broken(w: _World, word: str, s: str):
    assert w.word_answer(s, word) is None
    return (f"Who is {s}'s {_rt(word)}?", ("nofab", word))


def p_unknown(w: _World, word: str):
    return (f"Who is {w.new()}'s {_rt(word)}?", ("dk",))


def p_teach(w: _World, a: str, rel: str, b: str, correct: bool = False):
    return (w.put(a, rel, b, correct=correct, say=False), ("saved",))


# ------------------------------------------------------------------ the standard day
class _Day:
    """Teach lines, then day questions; people grouped by role for the probes."""

    def __init__(self, seed: int) -> None:
        self.w = _World(seed)
        self.rng = random.Random(7_000 + seed)
        self.asked: dict[str, list[str]] = {}
        self.unasked: dict[str, list[str]] = {}
        self.broken: dict[str, list[str]] = {}
        self.script: list[str] = []

    def people(self, word: str, n_ask: int = 9, n_unasked: int = 2, n_broken: int = 1) -> None:
        w = self.w
        self.asked.setdefault(word, []).extend(w.chain(word) for _ in range(n_ask))
        self.unasked.setdefault(word, []).extend(w.chain(word) for _ in range(n_unasked))
        for _ in range(n_broken):
            s = w.new()
            w.ensure(s, CHAIN[word][0])          # first hop only: the chain breaks after it
            self.broken.setdefault(word, []).append(s)

    def flush_teach(self, shuffle: bool = True) -> None:
        lines = list(self.w.lines)
        self.w.lines.clear()
        if shuffle:
            # keep each chain's own order intact but interleave chains
            self.rng.shuffle(lines)
        self.script.extend(lines)

    def ask(self, word: str, people=None, style: str = "plain", times: int = 1) -> None:
        people = self.asked[word] if people is None else people
        makers = {"plain": p_plain, "called": p_called, "whos": p_whos, "tell": p_tell}
        styles = ["plain", "whos", "tell"] if style == "mixed" else [style]
        for _ in range(times):
            for i, s in enumerate(people):
                self.script.append(makers[styles[i % len(styles)]](self.w, word, s)[0])
                if style == "mixed" and i % 4 == 1:
                    self.script.append(p_called(self.w, word, s)[0])

    def say(self, *texts: str) -> None:
        self.script.extend(texts)

    def night(self) -> None:
        self.script.append("#NIGHT")


# ------------------------------------------------------------------ fault contexts
class _Ctx:
    def __init__(self, loop, spec: dict) -> None:
        self.loop = loop
        self.spec = spec
        self.fault = spec["fault"][0]
        self.p = dict(spec["fault"][1])
        self.armed = False
        self.night_eps: list[dict] = []
        self.words_before: set[str] = set()
        self.flags: dict = {}
        self.inner = T360.inner_nb(loop)
        self.raw_append = self.inner._append     # captured before any runner lock

    # ------------------------------------------------------------ helpers
    def eid(self, name: str):
        r = self.inner.resolve(name)
        return r.detail["entity_id"] if r.status == C.OK else None

    def show(self, eid) -> str:
        return self.inner.entities.get(eid, str(eid))

    def hop(self, eid, rel):
        rows = self.inner.current(eid, rel)
        if rows and "entity" in rows[0]["value"]:
            return rows[0]["value"]["entity"]
        return None

    def walk(self, eid, rels):
        for r in rels:
            if eid is None:
                return None
            eid = self.hop(eid, r)
        return eid

    def qeid(self, q: dict):
        e = q.get("entity_id")
        return e if e is not None else self.eid(q.get("name", ""))

    def raw_write(self, fn):
        """Run fn with the notebook writer captured at run_case time."""
        inner = self.inner
        had = "_append" in vars(inner)
        cur = vars(inner).get("_append")
        inner._append = self.raw_append
        try:
            return fn()
        finally:
            if had:
                inner._append = cur
            else:
                try:
                    del inner._append
                except AttributeError:
                    pass

    def word_file(self) -> Path:
        return Path(self.loop.dir) / WORD_FILE

    def read_words(self) -> dict:
        try:
            data = json.loads(self.word_file().read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def write_words(self, data: dict) -> None:
        p = self.word_file()
        tmp = p.parent / (p.name + ".tmp364e")
        tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        os.replace(tmp, p)

    @staticmethod
    def ok(rec: dict, answer: str) -> dict:
        return {"kind": "answer", "status": C.OK, "name": rec.get("name", ""),
                "relations": list(rec.get("relations") or []),
                "fields": {"answer": answer, "trail": [], "source": "sleep-derived"}}

    @staticmethod
    def missing(rec: dict, name: str, rel: str) -> dict:
        return {"kind": "answer", "status": C.MISSING_FACT, "name": rec.get("name", ""),
                "relations": list(rec.get("relations") or []),
                "fields": {"subject": name, "relation": _rt(rel), "hop": 1, "trail": []}}


def _install_arm(ctx: _Ctx) -> None:
    sleeper = ctx.loop.sleeper
    inner_run = sleeper._run_exp46

    def run364e(notebook):
        reasoner = getattr(sleeper, "reasoner", None)
        ctx.night_eps = [dict(e) for e in getattr(reasoner, "episodes", [])]
        ctx.words_before = set(getattr(getattr(reasoner, "inner", None), "words", {}) or {})
        out = inner_run(notebook)
        ctx.armed = True
        hook = _AFTER_RECIPE.get(ctx.fault)
        if hook is not None:
            hook(ctx, out)
        return out

    sleeper._run_exp46 = run364e

    commit_hook = _COMMIT.get(ctx.fault)
    if commit_hook is not None:
        inner_commit = sleeper._commit_installs

        def commit364e(notebook, recipe):
            if not ctx.armed:
                return inner_commit(notebook, recipe)
            return commit_hook(ctx, inner_commit, notebook, recipe)

        sleeper._commit_installs = commit364e

    ans_hook = _ANSWER.get(ctx.fault)
    if ans_hook is not None:
        reasoner = ctx.loop.reasoner
        inner_answer = reasoner.answer

        def answer364e(question, notebook):
            rec = inner_answer(question, notebook)
            if not ctx.armed:
                return rec
            try:
                return ans_hook(ctx, question, rec)
            except Exception:  # noqa: BLE001 -- a fault never crashes the loop
                return rec

        reasoner.answer = answer364e

    turn_hook = _TURN.get(ctx.fault)
    if turn_hook is not None:
        inner_turn = ctx.loop.turn

        def turn364e(text):
            if not ctx.armed:
                return inner_turn(text)
            text2 = turn_hook(ctx, text)
            try:
                return inner_turn(text2)
            finally:
                ctx.flags.clear()

        ctx.loop.turn = turn364e

    nb_hook = _NBWRITE.get(ctx.fault)
    if nb_hook is not None:
        lnb = ctx.loop.nb
        inner_assert = lnb.assert_fact

        def assert364e(event_id, actor, source, subject, relation, value, **kw):
            if not ctx.armed:
                return inner_assert(event_id, actor, source, subject, relation, value, **kw)
            return nb_hook(ctx, inner_assert, event_id, actor, source, subject,
                           relation, value, kw)

        lnb.assert_fact = assert364e


# ---- faults acting when the recipe step ends (the night) -----------------------
def _after_extra_word(ctx: _Ctx, out: dict) -> None:
    """Evidence gate skipped: a word with too few episodes is installed anyway."""
    word = ctx.p["word"]
    reasoner = ctx.loop.sleeper.reasoner
    if word in reasoner.inner.words:
        return
    skills = list(SKILLS[word])
    stages = [skills[0], 0, skills[1]] if len(skills) == 2 else skills
    logits = [[30.0 if i == s else -30.0 for i in range(9)] for s in stages]
    reasoner.inner.words[word] = logits
    reasoner.install_episodes[word] = 1
    data = ctx.read_words()
    words = dict(data.get("words", {}))
    words[word] = {"logits": logits, "report_fid": None, "episodes": 1,
                   "seed": ctx.spec["seed"]}
    ctx.write_words({"words": words, "seed": ctx.spec["seed"]})


_AFTER_RECIPE = {"extra_word": _after_extra_word}


# ---- faults acting on the commit (bridge + persist) -----------------------------
def _commit_silent_noop(ctx, inner_commit, notebook, recipe):
    return {}                                   # reports success upstream, bridges nothing


def _commit_not_persisted(ctx, inner_commit, notebook, recipe):
    p = ctx.word_file()
    before = p.read_bytes() if p.exists() else None
    out = inner_commit(notebook, recipe)
    if before is None:
        p.unlink(missing_ok=True)
    else:
        p.write_bytes(before)
    return out


def _commit_forget_old(ctx, inner_commit, notebook, recipe):
    out = inner_commit(notebook, recipe)
    old = set(ctx.words_before)
    words = ctx.loop.sleeper.reasoner.inner.words
    for w in list(words):
        if w in old:
            del words[w]
    data = ctx.read_words()
    kept = {k: v for k, v in data.get("words", {}).items() if k not in old}
    ctx.write_words({"words": kept, "seed": data.get("seed")})
    return out


def _commit_forget_old_disk(ctx, inner_commit, notebook, recipe):
    out = inner_commit(notebook, recipe)
    old = set(ctx.words_before)
    data = ctx.read_words()
    kept = {k: v for k, v in data.get("words", {}).items() if k not in old}
    ctx.write_words({"words": kept, "seed": data.get("seed")})
    return out


def _commit_slot_mixup(ctx, inner_commit, notebook, recipe):
    out = inner_commit(notebook, recipe)
    a, b = ctx.p["src"], ctx.p["dst"]
    words = ctx.loop.sleeper.reasoner.inner.words
    if a in words and b in words:
        words[b] = copy.deepcopy(words[a])
        data = ctx.read_words()
        ws = dict(data.get("words", {}))
        if b in ws:
            ws[b] = dict(ws[b], logits=copy.deepcopy(words[a]))
            ctx.write_words({"words": ws, "seed": data.get("seed")})
    return out


def _commit_materialize(ctx, inner_commit, notebook, recipe):
    """Derived answers written as rows into the MAIN notebook (bypassing the scrap layer)."""
    out = inner_commit(notebook, recipe)
    word = ctx.p["word"]
    if word not in ctx.loop.sleeper.reasoner.inner.words:
        return out
    inner = ctx.inner
    rows = []
    for eid in sorted(inner.entities):
        ans = ctx.walk(eid, CHAIN[word])
        if ans is not None:
            rows.append((eid, ans))

    def go():
        for i, (eid, ans) in enumerate(rows):
            inner.assert_fact(f"sleep364e-mat-{word}-{i}", "sleep", "sleep-derived", eid,
                              word, {"entity": ans}, raw="sleep364e materialised answer")
    ctx.raw_write(go)
    return out


def _commit_overwrite(ctx, inner_commit, notebook, recipe):
    """Consolidation collapses one hop: a taught first-hop row is rewritten to the word's answer."""
    out = inner_commit(notebook, recipe)
    word, who = ctx.p["word"], ctx.p["who"]
    s = ctx.eid(who)
    ans = ctx.walk(s, CHAIN[word])
    if s is not None and ans is not None:
        ctx.raw_write(lambda: ctx.inner.assert_fact(
            "sleep364e-collapse-0", "listening", "taught", s, CHAIN[word][0],
            {"entity": ans}, correction=True, raw="sleep364e consolidation"))
    return out


def _commit_alias(ctx, inner_commit, notebook, recipe):
    """Identity step: the episode's start name is recorded as an alias of its answer."""
    out = inner_commit(notebook, recipe)
    word, who = ctx.p["word"], ctx.p["who"]
    s = ctx.eid(who)
    ans = ctx.walk(s, CHAIN[word])
    if s is not None and ans is not None:
        ctx.raw_write(lambda: ctx.inner.add_alias("sleep364e-alias-0", ans, who))
    return out


_COMMIT = {"silent_noop": _commit_silent_noop, "not_persisted": _commit_not_persisted,
           "forget_old_word": _commit_forget_old, "forget_old_on_disk": _commit_forget_old_disk,
           "slot_mixup": _commit_slot_mixup, "materialize_rows": _commit_materialize,
           "overwrite_taught": _commit_overwrite, "alias_merge": _commit_alias}


# ---- faults in the answer path after the night ----------------------------------
def _is_word_q(q: dict, word: str) -> bool:
    return list(q.get("relations") or []) == [word]


def _ans_made_up(ctx, q, rec):
    word = ctx.p["word"]
    if _is_word_q(q, word) and rec.get("status") in (C.MISSING_FACT, C.BROKEN_CHAIN):
        answers = Counter(e["answer"] for e in ctx.night_eps if e.get("word_name") == word)
        if answers:
            return ctx.ok(rec, ctx.show(answers.most_common(1)[0][0]))
    return rec


def _ans_stale_snapshot(ctx, q, rec):
    word = ctx.p["word"]
    if not _is_word_q(q, word):
        return rec
    snap = ctx.p.get("_snap")
    if snap is None:
        return rec
    cur = ctx.qeid(q)
    for r in CHAIN[word]:
        cur = snap.get((cur, r))
        if cur is None:
            return ctx.missing(rec, rec.get("name", ""), word)
    return ctx.ok(rec, ctx.show(cur))


def _after_snapshot(ctx: _Ctx, out: dict) -> None:
    word = ctx.p["word"]
    snap = {}
    for eid in list(ctx.inner.entities):
        for r in set(CHAIN[word]):
            v = ctx.hop(eid, r)
            if v is not None:
                snap[(eid, r)] = v
    ctx.p["_snap"] = snap


_AFTER_RECIPE["stale_snapshot"] = _after_snapshot


def _ans_minority(ctx, q, rec):
    word = ctx.p["word"]
    if _is_word_q(q, word) and rec.get("status") == C.OK and _minority(q.get("name", "")):
        m = ctx.hop(ctx.qeid(q), CHAIN[word][0])
        if m is not None:
            return ctx.ok(rec, ctx.show(m))
    return rec


def _minority(name: str) -> bool:
    return zlib.crc32(name.strip().lower().encode()) % 5 == 0


def _ans_stale_correction(ctx, q, rec):
    word = ctx.p["word"]
    if not (_is_word_q(q, word) and rec.get("status") == C.OK):
        return rec
    inner = ctx.inner
    cur = ctx.qeid(q)
    for r in CHAIN[word]:
        rows = [f for f in inner.facts.values()
                if f["subject"] == cur and f["relation"] == r and f["source"] == "taught"
                and "entity" in f["value"] and f["fact_id"] not in inner.retracted]
        if not rows:
            return rec
        cur = min(rows, key=lambda f: f["n"])["value"]["entity"]
    return ctx.ok(rec, ctx.show(cur))


def _ans_memorized(ctx, q, rec):
    word = ctx.p["word"]
    if _is_word_q(q, word) and rec.get("status") == C.OK:
        seen = {e["start"] for e in ctx.night_eps if e.get("word_name") == word}
        if ctx.qeid(q) not in seen:
            return ctx.missing(rec, rec.get("name", ""), word)
    return rec


def _ans_compositional(ctx, q, rec):
    word = ctx.p["word"]
    rels = list(q.get("relations") or [])
    if rec.get("status") == C.OK and ((len(rels) >= 2 and word in rels)
                                      or rels == list(CHAIN[word])):
        return ctx.missing(rec, rec.get("name", ""), " ".join(rels))
    return rec


def _ans_called(ctx, q, rec):
    word = ctx.p["word"]
    if ctx.flags.get("called") and _is_word_q(q, word) and rec.get("status") == C.OK:
        m = ctx.hop(ctx.qeid(q), CHAIN[word][0])
        if m is not None:
            return ctx.ok(rec, ctx.show(m))
    return rec


def _ans_base_damaged(ctx, q, rec):
    word = ctx.p["word"]
    if (list(q.get("relations") or []) == [CHAIN[word][0]] and rec.get("status") == C.OK):
        s = ctx.qeid(q)
        seen = {e["start"] for e in ctx.night_eps if e.get("word_name") == word}
        if s in seen:
            ans = ctx.walk(s, CHAIN[word])
            if ans is not None:
                return ctx.ok(rec, ctx.show(ans))
    return rec


_ANSWER = {"made_up_incomplete": _ans_made_up, "stale_snapshot": _ans_stale_snapshot,
           "minority_wrong": _ans_minority, "stale_correction": _ans_stale_correction,
           "memorized_only": _ans_memorized, "compositional_abstain": _ans_compositional,
           "called_route_wrong": _ans_called, "base_mother_damaged": _ans_base_damaged}


# ---- faults in the turn path after the night ------------------------------------
def _turn_called(ctx, text):
    if re.search(r"\bcalled\s*[?.!]*\s*$|\bname of\b", text, re.I):
        ctx.flags["called"] = True
    return text


def _turn_contraction(ctx, text):
    return re.sub(r"(?i)\bwho's\b", lambda m: m.group(0).replace("'", ""), text)


def _turn_reverse(ctx, text):
    word = ctx.p["word"]
    m = re.match(r"^\s*Whose (.+?) is (.+?)\?\s*$", text)
    if m and m.group(1).strip().lower() == _rt(CHAIN[word][0]):
        return f"Whose {_rt(word)} is {m.group(2)}?"
    return text


_TURN = {"called_route_wrong": _turn_called, "contraction_broken": _turn_contraction,
         "reverse_broken": _turn_reverse}


# ---- faults in the write path after the night -----------------------------------
def _nb_teach_to_scrap(ctx, inner_assert, event_id, actor, source, subject, relation,
                       value, kw):
    """The sleep proxy stays attached: taught rows after the night land in scrap only."""
    if actor == "listening" and source == "taught":
        scrap = getattr(ctx.loop, "scrap360", None)
        name = ctx.inner.entities.get(subject, subject)
        if scrap is not None:
            scrap.fact(event_id, actor, source, subject, relation, value, name,
                       raw=kw.get("raw"))
        shown = ctx.show(value["entity"]) if "entity" in value else str(value.get("literal"))
        return C.Result(C.SAVED, {"text": f"{name}'s {relation} is {shown}",
                                  "fact_id": None, "supersedes": None})
    return inner_assert(event_id, actor, source, subject, relation, value, **kw)


_NBWRITE = {"teach_to_scrap": _nb_teach_to_scrap}


# ------------------------------------------------------------------ case builders
# Each builder takes the case seed and returns a spec: script (day turns, "#NIGHT" for an
# earlier night), probes [(text, grade)], words (installed after the runner's night),
# category, fault (name, params) or None.

def _std_probes(d: _Day, word: str, *, extra=()):
    w = d.w
    a, u, b = d.asked[word], d.unasked[word], d.broken.get(word, [])
    pr = [p_plain(w, word, a[0]), p_plain(w, word, u[0]), p_called(w, word, a[1]),
          p_whos(w, word, a[2]), p_explicit(w, word, u[-1]),
          p_yn_base(w, a[3], CHAIN[word][0]), p_rev(w, a[4], CHAIN[word][0])]
    if b:
        pr.append(p_broken(w, word, b[0]))
    pr.extend(extra)
    return pr


def _spec(d: _Day, words, probes, category, fault=None):
    assert 6 <= len(probes) <= 12, (category, len(probes))
    return {"script": list(d.script), "probes": probes, "words": list(words),
            "category": category, "fault": fault}


# ----- clean shapes
def c_one_word(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    d.ask(MG)
    d.say("Thanks!")
    return _spec(d, [MG], _std_probes(d, MG, extra=[p_unknown(d.w, MG)]), "one word")


def c_big_world(seed):
    d = _Day(seed)
    d.people(MG, 10, 3, 1)
    d.w.filler(30, d.rng)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    pr = _std_probes(d, MG, extra=[p_plain(w, MG, d.unasked[MG][1]), p_yn_word(w, MG, d.asked[MG][5])])
    return _spec(d, [MG], pr, "big world")


def c_decoy_word(seed):
    d = _Day(seed)
    d.people(FOM, 9, 2, 1)
    d.people(BOS, 1, 1, 0)
    d.flush_teach()
    d.ask(FOM)
    d.ask(BOS)                                    # one lonely episode: not enough to learn
    w = d.w
    w.learned = {FOM}
    pr = _std_probes(d, FOM, extra=[p_plain(w, BOS, d.asked[BOS][0]),
                                    p_plain(w, BOS, d.unasked[BOS][0])])
    return _spec(d, [FOM], pr, "decoy word")


def c_two_words(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    for s in d.asked[MG] + d.unasked[MG]:
        d.w.chain(FOM, s)                          # same families, grandfather side too
    d.asked[FOM] = list(d.asked[MG])
    d.unasked[FOM] = list(d.unasked[MG])
    d.flush_teach()
    d.ask(MG)
    d.ask(FOM)
    w = d.w
    pr = _std_probes(d, MG, extra=[p_plain(w, FOM, d.asked[MG][5]),
                                   p_whos(w, FOM, d.unasked[MG][1]),
                                   p_yn_base(w, d.w.truth[(d.asked[MG][6], "mother")], "father")])
    return _spec(d, [MG, FOM], pr, "two words")


def c_two_spouse_words(seed):
    # separate couples per word: a spouse with both a boss and a teacher taught makes the
    # loop read "boss of spouse" as a plain spouse question (loop behaviour, not a fault)
    d = _Day(seed)
    d.people(BOS, 9, 2, 1)
    d.people(TOS, 9, 1, 0)
    d.flush_teach()
    d.ask(BOS, style="mixed")
    d.ask(TOS)
    w = d.w
    pr = _std_probes(d, BOS, extra=[p_plain(w, TOS, d.asked[TOS][4]),
                                    p_called(w, TOS, d.unasked[TOS][0])])
    return _spec(d, [BOS, TOS], pr, "two words")


def c_earlier_night(seed, first=MG, second=FOM, big=0):
    d = _Day(seed)
    d.people(first, 9, 1, 0)
    if big:
        d.w.filler(big, d.rng)
    d.flush_teach()
    d.ask(first)
    d.night()
    d.people(second, 9, 2, 1)
    d.flush_teach()
    d.ask(second)
    w = d.w
    pr = _std_probes(d, second, extra=[p_plain(w, first, d.asked[first][2]),
                                       p_called(w, first, d.unasked[first][0])])
    return _spec(d, [first, second], pr, "word from an earlier night")


def c_corrections(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    w = d.w
    a0, u0 = d.asked[MG][0], d.unasked[MG][0]
    m_a = w.truth[(a0, "mother")]
    d.say(w.put(m_a, "mother", w.new(), correct=True))        # fix before the questions
    d.ask(MG)
    m_u = w.truth[(u0, "mother")]
    d.say(w.put(m_u, "mother", w.new(), correct=True))        # fix an unasked family late
    pr = _std_probes(d, MG, extra=[p_base(w, m_u, "mother")])
    return _spec(d, [MG], pr, "corrections during the day")


def c_varied_phrasing(seed):
    d = _Day(seed)
    d.people(MG, 10, 2, 1)
    d.flush_teach()
    d.ask(MG, style="mixed")
    d.say("Hi", "Thanks!")
    w = d.w
    pr = _std_probes(d, MG, extra=[p_tell(w, MG, d.unasked[MG][1]), p_comp(w, MG, d.asked[MG][5])])
    return _spec(d, [MG], pr, "varied phrasings")


def c_three_hop(seed):
    d = _Day(seed)
    d.people(DMF, 9, 2, 1)
    d.flush_teach()
    d.ask(DMF)
    w = d.w
    pr = _std_probes(d, DMF, extra=[p_base(w, d.asked[DMF][5], "mother")])
    return _spec(d, [DMF], pr, "three-hop word")


def c_later_teaching(seed):
    d = _Day(seed)
    d.people(BOM, 9, 2, 1)
    d.flush_teach()
    d.ask(BOM)
    w = d.w
    a = d.asked[BOM]
    m = w.truth[(a[0], "mother")]
    pr = [p_plain(w, BOM, a[0]), p_teach(w, m, "boss", w.new(), correct=True),
          p_plain(w, BOM, a[0])]
    nk, nm = w.new(), w.new()
    pr += [p_teach(w, nk, "mother", nm), p_teach(w, nm, "boss", w.new()),
           p_plain(w, BOM, nk), p_plain(w, BOM, d.unasked[BOM][0]), p_whos(w, BOM, a[3]),
           p_yn_base(w, a[4], "mother")]
    return _spec(d, [BOM], pr, "teaching after the night")


def c_teacher_father_big(seed):
    d = _Day(seed)
    d.people(TOF, 9, 2, 1)
    d.w.filler(25, d.rng)
    d.flush_teach()
    d.ask(TOF)
    w = d.w
    pr = _std_probes(d, TOF, extra=[p_unknown(w, TOF)])
    return _spec(d, [TOF], pr, "big world")


def c_incomplete_decoys(seed):
    d = _Day(seed)
    d.people(DOS, 9, 2, 3)
    d.flush_teach()
    d.ask(DOS)
    d.ask(DOS, people=d.broken[DOS][1:])          # questions that cannot queue an episode
    w = d.w
    pr = _std_probes(d, DOS, extra=[p_broken(w, DOS, d.broken[DOS][2]), p_yn_word(w, DOS, d.asked[DOS][6])])
    return _spec(d, [DOS], pr, "decoy questions")


def c_doctor_boss(seed):
    d = _Day(seed)
    d.people(DOB, 10, 2, 1)
    d.flush_teach()
    d.ask(DOB, style="mixed")
    w = d.w
    pr = _std_probes(d, DOB, extra=[p_tell(w, DOB, d.unasked[DOB][1])])
    return _spec(d, [DOB], pr, "one word")


def c_teacher_mother_fix(seed):
    d = _Day(seed)
    d.people(TOM, 9, 2, 1)
    d.flush_teach()
    w = d.w
    u = d.unasked[TOM][0]
    m = w.truth[(u, "mother")]
    d.say(w.put(m, "teacher", w.new(), correct=True))
    d.ask(TOM)
    pr = _std_probes(d, TOM, extra=[p_base(w, m, "teacher")])
    return _spec(d, [TOM], pr, "corrections during the day")


def c_boss_father_decoy(seed):
    d = _Day(seed)
    d.people(BOF, 9, 2, 1)
    d.people(MG, 1, 1, 0)
    d.flush_teach()
    d.ask(BOF)
    d.ask(MG)
    w = d.w
    w.learned = {BOF}
    pr = _std_probes(d, BOF, extra=[p_plain(w, MG, d.asked[MG][0]), p_explicit(w, MG, d.unasked[MG][0])])
    return _spec(d, [BOF], pr, "decoy word")


def c_direct_taught(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    w = d.w
    lone, lg = w.new(), w.new()
    w.put(lone, MG, lg)                            # a word row taught directly, no chain
    d.flush_teach()
    d.ask(MG)
    pr = _std_probes(d, MG, extra=[p_plain(w, MG, lone), p_called(w, MG, lone)])
    return _spec(d, [MG], pr, "word taught directly")


def c_repeat_great(seed):
    d = _Day(seed)
    d.people(MG, 8, 2, 1)
    w = d.w
    a = d.asked[MG]
    w.ensure(w.word_answer(a[5], MG), "mother")    # a great-grandmother for one family
    d.flush_teach()
    d.ask(MG, times=2)
    pr = _std_probes(d, MG, extra=[p_comp(w, MG, a[5]), p_comp(w, MG, a[6])])
    return _spec(d, [MG], pr, "repeated questions")


def c_three_words(seed):
    d = _Day(seed)
    d.people(MOS, 9, 2, 1)
    d.people(TOS, 9, 1, 0)
    d.people(BOS, 9, 1, 0)
    d.flush_teach()
    d.ask(MOS)
    d.ask(TOS)
    d.ask(BOS)
    w = d.w
    pr = _std_probes(d, MOS, extra=[p_plain(w, TOS, d.asked[TOS][6]), p_plain(w, BOS, d.unasked[BOS][0]),
                                    p_whos(w, BOS, d.asked[BOS][7])])
    return _spec(d, [MOS, TOS, BOS], pr, "three words")


# ----- fault shapes
def f_made_up(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 2)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    pr = _std_probes(d, MG, extra=[p_broken(w, MG, d.broken[MG][1]), p_unknown(w, MG)])
    return _spec(d, [MG], pr, "made-up answers", ("made_up_incomplete", {"word": MG}))


def f_silent_noop(seed):
    d = _Day(seed)
    d.people(FOM, 10, 2, 1)
    d.flush_teach()
    d.ask(FOM)
    pr = _std_probes(d, FOM)
    return _spec(d, [FOM], pr, "silent no-op", ("silent_noop", {}))


def f_not_persisted(seed):
    d = _Day(seed)
    d.people(MG, 10, 3, 1)
    d.w.filler(25, d.rng)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    pr = _std_probes(d, MG, extra=[p_plain(w, MG, d.unasked[MG][1])])
    return _spec(d, [MG], pr, "lost on restart", ("not_persisted", {}))


def f_stale_snapshot(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    a = d.asked[MG]
    m = w.truth[(a[1], "mother")]
    nk, nm = w.new(), w.new()
    pr = [p_plain(w, MG, a[1]), p_teach(w, m, "mother", w.new(), correct=True),
          p_plain(w, MG, a[1]), p_teach(w, nk, "mother", nm), p_teach(w, nm, "mother", w.new()),
          p_plain(w, MG, nk), p_plain(w, MG, d.unasked[MG][0]), p_whos(w, MG, a[2]),
          p_rev(w, a[3], "mother")]
    return _spec(d, [MG], pr, "broken later teaching", ("stale_snapshot", {"word": MG}))


def f_teach_to_scrap(seed):
    d = _Day(seed)
    d.people(BOM, 9, 2, 1)
    d.flush_teach()
    d.ask(BOM)
    w = d.w
    a = d.asked[BOM]
    nk, nm = w.new(), w.new()
    pr = [p_plain(w, BOM, a[0]), p_teach(w, nk, "mother", nm), p_base(w, nk, "mother"),
          p_teach(w, nm, "boss", w.new()), p_plain(w, BOM, nk), p_called(w, BOM, a[2]),
          p_plain(w, BOM, d.unasked[BOM][0]), p_yn_base(w, a[3], "mother")]
    return _spec(d, [BOM], pr, "lost writes after the night", ("teach_to_scrap", {}))


def f_materialize(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    a = d.asked[MG]
    pr = _std_probes(d, MG, extra=[p_yn_word(w, MG, a[5]), p_yn_word(w, MG, d.unasked[MG][1])])
    return _spec(d, [MG], pr, "notebook writes", ("materialize_rows", {"word": MG}))


def f_overwrite(seed):
    d = _Day(seed)
    d.people(MG, 9, 3, 1)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    u = d.unasked[MG][2]
    pr = _std_probes(d, MG, extra=[p_base(w, u, "mother"), p_plain(w, MG, u)])
    return _spec(d, [MG], pr, "taught facts changed", ("overwrite_taught", {"word": MG, "who": u}))


def f_alias(seed):
    d = _Day(seed)
    d.people(TOS, 9, 2, 1)
    d.flush_teach()
    d.ask(TOS)
    w = d.w
    a = d.asked[TOS]
    pr = _std_probes(d, TOS, extra=[p_base(w, a[6], "spouse"), p_plain(w, TOS, a[6])])
    return _spec(d, [TOS], pr, "identity damage", ("alias_merge", {"word": TOS, "who": a[6]}))


def f_forget_old(seed):
    s = c_earlier_night(seed, MG, FOM)
    s.update(category="forgetting", fault=("forget_old_word", {}))
    return s


def f_forget_old_disk(seed):
    s = c_earlier_night(seed, BOS, DOS, big=10)
    s.update(category="lost on restart", fault=("forget_old_on_disk", {}))
    return s


def f_minority(seed):
    d = _Day(seed)
    d.people(MG, 10, 2, 1)
    d.w.filler(20, d.rng)
    # add unasked families until one start falls in the fault's minority
    extra = []
    while not any(_minority(x) for x in extra):
        extra.append(d.w.chain(MG))
    d.unasked[MG] = [x for x in extra if _minority(x)][:1] + d.unasked[MG]
    d.flush_teach()
    asked = [x for x in d.asked[MG]]
    d.ask(MG)
    w = d.w
    safe = [x for x in asked if not _minority(x)]
    pr = [p_plain(w, MG, safe[0]), p_plain(w, MG, d.unasked[MG][0]), p_called(w, MG, safe[1]),
          p_plain(w, MG, d.unasked[MG][1]), p_explicit(w, MG, d.unasked[MG][0]),
          p_yn_base(w, asked[3], "mother"), p_rev(w, asked[4], "mother"),
          p_broken(w, MG, d.broken[MG][0])]
    return _spec(d, [MG], pr, "wrong for a minority", ("minority_wrong", {"word": MG}))


def f_stale_correction(seed):
    d = _Day(seed)
    d.people(FOM, 9, 2, 1)
    d.flush_teach()
    w = d.w
    u = d.unasked[FOM][0]
    m = w.truth[(u, "mother")]
    d.say(w.put(m, "father", w.new(), correct=True))
    d.ask(FOM)
    pr = _std_probes(d, FOM, extra=[p_plain(w, FOM, u), p_base(w, m, "father")])
    return _spec(d, [FOM], pr, "ignores corrections", ("stale_correction", {"word": FOM}))


def f_memorized(seed):
    d = _Day(seed)
    d.people(TOM, 9, 2, 1)
    d.flush_teach()
    d.ask(TOM)
    w = d.w
    pr = _std_probes(d, TOM, extra=[p_called(w, TOM, d.unasked[TOM][1])])
    return _spec(d, [TOM], pr, "over-abstaining", ("memorized_only", {"word": TOM}))


def f_compositional(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    w = d.w
    a = d.asked[MG]
    w.ensure(w.word_answer(a[5], MG), "mother")
    d.flush_teach()
    d.ask(MG)
    pr = _std_probes(d, MG, extra=[p_comp(w, MG, a[5]), p_explicit(w, MG, a[6])])
    return _spec(d, [MG], pr, "over-abstaining", ("compositional_abstain", {"word": MG}))


def f_called(seed):
    d = _Day(seed)
    d.people(BOF, 9, 2, 1)
    d.flush_teach()
    d.ask(BOF)
    w = d.w
    pr = _std_probes(d, BOF, extra=[p_called(w, BOF, d.unasked[BOF][1])])
    return _spec(d, [BOF], pr, "paraphrase damage", ("called_route_wrong", {"word": BOF}))


def f_contraction(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    pr = _std_probes(d, MG, extra=[p_whos(w, MG, d.unasked[MG][1])])
    return _spec(d, [MG], pr, "paraphrase damage", ("contraction_broken", {}))


def f_slot_mixup(seed):
    s = c_two_words(seed)
    s.update(category="word mix-up", fault=("slot_mixup", {"src": MG, "dst": FOM}))
    return s


def f_base_damaged(seed):
    d = _Day(seed)
    d.people(MG, 9, 2, 1)
    d.flush_teach()
    d.ask(MG)
    w = d.w
    a = d.asked[MG]
    pr = _std_probes(d, MG, extra=[p_base(w, a[5], "mother")])
    return _spec(d, [MG], pr, "base skill damage", ("base_mother_damaged", {"word": MG}))


def f_reverse(seed):
    d = _Day(seed)
    d.people(MOS, 9, 2, 1)
    d.flush_teach()
    d.ask(MOS)
    w = d.w
    pr = _std_probes(d, MOS, extra=[p_rev(w, d.unasked[MOS][0], "spouse")])
    return _spec(d, [MOS], pr, "reverse lookup damage", ("reverse_broken", {"word": MOS}))


def f_extra_word(seed):
    s = c_decoy_word(seed)
    s.update(category="skipped evidence gate", fault=("extra_word", {"word": BOS}))
    return s


_CLEAN = [c_one_word, c_big_world, c_decoy_word, c_two_words, c_two_spouse_words,
          lambda sd: c_earlier_night(sd, MG, FOM),
          lambda sd: c_earlier_night(sd, BOS, MOS),
          c_corrections, c_varied_phrasing, c_three_hop, c_later_teaching,
          c_teacher_father_big, c_incomplete_decoys, c_doctor_boss, c_teacher_mother_fix,
          c_boss_father_decoy, lambda sd: c_earlier_night(sd, FOM, MG, big=20),
          c_direct_taught, c_repeat_great, c_three_words]
_FAULT = [f_made_up, f_silent_noop, f_not_persisted, f_stale_snapshot, f_teach_to_scrap,
          f_materialize, f_overwrite, f_alias, f_forget_old, f_forget_old_disk, f_minority,
          f_stale_correction, f_memorized, f_compositional, f_called, f_contraction,
          f_slot_mixup, f_base_damaged, f_reverse, f_extra_word]
assert len(_CLEAN) == 20 and len(_FAULT) == 20


def _make_cases():
    rng = random.Random(364_5)
    builders = [("clean", b) for b in _CLEAN] + [("fault", b) for b in _FAULT]
    rng.shuffle(builders)
    seeds = list(range(341, 381))
    rng.shuffle(seeds)
    cases, specs = [], {}
    for i, ((kind, build), seed) in enumerate(zip(builders, seeds), 1):
        cid = f"slp364e-{i:02d}"
        spec = build(seed)
        spec["seed"] = seed
        spec["kind"] = kind
        specs[cid] = spec
        cases.append({"id": cid, "kind": kind, "category": spec["category"], "seed": seed,
                      "probes": [t for t, _ in spec["probes"]]})
    return cases, specs


CASES, _SPECS = _make_cases()


# ------------------------------------------------------------------ run
def run_case(case: dict, state_dir, fault: bool = True):
    """Build the loop, play the day (earlier nights included), arm the fault; return the
    loop BEFORE the case's night. fault=False gives the fault-off twin."""
    spec = _SPECS[case["id"]]
    loop = T360.build(str(state_dir), spec["seed"], "P")
    day: list[tuple[str, str]] = []
    script = spec["script"]
    for text in script:
        if text == "#NIGHT":                      # an earlier night, before the fault exists
            T360.force_sleep(loop)
            day.append(("#NIGHT", ""))
        else:
            day.append((text, T360.say(loop, text)))
    if fault and spec["kind"] == "fault":
        _install_arm(_Ctx(loop, spec))
    loop.bench364e_day = day
    loop.bench364e_episodes = dict(Counter(e.get("word_name")
                                           for e in getattr(loop.reasoner, "episodes", [])))
    return loop


def expectations(case_id: str) -> list:
    """Per-probe grades for the check script (private spec)."""
    return [g for _, g in _SPECS[case_id]["probes"]]


def expected_words(case_id: str) -> list[str]:
    return list(_SPECS[case_id]["words"])


def grade(reply: str, g) -> bool | None:
    if g is None:
        return None
    r = reply.strip()
    if g[0] == "is":
        return r.endswith(f" is {g[1]}.")
    if g[0] == "dk":
        return "don't know" in r.lower()
    if g[0] == "yes":
        return r.startswith("Yes")
    if g[0] == "no":
        return r.startswith("No")
    if g[0] == "rev":
        return r.startswith(f"{g[1]}'s ")
    if g[0] == "nofab":
        return f"'s {_rt(g[1])} is " not in r and not r.startswith("I didn't understand")
    if g[0] == "saved":
        return r.startswith(("Saved", "Updated"))
    return None


if __name__ == "__main__":
    kinds = Counter(c["kind"] for c in CASES)
    print(len(CASES), dict(kinds))
    for c in CASES:
        s = _SPECS[c["id"]]
        print(c["id"], c["kind"], c["seed"], c["category"], s["words"],
              s["fault"][0] if s["fault"] else "-", len(c["probes"]), len(s["script"]))
