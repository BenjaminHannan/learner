"""First-look readout (FIRST-LOOK-10M-2026-10-07.md, amendment 1 + 2): python3 readout.py RESULTS_DIR [--json OUT]
RESULTS_DIR holds B2D_s{seed}/ PT13C0_s{seed}/ B2_s{seed}/ C0_s{seed}/ RESULT.json for seeds 200 and 201 (same box per seed)."""
import json, os, sys

SPLITS = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
Q33 = {200: dict(B2=73.00, tfsteps=66.82), 201: dict(B2=74.27, tfsteps=67.09)}   # q33 PC pooled-5 (shown earlier)


def load(d, name):
    p = os.path.join(d, name, 'RESULT.json')
    return json.load(open(p)) if os.path.exists(p) else None


def pooled(fe):
    c = sum(fe[k]['correct'] for k in SPLITS); n = sum(fe[k]['n'] for k in SPLITS)
    return 100.0 * c / n


def row(r):
    if r is None:
        return None
    fe = r['final_eval']
    ch = r.get('chain5') or {}
    ch = ch.get('intact', ch).get('exact') if isinstance(ch, dict) else None
    l0 = (r.get('lesions') or {}).get('loops:0', {}).get('in_dist', {}).get('exact')
    return dict(pooled5=pooled(fe), in_dist=fe['in_dist']['exact'], variant=fe['variant']['exact'], chain5=ch, loops0_in_dist=l0,
                params=r['n_params'], steps=r['steps'], status=r['status'], sps=r.get('steps_per_s'), train_h=(r.get('train_s') or 0) / 3600)


def main():
    d = sys.argv[1]
    out = {}
    for s in (200, 201):
        out[s] = {a: row(load(d, '%s_s%d' % (a, s))) for a in ('B2D', 'PT13C0', 'B2', 'C0')}
    print('%-5s %-7s %9s %8s %8s %7s %8s %11s %6s %6s' % ('seed', 'arm', 'params', 'pooled5', 'in_dist', 'variant', 'chain5', 'loops0_in', 'ups', 'hours'))
    for s, arms in out.items():
        for a, r in arms.items():
            if r is None:
                print('%-5d %-7s missing' % (s, a)); continue
            print('%-5d %-7s %9d %8.2f %8.2f %7.2f %8s %11s %6.2f %6.2f' % (s, a, r['params'], r['pooled5'], r['in_dist'], r['variant'],
                  '%.2f' % r['chain5'] if r['chain5'] is not None else '-', '%.2f' % r['loops0_in_dist'] if r['loops0_in_dist'] is not None else '-',
                  r['sps'] or 0, r['train_h']))
    print()
    verdict = {}
    for s, a in out.items():
        if not all(a.values()):
            verdict[s] = None; continue
        gain = a['B2D']['pooled5'] - a['B2']['pooled5']
        lead10 = a['B2D']['pooled5'] - a['PT13C0']['pooled5']
        lead3 = a['B2']['pooled5'] - a['C0']['pooled5']
        verdict[s] = dict(gain=gain, lead10=lead10, lead3=lead3, lead_change=lead10 - lead3,
                          machine=a['B2']['pooled5'] - Q33[s]['B2'], gain_vs_q33=a['B2D']['pooled5'] - Q33[s]['B2'])
        print('seed %d: B2 10M-3M %+.2f | lead 10M %+.2f, lead 3M %+.2f (change %+.2f) | same-box B2-3M minus q33 PC %+.2f | B2D minus q33 B2 %+.2f'
              % (s, gain, lead10, lead3, lead10 - lead3, verdict[s]['machine'], verdict[s]['gain_vs_q33']))
    v = [x for x in verdict.values() if x]
    if len(v) == 2:
        enc = all(x['gain'] >= 3.0 and x['lead_change'] >= -1.0 for x in v)
        flat = all(x['gain'] < 1.0 for x in v)
        print('READOUT:', 'ENCOURAGING' if enc else ('FLAT' if flat else 'UNCLEAR'), '(2 seeds; not a verdict)')
    if '--json' in sys.argv:
        json.dump(dict(rows=out, verdict=verdict), open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)


if __name__ == '__main__':
    main()
