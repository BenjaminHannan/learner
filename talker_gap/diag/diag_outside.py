"""Post-hoc diagnosis on spent outside sets (R3-R6). Never reads FRESH-R7. See DIAG_PLAN.md."""
import json, os, sys
import numpy as np, torch
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import common as C, run_t as RT, seal_eval_t as SE
SPLITS = ['FRESH-EN-R3', 'GEN-HELDOUT-R4', 'NEW-KINDS-R5', 'NEW-KINDS2-R6']
out = {}
for split in SPLITS:
    assert 'R7' not in split
    h, rows = SE.hits_b0('b0', 0, split)
    short = np.array([r['type'] == 'short_answer' for r in rows])
    out[f'{split}/b0_s0'] = {'S': round(100 * h[short].mean(), 2)}
    print(split, 'b0_s0 S', out[f'{split}/b0_s0']['S'], flush=True)
    for arm in ('t1', 't2'):
        ck = torch.load(os.path.join(HERE, 'results', f'{arm}_s0', 'model.pt'), map_location='cpu')
        itos = ck['itos']; stoi = {c: i for i, c in enumerate(itos)}
        d = RT.prep(RT.load_split(SE.SEALED, split, evaluate=True), stoi, RT.MAX_TGT, with_target=False)
        m = RT.TArm(arm, len(itos)); m.load_state_dict(ck['state_dict']); m.eval()
        gens = RT.predict(m, d, torch.device('cpu'), itos)
        ap, hits, echo = RT.score(d['rows'], gens)
        empty = np.array([C.en_norm(a) == '' for a in ap])
        notin = np.array([C.en_norm(a) != '' and C.en_norm(a) not in C.en_norm(r['prompt']) for a, r in zip(ap, d['rows'])])
        res = {'S': round(100 * hits[short].mean(), 2), 'echo_exact': round(100 * echo.mean(), 1),
               'empty_answer': round(100 * empty[short].mean(), 1), 'answer_not_in_prompt': round(100 * notin[short].mean(), 1),
               'mean_answer_len': round(float(np.mean([len(a.strip()) for a in np.array(ap)[short]])), 1),
               'mean_gold_len': round(float(np.mean([len(r['answer']) for r, s in zip(d['rows'], short) if s])), 1),
               'S_when_echo_ok': round(100 * hits[short & echo].mean(), 1) if (short & echo).any() else None,
               'S_when_echo_bad': round(100 * hits[short & ~echo].mean(), 1) if (short & ~echo).any() else None,
               'examples': [{'q': r['question'], 'gold': r['answer'], 'gen': g} for r, g, s in list(zip(d['rows'], gens, short))[:200:25] if s]}
        out[f'{split}/{arm}_s0'] = res
        print(split, arm, {k: v for k, v in res.items() if k != 'examples'}, flush=True)
json.dump(out, open(os.path.join(HERE, 'diag', 'diag_outside.json'), 'w'), indent=1)
print('wrote diag/diag_outside.json')
