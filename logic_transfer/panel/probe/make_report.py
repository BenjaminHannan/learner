"""Run every analysis on whatever res/*.pkl exist -> analysis/summary.json  (offline; no model).  python make_report.py"""
import json, os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
from analyze import *

TAGS = [t for t in ('parent', 'D1b1500', 'D1b3500', 'L1000', 'P1000') if os.path.exists(f'{OUT}/res/{t}.pkl')]
TRAJ = [t for t in ('parent', 'D1_1500', 'D1b500', 'D1b1000', 'D1b1500', 'D1b2000', 'D1b2500', 'D1b3000', 'D1b3500', 'L1000', 'P1000') if os.path.exists(f'{OUT}/res/{t}.pkl')]
S = {'tags': TAGS, 'traj': TRAJ}

def brief1(tag, cond):
    o = item1(tag, cond)
    a = o['all']
    d = decompose(tag, cond)
    return dict(n=a['n'], acc=a['acc'], nll_gold=a['raw']['gold'], nll_gold_ci=a['raw']['gold_ci'], ln3=round(LN3, 5), gain_over_ln3=round(LN3 - a['raw']['gold'], 5),
                nll_shuffled=a['raw']['shuffled'], adv_over_shuffled=a['raw']['adv'], adv_ci=a['raw']['adv_ci'], perm_p=a.get('perm_p_one_sided'),
                mass_on_options=a['mass_on_options'], mode_ce=a['mode_ce'], pmax3=a['mean_pmax3'],
                by_label={l: dict(adv=o[f'label={l}']['raw']['adv'], gold=o[f'label={l}']['raw']['gold'], acc=o[f'label={l}']['acc']) for l in OPT if f'label={l}' in o},
                by_depth={k: dict(adv=v['raw']['adv'], gold=v['raw']['gold'], acc=v['acc']) for k, v in o.items() if k.startswith('depth=')},
                r2_word=d['r2_word'], r2_slot=d['r2_slot'], r2_gold=d['r2_gold'], r2_gold_ci=d['r2_gold_ci'], calibrated_gain_nats=d['calibrated_gain_over_ln3_nats_crossfit'],
                ncalls_nonzero=o['ncalls_nonzero'])

# ---- item 1
S['item1'] = {}
for tag in TAGS:
    R = res(tag)
    S['item1'][tag] = {c: brief1(tag, c) for c in R if not c.startswith('cf_') and c not in ('full_logic_test_deeper',) and not c.startswith('extra')}
# ---- item 2
S['item2'] = {}
for tag in ('D1b3500', 'parent'):
    if tag in TAGS:
        R = res(tag)
        S['item2'][tag] = {c: item2(tag, c, 500) for c in R if c in ('full_logic_gate', 'full_logic_dev', 'full_placebo_dev', 'gate600', 'plac600') and (c.startswith('full_') or tag != 'D1b3500')}
S['mode_wordfrac'] = {}
for tag in TAGS:
    R = res(tag)
    S['mode_wordfrac'][tag] = {c: round(float((R[c]['mode'] == 1).mean()), 4) for c in ('gate600', 'dev600', 'plac600')}
# ---- item 3
S['item3'] = {tag: {b: cf_tables(tag, b) for b in ('gate', 'plac')} for tag in TAGS}
# ---- item 4
S['item4'] = {}
if 'D1b3500' in TAGS:
    S['item4']['D1b3500'] = item4('D1b3500', [c for c in res('D1b3500') if c.startswith('full_')])
    if 'parent' in TAGS:
        S['item4']['parent_gate'] = item4('parent', ['full_logic_gate'])
S['trajectory'] = {}
for tag in TRAJ:
    R = res(tag)
    S['trajectory'][tag] = {}
    for c in ('gate600', 'dev600', 'plac600'):
        if c in R:
            F = Frame(tag, c)
            qn = np.array([r['meta']['query'].startswith('~') for r in F.rows])
            Ls = np.array([len(r['prompt']) for r in F.rows])
            q5 = np.searchsorted(np.quantile(Ls, [.2, .4, .6, .8]), Ls, side='right')
            mi_len = mi_report(F.word, q5, 100, 200)
            S['trajectory'][tag][c + '_shape'] = dict(P_true_given_nonneg=round(float((F.word[~qn] == 'true').mean()), 3), P_true_given_neg=round(float((F.word[qn] == 'true').mean()), 3),
                                                      P_false_given_nonneg=round(float((F.word[~qn] == 'false').mean()), 3), P_false_given_neg=round(float((F.word[qn] == 'false').mean()), 3),
                                                      MI_pred_vs_length_quintile_bits=mi_len['mi'], MI_excess=mi_len['excess'], p_perm=mi_len['p_perm'],
                                                      P_option_word=round(float(np.isin(F.word, OPT).mean()), 4))
            S['trajectory'][tag][c] = dict(n=F.n, acc=round(float(F.hit.mean()), 4), ci=[round(x, 4) for x in boot_ci(F.hit)], pred={w: round(float((F.word == w).mean()), 3) for w in OPT},
                                          gain_over_ln3=round(LN3 - float(-F.logm[np.arange(F.n), [OPT.index(y) for y in F.y]].mean()), 4))
# ---- item 5
p5 = f'{OUT}/res/item5_D1b3500.json'
if os.path.exists(p5):
    S['item5'] = json.load(open(p5))
jdump(S, 'summary')
print('wrote summary.json', TAGS, TRAJ)
