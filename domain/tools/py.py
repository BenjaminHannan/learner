"""Python-subset help tool (domain mode, A24: the third subject, reading code).

Prompt: 'py: x = 4; y = x + 7; print(y)'. One line; '; ' stands for a newline. The text is parsed with ast.parse and then
walked by this file against a whitelist. Nothing is ever run with exec, eval or compile.

Allowed: Assign to one name (an int expression or a list of non-negative int constants); if/else, for over range(n) and
while, each with a one-statement body that is an assignment; def with one or two arguments and a body that is one return;
and, last, exactly one print(<int expression>), whose value is the answer. Expressions: + - * // on ints, names,
non-negative int constants, list[index] (index a constant or a name), calls to a defined function, max/min (2 or more
arguments, folded left), abs(a - b), sum(list) and len(list). A comparison (one of < > <= >= == !=) is allowed only as
the test of if/while and makes no calculator call: the model decides it itself.

Steps: each + - * // is one calculator call add/sub/mul/div; max and min are calls max/min; abs(a - b) is one sub with the
larger value first; sum(list) is a fold of add calls. 'mod' and 'cmp' never appear. // is the calculator's div, which is
exact only, so a // b that does not divide exactly gives '?'. A negative result, a value of 10^9 or more, more than 50
loop iterations in all, a deep call chain, or anything outside the whitelist gives '?'.
"""
import ast
import re

from domain.tools import BIG, Fail, execute

NAME = 'py'

MAX_ITERS = 50
MAX_DEPTH = 6        # nested function calls
MAX_NODES = 400
MAX_CHARS = 1000
RESERVED = {'print', 'range', 'max', 'min', 'abs', 'sum', 'len'}

# (kind, prompt, answer): one worked example per kind.
HELP = [
    ('assign add', 'py: x = 4; y = x + 7; print(y)', '11'),
    ('chain', 'py: a = 6; b = a * 3; c = b - 5; print(c)', '13'),
    ('max min', 'py: a = 9; b = 4; c = max(a, b) - min(a, b); print(c)', '5'),
    ('abs', 'py: a = 3; b = 8; print(abs(a - b))', '5'),
    ('list index', 'py: v = [5, 9, 2]; i = 1; print(v[i] + v[2])', '11'),
    ('for sum', 'py: s = 0; for i in range(4): s = s + i; print(s)', '6'),
    ('for repeat', 'py: p = 1; for i in range(3): p = p * 2; print(p)', '8'),
    ('if else', 'py: x = 7; if x > 5: y = x - 5; else: y = x + 5; print(y)', '2'),
    ('while', 'py: n = 1; while n < 20: n = n * 3; print(n)', '27'),
    ('function', 'py: def f(x): return x * 2 + 1; print(f(4))', '9'),
]

BINOPS = {ast.Add: 'add', ast.Sub: 'sub', ast.Mult: 'mul', ast.FloorDiv: 'div'}
CMPS = {ast.Lt: lambda a, b: a < b, ast.Gt: lambda a, b: a > b, ast.LtE: lambda a, b: a <= b,
        ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}


def help():
    """The help page: one {kind, prompt, answer} dict per kind."""
    return [{'kind': k, 'prompt': p, 'answer': a} for k, p, a in HELP]


