"""G-transfer test (section "G-transfer" of DESIGN-AND-MARKS-2026-10-10.md). No training; the models are frozen, read-only.

  python -m dopamine.g_transfer --run RUNDIR --seed 200 --out OUTDIR [--n 8000] [--threads 2] [--smoke]

For each day d = 2..N: the model that tried day d (night_{d-1}) answers N fresh make_practice questions (even share over kinds,
rng random.Random(f'g-transfer-{seed}-day{d}'), the run's quiz and ALL logged 'row' prompts excluded), labelled by the tool's value.
A head (D0's fit_logistic, C=1, standardised) is fit on S900 = [A, S, conf] of those rows (all, and a fixed 2,500 subset) and
scores day d's logged practice tries (D0's rows, D0's features pass, y as D0). Baseline = D0's walk-forward head (fit on days < d).
NOTE: D0's own head "G" uses [A, S] (899 dims, no conf); the baseline here uses exactly that so it reproduces D0's json. The
S900 variants and the cross-variants (S899 self-quiz, S900 walk-forward) are reported as extras.
Only OUTDIR is written.
"""
import argparse
import hashlib
import importlib
import json
import os
import random
import time
from collections import Counter

import numpy as np
import torch

from domain import mode
from domain.mode import guard
from dopamine.d0_guess import auc, day_features, fit_logistic, load_days, metrics, within_kind_auc
from custom_io.models import load_model

MARK_PASS_ABS, MARK_PASS_GAP, MARK_WRONG_GAP, VALID_TOL = 0.62, 0.05, 0.01, 0.01
SUBSET = 2500
HERE = os.path.dirname(os.path.abspath(__file__))


def setup(run):
    """Domain mode's machinery as g_ceiling.build_questions builds it, once per run.
    -> (tool, kinds, ex, ctx, run_seed, logged_prompts). ctx['seen'] holds the quiz and every logged 'row' prompt."""
    ev = [json.loads(l) for l in open(guard(os.path.join(run, 'log.jsonl')))]
    start = next(e for e in ev if e['event'] == 'start')
    cons, run_seed = start['constants'], start['seed']
    tool = importlib.import_module(f"domain.tools.{start['tool']}")
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ex = {h['kind']: h['prompt'] for h in helps}
    ck = torch.load(guard(start['parent']), map_location='cpu', weights_only=True)
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    mode.make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{run_seed}-quiz'), ctx, lambda *a, **k: None)
    logged = {e['prompt'] for e in ev if e['event'] == 'row'}
    ctx['seen'] |= logged
    return tool, kinds, ex, ctx, run_seed, logged


def questions(setup_out, seed, d, n):
    """n fresh questions for day d. -> (items, tries, discards). Asserts no overlap with the quiz or any logged prompt."""
    tool, kinds, ex, ctx0, _, logged = setup_out
    ctx = dict(ctx0, seen=set(ctx0['seen']), quiz_set=set(ctx0['quiz_set']))
    rng = random.Random(f'g-transfer-{seed}-day{d}')
    share = {k: 1 / len(kinds) for k in kinds}
    items, disc, tries = [], Counter(), 0
    while len(items) < n:
        got, dd, t, _ = mode.make_practice(tool, kinds, ex, share, n - len(items), rng, ctx)
        items += got
        disc.update(dd)
        tries += t
        if not got:
            break
    ps = [it['prompt'] for it in items]
    assert len(set(ps)) == len(ps), 'duplicate self-quiz prompts'
    assert not (set(ps) & logged), 'self-quiz overlaps logged prompts'
    assert not (set(ps) & ctx0['quiz_set']), 'self-quiz overlaps the run quiz'
    return items, tries, dict(disc)


def feats(m, prompts):
    """-> (answers, S900 = [A, S, conf]) from D0's own pass."""
    ans, A, S, c = day_features(m, prompts)
    return ans, np.hstack([A, S, c[:, None]])


def kind_rate_pred(ytr, ktr, kind):
    rate = {k: ytr[ktr == k].mean() for k in set(ktr)}
    return np.array([rate.get(k, ytr.mean()) for k in kind])


def pooled_table(P):
    """P[name] = dict(v, y, kind, day lists) -> {name: metrics}."""
    cat = lambda n, k: np.concatenate(P[n][k])
    return {n: metrics(cat(n, 'y'), cat(n, 'v'), cat(n, 'kind'), cat(n, 'day')) for n in P if P[n]['v']}


