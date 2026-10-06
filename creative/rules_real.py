"""C2's real rule rows (roadmap section 7, built 10-06): single-input number rules in the skills data's own prompt format

    Examples: x1 -> y1; x2 -> y2; x3 -> y3. Now q -> ?

(the format of the skills family fewshot_number_rule; B2 trained on its variants add, mult and pair_sum with answers, and the skills split held out the variants
affine and pair_diff by hash). Kinds:
  practised (warm-up, solver programs):  add  y = x + B          mult  y = A*x
  held out (never in any warm-up):       affine y = A*x + B      square y = x*x       sq_plus y = x*x + B
                                         last_digit y = x mod 10  double_add y = (x + B)*2
`affine` is the skills split's own held-out variant; the other held-out kinds are not in the skills generator at all. pair_sum / pair_diff take two inputs and
need a two-input checker: not tested here.

REPRESENTABILITY FIRST: a (kind, parameters) instance is used only if a reference program over the input x and the four constants runs in B2's executor within 7
steps (breadth-first search on 6 canonical inputs, then verified on the whole input domain). Instances the search does not reach are listed in the manifest as
`not_shown_representable` (wall 4 candidates), never as proved unrepresentable. A kind is sealed only if it keeps at least one representable instance.

Questions: 3 examples + 1 query, inputs from 2..29, no prompt number equal to a constant slot (1, 2, 10, 100) as in C1, every output >= 0, and the examples must pin the
query: among ALL kinds and parameters above exactly one prediction fits (so a fitting program that answers differently is a real wrong program, not an ambiguity).
Splits are by (kind, parameters, examples, query): warm (practised kinds only, solver programs), dev (held-out kinds, the cold-start gate), pool (held-out kinds, the
sleep pool: no question shared with test), test (held-out kinds, sealed, never read before the C2b run), plus a larger `labelled` pool for the plain nets' k labelled
examples. The answer key sits in `answer` and is read only for scoring, the mechanism report and the plain nets."""
import hashlib, itertools, json, os, random
from creative.programs import R0, Try, apply, run
from creative import fewshot

DOMAIN = tuple(x for x in range(2, 30) if x not in (2, 10))          # no prompt number equals a constant slot (1, 2, 10, 100)
CANON = (3, 7, 12, 19, 24, 29)                                       # inputs of the representability search (5 examples + a query)
SALT = 'c2-real-v1'
PRACTISED = ('add', 'mult')
HELD_OUT = ('affine', 'square', 'sq_plus', 'last_digit', 'double_add')
PARAMS = dict(add=[(b,) for b in range(3, 31)], mult=[(a,) for a in range(3, 10)],
              affine=[(a, b) for a in range(3, 7) for b in range(3, 16)], square=[()], sq_plus=[(b,) for b in range(3, 10)],
              last_digit=[()], double_add=[(b,) for b in range(3, 10)])
SPLITS = dict(warm=2048, dev=256, pool=1024, test=512, labelled=512)
KIND_SEAL = hashlib.sha256(json.dumps(dict(practised=PRACTISED, held_out=HELD_OUT, params={k: v for k, v in PARAMS.items()}, domain=DOMAIN, salt=SALT),
                                      sort_keys=True).encode()).hexdigest()


def fn(kind, params):
    if kind == 'add': return lambda x: x + params[0]
    if kind == 'mult': return lambda x: params[0] * x
    if kind == 'affine': return lambda x: params[0] * x + params[1]
    if kind == 'square': return lambda x: x * x
    if kind == 'sq_plus': return lambda x: x * x + params[0]
    if kind == 'last_digit': return lambda x: x % 10
    if kind == 'double_add': return lambda x: (x + params[0]) * 2
    raise KeyError(kind)


ALL_RULES = [(k, p) for k in PRACTISED + HELD_OUT for p in PARAMS[k]]
_TABLE = {(k, p): tuple(fn(k, p)(x) for x in DOMAIN) for k, p in ALL_RULES}
_COL = {x: i for i, x in enumerate(DOMAIN)}


def predictions(xs, ys, q):
    """The set of distinct values at q over every rule (any kind, any parameters) that reproduces all examples."""
    out = set()
    for key, tab in _TABLE.items():
        if all(tab[_COL[x]] == y for x, y in zip(xs, ys)):
            out.add(tab[_COL[q]])
    return out


def prompt_of(xs, ys, q):
    return 'Examples: ' + '; '.join(f'{x} -> {y}' for x, y in zip(xs, ys)) + f'. Now {q} -> ?'


# ---- representability ----
_REF = {}


def _canon_row(kind, params):
    f = fn(kind, params)
    xs = list(CANON)
    ys = [f(x) for x in xs]
    return dict(id='canon', prompt=prompt_of(xs[:-1], ys[:-1], xs[-1]), answer=str(ys[-1]), accepted=[str(ys[-1])])


def reference(kind, params, max_states=600000):
    """-> (Try over the canonical row's query slot, number of written steps) or None (not shown representable within the search budget).
    The found program is checked on the whole input domain, so a lucky fit on six inputs is rejected."""
    key = (kind, params)
    if key not in _REF:
        row = _canon_row(kind, params)
        t = fewshot.find_reference(row, max_steps=7, max_states=max_states)
        res = None
        if t is not None:
            qs = fewshot.parse(row['prompt'])['q_slot']
            f = fn(kind, params)
            ok = True
            for x in DOMAIN:
                nums = [0] * qs + [x]
                vals, valid = run(nums, t)
                if not valid[t.ans] or vals[t.ans] != f(x):
                    ok = False
                    break
            if ok:
                res = (t, sum(1 for o in t.ops if o), qs)
        _REF[key] = res
    return _REF[key]


