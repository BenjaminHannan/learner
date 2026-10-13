"""G-ceiling test (addendum B15 of DESIGN-AND-MARKS-2026-10-10.md). No training: the model is frozen and read-only.

  python -m dopamine.g_ceiling gen --seed 200 --ckpt PATH --run RUNDIR --out DIR [--n 32000] [--threads 2] [--smoke]
  python -m dopamine.g_ceiling fit --dir DIR

gen: N fresh practice questions from domain mode's own generator (draft() via make_practice, even share over the run's kinds,
rng random.Random(f'g-ceiling-{seed}'), deduplicated, the run's quiz prompts excluded), each labelled 1 when the model's
normal answer (8 loops, calculator on, as domain.mode.greedy) equals the tool's value. Features per row:
  S900 = D0's inputs: reader mean A, pooled state S, talker confidence c (d0_guess.day_features' pieces; see check_same()).
  P    = answers at forced loops 2/4/16/32 equal the normal answer (4 flags), distinct answers over the 5 runs, the talker's
         log-probability of its own answer at normal loops (= D0's c, talk_conf), calculator calls in the normal run, last call's
         result == answer, prompt length.
  LEN  = prompt length only.  DIAG = operand count, longest digit run (diagnostic, never shipped).
fit: 5-fold cross-fit stratified by kind on nested subsets; D0's fit_logistic, within-kind AUC; RESULT.json / RESULT.md.
"""
import argparse
import hashlib
import importlib
import json
import os
import random
import re
import time
from collections import Counter

import numpy as np
import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from domain import mode
from domain.mode import guard
from dopamine.d0_guess import auc, fit_logistic, pool_state, talk_conf, within_kind_auc

BS = 64
FORCED = (2, 4, 16, 32)
SIZES = (2500, 8000, 16000, 32000)
PROBES = ('S900', 'P', 'S900+P', 'LEN', 'DIAG')
SHIPPABLE = ('S900', 'P', 'S900+P')
BASELINE = {200: 0.543, 201: 0.597}
FOLDS, FOLD_SEED, SUBSET_SEED = 5, 0, 0
P_NAMES = ['same_2', 'same_4', 'same_16', 'same_32', 'n_distinct', 'logprob', 'n_calls', 'last_call_eq', 'prompt_len']


# ---------- process features (pure functions, tested on toys) ----------

def process_flags(normal, forced):
    """normal: the normal-run answer; forced: answers at loops 2,4,16,32. -> (4 flags 'equals normal', distinct answers over the 5)."""
    return [int(a == normal) for a in forced], len(set([normal] + list(forced)))


def call_features(calls, ans):
    """calls: [(t, op, a, b, result)] of the normal run. -> (number of calls, 1 if the last call's result == the answer)."""
    return len(calls), int(bool(calls) and calls[-1][4] == ans)


def diag_features(prompt):
    runs = re.findall(r'\d+', prompt)
    return len(runs), max((len(r) for r in runs), default=0)


# ---------- gen ----------

