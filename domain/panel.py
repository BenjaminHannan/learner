"""Sealed scoring panels for domain mode (DM-S sheet, and DM6 rpn). The model never sees these rows.

Own generator, own seeds (sheet 91001, rpn 91002). Nothing here imports the practice maker. The only imports from
this project are the two help tools (domain/tools): their caps, their vocabulary, their help prompts and evaluate().
evaluate() gives each row's answer and its step count. A candidate is redrawn when the tool answers '?', when the
prompt or answer breaks a cap, when the step count is over 7, when the shape is wrong, when the prompt repeats, or when
this file's own Python re-computation disagrees with the tool.

Sheet panel (1,000 rows = 10 kinds x (60 near + 40 far)):
  near: the help example's formula shape (checked by skeleton(): digit runs -> d, A/B -> c), range length 2-4 cells,
        grid 2-4 rows, values 1-99, either column for each reference, and no two references to the same cell.
  far:  grid 5-6 rows; SUM/MAX/MIN/PRODUCT use range length 5-6; the other column from the help example (each reference
        swapped for the two-column kinds); a second kind combined in the same formula with +, * or MOD(a,b). IF takes its
        second kind inside the comparison (IF costs 6 steps by itself, so nothing can be added after it).
        Two forced exceptions, both from the 7-step cap: COUNTIF costs 3n-1 steps (5 at 2 cells, 8 at 3), so far
        COUNTIF uses 2 cells; IF's partner costs at most 1 step.

RPN panel (800 rows = 8 kinds x (60 near + 40 far)):
  near: the help example's operator shape, values 1-99, and digit-run lengths (1 or 2 digits per number) different
        from the help example's. The practice maker keeps the example's digit-run lengths, so no near row can equal a
        practice prompt (DESIGN-AND-MARKS addendum A1; found 41 overlaps before this rule).
  far:  4 or 5 operators in a random postfix order, values 1-99, operators + - * / %. The help shapes have at most 3
        operators, so no far shape can equal one.

Run from the repo root:  python3 -m domain.panel            (v1: sheet.jsonl, rpn.jsonl; refuses to overwrite)
                           python3 -m domain.panel --v2       (v2, addendum A10: sheet.v2.jsonl, rpn.v2.jsonl, new seeds)
It writes sheet.jsonl and rpn.jsonl and a .sha256 for each into OUT_DIR, and refuses to replace existing files unless
main(overwrite=True) is called.
"""
import hashlib
import json
import math
import os
import random
import re
from collections import Counter

from domain.tools import ASCII, MAX_ANS, MAX_PROMPT, N_NUM, N_RES
from domain.tools import rpn as rpn_tool
from domain.tools import sheet as sheet_tool

SHEET_SEED = 91001
RPN_SEED = 91002
# v2 (addendum A10): a fresh draw with the same generator, counts and checks, written to new files (sheet.v2.jsonl,
# rpn.v2.jsonl). The v1 files are never rewritten by the v2 option.
V2_SHEET_SEED = 91011
V2_RPN_SEED = 91012
OUT_DIR = '/mnt/project-files/domain-mode/panel'
NEAR_PER_KIND, FAR_PER_KIND = 60, 40
MAX_TRIES = 200000  # a cell not full after this many draws is a bug in the generator, not a slow fill

SHEET_KINDS = ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF']
AGG = {'SUM': sum, 'MAX': max, 'MIN': min, 'PRODUCT': math.prod}
# The columns the help example uses, one letter per reference in reading order (IF: compare-left, compare-right, value, value).
HELP_COLS = {'SUM': 'A', 'MAX': 'A', 'MIN': 'B', 'PRODUCT': 'A', 'COUNTIF': 'A', 'cell arithmetic': 'AB',
             'division': 'AB', 'MOD': 'AB', 'ABS': 'AB', 'IF': 'ABAB'}

RPN_SHAPE = {'a b +': 'nn+', 'a b -': 'nn-', 'a b *': 'nn*', 'a b /': 'nn/', 'a b %': 'nn%',
             'a b + c *': 'nn+n*', 'a b c * +': 'nnn*+', 'a b + c d + *': 'nn+nn+*'}
RPN_OPS = '+-*/%'
RPN_HELP_RUNS = {h['kind']: tuple(len(t) for t in re.findall(r'\d+', h['prompt'])) for h in rpn_tool.help()}


def other(c):
    return 'B' if c == 'A' else 'A'


def skeleton(formula):
    """The shape of a formula: every digit run becomes d, every A or B becomes c."""
    return re.sub(r'\d+', 'd', re.sub(r'[AB]', 'c', formula))


