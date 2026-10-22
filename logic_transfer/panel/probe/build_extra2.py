import sys, pickle, collections
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
import cf
from probelib import OUT
C = pickle.load(open(f'{OUT}/conds.pkl', 'rb'))
E = {}
for tag, base in (('gate', C['cf_gate_base']), ('plac', C['cf_plac_base'])):
    built = collections.defaultdict(list)
    for r in base:
        b = cf.build_extra2(r)
        if b:
            for k, v in b.items():
                built[k] += v
    for k, v in built.items():
        E[f'cf_{tag}_{k}'] = v
pickle.dump(E, open(f'{OUT}/conds_extra2.pkl', 'wb'))
print({k: (len(v), dict(collections.Counter(x['exp'] for x in v))) for k, v in E.items()})
for k, v in E.items():
    print(k, v[0]['prompt'], '|', v[0]['exp'])
