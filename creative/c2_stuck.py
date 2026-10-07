"""C2 job 8, "more tries where it's stuck" (roadmap sec. 7, decided 10-07). CPU, DEV only.
  python3 -m creative.c2_stuck --nprime ~/creative/c2keep-s100/Nprime.pt --out DIR --skills-train ... --skills-data ...
ONE CHANGE against job 7, blind to rule kind: each night every pool question is sampled 32 times at T 3.0 (pass 1); every pool question with NO example-fitting try then gets 480 more
tries at T 3.0 (pass 2, 512 in all); questions that already have a fitting try get nothing more. Records = at most 2 distinct fitting tries per question. The allocation reads only
whether a question has a fitting try, never its kind (tests/test_c2_keep-style leak test: tests/test_c2_stuck.py).
FROZEN from job 7, no grid: start from N' (job 7's Nprime.pt; rebuilt exactly as job 7 did if missing and --ckpt/--warmed are given); pool T 3.0; dose lr 1e-3 x 32 visits, updates = 32 x
records / 32 per night; every sleep replays the warm add/mult rows and the skills data (16 + 16 of the 32). Night 2 starts from the night-1 model and resamples the pool with it, same search.
MARKS (fixed; the roadmap thread rules): 1 parts kept: fresh add/mult reach@32 >= 50% and skills harm <= 2 vs N' after each night, else this parent reports and stops. 2 search check: night-1
multi-step records >= 75 (s100) / >= 90 (s101). 3 climb: multi-step first try W(night 2) - N' >= +10 with the paired 95% interval above 0 on both parents. 4 proved wrong: search check passes and
the night-2 interval's upper end < +3 on both parents. 5 anything else goes back. The json carries a per-parent reading only."""
import argparse, copy, json, math, os, random, time
from creative import c2_dev, c2_keep, c2_pilot, c2_stones, fewshot, legal, rules_real as R, sleep, stones
from creative.pilot import skills_eval

DATA = 'creative/data/c2'
T_POOL, LR, VISITS = 3.0, 1e-3, 32
N1, N2 = 32, 480
MULTI = c2_keep.MULTI
SEARCH_MIN = {'s100': 75, 's101': 90}


def pyfit(p, t):
    """Cheap exact prefilter for fewshot.verdict == 'accept': a try that fails the structure rules or the python executor's example check can never be accepted (the torch executor
    only adds an agreement test), so the 2.5 ms torch check runs on survivors only."""
    try:
        if not fewshot.structure(p, t)[0]:
            return False
        a = fewshot.outputs_py(p, t)
        return all(o is not None for o in a) and a[:-1] == p['ys']
    except Exception:
        return False


def fits(p, t):
    return pyfit(p, t) and fewshot.verdict(p, t)[0] == 'accept'


def has_fit(rows, tries):
    """Per question: does any try fit every example? Reads only the example check (the key is not looked at, and neither is the kind)."""
    return [any(fits(fewshot.parse(r['prompt']), x.t) for x in tr) for r, tr in zip(rows, tries)]


def search(model, pool, vocab, device, seed, T=T_POOL, n1=N1, n2=N2):
    """Two-pass search. -> (combined tries per question in sampling order, fit1, fit_final, drawn dict). Allocation depends only on has_fit of pass 1."""
    t1 = legal.raw_samples(model, pool, vocab, device, n=n1, temperature=T, level=0, seed=seed)
    fit1 = has_fit(pool, t1)
    stuck = [i for i, f in enumerate(fit1) if not f]
    tries = [list(t) for t in t1]
    if stuck:
        t2 = legal.raw_samples(model, [pool[i] for i in stuck], vocab, device, n=n2, temperature=T, level=0, seed=seed + 1000)
        for i, t in zip(stuck, t2):
            tries[i] += t
    fit = has_fit(pool, tries)
    return tries, fit1, fit, dict(pass1=n1 * len(pool), pass2=n2 * len(stuck), stuck_questions=len(stuck))


def w_records(pool, tries, seed, per_cap=2, arm='W'):
    """At most `per_cap` distinct example-fitting tries per question, answered by the try's own output (same selection as fewshot.build_arms' W)."""
    rng = random.Random(seed)
    out, counts = [], {}
    for row, tr in zip(pool, tries):
        p = fewshot.parse(row['prompt'])
        kept = fewshot._distinct(p, [x for x in tr if pyfit(p, x.t)], rng, per_cap, lambda rules, full: full[0] == 'accept')
        for k, t in enumerate(kept):
            out.append(fewshot._record(row, t, arm, k))
        if kept:
            counts[row['id']] = len(kept)
    return out, counts


