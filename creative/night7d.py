"""Roadmap 7526d614e5, Test VL: does night 1 hurt skills less with each record seen fewer times (arm V) or at a lower lr (arm L)? CPU. Reads the skills TRAIN file (replay), C2 pool / warm rows (night records),
C2 DEV and skills DEV (MEASURE only); C2 test / labelled never opened.
  python3 -m creative.night7d run --nprime ~/c7d/s100/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 1
  python3 -m creative.night7d report --out DIR --parents s100 s101
Each arm is ONE change to the standard night 1 from N' (S3's W1 = sleep_on(N', W1's records, lr 1e-3, 32 visits, seed)): V = 8 visits per record (lr 1e-3); L = lr 1e-4 (32 visits).
W1's records are rebuilt from S1's day with S3's seeds and checked against W1_night in s3.json."""
import argparse, copy, json, os, pickle, time
import torch
from creative import c2_pilot, c2_stones, rules_real as R, sleep
from creative.sleep7d import (DATA, T_POOL, _arm_model, _by_kind, _cached, _h, _hstate, _limit, _log, _sha_file, add_adapter, adapter_state, creative, day_f, greedy_rows, score_rows, search,
                              sleep_on, w_records, w1_tries_from_day)
from creative import legal
from creative.repair7d import _stage, skills_dev
from creative.harm_look import harm_measure

ARMS = {'V': dict(lr=1e-3, visits=8), 'L': dict(lr=1e-4, visits=32)}
MARKS = dict(harm="(1) harm_measure(N' DEV hits, arm DEV hits) passes: in_dist drop <= 1.5 and no family fires (drop > 5 points and paired 95% interval below 0)",
             first_try='(2) C2 DEV first try within 2 points of W1: c2_pilot.boot(arm right, W1 right) point >= -2.0',
             passes='arm passes = (1) and (2)',
             proved_wrong="arm's in_dist drop vs N' is NOT at least 1.0 point smaller than W1's drop vs N' (arm_drop > W1_drop - 1.0) on BOTH parents (decided in the report)")
DECISION = ('if both pass, the arm with the smaller harm (mean in_dist drop vs N\' over parents) goes forward; if neither passes, the one not proved wrong is built on '
            '(both not proved wrong: the smaller mean drop; both proved wrong: none); if exactly one passes, that one')


def arm_marks(harm_passes, c2_point, arm_drop, w1_drop):
    """Pure. -> the arm's marks on one parent (drops in points vs N')."""
    first = bool(c2_point >= -2.0)
    return dict(harm=bool(harm_passes), first_try=first, passes=bool(harm_passes and first), proved_wrong=bool(arm_drop > w1_drop - 1.0))


def pick(per_parent):
    """Pure. per_parent {parent: {arm: dict(passes, proved_wrong, drop)}} -> (per-arm summary, picked arm or None)."""
    arms = sorted({a for m in per_parent.values() for a in m})
    s = {a: dict(passes=all(m[a]['passes'] for m in per_parent.values()), proved_wrong=all(m[a]['proved_wrong'] for m in per_parent.values()),
                 mean_drop=sum(m[a]['drop'] for m in per_parent.values()) / len(per_parent)) for a in arms}
    best = lambda xs: min(xs, key=lambda a: s[a]['mean_drop']) if xs else None
    passers = [a for a in arms if s[a]['passes']]
    return s, best(passers) if passers else best([a for a in arms if not s[a]['proved_wrong']])


def _peek(path, key):
    """A cache written by another run (read only): its value when the key matches, else None."""
    if os.path.exists(path):
        c = pickle.load(open(path, 'rb'))
        if c.get('key') == key:
            return c['v']
    return None


