"""RPN help tool (domain mode, DM6: the second domain).

Prompt: 'rpn: 3 4 + 2 *' (postfix). Tokens are whole numbers, the operators + - * / %, and the words max and min.
Each operator is one calculator step calc(op, a, b), where a is the value pushed first (so 'a b -' is sub a b).

value is '?' when: the stack is short for an operator, or not exactly one value is left at the end; a token is not
known; a number is 10^9 or more; a '-' has a < b (the result would be negative); or the calculator cannot run a step
(for example / that is not exact, or % or / by 0). Nothing caps the number of operators here: the caller checks
len(steps) against the model's 7 calls.
"""
import re

from domain.tools import BIG, Fail, execute

NAME = 'rpn'

OPS = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '%': 'mod', 'max': 'max', 'min': 'min'}

# (kind, prompt, answer): one worked example per kind.
HELP = [
    ('a b +', 'rpn: 3 4 +', '7'),
    ('a b -', 'rpn: 9 4 -', '5'),
    ('a b *', 'rpn: 6 7 *', '42'),
    ('a b /', 'rpn: 56 7 /', '8'),
    ('a b %', 'rpn: 17 5 %', '2'),
    ('a b + c *', 'rpn: 3 4 + 2 *', '14'),
    ('a b c * +', 'rpn: 3 4 2 * +', '11'),
    ('a b + c d + *', 'rpn: 1 2 + 3 4 + *', '21'),
]


def help():
    """The help page: one {kind, prompt, answer} dict per kind."""
    return [{'kind': k, 'prompt': p, 'answer': a} for k, p, a in HELP]


def _solve(prompt, calc_run):
    m = re.fullmatch(r'\s*rpn:(.*)', prompt, re.DOTALL)
    if m is None:
        raise Fail('not an rpn prompt')
    stack = []
    for tok in m.group(1).split():
        if re.fullmatch(r'[0-9]+', tok):
            v = int(tok)
            if v >= BIG:
                raise Fail('number too large')
            stack.append(v)
        elif tok in OPS:
            if len(stack) < 2:
                raise Fail('stack short for ' + tok)
            b = stack.pop()
            a = stack.pop()
            stack.append(calc_run.call(OPS[tok], a, b))
        else:
            raise Fail('unknown token ' + tok)
    if len(stack) != 1:
        raise Fail('stack has %d values at the end' % len(stack))
    return stack[0]


def evaluate(prompt):
    """{'value': str, 'steps': [(op, a, b, result), ...]} for an rpn prompt; value '?' if it cannot run."""
    if not isinstance(prompt, str):
        return {'value': '?', 'steps': []}
    return execute(lambda calc_run: _solve(prompt, calc_run))
