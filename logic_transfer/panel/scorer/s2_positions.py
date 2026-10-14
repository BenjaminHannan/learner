"""Is the option order in the ' (a/b/c)' suffix independent of the label? Contingency tables (label x gold position) for every
eval file and for the first 50,000 rows of each train file (streamed). Pure Python (stdlib only; chi-square p via the
regularised gamma series). Also: label shares, and constant/position predictor accuracy on the train rows.

  PYTHONPATH=<worktree> python s2_positions.py -> s2_positions.json
"""
import collections
import json
import math

from common import *          # noqa


def chi2_sf(x, k):
    """P(chi2_k >= x) via the regularised upper incomplete gamma (series / continued fraction)."""
    a, xx = k / 2.0, x / 2.0
    if xx <= 0:
        return 1.0
    if xx < a + 1:
        term = s = 1.0 / a
        n = a
        for _ in range(500):
            n += 1
            term *= xx / n
            s += term
            if term < s * 1e-14:
                break
        p = s * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
        return 1 - p
    b = xx + 1 - a
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        dl = d * c
        h *= dl
        if abs(dl - 1) < 1e-14:
            break
    return math.exp(-xx + a * math.log(xx) - math.lgamma(a)) * h


def table(rows):
    t = collections.defaultdict(lambda: [0, 0, 0])
    bad = 0
    for r in rows:
        s = suffix_order(r['prompt'])
        if s is None or r['answer'] not in s:
            bad += 1
            continue
        t[r['answer']][s.index(r['answer'])] += 1
    labs = [l for l in WORDS3]
    tab = [t[l] for l in labs]
    n = sum(map(sum, tab))
    rs = [sum(r) for r in tab]
    cs = [sum(tab[i][j] for i in range(3)) for j in range(3)]
    chi_ind = sum((tab[i][j] - rs[i] * cs[j] / n) ** 2 / (rs[i] * cs[j] / n) for i in range(3) for j in range(3))
    exp_u = n / 3
    chi_unif = sum((c - exp_u) ** 2 / exp_u for c in cs)
    return dict(n=n, bad_suffix=bad, label_counts={l: rs[i] for i, l in enumerate(labs)},
                position_counts=cs, position_share=[round(c / n, 4) for c in cs],
                table_label_by_position={l: tab[i] for i, l in enumerate(labs)},
                chi2_label_x_position=round(chi_ind, 3), p_independence=round(chi2_sf(chi_ind, 4), 4),
                chi2_position_uniform=round(chi_unif, 3), p_uniform=round(chi2_sf(chi_unif, 2), 4),
                label_share={l: round(rs[i] / n, 4) for i, l in enumerate(labs)})


def stream(path, k):
    out = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            out.append({'id': r['id'], 'prompt': r['prompt'], 'answer': r['answer']})
            if len(out) >= k:
                break
    return out


def main():
    R = {'eval': {}, 'train_first50k': {}}
    pooled = []
    for n in EVAL_FILES:
        rows = load(n, keep=('id', 'prompt', 'answer'))
        R['eval'][n] = table(rows)
        pooled += rows
    R['eval']['POOLED_ALL_EVAL'] = table(pooled)
    for n in ('logic_train', 'placebo_train'):
        rows = stream(f'{ROWS}/{n}.jsonl', 50000)
        R['train_first50k'][n] = table(rows)
        del rows
    wjson('s2_positions.json', R)
    for k, v in R['eval'].items():
        print(k, v['position_share'], 'p_indep', v['p_independence'], 'p_unif', v['p_uniform'])
    for k, v in R['train_first50k'].items():
        print(k, v['n'], v['position_share'], v['label_share'], 'p_indep', v['p_independence'], 'p_unif', v['p_uniform'])


if __name__ == '__main__':
    main()
