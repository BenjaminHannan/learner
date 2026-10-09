import sys, json, torch
sys.path.insert(0, '.')
import run_arm as R
from models import Arm
res = {}
for arm in ('b0', 'b0_nothinker'):
    model = Arm(arm); model.load_state_dict(torch.load(f'results/{arm}_s0/model.pt')); model.eval()
    d = R.load_split('/Users/ben-hannan/talker_gap_cache/pairs', 'pairs')
    mode, S, E = R.predict(model, d, torch.device('cpu'))
    rows = d['rows']; same = hit = 0
    for k in range(0, len(rows), 2):
        same += int(S[k] == S[k + 1] and E[k] == E[k + 1])
    for i, r in enumerate(rows):
        hit += int(S[i] == r['gold_words'][0] and E[i] == r['gold_words'][1])
    res[arm] = dict(pairs=len(rows) // 2, identical_span_pairs=same, span_exact_rows=f'{hit}/{len(rows)}')
print(json.dumps(res))
json.dump(res, open('results/pairs_qsens.json', 'w'))
