"""Hidden house score. FOR MEASUREMENT ONLY: import from eval.py and oracle.py only."""
import numpy as np


def _bbox(m):
    rows = np.flatnonzero(m.any(1))
    cols = np.flatnonzero(m.any(0))
    return rows[0], rows[-1], cols[0], cols[-1]


def find_body(g):
    best = None
    for a in range(1, 5):
        m = g == a
        if not m.any():
            continue
        r0, r1, c0, c1 = _bbox(m)
        w, h = c1 - c0 + 1, r1 - r0 + 1
        if w >= 3 and h >= 2 and not (g[r0:r1 + 1, c0:c1 + 1] == 0).any() and 2 * m.sum() >= w * h:
            if best is None or w * h > best[0]:
                best = (w * h, a, r0, r1, c0, c1)
    return best


def _roof_ok(g, b, top, bl, br):
    m = g == b
    rows = np.flatnonzero(m.any(1))
    if rows[-1] != top - 1:
        return False
    if not np.array_equal(rows, np.arange(rows[0], rows[-1] + 1)):
        return False
    prev = None
    for r in range(rows[-1], rows[0] - 1, -1):
        cols = np.flatnonzero(m[r])
        l, rr = cols[0], cols[-1]
        if len(cols) != rr - l + 1:
            return False
        if prev is None:
            if not (bl - 1 <= l <= bl and br <= rr <= br + 1):
                return False
        elif rr - l + 1 > prev[1] - prev[0] + 1:
            return False
        prev = (l, rr)
    return True


def score_grid(g):
    """-> (score in {0,.2,...,1}, (body, roof, door, symmetric, clean))."""
    g = np.asarray(g)
    body = find_body(g)
    if body is None:
        return 0.0, (False,) * 5
    _, A, top, bot, bl, br = body
    bw, bh = br - bl + 1, bot - top + 1
    roof_col, roof_n = None, -1
    for b in range(1, 5):
        if b == A or not (g == b).any():
            continue
        if _roof_ok(g, b, top, bl, br):
            n = int((g == b).sum())
            if n > roof_n:
                roof_col, roof_n = b, n
    roof = roof_col is not None
    door = False
    for c in range(1, 5):
        if c == A or (roof and c == roof_col):
            continue
        m = g == c
        if not m.any():
            continue
        r0, r1, c0, c1 = _bbox(m)
        w, h = c1 - c0 + 1, r1 - r0 + 1
        if (m.sum() == w * h and r0 >= top and r1 <= bot and c0 >= bl and c1 <= br
                and r1 == bot and w <= bw - 2):
            door = True
            break
    sym = clean = False
    if roof:
        cols = np.arange(12)
        cm = bl + br - cols
        inr = (cm >= 0) & (cm < 12)
        mirrored = g[:, np.clip(cm, 0, 11)]
        mism = int(((g != mirrored) & inr[None, :] & (cols < cm)[None, :]).sum())
        mism += int(((g != 0) & (~inr)[None, :]).sum())
        sym = mism <= 1
        allowed = (g == roof_col)
        allowed[top:bot + 1, bl:br + 1] = True
        clean = not ((g != 0) & ~allowed).any()
    t = (True, roof, door, sym, clean)
    return sum(t) / 5.0, t
