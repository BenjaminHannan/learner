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


def test_pair_split_rule():
    tr, ho = L.pair_split()
    assert (tr, ho) == L.pair_split()                      # deterministic
    assert len(tr) == 14 and len(ho) == 7 and not set(tr) & set(ho)
    assert len(set(tr) | set(ho)) == 21 and all(a != b and a in SP.SCORED and b in SP.SCORED for a, b in tr + ho)
    for k in SP.SCORED:
        assert any(k in p for p in tr) and any(k in p for p in ho)
    part = L.partners_of(tr)
    assert all(part[k] for k in SP.SCORED) and all((k, j) in tr or (j, k) in tr for k in part for j in part[k])


def test_pair_split_redraws_until_rule():
    # 3 kinds -> 3 pairs, 2 train / 1 held: no kind can be in the lone held-out pair AND all of... rule fails for the third kind
    # in 4 kinds: 6 pairs, 4 train / 2 held; held pairs must cover all 4 kinds (a perfect matching)
    tr, ho = L.pair_split(7, ['A', 'B', 'C', 'D'])
    assert len(tr) == 4 and len(ho) == 2 and len({k for p in ho for k in p}) == 4


def test_l3_cells_small():
    tr, ho = L.pair_split()
    ex = {'A: 1 | B: 2 ; =SUM(A1:A1)'}
    trows, _ = L.build_l3_train(random.Random(5), ex, tr, per_cell=14)
    assert [r['split'] for r in trows] == ['F4-two'] * 14 + ['F0-near'] * 14
    allowed = {frozenset(p) for p in tr}
    for r in trows[:14]:
        assert ')*(' not in r['prompt'] and frozenset((r['kind'], r['partner'])) in allowed
    train_prompts = {r['prompt'] for r in trows}
    erows, _ = L.build_l3_eval(random.Random(6), ex, train_prompts, tr, ho, per_cell=14)
    assert [r['split'] for r in erows] == [c for c in L.L3_CELLS for _ in range(14)]
    held = {frozenset(p) for p in ho}
    for r in erows:
        pr = frozenset((r['kind'], r['partner']))
        op_star = ')*(' in r['prompt']
        assert op_star == (r['split'] in ('HO', 'HPO'))
        assert (pr in held) == (r['split'] in ('HP', 'HPO')) and (pr in allowed) == (r['split'] in ('S', 'HO'))
        assert r['kind'] in SP.SCORED
    assert all(sum(r['kind'] == k for r in erows if r['split'] == 'S') == 2 for k in SP.SCORED)
    ep = [r['prompt'] for r in erows]
    assert len(set(ep)) == len(ep) and not set(ep) & train_prompts and not set(ep) & ex


@needs_probe
def test_eval_sets_l3(tmp_path):
    import json
    rows = [{'id': f'l3-{c}-{i}', 'kind': 'SUM', 'split': c, 'prompt': f'q{c}{i}', 'answer': '1'} for c in L.L3_CELLS for i in range(420)]
    path = tmp_path / 'e.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    sets = L.eval_sets(_fake_train('F4-two'), 'l3', L.L3_SEED, l3_path=str(path))
    assert list(sets) == ['S', 'HP', 'HO', 'HPO', 'F0-near', 'F4-two', 'fit'] and len(sets['fit']) == 420
    assert all(len(sets[c]) == 420 for c in L.L3_CELLS)


def test_arrangement():
    f = lambda body: L.arrangement('A: 4 7 2 | B: 3 5 1 ; =' + body)
    assert f('SUM(A1:A3)+MAX(B1:B3)') == 'plus'
    assert f('A1+B2*2+PRODUCT(A1:A3)') == 'plus'
    assert f('SUM(A1:A3)*MAX(B1:B3)') == 'other'
    assert f('(SUM(A1:A3))*(MAX(B1:B3))') == 'bracket-times'
    assert f('(A1+B1)*(A2+B2)') == 'bracket-times'


@needs_probe
def test_eval_sets_l4_is_union_of_all_and_l3(tmp_path):
    if not os.path.exists(L.L3_EVAL_ROWS):
        pytest.skip('L3 eval file missing')
    rows = [{'id': f'r{i}', 'kind': 'SUM', 'split': 'mode-two', 'prompt': f'p{i}'} for i in range(500)]
    s = L.eval_sets(rows, 'l4', L.L4_SEED)
    assert set(s) == set(L.PROBE_CELLS) | {'fit', 'v3-near', 'v3-far', 'S', 'HP', 'HO', 'HPO'}
    assert len(s['fit']) == 420 and len(s['S']) == 420
    assert [r['id'] for r in s['fit']] == ['fit-' + r['id'] for r in random.Random(L.L4_SEED).sample(rows, 420)]


@needs_rows
def test_build_l4_small():
    torch = pytest.importorskip('torch')
    if not os.path.exists(L.PARENT):
        pytest.skip('parent checkpoint missing')
    import json
    from custom_io.models import load_model
    from domain.mode import CONST_PATH
    ck = torch.load(L.PARENT, map_location='cpu', weights_only=True)
    m = load_model(L.PARENT).eval()
    ex = L.read_prompts(L.EXCLUDE_FILES)
    cons = dict(json.load(open(CONST_PATH)), widen_join=True, widen_ring_max=60)
    rows, st = L.build_mode_rows(m, ck['chars'], cons, ex, per_cell=4, seed=L.L4_SEED, draw_cap=300000, tag='learn4')
    assert st['complete'] and len(rows) == 8 and st['widen']['kept'][4] > 0
    assert all(r['id'].startswith('learn4-') and r['ring'] in (1, 2, 3, 4) for r in rows)
    assert not {r['prompt'] for r in rows} & ex


