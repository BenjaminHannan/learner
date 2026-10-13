"""v10 (addendum A30): the join-last kind in the mode: accepted join kinds, draw_item, and the fixed share in make_practice."""
import itertools
import json
import random
from collections import Counter

from domain import mode
from domain.far import joinlast
from domain.tools import sheet

CONS = json.load(open(mode.CONST_PATH))
HELPS = sheet.help()
KINDS = [h['kind'] for h in HELPS]


def ctx_for(share=None):
    chars = set(''.join(h['prompt'] for h in HELPS)) | set('0123456789 ')
    ctx = dict(vchars=chars, cons=CONS, seen=set(), quiz_set=set(), lmax=mode.lmax_of(HELPS, CONS['digit_len_extra']))
    ex = {h['kind']: h['prompt'] for h in HELPS}
    ctx['joinlast'] = dict(helps=HELPS, kinds=[(0, '+'), (1, '*')], share=share,
                           pick=lambda rng: (rng.choice(HELPS)['prompt'], rng.choice(KINDS)))
    ex[mode.JOIN_KIND] = None
    return ctx, ex


def test_accepted_kinds_deterministic_and_run_by_the_tool():
    ok = lambda p: mode.accept(sheet, p, ctx_for()[0])[2] is None
    a = joinlast.accepted_kinds(sheet, HELPS, ok, random.Random(3), tries=4000)
    b = joinlast.accepted_kinds(sheet, HELPS, ok, random.Random(3), tries=4000)
    assert a == b and a == sorted(a) and a, a
    assert all(f in range(4) and s in '+-*/' for f, s in a), a   # sheet has no postfix form (4, 5): the tool refuses them


def test_draw_item_renames_the_kind_and_drops_calls_without_a_row_form(monkeypatch=None):
    ctx, ex = ctx_for()
    good = dict(kind='SUM', prompt='p1', value='7', steps=[('add', '3', '4', '7')], edits=['letter_rename'], ring='joinlast')
    bad = dict(kind='MIN', prompt='p2', value='1', steps=[('mod', '5', '2', '1')], edits=[], ring='joinlast')
    orig, seq = joinlast.join_last_draft, iter([(good, None), (bad, None), (None, 'tool_?')])
    joinlast.join_last_draft = lambda *a, **k: next(seq)
    try:
        item, why = mode.draw_item(sheet, mode.JOIN_KIND, ex, random.Random(0), ctx)
        assert why is None and item['kind'] == 'join' and item['piece1'] == 'SUM' and item['ring'] == 4 and item['prompt'] == 'p1'
        assert mode.draw_item(sheet, mode.JOIN_KIND, ex, random.Random(0), ctx) == (None, 'no_row_form')
        assert mode.draw_item(sheet, mode.JOIN_KIND, ex, random.Random(0), ctx) == (None, 'tool_?')
    finally:
        joinlast.join_last_draft = orig


def stub_draw(counter):
    def draw(tool, kind, ex, rng, ctx, edits=None):
        n = next(counter)
        if kind == mode.JOIN_KIND and n % 3:   # a join draft is kept 1 time in 3
            return None, 'tool_?'
        return dict(kind=kind, prompt=f'{kind}-{n}', value='1', steps=[('add', '0', '1', '1')], edits=[], ring=4 if kind == mode.JOIN_KIND else 1), None
    return draw


def run_practice(share, n=200):
    ctx, ex = ctx_for(share)
    kinds = KINDS + [mode.JOIN_KIND]
    mix = {k: 1 / len(kinds) for k in kinds}
    orig, mode.draw_item = mode.draw_item, stub_draw(itertools.count(1))
    try:
        items, disc, tries, _ = mode.make_practice(sheet, kinds, ex, mix, n, random.Random(1), ctx)
    finally:
        mode.draw_item = orig
    return items, disc, tries


def test_fixed_share_gives_the_join_kind_exactly_that_fraction_of_the_day():
    items, disc, tries = run_practice(0.4)
    c = Counter(i['kind'] for i in items)
    assert len(items) == 200 and c[mode.JOIN_KIND] == 80, c
    assert all(c[k] > 0 for k in KINDS)   # the mix still covers the rest
    assert disc['tool_?'] > 0 and tries > 200


def test_without_a_share_the_join_kind_is_one_more_kind_of_the_mix():
    items, _, _ = run_practice(None, n=1100)
    c = Counter(i['kind'] for i in items)
    assert len(items) == 1100 and 0 < c[mode.JOIN_KIND] < 1100 / len(KINDS), c   # starved by its yield, not excluded


def test_a_day_with_the_cap_reached_returns_what_it_has():
    ctx, ex = ctx_for(1.0)
    mode.draw_item, orig = (lambda *a, **k: (None, 'tool_?')), mode.draw_item
    try:
        items, disc, tries, _ = mode.make_practice(sheet, KINDS + [mode.JOIN_KIND], ex, {k: 0.1 for k in KINDS + [mode.JOIN_KIND]}, 5, random.Random(0), ctx)
    finally:
        mode.draw_item = orig
    assert items == [] and tries == mode.PRACTICE_OVERDRAW * 5 and disc['tool_?'] == tries


def test_j_rule_bars():
    from domain import analyze
    assert analyze.j_rule(20.0)['verdict'] == 'PASS' and analyze.j_rule(19.99)['verdict'] == 'FAIL'
    assert analyze.j_rule(8.0)['verdict'] == 'FAIL' and analyze.j_rule(7.99)['verdict'] == 'PROVED WRONG'


def test_v4_panel_naming_and_decontam_suffix():
    from domain import audit
    assert audit.panel_suffix('/x/sheet.v4.jsonl') == '.v4' and audit.panel_files('.v4') == ('sheet.v4.jsonl',)
    assert '.v4' in audit.DECONTAM_SUFFIXES


def test_sealed_v4_panel_when_present():
    import hashlib
    import os
    import pytest
    from domain import panel
    path = os.path.join(panel.OUT_DIR, 'sheet.v4.jsonl')
    if not os.path.exists(path):
        pytest.skip('sheet.v4.jsonl not on this machine')
    rows = [json.loads(line) for line in open(path) if line.strip()]
    assert Counter(r['split'] for r in rows) == {'near': 600, 'far': 400, 'join': 420}
    assert len({r['prompt'] for r in rows}) == len(rows)
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    assert sha == 'f527a4872b5a2e74c71196b73a28ead88c5d5b07c58c1dcba4978baa531d0b79'
