"""Roadmap 7526d614e5, Test VL: does night 1 hurt skills less with each record seen fewer times (arm V) or at a lower lr (arm L)? CPU. Reads the skills TRAIN file (replay), C2 pool / warm rows (night records),
C2 DEV and skills DEV (MEASURE only); C2 test / labelled never opened.
  python3 -m creative.night7d run --nprime ~/c7d/s100/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 1
  python3 -m creative.night7d report --out DIR --parents s100 s101
Each arm is ONE change to the standard night 1 from N' (S3's W1 = sleep_on(N', W1's records, lr 1e-3, 32 visits, seed)): V = 8 visits per record (lr 1e-3); L = lr 1e-4 (32 visits).
W1's records are rebuilt from S1's day with S3's seeds and checked against W1_night in s3.json."""
import argparse, collections, copy, json, os, pickle, random, time
import math
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


def _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device):
    """W1's exact night-1 records, rebuilt as sleep7d.s3_parent does when it reuses W1 (S1's day, S3's seeds), checked against W1_night's count. `pool` = the full C2 pool of S3's args. -> (records, info)."""
    a3 = s3['args']
    seed, T, n1, n2 = s3['seed'], s3['T'], a3['n1'], a3['n2']
    got = w1_tries_from_day(os.path.join(s1dir, name, 'day.pkl'), (os.path.abspath(nprime), a3['pool_limit'], n1, n2, seed, T), N, pool, vocab, device, seed, T, n1, n2)
    assert got is not None, 'S1 day key differs: cannot rebuild W1 records'
    recs, _ = w_records(pool, got[0], seed + 1)
    want = s3['W1_night']['records']
    assert len(recs) == want, f'rebuilt {len(recs)} records, W1_night has {want}'
    return recs, dict(rebuilt=len(recs), W1_night=want, equal=True, night_seed=seed, source=got[4])


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
    recs, res['records'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    want = res['records']['W1_night']
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
                proved_wrong='the L2 - W2 multi-step first-try paired 95% interval has its upper end < 0 on BOTH parents (decided in the report)',
                proved_wrong_no_climb='L64 only: night-2 model minus L2 multi-step first try (paired point, 154 HARD_KINDS) < +1.0 point on BOTH parents ("more practice at the low rate adds no climb"); proved_wrong = either rule')
L2_NEXT = ('if L2 passes: lr 1e-4 becomes the night dose for new runs (6-parent confirm waits for job 9\'s scoring); '
           'if it misses mark 2: L64 on both nights is the next single change')


def l2_marks(harm_passes, ms_point, ms_hi, vs_l2_point=None):
    """Pure. -> the L2 marks on one parent: multi-step first try L2 - W2 (point, 95% upper end, in points). proved_wrong = rule 1 (L2 - W2 upper end < 0). vs_l2_point (L64 only) = night-2 model minus L2
    multi-step first try, point: proved_wrong_no_climb = it is below +1.0 ("more practice at the low rate adds no climb"; None when not given)."""
    ok2 = bool(ms_point >= -2.0)
    return dict(harm=bool(harm_passes), multi_step=ok2, passes=bool(harm_passes and ok2), proved_wrong=bool(ms_hi < 0), proved_wrong_no_climb=None if vs_l2_point is None else bool(vs_l2_point < 1.0))


def l2_verdict(per_parent):
    """Pure. {parent: l2_marks dict} -> dict(passes on every parent, proved_wrong on every parent, next text)."""
    nc = [m.get('proved_wrong_no_climb') for m in per_parent.values()]
    no_climb = None if any(x is None for x in nc) else all(nc)
    low = all(m['proved_wrong'] for m in per_parent.values())
    return dict(passes=all(m['passes'] for m in per_parent.values()), proved_wrong_vs_W2=low, proved_wrong_no_climb=no_climb, proved_wrong=bool(low or no_climb),
                disagree=[k for k in ('harm', 'multi_step', 'passes', 'proved_wrong', 'proved_wrong_no_climb') if len({m.get(k) for m in per_parent.values()}) > 1], next=L2_NEXT)


def _skills_as_tuple(v):
    return (None, v['hits'], v['pooled5'], v['in_dist']) if isinstance(v, dict) else v


def l2_parent(nprime, out, s3dir, jdir, rdir, vldir, s1wdir, skills_train, skills_data, seed=0, pool_limit=None, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True,
              log=_log, max_records=None, b2=None, visits=32, s1dir=None, l2dir=None):
    """One parent's Test L2 (visits=32, night 1 = VL's L) or L<visits> (visits != 32: night 1 is trained here from N' on W1's rebuilt records, stages L1v<visits> / L2v<visits>; needs s1dir; the field names
    'L' / 'L2' then mean this run's night-1 / night-2 model, res['label'] and res['models'] say which; l2dir = the L2 outputs for a report-only comparison). DIR/<name>/l2.json (l<visits>.json) is written after every stage; day 2, night 2 and every measure are cached. Reuses (key-checked, read only): R's skills / c2 caches for N', W1, W2, VL's for L,
    J's skills_B2, S1w's measure_U (W1 reach@32) and J's measure_W (W2 reach@32). max_records = smoke only (recorded)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, jd, rd, vd, s1wd = (os.path.join(d, name) for d in (out, s3dir, jdir, rdir, vldir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    std = visits == 32
    label, f1, f2 = ('L2', 'L', 'L2') if std else (f'L{visits}', f'L1v{visits}', f'L2v{visits}')
    tag = lambda a: {'L': f1, 'L2': f2}.get(a, a)
    jj = json.load(open(os.path.join(jd, 'j.json')))
    ja = jj['args']
    seed, T, s2, mseed, n1, n2 = jj['seed'], jj['T'], jj['day2_seed'], jj['measure_seed'], ja['n1'], ja['n2']
    assert s2 == seed + 1 and mseed == seed + 777 and ja['lr'] == 1e-3 and ja['visits'] == 32, 'J is not the standard two nights'
    pool_limit = ja['pool_limit'] if pool_limit is None else pool_limit
    b2 = os.path.expanduser(b2 or ja.get('b2') or '')
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], label=label, models=dict(L=f1, L2=f2), marks_rules=L2_MARKS, next=L2_NEXT, secs=secs, args=dict(seed=seed, day2_seed=s2, measure_seed=mseed, T=T, n1=n1, n2=n2, lr=1e-4, visits=visits, label=label,
               pool_limit=pool_limit, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, b2=b2, s3=s3dir, j=jdir, r=rdir, vl=vldir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'l2.json' if std else f'l{visits}.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, ja['replay_n'], seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    paths = dict(N=nprime, W1=os.path.join(s3d, 'W1.pt'), W2=os.path.join(jd, 'W2.pt'), L=os.path.join(vd, 'L.pt') if std else os.path.join(pdir, f1 + '.pt'))
    vl_L = os.path.join(vd, 'L.pt')
    if std:
        sha = {a: _sha_file(p) for a, p in paths.items()}
        res['night1'] = dict(L_path=paths['L'], L_sha256=sha['L'], vl_json_L=json.load(open(os.path.join(vd, 'vl.json')))['arms']['L'])
        L, _, _ = sleep.load_parent(paths['L'], device)
        L.eval()
    else:
        assert s1dir, "visits != 32: night 1 is rebuilt from S1's day, pass s1dir"
        s3 = json.load(open(os.path.join(s3d, 's3.json')))
        assert s3['args']['lr'] == 1e-3 and s3['args']['visits'] == 32 and s3['seed'] == seed, 'W1 is not the standard night'
        sha = {a: _sha_file(p) for a, p in paths.items() if a != 'L'}
        t0 = time.time()
        full_pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), s3['args']['pool_limit']))
        recs1, rinfo = _w1_records(nprime, name, s1dir, s3, full_pool, N, vocab, device)
        if max_records:
            recs1 = recs1[:max_records]
            rinfo['smoke_truncated_to'] = len(recs1)
        secs['records1'] = time.time() - t0

        def night1():
            t1 = time.time()
            m, si = sleep_on(N, recs1, vocab, replay, warm_rows, 1e-4, visits, seed, device)
            si['seconds'] = time.time() - t1
            return m, si
        L, i1, sha['L'] = _stage(pdir, f1, _h('l1v', sha['N'], 1e-4, visits, seed, len(recs1), rinfo['W1_night'], ja['replay_n'], bool(skills_train)), night1, meta, vocab, device, resume, log)
        L.eval()
        res['night1'] = dict(records=rinfo, sleep=i1, lr=1e-4, visits=visits, L_path=paths['L'], L_sha256=sha['L'])
        log(f1, i1)
    save()
    # 2. day 2 from L (j_parent's W arm: untrained adapter = plain two-pass search)
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    skey = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    t0 = time.time()
    dkey = (skey, s2, sha['L'], _hstate(init), 'L' if std else f1)
    day = _cached(os.path.join(pdir, f'day2_{f1}.pkl'), dkey, lambda: day_f(_arm_model(L, init, seed), pool, vocab, device, T, n1, n2, s2), resume, log, 'day 2 L')
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
        m, si = sleep_on(L, recs, vocab, replay, warm_rows, 1e-4, visits, s2, device)
        si['seconds'] = time.time() - t1
        return m, si
    L2, si, sha['L2'] = _stage(pdir, f2, _h('l2', dkey, len(recs), 1e-4, visits, ja['replay_n'], bool(skills_train)), night2, meta, vocab, device, resume, log)
    secs['night2_L2'] = time.time() - t0
    res['night2'] = dict(si, lr=1e-4, visits=visits)
    log(label, 'night 2', si)
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
        src = dict(N=rd, W1=rd, W2=rd, **({'L': vd} if std else {})).get(a)
        v = (src and _peek(os.path.join(src, f'skills_{a}.pkl'), sk)) or _cached(os.path.join(pdir, f'skills_{tag(a)}.pkl'), sk, lambda a=a: skills_dev(get(a), skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (src and _peek(os.path.join(src, f'c2_{a}.pkl' if a != 'L' else 'c2_L.pkl'), ck)) or _cached(os.path.join(pdir, f'c2_{tag(a)}.pkl'), ck, lambda a=a: greedy_rows(get(a), dev, vocab, device), resume, log, f'c2 dev {a}')
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
            v = _cached(os.path.join(pdir, f'c32_{tag(a)}.pkl'), ('c32', sha[a], dev_limit, mseed, T, 32), fn, resume, log, f'reach32 {a}')
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
    vs_prior = _vs_prior(std, l2dir, vl_L, name, skills_data, skills_limit, dev_limit, mseed, T, dev, rows, hits, c2, c32, hard_ix, res)
    vs_pt = ((vs_prior or {}).get('night2_minus_L2_multi_step_first_try') or {}).get('points')
    hN = harm_measure(hits['N'], hits['L2'], rows)
    ms = bd(right('L2', hard_ix), right('W2', hard_ix))
    res['marks'] = dict(l2_marks(hN['passes'], ms['points'], ms['hi'], vs_pt), in_dist_drop_vs_N=hN['in_dist_drop'], fired_vs_N=hN['fired'], pooled5=res['skills']['L2']['pooled5'], multi_step_first_try_L2_minus_W2=ms,
                        multi_step_n=len(hard_ix), rules=L2_MARKS)
    res['report_only'] = dict(
        multi_step_first_try_L2_minus_N=bd(right('L2', hard_ix), right('N', hard_ix)), climb_mark='job 8: +10 points', pooled_first_try={a: 100 * sum(right(a)) / len(dev) for a in c2},
        pooled_first_try_L2_minus_W2=bd(right('L2'), right('W2')), reach32=res['reach32'], reach32_multi_step_L2_minus_W2=bd(reach('L2', hard_ix), reach('W2', hard_ix)),
        harm_vs_B2={a: {k: v for k, v in harm_measure(hits['B2'], hits[a], rows).items() if k != 'families'} for a in ('N', 'W1', 'W2', 'L', 'L2')} if 'B2' in hits else None,
        night2_own_cost_L2_vs_L={k: v for k, v in harm_measure(hits['L'], hits['L2'], rows).items() if k != 'families'},
        night2_records=res['night2_records'])
    res['report_only']['vs_L2_and_VL'] = vs_prior
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'multi_step', 'passes', 'proved_wrong')})
    return res


def _vs_prior(std, l2dir, vl_L, name, skills_data, skills_limit, dev_limit, mseed, T, dev, rows, hits, c2, c32, hard_ix, res):
    """Report only (visits != 32): this run's night-2 model against L2's (l2dir/<name>/ caches) and its night-1 model against VL's L. None for what the caches (limits) cannot give."""
    if std:
        return None
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    out = dict(note='this run minus the lr 1e-4 / 32-visit chain; unavailable parts are None (limits differ from the caches)')
    l2p = os.path.join(l2dir, name) if l2dir else None
    if l2p and os.path.exists(os.path.join(l2p, 'L2.pt')):
        sh = _sha_file(os.path.join(l2p, 'L2.pt'))
        sk = _peek(os.path.join(l2p, 'skills_L2.pkl'), ('skills', sh, skills_data, skills_limit))
        c = _peek(os.path.join(l2p, 'c2_L2.pkl'), ('c2', sh, dev_limit))
        r32 = _peek(os.path.join(l2p, 'c32_L2.pkl'), ('c32', sh, dev_limit, mseed, T, 32))
        out['L2_night2'] = dict(source=l2p, skills_in_dist=sk and sk[3], c2_first_try=c and 100 * sum(d['right'] for d in c) / len(dev))
        if c:
            right = lambda m, ix: [float(m[i]['right']) for i in ix]
            allix, hix = list(range(len(dev))), list(hard_ix)
            out['night2_minus_L2_multi_step_first_try'] = bd(right(c2['L2'], hix), right(c, hix))
            out['night2_minus_L2_pooled_first_try'] = bd(right(c2['L2'], allix), right(c, allix))
        if sk:
            out['harm_L2_vs_night2'] = {k: v for k, v in harm_measure(sk[1], hits['L2'], rows).items() if k != 'families'}
        if r32:
            out['night2_minus_L2_reach32_pooled'] = bd([float(x['right32']) for x in c32['L2']], [float(x['right32']) for x in r32])
            out['night2_minus_L2_reach32_multi_step'] = bd([float(c32['L2'][i]['right32']) for i in hard_ix], [float(r32[i]['right32']) for i in hard_ix])
    if os.path.exists(vl_L):
        sh = _sha_file(vl_L)
        sk = _peek(os.path.join(os.path.dirname(vl_L), 'skills_L.pkl'), ('skills', sh, skills_data, skills_limit))
        c = _peek(os.path.join(os.path.dirname(vl_L), 'c2_L.pkl'), ('c2', sh, dev_limit))
        out['night1_vs_VL_L'] = dict(VL_L_in_dist=sk and sk[3], night1_in_dist=res['skills']['L']['in_dist'], VL_L_c2_first_try=c and 100 * sum(d['right'] for d in c) / len(dev),
                                     night1_c2_first_try=100 * res['c2_dev']['L']['first_try_right'])
    return out


