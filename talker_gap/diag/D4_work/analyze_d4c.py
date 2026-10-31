#!/usr/bin/env python3
"""TASK D4 part 3 (advisor follow-ups). Writes only under <DIAG>/D4_work/ and fixes split_proposal_v2.json
stale v1 blocks in place. Stdlib only. Run with -I.
"""
import collections
import gzip
import json
import os
import re

D = '/Users/ben-hannan/Desktop/projects/talker-gap-wt/talker_gap/diag'
TEACH = '/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz'
OUT = os.path.join(D, 'D4_work')
WORD = re.compile(r"[a-z0-9']+")


def words(s):
    return WORD.findall((s or '').lower())


def clean(a):
    return (a or '').strip().rstrip('.').strip()


# 1) fix v2 JSON: rename stale v1 blocks, add the v2 rule text
p2 = os.path.join(D, 'split_proposal_v2.json')
v2 = json.load(open(p2))
for old in ['rule_kind_level', 'passage_overlap_before_guard', 'verification_expected_zero',
            'dev_test_eval_mix_alternative', 'diagnostic_first_id_hash_slice']:
    if old in v2:
        v2[old + '_v1'] = v2.pop(old)
v2['rule_kind_level_v2'] = ('A row is split=dev if its kind is in dev_kinds AND its source_text does not occur in any '
                            'test-kind row (otherwise split=dropped_dev_test_passage_overlap). A row is split=test if its '
                            'kind is in test_kinds. Dev/test kinds are unchanged from v1.')
v2['rule_dev_test_passage_guard_v2'] = ('Dev rows whose source_text occurs in a test row are moved to '
                                        'dropped_dev_test_passage_overlap (130 rows, ids in '
                                        'D4_work/v2_dev_rows_moved_to_dropped_ids.txt). Test is never changed.')
v2['rule_passage_guard_v2_note'] = ('Train-side guard is unchanged from v1: a train-kind row is dropped if its source_text '
                                    'occurs in ANY dev or test row, including the 130 dev rows moved above. This is '
                                    'conservative, and it keeps the train side and practised_slice_ids.txt identical to v1.')
v2['rule_practised_slice_v2'] = ('Unchanged from v1 (rule_practised_slice_v1 is not re-derived by D4; the slice ids are '
                                 'taken from practised_slice_ids.txt). D4 verified: no slice passage on the train side; '
                                 'all slice ids are TEACH ids of kept (train-side) kinds. The ascending sha256(source_text) '
                                 'selection order is UNTESTED.')
v2['dev_test_eval_mix_alternative_v1_note'] = ('v1 thinning block (dev_test_eval_mix_alternative_v1) is NOT applied in '
                                               'v2 and its counts refer to v1 dev. D4 verified only the counts 22,171 yes/no '
                                               'and 21,256 short in v1 dev+test; the kept-id sha256 was not re-derived.')
v2['note_on_stale_blocks'] = ('Blocks ending in _v1 describe the v1 split and do not apply to v2. Use the *_v2 rules and '
                              'the verification_v2 block.')
with open(p2, 'w') as fh:
    json.dump(v2, fh, indent=1, default=str)
print('v2 keys now:', sorted(v2.keys()))

# 2) prompt-overlap variants for short answers, and question-form counts, one streaming pass
dv = collections.Counter()
n_short = 0
forms = collections.Counter()
form_kinds = collections.defaultdict(collections.Counter)
src_quote = collections.Counter()
kind_n = collections.Counter()
PATS = {
    'how_many': lambda q: q.startswith('how many'),
    'how_much': lambda q: q.startswith('how much'),
    'how_long': lambda q: q.startswith('how long'),
    'why': lambda q: q.startswith('why'),
    'when': lambda q: q.startswith('when'),
    'what_time_or_day': lambda q: ('what time' in q) or ('what day' in q),
    'quote_mark_in_question_or_src': None,
}
with gzip.open(TEACH, 'rt') as f:
    for line in f:
        r = json.loads(line)
        ans = clean(r.get('canonical_answer'))
        src = r.get('source_text') or ''
        para = r.get('paraphrase') or ''
        q = (r.get('question') or '')
        ql = q.strip().lower()
        kind = r['kind']
        kind_n[kind] += 1
        if r['type'] != 'yes_no':
            n_short += 1
            aw = words(ans)
            for name, prompt in [('src_para_q', src + ' ' + para + ' ' + q),
                                 ('src_q', src + ' ' + q),
                                 ('para_q', para + ' ' + q)]:
                pw = set(words(prompt))
                if any(w not in pw for w in aw):
                    dv[name] += 1
        for name, fn in PATS.items():
            if fn is not None and fn(ql):
                forms[name] += 1
                form_kinds[name][kind] += 1
        if '"' in src or '“' in src or '”' in src or '"' in q:
            forms['quote_mark_in_src_or_q'] += 1
            form_kinds['quote_mark_in_src_or_q'][kind] += 1

res = {
    'short_rows': n_short,
    'novel_word_share': {k: round(v / n_short, 4) for k, v in dv.items()},
    'novel_word_counts': dict(dv),
    'question_form_counts': dict(forms),
    'question_form_top_kinds': {k: form_kinds[k].most_common(5) for k in form_kinds},
}
with open(os.path.join(OUT, 'results_c.json'), 'w') as fh:
    json.dump(res, fh, indent=1, default=str)
print('short rows', n_short)
print('novel share (any answer word absent): src+para+q', res['novel_word_share']['src_para_q'],
      '| src+q', res['novel_word_share']['src_q'], '| para+q', res['novel_word_share']['para_q'])
print('question forms (rows):', dict(forms))
for k in form_kinds:
    print('  top kinds', k, form_kinds[k].most_common(4))
