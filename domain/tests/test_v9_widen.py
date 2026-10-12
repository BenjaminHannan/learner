"""v9 (far transfer, 10-11): the swap tool that widens the help page, and the ring pick in the practice maker."""
import json
import pytest
import random
from collections import Counter

from custom_io.data import ASCII
from domain import mode
from domain.far import widen
from domain.tools import rpn, sheet

CONS = json.load(open(mode.CONST_PATH))


def ctx_for(tool):
    helps = tool.help()
    return dict(vchars=set(ASCII), cons=CONS, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, CONS['digit_len_extra']))


def build(tool, seed=1, ring_max=300, rings=3):
    cons = dict(CONS, widen_ring_max=ring_max, widen_rings=rings)
    ctx = ctx_for(tool)
    return widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(seed), cons)


def test_pieces_are_balanced_whole_tokens():
    t = widen.tokens('A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)')
    got = {''.join(t[i:j]) for i, j in widen.spans(t)}
    assert 'SUM(A1:A3)' in got and 'A1' in got and '4 7 2' in got
    assert 'SUM(A1' not in got and 'A1:A3)' not in got          # unbalanced
    assert not any(x.startswith(' ') or x.endswith(' ') for x in got)


def test_ring2_is_fixed_and_every_example_runs_within_caps():
    for tool in (sheet, rpn):
        a, sa = build(tool, seed=1)
        b, sb = build(tool, seed=2)
        assert a[2] == b[2]                                   # ring 2 is enumerated: no randomness
        ctx = ctx_for(tool)
        for r in (2, 3):
            assert a[r], (tool.NAME, r)
            for kind, p in a[r]:
                assert mode.accept(tool, p, ctx)[2] is None, p
        shapes = [widen.shape(p) for r in a for _, p in a[r]]
        assert len(shapes) == len(set(shapes))                # one example per digit shape, across rings
        assert sa['kept'][1] == len(tool.help())


def test_ring_examples_keep_the_kind_of_their_help_example():
    rings, _ = build(sheet, ring_max=3000, rings=2)          # ring 2 in full (the real cap does not bind on it)
    assert len(rings[2]) < 3000
    helps = {h['kind'] for h in sheet.help()}
    assert {k for r in rings for k, _ in rings[r]} <= helps
    joined = [p for k, p in rings[2] if k == 'cell arithmetic' and 'SUM(' in p]
    assert joined, 'a SUM piece swapped into the cell arithmetic example'


def test_pick_example_on_a_string_draws_nothing():
    rng = random.Random(5)
    state = rng.getstate()
    assert mode.pick_example('rpn: 3 4 +', rng) == ('rpn: 3 4 +', 1)
    assert rng.getstate() == state                            # runs without widening are unchanged


def test_pick_example_is_even_over_rings():
    rng = random.Random(0)
    ex = {1: ['a'], 2: ['b%d' % i for i in range(50)], 3: ['c%d' % i for i in range(500)]}
    c = Counter(mode.pick_example(ex, rng)[1] for _ in range(6000))
    assert all(1800 < c[r] < 2200 for r in (1, 2, 3)), c


def test_draft_from_rings_reaches_far_properties():
    rings, _ = build(sheet, ring_max=600)
    ex = widen.by_kind(rings, [h['kind'] for h in sheet.help()])
    ctx, rng = ctx_for(sheet), random.Random(3)
    items, tries = [], 0
    while len(items) < 300 and tries < 200000:
        tries += 1
        kind = rng.choice(sorted(ex))
        it, why = mode.draft(sheet, ex[kind], kind, rng, ctx)
        if it:
            ctx['seen'].add(it['prompt'])
            items.append(it)
    assert len(items) == 300
    tall = sum(max(len(c.split()) for c in it['prompt'].split(';')[0].replace('A:', '|').replace('B:', '|').split('|')) >= 5
               for it in items)
    assert tall > 30, tall                                     # grids of 5+ rows appear
    assert Counter(it['ring'] for it in items)[1] > 30


# ---- L4 join step (widen_join) ----

SHEET_V9_SHA_300_SEED7 = '75d20bb6260f0e36af80fd3c9b82e7b0f8edab9af26c5b01f42091d65c6a8c96'   # v9 output before the join step existed
RPN_V9_SHA_300_SEED7 = '77c3b771c1476efeaf71fd9c074ee607cbf22672df67e9c370773e7eec6411b3'


def test_v9_rings_unchanged_without_widen_join():
    for tool, sha in ((sheet, SHEET_V9_SHA_300_SEED7), (rpn, RPN_V9_SHA_300_SEED7)):
        rings, st = build(tool, seed=7, ring_max=300)
        assert st['sha256'] == sha and sorted(rings) == [1, 2, 3] and 'symbols' not in st


def build_join(tool, seed=1, ring_max=300):
    cons = dict(CONS, widen_ring_max=ring_max, widen_rings=3, widen_join=True)
    ctx = ctx_for(tool)
    return widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(seed), cons)