def vl_parent(nprime, out, s1dir, s3dir, rdir, skills_train, skills_data, seed=0, pool_limit=None, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True, log=_log,
              max_records=None, drift_dir=None):
    """One parent's Test VL. DIR/<name>/vl.json is written after every stage; each arm is cached (<arm>.pt + .pkl). max_records = smoke only: truncates the night-1 records (recorded)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, rd = os.path.join(out, name), os.path.join(s3dir, name), os.path.join(rdir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed, T, n1, n2 = s3['seed'], s3['T'], a3['n1'], a3['n2']
    assert a3['lr'] == 1e-3 and a3['visits'] == 32, 'W1 is not the standard night'
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], marks_rules=MARKS, decision_rule=DECISION, secs=secs, arms_spec=ARMS,
               args=dict(seed=seed, night_seed=seed, T=T, n1=n1, n2=n2, s3_args=a3, pool_limit=pool_limit, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, s1=s1dir, s3=s3dir, r=rdir,
                         skills_train=skills_train, skills_data=skills_data),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled never opened')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'vl.json'), 'w'), indent=1)
    pool_limit = a3['pool_limit'] if pool_limit is None else pool_limit
    replay = sleep.load_replay(skills_train, a3['replay_n'], seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    w1p = os.path.join(s3d, 'W1.pt')
    sha = dict(N=_sha_file(nprime), W1=_sha_file(w1p))
    # 1. W1's records, rebuilt from S1's day and S3's seeds
    t0 = time.time()
    got = w1_tries_from_day(os.path.join(s1dir, name, 'day.pkl'), (os.path.abspath(nprime), a3['pool_limit'], n1, n2, seed, T), N, pool, vocab, device, seed, T, n1, n2)
    assert got is not None, 'S1 day key differs: cannot rebuild W1 records'
    tries, source = got[0], got[4]
    recs, _ = w_records(pool, tries, seed + 1)
    want = s3['W1_night']['records']
    assert len(recs) == want, f'rebuilt {len(recs)} records, W1_night has {want}'
    res['records'] = dict(rebuilt=len(recs), W1_night=want, equal=True, night_seed=seed, source=source)
    secs['records'] = time.time() - t0
    if max_records:
        recs = recs[:max_records]
        res['records']['smoke_truncated_to'] = len(recs)
    save()
    # 2. arms
    models, ainfo = {}, {}
    for arm, spec in ARMS.items():
        t0 = time.time()
        key = _h('vl', sha['N'], spec['lr'], spec['visits'], seed, len(recs), want, a3['replay_n'], bool(skills_train))
        models[arm], ainfo[arm], sha[arm] = _stage(pdir, arm, key, lambda spec=spec: _night(N, recs, vocab, replay, warm_rows, spec, seed, device), meta, vocab, device, resume, log)
        secs[arm] = time.time() - t0
        res.setdefault('arms', {})[arm] = dict(ainfo[arm], **spec)
        log(arm, ainfo[arm])
        save()
    # 3. measures
    W1, _, _ = sleep.load_parent(w1p, device)
    W1.eval()
    allm = dict(N=N, W1=W1, **models)
    hits, c2, res['skills'], res['c2_dev'], rows = {}, {}, {}, {}, None
    for a, m in allm.items():
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        v = _peek(os.path.join(rd, f'skills_{a}.pkl'), sk) if a in ('N', 'W1') else None
        v = v or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (_peek(os.path.join(rd, f'c2_{a}.pkl'), ck) if a in ('N', 'W1') else None) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a], p5, ia = v[:4]
        c2[a] = c
        res['skills'][a] = dict(pooled5=p5, in_dist=ia, n=len(hits[a]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    # 4. marks
    right = lambda a: [float(d['right']) for d in c2[a]]
    w1_drop = res['skills']['N']['in_dist'] - res['skills']['W1']['in_dist']
    res['W1_drop_vs_N'] = w1_drop
    res['marks'] = {}
    for arm in ARMS:
        hN, hW = harm_measure(hits['N'], hits[arm], rows), harm_measure(hits['W1'], hits[arm], rows)
        bt = dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(right(arm), right('W1'))))
        mk = arm_marks(hN['passes'], bt['points'], hN['in_dist_drop'], w1_drop)
        res['marks'][arm] = dict(mk, in_dist_drop_vs_N=hN['in_dist_drop'], W1_in_dist_drop_vs_N=w1_drop, fired_vs_N=hN['fired'], pooled5=res['skills'][arm]['pooled5'], first_try_boot_vs_W1=bt,
                                 report_only_vs_W1=dict(in_dist_drop=hW['in_dist_drop'], fired=hW['fired'], passes=hW['passes']))
    dp = os.path.join(drift_dir or os.path.expanduser('~/c7d/drift'), name, 'drift.json')
    if os.path.exists(dp):
        res['fresh_pass_reference'] = dict(source=dp, row=json.load(open(dp))['table'].get('lr1e-4_fresh'), note='W1 + 256 fresh-row replay-only updates at 1e-4; report only')
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {a: {k: v for k, v in m.items() if k in ('harm', 'first_try', 'passes', 'proved_wrong')} for a, m in res['marks'].items()})
    return res


def _night(N, recs, vocab, replay, warm_rows, spec, seed, device):
    t0 = time.time()
    m, info = sleep_on(N, recs, vocab, replay, warm_rows, spec['lr'], spec['visits'], seed, device)
    info['seconds'] = time.time() - t0
    return m, info


def vl(nprimes, out, s1dir, s3dir, rdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: vl_parent(p, out, s1dir, s3dir, rdir, **kw) for p in nprimes}


def vlreport(out, parents):
    """-> DIR/vl-report.json: per arm, passes / proved_wrong on every parent, mean drop; the decision rule and the arm it picks (or none)."""
    res = {p: json.load(open(os.path.join(out, p, 'vl.json'))) for p in parents}
    pp = {p: {a: dict(passes=m['passes'], proved_wrong=m['proved_wrong'], drop=m['in_dist_drop_vs_N']) for a, m in x['marks'].items()} for p, x in res.items()}
    summ, picked = pick(pp)
    rep = dict(parents=list(parents), arms=summ, per_parent=pp, picked=picked, decision_rule=DECISION, rules=MARKS, tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], marks=x['marks'], arms=x['arms'],
               fresh_pass_reference=x.get('fresh_pass_reference')) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'vl-report.json'), 'w'), indent=1)
    return rep



# ---------------------------------------------------------------- Test L2 (roadmap 7c8041caa3)
L2_MARKS = dict(harm="(1) harm_measure(N' DEV hits, L2 DEV hits) passes: in_dist drop <= 1.5 and no family fires",
                multi_step='(2) C2 DEV first try on the multi-step kinds (c2_pilot.HARD_KINDS, 154 questions): c2_pilot.boot(L2 right, W2 right) point >= -2.0',
                passes='passes = (1) and (2) on a parent; the verdict needs both parents',
                proved_wrong='the L2 - W2 multi-step first-try paired 95% interval has its upper end < 0 on BOTH parents (decided in the report)')
L2_NEXT = ('if L2 passes: lr 1e-4 becomes the night dose for new runs (6-parent confirm waits for job 9\'s scoring); '
           'if it misses mark 2: L64 on both nights is the next single change')


def l2_marks(harm_passes, ms_point, ms_hi):
    """Pure. -> the L2 marks on one parent: multi-step first try L2 - W2 (point, 95% upper end, in points)."""
    ok2 = bool(ms_point >= -2.0)
    return dict(harm=bool(harm_passes), multi_step=ok2, passes=bool(harm_passes and ok2), proved_wrong=bool(ms_hi < 0))


def l2_verdict(per_parent):
    """Pure. {parent: l2_marks dict} -> dict(passes on every parent, proved_wrong on every parent, next text)."""
    return dict(passes=all(m['passes'] for m in per_parent.values()), proved_wrong=all(m['proved_wrong'] for m in per_parent.values()),
                disagree=[k for k in ('harm', 'multi_step', 'passes', 'proved_wrong') if len({m[k] for m in per_parent.values()}) > 1], next=L2_NEXT)


def _skills_as_tuple(v):
    return (None, v['hits'], v['pooled5'], v['in_dist']) if isinstance(v, dict) else v


def l2_parent(nprime, out, s3dir, jdir, rdir, vldir, s1wdir, skills_train, skills_data, seed=0, pool_limit=None, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True,
              log=_log, max_records=None, b2=None):
    """One parent's Test L2. DIR/<name>/l2.json is written after every stage; day 2, night 2 and every measure are cached. Reuses (key-checked, read only): R's skills / c2 caches for N', W1, W2, VL's for L,
    J's skills_B2, S1w's measure_U (W1 reach@32) and J's measure_W (W2 reach@32). max_records = smoke only (recorded)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, jd, rd, vd, s1wd = (os.path.join(d, name) for d in (out, s3dir, jdir, rdir, vldir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    jj = json.load(open(os.path.join(jd, 'j.json')))
    ja = jj['args']
    seed, T, s2, mseed, n1, n2 = jj['seed'], jj['T'], jj['day2_seed'], jj['measure_seed'], ja['n1'], ja['n2']
    assert s2 == seed + 1 and mseed == seed + 777 and ja['lr'] == 1e-3 and ja['visits'] == 32, 'J is not the standard two nights'
    pool_limit = ja['pool_limit'] if pool_limit is None else pool_limit
    b2 = os.path.expanduser(b2 or ja.get('b2') or '')
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], marks_rules=L2_MARKS, next=L2_NEXT, secs=secs, args=dict(seed=seed, day2_seed=s2, measure_seed=mseed, T=T, n1=n1, n2=n2, lr=1e-4, visits=32,
               pool_limit=pool_limit, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, b2=b2, s3=s3dir, j=jdir, r=rdir, vl=vldir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'l2.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, ja['replay_n'], seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    paths = dict(N=nprime, W1=os.path.join(s3d, 'W1.pt'), W2=os.path.join(jd, 'W2.pt'), L=os.path.join(vd, 'L.pt'))
    sha = {a: _sha_file(p) for a, p in paths.items()}
    res['night1'] = dict(L_path=paths['L'], L_sha256=sha['L'], vl_json_L=json.load(open(os.path.join(vd, 'vl.json')))['arms']['L'])
    L, _, _ = sleep.load_parent(paths['L'], device)
    L.eval()
    # 2. day 2 from L (j_parent's W arm: untrained adapter = plain two-pass search)
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    skey = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    t0 = time.time()
    dkey = (skey, s2, sha['L'], _hstate(init), 'L')
    day = _cached(os.path.join(pdir, 'day2_L.pkl'), dkey, lambda: day_f(_arm_model(L, init, seed), pool, vocab, device, T, n1, n2, s2), resume, log, 'day 2 L')
    secs['day2_L'] = time.time() - t0
    res['day2'] = dict(drawn=day['drawn'], greedy_pass=sum(day['greedy_fit']) / len(pool), pool_with_fit_pass1=sum(day['fit1']), pool_with_fit_final=sum(day['fit_final']), pool_rows=len(pool),
                       seconds=secs['day2_L'], seconds_per_pool_row=secs['day2_L'] / len(pool))
    log('day 2 L', res['day2'])
    save()
    # 3. night 2
    recs, cnt = w_records(pool, day['tries'], s2 + 1)
    assert recs, 'L: no day-2 records'
    res['night2_records'] = dict(records=len(recs), records_by_kind=_by_kind(pool, cnt), W2_records=jj['night2']['W']['records'], W2_records_by_kind=jj['night2']['W']['records_by_kind'])
    if max_records:
        recs = recs[:max_records]
        res['night2_records']['smoke_truncated_to'] = len(recs)
    t0 = time.time()

    def night2():
        t1 = time.time()
        m, si = sleep_on(L, recs, vocab, replay, warm_rows, 1e-4, 32, s2, device)
        si['seconds'] = time.time() - t1
        return m, si
    L2, si, sha['L2'] = _stage(pdir, 'L2', _h('l2', dkey, len(recs), 1e-4, 32, ja['replay_n'], bool(skills_train)), night2, meta, vocab, device, resume, log)
    secs['night2_L2'] = time.time() - t0
    res['night2'] = dict(si, lr=1e-4, visits=32)
    log('L2 night 2', si)
    save()
    # 4. measures
    models, getm = dict(N=N, L=L, L2=L2), {}
    def get(a):
        if a not in models:
            m, _, _ = sleep.load_parent(paths[a], device)
            m.eval()
            models[a] = m
        return models[a]
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    for a in ('N', 'W1', 'W2', 'L', 'L2'):
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        src = dict(N=rd, W1=rd, W2=rd, L=vd).get(a)
        v = (src and _peek(os.path.join(src, f'skills_{a}.pkl'), sk)) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda a=a: skills_dev(get(a), skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (src and _peek(os.path.join(src, f'c2_{a}.pkl' if a != 'L' else 'c2_L.pkl'), ck)) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda a=a: greedy_rows(get(a), dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
        c2[a] = c
        res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    if os.path.exists(b2):                                      # B2, skills only (report-only harm of the whole chain)
        bs = _sha_file(b2)
        bj = _peek(os.path.join(jd, 'skills_B2.pkl'), ('B2', skills_data, bs)) if not skills_limit else None
        bv = _skills_as_tuple(bj) if bj else _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', bs, skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
        save()
    # multi-step reach@32 per night (W1, W2, L, L2): 32 plain samples per C2 DEV row, untrained adapter, mseed
    reuse = dict(W1=(os.path.join(s1wd, 'measure_U.pkl'), 'U'), W2=(os.path.join(jd, 'measure_W.pkl'), 'W'))
    for a in ('W1', 'W2', 'L', 'L2'):
        t0 = time.time()
        v, how = None, 'computed'
        if a in reuse and os.path.exists(reuse[a][0]):
            c = pickle.load(open(reuse[a][0], 'rb'))
            kk = c['key']
            # the cached key is a hash of the whole night's arguments: check the parts that are visible (arm, n_eval, k, measure seed, dev limit, skills dir for J) and that the rows line up
            ok = kk[1] == reuse[a][1] and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and (a != 'W2' or kk[7] == skills_data) and len(c['v']['c32']) == len(dev)
            ok = ok and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
            if ok:
                v, how = c['v']['c32'], f'reused {reuse[a][0]}'
        if v is None:
            def fn(a=a):
                mm = _arm_model(get(a) if a in ('L', 'L2') else sleep.load_parent(paths[a], device)[0].eval(), init, seed)
                with creative(mm, True):
                    smp = legal.raw_samples(mm, dev, vocab, device, n=32, temperature=T, level=0, seed=mseed)
                return score_rows(dev, smp, ks=(32,))
            v = _cached(os.path.join(pdir, f'c32_{a}.pkl'), ('c32', sha[a], dev_limit, mseed, T, 32), fn, resume, log, f'reach32 {a}')
        c32[a] = v
        hard = [x['right32'] for x, r in zip(v, dev) if r['kind'] in c2_pilot.HARD_KINDS]
        res['reach32'][a] = dict(pooled=100 * sum(x['right32'] for x in v) / len(v), multi_step=100 * sum(hard) / max(len(hard), 1), source=how)
        secs[f'reach32_{a}'] = time.time() - t0
        log('reach32', a, res['reach32'][a])
        save()
    # 5. marks and report-only
    hard_ix = [i for i, r in enumerate(dev) if r['kind'] in c2_pilot.HARD_KINDS]
    if not dev_limit:
        assert len(hard_ix) == 154, f'{len(hard_ix)} multi-step DEV questions, expected 154'
    res['multi_step_n'] = len(hard_ix)
    right = lambda a, ix=None: [float(c2[a][i]['right']) for i in (range(len(dev)) if ix is None else ix)]
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    reach = lambda a, ix: [float(c32[a][i]['right32']) for i in ix]
    hN = harm_measure(hits['N'], hits['L2'], rows)
    ms = bd(right('L2', hard_ix), right('W2', hard_ix))
    res['marks'] = dict(l2_marks(hN['passes'], ms['points'], ms['hi']), in_dist_drop_vs_N=hN['in_dist_drop'], fired_vs_N=hN['fired'], pooled5=res['skills']['L2']['pooled5'], multi_step_first_try_L2_minus_W2=ms,
                        multi_step_n=len(hard_ix), rules=L2_MARKS)
    res['report_only'] = dict(
        multi_step_first_try_L2_minus_N=bd(right('L2', hard_ix), right('N', hard_ix)), climb_mark='job 8: +10 points', pooled_first_try={a: 100 * sum(right(a)) / len(dev) for a in c2},
        pooled_first_try_L2_minus_W2=bd(right('L2'), right('W2')), reach32=res['reach32'], reach32_multi_step_L2_minus_W2=bd(reach('L2', hard_ix), reach('W2', hard_ix)),
        harm_vs_B2={a: {k: v for k, v in harm_measure(hits['B2'], hits[a], rows).items() if k != 'families'} for a in ('N', 'W1', 'W2', 'L', 'L2')} if 'B2' in hits else None,
        night2_own_cost_L2_vs_L={k: v for k, v in harm_measure(hits['L'], hits['L2'], rows).items() if k != 'families'},
        night2_records=res['night2_records'])
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'multi_step', 'passes', 'proved_wrong')})
    return res


