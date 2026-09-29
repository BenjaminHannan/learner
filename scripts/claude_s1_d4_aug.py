"""S1 helper: the 8 rotations/reflections (D4) of a maze item. Pure python (no torch), so it can be tested anywhere.

A maze item's tokens, fill slots and answer grid are turned together; start and goal are re-read from the turned tokens.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_data as D  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358m_maze as M  # noqa: E402


def turn(grid, t):
    """t in 0..7: t % 4 clockwise quarter turns, then a left-right mirror if t >= 4."""
    g = [list(r) for r in grid]
    for _ in range(t % 4):
        g = [list(r) for r in zip(*g[::-1])]
    if t >= 4:
        g = [r[::-1] for r in g]
    return g


def unturn(grid, t):
    """Inverse of turn(., t)."""
    g = [list(r) for r in grid]
    if t >= 4:
        g = [r[::-1] for r in g]
    for _ in range(-(t % 4) % 4):
        g = [list(r) for r in zip(*g[::-1])]
    return g


def d4_item(item, t):
    tokens, slot, target = turn(item.tokens, t), turn(item.slot, t), turn(item.target, t)
    pos = {tok: (r, c) for r, row in enumerate(tokens) for c, tok in enumerate(row) if tok in (M.START, M.GOAL)}
    meta = dict(item.meta, start=pos[M.START], goal=pos[M.GOAL])
    return E.Item(item.env, item.size, tokens, slot, target, meta)


def allowed_views(item, banned):
    """Views whose wall layout is not (any turn of) a dev/holdout panel layout. t=0 is always allowed (pool is disjoint)."""
    return [t for t in range(8) if t == 0 or D.layout_key(d4_item(item, t)) not in banned]
