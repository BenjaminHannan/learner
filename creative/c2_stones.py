"""C2 stepping-stone stage (Mac job 5). CPU.   python3 -m creative.c2_stones --ckpt B2_s100.pt --out DIR --skills-train train.jsonl [--floors dev_floors.json]
0. warm the raw parent (2,048 add/mult solver rows, 4 visits, lr 3e-4, skills replay) = N; practised-kind check on 256 FRESH add/mult questions (new salt): reach@32 and
   first try at T=1.0. If reach@32 < 50%: re-warm with 16 visits, re-run the plain DEV gate on that parent; if it passes by itself the cause was under-warming (stop:
   C2b starts from it, no stones); otherwise it is the base for every arm.
1. arms from the base, same sleep each (4 visits, lr 3e-4, skills replay, 2,048 records = 256 updates): SS (stepping stones), P (placebo: 2,048 more fresh add/mult rows),
   PC (report only: full-difficulty held-out-kind solver programs from the POOL split; the pool has 1,024 questions so each is used twice as two records).
2. the same DEV gate on N, SS, P, PC (32 plain samples with repeats, T 0.5-1.4; 2.0 and 3.0 added when the best T is the top edge); per kind reach@32, reach@4, greedy first try,
   variety; plus how many DEV questions a stepping-stone rule fits with a different answer.
test and labelled are never opened; pool only for PC. Checkpoints stay local."""
import argparse, copy, json, os, time
from creative import c2_dev, fewshot, rules_real as R, sleep, stones

DATA = 'creative/data/c2'


def _warm(raw_ckpt, recs, replay, visits, lr, seed, device):
    m, vocab, meta = sleep.load_parent(raw_ckpt, device)
    cfg = sleep.SleepCfg(updates=sleep.max_updates(len(recs), 64, bool(replay), visits), batch=64, lr=lr, warmup=20, seed=seed, max_visits=visits)
    r = sleep.sleep(m, recs, replay, vocab, cfg, device)
    return m, vocab, meta, dict(updates=cfg.updates, records=len(recs), visits=visits, last_loss=r['loss'][-1] if r['loss'] else None)


def _with_nums(rows):
    return [dict(r, nums=fewshot.parse(r['prompt'])['nums']) for r in rows]


def _arm(base, recs, replay, vocab, visits, lr, seed, device):
    m = copy.deepcopy(base)
    cfg = sleep.SleepCfg(updates=sleep.max_updates(len(recs), 64, bool(replay), visits), batch=64, lr=lr, warmup=20, seed=seed, max_visits=visits)
    r = sleep.sleep(m, recs, replay, vocab, cfg, device)
    return m, dict(updates=cfg.updates, records=len(recs), last_loss=r['loss'][-1] if r['loss'] else None)


