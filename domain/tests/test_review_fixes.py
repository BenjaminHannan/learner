"""Regression tests for the 2026-10-09 review fixes (DESIGN-AND-MARKS addenda A1, A2, A5, A6, A7).

Run: python3 -m domain.tests.test_review_fixes   (or: pytest domain/tests/test_review_fixes.py)
The model-dependent tests load the parent checkpoint (CPU) and skip when it is not on disk.
"""
import json
import os
import random

from domain import mode, panel
from domain import audit
from domain.tools import rpn as rpn_tool
from domain.tools import sheet as sheet_tool

HERE = os.path.dirname(os.path.abspath(__file__))
CONST = json.load(open(os.path.join(HERE, '..', 'constants.json')))
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'


def ctx(chars=None):
    return dict(vchars=chars or set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz :|;=()+-*/,<>"[]._'),
                cons=CONST, seen=set(), quiz_set=set(), lmax=mode.lmax_of(sheet_tool.help(), CONST['digit_len_extra']))  # A10


def test_rpn_near_rows_differ_from_help_digit_runs():
    # A1: practice keeps each help example's digit-run lengths, so near rows must not use them
    for kind in panel.RPN_SHAPE:
        for seed in range(300):
            prompt, _, _ = panel.rpn_draw(kind, 'near', random.Random(seed))
            runs = panel.digit_runs(prompt.split()[1:])
            assert runs != panel.RPN_HELP_RUNS[kind], (kind, prompt)


def test_zero_step_rows_refused_and_mod_cmp_have_no_row_form():
    # A5: answer-only rows never train; A2: mod and cmp have no text form
    assert mode.make_row(None, 'domain_sheet', 'A: 1 2 | B: 3 4 ; =SUM(A1:A2)', '3', [], CONST, 'tool') == (None, 'zero_steps')
    assert mode.step_text('mod', '7', '5', '2') is None
    assert mode.step_text('cmp', '7', '5', '1') is None
    assert mode.step_text('add', '7', '5', '12') == '7 + 5 = 12'


def test_single_cell_drafts_refused():
    # A5: a degenerate range (A1:A3 -> A3:A3) has no working; no accepted draft may have empty steps
    ex = 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'
    accepted_empty, refused = 0, 0
    for s in range(1500):
        item, why = mode.draft(sheet_tool, ex, 'SUM', random.Random(s), ctx())
        if item is None:
            refused += why == 'no_steps'
        else:
            accepted_empty += item['steps'] == []
    assert accepted_empty == 0 and refused > 0, (accepted_empty, refused)


def test_audit_rules():
    # A1/A5/A7: overlap with a sealed prompt, zero steps and unknown sources are each caught
    panel_map = {'rpn: 9 4 -': 'rpn.jsonl:rpn-near-x'}
    rows = [dict(id='1', source='tool', kind='a b -', prompt='rpn: 9 4 -', steps=['9 - 4 = 5']),
            dict(id='2', source='tool', kind='SUM', prompt='A: 1 | B: 2 ; =A1', steps=[]),
            dict(id='3', source='mystery', kind='x', prompt='rpn: 1 2 +', steps=['1 + 2 = 3'])]
    rep = audit.audit_rows(rows, panel_map)
    assert not rep['ok']
    assert [o['id'] for o in rep['panel_overlap']] == ['1'] and rep['zero_steps'] == ['2'] and rep['bad_source'] == ['3']
    clean = [dict(id='4', source='own', kind='a b +', prompt='rpn: 1 2 +', steps=['1 + 2 = 3'])]
    assert audit.audit_rows(clean, panel_map)['ok']


def test_own_try_kept_only_when_it_is_the_tools_working():
    # A6: a right final answer with a different working is not an own row; the tool's working is used instead
    if not os.path.exists(PARENT):
        return
    import torch
    from custom_io.models import load_model
    m = load_model(PARENT).eval()
    prompt = 'A: 9 1 6 | B: 0 5 9 ; =ABS(A1-B3)'
    ev = sheet_tool.evaluate(prompt)
    item = dict(kind='ABS', prompt=prompt, value=ev['value'], steps=[tuple(s) for s in ev['steps']])
    saved, rows = mode.greedy, []
    try:
        for calls, want in (([('sub', '0', '0', '0')], 'tool'), ([tuple(s) for s in ev['steps']], 'own')):
            mode.greedy = lambda m_, ps, calls=calls: [(calls, ev['value'])] * len(ps)
            rows.clear()
            mode.try_day(m, sheet_tool, [item], ['ABS'], CONST, lambda *a, **k: None, 1, lambda **kw: rows.append(kw))
            assert len(rows) == 1 and rows[0]['source'] == want, (want, rows)
    finally:
        mode.greedy = saved


def test_check_set_not_starved_by_diary_refusals():
    # A5: if every diary answer is refused, the check set is still the first n_c pool prompts (not empty)
    if not os.path.exists(PARENT):
        return
    from custom_io.models import load_model
    m = load_model(PARENT).eval()
    pool = [f'A: {i} 2 | B: 3 4 ; =SUM(A1:A2)' for i in range(40)]
    saved = mode.greedy
    try:
        mode.greedy = lambda m_, ps, bs=64: [([], '')] * len(ps)
        diary, check, _ = mode.build_diary(m, pool, dict(CONST, diary=10, check=5), ctx(), lambda *a, **k: None, lambda **kw: None)
    finally:
        mode.greedy = saved
    assert diary == [] and [c['prompt'] for c in check] == pool[:5]


if __name__ == '__main__':
    fns = [v for k, v in list(globals().items()) if k.startswith('test_') and callable(v)]
    for f in fns:
        f()
        print('PASS', f.__name__)
    print(len(fns), 'tests passed')
