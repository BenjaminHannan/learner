"""Tests for domain/tools/py.py and the sealed py panel (A24).

Run: python -m domain.tests.test_py   (or: pytest domain/tests/test_py.py)
The expected values below were worked out by hand, not taken from the tool.
"""
import json
import os
import re

from custom_io.data import ASCII, MAX_ANS, MAX_PROMPT
from custom_io.models.tool import N_NUM, N_RES, NAMES, calc
from domain import panel
from domain.tests.test_tools import caps, replay
from domain.tools import py

PANEL = os.path.join(panel.OUT_DIR, 'py.jsonl')


def test_help_shape():
    h = py.help()
    assert len(h) == 10 and py.NAME == 'py'
    assert [x['kind'] for x in h] == ['assign add', 'chain', 'max min', 'abs', 'list index', 'for sum', 'for repeat',
                                      'if else', 'while', 'function']
    for x in h:
        assert set(x) == {'kind', 'prompt', 'answer'}, x


def test_help_examples():
    for h in py.help():
        res = py.evaluate(h['prompt'])
        assert res['value'] == h['answer'], (h, res)
        assert 1 <= len(res['steps']) <= N_RES, h
        replay(res)
        caps(h['prompt'], h['answer'], res['steps'])


def test_exact_steps():
    assert py.evaluate('py: a = 6; b = a * 3; c = b - 5; print(c)')['steps'] == [
        ('mul', '6', '3', '18'), ('sub', '18', '5', '13')]
    assert py.evaluate('py: a = 3; b = 8; print(abs(a - b))')['steps'] == [('sub', '8', '3', '5')]
    assert py.evaluate('py: a = 9; b = 4; c = max(a, b) - min(a, b); print(c)')['steps'] == [
        ('max', '9', '4', '9'), ('min', '9', '4', '4'), ('sub', '9', '4', '5')]
    assert py.evaluate('py: s = 0; for i in range(3): s = s + i; print(s)')['steps'] == [
        ('add', '0', '0', '0'), ('add', '0', '1', '1'), ('add', '1', '2', '3')]
    assert py.evaluate('py: v = [4, 5, 6]; print(sum(v) + len(v))')['steps'] == [
        ('add', '4', '5', '9'), ('add', '9', '6', '15'), ('add', '15', '3', '18')]
    assert py.evaluate('py: x = 2; if x > 5: y = x - 5; else: y = x + 5; print(y)')['steps'] == [('add', '2', '5', '7')]


def test_more_cases():
    cases = [('py: print(max(3, 9, 4))', '9'), ('py: print(min(3, 9, 4))', '3'), ('py: print(8 // 2)', '4'),
             ('py: def g(a, b): return a * b; print(g(3, 4) + 1)', '13'),
             ('py: n = 1; while n < 100: n = n * 2; print(n)', '128'),
             ('py: v = [1, 2, 3]; k = 2; print(v[k])', '3')]
    for prompt, want in cases:
        res = py.evaluate(prompt)
        assert res['value'] == want, (prompt, want, res)
        replay(res)