def test_combine_layout_text_and_value():
    K = ('SUM(A1:A2)', lambda g: g['A'][0] + g['A'][1])
    J = ('B1', lambda g: g['B'][0])
    g = {'A': [5, 4], 'B': [2, 1]}
    want = {'K+J': ('SUM(A1:A2)+B1', 11), 'K-J': ('SUM(A1:A2)-B1', 7), 'K*J': ('SUM(A1:A2)*B1', 18),
            '(K)+(J)': ('(SUM(A1:A2))+(B1)', 11), '(K)-(J)': ('(SUM(A1:A2))-(B1)', 7), '(K)*(J)': ('(SUM(A1:A2))*(B1)', 18)}
    for lay, (text, val) in want.items():
        t, fn = L.combine_layout(lay, K, J)
        assert (t, fn(g)) == (text, val), lay
    none = ('B1', lambda g: None)
    assert all(L.combine_layout(lay, K, none)[1](g) is None for lay in want)


def test_l5_cells_small():
    tr, ho = L.pair_split()
    ex = {'A: 1 | B: 2 ; =SUM(A1:A1)'}
    trows, _ = L.build_l5_train(random.Random(5), ex, tr, per_layout=14, per_cell=14)
    joined = [r for r in trows if r['split'] == 'F4-two']
    assert len(joined) == 70 and len(trows) == 84
    assert [r['layout'] for r in joined] == [lay for lay in L.L5_LAYOUTS for _ in range(14)]
    allowed = {frozenset(p) for p in tr}
    assert all(frozenset((r['kind'], r['partner'])) in allowed for r in joined)
    assert not any(')*(' in r['prompt'] for r in joined)
    train_prompts = {r['prompt'] for r in trows}
    erows, _ = L.build_l5_eval(random.Random(6), ex, train_prompts, tr, ho, per_cell=14, per_layout=14)
    assert [r['split'] for r in erows] == ['S5'] * 70 + [c for c in L.L5_CELLS[1:] for _ in range(14)]
    held = {frozenset(p) for p in ho}
    for r in erows:
        pr = frozenset((r['kind'], r['partner']))
        assert (pr in held) == (r['split'] in ('HP', 'HPO'))
        assert (r['layout'] == '(K)*(J)') == (r['split'] in ('HO', 'HPO'))
        assert (')*(' in r['prompt']) == (r['layout'] == '(K)*(J)')
    ep = [r['prompt'] for r in erows]
    assert len(set(ep)) == len(ep) and not set(ep) & train_prompts and not set(ep) & ex


@needs_probe
def test_eval_sets_l5(tmp_path):
    import json
    rows = [{'id': f'l5-{c}-{i}', 'kind': 'SUM', 'split': c, 'prompt': f'q{c}{i}', 'answer': '1'} for c in L.L5_CELLS for i in range(420)]
    path = tmp_path / 'e.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    sets = L.eval_sets(_fake_train('F4-two'), 'l5', L.L5_SEED, l5_path=str(path))
    assert list(sets) == ['S5', 'S', 'HP', 'HO', 'HPO', 'F0-near', 'F4-two', 'fit'] and len(sets['fit']) == 420


def test_addon_size_defaults_and_override():
    cons = {'addon_rank': 8, 'addon_alpha': 16}
    assert L.addon_size('LA', cons) == (8, 16)
    assert L.addon_size('LA', cons, 64, 128) == (64, 128)
    assert L.addon_size('LA', cons, rank=4) == (4, 16)
    assert L.addon_size('LB', cons) == (None, None)
    with pytest.raises(SystemExit):
        L.addon_size('LB', cons, 64, None)
    with pytest.raises(SystemExit):
        L.main(['train', '--arm', 'LB', '--out', 'x', '--addon-alpha', '128'])


def test_addon_override_reaches_addon(tmp_path, monkeypatch):
    pytest.importorskip('torch')
    import domain.mode as M
    seen = []

    class Stop(Exception):
        pass

    def stub(m, rank, alpha, seed):
        seen.append((rank, alpha))
        raise Stop

    monkeypatch.setattr(M, 'AddOn', stub)
    monkeypatch.setattr(L, 'load_jsonl', lambda p: [])
    monkeypatch.setattr(L, 'eval_sets', lambda *a, **k: {})
    monkeypatch.setattr(L, 'make_rows', lambda m, r, c: ([], {}))
    import custom_io.data as D
    import custom_io.models as MD
    monkeypatch.setattr(MD, 'load_model', lambda p: type('X', (), {'eval': lambda s: s, 'vocab': None})())
    monkeypatch.setattr(D, 'Dataset', lambda rows, vocab: None)
    import torch
    monkeypatch.setattr(torch, 'load', lambda *a, **k: {})
    for kw, want in (({}, None), ({'addon_rank': 64, 'addon_alpha': 128}, (64, 128))):
        seen.clear()
        with pytest.raises(Stop):
            L.train('LA', 1, 1, str(tmp_path / str(len(kw))), [0], **kw)
        cons = __import__('json').load(open(M.CONST_PATH))
        assert seen == [want or (cons['addon_rank'], cons['addon_alpha'])]
