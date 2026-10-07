"""C2b, the real run (roadmap sec. 7, "Decided (10-07): the real C2b goes ahead"). CPU. Two commands:

  train  python3 -m creative.c2b train --ckpt B2_s200.pt --out ROOT/s200 --skills-train train.jsonl --skills-data data_big [--warmed warm.pt]
         one parent, resumable (every stage writes its files; a re-run skips what exists). DEV is used ONLY to pick the pool temperature; the sealed test split is not opened here.
  score  python3 -m creative.c2b score --root ROOT --skills-train train.jsonl --skills-data data_big
         opens the sealed test split ONCE, only if all 6 parents x 4 arms (+ N') exist under ROOT/s200..s205; refuses otherwise, and refuses a second time once REPORT.json exists.
  check  python3 -m creative.c2b check --root ROOT          (what is missing, nothing opened)

PER PARENT (B2 s200..s205): raw B2 -> warm-up (2,048 warm add/mult rows, 4 visits, lr 3e-4, skills replay, seed 0; = fast-sleep's warm.pt) -> N' (stepping-stone sleep with add/mult
replay, exactly job 7) -> pool temperature T = job 6's rule on DEV for N' (best reach@32 among temperatures passing sameness).
ARMS, two nights each, on the 1,024 pool questions; night 2 samples with the arm's own night-1 model; dose lr 1e-3 x 32 visits, updates = 32 x W's records / 32, half of every batch is
replay (16 skills + 16 warm add/mult), the same updates for W, R and H:
  W  job 8's search (32 tries, then 480 more where no try fits), <= 2 distinct example-fitting tries per question.
  R  same questions and the same number of records per question as W's that night, tries that FAIL the example check, from the model's own 32 pass-1 tries; no pass 2.
  H  R's tries relabelled with what they compute on the shown examples.
  M  (reported) N' + memory of W's night-1 records + 512 old notes, answer note off, chain-5 harm guard each night (fastsleep.nightly_recall, PR #48). Night 2 samples with M's
     night-1 model and adds its hits to the memory. The weights of M never change.
No answer key and no rule-kind label touches an arm's records, the search or the allocation (tests/test_c2b.py corrupts every key and scrambles every kind and demands identical records).
MEASURED on the sealed test split (512) for N', W, R, H, M after night 2: greedy first try (fits and right) per kind and pooled; reach@4, reach@32 (32 plain samples with repeats at T);
practised check (256 fresh add/mult, reach@32 at T 1.0); skills harm (pooled-5 vs N'). Intervals: paired bootstrap over questions within parents, pooled over the 6 parents.
The json carries numbers and per-parent readings only; the roadmap thread gives the verdict."""
import argparse, copy, json, math, os, random, time
import numpy as np
import torch
from creative import c2_dev, c2_pilot, c2_stones, c2_stuck, fastsleep, fewshot, legal, rules_real as R, sleep, stones
from creative.c2_keep import MULTI
from creative.pilot import skills_eval
from custom_io.models import progparse as pp

DATA = 'creative/data/c2'
PARENTS = ('s200', 's201', 's202', 's203', 's204', 's205')
ARMS = ('W', 'R', 'H', 'M')
T_GRID = c2_pilot.TEMPS
LR, VISITS = 1e-3, 32
N1, N2 = 32, 480
FILES = ('setup.json', 'Nprime.pt', 'W2.pt', 'R2.pt', 'H2.pt', 'M_final.pt', 'complete.json')
log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)


# ------------------------------------------------------------------ records (saved with their target cache, so a re-run can reload them)
def save_recs(path, recs, **extra):
    torch.save(dict(records=recs, cache={r['id']: pp._CACHE[r['id']] for r in recs}, **extra), path)


def load_recs(path):
    d = torch.load(path, weights_only=False)
    pp._CACHE.update(d['cache'])
    return d


