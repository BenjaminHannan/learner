"""Blind recount 4 of the bm390 benchmark scores (LoCoMo, MMLU, GSM8K).

Written from scratch from the registered rules and the LoCoMo repo's own
evaluation code (task_eval/evaluation.py, task_eval/hf_llm_utils.py). It does
not read the first scorer's code or output. It prints and writes counts,
scores, ids and hashes only; no question, gold or reply text.

Run:
  <scratchpad>/venv/bin/python recount.py
Writes recount.json next to this file.
"""
import hashlib
import json
import math
import os
import re
import string
import sys
import types
from collections import Counter

import numpy as np
import regex
from nltk.stem import PorterStemmer

SCRATCH = "/tmp/claude-0/-home-user-learner/7058353c-6d6a-5191-a096-07082a743674/scratchpad"
RUNS = os.path.join(SCRATCH, "runs390all")
DATA = os.path.join(SCRATCH, "data390")
REPO = os.path.join(SCRATCH, "locomo_code", "repo")
OUT = os.path.dirname(os.path.abspath(__file__))

SEED = 390
N_BOOT = 10_000

# ---------------------------------------------------------------------------
# LoCoMo scoring, re-implemented line by line from task_eval/evaluation.py
# ---------------------------------------------------------------------------
ps = PorterStemmer()