def l2(nprimes, out, s3dir, jdir, rdir, vldir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: l2_parent(p, out, s3dir, jdir, rdir, vldir, s1wdir, **kw) for p in nprimes}


def l2report(out, parents, file='l2.json', label='L2'):
    """-> DIR/l2-report.json: per-parent marks, the verdict (passes on both parents), proved_wrong (on both), and the next-step text."""
    res = {p: json.load(open(os.path.join(out, p, file))) for p in parents}
    pm = {p: {k: x['marks'].get(k) for k in ('harm', 'multi_step', 'passes', 'proved_wrong', 'proved_wrong_no_climb')} for p, x in res.items()}
    rep = dict(parents=list(parents), label=label, per_parent=pm, verdict=l2_verdict(pm), rules=L2_MARKS, next=L2_NEXT,
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], report_only=x['report_only'], day2=x['day2'], night2=x['night2'], night1=x.get('night1')) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'l2-report.json' if label == 'L2' else f'{label.lower()}-report.json'), 'w'), indent=1)
    return rep



# ---------------------------------------------------------------- Test SC (roadmap a92e5945fe): the model picks its own skills replay
SC_MARKS = dict(harm="(1) harm_measure(N' DEV hits, SC DEV hits) passes: in_dist drop <= 1.5 and no family fires",
                first_try='(2) C2 DEV first try: c2_pilot.boot(SC right, W1 right) point >= -2.0',
                reach32='(3) multi-step reach@32 (HARD_KINDS, 154 questions): SC - W1 point >= -3.0',
                passes='passes = (1) and (2) and (3) on a parent; the verdict needs both parents',
                proved_wrong="SC's in_dist drop vs N' is NOT at least 1.0 smaller than W1's drop vs N' (SC_drop > W1_drop - 1.0) on BOTH parents (decided in the report)")
SC_RECIPE = ("night 1 = W1's exact recipe (835 / 808 records, lr 1e-3, 32 visits, W1's seed, warm replay, schedule) with ONE change: after the first 32 updates, every 32 updates 1,024 fresh skills TRAIN rows are scored "
             "(loss now - loss of the frozen pre-night N'), the 256 with the largest rise are the skills replay of the next 32 updates (512 slots, ~2 visits each, seeded shuffled)")
SC_EVERY, SC_DRAW, SC_PICK = 32, 1024, 256


def sc_marks(harm_passes, c2_point, reach_point, sc_drop, w1_drop):
    """Pure. -> the SC marks on one parent (points; drops vs N')."""
    f, r = bool(c2_point >= -2.0), bool(reach_point >= -3.0)
    return dict(harm=bool(harm_passes), first_try=f, reach32=r, passes=bool(harm_passes and f and r), proved_wrong=bool(sc_drop > w1_drop - 1.0))


SC_SCORECARD = dict(source="big-run PLAN.md SCORECARD 10-09 row 5 (11:00 AM ET); set as SC's marks by the roadmap (097902443a, proved-wrong wording 5a1efd4d20, near-miss rule 10-09 11:21 AM ET) before any result. These govern the verdict; SC_MARKS are report only",
                    gain="gain = C2 DEV first try minus N' first try (points); ratio = SC gain / W1 gain (W1 = the same night with hand-picked uniform skills replay)",
                    passes="on BOTH parents: harm_measure(N' DEV hits, SC DEV hits) passes (in_dist drop <= 1.5, no family fires) and mark 2 is met",
                    mark2="the 0.9x ratio governs (the roadmap's 28.1 / 31.0 floors were rounding). A shortfall of ONE question (one more right DEV answer would reach 0.9x, e.g. 72 of 256 on s100, ratio 0.899) counts as met under Ben's near-miss rule; short by two or more questions fails",
                    proved_wrong="harm fails on EITHER parent, or ratio < 0.5 on BOTH parents",
                    scope="this SC picks only its replay rows; the scorecard row also names nights and temperature, which this run does not let the model pick")


def sc_scorecard(sc_ft, w1_ft, n_ft, harm_passes, n=256, keys=('gain_SC', 'gain_W1')):
    """Pure. First-try percents for SC, W1 and N' on n DEV questions -> the scorecard marks on one parent. questions_short = how many more right answers SC
    needs for ratio >= 0.9 (0 = met outright, 1 = near miss, counted as met); low = ratio under 0.5, or no W1 gain to compare with.
    keys = the names of the two gains in the result (SC's default; SCL / SCM pass ('gain_test', 'gain_control') because their control is not W1 / SC)."""
    g_sc, g_w1 = sc_ft - n_ft, w1_ft - n_ft
    ratio = g_sc / g_w1 if g_w1 > 0 else float('nan')
    if g_w1 > 0:
        short = max(0, math.ceil(round((0.9 * g_w1 - g_sc) * n / 100, 9)))
    else:
        short = None
    m2 = short is not None and short <= 1
    return dict({keys[0]: g_sc, keys[1]: g_w1}, ratio=ratio, harm=bool(harm_passes), questions_short=short, near_miss=short == 1, mark2=bool(m2), low=bool(not ratio >= 0.5),
                passes=bool(m2 and harm_passes))


def sc_scorecard_verdict(per_parent):
    """Pure. {parent: sc_scorecard} -> passes on every parent; proved wrong = harm fails on any parent, or low on every parent."""
    return dict(passes=all(m['passes'] for m in per_parent.values()),
                proved_wrong=any(not m['harm'] for m in per_parent.values()) or all(m['low'] for m in per_parent.values()),
                harm_failed_on=[p for p, m in per_parent.items() if not m['harm']], low_on=[p for p, m in per_parent.items() if m['low']])


def sc_verdict(per_parent):
    """Pure. {parent: sc_marks} -> passes on every parent, proved_wrong on every parent, where the parents disagree."""
    return dict(passes=all(m['passes'] for m in per_parent.values()), proved_wrong=all(m['proved_wrong'] for m in per_parent.values()),
                disagree=[k for k in ('harm', 'first_try', 'reach32', 'passes', 'proved_wrong') if len({m[k] for m in per_parent.values()}) > 1])


def row_losses(model, rows, vocab, device='cpu', bs=128):
    """Per-row model.loss (Ledger): the same terms as ledger.Ledger.loss with the batch mean left out, so mean(row_losses) == model.loss on the same batch (checked in the tests). Eval mode, no grad;
    the model is returned to its previous mode. -> list of floats."""
    import torch.nn.functional as F
    from custom_io.data import Dataset, collate, to_device
    from custom_io.models import ledger as LG
    was = model.training
    model.eval()
    out = []
    with torch.no_grad():
        for s0 in range(0, len(rows), bs):
            rs = rows[s0:s0 + bs]
            ds = Dataset(rs, vocab, strict=False)
            batch = to_device(collate([ds[i] for i in range(len(rs))]), device)
            dev = batch['prompt_ids'].device
            g = model.gold(batch['rows'], dev)
            o = model.run(batch, gold=g)
            w_row = torch.where(g['has'], 1.0, model.w_noop)
            comm = torch.isin(g['op'], torch.tensor(LG.COMM, device=dev))
            tot = 0.0
            for st, (lg, la, lb) in enumerate(o['steps']):
                lg = lg.float()
                tot = tot + F.cross_entropy(lg, g['op'][:, st], reduction='none') * w_row
                pa, pb = la.log_softmax(-1), lb.log_softmax(-1)
                ga, gb = g['a'][:, st], g['b'][:, st]
                lab = torch.logsumexp(pa.masked_fill(~ga, -1e9), -1) + torch.logsumexp(pb.masked_fill(~gb, -1e9), -1)
                lba = torch.logsumexp(pa.masked_fill(~gb, -1e9), -1) + torch.logsumexp(pb.masked_fill(~ga, -1e9), -1)
                nll = -torch.where(comm[:, st], torch.logaddexp(lab, lba), lab)
                tot = tot + nll * (g['op'][:, st] > 0)
            marg = lambda lg, m, sel: torch.where(sel, -(torch.logsumexp(lg.masked_fill(~m, -1e9), -1) - torch.logsumexp(lg, -1)), torch.zeros_like(lg[:, 0]))
            tot = tot + F.cross_entropy(o['lmode'].float(), g['mode'], reduction='none') + marg(o['lans'], g['ans'], g['mode'] == 0) + marg(o['lword'], g['word'], g['mode'] == 1)
            n_t = (g['gen'] >= 0).sum(1).clamp(min=1)
            if model.copy:
                p, gate = model.gen_copy(o['R'], o['X'], o['xm'], batch['prompt_ids'])
                tg = g['gen']
                ce = -torch.log(p.gather(2, tg.clamp(min=0)[..., None])[..., 0] + 1e-6).masked_fill(tg < 0, 0.0)
            else:
                ce = F.cross_entropy(model.readout(o['R']).float().flatten(0, 1), g['gen'].flatten(), ignore_index=-100, reduction='none').view(len(rs), -1)
            tot = tot + (ce.sum(1) / n_t) * (g['mode'] == 2)
            out += [float(x) for x in tot]
    model.train(was)
    return out