def failing_records(pool, tries, counts, seed, night):
    """R and H for one night. tries[i] = the model's own pass-1 TryRecs for pool[i]; counts[id] = W's record count for that question that night. R = distinct tries that run on
    every example but do not fit them all (and can be relabelled), up to the count; H = the same tries with the example outputs rewritten to what each computes. Reads no key and no kind.
    -> (R, H, short) with short[id] = how many records were missing."""
    rng = random.Random(seed)
    Rr, Hh, short = [], [], {}
    for row, tr in zip(pool, tries):
        n = counts.get(row['id'], 0)
        if not n:
            continue
        p = fewshot.parse(row['prompt'])
        pick = fewshot._distinct(p, tr, rng, 10 ** 6, lambda rules, full: rules[0] == 'accept' and full[0] == 'reject')
        pick = [t for t in pick if fewshot.relabel_prompt(row['prompt'], p, t) is not None][:n]
        if len(pick) < n:
            short[row['id']] = n - len(pick)
        for k, t in enumerate(pick):
            Rr.append(fewshot._record(row, t, f'R{night}', k))
            Hh.append(fewshot._record(row, t, f'H{night}', k, prompt=fewshot.relabel_prompt(row['prompt'], p, t)))
    return Rr, Hh, short


def night_info(pool, drawn, recs, counts, fit1=None, fit=None):
    """Reporting only (kind labels are read here, never by the search or the records)."""
    kind_of = {r['id']: r['kind'] for r in pool}
    kinds = sorted(set(kind_of.values()))
    by_kind = {k: sum(c for i, c in counts.items() if kind_of[i] == k) for k in kinds}
    out = dict(samples=drawn, records=len(recs), records_by_kind=by_kind, multi_step_records=sum(by_kind[k] for k in MULTI if k in by_kind),
               questions_with_records=len(counts))
    if fit1 is not None:
        out['questions_with_find_by_kind'] = {k: dict(pass1=sum(1 for r, f in zip(pool, fit1) if r['kind'] == k and f),
                                                      pass2=sum(1 for r, f1, f2 in zip(pool, fit1, fit) if r['kind'] == k and f2 and not f1),
                                                      pool_questions=sum(r['kind'] == k for r in pool)) for k in kinds}
    return out