def judge(res, base_json_wk, seed):
    """Marks for one seed from pooled within-kind AUCs. res: pooled table. -> dict."""
    sq, d0 = res['SELFQUIZ8K']['within_kind_auc'], res['D0']['within_kind_auc']
    out = dict(selfquiz8k=sq, d0_recomputed=d0, d0_json=base_json_wk)
    if base_json_wk is None or d0 is None or abs(d0 - base_json_wk) > VALID_TOL:
        out['verdict'] = 'NOT JUDGED: baseline did not reproduce'
        out['PASS'] = out['PROVED WRONG'] = None
        return out
    out['PASS'] = bool(sq is not None and sq >= MARK_PASS_ABS and sq >= d0 + MARK_PASS_GAP)
    out['PROVED WRONG'] = bool(sq is not None and sq <= d0 + MARK_WRONG_GAP)
    out['verdict'] = 'judged'
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='G-transfer: does a head fit on a self-quiz rank the next day\'s real practice?')
    ap.add_argument('--run', required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=8000)
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--smoke', action='store_true', help='days 2..3, 300 self-quiz questions, 128 day rows per day')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    os.makedirs(a.out, exist_ok=True)
    t00 = time.time()
    secs = dict(setup=0.0, load=0.0, day_features=0.0, make_questions=0.0, selfquiz_features=0.0, fit=0.0)
    n_sq = 300 if a.smoke else a.n
    parent, rows, N = load_days(a.run)
    if a.smoke:
        N = min(N, 3)
    rows = {d: (rows[d][:128] if a.smoke else rows[d]) for d in range(1, N + 1)}
    t = time.time()
    so = setup(a.run)
    secs['setup'] = time.time() - t
    sub_n = min(SUBSET, n_sq)

    D = {}   # day -> dict(y, kind, X)  day rows with the model that tried them
    info_days = {}
    P = {n: dict(v=[], y=[], kind=[], day=[]) for n in
         ('SELFQUIZ8K', 'SELFQUIZ2.5K', 'D0', 'K_D0', 'K_SQ', 'SELFQUIZ8K_S899', 'D0_S900')}
    add = lambda n, v, y, kind, d: [P[n][k].append(x) for k, x in (('v', v), ('y', y), ('kind', kind), ('day', np.full(len(y), d)))]
    per_day = {}

    for d in range(1, N + 1):
        t = time.time()
        ck = parent if d == 1 else os.path.join(a.run, f'night_{d - 1}', 'checkpoint.pt')
        m = load_model(guard(ck)).eval()
        secs['load'] += time.time() - t
        t = time.time()
        rs = rows[d]
        ans, X = feats(m, [r['prompt'] for r in rs])
        y = np.array([int(x == r['answer']) for x, r in zip(ans, rs)])
        kind = np.array([r['kind'] for r in rs])
        D[d] = dict(y=y, kind=kind, X=X)
        secs['day_features'] += time.time() - t
        np.savez(os.path.join(a.out, f'day{d}_rows.npz'), y=y, kind=kind, S900=X)
        print(f'day {d}: model {"parent" if d == 1 else f"night_{d - 1}"}, {len(rs)} day rows, right {y.mean():.3f}', flush=True)
        if d == 1:
            info_days[d] = dict(n_rows=len(rs), success=float(y.mean()), ok=True)
            continue
        t = time.time()
        items, tries, disc = questions(so, a.seed, d, n_sq)
        secs['make_questions'] += time.time() - t
        t = time.time()
        qa, QX = feats(m, [it['prompt'] for it in items])
        qy = np.array([int(x == it['value']) for x, it in zip(qa, items)])
        qk = np.array([it['kind'] for it in items])
        secs['selfquiz_features'] += time.time() - t
        np.savez(os.path.join(a.out, f'day{d}_selfquiz.npz'), y=qy, kind=qk, S900=QX)
        print(f'day {d}: self-quiz {len(qy)} q, right {qy.mean():.3f}, {(time.time() - t) / len(qy):.3f} s/q', flush=True)
        t = time.time()
        sub = np.sort(np.random.default_rng(0).permutation(len(qy))[:sub_n])
        tr = list(range(1, d))
        Xtr, ytr, ktr = (np.concatenate([D[x][k] for x in tr]) for k in ('X', 'y', 'kind'))
        Xd = D[d]['X']
        preds = {
            'SELFQUIZ8K': fit_logistic(QX, qy)(Xd),
            'SELFQUIZ2.5K': fit_logistic(QX[sub], qy[sub])(Xd),
            'D0': fit_logistic(Xtr[:, :-1], ytr)(Xd[:, :-1]),             # D0's G: [A, S] without conf
            'K_D0': kind_rate_pred(ytr, ktr, kind),
            'K_SQ': kind_rate_pred(qy, qk, kind),
            'SELFQUIZ8K_S899': fit_logistic(QX[:, :-1], qy)(Xd[:, :-1]),   # extras: same feature set as D0
            'D0_S900': fit_logistic(Xtr, ytr)(Xd),
        }
        secs['fit'] += time.time() - t
        for n, v in preds.items():
            add(n, v, y, kind, d)
        per_day[d] = {n: metrics(y, v, kind, np.full(len(y), d)) for n, v in preds.items()}
        info_days[d] = dict(n_rows=len(rs), success=float(y.mean()), selfquiz_n=len(qy), selfquiz_success=float(qy.mean()),
                            selfquiz_tries=tries, selfquiz_discards=disc, ok=True)
        print(f'day {d}: wk-AUC ' + ' '.join(f'{n}={per_day[d][n]["within_kind_auc"]:.3f}' if per_day[d][n]['within_kind_auc'] is not None
                                           else f'{n}=-' for n in ('SELFQUIZ8K', 'SELFQUIZ2.5K', 'D0')), flush=True)

    pooled = pooled_table(P)
    jpath = os.path.join(os.path.dirname(HERE), 'dopamine', 'results', 'd0', f'sheet-s{a.seed}-v7.json')
    bj = None
    if os.path.exists(jpath):
        bj = json.load(open(jpath))['pooled_days_2_to_N']['G']['within_kind_auc']
    marks = judge(pooled, bj, a.seed)
    code_sha = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    total = time.time() - t00
    nq = sum(v.get('selfquiz_n', 0) for v in info_days.values())
    info = dict(code_sha256=code_sha, run=a.run, seed=a.seed, smoke=a.smoke, days=N, threads=a.threads,
                secs={k: round(v, 1) for k, v in secs.items()}, secs_total=round(total, 1),
                secs_per_selfquiz_question=round(secs['selfquiz_features'] / nq, 4) if nq else None,
                per_day=info_days, n_selfquiz_rows=nq, n_day_rows=sum(len(D[d]['y']) for d in D))
    json.dump(info, open(os.path.join(a.out, 'info.json'), 'w'), indent=1)
    result = dict(seed=a.seed, smoke=a.smoke, pooled_days_2_to_N=pooled, per_day=per_day, marks=marks, d0_json_path=jpath)
    json.dump(result, open(os.path.join(a.out, 'RESULT.json'), 'w'), indent=1)

    f3 = lambda x: '-' if x is None else f'{x:.3f}'
    L = [f'# G-transfer result, seed {a.seed}{" (SMOKE: not a result)" if a.smoke else ""}', '',
         f'run {a.run}; days 2..{N}; self-quiz {n_sq} q per day; subset {sub_n}.', '',
         '| head | within-kind AUC | groups | pooled AUC | Brier |', '|---|---|---|---|---|']
    for n, r in pooled.items():
        L.append(f'| {n} | {f3(r["within_kind_auc"])} | {r["within_kind_groups"]} | {f3(r["auc"])} | {r["brier"]:.4f} |')
    L += ['', 'Per day within-kind AUC (SELFQUIZ8K / SELFQUIZ2.5K / D0) and pooled AUC:', '']
    for d, pdm in per_day.items():
        L.append(f'- day {d}: ' + ' / '.join(f3(pdm[n]['within_kind_auc']) for n in ('SELFQUIZ8K', 'SELFQUIZ2.5K', 'D0'))
                 + ' ; AUC ' + ' / '.join(f3(pdm[n]['auc']) for n in ('SELFQUIZ8K', 'SELFQUIZ2.5K', 'D0')))
    L += ['', 'Marks (this seed; seeds are combined by hand):', '']
    if marks['verdict'] != 'judged':
        L.append(f'- NOT JUDGED: baseline did not reproduce. D0 recomputed {f3(marks["d0_recomputed"])}, D0 json {f3(marks["d0_json"])} '
                 f'(tolerance {VALID_TOL}).')
    else:
        L.append(f'- Baseline check: D0 recomputed {f3(marks["d0_recomputed"])} vs json {f3(marks["d0_json"])}: reproduces.')
    for k, rule in (('PASS', f'SELFQUIZ8K >= {MARK_PASS_ABS} and >= D0 + {MARK_PASS_GAP}'), ('PROVED WRONG', f'SELFQUIZ8K <= D0 + {MARK_WRONG_GAP}')):
        h = marks[k]
        L.append(f'- {k} ({rule}): ' + ('not judged' if h is None else 'HOLDS' if h else 'does not hold')
                 + f'. SELFQUIZ8K {f3(marks["selfquiz8k"])}, D0 {f3(marks["d0_recomputed"])}')
    L += ['', 'Extras: SELFQUIZ8K_S899 = self-quiz head on [A,S] (D0\'s feature set); D0_S900 = walk-forward head on [A,S,conf].']
    open(os.path.join(a.out, 'RESULT.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print(f'total {total:.0f}s, {info["secs_per_selfquiz_question"]} s per self-quiz question', flush=True)


if __name__ == '__main__':
    main()