def sleep_sc(model, records, replay_rows, vocab, cfg, device='cpu', replay_extra=None, frozen=None, select=True, every=SC_EVERY, n_draw=SC_DRAW, n_pick=SC_PICK, log=None):
    """A faithful copy of sleep.sleep's loop (same rng consumption, same order lists, same optimiser groups, schedule, clip) with a hook on the skills-replay slots: with select=False it is sleep.sleep bit
    for bit. With select=True, at every `every`-th update from update `every` on, `n_draw` fresh rows of `replay_rows` (random.Random(seed + 5000 + step)) are scored under the current model and under
    `frozen` (default: a copy of the model before the night), the `n_pick` with the largest loss rise are the skills replay of the next `every` updates (balanced seeded order). -> sleep.sleep's dict + selection
    (per round: step, family counts of the picked rows, mean rise picked / all, score_seconds) and score_seconds."""
    from custom_io.data import Dataset, collate, to_device
    from custom_io.train import lr_at
    if not records:
        return dict(loss=[], visits={}, updates=0, selection=[], score_seconds=0.0)
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('puzzle record ids must be unique (the target cache is keyed by id)')
    sleep.check_visits(len(records), cfg, bool(replay_rows))
    half = cfg.batch // 2 if replay_rows else cfg.batch
    draws = cfg.updates * half
    rng = random.Random(cfg.seed)
    torch.manual_seed(cfg.seed)
    rec_order = sleep._order(len(records), draws, rng)
    nrep = cfg.batch - half
    n_extra = nrep // 2 if (replay_rows and replay_extra) else 0
    rep_order = sleep._order(len(replay_rows), cfg.updates * (nrep - n_extra), rng) if replay_rows else []
    ext_order = sleep._order(len(replay_extra), cfg.updates * n_extra, rng) if n_extra else []
    if select and frozen is None:
        frozen = copy.deepcopy(model)
        frozen.eval()
        for p in frozen.parameters():
            p.requires_grad_(False)
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': cfg.weight_decay}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=cfg.lr, betas=(0.9, 0.95), fused=torch.device(device).type == 'cuda')
    visits, losses, sel, slots, score_s = {}, [], [], None, 0.0
    k = nrep - n_extra
    model.train()
    for step in range(cfg.updates):
        if select and replay_rows and step >= every and step % every == 0:
            t0 = time.time()
            drawn = random.Random(cfg.seed + 5000 + step).sample(replay_rows, min(n_draw, len(replay_rows)))
            now, then = row_losses(model, drawn, vocab, device), row_losses(frozen, drawn, vocab, device)
            rise = [a - b for a, b in zip(now, then)]
            top = sorted(range(len(drawn)), key=lambda i: -rise[i])[:n_pick]
            picked = [drawn[i] for i in top]
            order = sleep._order(len(picked), every * k, random.Random(cfg.seed + 6000 + step))
            slots = [picked[i] for i in order]
            dt = time.time() - t0
            score_s += dt
            sel.append(dict(step=step, families=dict(collections.Counter(r['family'] for r in picked)), mean_rise_picked=sum(rise[i] for i in top) / len(top), mean_rise_all=sum(rise) / len(rise),
                            drawn=len(drawn), score_seconds=dt))
            model.train()
            if log:
                log('SC select', step, dict(rise_picked=round(sel[-1]['mean_rise_picked'], 4), rise_all=round(sel[-1]['mean_rise_all'], 4), seconds=round(dt, 1)))
        rows = [records[i] for i in rec_order[step * half:(step + 1) * half]]
        if slots is not None:
            j = (step % every) * k
            rows += slots[j:j + k]
        else:
            rows += [replay_rows[i] for i in rep_order[step * k:(step + 1) * k]]
        rows += [replay_extra[i] for i in ext_order[step * n_extra:(step + 1) * n_extra]]
        for r in rows[:half]:
            visits[r['id']] = visits.get(r['id'], 0) + 1
        ds = Dataset(rows, vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(rows))]), device)
        for g in opt.param_groups:
            g['lr'] = lr_at(step, cfg.updates, cfg.warmup, cfg.lr)
        out = model.loss(batch)
        loss, aux = out if isinstance(out, tuple) else (out, {})
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
    assert max(visits.values()) <= cfg.max_visits, 'a record was seen too often'
    return dict(loss=losses, visits=visits, updates=cfg.updates, selection=sel, score_seconds=score_s)


def _sc_night(N, recs, replay, warm_rows, vocab, lr, visits, seed, device, log, select=True):
    """sleep7d.sleep_on's recipe through sleep_sc. -> (model, info)."""
    m = copy.deepcopy(N)
    u = visits * len(recs) // 32
    per = 32 if replay else 64
    mv = max(visits, math.ceil(u * per / max(len(recs), 1)))
    t0 = time.time()
    so = sleep_sc(m, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows, frozen=None, select=select, log=log)
    m.eval()
    sel = so['selection']
    fam_all = collections.Counter()
    for r in sel:
        fam_all.update(r['families'])
    pool_mix = collections.Counter(r['family'] for r in replay)
    n_pick = sum(fam_all.values())
    return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / max(len(recs), 1), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1) if so['loss'] else None,
                   rounds=sel, picked_family_share={f: fam_all[f] / max(n_pick, 1) for f in sorted(pool_mix)}, pool_family_share={f: pool_mix[f] / len(replay) for f in sorted(pool_mix)},
                   seconds=time.time() - t0, score_seconds=so['score_seconds'], train_seconds=time.time() - t0 - so['score_seconds'])


def sc_parent(nprime, out, s1dir, s3dir, rdir, s1wdir, skills_train, skills_data, seed=0, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True, log=_log, max_records=None, b2=None):
    """One parent's Test SC. DIR/<name>/sc.json is written after every stage; SC.pt is a cached stage. Reuses (key-checked, read only) R's skills / c2 caches for N' and W1 and S1w's measure_U (W1 reach@32).
    max_records = smoke only (recorded)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, rd, s1wd = (os.path.join(d, name) for d in (out, s3dir, rdir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed, T = s3['seed'], s3['T']
    mseed = seed + 777
    assert a3['lr'] == 1e-3 and a3['visits'] == 32, 'W1 is not the standard night'
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], recipe=SC_RECIPE, marks_rules=SC_MARKS, secs=secs,
               args=dict(seed=seed, night_seed=seed, T=T, measure_seed=mseed, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, every=SC_EVERY, draw=SC_DRAW, pick=SC_PICK, s1=s1dir, s3=s3dir,
                         r=rdir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data, b2=b2),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened; the pick uses only skills TRAIN rows and the model\'s own losses')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'sc.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, a3['replay_n'], seed)
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), a3['pool_limit']))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    w1p = os.path.join(s3d, 'W1.pt')
    sha = dict(N=_sha_file(nprime), W1=_sha_file(w1p))
    t0 = time.time()
    recs, res['records'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    secs['records'] = time.time() - t0
    if max_records:
        recs = recs[:max_records]
        res['records']['smoke_truncated_to'] = len(recs)
    save()
    t0 = time.time()
    SC, info, sha['SC'] = _stage(pdir, 'SC', _h('sc', sha['N'], 1e-3, 32, seed, len(recs), res['records']['W1_night'], a3['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK),
                                 lambda: _sc_night(N, recs, replay, warm_rows, vocab, 1e-3, 32, seed, device, log), meta, vocab, device, resume, log)
    secs['SC'] = time.time() - t0
    res['night'] = {k: v for k, v in info.items() if k not in ('rounds', 'picked_family_share', 'pool_family_share')}
    res['selection'] = dict(rounds=info['rounds'], picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                            rise_picked_vs_all=[(r['step'], r['mean_rise_picked'], r['mean_rise_all']) for r in info['rounds']])
    log('SC night', res['night'])
    save()
    # measures: N', W1 (R / S1w caches), SC
    W1, _, _ = sleep.load_parent(w1p, device)
    W1.eval()
    allm = dict(N=N, W1=W1, SC=SC)
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    for a, m in allm.items():
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        v = (_peek(os.path.join(rd, f'skills_{a}.pkl'), sk) if a != 'SC' else None) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (_peek(os.path.join(rd, f'c2_{a}.pkl'), ck) if a != 'SC' else None) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
        c2[a] = c
        res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    if b2 and os.path.exists(os.path.expanduser(b2)):
        b2p = os.path.expanduser(b2)
        bv = _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', _sha_file(b2p), skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2p, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
    for a in ('W1', 'SC'):
        t0 = time.time()
        v, how = None, 'computed'
        mu = os.path.join(s1wd, 'measure_U.pkl')
        if a == 'W1' and os.path.exists(mu):
            c = pickle.load(open(mu, 'rb'))
            kk = c['key']
            ok = kk[1] == 'U' and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and len(c['v']['c32']) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
            if ok:
                v, how = c['v']['c32'], f'reused {mu}'
        if v is None:
            def fn(a=a):
                mm = _arm_model(allm[a], init, seed)
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
    # marks
    hard_ix = [i for i, r in enumerate(dev) if r['kind'] in c2_pilot.HARD_KINDS]
    if not dev_limit:
        assert len(hard_ix) == 154, f'{len(hard_ix)} multi-step DEV questions, expected 154'
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    right = lambda a: [float(d['right']) for d in c2[a]]
    reach = lambda a: [float(c32[a][i]['right32']) for i in hard_ix]
    hN, hW = harm_measure(hits['N'], hits['SC'], rows), harm_measure(hits['W1'], hits['SC'], rows)
    w1_drop = res['skills']['N']['in_dist'] - res['skills']['W1']['in_dist']
    ft, rc = bd(right('SC'), right('W1')), bd(reach('SC'), reach('W1'))
    res['marks'] = dict(sc_marks(hN['passes'], ft['points'], rc['points'], hN['in_dist_drop'], w1_drop), in_dist_drop_vs_N=hN['in_dist_drop'], W1_in_dist_drop_vs_N=w1_drop, fired_vs_N=hN['fired'],
                        first_try_SC_minus_W1=ft, multi_step_reach32_SC_minus_W1=rc, multi_step_n=len(hard_ix), W1_multi_step_reach32=res['reach32']['W1']['multi_step'], rules=SC_MARKS)
    res['report_only'] = dict(harm_vs_W1={k: v for k, v in hW.items() if k != 'families'}, pooled5=dict(N=res['skills']['N']['pooled5'], W1=res['skills']['W1']['pooled5'], SC=res['skills']['SC']['pooled5']),
                              harm_vs_B2={a: {k: v for k, v in harm_measure(hits['B2'], hits[a], rows).items() if k != 'families'} for a in ('N', 'W1', 'SC')} if 'B2' in hits else None,
                              reach32=res['reach32'], pooled_first_try_SC_minus_W1=bd(right('SC'), right('W1')), cpu_seconds=dict(night=secs['SC'], scoring=info['score_seconds'], measures=sum(v for k, v in secs.items() if k.startswith(('measure_', 'reach32_')))))
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'first_try', 'reach32', 'passes', 'proved_wrong')})
    return res


def sc(nprimes, out, s1dir, s3dir, rdir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: sc_parent(p, out, s1dir, s3dir, rdir, s1wdir, **kw) for p in nprimes}


def screport(out, parents):
    """-> DIR/sc-report.json: the scorecard verdict (SC_SCORECARD governs), the roadmap's SC_MARKS as report only, tables."""
    res = {p: json.load(open(os.path.join(out, p, 'sc.json'))) for p in parents}
    pm = {p: {k: x['marks'][k] for k in ('harm', 'first_try', 'reach32', 'passes', 'proved_wrong')} for p, x in res.items()}
    ft = lambda x, a: 100 * x['c2_dev'][a]['first_try_right']
    sp = {p: dict(sc_scorecard(ft(x, 'SC'), ft(x, 'W1'), ft(x, 'N'), x['marks']['harm'], x['c2_dev']['SC']['n']), SC_first_try=ft(x, 'SC'), W1_first_try=ft(x, 'W1'), N_first_try=ft(x, 'N'),
                  in_dist_drop_vs_N=x['marks']['in_dist_drop_vs_N'], fired_vs_N=x['marks']['fired_vs_N']) for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=sp, verdict=sc_scorecard_verdict(sp), rules=SC_SCORECARD, recipe=SC_RECIPE,
               near_miss_on=[p for p, m in sp.items() if m['near_miss']],
               report_only_roadmap_marks=dict(label='report only (roadmap 097902443a): the original SC marks', rules=SC_MARKS, per_parent=pm, verdict=sc_verdict(pm)),
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], report_only=x['report_only'], night=x['night'], selection=x['selection']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'sc-report.json'), 'w'), indent=1)
    return rep



# ---------------------------------------------------------------- Test SCL (roadmap e5ab95d650): SC's self-picked skills replay on VL's arm L (lr 1e-4, 32 visits)
SCL_RECIPE = ("night 1 from N' = VL's arm L exactly (W1's records, lr 1e-4, 32 visits, W1's seed, warm replay, schedule) with ONE change, SC's: after the first 32 updates, every 32 updates 1,024 fresh skills TRAIN rows "
              "are scored (loss now - loss of the frozen pre-night N'), the 256 with the largest rise are the skills replay of the next 32 updates. Control = VL's L (uniform replay), already trained")
