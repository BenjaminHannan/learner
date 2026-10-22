"""python3 -m custom_io.tests.test_cb0_check   (CPU, seconds; no data files). The C2 example checker (custom_io/cb0_check.py) and the writer's copy record it reads.
MARK (1): reference programs for every kind (hand-made copy records) are ACCEPTED, each with ONE constant changed REJECTED. MARK (3): verdicts do not change when row['answer'] /
row['accepted'] / 'kind' are corrupted or deleted. Each rule 1-5 and each disclosed default has its own test. The copy record: greedy(record=False) equals the old code, the record's
meaning, and sample_traces' `copies` on a tiny real B3G2 with random weights (byte lengths, src indices point at the written byte)."""
import copy
import torch
from custom_io import cb0_check as C
from custom_io.data import EOS, N_SPECIAL
from custom_io.models.writer import ByteWriter
from custom_io.tests.test_b3 import batch_of, rows
from custom_io.tests.test_b3g2 import make, V

KINDS = dict(affine=lambda x, A=3, B=5: A * x + B, square=lambda x: x * x, sq_plus=lambda x, B=7: x * x + B, last_digit=lambda x: x % 10, double_add=lambda x, B=4: (x + B) * 2)


def prompt_of(f, xs, q):
    return 'Examples: ' + '; '.join(f'{x} -> {f(x)}' for x in xs) + f'. Now {q} -> ?'


class Prog:
    """Builds a trace with a hand-made copy record. A piece is ('g', text) generated; ('q',) the whole query number; ('qp', a, b) its chars a:b; ('P', text) a copy of `text` from the
    prompt's example lines; ('raw', a, n) prompt[a:a+n]; ('R', k) the whole reply of entry k; ('Rp', k, a, b) chars a:b of it; ('T', k, tok) call token tok of entry k;
    ('E', k, a, n) entry k's text[a:a+n]. A string is a list of pieces; the answer is the last list."""

    def __init__(self, prompt):
        self.prompt = prompt
        qa = prompt.rindex('Now ') + 4
        self.qa, self.qe = qa, prompt.index(' -> ?', qa)

    def written(self, pieces, calls):
        text, src = '', []
        for p in pieces:
            if p[0] == 'g':
                s, o = p[1], [None] * len(p[1])
            elif p[0] == 'q':
                s = self.prompt[self.qa:self.qe]
                o = [('prompt', self.qa + i) for i in range(len(s))]
            elif p[0] == 'qp':
                s = self.prompt[self.qa:self.qe][p[1]:p[2]]
                o = [('prompt', self.qa + p[1] + i) for i in range(len(s))]
            elif p[0] == 'P':
                a = self.prompt.index(p[1])
                s, o = p[1], [('prompt', a + i) for i in range(len(p[1]))]
            elif p[0] == 'raw':
                s, o = self.prompt[p[1]:p[1] + p[2]], [('prompt', p[1] + i) for i in range(p[2])]
            elif p[0] in ('R', 'Rp'):
                c, r = calls[p[1]]
                a = len(c) + 3
                lo, hi = (0, len(r)) if p[0] == 'R' else (p[2], p[3])
                s, o = r[lo:hi], [('tape', p[1], a + lo + i) for i in range(hi - lo)]
            elif p[0] == 'T':
                c = calls[p[1]][0]
                a = sum(len(t) + 1 for t in c.split(' ')[:p[2]])
                tk = c.split(' ')[p[2]]
                s, o = tk, [('tape', p[1], a + i) for i in range(len(tk))]
            else:
                e = C.entry_of(*calls[p[1]])
                s, o = e[p[2]:p[2] + p[3]], [('tape', p[1], p[2] + i) for i in range(p[3])]
            text += s
            src += o
        return text, [dict(copied=x is not None, src=x, share=1.0 if x is not None else 0.0) for x in src]

    def trace(self, steps, answer):
        calls, recs = [], []
        for pieces in steps:
            t, r = self.written(pieces, calls)
            calls.append((t, C.run_call(t)))
            recs.append(r)
        t, r = self.written(answer, calls)
        return dict(calls=calls, answer=t, copies=dict(calls=recs, answer=r))


def reference(kind, xs, q, **k):
    """-> (row, trace) of the reference program for a kind (prompt: affine 3x+5, sq_plus x*x+7, double_add (x+4)*2); the try's constants changed through k (A, B, M, op)."""
    A, B, M, op = k.get('A', 3), k.get('B', dict(affine=5, sq_plus=7, double_add=4).get(kind)), k.get('M', 10), k.get('op', 'mul')
    f = dict(KINDS, affine=lambda x: 3 * x + 5, sq_plus=lambda x: x * x + 7, double_add=lambda x: (x + 4) * 2)[kind]
    row = dict(prompt=prompt_of(f, xs, q))
    P = Prog(row['prompt'])
    Q = [('q',)]
    steps = dict(affine=[[('g', 'mul ')] + Q + [('g', f' {A}')], [('g', 'add '), ('R', 0), ('g', f' {B}')]],
                 square=[[('g', op + ' ')] + Q + [('g', ' ')] + Q],
                 sq_plus=[[('g', 'mul ')] + Q + [('g', ' ')] + Q, [('g', 'add '), ('R', 0), ('g', f' {B}')]],
                 last_digit=[[('g', 'mod ')] + Q + [('g', f' {M}')]],
                 double_add=[[('g', 'add ')] + Q + [('g', f' {B}')], [('g', 'mul '), ('R', 0), ('g', ' 2')]])[kind]
    return row, P.trace(steps, [('R', len(steps) - 1)])


XS = [[2, 7, 13], [12, 17, 29], [5, 22, 9]]
QS = [11, 4, 25]
MUT = dict(affine=[dict(A=4), dict(B=6)], square=[dict(op='add')], sq_plus=[dict(B=8)], last_digit=[dict(M=9)], double_add=[dict(B=5)])


def verdict(row, tr, **k):
    return C.check_try(row, tr, **k)


def test_mark1_reference_accepted_and_mutants_rejected():
    n = 0
    for kind in KINDS:
        for xs, q in zip(XS, QS):
            row, tr = reference(kind, xs, q)
            v = verdict(row, tr)
            assert v['verdict'] == 'accept' and C.check(row, tr), (kind, xs, q, v)
            assert v['outputs'] == [str(C.parse(row['prompt'])['examples'][i][1]) for i in range(len(xs))], v
            for mu in MUT[kind]:
                r2, t2 = row, reference(kind, xs, q, **mu)[1]
                w = verdict(r2, t2)
                assert w['verdict'] == 'reject' and w['reason'] == 'example mismatch' and not C.check(r2, t2), (kind, mu, w)
                n += 1
    print('ok mark 1: %d reference tries accepted, %d one-constant mutants rejected' % (len(KINDS) * len(XS), n))


