#!/usr/bin/env python3
"""Ten code-made practice kinds for the practice-breadth test (Director helper A, 2026-09-28).

Design: artifacts/claude-dir-a-breadth-20260928/DESIGN.md; marks: PASSMARKS.md (same folder).
Pure python (no torch, no numpy). Same token format as the ruler's nets (claude_rsn358a_envs vocabulary,
125 tokens): an H x W grid of token ids, a fill-slot grid (1 = the net writes here), a target grid.
The nets get no puzzle-kind input; the kind is only in the tokens.

The current practice is two kinds (sums and Latin squares, 50/50). The breadth mixture is TEN kinds, an equal
number of practice steps each (1,200 of 12,000): the same two, plus eight new ones. Every new kind is
content-addressed (a cell finds what it needs by matching names or values, never by counting columns), because
the ruler's nets have no absolute position:

  assoc     look up the value stored under a name                    (3 rows-per-pair table, 3 queries)
  compose   follow two lookup tables in a row: name -> name -> digit  (two tables, 3 queries)
  parity    xor of a row of bits
  member    is each query digit in a small set: yes / no
  multi     how many times does each digit occur in its row
  moddiff   column-by-column difference of two digit rows, mod 10 (no carries)
  odd       which name differs from all the others in its row (three rows)
  bitop     and / or / xor of two bit rows, the operator is a symbol row

Kinds NOT allowed in the practice set (they are, or would give away, the held-out exam): shortest distance or
reachability on a graph or a grid, any path or maze-like propagation, and counting how many digits are smaller.
`multi` counts EQUAL digits, `compose` follows two fixed lookups: both are disclosed in DESIGN.md as the nearest
neighbours of the exam kinds (rank, graph-hop) and are the reason for the leave-out check described there.

Token rule (checked by the selftest): the practice kinds never use a token that a held-out kind uses as its
own vocabulary (graph: VAL+0..9 as distances, VAL+50..99; maze: START, GOAL, WALL, and the 'ON'/'OFF' digits are
shared with sums and stay allowed). New kinds draw markers and names only from VAL+10..VAL+49, DIG and SYM.

  python3 -B scripts/claude_dir_a_kinds.py selftest
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # vocabulary and Item class only
import claude_fewex_data as D    # sums / latin_legend generators of the current practice

VAL, DIG, SYM, MASK, BLANK = E.VAL, E.DIG, E.SYM, E.MASK, E.BLANK

# ---- tokens (all inside VAL+10 .. VAL+49, DIG, SYM) ----
MK, M2, ASK, YES, NO = VAL + 10, VAL + 11, VAL + 12, VAL + 13, VAL + 14
NAME0, NNAME = VAL + 20, 30                      # anonymous names VAL+20 .. VAL+49
OP_AND, OP_OR, OP_XOR = SYM + 0, SYM + 1, SYM + 2

NEW_KINDS = ("assoc", "compose", "parity", "member", "multi", "moddiff", "odd", "bitop")
OLD_KINDS = ("sums", "grids")
KINDS = OLD_KINDS + NEW_KINDS                    # the ten practice kinds
LEVELS = {"sums": (1, 2, 3, 4), "grids": (4, 5), "assoc": (4, 6), "compose": (4, 5), "parity": (6, 8),
          "member": (4, 6), "multi": (7, 9), "moddiff": (5, 7), "odd": (6, 8), "bitop": (8, 10)}
STEPS, BATCH = 12000, 64                         # the current practice: 12,000 batches of 64
STEPS_PER_KIND = STEPS // len(KINDS)             # 1,200

# tokens a held-out kind owns; no NEW practice kind may emit or ask for them
GRAPH_TOKENS = set(range(VAL + 0, VAL + 10)) | set(range(VAL + 50, VAL + 100))
HELD_OUT_TOKENS = GRAPH_TOKENS | {E.OPS["+"], E.OPS["*"], E.OPS["/"]}   # graph vocabulary, maze START/GOAL/WALL

STREAM_SEED = 9502800
GUARD_SEED = 9512800        # fresh 200-item guard panel per kind (mastery report)
DEV_SEED = 9522800          # 200-item source-dev panel per kind (fixed depth / plain lr choice)
SCHEDULE_SEED = 9532800


def _item(env, size, tokens, slot, target, meta=None):
    return E.Item(env, size, tokens, slot, target, meta or {})


def _bits(rng, w):
    return [rng.randrange(2) for _ in range(w)]


# =============================== generators ===============================
def make_assoc(rng, n):
    names = rng.sample(range(NNAME), n)
    vals = [rng.randrange(10) for _ in range(n)]
    order = list(range(n))
    rng.shuffle(order)
    tokens, slot, target = [], [], []
    for i in order:
        tokens.append([MK, NAME0 + names[i], DIG + vals[i]])
        slot.append([0, 0, 0]); target.append([0, 0, 0])
    for i in rng.sample(range(n), 3):
        tokens.append([ASK, NAME0 + names[i], MASK])
        slot.append([0, 0, 1]); target.append([0, 0, DIG + vals[i]])
    return _item("assoc", n, tokens, slot, target)


def make_compose(rng, n):
    both = rng.sample(range(NNAME), 2 * n)
    a_names, b_names = both[:n], both[n:]
    f = [rng.choice(b_names) for _ in a_names]
    g = [rng.randrange(10) for _ in b_names]
    rows = [[MK, NAME0 + a_names[i], NAME0 + f[i]] for i in range(n)] + \
           [[M2, NAME0 + b_names[i], DIG + g[i]] for i in range(n)]
    rng.shuffle(rows)
    tokens = [r[:] for r in rows]
    slot = [[0, 0, 0] for _ in rows]
    target = [[0, 0, 0] for _ in rows]
    for i in rng.sample(range(n), 3):
        tokens.append([ASK, NAME0 + a_names[i], MASK])
        slot.append([0, 0, 1])
        target.append([0, 0, DIG + g[b_names.index(f[i])]])
    return _item("compose", n, tokens, slot, target)


def make_parity(rng, w):
    tokens, slot, target = [], [], []
    for _ in range(3):
        b = _bits(rng, w)
        tokens.append([DIG + x for x in b] + [MASK])
        slot.append([0] * w + [1])
        target.append([0] * w + [DIG + sum(b) % 2])
    return _item("parity", w, tokens, slot, target)


def make_member(rng, m):
    s = rng.sample(range(10), m)
    out = [x for x in range(10) if x not in s]
    qs = rng.sample(s, 3) + rng.sample(out, 3)        # exactly three members and three non-members
    rng.shuffle(qs)
    row0 = [DIG + x for x in s] + [BLANK] * (6 - m)
    rng.shuffle(row0)
    tokens = [row0, [DIG + q for q in qs], [MASK] * 6]
    slot = [[0] * 6, [0] * 6, [1] * 6]
    target = [[0] * 6, [0] * 6, [YES if q in s else NO for q in qs]]
    return _item("member", m, tokens, slot, target)


def make_multi(rng, n):
    while True:
        v = [rng.randrange(6) for _ in range(n)]
        if max(v.count(x) for x in set(v)) >= 2:
            break
    return _item("multi", n, [[DIG + x for x in v], [MASK] * n], [[0] * n, [1] * n],
                 [[0] * n, [DIG + v.count(x) for x in v]])


def make_moddiff(rng, n):
    a, b = [rng.randrange(10) for _ in range(n)], [rng.randrange(10) for _ in range(n)]
    return _item("moddiff", n, [[DIG + x for x in a], [DIG + x for x in b], [MASK] * n],
                 [[0] * n, [0] * n, [1] * n], [[0] * n, [0] * n, [DIG + (x - y) % 10 for x, y in zip(a, b)]])


def make_odd(rng, n):
    tokens, slot, target = [], [], []
    for _ in range(3):
        common, other = rng.sample(range(NNAME), 2)
        row = [common] * n
        row[rng.randrange(n)] = other
        tokens.append([NAME0 + x for x in row] + [MASK])
        slot.append([0] * n + [1])
        target.append([0] * n + [NAME0 + other])
    return _item("odd", n, tokens, slot, target)


def _bitfun(op, x, y):
    return {OP_AND: x & y, OP_OR: x | y, OP_XOR: x ^ y}[op]


def make_bitop(rng, w):
    op = rng.choice((OP_AND, OP_OR, OP_XOR))
    a, b = _bits(rng, w), _bits(rng, w)
    return _item("bitop", w, [[DIG + x for x in a], [DIG + x for x in b], [op] * w, [MASK] * w],
                 [[0] * w] * 3 + [[1] * w], [[0] * w] * 3 + [[DIG + _bitfun(op, x, y) for x, y in zip(a, b)]])


MAKERS = {"assoc": make_assoc, "compose": make_compose, "parity": make_parity, "member": make_member,
          "multi": make_multi, "moddiff": make_moddiff, "odd": make_odd, "bitop": make_bitop}


def make_item(kind, rng, level):
    if kind == "sums":
        return E.make_sum(rng, level)
    if kind == "grids":
        return D.latin_legend(rng, level)
    return MAKERS[kind](rng, level)


# =============================== checkers: re-derive the answer from the TOKENS only ===============================
def expected_new(env, tokens):
    """dict {(row, col): token} of what the fill cells must contain, computed from the tokens alone."""
    out = {}
    if env == "assoc":
        table = {r[1]: r[2] for r in tokens if r[0] == MK}
        for i, r in enumerate(tokens):
            if r[0] == ASK:
                out[(i, 2)] = table[r[1]]
    elif env == "compose":
        f = {r[1]: r[2] for r in tokens if r[0] == MK}
        g = {r[1]: r[2] for r in tokens if r[0] == M2}
        for i, r in enumerate(tokens):
            if r[0] == ASK:
                out[(i, 2)] = g[f[r[1]]]
    elif env == "parity":
        for i, r in enumerate(tokens):
            out[(i, len(r) - 1)] = DIG + sum(t - DIG for t in r[:-1]) % 2
    elif env == "member":
        s = {t for t in tokens[0] if t != BLANK}
        for j, q in enumerate(tokens[1]):
            out[(2, j)] = YES if q in s else NO
    elif env == "multi":
        for j, t in enumerate(tokens[0]):
            out[(1, j)] = DIG + tokens[0].count(t)
    elif env == "moddiff":
        for j in range(len(tokens[0])):
            out[(2, j)] = DIG + (tokens[0][j] - tokens[1][j]) % 10
    elif env == "odd":
        for i, row in enumerate(tokens):
            body = row[:-1]
            out[(i, len(row) - 1)] = next(t for t in body if body.count(t) == 1)
    elif env == "bitop":
        a, b, opr = tokens[0], tokens[1], tokens[2]
        for j in range(len(a)):
            out[(3, j)] = DIG + _bitfun(opr[j], a[j] - DIG, b[j] - DIG)
    else:
        raise ValueError(env)
    return out


def check(item, pred):
    """True when every fill cell equals the value re-derived from the tokens. sums / grids use the ruler's checker."""
    if item.env == "sums":
        return E.check_sum(item, pred[2])
    if item.env == "grids":
        return E.check(item, pred)
    exp = expected_new(item.env, item.tokens)
    fill = {(r, c) for r, row in enumerate(item.slot) for c, v in enumerate(row) if v}
    return fill == set(exp) and all(pred[r][c] == t for (r, c), t in exp.items())


