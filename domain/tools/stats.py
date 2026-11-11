"""Stats help tool: the look-alike test tool (domain/LOOKALIKE-MARKS-2026-10-10.md).

Prompt: 'Numbers: 6, 3, 4. What is the product of the numbers?' The frame matches the old compare_numbers and list_stats
questions. Each chain step and the final step is one calculator call. value is '?' when the prompt does not parse, is not
one of the 7 questions, has a number of 10^9 or more, or a step gives '?' (for example half of an odd sum).
"""
import re

from domain.tools import BIG, Fail, execute

NAME = 'stats'

# (kind, prompt, answer): one worked example per kind.
HELP = [
    ('product', 'Numbers: 6, 3, 4. What is the product of the numbers?', '72'),
    ('half the sum', 'Numbers: 12, 4, 8. What is half the sum of the numbers?', '12'),
    ('largest plus smallest', 'Numbers: 65, 84, 7. What is the largest plus the smallest?', '91'),
    ('largest times smallest', 'Numbers: 9, 4, 7. What is the largest times the smallest?', '36'),
    ('twice the largest', 'Numbers: 65, 84, 7, 20. What is twice the largest?', '168'),
    ('twice the smallest', 'Numbers: 31, 6, 58. What is twice the smallest?', '12'),
    ('sum minus largest', 'Numbers: 12, 30, 5. What is the sum minus the largest?', '17'),
]

# The question text (the part after 'Numbers: .... ') -> kind. Only these exact questions are accepted.
KIND_OF_QUESTION = {p.split('. ', 1)[1]: k for k, p, _ in HELP}


def help():
    """The help page: one {kind, prompt, answer} dict per kind."""
    return [{'kind': k, 'prompt': p, 'answer': a} for k, p, a in HELP]


def _chain(calc_run, op, xs):
    """xs[0] op xs[1] op xs[2] ... left to right: one calculator call per pair."""
    v = xs[0]
    for x in xs[1:]:
        v = calc_run.call(op, v, x)
    return v


def _solve(prompt, calc_run):
    m = re.fullmatch(r'Numbers: (\d+(?:, \d+)+)\. (.+)', prompt, re.ASCII)
    if m is None:
        raise Fail('not a stats prompt')
    kind = KIND_OF_QUESTION.get(m.group(2))
    if kind is None:
        raise Fail('not one of the stats questions')
    xs = []
    for tok in m.group(1).split(', '):
        v = int(tok)
        if v >= BIG:
            raise Fail('number too large')
        xs.append(v)
    if kind == 'product':
        return _chain(calc_run, 'mul', xs)
    if kind == 'half the sum':
        return calc_run.call('div', _chain(calc_run, 'add', xs), 2)
    if kind == 'largest plus smallest':
        big = _chain(calc_run, 'max', xs)
        small = _chain(calc_run, 'min', xs)
        return calc_run.call('add', big, small)
    if kind == 'largest times smallest':
        big = _chain(calc_run, 'max', xs)
        small = _chain(calc_run, 'min', xs)
        return calc_run.call('mul', big, small)
    if kind == 'twice the largest':
        return calc_run.call('mul', _chain(calc_run, 'max', xs), 2)
    if kind == 'twice the smallest':
        return calc_run.call('mul', _chain(calc_run, 'min', xs), 2)
    # sum minus largest
    total = _chain(calc_run, 'add', xs)
    return calc_run.call('sub', total, _chain(calc_run, 'max', xs))


def evaluate(prompt):
    """{'value': str, 'steps': [(op, a, b, result), ...]} for a stats prompt; value '?' if it cannot run."""
    if not isinstance(prompt, str):
        return {'value': '?', 'steps': []}
    return execute(lambda calc_run: _solve(prompt, calc_run))
