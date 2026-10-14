"""python run_extra.py TAG: forward passes on the content-free edits (conds_extra.pkl) -> res/extra_TAG.pkl"""
import pickle, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
from probelib import *
from run_probe import CK
tag = sys.argv[1]
E = pickle.load(open(f'{OUT}/conds_extra.pkl', 'rb'))
m = load_model(CK[tag], 'cpu')
res = {}
for name, rows in E.items():
    t = time.time()
    res[name] = forward(m, rows)
    res[name]['ids'] = [r['id'] for r in rows]
    print(f'{tag} {name} n={len(rows)} {time.time() - t:.1f}s', flush=True)
pickle.dump(res, open(f'{OUT}/res/extra_{tag}.pkl', 'wb'))
