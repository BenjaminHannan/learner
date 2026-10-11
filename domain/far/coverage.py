#!/usr/bin/env python3
"""Practice coverage against the far-transfer properties (domain mode, diagnosis).

Reads the v7 spreadsheet runs (sheet-s200-v7, sheet-s201-v7) and the v7 RPN run (rpn-s200-v7) from their
log.jsonl. Practice rows are events 'row' with source 'own' or 'tool'; 'diary' rows (old skills) are skipped.
Each prompt is parsed (pure Python: no model, no torch) and measured against the far-transfer properties.
Writes coverage.json and coverage.md to the output folder and prints a short summary.

Run from /home/user/learner:  python3 domain/far/coverage.py [OUT_DIR]
"""
import collections
import json
import os
import re
import sys

RUN_DIR = '/mnt/project-files/domain-mode/runs'
RUNS = [('sheet-s200-v7', 'sheet'), ('sheet-s201-v7', 'sheet'), ('rpn-s200-v7', 'rpn')]
DEFAULT_OUT = '/mnt/project-files/far-transfer/diag'
SHEET_FUNCS = ('SUM', 'MAX', 'MIN', 'PRODUCT', 'ABS', 'MOD', 'COUNTIF', 'IF')
SHEET_BIN = '+-*/'
RPN_OPS = ('+', '-', '*', '/', '%', 'max', 'min')
TOKEN = re.compile(r'(?:("[^"]*")|([A-Z]+[0-9]+)|([A-Z]+)|([0-9]+)|([-+*/(),:<>=]))')
TOKEN_KINDS = ('str', 'cell', 'word', 'num', 'punct')
FAR_ROWS = (5, 6)


def tokenize(text):
    """Tokens as (kind, text); kinds str, cell, word, num, punct. ValueError on any other character."""
    out = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        m = TOKEN.match(text, pos)
        if m is None:
            raise ValueError('bad character %r' % text[pos])
        pos = m.end()
        for k, g in zip(TOKEN_KINDS, m.groups()):
            if g is not None:
                out.append((k, g))
                break
    return out


def cell(text):
    """'A12' -> ('A', 12)."""
    m = re.fullmatch(r'([A-Z]+)([0-9]+)', text)
    return m.group(1), int(m.group(2))


