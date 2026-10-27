#!/usr/bin/env python3
"""rsn-358a puzzle environments (sleep research thread, 2026-09-25).

Plan: design/v3/30-modes/358a-loop-vs-plain-general-puzzles.md. Three kinds of checkable puzzle, none about
relation facts, each written as a small grid of tokens with some cells left blank for the model to fill:

  sums     column addition with carries: row 0 = a, row 1 = b, row 2 = answer slots (right-aligned).
           Practise at most 4 digits; tested at 6 (graded) and 8 (reported) digits.
  grids    Latin-square completion (each symbol once per row and column), unique solution. Symbols are 9
           anonymous tokens relabelled every episode. Practise 4x4 and 5x5; tested 6x6 (graded), 7x7 (reported).
  numbers  the creative thread's number puzzles (use each number once with + - * / to hit the target; its
           solver and checker in scripts/claude_blurt1.py are reused). Row 0 = numbers, row 1 = target,
           row 2 = answer slots written in postfix. Practise 3 numbers (target 5-40) and 4 numbers (target 24);
           tested on 5 numbers (target 24, graded) and on 300 held-out 4-number hands (practised size).

Every item is made by code and graded by exact code; a practised-size test never re-uses a training item
(numbers: 300 held-out hands; sums and grids: fresh seeds in huge spaces, collision checks in selftest).

  python -B scripts/claude_rsn358a_envs.py selftest
"""
from __future__ import annotations

