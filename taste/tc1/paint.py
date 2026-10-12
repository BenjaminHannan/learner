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


def random_programs(rng, n):
    return [random_program(rng) for _ in range(n)]


def encode_batch(programs):
    """list of token lists (no BOS, end with END) -> int64 array (N, CTX): BOS prog PAD..."""
    out = np.zeros((len(programs), CTX), dtype=np.int64)
    out[:, 0] = BOS
    for i, p in enumerate(programs):
        out[i, 1:1 + len(p)] = p
    return out


def draws(grid):
    return bool(np.any(grid))
