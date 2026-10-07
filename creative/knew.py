"""K_new (roadmap 7d): ten pre-registered NEW rule kinds, four of which become the transfer set for the creative-part screens. CPU.
  python3 -m creative.knew --nprime A.pt B.pt --out creative/data/knew [--workers 2]
Candidates, in this fixed order (fn over int x): 1 sq_minus x*x-B (B 3..9); 2 triple_add (x+B)*3 (B 3..9); 3 mult_sub A*x-B (A 3..6, B 3..15); 4 sq_plus_x x*x+x; 5 double_sq 2*x*x;
6 sub_from B-x (B 30..45); 7 cube x*x*x; 8 mod_plus (x mod 10)+B (B 3..9); 9 add_sq (x+B)*(x+B) (B 3..9); 10 sq_mod (x*x) mod 10.
Questions are rules_real.make_questions' own format and filters (3 examples + query, DOMAIN inputs, outputs >= 0, no example output in {1, 2, 10, 100}) and the examples must pin the query among
ALL rules: rules_real.ALL_RULES (C2 + practised), stones.SS_PARAMS (mod and the other stepping stones) and every candidate's parameters. Salt 'knew-v1', seed 0; DEV = 64 per candidate (tag kdev).
A candidate qualifies when ALL THREE hold on its DEV: (a) representable: a reference program within 7 steps (fewshot.find_reference on a canonical row, checked on the whole DOMAIN; parameters
not shown representable are dropped, a kind with none is dropped); (b) blind search with the checker (blind_baseline.search_fits, BFS) at the test's guess budget: a fitting candidate among the first 32 candidates
examined on <= 20% of its DEV questions (the roadmap's rule for finding tests: blind search with the checker fails at the test's guess budget; S1 gives
the model 32 tries). --blind-rule fits applies blind_baseline's other reading (right within the first 32 FITTING candidates of 50,000 examined), under
which no candidate qualifies (10-07: 34-100%); both numbers are always reported; (c) the parent N' (untrained adapter = N' itself) at T 3.0, 32 plain samples (legal.raw_samples): reach@32 (a fitting try whose answer is in `accepted`; the key only scores)
between 2% and 40% on BOTH parents. The first four in list order that qualify are K_new; fewer than four = report and stop. Writes (dev.jsonl: the four kinds' DEV, 256 rows; test.jsonl: 128 per kind,
tag ktest, avoiding every DEV key, GENERATED AND WRITTEN ONLY: its sha256 is taken from the bytes written and nothing here ever reads it back or scores it; MANIFEST.json; report.json; candidates_dev.jsonl)."""
import argparse, hashlib, json, os, random, time
from concurrent.futures import ProcessPoolExecutor
from creative import blind_baseline, fewshot, rules_real as R, stones
from creative import programs

SALT = 'knew-v1'
DOMAIN, _COL = R.DOMAIN, R._COL
CAND = ('sq_minus', 'triple_add', 'mult_sub', 'sq_plus_x', 'double_sq', 'sub_from', 'cube', 'mod_plus', 'add_sq', 'sq_mod')
PARAMS = dict(sq_minus=[(b,) for b in range(3, 10)], triple_add=[(b,) for b in range(3, 10)], mult_sub=[(a, b) for a in range(3, 7) for b in range(3, 16)], sq_plus_x=[()],
              double_sq=[()], sub_from=[(b,) for b in range(30, 46)], cube=[()], mod_plus=[(b,) for b in range(3, 10)], add_sq=[(b,) for b in range(3, 10)], sq_mod=[()])
N_DEV, N_TEST, N_PICK = 64, 128, 4
BLIND_MAX, REACH_LO, REACH_HI, T_POOL, N_SAMPLES = 0.20, 0.02, 0.40, 3.0, 32
BLIND_GUESSES = 32
RULES = dict(examined='(b) blind search with the checker fits within the first 32 candidates examined on <= 20% of DEV',
             fits='(b) blind search right within the first 32 fitting candidates (50,000 examined) on <= 20% of DEV')
