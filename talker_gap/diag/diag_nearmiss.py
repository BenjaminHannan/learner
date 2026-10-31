"""Near-miss count on spent outside sets R3-R6 (never FRESH-R7). See DIAG_PLAN.md addendum."""
import json, os, sys
import numpy as np, torch
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import common as C, run_t as RT, seal_eval_t as SE
def ed(a, b):
    p = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        q = [i]
        for j, y in enumerate(b, 1):
            q.append(min(p[j] + 1, q[j - 1] + 1, p[j - 1] + (x != y)))
        p = q
    return p[-1]
out = {}
for arm in ('t1', 't2'):
    ck = torch.load(os.path.join(HERE, 'results', f'{arm}_s0', 'model.pt'), map_location='cpu')
    itos = ck['itos']; stoi = {c: i for i, c in enumerate(itos)}
    m = RT.TArm(arm, len(itos)); m.load_state_dict(ck['state_dict']); m.eval()
    tot = {'wrong': 0, 'near': 0, 'contains': 0, 'hits': 0, 'n': 0}
    for split in ('FRESH-EN-R3', 'GEN-HELDOUT-R4', 'NEW-KINDS-R5', 'NEW-KINDS2-R6'):
        d = RT.prep(RT.load_split(SE.SEALED, split, evaluate=True), stoi, RT.MAX_TGT, with_target=False)
        gens = RT.predict(m, d, torch.device('cpu'), itos)
        ap, hits, _ = RT.score(d['rows'], gens)
        for a, h, r in zip(ap, hits, d['rows']):
            if r['type'] != 'short_answer':
                continue
            tot['n'] += 1; tot['hits'] += int(h)
            if h:
                continue
            tot['wrong'] += 1
            a2 = C.en_norm(a); acc = [C.en_norm(x) for x in r['accepted']]
            if any(x and x in a2 for x in acc):
                tot['contains'] += 1; tot['near'] += 1
            elif any(ed(a2, x) <= 2 for x in acc):
                tot['near'] += 1
    tot['near_share_of_wrong'] = round(100 * tot['near'] / tot['wrong'], 1)
    tot['S_if_near_counted'] = round(100 * (tot['hits'] + tot['near']) / tot['n'], 1)
    tot['S'] = round(100 * tot['hits'] / tot['n'], 1)
    out[f'{arm}_s0'] = tot
    print(arm, tot, flush=True)
json.dump(out, open(os.path.join(HERE, 'diag', 'diag_nearmiss.json'), 'w'), indent=1)
