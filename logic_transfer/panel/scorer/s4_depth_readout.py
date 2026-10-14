"""Which rows does score.py's by_depth / by_depth_label silently leave out, and what does 'chance' mean for the depth read-outs?
Uses the real score.analyze with constant predictors (fake model, no checkpoint).

  PYTHONPATH=<worktree> python s4_depth_readout.py -> s4_depth_readout.json
"""
import collections
import json

import torch

torch.set_num_threads(1)
from common import *          # noqa
from s1_controls import Fake  # noqa
from logic_transfer import score as S


def main():
    R = {}
    for n in EVAL_FILES:
        rows = load(n)
        lv = collections.Counter((r['level'], r['meta']['label']) for r in rows)
        dn = collections.Counter((r['meta'].get('depth'), r['meta']['label']) for r in rows)
        d = dict(n=len(rows),
                 level_x_label={f'{k[0]}|{k[1]}': v for k, v in sorted(lv.items(), key=str)},
                 metadepth_x_label={f'{k[0]}|{k[1]}': v for k, v in sorted(dn.items(), key=str)},
                 n_rows_with_depth_None=sum(r['meta'].get('depth') is None for r in rows),
                 depth_None_labels=dict(collections.Counter(r['meta']['label'] for r in rows if r['meta'].get('depth') is None)))
        const = {}
        for w in WORDS3:
            out, _ = S.analyze(Fake(lambda r, w=w: w), rows, 128, logic=True)
            const[w] = dict(overall=[out['correct'], out['n']], by_level=out['by_level'], by_depth=out['by_depth'])
        d['constant_predictors'] = const
        # pooled depth 2-3 (the marks' 'rule-first depths 2-3 pooled' readout) under each constant predictor
        pool = {}
        for w, c in const.items():
            cs = sum(c['by_depth'].get(k, {'correct': 0})['correct'] for k in ('2', '3'))
            ns = sum(c['by_depth'].get(k, {'n': 0})['n'] for k in ('2', '3'))
            pool[w] = [cs, ns, round(100 * cs / max(ns, 1), 2)]
        d['pooled_depth2_3_constant_predictor_accuracy_correct_n_pct'] = pool
        R[n] = d
    wjson('s4_depth_readout.json', R)
    for n, d in R.items():
        print(n, 'depth None rows', d['n_rows_with_depth_None'], d['depth_None_labels'], 'pooled d2-3 const:', d['pooled_depth2_3_constant_predictor_accuracy_correct_n_pct'])
        print('   level x label', d['level_x_label'])


if __name__ == '__main__':
    main()