SCL_LR, SCL_VISITS = 1e-4, 32
GAIN_KEYS = ('gain_test', 'gain_control')      # SCL / SCM: the test arm's gain over N' and the control arm's (L for SCL, W1 for SCM)
SCL_SCORECARD = dict(source="roadmap e5ab95d650 (Test SCL), set before any result; same form as SC's scorecard with L (VL's lr 1e-4 night) in W1's place",
                     gain="gain = C2 DEV first try minus N' first try (points); ratio = SCL gain / L gain",
                     passes="on BOTH parents: harm_measure(N' DEV hits, SCL DEV hits) passes (in_dist drop <= 1.5, no family fires) and first-try gain over N' >= 0.9x L's gain",
                     near_miss="as in SC: a shortfall of exactly ONE DEV question counts as met; two or more fails (questions_short is reported)",
                     proved_wrong="harm fails on EITHER parent, or gain < 0.5x L's on BOTH parents",
                     report_only="SCL - L and SCL - W1 first try (paired boot), multi-step reach@32 SCL - L and SCL - W1, in_dist drop SCL vs L, harm SCL vs L and vs W1, harm vs B2, picked family mix, loss rise picked vs random, CPU seconds")


def scl_parent(nprime, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, skills_train, skills_data, seed=0, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True, log=_log, max_records=None, b2=None):
    """One parent's Test SCL. DIR/<name>/scl.json is written after every stage; SCL.pt is a cached stage. Reuses (key-checked, read only): R's skills / c2 caches for N', VL's for L (and L.pt), L2's c32_L.pkl for
    L's reach@32. Asserts VL's L was trained with this night's records count, lr 1e-4, 32 visits and seed. max_records = smoke only (recorded; L's key check is then skipped)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, rd, vd, l2d, s1wd = (os.path.join(d, name) for d in (out, s3dir, rdir, vldir, l2dir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed, T = s3['seed'], s3['T']
    mseed = seed + 777
    assert a3['lr'] == 1e-3 and a3['visits'] == 32, 'W1 is not the standard night'
    vj = json.load(open(os.path.join(vd, 'vl.json')))
    vL = vj['arms']['L']
    assert vL['lr'] == SCL_LR and vL['visits'] == SCL_VISITS and vj['args']['seed'] == seed and vj['args']['night_seed'] == seed, "VL's L is not lr 1e-4 / 32 visits / this seed"
    assert vj['records']['rebuilt'] == vj['records']['W1_night'] and not vj['args'].get('max_records') and vj['args']['s3_args'] == a3, "VL's L was not trained on the full W1 records of this S3 run"
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], recipe=SCL_RECIPE, marks_rules=SCL_SCORECARD, secs=secs,
               args=dict(seed=seed, night_seed=seed, T=T, measure_seed=mseed, lr=SCL_LR, visits=SCL_VISITS, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, every=SC_EVERY, draw=SC_DRAW, pick=SC_PICK,
                         s1=s1dir, s3=s3dir, r=rdir, vl=vldir, l2=l2dir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data, b2=b2),
               night_L=vL, note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened; the pick uses only skills TRAIN rows and the model\'s own losses')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'scl.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, a3['replay_n'], seed)
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), a3['pool_limit']))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    lp = os.path.join(vd, 'L.pt')
    w1p = os.path.join(s3d, 'W1.pt')
    sha = dict(N=_sha_file(nprime), L=_sha_file(lp), W1=_sha_file(w1p))
    t0 = time.time()
    recs, res['records'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    secs['records'] = time.time() - t0
    want = res['records']['W1_night']
    # VL's stage key for L, recomputed: the same N', lr, visits, seed, records count, replay setting
    lkey = _h('vl', sha['N'], SCL_LR, SCL_VISITS, seed, len(recs), want, a3['replay_n'], bool(skills_train))
    lpk = pickle.load(open(os.path.join(vd, 'L.pkl'), 'rb'))['key']
    if max_records:
        recs = recs[:max_records]
        res['records']['smoke_truncated_to'] = len(recs)
        res['L_key_check'] = 'skipped (smoke truncation)'
    else:
        assert lpk == lkey, "VL's L stage key differs from the key of lr 1e-4 / 32 visits / this seed / these records"
        res['L_key_check'] = 'equal'
    save()
    t0 = time.time()
    SCL, info, sha['SCL'] = _stage(pdir, 'SCL', _h('scl', sha['N'], SCL_LR, SCL_VISITS, seed, len(recs), want, a3['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK),
                                   lambda: _sc_night(N, recs, replay, warm_rows, vocab, SCL_LR, SCL_VISITS, seed, device, log), meta, vocab, device, resume, log)
    secs['SCL'] = time.time() - t0
    res['night'] = {k: v for k, v in info.items() if k not in ('rounds', 'picked_family_share', 'pool_family_share')}
    res['selection'] = dict(rounds=info['rounds'], picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                            rise_picked_vs_all=[(r['step'], r['mean_rise_picked'], r['mean_rise_all']) for r in info['rounds']])
    log('SCL night', res['night'])
    save()
    # measures: N' (R's caches), L (VL's caches, L.pt), SCL
    L, _, _ = sleep.load_parent(lp, device)
    L.eval()
    W1, _, _ = sleep.load_parent(w1p, device)
    W1.eval()
    allm = dict(N=N, L=L, W1=W1, SCL=SCL)      # W1 = report only
    src = dict(N=rd, L=vd, W1=rd)
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    for a, m in allm.items():
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        v = (a in src and _peek(os.path.join(src[a], f'skills_{a}.pkl'), sk)) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (a in src and _peek(os.path.join(src[a], f'c2_{a}.pkl'), ck)) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
        c2[a] = c
        res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    if b2 and os.path.exists(os.path.expanduser(b2)):
        b2p = os.path.expanduser(b2)
        bv = _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', _sha_file(b2p), skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2p, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
    for a in ('L', 'W1', 'SCL'):
        t0 = time.time()
        v, how = None, 'computed'
        key = ('c32', sha[a], dev_limit, mseed, T, 32)
        if a == 'W1':
            mu = os.path.join(s1wd, 'measure_U.pkl')
            if os.path.exists(mu):
                c = pickle.load(open(mu, 'rb'))
                kk = c['key']
                ok = kk[1] == 'U' and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and len(c['v']['c32']) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
                if ok:
                    v, how = c['v']['c32'], f'reused {mu}'
        if a == 'L':
            v = _peek(os.path.join(l2d, 'c32_L.pkl'), key)
            if v is not None and len(v) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(v, dev)):
                how = f"reused {os.path.join(l2d, 'c32_L.pkl')}"
            else:
                v = None
        if v is None:
            def fn(a=a):
                mm = _arm_model(allm[a], init, seed)
                with creative(mm, True):
                    smp = legal.raw_samples(mm, dev, vocab, device, n=32, temperature=T, level=0, seed=mseed)
                return score_rows(dev, smp, ks=(32,))
            v = _cached(os.path.join(pdir, f'c32_{a}.pkl'), key, fn, resume, log, f'reach32 {a}')
        c32[a] = v
        hard = [x['right32'] for x, r in zip(v, dev) if r['kind'] in c2_pilot.HARD_KINDS]
        res['reach32'][a] = dict(pooled=100 * sum(x['right32'] for x in v) / len(v), multi_step=100 * sum(hard) / max(len(hard), 1), source=how)
        secs[f'reach32_{a}'] = time.time() - t0
        log('reach32', a, res['reach32'][a])
        save()
    # marks
    hard_ix = [i for i, r in enumerate(dev) if r['kind'] in c2_pilot.HARD_KINDS]
    if not dev_limit:
        assert len(hard_ix) == 154, f'{len(hard_ix)} multi-step DEV questions, expected 154'
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    right = lambda a: [float(d['right']) for d in c2[a]]
    reach = lambda a: [float(c32[a][i]['right32']) for i in hard_ix]
    slim = lambda h: {k: v for k, v in h.items() if k != 'families'}
    hN, hNL, hL = harm_measure(hits['N'], hits['SCL'], rows), harm_measure(hits['N'], hits['L'], rows), harm_measure(hits['L'], hits['SCL'], rows)
    hW = harm_measure(hits['W1'], hits['SCL'], rows)
    ft, rc = bd(right('SCL'), right('L')), bd(reach('SCL'), reach('L'))
    pct = lambda a: 100 * res['c2_dev'][a]['first_try_right']
    res['marks'] = dict(sc_scorecard(pct('SCL'), pct('L'), pct('N'), hN['passes'], res['c2_dev']['SCL']['n'], keys=GAIN_KEYS), SCL_first_try=pct('SCL'), L_first_try=pct('L'), N_first_try=pct('N'),
                        in_dist_drop_vs_N=hN['in_dist_drop'], fired_vs_N=hN['fired'], rules=SCL_SCORECARD)
    rs = info['rounds']
    res['report_only'] = dict(first_try_SCL_minus_L=ft, multi_step_reach32_SCL_minus_L=rc, multi_step_n=len(hard_ix), first_try_SCL_minus_W1=bd(right('SCL'), right('W1')),
                              multi_step_reach32_SCL_minus_W1=bd(reach('SCL'), reach('W1')), harm_SCL_vs_W1=slim(hW), W1_in_dist_drop_vs_N=res['skills']['N']['in_dist'] - res['skills']['W1']['in_dist'],
                              in_dist_drop_vs_N=dict(SCL=hN['in_dist_drop'], L=hNL['in_dist_drop'], SCL_minus_L=hN['in_dist_drop'] - hNL['in_dist_drop']),
                              harm_vs_N=dict(SCL=slim(hN), L=slim(hNL)), harm_SCL_vs_L=slim(hL),
                              harm_vs_B2={a: slim(harm_measure(hits['B2'], hits[a], rows)) for a in ('N', 'L', 'W1', 'SCL')} if 'B2' in hits else None,
                              picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                              loss_rise_picked_vs_random=dict(picked=sum(r['mean_rise_picked'] for r in rs) / len(rs) if rs else None, random=sum(r['mean_rise_all'] for r in rs) / len(rs) if rs else None, rounds=len(rs)),
                              pooled5=dict(N=res['skills']['N']['pooled5'], L=res['skills']['L']['pooled5'], W1=res['skills']['W1']['pooled5'], SCL=res['skills']['SCL']['pooled5']), reach32=res['reach32'],
                              cpu_seconds=dict(night=secs['SCL'], scoring=info['score_seconds'], measures=sum(v for k, v in secs.items() if k.startswith(('measure_', 'reach32_')))))
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'ratio', 'questions_short', 'mark2', 'low', 'passes')})
    return res


def scl(nprimes, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: scl_parent(p, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, **kw) for p in nprimes}


def sclreport(out, parents):
    """-> DIR/scl-report.json: the scorecard verdict (SCL_SCORECARD governs; gain_test / gain_control in the rows are SCL's and L's gain over N'), the report-only block, tables."""
    res = {p: json.load(open(os.path.join(out, p, 'scl.json'))) for p in parents}
    pp = {p: {k: v for k, v in x['marks'].items() if k != 'rules'} for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=pp, verdict=sc_scorecard_verdict(pp), rules=SCL_SCORECARD, recipe=SCL_RECIPE, near_miss_on=[p for p, m in pp.items() if m['near_miss']],
               questions_short={p: m['questions_short'] for p, m in pp.items()}, report_only={p: x['report_only'] for p, x in res.items()},
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], night=x['night'], selection=x['selection'], night_L=x['night_L']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'scl-report.json'), 'w'), indent=1)
    return rep



# ---------------------------------------------------------------- Test SCM (roadmap 10-09): SCL's recipe with ONE change, lr 3e-4; control = W1
SCM_LR, SCM_VISITS = 3e-4, 32
SCM_RECIPE = ("night 1 from N' = SCL's night exactly (SC's model-picked skills replay, same pick rule / sizes / pick seeds; W1's records, 32 visits, W1's seed, warm replay, schedule) with ONE change: lr 3e-4 "
              "(SCL = 1e-4, SC = 1e-3). Control = S3's W1 (lr 1e-3, uniform replay), already trained")