RULE = ('first 4 candidates in list order with (a) a representable parameter, %s, (c) N\' creative-mode reach@32 in [2%%, 40%%] on both parents')


def fn(kind, p):
    if kind == 'sq_minus': return lambda x: x * x - p[0]
    if kind == 'triple_add': return lambda x: (x + p[0]) * 3
    if kind == 'mult_sub': return lambda x: p[0] * x - p[1]
    if kind == 'sq_plus_x': return lambda x: x * x + x
    if kind == 'double_sq': return lambda x: 2 * x * x
    if kind == 'sub_from': return lambda x: p[0] - x
    if kind == 'cube': return lambda x: x * x * x
    if kind == 'mod_plus': return lambda x: x % 10 + p[0]
    if kind == 'add_sq': return lambda x: (x + p[0]) * (x + p[0])
    if kind == 'sq_mod': return lambda x: x * x % 10
    raise KeyError(kind)


_CANDS = [(k, p) for k in CAND for p in PARAMS[k]]
_TABS = (list(R._TABLE.values()) + [tuple(R.fn(k, p)(x) for x in DOMAIN) for k, ps in stones.SS_PARAMS.items() for p in ps]
         + [tuple(fn(k, p)(x) for x in DOMAIN) for k, p in _CANDS])


def predictions(xs, ys, q):
    """The distinct values at q over every known rule (C2 + practised, stepping stones, every candidate) that reproduces all examples."""
    return {tab[_COL[q]] for tab in _TABS if all(tab[_COL[x]] == y for x, y in zip(xs, ys))}


def candidates_hash():
    return hashlib.sha256(json.dumps(dict(kinds=CAND, params=PARAMS, salt=SALT), sort_keys=True).encode()).hexdigest()


# ---- (a) representability
def reference(kind, params, max_states=600000):
    """-> (Try over the canonical row's query slot, written steps, query slot) or None (not shown representable within the search budget). Checked on the whole DOMAIN."""
    f = fn(kind, params)
    xs = list(R.CANON)
    ys = [f(x) for x in xs]
    row = dict(id='canon', prompt=R.prompt_of(xs[:-1], ys[:-1], xs[-1]), answer=str(ys[-1]), accepted=[str(ys[-1])])
    t = fewshot.find_reference(row, max_steps=7, max_states=max_states)
    if t is None:
        return None
    qs = fewshot.parse(row['prompt'])['q_slot']
    for x in DOMAIN:
        vals, valid = programs.run([0] * qs + [x], t)
        if not valid[t.ans] or vals[t.ans] != f(x):
            return None
    return t, sum(1 for o in t.ops if o), qs


def _ref_job(kp):
    r = reference(*kp)
    return kp, (r[1] if r else None)


def representable(workers=2, limit_kinds=None):
    """-> {kind: {params: written steps or None}} over every candidate parameter."""
    jobs = [kp for kp in _CANDS if limit_kinds is None or kp[0] in limit_kinds]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            res = list(ex.map(_ref_job, jobs, chunksize=1))
    else:
        res = [_ref_job(j) for j in jobs]
    out = {}
    for (k, p), s in res:
        out.setdefault(k, {})[p] = s
    return out


# ---- questions
def make_questions(kind, usable, n, tag, avoid, idx0=0, seed=0, k_ex=3):
    """n distinct questions of one candidate kind over its usable parameters (rules_real.make_questions' format and filters; uniqueness against every known rule).
    `avoid` = keys (kind, params, examples, query) already used (updated). Ids knew:<tag>:<idx0 + i>."""
    rng = random.Random(f'{SALT}|{seed}|{tag}|{kind}')
    out, tries = [], 0
    while len(out) < n:
        tries += 1
        assert tries < 200 * n + 1000, f'cannot build {n} questions for {kind} ({len(out)} so far)'
        params = usable[rng.randrange(len(usable))]
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
        out.append(dict(id=f'knew:{tag}:{idx0 + len(out):05d}', prompt=R.prompt_of(xs[:-1], ys[:-1], xs[-1]), answer=str(ys[-1]), accepted=[str(ys[-1])],
                        family='fewshot_number_rule', level=7, stage=9, variant='', steps=[], kind=kind, params=list(params), knew=True))
    return out


