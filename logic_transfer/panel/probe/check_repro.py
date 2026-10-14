"""Decode reproduction: full logic_gate with my decode vs the stored scorer output (scoreL-*/out/score.json).  python check_repro.py TAG"""
import json, pickle, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
from probelib import *
from run_probe import CK
tag = sys.argv[1]
C = pickle.load(open(f'{OUT}/conds.pkl', 'rb'))
m = load_model(CK[tag], 'cpu')
rows = C['full_logic_gate']
f = forward(m, rows)
hit = sum(norm(p) == norm(r['answer']) for p, r in zip(f['pred'], rows))
stored = {'L1000': f'{SP}/lt2/jobs/scoreL-s200-L-s1-u1000/out/score.json', 'P1000': f'{SP}/lt2/jobs/scoreL-s200-P-s1-u1000/out/score.json'}[tag]
s = json.load(open(stored))['splits']['logic_gate']
out = dict(tag=tag, mine=[hit, len(rows)], stored=[s['correct'], s['n']], equal=(hit == s['correct']))
json.dump(out, open(f'{OUT}/res/repro_{tag}.json', 'w'))
print(out)