SCM_REACH_SLACK, SCM_VS_SCL_MIN = 3.0, 3.0     # points
SCM_SCORECARD = dict(source="roadmap 10-09 (Test SCM), fixed before the run; same form as SCL's scorecard with W1 in L's place",
                     gain="gain = C2 DEV first try minus N' first try (points); ratio = SCM gain / W1 gain (gain_test = SCM's, gain_control = W1's)",
                     passes="on BOTH parents: (1) harm_measure(N' DEV hits, SCM DEV hits) passes (in_dist drop <= 1.5, no family fires); (2) first-try gain over N' >= 0.9x W1's gain, a shortfall of exactly ONE DEV question "
                            "counts as met, two or more fails (questions_short reported); (3) multi-step reach@32 (HARD_KINDS, 154 questions) SCM >= W1's minus 3 points",
                     proved_wrong="harm fails on EITHER parent, or multi-step reach@32 SCM minus SCL is under +3 points on BOTH parents",
                     report_only="SCM vs SCL and vs W1 on everything (first try paired boot, in_dist via harm_measure with families omitted, multi-step and pooled reach@32), harm vs B2, picked family mix, loss rise picked vs random, CPU seconds")


def scm_marks(harm_passes, scorecard, scm_reach, w1_reach):
    """Pure. scorecard = sc_scorecard(...) for SCM with W1 as control on one parent; reach = multi-step reach@32 in points. -> the SCM marks on one parent (mark 3: SCM >= W1 - 3.0, inclusive)."""
    reach_ok = bool(round(scm_reach - (w1_reach - SCM_REACH_SLACK), 9) >= 0)
    return dict(harm=bool(harm_passes), mark2=bool(scorecard['mark2']), questions_short=scorecard['questions_short'], reach_ok=reach_ok,
                passes=bool(harm_passes and scorecard['mark2'] and reach_ok))


def scm_vs_scl(scm_reach, scl_reach):
    """Pure. -> multi-step reach@32 SCM minus SCL (points) and whether it is under +3.0 (the proved-wrong half)."""
    d = scm_reach - scl_reach
    return dict(scm_minus_scl=d, under_3=bool(round(d - SCM_VS_SCL_MIN, 9) < 0))


def scm_verdict(per_parent):
    """Pure. {parent: scm_marks + scm_vs_scl fields} -> passes on every parent; proved wrong = harm fails on any parent, or SCM - SCL reach under +3 on every parent."""
    return dict(passes=all(m['passes'] for m in per_parent.values()),
                proved_wrong=any(not m['harm'] for m in per_parent.values()) or all(m['under_3'] for m in per_parent.values()),
                harm_failed_on=[p for p, m in per_parent.items() if not m['harm']], under_3_on=[p for p, m in per_parent.items() if m['under_3']])


def scm_parent(nprime, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, sclrdir, skills_train, skills_data, seed=0, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True, log=_log, max_records=None, b2=None):
    """One parent's Test SCM. DIR/<name>/scm.json is written after every stage; SCM.pt is a cached stage. Reuses (key-checked, read only): R's skills / c2 caches for N' and W1, S1w's measure_U for W1's reach@32,
    SCL's finished model and skills / c2 / c32 caches under sclrdir/<name>/ (recomputed into DIR only if their keys do not match). vldir / l2dir are accepted for CLI symmetry with scl and unused."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, rd, s1wd, sd = (os.path.join(d, name) for d in (out, s3dir, rdir, s1wdir, sclrdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed, T = s3['seed'], s3['T']
    mseed = seed + 777
    assert a3['lr'] == 1e-3 and a3['visits'] == 32, 'W1 is not the standard night'
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], recipe=SCM_RECIPE, marks_rules=SCM_SCORECARD, secs=secs,
               args=dict(seed=seed, night_seed=seed, T=T, measure_seed=mseed, lr=SCM_LR, visits=SCM_VISITS, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, every=SC_EVERY, draw=SC_DRAW, pick=SC_PICK,
                         s1=s1dir, s3=s3dir, r=rdir, s1w=s1wdir, scl=sclrdir, skills_train=skills_train, skills_data=skills_data, b2=b2),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened; the pick uses only skills TRAIN rows and the model\'s own losses')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'scm.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, a3['replay_n'], seed)
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), a3['pool_limit']))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    w1p, sclp = os.path.join(s3d, 'W1.pt'), os.path.join(sd, 'SCL.pt')
    sha = dict(N=_sha_file(nprime), W1=_sha_file(w1p), SCL=_sha_file(sclp))
    t0 = time.time()
    recs, res['records'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    secs['records'] = time.time() - t0
    want = res['records']['W1_night']
    sclkey = _h('scl', sha['N'], SCL_LR, SCL_VISITS, seed, len(recs), want, a3['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK)
    if max_records:
        recs = recs[:max_records]
        res['records']['smoke_truncated_to'] = len(recs)
        res['SCL_key_check'] = 'skipped (smoke truncation)'
    else:
        assert pickle.load(open(os.path.join(sd, 'SCL.pkl'), 'rb'))['key'] == sclkey, "SCL's stage key differs from the key of lr 1e-4 / this seed / these records"
        res['SCL_key_check'] = 'equal'
    save()
    t0 = time.time()
    SCM, info, sha['SCM'] = _stage(pdir, 'SCM', _h('scm', sha['N'], SCM_LR, SCM_VISITS, seed, len(recs), want, a3['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK),
                                   lambda: _sc_night(N, recs, replay, warm_rows, vocab, SCM_LR, SCM_VISITS, seed, device, log), meta, vocab, device, resume, log)
    secs['SCM'] = time.time() - t0
    res['night'] = {k: v for k, v in info.items() if k not in ('rounds', 'picked_family_share', 'pool_family_share')}
    res['selection'] = dict(rounds=info['rounds'], picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                            rise_picked_vs_all=[(r['step'], r['mean_rise_picked'], r['mean_rise_all']) for r in info['rounds']])
    log('SCM night', res['night'])
    save()
    # measures: N', W1 (R's caches), SCL (SCL's caches, SCL.pt), SCM
    W1, _, _ = sleep.load_parent(w1p, device)
    W1.eval()
    SCL, _, _ = sleep.load_parent(sclp, device)
    SCL.eval()
    allm = dict(N=N, W1=W1, SCL=SCL, SCM=SCM)
    src = dict(N=rd, W1=rd, SCL=sd)
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    for a, m in allm.items():
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        v = (a in src and _peek(os.path.join(src[a], f'skills_{a}.pkl'), sk)) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')
        c = (a in src and _peek(os.path.join(src[a], f'c2_{a}.pkl'), ck)) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
        c2[a] = c
        res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    if b2 and os.path.exists(os.path.expanduser(b2)):
        b2p = os.path.expanduser(b2)
        bv = _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', _sha_file(b2p), skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2p, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
    for a in ('W1', 'SCL', 'SCM'):
        t0 = time.time()
        v, how = None, 'computed'
        key = ('c32', sha[a], dev_limit, mseed, T, 32)
        if a == 'W1':
            mu = os.path.join(s1wd, 'measure_U.pkl')
            if os.path.exists(mu):
                c = pickle.load(open(mu, 'rb'))
                kk = c['key']
                ok = kk[1] == 'U' and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and len(c['v']['c32']) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
                if ok:
                    v, how = c['v']['c32'], f'reused {mu}'
        if a == 'SCL':
            v = _peek(os.path.join(sd, 'c32_SCL.pkl'), key)
            if v is not None and len(v) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(v, dev)):
                how = f"reused {os.path.join(sd, 'c32_SCL.pkl')}"
            else:
                v = None
        if v is None:
            def fn(a=a):
                mm = _arm_model(allm[a], init, seed)
                with creative(mm, True):
                    smp = legal.raw_samples(mm, dev, vocab, device, n=32, temperature=T, level=0, seed=mseed)
                return score_rows(dev, smp, ks=(32,))
            v = _cached(os.path.join(pdir, f'c32_{a}.pkl'), key, fn, resume, log, f'reach32 {a}')
        c32[a] = v
        hard = [x['right32'] for x, r in zip(v, dev) if r['kind'] in c2_pilot.HARD_KINDS]
        res['reach32'][a] = dict(pooled=100 * sum(x['right32'] for x in v) / len(v), multi_step=100 * sum(hard) / max(len(hard), 1), source=how)
        secs[f'reach32_{a}'] = time.time() - t0
        log('reach32', a, res['reach32'][a])
        save()
    # marks
    hard_ix = [i for i, r in enumerate(dev) if r['kind'] in c2_pilot.HARD_KINDS]
    if not dev_limit:
        assert len(hard_ix) == 154, f'{len(hard_ix)} multi-step DEV questions, expected 154'
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    right = lambda a: [float(d['right']) for d in c2[a]]
    reach = lambda a: [float(c32[a][i]['right32']) for i in hard_ix]
    pooled = lambda a: [float(x['right32']) for x in c32[a]]
    slim = lambda h: {k: v for k, v in h.items() if k != 'families'}
    hN, hW1, hSCL = harm_measure(hits['N'], hits['SCM'], rows), harm_measure(hits['W1'], hits['SCM'], rows), harm_measure(hits['SCL'], hits['SCM'], rows)
    pct = lambda a: 100 * res['c2_dev'][a]['first_try_right']
    card = sc_scorecard(pct('SCM'), pct('W1'), pct('N'), hN['passes'], res['c2_dev']['SCM']['n'], keys=GAIN_KEYS)
    ms = lambda a: res['reach32'][a]['multi_step']
    res['marks'] = dict(card, **scm_marks(hN['passes'], card, ms('SCM'), ms('W1')), **scm_vs_scl(ms('SCM'), ms('SCL')), SCM_first_try=pct('SCM'), W1_first_try=pct('W1'), N_first_try=pct('N'),
                        SCM_multi_step_reach32=ms('SCM'), W1_multi_step_reach32=ms('W1'), SCL_multi_step_reach32=ms('SCL'), in_dist_drop_vs_N=hN['in_dist_drop'], fired_vs_N=hN['fired'], rules=SCM_SCORECARD)
    rs = info['rounds']
    res['report_only'] = dict(first_try_SCM_minus_SCL=bd(right('SCM'), right('SCL')), first_try_SCM_minus_W1=bd(right('SCM'), right('W1')),
                              multi_step_reach32_SCM_minus_SCL=bd(reach('SCM'), reach('SCL')), multi_step_reach32_SCM_minus_W1=bd(reach('SCM'), reach('W1')), multi_step_n=len(hard_ix),
                              pooled_reach32_SCM_minus_SCL=bd(pooled('SCM'), pooled('SCL')), pooled_reach32_SCM_minus_W1=bd(pooled('SCM'), pooled('W1')),
                              in_dist_drop_vs_N={a: res['skills']['N']['in_dist'] - res['skills'][a]['in_dist'] for a in ('W1', 'SCL', 'SCM')},
                              harm_vs_N=dict(SCM=slim(hN), SCL=slim(harm_measure(hits['N'], hits['SCL'], rows)), W1=slim(harm_measure(hits['N'], hits['W1'], rows))),
                              harm_SCM_vs_SCL=slim(hSCL), harm_SCM_vs_W1=slim(hW1),
                              harm_vs_B2={a: slim(harm_measure(hits['B2'], hits[a], rows)) for a in ('N', 'W1', 'SCL', 'SCM')} if 'B2' in hits else None,
                              picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                              loss_rise_picked_vs_random=dict(picked=sum(r['mean_rise_picked'] for r in rs) / len(rs) if rs else None, random=sum(r['mean_rise_all'] for r in rs) / len(rs) if rs else None, rounds=len(rs)),
                              pooled5={a: res['skills'][a]['pooled5'] for a in ('N', 'W1', 'SCL', 'SCM')}, reach32=res['reach32'],
                              cpu_seconds=dict(night=secs['SCM'], scoring=info['score_seconds'], measures=sum(v for k, v in secs.items() if k.startswith(('measure_', 'reach32_')))))
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'ratio', 'questions_short', 'mark2', 'reach_ok', 'passes', 'scm_minus_scl', 'under_3')})
    return res


def scm(nprimes, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, sclrdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: scm_parent(p, out, s1dir, s3dir, rdir, vldir, l2dir, s1wdir, sclrdir, **kw) for p in nprimes}


def scmreport(out, parents):
    """-> DIR/scm-report.json: the verdict (SCM_SCORECARD governs; gain_test / gain_control are SCM's and W1's gain over N'), per-parent marks, the report-only block, tables."""
    res = {p: json.load(open(os.path.join(out, p, 'scm.json'))) for p in parents}
    keep = ('gain_test', 'gain_control', 'ratio', 'harm', 'questions_short', 'near_miss', 'mark2', 'low', 'reach_ok', 'passes', 'scm_minus_scl', 'under_3', 'SCM_first_try', 'W1_first_try', 'N_first_try',
            'SCM_multi_step_reach32', 'W1_multi_step_reach32', 'SCL_multi_step_reach32', 'in_dist_drop_vs_N', 'fired_vs_N')
    pp = {p: {k: x['marks'][k] for k in keep} for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=pp, verdict=scm_verdict(pp), rules=SCM_SCORECARD, recipe=SCM_RECIPE, near_miss_on=[p for p, m in pp.items() if m['near_miss']],
               questions_short={p: m['questions_short'] for p, m in pp.items()}, report_only={p: x['report_only'] for p, x in res.items()},
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], night=x['night'], selection=x['selection']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'scm-report.json'), 'w'), indent=1)
    return rep


