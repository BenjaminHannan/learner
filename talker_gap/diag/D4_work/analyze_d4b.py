#!/usr/bin/env python3
"""TASK D4 part 2: dev/test passage overlap, v2 split proposal, and a few side checks.

Writes only under <DIAG>/D4_work/ and <DIAG>/split_proposal_v2.json. Stdlib only. Run with -I.
Train side, practised slice and test are left exactly as in split_proposal.json (v2 only moves
dev rows whose passage also occurs in test), so practised_slice_ids.txt stays valid.
"""
import collections
import gzip
import json
import os

D = '/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag'
TEACH = '/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz'
OUT = os.path.join(D, 'D4_work')

P = json.load(open(os.path.join(D, 'split_proposal.json')))
DEV, TEST = set(P['dev_kinds']), set(P['test_kinds'])
SLICE = {l.strip() for l in open(os.path.join(D, 'practised_slice_ids.txt')) if l.strip()}
TS = json.load(open(os.path.join(D, 'teach_stats.json')))

rows = []
with gzip.open(TEACH, 'rt') as f:
    for line in f:
        r = json.loads(line)
        rows.append((r['id'], r['kind'], r['type'], r.get('source_text') or '', (r.get('canonical_answer') or '').strip()))

# side check 1: SPARES kinds and the 60-kind list
kinds_all = {k for _, k, _, _, _ in rows}
spares = TS['teach']['kinds_py_check']['SPARES']
print('TEACH distinct kinds', len(kinds_all), '| SPARES in TEACH', sum(s in kinds_all for s in spares), 'of', len(spares))
print('SPARES missing from TEACH rows', [s for s in spares if s not in kinds_all])

# side check 2: teach_stats substring numbers for TEACH overall (compare with our recomputation)
ov = TS['teach']['overall'] if 'teach' in TS and 'overall' in TS['teach'] else None
if ov is None:
    ov = TS.get('overall', {})
print('teach_stats overall keys with sub/novel:', {k: ov[k] for k in ov if 'sub' in k or 'novel' in k or 'substring' in k})

# dev/test passage overlap
test_pass = {src for _, k, _, src, _ in rows if k in TEST}
dev_pass = {src for _, k, _, src, _ in rows if k in DEV}
d1 = [(i, k, src) for i, k, t, src, a in rows if k in DEV and src in test_pass]
d2 = [(i, k, src) for i, k, t, src, a in rows if k in TEST and src in dev_pass]
print('dev rows with passage in test', len(d1), 'distinct passages', len({s for _, _, s in d1}),
      'dev kinds', collections.Counter(k for _, k, _ in d1).most_common(8))
print('test rows with passage in dev', len(d2), 'distinct passages', len({s for _, _, s in d2}),
      'test kinds', collections.Counter(k for _, k, _ in d2).most_common(6))

# v2 option A: move dev rows whose passage occurs in test to dropped (test untouched)
drop_ids = {i for i, _, _ in d1}
PER = collections.defaultdict(list)
for i, k, t, src, a in rows:
    if k in DEV:
        lab = 'dropped_dev_test_passage_overlap' if i in drop_ids else 'dev'
    elif k in TEST:
        lab = 'test'
    elif src in test_pass or src in dev_pass:
        lab = 'dropped_passage_overlap_with_dev_test'
    elif i in SLICE:
        lab = 'practised_slice'
    else:
        lab = 'train'
    PER[lab].append((i, k, t, src, a))


def stats(rs):
    n = len(rs)
    yn = sum(1 for x in rs if x[2] == 'yes_no')
    return {'rows': n, 'yes_no_share': round(yn / n, 4) if n else None,
            'distinct_kinds': len({x[1] for x in rs}), 'distinct_passages': len({x[3] for x in rs}),
            'answer_words_mean': round(sum(len(x[4].split()) for x in rs) / n, 3) if n else None}


