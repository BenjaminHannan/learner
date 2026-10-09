"""Traces as text (B3 group 2, L1; architecture/B3-GROUP2-BUILD-2026-10-09.md sec. 4). A row's worked `steps` -> the list of calculator calls
as TEXT, in evaluation order, with no slot matching: operands are strings, so an operand that is not in the question is still a target.
A call is dict(op 'sub', a '12', b '5', a_src, b_src, result '7'); src is 'prompt', 'const' (1 2 10 100), ('res', k) (the k-th earlier call's
result) or 'hidden' (as_written only: an operand that is the unknown answer and is in no slot). Op names are progparse OPS lowercased (tool.NAMES).
steps_of(row, as_written=False) -> (calls, reason), or (None, reason) when the row cannot be read (as progparse.program_for; raises nothing).
The step forms, their parsing and their order are progparse.to_program's (its tokenizer, precedence parser and fold are reused), written over text.
as_written=False: the SAME calls T1 trains on today (Tool.row_gold: tested equal), including the inverse-op rewrite for a missing operand
("7 + 5 = 12" with answer 7 absent from the question becomes `sub 12 5`) and the answer-based MIN / MAX of compare_numbers, and verify_claim's
hand-added CMP(last, claimed number).
as_written=True (L1) differs in three ways only (each shown by test_progtext):
 (1) no inverse rewrite: that step is the call `add 7 5` (a_src 'hidden'); the answer is a hidden operand, so the final check is "answer is the last
     result or a hidden operand" (False: answer == last result);
 (2) `compare x y` is the call `cmp x y` as written (False: MIN or MAX picked by looking at the answer when it is a number; so
     in compare_numbers the answer, x or y, is then no call's result: the model copies it from the question; the final check accepts x or y);
 (3) verify_claim gets no hand-added CMP step.
(4) a step that is not a calculator call (progparse's 'unparsed step': list_stats "count_even of [4, 7, 10]", "second_largest of [..]",
     "sum of [..]", verify_claim "scan") is a NOTE: dict(op='note', text=<the step, stripped>, result=''), in step order among the calls; False
     still reads such a row as unreadable. Later calls resolve operands against the prompt, constants and earlier results as before; ('res', k)
     counts positions in the step list (notes included). A row with a note skips the final answer check; a row of only notes has a trace.
     A call whose operand is the answer (written in the call) also passes the final check (arith_bare rows whose answer is a question number).
     text(step) renders a call `op a b` and a note `note <text>`; entry(step) is the tape entry (`op a b = r`; a note is its text alone).
Either way the operand order is the step's own (T1's either-order freedom for add / mul / min / max is dropped with the writer; disclosed).
drill(steps, answer, rng) is tool.drill_gold on text; report(rows, as_written) counts rows per family."""
import re
from custom_io.models import progparse as pp
from custom_io.models import tool

CAUGHT = (ValueError, AssertionError, IndexError, ZeroDivisionError, KeyError, TypeError, AttributeError)
INT = re.compile(r'-?\d+')


class TB:
    """Text builder: values as in progparse.Builder, but a call keeps operand strings and where each came from."""

    def __init__(self, nums, as_written, ans):
        self.vals, self.src, self.n_prompt, self.calls = list(nums) + pp.CONSTS, ['prompt'] * len(nums) + ['const'] * len(pp.CONSTS), len(nums), []
        self.invert, self.w, self.ans, self.cmp_args, self.notes = None, as_written, ans, set(), 0

    def find(self, v):
        for x, s in zip(self.vals, self.src):       # first match, as row_gold's cands[0]: prompt, then constants, then earlier results
            if x == v:
                return s

    def op(self, op, va, vb):
        sa, sb = self.find(va), self.find(vb)
        if not self.w and (sa is None or sb is None) and self.invert is not None and op in pp.SYM.values():
            res, ans = self.invert          # "a op ? = c" / "? op b = c": the answer is the missing operand, so the call is the inverse op
            has = self.find(res) is not None
            if sa is None and va == ans and has and sb is not None:
                self.invert = None
                return self.op(*{'ADD': ('SUB', res, vb), 'SUB': ('ADD', res, vb), 'MUL': ('DIV', res, vb), 'DIV': ('MUL', res, vb)}[op])
            if sb is None and vb == ans and has and sa is not None:
                self.invert = None
                return self.op(*{'ADD': ('SUB', res, va), 'SUB': ('SUB', va, res), 'MUL': ('DIV', res, va), 'DIV': ('DIV', va, res)}[op])
        if self.w and self.ans is not None:         # as written: the unknown answer is an operand of the call
            if sa is None and sb is not None and va == self.ans:
                sa = 'hidden'
            elif sb is None and sa is not None and vb == self.ans:
                sb = 'hidden'
        if sa is None or sb is None:
            raise ValueError(f'operand not found {va} {vb}')
        v = pp.ex(op, va, vb)
        if v is None:
            raise ValueError('bad div')
        self.calls.append(dict(op=op.lower(), a=str(va), b=str(vb), a_src=sa, b_src=sb, result=str(v)))
        self.vals.append(v)
        self.src.append(('res', len(self.calls) - 1))
        return v


