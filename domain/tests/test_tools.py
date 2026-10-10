"""Tests for domain/tools/sheet.py and domain/tools/rpn.py.

Run: python -m domain.tests.test_tools   (or: pytest domain/tests/test_tools.py)
The expected values below were worked out by hand, not taken from the tools.
"""
import re

from custom_io.data import ASCII, MAX_ANS, MAX_PROMPT
from custom_io.models.tool import N_NUM, N_RES, NAMES, calc
from domain.tools import rpn, sheet

# 10 hand-checked cases per tool: nesting, 6-cell ranges, and bad prompts (value '?').
SHEET_CASES = [
    ('A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)', '13'),                       # 4+7+2
    ('A: 4 7 2 | B: 3 5 1 ; =SUM(B1:B3)+MAX(A1:A2)', '16'),            # (3+5+1) + max(4,7)
    ('A: 4 7 2 9 1 6 | B: 3 5 1 ; =SUM(A1:A6)', '29'),                 # 6 cells
    ('A: 4 7 2 | B: 3 5 1 ; =A1+B2*2', '14'),                          # * first: 4 + 5*2
    ('A: 8 7 2 | B: 2 5 1 ; =A1/B1', '4'),                             # exact division
    ('A: 4 7 2 | B: 3 5 1 ; =A1/B1', '?'),                             # bad: 4/3 is not exact
    ('A: 4 7 2 | B: 3 5 1 ; =MOD(A2,B2)', '2'),                        # 7 mod 5
    ('A: 4 7 2 | B: 3 5 1 ; =ABS(B1-A1)', '1'),                        # |3-4|
    ('A: 4 7 2 9 1 6 | B: 3 5 1 ; =COUNTIF(A1:A6,">3")', '4'),         # 6 cells: 4,7,9,6
    ('A: 2 7 2 | B: 3 5 1 ; =IF(A1>B1,A2,B2)', '5'),                   # 2 > 3 is false: B2
]

SHEET_BAD = [
    'A: 4 7 2 | B: 3 5 1 ; =B1-A1',              # would be negative
    'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:B3)',         # range across two columns
    'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A9)',         # cell not in the grid
    'A: 4 7 2 | B: 3 5 1 ; =SUM(A1)',            # a function needs a range
    'A: 4 7 2 | B: 3 5 1 ; SUM(A1:A3)',          # no =
    'A: 4 7 2 | B: 3 5 1',                       # no formula
    'A: 4 7 2 | B: 3 5 1 ; =AVG(A1:A3)',         # unknown function
    'A: 4 7 2 | B: 3 5 1 ; =COUNTIF(A1:A2,"<3")',  # only ">k" is a criterion
    'A: 4 7 2 | B: 3 5 1 ; =IF(A1<B1,A2,B2)',   # only ">" is a comparison
    'A: 4 7 2 | B: 3 5 1 ; =A1/B2',             # 4/5 is not exact
    'A: 4 7 2 | B: 3 5 1 ; =MOD(A1,0)',         # mod by zero
]

RPN_CASES = [
    ('rpn: 3 4 + 2 *', '14'),                    # (3+4)*2
    ('rpn: 1 2 + 3 4 + *', '21'),                # (1+2)*(3+4)
    ('rpn: 9 4 -', '5'),
    ('rpn: 56 7 /', '8'),
    ('rpn: 5 2 /', '?'),                         # bad: not exact
    ('rpn: 17 5 %', '2'),
    ('rpn: 3 9 max 4 min', '4'),                 # max(3,9) = 9, min(9,4) = 4
    ('rpn: 1 2 3 4 5 6 7 8 + + + + + + +', '36'),  # 7 operators
    ('rpn: 1 2 3 4 5 6 + + + + +', '21'),        # 6 numbers
    ('rpn: 4 9 -', '?'),                         # bad: would be negative
]

RPN_BAD = [
    'rpn: 3 +',                  # stack short
    'rpn: 3 4',                  # two values left at the end
    'rpn: 3 4 ^',                # unknown token
    'rpn: 3 4 2 * -',            # 3 - 8 would be negative
    'rpn: 6 0 %',                # mod by zero
    'rpn: 0 0 /',                # divide by zero
    'rpn: 1000000000 1 +',       # number too large
    '3 4 +',                     # no rpn: prefix
]


