"""Roadmap 7526d614e5, Test VL: does night 1 hurt skills less with each record seen fewer times (arm V) or at a lower lr (arm L)? CPU. Reads the skills TRAIN file (replay), C2 pool / warm rows (night records),
C2 DEV and skills DEV (MEASURE only); C2 test / labelled never opened.
  python3 -m creative.night7d run --nprime ~/c7d/s100/Nprime.pt --s1 ~/c7d/s1 --s3 ~/c7d/s3 --r ~/c7d/r --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 1
  python3 -m creative.night7d report --out DIR --parents s100 s101
Each arm is ONE change to the standard night 1 from N' (S3's W1 = sleep_on(N', W1's records, lr 1e-3, 32 visits, seed)): V = 8 visits per record (lr 1e-3); L = lr 1e-4 (32 visits).
W1's records are rebuilt from S1's day with S3's seeds and checked against W1_night in s3.json."""
import argparse, json, os, pickle, time
import torch
from creative import c2_pilot, c2_stones, rules_real as R, sleep
from creative.sleep7d import DATA, _cached, _h, _limit, _log, _sha_file, greedy_rows, sleep_on, search, w_records, w1_tries_from_day
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


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('run'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True); q.add_argument('--r', required=True)
    q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--dev-limit', type=int)
    q.add_argument('--skills-limit', type=int); q.add_argument('--pool-limit', type=int); q.add_argument('--max-records', type=int, help='smoke only: truncate the night-1 records'); q.add_argument('--device', default='cpu')
    q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'report':
        print(json.dumps(vlreport(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        vl(a.nprime, a.out, ex(a.s1), ex(a.s3), ex(a.r), skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit, skills_limit=a.skills_limit,
           device=a.device, resume=not a.no_resume, max_records=a.max_records)
