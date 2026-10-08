"""C2b DEV pilot (roadmap sec. 7, decided 10-07). CPU.  python3 -m creative.c2_pilot --ckpt B2_s100.pt --out DIR --skills-train train.jsonl --skills-data data_big
N = the stepping-stone parent (raw B2 -> warm-up on add/mult solver rows -> SS sleep; exactly job 5's SS arm, same seed and rows). DEV only: test and labelled are never opened.
 1. pool temperature: DEV gate on N over T in 0.5..6.0 (4.0 and 6.0 added once, standing rule); T = best DEV reach@32 among temperatures that pass sameness.
 2. N samples the 1,024 pool questions 32 times at T (plain, no mask, repeats kept). Arms (build_arms): W = tries that fit every example (<= 2 distinct per question),
    R = tries that fail the example check (same questions, same count), H = R's tries relabelled with what they compute on the shown examples, PC = the kind's reference
    solver program for W's questions (same count). No answer key touches W, R, H or PC: the corrupt-every-key test rebuilds the arms with every key corrupted and demands identical records.
 3. sleep dose chosen on DEV with PC only: lr {3e-4, 1e-3} x visits {4, 8, 16}, updates = visits x records / 32, pooled-5 skills harm vs N <= 2 points, then the pick (best DEV pooled
    greedy first try that FITS AND IS RIGHT, then reach@4) is frozen for every arm.
 4. PC FEASIBILITY GATE: PC - N greedy first try (fits and right), pooled over DEV, >= +15 points. If it misses, this parent stops here and reports.
 5. W, R, H at the frozen dose (same updates for every arm). Measured on DEV for N and every arm: greedy first try (fits, right) per kind and pooled, reach@4 and reach@32 over 32
    plain samples with repeats at T, the practised-kind check (256 fresh add/mult), pooled-5 skills harm vs N; paired bootstrap 95% intervals for W-N and W-R.
 6. Night 2 (REPORT ONLY): W's model samples the pool again at T, sleeps again on its new hits (same dose), and reports per-kind reach@32 and first try.
 Label (fixed in the roadmap): pooled W-N >= +15 carried by square and last_digit alone (affine, sq_plus, double_add each within 2 points of N) reads "PASS, near-copy kinds only"."""
import argparse, copy, json, math, os, random, time
from creative import c2_dev, c2_stones, fewshot, legal, rules_real as R, sampler, sleep, stones
from creative.pilot import skills_eval

DATA = 'creative/data/c2'
TEMPS = (0.5, 0.7, 1.0, 1.4, 2.0, 3.0, 4.0, 6.0)
LRS, VISITS = (3e-4, 1e-3), (4, 8, 16)
SKILLS_HARM_MAX = 2.0
PC_GATE_POINTS = 15.0
COPY_KINDS = ('square', 'last_digit')
HARD_KINDS = ('affine', 'sq_plus', 'double_add')


def greedy_eval(m, dev, vocab, device):
    """B2's plain greedy first try per DEV question: fits every example / fits and equals the key (the key only scores it). -> dict(by_kind, fits, right, per_q_right)."""
    m.eval()
    gt = sampler.greedy_tries(m, dev, vocab, device, level=0)
    per, fits = [], []
    by = {}
    for r, t in zip(dev, gt):
        v = fewshot.verdict(fewshot.parse(r['prompt']), t.t)
        f, ok = v[0] == 'accept', v[0] == 'accept' and str(v[2]) in r['accepted']
        fits.append(f)
        per.append(ok)
        d = by.setdefault(r['kind'], [0, 0, 0])
        d[0] += 1
        d[1] += f
        d[2] += ok
    return dict(by_kind={k: dict(n=d[0], fits=d[1] / d[0], right=d[2] / d[0]) for k, d in by.items()}, fits=sum(fits) / len(dev), right=sum(per) / len(dev), per_q_right=per)


def boot(a, b, iters=2000, seed=0):
    """Paired bootstrap over questions of mean(a) - mean(b), in points. -> (diff, lo, hi) 95%."""
    rng = random.Random(seed)
    n = len(a)
    d = [x - y for x, y in zip(a, b)]
    ms = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return 100 * sum(d) / n, 100 * ms[int(0.025 * iters)], 100 * ms[int(0.975 * iters)]


