"""Build every row set used by the probes (no model needed).  python build_conds.py  -> conds.pkl, conds_summary.json
Sets: gate600/dev600/plac600 (label-balanced subsets of the held-out/dev files), full_* (whole eval files), cf_* (counterfactual rows of
300 gate + 300 depth-0 placebo rows), tr_* (train rows grouped by how many times the checkpoint saw them; reconstructed from course.py's
own index stream, verified against run.json's ex_idx_sha256)."""
import collections, hashlib, json, pickle, random, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
import numpy as np
import cf
from probelib import ROWS, SP, OUT, load_rows
from logic_transfer.course import _perm_stream, MIX_STREAM

N_TRAIN = 130000


def strat(rows, key, per, seed):
    rng = random.Random(seed)
    g = collections.defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    out = []
    for k in sorted(g, key=str):
        xs = g[k][:]
        rng.shuffle(xs)
        q = per(k) if callable(per) else per
        out += xs[:q]
    rng.shuffle(out)
    return out


def stream(seed, updates, k):
    return _perm_stream(np.random.RandomState(seed + MIX_STREAM), N_TRAIN, updates * k).reshape(updates, k)


def read_indices(path, idxs):
    want = set(int(i) for i in idxs)
    got = {}
    with open(path) as f:
        for i, line in enumerate(f):
            if i in want:
                got[i] = json.loads(line)
                if len(got) == len(want):
                    break
    return got


def main():
    C, S = {}, {}
    ev = {n: load_rows(f'{ROWS}/eval/{n}.jsonl', keep=None) for n in
          ('logic_gate', 'logic_dev', 'placebo_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_test_wording')}
    for n, r in ev.items():
        C['full_' + n] = r
    C['gate600'] = strat(ev['logic_gate'], lambda r: (r['meta']['depth'], r['meta']['label']), 50, 1)
    C['dev600'] = strat(ev['logic_dev'], lambda r: (r['meta']['depth'], r['meta']['label']), lambda k: 20 if k[0] == 0 else 60, 2)
    C['plac600'] = strat(ev['placebo_dev'], lambda r: r['meta']['label'], 200, 3)
    # counterfactual base rows: 300 gate (25 per depth x label) and 300 depth-0 placebo (100 per label), subsets of gate600 / plac600
    cfg = strat(C['gate600'], lambda r: (r['meta']['depth'], r['meta']['label']), 25, 4)
    cfp = strat(C['plac600'], lambda r: r['meta']['label'], 100, 5)
    C['cf_gate_base'], C['cf_plac_base'] = cfg, cfp
    fails = {}
    for tag, base in (('gate', cfg), ('plac', cfp)):
        built = collections.defaultdict(list)
        nf = 0
        for r in base:
            b = cf.build(r, base)
            if b is None:
                nf += 1
                continue
            for k, v in b.items():
                built[k] += v
        fails[tag] = nf
        for k, v in built.items():
            C[f'cf_{tag}_{k}'] = v
    S['cf_parse_failures'] = fails
    # ---- train rows grouped by exposures
    d1 = stream(1, 1500, 60)
    d1b = stream(2, 3500, 60)
    for nm, arr, run in (('D1', d1, 'diag/D1/run.json'), ('D1b', d1b, 'diag/D1b/run.json')):
        h = hashlib.sha256(arr.astype(np.int64).tobytes()).hexdigest()
        want = json.load(open(f'{SP}/lt2/{run}'))['ex_idx_sha256']
        S[f'{nm}_ex_idx_sha_match'] = (h == want)
        assert h == want, (nm, h, want)
    cnt1 = np.bincount(d1.ravel(), minlength=N_TRAIN)
    cnt2_1500 = np.bincount(d1b[:1500].ravel(), minlength=N_TRAIN)
    cnt2_3500 = np.bincount(d1b.ravel(), minlength=N_TRAIN)
    l1000 = stream(1, 8000, 16)[:1000]
    cntL = np.bincount(l1000.ravel(), minlength=N_TRAIN)
    rng = np.random.RandomState(7)
    pick = {}
    for name, cnt, ks in (('D1b1500', cnt1 + cnt2_1500, (0, 1, 2)), ('D1b3500', cnt1 + cnt2_3500, (1, 2, 3)), ('L1000', cntL, (0, 1))):
        S[f'exposure_hist_{name}'] = {int(k): int((cnt == k).sum()) for k in np.unique(cnt)}
        for k in ks:
            pool = np.where(cnt == k)[0]
            pick[f'tr_{name}_k{k}'] = rng.choice(pool, 600, replace=False)
    # the mix rows of the update slices (every 5th update) of the last 100 updates of D1b: what log.jsonl's loss_mix at 3500 measured
    slice_ups = list(range(3405, 3501, 5))
    pick['slice_D1b3500'] = np.concatenate([d1b[u - 1] for u in slice_ups])
    allidx = set(int(i) for v in pick.values() for i in v)
    for fam in ('logic', 'placebo'):
        got = read_indices(f'{ROWS}/{fam}_train.jsonl', allidx if fam == 'logic' else pick['tr_L1000_k0'].tolist() + pick['tr_L1000_k1'].tolist())
        if fam == 'logic':
            for name, idx in pick.items():
                C[name] = [got[int(i)] for i in idx]
        else:
            C['tr_P1000_k0'] = [got[int(i)] for i in pick['tr_L1000_k0']]
            C['tr_P1000_k1'] = [got[int(i)] for i in pick['tr_L1000_k1']]
    C['tr_parent_k0'] = C['tr_L1000_k0']
    S['slice_updates'] = slice_ups
    S['n_rows'] = {k: len(v) for k, v in C.items()}
    S['cf_exp_label_hist'] = {k: dict(collections.Counter(x['exp'] for x in v)) for k, v in C.items() if k.startswith('cf_') and 'exp' in v[0]}
    pickle.dump(C, open(f'{OUT}/conds.pkl', 'wb'))
    json.dump(S, open(f'{OUT}/conds_summary.json', 'w'), indent=1)
    print(json.dumps(S['n_rows']))
    print(S['exposure_hist_D1b1500'], S['exposure_hist_D1b3500'], S['exposure_hist_L1000'], S['cf_parse_failures'])


if __name__ == '__main__':
    main()
