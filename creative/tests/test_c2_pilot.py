"""python3 -m creative.tests.test_c2_pilot   (CPU, ~20 s) C2b pilot pieces: label rule, paired bootstrap, PC records never read the key, the corrupt-every-key test on real pool rows."""
import random
from creative import c2_pilot as P, c2_stones, fewshot as F, rules_real as R
from creative.programs import Try


def test_label_and_boot():
    assert P.label({'square': 20, 'last_digit': 10, 'affine': 0, 'sq_plus': 1, 'double_add': -1}, 16) == 'PASS, near-copy kinds only'
    assert P.label({'square': 20, 'last_digit': 10, 'affine': 5}, 16).startswith('PASS on pooled')
    assert P.label({'square': 2}, 5).startswith('no pooled')
    d, lo, hi = P.boot([1, 1, 0, 0] * 50, [0] * 200)
    assert abs(d - 50) < 1e-9 and lo < d < hi


class Rec:
    def __init__(self, t): self.t = t


def test_leak_test_on_real_rows():
    pool = c2_stones._with_nums(R.load_split('creative/data/c2', 'pool')[:60])
    rng = random.Random(0)
    samples = []
    for r in pool:                        # good reference try, a wrong one, and the reference with the query slot swapped for a constant: all key-independent
        t, _, qs = R.reference(r['kind'], tuple(r['params']))
        q = F.parse(r['prompt'])['q_slot']
        good = R.remap(t, qs, q)
        bad = Try.make([(1, q, 16)], 20)
        samples.append([Rec(good), Rec(bad), Rec(good), Rec(bad)])
    arms = F.build_arms(pool, samples, samples, seed=0)
    assert arms['W'] and arms['R'] and arms['H']
    lt = P.leak_test(pool, samples, arms)
    assert lt['passes'], lt
    pc = P.pc_records(pool, arms['counts'])
    assert len(pc) == len(arms['W'])
    for rec in pc[:20]:
        assert rec['answer'] and rec['answer'] != '-7'


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
