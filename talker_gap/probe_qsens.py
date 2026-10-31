"""Question-sensitivity probe (DIAGNOSIS.md claim 2): for pairs of SHORT-ANSWER rows that share a passage and have
different gold spans, how often does a trained arm predict the identical span? PR #37 copytalk: 59% on unseen kinds, 0% practised."""
import json, sys, itertools, collections
import numpy as np, torch
sys.path.insert(0, '.')
import run_arm as R
from models import Arm
arm, seed = sys.argv[1], sys.argv[2]
dev = torch.device('cpu')
model = Arm(arm); model.load_state_dict(torch.load(f'results/{arm}_s{seed}/model.pt')); model.eval()
out = {}
for split in ('dev', 'practised'):
    d = R.load_split('/Users/ben-hannan/talker_gap_cache', split)
    mode, S, E = R.predict(model, d, dev)
    by = collections.defaultdict(list)
    for i, r in enumerate(d['rows']):
        if r['type'] == 'short_answer' and r['gold_words'] is not None:
            by[r['passage']].append(i)
    pairs = same = 0
    for idx in by.values():
        for i, j in itertools.combinations(idx, 2):
            if d['rows'][i]['gold_words'] != d['rows'][j]['gold_words']:
                pairs += 1
                same += int(S[i] == S[j] and E[i] == E[j] and S[i] >= 0)
    out[split] = dict(pairs=pairs, identical=same, rate=round(100 * same / max(pairs, 1), 2))
print(arm, seed, json.dumps(out))
json.dump(out, open(f'results/{arm}_s{seed}/qsens.json', 'w'))
