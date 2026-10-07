"""python3 -m creative.tests.test_c2_stuck   (CPU, ~30 s) job 8: the two-pass search draws pass 2 only for questions with no fitting try, never reads the kind label (scrambled kinds give the
same allocation and the same records), keeps at most 2 distinct fitting tries per question, and the per-parent reading follows the fixed marks."""
import hashlib
from creative import c2_keep, c2_stones, c2_stuck as S, fewshot as F, legal, rules_real as R
from creative.programs import Try


class Rec:
    def __init__(self, t): self.t = t


def _fixture(n=80):
    pool = c2_stones._with_nums(R.load_split('creative/data/c2', 'pool')[:n])
    good, bad = {}, {}
    for r in pool:
        t, _, qs = R.reference(r['kind'], tuple(r['params']))
        q = F.parse(r['prompt'])['q_slot']
        good[r['id']] = R.remap(t, qs, q)
        bad[r['id']] = Try.make([(1, q, 16)], 20)
    return pool, good, bad


def _fake(pool, good, bad, calls):
    h = lambda s: int(hashlib.sha256(s.encode()).hexdigest(), 16)
    def raw_samples(model, rows, vocab, device, n=32, temperature=1.0, level=0, seed=0, bs=2048):
        calls.append((len(rows), n, temperature, seed))
        out = []
        for r in rows:
            k = h(r['id']) % 3                           # 0: fits in pass 1; 1: fits only in pass 2 (late in the 480); 2: never
            if seed < 1000:
                tr = [Rec(good[r['id']]) if k == 0 and i == 5 else Rec(bad[r['id']]) for i in range(n)]
            else:
                tr = [Rec(good[r['id']]) if k == 1 and i in (100, 300) else Rec(bad[r['id']]) for i in range(n)]
            out.append(tr)
        return out
    return raw_samples


def test_search_allocation_and_blindness():
    pool, good, bad = _fixture()
    calls = []
    real = legal.raw_samples
    legal.raw_samples = _fake(pool, good, bad, calls)
    try:
        tries, fit1, fit, drawn = S.search(None, pool, None, 'cpu', seed=10)
        # same pool with every kind label scrambled (rotated among rows) and params removed
        kinds = [r['kind'] for r in pool]
        scr = [dict(r, kind=kinds[(i + 7) % len(kinds)], params=[]) for i, r in enumerate(pool)]
        tries2, fit1b, fitb, drawn2 = S.search(None, scr, None, 'cpu', seed=10)
    finally:
        legal.raw_samples = real
    n_stuck = sum(1 for f in fit1 if not f)
    assert drawn == dict(pass1=32 * len(pool), pass2=480 * n_stuck, stuck_questions=n_stuck) and n_stuck > 0
    assert calls[0][:3] == (len(pool), 32, 3.0) and calls[1][:3] == (n_stuck, 480, 3.0)
    for tr, f1 in zip(tries, fit1):
        assert len(tr) == (32 if f1 else 512)
    assert fit1 == fit1b and fit == fitb and drawn == drawn2
    recs, cnt = S.w_records(pool, tries, seed=1)
    recs2, cnt2 = S.w_records(scr, tries2, seed=1)
    assert [(r['prompt'], r['answer']) for r in recs] == [(r['prompt'], r['answer']) for r in recs2] and cnt == cnt2
    assert all(c <= 2 for c in cnt.values())
    assert sum(fit) > sum(fit1)                       # pass 2 found some


def test_w_records_match_build_arms_W():
    pool, good, bad = _fixture(40)
    tries = [[Rec(bad[r['id']]), Rec(good[r['id']]), Rec(bad[r['id']]), Rec(good[r['id']])] for r in pool]
    a = F.build_arms(pool, tries, tries, seed=3)
    recs, cnt = S.w_records(pool, tries, seed=3)
    assert [(r['id'], r['prompt'], r['answer']) for r in recs] == [(r['id'], r['prompt'], r['answer']) for r in a['W']] and cnt == a['counts']


def test_verdict_reading():
    assert S.verdict_parent(False, True, (0, 0, 0)).startswith('parts not kept')
    assert S.verdict_parent(True, True, (12.0, 3.0, 20.0)).startswith('climb pass')
    assert S.verdict_parent(True, True, (0.6, -1.0, 2.5)).startswith('proved wrong')
    assert S.verdict_parent(True, False, (0.6, -1.0, 2.5)).startswith('between')
    assert S.verdict_parent(True, True, (3.2, 0.0, 6.5)).startswith('between')


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