# ---------------------------------------------------------------- Test SCM2 (roadmap a6fa5a931b follow-up): both nights at SCM's recipe
SCM2_MARKS = dict(harm="(1) harm_measure(N' DEV hits, SCM2 DEV hits) passes: in_dist drop <= 1.5 and no family fires",
                  multi_step='(2) C2 DEV first try on the multi-step kinds (c2_pilot.HARD_KINDS, 154 questions): c2_pilot.boot(SCM2 right, W2 right) point >= -2.0',
                  passes='passes = (1) and (2) on a parent; the verdict needs both parents',
                  proved_wrong='the SCM2 - W2 multi-step first-try paired 95% interval has its upper end < 0 on BOTH parents (decided in the report)')
SCM2_RECIPE = ("both nights at SCM's recipe from N' (model-picked skills replay, lr 3e-4, 32 visits) against the standard two nights (W1 then W2). Night 1 = SCM, already trained (never retrained). "
               "Day 2 from SCM exactly as L2's day 2 from L (day_f, seed + 1 for day 2, records via w_records(..., s2 + 1)). Night 2 continues from SCM on SCM's own day-2 records, "
               "the pick's frozen pre-night copy is SCM, lr 3e-4, 32 visits, updates = records x 32 / 32, J's night-2 seed and replay / warm rows")
SCM2_MS_MIN = -2.0      # points


def scm2_marks(harm_passes, ms_point, ms_hi):
    """Pure. -> the SCM2 marks on one parent: multi-step first try SCM2 - W2 (point, 95% upper end, in points). multi_step = point >= -2.0 (inclusive); proved_wrong = upper end < 0."""
    ok2 = bool(round(ms_point - SCM2_MS_MIN, 9) >= 0)
    return dict(harm=bool(harm_passes), multi_step=ok2, passes=bool(harm_passes and ok2), proved_wrong=bool(round(ms_hi, 9) < 0))


def scm2_verdict(per_parent):
    """Pure. {parent: scm2_marks dict} -> passes on every parent (both marks, both parents); proved_wrong only if the interval is below 0 on EVERY parent."""
    return dict(passes=all(m['passes'] for m in per_parent.values()), proved_wrong=all(m['proved_wrong'] for m in per_parent.values()),
                disagree=[k for k in ('harm', 'multi_step', 'passes', 'proved_wrong') if len({m.get(k) for m in per_parent.values()}) > 1])