def test_join_ring_deterministic_keeps_kinds_and_caps():
    plain, _ = build(sheet, seed=3)
    a, sa = build_join(sheet, seed=3)
    b, sb = build_join(sheet, seed=3)
    assert sa['sha256'] == sb['sha256'] and a == b
    assert all(a[r] == plain[r] for r in (1, 2, 3))           # the swap rings are the same with the join on
    assert sorted(a) == [1, 2, 3, 4] and a[4] and sa['kept'][4] == len(a[4]) <= 300
    assert sa['tries'][4] > 0 and sum(sa['per_kind'][4].values()) == len(a[4])
    assert set(sa['symbols']) >= set('+*:|;=,') and not set(sa['symbols']) & set('()[]{}')
    ctx = ctx_for(sheet)
    helps = {h['kind'] for h in sheet.help()}
    shapes = [widen.shape(p) for r in a for _, p in a[r]]
    assert len(shapes) == len(set(shapes))                    # digit shape new across all rings
    for kind, p in a[4]:
        assert kind in helps and mode.accept(sheet, p, ctx)[2] is None, p


def test_join_ring_stops_at_try_cap():
    cons = dict(CONS, widen_ring_max=3, widen_rings=3, widen_join=True)
    short = lambda p: len(p) <= 5   # the page runs, every join is too long
    rings = {r: [('k', '1 2 +')] for r in (1, 2, 3)}
    out, tries, info = widen.join_ring(sheet, [{'kind': 'k', 'prompt': '1 2 +'}], rings, short, random.Random(0), cons, set())
    assert out == [] and tries == 3000 and info['accepted'] == []


def test_join_forms_and_brackets_only_with_brackets():
    assert [widen.join_form('P', 'Q', '+', f, ' ') for f in range(6)] == \
        ['P + Q', 'Q + P', '(P) + (Q)', '(Q) + (P)', 'P Q +', 'Q P +']
    assert widen.join_form('P', 'Q', '+', 0, '') == 'P+Q'
    helps = [{'kind': 'a', 'prompt': '3 4 + 2 *'}, {'kind': 'b', 'prompt': '9 1 - 5 max'}]
    cons = dict(CONS, widen_ring_max=200, widen_rings=3, widen_join=True)
    rings = {r: [(h['kind'], h['prompt']) for h in helps] for r in (1, 2, 3)}
    out, _, _ = widen.join_ring(rpn, helps, rings, lambda p: True, random.Random(4), cons, set())
    assert widen.symbols(helps) == ['*', '+', '-'] and out
    assert not any('(' in p or ')' in p for _, p in out)
    helps2 = [{'kind': 'a', 'prompt': '(3 + 4) * 2'}]
    out2, _, _ = widen.join_ring(rpn, helps2, {r: [('a', '(3 + 4) * 2')] for r in (1, 2, 3)}, lambda p: True, random.Random(4), cons,
                                 set())
    assert any(p.count('(') > 1 for _, p in out2)


def test_join_ring_quota_per_accepted_kind():
    a, st = build_join(sheet, seed=3, ring_max=60)
    info = st['join']
    assert info['accepted'] and set(info['kept']) == set(info['accepted'])
    assert max(info['kept'].values()) <= max(60 // len(info['accepted']), 1) + 20   # probe overshoot allowed
    assert sum(info['kept'].values()) == len(a[4]) == st['kept'][4]


def test_value_slots_replace_by_one_still_runs():
    ctx = ctx_for(sheet)
    p = sheet.help()[0]['prompt']
    t, sl = widen.value_slots(p, lambda x: mode.accept(sheet, x, ctx)[2] is None)
    assert sl and all(mode.accept(sheet, widen.swap(t, i, j, '1'), ctx)[2] is None for i, j in sl)


# ---- L8 substitution ring (widen_subst) ----

def build_subst(tool, seed=1, ring_max=60, subst=3, **extra):
    cons = dict(CONS, widen_ring_max=ring_max, widen_rings=3, widen_subst=subst, **extra)
    ctx = ctx_for(tool)
    return widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(seed), cons)


def test_layout_is_domain_free():
    assert widen.layout('A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)+MAX(B1:B2)') == 'x: x | x: x ; =x(x:x)+x(x:x)'


def test_build_unchanged_without_widen_subst():
    for tool, sha in ((sheet, SHEET_V9_SHA_300_SEED7), (rpn, RPN_V9_SHA_300_SEED7)):
        rings, st = build(tool, seed=7, ring_max=300)
        assert st['sha256'] == sha and 'subst' not in st
        cons = dict(CONS, widen_ring_max=300, widen_rings=3, widen_subst=0)   # 0 = off
        ctx = ctx_for(tool)
        r0, s0 = widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(7), cons)
        assert s0['sha256'] == sha and r0 == rings


