"""Roadmap 7d, Test R: a repair pass after each sleep night. CPU. Reads the skills TRAIN file, C2 pool / DEV and skills DEV (to MEASURE only: the repair never reads DEV); C2 test / labelled never opened.
  python3 -m creative.repair7d r --nprime ~/c7d/s100/Nprime.pt ~/c7d/s101/Nprime.pt --j DIR --s3 DIR --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 2
  python3 -m creative.repair7d rreport --out DIR --parents s100 s101
R = "no outside help, not own choices": after a night the model checks itself on a held slice of its own skills TRAINING rows (greedy exact per row, the same check before the night and after it);
the families that fire under the harm rule get replay-only updates on their other training rows; re-check, up to 4 rounds, stop early when nothing fires.
E (report only) = the same number of updates spread evenly over ALL families' repair rows. Answer keys of the skills rows are the rows' own targets; DEV never picks a row or a setting."""
import argparse, json, math, os, random, time, copy
import torch
from creative import c2_pilot, c2_stones, rules_real as R, sleep
from creative.sleep7d import DATA, _cached, _h, _limit, _log, _sha_file, greedy_rows, sleep_on, w_records
from custom_io.data import load_rows
from custom_io.evalx import evaluate, is_hit, subsample
from creative.harm_look import harm_measure, skills_hits

N_RECORDS = 1024                       # distinct repair rows drawn per round (64 updates x 64 rows = 4 visits each)
MARKS = dict(harm='(a) DEV harm measure of the repaired model against its pre-night model passes: W1r vs N\' and W2r vs W1r (in_dist drop <= 1.5, no family fires: drop > 5 points and paired 95% interval of b - a below 0)',
             first_try='(b) C2 DEV first try right within 2 points of the unrepaired night: W1r - W1 and W2r - W2 >= -2 (paired bootstrap point estimate, c2_pilot.boot)',
             proved_wrong='PROVED WRONG: after repair, DEV in_dist is still more than 1.5 below the pre-night model at point 1 (W1r vs N\') on both parents (point 2 reported too); rreport decides "both parents"',
             passes='PASS = (a) and (b) at both points on both parents', report_only='E against R (in_dist, fired families), the update counts, everything against N\'')


def held_split(train_rows, per_family=100, seed=0):
    """Own TRAINING rows only. -> (held rows [per_family per family, in file order within family, families sorted], repair pool {family: the family's other rows}). Seeded, disjoint, deterministic."""
    fams = {}
    for r in train_rows:
        fams.setdefault(r['family'], []).append(r)
    held, pool = [], {}
    for f in sorted(fams):
        rows = fams[f]
        assert len(rows) > per_family, f'{f}: {len(rows)} rows, need more than {per_family}'
        pick = set(random.Random(_h('held', seed, f)).sample(range(len(rows)), per_family))
        held += [r for i, r in enumerate(rows) if i in pick]
        pool[f] = [r for i, r in enumerate(rows) if i not in pick]
    return held, pool


def held_hits(model, rows, device='cpu', bs=128):
    """The model's own check: greedy exact per row (evaluate + is_hit) -> [0/1 per row]."""
    e = evaluate(model, rows, bs, device, return_preds=True)
    return [int(is_hit(e['preds'][r['id']], r)) for r in rows]


