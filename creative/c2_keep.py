"""C2 job 7, "keep the parts" (roadmap sec. 7, decided 10-07). CPU, DEV only.  python3 -m creative.c2_keep --ckpt B2_s100.pt --warmed warm4.pt --out DIR --skills-train ... --skills-data ...
ONE CHANGE against jobs 5 and 6: every sleep (stepping stones, PC', each night) also replays the 2,048 warm add/mult solver rows: the replay half of each batch is split evenly
between the skills replay and these rows (sleep.sleep(replay_extra=...)). Same seeds, rows, pool, temperature rule and dose rule; dose visits widened once to 32.
 N'  = warmed parent + stepping-stone sleep with that replay.
 PARTS KEPT (else report and stop): fresh add/mult reach@32 >= 50% for N' and after each night; N' passes the cold-start gate (reach@32 >= 14.5% with sameness at its best T); skills harm
     <= 2 points (N' against the warmed parent; every later model against N').
 PC' = reference programs for every multi-step pool question (affine, sq_plus, double_add; one record each). Dose chosen on DEV with PC' (lr {3e-4, 1e-3} x visits {4, 8, 16, 32}): best
     multi-step greedy first try (fits and right), then reach@4, among settings with harm <= 2 and parts kept; frozen.
 FEASIBILITY: PC' - N' multi-step greedy first try (the 154 DEV questions of affine, sq_plus, double_add) >= +10 points. A miss = explanation (b); the climb retires on B2 (this parent stops).
 CLIMB: W' night 1 (from N', on N''s example-checked tries) and night 2 (from the night-1 model, sampling the pool again with it, on its own example-checked tries) at the frozen dose,
     updates = visits x records / 32 per night. Pass: multi-step first try W'(night 2) - N' >= +10 with the paired 95% interval above 0. Proved wrong: parts kept and the interval's
     upper end < +3. No R or H arms. Per kind, night 1, reach@4, reach@32 and records per kind are reported."""
import argparse, copy, json, math, os, time
from creative import c2_dev, c2_pilot, c2_stones, fewshot, legal, rules_real as R, sampler, sleep, stones
from creative.pilot import skills_eval

DATA = 'creative/data/c2'
TEMPS = c2_pilot.TEMPS
LRS, VISITS = (3e-4, 1e-3), (4, 8, 16, 32)
MULTI = ('affine', 'sq_plus', 'double_add')
PARTS_MIN = 0.5
COLD_MIN = 0.145
FEAS_POINTS, CLIMB_POINTS, WRONG_UPPER = 10.0, 10.0, 3.0
HARM_MAX = 2.0


def multi_right(per_q_right, dev):
    return [x for x, r in zip(per_q_right, dev) if r['kind'] in MULTI]


def pc_multi(pool):
    """PC': the reference solver program of every multi-step pool question, one record each. Key-independent."""
    out = []
    for row in pool:
        if row['kind'] in MULTI:
            t, _, qs = R.reference(row['kind'], tuple(row['params']))
            out.append(fewshot._record(row, R.remap(t, qs, fewshot.parse(row['prompt'])['q_slot']), 'PCm', 0))
    return out


def verdict_parent(feas_pass, parts_kept, climb):
    """Per-parent reading of the fixed marks (the roadmap thread combines the two parents)."""
    if not parts_kept:
        return 'parts not kept: report and stop'
    if not feas_pass:
        return 'feasibility miss: explanation (b), the climb retires on B2'
    d, lo, hi = climb
    if d >= CLIMB_POINTS and lo > 0:
        return 'climb pass (this parent)'
    if hi < WRONG_UPPER:
        return 'proved wrong (this parent): parts kept, no climb'
    return 'between the marks (comes back to the roadmap thread)'