def _interleave(by_kind, kinds):
    """Rows of several kinds, one of each kind in turn (kinds in the given order)."""
    return [by_kind[k][j] for j in range(max(len(by_kind[k]) for k in kinds)) for k in kinds if j < len(by_kind[k])]


# ---- (b) blind search
def blind_conditions(rows, workers=2, cache=None):
    """Blind BFS per DEV row (cached by id). -> blind_baseline.summarize(rows, fits)."""
    c = json.load(open(cache)) if cache and os.path.exists(cache) else {}
    todo = [r for r in rows if r['id'] not in c]
    if todo:
        if workers > 1:
            with ProcessPoolExecutor(workers) as ex:
                got = list(ex.map(blind_baseline._one, todo, chunksize=4))
        else:
            got = [blind_baseline._one(r) for r in todo]
        c.update({r['id']: g for r, g in zip(todo, got)})
        if cache:
            json.dump(c, open(cache, 'w'))
    fits = [c[r['id']] for r in rows]
    out = blind_baseline.summarize(rows, fits)
    for k in out['by_kind']:
        ix = [i for i, r in enumerate(rows) if r['kind'] == k]
        out['by_kind'][k]['fit_within_32_examined'] = sum(any(e <= BLIND_GUESSES for e, _ in fits[i]) for i in ix) / len(ix)
        out['by_kind'][k]['right_within_32_examined'] = sum(any(e <= BLIND_GUESSES and ok for e, ok in fits[i]) for i in ix) / len(ix)
        first = sorted(next((e for e, ok in fits[i] if ok), None) for i in ix if any(ok for _, ok in fits[i]))
        out['by_kind'][k]['examined_to_first_right'] = dict(share_with_right_fit=len(first) / len(ix), median=first[len(first) // 2] if first else None,
                                                          mean=sum(first) / len(first) if first else None, min=first[0] if first else None, max=first[-1] if first else None)
    return out


# ---- (c) the parents in creative mode (untrained adapter = N' itself)
def parent_reach(nprime, rows, T=T_POOL, n=N_SAMPLES, seed=0, device='cpu'):
    """N' at T, n plain samples per row (legal.raw_samples): per kind reach@32 = a fitting try whose answer is in `accepted`. -> {kind: dict(n, reach32, fit32)}."""
    from creative import c2_stones, legal, sleep, sleep7d
    m, vocab, _ = sleep.load_parent(nprime, device)
    m.eval()
    rows = c2_stones._with_nums(rows)
    smp = legal.raw_samples(m, rows, vocab, device, n=n, temperature=T, level=0, seed=seed)
    per = sleep7d.score_rows(rows, smp)
    return {k: dict(n=len(q), reach32=sum(d['right'] for d in q) / len(q), fit32=sum(d['fit'] for d in q) / len(q))
            for k in sorted({r['kind'] for r in rows}) for q in [[d for d in per if d['kind'] == k]]}


# ---- writing and loading
def _dump(rows):
    return ''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows).encode()


def _write(path, rows):
    """Write rows; -> sha256 of the bytes WRITTEN (never read back)."""
    b = _dump(rows)
    with open(path, 'wb') as f:
        f.write(b)
    return hashlib.sha256(b).hexdigest()


