"""The night pipeline: sleepb.py's ab_ob_b4_nb recipe, ported to a Backend interface.

tag the day's facts -> names re-read pass -> NREM cards (paraphrases + Q&A, checked by the base model) ->
LoRA training in 4 cycles (NREM steps, then REM two-step dreams written by the current adapter, then REM+NREM steps) with
open-book rehearsal, replay of earlier nights' cards and a KL leash to the base -> downscale (SHY) -> morning gate.

A chunk may end at any generate batch or training step (Stop): the night's state, a generation cache and the adapter are on disk, and the
next chunk resumes. See README.md for what is ported faithfully and what is simplified.
"""
from __future__ import annotations

import hashlib
import copy
import itertools
import json
import os
import math
import random
import re
import shutil
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date as _date
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import diary as diary_mod
from . import gate as gate_mod
from . import grading as grading_mod
from . import lessons as L_mod
from . import prompts as P
from . import replay as replay_mod
from .backend import Backend, Clock, Stop
from .checkpoint import CheckpointError, Checkpoints
from .corpus import Diary, has_ans, norm, pat
from .paths import Paths, read_json, write_json, write_text

GENERIC = {"ben", "i", "me", "my", "we", "you", "he", "she", "they", "it", "user", "the user", "someone", "somebody"}
SELF = {"i", "me", "my", "myself", "mine", "user", "the user"}   # Ben speaking of himself: these become `who`
CARD_LINES = re.compile(r"^\s*(?:[-*]\s*)?[^=>\n]+?\s*=>\s*[^=>\n]+?\s*=>\s*[^=>\n]+?\s*$")   # "Subject => relation => Object": ingested as fact Items elsewhere
IMP_RE = re.compile(r"remember|important|don'?t forget", re.I)
COR_RE = re.compile(r"\bactually\b|correction|no, it'?s", re.I)
NREM_SHARE = [0.80, 0.65, 0.50, 0.35]
NAMES_CAP = 6
RESLEEP_TURNS = 5
PHASES = ["tag", "dream", "train", "downscale", "gate", "finalize", "done"]

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
    replay_mode: str = "prompt"  # opt-in "continuation": base answer contexts; measure paired retention before enabling
    replay_max_tokens: int = 128  # capped teacher generation, cached separately from private diary work
    gate_n: int = 40              # general questions in the gate
    gate_max_tokens: int = 24
    recall_max_tokens: int = 16
    llama_cpp_dir: Optional[str] = None      # set: export a GGUF LoRA when a night commits (torch backend)
    gguf_base_dir: Optional[str] = None      # the HF base model dir the converter needs
    dreamcheck: bool = True                  # check the night's Q&A dreams against the diary before training (dreamhook.py)
    dreamcheck_share: float = 0.10           # at most this share of the night's budget goes to it (the rest stay unchecked, kept)
    llama_server: Optional[str] = None       # set with base_gguf: check the exported adapter inside llama-server (served.py)
    base_gguf: Optional[str] = None          # explicitly bound served GGUF; learned-fact transfer needs separate evaluation
    # Extra sources (lessons.py). Not part of ab_ob_b4_nb: they only add cards to the same pool; every setting above is unchanged.
    use_lessons: bool = True      # post-mortems of the day's failures -> lesson cards (and corrections retire the fact they replace)
    max_lessons: int = 8          # lessons written per night (x work scale)
    lesson_tokens: int = 200
    max_rated: int = 12           # thumbs-rated turns carded per night (x work scale), oldest first
    rated_tokens: int = 300
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


def is_card_note(n: dict) -> bool:
    return n["topic"].strip().lower() == "card" and bool(card_lines(n["text"]))


def card_lines(text: str) -> List[Tuple[str, str, str]]:
    out = []
    for l in re.split(r"[\n;]", text):   # a saved note is one line (the Desk collapses whitespace): several cards are told apart by ";"
        if CARD_LINES.match(l):
            sj, rl, ob = (x.strip() for x in re.sub(r"^\s*[-*]\s+", "", l).split("=>"))
            out.append((sj, rl, ob))
    return out


def note_sig(n: dict) -> str:
    return hashlib.sha1(("%s|%s|%s" % (n["id"], n["topic"], n["text"])).encode()).hexdigest()[:16]


def card_claim_sig(subj: str, rel: str, obj: str) -> str:
    return hashlib.sha256(json.dumps([norm(subj), norm(rel), norm(obj)]).encode()).hexdigest()


def card_claim_key(note_id: str, signature: str) -> str:
    return "card|" + hashlib.sha256(json.dumps([note_id, signature]).encode()).hexdigest()


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
    kind: str = "fact"            # fact (tagged from the diary) | lesson | rated | habit | note | track (lessons.py; their cards are made, not dreamed)
    source: str = ""              # where a non-fact item came from (kept on its cards)
    until: str = ""               # YYYY-MM-DD: after this day the item is not trained (tracked items)
    line: str = ""                # fact from a saved card note: the card line "Subject => relation => Object" (its dream context when no chat turn names both sides)
    sig: str = ""                 # note items: hash of the note's id and text the quiz card was made for (unchanged note = same card, no regeneration)
    card_note_id: str = ""        # saved-card source identity; sig is its normalized triple signature

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


def selfify(x: str, who: str) -> str:
    return who if norm(x) in SELF or norm(x) == norm(who) else x


