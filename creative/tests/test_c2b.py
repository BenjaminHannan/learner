"""python3 -m creative.tests.test_c2b   (CPU, ~1 min) real C2b: R and H take W's counts from tries that fail the example check, read no key and no kind; the pooled bootstrap is paired
within parents; the sealed test split stays closed unless all 6 parents x 4 arms exist, and opens once."""
import json, os, tempfile
import numpy as np
from creative import c2_stones, c2b as C, fewshot as F, rules_real as R
from creative.tests.test_c2_stuck import Rec, _fixture


def _tries(pool, good, bad):
    return [[Rec(bad[r['id']]), Rec(good[r['id']]), Rec(bad[r['id']]), Rec(good[r['id']])] for r in pool]


def test_failing_records():
    pool, good, bad = _fixture(40)
    tries = _tries(pool, good, bad)
    W, counts = C.c2_stuck.w_records(pool, tries, seed=1, arm='W1')
    Rr, Hh, short = C.failing_records(pool, tries, counts, seed=1, night=1)
    assert len(Rr) == len(Hh) and all(r['id'].startswith('R1:') for r in Rr) and all(h['id'].startswith('H1:') for h in Hh) and all(w['id'].startswith('W1:') for w in W)
    per = {}
    for r in Rr:
        per[r['source']] = per.get(r['source'], 0) + 1
    assert all(per[q] <= counts[q] for q in per) and all(q in counts for q in per)
    for r in Rr:                                         # R's tries do NOT fit the shown examples
        p = F.parse(r['prompt'])
        t = F._recover(r)
        assert F.verdict(p, t)[0] == 'reject'
    for h in Hh:                                         # H's relabelled prompt is fit by the same try
        assert F.verdict(F.parse(h['prompt']), F._recover(h))[0] == 'accept'
    # key corruption and kind scrambling change nothing
    bad_key = [dict(r, answer='-7', accepted=['-7']) for r in pool]
    kinds = [r['kind'] for r in pool]
    scr = [dict(r, kind=kinds[(i + 7) % len(kinds)], params=[]) for i, r in enumerate(bad_key)]
    W2, c2 = C.c2_stuck.w_records(scr, tries, seed=1, arm='W1')
    R2, H2, s2 = C.failing_records(scr, tries, c2, seed=1, night=1)
    f = lambda xs: [(x['id'], x['prompt'], x['answer']) for x in xs]
    assert f(W) == f(W2) and f(Rr) == f(R2) and f(Hh) == f(H2) and short == s2


def test_boot_pooled_paired():
    est, lo, hi = C.boot_pooled([([1] * 50, [0] * 50), ([1] * 30, [0] * 30)])
    assert est == lo == hi == 100.0
    a, b = [1, 0] * 100, [1, 0] * 100
    est, lo, hi = C.boot_pooled([(a, b), (a, b)])
    assert est == lo == hi == 0.0
    rng = np.random.default_rng(0)
    x = (rng.random(300) < 0.6).astype(float)
    y = (rng.random(300) < 0.3).astype(float)
    est, lo, hi = C.boot_pooled([(x, y)])
    assert lo < est < hi and lo > 0


def test_sealed_test_stays_closed():
    seen = []
    real = R.load_split
    R.load_split = lambda d, name: (seen.append(name), real(d, name))[1]
    try:
        with tempfile.TemporaryDirectory() as root:
            for p in C.PARENTS[:5]:                       # 5 parents only
                os.makedirs(os.path.join(root, p))
                for f in C.FILES:
                    open(os.path.join(root, p, f), 'w').close()
            try:
                C.score_test(root)
                assert False, 'must refuse with a parent missing'
            except SystemExit as e:
                assert 'REFUSED' in str(e) and 's205' in str(e)
            os.makedirs(os.path.join(root, 's205'))
            for f in C.FILES[:-1]:                        # last parent lacks complete.json
                open(os.path.join(root, 's205', f), 'w').close()
            try:
                C.score_test(root)
                assert False, 'must refuse without complete.json'
            except SystemExit as e:
                assert 'complete.json' in str(e)
            open(os.path.join(root, 's205', 'complete.json'), 'w').close()
            open(os.path.join(root, 'REPORT.json'), 'w').close()
            try:
                C.score_test(root)
                assert False, 'must refuse a second pass'
            except SystemExit as e:
                assert 'already opened' in str(e)
    finally:
        R.load_split = real
    assert 'test' not in seen and not os.path.exists('TEST-OPENED.json')


def _fake_parent(name, shift, n=40):
    rng = np.random.default_rng(abs(hash(name)) % 1000)
    def arm(p, harm=0.0):
        right = (rng.random(n) < p).astype(float).tolist()
        return dict(first_try=sum(right) / n, fits=sum(right) / n, reach4=p, reach32=p + 0.1, by_kind={}, practised=dict(reach32=0.9, first_sample=0.8), skills_pooled5=0.98 - harm / 100,
                    per_q=dict(right=right, reach4=right, reach32=right))
    d = dict(parent=name, T=3.0, recall=dict(recall_on=True, chain5_harm_points=0.1), N=arm(0.2), W=arm(0.2 + shift), R=arm(0.2), H=arm(0.2), M=arm(0.2 + shift / 2))
    return d


def test_report_readings():
    test = [dict(kind=k) for k in ('affine', 'square', 'sq_plus', 'last_digit', 'double_add') * 8]
    per = [_fake_parent(f's20{i}', 0.5) for i in range(6)]
    for p in per:
        for a in ('N', 'W', 'R', 'H', 'M'):
            p[a]['by_kind'] = {k: dict(first_try=p[a]['first_try'], reach4=0, reach32=0) for k in ('affine', 'square', 'sq_plus', 'last_digit', 'double_add')}
    rep = C.report(per, test)
    assert rep['readings']['pooled first try W-N >= +15 with the interval above 0'] and rep['readings']['pooled first try W-R >= +10 with the interval above 0']
    assert rep['readings']['W-N positive on >= 5 of 6 parents'] and rep['readings']['skills harm <= 2 on every parent (W)']
    assert not rep['readings']['proved wrong: W-R upper end < +3'] and 'verdict' not in rep
    per2 = [_fake_parent(f's20{i}', 0.0) for i in range(6)]
    for p in per2:
        for a in ('N', 'W', 'R', 'H', 'M'):
            p[a]['by_kind'] = {k: dict(first_try=0, reach4=0, reach32=0) for k in ('affine', 'square', 'sq_plus', 'last_digit', 'double_add')}
    assert not C.report(per2, test)['readings']['pooled first try W-N >= +15 with the interval above 0']


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
