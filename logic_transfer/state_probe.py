"""State probe (PREREG-SWAP-PROBE-2026-10-16.md item 3): can the controller's internal state tell a SPLIT swap-pair member from its BOUND partner?

  python -m logic_transfer.state_probe verify  --ckpt CK            (re-derivation check on 20 rows: scorer logP through the hooked path, to 1e-4)
  python -m logic_transfer.state_probe all     [--cache DIR] [--out JSON] [--readme MD]   (extract + probe all 9 checkpoints, write JSON and README)
  python -m logic_transfer.state_probe extract --name NAME --ckpt CK [--cache DIR]
  python -m logic_transfer.state_probe probe   --name NAME [--cache DIR]
  python -m logic_transfer.state_probe report  [--cache DIR] [--out JSON] [--readme MD]

EXTRACTION. No model code is changed. Tool.run(batch, each=...) calls `each(t, {Z, ...})` after every controller iteration t = 0..n_loops-1; the hook keeps a
copy of Z [B, 17, d] (8 control tokens, then 9 register tokens). Tool.state is wrapped so the answer-word scorer (answer_words.score_rows) runs unchanged
through the hooked path; so the features and the model's own pointer scores (logP of each option) come from the SAME forward pass. Features per row:
  zf         ln_z(Z[:, 1]) after the last iteration: the readout state (mode_head and q_word read it), 256-d
  qword      q_word(zf), the word-pointer query, dk = 64-d
  ctrl_mean  the 8 control tokens after the loop (Z[:, :8], before ln_z), MEAN-pooled over the tokens, 256-d
  (the same 8 tokens flattened, 2048-d, are stored in the cache as `ctrl_flat` but NOT probed: n = 1,280 train rows < 2,048 features, so every fit needs a
   1,280-dim Newton system, 10-25 s per fit on this box and ~300 fits per checkpoint; the pooled choice is the mean)
  zf_it1/3/5 ln_z(Z[:, 1]) after iteration 1 / 3 / 5 (the last iteration is 7, so zf is zf_it7), 256-d
`verify` checks (a) mode_head(zf) equals the model's own lmode, (b) the scorer's logP through the hooked path equals the stock path to 1e-4.

PROBE. L2 logistic regression (sklearn lbfgs), features standardised on the TRAIN part of each fold, C in C_GRID chosen by 3-fold inner CV (AUC) on the train
part, outer 5-fold CV GROUPED BY pair_id (a pair never spans train and test; folds come from a seeded shuffle of the sorted pair ids). Reported per fold:
test AUC; the table gives the mean. Tasks (label 1 = the first named):
  T1  split vs bound, equal-not pairs, dev vocabulary (main)          T2  the same on differ-not pairs
  T3  word-missing (wm_ent + wm_pred) vs their bound source rows (positive control; group = the source pair)
  T4  T1 with the label swapped at the PAIR level by a seeded coin (which member is called split): exactly null. T4 is the first coin; T4b, T4c are two more
  T5  train on all T1 rows (dev), test on the newwords equal-not pairs (T5d: the same fit tested on newwords differ-not pairs, extra)
Also reported, no fit: `pointer` = AUC of the model's own logP(unknown) for split vs bound on the same rows (per the same folds).
"""
import argparse
import json
import os
import random
import sys
import time
import warnings

import numpy as np

from logic_transfer import swap_probe as SP