def l2(nprimes, out, s3dir, jdir, rdir, vldir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: l2_parent(p, out, s3dir, jdir, rdir, vldir, s1wdir, **kw) for p in nprimes}


def l2report(out, parents):
    """-> DIR/l2-report.json: per-parent marks, the verdict (passes on both parents), proved_wrong (on both), and the next-step text."""
    res = {p: json.load(open(os.path.join(out, p, 'l2.json'))) for p in parents}
    pm = {p: {k: x['marks'][k] for k in ('harm', 'multi_step', 'passes', 'proved_wrong')} for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=pm, verdict=l2_verdict(pm), rules=L2_MARKS, next=L2_NEXT,
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], report_only=x['report_only'], day2=x['day2'], night2=x['night2']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'l2-report.json'), 'w'), indent=1)
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('run'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True); q.add_argument('--r', required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--pool-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only: truncate the night-1 records'); q.add_argument('--device', default='cpu')
    q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('l2'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s3', 'j', 'r', 'vl', 's1w'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--pool-limit', type=int)
    q.add_argument('--dev-limit', type=int); q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu')
    q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('l2report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'l2report':
        print(json.dumps(l2report(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'l2':
        ex = os.path.expanduser
        l2(a.nprime, a.out, ex(a.s3), ex(a.j), ex(a.r), ex(a.vl), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit,
           skills_limit=a.skills_limit, device=a.device, resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'report':
        print(json.dumps(vlreport(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        vl(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit, skills_limit=a.skills_limit,
           device=a.device, resume=not a.no_resume, max_records=a.max_records)