def replay(res):
    """Each step is a calc() call that gives its result, no step is negative, and the last step gives the value."""
    steps, value = res['steps'], res['value']
    for i, (op, a, b, r) in enumerate(steps):
        assert op in NAMES[1:], op
        assert re.fullmatch(r'[0-9]+', a) and re.fullmatch(r'[0-9]+', b), (op, a, b)
        assert calc(op, a, b) == r, (op, a, b, r)
        if r == '?':
            assert i == len(steps) - 1, steps  # a '?' step can only be the last one
        else:
            assert re.fullmatch(r'[0-9]+', r), (op, a, b, r)  # digits only: never negative
    if value != '?' and steps:
        assert steps[-1][3] == value, res


def caps(prompt, answer, steps):
    """The model's caps for a help example: prompt length, answer length, numbers, calls, and vocabulary."""
    assert len(prompt) <= MAX_PROMPT, len(prompt)
    assert len(answer) <= MAX_ANS, answer
    assert len(re.findall(r'[0-9]+', prompt)) <= N_NUM, prompt
    assert len(steps) <= N_RES, len(steps)
    assert all(c in ASCII for c in prompt + answer), prompt + answer


def test_help_shape():
    sh, rp = sheet.help(), rpn.help()
    assert len(sh) == 10 and len(rp) == 8 and len(sh) + len(rp) == 18
    assert [h['kind'] for h in sh] == ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS',
                                       'COUNTIF', 'IF']
    for h in sh + rp:
        assert set(h) == {'kind', 'prompt', 'answer'}, h


def test_sheet_help_examples():
    for h in sheet.help():
        res = sheet.evaluate(h['prompt'])
        assert res['value'] == h['answer'], (h, res)
        replay(res)
        caps(h['prompt'], h['answer'], res['steps'])


def test_rpn_help_examples():
    for h in rpn.help():
        res = rpn.evaluate(h['prompt'])
        assert res['value'] == h['answer'], (h, res)
        replay(res)
        caps(h['prompt'], h['answer'], res['steps'])


def test_sheet_cases():
    assert len(SHEET_CASES) == 10
    for prompt, want in SHEET_CASES:
        res = sheet.evaluate(prompt)
        assert res['value'] == want, (prompt, want, res)
        replay(res)


def test_sheet_bad_prompts():
    for prompt in SHEET_BAD:
        res = sheet.evaluate(prompt)
        assert res['value'] == '?', (prompt, res)
        replay(res)


def test_sheet_exact_steps():
    assert sheet.evaluate('A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)')['steps'] == [
        ('add', '4', '7', '11'), ('add', '11', '2', '13')]
    assert sheet.evaluate('A: 4 7 2 | B: 3 5 1 ; =ABS(B1-A1)')['steps'] == [
        ('max', '3', '4', '4'), ('min', '3', '4', '3'), ('sub', '4', '3', '1')]
    assert sheet.evaluate('A: 4 7 2 | B: 3 5 1 ; =A1+B2*2')['steps'] == [
        ('mul', '5', '2', '10'), ('add', '4', '10', '14')]
    assert sheet.evaluate('A: 2 7 2 | B: 3 5 1 ; =IF(A1>B1,A2,B2)')['steps'] == [
        ('max', '2', '3', '3'), ('cmp', '3', '3', '0'), ('mul', '0', '7', '0'), ('sub', '1', '0', '1'),
        ('mul', '1', '5', '5'), ('add', '0', '5', '5')]
    assert sheet.evaluate('A: 4 7 2 | B: 3 5 1 ; =COUNTIF(A1:A2,">3")')['steps'] == [
        ('max', '4', '3', '4'), ('cmp', '4', '3', '1'), ('max', '7', '3', '7'), ('cmp', '7', '3', '1'),
        ('add', '1', '1', '2')]


def test_rpn_cases():
    assert len(RPN_CASES) == 10
    for prompt, want in RPN_CASES:
        res = rpn.evaluate(prompt)
        assert res['value'] == want, (prompt, want, res)
        replay(res)


def test_rpn_bad_prompts():
    for prompt in RPN_BAD:
        res = rpn.evaluate(prompt)
        assert res['value'] == '?', (prompt, res)
        replay(res)


def test_rpn_exact_steps():
    assert rpn.evaluate('rpn: 3 4 + 2 *')['steps'] == [('add', '3', '4', '7'), ('mul', '7', '2', '14')]
    assert rpn.evaluate('rpn: 9 4 -')['steps'] == [('sub', '9', '4', '5')]
    assert rpn.evaluate('rpn: 4 9 -')['steps'] == []  # refused before the calculator runs


def test_non_string_prompt():
    assert sheet.evaluate(None)['value'] == '?'
    assert rpn.evaluate(None)['value'] == '?'


if __name__ == '__main__':
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith('test_') and callable(fn)]
    for name, fn in tests:
        fn()
        print('ok', name)
    print('%d tests passed' % len(tests))
