"""The night pipeline: sleepb.py's ab_ob_b4_nb recipe, ported to a Backend interface.

tag the day's facts -> names re-read pass -> NREM cards (paraphrases + Q&A, checked by the base model) ->
LoRA training in 4 cycles (NREM steps, then REM two-step dreams written by the current adapter, then REM+NREM steps) with
open-book rehearsal, replay of earlier nights' cards and a KL leash to the base -> downscale (SHY) -> morning gate.

A chunk may end at any generate batch or training step (Stop): the night's state, a generation cache and the adapter are on disk, and the
next chunk resumes. See README.md for what is ported faithfully and what is simplified.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import math
import random
import re
import shutil
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date as _date
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import diary as diary_mod
from . import gate as gate_mod
from . import lessons as L_mod
from . import prompts as P
from .backend import Backend, Clock, Stop
from .corpus import Diary, has_ans, norm, pat
from .paths import Paths, read_json, write_json

GENERIC = {"ben", "i", "me", "my", "we", "you", "he", "she", "they", "it", "user", "the user", "someone", "somebody"}
IMP_RE = re.compile(r"remember|important|don'?t forget", re.I)
COR_RE = re.compile(r"\bactually\b|correction|no, it'?s", re.I)
NREM_SHARE = [0.80, 0.65, 0.50, 0.35]
NAMES_CAP = 6
RESLEEP_TURNS = 5
PHASES = ["tag", "dream", "train", "downscale", "gate", "done"]

GENERIC_PROMPTS = (
    ["What is the capital of France?", "How many days are in a leap year?", "Translate 'good morning' into Spanish.", "What is 17 times 23?",
     "Give me a recipe idea for dinner with rice and beans.", "What is the difference between weather and climate?", "Suggest a name for a pet goldfish.",
     "How do I politely decline an invitation?", "What is the boiling point of water in Fahrenheit?", "Write a two-line poem about autumn.",
     "Who wrote Romeo and Juliet?", "Explain what a prime number is.", "What are three tips for studying effectively?", "Convert 5 kilometres to miles.",
     "What does DNA stand for?", "Write a polite email asking for a deadline extension.", "What is the largest planet in our solar system?",
     "Why is the sky blue?", "Give me a synonym for 'happy'.", "Write a Python function that reverses a string."]
    + ["Explain %s in two sentences." % t for t in ("volcanoes", "bread", "the moon", "bicycles", "photosynthesis", "tea", "honeybees", "chess")]
    + ["Give me three fun facts about %s." % t for t in ("the ocean", "jazz", "glaciers", "the internet", "dinosaurs", "coffee")])


def dc_total(stats: dict) -> Optional[dict]:
    """The night's dream-check counts, NREM cards and every REM cycle added up."""
    parts = [stats.get("dreamcheck")] + [r.get("dreamcheck") for r in stats.get("rem", []) if isinstance(r, dict)]
    parts = [p for p in parts if isinstance(p, dict) and p.get("n")]
    if not parts:
        return None
    out = {"available": all(p.get("available", True) for p in parts)}
    for k in ("n", "supported", "contradicted", "unknown", "unchecked", "dropped", "elapsed_s"):
        out[k] = sum(p.get(k, 0) or 0 for p in parts)
    reasons = [p.get("reason") for p in parts if p.get("reason")]
    if reasons:
        out["reason"] = reasons[0]
    return out


# ---------------------------------------------------------------- config
@dataclass
class Config:
    who: str = "Ben"
    seed: int = 0
    bsz: int = 16                 # cards per training step (sleepb --bsz)
    replay_bsz: int = 8           # KL replay examples per step
    lr: float = 2e-4
    shy_factor: float = 0.85
    shy_thresh: float = 0.05
    max_dream_items: int = 160    # sleepb defaults; each x work scale s
    rem_chains: int = 30
    rem_gist: int = 30
    gist_min_days: int = 3
    ob_share: float = 0.5
    ref_steps: int = 150          # reference night length used to plan the work scale (sleepb: 150 with no schedule)
    min_cards: int = 12           # fewer trainable cards than this: dry run, not an error
    min_item_days: int = 1        # sleepb: 2 (a fact must recur); 1 lets a first, single-day diary train
    holdout_frac: float = 0.10
    night_budget_s: Optional[float] = None   # s = clip(B / R, 0.25, 4); None = this chunk's budget
    scale: Optional[float] = None            # pin s (tests)
    ckpt_every: int = 10
    card_shape: str = "model"     # "templated12": per fact the raw note + 5 rewrites + 6 Q&A from templates, no model (data A/B arm B), instead of model-written cards
    max_seq_len: int = 640        # training sequences longer than this fall back to closed-book
    harm_max: float = gate_mod.HARM_MAX
    gate_min_gain: int = gate_mod.MIN_GAIN   # held-out cards the night must add over the adapter it started from (gate.decide)
    verify_tokens: int = 20
    kl_every: int = 1             # KL replay every n-th step (CPU profile: 4)
    gate_n: int = 40              # general questions in the gate
    gate_max_tokens: int = 24
    llama_cpp_dir: Optional[str] = None      # set: export a GGUF LoRA when a night commits (torch backend)
    gguf_base_dir: Optional[str] = None      # the HF base model dir the converter needs
    dreamcheck: bool = True                  # check the night's Q&A dreams against the diary before training (dreamhook.py)
    dreamcheck_share: float = 0.10           # at most this share of the night's budget goes to it (the rest stay unchecked, kept)
    llama_server: Optional[str] = None       # set with base_gguf: check the exported adapter inside llama-server (served.py)
    base_gguf: Optional[str] = None          # the GGUF the daytime model serves (must be the same base as the profile)
    # Extra sources (lessons.py). Not part of ab_ob_b4_nb: they only add cards to the same pool; every setting above is unchanged.
    use_lessons: bool = True      # post-mortems of the day's failures -> lesson cards (and corrections retire the fact they replace)
    max_lessons: int = 8          # lessons written per night (x work scale)
    lesson_tokens: int = 200
    use_habits: bool = True       # the same tool job on habit_min+ turns -> habit cards
    habit_min: int = 3
    use_userdata: bool = True     # the Desk's saved notes (memory.json) and Keeping track of list (tracking.md)


def clip_scale(budget_s: float, t_step: float, t_gen: float, ref_steps: int, ref_gen_batches: float) -> float:
    """sleepb.plan_scale: s = clip(B / R, 0.25, 4), R = ref_steps x t_step + ref_gen_batches x t_gen."""
    r = ref_steps * t_step + ref_gen_batches * t_gen
    return min(max(budget_s / r, 0.25), 4.0) if r > 0 else 4.0