class _Run:
    def __init__(self, runner):
        self.r = runner
        self.funcs = {}
        self.iters = 0

    # ---- expressions ----
    def name(self, node, env):
        if not isinstance(node, ast.Name) or node.id not in env:
            raise Fail('unknown name')
        return env[node.id]

    def listval(self, node, env):
        if isinstance(node, ast.List):
            return self.literal_list(node)
        v = self.name(node, env)
        if not isinstance(v, list):
            raise Fail('not a list')
        return v

    def literal_list(self, node):
        out = []
        for e in node.elts:
            if not (isinstance(e, ast.Constant) and type(e.value) is int and 0 <= e.value < BIG):
                raise Fail('list holds only non-negative int constants')
            out.append(e.value)
        return out

    def num(self, node, env, depth=0):
        """An int expression's value."""
        if isinstance(node, ast.Constant):
            if type(node.value) is int and 0 <= node.value < BIG:
                return node.value
            raise Fail('bad constant')
        if isinstance(node, ast.Name):
            v = self.name(node, env)
            if type(v) is not int:
                raise Fail('list used as a number')
            return v
        if isinstance(node, ast.BinOp):
            op = BINOPS.get(type(node.op))
            if op is None:
                raise Fail('operator not allowed')
            a = self.num(node.left, env, depth)
            b = self.num(node.right, env, depth)
            return self.r.call(op, a, b)
        if isinstance(node, ast.Subscript):
            if not isinstance(node.slice, (ast.Constant, ast.Name)):
                raise Fail('index must be a constant or a name')
            lst = self.listval(node.value, env)
            i = self.num(node.slice, env, depth)
            if i >= len(lst):
                raise Fail('index out of range')
            return lst[i]
        if isinstance(node, ast.Call):
            return self.call(node, env, depth)
        raise Fail('expression not allowed')

    def call(self, node, env, depth):
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise Fail('call not allowed')
        f, args = node.func.id, node.args
        if f in ('max', 'min'):
            if len(args) < 2:
                raise Fail(f + ' needs 2 or more arguments')
            acc = self.num(args[0], env, depth)
            for a in args[1:]:
                acc = self.r.call(f, acc, self.num(a, env, depth))
            return acc
        if f == 'abs':
            if len(args) != 1 or not (isinstance(args[0], ast.BinOp) and isinstance(args[0].op, ast.Sub)):
                raise Fail('abs takes (a - b)')
            x = self.num(args[0].left, env, depth)
            y = self.num(args[0].right, env, depth)
            return self.r.call('sub', max(x, y), min(x, y))
        if f == 'sum':
            if len(args) != 1:
                raise Fail('sum takes one list')
            lst = self.listval(args[0], env)
            if not lst:
                return 0
            acc = lst[0]
            for v in lst[1:]:
                acc = self.r.call('add', acc, v)
            return acc
        if f == 'len':
            if len(args) != 1:
                raise Fail('len takes one list')
            return len(self.listval(args[0], env))
        if f in self.funcs:
            params, body = self.funcs[f]
            if len(args) != len(params) or depth >= MAX_DEPTH:
                raise Fail('bad call of ' + f)
            vals = [self.num(a, env, depth) for a in args]
            return self.num(body, dict(zip(params, vals)), depth + 1)
        raise Fail('unknown function ' + f)

    def test(self, node, env):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
            raise Fail('test must be one comparison')
        fn = CMPS.get(type(node.ops[0]))
        if fn is None:
            raise Fail('comparison not allowed')
        return fn(self.num(node.left, env), self.num(node.comparators[0], env))

    # ---- statements ----
    def assign(self, node, env):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            raise Fail('statement must be an assignment')
        t = node.targets[0].id
        if t in RESERVED or t in self.funcs or t.startswith('_'):
            raise Fail('name not allowed')
        env[t] = self.literal_list(node.value) if isinstance(node.value, ast.List) else self.num(node.value, env)

    def one(self, body):
        if len(body) != 1:
            raise Fail('body must be one statement')
        return body[0]

    def tick(self):
        self.iters += 1
        if self.iters > MAX_ITERS:
            raise Fail('too many loop iterations')

    def stmt(self, node, env):
        if isinstance(node, ast.Assign):
            return self.assign(node, env)
        if isinstance(node, ast.If):
            body = self.one(node.body)
            other = self.one(node.orelse) if node.orelse else None
            if self.test(node.test, env):
                self.assign(body, env)
            elif other is not None:
                self.assign(other, env)
            return
        if isinstance(node, ast.For):
            it = node.iter
            if not (isinstance(node.target, ast.Name) and isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                    and it.func.id == 'range' and len(it.args) == 1 and not it.keywords and not node.orelse):
                raise Fail('for must be over range(n)')
            if node.target.id in RESERVED or node.target.id in self.funcs:
                raise Fail('name not allowed')
            body = self.one(node.body)
            n = self.num(it.args[0], env)
            if n > MAX_ITERS:
                raise Fail('range too long')
            for k in range(n):
                self.tick()
                env[node.target.id] = k
                self.assign(body, env)
            return
        if isinstance(node, ast.While):
            body = self.one(node.body)
            if node.orelse:
                raise Fail('while-else not allowed')
            while self.test(node.test, env):
                self.tick()
                self.assign(body, env)
            return
        if isinstance(node, ast.FunctionDef):
            a = node.args
            if (not 1 <= len(a.args) <= 2 or a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs or a.defaults
                    or node.decorator_list or node.returns or node.name in RESERVED or node.name in env
                    or node.name.startswith('_')):
                raise Fail('def not allowed')
            ret = self.one(node.body)
            if not (isinstance(ret, ast.Return) and ret.value is not None):
                raise Fail('function body must be one return')
            params = [p.arg for p in a.args]
            if len(set(params)) != len(params) or any(p in RESERVED or p in self.funcs or p.startswith('_') for p in params):
                raise Fail('bad parameter')
            self.funcs[node.name] = (params, ret.value)
            return
        raise Fail('statement not allowed')


def _solve(prompt, runner):
    m = re.fullmatch(r'\s*py: (.+)', prompt, re.DOTALL)
    if m is None:
        raise Fail('not a py prompt')
    text = m.group(1)
    if len(text) > MAX_CHARS or not all(' ' <= c <= '~' for c in text) or '#' in text:
        raise Fail('bad characters')
    parts = text.split('; ')
    if any(not p.strip() or ';' in p for p in parts):
        raise Fail('bad statement separator')
    try:
        tree = ast.parse('\n'.join(parts))
    except (SyntaxError, ValueError, MemoryError, RecursionError) as e:
        raise Fail('syntax: %s' % e)
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise Fail('program too big')
    body = tree.body
    last = body[-1] if body else None
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call) and isinstance(last.value.func, ast.Name)
            and last.value.func.id == 'print' and len(last.value.args) == 1 and not last.value.keywords):
        raise Fail('the last statement must be print(<expression>)')
    run, env = _Run(runner), {}
    for node in body[:-1]:
        run.stmt(node, env)
    v = run.num(last.value.args[0], env)
    if v < 0 or v >= BIG:
        raise Fail('value out of range')
    return v


def evaluate(prompt):
    """{'value': str, 'steps': [(op, a, b, result), ...]} for a py prompt; value '?' if it cannot run."""
    if not isinstance(prompt, str):
        return {'value': '?', 'steps': []}
    return execute(lambda runner: _solve(prompt, runner))