def test_mark3_corrupt_every_key():
    for kind in KINDS:
        row, tr = reference(kind, XS[1], QS[0])
        base = verdict(row, tr)
        assert base['verdict'] == 'accept'
        for mod in (dict(answer='xx', accepted=['zz']), dict(answer=None), dict(accepted=[]), dict(kind='affine'), dict(kind='nonsense', answer='1', accepted=['1'])):
            r2 = dict(row, **mod)
            assert verdict(r2, copy.deepcopy(tr)) == base, (kind, mod)
        r3 = dict(row, answer='1', accepted=['1'], kind='square')
        for key in ('answer', 'accepted', 'kind'):
            r4 = dict(r3)
            del r4[key]
            assert verdict(r4, tr) == base
        assert verdict(dict(prompt=row['prompt']), tr) == base
    # a bad try is judged the same too
    row, tr = reference('square', XS[0], QS[0])
    bad = dict(tr, answer='1')
    assert verdict(dict(row, answer='1', kind='x'), bad) == verdict(dict(prompt=row['prompt']), bad)
    print('ok mark 3: verdicts and outputs do not depend on row answer / accepted / kind')


def test_parse():
    p = C.parse('Examples: 2 -> 9; 7 -> 26; 13 -> -4. Now 11 -> ?')
    assert p['examples'] == [(2, 9), (7, 26), (13, -4)] and p['query'] == 11
    pr = 'Examples: 2 -> 9; 7 -> 26; 13 -> -4. Now 11 -> ?'
    assert [(pr[a:b], pr[c:d]) for (a, b), (c, d) in p['spans']['examples']] == [('2', '9'), ('7', '26'), ('13', '-4')] and pr[slice(*p['spans']['query'])] == '11'
    for bad in ('', 'Examples: 2 -> 9. Now 11', 'Examples: 2 -> 9; Now 11 -> ?', 'Hello 2 -> 9. Now 11 -> ?', None, 'Examples: 2 -> 9. Now 11 -> ? and more'):
        assert C.parse(bad) is None, bad
    assert verdict(dict(prompt='nope'), dict(calls=[], answer='', copies=dict(calls=[], answer=[])))['reason'] == 'unparseable prompt'
    print('ok parse')


def test_rule1_merge_into_x():
    row, tr = reference('square', [12, 17, 29], 12)
    P = Prog(row['prompt'])
    segs = C.template(C.Trace(tr, row['prompt'], (P.qa, P.qe), False), 0)
    assert segs == [('c', 'mul '), ('x',), ('c', ' '), ('x',)], segs                 # the two bytes of 12 merged into a whole query number = x
    # the same two bytes copied from NON-consecutive positions are not a whole query number: digit 1 from the query (partial), digit 2 an example-line constant
    pr = row['prompt']
    two = pr.index('2', pr.index('17'))                                          # a '2' in the example lines
    t = dict(tr)
    rec = [dict(r) for r in tr['copies']['calls'][0]]
    rec[5] = dict(copied=True, src=('prompt', two), share=1.0)
    segs = C.template(C.Trace(dict(t, copies=dict(calls=[rec], answer=tr['copies']['answer'])), pr, (P.qa, P.qe), False), 0)
    assert segs == [('c', 'mul '), ('xp', 1, 1), ('c', '2'), ('c', ' '), ('x',)], segs
    print('ok rule 1: consecutive copied bytes from consecutive positions merge into one span; whole query number = x')


def test_rule2_rebinding():
    # a copy of the earlier reply is re-bound (affine reference accepted above); a constant written where the reply should have been copied is REJECTED on the examples
    row, tr = reference('affine', [2, 7, 13], 11)
    P = Prog(row['prompt'])
    const = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('g', '33'), ('g', ' 5')]], [('R', 1)])
    assert verdict(row, tr)['verdict'] == 'accept'
    # (call 1 here has NO copied byte, so it is read by value: the written 33 equals call 0's result and may be that result: accepted, the same program as the reference)
    v = verdict(row, const)
    assert v['verdict'] == 'accept' and v['path'] == 'mixed', v
    const = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('g', '33'), ('g', ' '), ('T', 0, 1)]], [('R', 1)])
    assert const['answer'] == '44'
    v = verdict(row, const)
    assert v['verdict'] == 'reject' and v['reason'] == 'example mismatch', v                 # x is read, but the reply (33) was written, not copied
    # a copy of an earlier call-text field (the operand) is re-bound to that operand's re-run value: y = 4x as 'mul x 3' then 'add <copy of x from entry 0> R0'
    pr = prompt_of(lambda x: 4 * x, [2, 7, 13], 11)
    P = Prog(pr)
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('T', 0, 1), ('g', ' '), ('R', 0)]], [('R', 1)])
    assert t['calls'] == [('mul 11 3', '33'), ('add 11 33', '44')]
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'accept' and v['outputs'] == ['8', '28', '52'], v
    # the same operand written as a constant 11 (generated) is not re-bound: rejected
    t2 = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add 11 '), ('R', 0)]], [('R', 1)])
    assert verdict(dict(prompt=pr), t2)['verdict'] == 'reject'
    # a run copied across fields of an entry (operand a, the space, operand b): the default cut splits it per field (each re-bound), here giving a 3-operand call -> rejected
    # on the examples; the fully literal merge (cut=False) leaves a field-crossing span -> uncheckable
    t3 = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('E', 0, 4, 4), ('g', ' '), ('R', 0)]], [('R', 1)])
    v = verdict(dict(prompt=pr), t3)
    assert v['verdict'] == 'reject' and v['reason'] == 'calculator error on an example', v
    v = verdict(dict(prompt=pr), t3, cut=False)
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'span crosses fields', v
    # a span of separators only is a constant: the ' = ' copied
    t4 = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('T', 0, 1), ('g', ' '), ('R', 0)]], [('R', 1)])
    assert verdict(dict(prompt=pr), t4)['verdict'] == 'accept'
    print('ok rule 2: reply and operand copies are re-bound; a constant is not; a field-crossing span is uncheckable')


