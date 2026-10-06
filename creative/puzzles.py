"""C1 puzzles: "use A, B and C once each with + - x / to make T". Generator, exact solver, twin targets, hash-sealed splits, floors.

Numbers 3..40 excluding 10 (so no given number equals a B2 constant 1 2 10 100), T >= 1 (B2's number reader drops minus signs),
T not a constant and not a given number, exact division only, solvable, and no 2-number shortcut (no pair of the given numbers makes T).
Prompt order is the given numbers, then the target, so the target is slot len(numbers) and the given numbers are slots 0..n-1.
One fixed instruction line, identical in every arm (it carries no digits, so it adds no number slots)."""
import hashlib, itertools, json, os, random
from fractions import Fraction
from creative.programs import ADD, ARITH, CONSTS, DIV, MUL, OPS, R0, SUB, Try, apply, expr, run

POOL = [n for n in range(3, 41) if n != 10]
T_MAX = 999
FAMILY = 'make_target'
SALT = 'creative-c1-v1'
SPLITS = dict(practice=1024, dev=128, t1=256, t1b=256)       # 3-number puzzles, disjoint number sets
X_SIZE = 128                                                    # 4-number puzzles, report only
TWINS = ('dev', 't1', 't1b')                                    # splits whose puzzles carry a twin target
SYM = {ADD: '+', SUB: '-', MUL: 'x', DIV: '/'}


def prompt(nums, target):
    return f'Numbers: {", ".join(map(str, nums))}. Target: {target}. Use each number once with + - x / to make the target.'


def all_exprs(nums):
    """{value: [expression]} over every way to use ALL the numbers exactly once. Expression = slot int or (op, l, r). Division must be
    exact at every step; intermediates may be zero or negative. Commutative ops appear in one operand order."""
    n = len(nums)
    by_mask = {1 << i: {nums[i]: [i]} for i in range(n)}
    for mask in range(1, 1 << n):
        if mask in by_mask:
            continue
        out = {}
        sub = (mask - 1) & mask
        while sub:
            other = mask ^ sub
            if sub < other:
                for vl, el in by_mask[sub].items():
                    for vr, er in by_mask[other].items():
                        for op in ARITH:
                            for x, ex_, y, ey in ((vl, el, vr, er),) if op in (ADD, MUL) else ((vl, el, vr, er), (vr, er, vl, el)):
                                v = apply(op, x, y)
                                if v is not None:
                                    out.setdefault(v, []).extend((op, e1, e2) for e1 in ex_ for e2 in ey)
            sub = (sub - 1) & mask
        by_mask[mask] = out
    return by_mask[(1 << n) - 1]


def expr_to_try(e):
    """Post-order linearisation of a nested expression into B2 steps; the answer is the last result."""
    steps = []

    def go(x):
        if isinstance(x, int):
            return x
        a, b = go(x[1]), go(x[2])
        steps.append((x[0], a, b))
        return R0 + len(steps) - 1
    ans = go(e)
    return Try.make(steps, ans)


def reachable_from_pair(nums, T):
    for i, j in itertools.combinations(range(len(nums)), 2):
        for op in ARITH:
            if apply(op, nums[i], nums[j]) == T or apply(op, nums[j], nums[i]) == T:
                return True
    return False


def valid_targets(nums):
    """-> {T: [Try, ...]}: solvable targets for this number set under the puzzle rules, each with all its solutions."""
    res = {}
    for v, exprs in all_exprs(list(nums)).items():
        if 1 <= v <= T_MAX and v not in CONSTS and v not in nums and not reachable_from_pair(nums, v):
            res[v] = [expr_to_try(e) for e in exprs]
    return res


def solutions(nums, T):
    return valid_targets(nums).get(T, [])


def steps_text(nums, t):
    vals, _ = run(list(nums), t)
    return [f'{vals[a]} {SYM.get(op, OPS[op])} {vals[b]} = {vals[R0 + s]}' for s, (op, a, b) in enumerate(t.steps()) if op]


def make_row(pid, nums, target, split):
    return dict(id=pid, prompt=prompt(nums, target), answer=str(target), accepted=[str(target)], family=FAMILY, level=0, stage=0,
                variant='', steps=[], split=split, nums=list(nums), target=target)


def _h(*parts):
    return int(hashlib.sha256('|'.join(map(str, (SALT,) + parts)).encode()).hexdigest(), 16)


def build_splits():
    """Deterministic splits by number set (hash order). -> {split: [row], 'x': [row]}. Rows in TWINS splits carry row['twin'] = a second row
    with the same numbers and a different solvable target. Rows carry their solution count ('n_solutions')."""
    triples = sorted(itertools.combinations_with_replacement(POOL, 3), key=lambda s: _h('set3', s))
    out = {k: [] for k in SPLITS}
    order, cur = list(SPLITS), 0
    for tri in triples:
        while cur < len(order) and len(out[order[cur]]) >= SPLITS[order[cur]]:
            cur += 1
        if cur == len(order):
            break
        split = order[cur]
        vt = valid_targets(tri)
        if not vt or (split in TWINS and len(vt) < 2):
            continue
        rng = random.Random(_h('target', tri))
        ts = sorted(vt)
        T = rng.choice(ts)
        row = make_row(f'mk:{split}:{len(out[split]):04d}', tri, T, split)
        row['n_solutions'] = len(vt[T])
        if split in TWINS:
            T2 = rng.choice([x for x in ts if x != T])
            tw = make_row(row['id'] + ':twin', tri, T2, split)
            tw['n_solutions'], tw['twin_of'] = len(vt[T2]), row['id']
            row['twin'] = tw
        out[split].append(row)
    out['x'] = []
    for q in sorted(itertools.combinations_with_replacement(POOL, 4), key=lambda s: _h('set4', s)):
        if len(out['x']) >= X_SIZE:
            break
        vt = valid_targets(q)
        if vt:
            T = random.Random(_h('target4', q)).choice(sorted(vt))
            r = make_row(f'mk:x:{len(out["x"]):04d}', q, T, 'x')
            r['n_solutions'] = len(vt[T])
            out['x'].append(r)
    for k, n in dict(SPLITS, x=X_SIZE).items():
        assert len(out[k]) == n, (k, len(out[k]))
    return out