def triple_status(diary: Diary, dropped: set, ti: int, sj: str, ob: str, who: str = "") -> str:
    """`who` (Ben) may be one side of a fact he states about himself (not both, not next to a generic word)."""
    w = norm(who) if who else None
    gen = lambda x: norm(x) in GENERIC and norm(x) != w   # noqa: E731
    if min(len(sj), len(ob)) < 2 or max(len(sj), len(ob)) > 60 or norm(sj) == norm(ob) or gen(sj) or gen(ob):
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
    def load_items(self, data=None):
        d = (read_json(self.paths.items, {}) or {}) if data is None else data
        self.items: Dict[str, Item] = {k: Item.from_dict(v) for k, v in d.get("items", {}).items()}
        self.rem_pool: List[dict] = d.get("rem_pool", [])
        self.rem_done = Counter(d.get("rem_done", {}))
        self.gist_done = Counter(d.get("gist_done", {}))
        self.dropped = set(d.get("dropped", []))
        self.wrong: Dict[str, set] = {k: set(v) for k, v in (d.get("wrong") or {}).items()}   # name -> values a correction said are wrong

    def _items_data(self):
        return {"items": {k: asdict(v) for k, v in self.items.items()}, "rem_pool": self.rem_pool,
                                      "rem_done": dict(self.rem_done), "gist_done": dict(self.gist_done), "dropped": sorted(self.dropped),
                                      "wrong": {k: sorted(v) for k, v in self.wrong.items()}}

    def save_items(self):
        write_json(self.paths.items, self._items_data())

    def load_state(self):
        st = read_json(self.paths.state, {}) or {}
        st.setdefault("slept_days", [])
        st.setdefault("nights", 0)
        return st

    def save_night(self, adapter=False):
        """Publish state and its matching immutable weights as one generation."""
        if getattr(self, "_trained_since_ckpt", 0) and not adapter:
            return  # never publish progress ahead of the weights
        checkpoints = getattr(self, "_checkpoints", None) or Checkpoints(self.paths)
        checkpoints.publish(self.N, self._items_data(), self.be.save_adapter if adapter else None)
        if adapter:
            self._trained_since_ckpt = 0

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
        self.diary.who = self.who.lower()   # occurs(Ben) = every turn, so a fact Ben states about himself is "in the turn"
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
                sj, ob = selfify(sj, self.who), selfify(ob, self.who)   # I / my / me -> Ben
                ck = triple_status(self.diary, self.dropped, t["i"], sj, ob, self.who)
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

    def ctx_of(self, it: Item, d: int, newest_first: bool = False) -> str:
        """Chat turns naming both sides (newest first for dreams), plus the saved card line for a card-note fact."""
        if it.card_note_id:
            return "[Saved card note] " + it.line
        idx = self.diary.containing(it.subj, it.obj, d)
        txt = self.diary.label(idx[::-1][:4] if newest_first else idx[-4:])
        return (txt + "\n" if txt else "") + ("[Saved card note] " + it.line if it.line else "")

    def _retire_card_claim(self, it: Item, st: Counter) -> None:
        """Remove source-owned rehearsal data without changing adapter bytes."""
        if not it.dead:
            st["card_retired"] += 1
        it.dead, it.trained, it.dirty = True, False, False
        it.para, it.qa, it.held = [], [], []
        obsolete = [row for row in self.rem_pool if it.key in row.get("keys", [])]
        self.rem_pool = [row for row in self.rem_pool if it.key not in row.get("keys", [])]
        st["card_rem_retired"] += len(obsolete)
        self.gist_done.pop(it.key, None)
        for row in obsolete:
            if row.get("kind") == "chain":
                self.rem_done.pop("|".join(sorted(row.get("keys", []))), None)
        night = getattr(self, "N", {})
        night.pop("pre", None)
        if "card_holdout_pending" in night:
            night["card_holdout_pending"] = [key for key in night["card_holdout_pending"] if key != it.key]

    def card_notes(self, d: int, st: Counter) -> None:
        """Bind each saved triple to its note ID and content, independently of diary facts.

        Reconciliation occurs at tag/dream boundaries. A train-phase resume keeps
        its immutable published source snapshot; it does not hot-reload edits.
        """
        if not self.cfg.use_userdata:
            return
        # Older versions keyed source-owned cards by their entity pair. Their
        # note IDs cannot be recovered safely from a collision, so retire their
        # rehearsal artifacts and re-dream current claims under explicit IDs.
        for key, it in list(self.items.items()):
            if it.kind == "fact" and it.line and it.source == "saved card note" and not it.card_note_id:
                self._retire_card_claim(it, st)
                del self.items[key]
                it.key = "retired_card|" + hashlib.sha256(json.dumps([key, it.line]).encode()).hexdigest()
                it.source = "retired legacy saved card note"
                self.items[it.key] = it
                st["card_migrated"] += 1
        have, ud = set(), self.paths.userdata_dir
        night = getattr(self, "N", {})
        pending = set(night.get("card_holdout_pending", []))
        for n in L_mod.read_notes(ud, diary_mod.load_ignore(self.paths.ignore)):
            if not is_card_note(n):
                continue
            for sj, rl, ob in card_lines(n["text"]):
                sj, ob = selfify(sj, self.who), selfify(ob, self.who)
                if min(len(sj), len(ob)) < 2 or max(len(sj), len(ob)) > 60 or norm(sj) == norm(ob):
                    st["card_invalid"] += 1
                    continue
                signature = card_claim_sig(sj, rl, ob)
                key = card_claim_key(n["id"], signature)
                have.add(key)
                it = self.items.get(key)
                if it is not None and (it.card_note_id != n["id"] or it.sig != signature):
                    raise ValueError("saved-card identity does not match its item key")
                if key in self.dropped:
                    continue
                if it is None or it.dead:
                    self.items[key] = Item(key, sj, ob, rl, d, first=d, days=1, nment=1, imp=True, dirty=True,
                                           line="%s %s %s." % (sj, rl, ob), source="saved card note",
                                           card_note_id=n["id"], sig=signature)
                    pending.add(key)
                    night.pop("pre", None)
                    st["card_new"] += 1
        for it in self.items.values():
            if it.card_note_id and not it.dead and it.key not in have:
                self._retire_card_claim(it, st)
                pending.discard(it.key)
        if pending or "card_holdout_pending" in night:
            night["card_holdout_pending"] = sorted(pending)

    def refresh(self, d: int) -> None:
        for it in self.items.values():
            if it.dead or it.kind != "fact":
                continue
            idx = self.diary.containing(it.subj, it.obj, d)
            days = {self.diary.turns[i]["day"] for i in idx}
            it.nment, it.days, it.first = len(idx), len(days), (min(days) if days else it.born)
            if it.line:   # a saved card note counts as one mention, however many chat turns also name both sides
                it.nment, it.days = max(it.nment, 1), max(it.days, 1)
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
            ctxs[it.key] = self.ctx_of(it, d, True)
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
            note = it.line if it.card_note_id else (self.diary.turns[idx[-1]]["text"][:300] if idx else (it.line or it.fact))
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
        src = lambda o: self.ctx_of(o, N["day"]) if isinstance(o, Item) else ""   # noqa: E731
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
                                   dreamed_night=d, kind="lesson", source=(("idea review %s: %s" if "idea_poor" in f["signals"] else "helper run %s: %s") % (date, f["helper"]) if f["kind"] == "delegation" else "chat %s, turn %d: %s" % (date, f["turn"] + 1, L_mod.KIND_WORDS[f["kind"]])))
            if f["kind"] == "correction" and wv and norm(wv) != norm(a):
                ti = self.turn_index(d, f["turn"])
                for it in (self.turn_items(ti) if ti is not None else []):
                    self.wrong.setdefault(norm(it.subj), set()).add(norm(wv))
            if text not in self.N.setdefault("lessons", []):
                self.N["lessons"].append(text)
            st["lessons_kept"] += 1

    def rated_stage(self, week: dict, d: int, st: Counter) -> None:
        """Flashcards from every turn Ben rated (thumbs up or down), oldest first, at most max_rated x s a night. The base model reads the chat
        around the turn and writes 2 to 4 question-answer cards plus a one-sentence summary; each answer must be in the chat text (for a
        thumbs down that Ben corrected, in Ben's own words), must not be a known wrong value, and the base model must give it back from the
        chat text alone. A turn already carded is never regenerated; a turn that gave no card is remembered (an empty item) and not retried
        unless its text or rating changes. A thumbs-up turn with no card keeps its word-for-word liked card (extras)."""
        if not self.cfg.use_lessons:
            return
        date_of = lambda x: diary_mod.date_of_day(week, x) or self.N["date"]   # noqa: E731
        every = L_mod.rated(week)
        have = {r["key"] for r in every}
        for it in self.items.values():
            if it.kind == "rated" and not it.dead and it.key not in have:
                it.dead = True   # Ben took the rating back, or the turn is gone from the diary
                st["rated_retired"] += 1
        todo = [r for r in every if not (self.items.get(r["key"]) and not self.items[r["key"]].dead and self.items[r["key"]].sig == str(r["fb"]))]
        st["rated_turns"] = len(every)
        todo = todo[:self.sc(self.cfg.max_rated)]
        if not todo:
            return
        raw = self.gen([P.rated_prompt(self.R, r["ctx"], r["fb"], self.who) for r in todo], self.cfg.rated_tokens, salt="rated")
        cand = []   # (turn, summary, [[q, a]] checked, wrong values)
        for r, txt in zip(todo, raw):
            j = P.parse_lesson(txt)
            cards = j.get("cards") if j else None
            if not isinstance(cards, list):
                st["rated_parse_fail"] += 1
                cand.append((r, "", [], set()))
                continue
            wrong = set()
            if r["fb"] == -1:
                wrong = self.wrong_for_turn(r["day"], {"turn": r["turn"], "kind": "disliked", "user": r["user"]}) | {norm(x) for x in L_mod.not_terms(r["next_user"])}
            truth = r["next_user"] if r["fb"] == -1 and r["next_user"] and L_mod.is_correction(r["next_user"]) else r["ctx"]   # a correction's truth is Ben's words
            good, seen = [], set()
            for c in cards[:6]:
                q, a = (str(c.get("q") or "").strip(), str(c.get("a") or "").strip().rstrip(".")) if isinstance(c, dict) else ("", "")
                if not (q and a):
                    why = "malformed"
                elif not 1 <= len(a.split()) <= 6 or len(a) > 60:
                    why = "answer_too_long"
                elif not q.endswith("?"):
                    why = "not_a_question"
                elif not norm(a) or not pat(norm(a)).search(norm(truth)):
                    why = "answer_not_in_chat"
                elif norm(a) in norm(q):
                    why = "answer_in_question"
                elif norm(a) in wrong:
                    why = "answer_is_the_wrong_value"
                elif any(diary_mod.looks_secret(x) or diary_mod.talks_secrets(x) for x in (q, a)):
                    why = "secret"
                elif self.leaky(q):
                    why = "test_leak"
                elif norm(q) in seen:
                    why = "dup"
                else:
                    why = None
                if why:
                    st["rated_qa_dropped_" + why] += 1
                else:
                    seen.add(norm(q))
                    good.append([q, a])
            cand.append((r, " ".join(str(j.get("summary") or "").split()), good[:4], wrong))
        flat = [(i, q, a) for i, (r, _, good, _) in enumerate(cand) for q, a in good]
        ver = self.gen([P.ctx_prompt(self.R, cand[i][0]["ctx"], q, self.who) for i, q, a in flat], self.cfg.verify_tokens, salt="rated_verify")
        kept = defaultdict(list)
        for (i, q, a), v in zip(flat, ver):
            if has_ans(a, v):
                kept[i].append([q, a])
                st["rated_qa_kept"] += 1
            else:
                st["rated_qa_dropped_unverified"] += 1
        for i, (r, summary, _, wrong) in enumerate(cand):
            key, qa = r["key"], kept[i]
            if not qa:
                st["rated_none"] += 1
                self.items[key] = Item(key, self.who, r["user"][:60], "rated", d, first=d, kind="rated", sig=str(r["fb"]), source="chat %s, turn %d: no cards" % (date_of(r["day"]), r["turn"] + 1))
                continue
            ask = r["user"][:200]
            if r["fb"] == 1:
                fallback = "%s liked how Glim answered \"%s\": %s" % (self.who, ask, r["answer"][:300])
            else:
                fallback = "%s gave Glim's answer to \"%s\" a thumbs down." % (self.who, ask) + (" %s then said: %s" % (self.who, r["next_user"][:300]) if r["next_user"] else "")
            text = L_mod.scrub(summary if 15 <= len(summary) <= 400 and not (diary_mod.looks_secret(summary) or diary_mod.talks_secrets(summary)) else fallback, wrong)
            if self.leaky(text):
                text = fallback
            self.items[key] = Item(key, self.who, r["user"][:60], "rated", d, first=d, days=1, nment=1, imp=True, cor=r["fb"] == -1, para=[text], qa=qa, seen_ment=1,
                                   dreamed_night=d, kind="rated", sig=str(r["fb"]),
                                   source="chat %s, turn %d: thumbs %s" % (date_of(r["day"]), r["turn"] + 1, "up" if r["fb"] == 1 else "down"))
            st["rated_new"] += 1

    def hold_rated(self, d: int, st: Counter) -> None:
        """Hold out 1 Q&A of each new rated item that has 2 or more (it keeps the rest), so a night of only rated turns still has a quiz."""
        n = 0
        for it in sorted(self.items.values(), key=lambda it: it.key):
            if it.kind == "rated" and it.first == d and not it.dead and not it.held and len(it.qa) >= 2:
                h = int(hashlib.sha1((str(self.cfg.seed) + "rated" + it.key).encode()).hexdigest(), 16)
                q, a = it.qa.pop(h % len(it.qa))
                it.held.append({"q": q, "a": a, "dir": "forward", "night": d})
                n += 1
        st["rated_held_out"] = n

    def extras(self, week: dict, d: int, st: Counter) -> None:
        """Habit cards from repeated tool jobs, and cards for the Desk's saved notes and Keeping track of list. These cards are built from
        the logs and files word for word (no model writes them). Each carries its source; a tracked item past its until date, finished or
        removed, and a forgotten note, leave the training pool."""
        cfg, today, want, sigs = self.cfg, self.today(), {}, {}
        if cfg.use_habits:
            for h in L_mod.habits(week, d, cfg.habit_min):
                para, qa = L_mod.habit_cards(h, self.who)
                src = "diary tool log: %d uses on %d days, %s to %s" % (h["n"], h["days"], diary_mod.date_of_day(week, h["first"]), diary_mod.date_of_day(week, h["last"]))
                want[h["key"]] = ("habit", h["target"], para, qa, src, "", h["days"])
            for h in L_mod.helper_habits(week):
                para, qa = L_mod.helper_cards(h, self.who)
                want[h["key"]] = ("delegate", h["name"], para, qa, "helper runs: %d good runs" % h["n"], "", 1)
        if cfg.use_lessons:   # Ben's thumbs up: the answer he liked, word for word (a thumbs down becomes a lesson in lessons())
            for l in L_mod.liked(week):
                r = self.items.get("rated|" + l["key"].split("|", 1)[1])
                if r and not r.dead and (r.para or r.qa or r.held):
                    st["liked_skipped_rated"] += 1   # carded by rated_stage: no second card for the same turn
                    continue
                para, qa = L_mod.liked_cards(l, self.who)
                want[l["key"]] = ("liked", l["user"][:60], para, qa, "chat %s, turn %d: %s liked the answer" % (diary_mod.date_of_day(week, l["day"]), l["turn"] + 1, self.who), "", 1)
            for v in L_mod.good_ideas(week):   # Ben Oct 28: a Mote's idea a reviewer called good
                para, qa = L_mod.idea_cards(v, self.who)
                want["idea|" + hashlib.sha1(str(v.get("id") or v["idea"]).encode()).hexdigest()[:12]] = ("idea", v["idea"][:60], para, qa, "idea review %s: %s" % (str(v.get("ts") or "")[:10], v.get("helper") or ""), "", 1)
        if cfg.use_userdata:
            ignore = diary_mod.load_ignore(self.paths.ignore)
            ud = self.paths.userdata_dir
            notes = L_mod.read_notes(ud, ignore)
            notes = [n for n in notes if not is_card_note(n)]   # card notes are fact Items (card_notes), not note cards
            nqa = self.note_qas(notes, d, st)
            for n in notes:
                para, _ = L_mod.note_cards(n, self.who)
                key, old = "note|" + n["id"], self.items.get("note|" + n["id"])
                keep = bool(old and not old.dead and old.sig == note_sig(n))   # unchanged note: its card (trainable or held) stays as it is
                sigs[key] = note_sig(n) if keep or n["id"] in nqa else ""
                want[key] = ("note", n["text"][:60], para, old.qa if keep else nqa.get(n["id"], []), "saved note" + (", updated " + n["updated"] if n["updated"] else ""), "", 1)
            for t in L_mod.read_tracking(ud, today, ignore):
                para, qa = L_mod.track_cards(t, self.who)
                want["track|" + norm(t["what"])] = ("track", t["what"][:60], para, qa, t["source"] or "Keeping track of list", t["until"], 1)
        for key, (kind, obj, para, qa, src, until, days) in want.items():
            it = self.items.get(key)
            if it and not it.dead and it.para == para and it.qa == qa and it.sig == sigs.get(key, it.sig):
                it.source, it.until, it.days = src, until, days
                continue
            self.items[key] = Item(key, self.who, obj, kind, d, first=d, days=days, nment=1, para=para, qa=qa, seen_ment=1, dreamed_night=d,
                                   kind=kind, source=src, until=until, sig=sigs.get(key, ""))
            st[kind + "_new" if not it else kind + "_changed"] += 1
        for it in self.items.values():
            if it.kind in ("habit", "note", "track", "liked", "delegate", "idea") and not it.dead and it.key not in want:
                it.dead = True
                st[it.kind + "_retired"] += 1
        st["habit"] = sum(1 for k in want if k.startswith("habit|"))
        st["note"] = sum(1 for k in want if k.startswith("note|"))
        st["track"] = sum(1 for k in want if k.startswith("track|"))
        st["liked"] = sum(1 for k in want if k.startswith("liked|"))
        st["delegate"] = sum(1 for k in want if k.startswith("delegate|"))
        st["idea"] = sum(1 for k in want if k.startswith("idea|"))

    def note_qas(self, notes: List[dict], d: int, st: Counter) -> Dict[str, List[List[str]]]:
        """One quiz card per new or changed saved note (at most max_lessons x s a night): the base model writes q and a (a = 1 to 4 words of the
        note), checked like a lesson: the answer is in the note, the question does not leak the test or the answer, and the base model gives the
        answer back from the note alone. Returns note id -> [[q, a]] or [] for a note tried and dropped (it is not tried again until it changes);
        a note left out for the cap is tried on a later night. A note made of "Subject => relation => Object" lines is a fact source: no card here."""
        out, todo = {}, []
        for n in notes:
            old = self.items.get("note|" + n["id"])
            if old and not old.dead and old.sig == note_sig(n):
                continue
            lines = [l for l in re.split(r"[\n;]", n["text"]) if l.strip()]
            if lines and all(CARD_LINES.match(l) for l in lines):
                out[n["id"]] = []
                st["note_qa_skipped_card_lines"] += 1
            else:
                todo.append(n)
        todo = todo[:self.sc(self.cfg.max_lessons)]
        if not todo:
            return out
        raw = self.gen([P.note_qa_prompt(self.R, n["text"], self.who) for n in todo], self.cfg.lesson_tokens, salt="note_qa")
        cand = []
        for n, txt in zip(todo, raw):
            out[n["id"]] = []
            c = P.parse_lesson(txt)
            q, a = (str(c.get("q") or "").strip(), str(c.get("a") or "").strip().rstrip(".")) if c else ("", "")
            if not (q and a):
                why = "parse_fail"
            elif not 1 <= len(a.split()) <= 4 or not pat(norm(a)).search(norm(n["text"])):
                why = "answer_not_in_note"
            elif norm(a) in norm(q):
                why = "answer_in_question"
            elif self.leaky(q):
                why = "test_leak"
            else:
                why = None
            if why:
                st["note_qa_dropped_" + why] += 1
            else:
                cand.append((n, q, a))
        ver = self.gen([P.ctx_prompt(self.R, n["text"], q, self.who) for n, q, a in cand], self.cfg.verify_tokens, salt="note_qa_verify")
        for (n, q, a), v in zip(cand, ver):
            if has_ans(a, v):
                out[n["id"]] = [[q, a]]
                st["note_qa_kept"] += 1
            else:
                st["note_qa_dropped_unverified"] += 1
        return out

    def leaky(self, text: str) -> bool:
        n = norm(text)
        return any(l in n or (len(n) >= 10 and n in l) for l in self.leak)

    def split_holdout(self, fresh: List[Item], d: int, st: Counter) -> None:
        """Hold out ~holdout_frac of tonight's new cards (Q&A only, never trained on). An item keeps at least 2 trainable cards, so
        its fact is still taught by other wordings and the other direction: the quiz then tests paraphrase and reverse. On a small
        night where no fact has 3 cards, a fact keeps at least 1 (a paraphrase) instead."""
        total = sum(len(it.para) + len(it.qa) for it in fresh)
        key = lambda it: hashlib.sha1((str(self.cfg.seed) + it.key).encode()).hexdigest()   # noqa: E731
        order = sorted((it for it in fresh if len(it.qa) >= 1 and len(it.para) + len(it.qa) >= 3), key=key)
        # a small night (one or two cards per fact) still holds some out, or the gate has nothing to check and undoes it: items with
        # 3+ cards first, then those with 2 (they keep one card)
        order += sorted((it for it in fresh if len(it.qa) >= 1 and len(it.para) + len(it.qa) == 2), key=key)
        want = max(2, int(round(self.cfg.holdout_frac * total))) if order else 0
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

    def top_up_holdout(self, d: int, st: Counter) -> None:
        """A night must end with at least 2 held-out cards (the gate undoes a night with none). If facts and lessons gave fewer, hold out the
        Q&A of tonight's new lessons (even when fewer than 3), then of new notes. The item keeps its paraphrase: never its only card."""
        n = sum(1 for it in self.items.values() for h in it.held if h["night"] == d)
        key = lambda it: hashlib.sha1((str(self.cfg.seed) + "topup" + it.key).encode()).hexdigest()   # noqa: E731
        pool = lambda kind: sorted((it for it in self.items.values() if it.kind == kind and it.first == d and not it.dead and it.qa and len(it.para) + len(it.qa) >= 2), key=key)   # noqa: E731
        k = 0
        for it in pool("lesson") + pool("rated") + pool("note"):
            if n + k >= 2:
                break
            q, a = it.qa.pop(0)
            it.held.append({"q": q, "a": a, "dir": "forward", "night": d})
            k += 1
        st["topup_held_out"] = k

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
                idx = sorted({i for it in (p, q) if not it.card_note_id for i in self.diary.containing(it.subj, it.obj, d)[-2:]})
                cand.append(("chain", (p, q), qq, es[0], "\n".join(x for x in (self.diary.label(idx), p.line, q.line) if x)))
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
                cand.append(("gist", (it,), qq, es[0], self.ctx_of(it, d)))
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
            if not it.dead and it.kind == "fact" and not it.card_note_id:
                groups[frozenset(it.key.split("|"))].append(it)
        for g in groups.values():
            if len(g) > 1:
                g.sort(key=lambda it: (-len(it.para) - len(it.qa), it.born))
                for x in g[1:]:
                    x.dead = True
                    st["merged"] += 1
        return dict(st)

    # ---- training examples
    def target_stat(self, **counts):
        stats = getattr(self, "N", {}).setdefault("stats", {}).setdefault("training_targets", {})
        for key, count in counts.items():
            stats[key] = stats.get(key, 0) + count

    def ex_text(self, text: str):
        # Raw language modelling intentionally supervises text tokens. Unlike QA,
        # a raw-text prefix remains a valid LM example when clipped.
        ids = self.be.encode(text) + [self.be.stop_id]
        self.target_stat(raw_lm_seen=1, raw_lm_truncated=int(len(ids) > self.cfg.max_seq_len))
        ids = ids[:self.cfg.max_seq_len]
        if len(ids) < 2:
            self.target_stat(raw_lm_skipped=1)
            return None
        self.target_stat(raw_lm_examples=1, raw_lm_target_tokens=len(ids) - 1)
        return (ids, 0)

    def ex_qa(self, q: str, a: str, rng: random.Random, d: int):
        self.target_stat(qa_seen=1)
        answer = self.be.encode(a)
        if not answer:
            self.target_stat(qa_skipped_empty_answer=1)
            return None
        # Native reasoning models start generation inside <think>. The answer
        # target must close that block, otherwise it teaches a hidden answer.
        target = self.be.encode(self.prof.training_answer_prefix) + answer + [self.be.stop_id]
        ob = rng.random() < self.cfg.ob_share
        if ob:
            p = self.be.encode(P.diary_prompt(self.R, self.diary, q, d))
            if p and len(p) + len(target) <= self.cfg.max_seq_len:
                self.target_stat(qa_examples=1, qa_open_book=1, qa_target_tokens=len(target))
                return (p + target, len(p))
            self.target_stat(qa_open_book_fallback=1)
        p = self.be.encode(P.plain_prompt(self.R, q))
        if not p or len(p) + len(target) > self.cfg.max_seq_len:
            self.target_stat(qa_skipped_too_long=1)
            return None
        self.target_stat(qa_examples=1, qa_closed_book=1, qa_target_tokens=len(target))
        return (p + target, len(p))

    def nrem(self, act: List[Item], cum: List[float], n: int, rng: random.Random, d: int):
        out = []
        for _ in range(n):
            if not act:
                break
            it = rng.choices(act, cum_weights=cum)[0]
            o = rng.choice(it.para + it.qa)
            ex = self.ex_text(o) if isinstance(o, str) else self.ex_qa(o[0], o[1], rng, d)
            if ex is not None:
                out.append(ex)
        return out

    def replay_set(self):
        # Evaluation questions never become replay contexts, including in legacy
        # prompt mode. Replay sources are the public list only, never diary facts.
        from .replay_monitor import MONITOR_QA
        excluded = [q for q, _ in gate_mod.GENERAL_QA] + [q for q, _ in MONITOR_QA]
        questions = replay_mod.public_questions(GENERIC_PROMPTS, excluded)
        if self.cfg.replay_mode == "prompt":
            return replay_mod.prompt_examples(self.be, [self.R.render(P.SYS, q) for q in questions], self.cfg.max_seq_len)
        if self.cfg.replay_mode != "continuation":
            raise ValueError("unknown replay_mode %r" % self.cfg.replay_mode)
        examples, stats = replay_mod.continuation_examples(
            self.be, self.R, questions, self.paths.home / "replay_cache.json",
            max_tokens=self.cfg.replay_max_tokens, max_seq_len=self.cfg.max_seq_len,
            before_generate=lambda n: self.clock.check((self.sec_per_batch_tok or 0.25) * n * 1.2 + 2))
        getattr(self, "N", {}).setdefault("stats", {})["replay"] = stats
        self.log("[night] replay %s" % stats)
        return examples

    def recall_identity(self, held):
        cards = [(h["q"], h["a"], h.get("dir", "forward")) for h in held]
        identity = {"cards": cards, "profile": self.prof.name, "model_dir": self.prof.model_dir,
                    "hf_id": self.prof.hf_id, "source_revision": self.prof.source_revision,
                    "backend": self.prof.backend, "loader": self.prof.loader,
                    "prompts": [self.R.render("Answer with just the name.", h["q"]) for h in held], "max_tokens": self.cfg.recall_max_tokens}
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def recall_baseline_valid(self, pre, held):
        return (gate_mod.measured_recall(pre, len(held)) and pre.get("grader") == gate_mod.GRADER
                and pre.get("cards") == self.recall_identity(held))

    def measure_incumbent_recall(self, held):
        """Regrade the unchanged incumbent, even when a candidate checkpoint exists."""
        candidate = self.paths.work_adapter if self.paths.work_adapter.exists() else None
        self.be.load_adapter(self.paths.adapter if self.paths.adapter.exists() else None)
        try:
            return dict(gate_mod.score_recall(self.be, self.R, held, adapter=True, max_tokens=self.cfg.recall_max_tokens),
                        grader=gate_mod.GRADER, cards=self.recall_identity(held))
        finally:
            if candidate is not None:
                self.be.load_adapter(candidate)

    def general_base_identity(self, rendered=True):
        identity = {"profile": self.prof.name, "model_dir": self.prof.model_dir, "n": self.cfg.gate_n,
                "hf_id": self.prof.hf_id, "source_revision": self.prof.source_revision,
                "backend": self.prof.backend, "loader": self.prof.loader,
                "max_tokens": self.cfg.gate_max_tokens, "grader": gate_mod.GRADER,
                "questions": hashlib.sha256(json.dumps(gate_mod.gate_questions(self.cfg.gate_n)).encode()).hexdigest(),
                "system": gate_mod.GATE_SYS}
        if rendered:
            identity["prompts"] = hashlib.sha256(json.dumps(gate_mod.general_prompts(self.R, self.cfg.gate_n)).encode()).hexdigest()
        return identity

    def finalization_context(self):
        """Declared model, acceptance policy and export target; no model load."""
        profile = asdict(self.prof)
        # Runtime sizing and training schedules do not authorize a gate result.
        profile.pop("runtime", None)
        profile.pop("recipe", None)
        return {"profile": profile, "policy": {key: getattr(self.cfg, key) for key in
                    ("who", "harm_max", "gate_min_gain", "gate_n", "gate_max_tokens", "recall_max_tokens")},
                "export": {key: getattr(self.cfg, key) for key in
                    ("llama_cpp_dir", "gguf_base_dir", "llama_server", "base_gguf")}}

    def _finalization_held(self):
        # Checkpoint JSON sorts item keys; the same held set must retain its
        # identity when restored with a different dictionary insertion order.
        held = []
        for it in self.items.values():
            for h in it.held:
                if not isinstance(h, dict): raise ValueError('invalid held snapshot row')
                if h.get("night") != self.N["day"]: continue
                if (type(h.get("night")) is not int or any(not isinstance(h.get(k), str) or not h[k].strip() for k in ("q", "a"))
                        or not isinstance(h.get("dir", "forward"), str)):
                    raise ValueError('invalid held snapshot row')
                held.append(h)
        held.sort(key=lambda h: (h["q"], h["a"], h.get("dir", "forward")))
        return held

    def finalization_evaluation(self):
        held = self._finalization_held()
        rows = [(h["q"], h["a"], h.get("dir", "forward")) for h in held]
        return {"general": self.general_base_identity(), "recall": self.recall_identity(held), "held_count": len(held),
                "held_sha256": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}

    def _finalization_bound(self, *, rendered=True):
        final = self.N.get("finalization")
        if (not isinstance(final, dict) or type(final.get("version")) is not int or final["version"] != 2
                or final.get("night_id") != self.N.get("id") or final.get("grader") != gate_mod.GRADER
                or final.get("grading_contract_sha256") != grading_mod.CONTRACT_SHA256):
            return False
        def same(left, right):
            try:
                return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)
            except (TypeError, ValueError):
                return False
        try:
            evaluation = final.get("evaluation")
            if (not isinstance(evaluation, dict) or set(evaluation) != {"general", "recall", "held_count", "held_sha256"}
                    or type(evaluation["held_count"]) is not int or evaluation["held_count"] < 1
                    or any(not isinstance(evaluation[key], str) or not re.fullmatch(r'[0-9a-f]{64}', evaluation[key])
                           for key in ("recall", "held_sha256"))):
                return False
            held = self._finalization_held()
            rows = [(h["q"], h["a"], h.get("dir", "forward")) for h in held]
            general = evaluation["general"]
            static = self.general_base_identity(rendered=False)
            return (isinstance(general, dict) and set(general) == set(static) | {"prompts"}
                    and isinstance(general["prompts"], str) and re.fullmatch(r'[0-9a-f]{64}', general["prompts"]) is not None
                    and same({key: general[key] for key in static}, static)
                    and evaluation["held_count"] == len(held)
                    and evaluation["held_sha256"] == hashlib.sha256(json.dumps(rows).encode()).hexdigest()
                    and same(final.get("context"), self.finalization_context())
                    and (not rendered or same(evaluation, self.finalization_evaluation())))
        except (AttributeError, KeyError, TypeError, ValueError):
            return False

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
        self._checkpoints = Checkpoints(self.paths, getattr(self, "checkpoint_hook", None))
        self._trained_since_ckpt = 0
        resumed = False
        self.N, checkpoint_items = self._checkpoints.load() if not dry_run else (None, None)
        self.load_items(checkpoint_items)
        if self.N and self.N.get("dry_run"):
            self.N = None
        if self.N:
            resumed = True
            d, date = self.N["day"], self.N["date"]
            if date not in week.get("dates", {}).values() and not self.N.get("finalization"):
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
            self.N = {"id": uuid.uuid4().hex, "day": d, "date": date, "phase": "tag", "scale": None, "done_steps": 0, "rem_done": [], "chunks": 0, "stats": {}, "elapsed_s": 0.0,
                      "dry_run": bool(dry_run), "started": time.time()}
        N = self.N
        N.setdefault("id", uuid.uuid4().hex)  # upgrade an older, resumable night
        N["chunks"] += 1
        N["steps_this_chunk"] = 0
        self.diary = Diary(week, self.who)
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
            # An unexpected failure retains the last complete generation. In
            # particular, never publish a phase change after its weight save failed.
        res["phase"] = N.get("phase")
        res["steps"] = N.get("steps_this_chunk", 0)
        res["scale"] = N.get("scale")
        return res

    def _on_stop(self, res: dict) -> None:
        """Checkpoint what is in memory when a chunk ends mid-night."""
        N = self.N
        if not N.get("dry_run"):
            self.save_night(adapter=N["phase"] == "train" and getattr(self, "_trained_since_ckpt", 0) > 0)
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
        if N["phase"] in ("finalize", "done"):
            self._finalize(res)
            return
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
            self.card_notes(d, st)
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
            else:
                # A dream-phase resume may already have split its old claims.
                # Hold new/changed source claims separately without moving any
                # unchanged held-out cards back into the training pool.
                pending = set(N.get("card_holdout_pending", []))
                changed = [it for it in fresh if it.key in pending]
                if changed:
                    previous = st.get("held_out", 0)
                    self.split_holdout(changed, d, st)
                    st["held_out"] += previous
            ready = {it.key for it in fresh}
            N["card_holdout_pending"] = [key for key in N.get("card_holdout_pending", []) if key not in ready]
            st_all["dream"] = dict(st)
            st = Counter()
            self.lessons_stage(week, d, st)
            self.rated_stage(week, d, st)
            self.extras(week, d, st)
            if "lesson_holdout_done" not in N:
                self.hold_lessons(d, st)
                N["lesson_holdout_done"] = True
            if "rated_holdout_done" not in N:
                self.hold_rated(d, st)
                N["rated_holdout_done"] = True
            if "topup_holdout_done" not in N:
                self.top_up_holdout(d, st)
                N["topup_holdout_done"] = True
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
        # Oct 28: a night with nothing held out can never pass the morning gate (it needs >= 1 held-out card), so training it is wasted time;
        # a resumed night skipped the min_cards check above and trained on 7 note cards. Skip it the same way: no training, the day stays unslept.
        if N["phase"] == "train" and not dry_run and not any(h["night"] == d for it in self.items.values() for h in it.held):
            why = "no held-out cards to check what was learned: no training tonight; the day stays unslept"
            res.update(status="dry_run", dry_run=True, message=why, cards=st_all.get("trainable_cards"), quiz=None, harm=None, lessons=list(N.get("lessons", [])))
            self.append_night(res, extra={"dry_run_reason": why, "stats": st_all})
            self.state.setdefault("small", {})[N["date"]] = sum(1 for t in self.diary.turns if t["day"] == d)
            write_json(self.paths.state, self.state)
            shutil.rmtree(str(self.paths.work), ignore_errors=True)
            N["phase"] = "done"
            return
        if N["phase"] == "train":
            self._train(week, d, E, res)
        if N["phase"] == "downscale":
            self.clock.check(30)
            self.be.load_adapter(self.paths.work_adapter)
            st_all["shy"] = self.be.downscale(cfg.shy_factor, cfg.shy_thresh, cfg.seed * 100 + d)
            N["phase"] = "gate"
            self.save_night(adapter=True)
        if N["phase"] == "gate":
            self._gate(week, d, E, res)

    def _train(self, week: dict, d: int, E: List[Item], res: dict) -> None:
        N, cfg = self.N, self.cfg
        # state of the adapter at the start of (or resuming) training
        if self.paths.work_adapter.exists():
            self.be.load_adapter(self.paths.work_adapter)
        else:
            self.be.load_adapter(self.paths.adapter if self.paths.adapter.exists() else None)
        held = [h for it in self.items.values() for h in it.held if h["night"] == d]
        if not self.recall_baseline_valid(N.get("pre"), held):
            self.clock.check(60)
            N["held_n"] = len(held)
            N["pre"] = self.measure_incumbent_recall(held)
            if not self.paths.gate_base.exists():
                flags = gate_mod.score_general(self.be, self.R, adapter=False, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
                write_json(self.paths.gate_base, dict(self.general_base_identity(), flags=flags, score=gate_mod.pct(flags)))
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
                if self._trained_since_ckpt:
                    self.save_night(adapter=True)
                before_rem = copy.deepcopy(self._items_data())
                st = Counter()
                try:
                    self.rem(E, d, ci, st)
                    new = [x for x in self.rem_pool if x.get("night") == d and x.get("cycle") == ci]
                    st["dreamcheck"] = self.check_dreams([(x, x["q"], x["a"]) for x in new], "rem")
                except BaseException:
                    # Completed generation batches stay cached, but a partial
                    # REM cycle must not increment its counters again on resume.
                    self.load_items(before_rem)
                    raise
                N["rem_done"].append(ci)
                N["stats"].setdefault("rem", []).append(dict(st))
                self.save_night()
            live = [x for x in self.rem_pool if all(k in self.items and not self.items[k].dead for k in x["keys"])]
            rng = random.Random("step:%s:%s:%s" % (cfg.seed, d, i))
            nr0 = round(0.7 * cfg.bsz) if (kind == "r" and live) else 0
            batch = []
            for x in rng.choices(live, k=nr0) if nr0 else []:
                ex = self.ex_qa(x["q"], x["a"], rng, d)
                if ex is not None:
                    batch.append(ex)
            batch += self.nrem(act, cum, cfg.bsz - len(batch), rng, d)
            rb = rng.sample(replay, min(cfg.replay_bsz, len(replay))) if i % max(cfg.kl_every, 1) == 0 else []
            t0 = self.clock.now()
            if batch:
                r = self.be.train_step(batch, rb, i)
            else:
                self.target_stat(empty_batches_skipped=1)
                r = {}
            dt = self.clock.now() - t0
            self.t_step = dt if self.t_step is None else 0.7 * self.t_step + 0.3 * dt
            last_ce = r.get("ce")
            i += 1
            N["done_steps"] = i
            N["steps_this_chunk"] = N.get("steps_this_chunk", 0) + 1
            self._trained_since_ckpt += 1
            ck = self._trained_since_ckpt >= cfg.ckpt_every
            if ck:
                self.save_night(adapter=True)
            if ck or i == total:   # the sleep bar reads "step N/N": the last step is always logged
                self.log("[night] step %d/%d ce %s %.1fs" % (i, total, last_ce, dt))
                self.log("[night] training targets %s" % N["stats"].get("training_targets", {}))
        N["last_ce"] = last_ce
        N["phase"] = "downscale"
        self.save_night(adapter=True)

    def _gate(self, week: dict, d: int, E: List[Item], res: dict) -> None:
        N, cfg, P_ = self.N, self.cfg, self.paths
        self.clock.check(90)
        self.be.load_adapter(P_.work_adapter)
        self.log("[night] quiz")
        held = [h for it in self.items.values() for h in it.held if h["night"] == d]
        post = gate_mod.score_recall(self.be, self.R, held, adapter=True, max_tokens=cfg.recall_max_tokens)
        base = read_json(P_.gate_base, {}) or {}
        flags = gate_mod.score_general(self.be, self.R, adapter=True, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
        bflags = base.get("flags") if (all(base.get(k) == v for k, v in self.general_base_identity().items())
                                       and len(base.get("flags", [])) == len(flags)) else None
        if bflags is None:   # recorded for another question set or by another grader: record the base again now (adapter off)
            bflags = gate_mod.score_general(self.be, self.R, adapter=False, max_tokens=cfg.gate_max_tokens, n=cfg.gate_n)
            write_json(P_.gate_base, dict(self.general_base_identity(), flags=bflags, score=gate_mod.pct(bflags)))
        j = gate_mod.judge(bflags, flags, cfg.harm_max)
        if not self.recall_baseline_valid(N.get("pre"), held):
            N["pre"] = self.measure_incumbent_recall(held)
            self.save_night()
        pre = N.get("pre")
        reasons = gate_mod.decide(j, pre, post, cfg.gate_min_gain)
        quiz = post["recall"]
        reverted = bool(reasons)
        if not reverted:
            for it in E:
                if it.para or it.qa:
                    it.trained = True
        result = dict(res, status="done", quiz=quiz, harm=j["harm"], general=j["general"], general_base=j["general_base"], reverted=reverted,
                      revert_reason=reasons, recall_pre=(N.get("pre") or {}).get("recall"), held_out=post["n"], recall_by_dir=post["by_dir"],
                      steps_total=N.get("total_steps"), message="night done" + (" (REVERTED: %s)" % "; ".join(reasons) if reverted else ""),
                      lessons=list(N.get("lessons", [])), dreamcheck=dc_total(N["stats"]))
        state = copy.deepcopy(self.state)
        state["nights"] += 1
        if N["date"] not in state["slept_days"]:
            state["slept_days"].append(N["date"])
        state.setdefault("slept_turns", {})[N["date"]] = self.day_turns(week, d)
        state["last_night"] = {"id": N["id"], "date": N["date"], "reverted": reverted, "quiz": quiz, "harm": j["harm"]}
        N["finalization"] = {"version": 2, "grader": gate_mod.GRADER, "night_id": N["id"],
                             "grading_contract_sha256": grading_mod.CONTRACT_SHA256,
                             "context": self.finalization_context(), "evaluation": self.finalization_evaluation(),
                             "result": result, "state": state, "extra": {
            "stats": copy.deepcopy(N["stats"]), "bench": N.get("bench"), "chunks": N["chunks"], "elapsed_s": N["elapsed_s"],
            "lessons": result["lessons"], "last_ce": N.get("last_ce"), "recall_samples": post.get("samples")}}
        N["phase"] = "finalize"
        self.save_night()
        self._finalize(res)

    def _block_finalization(self, res: dict, reason: str) -> None:
        res.update(status="stopped", quiz=None, interrupted=True, blocked=True,
                   stop_reason="gate_recheck_required", gate_recheck_required=True,
                   message="stopped: %s; explicit re-gate with comparable baselines is required before promotion; checkpoint and candidate retained" % reason)
        self.log("[night] " + res["message"])

    def _finalization_payload_valid(self, final) -> bool:
        N = self.N
        if (not isinstance(final, dict) or not all(isinstance(final.get(k), dict) for k in ("result", "state", "extra"))
                or not isinstance(N.get("id"), str) or not re.fullmatch(r"[0-9a-f]{32}", N["id"])
                or not isinstance(N.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", N["date"])
                or type(N.get("day")) is not int or N["day"] <= 0):
            return False
        result, state = final["result"], final["state"]
        last = state.get("last_night")
        return (result.get("status") == "done" and type(result.get("reverted")) is bool
                and result.get("date") == N["date"] and type(result.get("day")) is int and result["day"] == N["day"]
                and type(state.get("nights")) is int and state["nights"] > 0
                and type(result.get("night")) is int and result["night"] == state["nights"]
                and isinstance(state.get("slept_days"), list) and N["date"] in state["slept_days"]
                and isinstance(last, dict) and last.get("id") == N["id"] and last.get("date") == N["date"]
                and type(last.get("reverted")) is bool and last["reverted"] == result["reverted"])

    def _finalization_block_reason(self) -> Optional[str]:
        """Read-only admission shared by worker preflight and finalization."""
        N = self.N
        final = N.get("finalization")
        if not self._finalization_payload_valid(final):
            return "saved gate decision has an invalid payload or night identity"
        self._checkpoints = getattr(self, "_checkpoints", None) or Checkpoints(self.paths)
        bound = self._finalization_bound(rendered=self.R is not None)
        if not bound:
            # A saved rejection cannot promote or export. Its original gate did
            # not mark new items trained, so it may complete after an upgrade.
            committed = final["result"]["reverted"] is True
            reason = "saved gate decision has a missing or changed model, evaluation or grader binding"
            if not committed:
                try:
                    committed = self._checkpoints.is_committed(N)
                except CheckpointError as error:
                    reason = "saved gate decision cannot prove committed adapter identity: %s" % error
            if not committed:
                # Old decisions already changed item.trained in their immutable
                # checkpoint. There is no reliable pre-decision item snapshot
                # with which to undo that metadata after a different regrade.
                # Keep the entire checkpoint untouched for an explicit re-gate.
                return reason
        return None

    def _finalize(self, res: dict) -> None:
        """Replay a published decision without rotating twice or rescoring it."""
        N, cfg, P_ = self.N, self.cfg, self.paths
        reason = self._finalization_block_reason()
        if reason:
            self._block_finalization(res, reason)
            return
        final = N["finalization"]
        export_authorized = self._finalization_bound()
        resumed = res.get("resumed", False)
        res.update(final["result"])
        res["resumed"] = resumed
        if res["reverted"]:
            self.be.load_adapter(P_.adapter if P_.adapter.exists() else None)
        else:
            self._checkpoints.promote(N)
            if cfg.llama_cpp_dir and not export_authorized:
                # Historical committed outcomes may finish bookkeeping, but a
                # changed model/configuration cannot relabel or export weights.
                res["gguf"] = {"ok": None, "pending": True, "message": "export deferred: saved gate context is not current; explicit matching re-gate required"}
                res.pop("served", None)
                final["result"] = dict(res)
            elif cfg.llama_cpp_dir:
                # Export rotates GGUF files separately. A crash during export is
                # recorded as incomplete rather than silently rotating again.
                if not final.get("export_started"):
                    final["export_started"] = True
                    self.save_night()
                    try:
                        from . import export as export_mod
                        ok, msg = (self.exporter or export_mod.export_gguf)(cfg.llama_cpp_dir, cfg.gguf_base_dir, P_.adapter, P_.home / "adapter.gguf")
                        if ok:
                            gguf = P_.home / "adapter.gguf"
                            if not gguf.is_file() or gguf.stat().st_size == 0:
                                raise ValueError("converter reported success without a nonempty GGUF output file")
                            # Artifact hashing/metadata publication is part of
                            # export. Its failure must not undo the trained night.
                            self._after_export(gguf, res)
                    except Exception as e:
                        ok, msg = False, "%s: %s" % (type(e).__name__, e)
                        self.served_pending = False
                        res.pop("served", None)
                    res["gguf"] = {"ok": ok, "message": msg}
                    self.log("[night] gguf export: %s %s" % ("ok" if ok else "FAILED", msg))
                    final["result"] = dict(res)
                    self.save_night()
                else:
                    res.setdefault("gguf", {"ok": False, "message": "previous export was interrupted; export-gguf can retry it"})
                from . import export as export_mod, served as served_mod
                side = read_json(export_mod.sidecar_path(P_.home / "adapter.gguf"), {}) or {}
                if isinstance(side, dict) and side.get("night_id") == N["id"]:
                    if served_mod.pending_check(P_):
                        self.served_pending = True
                    if side.get("served"):
                        res["served"] = side["served"]
        self.state = final["state"]
        write_json(P_.state, self.state)
        self._checkpoints.hook("state_written")
        self.save_items()
        self.write_cards()
        self._checkpoints.hook("items_written")
        self.append_night(res, extra=dict(final["extra"], night_id=N["id"]))
        self._checkpoints.hook("history_written")
        N["phase"] = "done"
        # Once done is published, state/history are durable. Remove the manifest
        # before deleting generations, so partial cleanup cannot expose a dangling one.
        self.save_night()
        self._checkpoints.hook("finalized")
        P_.night_json.unlink()
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
        from . import served as served_mod
        artifact = {"version": 1, "sha256": served_mod.artifact_hash(gguf), "bytes": gguf.stat().st_size}
        side = {"base_hf_id": self.prof.hf_id, "profile": self.prof.name, "base_dir": cfg.gguf_base_dir,
                "base_gguf": cfg.base_gguf, "artifact": artifact,
                "night_id": self.N["id"], "date": self.N.get("date"), "night": self.state.get("nights", 0) + 1, "created": time.time()}
        if not (cfg.llama_server and cfg.base_gguf):
            res["served"] = {"ok": None, "reasons": ["not checked: no llama-server configured (SLEEPMLX_LLAMA_SERVER, SLEEPMLX_BASE_GGUF)"]}
        else:
            d = self.N["day"]
            held = [{"q": h["q"], "a": h["a"]} for it in self.items.values() for h in it.held if h["night"] == d]
            previous = export_mod.prev_path(gguf)
            side["served_pending"] = {"version": 1, "night_id": self.N["id"], "profile": self.prof.name,
                                      "base_hf_id": self.prof.hf_id, "base_gguf": cfg.base_gguf, "llama_server": cfg.llama_server,
                                      "adapter": self.paths.adapter.relative_to(self.paths.home).as_posix(),
                                      "sha256": artifact["sha256"],
                                      "previous_hash": served_mod.artifact_hash(previous) if previous.is_file() else None,
                                      "held": held}
            self.served_pending = True
            res["served"] = {"ok": None, "pending": True, "reasons": ["checked after the trainer's model is unloaded"]}
        side["served"] = res["served"]
        # One atomic sidecar publishes the identity and deferred work together.
        write_json(export_mod.sidecar_path(gguf), side)

    def finish_served(self, res: dict) -> None:
        """Replay the durable served check after the trainer has unloaded."""
        from . import served as served_mod
        self.served_pending = False
        result = served_mod.finish_pending(self.paths, self.prof, self.cfg, checker=self.served_checker, log=self.log)
        if result is not None:
            res["served"] = result

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
        write_text(self.paths.cards, "".join(json.dumps(r) + "\n" for r in self.card_rows()))

    def append_night(self, res: dict, extra: Optional[dict] = None) -> None:
        row = {"ts": time.time(), "date": res.get("date"), "night": res.get("night"), "status": res.get("status"), "dry_run": res.get("dry_run"),
               "night_id": getattr(self, "N", {}).get("id"),
               "scale": res.get("scale"), "quiz": res.get("quiz"), "recall_pre": res.get("recall_pre"), "harm": res.get("harm"), "general": res.get("general"),
               "reverted": res.get("reverted"), "steps": res.get("steps_total"), "held_out": res.get("held_out"), "profile": self.prof.name}
        row.update(extra or {})
        previous = self.paths.nights.read_text() if self.paths.nights.exists() else ""
        if row.get("night_id"):
            for line in previous.splitlines():
                try:
                    if json.loads(line).get("night_id") == row["night_id"]:
                        return
                except ValueError:
                    continue
        write_text(self.paths.nights, previous + ("\n" if previous and not previous.endswith("\n") else "") + json.dumps(row) + "\n")