def test_rule3_partial_copy_from_the_end():
    # last digit as 'add <last byte of the query> 0': aligned from the END, accepted even though x_i has 1 or 2 digits
    pr = prompt_of(lambda x: x % 10, [2, 17, 29, 9], 25)
    P = Prog(pr)
    t = P.trace([[('g', 'add '), ('qp', 1, 2), ('g', ' 0')]], [('R', 0)])
    assert t['calls'] == [('add 5 0', '5')]
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'accept' and v['outputs'] == ['2', '7', '9', '9'], v
    # the FIRST digit of a 2-digit query (offset 1 from the end): x_i = 2 has no such digit -> uncheckable
    t = P.trace([[('g', 'add '), ('qp', 0, 1), ('g', ' 0')]], [('R', 0)])
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'x too short for a partial copy', v
    # a run copied past the number (the last digit and the space after it): the default cut splits it at the number's end ('5' + ' ', the space a constant) -> accepted;
    # the fully literal merge (cut=False) leaves one span that is not inside one number -> uncheckable
    t = P.trace([[('g', 'add '), ('raw', P.qe - 1, 2), ('g', '0')]], [('R', 0)])
    assert t['calls'][0][0] == 'add 5 0' and verdict(dict(prompt=pr), t)['verdict'] == 'accept'
    v = verdict(dict(prompt=pr), t, cut=False)
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'ambiguous partial copy', v
    print('ok rule 3: partial copies align from the end; ambiguous / too short are uncheckable')


def test_rule4_example_lines_are_constants():
    # affine A and B read off an example (copied from the prompt) stay constants: the prompt "3 -> 14"?? use y = 3x + 5: examples 2 -> 11, 7 -> 26; B=5 is not in the lines,
    # so write 'add R <copy of "3" taken from the example "13">' style: A as a copy of the digit 3 inside '13'
    pr = prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 11)
    P = Prog(pr)
    a = pr.index('13') + 1
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' '), ('raw', a, 1)], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('R', 1)])
    assert t['calls'][0][0] == 'mul 11 3'
    segs = C.template(C.Trace(t, pr, (P.qa, P.qe), False), 0)
    assert segs == [('c', 'mul '), ('x',), ('c', ' '), ('c', '3')], segs
    assert verdict(dict(prompt=pr), t)['verdict'] == 'accept'
    # generated bytes are constants: a wrong generated constant is rejected (mark 1), and copied=False with a src is still generated
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('R', 1)])
    t['copies']['calls'][0][4] = dict(copied=False, src=('prompt', P.qa), share=0.1)         # an uncopied byte: a constant, not x
    assert C.template(C.Trace(t, pr, (P.qa, P.qe), False), 0)[0:2] == [('c', 'mul 1'), ('xp', 0, 1)]
    print('ok rule 4: example-line copies and generated bytes are constants')


def test_rule5_answer_is_the_last_result():
    row, tr = reference('affine', [2, 7, 13], 11)
    P = Prog(row['prompt'])
    # an answer copied from the query: uncheckable
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')]], [('q',)])
    v = verdict(row, t)
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'answer is not the last result', v
    # a written number that is not the last result: uncheckable
    assert verdict(row, P.trace([[('g', 'mul '), ('q',), ('g', ' 3')]], [('g', '7')]))['reason'] == 'answer is not the last result'
    # the first result when there are two calls: not the last
    assert verdict(row, P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('R', 0)]))['verdict'] == 'uncheckable'
    # no calls, the answer written as a constant: checked by rules 1-4 (ruling c8ff22777a), so it never reads x -> rejected
    t = P.trace([], [('g', '38')])
    v = verdict(row, t)
    assert v['verdict'] == 'reject' and v['reason'] == 'never reads x', v
    # Ben's rule 2: the answer is written from the thinker's thoughts, never copied, so its record is empty. An answer equal to the last result (with no copied byte) is bound to that
    # result (before rule 2 it was a constant and was rejected 'never reads x'); one that differs from the last result is still uncheckable (above).
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('g', '38')])
    assert t['answer'] == '38' and verdict(row, t)['verdict'] == 'accept'
    print('ok rule 5: with a call, an answer other than the last result (or a copy of it) is uncheckable')


def test_rule2_empty_answer_records():
    """Ben's rule 2: an answer is never copied (all copied=False). A call try whose answer equals the last result is still checkable (bound to the result); a no-call answer is a constant: rejected 'never reads x', never accepted."""
    xs, q = XS[0], QS[0]
    for kind in MUT:
        row, good = reference(kind, xs, q)
        g2 = copy.deepcopy(good)
        g2['copies']['answer'] = [dict(copied=False, src=None, share=0.0) for _ in g2['answer']]
        if g2['calls'] and g2['answer'] == g2['calls'][-1][1]:
            assert verdict(row, g2)['verdict'] == 'accept', (kind, verdict(row, g2))
            _, bad = reference(kind, xs, q, **MUT[kind][0])
            b2 = copy.deepcopy(bad)
            b2['copies']['answer'] = [dict(copied=False, src=None, share=0.0) for _ in b2['answer']]
            assert verdict(row, b2)['verdict'] == 'reject'
    row = dict(prompt=prompt_of(lambda x: x % 10, XS[0], 25))
    P = Prog(row['prompt'])
    t = P.trace([], [('g', '5')])                                              # no call, the right last digit, but written: a constant
    t['copies']['answer'] = [dict(copied=False, src=None, share=0.0)]
    v = verdict(row, t)
    assert v['verdict'] == 'reject' and v['reason'] == 'never reads x', v
    print('ok rule 2 records: call answers equal to the last result stay checkable; a no-call answer is a constant (reject, never reads x)')


def test_no_call_last_digit():
    """Ruling c8ff22777a: rule 5 applies only to tries that make a call; a no-call answer is checked by rules 1-4. (Hand-made copy records: after Ben's rule 2 the model cannot write a copied answer byte any more, so on real tries a no-call answer is a constant; see test_rule2_empty_answer_records.)"""
    for xs, q in zip(XS, QS):
        row = dict(prompt=prompt_of(lambda x: x % 10, xs, q))
        P = Prog(row['prompt'])
        n = len(str(q))
        t = P.trace([], [('qp', n - 1, n)])                                   # the query's last byte copied as the answer
        v = verdict(row, t)
        if n == 1:                                                            # a 1-digit query: its last byte IS the whole number, so the copy is x (rule 1): identity, rejected
            assert v['verdict'] == 'reject' and v['reason'] == 'example mismatch', v
            continue
        assert v['verdict'] == 'accept' and v['outputs'] == [str(x % 10) for x in xs], v
        t = P.trace([], [('g', str((q + 1) % 10))])                           # one constant changed: the last digit written, not copied
        assert verdict(row, t)['verdict'] == 'reject'
        if n == 2:                                                            # a 2-digit query: answer = its last byte copied, then '0' written -> 10 * (x mod 10): rejected
            t = P.trace([], [('qp', 1, 2), ('g', '0')])
            assert verdict(row, t)['verdict'] == 'reject'
    # no-call partial copy needing more digits than an example has: uncheckable (rule 3)
    row = dict(prompt=prompt_of(lambda x: x % 10, [2, 17, 29], 25))
    P = Prog(row['prompt'])
    v = verdict(row, P.trace([], [('qp', 0, 1)]))
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'x too short for a partial copy', v
    # a no-call answer copying the whole query (identity rule) on last_digit: checked, rejected on the examples
    v = verdict(row, P.trace([], [('q',)]))
    assert v['verdict'] == 'reject' and v['reason'] == 'example mismatch', v
    print('ok no-call answers: checked by rules 1-4 (last_digit last-byte copy accepted, a changed constant rejected)')