def label(by_kind_gain, pooled_gain):
    """by_kind_gain = {kind: W - N greedy right in points}. Pooled pass needs >= +15 (W's mark)."""
    if pooled_gain < 15:
        return 'no pooled pass (W - N < +15 points)'
    if all(abs(by_kind_gain.get(k, 0.0)) <= 2.0 for k in HARD_KINDS) and any(by_kind_gain.get(k, 0.0) > 2.0 for k in COPY_KINDS):
        return 'PASS, near-copy kinds only'
    return 'PASS on pooled first try, beyond the near-copy kinds'


def pc_records(pool, counts):
    """PC: the reference solver program of each W question's kind, `counts[id]` records per question (same count as W). Key-independent."""
    out = []
    for row in pool:
        n = counts.get(row['id'], 0)
        if n:
            t, _, qs = R.reference(row['kind'], tuple(row['params']))
            q = fewshot.parse(row['prompt'])['q_slot']
            for k in range(n):
                out.append(fewshot._record(row, R.remap(t, qs, q), 'PC', k))
    return out


def leak_test(pool, samples, arms):
    """Corrupt every answer key and rebuild: W, R, H records must be identical (no key reaches a record) and the PC build must not read it either."""
    bad = [dict(r, answer='-7', accepted=['-7']) for r in pool]
    a2 = fewshot.build_arms(bad, samples, samples, seed=0)
    same = all([(x['prompt'], x['answer']) for x in arms[k]] == [(x['prompt'], x['answer']) for x in a2[k]] for k in ('W', 'R', 'H'))
    pc_same = [(x['prompt'], x['answer']) for x in pc_records(pool, arms['counts'])] == [(x['prompt'], x['answer']) for x in pc_records(bad, arms['counts'])]
    return dict(records_identical=bool(same), pc_identical=bool(pc_same), passes=bool(same and pc_same))


