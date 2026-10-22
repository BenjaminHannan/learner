"""Toy Paint: 12x12 canvas, colours 0-4, token program grammar."""
import numpy as np

PAD, BOS, END, R, T, D = 0, 1, 2, 3, 4, 5
NUM0 = 6                      # number token for value v is NUM0 + v, v in 0..12
VOCAB = NUM0 + 13             # 19
H = W = 12
MAX_CMDS = 6
CTX = 40                      # BOS + 6*6 + END = 38 <= 40
ARITY = {R: 5, T: 4, D: 3}
RANGES = {
    R: [(0, 11), (0, 11), (1, 12), (1, 12), (1, 4)],   # r c h w k
    T: [(0, 11), (0, 11), (1, 12), (1, 4)],            # r c w k
    D: [(0, 11), (0, 11), (1, 4)],                     # r c k
}


def parse(tokens):
    """tokens (no BOS needed; a single leading BOS is stripped) -> list of commands or None."""
    toks = [int(t) for t in tokens]
    if toks and toks[0] == BOS:
        toks = toks[1:]
    n = len(toks)
    cmds = []
    i = 0
    while True:
        if i >= n:
            return None                      # missing END
        t = toks[i]
        if t == END:
            return cmds if i == n - 1 else None   # tokens after END are invalid
        if t not in ARITY:
            return None
        if len(cmds) >= MAX_CMDS:
            return None
        if i + 1 + ARITY[t] > n:
            return None
        vals = []
        for j, (lo, hi) in enumerate(RANGES[t]):
            tok = toks[i + 1 + j]
            if tok < NUM0 or tok >= NUM0 + 13:
                return None
            v = tok - NUM0
            if not (lo <= v <= hi):
                return None
            vals.append(v)
        cmds.append((t, *vals))
        i += 1 + ARITY[t]


def render(commands):
    g = np.zeros((H, W), dtype=np.int8)
    for cmd in commands:
        t = cmd[0]
        if t == R:
            _, r, c, h, w, k = cmd
            g[r:min(r + h, H), c:min(c + w, W)] = k
        elif t == T:
            _, r, c, w, k = cmd
            i = 0
            while True:
                row = r - i
                width = w - 2 * i
                if row < 0 or width <= 0:
                    break
                g[row, c + i:min(c + w - i, W)] = k
                i += 1
        elif t == D:
            _, r, c, k = cmd
            g[r, c] = k
    return g


def encode(commands):
    toks = []
    for cmd in commands:
        toks.append(cmd[0])
        toks.extend(NUM0 + v for v in cmd[1:])
    toks.append(END)
    return toks


def random_program(rng):
    """Token list (no BOS) ending with END."""
    n = int(rng.integers(1, MAX_CMDS + 1))
    types = rng.integers(0, 3, n)
    cmds = []
    for ti in types:
        t = (R, T, D)[int(ti)]
        vals = [int(rng.integers(lo, hi + 1)) for lo, hi in RANGES[t]]
        cmds.append((t, *vals))
    return encode(cmds)


def _tri_height(w):
    return (w + 1) // 2


def _bbox_of(cmd):
    """(r0, r1, c0, c1) of a command's cells, clipped to the canvas."""
    t = cmd[0]
    if t == R:
        _, r, c, h, w, _ = cmd
        return r, min(r + h, H) - 1, c, min(c + w, W) - 1
    if t == T:
        _, r, c, w, _ = cmd
        return max(r - _tri_height(w) + 1, 0), r, c, min(c + w, W) - 1
    _, r, c, _ = cmd
    return r, r, c, c


def _align(rng, lo, hi, size):
    """Start of a span of `size` cells placed along [lo, hi]: centred, start-flush, end-flush or random."""
    mode = int(rng.integers(0, 4))
    if mode == 0:
        s = lo + ((hi - lo + 1) - size) // 2
    elif mode == 1:
        s = lo
    elif mode == 2:
        s = hi - size + 1
    else:
        s = int(rng.integers(lo - size + 1, hi + 1))
    return int(np.clip(s, 0, W - 1))


