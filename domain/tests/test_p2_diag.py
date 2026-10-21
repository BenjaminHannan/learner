"""P2 diagnostics (domain/far/MARKS-P2-diagnostics-2026-10-14.md): the pure scoring helpers of domain/far/p2_diag.py (no model)."""
from domain.far import p2_diag as P
from domain.tools import sheet

PROMPT = 'A: 49 20 65 | B: 78 59 92 ; =SUM(B2:B3)+MAX(B2:B3)'
STEPS = [list(s) for s in sheet.evaluate(PROMPT)['steps']]


def rec(calls, pred=None):
    return dict(calls=calls, pred=pred if pred is not None else '243', gold='243', steps=STEPS, k_steps=STEPS[:1], j_steps=STEPS[1:2])


def test_norm_answer():
    assert P.norm_answer(' +5 ') == P.norm_answer('5') == P.norm_answer('5.0') == P.norm_answer('05')
    assert P.norm_answer('1,234') == P.norm_answer('1234')
    assert P.norm_answer('Yes') == 'yes'
    assert P.norm_answer('12') != P.norm_answer('13')


def test_ladder_exact_and_shortcut():
    L = P.ladder(rec([list(s) for s in STEPS]))
    assert all(L[k] for k in ('R1', 'R2', 'R3', 'R4', 'R5', 'O2', 'O3', 'O4'))
    # operand order of add / max does not matter; the MAX call skipped (its value written straight into the join) still answers right
    short = [['add', '92', '59', '151'], ['add', '151', '92', '243']]
    L = P.ladder(rec(short))
    assert L['R1'] and L['R2'] and not L['R3'] and not L['R4'] and L['R5']
    assert P.used_values(short) >= {'59', '92', '151', '243'}


def test_order_free_swapped_vs_missing():
    swapped = [STEPS[1], STEPS[0], STEPS[2]]
    assert P.order_free(swapped, STEPS) == [True, True, True]
    assert not P.prefix_ok(swapped, STEPS, 0, 1)
    assert P.order_free(swapped[:2], STEPS) == [True, True, False]


def test_classify_types():
    assert P.classify(PROMPT, [], STEPS)[2] == 'no calls'
    assert P.classify(PROMPT, [list(s) for s in STEPS[:2]], STEPS)[2] == 'stopped early'
    assert P.classify(PROMPT, [list(s) for s in STEPS] + [['add', '1', '2', '3']], STEPS)[2] == 'extra calls'
    r, where, cat, n = P.classify(PROMPT, [['add', '92', '92', '184']] + [list(s) for s in STEPS[1:]], STEPS, 1, 1)
    assert (r, where, n) == (0, 'r0', 1) and 'cell the formula names' in cat
    r, where, cat, n = P.classify(PROMPT, [['add', '59', '49', '108']] + [list(s) for s in STEPS[1:]], STEPS, 1, 1)
    assert 'does not name' in cat
    assert P.classify(PROMPT, [['mul', '59', '92', '5428']], STEPS)[2] == 'wrong op'
    # a later step done first: order swapped when the skipped step is made later, skipped otherwise
    assert 'order swapped' in P.classify(PROMPT, [STEPS[1], STEPS[0], STEPS[2]], STEPS)[2]
    assert 'skipped' in P.classify(PROMPT, [STEPS[1], STEPS[2]], STEPS)[2]
    assert P.classify(PROMPT, [list(s) for s in STEPS], STEPS)[2] == 'answer only (all calls right)'


def test_number_spot():
    assert P.number_spot(PROMPT, '92').startswith('operand: a cell the formula names')
    assert P.number_spot(PROMPT, '49').startswith('operand: a grid cell the formula does not name')
    assert P.number_spot('A: 5 6 ; =A1+A2*2', '2') == 'operand: a literal of the formula'
    assert P.number_spot(PROMPT, '7') is None
    grid, refs, lits = P.grid_and_refs('A: 1 2 3 | B: 4 5 6 ; =SUM(A1:B2)')
    assert refs == {('A', 1), ('A', 2), ('B', 1), ('B', 2)} and grid[('B', 3)] == 6 and lits == set()


def test_tf_summary_roles():
    r = dict(steps=STEPS, k_steps=STEPS[:1], j_steps=STEPS[1:2], tf_gold=[tuple(s[:3]) for s in STEPS],
             tf_model=[('add', '92', '59'), ('max', '59', '92'), ('mul', '151', '92')] + [('noop', '', '')] * 4)
    s = P.tf_summary([r])
    assert (s['same_len'], s['r0'], s['K'], s['J'], s['join'], s['all']) == (1, 1, 1, 1, 0, 0)
    assert s['by_round'][2] == [0, 1] and s['by_round'][0] == [1, 1]
