#!/usr/bin/env python3
"""TASK D4: review TEACH profile and split_proposal.json (read-only on inputs).

Writes only under <DIAG>/D4_work/. Stdlib only. Run: python3 -I analyze_d4.py
Passage = source_text. Word = regex [a-z0-9']+ on lowercased text (teach_profile.py convention).
"""
import collections
import csv
import glob
import gzip
import json
import os
import re

D = '/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag'
TEACH = '/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz'
OUT = os.path.join(D, 'D4_work')
os.makedirs(OUT, exist_ok=True)
WORD = re.compile(r"[a-z0-9']+")


def words(s):
    return WORD.findall((s or '').lower())


def clean(a):
    return (a or '').strip().rstrip('.').strip()


def pct(vals, p):
    v = sorted(vals)
    if not v:
        return None
    k = (len(v) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return round(v[f] + (v[c] - v[f]) * (k - f), 2)


def mean(vals):
    return round(sum(vals) / len(vals), 3) if vals else None


def share(flags):
    return round(sum(1 for x in flags if x) / len(flags), 4) if flags else None


# ---------- load TEACH (stream, 171,940 rows) ----------
rows = []
with gzip.open(TEACH, 'rt') as f:
    for line in f:
        r = json.loads(line)
        ans = clean(r.get('canonical_answer'))
        src = r.get('source_text') or ''
        para = r.get('paraphrase') or ''
        q = r.get('question') or ''
        pw = set(words(src + ' ' + para + ' ' + q))
        aw = words(ans)
        rows.append({
            'id': r['id'], 'kind': r['kind'], 'typ': r['type'], 'src': src, 'para': para,
            'q': q, 'ans': ans, 'achars': len(ans), 'awords': len(aw),
            'sub_src_ci': bool(ans) and ans.lower() in src.lower(),
            'sub_src_cs': bool(ans) and ans in src,
            'sub_para_ci': bool(ans) and ans.lower() in para.lower(),
            'sub_q_ci': bool(ans) and ans.lower() in q.lower(),
            'novel': any(w not in pw for w in aw),
            'target': q.strip() + ' ' + ans,
        })


def summ(rs):
    n = len(rs)
    yn = [r for r in rs if r['typ'] == 'yes_no']
    sh = [r for r in rs if r['typ'] != 'yes_no']
    d = {'n': n, 'n_yes_no': len(yn), 'yn_share': round(len(yn) / n, 4) if n else None,
         'n_short': len(sh)}
    if sh:
        sc = [r['achars'] for r in sh]
        sw = [r['awords'] for r in sh]
        d.update({
            'short_words_mean': mean(sw), 'short_words_p50': pct(sw, 50), 'short_words_max': max(sw),
            'short_chars_mean': mean(sc), 'short_chars_p50': pct(sc, 50),
            'short_chars_p90': pct(sc, 90), 'short_chars_max': max(sc),
            'short_gt8chars_share': share([c > 8 for c in sc]),
            'short_sub_src_ci': share([r['sub_src_ci'] for r in sh]),
            'short_sub_src_cs': share([r['sub_src_cs'] for r in sh]),
            'short_sub_para_ci': share([r['sub_para_ci'] for r in sh]),
            'short_sub_q_ci': share([r['sub_q_ci'] for r in sh]),
            'short_novel_word_share': share([r['novel'] for r in sh]),
        })
    return d


# ---------- 1) per-kind and overall stats ----------
overall = summ(rows)
overall['typ_counts'] = dict(collections.Counter(r['typ'] for r in rows))
overall['n_empty_answer'] = sum(1 for r in rows if not r['ans'])
overall['yn_answer_values'] = dict(collections.Counter(r['ans'].lower() for r in rows if r['typ'] == 'yes_no'))
bykind = collections.defaultdict(list)
for r in rows:
    bykind[r['kind']].append(r)
kind_stats = {k: summ(v) for k, v in bykind.items()}
fields = ['kind'] + sorted({f for s in kind_stats.values() for f in s})
with open(os.path.join(OUT, 'per_kind.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for k in sorted(kind_stats):
        w.writerow(dict(kind=k, **kind_stats[k]))

# ---------- 2) split reconstruction and checks ----------
P = json.load(open(os.path.join(D, 'split_proposal.json')))
DEV, TEST = set(P['dev_kinds']), set(P['test_kinds'])
SLICE = [l.strip() for l in open(os.path.join(D, 'practised_slice_ids.txt')) if l.strip()]
SLICE_SET = set(SLICE)
dt_pass = {r['src'] for r in rows if r['kind'] in DEV or r['kind'] in TEST}
for r in rows:
    if r['kind'] in DEV:
        s = 'dev'
    elif r['kind'] in TEST:
        s = 'test'
    elif r['src'] in dt_pass:
        s = 'dropped_passage_overlap_with_dev_test'
    elif r['id'] in SLICE_SET:
        s = 'practised_slice'
    else:
        s = 'train'
    r['split'] = s

counts = collections.Counter(r['split'] for r in rows)
checks = []


def chk(name, ok, detail):
    checks.append({'check': name, 'result': 'PASS' if ok else 'FAIL', 'detail': detail})


ALLK = set(bykind)
chk('dev_test_kinds_disjoint', not (DEV & TEST), f'intersection={sorted(DEV & TEST)}')
chk('dev_test_kinds_exist_in_teach', (DEV | TEST) <= ALLK,
    f'dev={len(DEV)} test={len(TEST)} missing={sorted((DEV | TEST) - ALLK)}')
train_side_kinds = {r['kind'] for r in rows if r['split'] in ('train', 'practised_slice')}
chk('leave_kinds_out_train_side', not (train_side_kinds & (DEV | TEST)),
    f'train-side kinds ∩ dev/test kinds={sorted(train_side_kinds & (DEV | TEST))}; '
    f'n_train_side_kinds={len(train_side_kinds)}')
chk('dev_test_rows_only_in_dev_test',
    all((r['split'] == 'dev') == (r['kind'] in DEV) and (r['split'] == 'test') == (r['kind'] in TEST)
        for r in rows if r['kind'] in DEV | TEST),
    'every dev/test-kind row labelled dev/test and no other row is')
for k, v in P['per_split'].items():
    chk(f'reproduce_count_{k}', counts.get(k, 0) == v['rows'],
        f"reconstructed={counts.get(k, 0)} proposal={v['rows']}")

overall_yn = overall['yn_share']


def sp(label):
    rs = [r for r in rows if r['split'] == label]
    s = summ(rs)
    s['distinct_kinds'] = len({r['kind'] for r in rs})
    s['distinct_passages'] = len({r['src'] for r in rs})
    s['answer_words_mean_split'] = mean([r['awords'] for r in rs])
    return s


split_stats = {lab: sp(lab) for lab in ['train', 'practised_slice', 'dev', 'test', 'dropped_passage_overlap_with_dev_test']}
for lab in ['train', 'practised_slice', 'dev', 'test']:
    chk(f'yn_mix_within_0.02_{lab}', abs(split_stats[lab]['yn_share'] - overall_yn) <= 0.02,
        f"split yn={split_stats[lab]['yn_share']} overall yn={overall_yn}")

slice_labels = collections.Counter(r['split'] for r in rows if r['id'] in SLICE_SET)
ids_in_teach = len({r['id'] for r in rows} & SLICE_SET)
chk('slice_ids_unique', len(SLICE) == len(SLICE_SET), f'lines={len(SLICE)} unique={len(SLICE_SET)}')
chk('slice_ids_all_in_teach', ids_in_teach == len(SLICE_SET), f'found={ids_in_teach} of {len(SLICE_SET)}')
chk('slice_rows_labelled_practised', dict(slice_labels) == {'practised_slice': len(SLICE_SET)},
    f'labels={dict(slice_labels)}')
slice_kinds = {r['kind'] for r in rows if r['id'] in SLICE_SET}
chk('slice_kinds_are_kept_train_kinds', slice_kinds <= train_side_kinds and not (slice_kinds & (DEV | TEST)),
    f'n_slice_kinds={len(slice_kinds)} n_kept_kinds={len(train_side_kinds)}')
chk('slice_count_matches_proposal', len(SLICE_SET) == P['practised_slice']['n_rows'],
    f"ids={len(SLICE_SET)} proposal={P['practised_slice']['n_rows']}")

PS = {lab: {r['src'] for r in rows if r['split'] == lab} for lab in ['train', 'practised_slice', 'dev', 'test']}
train_side_pass = PS['train'] | PS['practised_slice']
n_dt_train = len((PS['dev'] | PS['test']) & train_side_pass)
n_dev_test = len(PS['dev'] & PS['test'])
n_slice_train = len(PS['practised_slice'] & PS['train'])
chk('passages_dev_test_not_in_train_side', n_dt_train == 0, f'shared passages={n_dt_train}')
chk('passages_slice_not_in_train', n_slice_train == 0, f'shared passages={n_slice_train}')
chk('passages_dev_vs_test_disjoint', n_dev_test == 0,
    f'shared dev/test passages={n_dev_test} (stricter than proposal rules; proposal does not state it)')

# ---------- 3) eval sets vs TEACH ----------
evals = {}
for fp in sorted(glob.glob(os.path.join(D, 'eval_sets', '*.json'))):
    e = json.load(open(fp))
    items = []
    for ex in e['examples']:
        for qq in ex['questions']:
            items.append({'fam': ex['family'], 'id': ex['id'], 'src': ex['source_text'],
                          'para': ex['paraphrase'], 'typ': qq['type'],
                          'ans': clean(qq['canonical_answer']), 'q': qq['question']})
    evals[os.path.basename(fp)] = items
src_set = {r['src'] for r in rows}
para_set = {r['para'] for r in rows}
q_set = {r['q'] for r in rows}
eval_summary = {}
for name, items in evals.items():
    sh = [it for it in items if it['typ'] != 'yes_no']
    yn = len(items) - len(sh)
    eval_summary[name] = {
        'n_q': len(items), 'yn_share': round(yn / len(items), 4),
        'short_chars_mean': mean([len(it['ans']) for it in sh]),
        'short_chars_p50': pct([len(it['ans']) for it in sh], 50),
        'short_gt8chars_share': share([len(it['ans']) > 8 for it in sh]),
        'short_words_mean': mean([len(words(it['ans'])) for it in sh]),
        'exact_src_in_teach': sum(it['src'] in src_set for it in items),
        'exact_para_in_teach': sum(it['para'] in para_set for it in items),
        'exact_question_in_teach': sum(it['q'] in q_set for it in items),
        'families': sorted({it['fam'] for it in items}),
    }
all_items = [it for v in evals.values() for it in v]
eval_yn_overall = round(sum(1 for it in all_items if it['typ'] == 'yes_no') / len(all_items), 4)
fams = sorted({it['fam'] for it in all_items})
fam_status = {}
for f_ in fams:
    sp_ = sorted({r['split'] for r in rows if r['kind'] == f_})
    fam_status[f_] = {'in_teach': bool(sp_), 'teach_splits': sp_,
                      'n_teach_rows': sum(1 for r in rows if r['kind'] == f_),
                      'eval_items': sum(1 for it in all_items if it['fam'] == f_)}
# token-overlap hints for families not present by exact name (suggested only)
kinds_tokens = {k: set(k.split('_')) - {'the', 'of', 'and', 'with', 'from', 'to', 'a', 'in', 'by', 'is'} for k in ALLK}
near = {}
for f_, st in fam_status.items():
    if not st['in_teach']:
        toks = set(f_.split('_'))
        near[f_] = sorted(k for k, kt in kinds_tokens.items() if kt & toks and len(kt & toks) >= 1)

# ---------- 4) say-back targets ----------
def dist(vals):
    return {'mean': mean(vals), 'p50': pct(vals, 50), 'p90': pct(vals, 90), 'p99': pct(vals, 99), 'max': max(vals)}


sayback = {
    'target_chars_all': dist([len(r['target']) for r in rows]),
    'target_words_all': dist([len(words(r['target'])) for r in rows]),
    'answer_chars_all': dist([r['achars'] for r in rows]),
    'answer_words_all': dist([r['awords'] for r in rows]),
    'answer_gt8chars_all_share': share([r['achars'] > 8 for r in rows]),
    'answer_gt8chars_n_all': sum(1 for r in rows if r['achars'] > 8),
    'answer_gt8chars_n_short': sum(1 for r in rows if r['typ'] != 'yes_no' and r['achars'] > 8),
    'answer_gt8chars_share_short': share([r['achars'] > 8 for r in rows if r['typ'] != 'yes_no']),
    'answer_gt8chars_share_yes_no': share([r['achars'] > 8 for r in rows if r['typ'] == 'yes_no']),
    'target_chars_short': dist([len(r['target']) for r in rows if r['typ'] != 'yes_no']),
    'answer_chars_short': dist([r['achars'] for r in rows if r['typ'] != 'yes_no']),
    'target_words_short': dist([len(words(r['target'])) for r in rows if r['typ'] != 'yes_no']),
    'answer_words_short': dist([r['awords'] for r in rows if r['typ'] != 'yes_no']),
    'distinct_short_answers_gt8': len({r['ans'] for r in rows if r['typ'] != 'yes_no' and r['achars'] > 8}),
    'top_short_answers_gt8': collections.Counter(r['ans'] for r in rows if r['typ'] != 'yes_no' and r['achars'] > 8).most_common(12),
}
eval_all_short = [it['ans'] for it in all_items if it['typ'] != 'yes_no']
sayback['eval_short_answers_gt8_share'] = share([len(a) > 8 for a in eval_all_short])

results = {
    'overall': overall, 'split_stats': split_stats, 'checks': checks,
    'counts_reconstructed': dict(counts), 'eval_summary': eval_summary,
    'eval_yn_share_all_four': eval_yn_overall, 'fam_status': fam_status,
    'near_token_hints_for_new_families': near, 'sayback': sayback,
    'train_kinds_n': len(train_side_kinds), 'slice_kinds_n': len(slice_kinds),
    'teach_kinds_n': len(ALLK),
}
with open(os.path.join(OUT, 'results.json'), 'w') as fh:
    json.dump(results, fh, indent=1, default=str)

# compact stdout
print('CHECKS')
for c in checks:
    print(c['result'], c['check'], '|', c['detail'])
print('OVERALL', {k: overall[k] for k in ['n', 'n_yes_no', 'yn_share', 'short_words_mean', 'short_chars_mean',
                                         'short_chars_p50', 'short_chars_p90', 'short_chars_max',
                                         'short_gt8chars_share', 'short_sub_src_ci', 'short_sub_src_cs',
                                         'short_sub_para_ci', 'short_sub_q_ci', 'short_novel_word_share']})
print('typ', overall['typ_counts'], 'empty_ans', overall['n_empty_answer'])
print('yn answers', overall['yn_answer_values'])
for lab, s in split_stats.items():
    print('SPLIT', lab, {k: s.get(k) for k in ['n', 'yn_share', 'distinct_kinds', 'distinct_passages',
                                              'answer_words_mean_split', 'short_chars_mean', 'short_gt8chars_share']})
print('EVAL', {k: {kk: v[kk] for kk in ['n_q', 'yn_share', 'short_chars_mean', 'short_gt8chars_share',
                                        'exact_src_in_teach', 'exact_para_in_teach', 'exact_question_in_teach']}
               for k, v in eval_summary.items()})
print('EVAL yn all four', eval_yn_overall)
for f_, st in fam_status.items():
    print('FAM', f_, st['in_teach'], st['teach_splits'], st['n_teach_rows'], st['eval_items'])
print('NEAR', near)
print('SAYBACK', json.dumps({k: v for k, v in sayback.items() if k not in ('top_short_answers_gt8',)}, default=str))
print('TOP_GT8', sayback['top_short_answers_gt8'])