def run(ckpt, out, skills_train=None, skills_data=None, warmed=None, device='cpu', seed=0, limit=None, pool_limit=None, n=32, temps=TEMPS, lrs=LRS, visits_grid=VISITS, visits=4, lr=3e-4, pc_gate=PC_GATE_POINTS):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)
    res = dict(ckpt=ckpt, seed=seed, spec=__doc__.split('\n')[0], note='DEV only; test/labelled never opened; plain samples, no mask, repeats counted; the pool temperature and the sleep dose are '
               'picked on DEV (tuning split) by the rules in the module doc; night 2 is report only')
    save = lambda: json.dump(res, open(os.path.join(out, 'c2_pilot.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev')[:limit])
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool')[:pool_limit])
    fresh, _ = stones.fresh_practised(256, 1, 'fresh-check')
    fresh = c2_stones._with_nums(fresh)
    floors = c2_dev.floors_for(dev, os.path.join(out, 'dev_floors.json'))
    # ---- N = the stepping-stone parent
    if warmed and os.path.exists(warmed):
        m0, vocab, meta = sleep.load_parent(warmed, device)
        res['warm'] = dict(source=warmed)
    else:
        m0, vocab, meta, w = c2_stones._warm(ckpt, R.warm_records(R.load_split(DATA, 'warm')), replay, 4, 3e-4, seed, device)
        res['warm'] = w
    ss_rows, ss_info = stones.make_stone_rows(2048, seed)
    N, ss = c2_stones._arm(m0, stones.solver_records(ss_rows), replay, vocab, visits, lr, seed, device)
    res['N'] = dict(sleep=ss, stones=ss_info['kinds'])
    sleep.save_parent(N, meta['name'], meta['cfg'], vocab, os.path.join(out, 'N_ss.pt'), step=(meta['step'] or 0), warmup=True)
    log('N built', ss)

    def prac(m):
        smp = legal.raw_samples(m, fresh, vocab, device, n=n, temperature=1.0, level=0, seed=seed)
        sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
        return dict(reach32=sc['reach32'], first_sample=sc['reach1'])

    base_sk = skills_eval(N, skills_data, device)
    res['N']['skills'] = base_sk
    # ---- 1. pool temperature
    rep = c2_dev.dev_report(N, vocab, dev, floors, device, n, seed, temps=temps, extend=(), log=log)
    ok = {T: g for T, g in rep['temps'].items() if g['sameness_ok']}
    res['pool_temperature'] = dict(grid={T: dict(reach32=g['reach32'], sameness_ok=g['sameness_ok'], distinct_rules=g['distinct_rules'], verdict=g['verdict']) for T, g in rep['temps'].items()},
                                   rule='best DEV reach@32 among temperatures passing sameness (>= 4 distinct rule-following programs); grid widened once to 4.0 and 6.0')
    if not ok:
        res['stop'] = 'no temperature passes sameness'
        save()
        return res
    T = float(max(ok, key=lambda t: ok[t]['reach32']))
    res['pool_temperature']['chosen'] = T
    log('pool T', T)
    save()

    def evaluate(m):
        g = greedy_eval(m, dev, vocab, device)
        smp = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
        sc = fewshot.score_samples(dev, smp, ks=(1, 4, 32))
        bk = {}
        for k in sorted({r['kind'] for r in dev}):
            pq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] == k]
            bk[k] = dict(reach4=sum(d['reach4'] for d in pq) / len(pq), reach32=sum(d['reach32'] for d in pq) / len(pq))
        sk = skills_eval(m, skills_data, device)
        harm = 100 * (base_sk['pooled5'] - sk['pooled5']) if sk and base_sk else None
        return dict(greedy=dict(by_kind=g['by_kind'], fits=g['fits'], right=g['right']), reach4=sc['reach4'], reach32=sc['reach32'], reach_by_kind=bk, luck=sc['luck'],
                    practised=prac(m), skills=sk, skills_harm_points=harm), g['per_q_right']

    rN, qN = evaluate(N)
    res['arms'] = dict(N=rN)
    # ---- 2. arms from N's pool samples
    samples = legal.raw_samples(N, pool, vocab, device, n=n, temperature=T, level=0, seed=seed + 1)
    arms = fewshot.build_arms(pool, samples, samples, seed=seed)
    counts = arms['counts']
    PC = pc_records(pool, counts)
    res['arm_build'] = dict(diag=arms['diag'], questions_with_W=len(counts), n_PC=len(PC), W_by_kind={k: sum(c for i, c in counts.items() if next(r for r in pool if r['id'] == i)['kind'] == k)
                                                                                                for k in sorted({r['kind'] for r in pool})})
    res['leak_test'] = leak_test(pool, samples, arms)
    log('arms', res['arm_build'], res['leak_test'])
    save()
    if not res['leak_test']['passes'] or not arms['W']:
        res['stop'] = 'leak test failed or no W records'
        save()
        return res
    upd = lambda recs, v: v * len(arms['W']) // 32

    def sleep_arm(base, recs, lr_, v, label_):
        m = copy.deepcopy(base)
        u = upd(recs, v)
        per = 32 if replay else 64
        mv = max(v, math.ceil(u * per / max(len(recs), 1)))              # a short arm (R) revisits its records more; reported
        so = sleep.sleep(m, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr_, warmup=20, seed=seed, max_visits=mv), device)
        return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / max(len(recs), 1), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1))

    # ---- 3. dose on PC
    grid = {}
    for lr_ in lrs:
        for v in visits_grid:
            m, info = sleep_arm(N, PC, lr_, v, 'PC')
            g = greedy_eval(m, dev, vocab, device)
            smp = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
            sc = fewshot.score_samples(dev, smp, ks=(4, 32))
            sk = skills_eval(m, skills_data, device)
            harm = 100 * (base_sk['pooled5'] - sk['pooled5']) if sk and base_sk else None
            grid[(lr_, v)] = dict(lr=lr_, visits=v, **info, dev_first_try_right=g['right'], dev_first_try_fits=g['fits'], dev_reach4=sc['reach4'], dev_reach32=sc['reach32'],
                                  skills_harm_points=harm, within_skills_limit=harm is None or harm <= SKILLS_HARM_MAX)
            res['dose_grid'] = [grid[k] for k in sorted(grid)]
            save()
            log('dose', {k: x for k, x in grid[(lr_, v)].items()})
    within = [k for k in grid if grid[k]['within_skills_limit']]
    if not within:
        res['stop'] = 'no PC dose within the 2-point skills-harm limit'
        save()
        return res
    best = max(within, key=lambda k: (grid[k]['dev_first_try_right'], grid[k]['dev_reach4']))
    lr_, v = best
    res['dose_choice'] = dict(lr=lr_, visits=v, updates=grid[best]['updates'], rule='best DEV pooled greedy first try (fits and right), then reach@4, among settings with skills harm <= 2 points; frozen')
    # ---- 4. PC feasibility gate
    pcm, info = sleep_arm(N, PC, lr_, v, 'PC')
    rPC, qPC = evaluate(pcm)
    res['arms']['PC'] = dict(sleep=info, **rPC)
    gain = 100 * (rPC['greedy']['right'] - rN['greedy']['right'])
    res['pc_gate'] = dict(pc_minus_n_first_try_points=gain, threshold=pc_gate, passes=gain >= pc_gate, ci=boot(qPC, qN))
    log('PC gate', res['pc_gate'])
    save()
    if gain < pc_gate:
        res['stop'] = 'PC feasibility gate missed on this parent: the W mark is out of reach by design; back to the roadmap thread'
        save()
        return res
    # ---- 5. W, R, H
    models, per_q = {}, {'N': qN, 'PC': qPC}
    for name in ('W', 'R', 'H'):
        m, info = sleep_arm(N, arms[name], lr_, v, name)
        r, q = evaluate(m)
        res['arms'][name] = dict(sleep=info, **r)
        models[name], per_q[name] = m, q
        save()
        log('arm', name, info, {'first_try_right': r['greedy']['right'], 'reach32': r['reach32'], 'harm': r['skills_harm_points']})
    wn, wr = boot(per_q['W'], per_q['N']), boot(per_q['W'], per_q['R'])
    gk = {k: 100 * (res['arms']['W']['greedy']['by_kind'][k]['right'] - rN['greedy']['by_kind'][k]['right']) for k in rN['greedy']['by_kind']}
    res['W_marks'] = dict(W_minus_N=dict(points=wn[0], lo=wn[1], hi=wn[2]), W_minus_R=dict(points=wr[0], lo=wr[1], hi=wr[2]),
                          by_kind_W_minus_N_points=gk, label=label(gk, wn[0]),
                          reach4_W_minus_N_points=100 * (res['arms']['W']['reach4'] - rN['reach4']),
                          practised_W_minus_N_points=100 * (res['arms']['W']['practised']['reach32'] - rN['practised']['reach32']),
                          proved_wrong_if='W - R upper end < +3 (real C2b, on test); here DEV pilot only')
    save()
    # ---- 6. night 2 (report only)
    s2 = legal.raw_samples(models['W'], pool, vocab, device, n=n, temperature=T, level=0, seed=seed + 2)
    a2 = fewshot.build_arms(pool, s2, s2, seed=seed + 2)
    u2 = v * len(a2['W']) // 32
    if a2['W'] and u2 >= 1:
        m2 = copy.deepcopy(models['W'])
        sleep.sleep(m2, a2['W'], replay, vocab, sleep.SleepCfg(updates=u2, batch=64, lr=lr_, warmup=20, seed=seed, max_visits=v), device)
        r2, _ = evaluate(m2)
        res['night2'] = dict(note='REPORT ONLY', W2_records=len(a2['W']), updates=u2, **r2)
    else:
        res['night2'] = dict(note='REPORT ONLY', W2_records=0)
    res['seconds'] = time.time() - t0
    save()
    log('DONE', res['W_marks'])
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--skills-data')
    a.add_argument('--warmed', help='job 5 warm4.pt (re-made from --ckpt when missing)'); a.add_argument('--device', default='cpu'); a.add_argument('--seed', type=int, default=0)
    a.add_argument('--limit', type=int); a.add_argument('--pool-limit', type=int)
    a = a.parse_args()
    run(a.ckpt, a.out, a.skills_train, a.skills_data, a.warmed, a.device, a.seed, a.limit, a.pool_limit)
