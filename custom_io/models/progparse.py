"""Ledger's supervision: a row's `steps` -> an executable slot program, and the row's talker mode. Hand-written, no search.
Workspace slots (27): 0..15 prompt numbers (regex \\d+, first 16), 16..19 constants 1 2 10 100, 20..26 results (<= 7 steps).
A step is (op, cands_a, cands_b, value): the operand slots that hold the operand values (any of them is a correct pointer).
row_targets(row) -> dict(prog, mode (0 NUM / 1 WORD / 2 GEN), ans (slots), word (word indices)), cached by row id."""
import re
from custom_io import capcount
from custom_io.data import word_spans

N_NUM, CONSTS, N_RES, W_MAX = 16, [1, 2, 10, 100], 7, 64
R0 = N_NUM + len(CONSTS)                       # first result slot
M = R0 + N_RES                                 # 27
OPS = ['NOOP', 'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'MIN', 'MAX', 'CMP']
COMM = (1, 3, 6, 7)                            # ADD MUL MIN MAX: operand order does not matter
SYM = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV'}
NUM_RE = re.compile(r'\d+')


def prompt_numbers(prompt):
    nums = [int(m.group()) for m in NUM_RE.finditer(prompt)]
    return nums[:N_NUM]      # the cut itself is counted once per distinct prompt in ledger.spans (capcount numbers_over)


def ex(op, a, b):
    """Reference executor (python ints). None = invalid (DIV only when exact)."""
    if op == 'ADD': return a + b
    if op == 'SUB': return a - b
    if op == 'MUL': return a * b
    if op == 'DIV': return a // b if b and a % b == 0 else None
    if op == 'MOD': return a % b if b else None
    if op == 'MIN': return min(a, b)
    if op == 'MAX': return max(a, b)
    if op == 'CMP': return (a > b) - (a < b)


class Builder:
    """Operand values resolve to the slots that hold them (prompt numbers, constants, earlier results)."""

    def __init__(self, nums):
        self.vals, self.n_prompt, self.prog, self.invert = list(nums) + CONSTS, len(nums), [], None

    def op(self, op, va, vb):
        ca = [i for i, x in enumerate(self.vals) if x == va]
        cb = [i for i, x in enumerate(self.vals) if x == vb]
        if (not ca or not cb) and self.invert is not None and op in SYM.values():
            # "a op ? = c" / "? op b = c": the answer is the missing operand, so the program runs the inverse op
            res, ans = self.invert
            has = lambda v: any(x == v for x in self.vals)
            if not ca and va == ans and has(res) and cb:
                self.invert = None
                return self.op(*{'ADD': ('SUB', res, vb), 'SUB': ('ADD', res, vb), 'MUL': ('DIV', res, vb), 'DIV': ('MUL', res, vb)}[op])
            if not cb and vb == ans and has(res) and ca:
                self.invert = None
                return self.op(*{'ADD': ('SUB', res, va), 'SUB': ('SUB', va, res), 'MUL': ('DIV', res, va), 'DIV': ('DIV', va, res)}[op])
        if not ca or not cb:
            raise ValueError(f'operand not found {va} {vb}')
        v = ex(op, va, vb)
        if v is None:
            raise ValueError('bad div')
        self.prog.append((op, ca, cb, v))
        self.vals.append(v)
        return v


def tok_expr(s):
    # a '-' directly before digits at the start or after an operator/'(' is a negative literal (a previous result)
    return re.findall(r'(?:(?<=^)|(?<=[-+*/(] )|(?<=[-+*/(]))-\d+|\d+|[-+*/()]', s)


def eval_expr(b, toks):
    """Left-to-right with * / precedence and parentheses; emits ops into the builder."""
    pos = 0

    def atom():
        nonlocal pos
        t = toks[pos]
        if t == '(':
            pos += 1
            v = expr()
            assert toks[pos] == ')'
            pos += 1
            return v
        if t == '-':
            raise ValueError('unary minus')
        pos += 1
        return int(t)

    def chain(sub, ops):
        nonlocal pos
        v = sub()
        while pos < len(toks) and toks[pos] in ops:
            o = toks[pos]
            pos += 1
            v = b.op(SYM[o], v, sub())
        return v

    term = lambda: chain(atom, '*/')
    expr = lambda: chain(term, '+-')
    v = expr()
    assert pos == len(toks)
    return v


def fold(b, op, xs):
    v = xs[0]
    for x in xs[1:]:
        v = b.op(op, v, x)
    return v


def to_program(r):
    nums = prompt_numbers(r['prompt'])
    b, last = Builder(nums), None
    if re.fullmatch(r'-?\d+', r['answer']):
        pn = [int(x) for x in NUM_RE.findall(r['prompt'])]
        if pn:
            b.invert = (pn[-1], int(r['answer']))     # the result of a missing-operand equation is its last number
    for s in r['steps']:
        s = s.strip()
        m = re.fullmatch(r'(\d+) ([-+*/]) (\d+) = (\d+)', s)
        if m and len(r['steps']) == 1 and re.fullmatch(r'\d+', r['answer']):       # arith_bare missing operand
            a, o, c2, res = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
            ans = int(r['answer'])
            if ans != res and res in nums:
                if a == ans and a not in nums:
                    last = b.op({'+': 'SUB', '-': 'ADD', '*': 'DIV', '/': 'MUL'}[o], res, c2)
                    continue
                if c2 == ans and c2 not in nums:
                    last = b.op({'+': 'SUB', '-': 'SUB', '*': 'DIV', '/': 'DIV'}[o], *((res, a) if o in '+*' else (a, res)))
                    continue
        m = re.fullmatch(r'([+-])(\d+) -> (-?\d+)', s)                   # state_update running total
        if m:
            last = b.op('ADD' if m.group(1) == '+' else 'SUB', last if last is not None else nums[0], int(m.group(2)))
            assert last == int(m.group(3)), 'state mismatch'
            continue
        m = re.fullmatch(r'(?:[a-z] = )?(.+?)(?:\s*=\s*(-?\d+))?', s)     # "x = a op b = c", "a op b = c", "a op b"
        lhs = m.group(1)
        mm = re.fullmatch(r'sum \[(.*)\]', s)
        if mm:
            last = fold(b, 'ADD', [int(x) for x in mm.group(1).split(',')])
            continue
        mm = re.fullmatch(r'(smallest|largest) of \[(.*)\]', s)
        if mm:
            last = fold(b, 'MIN' if mm.group(1) == 'smallest' else 'MAX', [int(x) for x in mm.group(2).split(',')])
            continue
        mm = re.fullmatch(r'compare (\d+) (\d+)', s)
        if mm:
            x, y = int(mm.group(1)), int(mm.group(2))
            if r['answer'].isdigit():                  # compare_numbers: the answer is one of them
                last = b.op('MIN' if int(r['answer']) == min(x, y) else 'MAX', x, y)
            else:                                      # compare_after: a sign, rendered by the talker
                last = b.op('CMP', x, y)
            continue
        mm = re.fullmatch(r'range of \[(.*)\]', s)
        if mm:
            xs = [int(x) for x in mm.group(1).split(',')]
            last = b.op('SUB', fold(b, 'MAX', xs), fold(b, 'MIN', xs))
            continue
        if re.fullmatch(r'[-+*/() \d]+', lhs) and re.search(r'\d', lhs) and re.search(r'[-+*/]', lhs):
            v = eval_expr(b, tok_expr(lhs))
            if m.group(2) is not None:
                assert v == int(m.group(2)), f'expr mismatch {s}'
            last = v
            continue
        raise ValueError('unparsed step')
    if not b.prog:
        raise ValueError('no ops')
    return b, last


def program_for(r):
    """-> (dict(prog, nums, mode 'NUM'|'GEN') or None, reason). Builder slot ids: nums, then constants, then results."""
    try:
        b, last = to_program(r)
    except (ValueError, AssertionError, IndexError, ZeroDivisionError, KeyError) as e:
        return None, str(e)[:40]
    ans = r['answer']
    if r['family'] == 'verify_claim' and ans in ('yes', 'no'):       # last value vs the claimed (last prompt) number
        b.op('CMP', last, b.vals[b.n_prompt - 1])
        return dict(prog=b.prog, nums=b.vals[:b.n_prompt], mode='GEN'), 'ok'
    if re.fullmatch(r'-?\d+', ans):
        if int(ans) != last:
            return None, 'final mismatch'
        return dict(prog=b.prog, nums=b.vals[:b.n_prompt], mode='NUM'), 'ok'
    return dict(prog=b.prog, nums=b.vals[:b.n_prompt], mode='GEN'), 'ok'


_CACHE = {}


def row_targets(r):
    """Cached by row id. prog = ((op index, cands_a, cands_b, value), ...) in workspace slot ids, at most N_RES steps."""
    t = _CACHE.get(r['id'])
    if t is None:
        t = _CACHE[r['id']] = _targets(r)
    return t


def _targets(r):
    nums, a, prog = prompt_numbers(r['prompt']), r['answer'], ()
    p, _ = program_for(r)
    if p is not None and len(p['prog']) > N_RES:
        capcount.hit('steps_over')
    if p is None and any(str(s).strip() for s in r.get('steps') or ()):
        capcount.hit('steps_unparsed')     # the row HAS worked steps the parser cannot turn into calls: it trains answer-only (PASS-MARKS addendum 23)
    if p is not None and len(p['prog']) <= N_RES:
        n = len(p['nums'])
        remap = lambda i: i if i < n else (N_NUM + i - n if i < n + len(CONSTS) else R0 + i - n - len(CONSTS))
        prog = tuple((OPS.index(op), tuple(remap(i) for i in ca), tuple(remap(i) for i in cb), v) for op, ca, cb, v in p['prog'])
    vals = nums + [None] * (N_NUM - len(nums)) + CONSTS + [s[3] for s in prog]
    words = [r['prompt'][s:e].lower() for s, e in word_spans(r['prompt'])][:W_MAX]      # words past W_MAX are counted in ledger.spans
    isint = re.fullmatch(r'-?\d+', a) is not None and str(int(a)) == a
    ans = tuple(i for i, u in enumerate(vals) if u is not None and isint and u == int(a)) if isint and (prog or int(a) in nums) else ()
    word = tuple(i for i, w in enumerate(words) if w == a.lower())
    mode = 0 if ans else (1 if word else 2)
    return dict(prog=prog, mode=mode, ans=ans if mode == 0 else (), word=word if mode == 1 else ())


def coverage(rows):
    """-> {family: {'n', 'prog' (% with a program), 'NUM', 'WORD', 'GEN' (% of rows by talker mode)}} and the overall dict."""
    fam = {}
    for r in rows:
        t = row_targets(r)
        c = fam.setdefault(r['family'], dict(n=0, prog=0, NUM=0, WORD=0, GEN=0))
        c['n'] += 1
        c['prog'] += bool(t['prog'])
        c[('NUM', 'WORD', 'GEN')[t['mode']]] += 1
    tot = {k: sum(c[k] for c in fam.values()) for k in ('n', 'prog', 'NUM', 'WORD', 'GEN')}
    pct = lambda c: {k: (v if k == 'n' else round(100 * v / max(c['n'], 1), 2)) for k, v in c.items()}
    return {'all': pct(tot), 'by_family': {f: pct(c) for f, c in sorted(fam.items())}}