ROWS = SP.OUT
HERE = os.path.dirname(os.path.abspath(__file__))
PROBE_DIR = os.path.dirname(ROWS)
OUT = os.path.join(PROBE_DIR, 'STATE_PROBE.json')
README = os.path.join(PROBE_DIR, 'README.md')
SCRATCH = '/tmp/claude-0/-home-user/25d50c87-f133-5117-867c-2334706963ac/scratchpad'
CACHE = os.path.join(SCRATCH, 'state_probe_cache')
PARENT = lambda s: f'{SCRATCH}/feas/T1SDR_s{s}.pt'
REPLICA = lambda n: os.path.join(HERE, 'replicas', 'r2a', n, 'checkpoint.pt')
CKPTS = [(f'parent-s{s}', PARENT(s)) for s in (200, 201, 204)] + [(n, REPLICA(n)) for n in ('s200-s1', 's200-s2', 's201-s1', 's201-s2', 's204-s1', 's204-s2')]
REPLICAS = [n for n, _ in CKPTS[3:]]
FEATS = ['zf', 'qword', 'ctrl_mean', 'zf_it1', 'zf_it3', 'zf_it5']
PRIMARY = 'zf'
IT_KEEP = (1, 3, 5)
TASKS = ['T1', 'T2', 'T3', 'T4', 'T4b', 'T4c', 'T5', 'T5d']
C_GRID = (1e-3, 1e-2, 1e-1, 1.0, 10.0)
OUTER, INNER, SEED = 5, 3, 20261016
LOW, HIGH, CTRL_LO, CTRL_HI, POS_MIN = 0.65, 0.75, 0.40, 0.60, 0.80      # the prereg's probe thresholds, fixed there
THREADS = 2


def load_rows():
    """-> all probe rows keyed by id (dev_pairs, nw_pairs, wm), in file order."""
    out = {}
    for n in ('dev_pairs', 'nw_pairs', 'wm'):
        for r in SP.read(os.path.join(ROWS, n + '.jsonl')):
            out[r['id']] = r
    return out


# ---- extraction ----
def hooked(model, store):
    """Wrap model.state so every forward keeps the per-iteration controller states, keyed by row id. -> restore function."""
    import torch

    def state(batch, loops=None, lesion=None, oracle=None):
        zs = []
        o = model.run(batch, loops, lesion=lesion, oracle=oracle, each=lambda t, d: zs.append(d['Z'].detach().clone()) and False)
        Z = zs[-1]
        with torch.no_grad():
            zf = model.ln_z(Z[:, 1])
            assert torch.allclose(model.mode_head(zf), o['lmode'], atol=1e-5), 'zf does not reproduce the model readout'
            ff = dict(zf=zf, qword=model.q_word(zf), ctrl_mean=Z[:, :8].mean(1), ctrl_flat=Z[:, :8].flatten(1))
            for t in IT_KEEP:
                ff[f'zf_it{t}'] = model.ln_z(zs[t][:, 1])
        for i, r in enumerate(batch['rows']):
            store[r['id']] = {k: v[i].float().numpy() for k, v in ff.items()}
        return model.state_of(o)

    model.state = state
    return lambda: model.__dict__.pop('state', None)


def extract(name, ckpt, rows, cache=CACHE, log=print):
    """Run the scorer through the hooked path on every probe row -> cache/NAME.npz (features, aligned with the ids list) + NAME.score.jsonl."""
    import torch
    from logic_transfer import answer_words as AW
    torch.set_num_threads(THREADS)
    model, _ = AW.load(ckpt)
    store = {}
    undo = hooked(model, store)
    t0 = time.time()
    ids = list(rows)
    recs = AW.score_rows(model, [rows[i] for i in ids], 64)
    undo()
    assert all(r['id'] in store for r in recs) and [r['id'] for r in recs] == ids
    arr = {k: np.stack([store[i][k] for i in ids]) for k in FEATS + ['ctrl_flat']}
    os.makedirs(cache, exist_ok=True)
    np.savez(os.path.join(cache, name + '.npz'), ids=np.array(ids), **arr)
    with open(os.path.join(cache, name + '.score.jsonl'), 'w') as f:
        for r in recs:
            f.write(json.dumps(r) + '\n')
    log(f'extract {name}: {len(ids)} rows in {time.time() - t0:.0f}s; ' + json.dumps(AW.agreement(recs)))