def test_defaults():
    # never reads x: all examples have y = 7, the try is add 3 4 -> 7: rejected, though it reproduces every example
    pr = prompt_of(lambda x: 7, [2, 9, 13], 11)
    P = Prog(pr)
    t = P.trace([[('g', 'add 3 4')]], [('R', 0)])
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'reject' and v['reason'] == 'never reads x', v
    # ... a try reading x only through a re-bound result counts as reading it
    pr = prompt_of(lambda x: x + 0, [2, 9, 13], 11)
    P = Prog(pr)
    t = P.trace([[('g', 'add '), ('q',), ('g', ' 0')], [('g', 'add '), ('R', 0), ('g', ' 0')]], [('R', 1)])
    assert verdict(dict(prompt=pr), t)['verdict'] == 'accept'
    # self re-run mismatch: the trace's reply is not what the calculator gives
    t = dict(calls=[('add 3 4', '8')], answer='8', copies=dict(calls=[[dict(copied=False, src=None, share=0.0)] * 7], answer=[dict(copied=True, src=('tape', 0, 10), share=1.0)]))
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'self re-run mismatch', v
    # a calculator reply '?' on an example is a reject (the query's own reply is '?' as well, so the self re-run holds)
    pr = prompt_of(lambda x: 0, [2, 9, 13], 11)
    P = Prog(pr)
    t = P.trace([[('g', 'div '), ('q',), ('g', ' 0')]], [('R', 0)])
    assert t['answer'] == '?'
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'reject' and v['reason'] == 'calculator error on an example', v
    # a record that disagrees with the text: uncheckable
    row, tr = reference('square', [2, 7, 13], 11)
    bad = copy.deepcopy(tr)
    bad['copies']['calls'][0][4] = dict(copied=True, src=('prompt', 0), share=1.0)           # 'E' of 'Examples' is not '1'
    assert verdict(row, bad)['reason'] == 'bad copy record'
    short = copy.deepcopy(tr)
    short['copies']['calls'][0].pop()
    assert verdict(row, short)['reason'] == 'bad copy record'
    fut = copy.deepcopy(tr)
    fut['copies']['calls'][0][4] = dict(copied=True, src=('tape', 0, 0), share=1.0)           # a copy from the entry being written
    assert verdict(row, fut)['reason'] == 'bad copy record'
    assert verdict(row, dict(calls=tr['calls'], answer=tr['answer']))['verdict'] == 'accept'      # no 'copies' at all: every string is read by value (addendum 2)
    for junk in (None, [], dict(calls=[('mul 11 11',)], answer='121'), dict(calls=tr['calls'], answer=121), dict(calls=tr['calls'], answer='121', copies=7),
                 dict(calls=tr['calls'], answer='121', copies=dict(calls=[[], []], answer=[]))):
        assert verdict(row, junk)['reason'] == 'malformed trace', junk
    assert verdict(row, dict(calls=tr['calls'], answer='121', copies=dict(calls=[{}], answer=[])))['reason'] == 'bad copy record'      # a record that is not a list of bytes
    # summarise: the counts plus the mark 2 / addenda figures
    vs = [verdict(row, tr), verdict(row, bad), verdict(row, short), verdict(row, tr)]
    s = C.summarise(vs)
    assert s == dict(n=4, verdict=dict(accept=2, uncheckable=2), reason={'accept/reproduces every example': 2, 'uncheckable/bad copy record': 2}, calling=4, no_call=0, no_call_share=0.0,
                     uncheckable_calling=2, uncheckable_calling_share=0.5, uncheckable_calling_of_tries=0.5, accepted=2, accepted_multi=0, accepted_multi_share=0.0, path=dict(copy=2)), s
    print('ok defaults: never reads x, self re-run mismatch, calculator error, bad record, summarise')


def test_swap_is_safe_on_wrong_records():
    # a constant that collides with x on the query but was recorded as a copy of x: put back on the query it is the original try; on the examples it is wrong -> rejected, never accepted
    pr = prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 11)
    P = Prog(pr)
    a = pr.index('13') + 1
    t = P.trace([[('g', 'mul 11 '), ('raw', a, 1)], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('R', 1)])      # '11' generated (the call copies a '3', so it is read by its record: a constant)
    assert t['calls'][0][0] == 'mul 11 3'
    v = verdict(dict(prompt=pr), t)
    assert v['verdict'] == 'reject' and v['reason'] == 'never reads x', v
    t = P.trace([[('g', 'mul 11 '), ('g', '3')], [('g', 'add '), ('R', 0), ('g', ' 5'), ]], [('R', 1)])       # no copied byte in call 0: read by value, '11' may be x: the right program
    assert verdict(dict(prompt=pr), t)['verdict'] == 'accept'
    # a collision that is only a coincidence on the query (x = 5, and the constant of the rule is 5): read by value, enumeration finds the binding that fits
    pr5 = prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 5)
    t = Prog(pr5).trace([[('g', 'mul 5 3')], [('g', 'add 15 5')]], [('g', '20')])
    v = verdict(dict(prompt=pr5), t)
    assert v['verdict'] == 'accept' and v['assignments'] == 8 and v['fits'] == 1, v
    print('ok a value colliding with x can only cause a false reject (copy record) or is enumerated (by value)')


