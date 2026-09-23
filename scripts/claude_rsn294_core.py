#!/usr/bin/env python3
"""rsn-294: a learned, brain-style reasoner (loop) and its equal-size plain twin.

Design: design/v3/30-modes/294-learned-reasoner-plan.md.

WHAT IT DOES
  Input  = one question FRAME (as the reader hands it over: kind, who, relations, value,
           direction) + the NOTEBOOK rows about the people involved.
  Output = ONE action from a fixed menu:
             UNK (I don't know) | YES | NO | COUNT_0..COUNT_12 | WHO_0 | WHO_1 |
             ROWV_i (answer = row i's value) | ROWS_i (answer = row i's subject)
           plus a per-row "I used this fact" support bit.
  Every answer is COPIED from a notebook row or a fixed token, so the reasoner cannot make up
  a name or a value (the "better than a brain" part).  Names, values and relation names are
  replaced by anonymous symbols that are re-shuffled every episode, so memorising facts can
  never pay: the only way to score is to read the rows.

TWO ARMS, SAME NUMBER OF LEARNED NUMBERS (the one change in exp 294)
  plain : 6 ordinary transformer layers, width 640 (about 30M numbers).
  loop  : 2 transformer layers of width 1024, run again and again (a thought is re-read and
          refined each pass; more passes on harder questions).  Same number of learned
          numbers, more compute per question.

Nothing here reads any TEST-ONLY panel.  The panel is read only by claude_rsn294_run.py eval.
"""
from __future__ import annotations

import json
import math
import random
import string
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

KINDS = ["value", "who", "yesno", "count", "compare", "before", "after"]
DIRS = [None, "more", "less"]
MAX_ROWS = 48
MAX_COUNT = 12
N_SYM = 160          # anonymous symbols per episode (names / values)
N_REL = 48           # anonymous relation symbols per episode
MAX_WHO = 2
MAX_HOPS = 3

# action layout
A_UNK, A_YES, A_NO = 0, 1, 2
A_COUNT0 = 3
A_WHO0 = A_COUNT0 + MAX_COUNT + 1          # 16
A_ROWV0 = A_WHO0 + MAX_WHO                 # 18
A_ROWS0 = A_ROWV0 + MAX_ROWS               # 66
N_ACT = A_ROWS0 + MAX_ROWS                 # 114


# ----------------------------------------------------------------------------------------
# practice-episode generator (fictional names only; freshly invented every episode)
# ----------------------------------------------------------------------------------------
_ON = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "dr",
       "gr", "kl", "st", "th", "tr", "vr", "sh", "ph", "qu", "j", "h", "w", "y", "x"]
_NU = ["a", "e", "i", "o", "u", "ae", "ai", "ou", "ea", "io", "y"]
_CO = ["", "n", "r", "l", "s", "th", "x", "nd", "rk", "sk", "m", "v", "sh", "t"]


def fake_name(rng: random.Random) -> str:
    n = "".join(rng.choice(_ON) + rng.choice(_NU) for _ in range(rng.choice([1, 2, 2, 3])))
    return (n + rng.choice(_CO)).capitalize()


PERSON_RELS = ["sister", "brother", "boss", "friend", "mother", "father", "neighbor",
               "coach", "cousin", "partner", "mentor", "roommate", "teacher", "aunt", "uncle"]
MULTI_RELS = ["child", "pet", "sibling", "car", "grandchild", "colleague", "student"]
THING_RELS = ["lives_in", "employer", "dog", "cat", "favorite_food", "favorite_color",
              "hobby", "job", "school", "instrument", "hometown", "team", "language",
              "car_brand", "favorite_book", "street"]
NUM_RELS = ["birth_year", "height_cm", "age", "shoe_size", "salary", "weight_kg",
            "house_number", "score"]
YEAR_RELS = ["lives_in", "employer", "job", "school", "team"]


def thing_value(rng: random.Random, rel: str) -> str:
    # 1 in 5 values are two words; collisions between invented words are rare and harmless
    return fake_name(rng) if rng.random() < 0.8 else (fake_name(rng) + " " + fake_name(rng))