def numbers(prompt):
    """How many numbers the model reads from a prompt (digit runs, as the model's prompt-number slots count them)."""
    return len(re.findall(r'[0-9]+', prompt))


def shape_of(prompt):
    return ''.join('n' if t.isdigit() else t for t in prompt.split()[1:])


def _mod(x, y):
    return x % y if y else None


def _div(x, y):
    return x // y if y and x % y == 0 else None


def _bin(f, x, y):
    return None if x is None or y is None else f(x, y)


def _pick(rng, n, k, cols):
    """k distinct cells as (column, row) pairs. cols: the column letter of each cell, or None to draw either column."""
    while True:
        pairs = [(cols[i] if cols else rng.choice('AB'), rng.randint(1, n)) for i in range(k)]
        if len(set(pairs)) == k:
            return pairs


def piece(kind, rng, n, cols, L):
    """One kind's formula on an n-row grid. cols: the column letter of each reference (help order), or None to draw
    each reference's column (either column). L: range length (range kinds only).
    Returns (formula text, value function of g = {'A': [...], 'B': [...]}; None where the calculator must refuse)."""
    if kind in AGG or kind == 'COUNTIF':
        c = cols[0] if cols else rng.choice('AB')
        r1 = rng.randint(1, n - L + 1)
        r2 = r1 + L - 1
        if kind in AGG:
            f = AGG[kind]
            return f'{kind}({c}{r1}:{c}{r2})', lambda g: f(g[c][r1 - 1:r2])
        k = rng.randint(1, 99)
        return f'COUNTIF({c}{r1}:{c}{r2},">{k}")', lambda g: sum(1 for x in g[c][r1 - 1:r2] if x > k)
    if kind == 'IF':
        (a, r), (b, s), (c, t), (d, u) = _pick(rng, n, 4, cols)
        return (f'IF({a}{r}>{b}{s},{c}{t},{d}{u})',
                lambda g: g[c][t - 1] if g[a][r - 1] > g[b][s - 1] else g[d][u - 1])
    (a, r), (b, s) = _pick(rng, n, 2, cols)
    if kind == 'cell arithmetic':
        return f'{a}{r}+{b}{s}*2', lambda g: g[a][r - 1] + 2 * g[b][s - 1]
    if kind == 'division':
        return f'{a}{r}/{b}{s}', lambda g: _div(g[a][r - 1], g[b][s - 1])
    if kind == 'MOD':
        return f'MOD({a}{r},{b}{s})', lambda g: _mod(g[a][r - 1], g[b][s - 1])
    if kind == 'ABS':
        return f'ABS({a}{r}-{b}{s})', lambda g: abs(g[a][r - 1] - g[b][s - 1])
    raise ValueError(kind)


def if_with_left(left, rng, n, cols):
    """IF(left > cell, value, value): the second kind sits in the comparison. cols: compare-right, value, value."""
    lt, lf = left
    (b, s), (c, t), (d, u) = _pick(rng, n, 3, cols)

    def fn(g):
        x = lf(g)
        if x is None:
            return None
        return g[c][t - 1] if x > g[b][s - 1] else g[d][u - 1]
    return f'IF({lt}>{b}{s},{c}{t},{d}{u})', fn


def combine(op, K, J):
    (kt, kf), (jt, jf) = K, J
    if op == '+':
        return f'{kt}+{jt}', lambda g: _bin(lambda x, y: x + y, kf(g), jf(g))
    if op == '*':
        return f'({kt})*({jt})', lambda g: _bin(lambda x, y: x * y, kf(g), jf(g))
    return f'MOD({kt},{jt})', lambda g: _bin(_mod, kf(g), jf(g))


def render(g, formula):
    return f"A: {' '.join(map(str, g['A']))} | B: {' '.join(map(str, g['B']))} ; ={formula}"


def sheet_candidate(kind, split, rng):
    """One candidate: (prompt, value function of the grid, the grid, the formula text)."""
    cols = HELP_COLS[kind]
    if split == 'near':
        if kind in AGG or kind == 'COUNTIF':
            L = rng.choice([2, 3, 4])
            n = rng.randint(L, 4)
        else:
            L = None
            n = rng.choice([2, 3, 4])
        formula, fn = piece(kind, rng, n, None, L)
    else:
        n = rng.choice([5, 6])
        far = ''.join(other(c) for c in cols)
        L = rng.randint(5, n) if kind in AGG else (2 if kind == 'COUNTIF' else None)
        partner = rng.choice([k for k in SHEET_KINDS if k not in (kind, 'IF')])
        if partner in AGG:
            pL = 2 if kind == 'IF' else rng.choice([2, 3])
        elif partner == 'COUNTIF':
            pL = 2
        else:
            pL = None
        J = piece(partner, rng, n, None, pL)
        if kind == 'IF':
            formula, fn = if_with_left(J, rng, n, far[1:])
        else:
            K = piece(kind, rng, n, far, L)
            formula, fn = combine(rng.choice(['+', '*', 'MOD']), K, J)
    g = {c: [rng.randint(1, 99) for _ in range(n)] for c in 'AB'}
    return render(g, formula), fn, g, formula