def sleep_on(base, recs, updates, vocab, replay, warm_rows, seed, device, lr=LR, visits=VISITS):
    """One night's weight sleep: fresh AdamW from `base`, `updates` updates, half of each batch replay (skills + warm add/mult, evenly)."""
    m = copy.deepcopy(base)
    per = 32 if replay else 64
    mv = max(visits, math.ceil(updates * per / max(len(recs), 1)))
    so = sleep.sleep(m, recs, replay, vocab, sleep.SleepCfg(updates=updates, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows)
    tail = so['loss'][-10:]
    return m, dict(updates=updates, records=len(recs), visits_per_record=updates * per / max(len(recs), 1), last_loss=sum(tail) / max(len(tail), 1))


# ------------------------------------------------------------------ one parent
def train_parent(out, ckpt, skills_train=None, skills_data=None, warmed=None, device='cpu', seed=0, pool_limit=None, dev_limit=None, n1=N1, n2=N2, temps=T_GRID, T=None, lr=LR,
                 visits=VISITS, min_records=1):
    os.makedirs(out, exist_ok=True)
    P = lambda f: os.path.join(out, f)
    t00 = time.time()
    path = P('train.json')
    info = json.load(open(path)) if os.path.exists(path) else dict(ckpt=ckpt, seed=seed, spec=__doc__.split('\n')[0], seconds={}, stages=[],
                                                                    note='test/labelled never opened; DEV only picks the pool temperature; no kind label or key touches an arm')
    save = lambda: json.dump(info, open(path, 'w'), indent=1)
    done = lambda f: os.path.exists(P(f))

    def stage(name, secs):
        info['seconds'][name] = round(secs, 1)
        info['stages'].append(name)
        save()
        log('stage', name, round(secs))

    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool')[:pool_limit])

    # ---- setup: warm-up, N', pool temperature
    ts = time.time()
    if not done('Nprime.pt'):
        if warmed and os.path.exists(warmed):
            m0, vocab, meta = sleep.load_parent(warmed, device)
            info['warm'] = dict(source=warmed)
        else:
            m0, vocab, meta, w = c2_stones._warm(ckpt, warm_rows, replay, 4, 3e-4, seed, device)
            sleep.save_parent(m0, meta['name'], meta['cfg'], vocab, P('warm.pt'), step=(meta['step'] or 0), warmup=True)
            info['warm'] = dict(source='REBUILT from the raw checkpoint (2,048 warm rows, 4 visits, lr 3e-4, seed 0)', **w)
        ss_rows, _ = stones.make_stone_rows(2048, seed)
        N = copy.deepcopy(m0)
        cfg = sleep.SleepCfg(updates=sleep.max_updates(2048, 64, bool(replay), 4), batch=64, lr=3e-4, warmup=20, seed=seed, max_visits=4)
        sleep.sleep(N, stones.solver_records(ss_rows), replay, vocab, cfg, device, replay_extra=warm_rows)
        sleep.save_parent(N, meta['name'], meta['cfg'], vocab, P('Nprime.pt'), step=(meta['step'] or 0), warmup=True)
        stage('Nprime', time.time() - ts)
    N, vocab, meta = sleep.load_parent(P('Nprime.pt'), device)
    N.eval()
    ts = time.time()
    if not done('setup.json'):
        dev = c2_stones._with_nums(R.load_split(DATA, 'dev')[:dev_limit])
        floors = c2_dev.floors_for(dev, P('dev_floors.json'))
        base5 = fastsleep.skills5(N, skills_data, device) if skills_data else None
        res = dict(base5=base5)
        if T is None:
            rep = c2_dev.dev_report(N, vocab, dev, floors, device, 32, seed, temps=temps, extend=(), log=log)
            ok = {t: g for t, g in rep['temps'].items() if g['sameness_ok']} or rep['temps']
            T = float(max(ok, key=lambda t: ok[t]['reach32']))
            res['pool_temperature'] = {t: dict(reach32=g['reach32'], sameness_ok=g['sameness_ok']) for t, g in rep['temps'].items()}
        res['T'] = T
        json.dump(res, open(P('setup.json'), 'w'), indent=1)
        stage('setup', time.time() - ts)
    setup = json.load(open(P('setup.json')))
    T, base5 = setup['T'], setup['base5']
    info['T'] = T
    save()
    seeds = {n: seed + 10 * n for n in (1, 2)}

    def load(arm, night):
        m, _, _ = sleep.load_parent(P(f'{arm}{night}.pt'), device)
        m.eval()
        return m

    def save_model(m, arm, night):
        sleep.save_parent(m, meta['name'], meta['cfg'], vocab, P(f'{arm}{night}.pt'), step=(meta['step'] or 0), warmup=True)

    def build_M(recs):
        m, rep = fastsleep.nightly_recall(N, recs, replay, vocab, device, skills_data, base5=base5, setting=fastsleep.MEMORY_C2B, seed=seed, log_fn=log) if skills_data else (N, dict(recall_on=None, note='no skills data'))
        return m, rep

    # ---- night 1 records: W's two-pass search on N'; R and H from the same N' pass-1 tries
    ts = time.time()
    if not (done('rec_W1.pt') and done('rec_R1.pt') and done('rec_H1.pt')):
        tries, fit1, fit, drawn = c2_stuck.search(N, pool, vocab, device, seeds[1], T, n1, n2)
        W1, c1 = c2_stuck.w_records(pool, tries, seed + 1, arm='W1')
        R1, H1, short = failing_records(pool, [t[:n1] for t in tries], c1, seed + 1, 1)
        ni = night_info(pool, drawn, W1, c1, fit1, fit)
        save_recs(P('rec_W1.pt'), W1, counts=c1, info=ni)
        save_recs(P('rec_R1.pt'), R1, short=short)
        save_recs(P('rec_H1.pt'), H1, short=short)
        info['night1'] = dict(W=ni, R=dict(records=len(R1), short_questions=len(short), short_records=sum(short.values())), H=dict(records=len(H1)))
        stage('night1_records', time.time() - ts)
    dW1 = load_recs(P('rec_W1.pt'))
    W1, c1 = dW1['records'], dW1['counts']
    info.setdefault('night1', dict(W=dW1['info']))
    if len(W1) < min_records:
        info['stop'] = 'night 1: too few W records'
        save()
        return info
    u1 = visits * len(W1) // 32
    # ---- night 1 sleeps
    for arm in ('W', 'R', 'H'):
        if not done(f'{arm}1.pt'):
            ts = time.time()
            recs = load_recs(P(f'rec_{arm}1.pt'))['records']
            m, si = sleep_on(N, recs, u1, vocab, replay, warm_rows, seed, device, lr, visits)
            save_model(m, arm, 1)
            info['night1'][arm]['sleep'] = si
            stage(f'{arm}1_sleep', time.time() - ts)
    ts = time.time()
    M1, rep1 = build_M(W1)
    info['night1']['M'] = dict(recall=rep1, records=len(W1))
    stage('M1_recall', time.time() - ts)

    # ---- night 2 records: every arm samples with its own night-1 model; R and H take W's night-2 counts
    if not done('rec_W2.pt'):
        ts = time.time()
        tries, fit1, fit, drawn = c2_stuck.search(load('W', 1), pool, vocab, device, seeds[2], T, n1, n2)
        W2, c2 = c2_stuck.w_records(pool, tries, seed + 2, arm='W2')
        ni = night_info(pool, drawn, W2, c2, fit1, fit)
        save_recs(P('rec_W2.pt'), W2, counts=c2, info=ni)
        info['night2'] = dict(W=ni)
        stage('W2_search', time.time() - ts)
    dW2 = load_recs(P('rec_W2.pt'))
    W2, c2 = dW2['records'], dW2['counts']
    info.setdefault('night2', dict(W=dW2['info']))
    for arm in ('R', 'H'):
        if not done(f'rec_{arm}2.pt'):
            ts = time.time()
            t1 = legal.raw_samples(load(arm, 1), pool, vocab, device, n=n1, temperature=T, level=0, seed=seeds[2])
            Rr, Hh, short = failing_records(pool, t1, c2, seed + 2, 2)
            save_recs(P(f'rec_{arm}2.pt'), Rr if arm == 'R' else Hh, short=short)
            info['night2'][arm] = dict(records=len(Rr), short_questions=len(short), short_records=sum(short.values()))
            stage(f'{arm}2_records', time.time() - ts)
    if not done('rec_M2.pt'):
        ts = time.time()
        tries, fit1, fit, drawn = c2_stuck.search(M1, pool, vocab, device, seeds[2], T, n1, n2)
        M2, cM = c2_stuck.w_records(pool, tries, seed + 2, arm='M2')
        ni = night_info(pool, drawn, M2, cM, fit1, fit)
        save_recs(P('rec_M2.pt'), M2, counts=cM, info=ni)
        info['night2']['M'] = dict(search=ni)
        stage('M2_search', time.time() - ts)
    M2 = load_recs(P('rec_M2.pt'))['records']
    u2 = visits * len(W2) // 32
    # ---- night 2 sleeps (from each arm's own night-1 model) and the final memory
    if len(W2) < min_records:
        info['stop'] = 'night 2: too few W records'
        save()
        return info
    for arm in ('W', 'R', 'H'):
        if not done(f'{arm}2.pt'):
            ts = time.time()
            recs = load_recs(P(f'rec_{arm}2.pt'))['records']
            m, si = sleep_on(load(arm, 1), recs, u2, vocab, replay, warm_rows, seed, device, lr, visits)
            save_model(m, arm, 2)
            info['night2'][arm]['sleep'] = si
            stage(f'{arm}2_sleep', time.time() - ts)
    if not done('M_final.pt'):
        ts = time.time()
        allrecs = W1 + M2
        _, rep2 = build_M(allrecs)
        save_recs(P('M_final.pt'), allrecs, rep=rep2)
        info['night2']['M']['recall'] = rep2
        stage('M_final', time.time() - ts)
    info['seconds']['total'] = round(time.time() - t00, 1)
    json.dump(dict(parent=os.path.basename(out.rstrip('/')), T=T, base5=base5), open(P('complete.json'), 'w'))
    save()
    log('PARENT DONE', out)
    return info


# ------------------------------------------------------------------ sealed test (opened once, after everything is trained)
def missing(root, parents=PARENTS):
    return [os.path.join(p, f) for p in parents for f in FILES if not os.path.exists(os.path.join(root, p, f))]


def boot_pooled(pairs, iters=2000, seed=0):
    """Paired bootstrap of mean(a) - mean(b) in points, over questions within each parent, pooled over parents. pairs = [(a, b)] per parent (0/1 or reach vectors)."""
    rng = np.random.default_rng(seed)
    d = [np.asarray(a, float) - np.asarray(b, float) for a, b in pairs]
    n = sum(len(x) for x in d)
    est = sum(x.sum() for x in d) / n
    means = np.zeros(iters)
    for x in d:
        idx = rng.integers(0, len(x), size=(iters, len(x)))
        means += x[idx].sum(1)
    means = np.sort(means / n)
    return 100 * est, 100 * means[int(0.025 * iters)], 100 * means[int(0.975 * iters) - 1]


def measure(m, rows, vocab, device, T, fresh, skills_data, seed):
    g = c2_pilot.greedy_eval(m, rows, vocab, device)
    smp = legal.raw_samples(m, rows, vocab, device, n=32, temperature=T, level=0, seed=seed)
    sc = fewshot.score_samples(rows, smp, ks=(1, 4, 32))
    fs = legal.raw_samples(m, fresh, vocab, device, n=32, temperature=1.0, level=0, seed=seed)
    pr = fewshot.score_samples(fresh, fs, ks=(1, 4, 32))
    sk = skills_eval(m, skills_data, device) if skills_data else None
    kinds = sorted({r['kind'] for r in rows})
    by_kind = {}
    for k in kinds:
        ix = [i for i, r in enumerate(rows) if r['kind'] == k]
        by_kind[k] = dict(first_try=sum(g['per_q_right'][i] for i in ix) / len(ix), reach4=sum(sc['per_question'][i]['reach4'] for i in ix) / len(ix),
                          reach32=sum(sc['per_question'][i]['reach32'] for i in ix) / len(ix))
    return dict(first_try=g['right'], fits=g['fits'], reach4=sc['reach4'], reach32=sc['reach32'], by_kind=by_kind, practised=dict(reach32=pr['reach32'], first_sample=pr['reach1']),
                skills_pooled5=(sk or {}).get('pooled5'), per_q=dict(right=[float(x) for x in g['per_q_right']], reach4=[d['reach4'] for d in sc['per_question']],
                                                                     reach32=[d['reach32'] for d in sc['per_question']]))


def score_parent(root, parent, skills_train, skills_data, test, fresh, device, seed):
    out = os.path.join(root, 'test', f'{parent}.json')
    if os.path.exists(out):
        return json.load(open(out))
    d = os.path.join(root, parent)
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    setup = json.load(open(os.path.join(d, 'setup.json')))
    T = setup['T']
    N, vocab, meta = sleep.load_parent(os.path.join(d, 'Nprime.pt'), device)
    models = dict(N=N)
    for arm in ('W', 'R', 'H'):
        models[arm], _, _ = sleep.load_parent(os.path.join(d, f'{arm}2.pt'), device)
    dm = load_recs(os.path.join(d, 'M_final.pt'))
    rep = dm['rep']
    if rep.get('recall_on') is False:
        models['M'] = N                                  # the harm guard switched recall off: M is N' that night
    else:
        name, kw = fastsleep.MEMORY_C2B
        models['M'], _ = fastsleep.METHODS[name](N, dm['records'], replay, vocab, device, len(dm['records']), seed=seed, **kw)
    res = dict(parent=parent, T=T, recall=rep)
    for arm, m in models.items():
        m.eval()
        t0 = time.time()
        res[arm] = measure(m, test, vocab, device, T, fresh, skills_data, seed)
        log('test', parent, arm, {k: round(res[arm][k], 4) for k in ('first_try', 'reach4', 'reach32')}, round(time.time() - t0))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, 'w'))
    return res


