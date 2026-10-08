"""python3 -m creative.tests.test_legal   (CPU, under a minute; no data: tiny random Ledger(copy=True), puzzles from number sets in no sealed split)
Checks the rule-masked sampler (creative/legal.py): level 0 is the plain sampler, level 4 tries always follow the C1 rules (both checkers), level 3 breaks
only on inexact division, the masks never depend on the target, seeds repeat, and 2- and 4-number puzzles get k-1 steps with the answer on the last result."""
import torch
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import legal, puzzles, sampler
from creative.checkers import rules_a, rules_b, verdict
from creative.programs import NOOP, R0, raw_key, run

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
VOCAB = CharVocab.build([])


def model(seed=0):
    torch.manual_seed(seed)
    m = Ledger(VOCAB, copy=True, **SMALL)
    m.eval()
    return m


def rows3(n=12):
    return [r for r, _ in puzzles.warmup3_rows(n, seed=7)]


def judge(row, t):
    nums, k = row['nums'] + [row['target']], len(row['nums'])
    a, b = rules_a(nums, k, t, check_value=False)[0], rules_b(nums, k, t, check_value=False)[0]
    assert a == b, (row['nums'], t)
    return a


def test_level0_is_plain():
    m, rs = model(), rows3()
    b = sampler.make_batch(rs, VOCAB, 'cpu')
    o0, o1 = sampler.sample_run(m, b, greedy=True), legal.sample_run_masked(m, b, legal._k(rs), 0, greedy=True)
    assert all(torch.equal(o0[k], o1[k]) for k in ('ops', 'a', 'b', 'ans'))
    g0, g1 = torch.Generator().manual_seed(3), torch.Generator().manual_seed(3)
    s0, s1 = sampler.sample_run(m, b, 1.0, False, g0), legal.sample_run_masked(m, b, legal._k(rs), 0, 1.0, False, g1)
    assert all(torch.equal(s0[k], s1[k]) for k in ('ops', 'a', 'b', 'ans'))
    print('ok level0_is_plain')


def test_level4_always_legal():
    m, rs = model(1), rows3()
    for T in (0.3, 1.0, 3.0):
        for br in (8, 0):
            tr, raw = legal.sample_tries_masked(m, rs, VOCAB, 'cpu', 32, T, 4, branch=br, seed=1)
            assert all(len(t) > 0 for t in tr)
            for row, t in zip(rs, tr):
                assert len({raw_key(x.t) for x in t}) == len(t)
                for x in t:
                    assert judge(row, x.t), (T, br, row['nums'], x.t)
                    assert x.t.ans == R0 + 1 and all(o == NOOP for o in x.t.ops[2:])
                    assert verdict(row['nums'] + [row['target']], 3, x.t, check_value=False)[0] == 'accept'
    print('ok level4_always_legal')


def test_level3_breaks_only_on_division():
    m, rs = model(2), rows3()
    tr, _ = legal.sample_tries_masked(m, rs, VOCAB, 'cpu', 32, 2.0, 3, branch=8, seed=2)
    for row, t in zip(rs, tr):
        for x in t:
            if not judge(row, x.t):
                _, valid = run(row['nums'] + [row['target']], x.t)
                assert not all(valid[R0 + s] for s in range(2)), x.t
    print('ok level3_breaks_only_on_division')


def test_mask_ignores_target():
    m = model(3)
    base = rows3(6)
    other = [puzzles.make_row(r['id'] + ':alt', r['nums'], r['target'] + 1, 'warm3') for r in base]
    a1 = legal.sample_run_masked(m, sampler.make_batch(base, VOCAB, 'cpu'), legal._k(base), 4, stop_at=1)['allow']
    a2 = legal.sample_run_masked(m, sampler.make_batch(other, VOCAB, 'cpu'), legal._k(other), 4, stop_at=1)['allow']
    assert torch.equal(a1, a2)
    print('ok mask_ignores_target')


def test_seeds_repeat_and_arity():
    m = model(4)
    rs = rows3(6)
    t1, _ = legal.sample_tries_masked(m, rs, VOCAB, 'cpu', 16, 1.0, 4, seed=5)
    t2, _ = legal.sample_tries_masked(m, rs, VOCAB, 'cpu', 16, 1.0, 4, seed=5)
    assert [[x.t for x in t] for t in t1] == [[x.t for x in t] for t in t2]
    r2 = [r for r, _ in puzzles.warmup_rows(6, 0)]
    r4 = [puzzles.make_row('t4:0', [3, 5, 7, 11], 64, 'x'), puzzles.make_row('t4:1', [4, 6, 9, 13], 71, 'x')]
    for rows, k in ((r2, 2), (r4, 4)):
        tr, _ = legal.sample_tries_masked(m, rows, VOCAB, 'cpu', 16, 1.0, 4, seed=6)
        for row, t in zip(rows, tr):
            for x in t:
                assert judge(row, x.t) and x.t.ans == R0 + k - 2 and all(o == NOOP for o in x.t.ops[k - 1:]), (k, x.t)
    print('ok seeds_repeat_and_arity')


if __name__ == '__main__':
    torch.set_num_threads(1)
    for f in (test_level0_is_plain, test_level4_always_legal, test_level3_breaks_only_on_division, test_mask_ignores_target, test_seeds_repeat_and_arity):
        f()
    print('OK')