def run(ckpt, out, skills_train=None, floors_path=None, visits=4, lr=3e-4, device='cpu', seed=0, limit=None, n=32, min_practised=0.5):
    os.makedirs(out, exist_ok=True)
    log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)
    save = lambda: json.dump(res, open(os.path.join(out, 'c2_stones.json'), 'w'), indent=1)
    res = dict(ckpt=ckpt, visits=visits, lr=lr, seed=seed,
               note='plain samples, no mask, repeats counted in sampling order; temperature picked on DEV (tuning split); test/labelled never opened; pool only for the report-only PC arm; '
                    'PC uses each of the pool\'s 1,024 questions twice (two records) to reach 2,048')
    replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
    dev = _with_nums(R.load_split(DATA, 'dev')[:limit])
    floors = None
    if floors_path and os.path.exists(floors_path):
        c = json.load(open(floors_path))
        if c['ids'] == [r['id'] for r in dev]:
            floors = c['floors']
    if floors is None:
        floors = c2_dev.floors_for(dev, os.path.join(out, 'dev_floors.json'))
    res['floor'] = dict(mean_per_try=sum(floors) / len(floors), n_dev=len(dev))
    warm_recs = R.warm_records(R.load_split(DATA, 'warm'))
    m, vocab, meta, w = _warm(ckpt, warm_recs, replay, visits, lr, seed, device)
    res['warmup'] = w
    log('warm-up done', w)
    # --- 0. practised-kind check on fresh questions
    fresh, _ = stones.fresh_practised(256, 1, 'fresh-check')
    fresh = _with_nums(fresh)
    from creative import legal
    def prac_check(model):
        model.eval()
        smp = legal.raw_samples(model, fresh, vocab, device, n=n, temperature=1.0, level=0, seed=seed)
        sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
        return dict(reach32=sc['reach32'], reach4=sc['reach4'], first_try=sc['reach1'], luck=sc['luck'], key_luck=sc['key_luck'], temperature=1.0, n_questions=len(fresh))
    res['practised_check'] = prac_check(m)
    log('practised check', res['practised_check'])
    base_name = f'warm{visits}'
    res['base'] = dict(name=base_name)
    if res['practised_check']['reach32'] < min_practised:
        m16, _, _, w16 = _warm(ckpt, warm_recs, replay, 16, lr, seed, device)
        res['rewarm16'] = dict(warmup=w16, practised_check=prac_check(m16))
        log('re-warm 16 visits', res['rewarm16'])
        res['rewarm16']['dev_gate'] = c2_dev.dev_report(m16, vocab, dev, floors, device, n, seed, log=log)
        save()
        if res['rewarm16']['dev_gate']['verdict'] == 'pass':
            res['stop'] = 'under-warmed: the 16-visit warm-up passes the plain DEV gate by itself; C2b starts from it with no stepping stones'
            save()
            log('STOP', res['stop'])
            return res
        m, base_name = m16, 'warm16'
        res['base'] = dict(name=base_name, reason='practised reach@32 < 50%: every arm starts from the 16-visit parent')
    sleep.save_parent(m, meta['name'], meta['cfg'], vocab, os.path.join(out, f'{base_name}.pt'), step=(meta['step'] or 0), warmup=True)
    base = m
    # --- arms
    ss_rows, ss_info = stones.make_stone_rows(2048, seed)
    res['stones'] = dict(info=ss_info, dev_conflicts=stones.dev_conflicts(dev))
    p_rows, _ = stones.fresh_practised(2048, 2, 'placebo')
    pool = R.load_split(DATA, 'pool')
    arms = dict(SS=stones.solver_records(ss_rows), P=stones.solver_records(p_rows), PC=stones.solver_records(pool, copies=2))
    res['arms'] = {}
    res['arms']['N'] = dict(note=f'the base parent ({base_name}) itself', **c2_dev.dev_report(base, vocab, dev, floors, device, n, seed, log=log))
    save()
    for name, recs in arms.items():
        am, info = _arm(base, recs, replay, vocab, visits, lr, seed, device)
        log('arm', name, info)
        res['arms'][name] = dict(sleep=info, **c2_dev.dev_report(am, vocab, dev, floors, device, n, seed, log=log))
        save()
        if name == 'SS':
            del am
    # --- summary (the decision rule is applied by the roadmap thread; these are the numbers it needs)
    A = res['arms']
    b = lambda a: A[a]['temps'][str(A[a]['best_temperature'])]
    res['summary'] = dict(N_reach32=b('N')['reach32'], SS_reach32=b('SS')['reach32'], P_reach32=b('P')['reach32'], PC_reach32=b('PC')['reach32'],
                          SS_minus_P_points=100 * (b('SS')['reach32'] - b('P')['reach32']), SS_verdict=A['SS']['verdict'], N_verdict=A['N']['verdict'],
                          SS_best_T=A['SS']['best_temperature'], P_best_T=A['P']['best_temperature'], floor_reach32=b('SS')['floor_reach32'])
    save()
    log('SUMMARY', res['summary'])
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--floors')
    a.add_argument('--min-practised', type=float, default=0.5); a.add_argument('--device', default='cpu'); a.add_argument('--limit', type=int); a.add_argument('--seed', type=int, default=0)
    a = a.parse_args()
    run(a.ckpt, a.out, a.skills_train, a.floors, device=a.device, seed=a.seed, limit=a.limit, min_practised=a.min_practised)
