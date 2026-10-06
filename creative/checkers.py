"""C1's two independently written checkers (no answer key) and the judge that combines them with an exact replay.

Rules, from the roadmap section 6: allowed ops ADD SUB MUL DIV only; take the tree of steps that feeds the final answer slot; it uses
each given number exactly once by slot id, never the target's slot or a constant, DIV exact, and ends on the target value.
  rules_a: recursive descent over the logged slot ids, python ints, leaf multiset by expansion.
  rules_b: a different algorithm: reverse reachability for the step set, then a consumption pool with Fractions (each step eats its
           two operands from the pool and adds its result; at the end the pool must be exactly {answer slot}).
verdict(): 'accept' | 'reject' | 'unresolved' (checkers disagree, B2's torch executor does not reproduce the replay, or a crash).
`nums` = the prompt numbers in order (the given numbers, then the target); target_slot = len(given) = the target's slot.
check_value=False judges the rules only (what the R placebo and the hindsight arms select on)."""
from collections import Counter
from fractions import Fraction
from creative.programs import ARITH, CONSTS, M, N_NUM, N_RES, NOOP, R0, cone, leaves, run

ADD_, SUB_, MUL_, DIV_ = ARITH
CONST_SLOTS = set(range(N_NUM, N_NUM + len(CONSTS)))


def rules_a(nums, target_slot, t, check_value=True, target=None):
    """-> (ok, reason)."""
    vals, valid = run(nums, t)
    if not (R0 <= t.ans < M) or not valid[t.ans]:
        return False, 'answer is not a written, valid result'
    c = cone(t)
    if c is None:
        return False, 'answer cone reads an unwritten or later step'
    for s in c:
        if t.ops[s] not in ARITH:
            return False, 'op not allowed'
        if not valid[R0 + s]:
            return False, 'invalid step'
    lv = Counter(leaves(t, t.ans))
    if any(x in CONST_SLOTS for x in lv):
        return False, 'uses a constant'
    if lv.get(target_slot, 0):
        return False, 'uses the target slot'
    if set(lv) != set(range(target_slot)) or any(v != 1 for v in lv.values()):
        return False, 'does not use each number exactly once'
    if check_value and vals[t.ans] != (nums[target_slot] if target is None else target):
        return False, 'does not end on the target'
    return True, 'ok'


def rules_b(nums, target_slot, t, check_value=True, target=None):
    if not (R0 <= t.ans < R0 + N_RES):
        return False, 'answer is not a result slot'
    need, stack = set(), [t.ans]
    while stack:                                                  # reverse reachability from the answer slot
        slot = stack.pop()
        if R0 <= slot < R0 + N_RES:
            st = slot - R0
            if st not in need:
                need.add(st)
                stack += [t.a[st], t.b[st]]
    pool = {i: Fraction(nums[i]) for i in range(target_slot)}     # slot -> value of everything still available
    for st in sorted(need):
        op, a, b = t.ops[st], t.a[st], t.b[st]
        if op not in ARITH:
            return False, 'op not allowed'
        if a == b or a not in pool or b not in pool:
            return False, 'operand not available exactly once'
        x, y = pool.pop(a), pool.pop(b)
        if op == ADD_:
            v = x + y
        elif op == SUB_:
            v = x - y
        elif op == MUL_:
            v = x * y
        else:
            if y == 0 or (x / y).denominator != 1:
                return False, 'inexact division'
            v = x / y
        pool[R0 + st] = v
    if set(pool) != {t.ans}:
        return False, 'does not use each number exactly once'
    if check_value and pool[t.ans] != Fraction(nums[target_slot] if target is None else target):
        return False, 'does not end on the target'
    return True, 'ok'


def replay_agrees(nums, t):
    """Run the logged program with B2's own torch int64 executor (custom_io.models.ledger.replay) and compare each step the python run
    wrote with it. False = the replay does not reproduce."""
    import torch
    from custom_io.models.ledger import replay
    vals, valid = run(nums, t)
    v0 = torch.zeros(1, M, dtype=torch.long)
    ok0 = torch.zeros(1, M, dtype=torch.bool)
    for i, n in enumerate(nums[:N_NUM]):
        v0[0, i], ok0[0, i] = min(n, 10 ** 18), True
    for i, c in enumerate(CONSTS):
        v0[0, N_NUM + i], ok0[0, N_NUM + i] = c, True
    row = lambda xs: torch.tensor([list(xs)], dtype=torch.long)
    v, ok = replay(v0, ok0, row(t.ops), row(t.a), row(t.b))
    for s in range(N_RES):
        clean = (t.ops[s] != NOOP and all(0 <= x < R0 + s and valid[x] for x in (t.a[s], t.b[s])))     # torch reads 0 from an unwritten slot: compare clean steps only
        if clean and (valid[R0 + s] != bool(ok[0, R0 + s]) or (valid[R0 + s] and vals[R0 + s] != int(v[0, R0 + s]))):
            return False
    return True


def verdict(nums, target_slot, t, check_value=True, target=None, replay=True):
    """-> (verdict, reason). 'unresolved' counts as no hit everywhere."""
    try:
        ra, rb = rules_a(nums, target_slot, t, check_value, target), rules_b(nums, target_slot, t, check_value, target)
        if ra[0] != rb[0]:
            return 'unresolved', f'checkers disagree: a={ra[1]} b={rb[1]}'
        if replay and ra[0] and not replay_agrees(nums, t):         # only an accept needs the exact-executor replay
            return 'unresolved', 'replay does not reproduce'
        return ('accept' if ra[0] else 'reject'), ra[1]
    except Exception as e:
        return 'unresolved', f'crash: {type(e).__name__}: {e}'
