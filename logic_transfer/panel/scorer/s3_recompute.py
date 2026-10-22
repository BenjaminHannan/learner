"""Scorer audit, part 3+4: recompute with a real checkpoint (ONE checkpoint, ONE thread, batch <= 128), keep predictions.

  PYTHONPATH=<worktree> python s3_recompute.py --tag d1b --ckpt <path> [--n 400] [--full] [--bs-sweep]

Writes s3_<tag>.json (+ s3_<tag>_preds.json with per-row predictions on the subset).
  1. score.analyze() on the fixed subset twice (determinism), and my own decode (state + talk(return_modes=True)) -> same predictions?
  2. mode head choice (NUM/WORD/GEN) per row, where the WORD pointer lands (option 1/2/3 of the suffix, label word in text, other word, out of range),
     hit rate per mode, mean softmax mass of the word pointer on the gold word set (training lword NLL) and mean mode CE (training lmode).
  3. batch-size / order sensitivity of the predictions on the subset (bs 1, 16, 64, 128 sorted-by-length vs. reversed file order).
  4. --full: score.analyze on the whole logic_gate file -> compare with the saved score.json cell by cell.
"""
import argparse
import collections
import json
import math
import time

import numpy as np
import torch

torch.set_num_threads(1)
from common import *          # noqa
from custom_io import evalx
from custom_io.data import Dataset, collate, to_device, word_spans
from custom_io.models import load_model
from custom_io.models import progparse as pp
from logic_transfer import score as S

DEV = torch.device('cpu')


@torch.no_grad()
def my_decode(model, rows, bs=128, order=None, detail=False):
    """Same loop as evalx.evaluate (length-sorted, stable) but calls state()+talk(return_modes=True); optionally keeps the heads' raw outputs."""
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    order = order if order is not None else sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    preds, modes, extra = [None] * len(rows), [None] * len(rows), [None] * len(rows)
    for s in range(0, len(order), bs):
        ids = order[s:s + bs]
        b = to_device(collate([ds[i] for i in ids]), DEV)
        st = model.state(b)
        out, md = model.talk(st, b, return_modes=True)
        lmode, lword = st[4].float(), st[5].float()
        for k, i in enumerate(ids):
            preds[i], modes[i] = out[k], md[k]
            if detail:
                extra[i] = dict(lmode=lmode[k].tolist(), lword=lword[k].tolist())
    return preds, modes, extra


