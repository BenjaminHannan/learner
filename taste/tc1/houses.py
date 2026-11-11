"""Hidden house generator (test scaffolding). Returns grids only to callers; params stay here."""
from dataclasses import dataclass
import numpy as np
from .copyguard import CopyGuard


@dataclass
class HP:
    bw: int
    bh: int
    A: int
    B: int
    C: int
    oh: int          # roof overhang per side (0 or 1)
    top: int
    left: int
    door_h: int
    win: tuple = None   # (colour, row, col_offset j>=1) for the novel sub-family


def n_roof_rows(bw, oh):
    return (bw + 2 * oh + 1) // 2


def door_geom(p):
    dw = 1 if p.bw % 2 == 1 else 2
    dc = p.left + (p.bw - dw) // 2
    bottom = p.top + p.bh - 1
    return dw, dc, bottom - p.door_h + 1, bottom


def draw_roof(g, p, below=False):
    W = p.bw + 2 * p.oh
    n = n_roof_rows(p.bw, p.oh)
    for j in range(n):
        row = (p.top + p.bh + j) if below else (p.top - 1 - j)
        if 0 <= row < 12:
            g[row, p.left - p.oh + j: p.left + p.bw + p.oh - j] = p.B


def draw_house(p):
    g = np.zeros((12, 12), dtype=np.int8)
    g[p.top:p.top + p.bh, p.left:p.left + p.bw] = p.A
    draw_roof(g, p)
    dw, dc, dtop, dbot = door_geom(p)
    g[dtop:dbot + 1, dc:dc + dw] = p.C
    if p.win is not None:
        col, row, j = p.win
        g[row, p.left + j] = col
        g[row, p.left + p.bw - 1 - j] = col
    return g


def sample_params(rng, novel=False):
    while True:
        bw = int(rng.integers(3, 10))
        bh = int(rng.integers(2, 6))
        if novel and (bw < 5 or bh < 3):
            continue
        oh = int(rng.integers(0, 2))
        cols = [int(c) for c in rng.permutation([1, 2, 3, 4])]
        A, B, C, Dc = cols
        nr = n_roof_rows(bw, oh)
        if novel:
            door_h = int(rng.integers(1, bh - 1))      # 1..bh-2 so a window row exists above
        else:
            door_h = int(rng.integers(1, bh))          # 1..bh-1
        top_lo, top_hi = nr, 12 - bh
        left_lo, left_hi = oh, 12 - bw - oh
        if top_lo > top_hi or left_lo > left_hi:
            continue
        top = int(rng.integers(top_lo, top_hi + 1))
        left = int(rng.integers(left_lo, left_hi + 1))
        p = HP(bw, bh, A, B, C, oh, top, left, door_h)
        if novel:
            _, _, dtop, _ = door_geom(p)
            row = int(rng.integers(top + 1, dtop))     # strictly inside, above door top
            j = int(rng.integers(1, (bw - 2) // 2 + 1))
            p.win = (Dc, row, j)
        return p


def make_broken(params, rng):
    """Exam scaffolding: three kinds of broken versions of the given houses."""
    roof_below, door_up, shuffled = [], [], []
    for p in params:
        # roof moved below the body (same orientation start, narrowing downward); whole picture
        # shifted up so everything still fits (roof rows + body rows always fit in the canvas)
        nr = n_roof_rows(p.bw, p.oh)
        q = HP(**{**p.__dict__, "top": p.top - nr, "win": None})
        g = np.zeros((12, 12), dtype=np.int8)
        g[q.top:q.top + q.bh, q.left:q.left + q.bw] = q.A
        draw_roof(g, q, below=True)
        dw, dc, dtop, dbot = door_geom(q)
        g[dtop:dbot + 1, dc:dc + dw] = q.C
        roof_below.append(g)
        # door moved up 2 rows (painted over everything)
        g = np.zeros((12, 12), dtype=np.int8)
        g[p.top:p.top + p.bh, p.left:p.left + p.bw] = p.A
        draw_roof(g, p)
        dw, dc, dtop, dbot = door_geom(p)
        g[max(dtop - 2, 0):dbot - 1, dc:dc + dw] = p.C
        door_up.append(g)
        # same colour counts, cells randomly permuted
        g = draw_house(p).reshape(-1).copy()
        rng.shuffle(g)
        shuffled.append(g.reshape(12, 12))
    return {"roof_below": np.stack(roof_below), "door_up": np.stack(door_up),
            "shuffled": np.stack(shuffled)}


@dataclass
class HouseData:
    critic: np.ndarray       # (200,12,12)
    heldback: np.ndarray     # (100,...)
    novel: np.ndarray        # (100,...)
    broken: dict             # exam scaffolding built from held-back houses


def _fresh(rng, n, novel, guard, batch=64):
    out, params = [], []
    while len(out) < n:
        ps = [sample_params(rng, novel) for _ in range(batch)]
        gs = np.stack([draw_house(p) for p in ps])
        d = guard.distances(gs)
        for p, g, di in zip(ps, gs, d):
            if di > 0 and len(out) < n:
                out.append(g)
                params.append(p)
    return np.stack(out), params


def make_data(seed, n_critic=200, n_held=100, n_novel=100):
    rng = np.random.default_rng([seed, 4242])
    cp = [sample_params(rng, False) for _ in range(n_critic)]
    critic = np.stack([draw_house(p) for p in cp])
    guard = CopyGuard(critic)
    held, hp = _fresh(rng, n_held, False, guard)
    novel, _ = _fresh(rng, n_novel, True, guard)
    broken = make_broken(hp, rng)
    return HouseData(critic, held, novel, broken)