def parse_sheet(prompt):
    """Measure one spreadsheet prompt: 'A: 4 7 2 | B: 3 5 1 ; =SUM(A1:A3)'."""
    head, sep, formula = prompt.partition(';')
    if not sep:
        raise ValueError('no formula')
    cols = {}
    for part in head.split('|'):
        m = re.fullmatch(r'\s*([A-Z])\s*:([0-9\s]*)', part)
        if m is None or m.group(1) in cols:
            raise ValueError('grid')
        cols[m.group(1)] = [int(v) for v in m.group(2).split()]
    formula = formula.strip()
    if formula.startswith('='):
        formula = formula[1:]
    toks = tokenize(formula)
    refs, ranges, funcs, shape = [], [], [], []
    n_bin = n_bin_out = 0
    stack = []  # one entry per open '(': the function name, or None for a plain bracket
    i = 0
    while i < len(toks):
        kind, text = toks[i]
        if kind == 'word':
            if i + 1 >= len(toks) or toks[i + 1] != ('punct', '('):
                raise ValueError('bare word ' + text)
            funcs.append(text)
            stack.append(text)
            shape.append(text + '(')
            i += 2
            continue
        if kind == 'cell':
            if i + 2 < len(toks) and toks[i + 1] == ('punct', ':') and toks[i + 2][0] == 'cell':
                ranges.append((cell(text), cell(toks[i + 2][1])))
                shape.append('r')
                i += 3
                continue
            refs.append(cell(text))
            shape.append('c')
        elif kind == 'num':
            shape.append('n')
        elif kind == 'str':
            shape.append('s')
        else:
            if text == '(':
                stack.append(None)
            elif text == ')':
                if not stack:
                    raise ValueError('unbalanced )')
                stack.pop()
            elif text in SHEET_BIN:
                n_bin += 1
                if all(f is None for f in stack):
                    n_bin_out += 1  # not inside any function call
            shape.append(text)
        i += 1
    if stack:
        raise ValueError('unclosed (')

    rng_cells, rng_end, rows_hit = [], [], []
    cross = 0
    for (c1, r1), (c2, r2) in ranges:
        lo, hi = min(r1, r2), max(r1, r2)
        rng_cells.append(hi - lo + 1)
        rng_end.append(hi)
        cross += c1 != c2
        rows_hit.append((lo, hi))
    for _, r in refs:
        rows_hit.append((r, r))
    col_len = {c: len(v) for c, v in cols.items()}
    nums = [v for vals in cols.values() for v in vals]
    return {
        'n_cols': len(cols),
        'col_len': sorted(col_len.values()),
        'grid_rows': max(col_len.values() or [0]),
        'grid_rows_min': min(col_len.values() or [0]),
        'grid_max_value': max(nums or [0]),
        'n_refs': len(refs),
        'range_cells': rng_cells,
        'range_end_rows': rng_end,
        'max_range_cells': max(rng_cells or [0]),
        'cross_col_ranges': cross,
        'cols_ref': sorted({c for c, _ in refs} | {c for rg in ranges for c, _ in rg}),
        'max_row_ref': max([hi for _, hi in rows_hit] or [0]),
        'touch_5_6': any(lo <= x <= hi for lo, hi in rows_hit for x in FAR_ROWS),
        'endpoint_5_6': any(r in FAR_ROWS for _, r in refs)
                        or any(r in FAR_ROWS for rg in ranges for _, r in rg),
        'funcs': funcs,
        'n_func': len(funcs),
        'unknown_funcs': [f for f in funcs if f not in SHEET_FUNCS],
        'n_bin': n_bin,
        'n_bin_outside': n_bin_out,
        'two_kinds': len(funcs) >= 2 or (len(funcs) >= 1 and n_bin_out >= 1),
        'shape': ''.join(shape),
    }


def parse_rpn(prompt):
    """Measure one RPN prompt: 'rpn: 3 4 + 2 *'."""
    m = re.fullmatch(r'\s*rpn:(.*)', prompt, re.S)
    if m is None:
        raise ValueError('not rpn')
    nums, ops, shape = [], [], []
    for t in m.group(1).split():
        if re.fullmatch(r'[0-9]+', t):
            nums.append(t)
            shape.append('n')
        elif t in RPN_OPS:
            ops.append(t)
            shape.append(t)
        else:
            raise ValueError('token ' + t)
    return {
        'n_nums': len(nums),
        'n_ops': len(ops),
        'digits': [len(t) for t in nums],
        'max_digits': max((len(t) for t in nums), default=0),
        'max_value': max((int(t) for t in nums), default=0),
        'ops': ops,
        'shape': ' '.join(shape),
    }


def answer_int(a):
    try:
        return int(a)
    except (TypeError, ValueError):
        return None


def analyse(name, family):
    """Parse the practice rows of one run. Returns the rows plus the bookkeeping counts."""
    path = os.path.join(RUN_DIR, name, 'log.jsonl')
    sources = collections.Counter()
    rows, fails, days, prompts = [], [], [], set()
    bad = 0
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if d.get('event') != 'row':
                continue
            src = d.get('source')
            sources[str(src)] += 1
            if src not in ('own', 'tool'):
                continue
            try:
                m = parse_sheet(d['prompt']) if family == 'sheet' else parse_rpn(d['prompt'])
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                fails.append(str(e)[:60])
                continue
            steps = d.get('steps') or []
            m.update(run=name, family=family, source=src, kind=str(d.get('kind')), day=d.get('day'),
                     prompt=d['prompt'], answer=d.get('answer'), answer_int=answer_int(d.get('answer')),
                     n_steps=len(steps))
            rows.append(m)
            prompts.add(d['prompt'])
            if isinstance(d.get('day'), int):
                days.append(d['day'])
    return {
        'name': name, 'family': family, 'rows': rows, 'fails': fails, 'bad_lines': bad,
        'sources': dict(sources), 'unique_prompts': len(prompts),
        'days': [min(days), max(days)] if days else None,
    }


