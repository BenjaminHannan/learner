#!/usr/bin/env python3
"""rsn-299 exact tool: the calculator the 1B calls while it thinks.

The model writes a calculation between << and >>; this module computes it exactly and the
runner writes "=<result>" right after it, so no arithmetic, counting or comparing is ever done
by the model itself.  Safe: only numbers, strings, + - * / // % **, parentheses and the
functions below are allowed (checked on the parsed tree; nothing is exec'd).

  arithmetic   round(x, n) ceil(x) floor(x) min(...) max(...) abs(x) sum([...])
  clock        t("9:47") -> minutes after midnight;  hhmm(minutes) -> "HH:MM" (wraps at 24 h)
  weekdays     day("Tuesday") -> 0..6 (Monday = 0);  dayname(n) -> weekday name (wraps)
  counting     count("a, b, c") -> number of comma-separated items;  letters("word") -> letters
  comparing    biggest("A", 3, "B", 4) -> "B";  smallest("A", 3, "B", 4) -> "A"
"""
from __future__ import annotations

import ast
import math
import operator as op

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _t(s):
    h, m = str(s).strip().split(":")
    return int(h) * 60 + int(m)


def _hhmm(x):
    x = int(round(float(x))) % 1440
    return f"{x // 60:02d}:{x % 60:02d}"


def _day(s):
    s = str(s).strip().lower()
    for i, d in enumerate(DAYS):
        if d.lower().startswith(s[:3]):
            return i
    raise ValueError(f"unknown day {s!r}")


def _dayname(n):
    return DAYS[int(n) % 7]


def _count(s):
    return len([x for x in str(s).split(",") if x.strip()])


def _letters(s):
    return sum(ch.isalpha() for ch in str(s))


def _pairs(args):
    if len(args) < 4 or len(args) % 2:
        raise ValueError("give name, value pairs")
    return [(str(args[i]), float(args[i + 1])) for i in range(0, len(args), 2)]


def _biggest(*args):
    p = _pairs(args)
    top = max(v for _, v in p)
    names = [n for n, v in p if v == top]
    if len(names) > 1:
        raise ValueError("tie")
    return names[0]


def _smallest(*args):
    p = _pairs(args)
    low = min(v for _, v in p)
    names = [n for n, v in p if v == low]
    if len(names) > 1:
        raise ValueError("tie")
    return names[0]


FUNCS = {"round": round, "ceil": math.ceil, "floor": math.floor, "min": min, "max": max,
         "abs": abs, "sum": sum, "t": _t, "hhmm": _hhmm, "day": _day, "dayname": _dayname,
         "count": _count, "letters": _letters, "biggest": _biggest, "smallest": _smallest}
BINOPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
          ast.FloorDiv: op.floordiv, ast.Mod: op.mod, ast.Pow: op.pow}


def _ev(n):
    if isinstance(n, ast.Expression):
        return _ev(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float, str)):
        return n.value
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        v = _ev(n.operand)
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.BinOp) and type(n.op) in BINOPS:
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Pow) and abs(b) > 12:
            raise ValueError("power too big")
        return BINOPS[type(n.op)](a, b)
    if isinstance(n, (ast.List, ast.Tuple)):
        return [_ev(x) for x in n.elts]
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
        return FUNCS[n.func.id](*[_ev(a) for a in n.args])
    raise ValueError(f"not allowed: {ast.dump(n)[:60]}")


def fmt(v) -> str:
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


def calc(expr: str) -> str:
    """exact result as text, or 'error' (the model then sees =error and can rewrite)."""
    try:
        tree = ast.parse(expr.strip().replace("×", "*").replace("÷", "/"), mode="eval")
        return fmt(_ev(tree))
    except Exception:
        return "error"


if __name__ == "__main__":
    tests = {"3*12+2": "38", "(19.99*3)*0.85": "50.9745", "hhmm(t('9:47')+98)": "11:25",
             "dayname(day('Tuesday')+10)": "Friday", "count('apple, pear, fig')": "3",
             "letters('banana')": "6", "biggest('Oslo', 3, 'Rome', 4.5)": "Rome",
             "ceil(47/12)": "4", "__import__('os')": "error", "round(10/3, 2)": "3.33"}
    bad = {k: (calc(k), v) for k, v in tests.items() if calc(k) != v}
    print("selftest ok" if not bad else f"selftest FAIL {bad}")