# ---- binding by value: no copy record anywhere (creative roadmap addenda 1 and 2) ----
def strip(tr, how):
    """A trace without its copy record, in the ways a talker that cannot copy may hand it over: 'absent' (no 'copies' key), 'empty' (empty record lists), 'short' (copies.calls = [] and
    answer None), 'false' (one all-uncopied record per byte, as the writer gives when nothing is copied)."""
    out = dict(calls=list(tr['calls']), answer=tr['answer'])
    if how == 'empty':
        out['copies'] = dict(calls=[[] for _ in tr['calls']], answer=[])
    elif how == 'short':
        out['copies'] = dict(calls=[], answer=None)
    elif how == 'false':
        out['copies'] = dict(calls=[[dict(copied=False, src=None, share=0.0) for _ in c] for c, _ in tr['calls']], answer=[dict(copied=False, src=None, share=0.0) for _ in tr['answer']])
    else:
        assert how == 'absent'
    return out


HOWS = ('absent', 'empty', 'short', 'false')


def test_value_mark1_without_copy_records():
    """CB-0 mark (1), addendum 2: reference call texts for every kind, with NO copy record, are accepted on all examples; each version with one constant changed is rejected. Every record
    style (absent / empty / short / all-uncopied) gives the same verdict, and the path is 'value'."""
    n = m = 0
    for kind in KINDS:
        for xs, q in zip(XS, QS):
            row, tr = reference(kind, xs, q)
            want = verdict(row, tr)
            for how in HOWS:
                t = strip(tr, how)
                v = verdict(row, t)
                assert v['verdict'] == 'accept' and C.check(row, t) and v['path'] == 'value' and v['fits'] >= 1 and 1 <= v['assignments'] <= C.MAX_ASSIGN, (kind, xs, q, how, v)
                assert v['outputs'] == want['outputs'] == [str(C.parse(row['prompt'])['examples'][i][1]) for i in range(len(xs))], v
                n += 1
                for mu in MUT[kind]:
                    t2 = strip(reference(kind, xs, q, **mu)[1], how)
                    w = verdict(row, t2)
                    assert w['verdict'] == 'reject' and w['reason'] == 'example mismatch' and not C.check(row, t2), (kind, mu, how, w)
                    m += 1
    print('ok value mark 1: %d reference tries (4 record styles) accepted, %d one-constant mutants rejected, no copy record read' % (n, m))


def test_value_mark1_sweep_over_queries():
    """The same over every query 1..60 (so the query takes the value of every rule constant and of intermediate results): reference accepted, each one-constant mutant rejected, never
    uncheckable (<= 16 assignments for the reference programs)."""
    worst, n = 0, 0
    for kind in KINDS:
        for xs in XS:
            for q in range(1, 61):
                row, tr = reference(kind, xs, q)
                t = strip(tr, 'absent')
                v = verdict(row, t)
                assert v['verdict'] == 'accept', (kind, xs, q, v)
                worst = max(worst, v['assignments'])
                for mu in MUT[kind]:
                    w = verdict(row, strip(reference(kind, xs, q, **mu)[1], 'absent'))
                    assert w['verdict'] == 'reject', (kind, xs, q, mu, w)
                n += 1
    assert worst <= C.MAX_ASSIGN
    print('ok value sweep: %d reference tries over queries 1..60 accepted (at most %d assignments), every mutant rejected' % (n, worst))


def test_value_two_call_sq_plus():
    """A two-call sq_plus try whose second call uses the first call's result: accepted by value; its one-constant mutants rejected."""
    xs, q = [2, 7, 13], 11
    row = dict(prompt=prompt_of(lambda x: x * x + 7, xs, q))
    good = dict(calls=[('mul 11 11', '121'), ('add 121 7', '128')], answer='128')
    v = verdict(row, good)
    assert v['verdict'] == 'accept' and v['outputs'] == ['11', '56', '176'] and v['path'] == 'value', v
    assert (v['assignments'], v['fits']) == (2 * 2 * 2, 1), v                                    # '11' x2 may be x, '121' may be call 0's result, '7' only a constant
    for calls, ans, why in ((['mul 11 11', 'add 121 8'], '129', 'example mismatch'), (['mul 11 12', 'add 132 7'], '139', 'example mismatch'),
                            (['add 11 11', 'add 22 7'], '29', 'example mismatch'),
                            (['mul 11 11', 'add 120 7'], '127', 'never reads x')):              # 120 is no result of the try: a constant, so the answer ignores x
        w = verdict(row, dict(calls=[(c, C.run_call(c)) for c in calls], answer=ans))
        assert w['verdict'] == 'reject' and w['reason'] == why, (calls, w)
    # the second call's operand is the first result, not x: the first result written as a constant elsewhere does not fit
    assert verdict(row, dict(calls=[('mul 11 11', '121'), ('add 121 7', '128')], answer='127'))['reason'] == 'answer is not the last result'
    print('ok value two-call sq_plus: the second call binds to the first result; mutants rejected')


def test_value_ambiguity_enumerated():
    """A query equal to a rule constant (or an intermediate result) matches several tokens; every assignment is tried and the one that fits is found."""
    # affine 3x + 5, query 3 (= A): 'mul 3 3' = 9; 'add 9 5' = 14. Tokens: 3 (x or c), 3 (x or c), 9 (r0 or c), 5 (c): 8 assignments; (x, 3, r0, 5) and (3, x, r0, 5) fit (mul is symmetric)
    row = dict(prompt=prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 3))
    v = verdict(row, dict(calls=[('mul 3 3', '9'), ('add 9 5', '14')], answer='14'))
    assert v['verdict'] == 'accept' and (v['assignments'], v['fits']) == (8, 2), v
    # query 5 (= B): 'mul 5 3' = 15; 'add 15 5' = 20
    row = dict(prompt=prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 5))
    v = verdict(row, dict(calls=[('mul 5 3', '15'), ('add 15 5', '20')], answer='20'))
    assert v['verdict'] == 'accept' and (v['assignments'], v['fits']) == (8, 1), v
    # the same try with a wrong constant that also equals x (B written as 6 when the query is 6): rejected: 3x + 6
    row6 = dict(prompt=prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 6))
    v = verdict(row6, dict(calls=[('mul 6 3', '18'), ('add 18 6', '24')], answer='24'))
    assert v['verdict'] == 'reject' and v['reason'] == 'example mismatch', v                  # 3x + 6 and 3x + x both fail
    # sq_plus x*x + 7, query 7 (= B): 4 tokens that match -> 16 assignments (the limit), accepted by one
    row = dict(prompt=prompt_of(lambda x: x * x + 7, [2, 5, 13], 7))
    v = verdict(row, dict(calls=[('mul 7 7', '49'), ('add 49 7', '56')], answer='56'))
    assert v['verdict'] == 'accept' and (v['assignments'], v['fits']) == (16, 1), v
    # double_add (x + 4) * 2, query 4: x + 4 is symmetric, so two assignments fit (4 as the variable first, or second): accepted with more than one fit
    row = dict(prompt=prompt_of(lambda x: (x + 4) * 2, [2, 7, 13], 4))
    v = verdict(row, dict(calls=[('add 4 4', '8'), ('mul 8 2', '16')], answer='16'))
    assert v['verdict'] == 'accept' and v['fits'] == 2 and v['assignments'] == 8, v
    # a result that equals the query as well as a token: 3 alternatives (constant, x, the result)
    row = dict(prompt=prompt_of(lambda x: x + x + x, [2, 7, 13], 4))
    tr = C.Trace(dict(calls=[('add 2 2', '4'), ('add 4 4', '8')], answer='8'), row['prompt'], C.parse(row['prompt'])['spans']['query'], True)
    plan = C.value_plan(tr, 1, '4')
    assert [len(x) for x in plan if isinstance(x, C.Choice)] == [3, 3], plan
    # every assignment, put back on the query, reproduces the original try (the checker asserts it; here from outside)
    p = C.parse(row['prompt'])
    plans = [C.plan_of(tr, i, '4')[0] for i in range(3)]
    n = 0
    for temps in C.assignments(plans):
        assert C.execute(tr, temps, '4', False) == (tr.calls, tr.answer)
        n += 1
    assert n == C.n_assignments(plans) == 3 * 3
    # and the assertion is live: an assignment that does not reproduce the try raises, it is not a verdict
    bad = [list(x) for x in plans]
    bad[1][1], bad[1][3] = ('c', '9'), ('c', '4')
    try:
        C.run_assignment(tr, bad, p, True)
    except AssertionError:
        pass
    else:
        raise RuntimeError('a non-reproducing value assignment must raise AssertionError')
    print('ok value ambiguity: a query equal to a rule constant is accepted through enumeration (up to 16 assignments); every assignment reproduces the try')


