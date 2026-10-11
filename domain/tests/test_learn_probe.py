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


needs_probe = pytest.mark.skipif(not (os.path.exists(SP.PROBE) and os.path.exists(L.V3_PANEL)), reason='shared probe/panel missing')


def _fake_train(joined_cell):
    return [{'id': f'x{i}', 'kind': 'SUM', 'split': joined_cell if i % 2 else 'other', 'prompt': f'p{i}', 'answer': '1'}
            for i in range(2000)]


@needs_probe
def test_eval_sets_l1_unchanged():
    sets = L.eval_sets(_fake_train('F4-two'))
    assert list(sets) == ['F4-two', 'F0-near', 'F2b-rows', 'fit'] and len(sets['fit']) == 420


@needs_probe
def test_eval_sets_all_cells_and_fit_cell_name():
    for cell in ('F4-two', 'mode-two'):
        sets = L.eval_sets(_fake_train(cell), 'all', L.MODE_SEED)
        assert list(sets)[:12] == list(L.PROBE_CELLS) and 'fit' in sets and {'v3-near', 'v3-far'} <= set(sets)
        assert len(sets['fit']) == 420 and all(r['split'] == 'fit' for r in sets['fit'])
        assert all(r['kind'] in SP.SCORED for s in sets.values() for r in s)
        assert sets['v3-near'] and sets['v3-far']
        ids = [r['id'] for s in sets.values() for r in s]
        assert len(ids) == len(set(ids))
    assert sets['fit'] == L.eval_sets(_fake_train('mode-two'), 'all', L.MODE_SEED)['fit']   # fixed slice


def test_far_props():
    p = L.far_props('A: 1 2 3 4 5 | B: 1 2 3 4 5 ; =SUM(A1:A5)+MAX(B1:B2)')
    assert p == dict(two_kinds=True, grid_rows=True, max_range_cells=True, max_row_ref=True)
    assert not L.far_props('A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)')['two_kinds']


@needs_rows
def test_build_mode_small():
    torch = pytest.importorskip('torch')
    if not os.path.exists(L.PARENT):
        pytest.skip('parent checkpoint missing')
    import json
    from custom_io.models import load_model
    from domain.mode import CONST_PATH
    ck = torch.load(L.PARENT, map_location='cpu', weights_only=True)
    m = load_model(L.PARENT).eval()
    ex = L.read_prompts(L.EXCLUDE_FILES)
    rows, st = L.build_mode_rows(m, ck['chars'], json.load(open(CONST_PATH)), ex, per_cell=4, draw_cap=300000)
    assert st['complete'] and len(rows) == 8
    assert {r['split'] for r in rows} == set(L.MODE_CELLS) and all(r['cell'] == r['split'] for r in rows)
    assert not {r['prompt'] for r in rows} & ex and len({r['prompt'] for r in rows}) == 8
    assert all(r['kind'] in SP.SCORED and L.far_props(r['prompt'])['two_kinds'] == (r['split'] == 'mode-two') for r in rows)
