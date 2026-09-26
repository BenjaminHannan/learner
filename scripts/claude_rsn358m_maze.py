#!/usr/bin/env python3
"""rsn-358m draft (sleep research thread, 2026-09-26; NOT sealed, not run): maze puzzles as a NEW kind for the loop vs
plain nets, to test how fast each net picks up something it never practised (Ben 13:49-14:01 UTC: "smart overall").

Plan (to be registered after 358i): after the normal 358i practice (sums, grids, number puzzles), both nets get the
same short practice on small mazes only (5x5, 7x7), then are tested on bigger mazes (9x9 graded, 11x11 and 13x13
report). A net this small has no words, so it cannot do a kind it was never shown at all; the question is which net
learns the new kind faster and carries it to bigger mazes.

Mazes are "perfect" (every open cell reachable by exactly one path; carved by a randomised depth-first walk on a
(2k+1)x(2k+1) grid), so the path from start to goal is unique and the training answer is never ambiguous (the lesson
of the 358a grid bug). Page: walls, open cells, start, goal; the net marks every open cell 1 (on the path) or 0.
Checker: the marked cells plus start and goal must form one connected chain from start to goal through open cells,
with no extra marked cell (so only the true path passes).

  python -B scripts/claude_rsn358m_maze.py selftest
"""
from __future__ import annotations

import random
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402

WALL, START, GOAL = E.OPS["/"], E.OPS["+"], E.OPS["*"]      # reused tokens; meaning comes from the maze practice
ON, OFF = E.DIG + 1, E.DIG + 0
SIZES_PRACTICE, SIZES_TEST = [5, 7], [9, 11, 13]


def carve(rng, s):
    """perfect maze on an s x s grid (s odd): True = open."""
    g = [[False] * s for _ in range(s)]
    stack = [(1, 1)]
    g[1][1] = True
    while stack:
        r, c = stack[-1]
        nxt = [(r + dr, c + dc, dr // 2, dc // 2) for dr, dc in ((2, 0), (-2, 0), (0, 2), (0, -2))
               if 0 < r + dr < s - 1 and 0 < c + dc < s - 1 and not g[r + dr][c + dc]]
        if not nxt:
            stack.pop()
            continue
        nr, nc, hr, hc = rng.choice(nxt)
        g[r + hr][c + hc] = True
        g[nr][nc] = True
        stack.append((nr, nc))
    return g


def path_of(g, a, b):
    s = len(g)
    prev = {a: None}
    q = deque([a])
    while q:
        r, c = q.popleft()
        if (r, c) == b:
            break
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < s and 0 <= nc < s and g[nr][nc] and (nr, nc) not in prev:
                prev[(nr, nc)] = (r, c)
                q.append((nr, nc))
    out, x = [], b
    while x is not None:
        out.append(x)
        x = prev[x]
    return out[::-1]


def make_maze(rng, s):
    g = carve(rng, s)
    cells = [(r, c) for r in range(1, s, 2) for c in range(1, s, 2)]
    a, b = rng.sample(cells, 2)
    on = set(path_of(g, a, b))
    tokens, slot, target = [], [], []
    for r in range(s):
        tr, sr, yr = [], [], []
        for c in range(s):
            if (r, c) == a:
                tr.append(START); sr.append(0); yr.append(0)
            elif (r, c) == b:
                tr.append(GOAL); sr.append(0); yr.append(0)
            elif not g[r][c]:
                tr.append(WALL); sr.append(0); yr.append(0)
            else:
                tr.append(E.MASK); sr.append(1); yr.append(ON if (r, c) in on else OFF)
        tokens.append(tr); slot.append(sr); target.append(yr)
    return E.Item("mazes", s, tokens, slot, target, {"start": a, "goal": b, "path_len": len(on)})


def check_maze(item, pred):
    s = item.size
    a, b = tuple(item.meta["start"]), tuple(item.meta["goal"])
    marked = {a, b}
    for r in range(s):
        for c in range(s):
            if item.slot[r][c]:
                if pred[r][c] == ON:
                    marked.add((r, c))
                elif pred[r][c] != OFF:
                    return False
    # every marked cell open, and the marked set is exactly one chain from a to b
    deg = {x: sum((x[0] + dr, x[1] + dc) in marked for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))) for x in marked}
    if deg[a] != 1 or deg[b] != 1 or any(deg[x] != 2 for x in marked if x not in (a, b)):
        return False
    seen, q = {a}, deque([a])
    while q:
        r, c = q.popleft()
        for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if n in marked and n not in seen:
                seen.add(n); q.append(n)
    return seen == marked


def selftest():
    rng = random.Random(1)
    for s in SIZES_PRACTICE + SIZES_TEST:
        lens = []
        for _ in range(200):
            it = make_maze(rng, s)
            assert check_maze(it, it.target)
            bad = [row[:] for row in it.target]
            cells = [(r, c) for r in range(s) for c in range(s) if it.slot[r][c]]
            r, c = rng.choice(cells)
            bad[r][c] = ON if bad[r][c] == OFF else OFF       # flipping any one cell must fail
            assert not check_maze(it, bad)
            lens.append(it.meta["path_len"])
        print(f"{s}x{s}: 200 mazes ok; path length mean {sum(lens) / len(lens):.1f}, max {max(lens)}")
    print("selftest ok")


if __name__ == "__main__":
    selftest()
