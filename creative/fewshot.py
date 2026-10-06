"""C2 (roadmap section 7): rules from a few examples, checked by the prompt's own examples (no answer key).

C2a, the checker. A prompt like "12->48; 18->72. Now 10->?" holds example pairs (x_i -> y_i) and a query x_q. B2's pointers point at fixed prompt
slots, so a try is a program over the QUERY's input slot (the role "x"), the four constants and its own earlier results. To re-run it on example
i, slot x_q is re-bound to x_i; nothing in B2 changes. A try passes only if it reproduces EVERY example pair (and reads x at all); then its
output on the query is its answer. A pointer at any other prompt number (another example's x or y) has no role and is rejected.
Two independent executions: python ints (programs.run) and B2's torch executor (ledger.replay) over the examples as one batch.

C2b, the arms (sleep on held-out rule kinds, no answer keys): W = tries that fit every example (at most 2 distinct programs per question);
R = placebo, tries that follow the rules and run on every example but do NOT fit them all, matched count, separate pool;
H = R's tries relabelled with the rule each actually computes: the example outputs in the prompt are rewritten to f(x_i).
The training form is a forced program (slot ids) answering with its own output on the query: the answer key is never read.

The synthetic rule kinds below are a CPU smoke generator only. The real C2 rows are the skills data's fewshot_number_rule / rule_apply families,
parsed by the same parse(); sealing their held-out kinds by hash is a step of C2's own spec (sealed after C1's plumbing works)."""
import hashlib, json, random, re
from collections import Counter
from creative.programs import M, N_NUM, R0, Try, cone, leaves, register_targets, result_key, run, train_form

NUM = re.compile(r'\d+')
OPS_OK = (1, 2, 3, 4, 5, 6, 7, 8)          # B2's whole language except NOOP


def parse(prompt):
    """-> dict(xs, ys, q, q_slot, spans): numbers read in prompt order as (x1 y1 x2 y2 ... x_q); None if the shape is not pairs + one query."""
    ms = list(NUM.finditer(prompt))
    nums = [int(m.group()) for m in ms]
    if len(nums) < 3 or len(nums) % 2 == 0 or len(nums) > N_NUM:
        return None
    k = (len(nums) - 1) // 2
    return dict(xs=nums[0:2 * k:2], ys=nums[1:2 * k:2], q=nums[-1], q_slot=2 * k, nums=nums, spans=[m.span() for m in ms])


def structure(parsed, t):
    """Value-blind rules: the answer cone exists, reads the query's x, and points only at x, constants or earlier results. -> (ok, reason)."""
    if cone(t) is None:
        return False, 'no answer cone'
    q = parsed['q_slot']
    lv = leaves(t, t.ans)
    for s in cone(t):
        if t.ops[s] not in OPS_OK:
            return False, 'op not allowed'
    if any(x < N_NUM and x != q for x in lv):
        return False, 'points at a prompt number that is not the query input'
    if q not in lv:
        return False, 'never reads the input x'
    return True, 'ok'


def outputs_py(parsed, t):
    """Run the try with x re-bound to each example input, then on the query. -> [out_1.. out_k, out_q], None where the answer is not valid."""
    res = []
    for x in parsed['xs'] + [parsed['q']]:
        nums = list(parsed['nums'])
        nums[parsed['q_slot']] = x
        vals, valid = run(nums, t)
        res.append(vals[t.ans] if valid[t.ans] else None)
    return res