def random_program_v2(rng):
    """TC-1b 'touching shapes' babbling prior: 1-3 shapes, each after the first touches (or sits
    inside, bottom-aligned) a random earlier shape with a similar size along the touching side.
    Token list (no BOS) ending with END."""
    n = int(rng.integers(1, 4))
    k = int(rng.integers(1, 5))
    if rng.integers(0, 2) == 0:
        h, w = int(rng.integers(1, 6)), int(rng.integers(1, 10))
        cmds = [(R, int(rng.integers(0, H - h + 1)), int(rng.integers(0, W - w + 1)), h, w, k)]
    else:
        w = int(rng.integers(1, 10))
        th = _tri_height(w)
        cmds = [(T, int(rng.integers(th - 1, H)), int(rng.integers(0, W - w + 1)), w, k)]
    for _ in range(n - 1):
        r0, r1, c0, c1 = _bbox_of(cmds[int(rng.integers(0, len(cmds)))])
        aw, ah = c1 - c0 + 1, r1 - r0 + 1
        t = (R, T, D)[int(rng.integers(0, 3))]
        rel = int(rng.integers(0, 5))          # above, below, left, right, inside
        k = int(rng.integers(1, 5))
        d = int(rng.integers(-2, 3))
        if t == D:
            if rel == 0:
                r, c = r0 - 1, _align(rng, c0, c1, 1)
            elif rel == 1:
                r, c = r1 + 1, _align(rng, c0, c1, 1)
            elif rel == 2:
                r, c = _align(rng, r0, r1, 1), c0 - 1
            elif rel == 3:
                r, c = _align(rng, r0, r1, 1), c1 + 1
            else:
                r, c = r1, _align(rng, c0, c1, 1)
            cmds.append((D, int(np.clip(r, 0, H - 1)), int(np.clip(c, 0, W - 1)), k))
        elif t == R:
            if rel in (0, 1):
                w, h = int(np.clip(aw + d, 1, 12)), int(rng.integers(1, 6))
                c = _align(rng, c0, c1, w)
                r = r0 - h if rel == 0 else r1 + 1
            elif rel in (2, 3):
                h, w = int(np.clip(ah + d, 1, 12)), int(rng.integers(1, 10))
                r = _align(rng, r0, r1, h)
                c = c0 - w if rel == 2 else c1 + 1
            else:
                w, h = int(np.clip(aw + d, 1, aw)), int(rng.integers(1, ah + 1))
                c = _align(rng, c0, c1, w)
                r = r1 - h + 1
            cmds.append((R, int(np.clip(r, 0, H - 1)), int(np.clip(c, 0, W - 1)), h, w, k))
        else:
            if rel in (0, 1):
                w = int(np.clip(aw + d, 1, 12))
                c = _align(rng, c0, c1, w)
                r = r0 - 1 if rel == 0 else r1 + _tri_height(w)
            elif rel in (2, 3):
                w = int(rng.integers(1, 10))
                r = r1
                c = c0 - w if rel == 2 else c1 + 1
            else:
                w = int(np.clip(aw + d, 1, min(aw, 2 * ah)))
                c = _align(rng, c0, c1, w)
                r = r1
            cmds.append((T, int(np.clip(r, 0, H - 1)), int(np.clip(c, 0, W - 1)), w, k))
    return encode(cmds)


PRIORS = {"clutter": random_program, "touching": random_program_v2}


def random_programs(rng, n, prior="clutter"):
    f = PRIORS[prior]
    return [f(rng) for _ in range(n)]


def encode_batch(programs):
    """list of token lists (no BOS, end with END) -> int64 array (N, CTX): BOS prog PAD..."""
    out = np.zeros((len(programs), CTX), dtype=np.int64)
    out[:, 0] = BOS
    for i, p in enumerate(programs):
        out[i, 1:1 + len(p)] = p
    return out


def canonical(g):
    """Folded picture key: drawn cells moved to the top-left corner, mirror folded."""
    def tight(a):
        rows, cols = np.flatnonzero(a.any(1)), np.flatnonzero(a.any(0))
        out = np.zeros_like(a)
        sub = a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
        out[:sub.shape[0], :sub.shape[1]] = sub
        return out
    g1 = tight(g)
    g2 = tight(g1[:, ::-1])
    return min(g1.tobytes(), g2.tobytes())


def draws(grid):
    return bool(np.any(grid))
