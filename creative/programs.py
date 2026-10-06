"""Programs in B2's workspace, run with exact python ints, plus the forced-replay training form.

Slots (custom_io.models.progparse): 0..15 prompt numbers, 16..19 constants 1 2 10 100, 20..26 results (step s -> slot R0 + s).
A try is what B2 logs: up to 7 steps (op index into pp.OPS, operand slot a, operand slot b) and an answer slot.
Everything here is plain python (no torch) so the checkers stay independent of B2's tensor executor."""
from dataclasses import dataclass
from custom_io.models import progparse as pp

N_NUM, CONSTS, N_RES, R0, M, OPS, COMM = pp.N_NUM, pp.CONSTS, pp.N_RES, pp.R0, pp.M, pp.OPS, pp.COMM
NOOP, ADD, SUB, MUL, DIV = 0, 1, 2, 3, 4
ARITH = (ADD, SUB, MUL, DIV)
BIG = 10 ** 9


@dataclass(frozen=True)
class Try:
    """ops/a/b are length-7 tuples (NOOP padded, a = b = 0 on NOOP); ans = the answer-pointer slot."""
    ops: tuple
    a: tuple
    b: tuple
    ans: int

    @staticmethod
    def make(steps, ans):
        steps = list(steps)[:N_RES]
        pad = N_RES - len(steps)
        return Try(tuple(s[0] for s in steps) + (NOOP,) * pad, tuple(s[1] for s in steps) + (0,) * pad,
                   tuple(s[2] for s in steps) + (0,) * pad, ans)

    def steps(self):
        return list(zip(self.ops, self.a, self.b))


def apply(op, x, y):
    """Reference semantics of custom_io.models.ledger.execute for python ints. None = invalid (DIV only when exact)."""
    if abs(x) >= BIG or abs(y) >= BIG or op == NOOP:
        return None
    if op == ADD: v = x + y
    elif op == SUB: v = x - y
    elif op == MUL: v = x * y
    elif op == DIV: v = None if y == 0 or x % y else x // y
    elif op == 5: v = None if y == 0 else x % y
    elif op == 6: v = min(x, y)
    elif op == 7: v = max(x, y)
    elif op == 8: v = (x > y) - (x < y)
    else: return None
    return None if v is None or abs(v) >= BIG else v


def run(nums, t):
    """-> (vals [M], valid [M]) after running the try on prompt numbers `nums` (first 16 kept). Invalid operand -> invalid result."""
    vals, valid = [0] * M, [False] * M
    for i, n in enumerate(nums[:N_NUM]):
        vals[i], valid[i] = n, True
    for i, c in enumerate(CONSTS):
        vals[N_NUM + i], valid[N_NUM + i] = c, True
    for s, (op, a, b) in enumerate(t.steps()):
        if 0 <= a < M and 0 <= b < M and valid[a] and valid[b]:
            v = apply(op, vals[a], vals[b])
            if v is not None:
                vals[R0 + s], valid[R0 + s] = v, True
    return vals, valid


def cone(t):
    """Step indices (ascending) that feed the answer slot, or None if the answer is not a result slot, or the tree reads an unwritten
    (NOOP) step or a step that is not strictly earlier."""
    if not R0 <= t.ans < M:
        return None
    seen = set()

    def visit(s):
        if s in seen:
            return True
        if t.ops[s] == NOOP:
            return False
        seen.add(s)
        for p in (t.a[s], t.b[s]):
            if R0 <= p < M and (p - R0 >= s or not visit(p - R0)):
                return False
        return True
    return sorted(seen) if visit(t.ans - R0) else None


def leaves(t, slot):
    """Expanded leaf slots (with repeats) of the expression tree rooted at `slot`; [slot] for a non-result slot."""
    if not R0 <= slot < M:
        return [slot]
    s = slot - R0
    return leaves(t, t.a[s]) + leaves(t, t.b[s])


def expr(t, slot):
    """Canonical string of the expression rooted at `slot`: leaf = slot id, (OP l r) with commutative operands sorted."""
    if not R0 <= slot < M:
        return str(slot)
    s = slot - R0
    l, r = expr(t, t.a[s]), expr(t, t.b[s])
    if t.ops[s] in COMM and l > r:
        l, r = r, l
    return f'({OPS[t.ops[s]]} {l} {r})'


def raw_key(t):
    """Duplicate key for the sampler: the written steps with commutative operands ordered, then the answer slot."""
    st = tuple((o, min(x, y), max(x, y)) if o in COMM else (o, x, y) for o, x, y in t.steps())
    return st, t.ans


def result_key(t, valid):
    """The 'steps that do something': canonical expression of the answer cone; 'dead' if the answer slot holds nothing."""
    if not (0 <= t.ans < M and valid[t.ans]):
        return 'dead'
    return expr(t, t.ans) if cone(t) is not None else f'leaf:{t.ans}'


def train_form(t):
    """The accepted tree in the first steps, then NOOP, from the logged slot ids (never re-parsed from values):
    -> (steps [(op, a, b)], ans_slot) with the cone's steps renumbered 0..k-1 in their original order. None if the try has no cone."""
    c = cone(t)
    if c is None:
        return None
    new = {R0 + s: R0 + j for j, s in enumerate(c)}
    steps = [(t.ops[s], new.get(t.a[s], t.a[s]), new.get(t.b[s], t.b[s])) for s in c]
    return steps, new[t.ans]


def register_targets(row_id, nums, steps, ans):
    """Seed custom_io's per-row-id target cache so Ledger.gold() forces exactly these slot ids (mode NUM, answer pointer = ans).
    Row ids must be unique across everything sleeping together: the cache is keyed by id. Returns the program's step values."""
    t = Try.make(steps, ans)
    vals, valid = run(nums, t)
    assert all(valid[R0 + s] for s in range(len(steps))) and valid[ans], 'forced program must run cleanly'
    prog = tuple((o, (a,), (b,), vals[R0 + s]) for s, (o, a, b) in enumerate(steps))
    pp._CACHE[row_id] = dict(prog=prog, mode=0, ans=(ans,), word=())
    return [vals[R0 + s] for s in range(len(steps))]