def sheet_draw(kind, split, rng):
    prompt, fn, g, formula = sheet_candidate(kind, split, rng)
    return prompt, fn(g), formula


def rpn_far_shape(rng):
    """A random postfix order with 4 or 5 operators: operands and operators in a valid stack order."""
    k = rng.choice([4, 5])
    shape, pushed, stack, ops_left = '', 0, 0, k
    while pushed < k + 1 or ops_left:
        can_op = stack >= 2 and ops_left > 0
        if pushed < k + 1 and (not can_op or rng.random() < 0.5):
            shape += 'n'
            pushed += 1
            stack += 1
        else:
            shape += rng.choice(RPN_OPS)
            stack -= 1
            ops_left -= 1
    return shape


def rpn_expect(tokens):
    """This file's own RPN value (None where the calculator must refuse)."""
    st = []
    for t in tokens:
        if t.isdigit():
            st.append(int(t))
            continue
        b, a = st.pop(), st.pop()
        if t == '+':
            v = a + b
        elif t == '-':
            v = a - b if a >= b else None
        elif t == '*':
            v = a * b
        elif t == '/':
            v = _div(a, b)
        else:
            v = _mod(a, b)
        if v is None:
            return None
        st.append(v)
    return st[0]


def digit_runs(tokens):
    return tuple(len(t) for t in tokens if t.isdigit())


def rpn_draw(kind, split, rng):
    if split == 'near':
        # redraw until the digit-run lengths differ from the help example's (see the module docstring)
        shape = RPN_SHAPE[kind]
        while True:
            tokens = [str(rng.randint(1, 99)) if ch == 'n' else ch for ch in shape]
            if digit_runs(tokens) != RPN_HELP_RUNS[kind]:
                break
    else:
        shape = rpn_far_shape(rng)
        tokens = [str(rng.randint(1, 99)) if ch == 'n' else ch for ch in shape]
    return 'rpn: ' + ' '.join(tokens), rpn_expect(tokens), shape


def fill_panel(domain, kinds, rng, draw, evaluate, help_prompts, shape_ok):
    """Draw until every (kind, split) cell is full. Returns (rows, per-cell stats)."""
    rows, stats, seen = [], {}, set()
    for ki, kind in enumerate(kinds, 1):
        for split, target in (('near', NEAR_PER_KIND), ('far', FAR_PER_KIND)):
            st = Counter()
            while st['accepted'] < target:
                st['tries'] += 1
                if st['tries'] > MAX_TRIES:
                    raise RuntimeError(f'{domain} {kind} {split}: not full after {MAX_TRIES} draws')
                prompt, expect, info = draw(kind, split, rng)
                res = evaluate(prompt)
                steps = len(res['steps'])
                if res['value'] == '?':
                    st['tool ?'] += 1
                elif expect is None or str(expect) != res['value']:
                    st['python disagrees'] += 1
                elif steps > N_RES:
                    st['steps over 7'] += 1
                elif len(prompt) > MAX_PROMPT:
                    st['prompt over cap'] += 1
                elif numbers(prompt) > N_NUM:
                    st['numbers over 16'] += 1
                elif len(res['value']) > MAX_ANS:
                    st['answer over 8'] += 1
                elif not shape_ok(kind, split, info):
                    st['shape'] += 1
                elif prompt in help_prompts:
                    st['help example'] += 1
                elif prompt in seen:
                    st['duplicate'] += 1
                else:
                    seen.add(prompt)
                    rows.append({'id': f'{domain}-{split}-{ki:02d}-{st["accepted"]:03d}', 'domain': domain,
                                 'kind': kind, 'split': split, 'prompt': prompt, 'answer': res['value'],
                                 'n_steps': steps})
                    st['accepted'] += 1
            stats[(kind, split)] = st
    return rows, stats


def build_sheet(seed=SHEET_SEED):
    rng = random.Random(seed)
    help_list = sheet_tool.help()
    assert [h['kind'] for h in help_list] == SHEET_KINDS
    help_skel = {h['kind']: skeleton(h['prompt'].split('; =')[1]) for h in help_list}
    help_prompts = {h['prompt'] for h in help_list}
    return fill_panel('sheet', SHEET_KINDS, rng, sheet_draw, sheet_tool.evaluate, help_prompts,
                      lambda kind, split, formula: split == 'far' or skeleton(formula) == help_skel[kind])