def load_dev(out_dir):
    """K_new DEV rows, checked against the sealed hash in MANIFEST.json. The test file is never opened here (nor anywhere in this package)."""
    man = json.load(open(os.path.join(out_dir, 'MANIFEST.json')))
    raw = open(os.path.join(out_dir, 'dev.jsonl'), 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == man['dev']['sha256'], 'knew dev: does not match the sealed hash'
    return [json.loads(l) for l in raw.decode().splitlines()]


def write_data(out_dir, chosen, usable, dev_by_kind, cond, rule, nprime=None, smoke=False):
    """dev.jsonl (the chosen kinds' DEV, interleaved), test.jsonl (N_TEST per kind, avoiding every candidate DEV key), MANIFEST.json. -> manifest dict."""
    os.makedirs(out_dir, exist_ok=True)
    dev = _interleave(dev_by_kind, chosen)
    avoid = {(r['kind'], tuple(r['params']), tuple(fewshot.parse(r['prompt'])['xs']), fewshot.parse(r['prompt'])['q']) for rows in dev_by_kind.values() for r in rows}
    test_by = {k: make_questions(k, usable[k], N_TEST, 'ktest', avoid, idx0=i * N_TEST) for i, k in enumerate(chosen)}
    test = _interleave(test_by, chosen)
    man = dict(dev=dict(n=len(dev), sha256=_write(os.path.join(out_dir, 'dev.jsonl'), dev), kinds={k: sum(r['kind'] == k for r in dev) for k in chosen}),
               test=dict(n=len(test), sha256=_write(os.path.join(out_dir, 'test.jsonl'), test), kinds={k: len(test_by[k]) for k in chosen},
                         note='generated and written only; never read back or scored by anything in creative/knew.py or creative/sleep7d.py'))
    params = {k: [list(p) for p in usable[k]] for k in chosen}
    man['_spec'] = dict(kinds=list(chosen), params=params, salt=SALT, seed=0, rule=rule, smoke=smoke, nprime=nprime,
                        kind_hash=hashlib.sha256(json.dumps(dict(kinds=list(chosen), params=params, salt=SALT), sort_keys=True).encode()).hexdigest(),
                        candidates_hash=candidates_hash(), conditions=cond)
    json.dump(man, open(os.path.join(out_dir, 'MANIFEST.json'), 'w'), indent=1, sort_keys=True)
    return man


def run_conditions(out, nprimes=(), workers=2, limit=None, log=None, device='cpu', blind_rule='examined'):
    """All ten candidates: DEV rows, (a), (b), (c). -> (cond {kind: dict}, usable {kind: [params]}, dev_by_kind). Caches (a) and (b) in `out`."""
    log = log or (lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True))
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    ac = os.path.join(out, 'cache_a.json')
    if os.path.exists(ac):
        rep = {k: {tuple(p): s for p, s in v} for k, v in json.load(open(ac)).items()}
    else:
        rep = representable(workers)
        json.dump({k: [[list(p), s] for p, s in v.items()] for k, v in rep.items()}, open(ac, 'w'))
    log('(a) representability', {k: f'{sum(s is not None for s in v.values())}/{len(v)}' for k, v in rep.items()}, round(time.time() - t0))
    usable = {k: [p for p in PARAMS[k] if rep.get(k, {}).get(p) is not None] for k in CAND}
    avoid, dev_by_kind = set(), {}
    for i, k in enumerate(CAND):
        if usable[k]:
            dev_by_kind[k] = make_questions(k, usable[k], N_DEV, 'kdev', avoid, idx0=i * N_DEV)
    cond = {}
    for k in CAND:
        steps = [s for s in rep.get(k, {}).values() if s is not None]
        cond[k] = dict(params=len(PARAMS[k]), usable_params=len(usable[k]), max_ref_steps=max(steps) if steps else None, dev_questions=len(dev_by_kind.get(k, [])),
                       a=dict(passes=bool(usable[k]), representable_params=f'{len(usable[k])}/{len(PARAMS[k])}'))
    t0 = time.time()
    use_rows = [r for k in CAND for r in dev_by_kind.get(k, [])[:limit]]
    bsum = blind_conditions(use_rows, workers, os.path.join(out, 'cache_b.json') if not limit else None)
    for k in dev_by_kind:
        b = bsum['by_kind'][k]
        key = 'fit_within_32_examined' if blind_rule == 'examined' else 'right_within_32_guesses'
        cond[k]['b'] = dict(passes=b[key] <= BLIND_MAX, rule=RULES[blind_rule], **b)
    log('(b) blind search', blind_rule, {k: (round(cond[k]['b']['fit_within_32_examined'], 3), round(cond[k]['b']['right_within_32_guesses'], 3)) for k in dev_by_kind},
        '(fit within 32 examined, right within 32 fitting)', round(time.time() - t0))
    for p in nprimes:
        t0 = time.time()
        pr = parent_reach(p, use_rows, device=device)
        for k, v in pr.items():
            cond[k].setdefault('c', dict(parents={}))['parents'][p] = v
        log('(c) reach@32', p, {k: round(v['reach32'], 3) for k, v in pr.items()}, round(time.time() - t0))
    for k in CAND:
        c = cond[k].get('c')
        if c:
            c['passes'] = len(c['parents']) == len(nprimes) and all(REACH_LO <= v['reach32'] <= REACH_HI for v in c['parents'].values())
        cond[k]['qualifies'] = all(cond[k].get(x, {}).get('passes') for x in 'abc')
    return cond, usable, dev_by_kind


