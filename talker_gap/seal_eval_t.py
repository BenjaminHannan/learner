"""Amendments 2 and 2c scoring: B0, T1, T1-nothinker, T2, T1-long (seeds 0-2) on FRESH-R7, marks C1/C1b/C2/C3.

FRESH-R7 is spent by reading it, so scoring it needs --final and happens once, after every arm and seed has finished.
Any other split (e.g. TEST, to exercise this script) needs no flag. Nothing is tuned on what this prints.
Decision rule (Amendment 2c): pass_by_rows decides; pass_by_question_clusters is a sensitivity report only.

  PYTHONPATH=... seal_eval_t.py --final
  PYTHONPATH=... seal_eval_t.py --split TEST --runs b0:0,t1:0      (pipeline check; not a mark)
"""
import argparse
import json
import os
import random
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import run_arm as RA  # noqa: E402
import run_t as RT  # noqa: E402
from models import Arm  # noqa: E402

SEALED = os.path.expanduser('~/talker_gap_cache/sealed')
R7 = 'FRESH-R7'
DEFAULT_RUNS = [(a, s) for a in ('b0', 't1', 't1_nothinker', 't2', 't1_long') for s in (0, 1, 2)]
PRACTISED_OPENERS = ('who', 'what', 'which')     # openers TEACH covers; the other four are never practised
C1_MARK, C2_MARK = 3.0, 5.0                      # Amendment 2
C1B_MARK = 3.0                                   # Amendment 2c: T2 - T1-long


def parse_runs(text):
    out = []
    for item in text.split(','):
        arm, seed = item.split(':')
        out.append((arm, int(seed)))
    return out


def hits_b0(arm, seed, split):
    d = RA.load_split(SEALED, split)
    m = Arm(arm)
    m.load_state_dict(torch.load(os.path.join(HERE, 'results', f'{arm}_s{seed}', 'model.pt'), map_location='cpu'))
    m.eval()
    mode, S, E = RA.predict(m, d, torch.device('cpu'))
    return np.array([int(C.is_hit(RA.pred_string(r, int(mode[i]), int(S[i]), int(E[i])), r['accepted']))
                     for i, r in enumerate(d['rows'])], np.int64), d['rows']


def hits_t(arm, seed, split):
    ck = torch.load(os.path.join(HERE, 'results', f'{arm}_s{seed}', 'model.pt'), map_location='cpu')
    itos = ck['itos']
    stoi = {c: i for i, c in enumerate(itos)}
    d = RT.prep(RT.load_split(SEALED, split, evaluate=True), stoi, RT.MAX_TGT, with_target=False)
    m = RT.TArm(arm, len(itos))
    m.load_state_dict(ck['state_dict'])
    m.eval()
    gens = RT.predict(m, d, torch.device('cpu'), itos)
    _, hits, _ = RT.score(d['rows'], gens)
    return hits.astype(np.int64), d['rows']


def opener(row):
    return row['question'].split()[0].lower()


def qid(row):
    return row['id'].rsplit('/', 1)[0]            # source and paraphrase of one question share this


def cluster_bootstrap(diff, groups, n=2000, seed=0):
    """Resample whole questions (source+paraphrase together). -> (mean, lo, hi) in points."""
    rng = random.Random(seed)
    by = {}
    for x, g in zip(diff, groups):
        by.setdefault(g, []).append(float(x))
    keys = list(by)
    rows = len(diff)
    stats = []
    for _ in range(n):
        s = 0.0
        cnt = 0
        for _ in keys:
            v = by[keys[rng.randrange(len(keys))]]
            s += sum(v)
            cnt += len(v)
        stats.append(100.0 * s / cnt)
    stats.sort()
    return 100.0 * float(np.mean(diff)), stats[int(0.025 * n)], stats[int(0.975 * n) - 1]