def remap(t, q_from, q_to):
    """The same program with its input slot moved (a question with a different number of examples has its query at another slot)."""
    return Try(t.ops, tuple(q_to if s == q_from else s for s in t.a), tuple(q_to if s == q_from else s for s in t.b), t.ans)


def representable_params(kinds, max_states=600000):
    """-> (usable {kind: [params]}, not_shown {kind: [params]}, steps {(kind, params): n})."""
    use, no, steps = {}, {}, {}
    for k in kinds:
        for p in PARAMS[k]:
            r = reference(k, p, max_states)
            if r is None:
                no.setdefault(k, []).append(p)
            else:
                use.setdefault(k, []).append(p)
                steps[(k, p)] = r[1]
    return use, no, steps


# ---- questions ----
def _hash(*parts):
    return hashlib.sha256('|'.join(map(str, (SALT,) + parts)).encode()).hexdigest()


def make_questions(kinds, usable, n, seed, tag, avoid=None, k_ex=3):
    """n distinct questions cycling over kinds and over each kind's usable parameters. `avoid` = set of (kind, params, examples, query) keys already used by another split."""
    rng = random.Random(f'{SALT}|{seed}|{tag}')
    avoid = avoid if avoid is not None else set()
    out, tries = [], 0
    while len(out) < n:
        tries += 1
        assert tries < 200 * n + 1000, f'cannot build {n} questions for {kinds} ({len(out)} so far)'
        kind = kinds[len(out) % len(kinds)]
        ps = usable.get(kind)
        if not ps:
            raise ValueError(f'kind {kind} has no representable instance')
        params = ps[rng.randrange(len(ps))]
        f = fn(kind, params)
        xs = rng.sample(DOMAIN, k_ex + 1)
        ys = [f(x) for x in xs]
        if min(ys) < 0 or any(y in (1, 2, 10, 100) for y in ys[:-1]):
            continue
        if predictions(xs[:-1], ys[:-1], xs[-1]) != {ys[-1]}:
            continue
        qk = (kind, params, tuple(xs[:-1]), xs[-1])
        if qk in avoid:
            continue
        avoid.add(qk)
        out.append(dict(id=f'c2:{tag}:{len(out):05d}', prompt=prompt_of(xs[:-1], ys[:-1], xs[-1]), answer=str(ys[-1]), accepted=[str(ys[-1])],
                        family='fewshot_number_rule', level=7, stage=9, variant='', steps=[], kind=kind, params=list(params), real=True))
    return out


def build_splits(seed=0, max_states=600000, sizes=None):
    """-> (splits {name: rows}, info dict with representability and counts). Held-out kinds with no representable instance are dropped and listed."""
    sizes = sizes or SPLITS
    use_p, no_p, st_p = representable_params(PRACTISED, max_states)
    use_h, no_h, st_h = representable_params(HELD_OUT, max_states)
    held = tuple(k for k in HELD_OUT if use_h.get(k))
    prac = tuple(k for k in PRACTISED if use_p.get(k))
    avoid, sp = set(), {}
    sp['warm'] = make_questions(prac, use_p, sizes['warm'], seed, 'warm', avoid)
    for name in ('dev', 'pool', 'test', 'labelled'):
        sp[name] = make_questions(held, use_h, sizes[name], seed, name, avoid)       # `avoid` is shared: no (rule, examples, query) triple crosses splits
    info = dict(practised=prac, held_out=held, dropped_kinds=[k for k in HELD_OUT if k not in held], not_shown_representable={k: v for k, v in {**no_p, **no_h}.items()},
                usable_counts={k: len(v) for k, v in {**use_p, **use_h}.items()}, ref_steps={f'{k}{p}': n for (k, p), n in {**st_p, **st_h}.items()},
                kind_seal=KIND_SEAL, sizes=sizes)
    return sp, info


def write_splits(out_dir, seed=0, max_states=600000):
    os.makedirs(out_dir, exist_ok=True)
    sp, info = build_splits(seed, max_states)
    man = {}
    for k, rows in sp.items():
        path = os.path.join(out_dir, f'{k}.jsonl')
        with open(path, 'w') as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True) + '\n')
        man[k] = dict(n=len(rows), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                      kinds={kd: sum(r['kind'] == kd for r in rows) for kd in sorted({r['kind'] for r in rows})})
    man['_spec'] = info
    json.dump(man, open(os.path.join(out_dir, 'MANIFEST.json'), 'w'), indent=1, sort_keys=True)
    return man


def load_split(out_dir, name):
    path = os.path.join(out_dir, f'{name}.jsonl')
    man = json.load(open(os.path.join(out_dir, 'MANIFEST.json')))
    assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == man[name]['sha256'], f'{name}: file does not match the sealed hash'
    return [json.loads(l) for l in open(path)]


def warm_records(rows, per_question=1, seed=0):
    """Solver-program training records for practised-kind questions: the kind's reference program (input slot moved to the question's own), answering with the
    program's own output (the same record form the C2 arms use)."""
    out = []
    for r in rows:
        assert r['kind'] in PRACTISED, 'warm-up only teaches practised kinds'
        t, _, qs = reference(r['kind'], tuple(r['params']))
        p = fewshot.parse(r['prompt'])
        out.append(fewshot._record(r, remap(t, qs, p['q_slot']), 'WU2', 0))
    return out