def share(rows, pred):
    k = sum(1 for r in rows if pred(r))
    n = len(rows)
    return {'n': k, 'of': n, 'share': round(k / n, 4) if n else None}


def hist(values):
    c = collections.Counter(values)
    return {str(k): c[k] for k in sorted(c)}


def largest(rows, fields):
    out = {}
    for f in fields:
        if not rows:
            break
        best = max(rows, key=lambda r: r[f] if r[f] is not None else -1)
        if best[f] is None:
            continue
        out[f] = {'value': best[f], 'kind': best['kind'], 'run': best['run'], 'prompt': best['prompt']}
    return out


SHEET_FAR = collections.OrderedDict([
    ('grid_ge5_rows', lambda r: r['grid_rows'] >= 5),
    ('range_ge5_cells', lambda r: r['max_range_cells'] >= 5),
    ('ref_row5_or_6', lambda r: r['touch_5_6']),
    ('two_kinds', lambda r: r['two_kinds']),
    ('ref_endpoint_row5_or_6', lambda r: r['endpoint_5_6']),
    ('any_sheet_far', lambda r: r['grid_rows'] >= 5 or r['max_range_cells'] >= 5
                                or r['touch_5_6'] or r['two_kinds']),
])


def sheet_summary(rows):
    return {
        'rows': len(rows),
        'far': {k: share(rows, f) for k, f in SHEET_FAR.items()},
        'hist': {
            'grid_rows': hist(r['grid_rows'] for r in rows),
            'grid_rows_min': hist(r['grid_rows_min'] for r in rows),
            'col_len': hist(x for r in rows for x in r['col_len']),
            'n_cols': hist(r['n_cols'] for r in rows),
            'range_cells': hist(x for r in rows for x in r['range_cells']),
            'range_end_row': hist(x for r in rows for x in r['range_end_rows']),
            'max_row_ref': hist(r['max_row_ref'] for r in rows),
            'n_func': hist(r['n_func'] for r in rows),
            'n_bin': hist(r['n_bin'] for r in rows),
            'n_bin_outside': hist(r['n_bin_outside'] for r in rows),
            'n_steps': hist(r['n_steps'] for r in rows),
        },
        'func_names': dict(collections.Counter(f for r in rows for f in r['funcs'])),
        'answer_unknown': sum(1 for r in rows if r['answer_int'] is None),
        'largest': largest(rows, ['grid_rows', 'max_range_cells', 'max_row_ref', 'n_func', 'n_bin',
                                  'n_steps', 'grid_max_value', 'answer_int']),
    }


def rpn_summary(rows):
    return {
        'rows': len(rows),
        'far': {'ops_ge4': share(rows, lambda r: r['n_ops'] >= 4)},
        'hist': {
            'n_ops': hist(r['n_ops'] for r in rows),
            'n_nums': hist(r['n_nums'] for r in rows),
            'n_steps': hist(r['n_steps'] for r in rows),
            'digits_per_number': hist(d for r in rows for d in r['digits']),
            'max_digits_per_row': hist(r['max_digits'] for r in rows),
        },
        'op_counts': dict(collections.Counter(o for r in rows for o in r['ops'])),
        'answer_unknown': sum(1 for r in rows if r['answer_int'] is None),
        'largest': largest(rows, ['n_ops', 'n_nums', 'max_digits', 'max_value', 'answer_int', 'n_steps']),
    }


def shapes_top(rows, k=10):
    return [[s, n] for s, n in collections.Counter(r['shape'] for r in rows).most_common(k)]


def group(rows, family):
    summary = sheet_summary if family == 'sheet' else rpn_summary
    kinds = sorted({r['kind'] for r in rows})
    out = {'pooled': summary(rows), 'by_kind': {k: summary([r for r in rows if r['kind'] == k]) for k in kinds},
           'shapes_top': shapes_top(rows)}
    return out