def score_test(root, skills_train=None, skills_data=None, device='cpu', seed=0, parents=PARENTS, test_limit=None, force=False):
    """Refuses unless every parent has every arm; refuses a second pass once REPORT.json exists. Opens the sealed test split only after both checks."""
    miss = missing(root, parents)
    if miss:
        raise SystemExit(f'REFUSED: the sealed test split stays closed. {len(miss)} file(s) missing (6 parents x W, R, H, M and N\' must all exist):\n  ' + '\n  '.join(miss[:30]))
    rep_path = os.path.join(root, 'REPORT.json')
    if os.path.exists(rep_path) and not force:
        raise SystemExit('REFUSED: the test split was already opened and scored once (REPORT.json exists).')
    sentinel = os.path.join(root, 'TEST-OPENED.json')
    if not os.path.exists(sentinel):
        json.dump(dict(opened=time.strftime('%Y-%m-%d %H:%M:%S'), parents=list(parents)), open(sentinel, 'w'))
    test = c2_stones._with_nums(R.load_split(DATA, 'test')[:test_limit])
    fresh = c2_stones._with_nums(stones.fresh_practised(256, 1, 'fresh-check')[0])
    per = [score_parent(root, p, skills_train, skills_data, test, fresh, device, seed) for p in parents]
    rep = report(per, test)
    json.dump(rep, open(rep_path, 'w'), indent=1)
    return rep