def outputs_torch(parsed, t):
    """The same with B2's exact torch executor, all rows as one batch."""
    import torch
    from custom_io.models.ledger import replay
    from creative.programs import CONSTS
    xs = parsed['xs'] + [parsed['q']]
    v0 = torch.zeros(len(xs), M, dtype=torch.long)
    ok0 = torch.zeros(len(xs), M, dtype=torch.bool)
    for r, x in enumerate(xs):
        nums = list(parsed['nums'])
        nums[parsed['q_slot']] = x
        for i, n in enumerate(nums):
            v0[r, i], ok0[r, i] = n, True
        for i, c in enumerate(CONSTS):
            v0[r, N_NUM + i], ok0[r, N_NUM + i] = c, True
    row = lambda xs_: torch.tensor([list(xs_)] * len(xs), dtype=torch.long)
    v, ok = replay(v0, ok0, row(t.ops), row(t.a), row(t.b))
    ok = ok.clone()
    for s in range(len(t.ops)):             # the torch executor reads 0 from an invalid slot; a result is valid only if its operands were
        ok[:, R0 + s] &= ok[:, t.a[s]] & ok[:, t.b[s]]
    return [int(v[r, t.ans]) if bool(ok[r, t.ans]) else None for r in range(len(xs))]


def verdict(parsed, t, rules_only=False):
    """-> (verdict, reason, answer). 'accept': structure ok and reproduces every example (both executors). 'reject' otherwise.
    'unresolved' (executors disagree, crash) counts as no hit. rules_only=True returns 'accept' for any structure-ok try that RUNS on every
    row (fit or not): what the R / H selection looks at (never whether it fits)."""
    try:
        ok, why = structure(parsed, t)
        if not ok:
            return 'reject', why, None
        a, b = outputs_py(parsed, t), outputs_torch(parsed, t)
        if a != b:
            return 'unresolved', 'executors disagree', None
        if any(o is None for o in a):
            return 'reject', 'does not run on every example', None
        if rules_only:
            return 'accept', 'runs', a[-1]
        if a[:-1] != parsed['ys']:
            return 'reject', 'does not reproduce every example', a[-1]
        return 'accept', 'ok', a[-1]
    except Exception as e:
        return 'unresolved', f'crash: {type(e).__name__}: {e}', None


def mechanism_report(rows, tries):
    """C2a mechanism mark: the example check agrees with the answer key on >= 99% of accepted tries. The key is read here, only to report.
    -> dict(accepted, agree, agreement, by_row_any_accepted)."""
    acc = agree = 0
    for row, tr in zip(rows, tries):
        p = parse(row['prompt'])
        for r in tr:
            v, _, ans = verdict(p, r.t)
            if v == 'accept':
                acc += 1
                agree += str(ans) in row['accepted']
    return dict(accepted=acc, agree=agree, agreement=agree / acc if acc else None, passes=bool(acc) and agree / acc >= 0.99)


def score_fewshot(rows, tries, raw=None):
    """Scoreboard on held-out kind questions: luck (share of kept tries that fit every example), reach@4 / @32, variety, key_luck (accepted AND
    equal to the key; reported, never selected on), unresolved. Shares are over kept (distinct) tries."""
    from creative.scoreboard import reach_at
    tot = Counter()
    per = []
    for i, row in enumerate(rows):
        p = parse(row['prompt'])
        vs = [verdict(p, r.t) for r in tries[i]]
        acc = [v[0] == 'accept' for v in vs]
        keyed = [a and str(v[2]) in row['accepted'] for a, v in zip(acc, vs)]
        keys = {result_key(r.t, run(p['nums'], r.t)[1]) for r in tries[i]} - {'dead'}
        rk = {result_key(r.t, run(p['nums'], r.t)[1]) for r in tries[i] if structure(p, r.t)[0]}
        per.append(dict(id=row['id'], m=len(acc), c=sum(acc), reach4=reach_at(sum(acc), len(acc), 4), reach32=float(any(acc)), distinct=len(keys), distinct_rules=len(rk),
                        key_c=sum(keyed)))
        tot.update(tries=len(acc), acc=sum(acc), keyed=sum(keyed), unres=sum(v[0] == 'unresolved' for v in vs), raw=raw[i] if raw else len(acc))
    n = max(len(rows), 1)
    return dict(n_questions=len(rows), n_tries=tot['tries'], luck=tot['acc'] / max(tot['tries'], 1), distinct_rules=sum(d['distinct_rules'] for d in per) / n, key_luck=tot['keyed'] / max(tot['tries'], 1),
                unresolved=tot['unres'] / max(tot['tries'], 1), reach4=sum(d['reach4'] for d in per) / n, reach32=sum(d['reach32'] for d in per) / n,
                distinct=sum(d['distinct'] for d in per) / n, per_question=per)