v2_stats = {lab: stats(v) for lab, v in PER.items()}
v1_expected = {k: v['rows'] for k, v in P['per_split'].items()}
print('V2 per split', {k: v['rows'] for k, v in v2_stats.items()})
print('V2 dev', v2_stats['dev'], '| test', v2_stats['test'])
dev_pass_v2 = {x[3] for x in PER['dev']}
test_pass_v2 = {x[3] for x in PER['test']}
dt_overlap_v2 = len(dev_pass_v2 & test_pass_v2)
train_side_v2 = {x[3] for x in PER['train'] + PER['practised_slice']}
dt_train_v2 = len((dev_pass_v2 | test_pass_v2) & train_side_v2)
slice_ids_ok = {x[0] for x in PER['practised_slice']} == SLICE
kinds_ok = {x[1] for x in PER['dev']} == DEV and {x[1] for x in PER['test']} == TEST
print('V2 checks: dev-test shared passages', dt_overlap_v2, '| dev/test passages in train side', dt_train_v2,
      '| slice ids unchanged', slice_ids_ok, '| dev/test kinds all present', kinds_ok)

# option B for comparison: also drop test rows sharing passage with dev
drop_b = len(d2)
print('option B (also drop test-side overlap) would remove additional test rows:', drop_b,
      'test rows left', v2_stats['test']['rows'] - drop_b)

# alternative yes/no thinning from proposal: verify counts only
dt_rows = [x for x in rows if x[1] in DEV | TEST]
dt_yn = sum(1 for x in dt_rows if x[2] == 'yes_no')
dt_short = len(dt_rows) - dt_yn
print('dev+test rows', len(dt_rows), 'yes/no', dt_yn, 'short', dt_short,
      'yn share', round(dt_yn / len(dt_rows), 4), '| proposal says yes/no before', P['dev_test_eval_mix_alternative']['dev_test_yes_no_rows_before'])
keep = P['dev_test_eval_mix_alternative']['dev_test_yes_no_rows_kept']
print('alt thinning keep', keep, '-> resulting yes/no share', round(keep / (keep + dt_short), 4))

# write v2 proposal (copy of v1 with dev-only change) and the dropped ids
ids_path = os.path.join(OUT, 'v2_dev_rows_moved_to_dropped_ids.txt')
with open(ids_path, 'w') as fh:
    for i in sorted(drop_ids):
        fh.write(i + '\n')
v2 = dict(P)
v2['v2_change'] = ('Dev rows whose source_text also occurs in a test row are moved to '
                   'split=dropped_dev_test_passage_overlap. Train side, practised slice and test are unchanged '
                   'from v1, so practised_slice_ids.txt is still valid.')
v2['v1_failed_check'] = 'dev/test shared passages = 105 (v1 had no dev-vs-test passage rule)'
v2['dev_rows_moved_to_dropped'] = len(drop_ids)
v2['dropped_dev_ids_file'] = ids_path
v2['per_split'] = {k: {kk: vv for kk, vv in s.items()} for k, s in v2_stats.items()}
v2['per_split']['dropped_passage_overlap_with_dev_test'] = v2_stats.get('dropped_passage_overlap_with_dev_test')
v2['verification_v2'] = {
    'dev_test_shared_passages': dt_overlap_v2,
    'dev_test_passages_in_train_side': dt_train_v2,
    'practised_slice_ids_unchanged': slice_ids_ok,
    'dev_and_test_kinds_present': kinds_ok,
    'dev_yes_no_share_within_0.02_of_teach': abs(v2_stats['dev']['yes_no_share'] - 0.5107) <= 0.02,
    'test_yes_no_share_within_0.02_of_teach': abs(v2_stats['test']['yes_no_share'] - 0.5107) <= 0.02,
}
v2['open_question_not_fixed_here'] = ('Dev/test yes/no share is ~51% (TEACH mix) while the four eval sets are '
                                      '10.7% yes/no. dev_test_eval_mix_alternative in v1 is optional; not applied.')
with open(os.path.join(D, 'split_proposal_v2.json'), 'w') as fh:
    json.dump(v2, fh, indent=1, default=str)
print('WROTE split_proposal_v2.json and', ids_path, 'dropped_dev', len(drop_ids))
