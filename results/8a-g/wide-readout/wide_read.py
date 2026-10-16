# Read-only: score the Modal WIDE run (arm B2 10MW, seed 400) from its RESULT.json.
# pooled-5 = correct / n over the five dev splits; blocks = unweighted mean of per-family pooled-5 (13 calculator families, the other 21).
import json, sys
S = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
C13 = 'arith_bare backward_solve chain_ops story_addsub story_chain3 chain_story2 var_chain div_exact table_calc distance_units compare_numbers state_update percent_rate'.split()
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'B2-full/RESULT.json'))
fe = d['final_eval']
fam = {}
for k in S:
    for name, v in fe[k]['by_family'].items():
        c, n = fam.get(name, (0, 0)); fam[name] = (c + v['correct'], n + v['n'])
other = sorted(f for f in fam if f not in C13)
def block(names):
    return sum(100.0 * fam[f][0] / fam[f][1] for f in names) / len(names), sum(fam[f][1] - fam[f][0] for f in names), sum(fam[f][1] for f in names)
c = sum(fe[k]['correct'] for k in S); n = sum(fe[k]['n'] for k in S)
print('steps', d['steps'], 'status', d['status'], 'params', d['n_params'])
print('pooled5 %.3f (%d/%d) errors %d' % (100.0 * c / n, c, n, n - c))
print('chain5 intact', d['chain5']['intact']['exact'])
for name, names in (('21 non-calculator', other), ('13 calculator', C13)):
    m, e, r = block(names); print('%s block: mean %.2f, errors %d of %d rows' % (name, m, e, r))
print('splits', {k: round(fe[k]['exact'], 2) for k in S})