def run(out, nprimes=(), workers=2, limit=None, force=None, log=None, device='cpu', blind_rule='examined'):
    log = log or (lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True))
    cond, usable, dev_by_kind = run_conditions(out, nprimes, workers, limit, log, device, blind_rule)
    rule_text = RULE % RULES[blind_rule]
    with open(os.path.join(out, 'candidates_dev.jsonl'), 'w') as f:
        for k in CAND:
            for r in dev_by_kind.get(k, []):
                f.write(json.dumps(r, sort_keys=True) + '\n')
    rep = dict(spec=__doc__.split('\n')[0], rule=rule_text, blind_rule=blind_rule, salt=SALT, candidates_hash=candidates_hash(), nprime=list(nprimes), limit=limit, conditions=cond,
               note='conditions (b) and (c) are over the first `limit` DEV questions per kind when limit is set (smoke); nothing is written then' if limit else '')
    qual = [k for k in CAND if cond[k]['qualifies']]
    rep['qualifying'] = qual
    if force:
        chosen, rule, smoke = list(force), 'FORCED kinds (smoke only: conditions not applied)', True
    else:
        chosen, rule, smoke = qual[:N_PICK], rule_text, False
    rep['chosen'] = chosen
    if limit or (not force and (not nprimes or len(qual) < N_PICK)):
        rep['status'] = ('smoke on a slice: nothing written' if limit else 'conditions (c) not run: nothing written' if not nprimes else
                         f'only {len(qual)} candidate(s) qualify: report and stop')
        json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1, sort_keys=True)
        log('STATUS', rep['status'], 'qualifying', qual)
        return rep
    assert all(k in dev_by_kind for k in chosen), 'a forced kind has no representable parameter'
    man = write_data(out, chosen, usable, dev_by_kind, cond, rule, list(nprimes), smoke)
    rep['status'] = 'written'
    rep['manifest'] = {k: man[k] for k in ('dev', 'test')}
    json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1, sort_keys=True)
    log('WRITTEN', chosen, rep['manifest'])
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--nprime', nargs='*', default=[], help='the two N\' checkpoints for condition (c)'); a.add_argument('--out', required=True)
    a.add_argument('--workers', type=int, default=2); a.add_argument('--limit', type=int, help='smoke: conditions on the first N DEV questions per kind, write nothing')
    a.add_argument('--force-kinds', help='SMOKE ONLY: comma list of kinds to write without the conditions (the MANIFEST says so)'); a.add_argument('--threads', type=int)
    a.add_argument('--blind-rule', choices=sorted(RULES), default='examined', help='reading of condition (b); both numbers are always reported')
    a = a.parse_args()
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    run(a.out, tuple(os.path.expanduser(p) for p in a.nprime), a.workers, a.limit, a.force_kinds.split(',') if a.force_kinds else None, blind_rule=a.blind_rule)
