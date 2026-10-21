"""A1 join-gap audit (evaluation only): on joined probe rows, does a checkpoint fail at the pieces or at the join?

  python3 -m domain.far.join_gap --ckpt PATH [--addon-rank 64 --addon-alpha 128] --probe PATH --out DIR --label NAME

Per row the formula is split at its top-level join (K+J, or (K)*(J)). W: the whole row right (as the probe scores it).
P: both pieces right, each asked alone on the same grid. T: P and the model's answer to the join of its own two piece
answers (=a+b or =a*b) right, i.e. what an outside splitter would score. First error (W false): the first round whose
call differs from the tool's working. Scoring only: no training; the add-on of an LA checkpoint is already merged into
its saved weights (mode.save_ckpt), so --addon-rank/--addon-alpha only label the run.
"""
import argparse
import json
import os
import re
from collections import Counter

from domain.far import learn_probe as L
from domain.far import sheet_probe as SP
from domain.tools import sheet as sheet_tool

CELLS = ('F4-two', 'F5-far')
SYM = {'add', 'mul', 'min', 'max'}
CA = re.compile(r'[AB]\d+\+[AB]\d+\*2')   # the cell-arithmetic piece holds a depth-0 + and *: one atom
PAIRS = ('range+range', 'range+cell', 'cell+cell')
ERRS = ('K', 'J', 'join', 'stopped/extra', 'answer')   # 'answer': every call matches, the final answer is wrong


def depth0(s, ops='+*'):
    """Positions of the characters of `ops` at bracket depth 0."""
    d, out = 0, []
    for i, ch in enumerate(s):
        d += ch == '('
        d -= ch == ')'
        if d == 0 and ch in ops:
            out.append(i)
    return out


def strip_outer(s):
    """s without one outer pair of brackets, or None when s is not '(...)' with the first bracket closing at the end."""
    if len(s) < 2 or s[0] != '(' or s[-1] != ')':
        return None
    d = 0
    for i, ch in enumerate(s):
        d += ch == '('
        d -= ch == ')'
        if d == 0 and i < len(s) - 1:
            return None
    return s[1:-1]


def split_formula(f):
    """(op, K, J, strict) for a formula that splits at its top-level join, else None. strict: exactly one + or * at depth 0.
    Not strict: the cell-arithmetic piece (A1+B2*2, a depth-0 + and *) is one atom, then exactly one + at depth 0."""
    pos = depth0(f)
    if len(pos) == 1 and pos[0] > 0:
        i = pos[0]
        op, K, J = f[i], f[:i], f[i + 1:]
        if op == '*':
            K, J = strip_outer(K), strip_outer(J)
        if K and J:
            return op, K, J, True
        return None
    masked = CA.sub(lambda m: 'x' * len(m.group()), f)
    pos = [i for i in depth0(masked) if masked[i] == '+']
    if len(pos) == 1 and '*' not in ''.join(masked[i] for i in depth0(masked)):
        i = pos[0]
        if f[:i] and f[i + 1:]:
            return '+', f[:i], f[i + 1:], False
    return None


def grid_of(prompt):
    return prompt.split(';')[0].rstrip()


def piece_prompt(prompt, formula):
    return f'{grid_of(prompt)} ; ={formula}'


def join_prompt(prompt, op, a, b):
    return f'{grid_of(prompt)} ; ={a}{op}{b}'


def pair_type(K, J):
    n = (':' in K) + (':' in J)
    return PAIRS[2 - n]


def num(x):
    return int(x) if str(x).isdigit() else str(x)


def same_call(model, tool):
    """Calls (op, a, b, result) as numbers: same op and operands; either order for add/mul/min/max."""
    if model[0] != tool[0]:
        return False
    a, b, c, d = num(model[1]), num(model[2]), num(tool[1]), num(tool[2])
    return (a, b) == (c, d) or (model[0] in SYM and (a, b) == (d, c))


def first_error(calls, steps, nK, nJ):
    """Why a whole question failed, from the model's calls vs the tool's steps: K / J / join (the first differing round
    is in K's rounds, J's, or the final join call), 'stopped/extra' (a prefix agrees but the count differs), or 'answer'."""
    for i, (m, t) in enumerate(zip(calls, steps)):
        if not same_call(m, t):
            return 'K' if i < nK else 'J' if i < nK + nJ else 'join'
    return 'stopped/extra' if len(calls) != len(steps) else 'answer'


def pct(h, n):
    return round(100.0 * h / n, 1) if n else None


