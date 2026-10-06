"""python3 -m creative.tests.test_stones   (CPU, ~30 s) stepping-stone rows: params disjoint from every sealed split, references <= 3 steps, no triple shared with any sealed split,
fresh practised questions share nothing with warm, solver records accepted."""
from creative import fewshot as F, rules_real as R, stones as S

D = 'creative/data/c2'


def test_stones_disjoint_and_short():
    rows, info = S.make_stone_rows(256, 0, D)
    sealed = S.sealed_rule_keys(D)
    assert {(r['kind'], tuple(r['params'])) for r in rows}.isdisjoint(sealed)
    assert all(v <= S.SS_STEPS_MAX for v in info['ref_steps'].values())
    keys = [(r['kind'], tuple(r['params']), r['prompt']) for r in rows]
    assert len(keys) == len(set(keys))
    for r in rows[:100]:
        p = F.parse(r['prompt'])
        assert str(R.fn(r['kind'], tuple(r['params']))(p['q'])) == r['answer']
    recs = S.solver_records(rows[:40])
    for r, rec in zip(rows[:40], recs):
        assert F.verdict(F.parse(r['prompt']), F.record_try(rec))[0] == 'accept'


def test_no_row_from_dev_pool_test():
    rows, _ = S.make_stone_rows(256, 0, D)
    heldout_prompts = {r['prompt'] for n in ('dev', 'pool', 'test', 'labelled') for r in R.load_split(D, n)}
    assert not any(r['prompt'] in heldout_prompts for r in rows)


def test_fresh_practised_share_nothing_with_warm():
    fr, avoid = S.fresh_practised(64, 1, 'fresh-check', D)
    warm = {r['prompt'] for r in R.load_split(D, 'warm')}
    assert not any(r['prompt'] in warm for r in fr)


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
