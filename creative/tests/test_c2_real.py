"""python3 -m creative.tests.test_c2_real   (CPU; reads the sealed splits in creative/data/c2, never `test` rows' answers beyond triple/ambiguity checks)
Real C2 rows: unique rule from examples, splits disjoint by (kind, params, examples, query), hash seal, reference programs right on the whole domain,
solver warm-up records accepted by the checker, key corruption changes nothing about the check, repeat-counted scoring."""
import json, os, random, shutil, tempfile
from creative import fewshot as F, rules_real as R
from creative.programs import Try

D = os.path.join(os.path.dirname(__file__), '..', 'data', 'c2')


def triple(r):
    p = F.parse(r['prompt'])
    return (r['kind'], tuple(r['params']), tuple(p['xs']), tuple(p['ys']), p['q'])


def test_sealed_hashes_and_kinds():
    man = json.load(open(os.path.join(D, 'MANIFEST.json')))
    for name in ('warm', 'dev', 'pool', 'test', 'labelled'):
        rows = R.load_split(D, name)
        assert len(rows) == man[name]['n']
    assert {r['kind'] for r in R.load_split(D, 'warm')} <= set(R.PRACTISED)
    for name in ('dev', 'pool', 'test', 'labelled'):
        assert {r['kind'] for r in R.load_split(D, name)} <= set(R.HELD_OUT)


def test_hash_catches_tampering():
    t = tempfile.mkdtemp()
    try:
        for f in os.listdir(D):
            shutil.copy(os.path.join(D, f), t)
        with open(os.path.join(t, 'dev.jsonl'), 'a') as f:
            f.write('\n')
        try:
            R.load_split(t, 'dev')
            assert False, 'tampered split loaded'
        except AssertionError as e:
            assert 'sealed hash' in str(e)
    finally:
        shutil.rmtree(t)


def test_splits_share_no_triple():
    seen = {}
    for name in ('warm', 'dev', 'pool', 'test', 'labelled'):
        ts = [triple(r) for r in R.load_split(D, name)]
        assert len(ts) == len(set(ts)), f'{name} repeats a triple'
        for t in ts:
            assert t not in seen, f'{name} shares a triple with {seen[t]}'
            seen[t] = name


def test_rule_unique_from_examples_and_answer_matches():
    for name in ('dev', 'test', 'warm'):
        for r in R.load_split(D, name)[:200]:
            p = F.parse(r['prompt'])
            preds = R.predictions(p['xs'], p['ys'], p['q'])
            assert set(preds) == {int(r['answer'])} and r['accepted'] == [r['answer']]


def test_references_correct_on_whole_domain():
    for kind, params in [('add', (5,)), ('mult', (4,)), ('square', ()), ('last_digit', ()), ('sq_plus', (4,)), ('double_add', (5,)), ('affine', (3, 4))]:
        got = R.reference(kind, params, 200000)
        assert got is not None, (kind, params)
        t, steps, qs = got
        assert steps <= 7
        f = R.fn(kind, params)
        nums = [0] * 16
        for x in R.DOMAIN:
            nums[qs] = x
            vals, valid = F.run(nums, t)
            assert valid[t.ans] and vals[t.ans] == f(x), (kind, params, x)


def test_warm_records_accepted():
    rows = R.load_split(D, 'warm')[:40]
    recs = R.warm_records(rows)
    assert len(recs) == len(rows)
    for r, rec in zip(rows, recs):
        t = F.record_try(rec)
        assert F.verdict(F.parse(r['prompt']), t)[0] == 'accept'
        assert rec['answer'] == r['answer']


def test_check_never_reads_key():
    r = R.load_split(D, 'dev')[0]
    p = F.parse(r['prompt'])
    t, _, qs = R.reference(r['kind'], tuple(r['params']))
    t = R.remap(t, qs, p['q_slot'])
    v0 = F.verdict(p, t)
    assert v0[0] == 'accept'
    bad = dict(r, answer='-1', accepted=['-1'])
    assert F.verdict(F.parse(bad['prompt']), t) == v0


def test_scoring_counts_repeats_in_order():
    r = R.load_split(D, 'dev')[0]
    p = F.parse(r['prompt'])
    t, _, qs = R.reference(r['kind'], tuple(r['params']))
    good = R.remap(t, qs, p['q_slot'])
    bad = Try.make([(1, p['q_slot'], 16)], 20)
    rec = lambda tr: type('S', (), dict(t=tr))()
    s = F.score_samples([r], [[rec(bad)] * 4 + [rec(good)] * 3 + [rec(bad)] * 25])
    assert s['luck'] == 3 / 32 and s['reach4'] == 0.0 and s['reach32'] == 1.0
    s = F.score_samples([r], [[rec(bad), rec(good), rec(good)] + [rec(bad)] * 29])
    assert s['reach4'] == 1.0 and abs(s['luck'] - 2 / 32) < 1e-9


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