def num_value(rng: random.Random, rel: str) -> int:
    lo, hi = {"birth_year": (1930, 2020), "height_cm": (120, 210), "age": (3, 99),
              "shoe_size": (30, 50), "salary": (20000, 200000), "weight_kg": (30, 140),
              "house_number": (1, 999), "score": (0, 100)}[rel]
    return rng.randint(lo, hi)


class Book:
    def __init__(self, rng):
        self.rng = rng
        self.rows: list[dict] = []
        self.when = 0
        self.used: set[str] = set()

    def name(self) -> str:
        while True:
            n = fake_name(self.rng)
            if n not in self.used:
                self.used.add(n)
                return n

    def add(self, s, r, v, year=None) -> str:
        self.when += 1
        row = {"fid": "", "subject": s, "relation": r, "value": str(v), "when": self.when}
        if year is not None:
            row["year"] = int(year)
        self.rows.append(row)
        return row

    def distract(self, k: int, people: list[str]):
        taken = {(x["subject"], x["relation"]) for x in self.rows}
        added = 0
        while added < k:
            s = self.rng.choice(people + [self.name()])
            u = self.rng.random()
            r = self.rng.choice(PERSON_RELS if u < 0.35 else THING_RELS if u < 0.8 else NUM_RELS)
            if (s, r) in taken:          # never a second value for a pair already in the book
                continue
            v = num_value(self.rng, r) if r in NUM_RELS else self.name()
            self.add(s, r, v)
            taken.add((s, r))
            added += 1

    def finish(self):
        """shuffle rows (keep 'when' stamps), assign fids"""
        self.rng.shuffle(self.rows)
        for i, r in enumerate(self.rows):
            r["fid"] = f"f{i + 1}"
        return self.rows


def _frame(kind, who=(), rels=(), value=None, direction=None):
    return {"kind": kind, "who": list(who), "relations": list(rels), "value": value,
            "direction": direction}