def scm2_parent(nprime, out, s1dir, s3dir, rdir, jdir, l2dir, scmdir, s1wdir, skills_train, skills_data, seed=0, pool_limit=None, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True,
                log=_log, max_records=None, b2=None):
    """One parent's Test SCM2. DIR/<name>/scm2.json is written after every stage; day2_SCM.pkl and SCM2.pt are cached stages. Night 1 = scmdir/<name>/SCM.pt (key-checked against SCM.pkl, never retrained).
    Reuses (key-checked, read only): R's skills / c2 for N', W1, W2; J's skills_B2 and measure_W (W2 reach@32); S1w's measure_U (W1 reach@32); L2's and SCM's skills / c2 / c32 caches. Anything whose key
    does not match is recomputed into DIR. max_records = smoke only (recorded; skips the SCM key check)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, jd, rd, l2d, scmd, s1wd = (os.path.join(d, name) for d in (out, s3dir, jdir, rdir, l2dir, scmdir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    jj = json.load(open(os.path.join(jd, 'j.json')))
    ja = jj['args']
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    a3 = s3['args']
    seed, T, s2, mseed, n1, n2 = jj['seed'], jj['T'], jj['day2_seed'], jj['measure_seed'], ja['n1'], ja['n2']
    assert s2 == seed + 1 and mseed == seed + 777 and ja['lr'] == 1e-3 and ja['visits'] == 32, 'J is not the standard two nights'
    assert a3['lr'] == 1e-3 and a3['visits'] == 32 and s3['seed'] == seed and a3['replay_n'] == ja['replay_n'], 'S3 / J disagree on seed, lr, visits or replay size'
    pool_limit = ja['pool_limit'] if pool_limit is None else pool_limit
    b2 = os.path.expanduser(b2 or ja.get('b2') or '')
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], recipe=SCM2_RECIPE, marks_rules=SCM2_MARKS, secs=secs,
               args=dict(seed=seed, day2_seed=s2, measure_seed=mseed, T=T, n1=n1, n2=n2, lr=SCM_LR, visits=SCM_VISITS, pool_limit=pool_limit, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records,
                         every=SC_EVERY, draw=SC_DRAW, pick=SC_PICK, b2=b2, s1=s1dir, s3=s3dir, j=jdir, r=rdir, l2=l2dir, scm=scmdir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened; the pick uses only skills TRAIN rows and the model\'s own losses')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'scm2.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, ja['replay_n'], seed)
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    paths = dict(N=nprime, W1=os.path.join(s3d, 'W1.pt'), W2=os.path.join(jd, 'W2.pt'), L2=os.path.join(l2d, 'L2.pt'), SCM=os.path.join(scmd, 'SCM.pt'))
    sha = {a: _sha_file(p) for a, p in paths.items() if os.path.exists(p)}
    # 1. night 1 = SCM, key-checked against its stored stage key (the key scm_parent wrote), never retrained
    want = s3['W1_night']['records']
    nrec1 = want
    if not max_records:
        full_pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), a3['pool_limit']))
        recs1, rinfo = _w1_records(nprime, name, s1dir, s3, full_pool, N, vocab, device)
        nrec1 = len(recs1)
    scmkey = _h('scm', sha['N'], SCM_LR, SCM_VISITS, seed, nrec1, want, a3['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK)
    if max_records:
        key_check = 'skipped (smoke truncation)'
    else:
        assert pickle.load(open(os.path.join(scmd, 'SCM.pkl'), 'rb'))['key'] == scmkey, "SCM's stage key differs from the key of lr 3e-4 / this seed / these records"
        key_check = 'equal'
    SCM, _, _ = sleep.load_parent(paths['SCM'], device)
    SCM.eval()
    res['night1'] = dict(SCM_path=paths['SCM'], SCM_sha256=sha['SCM'], SCM_key_check=key_check, SCM_key=scmkey)
    save()
    # 2. day 2 from SCM: l2_parent's day 2 from L, line for line (untrained adapter = plain two-pass search)
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    skey = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    t0 = time.time()
    dkey = (skey, s2, sha['SCM'], _hstate(init), 'SCM')
    day = _cached(os.path.join(pdir, 'day2_SCM.pkl'), dkey, lambda: day_f(_arm_model(SCM, init, seed), pool, vocab, device, T, n1, n2, s2), resume, log, 'day 2 SCM')
    secs['day2_SCM'] = time.time() - t0
    res['day2'] = dict(drawn=day['drawn'], greedy_pass=sum(day['greedy_fit']) / len(pool), pool_with_fit_pass1=sum(day['fit1']), pool_with_fit_final=sum(day['fit_final']), pool_rows=len(pool),
                       seconds=secs['day2_SCM'], seconds_per_pool_row=secs['day2_SCM'] / len(pool))
    log('day 2 SCM', res['day2'])
    save()
    # 3. night 2: from SCM, model-picked replay whose frozen pre-night copy is SCM (sleep_sc copies the model it is handed)
    recs, cnt = w_records(pool, day['tries'], s2 + 1)
    assert recs, 'SCM: no day-2 records'
    res['night2_records'] = dict(records=len(recs), records_by_kind=_by_kind(pool, cnt), W2_records=jj['night2']['W']['records'], W2_records_by_kind=jj['night2']['W']['records_by_kind'])
    if max_records:
        recs = recs[:max_records]
        res['night2_records']['smoke_truncated_to'] = len(recs)
    t0 = time.time()
    SCM2, info, sha['SCM2'] = _stage(pdir, 'SCM2', _h('scm2', sha['SCM'], dkey, SCM_LR, SCM_VISITS, len(recs), ja['replay_n'], len(replay), SC_EVERY, SC_DRAW, SC_PICK, bool(skills_train)),
                                     lambda: _sc_night(SCM, recs, replay, warm_rows, vocab, SCM_LR, SCM_VISITS, s2, device, log), meta, vocab, device, resume, log)
    secs['night2_SCM2'] = time.time() - t0
    res['night2'] = {k: v for k, v in info.items() if k not in ('rounds', 'picked_family_share', 'pool_family_share')}
    res['night2']['lr'], res['night2']['visits'], res['night2']['frozen_copy'] = SCM_LR, SCM_VISITS, 'SCM'
    res['selection'] = dict(rounds=info['rounds'], picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
                            rise_picked_vs_all=[(r['step'], r['mean_rise_picked'], r['mean_rise_all']) for r in info['rounds']])
    log('SCM2 night 2', res['night2'])
    save()
    # 4. measures
    models = dict(N=N, SCM=SCM, SCM2=SCM2)

    def get(a):
        if a not in models:
            m, _, _ = sleep.load_parent(paths[a], device)
            m.eval()
            models[a] = m
        return models[a]
    src = dict(N=rd, W1=rd, W2=rd, L2=l2d, SCM=scmd)
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    for a in ('N', 'W1', 'W2', 'L2', 'SCM', 'SCM2'):
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        if a != 'L2':                                           # L2: first try only (report only), no skills needed
            v = (a in src and _peek(os.path.join(src[a], f'skills_{a}.pkl'), sk)) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda a=a: skills_dev(get(a), skills_data, device, skills_limit), resume, log, f'skills {a}')
            rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
            res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        c = (a in src and _peek(os.path.join(src[a], f'c2_{a}.pkl'), ck)) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda a=a: greedy_rows(get(a), dev, vocab, device), resume, log, f'c2 dev {a}')
        c2[a] = c
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'].get(a), res['c2_dev'][a])
        save()
    if os.path.exists(b2):                                      # B2, skills only (report-only harm of the whole chain)
        bs = _sha_file(b2)
        bj = _peek(os.path.join(jd, 'skills_B2.pkl'), ('B2', skills_data, bs)) if not skills_limit else None
        bv = _skills_as_tuple(bj) if bj else _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', bs, skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
        save()
    # reach@32 per night (W1, W2, SCM, SCM2): 32 plain samples per C2 DEV row, untrained adapter, mseed
    reuse = dict(W1=(os.path.join(s1wd, 'measure_U.pkl'), 'U'), W2=(os.path.join(jd, 'measure_W.pkl'), 'W'))
    for a in ('W1', 'W2', 'SCM', 'SCM2'):
        t0 = time.time()
        v, how = None, 'computed'
        key = ('c32', sha[a], dev_limit, mseed, T, 32)
        if a in reuse and os.path.exists(reuse[a][0]):
            c = pickle.load(open(reuse[a][0], 'rb'))
            kk = c['key']
            ok = kk[1] == reuse[a][1] and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and (a != 'W2' or kk[7] == skills_data) and len(c['v']['c32']) == len(dev)
            ok = ok and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
            if ok:
                v, how = c['v']['c32'], f'reused {reuse[a][0]}'
        if v is None and a == 'SCM':
            v = _peek(os.path.join(scmd, 'c32_SCM.pkl'), key)
            if v is not None and len(v) == len(dev) and all(x['kind'] == r['kind'] for x, r in zip(v, dev)):
                how = f"reused {os.path.join(scmd, 'c32_SCM.pkl')}"
            else:
                v = None
        if v is None:
            def fn(a=a):
                mm = _arm_model(get(a), init, seed)
                with creative(mm, True):
                    smp = legal.raw_samples(mm, dev, vocab, device, n=32, temperature=T, level=0, seed=mseed)
                return score_rows(dev, smp, ks=(32,))
            v = _cached(os.path.join(pdir, f'c32_{a}.pkl'), key, fn, resume, log, f'reach32 {a}')
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
    reach = lambda a, ix=None: [float(c32[a][i]['right32']) for i in (range(len(dev)) if ix is None else ix)]
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    slim = lambda h: {k: v for k, v in h.items() if k != 'families'}
    hN = harm_measure(hits['N'], hits['SCM2'], rows)
    ms = bd(right('SCM2', hard_ix), right('W2', hard_ix))
    res['marks'] = dict(scm2_marks(hN['passes'], ms['points'], ms['hi']), in_dist_drop_vs_N=hN['in_dist_drop'], fired_vs_N=hN['fired'], pooled5=res['skills']['SCM2']['pooled5'],
                        multi_step_first_try_SCM2_minus_W2=ms, multi_step_n=len(hard_ix), rules=SCM2_MARKS)
    rs = info['rounds']
    res['report_only'] = dict(
        multi_step_first_try_SCM2_minus_L2=bd(right('SCM2', hard_ix), right('L2', hard_ix)), multi_step_first_try_SCM2_minus_N=bd(right('SCM2', hard_ix), right('N', hard_ix)),
        pooled_first_try={a: 100 * sum(right(a)) / len(dev) for a in ('N', 'W1', 'W2', 'L2', 'SCM', 'SCM2')}, pooled_first_try_SCM2_minus_W2=bd(right('SCM2'), right('W2')),
        reach32=res['reach32'], reach32_pooled_SCM2_minus_W2=bd(reach('SCM2'), reach('W2')), reach32_multi_step_SCM2_minus_W2=bd(reach('SCM2', hard_ix), reach('W2', hard_ix)),
        harm_vs_B2={a: slim(harm_measure(hits['B2'], hits[a], rows)) for a in ('N', 'W1', 'W2', 'SCM', 'SCM2')} if 'B2' in hits else None,
        night2_own_cost_SCM2_vs_SCM=slim(harm_measure(hits['SCM'], hits['SCM2'], rows)), night2_records=res['night2_records'],
        picked_family_share=info['picked_family_share'], pool_family_share=info['pool_family_share'],
        loss_rise_picked_vs_random=dict(picked=sum(r['mean_rise_picked'] for r in rs) / len(rs) if rs else None, random=sum(r['mean_rise_all'] for r in rs) / len(rs) if rs else None, rounds=len(rs)),
        cpu_seconds=dict(secs, night2_scoring=info['score_seconds']))
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('harm', 'multi_step', 'passes', 'proved_wrong')})
    return res


def scm2(nprimes, out, s1dir, s3dir, rdir, jdir, l2dir, scmdir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: scm2_parent(p, out, s1dir, s3dir, rdir, jdir, l2dir, scmdir, s1wdir, **kw) for p in nprimes}


def scm2report(out, parents):
    """-> DIR/scm2-report.json: the verdict (passes on both parents; proved_wrong on both), per-parent marks, the report-only block, tables."""
    res = {p: json.load(open(os.path.join(out, p, 'scm2.json'))) for p in parents}
    keep = ('harm', 'multi_step', 'passes', 'proved_wrong', 'multi_step_first_try_SCM2_minus_W2', 'in_dist_drop_vs_N', 'fired_vs_N')
    pm = {p: {k: x['marks'][k] for k in keep} for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=pm, verdict=scm2_verdict(pm), rules=SCM2_MARKS, recipe=SCM2_RECIPE, report_only={p: x['report_only'] for p, x in res.items()},
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], day2=x['day2'], night2=x['night2'], night1=x['night1'], selection=x['selection']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'scm2-report.json'), 'w'), indent=1)
    return rep



# ---------------------------------------------------------------- Test AP (roadmap a81b3bebd8): night 2 appends night 1's records
AP_MARKS = dict(first_try='(1) pooled C2 DEV first try: c2_pilot.boot(AP right, W2 right) point >= +2.0',
                multi_step='(2) multi-step first try (HARD_KINDS, 154 questions): AP - W2 point >= -2.0',
                harm="(3) night 2's own cost: harm_measure(W1 DEV hits, AP DEV hits) passes (in_dist drop <= 1.5, no family fires)",
                passes='passes = (1) and (2) and (3) on a parent; the verdict needs both parents',
                proved_wrong='the AP - W2 pooled first-try paired 95% interval has its upper end < +1.0 on BOTH parents (decided in the report)')
AP_RECIPE = ("night 2 from W1 on W2's exact recipe (J's W arm: day-2 records, lr 1e-3, W2's update count = number of night-2 records, seed s2, same skills replay and warm rows) with ONE change: the record half of "
             "each batch is drawn from night 1's records PLUS night 2's records (ids prefixed n1| / n2| on copies)")


def ap_marks(first_pt, ms_pt, harm_passes, first_hi):
    """Pure. Points; first_* = pooled first try AP - W2 (point, 95% upper end), ms_pt = multi-step AP - W2 point."""
    a, b = bool(first_pt >= 2.0), bool(ms_pt >= -2.0)
    return dict(first_try=a, multi_step=b, harm=bool(harm_passes), passes=bool(a and b and harm_passes), proved_wrong=bool(first_hi < 1.0))


def ap_verdict(per_parent):
    """Pure. {parent: ap_marks} -> passes on every parent, proved_wrong on every parent, where the parents disagree."""
    return dict(passes=all(m['passes'] for m in per_parent.values()), proved_wrong=all(m['proved_wrong'] for m in per_parent.values()),
                disagree=[k for k in ('first_try', 'multi_step', 'harm', 'passes', 'proved_wrong') if len({m[k] for m in per_parent.values()}) > 1])


def prefixed_copies(recs, prefix, register=True):
    """Copies of the record dicts with id = prefix + original id (the target cache is keyed by id; night-1 and night-2 ids can collide). The records' targets are REGISTERED in progparse._CACHE under the
    original id (fewshot._record), so with register=True each copy gets the same registered entry under its new id (the original's must exist)."""
    from custom_io.models import progparse as pp
    new = [dict(r, id=prefix + r['id']) for r in recs]
    if register:
        for r, n in zip(recs, new):
            assert r['id'] in pp._CACHE, f'no registered targets for {r["id"]}'
            pp._CACHE[n['id']] = pp._CACHE[r['id']]
    return new


def check_prefixed(recs, prefix, spot=8):
    """Before the night: no stale target-cache entry for any new id (assert); then register the prefixed copies and check that every copy's targets equal its original's (all rows; `spot` of them also
    through row_targets). -> dict for the log."""
    from custom_io.models import progparse as pp
    stale = [prefix + r['id'] for r in recs if prefix + r['id'] in pp._CACHE]
    assert not stale, f'stale target cache entries for {stale[:3]}'
    new = prefixed_copies(recs, prefix)
    assert all(pp._CACHE[n['id']] == pp._CACHE[r['id']] for r, n in zip(recs, new)), 'registered targets differ'
    idx = sorted({int(i * (len(recs) - 1) / max(spot - 1, 1)) for i in range(spot)}) if recs else []
    assert all(pp.row_targets(recs[i]) == pp.row_targets(new[i]) for i in idx)
    return dict(prefix=prefix, n=len(recs), spot_checked=len(idx), stale_entries=0, targets_equal=True)


def ap_parent(nprime, out, s1dir, s3dir, jdir, rdir, s1wdir, skills_train, skills_data, seed=0, dev_limit=None, skills_limit=None, device='cpu', name=None, resume=True, log=_log, max_records=None, b2=None):
    """One parent's Test AP. DIR/<name>/ap.json is written after every stage; AP.pt is a cached stage. Reuses (key-checked, read only): J's day2_W.pkl (key rebuilt as j_parent builds it), R's skills / c2 caches
    for N', W1, W2, J's skills_B2, S1w's measure_U and J's measure_W (reach@32). max_records = smoke only: truncates BOTH record sets (recorded)."""
    nprime = os.path.expanduser(nprime)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s3d, jd, rd, s1wd = (os.path.join(d, name) for d in (out, s3dir, jdir, rdir, s1wdir))
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    jj = json.load(open(os.path.join(jd, 'j.json')))
    ja = jj['args']
    s3 = json.load(open(os.path.join(s3d, 's3.json')))
    seed, T, s2, mseed, n1, n2 = jj['seed'], jj['T'], jj['day2_seed'], jj['measure_seed'], ja['n1'], ja['n2']
    assert s2 == seed + 1 and mseed == seed + 777 and ja['lr'] == 1e-3 and ja['visits'] == 32 and ja['pool_limit'] == s3['args']['pool_limit'], 'J is not the standard two nights'
    b2 = os.path.expanduser(b2 or ja.get('b2') or '')
    res = dict(nprime=nprime, name=name, spec=__doc__.split('\n')[0], recipe=AP_RECIPE, marks_rules=AP_MARKS, secs=secs,
               args=dict(seed=seed, day2_seed=s2, measure_seed=mseed, T=T, n1=n1, n2=n2, lr=1e-3, visits=32, dev_limit=dev_limit, skills_limit=skills_limit, max_records=max_records, b2=b2, s1=s1dir, s3=s3dir, j=jdir,
                         r=rdir, s1w=s1wdir, skills_train=skills_train, skills_data=skills_data),
               note='C2 pool / warm rows / DEV and skills train / DEV only; test / labelled / K_new never opened')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'ap.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, ja['replay_n'], seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), ja['pool_limit']))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    paths = dict(N=nprime, W1=os.path.join(s3d, 'W1.pt'), W2=os.path.join(jd, 'W2.pt'))
    sha = {a: _sha_file(p) for a, p in paths.items()}
    W1, _, _ = sleep.load_parent(paths['W1'], device)
    W1.eval()
    # night-1 records (W1's, rebuilt) and night-2 records (J's W arm day 2)
    t0 = time.time()
    recs1, res['records1'] = _w1_records(nprime, name, s1dir, s3, pool, N, vocab, device)
    from custom_io.models import progparse as pp
    tg1 = {r['id']: pp._CACHE[r['id']] for r in recs1}        # night 1's targets, snapshot NOW: night 2's records re-register the same 'W:<question>:<k>' ids below
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    skey = (os.path.abspath(nprime), ja['pool_limit'], n1, n2, seed, T)
    dp = os.path.join(jd, 'day2_W.pkl')
    c = pickle.load(open(dp, 'rb'))
    assert c['key'] == (skey, s2, sha['W1'], _hstate(init), 'W'), "J's day2_W.pkl key differs from the one j_parent builds"
    recs2, cnt = w_records(pool, c['v']['tries'], s2 + 1)
    tg2 = {r['id']: pp._CACHE[r['id']] for r in recs2}
    want2 = jj['night2']['W']['records']
    assert len(recs2) == want2, f'rebuilt {len(recs2)} night-2 records, J has {want2}'
    res['records2'] = dict(rebuilt=len(recs2), J_night2=want2, equal=True, source=dp, records_by_kind=_by_kind(pool, cnt))
    secs['records'] = time.time() - t0
    if max_records:
        recs1, recs2 = recs1[:max_records], recs2[:max_records]
        res['records2']['smoke_truncated_to'] = len(recs2)
        res['records1']['smoke_truncated_to'] = len(recs1)
    u = len(recs2)                                  # W2's update count: 32 * len(recs2) // 32
    mv = max(math.ceil(u * 32 / (len(recs1) + len(recs2))), 1)
    # prefixed copies registered from each night's own snapshot (registering from the live cache would give night-1 copies night 2's targets wherever the original ids collide)
    stale = [x + r['id'] for x, rs in (('n1|', recs1), ('n2|', recs2)) for r in rs if x + r['id'] in pp._CACHE]
    assert not stale, f'stale target cache entries for {stale[:3]}'
    for x, rs, tg in (('n1|', recs1, tg1), ('n2|', recs2, tg2)):
        for r in rs:
            pp._CACHE[x + r['id']] = tg[r['id']]
    overlap = {r['id'] for r in recs1} & {r['id'] for r in recs2}
    assert all(pp._CACHE['n2|' + r['id']] == pp._CACHE[r['id']] for r in recs2), 'night-2 copies differ from the live (night-2) targets'
    res['ids'] = dict(n1=len(recs1), n2=len(recs2), original_id_overlap=len(overlap), overlap_with_different_targets=sum(tg1[i] != tg2[i] for i in overlap), stale_entries=0,
                      note='ids prefixed n1| / n2| on copies; each copy registered with its own night\'s targets, snapshotted right after that night\'s records were built')
    res['plan'] = dict(records1=len(recs1), records2=len(recs2), union=len(recs1) + len(recs2), updates=u, visits_per_record=u * 32 / (len(recs1) + len(recs2)), W2_visits_per_record=32.0, max_visits=mv)
    log('AP plan', res['plan'], res['ids'])
    save()

    def night2():
        t1 = time.time()
        union = prefixed_copies(recs1, 'n1|', register=False) + prefixed_copies(recs2, 'n2|', register=False)       # targets registered above from each night's snapshot
        m = copy.deepcopy(W1)
        so = sleep.sleep(m, union, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=1e-3, warmup=20, seed=s2, max_visits=mv), device, replay_extra=warm_rows)
        m.eval()
        return m, dict(updates=u, records=len(union), visits_per_record=u * 32 / len(union), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1) if so['loss'] else None, seconds=time.time() - t1)
    AP, info, sha['AP'] = _stage(pdir, 'AP', _h('ap-snap', sha['W1'], 1e-3, 32, s2, len(recs1), len(recs2), res['records1']['W1_night'], ja['replay_n'], bool(skills_train)), night2, meta, vocab, device, resume, log)
    secs['AP'] = time.time() - t0
    res['night2'] = info
    log('AP night 2', info)
    save()
    # measures
    allm = dict(N=N, W1=W1, AP=AP)
    getm = lambda a: allm[a] if a in allm else allm.setdefault(a, sleep.load_parent(paths[a], device)[0].eval())
    hits, c2, c32, res['skills'], res['c2_dev'], res['reach32'], rows = {}, {}, {}, {}, {}, {}, None
    for a in ('N', 'W1', 'W2', 'AP'):
        t0 = time.time()
        sk, ck = ('skills', sha[a], skills_data, skills_limit), ('c2', sha[a], dev_limit)
        v = (_peek(os.path.join(rd, f'skills_{a}.pkl'), sk) if a != 'AP' else None) or _cached(os.path.join(pdir, f'skills_{a}.pkl'), sk, lambda a=a: skills_dev(getm(a), skills_data, device, skills_limit), resume, log, f'skills {a}')
        cc = (_peek(os.path.join(rd, f'c2_{a}.pkl'), ck) if a != 'AP' else None) or _cached(os.path.join(pdir, f'c2_{a}.pkl'), ck, lambda a=a: greedy_rows(getm(a), dev, vocab, device), resume, log, f'c2 dev {a}')
        rows, hits[a] = v[0] if v[0] is not None else rows, v[1]
        c2[a] = cc
        res['skills'][a] = dict(pooled5=v[2], in_dist=v[3], n=len(v[1]))
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in cc) / len(dev), stuck_rate=1 - sum(d['fit'] for d in cc) / len(dev), n=len(dev))
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    if os.path.exists(b2):
        bs = _sha_file(b2)
        bj = _peek(os.path.join(jd, 'skills_B2.pkl'), ('B2', skills_data, bs)) if not skills_limit else None
        bv = _skills_as_tuple(bj) if bj else _cached(os.path.join(pdir, 'skills_B2.pkl'), ('skills', bs, skills_data, skills_limit), lambda: skills_dev(sleep.load_parent(b2, device)[0].eval(), skills_data, device, skills_limit), resume, log, 'skills B2')
        hits['B2'] = bv[1]
        res['skills']['B2'] = dict(pooled5=bv[2], in_dist=bv[3], n=len(bv[1]))
        save()
    reuse = dict(W1=(os.path.join(s1wd, 'measure_U.pkl'), 'U'), W2=(os.path.join(jd, 'measure_W.pkl'), 'W'))
    for a in ('W1', 'W2', 'AP'):
        t0 = time.time()
        v, how = None, 'computed'
        if a in reuse and os.path.exists(reuse[a][0]):
            c = pickle.load(open(reuse[a][0], 'rb'))
            kk = c['key']
            ok = kk[1] == reuse[a][1] and kk[3] == 32 and kk[4] == mseed and kk[6] == dev_limit and (a != 'W2' or kk[7] == skills_data) and len(c['v']['c32']) == len(dev)
            ok = ok and all(x['kind'] == r['kind'] for x, r in zip(c['v']['c32'], dev))
            if ok:
                v, how = c['v']['c32'], f'reused {reuse[a][0]}'
        if v is None:
            def fn(a=a):
                mm = _arm_model(getm(a), init, seed)
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
    # marks and report-only
    hard_ix = [i for i, r in enumerate(dev) if r['kind'] in c2_pilot.HARD_KINDS]
    if not dev_limit:
        assert len(hard_ix) == 154, f'{len(hard_ix)} multi-step DEV questions, expected 154'
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    right = lambda a, ix=None: [float(c2[a][i]['right']) for i in (range(len(dev)) if ix is None else ix)]
    hm = lambda b, a: {k: v for k, v in harm_measure(hits[b], hits[a], rows).items() if k != 'families'}
    ft, ms = bd(right('AP'), right('W2')), bd(right('AP', hard_ix), right('W2', hard_ix))
    hW1 = harm_measure(hits['W1'], hits['AP'], rows)
    res['marks'] = dict(ap_marks(ft['points'], ms['points'], hW1['passes'], ft['hi']), first_try_AP_minus_W2=ft, multi_step_first_try_AP_minus_W2=ms, multi_step_n=len(hard_ix),
                        night2_in_dist_drop_vs_W1=hW1['in_dist_drop'], fired_vs_W1=hW1['fired'], rules=AP_MARKS)
    kinds = sorted({r['kind'] for r in dev})
    kix = {k: [i for i, r in enumerate(dev) if r['kind'] == k] for k in kinds}
    res['report_only'] = dict(
        per_kind_first_try={k: {a: 100 * sum(right(a, ix)) / len(ix) for a in ('W1', 'W2', 'AP')} for k, ix in kix.items()},
        per_kind_AP_minus_W2={k: bd(right('AP', ix), right('W2', ix)) for k, ix in kix.items()},
        reach32=res['reach32'], reach32_multi_step_AP_minus_W2=bd([float(c32['AP'][i]['right32']) for i in hard_ix], [float(c32['W2'][i]['right32']) for i in hard_ix]),
        reach32_pooled_AP_minus_W2=bd([float(x['right32']) for x in c32['AP']], [float(x['right32']) for x in c32['W2']]),
        harm_vs_N={a: hm('N', a) for a in ('W2', 'AP')}, harm_vs_B2={a: hm('B2', a) for a in ('W2', 'AP')} if 'B2' in hits else None, harm_AP_vs_W2=hm('W2', 'AP'),
        records=res['plan'], cpu_seconds=dict(night2=info['seconds'], measures=sum(v for k, v in secs.items() if k.startswith(('measure_', 'reach32_')))))
    res['report_only']['last_digit'] = dict(first_try=res['report_only']['per_kind_first_try'].get('last_digit'), AP_minus_W2=res['report_only']['per_kind_AP_minus_W2'].get('last_digit'), note='job 8 lost last_digit on night 2')
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: res['marks'][k] for k in ('first_try', 'multi_step', 'harm', 'passes', 'proved_wrong')})
    return res


