"""Shared pieces for the spreadsheet (sheet.py) and RPN (rpn.py) help tools.

Each tool step is one call of the outside calculator, custom_io.models.tool.calc(op, a, b). Runner makes those calls and
keeps each one as an (op, a, b, result) string tuple. It refuses a call that would give a negative number (a 'sub' with
a < b), and a '?' result ends the run, so no step a tool returns is ever negative.
"""
from custom_io.data import ASCII, MAX_ANS, MAX_PROMPT  # caps and vocab (custom_io/data.py:11, :24)
from custom_io.models.tool import BIG, N_NUM, N_RES, NAMES, calc  # calculator, op names, limits (tool.py:93, :86; ledger.py:61)

__all__ = ['ASCII', 'BIG', 'MAX_ANS', 'MAX_PROMPT', 'N_NUM', 'N_RES', 'NAMES', 'Fail', 'Runner', 'execute']


class Fail(Exception):
    """The tool cannot run this prompt: a parse error, a bad cell or range, a step that would be negative, or a '?'."""


class Runner:
    """Makes calculator calls for a tool and records each one as a step."""

    def __init__(self):
        self.steps = []

    def call(self, op, a, b):
        """One calculator step on non-negative ints a and b. Returns the int result."""
        if a < 0 or b < 0 or (op == 'sub' and a < b):  # the result would be negative: never run it
            raise Fail(f'{op} {a} {b} would be negative')
        r = calc(op, str(a), str(b))
        self.steps.append((op, str(a), str(b), r))
        if r == '?':
            raise Fail(f'{op} {a} {b} gave ?')
        return int(r)


def execute(solve):
    """Run solve(runner), which returns an int, and return {'value': str, 'steps': list}.

    Any Fail (or a parse nested too deep) gives value '?'. The steps run so far are kept; on a '?' value the last
    step may be the calculator's own '?'.
    """
    runner = Runner()
    try:
        value = solve(runner)
    except (Fail, RecursionError):
        return {'value': '?', 'steps': runner.steps}
    return {'value': str(value), 'steps': runner.steps}