def test_value_over_16_assignments_is_uncheckable():
    row = dict(prompt=prompt_of(lambda x: 2 * x, [3, 5, 9], 2))
    # 'add 2 2' twice: four tokens equal to the query -> 16 assignments, checkable; the second call decides the answer, so 4 assignments fit
    v = verdict(row, dict(calls=[('add 2 2', '4'), ('add 2 2', '4')], answer='4'))
    assert v['verdict'] == 'accept' and (v['assignments'], v['fits']) == (16, 4), v
    # a fifth token that may be x: 32 assignments -> uncheckable
    v = verdict(row, dict(calls=[('add 2 2', '4'), ('add 2 2', '4'), ('mul 2 1', '2')], answer='2'))
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'too many assignments' and v['assignments'] == 32 and not C.check(row, dict(calls=[('add 2 2', '4')] * 3, answer='4')), v
    v = verdict(row, dict(calls=[('add 2 2', '4')] * 3, answer='4'))
    assert v['verdict'] == 'uncheckable' and v['reason'] == 'too many assignments' and v['assignments'] == 64 and v['detail'] == '64 > 16', v      # six tokens that may be x
    # a token with several matches has 1 + matches choices: query 4, earlier results 4 and 4 -> each 4 of 'add 4 4' is a constant, x, r0 or r1: 4 x 4 = 16 assignments (the limit)
    row4 = dict(prompt=prompt_of(lambda x: x + 4, [3, 5, 9], 4))
    v = verdict(row4, dict(calls=[('add 2 2', '4'), ('add 1 3', '4'), ('add 4 4', '8')], answer='8'))
    assert v['verdict'] == 'accept' and (v['assignments'], v['fits']) == (16, 6), v          # fits: x in either place, the other a constant or either earlier 4 (2 x 3)
    v = verdict(row4, dict(calls=[('add 2 2', '4'), ('add 1 3', '4'), ('add 4 4', '8'), ('add 4 0', '4')], answer='4'))
    assert v['verdict'] == 'uncheckable' and v['assignments'] == 16 * 4 and v['reason'] == 'too many assignments', v
    print('ok value limit: 16 assignments are checked, more are uncheckable')


def test_value_mixed_copy_and_value_calls():
    """Per call: a call with a copied byte is read by its record, a call without one by value. Both orders; the answer is bound to the last result when its record has no copied byte."""
    row = dict(prompt=prompt_of(lambda x: 3 * x + 5, [2, 7, 13], 11))
    P = Prog(row['prompt'])
    t = P.trace([[('g', 'mul '), ('q',), ('g', ' 3')], [('g', 'add 33 5')]], [('g', '38')])
    v = verdict(row, t)
    assert v['verdict'] == 'accept' and v['path'] == 'mixed', v
    t = P.trace([[('g', 'mul 11 3')], [('g', 'add '), ('R', 0), ('g', ' 5')]], [('R', 1)])
    v = verdict(row, t)
    assert v['verdict'] == 'accept' and v['path'] == 'mixed', v
    # a copy record that really copies is still read as a record: the same try with all of call 0's bytes uncopied but one example-line byte copied is read by record ('11' is a constant)
    a = row['prompt'].index('13') + 1
    t = P.trace([[('g', 'mul 11 '), ('raw', a, 1)], [('g', 'add 33 5')]], [('g', '38')])
    v = verdict(row, t)
    assert v['verdict'] == 'reject' and v['path'] == 'mixed', v                                  # call 0 by record: 11 is a constant; call 1 by value: 33 may be call 0's result; x never read
    print('ok mixed: copy-record calls and value calls in one try')


def test_value_no_call_gives_no_record():
    """Addendum 1: a no-call answer has no record and reads as a constant: rejected 'never reads x' (even when it equals the query number or the right answer), so no record comes from it."""
    from custom_io import cb0
    row = dict(prompt=prompt_of(lambda x: x % 10, XS[0], 25))
    for ans in ('5', '25', '0'):
        for how in HOWS:
            t = strip(dict(calls=[], answer=ans), how)
            v = verdict(row, t)
            assert v['verdict'] == 'reject' and v['reason'] == 'never reads x' and v['path'] == 'none' and v['calls'] == 0 and v['assignments'] == 1, (ans, how, v)
            assert not C.check(row, t)
    # the day's records: nothing comes from a no-call try, a calling try `mod x 10` gives one
    good = dict(calls=[('mod 25 10', '5')], answer='5')
    no_call = dict(calls=[], answer='5')
    assert C.check(row, good) and not C.check(row, no_call)
    day = dict(tries=[[no_call, good, no_call]], fit=[[C.check(row, t) for t in (no_call, good, no_call)]])
    recs, counts = cb0.records([dict(row, id='r0', kind='last_digit')], day, seed=1)
    assert [r['trace'] for r in recs] == [good] and counts == dict(last_digit=1)
    day = dict(tries=[[no_call, no_call]], fit=[[C.check(row, no_call)] * 2])
    assert cb0.records([dict(row, id='r0', kind='last_digit')], day, seed=1)[0] == []
    # a calling try whose final answer is not the last result's string is uncheckable, on every record style
    for how in HOWS:
        v = verdict(row, strip(dict(calls=[('mod 25 10', '5')], answer='05'), how))
        assert v['verdict'] == 'uncheckable' and v['reason'] == 'answer is not the last result', v
    print('ok no-call tries give no record; a calling try whose answer is not the last result is uncheckable')


