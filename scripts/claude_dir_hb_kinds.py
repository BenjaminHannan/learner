#!/usr/bin/env python3
"""Fact-combining test for the learned reasoner: dates and multi-part questions (Director helper HB, 2026-09-28).

Design: artifacts/claude-dir-hb-dates-20260928/DESIGN.md; marks: PASSMARKS.md (same folder). Pure python (no torch, no numpy).

What one item is.  A "store" of recalled facts, written as rows of tokens (fictional people and activities are anonymous labels,
relabelled every item), followed by one to three question rows.  The learned reasoner must WRITE the answers into the blank cells.
A code stand-in plays the reader (it hands over the facts as tokens): disclosed test scaffolding, never product work.
No rule inside the net or in the scoring path answers a question; the checker re-derives every answer from the TOKENS.

Grid: W = 12 columns, no absolute positions in the net (only relative offsets), so the identity of a question is carried by tokens.
  fact row  [FACT, person, activity, year, month, day-tens, day-ones, flag1, flag2, flag3, -, -]
            flag j is a slot (input token FSLOT_j) only when question j is a "set" question; the net writes FLAG1 on the members.
  ques row  [op, arg1..arg6, ans1..ans4, QIDX_j]   answer slots (input MASK) in columns 7..10, QIDX_j names the question (1..3).
Ops (one question row each):
  WHEN   person, activity            -> date                          (single recall, the control)
  DIFF   p1 a1 p2 a2                 -> sign + 3 digits: days from event 1 to event 2 (AFTER if event 2 is later)
  PLUS   person, activity, N (3 dig) -> the date N days after the event
  DIFFT  person, activity, date T    -> sign + 3 digits: days from the event to T
  FIRST  p1 a1 p2 a2                 -> flag the earlier of the two fact rows
  JOIN   activity A, activity B      -> flag the A-row of every person who has both an A row and a B row (1 to 3 people)
  SETM   month, year                 -> flag every fact row in that month (1 to 4 rows)
  COUNT  person                      -> two digits: how many fact rows the person has
  COUNTM month, year                 -> two digits: how many fact rows fall in that month
Calendar: 2025-2027 are all non-leap years (no leap-year rule is needed); stored facts lie in 2025-2026; PLUS answers stay in 2027 or earlier.
Every (person, activity) pair occurs once per store and all dates in a store differ, so every answer is unique.

  python3 -B scripts/claude_dir_hb_kinds.py selftest
  python3 -B scripts/claude_dir_hb_kinds.py panels --out DIR        (writes dev and holdout panels as jsonl + sha256 lines)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

W = 12
BLANK, MASK, DIG = 0, 1, 2                       # digits 0-9 -> 2..11
FACT = 12
OPS = ["WHEN", "DIFF", "PLUS", "DIFFT", "FIRST", "JOIN", "SETM", "COUNT", "COUNTM"]
OP_T = {o: 13 + i for i, o in enumerate(OPS)}    # 13..21
T_OP = {v: k for k, v in OP_T.items()}
AFTER, BEFORE, SAME = 22, 23, 24
FLAG0, FLAG1 = 25, 26
YEAR0, MON0 = 27, 30                             # years 2025..2027 -> 27..29 ; months 1..12 -> 30..41
PER0, NPER = 42, 40                              # 42..81
ACT0, NACT = 82, 30                              # 82..111
QIDX0 = 112                                      # 112..114
FSLOT0 = 115                                     # 115..117 (input token of a flag slot for question 1..3)
VOCAB = 118
DATE_OPS = ["DIFF", "PLUS", "DIFFT", "FIRST"]
MULTI_OPS = ["JOIN", "SETM", "COUNT", "COUNTM"]
FLAG_OPS = {"FIRST", "JOIN", "SETM"}
D0 = dt.date(2025, 1, 1)
MAX_DATE = dt.date(2027, 12, 31)
STORE_LAST = dt.date(2026, 12, 31)
N_STORE_DAYS = (STORE_LAST - D0).days + 1        # 730

SPLITS = {   # name: (facts lo, facts hi)
    "s0": (8, 12), "s1": (8, 12), "s2": (8, 12), "s3": (16, 20)}
SPLIT_SEED = {"s0": 0, "s1": 1, "s2": 2, "s3": 3}
DEV_BASE, HOLD_BASE, TRAIN_BASE = 9601000, 9602000, 9603000
PANEL_N = 300


# ------------------------------------------------------------ tokens <-> values
def date_tokens(d):
    return [YEAR0 + d.year - 2025, MON0 + d.month - 1, DIG + d.day // 10, DIG + d.day % 10]


def date_of(tok4):
    y, m, a, b = tok4
    return dt.date(2025 + y - YEAR0, m - MON0 + 1, 10 * (a - DIG) + (b - DIG))


def num_tokens(n, width):
    s = str(n).rjust(width, "0")
    return [DIG + int(c) for c in s]


def num_of(toks):
    return int("".join(str(t - DIG) for t in toks))


def signed_tokens(days):          # days from event 1 to event 2
    if days == 0:
        return [SAME] + num_tokens(0, 3)
    return [AFTER if days > 0 else BEFORE] + num_tokens(abs(days), 3)


# ------------------------------------------------------------ item
class Item:
    __slots__ = ("split", "tokens", "slot", "target", "meta")

    def __init__(self, split, tokens, slot, target, meta):
        self.split, self.tokens, self.slot, self.target, self.meta = split, tokens, slot, target, meta

    def to_json(self):
        return {"split": self.split, "tokens": self.tokens, "slot": self.slot, "target": self.target, "meta": self.meta}

    @staticmethod
    def from_json(d):
        return Item(d["split"], d["tokens"], d["slot"], d["target"], d["meta"])


# ------------------------------------------------------------ solving from tokens (the checker's only source of truth)
def parse_tokens(tokens):
    facts, quests = [], []
    for r, row in enumerate(tokens):
        if row[0] == FACT:
            facts.append({"row": r, "p": row[1], "a": row[2], "d": date_of(row[3:7])})
        elif row[0] in T_OP:
            quests.append({"row": r, "op": T_OP[row[0]], "args": row[1:7], "j": row[11] - QIDX0 + 1})
    return facts, quests


def solve_question(q, facts):
    """-> (kind, value): kind 'slots' (value = 4 tokens for cols 7..10) or 'flags' (value = set of fact rows)."""
    op, a = q["op"], q["args"]
    ev = {(f["p"], f["a"]): f for f in facts}
    if op == "WHEN":
        return "slots", date_tokens(ev[(a[0], a[1])]["d"])
    if op == "DIFF":
        return "slots", signed_tokens((ev[(a[2], a[3])]["d"] - ev[(a[0], a[1])]["d"]).days)
    if op == "PLUS":
        return "slots", date_tokens(ev[(a[0], a[1])]["d"] + dt.timedelta(days=num_of(a[2:5])))
    if op == "DIFFT":
        return "slots", signed_tokens((date_of(a[2:6]) - ev[(a[0], a[1])]["d"]).days)
    if op == "FIRST":
        f1, f2 = ev[(a[0], a[1])], ev[(a[2], a[3])]
        return "flags", {(f1 if f1["d"] < f2["d"] else f2)["row"]}
    if op == "JOIN":
        both = {f["p"] for f in facts if f["a"] == a[0]} & {f["p"] for f in facts if f["a"] == a[1]}
        return "flags", {f["row"] for f in facts if f["a"] == a[0] and f["p"] in both}
    if op == "SETM":
        return "flags", {f["row"] for f in facts if f["d"].month == a[0] - MON0 + 1 and f["d"].year == 2025 + a[1] - YEAR0}
    if op == "COUNT":
        return "slots", [BLANK, BLANK] + num_tokens(sum(f["p"] == a[0] for f in facts), 2)
    if op == "COUNTM":
        return "slots", [BLANK, BLANK] + num_tokens(
            sum(f["d"].month == a[0] - MON0 + 1 and f["d"].year == 2025 + a[1] - YEAR0 for f in facts), 2)
    raise ValueError(op)


def derive_target(tokens):
    """Rebuild the full target grid (and slot grid) from the question tokens alone."""
    facts, quests = parse_tokens(tokens)
    tgt = [[0] * W for _ in tokens]
    slot = [[0] * W for _ in tokens]
    for q in quests:
        kind, val = solve_question(q, facts)
        if kind == "slots":
            n0 = 2 if q["op"] in ("COUNT", "COUNTM") else 0
            for c in range(7 + n0, 11):
                tgt[q["row"]][c] = val[c - 7]
                slot[q["row"]][c] = 1
        else:
            col = 7 + q["j"] - 1
            for f in facts:
                tgt[f["row"]][col] = FLAG1 if f["row"] in val else FLAG0
                slot[f["row"]][col] = 1
    return tgt, slot


def check(item, pred):
    """pred: full grid of predicted tokens. True iff every slot cell is right (every part of every question)."""
    tgt, slot = derive_target(item.tokens)
    return all(pred[r][c] == tgt[r][c] for r in range(len(tgt)) for c in range(W) if slot[r][c])


def part_results(item, pred):
    """[(op, correct)] one per question row, for reporting."""
    tgt, slot = derive_target(item.tokens)
    facts, quests = parse_tokens(item.tokens)
    out = []
    for q in quests:
        cells = [(q["row"], c) for c in range(7, 11) if slot[q["row"]][c]]
        cells += [(f["row"], 7 + q["j"] - 1) for f in facts if slot[f["row"]][7 + q["j"] - 1]] if q["op"] in FLAG_OPS else []
        out.append((q["op"], all(pred[r][c] == tgt[r][c] for r, c in cells)))
    return out


# ------------------------------------------------------------ making items
def canon_key(tokens):
    """Item key with person/activity labels renumbered by first appearance (so relabelled copies collide)."""
    pm, am, out = {}, {}, []
    for row in tokens:
        r = list(row)
        if PER0 <= r[1] < PER0 + NPER:
            r[1] = pm.setdefault(r[1], len(pm))
        if r[0] == FACT and ACT0 <= r[2] < ACT0 + NACT:
            r[2] = am.setdefault(r[2], len(am))
        elif r[0] in (OP_T["DIFF"], OP_T["FIRST"]) and ACT0 <= r[2] < ACT0 + NACT:
            r[2] = am.setdefault(r[2], len(am))
            r[3] = pm.setdefault(r[3], len(pm))
            r[4] = am.setdefault(r[4], len(am))
        out.append(tuple(r))
    return hashlib.sha256(repr(out).encode()).hexdigest()[:24]


def make_store(rng, nf):
    """nf facts, unique (person, activity), distinct dates.  A few people with several activities so joins and counts are real."""
    while True:
        npr = rng.randint(max(3, nf // 4), min(NPER, max(4, nf // 2 + 1)))
        nac = rng.randint(max(3, nf // 4), min(NACT, max(4, nf // 2 + 2)))
        if npr * nac >= nf + 3:
            break
    people = rng.sample(range(NPER), npr)
    acts = rng.sample(range(NACT), nac)
    pairs = set()
    while len(pairs) < nf:
        pairs.add((rng.choice(people), rng.choice(acts)))
    days = rng.sample(range(N_STORE_DAYS), nf)
    rows = [(p + PER0, a + ACT0, D0 + dt.timedelta(days=d)) for (p, a), d in zip(sorted(pairs), days)]
    rng.shuffle(rows)
    return rows


def _fact_row(p, a, d):
    return [FACT, p, a] + date_tokens(d) + [BLANK] * 5


def gen_question(rng, op, rows):
    """-> arg tokens (6) for op on this store, or None if the store cannot give a good question."""
    if op in ("WHEN", "DIFF", "FIRST", "PLUS", "DIFFT"):
        if op in ("DIFF", "FIRST"):
            (p1, a1, _), (p2, a2, _) = rng.sample(rows, 2)
            return [p1, a1, p2, a2, BLANK, BLANK]
        p, a, d = rng.choice(rows)
        if op == "WHEN":
            return [p, a] + [BLANK] * 4
        if op == "PLUS":
            room = (MAX_DATE - d).days
            n = rng.randint(1, min(400, room))
            return [p, a] + num_tokens(n, 3) + [BLANK]
        t = D0 + dt.timedelta(days=rng.randint(0, N_STORE_DAYS + 200))   # T may lie a little after the stored span
        t = min(t, MAX_DATE)
        return [p, a] + date_tokens(t)
    if op == "JOIN":
        by_p = {}
        for p, a, _ in rows:
            by_p.setdefault(p, set()).add(a)
        cands = []
        acts = sorted({a for _, a, _ in rows})
        for a in acts:
            for b in acts:
                if a != b:
                    n = sum(a in s and b in s for s in by_p.values())
                    if 1 <= n <= 3:
                        cands.append((a, b))
        if not cands:
            return None
        a, b = rng.choice(cands)
        return [a, b] + [BLANK] * 4
    if op in ("SETM", "COUNTM"):
        months = {}
        for _, _, d in rows:
            months.setdefault((d.year, d.month), 0)
            months[(d.year, d.month)] += 1
        ok = [k for k, n in months.items() if (1 <= n <= 4 if op == "SETM" else 1 <= n <= 9)]
        if not ok:
            return None
        y, m = rng.choice(sorted(ok))
        return [MON0 + m - 1, YEAR0 + y - 2025] + [BLANK] * 4
    if op == "COUNT":
        cnt = {}
        for p, _, _ in rows:
            cnt[p] = cnt.get(p, 0) + 1
        p = rng.choice(sorted(cnt))
        return [p] + [BLANK] * 5
    raise ValueError(op)


def build_item(split, rng, nf, ops_list):
    """ops_list: the ops of question 1..k (k <= 3).  Returns an Item, or None if some op had no good question."""
    rows = make_store(rng, nf)
    tokens = [_fact_row(p, a, d) for p, a, d in rows]
    for j, op in enumerate(ops_list, start=1):
        args = gen_question(rng, op, rows)
        if args is None:
            return None
        tokens.append([OP_T[op]] + args + [BLANK] * 4 + [QIDX0 + j - 1])
    facts, quests = parse_tokens(tokens)
    for q in quests:                      # flag slots exist only for set questions, input token names the question
        if q["op"] in FLAG_OPS:
            for f in facts:
                tokens[f["row"]][7 + q["j"] - 1] = FSLOT0 + q["j"] - 1
        else:
            n0 = 2 if q["op"] in ("COUNT", "COUNTM") else 0
            for c in range(7 + n0, 11):
                tokens[q["row"]][c] = MASK
    target, slot = derive_target(tokens)
    return Item(split, tokens, slot, target, {"ops": ops_list, "nf": nf, "store": [[p, a, d.isoformat()] for p, a, d in rows]})


def sample_ops(split, rng):
    if split == "s0":
        return ["WHEN"]
    if split == "s1":
        return [rng.choice(DATE_OPS)]
    if split == "s2":
        if rng.random() < 0.5:
            return [rng.choice(MULTI_OPS)]
        return [rng.choice(OPS) for _ in range(rng.choice((2, 3)))]
    if split == "s3":
        if rng.random() < 0.5:
            return [rng.choice(OPS[1:])]
        return [rng.choice(OPS) for _ in range(rng.choice((2, 3)))]
    if split == "train":                         # practice: recall control, dates, multi-fact, compound
        u = rng.random()
        if u < 0.15:
            return ["WHEN"]
        if u < 0.45:
            return [rng.choice(DATE_OPS)]
        if u < 0.65:
            return [rng.choice(MULTI_OPS)]
        return [rng.choice(OPS) for _ in range(rng.choice((2, 3)))]
    raise ValueError(split)


def make_item(split, rng):
    lo, hi = SPLITS[split] if split in SPLITS else (6, 12)
    while True:
        it = build_item(split, rng, rng.randint(lo, hi), sample_ops(split, rng))
        if it is not None:
            return it


def make_panel(split, base, n=PANEL_N):
    rng = random.Random(base + SPLIT_SEED[split])
    items, seen = [], set()
    while len(items) < n:
        it = make_item(split, rng)
        k = canon_key(it.tokens)
        if k not in seen:
            seen.add(k)
            items.append(it)
    return items


def panel_keys():
    keys = set()
    for base in (DEV_BASE, HOLD_BASE):
        for s in SPLITS:
            keys |= {canon_key(it.tokens) for it in make_panel(s, base)}
    return keys


class Stream:
    """Endless code-made practice.  Items whose canonical key is in any dev or holdout panel are dropped."""

    def __init__(self, seed):
        self.rng = random.Random(TRAIN_BASE + seed)
        self.block = panel_keys()
        self.dropped = 0

    def batch(self, n):
        out = []
        while len(out) < n:
            it = make_item("train", self.rng)
            if canon_key(it.tokens) in self.block:
                self.dropped += 1
                continue
            out.append(it)
        return out


# ------------------------------------------------------------ wrong-by-design baselines (code only, for the shortcut guard)
def baseline_predict(item, kind):
    facts, quests = parse_tokens(item.tokens)
    pred = [list(r) for r in item.tokens]
    _, slot = derive_target(item.tokens)
    for r in range(len(pred)):
        for c in range(W):
            if slot[r][c]:
                pred[r][c] = BLANK
    latest = max(f["d"] for f in facts)
    for q in quests:
        a = q["args"]
        if kind == "first_row":            # date = first fact's date; numbers 000 / 01; no flags
            if q["op"] in ("WHEN", "PLUS"):
                pred[q["row"]][7:11] = date_tokens(facts[0]["d"])
            elif q["op"] in ("DIFF", "DIFFT"):
                pred[q["row"]][7:11] = [AFTER] + num_tokens(0, 3)
            elif q["op"] in ("COUNT", "COUNTM"):
                pred[q["row"]][9:11] = num_tokens(1, 2)
        elif kind == "latest_date":        # date = latest date in the store; numbers 365 / 02
            if q["op"] in ("WHEN", "PLUS"):
                pred[q["row"]][7:11] = date_tokens(latest)
            elif q["op"] in ("DIFF", "DIFFT"):
                pred[q["row"]][7:11] = [AFTER] + num_tokens(365, 3)
            elif q["op"] in ("COUNT", "COUNTM"):
                pred[q["row"]][9:11] = num_tokens(2, 2)
        elif kind == "token_match":        # date = the date of the first row that shares any argument token; flag those rows
            toks = {t for t in a if t >= PER0 and t < QIDX0}
            hit = [f for f in facts if f["p"] in toks or f["a"] in toks]
            if q["op"] in FLAG_OPS:
                col = 7 + q["j"] - 1
                for f in facts:
                    pred[f["row"]][col] = FLAG1 if f in hit else FLAG0
            elif q["op"] in ("WHEN", "PLUS") and hit:
                pred[q["row"]][7:11] = date_tokens(hit[0]["d"])
            elif q["op"] in ("COUNT", "COUNTM"):
                pred[q["row"]][9:11] = num_tokens(min(len(hit), 99), 2)
    for it_r in range(len(pred)):          # inputs are copied, only slot cells count
        pass
    return pred


BASELINES = ["first_row", "latest_date", "token_match"]


# ------------------------------------------------------------ text rendering (test scaffolding for the plain-model rivals only)
NAMES = ("Aldous Pell,Brisa Quon,Corvin Hale,Dessa Marlow,Edric Voss,Fennel Ashby,Gwyneth Roke,Halvard Tint,Ilsabet Crowe,Joren Vane,"
         "Kestrel Moss,Lorcan Dree,Mirabel Thane,Nerys Fallow,Orsin Bledsoe,Pell Ambrose,Quill Harrow,Rowena Sedge,Sabin Ferrow,Tamsin Oake,"
         "Ulric Blythe,Verity Stone,Wystan Lake,Xanthe Grove,Yorick Dunmore,Zelda Fitch,Ambrin Cole,Bexley Rowan,Calder Nye,Dorrit Sable,"
         "Elowen Marsh,Faolan Reed,Garrick Swann,Hestia Vale,Ivor Kettle,Jessamy Brook,Kellan Frost,Lyra Wexford,Merrick Toll,Nolwenn Ash").split(",")
ACTS = ("repaired the clock tower;planted an orchard;won the chess cup;sailed to the north cape;opened a bakery;"
        "climbed the red ridge;wrote a play;adopted a fox cub;built a greenhouse;painted the harbour gate;"
        "hosted the lantern fair;crossed the salt marsh;fixed the old organ;taught a pottery class;found a silver key;"
        "cleaned the well;rode the night train;carved a wooden owl;brewed the winter ale;mapped the caves;"
        "trained a falcon;sold the blue barn;joined the choir;lit the beacon;bound a book of songs;"
        "dug a mill pond;flew a kite race;made a quilt;guided the river tour;stitched the town flag").split(";")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
assert len(NAMES) == NPER and len(ACTS) == NACT


def fmt_date(d):
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def render(item):
    """Plain-English chat lines, question texts and canonical answers for the same item (code-templated, test-only)."""
    facts, quests = parse_tokens(item.tokens)
    nm = lambda p: NAMES[p - PER0]
    ac = lambda a: ACTS[a - ACT0]
    fname = {f["row"]: f for f in facts}
    chat = [f"{nm(f['p'])} {ac(f['a'])} on {fmt_date(f['d'])}." for f in facts]
    qs, ans = [], []
    for q in quests:
        a, op = q["args"], q["op"]
        kind, val = solve_question(q, facts)
        if op == "WHEN":
            qs.append(f"When did {nm(a[0])} {ac(a[1])}?"); ans.append(fmt_date(date_tokens_to_date(val)))
        elif op == "DIFF":
            qs.append(f"How many days after {nm(a[0])} {ac(a[1])} did {nm(a[2])} {ac(a[3])}? (Say before if it was earlier.)")
            ans.append(_signed_text(val))
        elif op == "PLUS":
            qs.append(f"What is the date {num_of(a[2:5])} days after {nm(a[0])} {ac(a[1])}?"); ans.append(fmt_date(date_tokens_to_date(val)))
        elif op == "DIFFT":
            qs.append(f"How many days after {nm(a[0])} {ac(a[1])} is {fmt_date(date_of(a[2:6]))}? (Say before if it is earlier.)")
            ans.append(_signed_text(val))
        elif op == "FIRST":
            qs.append(f"Who came first: {nm(a[0])} who {ac(a[1])}, or {nm(a[2])} who {ac(a[3])}?")
            ans.append(nm(fname[next(iter(val))]["p"]))
        elif op == "JOIN":
            qs.append(f"Which people both {ac(a[0])} and {ac(a[1])}?")
            ans.append(", ".join(sorted(nm(fname[r]["p"]) for r in val)))
        elif op == "SETM":
            qs.append(f"Which events happened in {MONTHS[a[0] - MON0]} {2025 + a[1] - YEAR0}? Name the person for each.")
            ans.append(", ".join(sorted(nm(fname[r]["p"]) for r in val)))
        elif op == "COUNT":
            qs.append(f"How many things did {nm(a[0])} do?"); ans.append(str(num_of(val[2:])))
        elif op == "COUNTM":
            qs.append(f"How many events happened in {MONTHS[a[0] - MON0]} {2025 + a[1] - YEAR0}?"); ans.append(str(num_of(val[2:])))
    return {"chat": chat, "questions": qs, "answers": ans}


def date_tokens_to_date(val):
    return date_of(val)


def _signed_text(val):
    n = num_of(val[1:])
    return "same day" if val[0] == SAME else f"{n} days {'after' if val[0] == AFTER else 'before'}"


# ------------------------------------------------------------ selftest and panel writer
def _sha(items):
    return hashlib.sha256(json.dumps([it.to_json() for it in items], sort_keys=True).encode()).hexdigest()


def selftest():
    # 1. generator/checker agreement, and any one-cell change to a slot is rejected
    rng = random.Random(1)
    n = 0
    for split in ("s0", "s1", "s2", "s3", "train"):
        for _ in range(300):
            it = make_item(split, rng)
            tgt, slot = derive_target(it.tokens)
            assert tgt == it.target and slot == it.slot, "stored target differs from re-derived target"
            pred = [[tgt[r][c] if slot[r][c] else it.tokens[r][c] for c in range(W)] for r in range(len(tgt))]
            assert check(it, pred) and all(ok for _, ok in part_results(it, pred))
            cells = [(r, c) for r in range(len(tgt)) for c in range(W) if slot[r][c]]
            r, c = rng.choice(cells)
            bad = [list(x) for x in pred]
            bad[r][c] = (bad[r][c] + 1) % VOCAB if bad[r][c] != FLAG1 else FLAG0
            assert not check(it, bad)
            n += 1
    # 2. arithmetic against python's datetime, from the tokens (independent recomputation)
    for split in ("s1", "s3"):
        for it in make_panel(split, DEV_BASE, 60):
            facts, quests = parse_tokens(it.tokens)
            ev = {(f["p"], f["a"]): f["d"] for f in facts}
            for q in quests:
                a = q["args"]
                if q["op"] == "DIFF":
                    _, v = solve_question(q, facts)
                    days = num_of(v[1:]) * (1 if v[0] == AFTER else -1)
                    assert dt.date.fromisoformat(str(ev[(a[2], a[3])])).toordinal() - ev[(a[0], a[1])].toordinal() == days
                if q["op"] == "PLUS":
                    _, v = solve_question(q, facts)
                    assert date_of(v).toordinal() - ev[(a[0], a[1])].toordinal() == num_of(a[2:5])
                    assert date_of(v) <= MAX_DATE
    # 3. facts: distinct dates, unique pairs, 1..3 question rows, W columns everywhere
    for split in SPLITS:
        for it in make_panel(split, HOLD_BASE, 100):
            facts, quests = parse_tokens(it.tokens)
            assert len({f["d"] for f in facts}) == len(facts) and len({(f["p"], f["a"]) for f in facts}) == len(facts)
            assert 1 <= len(quests) <= 3 and all(len(r) == W for r in it.tokens)
            lo, hi = SPLITS[split]
            assert lo <= len(facts) <= hi
            assert all(0 <= t < VOCAB for r in it.tokens for t in r)
    # 4. panels: no key shared between dev and holdout, none repeated, 300 each
    dev = {s: make_panel(s, DEV_BASE) for s in SPLITS}
    hold = {s: make_panel(s, HOLD_BASE) for s in SPLITS}
    dk = {canon_key(it.tokens) for s in dev for it in dev[s]}
    hk = {canon_key(it.tokens) for s in hold for it in hold[s]}
    assert len(dk) == 4 * PANEL_N and len(hk) == 4 * PANEL_N and not (dk & hk)
    # 5. practice never contains a panel item (draw 3000 and count what the stream had to drop)
    st = Stream(0)
    got = st.batch(3000)
    assert not ({canon_key(it.tokens) for it in got} & (dk | hk))
    # 6. shortcut guard: each wrong-by-design predictor scores at most 45 of 300 on every dev and holdout split of s1, s2, s3
    worst = {}
    for tag, panels in (("dev", dev), ("hold", hold)):
        for s, items in panels.items():
            for b in BASELINES:
                score = sum(check(it, baseline_predict(it, b)) for it in items)
                worst[(tag, s, b)] = score
                assert s == "s0" or score <= 45, (tag, s, b, score)   # s0 is the easy recall control: reported, not guarded
    # 7. text rendering exists for every item and names are unique per store
    for s in SPLITS:
        for it in dev[s][:20]:
            r = render(it)
            assert len(r["chat"]) == it.meta["nf"] and len(r["questions"]) == len(r["answers"]) == len(it.meta["ops"])
    # 8. composition of the panels (op counts, for the results file)
    comp = {}
    for s, items in hold.items():
        for it in items:
            for op in it.meta["ops"]:
                comp.setdefault(s, {}).setdefault(op, 0)
                comp[s][op] += 1
    print("panel sha256 dev:", {s: _sha(dev[s])[:16] for s in dev})
    print("panel sha256 hold:", {s: _sha(hold[s])[:16] for s in hold})
    print("baseline max per split (x of 300):", {f"{t}-{s}": max(v for (tt, ss, b), v in worst.items() if tt == t and ss == s)
                                               for (t, s, _b) in worst})
    print("holdout question counts per split:", comp)
    print("practice items dropped for matching a panel key in 3000 draws:", st.dropped)
    print(f"selftest ok ({n} generator/checker items)")


def write_panels(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for tag, base in (("dev", DEV_BASE), ("hold", HOLD_BASE)):
        for s in SPLITS:
            items = make_panel(s, base)
            p = out / f"panel-{tag}-{s}.jsonl"
            with open(p, "w", encoding="utf-8") as f:
                for it in items:
                    d = it.to_json()
                    d["render"] = render(it)
                    f.write(json.dumps(d, sort_keys=True) + "\n")
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    (out / "PANELS.sha256.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        selftest()
    elif cmd == "panels":
        write_panels(sys.argv[sys.argv.index("--out") + 1])
