"""C2 DEV cold-start gate (roadmap sec. 7). CPU.   python3 -m creative.c2_dev --ckpt B2_s100.pt --out DIR --skills-train train.jsonl
1. warm-up: the parent sleeps on the practised-kind (add, mult) solver programs from creative/data/c2/warm.jsonl, skills replay on (same sleep as C1's warm-up).
2. cold start: n plain samples per held-out-kind DEV question (NO mask, repeats kept, order kept), temperature in a small grid; reach@32 / reach@4 / luck /
   variety from `fewshot.score_samples`; value-blind floors per question (cached); `fewshot.dev_gate_samples` is the verdict at the best temperature.
The temperature is picked on DEV by reach@32 (disclosed: DEV is the tuning split; every temperature is reported). Answer keys are read only to report key_luck.
`--no-warm` scores the raw parent for comparison. The sealed `test`, `pool` and `labelled` splits are never opened here."""
import argparse, json, os, time
from creative import fewshot, legal, rules_real as R, sleep

TEMPS = (0.5, 0.7, 1.0, 1.4)


def floors_for(rows, cache, n=4000):
    if os.path.exists(cache):
        c = json.load(open(cache))
        if c.get('n') == n and c['ids'] == [r['id'] for r in rows]:
            return c['floors']
    fl = [fewshot.value_blind_floor(r, n) for r in rows]
    json.dump(dict(n=n, ids=[r['id'] for r in rows], floors=fl), open(cache, 'w'))
    return fl


def run(ckpt, out, data='creative/data/c2', skills_train=None, warm=True, visits=4, lr=3e-4, n=32, device='cpu', seed=0, limit=None, temps=TEMPS):
    os.makedirs(out, exist_ok=True)
    m, vocab, meta = sleep.load_parent(ckpt, device)
    res = dict(ckpt=ckpt, warm=warm, visits=visits, lr=lr, n_samples=n, spec=json.load(open(os.path.join(data, 'MANIFEST.json')))['_spec'],
               note='no mask; luck and reach over samples with repeats in sampling order; temperature picked on DEV (tuning split); test/pool/labelled never opened')
    if warm:
        rows = R.load_split(data, 'warm')
        recs = R.warm_records(rows)
        replay = sleep.load_replay(skills_train, None, seed) if skills_train else []
        cfg = sleep.SleepCfg(updates=sleep.max_updates(len(recs), 64, bool(replay), visits), batch=64, lr=lr, warmup=20, seed=seed, max_visits=visits)
        t0 = time.time()
        r = sleep.sleep(m, recs, replay, vocab, cfg, device)
        res['warmup'] = dict(updates=cfg.updates, records=len(recs), replay=len(replay), seconds=time.time() - t0, last_loss=r['loss'][-1] if r['loss'] else None)
        print('warm-up done', res['warmup'], flush=True)
    m.eval()
    dev = [dict(r, nums=fewshot.parse(r['prompt'])['nums']) for r in R.load_split(data, 'dev')[:limit]]
    floors = floors_for(dev, os.path.join(out, 'dev_floors.json'))
    res['floor'] = dict(mean_per_try=sum(floors) / len(floors), n_dev=len(dev))
    res['temps'] = {}
    for T in temps:
        t0 = time.time()
        samples = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
        g = fewshot.dev_gate_samples(dev, samples, floors)
        sc = fewshot.score_samples(dev, samples)
        g['by_kind'] = {}
        for k in sorted({r['kind'] for r in dev}):
            pq = [d for d, r in zip(sc['per_question'], dev) if r['kind'] == k]
            g['by_kind'][k] = dict(n=len(pq), reach32=sum(d['reach32'] for d in pq) / len(pq), reach4=sum(d['reach4'] for d in pq) / len(pq),
                                   luck=sum(d['c'] for d in pq) / sum(d['m'] for d in pq))
        g['key_luck'] = sc['key_luck']
        g['seconds'] = time.time() - t0
        res['temps'][str(T)] = g
        print('T', T, {a: g[a] for a in ('verdict', 'reach32', 'floor_reach32', 'reach4', 'luck', 'distinct_rules')}, flush=True)
        json.dump(res, open(os.path.join(out, 'c2_dev.json'), 'w'), indent=1)
    best = max(res['temps'], key=lambda T: res['temps'][T]['reach32'])
    res['best_temperature'] = float(best)
    res['verdict'] = res['temps'][best]['verdict']
    json.dump(res, open(os.path.join(out, 'c2_dev.json'), 'w'), indent=1)
    print('VERDICT', res['verdict'], 'at T', best, flush=True)
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--ckpt', required=True); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--data', default='creative/data/c2')
    a.add_argument('--no-warm', action='store_true'); a.add_argument('--visits', type=int, default=4); a.add_argument('--lr', type=float, default=3e-4)
    a.add_argument('--device', default='cpu'); a.add_argument('--limit', type=int); a.add_argument('--seed', type=int, default=0)
    a = a.parse_args()
    run(a.ckpt, a.out, a.data, a.skills_train, not a.no_warm, a.visits, a.lr, device=a.device, seed=a.seed, limit=a.limit)
