"""D1b-3500 (or any checkpoint) on ALL six logic/placebo eval files, one pass each, one thread: which talker mode the mode head picks,
where the WORD pointer lands, how much pointer mass sits on the 3 option words and on the gold word set (= the training lword NLL),
whether the free run writes any calculator call (the training target for these rows is NOOP at every round), and hit rate per mode.

  PYTHONPATH=<worktree> python s7_modes_all.py --ckpt <path> --tag d1b
"""
import argparse
import collections
import json
import math

import numpy as np
import torch

torch.set_num_threads(1)
from common import *          # noqa
from custom_io import evalx
from custom_io.data import Dataset, collate, to_device, word_spans
from custom_io.models import load_model
from custom_io.models import progparse as pp
from s3_recompute import landing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--tag', required=True)
    a = ap.parse_args()
    model = load_model(a.ckpt, 'cpu').eval()
    R = {'ckpt': a.ckpt}
    for name in EVAL_FILES:
        rows = load(name, keep=None)
        ds = Dataset(rows, model.vocab, strict=False)
        order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
        modes, preds, hits = [0] * len(rows), [None] * len(rows), [0] * len(rows)
        land = collections.Counter(); land_hit = collections.Counter()
        nll_w, nll_m, mass3, massg, ncall, ops_nonnoop = [], [], [], [], 0, 0
        rounds_total = 0
        with torch.no_grad():
            for s in range(0, len(order), 128):
                ids = order[s:s + 128]
                b = to_device(collate([ds[i] for i in ids]), torch.device('cpu'))
                o = model.run(b)
                st = model.state_of(o)
                out, md = model.talk(st, b, return_modes=True)
                ncall += sum(1 for c in o['calls'] if c)
                for stp in o['steps']:
                    ops_nonnoop += int((stp[0].argmax(-1) != 0).sum()); rounds_total += len(ids)
                lw, lm = st[5].float(), st[4].float()
                for k, i in enumerate(ids):
                    r = rows[i]
                    preds[i], modes[i] = out[k], md[k]
                    hits[i] = int(evalx.is_hit(out[k], r))
                    w = int(lw[k].argmax())
                    if md[k] == 1:
                        l = landing(r, w, 1); land[l] += 1; land_hit[l] += hits[i]
                    sp = word_spans(r['prompt'])[:pp.W_MAX]
                    v = np.full(pp.W_MAX, -1e9); v[:len(sp)] = lw[k].numpy()[:len(sp)]
                    p = np.exp(v - v.max()); p /= p.sum()
                    gs = list(pp.row_targets(r)['word']); nt = len(word_spans(r['prompt']))
                    nll_w.append(-math.log(max(p[gs].sum(), 1e-12))); massg.append(float(p[gs].sum()))
                    mass3.append(float(p[[nt - 6, nt - 4, nt - 2]].sum()))
                    lpm = torch.log_softmax(lm[k], -1)
                    nll_m.append(float(-lpm[pp.row_targets(r)['mode']]))
        mc = collections.Counter(modes)
        R[name] = dict(n=len(rows), correct=sum(hits), mode_counts_NUM0_WORD1_GEN2=[mc.get(k, 0) for k in range(3)],
                       hit_by_mode={str(k): [sum(h for h, m in zip(hits, modes) if m == k), mc.get(k, 0)] for k in range(3)},
                       word_landing=dict(land), hit_by_landing={k: [land_hit[k], land[k]] for k in land},
                       rows_where_free_run_wrote_any_calculator_call=ncall,
                       share_of_round_ops_non_NOOP=round(ops_nonnoop / max(rounds_total, 1), 5),
                       mean_lword_NLL_gold_set=round(float(np.mean(nll_w)), 4), ln3=round(math.log(3), 4),
                       mean_lmode_CE=round(float(np.mean(nll_m)), 5), mean_pointer_mass_on_3_options=round(float(np.mean(mass3)), 4),
                       mean_pointer_mass_on_gold_set=round(float(np.mean(massg)), 4),
                       pred_word_counts=dict(collections.Counter(p.lower() for p in preds)))
        print(name, json.dumps({k: R[name][k] for k in ('n', 'correct', 'mode_counts_NUM0_WORD1_GEN2', 'word_landing', 'mean_lword_NLL_gold_set',
                                                       'mean_pointer_mass_on_3_options', 'rows_where_free_run_wrote_any_calculator_call')}), flush=True)
        if name == 'logic_gate':
            saved_preds = json.load(open(f'{OUT}/s3_{a.tag}_full_gate_preds.json')) if a.tag in ('d1b', 'parent') else None
            if saved_preds:
                R[name]['preds_equal_s3_full_gate_preds'] = all(preds[i] == saved_preds[r['id']] for i, r in enumerate(rows))
    wjson(f's7_modes_all_{a.tag}.json', R)


if __name__ == '__main__':
    main()