def ap(nprimes, out, s1dir, s3dir, jdir, rdir, s1wdir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: ap_parent(p, out, s1dir, s3dir, jdir, rdir, s1wdir, **kw) for p in nprimes}


def apreport(out, parents):
    """-> DIR/ap-report.json: per-parent marks, the verdict (passes on both parents; proved_wrong on both), tables."""
    res = {p: json.load(open(os.path.join(out, p, 'ap.json'))) for p in parents}
    pm = {p: {k: x['marks'][k] for k in ('first_try', 'multi_step', 'harm', 'passes', 'proved_wrong')} for p, x in res.items()}
    rep = dict(parents=list(parents), per_parent=pm, verdict=ap_verdict(pm), rules=AP_MARKS, recipe=AP_RECIPE,
               tables={p: dict(skills=x['skills'], c2_dev=x['c2_dev'], reach32=x['reach32'], marks=x['marks'], report_only=x['report_only'], night2=x['night2'], ids=x['ids'], plan=x['plan']) for p, x in res.items()})
    json.dump(rep, open(os.path.join(out, 'ap-report.json'), 'w'), indent=1)
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('run'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True); q.add_argument('--r', required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--pool-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only: truncate the night-1 records'); q.add_argument('--device', default='cpu')
    q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('sc'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s1', 's3', 'r', 's1w'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('screport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('scl'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s1', 's3', 'r', 'vl', 'l2'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--s1w', default='~/c7d/s1w', help='W1 reach@32 (report only)')
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('sclreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('scm'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s1', 's3', 'r', 'vl', 'l2', 's1w', 'scl'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('scmreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('scm2'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s1', 's3', 'r', 'j', 'l2', 'scm', 's1w'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--vl', help='accepted and ignored'); q.add_argument('--pool-limit', type=int)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('scm2report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('ap'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s1', 's3', 'j', 'r', 's1w'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only: truncates both record sets'); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int)
    q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('apreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('l2'); q.add_argument('--nprime', nargs='+', required=True)
    for f in ('s3', 'j', 'r', 'vl', 's1w'):
        q.add_argument('--' + f, required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--b2'); q.add_argument('--visits', type=int, default=32); q.add_argument('--s1', help='needed when visits != 32'); q.add_argument('--l2', help='the L2 outputs, report-only comparison')
    q.add_argument('--pool-limit', type=int)
    q.add_argument('--dev-limit', type=int); q.add_argument('--skills-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only'); q.add_argument('--device', default='cpu')
    q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('l2report'); q.add_argument('--visits', type=int, default=32); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    q = sub.add_parser('report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'apreport':
        print(json.dumps(apreport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'ap':
        ex = os.path.expanduser
        ap(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.j), ex(a.r), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), dev_limit=a.dev_limit, skills_limit=a.skills_limit,
           device=a.device, resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'scm2report':
        print(json.dumps(scm2report(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'scm2':
        ex = os.path.expanduser
        scm2(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), ex(a.j), ex(a.l2), ex(a.scm), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit,
             skills_limit=a.skills_limit, device=a.device, resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'scmreport':
        print(json.dumps(scmreport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'scm':
        ex = os.path.expanduser
        scm(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), ex(a.vl), ex(a.l2), ex(a.s1w), ex(a.scl), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), dev_limit=a.dev_limit, skills_limit=a.skills_limit,
            device=a.device, resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'sclreport':
        print(json.dumps(sclreport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'scl':
        ex = os.path.expanduser
        scl(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), ex(a.vl), ex(a.l2), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), dev_limit=a.dev_limit, skills_limit=a.skills_limit, device=a.device,
            resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'screport':
        print(json.dumps(screport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'sc':
        ex = os.path.expanduser
        sc(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), dev_limit=a.dev_limit, skills_limit=a.skills_limit, device=a.device,
           resume=not a.no_resume, max_records=a.max_records, b2=a.b2)
    elif a.cmd == 'l2report':
        print(json.dumps(l2report(a.out, tuple(a.parents), *(('l2.json', 'L2') if a.visits == 32 else (f'l{a.visits}.json', f'L{a.visits}'))), indent=1))
    elif a.cmd == 'l2':
        ex = os.path.expanduser
        l2(a.nprime, a.out, ex(a.s3), ex(a.j), ex(a.r), ex(a.vl), ex(a.s1w), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit,
           skills_limit=a.skills_limit, device=a.device, resume=not a.no_resume, max_records=a.max_records, b2=a.b2, visits=a.visits, s1dir=a.s1 and ex(a.s1), l2dir=a.l2 and ex(a.l2))
    elif a.cmd == 'report':
        print(json.dumps(vlreport(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        vl(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit, skills_limit=a.skills_limit,
           device=a.device, resume=not a.no_resume, max_records=a.max_records)