def item_key(item):
    return hashlib.sha256(json.dumps(item.tokens).encode()).hexdigest()


# =============================== the mixture ===============================
def schedule(seed):
    """12,000 kind labels, exactly 1,200 of each kind, shuffled. Same for the loop and the plain arm of a seed."""
    order = [k for k in KINDS for _ in range(STEPS_PER_KIND)]
    random.Random(SCHEDULE_SEED + seed).shuffle(order)
    return order


def practice_batch(rng, kind, n=BATCH):
    """One training batch: n items of ONE kind and ONE level (so the batch stacks), as the current practice does."""
    level = rng.choice(LEVELS[kind])
    return [make_item(kind, rng, level) for _ in range(n)]


def panel(kind, seed, n=200):
    """n items of a kind, levels mixed evenly, but every item has the same shape only within a level; returns
    {level: items}. Guard and dev panels are separate streams from the training stream."""
    rng = random.Random(seed + 101 * KINDS.index(kind))
    lv = LEVELS[kind]
    per = n // len(lv)
    return {level: [make_item(kind, rng, level) for _ in range(per)] for level in lv}


def panel_flat(kind, seed, n=200):
    return [x for items in panel(kind, seed, n).values() for x in items]


# =============================== self-test ===============================
def _gold(item):
    return [[item.target[r][c] if item.slot[r][c] else item.tokens[r][c] for c in range(len(item.tokens[0]))]
            for r in range(len(item.tokens))]