import ast
import itertools
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402  (creative thread's number-puzzle solver and checker)

# ---- vocabulary ----
BLANK, MASK = 0, 1
DIG = 2                  # digits 0-9 -> 2..11
SYM = 12                 # anonymous symbols S1..S9 -> 12..20
OPS = {"+": 21, "-": 22, "*": 23, "/": 24}
VAL = 25                 # values 0..99 -> 25..124
VOCAB = 125
ENVS = ["sums", "grids", "numbers"]
TRAIN_SIZES = {"sums": [1, 2, 3, 4], "grids": [4, 5], "numbers": [3, 4]}
OP_OF = {v: k for k, v in OPS.items()}


class Item:
    """tokens/answer are HxW lists; slot[r][c] = 1 where the model must write; target = answer tokens."""
    __slots__ = ("env", "size", "tokens", "slot", "target", "meta")

    def __init__(self, env, size, tokens, slot, target, meta):
        self.env, self.size, self.tokens, self.slot, self.target, self.meta = env, size, tokens, slot, target, meta


# ---------------- sums ----------------
def _digits_row(x, width):
    s = str(x)
    return [BLANK] * (width - len(s)) + [DIG + int(ch) for ch in s]


def make_sum(rng, n, a=None, b=None):
    """a + b with max n digits (at least one operand has exactly n digits)."""
    if a is None:
        lo = 10 ** (n - 1) if n > 1 else 0
        a = rng.randint(lo, 10 ** n - 1)
        b = rng.randint(0, 10 ** rng.randint(1, n) - 1)
        if rng.random() < 0.5:
            a, b = b, a
    w = n + 1
    tokens = [_digits_row(a, w), _digits_row(b, w), [MASK] * w]
    slot = [[0] * w, [0] * w, [1] * w]
    target = [[0] * w, [0] * w, _digits_row(a + b, w)]
    return Item("sums", n, tokens, slot, target, {"a": a, "b": b})


def check_sum(item, pred_row):
    s = "".join(str(t - DIG) for t in pred_row if DIG <= t < DIG + 10)
    lead_ok = all(t == BLANK for t in pred_row[:len(pred_row) - len(s)]) and \
        all(DIG <= t < DIG + 10 for t in pred_row[len(pred_row) - len(s):])
    return bool(s) and lead_ok and int(s) == item.meta["a"] + item.meta["b"]


# ---------------- grids (Latin squares) ----------------
def _count_solutions(grid, s, limit=2):
    rows = [0] * s
    cols = [0] * s
    empty = []
    for r in range(s):
        for c in range(s):
            v = grid[r][c]
            if v >= 0:
                if rows[r] >> v & 1 or cols[c] >> v & 1:
                    return 0
                rows[r] |= 1 << v
                cols[c] |= 1 << v
            else:
                empty.append((r, c))
    full = (1 << s) - 1
    count = 0

    def rec(todo):
        nonlocal count
        if not todo:
            count += 1
            return
        best, bi, bm = 99, -1, 0
        for i, (r, c) in enumerate(todo):
            m = full & ~(rows[r] | cols[c])
            k = bin(m).count("1")
            if k < best:
                best, bi, bm = k, i, m
                if k <= 1:
                    break
        if best == 0:
            return
        r, c = todo[bi]
        rest = todo[:bi] + todo[bi + 1:]
        m = bm
        while m and count < limit:
            v = (m & -m).bit_length() - 1
            m &= m - 1
            rows[r] |= 1 << v
            cols[c] |= 1 << v
            rec(rest)
            rows[r] &= ~(1 << v)
            cols[c] &= ~(1 << v)
    rec(empty)
    return count


def _random_latin(rng, s):
    grid = [[-1] * s for _ in range(s)]
    rows = [0] * s
    cols = [0] * s

    def rec(i):
        if i == s * s:
            return True
        r, c = divmod(i, s)
        vals = list(range(s))
        rng.shuffle(vals)
        for v in vals:
            if not (rows[r] >> v & 1 or cols[c] >> v & 1):
                grid[r][c] = v
                rows[r] |= 1 << v
                cols[c] |= 1 << v
                if rec(i + 1):
                    return True
                rows[r] &= ~(1 << v)
                cols[c] &= ~(1 << v)
                grid[r][c] = -1
        return False
    rec(0)
    return grid


def make_latin_base(rng, s):
    """(solution, puzzle) with values 0..s-1 and -1 for blanks; unique solution; removal depth varies."""
    sol = _random_latin(rng, s)
    puz = [row[:] for row in sol]
    cells = [(r, c) for r in range(s) for c in range(s)]
    rng.shuffle(cells)
    stop_frac = rng.uniform(0.35, 1.0)          # fraction of removable cells actually removed
    removed = 0
    for r, c in cells:
        keep = puz[r][c]
        puz[r][c] = -1
        if _count_solutions(puz, s) != 1:
            puz[r][c] = keep
        else:
            removed += 1
            if removed >= stop_frac * s * s * 0.75:
                break
    return sol, puz


def augment_latin(rng, sol, puz):
    """row/col permutation and transpose keep uniqueness."""
    s = len(sol)
    rp, cp = list(range(s)), list(range(s))
    rng.shuffle(rp)
    rng.shuffle(cp)
    t = rng.random() < 0.5
    def f(g):
        h = [[g[rp[r]][cp[c]] for c in range(s)] for r in range(s)]
        return [list(x) for x in zip(*h)] if t else h
    return f(sol), f(puz)


def latin_item(rng, sol, puz):
    s = len(sol)
    names = rng.sample(range(9), s)             # anonymous symbols, relabelled every episode
    tokens = [[SYM + names[v] if v >= 0 else MASK for v in row] for row in puz]
    slot = [[1 if v < 0 else 0 for v in row] for row in puz]
    target = [[SYM + names[sol[r][c]] if puz[r][c] < 0 else 0 for c in range(s)] for r in range(s)]
    return Item("grids", s, tokens, slot, target, {"puz": puz, "names": names})


def check_latin(item, pred):
    """any valid completion that keeps the givens is right (the puzzle has one anyway)."""
    s = item.size
    names = item.meta["names"]
    inv = {SYM + n: i for i, n in enumerate(names)}
    g = []
    for r in range(s):
        row = []
        for c in range(s):
            v = item.meta["puz"][r][c]
            if v < 0:
                t = pred[r][c]
                if t not in inv:
                    return False
                v = inv[t]
            row.append(v)
        g.append(row)
    full = set(range(s))
    return all(set(row) == full for row in g) and all({g[r][c] for r in range(s)} == full for c in range(s))


# ---------------- numbers ----------------
def to_postfix(expr: str):
    toks = []

    def rec(n):
        if isinstance(n, ast.Expression):
            return rec(n.body)
        if isinstance(n, ast.Constant):
            toks.append(("n", int(n.value)))
            return
        rec(n.left)
        rec(n.right)
        toks.append(("o", {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(n.op)]))
    rec(ast.parse(expr, mode="eval"))
    return toks


def postfix_to_infix(toks):
    st = []
    for kind, v in toks:
        if kind == "n":
            st.append(str(v))
        else:
            if len(st) < 2:
                return None
            y, x = st.pop(), st.pop()
            st.append(f"({x}{v}{y})")
    return st[0] if len(st) == 1 else None


def number_item(rng, nums, target, solution):
    k = len(nums)
    shown = nums[:]
    rng.shuffle(shown)
    L = 2 * k - 1
    w = max(k, L)
    pf = to_postfix(solution)
    assert len(pf) == L
    tokens = [[VAL + x for x in shown] + [BLANK] * (w - k), [VAL + target] + [BLANK] * (w - 1), [MASK] * L + [BLANK] * (w - L)]
    slot = [[0] * w, [0] * w, [1] * L + [0] * (w - L)]
    ans = [VAL + v if kind == "n" else OPS[v] for kind, v in pf]
    target_rows = [[0] * w, [0] * w, ans + [0] * (w - L)]
    return Item("numbers", k, tokens, slot, target_rows, {"nums": nums, "target": target})


def check_numbers(item, pred_row):
    k = len(item.meta["nums"])
    toks = []
    for t in pred_row[:2 * k - 1]:
        if VAL <= t < VAL + 100:
            toks.append(("n", t - VAL))
        elif t in OP_OF:
            toks.append(("o", OP_OF[t]))
        else:
            return False
    expr = postfix_to_infix(toks)
    return expr is not None and B1.check(expr, item.meta["nums"], item.meta["target"])


def number_hands():
    """All 4-number hands (1-13, target 24) and 3-number hands (1-9, targets 5-40) with a solution."""
    four, three = [], []
    for h in itertools.combinations_with_replacement(range(1, 14), 4):
        s = B1.solve(list(h), 24)
        if s:
            four.append((list(h), 24, s))
    for h in itertools.combinations_with_replacement(range(1, 10), 3):
        for t in range(5, 41):
            s = B1.solve(list(h), t)
            if s:
                three.append((list(h), t, s))
    return four, three


HELDOUT_SEED = 35801


def split_four(four):
    """300 held-out 4-number hands (practised-size test); the rest are practice."""
    idx = list(range(len(four)))
    random.Random(HELDOUT_SEED).shuffle(idx)
    held = set(idx[:300])
    return [four[i] for i in idx if i not in held], [four[i] for i in sorted(held)]


def five_hands(seed, n):
    rng, out, seen = random.Random(seed), [], set()
    while len(out) < n:
        h = tuple(sorted(rng.randint(1, 13) for _ in range(5)))
        if h in seen:
            continue
        seen.add(h)
        s = B1.solve(list(h), 24)
        if s:
            out.append((list(h), 24, s))
    return out


# ---------------- grading ----------------
def check(item, pred):
    if item.env == "sums":
        return check_sum(item, pred[2])
    if item.env == "grids":
        return check_latin(item, pred)
    return check_numbers(item, pred[2])


def selftest():
    rng = random.Random(0)
    for n in (1, 4, 8):
        for _ in range(200):
            it = make_sum(rng, n)
            assert check(it, it.target), (n, it.meta)
            bad = [row[:] for row in it.target]
            j = rng.randrange(len(bad[2]))
            bad[2][j] = DIG + (bad[2][j] - DIG + 1) % 10 if bad[2][j] != BLANK else DIG + 1
            assert not check(it, bad)
    for s in (4, 5, 6):
        for _ in range(20):
            sol, puz = make_latin_base(rng, s)
            assert _count_solutions(puz, s) == 1
            sol2, puz2 = augment_latin(rng, sol, puz)
            assert _count_solutions(puz2, s) == 1
            it = latin_item(rng, sol2, puz2)
            full = [[it.target[r][c] if it.slot[r][c] else 0 for c in range(s)] for r in range(s)]
            assert check(it, full)
            cells = [(r, c) for r in range(s) for c in range(s) if it.slot[r][c]]
            if len(cells) >= 2:
                (r1, c1), (r2, c2) = cells[:2]
                full[r1][c1] = SYM + (full[r1][c1] - SYM + 1) % 9
                assert not check(it, full)
    four, three = number_hands()
    train4, held4 = split_four(four)
    assert len(held4) == 300 and not ({tuple(h) for h, _, _ in train4} & {tuple(h) for h, _, _ in held4})
    for h, t, sol in rng.sample(four, 50) + rng.sample(three, 50) + five_hands(1, 20):
        it = number_item(rng, h, t, sol)
        assert check(it, it.target), (h, t, sol)
        bad = [row[:] for row in it.target]
        bad[2][0] = VAL + (bad[2][0] - VAL + 1) % 14 if bad[2][0] >= VAL else bad[2][0]
        assert not check(it, bad)
        assert B1.check(postfix_to_infix(to_postfix(sol)), h, t)
    print(f"selftest ok: {len(four)} four-hands ({len(train4)} practice, {len(held4)} held out), {len(three)} three-hands")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