def verdict_parent(parts_kept, search_ok, climb):
    d, lo, hi = climb
    if not parts_kept:
        return 'parts not kept: report and stop'
    if d >= 10.0 and lo > 0:
        return 'climb pass (this parent)' + ('' if search_ok else '; search check missed')
    if search_ok and hi < 3.0:
        return 'proved wrong (this parent): search check passed, no climb'
    return 'between the marks / search check missed (comes back to the roadmap thread)'


def run(nprime, out, skills_train=None, skills_data=None, ckpt=None, warmed=None, device='cpu', seed=0, limit=None, pool_limit=None, search_min=None, n1=N1, n2=N2,
        parts_min=0.5, lr=LR, visits=VISITS, T=T_POOL, min_records=32):
    os.makedirs(out, exist_ok=True)
    t00 = time.time()
    log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)
    res = dict(nprime=nprime, seed=seed, spec=__doc__.split('\n')[0], frozen=dict(T=T, lr=lr, visits=visits, n1=n1, n2=n2),
               note='DEV only; test/labelled never opened; no kind label touches allocation or records; night 2 continues from the night-1 model')
    save = lambda: json.dump(res, open(os.path.join(out, 'c2_stuck.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev')[:limit])
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool')[:pool_limit])
    fresh, _ = stones.fresh_practised(256, 1, 'fresh-check')
    fresh = c2_stones._with_nums(fresh)
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    kind_of = {r['id']: r['kind'] for r in pool}
    kinds = sorted({r['kind'] for r in pool})

    def sleep_on(base, recs):
        m = copy.deepcopy(base)
        u = visits * len(recs) // 32
        per = 32 if replay else 64
        mv = max(visits, math.ceil(u * per / max(len(recs), 1)))
        so = sleep.sleep(m, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows)
        return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / max(len(recs), 1), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1))

    t0 = time.time()
    if nprime and os.path.exists(nprime):
        N, vocab, meta = sleep.load_parent(nprime, device)
        res['N_prime'] = dict(source=nprime)
    else:
        if not (ckpt and warmed and os.path.exists(warmed)):
            raise SystemExit("N' checkpoint missing and no --ckpt/--warmed to rebuild it")
        m0, vocab, meta = sleep.load_parent(warmed, device)
        ss_rows, _ = stones.make_stone_rows(2048, seed)
        recs = stones.solver_records(ss_rows)
        N = copy.deepcopy(m0)
        cfg = sleep.SleepCfg(updates=sleep.max_updates(2048, 64, bool(replay), 4), batch=64, lr=3e-4, warmup=20, seed=seed, max_visits=4)
        sleep.sleep(N, recs, replay, vocab, cfg, device, replay_extra=warm_rows)
        res['N_prime'] = dict(source='REBUILT as job 7 did (checkpoint missing)')
    N.eval()
    sk_N = skills_eval(N, skills_data, device)

    def prac(m):
        smp = legal.raw_samples(m, fresh, vocab, device, n=32, temperature=1.0, level=0, seed=seed)
        sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
        return dict(reach32=sc['reach32'], first_sample=sc['reach1'])

    def evaluate(m):
        g = c2_pilot.greedy_eval(m, dev, vocab, device)
        smp = legal.raw_samples(m, dev, vocab, device, n=32, temperature=T, level=0, seed=seed)
        sc = fewshot.score_samples(dev, smp, ks=(1, 4, 32))
        bk = {}
        for k in kinds:
            pq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] == k]
            bk[k] = dict(first_try=g['by_kind'][k]['right'], reach4=sum(d['reach4'] for d in pq) / len(pq), reach32=sum(d['reach32'] for d in pq) / len(pq))
        mq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] in MULTI]
        sk = skills_eval(m, skills_data, device)
        harm = 100 * (sk_N['pooled5'] - sk['pooled5']) if sk and sk_N else None
        mr = c2_keep.multi_right(g['per_q_right'], dev)
        return dict(by_kind=bk, pooled_first_try=g['right'], multi_first_try=sum(mr) / len(mr), pooled_reach4=sc['reach4'], pooled_reach32=sc['reach32'],
                    multi_reach4=sum(d['reach4'] for d in mq) / len(mq), multi_reach32=sum(d['reach32'] for d in mq) / len(mq), practised=prac(m), skills=sk,
                    skills_harm_points=harm), g['per_q_right']

    rN, qN = evaluate(N)
    res["N'"] = rN
    res['seconds'] = dict(build_Nprime_and_eval=time.time() - t0)
    save()
    model, nights, per_q, ok_all = N, {}, {}, True
    for night in (1, 2):
        ts = time.time()
        tries, fit1, fit, drawn = search(model, pool, vocab, device, seed + 10 * night, T, n1, n2)
        t_search = time.time() - ts
        recs, counts = w_records(pool, tries, seed + night)
        rec_kind = {k: sum(c for i, c in counts.items() if kind_of[i] == k) for k in kinds}
        found = {k: dict(pass1=sum(1 for r, f in zip(pool, fit1) if r['kind'] == k and f),
                         pass2=sum(1 for r, f1, f2 in zip(pool, fit1, fit) if r['kind'] == k and f2 and not f1), pool_questions=sum(r['kind'] == k for r in pool)) for k in kinds}
        info = dict(samples=drawn, records=len(recs), records_by_kind=rec_kind, multi_step_records=sum(rec_kind[k] for k in MULTI), questions_with_find_by_kind=found)
        log('night', night, info)
        nights[night] = info
        res[f'night{night}_search'] = info
        res['seconds'][f'night{night}_search'] = t_search
        save()
        if len(recs) < min_records:
            res['stop'] = f'night {night}: too few records'
            save()
            return res
        ts = time.time()
        model, sinfo = sleep_on(model, recs)
        res['seconds'][f'night{night}_sleep'] = time.time() - ts
        ts = time.time()
        r, q = evaluate(model)
        res['seconds'][f'night{night}_eval'] = time.time() - ts
        parts = r['practised']['reach32'] >= parts_min and (r['skills_harm_points'] is None or r['skills_harm_points'] <= c2_keep.HARM_MAX)
        d, lo, hi = c2_pilot.boot(c2_keep.multi_right(q, dev), c2_keep.multi_right(qN, dev))
        res[f'night{night}'] = dict(sleep=sinfo, **r, parts_kept=parts, multi_W_minus_Nprime=dict(points=d, lo=lo, hi=hi),
                                    pooled_W_minus_Nprime_points=100 * (r['pooled_first_try'] - rN['pooled_first_try']),
                                    by_kind_W_minus_Nprime_points={k: 100 * (r['by_kind'][k]['first_try'] - rN['by_kind'][k]['first_try']) for k in kinds})
        save()
        log('night', night, 'multi W-N', (d, lo, hi), 'practised', r['practised'], 'harm', r['skills_harm_points'])
        if not parts:
            res['stop'] = f'parts not kept after night {night} (report and stop)'
            res['verdict'] = verdict_parent(False, True, (0, 0, 0))
            save()
            return res
    smin = search_min
    if smin is None:
        for k, v in SEARCH_MIN.items():
            if k in out:
                smin = v
    n1rec = nights[1]['multi_step_records']
    search_ok = None if smin is None else n1rec >= smin
    c = res['night2']['multi_W_minus_Nprime']
    res['search_check'] = dict(night1_multi_step_records=n1rec, required=smin, passes=search_ok)
    res['verdict'] = verdict_parent(True, bool(search_ok), (c['points'], c['lo'], c['hi']))
    res['marks'] = dict(climb='multi-step first try W(night 2) - N >= +10 with the paired 95% interval above 0, both parents', proved_wrong='search check passes and the night-2 upper end < +3, both parents')
    res['seconds']['total'] = time.time() - t00
    save()
    log('DONE', res['search_check'], c, res['verdict'])
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--nprime', required=True); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--skills-data')
    a.add_argument('--ckpt', help='only to rebuild N\' when --nprime is missing'); a.add_argument('--warmed', help='only to rebuild N\' when --nprime is missing')
    a.add_argument('--device', default='cpu'); a.add_argument('--seed', type=int, default=0); a.add_argument('--limit', type=int); a.add_argument('--pool-limit', type=int)
    a.add_argument('--search-min', type=int)
    a = a.parse_args()
    run(a.nprime, a.out, a.skills_train, a.skills_data, a.ckpt, a.warmed, a.device, a.seed, a.limit, a.pool_limit, a.search_min)