def test_value_mark3_corrupt_every_key():
    """Mark (3) for the value path: the verdicts of tries without copy records do not change when row['answer'] / row['accepted'] / 'kind' are corrupted or deleted."""
    for kind in KINDS:
        row, tr = reference(kind, XS[1], QS[0])
        for how in HOWS:
            t = strip(tr, how)
            base = verdict(row, t)
            assert base['verdict'] == 'accept'
            for mod in (dict(answer='xx', accepted=['zz']), dict(answer=None), dict(accepted=[]), dict(kind='affine'), dict(kind='nonsense', answer='1', accepted=['1'])):
                assert verdict(dict(row, **mod), copy.deepcopy(t)) == base, (kind, how, mod)
            assert verdict(dict(prompt=row['prompt']), t) == base
    print('ok value mark 3: verdicts do not depend on row answer / accepted / kind')


def test_summary_mark2_and_addenda():
    """Mark 2 counts uncheckable tries among calling tries only; per kind the no-call share and the share of accepted tries with more than one fitting assignment."""
    row = dict(prompt=prompt_of(lambda x: (x + 4) * 2, [2, 7, 13], 4))
    multi = dict(calls=[('add 4 4', '8'), ('mul 8 2', '16')], answer='16')               # two fitting assignments
    single = dict(calls=[('add 4 4', '8'), ('mul 8 3', '24')], answer='24')               # wrong constant: rejected
    right = dict(calls=[('add 4 4', '8'), ('mul 8 2', '16')], answer='16')
    unch = dict(calls=[('add 4 4', '8')], answer='9')                                      # answer is not the last result
    nocall = dict(calls=[], answer='16')
    vs = [verdict(row, t) for t in (multi, single, right, unch, nocall, nocall)]
    s = C.summarise(vs)
    assert s['n'] == 6 and s['calling'] == 4 and s['no_call'] == 2 and abs(s['no_call_share'] - 2 / 6) < 1e-12, s
    assert s['uncheckable_calling'] == 1 and s['uncheckable_calling_share'] == 0.25 and abs(s['uncheckable_calling_of_tries'] - 1 / 6) < 1e-12, s
    assert s['accepted'] == 2 and s['accepted_multi'] == 2 and s['accepted_multi_share'] == 1.0 and s['path'] == dict(value=3, none=2), s      # (the try whose answer is not the last result is judged before a path is chosen)
    assert s['verdict'] == dict(accept=2, reject=3, uncheckable=1), s
    # an uncheckable no-call try (a malformed trace) is not counted against mark 2
    bad = verdict(row, dict(calls=[], answer=None))
    assert bad['verdict'] == 'uncheckable' and bad['calls'] == 0
    assert C.summarise([bad])['uncheckable_calling'] == 0 and C.summarise([bad])['uncheckable_calling_share'] is None
    t = C.Tally()
    for kind, v in zip(('a', 'a', 'b', 'a', 'b', 'b'), vs):
        t.add(kind, v)
    sm = t.summary()
    assert sorted(sm['by_kind']) == ['a', 'b'] and sm['all'] == s and sm['by_kind']['a']['n'] == 3 and sm['by_kind']['b']['no_call'] == 2
    print('ok summary: mark 2 over calling tries, no-call share and multi-fit share per kind')


# ---- the copy record in the model ----
def old_greedy(self, Z, zmask, Xc, cmask, cids, mode, max_len=None, nocopy=False, ckeys=None, temperature=0.0, generator=None, bos=1, eos=2):
    """Verbatim copy of ByteWriter.greedy before the record was added."""
    B, N = cids.shape
    T = min(max_len or self.cap, self.cap)
    inp = torch.full((B, 1), bos, dtype=torch.long, device=cids.device)
    fb = torch.zeros(B, 1, N, device=cids.device)
    done = torch.zeros(B, dtype=torch.bool, device=cids.device)
    out = [[] for _ in range(B)]
    for i in range(T):
        p, gate, a = self.run(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy, ckeys)
        p = p[:, -1]
        if temperature > 0:
            nxt = torch.multinomial(p.pow(1 / temperature) + 1e-12, 1, generator=generator)[:, 0]
        else:
            nxt = p.argmax(-1)
        nxt = torch.where(done, torch.full_like(nxt, eos), nxt)
        for b in (~done & (nxt != eos)).nonzero()[:, 0].tolist():
            out[b].append(int(nxt[b]))
        done = done | (nxt == eos)
        if done.all():
            break
        inp = torch.cat([inp, nxt[:, None]], 1)
        fb = torch.cat([fb, ((1 - gate[:, -1:]) * a[:, -1])[:, None]], 1)
    return out, done


def tiny_writer(gate_bias=None, seed=0):
    torch.manual_seed(seed)
    d, B, N, Lz = 32, 4, 12, 3
    tok = torch.nn.Embedding(N_SPECIAL + 256, d)
    w = ByteWriter(d, tok, 10, dk=16, heads=2)
    for p in w.parameters():
        torch.nn.init.normal_(p, std=0.3) if p.dim() > 1 else None
    w.bias.data[EOS] = 2.0
    if gate_bias is not None:
        w.g_cp.bias.data[:] = gate_bias
    Z, Xc = torch.randn(B, Lz, d), torch.randn(B, N, d)
    cids = torch.randint(N_SPECIAL + 48, N_SPECIAL + 58, (B, N))
    cmask = torch.ones(B, N, dtype=torch.bool)
    cmask[1, 8:] = False
    return w, (Z, torch.ones(B, Lz, dtype=torch.bool), Xc, cmask, cids, torch.zeros(B, dtype=torch.long))


