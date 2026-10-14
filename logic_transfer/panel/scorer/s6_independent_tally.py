"""Stdlib-only re-tally (no custom_io, no score.py) of the D1b-3500 predictions on the full logic_gate file written by s3_recompute.py,
compared cell by cell with the saved score.json; plus z-scores of every saved D1b-3500 number against the best label-independent baseline.

  python s6_independent_tally.py -> s6_independent_tally.json
"""
import json
import math
import os

OUT = os.path.dirname(os.path.abspath(__file__))
EVAL = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval'
SAVED = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/score-D1b-u3500/score.json'


def main():
    R = {}
    preds = json.load(open(f'{OUT}/s3_d1b_full_gate_preds.json'))
    rows = [json.loads(l) for l in open(f'{EVAL}/logic_gate.jsonl')]
    saved = json.load(open(SAVED))['splits']
    correct, n = 0, 0
    by_label, by_depth, conf = {}, {}, {}
    for r in rows:
        p = ' '.join(preds[r['id']].strip().lower().split())
        g = ' '.join(r['answer'].strip().lower().split())
        h = int(p == g)
        correct += h
        n += 1
        c = by_label.setdefault(r['meta']['label'], [0, 0]); c[0] += h; c[1] += 1
        d = by_depth.setdefault(str(r['meta']['depth']), [0, 0]); d[0] += h; d[1] += 1
        cc = conf.setdefault(g, {}); cc[p] = cc.get(p, 0) + 1
    sv = saved['logic_gate']
    R['independent_tally_logic_gate'] = dict(correct=correct, n=n, by_label=by_label, by_depth=by_depth, confusion_gold_to_pred=conf)
    R['matches_saved'] = dict(
        correct=correct == sv['correct'], n=n == sv['n'],
        by_label=all(by_label[k] == [v['correct'], v['n']] for k, v in sv['by_label'].items()),
        by_level=all(by_depth[k] == [v['correct'], v['n']] for k, v in sv['by_level'].items()),
        confusion=all(conf[g].get(p, 0) == c for g, h in sv['answer_words']['logic_fc'].items() for p, c in h.items()))
    # z-scores of every saved number vs the best label-independent baseline measured in s1 (constant / position predictors)
    s1 = json.load(open(f'{OUT}/s1_controls.json'))
    z = {}
    for name, v in sv.items() if False else saved.items():
        k, nn = v['correct'], v['n']
        ctl = s1['controls'][name]
        base = {b: ctl[b]['correct'] for b in ('const_true', 'const_false', 'const_unknown', 'pos1_first_option', 'pos2_second_option', 'pos3_third_option')}
        best = max(base.values())
        p0 = 1 / 3
        sd = math.sqrt(nn * p0 * (1 - p0))
        z[name] = dict(correct=k, n=nn, acc=round(100 * k / nn, 2), best_baseline_correct=best, best_baseline_acc=round(100 * best / nn, 2),
                       z_vs_one_third=round((k - nn * p0) / sd, 2), z_vs_best_baseline_as_if_p=round((k - best) / sd, 2),
                       predicted_marginals={p: sum(h.get(p, 0) for h in v['answer_words'][next(iter(v['answer_words']))].values())
                                            for p in ('true', 'false', 'unknown')})
    R['saved_D1b_3500_vs_baselines'] = z
    json.dump(R, open(f'{OUT}/s6_independent_tally.json', 'w'), indent=1)
    print(json.dumps(R['matches_saved']))
    for k, v in z.items():
        print(k, v)


if __name__ == '__main__':
    main()