def write_splits(out_dir):
    """Write one jsonl per split and MANIFEST.json (sha256 of each file = the seal). Returns the manifest."""
    os.makedirs(out_dir, exist_ok=True)
    sp, man, seen = build_splits(), {}, {}
    for k, rows in sp.items():
        if k != 'x':
            for r in rows:
                assert seen.setdefault(tuple(sorted(r['nums'])), k) == k, 'number sets must not cross splits'
        path = os.path.join(out_dir, f'{k}.jsonl')
        with open(path, 'w') as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True) + '\n')
        man[k] = dict(n=len(rows), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                      twins=sum('twin' in r for r in rows), mean_solutions=round(sum(r['n_solutions'] for r in rows) / len(rows), 3))
    man['_spec'] = dict(salt=SALT, pool=POOL, t_max=T_MAX, sizes=dict(SPLITS, x=X_SIZE))
    json.dump(man, open(os.path.join(out_dir, 'MANIFEST.json'), 'w'), indent=1, sort_keys=True)
    return man


def load_split(out_dir, name):
    """Rows of a split; refuses a file that does not match the sealed hash."""
    path = os.path.join(out_dir, f'{name}.jsonl')
    man = json.load(open(os.path.join(out_dir, 'MANIFEST.json')))
    assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == man[name]['sha256'], f'{name}: file does not match the sealed hash'
    return [json.loads(l) for l in open(path)]


def solver_records(row, k, rng):
    """Up to k structurally distinct solver programs for the row's puzzle, chosen at random."""
    sols = solutions(row['nums'], row['target'])
    rng.shuffle(sols)
    seen, out = set(), []
    for t in sols:
        key = expr(t, t.ans)
        if key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) >= k:
            break
    return out


# ---- floors (recomputed for B2's slots; stage S0) ----
def rules_only_floor(nums, target):
    """Exact per-try luck of a value-blind rule-following random try: each step picks an op from + - x / and two distinct available
    slots (given numbers and earlier results not yet spent) uniformly at random; the last result is the answer. An inexact division is a miss."""
    def go(pool):
        if len(pool) == 1:
            return Fraction(int(pool[0] == target))
        tot, cnt = Fraction(0), 0
        for i, j in itertools.combinations(range(len(pool)), 2):
            rest = [pool[k] for k in range(len(pool)) if k not in (i, j)]
            for op in ARITH:
                for x, y in ((pool[i], pool[j]), (pool[j], pool[i])):
                    cnt += 1
                    v = apply(op, x, y)
                    tot += go(rest + [v]) if v is not None else 0
        return tot / cnt
    return float(go(list(nums)))


def uniform_floor(nums, target, n_samples=20000, seed=0):
    """Monte-Carlo per-try luck of a uniformly random B2 try judged by the C1 rules: 7 steps, each op uniform over B2's 9 ops, each operand
    uniform over the valid slots (given numbers, target, 4 constants, written results), answer uniform over valid slots."""
    from creative.checkers import rules_a
    rng = random.Random(seed)
    allnums = list(nums) + [target]
    hits = 0
    for _ in range(n_samples):
        valid = list(range(len(allnums))) + [16, 17, 18, 19]
        steps = []
        for s in range(7):
            op, a, b = rng.randrange(len(OPS)), rng.choice(valid), rng.choice(valid)
            steps.append((op, a, b))
            if op:
                valid.append(R0 + s)
        hits += rules_a(allnums, len(nums), Try.make(steps, rng.choice(valid)))[0]
    return hits / n_samples


def pass_at(p, k):
    return 1 - (1 - p) ** k


# ---- shared warm-up: B2 learns the format on 2-number puzzles with solver programs ----
def warmup_rows(n, seed=0):
    """n 2-number puzzles ("Numbers: A, B. Target: T. ...") with their solver program, each from its own number pair, T one exact operation of
    the pair under the C1 rules (T >= 1, not a constant, not a given number). -> [(row, Try)]. Ids 'mk:warmup:NNNN'."""
    pairs = sorted(itertools.combinations_with_replacement(POOL, 2), key=lambda s: _h('set2', seed, s))
    out = []
    for pr in pairs:
        if len(out) >= n:
            break
        opts = {}
        for op in ARITH:
            for x, y, a, b in ((pr[0], pr[1], 0, 1), (pr[1], pr[0], 1, 0)):
                v = apply(op, x, y)
                if v is not None and 1 <= v <= T_MAX and v not in CONSTS and v not in pr:
                    opts.setdefault(v, []).append(Try.make([(op, a, b)], R0))
        if not opts:
            continue
        rng = random.Random(_h('wtarget', seed, pr))
        T = rng.choice(sorted(opts))
        row = make_row(f'mk:warmup:{len(out):04d}', pr, T, 'warmup')
        out.append((row, rng.choice(opts[T])))
    assert len(out) == n, 'not enough 2-number puzzles'
    return out