DEFINITIONS = {
    'practice_rows': "event == 'row' and source in ('own', 'tool'); 'diary' rows skipped",
    'grid_rows': 'numbers in the longest column of the grid (grid_rows_min: shortest column)',
    'range_cells': 'cells in one range reference, A1:A5 = 5 (range_end_row = its last row)',
    'ref_row5_or_6': 'some cell or range in the formula covers row 5 or row 6 (a range A3:A6 counts)',
    'ref_endpoint_row5_or_6': 'a written row number (cell or range end) is 5 or 6 (stricter variant)',
    'two_kinds': 'two or more of SUM MAX MIN PRODUCT ABS MOD COUNTIF IF in one formula, or one of them '
                 'plus a + - * / outside its parentheses',
    'rpn_ops_ge4': 'RPN operators (+ - * / % max min) >= 4',
    'any_sheet_far': 'extra: any of the four sheet properties (grid_ge5_rows, range_ge5_cells, ref_row5_or_6, '
                     'two_kinds)',
}

SHEET_TABLE = [('grid >= 5 rows', 'grid_ge5_rows'), ('a range >= 5 cells', 'range_ge5_cells'),
               ('any ref to row 5 or 6', 'ref_row5_or_6'), ('two kinds in one formula', 'two_kinds'),
               ('ref endpoint is row 5 or 6 (strict)', 'ref_endpoint_row5_or_6'),
               ('any of the four (extra)', 'any_sheet_far')]


def fmt_share(s):
    if not s or not s['of']:
        return 'n/a'
    return '%d/%d (%.1f%%)' % (s['n'], s['of'], 100.0 * s['share'])


def fmt_hist(h):
    return ', '.join('%s:%d' % (k, v) for k, v in h.items()) or 'none'


