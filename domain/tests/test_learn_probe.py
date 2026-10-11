import os
import random

import pytest

from domain.far import learn_probe as L
from domain.far import sheet_probe as SP

needs_rows = pytest.mark.skipif(not (os.path.exists(L.TRAIN_ROWS) and os.path.exists(SP.PROBE)),
                                reason='shared L1 files missing')


def test_quotas_balance():
    q = L.quotas(6000, SP.SCORED)
    assert sum(q.values()) == 6000 and max(q.values()) - min(q.values()) == 1 and set(q) == set(SP.SCORED)


def test_batch_order_fixed_and_full():
    a = list(L.batch_order(10, 4, 5, 7))
    assert a == list(L.batch_order(10, 4, 5, 7))
    assert all(len(b) == 4 for b in a)
    first_pass = [x for b in a for x in b][:10]
    assert sorted(first_pass) == list(range(10))


def test_build_small_excludes_and_cells():
    ex = {'A: 1 | B: 2 ; =SUM(A1:A1)'}
    rows, stats = L.build_train_rows(random.Random(5), ex, per_cell=14)
    assert len(rows) == 28 and {r['split'] for r in rows} == {'F4-two', 'F0-near'}
    assert len({r['prompt'] for r in rows}) == 28 and not {r['prompt'] for r in rows} & ex
    assert {r['kind'] for r in rows} <= set(SP.SCORED)
    assert all(r['n_steps'] >= 1 for r in rows)


@needs_rows
def test_shared_rows_disjoint_from_probe_and_panels():
    rows = L.load_jsonl(L.TRAIN_ROWS)
    assert len(rows) == 12000
    assert not {r['prompt'] for r in rows} & L.read_prompts(L.EXCLUDE_FILES)
    sets = L.eval_sets(rows)
    assert [len(sets[k]) for k in ('F4-two', 'F0-near', 'fit')] == [420, 420, 420]


@needs_rows
def test_tiny_train_la(tmp_path):
    pytest.importorskip('torch')
    if not os.path.exists(L.PARENT):
        pytest.skip('parent checkpoint missing')
    # scoring 1,440 rows is slow: check the training loop only, with the scorer stubbed out
    calls = []
    orig = L.score_step
    L.score_step = lambda *a, **k: calls.append(a[6])
    try:
        spu = L.train('LA', 3, 1, str(tmp_path / 'o'), [0, 3], log_every=1)
    finally:
        L.score_step = orig
    assert calls == [0, 3] and spu > 0