def audit(m, rows, greedy=None):
    """Per-row records for one cell's rows (dicts with prompt, answer, kind, id) under model m."""
    if greedy is None:
        from domain.mode import greedy
    whole = greedy(m, [r['prompt'] for r in rows])
    recs, jobs = [], []
    for r, (calls, pred) in zip(rows, whole):
        f = r['prompt'].split(';', 1)[1].strip()[1:]
        rec = {'id': r['id'], 'kind': r['kind'], 'op': None, 'strict': None, 'W': int(pred.strip() == r['answer'].strip()),
               'P': 0, 'T': 0, 'first_error': None, 'pair': None, 'piece_refused': 0, 'join_refused': 0}
        recs.append(rec)
        sp = split_formula(f)
        res = sheet_tool.evaluate(r['prompt'])
        if sp is None:
            continue
        rec['op'], rec['K'], rec['J'], rec['strict'] = sp
        rec['pair'] = pair_type(sp[1], sp[2])
        ks, js = (sheet_tool.evaluate(piece_prompt(r['prompt'], x)) for x in sp[1:3])
        if '?' in (ks['value'], js['value']):
            rec['piece_refused'] = 1
            continue
        if not rec['W']:
            rec['first_error'] = first_error([tuple(c) for c in calls], [tuple(s) for s in res['steps']], len(ks['steps']), len(js['steps']))
        jobs.append((rec, r, ks['value'], js['value']))
    prompts = []
    for rec, r, kv, jv in jobs:
        prompts += [piece_prompt(r['prompt'], rec['K']), piece_prompt(r['prompt'], rec['J'])]
    out = greedy(m, prompts) if prompts else []
    nxt = []
    for i, (rec, r, kv, jv) in enumerate(jobs):
        a, b = out[2 * i][1].strip(), out[2 * i + 1][1].strip()
        rec['a'], rec['b'] = a, b
        rec['P'] = int(a == kv and b == jv)
        if rec['P']:
            jp = join_prompt(r['prompt'], rec['op'], a, b)
            jr = sheet_tool.evaluate(jp)
            if jr['value'] == '?':
                rec['join_refused'] = 1
            else:
                nxt.append((rec, jp, jr['value']))
    jout = greedy(m, [jp for _, jp, _ in nxt]) if nxt else []
    for (rec, jp, jv), (_, pred) in zip(nxt, jout):
        rec['join_pred'], rec['join_gold'] = pred.strip(), jv
        rec['T'] = int(pred.strip() == jv)
    return recs


def summarize(recs):
    n = len(recs)
    ok = [r for r in recs if r['op']]
    ok_n = len(ok)
    s = {'rows': n, 'split_ok': ok_n, 'split_strict': sum(1 for r in ok if r['strict']), 'split_failed': n - ok_n,
         'piece_refused': sum(r['piece_refused'] for r in recs), 'join_refused': sum(r['join_refused'] for r in recs)}
    for k in 'WPT':
        s[k] = sum(r[k] for r in recs)
        s[k + '_pct'] = pct(s[k], n)
        s[k + '_pct_of_split_ok'] = pct(sum(r[k] for r in ok), ok_n)
    s['T_minus_W'] = round(s['T_pct'] - s['W_pct'], 1) if n else None
    fails = [r for r in recs if r['first_error']]
    s['first_error'] = {e: sum(1 for r in fails if r['first_error'] == e) for e in ERRS}
    s['first_error_pct'] = {e: pct(v, len(fails)) for e, v in s['first_error'].items()}
    s['W_false_unsplit'] = sum(1 for r in recs if not r['W'] and not r['op'])
    s['by_pair'] = {p: {'rows': sum(1 for r in ok if r['pair'] == p), **{k: sum(r[k] for r in ok if r['pair'] == p) for k in 'WPT'}} for p in PAIRS}
    return s


def table(label, cells):
    lines = [f'== {label} ==',
             f'{"cell":7s} {"rows":>4s} {"split":>5s} {"W":>5s} {"P":>5s} {"T":>5s} {"T-W":>5s} | first error (of failed W, split ok): '
             'K / J / join / stopped-extra / answer-only']
    for c, s in cells.items():
        fe = s['first_error']
        lines.append(f'{c:7s} {s["rows"]:4d} {s["split_ok"]:5d} {s["W_pct"]:5.1f} {s["P_pct"]:5.1f} {s["T_pct"]:5.1f} {s["T_minus_W"]:5.1f} | '
                     + ' / '.join(str(fe[e]) for e in ERRS) + f'  (of {sum(fe.values())})')
        lines.append(f'        split ok: strict {s["split_strict"]}, via cell-arithmetic atom {s["split_ok"] - s["split_strict"]}, unsplit {s["split_failed"]} '
                     f'(W false among them {s["W_false_unsplit"]}); pieces refused {s["piece_refused"]}, joins refused {s["join_refused"]}; '
                     f'on split ok: W {s["W_pct_of_split_ok"]} P {s["P_pct_of_split_ok"]} T {s["T_pct_of_split_ok"]}')
        for p, v in s['by_pair'].items():
            lines.append(f'        {p:11s} rows {v["rows"]:3d}  W {pct(v["W"], v["rows"])}  P {pct(v["P"], v["rows"])}  T {pct(v["T"], v["rows"])}')
    return '\n'.join(lines)


def run(ckpt, probe, cells=CELLS):
    import torch
    from custom_io.models import load_model
    torch.set_num_threads(1)
    m = load_model(ckpt).eval()
    rows = [r for r in L.load_jsonl(probe) if r['kind'] in SP.SCORED]
    recs, out = {}, {}
    for c in cells:
        recs[c] = audit(m, [r for r in rows if r['split'] == c])
        out[c] = summarize(recs[c])
        print(f'{c}: W {out[c]["W"]}/{out[c]["rows"]} P {out[c]["P"]} T {out[c]["T"]}', flush=True)
    return out, recs


def main(argv=None):
    a = argparse.ArgumentParser(description='A1 join-gap audit: pieces vs join (scoring only).')
    a.add_argument('--ckpt', required=True)
    a.add_argument('--addon-rank', type=int)
    a.add_argument('--addon-alpha', type=float)
    a.add_argument('--probe', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--label', required=True)
    a.add_argument('--cells', default=','.join(CELLS))
    a = a.parse_args(argv)
    cells = [c for c in a.cells.split(',') if c]
    summ, recs = run(a.ckpt, a.probe, cells)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f'join-gap-{a.label}.json')
    with open(path, 'w') as f:
        json.dump({'label': a.label, 'ckpt': a.ckpt, 'probe': a.probe, 'addon': {'rank': a.addon_rank, 'alpha': a.addon_alpha,
                   'note': 'merged into the saved weights; nothing separate to load'}, 'cells': summ, 'rows': recs}, f, indent=1)
    print(table(a.label, summ))
    print('wrote', path)


if __name__ == '__main__':
    main()