def to_md(doc):
    L = []
    a = L.append
    runs = doc['runs']
    sp = doc['sheet']['pooled']
    a('# Practice coverage vs far-transfer properties')
    a('')
    a('Measured (shown) from the training logs by `domain/far/coverage.py`. Parsing only: no model was run and '
      'nothing was trained. Practice rows = `event == row` with source `own` or `tool`; `diary` rows (old skills) '
      'are skipped.')
    a('')
    a('## Runs')
    a('| run | practice rows | unique prompts | diary rows skipped | parse failures | days |')
    a('|---|---|---|---|---|---|')
    for name, info in runs.items():
        a('| %s | %d | %d | %d | %d | %s |' % (name, info['practice_rows'], info['unique_prompts'],
                                             info['sources'].get('diary', 0), info['parse_failures'],
                                             '%s-%s' % tuple(info['days']) if info['days'] else 'n/a'))
    a('')
    a('## Far-property shares (practice rows)')
    a('| property | sheet pooled (s200+s201) | sheet-s200-v7 | sheet-s201-v7 |')
    a('|---|---|---|---|')
    byrun = doc['sheet']['by_run']
    for label, key in SHEET_TABLE:
        a('| %s | %s | %s | %s |' % (label, fmt_share(sp['far'][key]),
                                    fmt_share(byrun['sheet-s200-v7']['far'][key]),
                                    fmt_share(byrun['sheet-s201-v7']['far'][key])))
    a('| RPN: >= 4 operators (rpn-s200-v7) | %s | | |' % fmt_share(doc['rpn']['pooled']['far']['ops_ge4']))
    a('')
    a('## Sheet by kind (pooled runs)')
    a('| kind | rows | grid >= 5 | range >= 5 cells | ref row 5/6 | two kinds | max grid rows | max range cells |')
    a('|---|---|---|---|---|---|---|---|')
    for k, s in doc['sheet']['by_kind'].items():
        lg = s['largest']
        a('| %s | %d | %s | %s | %s | %s | %s | %s |' % (
            k, s['rows'], fmt_share(s['far']['grid_ge5_rows']), fmt_share(s['far']['range_ge5_cells']),
            fmt_share(s['far']['ref_row5_or_6']), fmt_share(s['far']['two_kinds']),
            lg.get('grid_rows', {}).get('value', 'n/a'), lg.get('max_range_cells', {}).get('value', 'n/a')))
    a('')
    a('## Sheet histograms (pooled, value:count)')
    for k, h in sp['hist'].items():
        a('- %s: %s' % (k, fmt_hist(h)))
    a('- function names: %s' % fmt_hist(sp['func_names']))
    a('- answers that are not a number: %d' % sp['answer_unknown'])
    a('')
    a('## Sheet largest seen (pooled)')
    a('| measure | largest | kind | run | prompt |')
    a('|---|---|---|---|---|')
    for k, v in sp['largest'].items():
        a('| %s | %s | %s | %s | `%s` |' % (k, v['value'], v['kind'], v['run'], v['prompt']))
    a('')
    a('## Sheet top formula shapes (pooled; c cell, r range, n number, s string)')
    a(', '.join('`%s` %d' % (s, n) for s, n in doc['sheet']['shapes_top']))
    a('')
    rp = doc['rpn']['pooled']
    a('## RPN (rpn-s200-v7)')
    a('- operators per row: %s' % fmt_hist(rp['hist']['n_ops']))
    a('- numbers per row: %s' % fmt_hist(rp['hist']['n_nums']))
    a('- steps per row: %s' % fmt_hist(rp['hist']['n_steps']))
    a('- digits per number: %s' % fmt_hist(rp['hist']['digits_per_number']))
    a('- max digits per row: %s' % fmt_hist(rp['hist']['max_digits_per_row']))
    a('- operator tokens: %s' % fmt_hist(rp['op_counts']))
    a('- largest: ' + '; '.join('%s %s (`%s`)' % (k, v['value'], v['prompt']) for k, v in rp['largest'].items()))
    a('- shapes (top): %s' % ', '.join('`%s` %d' % (s, n) for s, n in doc['rpn']['shapes_top']))
    a('')
    a('## Definitions')
    for k, v in DEFINITIONS.items():
        a('- %s: %s' % (k, v))
    a('')
    return '\n'.join(L)


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else DEFAULT_OUT
    results = [analyse(name, fam) for name, fam in RUNS]
    sheet_rows = [r for res in results if res['family'] == 'sheet' for r in res['rows']]
    rpn_rows = [r for res in results if res['family'] == 'rpn' for r in res['rows']]
    runs = {}
    for res in results:
        runs[res['name']] = {
            'family': res['family'], 'practice_rows': len(res['rows']), 'unique_prompts': res['unique_prompts'],
            'sources': res['sources'], 'parse_failures': len(res['fails']), 'bad_lines': res['bad_lines'],
            'days': res['days'], 'parse_failure_examples': sorted(set(res['fails']))[:5],
        }
    sheet = group(sheet_rows, 'sheet')
    sheet['by_run'] = {res['name']: sheet_summary(res['rows']) for res in results if res['family'] == 'sheet'}
    rpn = group(rpn_rows, 'rpn')
    doc = {
        'generated_by': 'domain/far/coverage.py',
        'definitions': DEFINITIONS,
        'runs': runs,
        'sheet': sheet,
        'rpn': rpn,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'coverage.json'), 'w') as f:
        json.dump(doc, f, indent=1)
    with open(os.path.join(out_dir, 'coverage.md'), 'w') as f:
        f.write(to_md(doc))

    print('practice rows: ' + ', '.join('%s=%d' % (n, i['practice_rows']) for n, i in runs.items()))
    for label, key in SHEET_TABLE:
        print('%-36s pooled %s | s200 %s | s201 %s' % (
            label, fmt_share(sheet['pooled']['far'][key]),
            fmt_share(sheet['by_run']['sheet-s200-v7']['far'][key]),
            fmt_share(sheet['by_run']['sheet-s201-v7']['far'][key])))
    print('%-36s rpn %s' % ('rpn >= 4 operators', fmt_share(rpn['pooled']['far']['ops_ge4'])))
    print('written: %s, %s' % (os.path.join(out_dir, 'coverage.json'), os.path.join(out_dir, 'coverage.md')))


if __name__ == '__main__':
    main(sys.argv)