def compare(name, A, B, seeds, rows, mark=None):
    """A, B: {seed: hits}. Mark rule: mean diff >= mark, row-bootstrap 95% interval excludes 0, diff > 0 in every seed."""
    ma = np.mean([A[s] for s in seeds], axis=0)
    mb = np.mean([B[s] for s in seeds], axis=0)
    mean_d, lo, hi = C.paired_bootstrap(list(ma), list(mb))
    cm, clo, chi = cluster_bootstrap(ma - mb, [qid(r) for r in rows])
    per_seed = {int(s): round(100.0 * float(np.mean(A[s]) - np.mean(B[s])), 2) for s in seeds}
    out = {'name': name, 'mean_diff': round(mean_d, 2), 'row_ci95': [round(lo, 2), round(hi, 2)],
           'question_cluster_ci95': [round(clo, 2), round(chi, 2)], 'per_seed_diff': per_seed}
    if mark is not None:
        out['mark'] = mark
        out['pass_by_rows'] = bool(mean_d >= mark and lo > 0 and all(v > 0 for v in per_seed.values()))
        out['pass_by_question_clusters'] = bool(mean_d >= mark and clo > 0 and all(v > 0 for v in per_seed.values()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', action='store_true', help='required to score FRESH-R7 (once, at the very end)')
    ap.add_argument('--split', default=R7)
    ap.add_argument('--runs', default=None, help='arm:seed,arm:seed (default: all 15)')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    if a.split == R7 and not a.final:
        sys.exit('refusing: FRESH-R7 is scored once, at the very end, with --final')
    runs = parse_runs(a.runs) if a.runs else DEFAULT_RUNS
    out_path = a.out or os.path.join(HERE, 'results', f'{a.split.lower().replace("-", "_")}_results.json')
    if a.split == R7 and os.path.exists(out_path):
        sys.exit(f'refusing: {out_path} exists; FRESH-R7 results are never overwritten')

    hits, rows = {}, None
    for arm, seed in runs:
        h, r = (hits_b0 if arm == 'b0' else hits_t)(arm, seed, a.split)
        hits[(arm, seed)] = h
        if rows is None:
            rows = r
        assert [x['id'] for x in rows] == [x['id'] for x in r]
        print(f'{arm} s{seed}: short EM {100.0 * h.mean():.2f}', flush=True)

    arms = sorted({k[0] for k in hits})
    seeds_of = {arm: sorted(s for (a_, s) in hits if a_ == arm) for arm in arms}
    ops = np.array([opener(r) for r in rows])
    prac = np.isin(ops, PRACTISED_OPENERS)
    res = {'split': a.split, 'n_rows': len(rows), 'n_questions': len({qid(r) for r in rows}), 'runs': {}}
    for (arm, seed), h in sorted(hits.items()):
        res['runs'][f'{arm}_s{seed}'] = {
            'short_em': round(100.0 * float(h.mean()), 2),
            'by_opener': {o: round(100.0 * float(h[ops == o].mean()), 2) for o in sorted(set(ops))},
            'practised_openers_em': round(100.0 * float(h[prac].mean()), 2),
            'never_practised_openers_em': round(100.0 * float(h[~prac].mean()), 2)}
    res['arm_means'] = {arm: round(100.0 * float(np.mean([hits[(arm, s)].mean() for s in seeds_of[arm]])), 2)
                        for arm in arms}

    def pair(x, y):
        seeds = sorted(set(seeds_of.get(x, [])) & set(seeds_of.get(y, [])))
        if not seeds:
            return None
        return {s: hits[(x, s)] for s in seeds}, {s: hits[(y, s)] for s in seeds}, seeds

    marks = {}
    for key, x, y, mark in (('C1 T2-T1', 't2', 't1', C1_MARK), ('C1b T2-T1long', 't2', 't1_long', C1B_MARK),
                            ('C2 T2-B0', 't2', 'b0', C2_MARK), ('C3 T1-B0', 't1', 'b0', None),
                            ('T1-T1nothinker', 't1', 't1_nothinker', None), ('T1long-T1', 't1_long', 't1', None)):
        p = pair(x, y)
        if p:
            marks[key] = compare(key, p[0], p[1], p[2], rows, mark)
    res['marks'] = marks
    sec = {}
    p = pair('t2', 't1')
    if p:
        for label, mask in (('practised_openers', prac), ('never_practised_openers', ~prac)):
            idx = np.where(mask)[0]
            ma = np.mean([p[0][s][idx] for s in p[2]], axis=0)
            mb = np.mean([p[1][s][idx] for s in p[2]], axis=0)
            sec[label] = {'n_rows': int(mask.sum()), 'mean_diff': round(100.0 * float(np.mean(ma - mb)), 2)}
    res['secondary_t2_minus_t1_by_opener_group'] = sec
    with open(out_path, 'w') as f:
        json.dump(res, f, indent=1)
    with open(out_path.replace('_results.json', '_hits.json'), 'w') as f:
        json.dump({f'{k[0]}_s{k[1]}': [int(x) for x in v] for k, v in hits.items()}, f)
    print(json.dumps({'arm_means': res['arm_means'], 'marks': marks, 'secondary': sec}, indent=1))
    print('wrote', out_path)


if __name__ == '__main__':
    main()