def normalize_answer(s):
    s = s.replace(',', "")

    def remove_articles(text):
        return regex.sub(r'\b(a|an|the|and)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction, ground_truth):
    prediction_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    ground_truth_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def f1_multi(prediction, ground_truth):
    """evaluation.f1: split prediction and gold on commas, per-gold-part best match, mean."""
    predictions = [p.strip() for p in prediction.split(',')]
    ground_truths = [g.strip() for g in ground_truth.split(',')]
    return np.mean([max([f1_score(p, gt) for p in predictions]) for gt in ground_truths])


def score_item(category, output, gold):
    """evaluation.eval_question_answering, one item (prediction is a str, never a list)."""
    answer = str(gold)
    if category == 3:
        answer = answer.split(';')[0].strip()
    if category in [2, 3, 4]:
        return float(f1_score(output, answer))
    if category in [1]:
        return float(f1_multi(output, answer))
    if category in [5]:
        low = output.lower()
        return 1.0 if ('no information available' in low or 'not mentioned' in low) else 0.0
    raise ValueError(category)


def hf_clean(reply):
    """hf_llm_utils.get_hf_answers post-processing, non-category-5 branch."""
    answer = reply.replace('\\"', "'").strip()
    # The repo's filter `not w.strip().isspace()` never drops anything ('' .isspace() is False),
    # so this is simply "first line, stripped". Kept verbatim.
    answer = [w.strip() for w in answer.split('\n') if not w.strip().isspace()][0]
    answer = (answer.lower().replace('(a)', '').replace('(b)', '').replace('a)', '')
              .replace('b)', '').replace('answer:', '').strip())
    return answer


# ---------------------------------------------------------------------------
# MMLU letter picking (registered rule 3)
# ---------------------------------------------------------------------------
MMLU_PRIMARY = re.compile(r'(?i:answer is|answer|option)\s*[:\-]?\s*\(?([A-D])(?![A-Za-z])')
MMLU_FALLBACK = re.compile(r'(?<![A-Za-z])([A-D])(?![A-Za-z])')
# Sensitivity variants (not headline):
#   strict spacing: at most one space on each side of the optional ':'/'-'
MMLU_PRIMARY_STRICT = re.compile(r'(?i:answer is|answer|option) ?[:\-]? ?\(?([A-D])(?![A-Za-z])')
#   unicode letters count as "letters" for adjacency
MMLU_PRIMARY_UNI = regex.compile(r'(?i:answer is|answer|option)\s*[:\-]?\s*\(?([A-D])(?!\p{L})')
MMLU_FALLBACK_UNI = regex.compile(r'(?<!\p{L})([A-D])(?!\p{L})')


def mmlu_pick(reply, primary=MMLU_PRIMARY, fallback=MMLU_FALLBACK):
    m = primary.search(reply)
    if m:
        return m.group(1), 'primary'
    m = fallback.search(reply)
    if m:
        return m.group(1), 'fallback'
    return None, 'none'


# ---------------------------------------------------------------------------
# GSM8K number extraction (registered rule 4)
# ---------------------------------------------------------------------------
ANSWER_IS = re.compile(r'the answer is', re.IGNORECASE)
NUMBER = re.compile(r'-?\d[\d,]*(?:\.\d+)?|-?\.\d+')


def to_num(s):
    s = s.replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def gsm_pick(reply, fallback_if_no_number_after=False):
    hits = list(ANSWER_IS.finditer(reply))
    if hits:
        tail = reply[hits[-1].end():]
        m = NUMBER.search(tail)
        if m:
            return to_num(m.group(0)), 'after_phrase'
        if not fallback_if_no_number_after:
            return None, 'phrase_no_number'
    nums = NUMBER.findall(reply)
    if nums:
        return to_num(nums[-1]), ('last_number' if not hits else 'phrase_no_number_fallback')
    return None, 'no_number'


def num_eq(a, b):
    return a is not None and b is not None and abs(a - b) < 1e-9


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def read_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_scores(qids, scores):
    h = hashlib.sha256()
    for q in qids:
        h.update(('%s\t%.6f\n' % (q, scores[q])).encode())
    return h.hexdigest()


def r4(x):
    return None if x is None else round(float(x), 4)


def main():
    import nltk
    out = {'env': {'python': sys.version.split()[0], 'numpy': np.__version__, 'nltk': nltk.__version__,
                   'regex': regex.__version__},
           'inputs': {}, 'locomo': {}, 'mmlu': {}, 'gsm8k': {}, 'bootstrap': {}, 'checks': {}}

    # ---------------- LoCoMo ----------------
    locomo_path = os.path.join(DATA, 'locomo10.json')
    out['inputs']['locomo10.json'] = sha256_file(locomo_path)
    conv = json.load(open(locomo_path))
    gold = {}      # qid -> (category, gold)
    order = []     # data order: conversation order, then qa index
    for d in conv:
        for i, qa in enumerate(d['qa']):
            qid = '%s#%d' % (d['sample_id'], i)
            gold[qid] = (qa['category'], qa.get('answer'))
            order.append(qid)
    order14 = [q for q in order if gold[q][0] in (1, 2, 3, 4)]
    order5 = [q for q in order if gold[q][0] == 5]
    out['checks']['locomo_n_total'] = len(order)
    out['checks']['locomo_n_cat1_4'] = len(order14)
    out['checks']['locomo_cat_counts'] = {str(c): sum(1 for q in order if gold[q][0] == c) for c in range(1, 6)}
    out['checks']['locomo_cat1_4_missing_answer_field'] = sum(1 for q in order14 if gold[q][1] is None)
    out['checks']['locomo_cat1_4_int_gold'] = sum(1 for q in order14 if isinstance(gold[q][1], int))

    arm_files = {
        'T': ['locomo_T.jsonl'],
        'C': ['locomo_C.jsonl'],
        'L12': ['locomo_L12.jsonl'],
        'Q2': ['locomo_Q2.part%d.jsonl' % p for p in range(1, 6)],
    }
    per_item = {}
    per_item_r3 = {}
    for arm, files in arm_files.items():
        rows = []
        for fn in files:
            p = os.path.join(RUNS, fn)
            out['inputs'][fn] = sha256_file(p)
            rows += read_jsonl(p)
        qids = [r['qid'] for r in rows]
        chk = {
            'rows': len(rows),
            'unique_qids': len(set(qids)),
            'qids_equal_data': set(qids) == set(order),
            'category_field_mismatches': sum(1 for r in rows if r.get('category') != gold[r['qid']][0]),
            'multi_line_replies_cat1_4': 0,
            'empty_after_clean_cat1_4': 0,
        }
        assert chk['unique_qids'] == len(rows), arm
        byq = {r['qid']: r for r in rows}
        sc, sc_raw = {}, {}
        for q in order:
            cat, g = gold[q]
            reply = byq[q]['reply']
            cleaned = hf_clean(reply)
            if cat in (1, 2, 3, 4):
                if '\n' in reply.strip():
                    chk['multi_line_replies_cat1_4'] += 1
                if cleaned == '':
                    chk['empty_after_clean_cat1_4'] += 1
                sc[q] = score_item(cat, cleaned, g)
                sc_raw[q] = score_item(cat, reply, g)
            else:
                sc[q] = score_item(5, cleaned, None)
                sc_raw[q] = score_item(5, reply, None)
        per_item[arm] = sc
        per_item_r3[arm] = {q: round(v, 3) for q, v in sc.items()}
        res = {
            'n_cat1_4': len(order14),
            'headline_f1x100_cat1_4': r4(100 * np.mean([sc[q] for q in order14])),
            'per_category_f1x100': {},
            'per_category_n': {},
            'variant_repo_round3_headline': r4(100 * np.mean([per_item_r3[arm][q] for q in order14])),
            'variant_no_cleanup_headline': r4(100 * np.mean([sc_raw[q] for q in order14])),
            'cat5_repo_substring_rule_on_cleaned_reply': {
                'n': len(order5),
                'hits': int(sum(sc[q] for q in order5)),
                'pct': r4(100 * np.mean([sc[q] for q in order5])),
            },
            'cat5_repo_substring_rule_on_raw_reply_hits': int(sum(sc_raw[q] for q in order5)),
            'sha256_per_item_cat1_4': sha256_scores(order14, sc),
            'checks': chk,
        }
        for c in (1, 2, 3, 4):
            qs = [q for q in order14 if gold[q][0] == c]
            res['per_category_f1x100'][str(c)] = r4(100 * np.mean([sc[q] for q in qs]))
            res['per_category_n'][str(c)] = len(qs)
            res['variant_no_cleanup_per_category_' + str(c)] = r4(100 * np.mean([sc_raw[q] for q in qs]))
        out['locomo'][arm] = res

    # Cross-check: the re-implementation must agree with the repo's own functions.
    # evaluation.py imports bert_score at module level (unused for F1); stub it so the file imports.
    sys.modules.setdefault('bert_score', types.SimpleNamespace(score=None))
    sys.dont_write_bytecode = True  # do not write .pyc files into the repo checkout
    sys.path.insert(0, REPO)
    from task_eval import evaluation as repo_eval  # noqa: E402
    mism = 0
    total = 0
    for arm in arm_files:
        rows = []
        for fn in arm_files[arm]:
            rows += read_jsonl(os.path.join(RUNS, fn))
        qas = []
        for r in rows:
            cat, g = gold[r['qid']]
            qas.append({'qid': r['qid'], 'category': cat, 'answer': g if g is not None else '',
                        'evidence': [], 'pred': hf_clean(r['reply'])})
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            ems, _, _ = repo_eval.eval_question_answering(qas, eval_key='pred')
        for qa, e in zip(qas, ems):
            total += 1
            if abs(float(e) - per_item[arm][qa['qid']]) > 1e-12:
                mism += 1
    out['checks']['repo_eval_function_crosscheck'] = {'items_compared': total, 'mismatches': mism}

    # ---------------- Bootstrap (LoCoMo cat 1-4) ----------------
    n = len(order14)
    A = {arm: np.array([per_item[arm][q] for q in order14]) for arm in ('T', 'Q2', 'L12')}
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    boot = {}
    for arm in ('Q2', 'L12'):
        d_items = A[arm] - A['T']
        diffs = 100 * d_items[idx].mean(axis=1)
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        boot['%s-T' % arm] = {
            'point_f1x100': r4(100 * d_items.mean()),
            'ci95_lo': r4(lo), 'ci95_hi': r4(hi),
            'share_resamples_le_0': r4(float(np.mean(diffs <= 0))),
        }
    # Sensitivity: separate draws per comparison (Q2 first, then L12) from one rng(390).
    rng2 = np.random.default_rng(SEED)
    sens = {}
    for arm in ('Q2', 'L12'):
        idx2 = rng2.integers(0, n, size=(N_BOOT, n))
        diffs = 100 * (A[arm] - A['T'])[idx2].mean(axis=1)
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        sens['%s-T' % arm] = {'ci95_lo': r4(lo), 'ci95_hi': r4(hi)}
    # Sensitivity: rng.choice instead of rng.integers, one shared draw.
    rng3 = np.random.default_rng(SEED)
    idx3 = rng3.choice(n, size=(N_BOOT, n), replace=True)
    sens_choice_same = bool(np.array_equal(idx3, idx))
    # Sensitivity: items ordered by qid string instead of data order, one shared draw.
    order_s = sorted(order14)
    As = {arm: np.array([per_item[arm][q] for q in order_s]) for arm in ('T', 'Q2', 'L12')}
    idx4 = np.random.default_rng(SEED).integers(0, n, size=(N_BOOT, n))
    for arm in ('Q2', 'L12'):
        diffs = 100 * (As[arm] - As['T'])[idx4].mean(axis=1)
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        sens['%s-T_items_sorted_by_qid_string' % arm] = {'ci95_lo': r4(lo), 'ci95_hi': r4(hi)}
    out['bootstrap'] = {
        'n_items': n, 'n_resamples': N_BOOT, 'seed': SEED,
        'item_order': 'locomo10.json order (conversation, then qa index), categories 1-4 only',
        'resampling': 'one index matrix rng.integers(0,n,(10000,n)) shared by both comparisons',
        'results': boot,
        'sensitivity_separate_draws_per_comparison': sens,
        'sensitivity_rng_choice_gives_identical_indices': sens_choice_same,
    }

    # ---------------- MMLU ----------------
    mmlu_path = os.path.join(DATA, 'mmlu300.jsonl')
    out['inputs']['mmlu300.jsonl'] = sha256_file(mmlu_path)
    mg = {r['qid']: r['gold'] for r in read_jsonl(mmlu_path)}
    # gold cross-check against the arrow files (answer index -> letter)
    try:
        import pyarrow.ipc as ipc
        cache = {}
        agree = 0
        for qid, g in mg.items():
            _, subj, k = qid.split('/')
            if subj not in cache:
                cache[subj] = ipc.open_stream(open(os.path.join(DATA, 'mmlu', subj + '.arrow'), 'rb')).read_all()
            ans = cache[subj].column('answer')[int(k)].as_py()
            agree += int('ABCD'[ans] == g)
        out['checks']['mmlu_gold_matches_arrow_answer_index'] = '%d/%d' % (agree, len(mg))
    except Exception as e:  # pragma: no cover
        out['checks']['mmlu_gold_matches_arrow_answer_index'] = 'not checked: %s' % type(e).__name__
    for arm in ('T', 'Q2', 'L12'):
        fn = 'mmlu_%s.jsonl' % arm
        p = os.path.join(RUNS, fn)
        out['inputs'][fn] = sha256_file(p)
        rows = read_jsonl(p)
        assert len(rows) == 300 and set(r['qid'] for r in rows) == set(mg)
        right = 0
        how = Counter()
        right_strict = right_uni = 0
        none_strict = none_uni = 0
        per = {}
        for r in rows:
            letter, via = mmlu_pick(r['reply'])
            how[via] += 1
            ok = letter == mg[r['qid']]
            right += ok
            per[r['qid']] = int(ok)
            l2, v2 = mmlu_pick(r['reply'], MMLU_PRIMARY_STRICT, MMLU_FALLBACK)
            right_strict += (l2 == mg[r['qid']])
            none_strict += (v2 == 'none')
            l3, v3 = mmlu_pick(r['reply'], MMLU_PRIMARY_UNI, MMLU_FALLBACK_UNI)
            right_uni += (l3 == mg[r['qid']])
            none_uni += (v3 == 'none')
        out['mmlu'][arm] = {
            'right': right, 'n': len(rows), 'pct': r4(100 * right / len(rows)),
            'no_pickable_letter': how['none'],
            'picked_by_primary_pattern': how['primary'],
            'picked_by_fallback': how['fallback'],
            'variant_strict_spacing_right': right_strict, 'variant_strict_spacing_none': none_strict,
            'variant_unicode_letters_right': right_uni, 'variant_unicode_letters_none': none_uni,
            'sha256_per_item': sha256_scores(sorted(per), per),
        }

    # ---------------- GSM8K ----------------
    gsm_path = os.path.join(DATA, 'gsm8k300.jsonl')
    out['inputs']['gsm8k300.jsonl'] = sha256_file(gsm_path)
    gg_raw = {r['qid']: r['gold'] for r in read_jsonl(gsm_path)}
    # gold in gsm8k300.jsonl has no '####' (already the final answer); take the text after
    # the last '####' if present, else the whole string.
    gg = {q: to_num(g.split('####')[-1].strip()) for q, g in gg_raw.items()}
    out['checks']['gsm8k_gold_with_####'] = sum('####' in g for g in gg_raw.values())
    out['checks']['gsm8k_gold_unparseable'] = sum(v is None for v in gg.values())
    try:
        import pyarrow.parquet as pq
        t = pq.read_table(os.path.join(DATA, 'gsm8k_test.parquet')).column('answer').to_pylist()
        agree = 0
        for q, g in gg.items():
            k = int(q.split('/')[-1])
            agree += int(num_eq(to_num(t[k].split('####')[-1].strip()), g))
        out['checks']['gsm8k_gold_matches_parquet_after_####'] = '%d/%d' % (agree, len(gg))
    except Exception as e:  # pragma: no cover
        out['checks']['gsm8k_gold_matches_parquet_after_####'] = 'not checked: %s' % type(e).__name__
    for arm in ('T', 'Q2', 'L12'):
        fn = 'gsm8k_%s.jsonl' % arm
        p = os.path.join(RUNS, fn)
        out['inputs'][fn] = sha256_file(p)
        rows = read_jsonl(p)
        assert len(rows) == 300 and set(r['qid'] for r in rows) == set(gg)
        right = right_fb = 0
        how = Counter()
        per = {}
        for r in rows:
            v, via = gsm_pick(r['reply'])
            how[via] += 1
            ok = num_eq(v, gg[r['qid']])
            right += ok
            per[r['qid']] = int(ok)
            v2, _ = gsm_pick(r['reply'], fallback_if_no_number_after=True)
            right_fb += num_eq(v2, gg[r['qid']])
        out['gsm8k'][arm] = {
            'right': right, 'n': len(rows), 'pct': r4(100 * right / len(rows)),
            'extracted_after_last_answer_is': how['after_phrase'],
            'no_phrase_used_last_number': how['last_number'],
            'phrase_but_no_number_after': how['phrase_no_number'],
            'no_number_at_all': how['no_number'],
            'variant_fallback_to_last_number_when_phrase_has_no_number_right': right_fb,
            'sha256_per_item': sha256_scores(sorted(per), per),
        }

    out['per_item_locomo_f1'] = {arm: {q: round(per_item[arm][q], 6) for q in order} for arm in per_item}

    with open(os.path.join(OUT, 'recount.json'), 'w') as f:
        json.dump(out, f, indent=1, sort_keys=False)

    # console summary (numbers only)
    for arm in ('T', 'C', 'L12', 'Q2'):
        r = out['locomo'][arm]
        print('locomo', arm, r['headline_f1x100_cat1_4'], r['per_category_f1x100'],
              'r3', r['variant_repo_round3_headline'], 'raw', r['variant_no_cleanup_headline'],
              'cat5', r['cat5_repo_substring_rule_on_cleaned_reply'], r['checks'])
    print('crosscheck', out['checks'])
    print('bootstrap', json.dumps(out['bootstrap']))
    for arm in ('T', 'Q2', 'L12'):
        print('mmlu', arm, out['mmlu'][arm])
    for arm in ('T', 'Q2', 'L12'):
        print('gsm8k', arm, out['gsm8k'][arm])


if __name__ == '__main__':
    main()