def run(ckpt, out, skills_train=None, skills_data=None, warmed=None, device='cpu', seed=0, limit=None, pool_limit=None, n=32, temps=TEMPS, lrs=LRS, visits_grid=VISITS,
        visits=4, lr=3e-4, feas=FEAS_POINTS, parts_min=PARTS_MIN, cold_min=COLD_MIN, night2_min=32):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)
    res = dict(ckpt=ckpt, seed=seed, spec=__doc__.split('\n')[0],
               note='DEV only; test/labelled never opened; plain samples, no mask, repeats counted; the one change is the warm add/mult replay in every sleep; night 2 continues from the '
                    'night-1 model (as in job 6)')
    save = lambda: json.dump(res, open(os.path.join(out, 'c2_keep.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev')[:limit])
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool')[:pool_limit])
    fresh, _ = stones.fresh_practised(256, 1, 'fresh-check')
    fresh = c2_stones._with_nums(fresh)
    floors = c2_dev.floors_for(dev, os.path.join(out, 'dev_floors.json'))
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    if warmed and os.path.exists(warmed):
        m0, vocab, meta = sleep.load_parent(warmed, device)
        res['warm'] = dict(source=warmed)
    else:
        m0, vocab, meta, w = c2_stones._warm(ckpt, warm_rows, replay, 4, 3e-4, seed, device)
        res['warm'] = w
    sk_warm = skills_eval(m0, skills_data, device)

    def sleep_on(base, recs, lr_, v, updates=None):
        m = copy.deepcopy(base)
        u = updates if updates is not None else v * len(recs) // 32
        per = 32 if replay else 64
        mv = max(v, math.ceil(u * per / max(len(recs), 1)))
        so = sleep.sleep(m, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr_, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows)
        return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / max(len(recs), 1), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1))

    def prac(m):
        smp = legal.raw_samples(m, fresh, vocab, device, n=n, temperature=1.0, level=0, seed=seed)
        sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
        return dict(reach32=sc['reach32'], first_sample=sc['reach1'])

    # ---- N'
    ss_rows, ss_info = stones.make_stone_rows(2048, seed)
    N, ss = sleep_on(m0, stones.solver_records(ss_rows), lr, visits, updates=sleep.max_updates(2048, 64, bool(replay), visits))
    sleep.save_parent(N, meta['name'], meta['cfg'], vocab, os.path.join(out, 'Nprime.pt'), step=(meta['step'] or 0), warmup=True)
    sk_N = skills_eval(N, skills_data, device)
    harm_N = 100 * (sk_warm['pooled5'] - sk_N['pooled5']) if sk_N and sk_warm else None
    pN = prac(N)
    rep = c2_dev.dev_report(N, vocab, dev, floors, device, n, seed, temps=temps, extend=(), log=log)
    okT = {T: g for T, g in rep['temps'].items() if g['sameness_ok']}
    best = float(max(rep['temps'], key=lambda t: rep['temps'][t]['reach32']))
    gb = rep['temps'][str(best)]
    cold_ok = gb['reach32'] >= cold_min and gb['sameness_ok']
    res["N'"] = dict(sleep=ss, practised=pN, skills=sk_N, skills_harm_vs_warmed=harm_N, cold_start=dict(best_T=best, reach32=gb['reach32'], floor_reach32=gb['floor_reach32'],
                     sameness_ok=gb['sameness_ok'], verdict=gb['verdict'], passes=cold_ok),
                     grid={T: dict(reach32=g['reach32'], sameness_ok=g['sameness_ok'], distinct_rules=g['distinct_rules']) for T, g in rep['temps'].items()})
    parts_N = pN['reach32'] >= parts_min and cold_ok and (harm_N is None or harm_N <= HARM_MAX)
    res["N'"]['parts_kept'] = dict(practised_ge_50=pN['reach32'] >= parts_min, cold_start=cold_ok, skills_ok=harm_N is None or harm_N <= HARM_MAX, passes=parts_N)
    log("N'", res["N'"]['parts_kept'], pN)
    save()
    if not parts_N:
        res['stop'] = "parts not kept at N' (report and stop)"
        res['verdict'] = verdict_parent(True, False, (0, 0, 0))
        save()
        return res
    if not okT:
        res['stop'] = 'no temperature passes sameness'
        save()
        return res
    T = float(max(okT, key=lambda t: okT[t]['reach32']))
    res['pool_temperature'] = dict(chosen=T, rule='best DEV reach@32 among temperatures passing sameness (as job 6)')

    def evaluate(m, base_sk):
        g = c2_pilot.greedy_eval(m, dev, vocab, device)
        smp = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
        sc = fewshot.score_samples(dev, smp, ks=(1, 4, 32))
        bk = {}
        for k in sorted({r['kind'] for r in dev}):
            pq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] == k]
            bk[k] = dict(reach4=sum(d['reach4'] for d in pq) / len(pq), reach32=sum(d['reach32'] for d in pq) / len(pq))
        mq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] in MULTI]
        sk = skills_eval(m, skills_data, device)
        harm = 100 * (base_sk['pooled5'] - sk['pooled5']) if sk and base_sk else None
        mr = multi_right(g['per_q_right'], dev)
        return dict(greedy=dict(by_kind=g['by_kind'], fits=g['fits'], right=g['right'], multi_right=sum(mr) / len(mr)), reach4=sc['reach4'], reach32=sc['reach32'],
                    multi_reach4=sum(d['reach4'] for d in mq) / len(mq), multi_reach32=sum(d['reach32'] for d in mq) / len(mq), reach_by_kind=bk, practised=prac(m), skills=sk,
                    skills_harm_points=harm), g['per_q_right']

    rN, qN = evaluate(N, sk_N)
    res['arms'] = {"N'": rN}
    # ---- samples, W' records night 1
    samples = legal.raw_samples(N, pool, vocab, device, n=n, temperature=T, level=0, seed=seed + 1)
    a1 = fewshot.build_arms(pool, samples, samples, seed=seed)
    cnt1 = a1['counts']
    kind_of = {r['id']: r['kind'] for r in pool}
    res['night1_records'] = dict(n=len(a1['W']), by_kind={k: sum(c for i, c in cnt1.items() if kind_of[i] == k) for k in sorted({r['kind'] for r in pool})})
    PC = pc_multi(pool)
    res["PC'"] = dict(records=len(PC))
    save()
    if not a1['W']:
        res['stop'] = 'no W records'
        save()
        return res
    # ---- dose on PC'
    grid = {}
    for lr_ in lrs:
        for v in visits_grid:
            m, info = sleep_on(N, PC, lr_, v)
            r, q = evaluate(m, sk_N)
            kept = r['practised']['reach32'] >= parts_min
            grid[(lr_, v)] = dict(lr=lr_, visits=v, **info, multi_first_try=r['greedy']['multi_right'], pooled_first_try=r['greedy']['right'], reach4=r['reach4'],
                                  practised_reach32=r['practised']['reach32'], skills_harm_points=r['skills_harm_points'],
                                  eligible=(r['skills_harm_points'] is None or r['skills_harm_points'] <= HARM_MAX) and kept)
            res['dose_grid'] = [grid[k] for k in sorted(grid)]
            save()
            log('dose', grid[(lr_, v)])
    elig = [k for k in grid if grid[k]['eligible']]
    if not elig:
        res['stop'] = "no PC' dose keeps the parts (harm <= 2 and fresh add/mult >= 50%): parts not kept, report and stop"
        res['verdict'] = verdict_parent(True, False, (0, 0, 0))
        save()
        return res
    lr_, v = max(elig, key=lambda k: (grid[k]['multi_first_try'], grid[k]['reach4']))
    res['dose_choice'] = dict(lr=lr_, visits=v, rule="best multi-step greedy first try then reach@4 among settings with skills harm <= 2 and fresh add/mult reach@32 >= 50%; frozen")
    pcm, info = sleep_on(N, PC, lr_, v)
    rPC, qPC = evaluate(pcm, sk_N)
    res['arms']["PC'"] = dict(sleep=info, **rPC)
    d, lo, hi = c2_pilot.boot(multi_right(qPC, dev), multi_right(qN, dev))
    res['feasibility'] = dict(pcp_minus_np_multi_first_try_points=d, ci=[lo, hi], threshold=feas, passes=d >= feas, n_multi_dev=len(multi_right(qN, dev)))
    log('feasibility', res['feasibility'])
    save()
    if d < feas:
        res['stop'] = "PC' feasibility gate missed: explanation (b), the climb retires on B2"
        res['verdict'] = verdict_parent(False, True, (0, 0, 0))
        save()
        return res
    # ---- climb: night 1, night 2
    W1, info1 = sleep_on(N, a1['W'], lr_, v)
    r1, q1 = evaluate(W1, sk_N)
    res['arms']["W' night 1"] = dict(sleep=info1, **r1)
    res['arms']["W' night 1"]['parts_kept'] = r1['practised']['reach32'] >= parts_min and (r1['skills_harm_points'] is None or r1['skills_harm_points'] <= HARM_MAX)
    save()
    log("W' night 1", {'multi_first_try': r1['greedy']['multi_right'], 'right': r1['greedy']['right'], 'practised': r1['practised']})
    if not res['arms']["W' night 1"]['parts_kept']:
        res['stop'] = "parts not kept after night 1 (report and stop)"
        res['verdict'] = verdict_parent(True, False, (0, 0, 0))
        save()
        return res
    s2 = legal.raw_samples(W1, pool, vocab, device, n=n, temperature=T, level=0, seed=seed + 2)
    a2 = fewshot.build_arms(pool, s2, s2, seed=seed + 2)
    res['night2_records'] = dict(n=len(a2['W']), by_kind={k: sum(c for i, c in a2['counts'].items() if kind_of[i] == k) for k in sorted({r['kind'] for r in pool})})
    if len(a2['W']) < night2_min:
        res['stop'] = 'night 2 has too few records'
        save()
        return res
    W2, info2 = sleep_on(W1, a2['W'], lr_, v)
    r2, q2 = evaluate(W2, sk_N)
    res['arms']["W' night 2"] = dict(sleep=info2, **r2)
    parts2 = r2['practised']['reach32'] >= parts_min and (r2['skills_harm_points'] is None or r2['skills_harm_points'] <= HARM_MAX)
    d, lo, hi = c2_pilot.boot(multi_right(q2, dev), multi_right(qN, dev))
    d1, lo1, hi1 = c2_pilot.boot(multi_right(q1, dev), multi_right(qN, dev))
    gk = {k: 100 * (r2['greedy']['by_kind'][k]['right'] - rN['greedy']['by_kind'][k]['right']) for k in rN['greedy']['by_kind']}
    res['climb'] = dict(multi_W2_minus_Nprime=dict(points=d, lo=lo, hi=hi), multi_W1_minus_Nprime=dict(points=d1, lo=lo1, hi=hi1), by_kind_W2_minus_Nprime_points=gk,
                        pooled_W2_minus_Nprime_points=100 * (r2['greedy']['right'] - rN['greedy']['right']), parts_kept_after_night2=parts2,
                        marks=dict(pass_if='multi-step first try W(night 2) - N >= +10 with the paired 95% interval above 0, both parents',
                                   wrong_if='parts kept and the interval upper end < +3, both parents'))
    res['verdict'] = verdict_parent(True, parts2, (d, lo, hi))
    res['seconds'] = time.time() - t0
    save()
    log('DONE', res['climb'], res['verdict'])
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--skills-data')
    a.add_argument('--warmed'); a.add_argument('--device', default='cpu'); a.add_argument('--seed', type=int, default=0); a.add_argument('--limit', type=int); a.add_argument('--pool-limit', type=int)
    a = a.parse_args()
    run(a.ckpt, a.out, a.skills_train, a.skills_data, a.warmed, a.device, a.seed, a.limit, a.pool_limit)