def test_subst_ring_deterministic_and_runs():
    plain, _ = build(sheet, seed=3, ring_max=60)
    a, sa = build_subst(sheet, seed=3)
    b, sb = build_subst(sheet, seed=3)
    assert a == b and sa['sha256'] == sb['sha256']
    assert all(a[r] == plain[r] for r in (1, 2, 3))           # the swap rings are the same with the substitution on
    assert sorted(a) == [1, 2, 3, 4] and a[4] and sa['kept'][4] == len(a[4]) <= 60
    info = sa['subst']
    assert info['vq'] > 0 and info['accepted'] > 0 and set(info['depth']) <= {1, 2, 3} and sum(info['depth'].values()) == len(a[4])
    ctx = ctx_for(sheet)
    kinds = {h['kind'] for h in sheet.help()}
    for kind, p in a[4]:
        assert kind in kinds and mode.accept(sheet, p, ctx)[2] is None, p
    shapes = [widen.shape(p) for r in a for _, p in a[r]]
    assert len(shapes) == len(set(shapes))


def test_subst_ring_reaches_two_function_calls():
    import re
    a, _ = build_subst(sheet, seed=1)
    two = [p for _, p in a[4] if len(re.findall(r'[A-Z]+\(', p.partition(';')[2])) >= 2]
    assert two, [p for _, p in a[4]][:10]


def test_subst_makes_bracketed_substitutions():
    a, _ = build_subst(sheet, seed=1, ring_max=200)
    assert any('(' + v + ')' in p.partition(';')[2].replace('=(', '=') for _, p in a[4] for v in ('5', '2', 'B1', 'A1')), 'a wrapped piece'


def test_subst_without_brackets_is_bare():
    a, st = build_subst(rpn, seed=1, ring_max=40)
    assert a[4] and not any('(' in p for _, p in a[4])


def test_join_and_subst_together_refused():
    with pytest.raises(ValueError):
        build_subst(sheet, widen_join=True)


# ---- L9 whole-formula join ring (widen_join_whole) ----

def build_whole(tool, seed=1, ring_max=60, **extra):
    cons = dict(CONS, widen_ring_max=ring_max, widen_rings=3, widen_join_whole=True, **extra)
    ctx = ctx_for(tool)
    return widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(seed), cons)


def test_whole_piece_of_the_cell_arithmetic_example():
    _, st = build_whole(sheet)
    w = st['join_whole']['wholes']
    arith = [v for k, v in w.items() if k.partition(';')[2].strip() == '=A1+B2*2']
    assert arith == ['A1+B2*2'], w


def test_whole_pieces_of_call_and_division_examples():
    _, st = build_whole(sheet)
    w = st['join_whole']['wholes']
    assert w['A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'] == 'SUM(A1:A3)'
    assert w['A: 4 7 2 | B: 3 5 1 ; =MAX(A1:A3)'] == 'MAX(A1:A3)'
    div = [v for k, v in w.items() if k.endswith('=A1/B1')]
    assert div == ['A1/B1'], w
    assert all(w.values()), w


def test_whole_join_ring_deterministic_and_runs():
    plain, _ = build(sheet, seed=3, ring_max=60)
    a, sa = build_whole(sheet, seed=3)
    b, sb = build_whole(sheet, seed=3)
    assert a == b and sa['sha256'] == sb['sha256'] and sa['join_whole'] == sb['join_whole']
    assert all(a[r] == plain[r] for r in (1, 2, 3))
    assert sorted(a) == [1, 2, 3, 4] and a[4] and sa['kept'][4] == len(a[4]) <= 60
    info = sa['join_whole']
    assert info['accepted'] and sum(info['kept'].values()) == len(a[4]) and info['tries'] == sa['tries'][4]
    ctx = ctx_for(sheet)
    kinds = {h['kind'] for h in sheet.help()}
    for kind, p in a[4]:
        assert kind in kinds and mode.accept(sheet, p, ctx)[2] is None, p
    shapes = [widen.shape(p) for r in a for _, p in a[r]]
    assert len(shapes) == len(set(shapes))


def test_whole_join_ring_joins_two_calls_at_the_top_level():
    from domain.far.learn_probe import fn_op_fn
    a, _ = build_whole(sheet, seed=1)
    assert any(fn_op_fn(p) for _, p in a[4]), [p for _, p in a[4]][:10]


def test_whole_join_refuses_other_ring_flags():
    with pytest.raises(ValueError):
        build_whole(sheet, widen_join=True)
    with pytest.raises(ValueError):
        build_whole(sheet, widen_subst=3)


def test_build_unchanged_with_widen_join_whole_unset():
    for tool, sha in ((sheet, SHEET_V9_SHA_300_SEED7), (rpn, RPN_V9_SHA_300_SEED7)):
        cons = dict(CONS, widen_ring_max=300, widen_rings=3, widen_join_whole=False)
        ctx = ctx_for(tool)
        _, st = widen.build(tool, tool.help(), lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(7), cons)
        assert st['sha256'] == sha and 'join_whole' not in st