def build_rpn(seed=RPN_SEED):
    rng = random.Random(seed)
    help_list = rpn_tool.help()
    assert {h['kind']: shape_of(h['prompt']) for h in help_list} == RPN_SHAPE
    help_prompts = {h['prompt'] for h in help_list}
    help_shapes = set(RPN_SHAPE.values())
    return fill_panel('rpn', list(RPN_SHAPE), rng, rpn_draw, rpn_tool.evaluate, help_prompts,
                      lambda kind, split, shape: split == 'near' or shape not in help_shapes)


def hard_checks(name, rows, help_prompts):
    """Every cap and rule, asserted over the whole panel. Returns the counts it checked."""
    bad, seen = Counter(), set()
    for r in rows:
        p, a = r['prompt'], r['answer']
        if len(p) > MAX_PROMPT:
            bad['prompt over MAX_PROMPT'] += 1
        if numbers(p) > N_NUM:
            bad['over N_NUM numbers'] += 1
        if len(a) > MAX_ANS:
            bad['answer over MAX_ANS'] += 1
        if not 1 <= r['n_steps'] <= N_RES:
            bad['steps outside 1..N_RES'] += 1
        if not set(p + a) <= ASCII:
            bad['non-vocab character'] += 1
        if p in seen:
            bad['duplicate prompt'] += 1
        if p in help_prompts:
            bad['equals a help example'] += 1
        seen.add(p)
    assert not bad, (name, dict(bad))
    return {'rows': len(rows), 'unique_prompts': len(seen), 'violations': sum(bad.values())}


def write_panel(name, rows):
    path = os.path.join(OUT_DIR, name)
    data = ''.join(json.dumps(r) + '\n' for r in rows).encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with open(path, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == digest
    with open(path + '.sha256', 'w') as f:
        f.write(f'{digest}  {name}\n')
    return digest


def report(name, rows, stats):
    print(f'== {name}: {len(rows)} rows')
    for (kind, split), st in stats.items():
        reasons = ', '.join(f'{k} {v}' for k, v in st.items() if k not in ('tries', 'accepted') and v)
        steps = Counter(r['n_steps'] for r in rows if r['kind'] == kind and r['split'] == split)
        print(f"  {split:4s} {kind:16s} {st['accepted']:3d} rows, {st['tries']:6d} draws, steps {dict(sorted(steps.items()))}"
              + (f'; rejected: {reasons}' if reasons else ''))
    for (kind, split) in stats:
        for r in [r for r in rows if r['kind'] == kind and r['split'] == split][:3]:
            print(f"  sample {split} {kind}: {r['prompt']}  ->  {r['answer']}  [{r['n_steps']} steps]")


def main(overwrite=False, v2=False):
    """Build, check and write both panels. Without overwrite=True it refuses to replace existing files.
    v2=True writes sheet.v2.jsonl and rpn.v2.jsonl from the v2 seeds (addendum A10); the v1 files are not named here."""
    assert (N_NUM, N_RES, MAX_PROMPT, MAX_ANS) == (16, 7, 208, 8)
    sfx = '.v2' if v2 else ''
    names = (f'sheet{sfx}.jsonl', f'rpn{sfx}.jsonl')
    for n in names:
        for p in (os.path.join(OUT_DIR, n), os.path.join(OUT_DIR, n + '.sha256')):
            if os.path.exists(p) and not overwrite:
                raise SystemExit(f'refusing to overwrite {p}')
    sheet_rows, sheet_stats = build_sheet(V2_SHEET_SEED if v2 else SHEET_SEED)
    rpn_rows, rpn_stats = build_rpn(V2_RPN_SEED if v2 else RPN_SEED)
    clash = [r['prompt'] for r in rpn_rows
             if r['split'] == 'near' and digit_runs(r['prompt'].split()[1:]) == RPN_HELP_RUNS[r['kind']]]
    assert not clash, ('near RPN rows with the help digit-run lengths (practice can make these)', clash[:5])
    checks = {
        'sheet': hard_checks('sheet', sheet_rows, {h['prompt'] for h in sheet_tool.help()}),
        'rpn': hard_checks('rpn', rpn_rows, {h['prompt'] for h in rpn_tool.help()}),
    }
    print('hard checks:', checks)
    report('sheet', sheet_rows, sheet_stats)
    report('rpn', rpn_rows, rpn_stats)
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f'sha256 {names[0]}', write_panel(names[0], sheet_rows))
    print(f'sha256 {names[1]}', write_panel(names[1], rpn_rows))


if __name__ == '__main__':
    import sys
    main(v2='--v2' in sys.argv[1:])
