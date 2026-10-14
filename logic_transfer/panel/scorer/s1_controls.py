"""Scorer audit, part 1+2: row integrity, and controls that must come out exactly, pushed through the REAL
evalx.evaluate (length-sorted batching, pred reassignment, is_hit/norm, _tally) and the REAL score.analyze
(answer_words, by_label, by_depth, by_depth_label, noop_round1) using a fake model whose generate() is the predictor.
No checkpoint is loaded. One thread.

  PYTHONPATH=<worktree> python s1_controls.py   -> s1_controls.json
"""
import collections
import json
import random
import types

import torch
import torch.nn as nn

torch.set_num_threads(1)
from common import *          # noqa
from custom_io.data import CharVocab
from custom_io import evalx
from custom_io.data import word_spans
from custom_io.models import progparse as pp
W_MAX = pp.W_MAX
from custom_io.models.tool import Tool
from logic_transfer import score as S


class Fake(nn.Module):
    """generate() = fn(row); run() = all-NOOP so round1_noop works. Uses the real evaluate()/analyze() plumbing."""

    def __init__(self, fn):
        super().__init__()
        self.p = nn.Parameter(torch.zeros(1))
        self.vocab = CharVocab.build([])
        self.fn = fn

    def generate(self, batch, lesion=None):
        return [self.fn(r) for r in batch['rows']]

    def run(self, batch):
        B = len(batch['rows'])
        return {'steps': [(torch.zeros(B, 9),)]}


def tally(rows, fn, via='analyze'):
    m = Fake(fn)
    out, preds = S.analyze(m, rows, 128, logic=True)
    return out, preds