def test_bad_prompts():
    bad = [
        'py: import os; print(1)',
        'py: x = 1; print(x.__class__)',
        'py: print(__import__)',
        'py: x = (1).__class__; print(x)',
        'py: print(foo(1))',
        'py: print(open(1))',
        'py: x = "a"; print(x)',
        'py: x = 1; x += 2; print(x)',                       # AugAssign is not allowed
        'py: x = 3; print(x - 5)',                           # negative
        'py: print(5 // 2)',                                  # not exact
        'py: print(5 // 0)',
        'py: print(-3)',                                     # unary minus
        'py: print(1000000000)',                             # too large
        'py: x = 999999999; print(x + 1)',
        'py: print(7 % 2)',                                  # mod is not allowed
        'py: print(2 ** 3)',
        'py: s = 0; for i in range(51): s = s + 1; print(s)',   # over 50 iterations
        'py: s = 0; for i in range(30): s = s + 1; while s < 100: s = s + 1; print(s)',  # 30 + 70 > 50 in all
        'py: n = 0; while n < 5: n = n * 2; print(n)',       # never ends: capped
        'py: x = 1; print(x); print(x)',                     # exactly one print
        'py: x = 1',                                         # no print
        'py: print(1); x = 2',                               # print is not last
        'py: def f(x): return f(x) + 1; print(f(1))',        # unbounded recursion
        'py: def f(x): x = 1; return x; print(f(1))',        # body is two statements
        'py: def f(): return 1; print(f())',                 # needs one or two args
        'py: x = 1; print(x > 0)',                           # a comparison is not a value
        'py: x = 1; y = x if x else 0; print(y)',
        'py: print([1, 2][5])',                              # index out of range
        'py: print(abs(3))',                                 # abs takes (a - b)
        'py: print(max(3))',
        'py: x = 1;y = 2; print(x)',                         # only "; " separates statements
        'py: x = 1  # hi; print(x)',
        'py: x = lambda: 1; print(x())',
        'py: for i in [1, 2]: x = i; print(x)',
        'x = 1; print(x)',                                   # no py: prefix
        'py: ',
    ]
    for prompt in bad:
        res = py.evaluate(prompt)
        assert res['value'] == '?', (prompt, res)
        replay(res)
    assert py.evaluate(None)['value'] == '?'
    assert py.evaluate('py: ' + '(' * 5000 + '1' + ')' * 5000)['value'] == '?'


def test_no_mod_or_cmp_steps():
    seen = set()
    progs = [h['prompt'] for h in py.help()]
    if os.path.exists(PANEL):
        progs += [json.loads(l)['prompt'] for l in open(PANEL)]
    for p in progs:
        for s in py.evaluate(p)['steps']:
            seen.add(s[0])
    assert seen and seen <= {'add', 'sub', 'mul', 'div', 'max', 'min'}, seen
    assert 'mod' not in seen and 'cmp' not in seen
    assert all(o in NAMES[1:] for o in seen)


def test_panel_file():
    assert os.path.exists(PANEL), PANEL
    raw = open(PANEL, 'rb').read()
    want = open(PANEL + '.sha256').read().split()[0]
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == want
    rows = [json.loads(l) for l in raw.decode().splitlines()]
    assert len(rows) == 1000
    helps = {h['prompt'] for h in py.help()}
    seen = set()
    from collections import Counter
    cnt = Counter()
    for r in rows:
        assert set(r) == {'id', 'domain', 'kind', 'split', 'prompt', 'answer', 'n_steps'}
        assert r['domain'] == 'py'
        res = py.evaluate(r['prompt'])
        assert res['value'] == r['answer'] != '?', r
        assert len(res['steps']) == r['n_steps'], r
        replay(res)
        caps(r['prompt'], r['answer'], res['steps'])
        assert r['prompt'] not in helps and r['prompt'] not in seen
        seen.add(r['prompt'])
        cnt[(r['kind'], r['split'])] += 1
    assert set(cnt.values()) == {60, 40} or all(v in (60, 40) for v in cnt.values())
    assert len(cnt) == 20 and all(cnt[(k, 'near')] == 60 and cnt[(k, 'far')] == 40 for k in panel.PY_KINDS)


def test_panel_build_matches_file_and_is_in_caps():
    rows, _ = panel.build_py()
    got = ''.join(json.dumps(r) + '\n' for r in rows)
    assert len(rows) == 1000
    assert all(len(r['prompt']) <= MAX_PROMPT and panel.numbers(r['prompt']) <= N_NUM for r in rows)
    if os.path.exists(PANEL):
        assert got == open(PANEL).read()


if __name__ == '__main__':
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith('test_') and callable(fn)]
    for name, fn in tests:
        fn()
        print('ok', name)
    print('%d tests passed' % len(tests))