def build(r, as_written):
    """progparse.to_program over text -> (TB, last value, answer-is-hidden-operand flag)."""
    nums = pp.prompt_numbers(r['prompt'])
    isint = re.fullmatch(r'-?\d+', r['answer']) is not None
    b, last = TB(nums, as_written, int(r['answer']) if isint else None), None
    if isint:
        pn = [int(x) for x in pp.NUM_RE.findall(r['prompt'])]
        if pn:
            b.invert = (pn[-1], int(r['answer']))     # the result of a missing-operand equation is its last number
    for s in r['steps']:
        s = s.strip()
        m = re.fullmatch(r'(\d+) ([-+*/]) (\d+) = (\d+)', s)
        if not as_written and m and len(r['steps']) == 1 and re.fullmatch(r'\d+', r['answer']):       # arith_bare missing operand
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
            last = pp.fold(b, 'ADD', [int(x) for x in mm.group(1).split(',')])
            continue
        mm = re.fullmatch(r'(smallest|largest) of \[(.*)\]', s)
        if mm:
            last = pp.fold(b, 'MIN' if mm.group(1) == 'smallest' else 'MAX', [int(x) for x in mm.group(2).split(',')])
            continue
        mm = re.fullmatch(r'compare (\d+) (\d+)', s)
        if mm:
            x, y = int(mm.group(1)), int(mm.group(2))
            if as_written:
                b.cmp_args |= {x, y}
                last = b.op('CMP', x, y)
            elif r['answer'].isdigit():                # compare_numbers: the answer is one of them
                last = b.op('MIN' if int(r['answer']) == min(x, y) else 'MAX', x, y)
            else:                                      # compare_after: a sign, rendered by the talker
                last = b.op('CMP', x, y)
            continue
        mm = re.fullmatch(r'range of \[(.*)\]', s)
        if mm:
            xs = [int(x) for x in mm.group(1).split(',')]
            last = b.op('SUB', pp.fold(b, 'MAX', xs), pp.fold(b, 'MIN', xs))
            continue
        if re.fullmatch(r'[-+*/() \d]+', lhs) and re.search(r'\d', lhs) and re.search(r'[-+*/]', lhs):
            v = pp.eval_expr(b, pp.tok_expr(lhs))
            if m.group(2) is not None:
                assert v == int(m.group(2)), f'expr mismatch {s}'
            last = v
            continue
        if as_written:         # not a calculator call: a note, taught as written (Addendum A); False keeps raising, as progparse
            b.calls.append(dict(op='note', text=s, result=''))
            b.notes += 1
            continue
        raise ValueError('unparsed step')
    if not b.calls:
        raise ValueError('no ops')
    return b, last


def steps_of(row, as_written=False):
    """-> (list of call dicts, 'ok') or (None, reason). See the module docstring."""
    try:
        b, last = build(row, as_written)
        ans = row['answer']
        if row['family'] == 'verify_claim' and ans in ('yes', 'no'):       # last value vs the claimed (last prompt) number
            if not as_written:
                b.op('CMP', last, b.vals[b.n_prompt - 1])
        elif re.fullmatch(r'-?\d+', ans):
            hid = as_written and any(str(v) == ans for c in b.calls if c['op'] != 'note' for v, k in ((c['a'], c['a_src']), (c['b'], c['b_src'])) if k == 'hidden')
            opd = as_written and any(ans in (c['a'], c['b']) for c in b.calls if c['op'] != 'note')     # the answer is written in a call (copied from it)
            if int(ans) != last and not hid and not opd and int(ans) not in b.cmp_args and not b.notes:
                return None, 'final mismatch'
        return b.calls, 'ok'
    except CAUGHT as e:
        return None, (str(e) or type(e).__name__)[:40]