def gen_episode(rng: random.Random, kind: str | None = None, hops: int | None = None,
                n_rows: tuple[int, int] = (4, 14)) -> dict:
    """One practice episode: notebook rows + frame + gold (answer, support fids)."""
    kinds = ["value1", "value2", "who", "yesno", "count", "compare", "before", "after",
             "correction", "missing"]
    k = kind or rng.choice(kinds)
    b = Book(rng)
    target_rows = rng.randint(*n_rows)
    sup: list[dict] = []
    ans: str
    A = b.name()
    if k in ("value1", "value2", "value3", "value"):
        h = hops or {"value1": 1, "value2": 2, "value3": 3}.get(k, rng.choice([1, 2]))
        cur, rels = A, []
        for i in range(h - 1):
            r = rng.choice(PERSON_RELS)
            nxt = b.name()
            sup.append(b.add(cur, r, nxt)); rels.append(r); cur = nxt
        r = rng.choice(THING_RELS + NUM_RELS)
        v = thing_value(rng, r) if r in THING_RELS else num_value(rng, r)
        sup.append(b.add(cur, r, v)); rels.append(r)
        ans = str(v)
        # near-miss distractors: same final relation for other people, other rels for cur
        for _ in range(rng.randint(1, 3)):
            b.add(b.name(), r, thing_value(rng, r) if r in THING_RELS else num_value(rng, r))
        fr = _frame("value", [A], rels)
    elif k == "correction":
        r = rng.choice(THING_RELS)
        v1, v2 = thing_value(rng, r), thing_value(rng, r)
        b.add(A, r, v1)
        b.distract(rng.randint(0, 3), [A])
        sup.append(b.add(A, r, v2))
        ans = v2
        fr = _frame("value", [A], [r])
    elif k == "missing":
        r = rng.choice(THING_RELS + PERSON_RELS)
        other = [x for x in THING_RELS + PERSON_RELS if x != r]
        b.add(b.name(), r, thing_value(rng, r))              # someone else has r
        b.add(A, rng.choice(other), thing_value(rng, r))     # A has something else
        ans = "UNKNOWN"
        rels = [r]
        if rng.random() < 0.3:                               # broken two-step chain
            p = rng.choice(PERSON_RELS)
            B = b.name()
            b.add(A, p, B)
            b.add(B, rng.choice([x for x in other if x not in PERSON_RELS] or other),
                  thing_value(rng, r))
            rels = [p, r]
        fr = _frame("value", [A], rels)
    elif k == "who":
        r = rng.choice(PERSON_RELS + THING_RELS)
        v = b.name() if r in PERSON_RELS else thing_value(rng, r)
        sup.append(b.add(A, r, v))
        for _ in range(rng.randint(1, 3)):                   # same relation, other values
            b.add(b.name(), r, b.name() if r in PERSON_RELS else thing_value(rng, r))
        ans = A
        fr = _frame("who", [], [r], v)
    elif k == "yesno":
        r = rng.choice(THING_RELS + PERSON_RELS)
        v = b.name() if r in PERSON_RELS else thing_value(rng, r)
        row = b.add(A, r, v)
        sup.append(row)
        if rng.random() < 0.5:
            ans, asked = "yes", v
        else:
            ans = "no"
            asked = b.name() if r in PERSON_RELS else thing_value(rng, r)
            if rng.random() < 0.5:                           # the asked value belongs to someone else
                b.add(b.name(), r, asked)
        fr = _frame("yesno", [A], [r], asked)
    elif k == "count":
        r = rng.choice(MULTI_RELS)
        n = rng.randint(1, 7)
        for _ in range(n):
            sup.append(b.add(A, r, b.name()))
        for _ in range(rng.randint(0, 3)):
            b.add(b.name(), r, b.name())
        ans = str(n)
        fr = _frame("count", [A], [r])
    elif k == "compare":
        r = rng.choice(NUM_RELS)
        B = b.name()
        va, vb = num_value(rng, r), num_value(rng, r)
        while vb == va:
            vb = num_value(rng, r)
        sup += [b.add(A, r, va), b.add(B, r, vb)]
        d = rng.choice(["more", "less"])
        ans = (A if va > vb else B) if d == "more" else (A if va < vb else B)
        if rng.random() < 0.5:
            b.add(b.name(), r, num_value(rng, r))
        fr = _frame("compare", [A, B], [r], None, d)
    elif k in ("before", "after"):
        r = rng.choice(YEAR_RELS)
        n = rng.randint(2, 4)
        years = sorted(rng.sample(range(1960, 2026), n))
        vals = [thing_value(rng, r) for _ in range(n)]
        rows = [b.add(A, r, vals[i], years[i]) for i in range(n)]
        i = rng.randint(1, n - 1) if k == "before" else rng.randint(0, n - 2)
        j = i - 1 if k == "before" else i + 1
        ans = vals[j]
        sup += [rows[i], rows[j]]
        fr = _frame(k, [A], [r], vals[i])
    else:
        raise ValueError(k)
    b.distract(max(0, target_rows - len(b.rows)), [A])
    rows = b.finish()
    return {"category": k, "notebook": rows, "frame": fr,
            "gold": {"answer": ans, "support": [r["fid"] for r in sup]}}


# ----------------------------------------------------------------------------------------
# encoding: anonymous symbols, re-shuffled per episode
# ----------------------------------------------------------------------------------------
@dataclass
class Enc:
    kind: torch.Tensor        # [B]
    dirn: torch.Tensor        # [B]
    who: torch.Tensor         # [B, MAX_WHO]   sym id + 1 (0 = none)
    frels: torch.Tensor       # [B, MAX_HOPS]  rel id + 1 (0 = none)
    fval: torch.Tensor        # [B]            sym id + 1 (0 = none)
    fnum: torch.Tensor        # [B, 2]         frame value numeric rank feature, has-num
    subj: torch.Tensor        # [B, R]
    rel: torch.Tensor         # [B, R]
    val: torch.Tensor         # [B, R]
    num: torch.Tensor         # [B, R, 6]      numeric features
    mask: torch.Tensor        # [B, R] True = real row

    def to(self, dev):
        return Enc(**{k: v.to(dev) for k, v in self.__dict__.items()})