def main():
    R = {}
    # ------------------------------------------------------------------ A. row integrity
    integ = {}
    allrows = {n: load(n) for n in EVAL_FILES}
    for n, rows in allrows.items():
        ids = [r['id'] for r in rows]
        prm = [r['prompt'] for r in rows]
        lab = collections.Counter(r['answer'] for r in rows)
        d = dict(n=len(rows), unique_ids=len(set(ids)), unique_prompts=len(set(prm)), labels=dict(lab),
                 answer_eq_meta_label=sum(r['answer'] == r['meta']['label'] for r in rows),
                 accepted_eq_answer_only=sum(r['accepted'] == [r['answer']] for r in rows),
                 level_eq_meta_depth=sum(r['level'] == (r['meta'].get('depth') or 0) for r in rows),
                 depth_none=sum(r['meta'].get('depth') is None for r in rows),
                 families=dict(collections.Counter(r['family'] for r in rows)),
                 answer_not_in_3words=sum(r['answer'] not in WORDS3 for r in rows),
                 steps=dict(collections.Counter(json.dumps(r['steps']) for r in rows)))
        so = [suffix_order(r['prompt']) for r in rows]
        d['suffix_parsed'] = sum(s is not None for s in so)
        d['suffix_is_permutation'] = sum(s is not None and sorted(s) == sorted(WORDS3) for s in so)
        d['answer_in_suffix'] = sum(s is not None and r['answer'] in s for s, r in zip(so, rows))
        # gold position in suffix
        pos = collections.Counter(s.index(r['answer']) for s, r in zip(so, rows) if s)
        d['gold_position_counts'] = {str(k + 1): v for k, v in sorted(pos.items())}
        # per-label x position
        pl = collections.defaultdict(collections.Counter)
        for s, r in zip(so, rows):
            pl[r['answer']][s.index(r['answer'])] += 1
        d['gold_position_by_label'] = {l: {str(k + 1): v for k, v in sorted(c.items())} for l, c in pl.items()}
        # word window
        nw = [len(word_spans(p)) for p in prm]
        d['max_word_tokens'] = max(nw)
        d['rows_over_64_word_tokens'] = sum(x > 64 for x in nw)
        d['mean_word_tokens'] = round(sum(nw) / len(nw), 2)
        tg = [pp.row_targets(r) for r in rows]
        d['train_mode_NUM_WORD_GEN'] = [sum(t['mode'] == k for t in tg) for k in range(3)]
        d['rows_with_prog'] = sum(bool(t['prog']) for t in tg)
        # answer word occurrences outside the suffix (question text), case-insensitive whole word
        def n_out(r):
            body = SUFFIX_RE.sub('', r['prompt'])
            return sum(1 for s, e in word_spans(body) if body[s:e].lower() == r['answer'])
        c_out = collections.Counter(n_out(r) for r in rows)
        d['gold_word_occurrences_in_question_text'] = {str(k): v for k, v in sorted(c_out.items())}
        # any of the three words (any label) in the question text
        def any_out(r):
            body = SUFFIX_RE.sub('', r['prompt'])
            return [body[s:e].lower() for s, e in word_spans(body) if body[s:e].lower() in WORDS3]
        ao = [any_out(r) for r in rows]
        d['rows_with_any_label_word_in_question_text'] = sum(bool(a) for a in ao)
        d['rows_where_question_text_words_include_all_three'] = sum(set(a) == set(WORDS3) for a in ao)
        integ[n] = d
    R['integrity'] = integ

    # ------------------------------------------------------------------ B. normalisation / substring behaviour of is_hit
    row = dict(accepted=['false'])
    probes = ['false', 'False', ' FALSE ', 'false\n', 'fal se', 'falsee', 'fals', 'untrue', 'false true', 'not false', 'unknown', '', 'false.']
    R['is_hit_probes'] = {repr(p): bool(evalx.is_hit(p, row)) for p in probes}

    # ------------------------------------------------------------------ C. controls through the real pipeline
    ctl = {}
    rng = random.Random(12345)
    order = lambda r: suffix_order(r['prompt'])
    preds = {
        'oracle_gold': lambda r: r['answer'],
        'oracle_gold_messy_case_ws': lambda r: ('  ' + r['answer'].upper() + ' ') if hash(r['id']) % 2 else r['answer'].capitalize(),
        'const_true': lambda r: 'true', 'const_false': lambda r: 'false', 'const_unknown': lambda r: 'unknown',
        'pos1_first_option': lambda r: order(r)[0], 'pos2_second_option': lambda r: order(r)[1], 'pos3_third_option': lambda r: order(r)[2],
        'random3_seed': None,
        'wrong_always_other_word': lambda r: {'true': 'false', 'false': 'unknown', 'unknown': 'true'}[r['answer']],
    }
    for n, rows in allrows.items():
        ctl[n] = {}
        nrows = len(rows)
        lab = collections.Counter(r['answer'] for r in rows)
        so = [order(r) for r in rows]
        posc = [collections.Counter(s.index(r['answer']) for s, r in zip(so, rows))[k] for k in range(3)]
        expect = {'oracle_gold': nrows, 'oracle_gold_messy_case_ws': nrows, 'const_true': lab['true'], 'const_false': lab['false'],
                  'const_unknown': lab['unknown'], 'pos1_first_option': posc[0], 'pos2_second_option': posc[1],
                  'pos3_third_option': posc[2], 'wrong_always_other_word': 0}
        for k, fn in preds.items():
            if k == 'random3_seed':
                accs = []
                for seed in range(20):
                    rr = random.Random(seed)
                    cache = {r['id']: rr.choice(WORDS3) for r in rows}
                    out, _ = tally(rows, lambda r, c=cache: c[r['id']])
                    accs.append(out['correct'])
                ctl[n][k] = dict(mean_correct=sum(accs) / len(accs), min=min(accs), max=max(accs), n=nrows, expected=nrows / 3,
                                 sd_binomial=round((nrows * (1 / 3) * (2 / 3)) ** 0.5, 2))
                continue
            out, pr = tally(rows, fn)
            # reconciliation
            chk = dict(correct=out['correct'], n=out['n'], expected=expect[k], match=out['correct'] == expect[k])
            chk['by_label_sum_correct'] = sum(v['correct'] for v in out['by_label'].values())
            chk['by_label_sum_n'] = sum(v['n'] for v in out['by_label'].values())
            chk['by_level_sum_correct'] = sum(v['correct'] for v in out['by_level'].values())
            chk['by_level_sum_n'] = sum(v['n'] for v in out['by_level'].values())
            chk['by_depth_sum_n'] = sum(v['n'] for v in out['by_depth'].values())
            chk['by_depth_label_sum_correct'] = sum(c['correct'] for d in out['by_depth_label'].values() for c in d.values())
            chk['by_depth_label_sum_n'] = sum(c['n'] for d in out['by_depth_label'].values() for c in d.values())
            aw = out['answer_words'][rows[0]['family']]
            chk['answer_words_total'] = sum(sum(h.values()) for h in aw.values())
            chk['answer_words_diag'] = sum(h.get(g, 0) for g, h in aw.items())
            chk['answer_words_gold_totals'] = {g: sum(h.values()) for g, h in aw.items()}
            if k.startswith('const_'):
                w = k.split('_')[1]
                chk['answer_words_pred_col_only'] = {g: {p: c for p, c in h.items()} for g, h in aw.items()}
            chk['noop_round1'] = out['noop_round1']
            ctl[n][k] = chk
    R['controls'] = ctl

    # ------------------------------------------------------------------ D. pointer-position predictors through the REAL Tool.answers decode
    dummy = types.SimpleNamespace(vocab=CharVocab.build([]))
    ptr = {}
    for n, rows in allrows.items():
        nW = [min(len(word_spans(r['prompt'])), W_MAX) for r in rows]
        res_end, res_start = {}, {}
        for j in range(1, 14):         # j-th word token from the end of the prompt (1 = ')' , 2 = third option, 4 = second, 6 = first)
            w = [max(x - j, 0) for x in nW]
            outs, modes = Tool.answers(dummy, [[] for _ in rows], [1] * len(rows), w, rows)
            res_end[j] = sum(evalx.is_hit(o, r) for o, r in zip(outs, rows))
        for k in range(0, 14):         # k-th word token from the start
            outs, modes = Tool.answers(dummy, [[] for _ in rows], [1] * len(rows), [k] * len(rows), rows)
            res_start[k] = sum(evalx.is_hit(o, r) for o, r in zip(outs, rows))
        # all-GEN / all-NUM(span absent) with empty text -> never right
        outs, _ = Tool.answers(dummy, [[] for _ in rows], [2] * len(rows), [0] * len(rows), rows)
        ptr[n] = dict(n=len(rows), from_end={str(j): v for j, v in res_end.items()}, from_start={str(k): v for k, v in res_start.items()},
                      gen_mode_empty_text_correct=sum(evalx.is_hit(o, r) for o, r in zip(outs, rows)))
        # oracle in WORD mode with the real decode: pointer at the suffix word equal to the answer
        outs = []
        for r in rows:
            sp = word_spans(r['prompt'])[:W_MAX]
            idx = [i for i, (s, e) in enumerate(sp) if r['prompt'][s:e].lower() == r['answer']]
            outs.append(idx)
        # (a) oracle pointer = LAST occurrence (suffix), (b) FIRST occurrence (question text if there)
        for tag, pick in (('oracle_ptr_last_occurrence', lambda ix: ix[-1]), ('oracle_ptr_first_occurrence', lambda ix: ix[0])):
            w = [pick(ix) if ix else 0 for ix in outs]
            o2, _ = Tool.answers(dummy, [[] for _ in rows], [1] * len(rows), w, rows)
            ptr[n][tag] = sum(evalx.is_hit(o, r) for o, r in zip(o2, rows))
        ptr[n]['rows_with_no_occurrence_in_first_64_tokens'] = sum(not ix for ix in outs)
        ptr[n]['rows_with_multiple_occurrences'] = sum(len(ix) > 1 for ix in outs)
    R['pointer_position_predictors'] = ptr
    wjson('s1_controls.json', R)
    print(json.dumps({'ok': True}))


if __name__ == '__main__':
    main()
