"""python run_probe.py TAG   (forward passes only; one checkpoint loaded; 1 thread).  Writes res/TAG.pkl = {condition: forward() dict}."""
import pickle, sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
from probelib import *

SPR = f'{SP}/lt2'
CK = {
    'parent': '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt',
    'D1b1500': f'{SPR}/diag/D1b/checkpoint-1500.pt', 'D1b3500': f'{SPR}/diag/D1b/checkpoint-3500.pt',
    'L1000': f'{SPR}/jobs/course-s200-L-s1/out/checkpoint-1000.pt', 'P1000': f'{SPR}/jobs/course-s200-P-s1/out/checkpoint-1000.pt',
    **{f'D1b{u}': f'{SPR}/diag/D1b/checkpoint-{u}.pt' for u in (500, 1000, 2000, 2500, 3000)},
    'D1_1500': f'{SPR}/diag/D1/checkpoint-1500.pt',
}
BASE = ['gate600', 'dev600', 'plac600']
CF = [f'cf_{b}_{k}' for b in ('gate', 'plac') for k in ('perm', 'ent', 'neg', 'del_support', 'del_distractor', 'ctx_removed', 'body_swap')]
FULL = ['full_logic_gate', 'full_logic_dev', 'full_placebo_dev', 'full_logic_test_sampler', 'full_logic_test_deeper', 'full_placebo_test_wording']
PLAN = {
    'D1b3500': FULL + CF + ['tr_D1b3500_k1', 'tr_D1b3500_k2', 'tr_D1b3500_k3', 'slice_D1b3500'],
    'parent': ['full_logic_gate'] + BASE + CF + ['tr_parent_k0'],
    'D1b1500': BASE + CF + ['tr_D1b1500_k0', 'tr_D1b1500_k1', 'tr_D1b1500_k2'],
    'L1000': BASE + CF + ['tr_L1000_k0', 'tr_L1000_k1'],
    'P1000': BASE + CF + ['tr_P1000_k0', 'tr_P1000_k1'],
}
for u in (500, 1000, 2000, 2500, 3000):
    PLAN[f'D1b{u}'] = BASE
PLAN['D1_1500'] = BASE


def main(tag):
    C = pickle.load(open(f'{OUT}/conds.pkl', 'rb'))
    m = load_model(CK[tag], 'cpu')
    res, t0 = {}, time.time()
    ids_of = {}
    for name in PLAN[tag]:
        rows = C[name]
        # reuse a full run for the 600-row balanced subsets
        done = False
        if name in BASE:
            full = {'gate600': 'full_logic_gate', 'dev600': 'full_logic_dev', 'plac600': 'full_placebo_dev'}[name]
            if full in res:
                pos = {r['id']: i for i, r in enumerate(C[full])}
                ix = [pos[r['id']] for r in rows]
                res[name] = {k: ([v[i] for i in ix] if isinstance(v, list) else v[ix]) for k, v in res[full].items()}
                done = True
        if not done:
            t = time.time()
            res[name] = forward(m, rows)
            print(f'{tag} {name} n={len(rows)} {time.time() - t:.1f}s calls>0: {int((res[name]["ncalls"] > 0).sum())}', flush=True)
        res[name]['ids'] = [r['id'] for r in rows]
        pickle.dump(res, open(f'{OUT}/res/{tag}.pkl', 'wb'))
    print(f'{tag} done {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