def _isnum(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _key(s) -> str:
    return str(s).strip().lower()


def encode(items: list[dict], rng: random.Random) -> tuple[Enc, list[dict]]:
    """items: [{notebook, frame}] -> tensors + per-item decode info."""
    B = len(items)
    R = max(1, min(MAX_ROWS, max(len(it["notebook"]) for it in items)))
    z = lambda *s: torch.zeros(*s, dtype=torch.long)
    kind, dirn, fval = z(B), z(B), z(B)
    who, frels = z(B, MAX_WHO), z(B, MAX_HOPS)
    fnum = torch.zeros(B, 2)
    subj, rel, val = z(B, R), z(B, R), z(B, R)
    num = torch.zeros(B, R, 6)
    mask = torch.zeros(B, R, dtype=torch.bool)
    infos = []
    for b, it in enumerate(items):
        rows = it["notebook"][:MAX_ROWS]
        fr = it["frame"]
        syms = rng.sample(range(N_SYM), N_SYM)
        rels = rng.sample(range(N_REL), N_REL)
        smap, rmap = {}, {}

        def sid(x):
            k = _key(x)
            if k not in smap:
                smap[k] = syms[len(smap) % N_SYM]
            return smap[k] + 1

        def rid(x):
            k = _key(x)
            if k not in rmap:
                rmap[k] = rels[len(rmap) % N_REL]
            return rmap[k] + 1

        nums = sorted({float(r["value"]) for r in rows if _isnum(r["value"])})
        years = sorted({int(r["year"]) for r in rows if r.get("year") is not None})
        whens = sorted({int(r.get("when", 0)) for r in rows})
        rank = lambda xs, x: (xs.index(x) + 1) / (len(xs) + 1) if x in xs else 0.0
        # (ranks, not raw numbers: only order matters for older/taller/before/after)
        kind[b] = KINDS.index(fr["kind"]) if fr["kind"] in KINDS else 0
        dirn[b] = DIRS.index(fr.get("direction")) if fr.get("direction") in DIRS else 0
        for i, w in enumerate((fr.get("who") or [])[:MAX_WHO]):
            who[b, i] = sid(w)
        for i, r in enumerate((fr.get("relations") or [])[:MAX_HOPS]):
            frels[b, i] = rid(r)
        if fr.get("value") not in (None, ""):
            fval[b] = sid(fr["value"])
            if _isnum(fr["value"]) and float(fr["value"]) in nums:
                fnum[b] = torch.tensor([rank(nums, float(fr["value"])), 1.0])
        for i, r in enumerate(rows):
            subj[b, i] = sid(r["subject"])
            rel[b, i] = rid(r["relation"])
            val[b, i] = sid(r["value"])
            isn = _isnum(r["value"])
            y = r.get("year")
            num[b, i] = torch.tensor([
                rank(nums, float(r["value"])) if isn else 0.0, 1.0 if isn else 0.0,
                rank(years, int(y)) if y is not None else 0.0, 1.0 if y is not None else 0.0,
                rank(whens, int(r.get("when", 0))), 1.0])
            mask[b, i] = True
        infos.append({"rows": rows, "who": list(fr.get("who") or [])})
    return Enc(kind, dirn, who, frels, fval, fnum, subj, rel, val, num, mask), infos


def decode(action: int, info: dict) -> str:
    """action id -> answer string (always copied, never generated)."""
    rows = info["rows"]
    if action == A_UNK:
        return "UNKNOWN"
    if action == A_YES:
        return "yes"
    if action == A_NO:
        return "no"
    if A_COUNT0 <= action < A_WHO0:
        return str(action - A_COUNT0)
    if A_WHO0 <= action < A_ROWV0:
        i = action - A_WHO0
        return info["who"][i] if i < len(info["who"]) else "UNKNOWN"
    if A_ROWV0 <= action < A_ROWS0:
        i = action - A_ROWV0
        return rows[i]["value"] if i < len(rows) else "UNKNOWN"
    i = action - A_ROWS0
    return rows[i]["subject"] if i < len(rows) else "UNKNOWN"


def gold_action(item: dict, info: dict) -> int | None:
    """the action that yields the gold answer (for the copy phase); None if no action does."""
    g = _key(item["gold"]["answer"])
    kind = item["frame"]["kind"]
    if g == "unknown":
        return A_UNK
    if kind == "yesno":
        return A_YES if g == "yes" else A_NO
    if kind == "count":
        return A_COUNT0 + int(g) if g.isdigit() and int(g) <= MAX_COUNT else None
    if kind == "compare":
        for i, w in enumerate(info["who"][:MAX_WHO]):
            if _key(w) == g:
                return A_WHO0 + i
        return None
    sup = set(item["gold"].get("support") or [])
    col, base = ("subject", A_ROWS0) if kind == "who" else ("value", A_ROWV0)
    cands = [i for i, r in enumerate(info["rows"]) if _key(r[col]) == g]
    pref = [i for i in cands if info["rows"][i]["fid"] in sup]
    pick = (pref or cands)
    return base + pick[0] if pick else None


# ----------------------------------------------------------------------------------------
# the two networks
# ----------------------------------------------------------------------------------------
class Embed(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.sym = nn.Embedding(N_SYM + 1, d, padding_idx=0)
        self.rel = nn.Embedding(N_REL + 1, d, padding_idx=0)
        self.kind = nn.Embedding(len(KINDS), d)
        self.dirn = nn.Embedding(len(DIRS), d)
        self.slot = nn.Embedding(4 + MAX_WHO + MAX_HOPS, d)  # token-role embeddings
        self.num = nn.Linear(6, d)
        self.fnum = nn.Linear(2, d)
        self.subj_p = nn.Linear(d, d, bias=False)
        self.val_p = nn.Linear(d, d, bias=False)

    def forward(self, e: Enc) -> tuple[torch.Tensor, torch.Tensor]:
        B, R = e.subj.shape
        ids = torch.arange(4 + MAX_WHO + MAX_HOPS, device=e.subj.device)
        S = self.slot(ids)
        head = [self.kind(e.kind) + self.dirn(e.dirn) + S[0]]                 # 0: kind/dir
        for i in range(MAX_WHO):
            head.append(self.subj_p(self.sym(e.who[:, i])) + S[1 + i])
        for i in range(MAX_HOPS):
            head.append(self.rel(e.frels[:, i]) + S[1 + MAX_WHO + i])
        head.append(self.val_p(self.sym(e.fval)) + self.fnum(e.fnum) + S[1 + MAX_WHO + MAX_HOPS])
        h = torch.stack(head, 1)                                                # [B, H, d]
        rows = (self.subj_p(self.sym(e.subj)) + self.rel(e.rel) + self.val_p(self.sym(e.val))
                + self.num(e.num) + S[-1])
        x = torch.cat([h, rows], 1)
        hm = torch.cat([(e.who != 0), (e.frels != 0)], 1)
        m = torch.cat([torch.ones(B, 1, dtype=torch.bool, device=x.device), hm,
                       torch.ones(B, 1, dtype=torch.bool, device=x.device), e.mask], 1)
        return x, m


class Heads(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        self.fixed = nn.Linear(d, A_ROWV0)       # UNK YES NO COUNT* WHO*
        self.rowv = nn.Linear(d, 1)
        self.rows = nn.Linear(d, 1)
        self.sup = nn.Linear(d, 1)
        self.rowq = nn.Linear(d, d)

    def forward(self, x, e: Enc):
        x = self.norm(x)
        H = 1 + MAX_WHO + MAX_HOPS + 1
        cls, rows = x[:, 0], x[:, H:]
        q = self.rowq(cls).unsqueeze(1)
        r = rows * torch.sigmoid(q)
        B, R = e.mask.shape
        lv = torch.full((B, MAX_ROWS), -1e9, device=x.device)
        ls = torch.full((B, MAX_ROWS), -1e9, device=x.device)
        lv[:, :R] = self.rowv(r).squeeze(-1).masked_fill(~e.mask, -1e9)
        ls[:, :R] = self.rows(r).squeeze(-1).masked_fill(~e.mask, -1e9)
        fixed = self.fixed(cls)
        nwho = (e.who != 0).sum(1, keepdim=True)
        widx = torch.arange(MAX_WHO, device=x.device).unsqueeze(0)
        fixed[:, A_WHO0:A_ROWV0] = fixed[:, A_WHO0:A_ROWV0].masked_fill(widx >= nwho, -1e9)
        logits = torch.cat([fixed, lv, ls], 1)
        sup = torch.full((B, MAX_ROWS), -1e9, device=x.device)
        sup[:, :R] = self.sup(rows).squeeze(-1).masked_fill(~e.mask, -1e9)
        return logits, sup


def _layer(d, heads):
    return nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, batch_first=True,
                                      norm_first=True, activation="gelu")


class PlainThinker(nn.Module):
    """ordinary transformer: 6 different layers, one pass."""

    def __init__(self, d=640, layers=6, heads=10):
        super().__init__()
        self.emb, self.heads = Embed(d), Heads(d)
        self.layers = nn.ModuleList([_layer(d, heads) for _ in range(layers)])

    def forward(self, e: Enc, steps: int | None = None):
        x, m = self.emb(e)
        for L in self.layers:
            x = L(x, src_key_padding_mask=~m)
        return self.heads(x, e)


class LoopThinker(nn.Module):
    """brain-style: one small group of layers re-applied `steps` times to the same thought,
    re-reading the notebook rows by attention on every pass; a step signal tells it which
    pass it is on.  Train with a random number of passes; think longer when it is harder."""

    def __init__(self, d=1024, layers=2, heads=8):
        super().__init__()
        self.emb, self.heads = Embed(d), Heads(d)
        self.block = nn.ModuleList([_layer(d, heads) for _ in range(layers)])
        self.step = nn.Embedding(64, d)
        self.inject = nn.Linear(2 * d, d)       # keep the input in view each pass

    def forward(self, e: Enc, steps: int = 6):
        x0, m = self.emb(e)
        x = x0
        for t in range(steps):
            x = self.inject(torch.cat([x, x0], -1)) + self.step.weight[t]
            for L in self.block:
                x = L(x, src_key_padding_mask=~m)
        return self.heads(x, e)


def build(arm: str, size: str = "30m") -> nn.Module:
    if size == "tiny":            # CPU smoke tests only
        return PlainThinker(64, 3, 4) if arm == "plain" else LoopThinker(112, 1, 4)
    return PlainThinker() if arm == "plain" else LoopThinker()


def n_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


# ----------------------------------------------------------------------------------------
# reward (the code checker; used for practice only, never sees a panel)
# ----------------------------------------------------------------------------------------
def reward(pred: str, gold: str) -> float:
    p, g = _key(pred), _key(gold)
    if g == "unknown":
        return 0.3 if p == "unknown" else -2.0        # answering with no fact = inventing
    if p == "unknown":
        return -0.5
    return 1.0 if p == g else -1.0


def supported(action: int, sup_bits: list[bool], info: dict) -> bool:
    """fact-check on the way out: a row answer must cite its own row; cited rows exist."""
    if A_ROWV0 <= action < N_ACT:
        i = (action - A_ROWV0) % MAX_ROWS
        return i < len(info["rows"]) and sup_bits[i]
    return True


if __name__ == "__main__":
    rng = random.Random(0)
    for k in ["value1", "value2", "value3", "who", "yesno", "count", "compare", "before",
              "after", "correction", "missing"]:
        ep = gen_episode(rng, k)
        enc, infos = encode([ep], rng)
        ga = gold_action(ep, infos[0])
        assert ga is not None and _key(decode(ga, infos[0])) == _key(ep["gold"]["answer"]), k
    for arm in ("plain", "loop"):
        print(arm, n_params(build(arm)))
    print("selftest ok")