# ---- arms ----
def _record(row, t, arm, k, prompt=None):
    """Training record: the prompt (maybe with rewritten example outputs) answered by the try's own program run on the query."""
    tf = train_form(t)
    p = parse(row['prompt'] if prompt is None else prompt)
    steps, ans = tf
    rid = f'{arm}:{row["id"]}:{k}'
    vals = register_targets(rid, p['nums'], steps, ans)
    out = dict(row, id=rid, prompt=row['prompt'] if prompt is None else prompt, arm=arm, source=row['id'])
    out['answer'] = str(vals[-1])
    out['accepted'], out['steps'] = [out['answer']], []
    out.pop('kind', None)
    return out


def _distinct(row_p, tries, rng, n, want):
    """up to n structurally distinct tries whose verdict equals `want(v)`, chosen at random."""
    pool = [r.t for r in tries if want(verdict(row_p, r.t, rules_only=True), verdict(row_p, r.t))]
    rng.shuffle(pool)
    seen, out = set(), []
    for t in pool:
        key = result_key(t, run(row_p['nums'], t)[1])
        if key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) == n:
            break
    return out


def relabel_prompt(prompt, parsed, t):
    """Hindsight: rewrite the example outputs to f(x_i), where f is what the try computes. None if f is invalid / negative / too long."""
    outs = outputs_py(parsed, t)
    if any(o is None or o < 0 or o > 9999 for o in outs[:-1]) or outs[-1] is None or outs[-1] < 0:
        return None
    new, last = [], 0
    for k, (s, e) in enumerate(parsed['spans']):
        new.append(prompt[last:s])
        new.append(str(outs[k // 2]) if (k % 2 == 1 and k < len(parsed['spans']) - 1) else prompt[s:e])
        last = e
    new.append(prompt[last:])
    return ''.join(new)


def build_arms(rows, tries, pool_tries, seed=0, per_cap=2):
    """C2b arms for one parent. rows = held-out-kind practice questions; tries[i] = main-pool TryRecs for rows[i]; pool_tries = separate pool.
    -> dict(N=[], W, R, H, counts, diag). R and H share the same tries; all counts match W's."""
    rng = random.Random(seed)
    W, counts = [], {}
    for row, tr in zip(rows, tries):
        p = parse(row['prompt'])
        kept = _distinct(p, tr, rng, per_cap, lambda rules, full: full[0] == 'accept')
        for k, t in enumerate(kept):
            W.append(_record(row, t, 'W', k))
        if kept:
            counts[row['id']] = len(kept)
    R, H, n_fit = [], [], 0
    short = {}
    for row, tr in zip(rows, pool_tries):
        n = counts.get(row['id'], 0)
        if not n:
            continue
        p = parse(row['prompt'])
        # R: runs on every row but does not fit all examples; relabelable so H can use the same tries (relabel validity ignores the key)
        pick = _distinct(p, tr, rng, 10 ** 6, lambda rules, full: rules[0] == 'accept' and full[0] == 'reject')
        pick = [t for t in pick if relabel_prompt(row['prompt'], p, t) is not None][:n]
        if len(pick) < n:
            short[row['id']] = n - len(pick)
        for k, t in enumerate(pick):
            R.append(_record(row, t, 'R', k))
            H.append(_record(row, t, 'H', k, prompt=relabel_prompt(row['prompt'], p, t)))
    for r in H:
        pp_ = parse(r['prompt'])
        t = _recover(r)
        n_fit += verdict(pp_, t)[0] == 'accept'
    return dict(N=[], W=W, R=R, H=H, counts=counts,
                diag=dict(n_W=len(W), n_R=len(R), short=short, hindsight_fits=n_fit / max(len(H), 1)))


def _recover(r):
    from custom_io.models import progparse as pp
    c = pp._CACHE[r['id']]
    return Try.make([(o, ca[0], cb[0]) for o, ca, cb, _ in c['prog']], c['ans'][0])


def record_try(r):
    return _recover(r)


# ---- representability, floor and DEV gates (roadmap section 7, revised 10-06) ----
SEARCH_OPS = (1, 2, 3, 4, 5, 6, 7)          # ADD SUB MUL DIV MOD MIN MAX (CMP only gives -1/0/1: left out of the reference search)


def find_reference(row, max_steps=7, max_states=200000):
    """Offline seal-time check (reads the key): breadth-first search for a program over the input x and the constants, at most max_steps steps,
    that reproduces every example AND the key on the query. States are the vectors of values over (examples + query), so equal functions are
    merged. -> Try or None (None = not found within the budget: reported as 'not shown representable', never as proved unrepresentable)."""
    from creative.programs import CONSTS, apply
    p = parse(row['prompt'])
    xs = p['xs'] + [p['q']]
    target = tuple(p['ys']) + (int(row['answer']),)
    # slot -> value vector; slot ids as in B2: x = q_slot, constants 16..19, result s -> R0 + s
    base = {p['q_slot']: tuple(xs)}
    for i, c in enumerate(CONSTS):
        base[N_NUM + i] = (c,) * len(xs)
    if target in base.values():
        return None
    frontier = [((), dict(base))]
    seen = {v for v in base.values()}
    for depth in range(max_steps):
        nxt = []
        for steps, slots in frontier:
            items = list(slots.items())
            for sa, va in items:
                for sb, vb in items:
                    for op in SEARCH_OPS:
                        out = tuple(apply(op, x, y) for x, y in zip(va, vb))
                        if None in out or out in seen:
                            continue
                        seen.add(out)
                        ns = dict(slots)
                        ns[R0 + len(steps)] = out
                        st = steps + ((op, sa, sb),)
                        if out == target:
                            return Try.make(list(st), R0 + len(steps))
                        nxt.append((st, ns))
                        if len(seen) > max_states:
                            return None
        frontier = nxt
    return None


def representability(rows, max_steps=7, max_states=200000):
    """Per held-out kind: the share of its questions with a reference program within max_steps in B2's executor, and the step counts. A kind is
    SEALED only if every sampled question has one (roadmap: 'sealed only if its reference program runs in B2's executor within 7 steps');
    otherwise it is listed as wall 4 and not tested. -> {kind: dict(n, found, steps, sealed)}."""
    out = {}
    for r in rows:
        d = out.setdefault(r['kind'], dict(n=0, found=0, steps=[]))
        d['n'] += 1
        t = find_reference(r, max_steps, max_states)
        if t is not None and verdict(parse(r['prompt']), t)[0] == 'accept' and str(verdict(parse(r['prompt']), t)[2]) in r['accepted']:
            d['found'] += 1
            d['steps'].append(sum(1 for o in t.ops if o))
    for d in out.values():
        d['sealed'] = d['found'] == d['n']
    return out


def value_blind_floor(row, n_samples=20000, seed=0, max_len=4):
    """Per-try chance that a RANDOM program over the input and the constants fits every example by luck (value-blind: nothing looks at the examples
    when it is drawn). Length uniform 1..max_len; each step an op from SEARCH_OPS and two operands uniform over x, the four constants and earlier
    results; the answer is the last result. Monte Carlo; the program must read x and run on every row, exactly as the checker demands."""
    import random
    rng = random.Random(seed)
    p = parse(row['prompt'])
    hits = 0
    for _ in range(n_samples):
        L = rng.randint(1, max_len)
        slots = [p['q_slot'], 16, 17, 18, 19]
        steps = []
        for s in range(L):
            steps.append((rng.choice(SEARCH_OPS), rng.choice(slots), rng.choice(slots)))
            slots.append(R0 + s)
        t = Try.make(steps, R0 + L - 1)
        hits += verdict(p, t)[0] == 'accept'
    return hits / n_samples


GATE_REACH32_MIN, GATE_FLOOR_MULT, GATE_SAMENESS_MIN = 0.10, 3.0, 4.0


def dev_gate(rows, tries, floors, raw=None):
    """C2 DEV gates. cold start: an accepted try within 32 on >= 10% of questions AND >= 3x the value-blind floor (floors[i] = per-try floor of
    question i; the floor's own reach@32 = mean of 1 - (1 - p)^32); sameness: >= 4 distinct rule-following programs per question.
    If cold start fails: stepping stones first (C6's form on these kinds)."""
    s = score_fewshot(rows, tries, raw)
    floor32 = sum(1 - (1 - p) ** 32 for p in floors) / len(floors)
    cold = s['reach32'] >= GATE_REACH32_MIN and s['reach32'] >= GATE_FLOOR_MULT * floor32
    same = s['distinct_rules'] >= GATE_SAMENESS_MIN
    v = 'pass' if cold and same else ('stop: cold start and sameness' if not cold and not same else
                                       'stop: cold start (stepping stones first)' if not cold else 'stop: sameness (C3b first)')
    return dict(cold_start_ok=cold, sameness_ok=same, verdict=v, reach32=s['reach32'], floor_reach32=floor32, reach4=s['reach4'], luck=s['luck'],
                distinct_rules=s['distinct_rules'], unresolved=s['unresolved'])


# ---- comparison nets' labelled data ----
def labelled_sets(pool_rows, ks=(0, 8, 32, 128), seed=0):
    """Nested sets of k labelled examples (k in ks) drawn from a held-out-kind pool disjoint from the test questions: the plain nets' side of
    'examples to learn'. -> {k: [rows]}; each set contains the smaller ones."""
    order = list(pool_rows)
    random.Random(seed).shuffle(order)
    assert len(order) >= max(ks), 'pool too small'
    return {k: order[:k] for k in ks}


# ---- synthetic rule kinds (CPU smoke only) ----
PRACTISED = ('add', 'sub', 'mul')
HELD_OUT = ('affine', 'square', 'add_double')
KIND_SEAL = hashlib.sha256(json.dumps(dict(practised=PRACTISED, held_out=HELD_OUT), sort_keys=True).encode()).hexdigest()


def _rule(kind, rng):
    k, j = rng.randint(2, 5), rng.randint(1, 9)
    return {'add': lambda x: x + j, 'sub': lambda x: x - j, 'mul': lambda x: x * k, 'affine': lambda x: k * x + j,
            'square': lambda x: x * x, 'add_double': lambda x: (x + j) * 2}[kind]


def make_rows(kinds, n, seed=0, tag='syn'):
    """Synthetic few-example questions 'a->b; c->d. Now e->?' (key in 'answer', used only for scoring and for the plain nets). CPU smoke only."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        kind = kinds[len(out) % len(kinds)]
        f = _rule(kind, rng)
        xs = rng.sample(range(11, 41), rng.choice([3, 3, 4]))
        ys = [f(x) for x in xs]
        if min(ys) < 0 or max(ys) > 999:
            continue
        ex = '; '.join(f'{x}->{y}' for x, y in zip(xs[:-1], ys[:-1]))
        out.append(dict(id=f'{tag}:{seed}:{len(out):05d}', prompt=f'{ex}. Now {xs[-1]}->?', answer=str(ys[-1]), accepted=[str(ys[-1])],
                        family='fewshot_number_rule', level=7, stage=9, variant='', steps=[], kind=kind, synthetic=True))
    return out