def _draw(pool_by_family, fams, n, rng):
    """About n distinct rows spread evenly over `fams` (n // len(fams) each; a family short of rows hands its share to the others)."""
    fams = sorted(fams)
    take = {f: 0 for f in fams}
    left = min(n, sum(len(pool_by_family[f]) for f in fams))
    while left > 0:
        room = [f for f in fams if take[f] < len(pool_by_family[f])]
        per = max(left // len(room), 1)
        for f in room:
            k = min(per, len(pool_by_family[f]) - take[f], left)
            take[f] += k
            left -= k
            if left == 0:
                break
    out = []
    for f in fams:
        out += rng.sample(pool_by_family[f], take[f])
    return out, take


def _replay_only(model, rows, vocab, updates, lr, seed, device):
    """sleep.sleep with no replay rows: the whole batch is `rows`."""
    mv = max(math.ceil(updates * 64 / max(len(rows), 1)), 1)
    out = sleep.sleep(model, rows, [], vocab, sleep.SleepCfg(updates=updates, batch=64, lr=lr, warmup=10, seed=seed, max_visits=mv), device)
    model.eval()
    return out


def _fam_numbers(hm):
    return {f: dict(pre=v['a'], post=v['b'], drop=v['drop'], fires=v['fires']) for f, v in hm['families'].items()}


def repair(model, pre_hits, held_rows, repair_pool_by_family, vocab, device, seed, rounds=4, updates=64, lr=1e-3, n_records=N_RECORDS, log=_log):
    """R. The model (a copy; the argument is left alone) checks itself on `held_rows` against `pre_hits` (the same check before the night). Each round: the families that fire
    (harm_measure) get `updates` replay-only updates on `n_records` of their own non-held training rows, drawn evenly across the firing families (seed + round); re-check; stop early when
    nothing fires. -> (model, info: pre_in_dist, rounds [per check: round, fired, in_dist, in_dist_drop, passes, families, updates, records_by_family], updates (total), final_hits, final_fired)."""
    m = copy.deepcopy(model)
    m.eval()
    info = dict(pre_in_dist=100 * sum(pre_hits) / len(pre_hits), rounds=[], updates=0, rule='R = no outside help, not own choices: held-slice check, replay-only updates on the firing families\' other training rows')
    for i in range(rounds + 1):
        t0 = time.time()
        hits = held_hits(m, held_rows, device)
        hm = harm_measure(pre_hits, hits, held_rows)
        rd = dict(round=i, fired=hm['fired'], in_dist=hm['in_dist_b'], in_dist_drop=hm['in_dist_drop'], passes=hm['passes'], families=_fam_numbers(hm), updates=0, check_seconds=time.time() - t0)
        info['rounds'].append(rd)
        log('R round', i, 'fired', hm['fired'], 'held in_dist %.2f (pre %.2f)' % (hm['in_dist_b'], hm['in_dist_a']))
        if not hm['fired'] or i == rounds:
            info['final_hits'], info['final_fired'] = hits, hm['fired']
            break
        t0 = time.time()
        recs, take = _draw(repair_pool_by_family, hm['fired'], n_records, random.Random(seed + i))
        _replay_only(m, recs, vocab, updates, lr, seed + i, device)
        rd.update(updates=updates, records=len(recs), records_by_family=take, train_seconds=time.time() - t0)
        info['updates'] += updates
    return m, info


def spread(model, n_updates, repair_pool_by_family, vocab, device, seed, lr=1e-3, n_records=N_RECORDS):
    """Report-only arm E: the same number of updates as R used, batches drawn evenly over ALL families' repair rows. 0 updates = nothing. -> (model, info)."""
    m = copy.deepcopy(model)
    m.eval()
    if not n_updates:
        return m, dict(updates=0, records=0)
    recs, take = _draw(repair_pool_by_family, list(repair_pool_by_family), n_records, random.Random(seed))
    _replay_only(m, recs, vocab, n_updates, lr, seed, device)
    return m, dict(updates=n_updates, records=len(recs), records_by_family=take)


def _stage(pdir, name, key, fn, meta, vocab, device, resume, log):
    """A model stage cached as <name>.pt + <name>.pkl {key, v: info}: reloaded when the key matches (and resume), else fn() -> (model, info) is run and saved. -> (model, info, sha of the .pt)."""
    p = os.path.join(pdir, name + '.pt')
    c = {}
    if resume and os.path.exists(p) and os.path.exists(p[:-3] + '.pkl'):
        import pickle
        c = pickle.load(open(p[:-3] + '.pkl', 'rb'))
    if c.get('key') == key:
        m, _, _ = sleep.load_parent(p, device)
        m.eval()
        log(name, 'loaded', p)
        return m, c['v'], _sha_file(p)
    m, info = fn()
    sleep.save_parent(m, meta['name'], meta['cfg'], vocab, p, step=(meta['step'] or 0), warmup=True)
    import pickle
    pickle.dump(dict(key=key, v=info), open(p[:-3] + '.pkl', 'wb'))
    return m, info, _sha_file(p)


def skills_dev(m, skills_data, device, limit=None):
    """Skills DEV in_dist (measure only). -> (rows, per-row hits, pooled5 %, in_dist %); `limit` = rows spread evenly (smoke only)."""
    if not limit:
        return skills_hits(m, skills_data, device)
    from custom_io.evalx import CHAIN5
    rows = subsample(load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl')), limit)
    h = held_hits(m, rows, device)
    c5 = [x for x, r in zip(h, rows) if r['family'] in CHAIN5]
    return rows, h, 100 * sum(c5) / max(len(c5), 1), 100 * sum(h) / len(h)


def _strip(info):
    return {k: v for k, v in info.items() if k != 'final_hits'}


def r_parent(nprime, jdir, s3dir, out, skills_train, skills_data, seed=0, pool_limit=None, dev_limit=None, held_per_family=100, rounds=4, updates=64, lr=1e-3, n_records=N_RECORDS,
             skills_limit=None, device='cpu', name=None, resume=True, log=_log):
    """One parent's Test R. Night 1 = S3's W1 (from N'); night 2 = J's W arm (W1's day 2 -> W2.pt unrepaired). R and E repeat both nights on their own models with the same records: the night-2 records
    of W1r / W1e come from W1's day 2, not from their own day (disclosed in r.json). DIR/<name>/r.json is written after every stage; each model stage is cached (<stage>.pt + .pkl) and measures per model."""
    import pickle
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, jd, s3d = os.path.join(out, name), os.path.join(jdir, name), os.path.join(s3dir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    jj = json.load(open(os.path.join(jd, 'j.json')))
    s2 = jj['day2_seed']
    seed = jj['seed']
    ja = jj['args']
    pool_limit = ja['pool_limit'] if pool_limit is None else pool_limit
    assert s2 == seed + 1, f'j.json day2_seed {s2} != seed + 1'
    d2p, w2p = os.path.join(jd, 'day2_W.pkl'), os.path.join(jd, 'W2.pt')
    assert os.path.exists(d2p) and os.path.exists(w2p), f'J has not finished its W arm: need {d2p} and {w2p} (J may still be running)'
    tries = pickle.load(open(d2p, 'rb'))['v']['tries']
    w1p = os.path.join(s3d, 'W1.pt')
    assert os.path.exists(w1p), f'no {w1p}'
    res = dict(nprime=nprime, name=name, seed=seed, spec=__doc__.split('\n')[0], marks_rules=MARKS,
               args=dict(pool_limit=pool_limit, dev_limit=dev_limit, held_per_family=held_per_family, rounds=rounds, updates=updates, lr=lr, n_records=n_records, skills_limit=skills_limit,
                         j=jdir, s3=s3dir, skills_train=skills_train, skills_data=skills_data, replay_n=ja['replay_n'], visits=ja['visits']),
               note='skills TRAIN (held slice, repair rows), C2 pool and C2 DEV, skills DEV (MEASURE only: repair never reads DEV); test / labelled never opened',
               disclosure="R's and E's night-2 records are w_records(pool, W1's day-2 tries, s2 + 1), from W1's day 2 (J's W arm), not from their own day; the held slice rows are also among the replay rows (the whole skills train file) of every night")
    save = lambda: json.dump(res, open(os.path.join(pdir, 'r.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, ja['replay_n'], seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    assert len(tries) == len(pool), f'day2_W has {len(tries)} rows, pool {len(pool)}: pool_limit differs from J\'s'
    train = load_rows(skills_train)
    held, rpool = held_split(train, held_per_family, seed)
    res['held'] = dict(rows=len(held), per_family=held_per_family, families=len(rpool), repair_rows=sum(len(v) for v in rpool.values()), ids_sha256=_h([r['id'] for r in held]))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    W1, _, _ = sleep.load_parent(w1p, device)
    W1.eval()
    W2, _, _ = sleep.load_parent(w2p, device)
    W2.eval()
    sha = dict(N=_sha_file(nprime), W1=_sha_file(w1p), W2=_sha_file(w2p))
    hk = (res['held']['ids_sha256'], held_per_family)
    kw = dict(pdir=pdir, meta=meta, vocab=vocab, device=device, resume=resume, log=log)
    rkey = (rounds, updates, lr, n_records, seed)
    res['secs'] = secs
    # point 1 (after night 1): pre = N', post = W1
    t0 = time.time()
    hN = _cached(os.path.join(pdir, 'held_N.pkl'), ('N', sha['N'], hk), lambda: held_hits(N, held, device), resume, log, "held N'")
    secs['held_N'] = time.time() - t0
    t0 = time.time()
    W1r, i1r, sha['W1r'] = _stage(name='W1r', key=_h('W1r', sha['N'], sha['W1'], hk, rkey), fn=lambda: repair(W1, hN, held, rpool, vocab, device, seed + 100, rounds, updates, lr, n_records, log), **kw)
    secs['W1r'] = time.time() - t0
    res['point1'] = dict(R=_strip(i1r))
    save()
    t0 = time.time()
    W1e, i1e, sha['W1e'] = _stage(name='W1e', key=_h('W1e', sha['W1'], i1r['updates'], hk, rkey), fn=lambda: spread(W1, i1r['updates'], rpool, vocab, device, seed + 200, lr, n_records), **kw)
    secs['W1e'] = time.time() - t0
    res['point1']['E'] = i1e
    save()
    # point 2 (after night 2): the same records for every arm, from W1's day 2 (J's W arm)
    recs, cnt = w_records(pool, tries, s2 + 1)
    assert recs, 'no night-2 records'
    res['night2_records'] = dict(records=len(recs), source=d2p)
    hW1r = i1r['final_hits']
    t0 = time.time()
    def night2_r():
        mm, si = sleep_on(W1r, recs, vocab, replay, warm_rows, 1e-3, 32, s2, device)
        m2, ri = repair(mm, hW1r, held, rpool, vocab, device, seed + 300, rounds, updates, lr, n_records, log)
        return m2, dict(ri, night=si)
    W2r, i2r, sha['W2r'] = _stage(name='W2r', key=_h('W2r', sha['W1r'], len(recs), s2, hk, rkey), fn=night2_r, **kw)
    secs['W2r'] = time.time() - t0
    res['point2'] = dict(R=_strip(i2r))
    save()
    t0 = time.time()
    def night2_e():
        mm, si = sleep_on(W1e, recs, vocab, replay, warm_rows, 1e-3, 32, s2, device)
        m2, ei = spread(mm, i2r['updates'], rpool, vocab, device, seed + 400, lr, n_records)
        return m2, dict(ei, night=si)
    W2e, i2e, sha['W2e'] = _stage(name='W2e', key=_h('W2e', sha['W1e'], len(recs), s2, i2r['updates'], hk, rkey), fn=night2_e, **kw)
    secs['W2e'] = time.time() - t0
    res['point2']['E'] = i2e
    res['updates'] = dict(point1=i1r['updates'], point2=i2r['updates'])
    save()
    # measures (DEV, report and marks)
    models = dict(N=N, W1=W1, W1r=W1r, W1e=W1e, W2=W2, W2r=W2r, W2e=W2e)
    hits, c2, res['skills'], res['c2_dev'] = {}, {}, {}, {}
    rows = None
    for a, m in models.items():
        t0 = time.time()
        rows, h, p5, ia = _cached(os.path.join(pdir, f'skills_{a}.pkl'), ('skills', sha[a], skills_data, skills_limit), lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')[:4]
        hits[a] = h
        res['skills'][a] = dict(pooled5=p5, in_dist=ia, n=len(h))
        secs[f'skills_{a}'] = time.time() - t0
        t0 = time.time()
        c2[a] = _cached(os.path.join(pdir, f'c2_{a}.pkl'), ('c2', sha[a], dev_limit), lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        res['c2_dev'][a] = dict(first_try_right=sum(d['right'] for d in c2[a]) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c2[a]) / len(dev), n=len(dev))
        secs[f'c2_{a}'] = time.time() - t0
        log('measure', a, res['skills'][a], res['c2_dev'][a])
        save()
    hm = lambda b, a: harm_measure(hits[a], hits[b], rows)
    pairs = dict(W1_vs_N=('W1', 'N'), W1r_vs_N=('W1r', 'N'), W1e_vs_N=('W1e', 'N'), W2_vs_W1=('W2', 'W1'), W2r_vs_W1r=('W2r', 'W1r'), W2e_vs_W1e=('W2e', 'W1e'))
    res['harm'] = {k: hm(*v) for k, v in pairs.items()}
    res['harm_vs_N_report'] = {f'{b}_vs_N': hm(b, 'N') for b in ('W2', 'W2r', 'W2e')}
    right = lambda a: [float(d['right']) for d in c2[a]]
    res['first_try_boot'] = {k: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(right(a), right(b)))) for k, (a, b) in dict(W1r_minus_W1=('W1r', 'W1'), W2r_minus_W2=('W2r', 'W2')).items()}
    h1, h2 = res['harm']['W1r_vs_N'], res['harm']['W2r_vs_W1r']
    b1, b2 = res['first_try_boot']['W1r_minus_W1']['points'], res['first_try_boot']['W2r_minus_W2']['points']
    d1, d2 = res['skills']['N']['in_dist'] - res['skills']['W1r']['in_dist'], res['skills']['W1r']['in_dist'] - res['skills']['W2r']['in_dist']
    res['marks'] = dict(
        harm=dict(point1=h1['passes'], point2=h2['passes'], rule=MARKS['harm']),
        first_try=dict(point1_points=b1, point2_points=b2, point1=b1 >= -2.0, point2=b2 >= -2.0, rule=MARKS['first_try']),
        proved_wrong=dict(flag=d1 > 1.5, point1_in_dist_drop=d1, point2_in_dist_drop=d2, point2_flag=d2 > 1.5, rule=MARKS['proved_wrong']),
        report_only=dict(E_vs_R=dict(point1=dict(in_dist_R=res['skills']['W1r']['in_dist'], in_dist_E=res['skills']['W1e']['in_dist'], fired_R=h1['fired'], fired_E=res['harm']['W1e_vs_N']['fired']),
                                      point2=dict(in_dist_R=res['skills']['W2r']['in_dist'], in_dist_E=res['skills']['W2e']['in_dist'], fired_R=h2['fired'], fired_E=res['harm']['W2e_vs_W1e']['fired'])),
                         updates=res['updates'], rule=MARKS['report_only']))
    res['marks']['passes'] = bool(h1['passes'] and h2['passes'] and b1 >= -2.0 and b2 >= -2.0)
    res['marks']['passes_rule'] = MARKS['passes']
    secs['total'] = time.time() - t00
    save()
    log('MARKS', {k: v for k, v in res['marks'].items() if k != 'report_only' and not k.endswith('rule')})
    return res


def r(nprimes, jdir, s3dir, out, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: r_parent(p, jdir, s3dir, out, **kw) for p in nprimes}


def rreport(out, parents):
    """Test R verdict over the parents' DIR/<name>/r.json -> DIR/r-report.json: passes = every parent passes (a) and (b) at both points; proved_wrong = every parent's point-1 in_dist still > 1.5 below N'."""
    res = {p: json.load(open(os.path.join(out, p, 'r.json'))) for p in parents}
    mk = {p: x.get('marks') or {} for p, x in res.items()}
    rep = dict(parents=list(parents), passes=all(m.get('passes') is True for m in mk.values()), proved_wrong=all(m.get('proved_wrong', {}).get('flag') is True for m in mk.values()), per_parent=mk,
               updates={p: x.get('updates') for p, x in res.items()}, rules=MARKS)
    json.dump(rep, open(os.path.join(out, 'r-report.json'), 'w'), indent=1)
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('r'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--j', required=True); q.add_argument('--s3', required=True); q.add_argument('--out', required=True)
    q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True); q.add_argument('--pool-limit', type=int); q.add_argument('--dev-limit', type=int)
    q.add_argument('--held-per-family', type=int, default=100); q.add_argument('--rounds', type=int, default=4); q.add_argument('--updates', type=int, default=64); q.add_argument('--skills-limit', type=int)
    q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('rreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'rreport':
        print(json.dumps(rreport(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        r(a.nprime, ex(a.j), ex(a.s3), a.out, skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), pool_limit=a.pool_limit, dev_limit=a.dev_limit, held_per_family=a.held_per_family,
          rounds=a.rounds, updates=a.updates, skills_limit=a.skills_limit, device=a.device, resume=not a.no_resume)