def landing(row, w, mode_chosen):
    sp = word_spans(row['prompt'])[:pp.W_MAX]
    nt = len(word_spans(row['prompt']))
    if w >= len(sp):
        return 'out_of_range'
    txt = row['prompt'][sp[w][0]:sp[w][1]].lower()
    if w >= nt - 7 and w <= nt - 1:
        return {nt - 6: 'suffix_option1', nt - 4: 'suffix_option2', nt - 2: 'suffix_option3'}.get(w, 'suffix_punct')
    if txt in WORDS3:
        return 'label_word_in_question_text'
    return 'other_word'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--n', type=int, default=400)
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--bs-sweep', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    R = {'tag': a.tag, 'ckpt': a.ckpt, 'threads': torch.get_num_threads(), 'torch': torch.__version__}
    model = load_model(a.ckpt, 'cpu')
    rows_all = load('logic_gate', keep=None)
    sub = evalx.subsample(rows_all, a.n)               # the project's own even-spread subsample
    R['subset'] = dict(n=len(sub), first_id=sub[0]['id'], last_id=sub[-1]['id'], labels=dict(collections.Counter(r['answer'] for r in sub)),
                       levels=dict(collections.Counter(r['level'] for r in sub)))
    # --- 1. score.analyze twice
    t = time.time()
    o1, p1 = S.analyze(model, sub, 128, logic=True)
    R['t_analyze_s'] = round(time.time() - t, 1)
    o2, p2 = S.analyze(model, sub, 128, logic=True)
    R['analyze_run1_correct'] = o1['correct']
    R['analyze_rerun_identical_json'] = json.dumps(o1, sort_keys=True) == json.dumps(o2, sort_keys=True)
    R['analyze_rerun_identical_preds'] = p1 == p2
    R['analyze_subset'] = {k: o1[k] for k in ('correct', 'n', 'exact', 'by_level', 'by_label', 'by_depth', 'by_depth_label', 'answer_words', 'noop_round1')}
    # --- 2. own decode with modes
    preds, modes, extra = my_decode(model, sub, 128, detail=True)
    R['own_decode_equals_analyze_preds'] = all(preds[i] == p1[r['id']] for i, r in enumerate(sub))
    R['own_decode_n_diff'] = sum(preds[i] != p1[r['id']] for i, r in enumerate(sub))
    hit = [int(evalx.is_hit(p, r)) for p, r in zip(preds, sub)]
    mc = collections.Counter(modes)
    R['mode_counts_NUM0_WORD1_GEN2'] = [mc.get(k, 0) for k in range(3)]
    R['hit_by_mode'] = {str(k): [sum(h for h, m in zip(hit, modes) if m == k), mc.get(k, 0)] for k in range(3)}
    land = collections.Counter()
    land_hit = collections.Counter()
    pred_word = collections.Counter()
    nll_w, nll_m, mass_opts, gold_mass = [], [], [], []
    gen_texts = collections.Counter()
    for i, r in enumerate(sub):
        e = extra[i]
        sp = word_spans(r['prompt'])[:pp.W_MAX]
        wvalid = np.zeros(pp.W_MAX, bool)
        wvalid[:len(sp)] = True
        lw = np.array(e['lword'], dtype=np.float64)
        lw = np.where(wvalid, lw, -1e9)
        # argmax exactly as the decode (torch argmax over the fp32 logits incl. masked -1e9 entries)
        w = int(torch.tensor(e['lword']).argmax())
        if modes[i] == 1:
            lab = landing(r, w, 1)
            land[lab] += 1
            land_hit[lab] += hit[i]
            pred_word[preds[i].lower()] += 1
        elif modes[i] == 2:
            gen_texts[preds[i]] += 1
        p = np.exp(lw - lw.max())
        p /= p.sum()
        gold_set = list(pp.row_targets(r)['word'])
        nll_w.append(-math.log(max(p[gold_set].sum(), 1e-12)))
        nt = len(word_spans(r['prompt']))
        mass_opts.append(float(p[[nt - 6, nt - 4, nt - 2]].sum()))
        gold_mass.append(float(p[gold_set].sum()))
        lm = np.array(e['lmode'])
        lp = lm - lm.max()
        lp = lp - np.log(np.exp(lp).sum())
        nll_m.append(float(-lp[pp.row_targets(r)['mode']]))
    R['word_pointer_landing_among_WORD_mode_rows'] = dict(land)
    R['hit_by_landing'] = {k: [land_hit[k], land[k]] for k in land}
    R['predicted_word_among_WORD_mode_rows'] = dict(pred_word)
    R['gen_mode_prediction_texts_top'] = gen_texts.most_common(8)
    R['train_style_lword_NLL_mean(ln3=1.0986)'] = round(float(np.mean(nll_w)), 4)
    R['train_style_lmode_CE_mean'] = round(float(np.mean(nll_m)), 4)
    R['mean_pointer_mass_on_3_option_words'] = round(float(np.mean(mass_opts)), 4)
    R['mean_pointer_mass_on_gold_word_set'] = round(float(np.mean(gold_mass)), 4)
    R['accuracy_subset'] = round(sum(hit) / len(hit), 4)
    R['accuracy_subset_correct_n'] = [sum(hit), len(hit)]
    # --- 3. batch size / order sensitivity
    if a.bs_sweep:
        sw = {}
        base = preds
        for bs in (1, 16, 64, 128):
            t = time.time()
            pp_, _, _ = my_decode(model, sub, bs)
            sw[f'sorted_bs{bs}'] = dict(n_diff_vs_bs128_sorted=sum(x != y for x, y in zip(pp_, base)), correct=sum(evalx.is_hit(p, r) for p, r in zip(pp_, sub)),
                                        secs=round(time.time() - t, 1))
        pp_, _, _ = my_decode(model, sub, 128, order=list(range(len(sub))))
        sw['file_order_bs128'] = dict(n_diff_vs_bs128_sorted=sum(x != y for x, y in zip(pp_, base)), correct=sum(evalx.is_hit(p, r) for p, r in zip(pp_, sub)))
        pp_, _, _ = my_decode(model, sub, 128, order=list(range(len(sub)))[::-1])
        sw['reverse_file_order_bs128'] = dict(n_diff_vs_bs128_sorted=sum(x != y for x, y in zip(pp_, base)), correct=sum(evalx.is_hit(p, r) for p, r in zip(pp_, sub)))
        R['batch_sensitivity'] = sw
    json.dump({r['id']: p for r, p in zip(sub, preds)}, open(f'{OUT}/s3_{a.tag}_preds.json', 'w'))
    # --- 4. full logic_gate vs saved score.json
    if a.full:
        t = time.time()
        of, pf = S.analyze(model, rows_all, 128, logic=True)
        R['t_full_s'] = round(time.time() - t, 1)
        R['full_logic_gate'] = {k: of[k] for k in ('correct', 'n', 'exact', 'by_level', 'by_label', 'by_depth_label', 'answer_words', 'noop_round1')}
        saved = json.load(open(SAVED))['splits']['logic_gate']
        cmp = {k: (saved[k] == of[k]) for k in ('correct', 'n', 'exact', 'by_level', 'by_label', 'by_depth_label', 'answer_words', 'noop_round1', 'by_depth')
               if k in saved and k in of}
        R['full_vs_saved_score_json_identical'] = cmp
        json.dump(pf, open(f'{OUT}/s3_{a.tag}_full_gate_preds.json', 'w'))
        # my own full decode with modes
        pf2, mf, _ = my_decode(model, rows_all, 128)
        R['full_own_decode_equals_analyze'] = all(pf2[i] == pf[r['id']] for i, r in enumerate(rows_all))
        mcf = collections.Counter(mf)
        R['full_mode_counts_NUM0_WORD1_GEN2'] = [mcf.get(k, 0) for k in range(3)]
        hf = [int(evalx.is_hit(p, r)) for p, r in zip(pf2, rows_all)]
        R['full_hit_by_mode'] = {str(k): [sum(h for h, m in zip(hf, mf) if m == k), mcf.get(k, 0)] for k in range(3)}
    R['wall_s'] = round(time.time() - t0, 1)
    wjson(f's3_{a.tag}.json', R)
    print(json.dumps({k: R[k] for k in R if k not in ('analyze_subset', 'full_logic_gate')}, indent=1)[:6000])


if __name__ == '__main__':
    main()
