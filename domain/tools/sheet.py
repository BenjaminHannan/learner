"""Spreadsheet help tool (domain mode, DM-S).

Prompt: 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'. Columns are separated by '|' and listed top to bottom, so A2 is the
second number of column A. The formula after ';' starts with '='.

Works: SUM, MAX, MIN, PRODUCT over a range (A1:A3, one column); + - * / with * and / first, then left to right, and
parentheses; ABS(x-y); MOD(x,y); COUNTIF(range,">k"); IF(x>y,u,v). Functions nest in any way.

How each kind becomes calculator steps (no step is ever negative):
  SUM/MAX/MIN/PRODUCT  a chain of add/max/min/mul over the cells (n-1 steps for n cells)
  + - * /              one step per operator (a '-' with a < b gives '?')
  ABS(x-y)             max(x,y), min(x,y), then sub(max, min)
  MOD(x,y)             mod
  COUNTIF(range,">k")  per cell t = cmp(max(x,k),k), which is 1 when x>k and 0 otherwise (cmp never sees a value
                       below k, so it never gives -1); the t's are added (3n-1 steps for n cells)
  IF(x>y,u,v)          t = cmp(max(x,y),y) (1 when x>y); result = add(mul(t,u), mul(sub(1,t),v)) (6 steps, cells only)

value is '?' when the prompt cannot be parsed, a cell or range is out of the grid, a range is not in one column, a
step would be negative, or the calculator gives '?' (for example division that is not exact, or MOD by 0).
"""
import re

from domain.tools import BIG, Fail, execute

NAME = 'sheet'

BIN_OP = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div'}
AGG_OP = {'SUM': 'add', 'MAX': 'max', 'MIN': 'min', 'PRODUCT': 'mul'}
TOKEN = re.compile(r'\s*(?:("[^"]*")|([A-Z][0-9]+)|([A-Z]+)|([0-9]+)|([-+*/(),:<>]))')

# (kind, prompt, answer): one worked example per kind (values 1-99).
HELP = [
    ('SUM', 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)', '13'),
    ('MAX', 'A: 4 7 2 | B: 3 5 1 ; =MAX(A1:A3)', '7'),
    ('MIN', 'A: 4 7 2 | B: 3 5 1 ; =MIN(B1:B3)', '1'),
    ('PRODUCT', 'A: 4 7 2 | B: 3 5 1 ; =PRODUCT(A1:A3)', '56'),
    ('cell arithmetic', 'A: 4 7 2 | B: 3 5 1 ; =A1+B2*2', '14'),
    ('division', 'A: 8 7 2 | B: 2 5 1 ; =A1/B1', '4'),
    ('MOD', 'A: 4 7 2 | B: 3 5 1 ; =MOD(A2,B2)', '2'),
    ('ABS', 'A: 4 7 2 | B: 3 5 1 ; =ABS(A1-B1)', '1'),
    ('COUNTIF', 'A: 4 7 2 | B: 3 5 1 ; =COUNTIF(A1:A2,">3")', '2'),
    ('IF', 'A: 4 7 2 | B: 3 5 1 ; =IF(A1>B1,A2,B2)', '7'),
]


def help():
    """The help page: one {kind, prompt, answer} dict per kind."""
    return [{'kind': k, 'prompt': p, 'answer': a} for k, p, a in HELP]


def _tokens(text):
    toks, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if m is None:
            raise Fail('cannot read the formula at %d' % pos)
        pos = m.end()
        if m.group(1) is not None:
            toks.append(('str', m.group(1)))
        elif m.group(2) is not None:
            toks.append(('ref', m.group(2)))
        elif m.group(3) is not None:
            toks.append(('name', m.group(3)))
        elif m.group(4) is not None:
            toks.append(('num', m.group(4)))
        else:
            toks.append(('op', m.group(5)))
    return toks


