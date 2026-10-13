"""H0: read-only calibration of the motivator's competence head over C. See task text; writes only --out json."""
import argparse
import importlib
import json
import os
import random
import time

import numpy as np
import torch

from custom_io.models import load_model
from domain.mode import greedy, lmax_of, make_quiz
from dopamine.d0_guess import auc, fit_logistic, load_days, within_kind_auc
from dopamine.motivator import quiz_eval_hits, reader_features

CS = [0.001, 0.01, 0.1, 1.0]


class Dummy:
    def __call__(self, *a, **k):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    t0 = time.time()
    ev = [json.loads(l) for l in open(os.path.join(a.run, 'log.jsonl'))]
    st = next(e for e in ev if e['event'] == 'start')
    cons, seed, parent = st['constants'], st['seed'], st['parent']
    tool = importlib.import_module(f"domain.tools.{st['tool']}")
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ex = {h['kind']: h['prompt'] for h in helps}
    lmax = lmax_of(helps, cons['digit_len_extra'])
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=lmax)
    quiz = make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{seed}-quiz'), ctx, Dummy())
    qp = [q['prompt'] for q in quiz]
    qkind = np.array([q['kind'] for q in quiz])
    _, rows, N = load_days(a.run)
    log_before = next(e for e in ev if e['event'] == 'quiz')['per_kind']
    log_n1 = next(e for e in ev if e['event'] == 'night' and e['night'] == 1)['quiz_per_kind']

    data = []   # per k
    match = {}
    for k in range(N):
        path = parent if k == 0 else os.path.join(a.run, f'night_{k}', 'checkpoint.pt')
        torch.manual_seed(seed)
        m = load_model(path).eval()
        per, pooled, hits = quiz_eval_hits(m, quiz, kinds)
        if k == 0:
            match['parent_vs_before_night_1'] = {x: [round(per[x], 4), log_before[x]] for x in kinds}
        if k == 1:
            match['night_1_vs_log'] = {x: [round(per[x], 4), log_n1[x]] for x in kinds}
        Fq = reader_features(m, qp)
        rw = rows.get(k + 1, [])
        pr = [r['prompt'] for r in rw]
        res = greedy(m, pr)
        r = np.array([int(ans == row['answer']) for (_, ans), row in zip(res, rw)])
        Fd = reader_features(m, pr)
        data.append(dict(hits=np.array(hits), Fq=Fq, Fd=Fd, r=r, kind=np.array([x['kind'] for x in rw]), per=per))
        print('k', k, 'quiz', round(pooled, 4), 'day', k + 1, len(rw), 'right', r.mean() if len(r) else None, round(time.time() - t0), flush=True)
    ok = lambda d: all(abs(v[0] - v[1]) < 1e-3 for v in d.values())
    match_ok = {k: ok(v) for k, v in match.items()}

    def agg(ks, C):
        ys, Vs, Qs, kd, dy = [], [], [], [], []
        for k in ks:
            d = data[k]
            if not len(d['r']):
                continue
            V = fit_logistic(d['Fq'], d['hits'], C)(d['Fd'])
            rate = {x: d['hits'][d_kind == x].mean() for x in kinds for d_kind in [qkind]}
            Q = np.array([rate[x] for x in d['kind']])
            ys.append(d['r']); Vs.append(V); Qs.append(Q); kd.append(d['kind']); dy.append(np.full(len(d['r']), k + 1))
        y, V, Q, kd, dy = map(np.concatenate, (ys, Vs, Qs, kd, dy))
        w = within_kind_auc(y, V, kd, dy)
        wq = within_kind_auc(y, Q, kd, dy)
        u = V * (1 - V)
        return dict(n=len(y), right_rate=float(y.mean()), auc=auc(y, V), wk_auc=w[0], wk_groups=w[1], wk_auc_kindrate=wq[0],
                    brier=float(np.mean((y - V) ** 2)), brier_kindrate=float(np.mean((y - Q) ** 2)),
                    mean_abs_V_minus_kindrate=float(np.mean(np.abs(V - Q))),
                    meanVV_right=float(u[y == 1].mean()) if (y == 1).any() else None,
                    meanVV_wrong=float(u[y == 0].mean()) if (y == 0).any() else None, meanV=float(V.mean()))
    out = dict(run=a.run, N=N, quiz_match=match, quiz_match_ok=match_ok, table={})
    for C in CS:
        out['table'][str(C)] = dict(pooled_1_to_Nm1=agg(range(1, N), C), k0=agg([0], C))
    out['secs'] = round(time.time() - t0)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=float)
    f = lambda x: 'NA' if x is None else f'{x:.3f}'
    print('match', match_ok)
    for C in CS:
        for nm in ('pooled_1_to_Nm1', 'k0'):
            t = out['table'][str(C)][nm]
            print(f"C={C:<6} {nm:15} n={t['n']} AUC={f(t['auc'])} wkAUC={f(t['wk_auc'])}(kindrate {f(t['wk_auc_kindrate'])}) "
                  f"Brier={f(t['brier'])} (kindrate {f(t['brier_kindrate'])}) |V-q|={f(t['mean_abs_V_minus_kindrate'])} "
                  f"V(1-V) right={f(t['meanVV_right'])} wrong={f(t['meanVV_wrong'])}")
    print('secs', out['secs'])


main()