def report(per, test):
    """Pooled numbers and per-parent readings against the fixed marks. No verdict: the roadmap thread rules."""
    kinds = sorted({r['kind'] for r in test})
    multi = [i for i, r in enumerate(test) if r['kind'] in MULTI]
    pairs = lambda a, b, key, ix=None: [([p[a]['per_q'][key][i] for i in (ix if ix is not None else range(len(p[a]['per_q'][key])))],
                                          [p[b]['per_q'][key][i] for i in (ix if ix is not None else range(len(p[b]['per_q'][key])))]) for p in per]
    ci = lambda a, b, key, ix=None: dict(zip(('points', 'lo', 'hi'), boot_pooled(pairs(a, b, key, ix))))
    mean = lambda xs: sum(xs) / len(xs)
    arms = ('N',) + ARMS
    out = dict(parents=[p['parent'] for p in per], n_questions=len(test))
    out['pooled'] = {a: dict(first_try=mean([x for p in per for x in p[a]['per_q']['right']]), reach4=mean([p[a]['reach4'] for p in per]), reach32=mean([p[a]['reach32'] for p in per]),
                             practised_reach32=mean([p[a]['practised']['reach32'] for p in per]),
                             by_kind={k: mean([p[a]['by_kind'][k]['first_try'] for p in per]) for k in kinds}) for a in arms}
    out['intervals_first_try'] = {f'{a}-{b}': ci(a, b, 'right') for a, b in (('W', 'N'), ('W', 'R'), ('W', 'H'), ('W', 'M'), ('M', 'N'), ('R', 'N'), ('H', 'N'))}
    out['intervals_multi_step_first_try'] = {f'{a}-{b}': ci(a, b, 'right', multi) for a, b in (('W', 'N'), ('W', 'R'))}
    out['intervals_reach4'] = {'W-N': ci('W', 'N', 'reach4')}
    out['by_kind_W_minus_N_points'] = {k: 100 * (out['pooled']['W']['by_kind'][k] - out['pooled']['N']['by_kind'][k]) for k in kinds}
    rows = []
    for p in per:
        base = p['N']['skills_pooled5']
        row = dict(parent=p['parent'], T=p['T'], recall_on=p['recall'].get('recall_on'), chain5_harm_M_night2=p['recall'].get('chain5_harm_points'))
        for a in arms:
            row[a] = dict(first_try=p[a]['first_try'], reach4=p[a]['reach4'], reach32=p[a]['reach32'], practised=p[a]['practised']['reach32'],
                          skills_harm_points=None if base is None or p[a]['skills_pooled5'] is None else round(100 * (base - p[a]['skills_pooled5']), 4))
        row['W_minus_N_first_try_points'] = 100 * (p['W']['first_try'] - p['N']['first_try'])
        row['W_minus_R_first_try_points'] = 100 * (p['W']['first_try'] - p['R']['first_try'])
        rows.append(row)
    out['per_parent'] = rows
    wn, wr, ms = out['intervals_first_try']['W-N'], out['intervals_first_try']['W-R'], out['intervals_multi_step_first_try']['W-N']
    pr = 100 * (out['pooled']['W']['practised_reach32'] - out['pooled']['N']['practised_reach32'])
    r4 = 100 * (out['pooled']['W']['reach4'] - out['pooled']['N']['reach4'])
    harm = [r['W']['skills_harm_points'] for r in rows]
    out['readings'] = {
        'pooled first try W-N >= +15 with the interval above 0': bool(wn['points'] >= 15 and wn['lo'] > 0),
        'pooled first try W-R >= +10 with the interval above 0': bool(wr['points'] >= 10 and wr['lo'] > 0),
        'W-N positive on >= 5 of 6 parents': sum(r['W_minus_N_first_try_points'] > 0 for r in rows) >= 5,
        'reach@4 W no more than 2 points below N': bool(r4 >= -2),
        'practised check W no more than 2 points below N': bool(pr >= -2),
        'skills harm <= 2 on every parent (W)': None if None in harm else bool(all(h <= 2 for h in harm)),
        'label: beyond the near-copy kinds (pooled multi-step W-N interval above 0)': bool(ms['lo'] > 0),
        'proved wrong: W-R upper end < +3': bool(wr['hi'] < 3)}
    out['readings_numbers'] = dict(W_minus_N=wn, W_minus_R=wr, multi_step_W_minus_N=ms, practised_W_minus_N_points=pr, reach4_W_minus_N_points=r4, skills_harm_W=harm)
    out['note'] = 'numbers and per-parent readings only; the roadmap thread gives the verdict'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('cmd', choices=['train', 'score', 'check'])
    a.add_argument('--ckpt'); a.add_argument('--out'); a.add_argument('--root'); a.add_argument('--warmed'); a.add_argument('--skills-train'); a.add_argument('--skills-data')
    a.add_argument('--device', default='cpu'); a.add_argument('--seed', type=int, default=0)
    a.add_argument('--pool-limit', type=int); a.add_argument('--dev-limit', type=int); a.add_argument('--test-limit', type=int); a.add_argument('--T', type=float)
    a = a.parse_args()
    if a.cmd == 'train':
        train_parent(a.out, a.ckpt, a.skills_train, a.skills_data, a.warmed, a.device, a.seed, a.pool_limit, a.dev_limit, T=a.T)
    elif a.cmd == 'check':
        miss = missing(a.root)
        print('complete: all 6 parents x 4 arms present' if not miss else f'{len(miss)} missing:\n  ' + '\n  '.join(miss))
    else:
        r = score_test(a.root, a.skills_train, a.skills_data, a.device, a.seed, test_limit=a.test_limit)
        print(json.dumps(r['readings'], indent=1))