def ref_gen_batches(gen_bs: int, max_items: int = 160, rem_chains: int = 30, rem_gist: int = 30) -> float:
    nb = lambda n: -(-n // gen_bs)  # noqa: E731
    return nb(max_items) * 400 / 20 + nb(max_items * P.K) + 2 * nb(max_items) + 4 * (nb(rem_chains + rem_gist) * 40 / 20 + nb(rem_chains + rem_gist))


def rem_plan(steps: int) -> List[Tuple[int, int]]:
    """Per-cycle (NREM steps, REM steps): the quarters of `steps`, NREM_SHARE of each, the rest REM."""
    cyc = [steps // 4 + (1 if i < steps % 4 else 0) for i in range(4)]
    return [(round(c * NREM_SHARE[i]), c - round(c * NREM_SHARE[i])) for i, c in enumerate(cyc)]


def cosine_lr(lr: float, i: int, n: int) -> float:
    return lr * 0.5 * (1 + math.cos(math.pi * i / max(n, 1)))


# ---------------------------------------------------------------- items
def key_of(a: str, b: str) -> str:
    return norm(a) + "|" + norm(b)


@dataclass
class Item:
    key: str
    subj: str
    obj: str
    rel: str
    born: int
    first: int = 0
    days: int = 0
    nment: int = 0
    imp: bool = False
    cor: bool = False
    para: List[str] = field(default_factory=list)
    qa: List[List[str]] = field(default_factory=list)      # trainable [q, a]
    held: List[dict] = field(default_factory=list)         # held-out cards {q, a, dir, night}: never trained on
    seen_ment: int = -1
    dirty: bool = False
    fails: int = 0
    dead: bool = False
    trained: bool = False
    dreamed_night: int = 0
    kind: str = "fact"            # fact (tagged from the diary) | lesson | habit | note | track (lessons.py; their cards are made, not dreamed)
    source: str = ""              # where a non-fact item came from (kept on its cards)
    until: str = ""               # YYYY-MM-DD: after this day the item is not trained (tracked items)

    @property
    def fact(self) -> str:
        if self.kind != "fact":
            return "%s: %s" % (self.kind, self.source or self.obj)
        return "%s %s %s." % (self.subj, self.rel, self.obj)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def other(it: Item, x: str) -> Tuple[str, str]:
    return (it.subj, it.obj) if norm(it.subj) == x else (it.obj, it.subj)


def bridge_roles(p: Item, q: Item, x: str, k: int) -> Tuple[str, str, str]:
    (mid, fp), fq = other(p, x), other(q, x)[1]
    return (fp, fq, mid) if k % 2 == 0 else (fq, fp, mid)


NAME_TOK = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")
NAME_STOP = {norm(w) for w in ("Ben I I'm I've I'll I'd OK Ok Okay Hey Hi Hello Thanks Also Anyway But And So The A An My It This That English Christmas God Mom Dad "
                               "Yes No Yeah Please Sorry Well Oh Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June "
                               "July August September October November December".split())} | GENERIC


def cap_names(text: str) -> List[str]:
    """Capitalised words that are NOT sentence-initial."""
    text, out = text.replace("’", "'"), []
    for m in NAME_TOK.finditer(text):
        w = m.group()
        w = w[:-2] if w.lower().endswith("'s") else w
        if len(w) < 2 or not w[0].isupper() or norm(w) in NAME_STOP:
            continue
        pre = text[:m.start()]
        before = pre.rstrip(" \t\r\n\"'“‘([")
        if not before or "\n" in pre[len(before):] or before[-1] in ".!?":
            continue
        out.append(w)
    return out


def triple_status(diary: Diary, dropped: set, ti: int, sj: str, ob: str) -> str:
    if min(len(sj), len(ob)) < 2 or max(len(sj), len(ob)) > 60 or norm(sj) == norm(ob) or norm(sj) in GENERIC or norm(ob) in GENERIC:
        return "invalid"
    if ti not in diary.occurs(sj) or ti not in diary.occurs(ob):
        return "not_in_turn"
    return "dropped" if key_of(sj, ob) in dropped else "ok"


# ---------------------------------------------------------------- generation cache
class GenCache:
    """Generated texts by (prompt, max_tokens, mode, salt), appended to a jsonl as each batch finishes: a resumed chunk redoes no finished batch."""

    def __init__(self, path: Optional[Path]):
        self.path, self.d = path, {}
        if path and Path(path).exists():
            for line in Path(path).read_text().splitlines():
                try:
                    r = json.loads(line)
                    self.d[r["k"]] = r["v"]
                except (ValueError, KeyError):
                    pass

    @staticmethod
    def key(prompt, max_tokens, sample, base, salt) -> str:
        return hashlib.sha1(json.dumps([prompt, max_tokens, bool(sample), bool(base), salt]).encode()).hexdigest()

    def put_many(self, items: List[Tuple[str, str]]) -> None:
        for k, v in items:
            self.d[k] = v
        if self.path:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with open(str(self.path), "a") as f:
                for k, v in items:
                    f.write(json.dumps({"k": k, "v": v}) + "\n")


def next_day(week: dict, st: dict) -> Optional[Tuple[int, str]]:
    """The oldest day not slept yet. A slept day with at least RESLEEP_TURNS new turns since (the Desk was used after the night) counts as new again.
    A day already found too small with the same turns ("small") is passed over, so a thin day never blocks the days after it (its cards
    stay in items.json and are trained with a later night's)."""
    dates = week.get("dates", {})
    for k in sorted(dates, key=int):
        date = dates[k]
        n = sum(1 for t in week["diary"] if t["role"] == "user" and t["day"] == int(k))
        if date not in st.get("slept_days", []):
            if st.get("small", {}).get(date) == n:
                continue
            return int(k), date
        if n >= st.get("slept_turns", {}).get(date, 10 ** 9) + RESLEEP_TURNS:
            return int(k), date
    return None


# ---------------------------------------------------------------- the sleeper
class Sleeper:
    def __init__(self, backend: Backend, R, prof, cfg: Config, paths: Paths, clock: Clock, log: Callable[[str], None] = print):
        self.be, self.R, self.prof, self.cfg, self.paths, self.clock, self.log = backend, R, prof, cfg, paths, clock, log
        self.who = cfg.who
        self.sec_per_batch_tok = None   # seconds per generated token per batch (measured)
        self.t_step = None
        self.exporter = None            # tests inject a fake exporter
        self.served_checker = None      # and a fake served check
        self.dream_checker = None       # and a fake dream checker: item -> verdict
        self.leak = {norm(q) for q, _ in gate_mod.GENERAL_QA}
        self.today = lambda: _date.today().isoformat()   # expiry of tracked items is checked against the real date (tests pin it)

    # ---- persistence
    def load_items(self):
        d = read_json(self.paths.items, {}) or {}
        self.items: Dict[str, Item] = {k: Item.from_dict(v) for k, v in d.get("items", {}).items()}
        self.rem_pool: List[dict] = d.get("rem_pool", [])
        self.rem_done = Counter(d.get("rem_done", {}))
        self.gist_done = Counter(d.get("gist_done", {}))
        self.dropped = set(d.get("dropped", []))
        self.wrong: Dict[str, set] = {k: set(v) for k, v in (d.get("wrong") or {}).items()}   # name -> values a correction said are wrong

    def save_items(self):
        write_json(self.paths.items, {"items": {k: asdict(v) for k, v in self.items.items()}, "rem_pool": self.rem_pool,
                                      "rem_done": dict(self.rem_done), "gist_done": dict(self.gist_done), "dropped": sorted(self.dropped),
                                      "wrong": {k: sorted(v) for k, v in self.wrong.items()}})

    def load_state(self):
        st = read_json(self.paths.state, {}) or {}
        st.setdefault("slept_days", [])
        st.setdefault("nights", 0)
        return st

    def save_night(self):
        write_json(self.paths.night_json, self.N)

    # ---- generation (batched, cached, deadline-aware)
    def gen(self, prompts: List[str], max_tokens: int, sample: bool = False, base: bool = True, salt: str = "", stops=()) -> List[str]:
        n = len(prompts)
        keys = [self.cache.key(p, max_tokens, sample, base, salt) for p in prompts]
        out: List[Optional[str]] = [self.cache.d.get(k) for k in keys]
        todo = sorted((i for i in range(n) if out[i] is None), key=lambda i: len(prompts[i]))
        bs = self.be.gen_batch
        for s in range(0, len(todo), bs):
            idx = todo[s:s + bs]
            est = (self.sec_per_batch_tok or 0.25) * max_tokens * 1.2 + 2
            self.clock.check(est)
            t0 = self.clock.now()
            res = self.be.generate([prompts[i] for i in idx], max_tokens, 0.8 if sample else 0.0, not base, tuple(stops))
            dt = self.clock.now() - t0
            self.sec_per_batch_tok = max(dt / max(max_tokens, 1), 1e-4) if self.sec_per_batch_tok is None else 0.7 * self.sec_per_batch_tok + 0.3 * dt / max(max_tokens, 1)
            self.cache.put_many([(keys[i], r) for i, r in zip(idx, res)])
            for i, r in zip(idx, res):
                out[i] = r
        return [o or "" for o in out]

    def think_gen(self, build: Callable[[bool], List[str]], answer_tokens: int, think_tokens: int, sample: bool = False, base: bool = True, salt: str = "") -> List[str]:
        """Two-stage reply for a thinking model: stage 1 thinks (capped, stops at the close tag), stage 2 = prompt + thinking + close tag, then the answer."""
        close = self.prof.think_close
        p1 = build(True)
        raw1 = self.gen(p1, think_tokens, sample, base, salt + ":think", stops=(close, self.prof.stop_token))
        th = [P.strip_think(x, close, self.prof.stop_token) for x in raw1]
        self.last_think = th
        return self.gen([p + x + close for p, (x, _) in zip(p1, th)], answer_tokens, sample, base, salt + ":ans")

    # ---- 1. tagging
    def tag(self, d: int, st: Counter) -> None:
        turns = [t for t in self.diary.turns if t["day"] == d]
        q = self.prof
        texts = [t["text"][:1500] for t in turns]
        if q.thinks and q.quirk("tag_think"):
            raw = self.think_gen(lambda th: [P.tag_prompt(self.R, x, self.who, th) for x in texts], 160, q.quirk("think_tokens"), salt="tag")
        else:
            raw = self.gen([P.tag_prompt(self.R, x, self.who) for x in texts], 160, salt="tag")
        for t, txt in zip(turns, raw):
            fx = P.parse_facts(txt)
            if fx is None:
                st["tag_parse_fail"] += 1
                fx = []
            elif not fx:
                st["tag_empty"] += 1
            got = []
            for f in fx[:5]:
                st["extracted"] += 1
                sj, rl, ob = (str(f.get(k) or "").strip() for k in ("subject", "relation", "object"))
                ck = triple_status(self.diary, self.dropped, t["i"], sj, ob)
                if ck != "ok":
                    if ck != "dropped":
                        st["dropped_" + ck] += 1
                    continue
                key = key_of(sj, ob)
                if key not in self.items:
                    self.items[key] = Item(key, sj, ob, rl or "is linked to", d)
                    st["new_items"] += 1
                got.append((sj, ob))
            st["kept"] += len(got)
        st["turns"] = len(turns)

    def names_pass(self, d: int, st: Counter) -> None:
        """Re-read the day for pairs of candidate names that no item links yet (addendum 8)."""
        turns = [t for t in self.diary.turns if t["day"] == d]
        vocab: Dict[str, str] = {}
        for t in self.diary.turns:
            if t["day"] <= d:
                for w in cap_names(t["text"]):
                    vocab.setdefault(norm(w), w)
        pats = {n: pat(n) for n in vocab}
        ask = []
        for t in turns:
            hits = sorted((m.start(), n) for n, p in pats.items() for m in [p.search(self.diary.low[t["i"]])] if m)
            names = [(n, vocab[n]) for _, n in hits]
            cnt = 0
            for (na, a), (nb, b) in itertools.combinations(names, 2):
                if any(k in self.items and not self.items[k].dead for k in (na + "|" + nb, nb + "|" + na)) or (na + "|" + nb) in self.dropped or (nb + "|" + na) in self.dropped:
                    continue
                ask.append((t, a, b))
                cnt += 1
                if cnt == NAMES_CAP:
                    break
        st["names_pairs"] = len(ask)
        if not ask:
            return
        q = self.prof
        if q.thinks and q.quirk("names_think"):
            raw = self.think_gen(lambda th: [P.names_prompt(self.R, t["text"][:1500], a, b, self.who, th) for t, a, b in ask], 12, q.quirk("think_tokens"), salt="names")
        else:
            raw = self.gen([P.names_prompt(self.R, t["text"][:1500], a, b, self.who) for t, a, b in ask], 12, salt="names")
        parse = P.parse_rel_neg if q.quirk("negative_word_parse") else P.parse_rel
        for (t, a, b), txt in zip(ask, raw):
            rl = parse(txt)
            if rl is None:
                continue
            st["names_yes"] += 1
            if triple_status(self.diary, self.dropped, t["i"], a, b) != "ok":
                continue
            key = key_of(a, b)
            if key not in self.items:
                self.items[key] = Item(key, a, b, rl or "is linked to", d)
                st["names_new_items"] += 1

    def refresh(self, d: int) -> None:
        for it in self.items.values():
            if it.dead or it.kind != "fact":
                continue
            idx = self.diary.containing(it.subj, it.obj, d)
            days = {self.diary.turns[i]["day"] for i in idx}
            it.nment, it.days, it.first = len(idx), len(days), (min(days) if days else it.born)
            it.imp = it.imp or any(IMP_RE.search(self.diary.turns[i]["text"]) for i in idx)
            it.cor = it.cor or any(COR_RE.search(self.diary.turns[i]["text"]) for i in idx)

    def elig(self, it: Item) -> bool:
        if it.kind != "fact":
            return not it.dead and (not it.until or it.until >= self.today())
        return not it.dead and (it.days >= self.cfg.min_item_days) and (it.days >= 2 or self.cfg.min_item_days <= 1 or it.imp or it.cor)

    def prio(self, it: Item) -> float:
        if it.kind in ("note", "track"):
            return 0.25  # the Desk already shows these in every turn: a weight copy is mostly redundant, and a long notes file must not crowd out the night's facts
        return max(it.days, 1) * (1 + it.imp + it.cor) * 2   # surprise = 1 always (no morning probes)

    # ---- 4. NREM cards
    def dream(self, d: int, E: List[Item], st: Counter) -> List[Item]:
        need = [it for it in E if it.kind == "fact" and (it.dirty or it.seen_ment < it.nment or (it.fails and not (it.para or it.qa)))]
        need.sort(key=lambda it: (-it.days, -it.nment))
        st["backlog"] = max(0, len(need) - self.cap_items)
        need = need[:self.cap_items]
        if self.cfg.card_shape == "templated12":
            return self.dream_templated(d, need, st)
        prompts, ctxs = [], {}
        for it in need:
            idx = self.diary.containing(it.subj, it.obj, d)[::-1][:4]
            ctxs[it.key] = self.diary.label(idx)
            prompts.append(P.nrem_prompt(self.R, ctxs[it.key], it.subj, it.obj, self.k, self.who))
        raw = self.gen(prompts, self.dream_tokens, sample=True, salt="dream")
        cp, cq = [], []
        for it, txt in zip(need, raw):
            ents = [it.subj, it.obj]
            paras, qas = P.parse_dream(txt)
            if not paras and not qas:
                st["parse_fail"] += 1
            for p in paras[:self.k]:
                st["paraphrases_gen"] += 1
                if self.leaky(p):
                    st["dropped_test_leak"] += 1
                elif self.says_wrong(it, p):
                    st["dropped_wrong_claim"] += 1
                elif not all(e.lower() in p.lower() for e in ents):
                    st["dropped_missing_entities"] += 1
                else:
                    cp.append((it, p.strip()))
            for q, ans in qas[:self.k]:
                st["qa_gen"] += 1
                es = [e for e in ents if e.lower() in ans.lower()]
                if self.leaky(q):
                    st["dropped_test_leak"] += 1
                elif self.says_wrong(it, q + " " + ans):
                    st["dropped_wrong_claim"] += 1
                elif len(es) != 1 or es[0].lower() in q.lower():
                    st["dropped_bad_answer"] += 1
                else:
                    cq.append((it, q.strip(), es[0], ctxs[it.key]))
        ver = self.gen([P.ctx_prompt(self.R, c, q, self.who) for _, q, _, c in cq], self.cfg.verify_tokens, salt="verify")
        res = defaultdict(lambda: {"p": [], "q": []})
        seen = set()
        for (it, q, ans, c), v in zip(cq, ver):
            if not has_ans(ans, v):
                st["dropped_unverified"] += 1
            elif (it.key, norm(q)) in seen or norm(q) in {norm(h["q"]) for h in it.held}:
                st["dropped_dup"] += 1
            else:
                seen.add((it.key, norm(q)))
                res[it.key]["q"].append([q, ans])
        for it, p in cp:
            if (it.key, norm(p)) in seen:
                st["dropped_dup"] += 1
            else:
                seen.add((it.key, norm(p)))
                res[it.key]["p"].append(p)
        done = []
        for it in need:
            g = res[it.key]
            if g["p"] or g["q"]:
                it.para, it.qa, it.fails, it.trained, it.dreamed_night = g["p"], g["q"], 0, False, d
                it.held = [h for h in it.held]  # held cards stay held across re-dreams
                st["items_with_dreams"] += 1
                done.append(it)
            elif not (it.para or it.qa):
                it.fails += 1
                st["items_failed"] += 1
            it.seen_ment, it.dirty = it.nment, False
            st["paraphrases_kept"] += len(g["p"])
            st["qa_kept"] += len(g["q"])
        st["items"] = len(need)
        return done

    def dream_templated(self, d: int, need: List[Item], st: Counter) -> List[Item]:
        """card_shape templated12: the newest diary message naming both sides + 5 rewrites as docs, 6 Q&A in both directions."""
        done = []
        for it in need:
            idx = self.diary.containing(it.subj, it.obj, d)
            note = self.diary.turns[idx[-1]]["text"][:300] if idx else it.fact
            paras, qas = P.templated_cards(it.subj, it.rel, it.obj, note)
            seen, g = {norm(h["q"]) for h in it.held}, {"p": [], "q": []}
            for kind, x in [("p", p) for p in paras] + [("q", qa) for qa in qas]:
                txt = x if kind == "p" else x[0]
                st["paraphrases_gen" if kind == "p" else "qa_gen"] += 1
                if norm(txt) in seen:
                    st["dropped_dup"] += 1
                elif kind == "q" and self.leaky(txt):
                    st["dropped_test_leak"] += 1
                else:
                    seen.add(norm(txt))
                    g[kind].append(x if kind == "p" else list(x))
            it.para, it.qa, it.fails, it.trained, it.dreamed_night = g["p"], g["q"], 0, False, d
            it.seen_ment, it.dirty = it.nment, False
            st["items_with_dreams"] += 1
            st["paraphrases_kept"] += len(g["p"])
            st["qa_kept"] += len(g["q"])
            done.append(it)
        st["items"] = len(need)
        return done

    def check_dreams(self, rows, kind: str) -> dict:
        """Dream check (dreamhook.py): drop CONTRADICTED Q&A dreams. rows: (owner, q, a), owner an Item (NREM card) or a rem_pool entry.
        An item whose every new Q&A card is contradicted loses its new paraphrases too (the fact itself is suspect)."""
        from . import dreamhook
        cfg, N = self.cfg, self.N
        if not cfg.dreamcheck or not rows:
            return {"available": False, "reason": "turned off (dreamcheck=False)", "n": len(rows), "unchecked": len(rows)} if rows else {"n": 0}
        B = cfg.night_budget_s or self.clock.budget_s
        spent = N.setdefault("dc_spent_s", 0.0)
        budget = max(0.0, min(cfg.dreamcheck_share * B - spent, self.clock.left() - 120.0))
        model = dreamhook.LocalChat(self.be, getattr(self.R, "tok", None), self.prof, adapter=False)
        src = lambda o: self.diary.label(self.diary.containing(o.subj, o.obj, N["day"])[-4:]) if isinstance(o, Item) else ""   # noqa: E731
        r = dreamhook.check([{"q": q, "a": a, "source": src(o)} for o, q, a in rows], model, str(self.paths.diary_dir), budget,
                            now=self.clock.now, checker=self.dream_checker, cache=N.setdefault("dc_cache", {}), log=self.log)
        N["dc_spent_s"] = spent + r["stats"].get("elapsed_s", 0.0)
        bad = {k for k, v in r["verdicts"].items() if v == "CONTRADICTED"}
        if bad:
            gone = set()
            for o, q, a in rows:
                if dreamhook.item_id(q, a) not in bad:
                    continue
                if isinstance(o, Item):
                    o.qa = [x for x in o.qa if not (x[0] == q and x[1] == a)]
                    if not o.qa:
                        o.para = []
                else:
                    gone.add(id(o))
            if gone:
                self.rem_pool = [x for x in self.rem_pool if id(x) not in gone]
        st = dict(r["stats"], kind=kind, dropped=len(bad))
        self.log("[night] dream check (%s): %s" % (kind, st))
        try:
            with open(str(self.paths.home / "dreamcheck.jsonl"), "a") as f:
                for o, q, a in rows:
                    f.write(json.dumps({"night": N["date"], "kind": kind, "q": q, "a": a, "verdict": r["verdicts"].get(dreamhook.item_id(q, a))}) + "\n")
        except OSError:
            pass
        return st

    def says_wrong(self, it: Item, text: str) -> bool:
        """Does a card text for `it` mention a value a correction said is wrong for one of its names (newest wins)?"""
        vals = (self.wrong.get(norm(it.subj), set()) | self.wrong.get(norm(it.obj), set())) - {norm(it.subj), norm(it.obj)}
        n = norm(text)
        return any(v and re.search(r"(?<!\w)" + re.escape(v) + r"(?!\w)", n) for v in vals)

    # ---- corrections, lessons, habits, notes (lessons.py)
    def turn_index(self, d: int, turn: int) -> Optional[int]:
        for t in self.diary.turns:
            if t["day"] == d and t.get("turn") == turn:
                return t["i"]
        return None

    def turn_items(self, ti: int) -> List[Item]:
        return [it for it in self.items.values() if not it.dead and it.kind == "fact" and ti in self.diary.occurs(it.subj) and ti in self.diary.occurs(it.obj)]

    def corrections(self, week: dict, d: int, st: Counter) -> None:
        """Ben corrected Glim: the facts stated in the correction get the corrected flag (higher priority), and an older fact about the
        same name that the correction replaces is retired (dead, never re-made) and its value is remembered as wrong for that name, so no
        positive card says it again. Replaced = same name and relation, or its value is what Glim said, or the correction says "not <it>"."""
        for f in L_mod.find_failures(week, d):
            if "correction" not in f["signals"]:
                continue
            ti = self.turn_index(d, f["turn"])
            if ti is None:
                continue
            st["corrections"] += 1
            nots = {norm(x): x for x in L_mod.not_terms(f["user"])}
            for it in self.turn_items(ti):
                it.cor = True
                for o in list(self.items.values()):
                    if o is it or o.dead or o.kind != "fact" or norm(o.subj) != norm(it.subj) or norm(o.obj) == norm(it.obj):
                        continue
                    if ti in self.diary.occurs(o.subj) and ti in self.diary.occurs(o.obj):
                        continue   # stated in the correction itself
                    said = o.obj.lower() in (f["prev_answer"] or "").lower()
                    if norm(o.rel) == norm(it.rel) or said or norm(o.obj) in nots:
                        o.dead = True
                        self.dropped.add(o.key)
                        self.wrong.setdefault(norm(it.subj), set()).add(norm(o.obj))
                        st["superseded"] += 1
                        self.log("[night] correction: '%s' replaces '%s'" % (it.fact, o.fact))
                for n, x in nots.items():
                    if n in (norm(it.subj), norm(it.obj)):
                        continue
                    self.wrong.setdefault(norm(it.subj), set()).add(n)
                    for k in (key_of(it.subj, x), key_of(x, it.subj)):
                        self.dropped.add(k)
                        if k in self.items and not self.items[k].dead:
                            self.items[k].dead = True
                            st["superseded"] += 1

    def wrong_for_turn(self, d: int, f: dict) -> set:
        ti = self.turn_index(d, f["turn"])
        out = set()
        for it in (self.turn_items(ti) if ti is not None else []):
            out |= self.wrong.get(norm(it.subj), set()) | self.wrong.get(norm(it.obj), set())
        if f["kind"] == "correction":
            out |= {norm(x) for x in L_mod.not_terms(f["user"])}
        return out

    def lessons_stage(self, week: dict, d: int, st: Counter) -> None:
        """Post-mortems of the day's failures (at most max_lessons x s), written by the base model, checked like other cards: the answer must
        be in the chat text (in Ben's own words for a correction), must not be a wrong value, and the base model must give it back from the
        chat text alone. A kept lesson is one text card and one question-answer card, trained with the night's other cards."""
        if not self.cfg.use_lessons:
            return
        date = self.N["date"]
        fails = [f for f in L_mod.find_failures(week, d) if L_mod.failure_key(date, f) not in self.items]
        st["failures"] = len(fails)
        for f in fails:
            st["failure_" + f["kind"]] += 1
        fails = fails[:self.sc(self.cfg.max_lessons)]
        if not fails:
            return
        ctxs = [L_mod.failure_context(f, self.who) for f in fails]
        raw = self.gen([P.lesson_prompt(self.R, c, L_mod.KIND_WORDS[f["kind"]], self.who) for f, c in zip(fails, ctxs)], self.cfg.lesson_tokens, salt="lesson")
        cand = []
        for f, c, txt in zip(fails, ctxs, raw):
            les = P.parse_lesson(txt)
            if les is None:
                st["lesson_parse_fail"] += 1
                continue
            wrong = self.wrong_for_turn(d, f)
            why = L_mod.lesson_ok(les, f, c, wrong)
            if why is None and self.leaky(les["q"]):
                why = "test_leak"
            if why:
                st["lesson_dropped_" + why] += 1
                continue
            cand.append((f, c, les, wrong))
        ver = self.gen([P.ctx_prompt(self.R, c, les["q"].strip(), self.who) for f, c, les, _ in cand], self.cfg.verify_tokens, salt="lesson_verify")
        for (f, c, les, wrong), v in zip(cand, ver):
            a = les["a"].strip().rstrip(".")
            if not has_ans(a, v):
                st["lesson_dropped_unverified"] += 1
                continue
            wv = " ".join(str(les.get("wrong_value") or "").split()).strip(" .")
            bad = {x for x in wrong | ({wv} if wv else set()) if norm(x) != norm(a)}
            text = L_mod.scrub(L_mod.lesson_text(les, f, date), bad)
            q = L_mod.scrub(les["q"].strip(), bad)
            key = L_mod.failure_key(date, f)
            self.items[key] = Item(key, "Glim", a, "lesson", d, first=d, days=1, nment=1, imp=True, cor=True, para=[text], qa=[[q, a]], seen_ment=1,
                                   dreamed_night=d, kind="lesson", source="chat %s, turn %d: %s" % (date, f["turn"] + 1, L_mod.KIND_WORDS[f["kind"]]))
            if f["kind"] == "correction" and wv and norm(wv) != norm(a):
                ti = self.turn_index(d, f["turn"])
                for it in (self.turn_items(ti) if ti is not None else []):
                    self.wrong.setdefault(norm(it.subj), set()).add(norm(wv))
            if text not in self.N.setdefault("lessons", []):
                self.N["lessons"].append(text)
            st["lessons_kept"] += 1

    def extras(self, week: dict, d: int, st: Counter) -> None:
        """Habit cards from repeated tool jobs, and cards for the Desk's saved notes and Keeping track of list. These cards are built from
        the logs and files word for word (no model writes them). Each carries its source; a tracked item past its until date, finished or
        removed, and a forgotten note, leave the training pool."""
        cfg, today, want = self.cfg, self.today(), {}
        if cfg.use_habits:
            for h in L_mod.habits(week, d, cfg.habit_min):
                para, qa = L_mod.habit_cards(h, self.who)
                src = "diary tool log: %d uses on %d days, %s to %s" % (h["n"], h["days"], diary_mod.date_of_day(week, h["first"]), diary_mod.date_of_day(week, h["last"]))
                want[h["key"]] = ("habit", h["target"], para, qa, src, "", h["days"])
        if cfg.use_userdata:
            ignore = diary_mod.load_ignore(self.paths.ignore)
            ud = self.paths.userdata_dir
            for n in L_mod.read_notes(ud, ignore):
                para, qa = L_mod.note_cards(n, self.who)
                want["note|" + n["id"]] = ("note", n["text"][:60], para, qa, "saved note" + (", updated " + n["updated"] if n["updated"] else ""), "", 1)
            for t in L_mod.read_tracking(ud, today, ignore):
                para, qa = L_mod.track_cards(t, self.who)
                want["track|" + norm(t["what"])] = ("track", t["what"][:60], para, qa, t["source"] or "Keeping track of list", t["until"], 1)
        for key, (kind, obj, para, qa, src, until, days) in want.items():
            it = self.items.get(key)
            if it and not it.dead and it.para == para and it.qa == qa:
                it.source, it.until, it.days = src, until, days
                continue
            self.items[key] = Item(key, self.who, obj, kind, d, first=d, days=days, nment=1, para=para, qa=qa, seen_ment=1, dreamed_night=d,
                                   kind=kind, source=src, until=until)
            st[kind + "_new" if not it else kind + "_changed"] += 1
        for it in self.items.values():
            if it.kind in ("habit", "note", "track") and not it.dead and it.key not in want:
                it.dead = True
                st[it.kind + "_retired"] += 1
        st["habit"] = sum(1 for k in want if k.startswith("habit|"))
        st["note"] = sum(1 for k in want if k.startswith("note|"))
        st["track"] = sum(1 for k in want if k.startswith("track|"))

    def leaky(self, text: str) -> bool:
        n = norm(text)
        return any(l in n or (len(n) >= 10 and n in l) for l in self.leak)

    def split_holdout(self, fresh: List[Item], d: int, st: Counter) -> None:
        """Hold out ~holdout_frac of tonight's new cards (Q&A only, never trained on). An item keeps at least 2 trainable cards, so
        its fact is still taught by other wordings and the other direction: the quiz then tests paraphrase and reverse. On a small
        night where no fact has 3 cards, a fact keeps at least 1 (a paraphrase) instead."""
        total = sum(len(it.para) + len(it.qa) for it in fresh)
        want = int(round(self.cfg.holdout_frac * total))
        if total >= self.cfg.min_cards:
            want = max(want, 1)
        key = lambda it: hashlib.sha1((str(self.cfg.seed) + it.key).encode()).hexdigest()   # noqa: E731
        order = sorted((it for it in fresh if len(it.qa) >= 1 and len(it.para) + len(it.qa) >= 3), key=key)
        if not order:   # a small night (one or two cards per fact): still hold some out, or the gate has nothing to check and undoes it
            order = sorted((it for it in fresh if len(it.qa) >= 1 and len(it.para) + len(it.qa) >= 2), key=key)
        n = 0
        for it in order:
            if n >= want:
                break
            h = int(hashlib.sha1(("dir" + it.key).encode()).hexdigest(), 16)
            cand = [i for i, (q, a) in enumerate(it.qa) if (norm(a) == norm(it.subj)) == (h % 2 == 1)] or list(range(len(it.qa)))
            i = cand[h // 2 % len(cand)]
            q, a = it.qa.pop(i)
            it.held.append({"q": q, "a": a, "dir": "forward" if norm(a) == norm(it.obj) else "reverse", "night": d})
            n += 1
        st["held_out"] = n

    def hold_lessons(self, d: int, st: Counter) -> None:
        """Hold out 1 in 5 of tonight's new lesson cards (at least one when there are 3 or more lessons) so the recall quiz sees them.
        Same rule as the facts: Q&A only, and the lesson keeps at least 2 trainable cards."""
        new = [it for it in self.items.values() if it.kind == "lesson" and it.first == d and not it.dead and not it.held]
        if len(new) < 3:
            return
        cands = sorted((it for it in new if len(it.qa) >= 1 and len(it.para) + len(it.qa) >= 3),
                       key=lambda it: hashlib.sha1((str(self.cfg.seed) + "lesson" + it.key).encode()).hexdigest())
        n = 0
        for it in cands[:max(1, int(round(len(new) / 5.0)))]:
            q, a = it.qa.pop(0)
            it.held.append({"q": q, "a": a, "dir": "forward", "night": d})
            n += 1
        st["lessons_held_out"] = n

    # ---- 7. REM
    def rem(self, E: List[Item], d: int, ci: int, st: Counter) -> None:
        E = [it for it in E if it.kind == "fact"]   # chains and gist dreams join facts only
        by = defaultdict(list)
        for it in E:
            for x in {norm(it.subj), norm(it.obj)}:
                by[x].append(it)
        rng = random.Random("rem:%s:%s:%s" % (self.cfg.seed, d, ci))
        pairs = []
        for x, its in by.items():
            if x in GENERIC or len(its) > 12:
                continue
            for p, q in itertools.combinations(its, 2):
                if other(p, x)[1].lower() != other(q, x)[1].lower():
                    pairs.append((p, q, x))
        rng.shuffle(pairs)
        pairs.sort(key=lambda t: self.rem_done["|".join(sorted((t[0].key, t[1].key)))])
        pairs = pairs[:self.cap_chains]
        gist = [it for it in E if it.days >= self.cfg.gist_min_days]
        rng.shuffle(gist)
        gist.sort(key=lambda it: self.gist_done[it.key])
        gist = gist[:self.cap_gist]
        mode = self.prof.quirk("rem_chain_mode") if self.prof.thinks else ("q" if self.prof.quirk("rem_chain_mode") in ("q", "q_think") else "default")
        qmode, think = mode in ("q", "q_think"), mode in ("think", "q_think")
        salt = "rem%d" % ci
        roles = [bridge_roles(p, q, x, k) for k, (p, q, x) in enumerate(pairs)]
        if think:
            craw = self.think_gen(lambda th: [P.bridge_prompt(self.R, p.fact, q.fact, *rl, think=th, qonly=qmode) for (p, q, x), rl in zip(pairs, roles)],
                                  40, self.prof.quirk("rem_think_tokens"), sample=True, base=False, salt=salt + "c")
        else:
            craw = self.gen([P.bridge_prompt(self.R, p.fact, q.fact, *rl, qonly=qmode) for (p, q, x), rl in zip(pairs, roles)], 40, sample=True, base=False, salt=salt + "c")
        graw = self.gen([P.gist_prompt(self.R, it.fact, it.days, self.who) for it in gist], 40, sample=True, base=False, salt=salt + "g")
        cand = []
        for k, ((p, q, x), txt) in enumerate(zip(pairs, craw)):
            st["chain_gen"] += 1
            r = None
            if qmode:
                qs = P.parse_q1(txt)
                r = (qs, roles[k][1]) if qs else None
            else:
                r = P.parse_qa1(txt)
            if r is None:
                st["rem_parse_fail"] += 1
                continue
            qq, aa = r
            fp, fq = other(p, x)[1], other(q, x)[1]
            es = [e for e in (fp, fq) if e.lower() in aa.lower()]
            other_e = fq if es and es[0] == fp else fp
            if self.leaky(qq):
                st["rem_dropped_test_leak"] += 1
            elif len(es) != 1 or es[0].lower() in qq.lower() or other_e.lower() not in qq.lower() or x in qq.lower():
                st["rem_dropped_bad"] += 1
            else:
                idx = sorted(set(self.diary.containing(p.subj, p.obj, d)[-2:]) | set(self.diary.containing(q.subj, q.obj, d)[-2:]))
                cand.append(("chain", (p, q), qq, es[0], self.diary.label(idx)))
        for it, txt in zip(gist, graw):
            st["gist_gen"] += 1
            r = P.parse_qa1(txt)
            if r is None:
                st["rem_parse_fail"] += 1
                continue
            qq, aa = r
            es = [e for e in (it.subj, it.obj) if e.lower() in aa.lower()]
            other_e = it.obj if es and es[0] == it.subj else it.subj
            if self.leaky(qq):
                st["rem_dropped_test_leak"] += 1
            elif len(es) != 1 or es[0].lower() in qq.lower() or other_e.lower() not in qq.lower():
                st["rem_dropped_bad"] += 1
            else:
                cand.append(("gist", (it,), qq, es[0], self.diary.label(self.diary.containing(it.subj, it.obj, d)[-4:])))
        ver = self.gen([P.ctx_prompt(self.R, c, q, self.who) for _, _, q, _, c in cand], self.cfg.verify_tokens, salt=salt + "v")
        have = {(norm(x["q"]), x["a"].lower()) for x in self.rem_pool}
        for (kind, its, q, ans, c), v in zip(cand, ver):
            if not has_ans(ans, v):
                st["rem_dropped_unverified"] += 1
            elif (norm(q), ans.lower()) in have:
                st["rem_dropped_dup"] += 1
            else:
                have.add((norm(q), ans.lower()))
                self.rem_pool.append({"q": q, "a": ans, "keys": [i.key for i in its], "kind": kind, "night": d, "cycle": ci})
                st["rem_%s_kept" % kind] += 1
                if kind == "chain":
                    self.rem_done["|".join(sorted((its[0].key, its[1].key)))] += 1
                else:
                    self.gist_done[its[0].key] += 1
        st["rem_pool"] = len(self.rem_pool)

    # ---- 9. cleanup
    def cleanup(self) -> Dict[str, int]:
        st = Counter()
        for it in list(self.items.values()):
            if it.kind != "fact":
                continue
            if not it.dead and it.nment == 0 and it.days == 0 and it.born > 0:   # its turns are gone from the diary (ignored, or removed)
                it.dead = True
                st["dropped_unseen"] += 1
                continue
            if not it.dead and it.fails >= 2:
                it.dead = True
                self.dropped.add(it.key)
                st["dropped_failed"] += 1
        groups = defaultdict(list)
        for it in self.items.values():
            if not it.dead and it.kind == "fact":
                groups[frozenset(it.key.split("|"))].append(it)
        for g in groups.values():
            if len(g) > 1:
                g.sort(key=lambda it: (-len(it.para) - len(it.qa), it.born))
                for x in g[1:]:
                    x.dead = True
                    st["merged"] += 1
        return dict(st)

    # ---- training examples
    def ex_text(self, text: str):
        return (self.be.encode(text) + [self.be.stop_id], 0)

    def ex_qa(self, q: str, a: str, rng: random.Random, d: int):
        ob = rng.random() < self.cfg.ob_share
        if ob:
            p = self.be.encode(P.diary_prompt(self.R, self.diary, q, d))
            if len(p) + 24 <= self.cfg.max_seq_len:
                return (p + self.be.encode(a) + [self.be.stop_id], len(p))
        p = self.be.encode(P.plain_prompt(self.R, q))
        return (p + self.be.encode(a) + [self.be.stop_id], len(p))

    def nrem(self, act: List[Item], cum: List[float], n: int, rng: random.Random, d: int):
        out = []
        for _ in range(n):
            if not act:
                break
            it = rng.choices(act, cum_weights=cum)[0]
            o = rng.choice(it.para + it.qa)
            out.append(self.ex_text(o) if isinstance(o, str) else self.ex_qa(o[0], o[1], rng, d))
        return out

    def replay_set(self):
        return [(self.be.encode(self.R.render(P.SYS, q)) + [self.be.stop_id], 0) for q in GENERIC_PROMPTS]

    # ---- the night
    def day_turns(self, week: dict, d: int) -> int:
        return sum(1 for t in week["diary"] if t["role"] == "user" and t["day"] == d)

    def pick_day(self, week: dict, st: dict) -> Optional[Tuple[int, str]]:
        return next_day(week, st)

    def run(self, week: dict, dry_run: bool = False, only_date: Optional[str] = None) -> dict:
        """Run (or resume) one night. Returns the result dict (status: done / stopped / dry_run / no_new_day)."""
        self.paths.mk()
        cfg = self.cfg
        self.state = self.load_state()
        self.load_items()
        resumed = False
        self.N = read_json(self.paths.night_json, None) if not dry_run else None
        if self.N and self.N.get("dry_run"):
            self.N = None
        if self.N:
            resumed = True
            d, date = self.N["day"], self.N["date"]
            if date not in week.get("dates", {}).values():
                self.N = None
                resumed = False
        if not self.N:
            if only_date:
                d = diary_mod.day_of_date(week, only_date)
                pick = (d, only_date) if d else None
            else:
                pick = self.pick_day(week, self.state)
            if not pick:
                return {"status": "no_new_day", "message": "no new diary day to sleep on"}
            d, date = pick
            shutil.rmtree(str(self.paths.work), ignore_errors=True)
            self.N = {"day": d, "date": date, "phase": "tag", "scale": None, "done_steps": 0, "rem_done": [], "chunks": 0, "stats": {}, "elapsed_s": 0.0,
                      "dry_run": bool(dry_run), "started": time.time()}
        N = self.N
        N["chunks"] += 1
        self.diary = Diary(week)
        dry_cache = self.paths.home / "dry_gen_cache.jsonl"    # a dry run's generations are kept, so the real night after it does not redo them
        self.cache = GenCache(dry_cache if dry_run else self.paths.gen_cache)
        if not dry_run:
            self.cache.d.update({k: v for k, v in GenCache(dry_cache).d.items() if k not in self.cache.d})
        t_chunk0 = time.time()
        res = {"status": "stopped", "night": self.state["nights"] + 1, "date": N["date"], "day": d, "resumed": resumed, "dry_run": bool(dry_run)}
        try:
            self._night(week, d, dry_run, res)
        except Stop as s:
            res.update(status="stopped", stop_reason=s.reason, interrupted=s.external)
            self._on_stop(res)
        finally:
            N["elapsed_s"] = N.get("elapsed_s", 0.0) + time.time() - t_chunk0
            if N.get("phase") != "done" and not dry_run:
                self.save_night()
        res["phase"] = N.get("phase")
        res["steps"] = N.get("steps_this_chunk", 0)
        res["scale"] = N.get("scale")
        return res

    def _on_stop(self, res: dict) -> None:
        """Checkpoint what is in memory when a chunk ends mid-night."""
        N = self.N
        if N["phase"] == "train" and getattr(self, "_trained_since_ckpt", 0) > 0:
            self.be.save_adapter(self.paths.work_adapter)
            self._trained_since_ckpt = 0
        res["message"] = "stopped (%s) in phase %s at step %s/%s; will resume" % (res.get("stop_reason"), N["phase"], N["done_steps"], N.get("total_steps"))

    def _set_scale(self, dry_run: bool) -> None:
        N, cfg = self.N, self.cfg
        if N["scale"] is None:
            if cfg.scale is not None:
                s = cfg.scale
                N["bench"] = None
            else:
                self.be.bench_bsz = cfg.bsz                                           # time a step of the size we will really run
                self.be.bench_rep = max(1, round(cfg.replay_bsz / max(cfg.kl_every, 1)))
                t_step, t_gen = self.be.bench()
                B = cfg.night_budget_s or self.clock.budget_s
                s = clip_scale(B, t_step, t_gen, cfg.ref_steps, ref_gen_batches(self.be.gen_batch, cfg.max_dream_items, cfg.rem_chains, cfg.rem_gist))
                N["bench"] = {"t_step": t_step, "t_gen": t_gen, "budget_s": B}
            N["scale"] = s
            self.save_night() if not dry_run else None
        self.set_scale(N["scale"])
        if N.get("bench"):
            self.t_step = N["bench"]["t_step"]
            self.sec_per_batch_tok = N["bench"]["t_gen"] / 20.0

    def set_scale(self, s: float) -> None:
        cfg = self.cfg
        sc = (lambda n: n if s == 1 or n <= 0 else max(1, round(n * s)))  # noqa: E731
        self.scale, self.sc = s, sc
        self.k, self.cap_items, self.cap_chains, self.cap_gist, self.dream_tokens = sc(P.K), sc(cfg.max_dream_items), sc(cfg.rem_chains), sc(cfg.rem_gist), sc(400)

    def _night(self, week: dict, d: int, dry_run: bool, res: dict) -> None:
        N, cfg, st_all = self.N, self.cfg, self.N["stats"]
        self._set_scale(dry_run)
        res["scale"] = N["scale"]
        self.log("[night %d] day %s scale %.2f" % (self.state["nights"] + 1, N["date"], N["scale"]))
        ph = PHASES.index(N["phase"])
        # ---- tag + dream (cards)
        if ph <= PHASES.index("dream"):
            if not dry_run and self.state.get("small", {}).get(N["date"]) == sum(1 for t in self.diary.turns if t["day"] == d):
                res.update(status="dry_run", dry_run=True, quiz=None, harm=None, steps=0,
                           message="still too little data for %s (already checked with the same %d turns); waiting for more diary" % (N["date"], self.state["small"][N["date"]]))
                N["phase"] = "done"
                shutil.rmtree(str(self.paths.work), ignore_errors=True)
                return
            st = Counter()
            self.tag(d, st)
            self.names_pass(d, st)
            self.refresh(d)
            if cfg.use_lessons:
                self.corrections(week, d, st)
            st_all["tagging"] = dict(st)
            self.log("[night] tagging %s" % st_all["tagging"])
            E = [it for it in self.items.values() if self.elig(it)]
            st = Counter()
            fresh = self.dream(d, E, st)
            st_all["dreamcheck"] = self.check_dreams([(it, q, a) for it in fresh for q, a in it.qa], "nrem")
            if "holdout_done" not in N:
                self.split_holdout(fresh, d, st)
                N["holdout_done"] = True
            st_all["dream"] = dict(st)
            st = Counter()
            self.lessons_stage(week, d, st)
            self.extras(week, d, st)
            if "lesson_holdout_done" not in N:
                self.hold_lessons(d, st)
                N["lesson_holdout_done"] = True
            st_all["lessons"] = dict(st)
            self.log("[night] lessons and habits %s" % st_all["lessons"])
            st_all["cleanup"] = self.cleanup()
            self.log("[night] dream %s" % st_all["dream"])
            E = [it for it in self.items.values() if self.elig(it)]
            # notes and tracking cards do not start a night: a low-fact day should skip, not train mostly on notes
            ncards = sum(len(it.para) + len(it.qa) for it in E if it.kind not in ("note", "track"))
            st_all["trainable_cards"] = ncards
            self.save_items()
            self.write_cards()
            if dry_run or ncards < cfg.min_cards:
                why = "dry run requested" if dry_run else "only %d trainable cards (need %d): cards written, no training tonight; the day stays unslept" % (ncards, cfg.min_cards)
                res.update(status="dry_run", dry_run=True, message=why, cards=ncards, quiz=None, harm=None, lessons=list(N.get("lessons", [])))
                self.append_night(res, extra={"dry_run_reason": why, "stats": st_all})
                if not dry_run:
                    self.state.setdefault("small", {})[N["date"]] = sum(1 for t in self.diary.turns if t["day"] == d)
                    write_json(self.paths.state, self.state)
                shutil.rmtree(str(self.paths.work), ignore_errors=True)
                N["phase"] = "done"
                return
            N["phase"] = "train"
            self.save_night()
        E = [it for it in self.items.values() if self.elig(it)]
        # ---- training
        if N["phase"] == "train":
            self._train(week, d, E, res)
        if N["phase"] == "downscale":
            self.clock.check(30)
            self.be.load_adapter(self.paths.work_adapter)
            st_all["shy"] = self.be.downscale(cfg.shy_factor, cfg.shy_thresh, cfg.seed * 100 + d)
            self.be.save_adapter(self.paths.work_adapter)
            N["phase"] = "gate"
            self.save_night()
        if N["phase"] == "gate":
            self._gate(week, d, E, res)

    def _train(self, week: dict, d: int, E: List[Item], res: dict) -> None:
        N, cfg = self.N, self.cfg
        # state of the adapter at the start of (or resuming) training
        if self.paths.work_adapter.exists():
            self.be.load_adapter(self.paths.work_adapter)
        else:
            self.be.load_adapter(self.paths.adapter if self.paths.adapter.exists() else None)
        if "pre" in N and (N["pre"] or {}).get("grader") != gate_mod.GRADER and "total_steps" not in N:
            del N["pre"]   # measured by an older grader before training started: measure again
        if "pre" not in N:
            self.clock.check(60)
            held = [h for it in self.items.values() for h in it.held if h["night"] == d]
            N["held_n"] = len(held)
            N["pre"] = dict(gate_mod.score_recall(self.be, self.R, held, adapter=True), grader=gate_mod.GRADER)
            if not self.paths.gate_base.exists():
                flags = gate_mod.score_general(self.be, self.R, adapter=False, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
                write_json(self.paths.gate_base, {"flags": flags, "score": gate_mod.pct(flags), "profile": self.prof.name, "model_dir": self.prof.model_dir, "n": cfg.gate_n, "grader": gate_mod.GRADER})
            self.save_night()
        if "total_steps" not in N:
            n_act = sum(1 for it in E if (it.para or it.qa) and it.kind == "fact")   # night length planned from facts only, as before; extra cards share the steps
            ref_n = min(300, 40 + 4 * n_act)
            N["ref_steps"] = ref_n
            N["total_steps"] = self.sc(ref_n)
            N["plan"] = rem_plan(N["total_steps"])
            self.save_night()
        total, plan = N["total_steps"], [tuple(x) for x in N["plan"]]
        sched = []
        for ci, (nn, nr) in enumerate(plan):
            sched += [("n", ci)] * nn + [("r", ci)] * nr
        act = [it for it in E if it.para or it.qa]
        cum = list(itertools.accumulate(self.prio(it) for it in act))
        replay = self.replay_set()
        self.be.train_begin(total, cfg.lr)
        self._trained_since_ckpt = 0
        N["steps_this_chunk"] = 0
        last_ce = None
        i = N["done_steps"]
        while i < total:
            kind, ci = sched[i]
            self.clock.check((self.t_step or 40.0) * 1.3 + 15)
            if kind == "r" and ci not in N["rem_done"]:
                st = Counter()
                self.rem(E, d, ci, st)
                new = [x for x in self.rem_pool if x.get("night") == d and x.get("cycle") == ci]
                st["dreamcheck"] = self.check_dreams([(x, x["q"], x["a"]) for x in new], "rem")
                N["rem_done"].append(ci)
                N["stats"].setdefault("rem", []).append(dict(st))
                self.save_items()
                self.save_night()
            live = [x for x in self.rem_pool if all(k in self.items and not self.items[k].dead for k in x["keys"])]
            rng = random.Random("step:%s:%s:%s" % (cfg.seed, d, i))
            nr0 = round(0.7 * cfg.bsz) if (kind == "r" and live) else 0
            batch = []
            for x in rng.choices(live, k=nr0) if nr0 else []:
                batch.append(self.ex_qa(x["q"], x["a"], rng, d))
            batch += self.nrem(act, cum, cfg.bsz - len(batch), rng, d)
            batch = [(ids[:cfg.max_seq_len], min(ls, cfg.max_seq_len - 1)) for ids, ls in batch]
            rb = rng.sample(replay, min(cfg.replay_bsz, len(replay))) if i % max(cfg.kl_every, 1) == 0 else []
            t0 = self.clock.now()
            r = self.be.train_step(batch, rb, i)
            dt = self.clock.now() - t0
            self.t_step = dt if self.t_step is None else 0.7 * self.t_step + 0.3 * dt
            last_ce = r.get("ce")
            i += 1
            N["done_steps"] = i
            N["steps_this_chunk"] = N.get("steps_this_chunk", 0) + 1
            self._trained_since_ckpt += 1
            if self._trained_since_ckpt >= cfg.ckpt_every:
                self.be.save_adapter(self.paths.work_adapter)
                self._trained_since_ckpt = 0
                self.save_night()
                self.log("[night] step %d/%d ce %s %.1fs" % (i, total, last_ce, dt))
        self.be.save_adapter(self.paths.work_adapter)
        self._trained_since_ckpt = 0
        N["last_ce"] = last_ce
        N["phase"] = "downscale"
        self.save_night()

    def _gate(self, week: dict, d: int, E: List[Item], res: dict) -> None:
        N, cfg, P_ = self.N, self.cfg, self.paths
        self.clock.check(90)
        self.be.load_adapter(P_.work_adapter)
        held = [h for it in self.items.values() for h in it.held if h["night"] == d]
        post = gate_mod.score_recall(self.be, self.R, held, adapter=True)
        base = read_json(P_.gate_base, {}) or {}
        flags = gate_mod.score_general(self.be, self.R, adapter=True, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
        bflags = base.get("flags") if (base.get("n", 40) == cfg.gate_n and len(base.get("flags", [])) == len(flags)
                                       and base.get("grader") == gate_mod.GRADER) else None
        if bflags is None:   # recorded for another question set or by another grader: record the base again now (adapter off)
            bflags = gate_mod.score_general(self.be, self.R, adapter=False, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
            write_json(P_.gate_base, {"flags": bflags, "score": gate_mod.pct(bflags), "profile": self.prof.name, "model_dir": self.prof.model_dir, "n": cfg.gate_n, "grader": gate_mod.GRADER})
        j = gate_mod.judge(bflags, flags, cfg.harm_max)
        pre = N.get("pre") if (N.get("pre") or {}).get("grader") == gate_mod.GRADER else None   # an older grader's score is not comparable
        reasons = gate_mod.decide(j, pre, post, cfg.gate_min_gain)
        quiz = post["recall"]
        reverted = bool(reasons)
        if reverted:   # undo the night: the committed adapter stays; memory goes back to it
            self.be.load_adapter(P_.adapter if P_.adapter.exists() else None)
        else:
            if P_.adapter.exists():
                shutil.rmtree(str(P_.adapter_prev), ignore_errors=True)
                shutil.move(str(P_.adapter), str(P_.adapter_prev))
            shutil.move(str(P_.work_adapter), str(P_.adapter))
            for it in E:
                if it.para or it.qa:
                    it.trained = True
            if cfg.llama_cpp_dir:   # a failure here never fails the night
                try:
                    from . import export as export_mod
                    ok, msg = (self.exporter or export_mod.export_gguf)(cfg.llama_cpp_dir, cfg.gguf_base_dir, P_.adapter, P_.home / "adapter.gguf")
                except Exception as e:
                    ok, msg = False, "%s: %s" % (type(e).__name__, e)
                res["gguf"] = {"ok": ok, "message": msg}
                self.log("[night] gguf export: %s %s" % ("ok" if ok else "FAILED", msg))
                if ok:
                    self._after_export(P_.home / "adapter.gguf", res)
        self.state["nights"] += 1
        if N["date"] not in self.state["slept_days"]:
            self.state["slept_days"].append(N["date"])
        self.state.setdefault("slept_turns", {})[N["date"]] = self.day_turns(week, d)
        self.state["last_night"] = {"date": N["date"], "reverted": reverted, "quiz": quiz, "harm": j["harm"]}
        write_json(P_.state, self.state)
        self.save_items()
        self.write_cards()
        res.update(status="done", quiz=quiz, harm=j["harm"], general=j["general"], general_base=j["general_base"], reverted=reverted,
                   revert_reason=reasons, recall_pre=(N.get("pre") or {}).get("recall"), held_out=post["n"], recall_by_dir=post["by_dir"],
                   steps_total=N.get("total_steps"), message="night done" + (" (REVERTED: %s)" % "; ".join(reasons) if reverted else ""),
                   lessons=list(N.get("lessons", [])), dreamcheck=dc_total(N["stats"]))
        self.append_night(res, extra={"stats": N["stats"], "bench": N.get("bench"), "chunks": N["chunks"], "elapsed_s": N["elapsed_s"], "lessons": res["lessons"],
                                      "last_ce": N.get("last_ce"), "recall_samples": post.get("samples")})
        N["phase"] = "done"
        shutil.rmtree(str(P_.work), ignore_errors=True)
        try:
            (P_.home / "dry_gen_cache.jsonl").unlink()
        except OSError:
            pass

    def _after_export(self, gguf: Path, res: dict) -> None:
        """Record the adapter's base next to it (adapter.gguf.json; export_gguf rotated the old record with the old file). The served
        check (finish_served) runs after the night, once the worker has unloaded the trainer's model: on an 8 GB Mac the fp16 model
        and a llama-server do not fit together."""
        from . import export as export_mod
        cfg = self.cfg
        write_json(export_mod.sidecar_path(gguf), {"base_hf_id": self.prof.hf_id, "profile": self.prof.name, "base_dir": cfg.gguf_base_dir,
                                                   "date": self.N.get("date"), "night": self.state.get("nights", 0) + 1, "created": time.time()})
        if not (cfg.llama_server and cfg.base_gguf):
            res["served"] = {"ok": None, "reasons": ["not checked: no llama-server configured (SLEEPMLX_LLAMA_SERVER, SLEEPMLX_BASE_GGUF)"]}
            return
        d = self.N["day"]
        held = [{"q": h["q"], "a": h["a"]} for it in self.items.values() for h in it.held if h["night"] == d]
        self.served_pending = (gguf, held)
        res["served"] = {"ok": None, "pending": True, "reasons": ["checked after the trainer's model is unloaded"]}

    def finish_served(self, res: dict) -> None:
        """The served check of tonight's GGUF (served.check_gguf: our own llama-server, adapter on vs off). A GGUF that scores worse, or
        that the server will not load while the plain model loads fine, is replaced by the previous one. A check that could not run
        (no memory, port, timeout) changes nothing and says so."""
        from . import export as export_mod
        from . import served as served_mod
        pend, self.served_pending = getattr(self, "served_pending", None), None
        if not pend:
            return
        gguf, held = pend
        cfg = self.cfg
        r = (self.served_checker or served_mod.check_gguf)(cfg.llama_server, cfg.base_gguf, str(gguf), held,
                                                             log=str(self.paths.home / "served_check.log"))
        res["served"] = r
        self.log("[night] served check (llama-server, adapter on vs off): %s" % r)
        if r.get("ok") is False:
            restored = export_mod.restore_prev(gguf)
            res["served"]["fallback"] = "previous adapter.gguf" if restored else "plain model (no adapter.gguf)"
            res["served"]["note"] = "the trained adapter was kept for the next night; the daytime GGUF is the older one"
        else:
            try:
                side = read_json(export_mod.sidecar_path(gguf), {}) or {}
                side["served"] = r
                write_json(export_mod.sidecar_path(gguf), side)
            except OSError:
                pass

    # ---- outputs
    def card_rows(self) -> List[dict]:
        rows = []
        for it in self.items.values():
            if it.dead:
                continue
            status = "trained" if it.trained else "pending"
            if it.kind != "fact":
                extra = {"source": it.source, "until": it.until or None}
                for p in it.para:
                    rows.append(dict({"item": it.fact, "kind": it.kind, "text": p, "night": it.dreamed_night, "status": status}, **extra))
                for q, a in it.qa:
                    rows.append(dict({"item": it.fact, "kind": it.kind + "_qa", "q": q, "a": a, "night": it.dreamed_night, "status": status}, **extra))
                continue
            for p in it.para:
                rows.append({"item": it.fact, "kind": "paraphrase", "text": p, "night": it.dreamed_night, "status": status})
            for q, a in it.qa:
                rows.append({"item": it.fact, "kind": "qa", "q": q, "a": a, "night": it.dreamed_night, "status": status})
            for h in it.held:
                rows.append({"item": it.fact, "kind": "qa", "q": h["q"], "a": h["a"], "dir": h["dir"], "night": h["night"], "status": "held_out"})
        for x in self.rem_pool:
            rows.append({"item": " + ".join(self.items[k].fact for k in x["keys"] if k in self.items), "kind": "rem_" + x["kind"], "q": x["q"], "a": x["a"],
                         "night": x["night"], "status": "trained"})
        return rows

    def write_cards(self) -> None:
        self.paths.cards.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.paths.cards.with_name("cards.jsonl.tmp")
        tmp.write_text("".join(json.dumps(r) + "\n" for r in self.card_rows()))
        tmp.replace(self.paths.cards)

    def append_night(self, res: dict, extra: Optional[dict] = None) -> None:
        row = {"ts": time.time(), "date": res.get("date"), "night": res.get("night"), "status": res.get("status"), "dry_run": res.get("dry_run"),
               "scale": res.get("scale"), "quiz": res.get("quiz"), "recall_pre": res.get("recall_pre"), "harm": res.get("harm"), "general": res.get("general"),
               "reverted": res.get("reverted"), "steps": res.get("steps_total"), "held_out": res.get("held_out"), "profile": self.prof.name}
        row.update(extra or {})
        with open(str(self.paths.nights), "a") as f:
            f.write(json.dumps(row) + "\n")
