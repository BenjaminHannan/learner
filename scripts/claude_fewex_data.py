#!/usr/bin/env python3
"""Deterministic, code-made few-example puzzles and sealed panel construction."""
from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E
import claude_rsn358m_maze as M

PANEL_SIZES = {7: (24, 48), 9: (300, 300), 11: (300, 300)}
PANEL_SEED = 9202700
SUPPORT_SEED = 9212700
STREAM_SEED = 9222700
SOURCE_SEED = 9232700


def latin_legend(rng, s):
    it = E.latin_item(rng, *E.make_latin_base(rng, s))
    legend = [E.SYM + n for n in it.meta["names"]]
    rng.shuffle(legend)
    return E.Item("grids", s, it.tokens + [[E.BLANK] * s, legend],
                  it.slot + [[0] * s, [0] * s], it.target + [[0] * s, [0] * s], it.meta)


def source_batch(rng, n=64):
    if rng.random() < .5:
        digits = rng.choice((1, 2, 3, 4))
        return [E.make_sum(rng, digits) for _ in range(n)]
    s = rng.choice((4, 5))
    return [latin_legend(rng, s) for _ in range(n)]


def old_panels(seed=SOURCE_SEED):
    rng = random.Random(seed)
    return {"sums4": [E.make_sum(rng, 4) for _ in range(200)],
            "grids5": [latin_legend(rng, 5) for _ in range(200)]}


def replay_old(seed=SOURCE_SEED + 1):
    rng = random.Random(seed)
    return {"sums4": [E.make_sum(rng, 4) for _ in range(128)],
            "grids5": [latin_legend(rng, 5) for _ in range(128)]}


def make_maze(rng, s):
    """Wilson uniform spanning tree on the odd-by-odd rooms; same tokens as 358m."""
    k = (s - 1) // 2
    cells = [(i, j) for i in range(k) for j in range(k)]
    g = [[False] * s for _ in range(s)]
    root = rng.choice(cells)
    tree = {root}
    g[2 * root[0] + 1][2 * root[1] + 1] = True
    order = cells[:]
    rng.shuffle(order)
    for start in order:
        nxt, u = {}, start
        while u not in tree:
            nb = [(u[0] + a, u[1] + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= u[0] + a < k and 0 <= u[1] + b < k]
            nxt[u] = rng.choice(nb)
            u = nxt[u]
        u = start
        while u not in tree:
            tree.add(u)
            v = nxt[u]
            g[2 * u[0] + 1][2 * u[1] + 1] = True
            g[u[0] + v[0] + 1][u[1] + v[1] + 1] = True
            u = v
    a, b = rng.sample([(2 * i + 1, 2 * j + 1) for i, j in cells], 2)
    on = set(M.path_of(g, a, b))
    tokens, slot, target = [], [], []
    for r in range(s):
        tr, sr, yr = [], [], []
        for c in range(s):
            if (r, c) == a:
                tr.append(M.START); sr.append(0); yr.append(0)
            elif (r, c) == b:
                tr.append(M.GOAL); sr.append(0); yr.append(0)
            elif not g[r][c]:
                tr.append(M.WALL); sr.append(0); yr.append(0)
            else:
                tr.append(E.MASK); sr.append(1); yr.append(M.ON if (r, c) in on else M.OFF)
        tokens.append(tr); slot.append(sr); target.append(yr)
    return E.Item("mazes", s, tokens, slot, target, {"start": a, "goal": b, "path_len": len(on)})


def layout_key(item):
    # Endpoints and answer are deliberately excluded: overlap means same layout.
    wall = bytes(int(t == M.WALL) for row in item.tokens for t in row)
    return hashlib.sha256(bytes([item.size]) + wall).hexdigest()


def panels():
    out, banned = {"dev": {}, "holdout": {}}, set()
    for s, (nd, nh) in PANEL_SIZES.items():
        rng = random.Random(PANEL_SEED + s)
        for split, n in (("dev", nd), ("holdout", nh)):
            items = []
            while len(items) < n:
                it = make_maze(rng, s)
                key = layout_key(it)
                if key in banned:
                    continue
                banned.add(key)
                items.append(it)
            out[split][s] = items
    return out, banned


def unique_maze(rng, s, forbidden, seen):
    while True:
        it = make_maze(rng, s)
        key = layout_key(it)
        if key not in forbidden and key not in seen:
            seen.add(key)
            return it


def supports(seed, banned):
    rng = random.Random(SUPPORT_SEED + seed)
    seen = set()
    return [unique_maze(rng, 9, banned, seen) for _ in range(64)], seen


def stream(seed, banned, support_keys):
    rng = random.Random(STREAM_SEED + seed)
    seen = set()
    forbidden = banned | support_keys
    for _ in range(65536):
        yield unique_maze(rng, 9, forbidden, seen)
