"""Sealed check, step 2 (run once): score every trained arm on the four eval sets and TEST kinds. Nothing is tuned on these."""
import sys, json, torch
sys.path.insert(0, '.')
import common as C, run_arm as R
from models import Arm
CACHE = '/Users/ben-hannan/talker_gap_cache/sealed'
SETS = ['FRESH-EN-R3', 'GEN-HELDOUT-R4', 'NEW-KINDS-R5', 'NEW-KINDS2-R6', 'TEST']
RUNS = [('b0', 0), ('b0', 1), ('b0', 2), ('b0_nothinker', 0), ('b0_nothinker', 1), ('b0_nothinker', 2), ('p0', 0)]
data = {s: R.load_split(CACHE, s) for s in SETS}
hits = {}
for arm, seed in RUNS:
    m = Arm(arm); m.load_state_dict(torch.load(f'results/{arm}_s{seed}/model.pt')); m.eval()
    for s in SETS:
        d = data[s]; mode, S, E = R.predict(m, d, torch.device('cpu'))
        hits[(arm, seed, s)] = [int(C.is_hit(R.pred_string(r, int(mode[i]), int(S[i]), int(E[i])), r['accepted'])) for i, r in enumerate(d['rows'])]
def em(h, rows, f): 
    idx = [i for i, r in enumerate(rows) if f(r)]; return 100 * sum(h[i] for i in idx) / len(idx), len(idx)
short = lambda r: r['type'] == 'short_answer'; yn = lambda r: r['type'] != 'short_answer'; hard = C.hard_row
res = {}
for arm, seed in RUNS:
    row = {}
    for s in SETS:
        h = hits[(arm, seed, s)]; rows = data[s]['rows']
        row[s] = dict(short=round(em(h, rows, short)[0], 2), yesno=round(em(h, rows, yn)[0], 2), hard=round(em(h, rows, hard)[0], 2), n_short=em(h, rows, short)[1], n_hard=em(h, rows, hard)[1])
    # pooled R5+R6
    rows = data['NEW-KINDS-R5']['rows'] + data['NEW-KINDS2-R6']['rows']; h = hits[(arm, seed, 'NEW-KINDS-R5')] + hits[(arm, seed, 'NEW-KINDS2-R6')]
    row['R5+R6'] = dict(short=round(em(h, rows, short)[0], 2), yesno=round(em(h, rows, yn)[0], 2), hard=round(em(h, rows, hard)[0], 2), n_short=em(h, rows, short)[1], n_hard=em(h, rows, hard)[1])
    res[f'{arm}_s{seed}'] = row
boot = {}
def pooled(arm, seed): return hits[(arm, seed, 'NEW-KINDS-R5')] + hits[(arm, seed, 'NEW-KINDS2-R6')]
prow = data['NEW-KINDS-R5']['rows'] + data['NEW-KINDS2-R6']['rows']
sidx = [i for i, r in enumerate(prow) if short(r)]
for seed in (0, 1, 2):
    a, b = pooled('b0', seed), pooled('b0_nothinker', seed)
    boot[f'R5+R6 short: b0 - b0_nothinker seed{seed}'] = [round(v, 2) for v in C.paired_bootstrap([a[i] for i in sidx], [b[i] for i in sidx])]
a, b = pooled('b0', 0), pooled('p0', 0)
boot['R5+R6 short: b0 - p0 seed0'] = [round(v, 2) for v in C.paired_bootstrap([a[i] for i in sidx], [b[i] for i in sidx])]
tsi = [i for i, r in enumerate(data['TEST']['rows']) if short(r)]
for seed in (0, 1, 2):
    a, b = hits[('b0', seed, 'TEST')], hits[('b0_nothinker', seed, 'TEST')]
    boot[f'TEST short: b0 - b0_nothinker seed{seed}'] = [round(v, 2) for v in C.paired_bootstrap([a[i] for i in tsi], [b[i] for i in tsi])]
json.dump(dict(results=res, bootstrap=boot), open('results/sealed_results.json', 'w'), indent=1)
json.dump({f'{k[0]}_s{k[1]}|{k[2]}': v for k, v in hits.items()}, open('results/sealed_hits.json', 'w'))
for k, v in res.items():
    print(k, {s: (v[s]['short'], v[s]['hard']) for s in v})
for k, v in boot.items(): print(k, v)