def verify(ckpt, rows, n=20):
    """The hooked path must give the scorer's own logP (stock Tool.state) to 1e-4 on n rows. -> max abs difference."""
    import torch
    from logic_transfer import answer_words as AW
    torch.set_num_threads(THREADS)
    model, _ = AW.load(ckpt)
    rs = [rows[i] for i in list(rows)[::max(1, len(rows) // n)][:n]]
    base = AW.score_rows(model, rs, 8)
    store = {}
    undo = hooked(model, store)
    hook = AW.score_rows(model, rs, 8)
    undo()
    d = max(abs(a['logp'][w] - b['logp'][w]) for a, b in zip(base, hook) for w in AW.OPTIONS)
    same = all(a['pred'] == b['pred'] and a['mode'] == b['mode'] for a, b in zip(base, hook))
    assert d < 1e-4 and same, (d, same)
    return dict(n=len(rs), max_abs_logp_diff=d, same_greedy=same, features=sorted(store[rs[0]['id']]))


# ---- probe ----
def pair_folds(groups, k, seed):
    """{group: fold in 0..k-1} from a seeded shuffle of the sorted group names."""
    gs = sorted(set(groups))
    random.Random(f'{seed}|folds|{k}|{len(gs)}').shuffle(gs)
    return {g: i % k for i, g in enumerate(gs)}


def auc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s))


def fit(X, y, C):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        # newton-cholesky: exact Newton steps, 10-1000x faster than lbfgs here (checked equal: decision values within 0.02 and the same AUC to 4 digits)
        return make_pipeline(StandardScaler(), LogisticRegression(C=C, solver='newton-cholesky', max_iter=100, tol=1e-6)).fit(X, y)


def choose_C(X, y, g, seed):
    """Inner CV (INNER folds grouped by pair) on the train part: the C with the best mean AUC (ties: the smaller C)."""
    fo = pair_folds(g, INNER, f'{seed}|inner')
    f = np.array([fo[x] for x in g])
    best, bc = -1.0, C_GRID[0]
    for C in C_GRID:
        a = []
        for k in range(INNER):
            tr, te = f != k, f == k
            a.append(auc(y[te], fit(X[tr], y[tr], C).decision_function(X[te])))
        if np.mean(a) > best + 1e-9:
            best, bc = float(np.mean(a)), C
    return bc


def cv_probe(X, y, g, seed=SEED):
    """Grouped 5-fold CV -> dict(auc, folds, C, n, n_pairs)."""
    fo = pair_folds(g, OUTER, f'{seed}|outer')
    f = np.array([fo[x] for x in g])
    folds, Cs = [], []
    for k in range(OUTER):
        tr, te = f != k, f == k
        C = choose_C(X[tr], y[tr], g[tr], f'{seed}|{k}')
        folds.append(auc(y[te], fit(X[tr], y[tr], C).decision_function(X[te]))); Cs.append(C)
    return dict(auc=float(np.mean(folds)), folds=folds, C=Cs, n=int(len(y)), n_pairs=int(len(set(g))))


def transfer_probe(Xtr, ytr, gtr, tests, seed=SEED):
    """Fit on (Xtr, ytr) with C by grouped inner CV; AUC on each (X, y) of tests. -> {name: dict}."""
    C = choose_C(Xtr, ytr, gtr, f'{seed}|T5')
    m = fit(Xtr, ytr, C)
    return {k: dict(auc=auc(y, m.decision_function(X)), folds=[auc(y, m.decision_function(X))], C=[C], n=int(len(y)), n_pairs=int(len(y) // 2))
            for k, (X, y) in tests.items()}


def task_rows(rows):
    """-> {task: (row ids, labels, groups)} (T4 variants and the transfer sets are derived from these)."""
    rs = list(rows.values())
    T = {}
    for name, rel in (('T1', 'equal'), ('T2', 'differ')):
        sel = [r for r in rs if r['meta']['vocab'] == 'dev' and r['meta'].get('member') in ('bound', 'split') and r['meta']['not_rel'] == rel]
        T[name] = ([r['id'] for r in sel], np.array([r['meta']['member'] == 'split' for r in sel], int), np.array([r['meta']['pair_id'] for r in sel]))
    wm = [r for r in rs if r['meta'].get('source_row')]
    ids = [r['id'] for r in wm] + [r['meta']['source_row'] for r in wm]
    T['T3'] = (ids, np.array([1] * len(wm) + [0] * len(wm)), np.array([r['meta']['pair_id'] for r in wm] * 2))
    for name, rel in (('nw_eq', 'equal'), ('nw_diff', 'differ')):
        sel = [r for r in rs if r['meta']['vocab'] == 'newwords' and r['meta']['not_rel'] == rel]
        T[name] = ([r['id'] for r in sel], np.array([r['meta']['member'] == 'split' for r in sel], int), np.array([r['meta']['pair_id'] for r in sel]))
    return T


def shuffled(y, g, tag):
    """Pair-level label swap: a seeded coin per pair decides which member is called split (a pair still holds one 0 and one 1)."""
    coin = {p: random.Random(f'{SEED}|T4|{tag}|{p}').random() < 0.5 for p in sorted(set(g))}
    flip = np.array([coin[p] for p in g])
    return np.where(flip, 1 - y, y)


def probe(name, cache=CACHE, rows=None, log=print):
    rows = rows or load_rows()
    z = np.load(os.path.join(cache, name + '.npz'))
    pos = {i: k for k, i in enumerate(z['ids'].tolist())}
    score = {}
    for line in open(os.path.join(cache, name + '.score.jsonl')):
        r = json.loads(line)
        score[r['id']] = r['logp']['unknown']
    T = task_rows(rows)
    ix = lambda ids: np.array([pos[i] for i in ids])
    out = {}
    t0 = time.time()
    for feat in FEATS + ['pointer']:
        res = {}
        get = (lambda ids: z[feat][ix(ids)]) if feat != 'pointer' else (lambda ids: np.array([score[i] for i in ids])[:, None])
        for t in ('T1', 'T2', 'T3'):
            ids, y, g = T[t]
            X = get(ids)
            res[t] = cv_probe(X, y, g) if feat != 'pointer' else pointer_cv(X[:, 0], y, g)
        if feat != 'pointer':
            ids, y, g = T['T1']
            X = get(ids)
            for t, tag in (('T4', 'a'), ('T4b', 'b'), ('T4c', 'c')):
                res[t] = cv_probe(X, shuffled(y, g, tag), g, seed=f'{SEED}|{tag}')
            (i1, y1, g1), (i5, y5, _), (i6, y6, _) = T['T1'], T['nw_eq'], T['nw_diff']
            res['T5'] = None
            tr = transfer_probe(X, y1, g1, {'T5': (get(i5), y5), 'T5d': (get(i6), y6)})
            res.update(tr)
        else:
            for t, k in (('T5', 'nw_eq'), ('T5d', 'nw_diff')):
                ids, y, g = T[k]
                a = auc(y, get(ids)[:, 0])
                res[t] = dict(auc=a, folds=[a], C=[], n=int(len(y)), n_pairs=int(len(y) // 2))
            ids, y, g = T['T1']
            for t, tag in (('T4', 'a'), ('T4b', 'b'), ('T4c', 'c')):
                res[t] = pointer_cv(get(ids)[:, 0], shuffled(y, g, tag), g)
        out[feat] = res
        log(f'  {name} {feat}: ' + ' '.join(f'{t}={res[t]["auc"]:.3f}' for t in TASKS if res.get(t)) + f'  ({time.time() - t0:.0f}s)')
    return out


def pointer_cv(s, y, g):
    """AUC of a fixed score on the same grouped folds (nothing is fitted)."""
    fo = pair_folds(g, OUTER, f'{SEED}|outer')
    f = np.array([fo[x] for x in g])
    folds = [auc(y[f == k], s[f == k]) for k in range(OUTER)]
    return dict(auc=float(np.mean(folds)), folds=folds, C=[], n=int(len(y)), n_pairs=int(len(set(g))))


# ---- thresholds and report ----
def calls(res):
    """The prereg's probe thresholds, applied mechanically. res = {ckpt: {feat: {task: dict}}}. -> {feat: {...}}"""
    out = {}
    for feat in FEATS:
        rep = {n: res[n][feat] for n in REPLICAS if n in res}
        a = lambda n, t: rep[n][t]['auc']
        out[feat] = dict(
            n_replicas=len(rep),
            T1_below_0p65=sorted(n for n in rep if a(n, 'T1') < LOW),
            T1_at_least_0p75=sorted(n for n in rep if a(n, 'T1') >= HIGH),
            pointer_below_0p65=sorted(n for n in rep if res[n]['pointer']['T1']['auc'] < LOW),
            both_T1_at_least_0p75_and_pointer_below_0p65=sorted(n for n in rep if a(n, 'T1') >= HIGH and res[n]['pointer']['T1']['auc'] < LOW),
            T4_outside_0p40_0p60=sorted(n for n in res if not CTRL_LO <= res[n][feat]['T4']['auc'] <= CTRL_HI),
            T4_any_of_3_outside_0p40_0p60=sorted(n for n in res if any(not CTRL_LO <= res[n][feat][t]['auc'] <= CTRL_HI for t in ('T4', 'T4b', 'T4c'))),
            T3_below_0p80=sorted(n for n in res if res[n][feat]['T3']['auc'] < POS_MIN))
    return out


def table(res, feat):
    lines = ['| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |', '|---|---|---|---|---|---|---|']
    for n, _ in CKPTS:
        if n in res:
            r, p = res[n][feat], res[n]['pointer']
            lines.append(f'| {n} | ' + ' | '.join(f'{r[t]["auc"]:.3f}' for t in ('T1', 'T2', 'T3', 'T4', 'T5')) + f' | {p["T1"]["auc"]:.3f} |')
    return '\n'.join(lines)


def report(cache=CACHE, out=OUT, readme=README, log=print):
    res = {}
    for n, _ in CKPTS:
        p = os.path.join(cache, n + '.probe.json')
        if os.path.exists(p):
            res[n] = json.load(open(p))
    assert res, 'no probe results in ' + cache
    summary = calls(res)
    with open(out, 'w') as f:
        json.dump(dict(prereg='logic_transfer/PREREG-SWAP-PROBE-2026-10-16.md', seed=SEED, outer_folds=OUTER, inner_folds=INNER, c_grid=C_GRID,
                       primary_feature=PRIMARY, features=FEATS, tasks=TASKS, rows_build=os.path.join(ROWS, 'BUILD.json'),
                       thresholds=dict(low=LOW, high=HIGH, control=[CTRL_LO, CTRL_HI], positive_min=POS_MIN), checkpoints=res, threshold_report=summary),
                  f, indent=1)
    write_readme(res, summary, readme)
    log(f'wrote {out} and {readme}')


def write_readme(res, s, path):
    head = '## State probe'
    old = open(path).read() if os.path.exists(path) else ''
    keep = old.split(head)[0].rstrip() + '\n\n' if head in old else (old.rstrip() + '\n\n' if old else '# Swap-pair binding probe\n\n')
    p = s[PRIMARY]
    names = lambda v: ', '.join(v) if v else 'none'
    txt = [head, '',
           'Prereg item 3 (`logic_transfer/PREREG-SWAP-PROBE-2026-10-16.md`). `logic_transfer/state_probe.py`; results in `STATE_PROBE.json` (per checkpoint x feature set x task: '
           'AUC mean, fold AUCs, n, chosen C). Linear probe = L2 logistic regression, standardised features, C by 3-fold inner CV, 5-fold CV grouped by pair_id; AUC is '
           'on held-out pairs. Features: `zf` = ln_z of control token 1 after the last loop (the state mode_head and q_word read; primary); `qword` = q_word(zf); '
           '`ctrl_mean` = the 8 control tokens after the loop, mean-pooled (the flattened 2048-d block is extracted and cached but not probed: too slow to fit here, see the module docstring); `zf_it1/3/5` = zf after iteration 1/3/5 (last is 7). '
           'Tasks: T1 split vs bound, equal-not, dev vocabulary; T2 the same, differ-not; T3 word-missing vs bound (positive control); T4 shuffled-label control '
           '(split/bound label swapped at the pair level by a seeded coin; T4b, T4c are two more coins, in the JSON); T5 train T1 on dev, test on newwords equal-not pairs. '
           '`pointer` = AUC of the model\'s own logP(unknown), split vs bound, same rows and folds (nothing fitted).', '',
           f'Primary feature set `{PRIMARY}`, test AUC (mean over folds):', '', table(res, PRIMARY), '']
    for feat in FEATS:
        if feat != PRIMARY:
            txt += [f'Feature set `{feat}`:', '', table(res, feat), '']
    txt += ['Prereg probe thresholds, applied mechanically (replicas = the six 8,000-update checkpoints; parents shown above for the floor):', '',
            '| feature set | T1 AUC < 0.65 | T1 AUC >= 0.75 | pointer AUC < 0.65 | T1 >= 0.75 and pointer < 0.65 | T4 outside 0.40-0.60 | T3 < 0.80 |', '|---|---|---|---|---|---|---|']
    for feat in FEATS:
        q = s[feat]
        txt.append(f'| {feat} | {len(q["T1_below_0p65"])}/6 | {len(q["T1_at_least_0p75"])}/6 | {len(q["pointer_below_0p65"])}/6 | '
                   f'{len(q["both_T1_at_least_0p75_and_pointer_below_0p65"])}/6 | {len(q["T4_outside_0p40_0p60"])}/9 | {len(q["T3_below_0p80"])}/9 |')
    txt += ['', f'Primary set `{PRIMARY}`: T1 < 0.65 in {names(p["T1_below_0p65"])}; T1 >= 0.75 in {names(p["T1_at_least_0p75"])}; pointer < 0.65 in {names(p["pointer_below_0p65"])}. '
            f'Instrument checks (all 9 checkpoints): T4 outside 0.40-0.60: {names(p["T4_outside_0p40_0p60"])} (any of the 3 coins: {names(p["T4_any_of_3_outside_0p40_0p60"])}); '
            f'T3 below 0.80: {names(p["T3_below_0p80"])}.', '',
            'Commands (cwd /home/user/replica):', '', '```',
            'python3 -m logic_transfer.state_probe verify --ckpt logic_transfer/replicas/r2a/s200-s1/checkpoint.pt',
            'python3 -m logic_transfer.state_probe all', '```', '']
    with open(path, 'w') as f:
        f.write(keep + '\n'.join(txt))


def main(argv=None):
    global THREADS
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for c in ('verify', 'all', 'extract', 'probe', 'report'):
        s = sub.add_parser(c)
        s.add_argument('--cache', default=CACHE)
        s.add_argument('--out', default=OUT)
        s.add_argument('--readme', default=README)
        s.add_argument('--name')
        s.add_argument('--ckpt')
        s.add_argument('--threads', type=int, default=THREADS)
    a = ap.parse_args(argv)
    THREADS = a.threads
    from threadpoolctl import threadpool_limits
    threadpool_limits(THREADS)
    if a.cmd == 'verify':
        print(json.dumps(verify(a.ckpt, load_rows())))
    elif a.cmd == 'extract':
        extract(a.name, a.ckpt, load_rows(), a.cache)
    elif a.cmd == 'probe':
        res = probe(a.name, a.cache)
        json.dump(res, open(os.path.join(a.cache, a.name + '.probe.json'), 'w'))
    elif a.cmd == 'report':
        report(a.cache, a.out, a.readme)
    else:
        rows = load_rows()
        for n, ck in CKPTS:
            if not os.path.exists(os.path.join(a.cache, n + '.npz')):
                extract(n, ck, rows, a.cache)
            p = os.path.join(a.cache, n + '.probe.json')
            if not os.path.exists(p):
                json.dump(probe(n, a.cache, rows), open(p, 'w'))
        report(a.cache, a.out, a.readme)


if __name__ == '__main__':
    main()