def text(c):
    """The call the model writes: `op a b`; a note: `note <the step text>`."""
    return f"note {c['text']}" if c['op'] == 'note' else f"{c['op']} {c['a']} {c['b']}"


def entry(c):
    """The tape entry: `op a b = result` (tool.entry without the length cut); a note is its text alone (no ' = ', nothing replied)."""
    return text(c) if c['op'] == 'note' else f"{text(c)} = {c['result']}"


def drill(steps, answer, rng, lens=tool.DRILL_LEN):
    """tool.drill_gold on text steps: every result replaced by a random digit string, a later operand whose src is ('res', k) by call k's string,
    the answer by the string of the latest call whose real result is `answer`. -> (drilled steps, drilled answer), None when the answer is no
    call's result, 'too_long' when an entry would exceed tool.LE. The draws (one per call, in order) come only from rng."""
    hit = [i for i, c in enumerate(steps) if c['op'] != 'note' and c['result'] == answer]
    if not hit:
        return None
    d = [None if c['op'] == 'note' else tool.rand_digits(rng, *lens) for c in steps]      # notes have no result: no draw
    out = []
    for i, c in enumerate(steps):
        if c['op'] == 'note':
            if len(text(c)) > tool.LE:
                return 'too_long'
            out.append(dict(c))
            continue
        a = d[c['a_src'][1]] if isinstance(c['a_src'], tuple) else c['a']
        b = d[c['b_src'][1]] if isinstance(c['b_src'], tuple) else c['b']
        if len(f"{c['op']} {a} {b} = {d[i]}") > tool.LE:
            return 'too_long'
        out.append(dict(c, a=a, b=b, result=d[i]))
    return out, d[max(hit)]


def report(rows, as_written=False):
    """-> {family: counts} and 'all'. rows: how many; read / unreadable (reasons) under `as_written`; differ (calls differ between False and True);
    hidden (a 'hidden' operand under True); notes (note steps) and note_rows (rows with one), under `as_written`; no_trace (no steps at all: the
    no-answer-only rule, every training row needs its full target); steps_no_trace (rows that HAVE steps but still no trace: must be 0).
    Prints one loud line per family with no_trace > 0, and the reasons of every steps_no_trace row."""
    fam = {}
    for r in rows:
        c = fam.setdefault(r.get('family', '?'), dict(rows=0, read=0, unreadable=0, reasons={}, differ=0, hidden=0, no_trace=0, notes=0, note_rows=0, steps_no_trace=0))
        s0, why0 = steps_of(r, False)
        s1, why1 = steps_of(r, True)
        s, why = (s1, why1) if as_written else (s0, why0)
        c['rows'] += 1
        if s is None:
            c['unreadable'] += 1
            c['no_trace'] += 1
            c['steps_no_trace'] += bool(r.get('steps'))
            c['reasons'][why] = c['reasons'].get(why, 0) + 1
        else:
            c['read'] += 1
            n = sum(x['op'] == 'note' for x in s)
            c['notes'] += n
            c['note_rows'] += n > 0
        c['differ'] += s0 != s1
        c['hidden'] += bool(s1) and any('hidden' in (x.get('a_src'), x.get('b_src')) for x in s1)
    tot = dict(rows=0, read=0, unreadable=0, reasons={}, differ=0, hidden=0, no_trace=0, notes=0, note_rows=0, steps_no_trace=0)
    for c in fam.values():
        for k, v in c.items():
            if k == 'reasons':
                for w, n in v.items():
                    tot[k][w] = tot[k].get(w, 0) + n
            else:
                tot[k] += v
    for f, c in sorted(fam.items()):
        if c['no_trace']:
            print(f"!! NO TRACE: family {f}: {c['no_trace']} of {c['rows']} rows have no trace at all (as_written={as_written}); reasons {c['reasons']}")
        if c['steps_no_trace']:
            print(f"!! STEPS BUT NO TRACE: family {f}: {c['steps_no_trace']} rows that have steps; reasons {c['reasons']}")
    return dict(fam, all=tot)