class _Parser:
    """Recursive descent over the tokens. Nodes: ('num', v), ('ref', col, row), ('bin', op, L, R), ('SUM', rng),
    ('ABS', e), ('MOD', a, b), ('COUNTIF', rng, k), ('IF', L, R, X, Y), where rng = (col, r1, r2)."""

    def __init__(self, toks):
        self.toks, self.i = toks, 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def expect(self, ch):
        if self.peek() != ('op', ch):
            raise Fail('expected ' + ch)
        self.i += 1

    def expr(self):
        node = self.term()
        while self.peek()[0] == 'op' and self.peek()[1] in ('+', '-'):
            op = self.peek()[1]
            self.i += 1
            node = ('bin', op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.peek()[0] == 'op' and self.peek()[1] in ('*', '/'):
            op = self.peek()[1]
            self.i += 1
            node = ('bin', op, node, self.factor())
        return node

    def factor(self):
        kind, text = self.peek()
        if kind == 'num':
            self.i += 1
            if int(text) >= BIG:
                raise Fail('number too large')
            return ('num', int(text))
        if kind == 'ref':
            self.i += 1
            if self.peek() == ('op', ':'):
                raise Fail('a range is only allowed inside a function')
            return ('ref', text[0], int(text[1:]))
        if (kind, text) == ('op', '('):
            self.i += 1
            node = self.expr()
            self.expect(')')
            return node
        if kind == 'name':
            self.i += 1
            self.expect('(')
            node = self.call(text)
            self.expect(')')
            return node
        raise Fail('unexpected token')

    def ref(self):
        kind, text = self.peek()
        if kind != 'ref':
            raise Fail('expected a cell')
        self.i += 1
        return text[0], int(text[1:])

    def range_(self):
        c1, r1 = self.ref()
        self.expect(':')
        c2, r2 = self.ref()
        if c1 != c2 or r1 > r2:
            raise Fail('a range must run down one column')
        return c1, r1, r2

    def criterion(self):
        kind, text = self.peek()
        m = re.fullmatch(r'"\s*>\s*([0-9]+)\s*"', text) if kind == 'str' else None
        if m is None:
            raise Fail('COUNTIF needs a ">k" criterion')
        self.i += 1
        k = int(m.group(1))
        if k >= BIG:
            raise Fail('number too large')
        return k

    def call(self, name):
        if name in AGG_OP:
            return (name, self.range_())
        if name == 'COUNTIF':
            rng = self.range_()
            self.expect(',')
            return ('COUNTIF', rng, self.criterion())
        if name == 'ABS':
            return ('ABS', self.expr())
        if name == 'MOD':
            a = self.expr()
            self.expect(',')
            return ('MOD', a, self.expr())
        if name == 'IF':
            left = self.expr()
            self.expect('>')
            right = self.expr()
            self.expect(',')
            x = self.expr()
            self.expect(',')
            return ('IF', left, right, x, self.expr())
        raise Fail('unknown function ' + name)


def _parse_grid(text):
    cols = {}
    for part in text.split('|'):
        m = re.fullmatch(r'\s*([A-Z])\s*:([0-9\s]*)', part)
        if m is None or m.group(1) in cols:
            raise Fail('bad grid column')
        vals = [int(v) for v in m.group(2).split()]
        if any(v >= BIG for v in vals):
            raise Fail('number too large')
        cols[m.group(1)] = vals
    return cols


def _cells(grid, col, r1, r2=None):
    """The values of cells r1..r2 of one column (r2 defaults to r1)."""
    r2 = r1 if r2 is None else r2
    if col not in grid or r1 < 1 or r2 > len(grid[col]):
        raise Fail('cell %s%d or %s%d is not in the grid' % (col, r1, col, r2))
    return grid[col][r1 - 1:r2]


def _ev(node, grid, calc_run):
    kind = node[0]
    if kind == 'num':
        return node[1]
    if kind == 'ref':
        return _cells(grid, node[1], node[2])[0]
    if kind == 'bin':
        a = _ev(node[2], grid, calc_run)
        b = _ev(node[3], grid, calc_run)
        return calc_run.call(BIN_OP[node[1]], a, b)
    if kind in AGG_OP:
        vals = _cells(grid, *node[1])
        acc = vals[0]
        for v in vals[1:]:
            acc = calc_run.call(AGG_OP[kind], acc, v)
        return acc
    if kind == 'ABS':
        arg = node[1]
        if arg[0] == 'bin' and arg[1] == '-':
            x = _ev(arg[2], grid, calc_run)
            y = _ev(arg[3], grid, calc_run)
            hi = calc_run.call('max', x, y)
            lo = calc_run.call('min', x, y)
            return calc_run.call('sub', hi, lo)
        return _ev(arg, grid, calc_run)
    if kind == 'MOD':
        a = _ev(node[1], grid, calc_run)
        b = _ev(node[2], grid, calc_run)
        return calc_run.call('mod', a, b)
    if kind == 'COUNTIF':
        k, total = node[2], None
        for x in _cells(grid, *node[1]):
            t = calc_run.call('cmp', calc_run.call('max', x, k), k)
            total = t if total is None else calc_run.call('add', total, t)
        return total
    if kind == 'IF':
        vl = _ev(node[1], grid, calc_run)
        vr = _ev(node[2], grid, calc_run)
        t = calc_run.call('cmp', calc_run.call('max', vl, vr), vr)  # 1 when left > right, else 0
        vx = _ev(node[3], grid, calc_run)
        vy = _ev(node[4], grid, calc_run)
        p = calc_run.call('mul', t, vx)
        u = calc_run.call('sub', 1, t)
        q = calc_run.call('mul', u, vy)
        return calc_run.call('add', p, q)
    raise Fail('unknown node ' + kind)


def _solve(prompt, calc_run):
    if prompt.count(';') != 1:
        raise Fail('need exactly one ;')
    grid_text, formula = prompt.split(';')
    formula = formula.strip()
    if not formula.startswith('='):
        raise Fail('formula must start with =')
    grid = _parse_grid(grid_text)
    p = _Parser(_tokens(formula[1:]))
    node = p.expr()
    if p.peek()[0] is not None:
        raise Fail('text after the formula')
    return _ev(node, grid, calc_run)


def evaluate(prompt):
    """{'value': str, 'steps': [(op, a, b, result), ...]} for a sheet prompt; value '?' if it cannot run."""
    if not isinstance(prompt, str):
        return {'value': '?', 'steps': []}
    return execute(lambda calc_run: _solve(prompt, calc_run))