def batch_of(m, chunk):
    ds = Dataset([{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                  for i, p in enumerate(chunk)], m.vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')


def chunk_features(m, chunk):
    """One batch: the same normal run/talk as d0_guess.day_features plus the four forced-loop runs.
    -> dict of lists/arrays. Forced runs: m.run(batch, loops=d) then m.talk(m.state_of(o), batch), as greedy() with loops=d."""
    batch = batch_of(m, chunk)
    with torch.no_grad():
        o = m.run(batch)
        state = m.state_of(o)
        ans, modes = m.talk(state, batch, return_modes=True)
        X, xm = m.read(batch, talker=True)
        w = xm.float()[..., None]
        A = (X * w).sum(1) / w.sum(1).clamp(min=1)
        S = pool_state(state)
        c = talk_conf(m, state, X, xm, batch, modes)
        forced = []
        for d in FORCED:
            od = m.run(batch, loops=d)
            forced.append(m.talk(m.state_of(od), batch))
    return dict(ans=ans, A=A.numpy(), S=S.numpy(), c=c.numpy(), calls=o['calls'], forced=forced)


def check_same(m, prompts):
    """Our batch pass must give D0's numbers. Raises if day_features differs on these prompts."""
    from dopamine.d0_guess import day_features
    ans, A, S, c = day_features(m, prompts)
    r = chunk_features(m, prompts)
    assert ans == r['ans'] and np.allclose(A, r['A'], atol=1e-5) and np.allclose(S, r['S'], atol=1e-5) \
        and np.allclose(c, r['c'], atol=1e-5), 'features differ from d0_guess.day_features'


def build_questions(seed, run, n, smoke_log=None):
    """Domain mode's own machinery, as mode.main builds it. -> (items, kinds, info)."""
    ev = [json.loads(l) for l in open(guard(os.path.join(run, 'log.jsonl')))]
    start = next(e for e in ev if e['event'] == 'start')
    cons, run_seed = start['constants'], start['seed']
    tool = importlib.import_module(f"domain.tools.{start['tool']}")
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ex = {h['kind']: h['prompt'] for h in helps}
    ck = torch.load(guard(start['parent']), map_location='cpu', weights_only=True)
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    # the run's own quiz prompts (random.Random(f'{seed}-quiz')) are kept out, as practice does
    mode.make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{run_seed}-quiz'), ctx, lambda *a, **k: None)
    rng = random.Random(f'g-ceiling-{seed}')
    share = {k: 1 / len(kinds) for k in kinds}
    items, disc, tries = [], Counter(), 0
    while len(items) < n:
        got, d, t, _ = mode.make_practice(tool, kinds, ex, share, n - len(items), rng, ctx)
        items += got
        disc.update(d)
        tries += t
        if not got:
            break
    return items, kinds, dict(tries=tries, discards=dict(disc), run_seed=run_seed, constants_sha256=start.get('constants_sha256'))


def gen(a):
    torch.set_num_threads(a.threads)
    n = 600 if a.smoke else a.n
    out = a.out
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    items, kinds, info = build_questions(a.seed, a.run, n)
    t_make = time.time() - t0
    prompts = [it['prompt'] for it in items]
    assert len(set(prompts)) == len(prompts)
    m = load_model(guard(a.ckpt)).eval()
    check_same(m, prompts[:8])
    t1 = time.time()
    rows = dict(A=[], S=[], c=[], P=[], DIAG=[], y=[], same=[])
    for s in range(0, len(prompts), BS):
        chunk = prompts[s:s + BS]
        r = chunk_features(m, chunk)
        for i, p in enumerate(chunk):
            it = items[s + i]
            flags, nd = process_flags(r['ans'][i], [f[i] for f in r['forced']])
            ncalls, last = call_features(r['calls'][i], r['ans'][i])
            rows['P'].append(flags + [nd, float(r['c'][i]), ncalls, last, len(p)])
            rows['DIAG'].append(list(diag_features(p)))
            rows['y'].append(int(r['ans'][i] == it['value']))
        rows['A'].append(r['A']), rows['S'].append(r['S']), rows['c'].append(r['c'])
        if (s // BS) % 20 == 0:
            print(f'{s + len(chunk)}/{len(prompts)} {time.time() - t1:.0f}s', flush=True)
    t_feat = time.time() - t1
    y, kind = np.array(rows['y']), np.array([it['kind'] for it in items])
    A, S, c = np.concatenate(rows['A']), np.concatenate(rows['S']), np.concatenate(rows['c'])
    P = np.array(rows['P'], dtype=np.float64)
    np.savez(os.path.join(out, 'data.npz'), y=y, kind=kind, prompts=np.array(prompts), A=A, S=S, c=c,
             S900=np.hstack([A, S, c[:, None]]), P=P, LEN=P[:, -1:], DIAG=np.array(rows['DIAG'], dtype=np.float64),
             P_names=np.array(P_NAMES))
    per_kind = {k: dict(n=int((kind == k).sum()), success=float(y[kind == k].mean())) for k in kinds if (kind == k).any()}
    sha = hashlib.sha256(open(__file__, 'rb').read()).hexdigest()
    gi = dict(seed=a.seed, smoke=a.smoke, checkpoint=a.ckpt, run=a.run, n_rows=len(y), n_wanted=n, kinds=kinds,
              success_overall=float(y.mean()), success_per_kind=per_kind, dims=dict(A=A.shape[1], S=S.shape[1], S900=A.shape[1] + S.shape[1] + 1),
              secs=dict(make_questions=round(t_make, 1), features=round(t_feat, 1), per_question=round(t_feat / len(y), 4)),
              threads=a.threads, code_sha256=sha, **info)
    json.dump(gi, open(os.path.join(out, 'gen_info.json'), 'w'), indent=1)
    print(f'gen: {len(y)} rows, success {y.mean():.3f}, {t_feat / len(y):.3f}s/question (features, 5 runs), made in {t_make:.0f}s')


# ---------- fit ----------

def stratified_folds(kind, k=FOLDS, seed=FOLD_SEED):
    """Fold id per row; each kind's rows are shuffled (fixed seed) and dealt round-robin, so every row is in exactly one fold."""
    rs = np.random.RandomState(seed)
    fold = np.zeros(len(kind), dtype=int)
    off = 0
    for kd in sorted(set(kind)):
        ix = np.where(kind == kd)[0]
        ix = ix[rs.permutation(len(ix))]
        fold[ix] = (np.arange(len(ix)) + off) % k
        off += len(ix)
    return fold


def nested_subsets(n_rows, sizes=SIZES, seed=SUBSET_SEED):
    """One fixed permutation; size s -> its first min(s, n_rows) rows, so smaller subsets are inside larger ones."""
    perm = np.random.RandomState(seed).permutation(n_rows)
    return {s: np.sort(perm[:min(s, n_rows)]) for s in sizes}


def cross_fit(X, y, kind, k=FOLDS):
    """Out-of-fold probe prediction and out-of-fold per-kind rate (training folds only)."""
    fold = stratified_folds(kind, k)
    v, kr = np.zeros(len(y)), np.zeros(len(y))
    for f in range(k):
        tr, te = fold != f, fold == f
        v[te] = fit_logistic(X[tr], y[tr])(X[te])
        rate = {kd: y[tr & (kind == kd)].mean() for kd in set(kind[tr])}
        kr[te] = [rate.get(kd, y[tr].mean()) for kd in kind[te]]
    return v, kr


def score(y, v, kr, kind):
    wk, groups, rows = within_kind_auc(y, v, kind, np.zeros(len(y), dtype=int))
    return dict(n=len(y), within_kind_auc=wk, groups=groups, rows=rows, pooled_auc=auc(y, v),
                brier=float(np.mean((y - v) ** 2)), brier_kind_rate=float(np.mean((y - kr) ** 2)))


def marks(res, seed, sizes_used):
    """res[probe][size] -> dict. Per-seed verdict for each B15 mark (seeds are combined by hand)."""
    g = lambda p, s: res[p][s]['within_kind_auc'] if s in res[p] else None
    base, top = BASELINE.get(seed), max(sizes_used)
    out, ok = {}, lambda x: x is not None
    s0 = g('S900', min(sizes_used))
    out['Drift is a main limit'] = dict(holds=bool(ok(s0) and base is not None and s0 >= base + 0.05),
                                        detail=f'S900 at {min(sizes_used)} = {s0}, baseline {base} + 0.05 = {None if base is None else round(base + 0.05, 3)}')
    best = {p: max([g(p, s) for s in sizes_used if s <= 16000 and ok(g(p, s))] or [None], default=None) for p in SHIPPABLE}
    out['Readable with enough data (PASS)'] = dict(holds=any(ok(b) and b >= 0.65 for b in best.values()),
                                                   detail=f'best within-kind AUC at <=16000 rows: {best}')
    eq = {s: (g('P', s), g('S900', s)) for s in sizes_used}
    per = {s: bool(ok(p) and ok(q) and p >= 0.62 and p >= q) for s, (p, q) in eq.items()}
    out['Behaviour beats state'] = dict(holds=per[top], detail=f'(size: P, S900, holds) {[(s, *eq[s], per[s]) for s in sizes_used]}; verdict taken at the largest size {top}, any size: {any(per.values())}')
    at_top = {p: g(p, top) for p in SHIPPABLE}
    mid = [s for s in sizes_used if s == 16000]
    gain = {p: (None if not (mid and ok(g(p, top)) and ok(g(p, 16000))) else round(g(p, top) - g(p, 16000), 4)) for p in SHIPPABLE}
    wrong = all(ok(v) and v < 0.62 for v in at_top.values()) and all(ok(v) and v < 0.01 for v in gain.values())
    out['PROVED WRONG'] = dict(holds=bool(wrong), detail=f'at {top} rows: {at_top}; gain 16000->{top}: {gain}')
    return out


def fit(a):
    torch.set_num_threads(2)
    d = np.load(os.path.join(a.dir, 'data.npz'))
    gi = json.load(open(os.path.join(a.dir, 'gen_info.json')))
    seed = gi['seed']
    y, kind = d['y'].astype(float), d['kind']
    feats = {'S900': d['S900'], 'P': d['P'], 'S900+P': np.hstack([d['S900'], d['P']]), 'LEN': d['LEN'], 'DIAG': d['DIAG']}
    subs = nested_subsets(len(y))
    note = [f'{s}: only {len(y)} rows exist, all used' for s in SIZES if s > len(y)]
    res = {p: {} for p in PROBES}
    for s in SIZES:
        ix = subs[s]
        n = len(ix)
        for p in PROBES:
            t = time.time()
            v, kr = cross_fit(feats[p][ix], y[ix], kind[ix])
            res[p][s] = score(y[ix], v, kr, kind[ix])
            print(f'size {s} ({n} rows) {p}: wk-AUC {res[p][s]["within_kind_auc"]} ({time.time() - t:.0f}s)', flush=True)
    mk = marks(res, seed, list(SIZES))   # sizes above the rows available use all rows (noted)
    out = dict(seed=seed, n_rows=len(y), notes=note, baseline=BASELINE.get(seed), results={p: {str(s): r for s, r in v.items()} for p, v in res.items()}, marks=mk)
    json.dump(out, open(os.path.join(a.dir, 'RESULT.json'), 'w'), indent=1)
    f3 = lambda x: '-' if x is None else f'{x:.3f}'
    L = [f'# G-ceiling result, seed {seed} ({len(y)} rows, success {y.mean():.3f}; {a.dir})', '']
    L += [f'Note: {x}' for x in note] + ([''] if note else [])
    L += [f'Within-kind AUC (Brier vs per-kind rate Brier in brackets); baseline D0 walk-forward S900 = {BASELINE.get(seed)}', '',
          '| probe | ' + ' | '.join(str(s) for s in SIZES) + ' |', '|---|' + '---|' * len(SIZES)]
    for p in PROBES:
        L.append(f'| {p} | ' + ' | '.join(f'{f3(res[p][s]["within_kind_auc"])} ({res[p][s]["brier"]:.4f} / {res[p][s]["brier_kind_rate"]:.4f})' for s in SIZES) + ' |')
    L += ['', 'Pooled AUC:', '', '| probe | ' + ' | '.join(str(s) for s in SIZES) + ' |', '|---|' + '---|' * len(SIZES)]
    for p in PROBES:
        L.append(f'| {p} | ' + ' | '.join(f3(res[p][s]['pooled_auc']) for s in SIZES) + ' |')
    L += ['', 'Marks (this seed only; both seeds must hold):', '']
    for k, v in mk.items():
        L.append(f'- {k}: {"HOLDS" if v["holds"] else "does not hold"}. {v["detail"]}')
    open(os.path.join(a.dir, 'RESULT.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--seed', type=int, required=True)
    g.add_argument('--ckpt', required=True)
    g.add_argument('--run', required=True)
    g.add_argument('--out', required=True)
    g.add_argument('--n', type=int, default=32000)
    g.add_argument('--threads', type=int, default=2)
    g.add_argument('--smoke', action='store_true')
    f = sp.add_parser('fit')
    f.add_argument('--dir', required=True)
    a = ap.parse_args(argv)
    gen(a) if a.cmd == 'gen' else fit(a)


if __name__ == '__main__':
    main()
