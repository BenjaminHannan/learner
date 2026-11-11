"""Invoice help tool: a look-alike test tool (see domain/LOOKALIKE-MARKS-2026-10-10.md).
Its frame matches the old table_calc questions: rows 'Row NAME: qty Q, price P.' and one of six fixed questions.
Each step is one calculator call through Runner.call; chains run left to right over the rows in prompt order.
value is '?' when the prompt does not parse exactly, a row name is unknown or repeated, a number is BIG or more, or a step fails.
"""
import re

from domain.tools import BIG, Fail, execute

NAME = 'invoice'

ROW_RE = re.compile(r'Row ([a-z]+): qty ([0-9]+), price ([0-9]+)\.')

# The six question forms. The two-name forms capture the names (a first, then b).
QUESTIONS = [
    ('price sum', re.compile(r'What is the total price over all rows\?')),
    ('two rows cost', re.compile(r'What is the total cost of rows ([a-z]+) and ([a-z]+)\?')),
    ('largest qty', re.compile(r'What is the largest qty over all rows\?')),
    ('smallest price', re.compile(r'What is the smallest price over all rows\?')),
    ('cost difference', re.compile(r'How much more is the cost of row ([a-z]+) than row ([a-z]+)\?')),
    ('twice qty sum', re.compile(r'What is twice the total qty over all rows\?')),
]

# (kind, prompt, answer): one worked example per kind.
HELP = [
    ('price sum', 'Row zipper: qty 6, price 12. Row hammer: qty 2, price 10. Row pocket: qty 4, price 7. What is the total price over all rows?', '29'),
    ('two rows cost', 'Row candle: qty 3, price 9. Row ladder: qty 5, price 4. Row mitten: qty 2, price 11. What is the total cost of rows candle and mitten?', '49'),
    ('largest qty', 'Row basket: qty 7, price 3. Row feather: qty 4, price 12. Row lantern: qty 9, price 5. What is the largest qty over all rows?', '9'),
    ('smallest price', 'Row button: qty 8, price 6. Row saddle: qty 3, price 10. Row pillow: qty 5, price 4. What is the smallest price over all rows?', '4'),
    ('cost difference', 'Row anchor: qty 6, price 9. Row kettle: qty 4, price 5. Row bridge: qty 2, price 8. How much more is the cost of row anchor than row kettle?', '34'),
    ('twice qty sum', 'Row magnet: qty 2, price 7. Row jacket: qty 5, price 3. Row turtle: qty 3, price 8. What is twice the total qty over all rows?', '20'),
]


def help():
    """The help page: one {kind, prompt, answer} dict per kind."""
    return [{'kind': k, 'prompt': p, 'answer': a} for k, p, a in HELP]


def _parse(prompt):
    """(rows, kind, names): rows are (name, qty, price) in prompt order; names are the row names the question uses."""
    rows, rest = [], prompt
    while True:
        m = ROW_RE.match(rest)
        if m is None:
            break
        name, q, p = m.group(1), int(m.group(2)), int(m.group(3))
        if q >= BIG or p >= BIG:
            raise Fail('number too large')
        rows.append((name, q, p))
        rest = rest[m.end():]
        if not rest.startswith(' '):
            raise Fail('a row must be followed by one space')
        rest = rest[1:]
    if len(rows) < 2:
        raise Fail('need at least 2 rows')
    names = [n for n, _, _ in rows]
    if len(set(names)) != len(names):
        raise Fail('row names must be distinct')
    for kind, pat in QUESTIONS:
        m = pat.fullmatch(rest)
        if m is not None:
            break
    else:
        raise Fail('not one of the six question forms')
    named = m.groups()
    for n in named:
        if n not in names:
            raise Fail('unknown row ' + n)
    if len(named) == 2 and named[0] == named[1]:
        raise Fail('the two rows must be different')
    return rows, kind, named


def _chain(calc_run, op, values):
    """Fold values left to right with one calculator step per value after the first."""
    acc = values[0]
    for v in values[1:]:
        acc = calc_run.call(op, acc, v)
    return acc


def _solve(prompt, calc_run):
    rows, kind, named = _parse(prompt)
    qtys = [q for _, q, _ in rows]
    prices = [p for _, _, p in rows]
    if kind == 'price sum':
        return _chain(calc_run, 'add', prices)
    if kind == 'largest qty':
        return _chain(calc_run, 'max', qtys)
    if kind == 'smallest price':
        return _chain(calc_run, 'min', prices)
    if kind == 'twice qty sum':
        return calc_run.call('mul', _chain(calc_run, 'add', qtys), 2)
    # two rows cost, cost difference: the cost of each named row (a first), then add or sub.
    by_name = {n: (q, p) for n, q, p in rows}
    qa, pa = by_name[named[0]]
    qb, pb = by_name[named[1]]
    ca = calc_run.call('mul', qa, pa)
    cb = calc_run.call('mul', qb, pb)
    if kind == 'two rows cost':
        return calc_run.call('add', ca, cb)
    return calc_run.call('sub', ca, cb)


def evaluate(prompt):
    """{'value': str, 'steps': [(op, a, b, result), ...]} for an invoice prompt; value '?' if it cannot run."""
    if not isinstance(prompt, str):
        return {'value': '?', 'steps': []}
    return execute(lambda calc_run: _solve(prompt, calc_run))