def test_greedy_record_false_is_identical():
    w, args = tiny_writer()
    for temp in (0.0, 1.0):
        for seed in range(4):
            g1, g2 = torch.Generator().manual_seed(seed), torch.Generator().manual_seed(seed)
            a = old_greedy(w, *args, temperature=temp, generator=g1)
            b = w.greedy(*args, temperature=temp, generator=g2)
            c = w.greedy(*args, temperature=temp, generator=torch.Generator().manual_seed(seed), record=False)
            r = w.greedy(*args, temperature=temp, generator=torch.Generator().manual_seed(seed), record=True)
            assert len(b) == 2 and a[0] == b[0] == c[0] == r[0] and a[1].equal(b[1]) and a[1].equal(r[1]), (temp, seed)
    print('ok writer.greedy: record=False equals the old code (argmax and sampled); record=True writes the same bytes')


def test_greedy_record_meaning():
    for gb, kind in ((None, 'random'), (-20.0, 'copy'), (20.0, 'generate')):
        w, (Z, zm, Xc, cm, cids, mode) = tiny_writer(gb)
        out, done, rec = w.greedy(Z, zm, Xc, cm, cids, mode, record=True)
        seen = 0
        for b, (o, rs) in enumerate(zip(out, rec)):
            assert len(o) == len(rs)
            for byte, r in zip(o, rs):
                seen += 1
                assert set(r) == {'copied', 'src', 'share'} and 0.0 <= r['share'] <= 1.0 + 1e-6
                assert r['copied'] == (r['share'] >= 0.5 - 1e-6) or abs(r['share'] - 0.5) < 1e-4
                if r['src'] is not None:
                    assert bool(cm[b, r['src']]) and int(cids[b, r['src']]) == byte
                if kind == 'copy':
                    assert r['copied'] and r['src'] is not None and r['share'] > 0.99, r
                if kind == 'generate':
                    assert not r['copied'] and r['share'] < 0.01, r
        assert seen > 0, kind
    # nocopy forces the generate part: nothing copied
    w, (Z, zm, Xc, cm, cids, mode) = tiny_writer(-20.0)
    out, done, rec = w.greedy(Z, zm, Xc, cm, cids, mode, nocopy=True, record=True)
    assert all(not r['copied'] and r['share'] == 0.0 for rs in rec for r in rs)
    # the share is the model's own: copy part = (1 - gate) * attention mass on positions holding the byte, checked against the first step by hand
    w, (Z, zm, Xc, cm, cids, mode) = tiny_writer()
    out, done, rec = w.greedy(Z, zm, Xc, cm, cids, mode, max_len=1, record=True)
    with torch.no_grad():
        p, gate, a = w.run(Z, zm, Xc, cm, cids, mode, torch.full((4, 1), 1), torch.zeros(4, 1, Xc.shape[1]), False, None)
    for b in range(4):
        if out[b]:
            c = out[b][0]
            hold = (cids[b] == c) & cm[b]
            cp = float((1 - gate[b, 0]) * a[b, 0][hold].sum())
            assert abs(rec[b][0]['share'] - cp / float(p[b, 0, c])) < 1e-5
            assert rec[b][0]['src'] is None or rec[b][0]['src'] == int(a[b, 0].masked_fill(~hold, -1).argmax())
    print('ok writer.greedy record: copied / src / share as defined (random, copy-only, generate-only, nocopy, by hand)')


def quiet_writer(m):
    """A tiny B3G2 whose writer writes short ASCII lines and whose run goes to the cap (3 call rounds)."""
    m.eval()
    bias = m.writer.bias.data
    bias[:] = 0.0
    bias[N_SPECIAL + 128:] = -30.0                                         # ASCII only, so text length = byte length
    bias[[i for i in range(N_SPECIAL) if i != EOS]] = -30.0                # no special ids: decode would drop them
    bias[EOS] = 6.0
    m.stop.bias.data[:] = -20.0                                            # never the learned stop
    m.cap = 4
    return m


def test_sample_traces_no_copy_record():
    """G2f (Ben's rule 2: calls and answers are written from the thinker's thoughts): the writer has no copy path, so sample_traces gives exactly the calls and the answer, with no copy
    record, and the checker reads every number by value (creative roadmap addendum 2). trace_loss takes the traces as they come."""
    m = quiet_writer(make(11))
    assert not m.writer.copy and not hasattr(m.writer, 'g_cp')
    rs = rows(8)
    b = batch_of(rs, V)
    before = {k: v.clone() for k, v in m.state_dict().items()}
    tr = m.sample_traces(b, 1.0, torch.Generator().manual_seed(3))
    assert all(before[k].equal(v) for k, v in m.state_dict().items())
    assert all(set(t) == {'calls', 'answer'} and isinstance(t['answer'], str) for t in tr)
    ncalls = sum(len(t['calls']) for t in tr)
    assert ncalls >= 3, ncalls
    m.train()
    l1, _ = m.trace_loss(b, tr)
    assert torch.isfinite(l1)
    print('ok sample_traces (G2f): %d calls, no copy record; trace_loss runs on them' % ncalls)


def test_checker_on_real_traces():
    """A tiny real B3G2 (random weights) on C2-shaped prompts: the checker runs on its real tries (no copy record: every number is read by value) and its counts add up; the same tries
    with the stripped record styles give the same verdicts."""
    m = quiet_writer(make(11))
    rs = [dict(id=f'c{i}', family='c2', prompt=prompt_of(list(KINDS.values())[i % 5], [2, 7, 13], 11 + i), answer='0', steps=[]) for i in range(16)]
    b = batch_of(rs, V)
    tr = m.sample_traces(b, 1.0, torch.Generator().manual_seed(3))
    vs = [C.check_try(r, t) for r, t in zip(rs, tr)]
    s = C.summarise(vs)
    assert s['n'] == 16 and sum(s['verdict'].values()) == 16 and s['calling'] + s['no_call'] == 16 and s['calling'] == sum(bool(t['calls']) for t in tr)
    assert all(v['verdict'] in ('accept', 'reject', 'uncheckable') and v['calls'] == len(t['calls']) for v, t in zip(vs, tr))
    assert all(v['verdict'] == 'reject' and v['reason'] == 'never reads x' for v, t in zip(vs, tr) if not t['calls'])         # a no-call answer is a constant
    assert not any(v['path'] in ('copy', 'mixed') for v in vs)                              # no copy record is ever read ('' = stopped before the path, e.g. rule 5)
    for style in ('empty', 'short', 'false'):
        assert [(v['verdict'], v['reason']) for v in vs] == [(w['verdict'], w['reason']) for w in (C.check_try(r, strip(t, style)) for r, t in zip(rs, tr))], style
    print('ok checker on real B3G2 tries: %d tries, %d calling, read by value (no copy record; stripped styles agree)' % (s['n'], s['calling']))


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