def _constant_baselines(item):
    """Wrong-by-design predictors: every fill cell set to one token (the most likely one for the kind)."""
    out = {}
    for name, tok in (("all_digit0", DIG), ("all_digit1", DIG + 1), ("all_yes", YES), ("all_no", NO)):
        g = [row[:] for row in item.tokens]
        for r, row in enumerate(item.slot):
            for c, v in enumerate(row):
                if v:
                    g[r][c] = tok
        out[name] = g
    if item.env == "assoc" or item.env == "compose":     # copy the name asked about
        g = [row[:] for row in item.tokens]
        for r, row in enumerate(item.slot):
            for c, v in enumerate(row):
                if v:
                    g[r][c] = item.tokens[r][1]
        out["copy_name"] = g
    return out


def selftest():
    rng = random.Random(1)
    report = {}
    for kind in KINDS:
        info = {"levels": {}}
        for level in LEVELS[kind]:
            items = [make_item(kind, rng, level) for _ in range(300)]
            shapes = {(len(x.tokens), len(x.tokens[0])) for x in items}
            assert len(shapes) == 1, (kind, level, shapes)
            for it in items:
                assert max(max(row) for row in it.tokens) < E.VOCAB and max(max(row) for row in it.target) < E.VOCAB
                gold = _gold(it)
                assert check(it, gold), (kind, level)
                for _ in range(3 if kind in NEW_KINDS else 0):   # a one-cell change is always rejected (sums/grids: sealed ruler checkers)
                    g = _gold(it)
                    cells = [(r, c) for r, row in enumerate(it.slot) for c, v in enumerate(row) if v]
                    r, c = rng.choice(cells)
                    g[r][c] = rng.choice([t for t in range(DIG, DIG + 10) if t != g[r][c]])
                    assert not check(it, g), (kind, level)
                if kind in NEW_KINDS:          # answer re-derived from the tokens equals the stored target
                    exp = expected_new(kind, it.tokens)
                    assert {k: v for k, v in exp.items()} == {(r, c): it.target[r][c]
                                                              for r, row in enumerate(it.slot)
                                                              for c, v in enumerate(row) if v}
                    used = {t for row in it.tokens for t in row} | {t for row in it.target for t in row}
                    assert not used & HELD_OUT_TOKENS, (kind, used & HELD_OUT_TOKENS)
            info["levels"][str(level)] = {"grid": list(shapes.pop()), "items_ok": len(items)}
        # cheap wrong-by-design predictors on a dev panel
        dev = panel_flat(kind, DEV_SEED)
        wins = {}
        for it in dev:
            for name, grid in _constant_baselines(it).items():
                wins[name] = wins.get(name, 0) + int(check(it, grid))
        info["dev_constant_baselines_right_of_200"] = wins
        assert all(v <= 30 for v in wins.values()), (kind, wins)   # each must stay at or under 15%
        # panels are separate streams: guard, dev and a training sample share no printed item (large spaces only)
        g_keys = {item_key(x) for x in panel_flat(kind, GUARD_SEED)}
        d_keys = {item_key(x) for x in dev}
        info["guard_dev_overlap"] = len(g_keys & d_keys)
        info["guard_unique_of_200"] = len(g_keys)
        report[kind] = info
    # schedule: exactly 1,200 steps of each kind, equal for the two arms, batches stack
    for seed in (0, 1):
        s = schedule(seed)
        assert len(s) == STEPS and all(s.count(k) == STEPS_PER_KIND for k in KINDS)
    r2 = random.Random(3)
    for kind in KINDS:
        b = practice_batch(r2, kind, 8)
        assert len({(len(x.tokens), len(x.tokens[0])) for x in b}) == 1
    report["schedule"] = {"steps": STEPS, "per_kind": STEPS_PER_KIND, "batch": BATCH,
                          "items_total": STEPS * BATCH,
                          "sha256_seed0": hashlib.sha256("|".join(schedule(0)).encode()).hexdigest(),
                          "sha256_seed1": hashlib.sha256("|".join(schedule(1)).encode()).hexdigest()}
    print(json.dumps(report, indent=2, sort_keys=True))
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
