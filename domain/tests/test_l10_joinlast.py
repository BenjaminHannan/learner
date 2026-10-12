"""L10 (domain/far/MARKS-L10-2026-10-12.md): whole_piece, join_last_draft, the census."""
import json
import random

from domain import mode
from domain.far import joinlast, widen
from domain.far import learn_probe as L
from domain.tools import sheet

CONS = json.load(open(mode.CONST_PATH))
KINDS = [(f, s) for f in (0, 1, 2, 3) for s in '*+-/']


def ctx_for(tool=sheet):
    chars = set(''.join(h['prompt'] for h in tool.help())) | set('0123456789 ')
    return dict(vchars=chars, cons=CONS, seen=set(), quiz_set=set(), lmax=mode.lmax_of(tool.help(), CONS['digit_len_extra']))


def test_whole_piece_on_the_help_page():
    got = {}
    for h in sheet.help():
        w = widen.whole_piece(h['prompt'], sheet)
        assert w is not None, h['prompt']
        t, (i, j) = w
        got[h['prompt']] = ''.join(t[i:j])
    assert got['A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'] == 'SUM(A1:A3)'
    assert all(p.partition(';')[2].strip().lstrip('=') == v for p, v in got.items()), got
    assert widen.whole_piece('hello', sheet) is None


def run(seed, n=300):
    ctx, rng, out = ctx_for(), random.Random(seed), []
    for _ in range(n):
        item, why = joinlast.join_last_draft(sheet, sheet.help(), KINDS, rng, ctx)
        out.append((item, why))
        if item:
            ctx['seen'].add(item['prompt'])
    return out, ctx


def test_join_last_deterministic_and_accepted():
    a, ctx = run(11)
    b, _ = run(11)
    assert [(i and i['prompt'], w) for i, w in a] == [(i and i['prompt'], w) for i, w in b]
    kept = [i for i, _ in a if i]
    assert kept, [w for _, w in a][:20]
    probe_ctx = ctx_for()
    for i in kept:
        v, steps, why = mode.accept(sheet, i['prompt'], probe_ctx)
        assert why is None and v == i['value'] and i['ring'] == 'joinlast' and i['kind'] in {h['kind'] for h in sheet.help()}
    assert len({i['prompt'] for i in kept}) == len(kept)
    assert {w for i, w in a if i is None} <= {'no_whole_1', 'piece2', 'join', 'dup', 'quiz_dup', 'caps_prompt', 'vocab', 'caps_numbers',
                                              'tool_exception', 'tool_?', 'tool_negative', 'tool_mismatch', 'no_steps', 'caps_answer',
                                              'caps_calls', 'caps_operand', 'caps_entry', 'bad_op'}


def test_census_smoke():
    a, _ = run(5, 150)
    c = L.Census()
    for item, why in a:
        c.add(item, why)
    r = c.report()
    assert r['attempts'] == 150 and r['kept'] == sum(i is not None for i, _ in a) == c.kept
    assert sum(r['reasons'].values()) + r['kept'] == 150
    assert sum(r['digit_runs'].values()) == r['kept'] == sum(r['n_steps'].values())


def test_two_calls():
    assert L.two_calls('A: 1 2 | B: 3 4 ; =SUM(A1:A2)+MAX(B1:B2)')
    assert L.two_calls('A: 1 2 | B: 3 4 ; =(SUM(A1:A2))*(MAX(B1:B2))')
    assert not L.two_calls('A: 1 2 | B: 3 4 ; =SUM(A1:A2)')
    assert not L.two_calls('A: 1 2 | B: 3 4 ; =SUM(A1:A2)+B1*2')
    assert not L.two_calls('A: 1 2 | B: 3 4 ; =SUM(A1:A2)MAX(B1:B2)+')


def test_build_l10_small():
    import os
    import pytest
    torch = pytest.importorskip('torch')
    parent = os.environ.get('L8_TEST_PARENT', L.PARENT)
    if not os.path.exists(parent):
        pytest.skip('parent checkpoint missing')
    from custom_io.models import load_model
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    m = load_model(parent).eval()
    cen = L.Census()
    rows, st = L.build_l8_rows(m, ck['chars'], dict(CONS, widen_ring_max=60), set(), per_cell=3, draw_cap=300000,
                               seed=L.L10_SEED, tag=L.L10_TAG, join_kinds=KINDS, census=cen)
    two = [r for r in rows if r['cell'] == 'mode-two']
    one = [r for r in rows if r['cell'] == 'mode-one']
    assert st['complete'] and len(two) == 3 and len(one) == 3
    assert all(r['ring'] == 'joinlast' and L.far_props(r['prompt'])['two_kinds'] for r in two)
    assert all(r['ring'] in (1, 2, 3) and not L.far_props(r['prompt'])['two_kinds'] for r in one)
    assert all(r['id'].startswith('learn10-') for r in rows) and cen.attempts > 0
