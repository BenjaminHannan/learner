"""python3 -m custom_io.tests.test_progtext   (CPU, seconds; no data files)
progtext (architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 4): every step form on synthetic rows; as_written=False calls = Tool.row_gold's tape entries;
as_written=True differs in exactly the three disclosed ways; every call's result = tool.calc; drill = Tool.drill_gold on text (same draws, provenance)."""
import contextlib, io, random
from custom_io.data import CharVocab
from custom_io.models import progparse as pp, progtext as pt, reader, tool
from custom_io.models.tool import Tool

V = CharVocab.build([])
reader.N_PLACE = tool.CELLS           # the repo's caps raise the reader's place rows to >= CELLS; a bare test model needs the same
T = Tool(V, d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
_n = [0]


def row(prompt, answer, steps, family='chain_ops'):
    _n[0] += 1
    return dict(id=f'p{_n[0]}', family=family, prompt=prompt, answer=answer, steps=steps)


ROWS = dict(
    story=row('Tom has 12 apples and buys 5 more. How many now?', '17', ['12 + 5 = 17']),
    prec=row('3 + 4 * 5', '23', ['3 + 4 * 5 = 23']),
    paren=row('(3 + 4) * 5 - 2', '33', ['(3 + 4) * 5 - 2 = 33']),
    var=row('Let x = 6 * 7 and y = x + 10 with 6 7 10. What is y?', '52', ['x = 6 * 7 = 42', 'y = 42 + 10 = 52']),
    bare_a_add=row('? + 5 = 12', '7', ['7 + 5 = 12'], 'arith_bare'),
    bare_b_add=row('7 + ? = 12', '5', ['7 + 5 = 12'], 'arith_bare'),
    bare_a_sub=row('? - 5 = 12', '17', ['17 - 5 = 12'], 'arith_bare'),
    bare_b_sub=row('12 - ? = 7', '5', ['12 - 5 = 7'], 'arith_bare'),
    bare_a_mul=row('? * 4 = 20', '5', ['5 * 4 = 20'], 'arith_bare'),
    bare_b_div=row('20 / ? = 4', '5', ['20 / 5 = 4'], 'arith_bare'),
    invert=row('A number plus 5 equals 12. Find the number.', '7', ['7 + 5', 'x = 12 - 5 = 7'], 'backward_solve'),
    invert_eq=row('A number plus 5 equals 12. Find the number.', '7', ['7 + 5 = 12', 'x = 12 - 5 = 7'], 'backward_solve'),
    state=row('Start at 12. Then +5, -3. Where now?', '14', ['+5 -> 17', '-3 -> 14'], 'state_update'),
    sum=row('Add 3, 4, 5.', '12', ['sum [3,4,5]'], 'sum_list'),
    small=row('Smallest of 9 4 7?', '4', ['smallest of [9,4,7]'], 'min_list'),
    large=row('Largest of 9 4 7?', '9', ['largest of [9,4,7]'], 'max_list'),
    rng=row('Range of 9 4 7?', '5', ['range of [9,4,7]'], 'range_list'),
    cmp_big=row('Which is bigger, 9 or 4?', '9', ['compare 9 4'], 'compare_numbers'),
    cmp_small=row('Which is smaller, 9 or 4?', '4', ['compare 9 4'], 'compare_numbers'),
    cmp_after=row('Is 9 greater than 4? Say a sign.', '>', ['compare 9 4'], 'compare_after'),
    vc_yes=row('Tom has 12 and buys 5. Claim: Tom has 17.', 'yes', ['12 + 5 = 17'], 'verify_claim'),
    vc_no=row('Tom has 12 and buys 5. Claim: Tom has 18.', 'no', ['12 + 5 = 17'], 'verify_claim'),
    neg=row('3 - 8 + 2', '-3', ['3 - 8 + 2 = -3'], 'chain_ops'),
    bad=row('Tom has 12 apples and buys 5.', '99', ['12 + 5 = 17']),
    nosteps=row('Echo: sune', 'sune', [], 'copy_word'),
)
TEXT = lambda cs: [f"{c['op']} {c['a']} {c['b']} = {c['result']}" for c in cs]
SAME = {'story', 'prec', 'paren', 'var', 'state', 'sum', 'small', 'large', 'rng', 'cmp_after', 'neg'}      # calls equal in both settings


def test_parity():
    for k, r in ROWS.items():
        s, why = pt.steps_of(r, False)
        ops = T.row_gold(r)[0]
        if s is None:
            assert not ops, k
            continue
        assert TEXT(s) == T.row_gold(r)[2][:len(ops)] and len(s) == len(ops), (k, TEXT(s), T.row_gold(r)[2])
        for c in s:
            assert tool.NAMES.index(c['op']) > 0 and c['a_src'] != 'hidden' and c['b_src'] != 'hidden'
    assert pt.steps_of(ROWS['bad'])[0] is None and pt.steps_of(ROWS['bad'])[1] == 'final mismatch'
    assert pt.steps_of(ROWS['nosteps']) == (None, 'no ops')
    print('ok parity', len(ROWS))


def test_forms():
    g = lambda k, w=False: TEXT(pt.steps_of(ROWS[k], w)[0])
    assert g('story') == ['add 12 5 = 17']
    assert g('prec') == ['mul 4 5 = 20', 'add 3 20 = 23']
    assert g('paren') == ['add 3 4 = 7', 'mul 7 5 = 35', 'sub 35 2 = 33']
    assert g('var') == ['mul 6 7 = 42', 'add 42 10 = 52']
    assert g('bare_a_add') == ['sub 12 5 = 7'] and g('bare_b_add') == ['sub 12 7 = 5']
    assert g('bare_a_sub') == ['add 12 5 = 17'] and g('bare_b_sub') == ['sub 12 7 = 5']
    assert g('bare_a_mul') == ['div 20 4 = 5'] and g('bare_b_div') == ['div 20 4 = 5']
    assert g('invert') == ['sub 12 5 = 7', 'sub 12 5 = 7']
    # finding: with a stated result ("7 + 5 = 12") the rewrite's value (7) fails progparse's own `expr mismatch` check, so T1 cannot read the row
    assert pt.steps_of(ROWS['invert_eq'], False) == (None, 'expr mismatch 7 + 5 = 12')
    assert g('state') == ['add 12 5 = 17', 'sub 17 3 = 14']
    assert g('sum') == ['add 3 4 = 7', 'add 7 5 = 12']
    assert g('small') == ['min 9 4 = 4', 'min 4 7 = 4'] and g('large') == ['max 9 4 = 9', 'max 9 7 = 9']
    assert g('rng') == ['max 9 4 = 9', 'max 9 7 = 9', 'min 9 4 = 4', 'min 4 7 = 4', 'sub 9 4 = 5']
    assert g('cmp_big') == ['max 9 4 = 9'] and g('cmp_small') == ['min 9 4 = 4'] and g('cmp_after') == ['cmp 9 4 = 1']
    assert g('vc_yes') == ['add 12 5 = 17', 'cmp 17 17 = 0'] and g('vc_no') == ['add 12 5 = 17', 'cmp 17 18 = -1']
    assert g('neg') == ['sub 3 8 = -5', 'add -5 2 = -3']
    s = pt.steps_of(ROWS['var'])[0]
    assert (s[1]['a_src'], s[1]['b_src'], s[0]['a_src']) == (('res', 0), 'prompt', 'prompt')
    assert pt.steps_of(ROWS['prec'])[0][1]['b_src'] == ('res', 0)
    assert pt.steps_of(ROWS['story'])[0][0]['b_src'] == 'prompt'
    print('ok forms')


def test_as_written():
    g = lambda k: TEXT(pt.steps_of(ROWS[k], True)[0])
    for k in SAME:
        assert pt.steps_of(ROWS[k], True)[0] == pt.steps_of(ROWS[k], False)[0], k
    # (1) no inverse rewrite: the answer is a hidden operand of the call as written
    for k, t in dict(bare_a_add='add 7 5 = 12', bare_b_add='add 7 5 = 12', bare_a_sub='sub 17 5 = 12', bare_b_sub='sub 12 5 = 7', bare_a_mul='mul 5 4 = 20',
                     bare_b_div='div 20 5 = 4').items():
        assert g(k) == [t], (k, g(k))
    c = pt.steps_of(ROWS['bare_a_add'], True)[0][0]
    assert (c['a_src'], c['b_src']) == ('hidden', 'prompt')
    c = pt.steps_of(ROWS['bare_b_sub'], True)[0][0]
    assert (c['a_src'], c['b_src']) == ('prompt', 'hidden')
    assert g('invert') == ['add 7 5 = 12', 'sub 12 5 = 7'] and g('invert_eq') == g('invert')
    assert pt.steps_of(ROWS['invert'], True)[0][1]['a_src'] == ('res', 0) or pt.steps_of(ROWS['invert'], True)[0][1]['a_src'] == 'prompt'
    # (2) compare x y is cmp x y
    assert g('cmp_big') == g('cmp_small') == ['cmp 9 4 = 1']
    # (3) no hand-added CMP for verify_claim
    assert g('vc_yes') == g('vc_no') == ['add 12 5 = 17']
    # a hidden operand must be the answer: any other missing operand is unreadable, and a wrong answer still mismatches
    assert pt.steps_of(row('Tom has 12 apples.', '99', ['40 + 5 = 45']), True)[0] is None
    assert pt.steps_of(ROWS['bad'], True) == (None, 'final mismatch')
    print('ok as_written')


def test_calc():
    for k, r in ROWS.items():
        for w in (False, True):
            s = pt.steps_of(r, w)[0]
            for c in s or []:
                assert tool.calc(c['op'], c['a'], c['b']) == c['result'], (k, w, c)
    print('ok calc')


def test_drill():
    for k, r in ROWS.items():
        s = pt.steps_of(r, False)[0]
        if s is None:
            assert not T.drill_slots(r)
            continue
        a, b = random.Random(5), random.Random(5)
        d = pt.drill(s, r['answer'], a)
        slots = T.drill_slots(r)
        if not slots:
            assert d is None and a.getstate() == b.getstate(), k       # no draws for a row that is not drill-eligible
            continue
        g = T.drill_gold(r, b)
        assert d is not None and d != 'too_long' and g != 'too_long', k
        ds, ans = d
        assert [f"{c['op']} {c['a']} {c['b']} = {c['result']}" for c in ds] == g[2][:len(ds)] and ans == g[5], (k, ds, g)
        assert a.getstate() == b.getstate()                              # the same draws as drill_gold
        for i, (c, o) in enumerate(zip(ds, s)):                          # provenance
            for x, y, src in ((c['a'], o['a'], o['a_src']), (c['b'], o['b'], o['b_src'])):
                assert x == (ds[src[1]]['result'] if isinstance(src, tuple) else y), (k, i)
            assert c['a_src'] == o['a_src'] and c['op'] == o['op'] and c['result'].isdigit()
        assert ans == ds[max(i for i, o in enumerate(s) if o['result'] == r['answer'])]['result']
    s = pt.steps_of(ROWS['paren'])[0]
    one = pt.drill(s, '33', random.Random(1))
    assert one == pt.drill(s, '33', random.Random(1)) and one != pt.drill(s, '33', random.Random(2))
    assert pt.drill(pt.steps_of(ROWS['cmp_after'])[0], '>', random.Random(0)) is None
    assert pt.drill(pt.steps_of(ROWS['paren'])[0], '33', random.Random(0), lens=(30, 30)) == 'too_long'
    h = pt.steps_of(ROWS['bare_a_add'], True)[0]                         # as written: the answer 7 is no call's result
    assert pt.drill(h, '7', random.Random(0)) is None
    hh = pt.drill(h, '12', random.Random(0))
    assert hh[0][0]['a'] == '7' and hh[1] == hh[0][0]['result']          # a hidden operand is kept as written
    print('ok drill')


def test_report():
    rows = list(ROWS.values())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r0, r1 = pt.report(rows, False), pt.report(rows, True)
    out = buf.getvalue()
    assert out.count('NO TRACE') == 5 and 'copy_word' in out and 'backward_solve' in out        # loud: False: 3 families, True: 2
    for r, bad, why in ((r0, 3, {'final mismatch': 1, 'no ops': 1, 'expr mismatch 7 + 5 = 12': 1}), (r1, 2, {'final mismatch': 1, 'no ops': 1})):
        a = r['all']
        assert a['rows'] == len(rows) and a['read'] + a['unreadable'] == len(rows) and a['no_trace'] == a['unreadable'] == bad and a['reasons'] == why, a
        assert r['copy_word']['no_trace'] == 1
    assert r1['all']['hidden'] == r0['all']['hidden'] == 8                   # bare x6, invert, invert_eq (hidden is counted under True either way)
    assert r1['all']['differ'] == r0['all']['differ'] == 12, r0['all']       # bare x6, invert, invert_eq, cmp x2, verify_claim x2
    assert r1['verify_claim']['differ'] == 2 and r1['compare_numbers']['differ'] == 2
    print('ok report')


if __name__ == '__main__':
    for f in (test_parity, test_forms, test_as_written, test_calc, test_drill, test_report):
        f()
    print('ALL OK')
