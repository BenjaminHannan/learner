"""Anatomy of far-transfer misses in domain mode (diagnosis only: scores checkpoints, trains nothing, edits nothing).

For each row of the panel: the tool's working (domain.tools.sheet / rpn evaluate) and the model's greedy calls are
compared step by step. A miss is placed at its first divergence:
  right_calls_wrong_answer  every call matched, the answer text did not
  stopped_early             the model made fewer calls, all matched
  extra_calls               the model's calls all matched, then it kept calling
  wrong_op                  the first differing call has another op
  wrong_operand             the same op with another operand (slot a, b or both)

For a sheet wrong operand, the tool's operand is traced back to its grid cell (lab_eval mirrors sheet._ev and also
returns the label of each operand; the mirror is checked against sheet.evaluate on every row), and the model's value
is looked up in the grid, so the expected cell can be compared with the cell the model used.

  python3 -m domain.far.anatomy [--out DIR] [--limit N]

Writes DIR/anatomy.json and DIR/anatomy.md (default DIR: /mnt/project-files/far-transfer/diag). The panel is read
for scoring only, as domain/score.py does; the model never sees it.
"""
import argparse
import collections
import json
import os
import re

import torch

from custom_io.models import load_model
from domain.mode import NO_ROW_FORM, greedy
from domain.tools import Fail, Runner, rpn, sheet

PANEL = '/mnt/project-files/domain-mode/panel'
SHEET_PANEL = os.path.join(PANEL, 'sheet.v2.jsonl')
RPN_PANEL = os.path.join(PANEL, 'rpn.v2.jsonl')
RUNS = '/mnt/project-files/domain-mode/runs'
OUT = '/mnt/project-files/far-transfer/diag'
CKPTS = [  # (label, domain, checkpoint)
    ('sheet v7 s200 final', 'sheet', os.path.join(RUNS, 'sheet-s200-v7/night_7/checkpoint.pt')),
    ('sheet v7 s201 final', 'sheet', os.path.join(RUNS, 'sheet-s201-v7/night_8/checkpoint.pt')),
    ('rpn v7 s200 final', 'rpn', os.path.join(RUNS, 'rpn-s200-v7/night_4/checkpoint.pt')),
]
SHEET_KINDS = ('SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'ABS')
RPN_EXCLUDED = 'a b %'
COMMUTATIVE = {'add', 'mul', 'min', 'max'}
DIVS = ['wrong_op', 'wrong_operand', 'stopped_early', 'extra_calls', 'right_calls_wrong_answer']
CELL = re.compile(r'([A-Z])([0-9]+)')


# ---------- the tool's working, with the label of each operand (sheet) ----------

class LabelRunner(Runner):
    """Runner that also records each step's operand labels: a cell such as 'A5', 'calc' or 'const'."""

    def __init__(self):
        super().__init__()
        self.labels = []

    def lcall(self, op, a, b, la, lb):
        r = self.call(op, a, b)
        self.labels.append((la, lb))
        return r


def lab_eval(node, grid, rn):
    """Mirror of sheet._ev (same calls in the same order) that also returns the label of the value: (value, label)."""
    k = node[0]
    if k == 'num':
        return node[1], 'const'
    if k == 'ref':
        return sheet._cells(grid, node[1], node[2])[0], '%s%d' % (node[1], node[2])
    if k == 'bin':
        a, la = lab_eval(node[2], grid, rn)
        b, lb = lab_eval(node[3], grid, rn)
        return rn.lcall(sheet.BIN_OP[node[1]], a, b, la, lb), 'calc'
    if k in sheet.AGG_OP:
        col, r1, r2 = node[1]
        vals = sheet._cells(grid, col, r1, r2)
        acc, la = vals[0], '%s%d' % (col, r1)
        for i, v in enumerate(vals[1:], start=1):
            acc = rn.lcall(sheet.AGG_OP[k], acc, v, la, '%s%d' % (col, r1 + i))
            la = 'calc'
        return acc, la
    if k == 'ABS':
        arg = node[1]
        if arg[0] == 'bin' and arg[1] == '-':
            x, lx = lab_eval(arg[2], grid, rn)
            y, ly = lab_eval(arg[3], grid, rn)
            hi = rn.lcall('max', x, y, lx, ly)
            lo = rn.lcall('min', x, y, lx, ly)
            return rn.lcall('sub', hi, lo, 'calc', 'calc'), 'calc'
        return lab_eval(arg, grid, rn)
    if k == 'MOD':
        a, la = lab_eval(node[1], grid, rn)
        b, lb = lab_eval(node[2], grid, rn)
        return rn.lcall('mod', a, b, la, lb), 'calc'
    if k == 'COUNTIF':
        col, r1, r2 = node[1]
        kk, total = node[2], None
        for r in range(r1, r2 + 1):
            x = sheet._cells(grid, col, r)[0]
            t = rn.lcall('cmp', rn.lcall('max', x, kk, '%s%d' % (col, r), 'const'), kk, 'calc', 'const')
            total = t if total is None else rn.lcall('add', total, t, 'calc', 'calc')
        return total, 'calc'
    if k == 'IF':
        vl, ll = lab_eval(node[1], grid, rn)
        vr, lr = lab_eval(node[2], grid, rn)
        t = rn.lcall('cmp', rn.lcall('max', vl, vr, ll, lr), vr, 'calc', lr)
        vx, lx = lab_eval(node[3], grid, rn)
        vy, ly = lab_eval(node[4], grid, rn)
        p = rn.lcall('mul', t, vx, 'calc', lx)
        u = rn.lcall('sub', 1, t, 'const', 'calc')
        q = rn.lcall('mul', u, vy, 'calc', ly)
        return rn.lcall('add', p, q, 'calc', 'calc'), 'calc'
    raise Fail('unknown node ' + k)


def trace_sheet(prompt):
    """The tool's value, steps, operand labels and parsed grid for a sheet prompt."""
    rn = LabelRunner()
    grid, formula_text = {}, ''
    try:
        if prompt.count(';') != 1:
            raise Fail('need exactly one ;')
        grid_text, formula = prompt.split(';')
        formula_text = formula
        formula = formula.strip()
        if not formula.startswith('='):
            raise Fail('formula must start with =')
        grid = sheet._parse_grid(grid_text)
        p = sheet._Parser(sheet._tokens(formula[1:]))
        node = p.expr()
        if p.peek()[0] is not None:
            raise Fail('text after the formula')
        value = str(lab_eval(node, grid, rn)[0])
    except (Fail, RecursionError):
        value = '?'
    # numbers the model may copy: grid values and literal numbers in the formula (not the digits of a cell name)
    nums = {v for vals in grid.values() for v in vals}
    nums |= {int(x) for x in re.findall(r'(?<![A-Za-z0-9])[0-9]+', formula_text)}
    return dict(value=value, steps=list(rn.steps), labels=list(rn.labels), grid=grid, prompt_nums=nums)


def trace_rpn(prompt):
    ev = rpn.evaluate(prompt)
    toks = re.sub(r'^\s*rpn:', '', prompt).split()
    return dict(value=ev['value'], steps=[tuple(s) for s in ev['steps']], labels=None, grid={},
                prompt_nums={int(t) for t in toks if re.fullmatch(r'[0-9]+', t)},
                n_ops=sum(1 for t in toks if t in rpn.OPS))


# ---------- classification ----------

def as_int(s):
    try:
        return int(str(s).strip())
    except ValueError:
        return None


def same_call(t, m):
    """Same op and operands; add, mul, min and max also match with a and b swapped."""
    if t[0] != m[0]:
        return False
    if t[1] == m[1] and t[2] == m[2]:
        return True
    return t[0] in COMMUTATIVE and t[1] == m[2] and t[2] == m[1]


def cells_holding(grid, v):
    return sorted((col, r + 1) for col, vals in grid.items() for r, x in enumerate(vals) if x == v)


def pick_used(cands, exp_col, exp_row):
    """The cell the model used: same column first, then the nearest row."""
    return sorted(cands, key=lambda c: (c[0] != exp_col, abs(c[1] - exp_row), c[0], c[1]))[0]


def operand_event(slot, i, t, m, k, row, prior):
    """One wrong operand: where the tool's value sits in the grid and where the model's value came from."""
    labels = row['labels']
    lab = labels[k][i - 1] if labels is not None and k < len(labels) else None
    if lab is None:
        exp_src, exp_cell = 'unknown', None
    elif CELL.fullmatch(lab):
        exp_src, exp_cell = 'grid_cell', lab
    elif lab == 'calc':
        exp_src, exp_cell = 'intermediate', None
    else:
        exp_src, exp_cell = 'const', None
    mv = as_int(m[i])
    cands = cells_holding(row['grid'], mv) if mv is not None else []
    if cands:
        model_src = 'grid'
    elif mv is not None and mv in prior:
        model_src = 'prior_result'
    elif mv is not None and mv in row['prompt_nums']:
        model_src = 'prompt_number'
    else:
        model_src = 'other'
    used = None
    if exp_src == 'grid_cell' and cands:
        col, r = exp_cell[0], int(exp_cell[1:])
        uc, ur = pick_used(cands, col, r)
        used = '%s%d' % (uc, ur)
    return dict(slot=slot, exp_src=exp_src, exp_cell=exp_cell, exp_val=t[i], model_val=m[i],
                model_src=model_src, used_cell=used, n_cand=len(cands))


def classify(row, model_calls, model_ans):
    tc = [tuple(s[:3]) for s in row['steps']]
    mc = [tuple(str(x).strip() for x in c[:3]) for c in model_calls]
    hit = model_ans.strip() == row['value'].strip()
    n = min(len(tc), len(mc))
    k = 0
    while k < n and same_call(tc[k], mc[k]):
        k += 1
    rec = dict(id=row['id'], kind=row['kind'], split=row['split'], hit=hit, untrainable=row['untrainable'],
               n_tool=len(tc), n_model=len(mc), prefix_ok=k, div=None, div_slot=None, events=[],
               grid_rows=row['grid_rows'], n_ops=row['n_ops'])
    if hit:
        return rec
    if k == n:
        rec['div'] = ('stopped_early' if len(mc) < len(tc) else
                      'extra_calls' if len(mc) > len(tc) else 'right_calls_wrong_answer')
        return rec
    t, m = tc[k], mc[k]
    if t[0] != m[0]:
        rec['div'] = 'wrong_op'
        return rec
    rec['div'] = 'wrong_operand'
    wrong = [i for i in (1, 2) if t[i] != m[i]]
    rec['div_slot'] = {(1,): 'a', (2,): 'b', (1, 2): 'both'}[tuple(wrong)]
    prior_before = {as_int(c[3]) for c in model_calls[:k]}
    rec['events'] = [operand_event('a' if i == 1 else 'b', i, t, m, k, row, prior_before) for i in wrong]
    return rec


# ---------- summaries ----------

def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def bucket(recs, key):
    out = {}
    for r in recs:
        if r[key] is None:
            continue
        n, h = out.get(str(r[key]), (0, 0))
        out[str(r[key])] = (n + 1, h + int(r['hit']))
    return {k: dict(n=n, hits=h, hit_pct=pct(h, n)) for k, (n, h) in sorted(out.items(), key=lambda kv: kv[0])}


def summarise(recs):
    misses = [r for r in recs if not r['hit']]
    tr = [r for r in recs if not r['untrainable']]
    ut = [r for r in recs if r['untrainable']]
    events = [e for r in misses for e in r['events']]
    conf = [e for e in events if e['used_cell']]
    row_of = lambda c: int(c[1:])
    col_of = lambda c: c[0]
    out = dict(
        n=len(recs), hits=sum(r['hit'] for r in recs), hit_pct=pct(sum(r['hit'] for r in recs), len(recs)),
        untrainable_n=len(ut), untrainable_pct=pct(len(ut), len(recs)),
        trainable_n=len(tr), trainable_hit_pct=pct(sum(r['hit'] for r in tr), len(tr)),
        misses=len(misses),
        prefix_ok_hist={str(k): v for k, v in sorted(collections.Counter(r['prefix_ok'] for r in misses).items())},
        divergence={d: sum(1 for r in misses if r['div'] == d) for d in DIVS},
        divergence_pct_of_misses={d: pct(sum(1 for r in misses if r['div'] == d), len(misses)) for d in DIVS},
        wrong_operand_slot=dict(collections.Counter(r['div_slot'] for r in misses if r['div'] == 'wrong_operand')),
        calls_model_minus_tool={str(k): v for k, v in
                                sorted(collections.Counter(r['n_model'] - r['n_tool'] for r in misses).items())},
        operand_events=len(events),
        event_expected_source=dict(collections.Counter(e['exp_src'] for e in events)),
        event_model_source=dict(collections.Counter(e['model_src'] for e in events)),
        event_model_source_when_expected_grid=dict(
            collections.Counter(e['model_src'] for e in events if e['exp_src'] == 'grid_cell')),
        grid_events_with_used_cell=len(conf),
        grid_events_ambiguous_pct=pct(sum(e['n_cand'] > 1 for e in conf), len(conf)),
        same_column_pct=pct(sum(col_of(e['exp_cell']) == col_of(e['used_cell']) for e in conf), len(conf)),
        top10_confusions=[dict(expected=a.split('->')[0], used=a.split('->')[1], n=n) for a, n in
                          collections.Counter('%s->%s' % (e['exp_cell'], e['used_cell']) for e in conf).most_common(10)],
        top10_row_pairs=[dict(expected_row=int(a.split('->')[0]), used_row=int(a.split('->')[1]), n=n) for a, n in
                         collections.Counter('%d->%d' % (row_of(e['exp_cell']), row_of(e['used_cell']))
                                             for e in conf).most_common(10)],
        col_pairs=[dict(expected_col=a.split('->')[0], used_col=a.split('->')[1], n=n) for a, n in
                   collections.Counter('%s->%s' % (col_of(e['exp_cell']), col_of(e['used_cell'])) for e in conf)
                   .most_common(10)],
        row_shift_used_minus_expected={str(k): v for k, v in sorted(collections.Counter(
            row_of(e['used_cell']) - row_of(e['exp_cell']) for e in conf).items())},
        by_kind=bucket(recs, 'kind'),
        by_n_tool=bucket(recs, 'n_tool'),
        by_grid_rows=bucket(recs, 'grid_rows'),
        by_n_ops=bucket(recs, 'n_ops'),
    )
    return out


def fmt_calls(calls):
    return '; '.join('%s(%s,%s)=%s' % (str(c[0]).strip(), str(c[1]).strip(), str(c[2]).strip(), str(c[3]).strip())
                     for c in calls) or '(none)'


def pick_examples(recs, rows, outs, k=8):
    """8 far misses: first one of each kind in panel order, then fill."""
    far = [i for i, r in enumerate(recs) if r['split'] == 'far' and not r['hit']]
    chosen, seen = [], set()
    for i in far:
        if recs[i]['kind'] not in seen and len(chosen) < k:
            chosen.append(i)
            seen.add(recs[i]['kind'])
    for i in far:
        if len(chosen) >= k:
            break
        if i not in chosen:
            chosen.append(i)
    return [dict(id=rows[i]['id'], kind=rows[i]['kind'], prompt=rows[i]['prompt'],
                 tool_value=rows[i]['value'], tool_working=fmt_calls(rows[i]['steps']),
                 model_calls=fmt_calls(outs[i][0]), model_answer=outs[i][1].strip(),
                 divergence=recs[i]['div'], prefix_ok=recs[i]['prefix_ok'],
                 n_tool=recs[i]['n_tool'], n_model=recs[i]['n_model']) for i in chosen]


# ---------- panel rows ----------

def load_rows(path, keep):
    out = []
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if keep(r):
                    out.append(r)
    return out


def prepare(rows, domain, limit=0):
    """Tool traces for the rows; checks the tool's value against the panel answer (and sheet labels against the tool)."""
    if limit:
        rows = rows[:limit]
    prepared, checks = [], dict(rows=len(rows), tool_value_ne_panel_answer=0, tool_value_question_mark=0,
                                label_mirror_mismatch=0)
    for r in rows:
        tr = trace_sheet(r['prompt']) if domain == 'sheet' else trace_rpn(r['prompt'])
        if domain == 'sheet':
            ref = sheet.evaluate(r['prompt'])
            if ref['value'] != tr['value'] or [tuple(s) for s in ref['steps']] != tr['steps']:
                checks['label_mirror_mismatch'] += 1
        else:
            ref = rpn.evaluate(r['prompt'])
            if ref['value'] != tr['value']:
                checks['label_mirror_mismatch'] += 1
        if tr['value'] != str(r['answer']).strip():
            checks['tool_value_ne_panel_answer'] += 1
        if tr['value'] == '?':
            checks['tool_value_question_mark'] += 1
        ops = {s[0] for s in tr['steps']}
        grid_rows = max((len(v) for v in tr['grid'].values()), default=None) if tr['grid'] else None
        prepared.append(dict(id=r['id'], kind=r['kind'], split=r['split'], prompt=r['prompt'],
                             answer=str(r['answer']).strip(), value=tr['value'], steps=tr['steps'],
                             labels=tr['labels'], grid=tr['grid'], prompt_nums=tr['prompt_nums'],
                             untrainable=bool(ops & NO_ROW_FORM), grid_rows=grid_rows,
                             n_ops=tr.get('n_ops') if domain == 'rpn' else None))
    return prepared, checks


def run_one(label, domain, path, rows):
    m = load_model(path).eval()
    res = greedy(m, [r['prompt'] for r in rows])
    recs = [classify(r, calls, ans) for r, (calls, ans) in zip(rows, res)]
    ops_seen = dict(collections.Counter(str(c[0]).strip() for calls, _ in res for c in calls))
    block = {}
    for split in ('near', 'far'):
        idx = [i for i, r in enumerate(recs) if r['split'] == split]
        block[split] = summarise([recs[i] for i in idx])
    block['ops_seen_in_model_calls'] = ops_seen
    if domain == 'sheet':
        block['far_examples'] = pick_examples(recs, rows, res)
    return block


# ---------- output ----------

def render_md(out):
    L = ['# Far-transfer anatomy: how the trained model misses (measured)', '',
         'Scored rows only: sheet = the 7 scored kinds of sheet.v2; rpn = every kind except `a b %` (rpn.v2). Greedy '
         'answers, calculator on. "needs mod/cmp" is the share of rows whose tool working uses op mod or cmp: the '
         'ceiling for this training mode. Hit = model answer equals the tool value. Numbers are measured.', '']
    for label, block in out['checkpoints'].items():
        L += ['## %s' % label, '']
        L += ['| split | n | hit % | needs mod/cmp % (ceiling) | hit % on trainable rows | misses |',
              '|---|---|---|---|---|---|']
        for split in ('near', 'far'):
            s = block[split]
            L.append('| %s | %d | %s | %s | %s | %d |' % (split, s['n'], s['hit_pct'], s['untrainable_pct'],
                                                        s['trainable_hit_pct'], s['misses']))
        L.append('')
        for split in ('near', 'far'):
            s = block[split]
            L += ['### %s: misses' % split, '']
            L.append('- first divergence: ' + ', '.join('%s %d (%s%%)' % (d, s['divergence'][d],
                                                                           s['divergence_pct_of_misses'][d])
                                                       for d in DIVS))
            L.append('- prefix_ok (leading model calls equal to the tool): ' +
                     ', '.join('%s: %d' % kv for kv in s['prefix_ok_hist'].items()))
            L.append('- model calls minus tool calls: ' +
                     ', '.join('%s: %d' % kv for kv in s['calls_model_minus_tool'].items()))
            if s['operand_events']:
                L.append('- wrong operands: %d events; tool operand from %s; model operand from %s' %
                         (s['operand_events'], s['event_expected_source'], s['event_model_source']))
                L.append('- grid events with a used cell: %d; same column %s%%; ambiguous value %s%%; row shift '
                         '(used minus expected) %s' % (s['grid_events_with_used_cell'], s['same_column_pct'],
                                                      s['grid_events_ambiguous_pct'], s['row_shift_used_minus_expected']))
            if s['top10_confusions']:
                L += ['', '| expected cell | used cell | n |', '|---|---|---|']
                L += ['| %s | %s | %d |' % (c['expected'], c['used'], c['n']) for c in s['top10_confusions']]
            L.append('')
        L.append('by kind (near / far hit %): ' + '; '.join(
            '%s %s/%s' % (k, block['near']['by_kind'].get(k, {}).get('hit_pct'),
                          block['far']['by_kind'].get(k, {}).get('hit_pct'))
            for k in sorted(set(block['near']['by_kind']) | set(block['far']['by_kind']))))
        L.append('')
        if block.get('far_examples'):
            L += ['### far examples (misses)', '']
            for e in block['far_examples']:
                L += ['- %s (%s) `%s`' % (e['id'], e['kind'], e['prompt']),
                      '  - tool value %s; tool working: %s' % (e['tool_value'], e['tool_working']),
                      '  - model calls: %s; model answer %s; first divergence %s after %d matching calls '
                      '(tool made %d, model made %d)' %
                      (e['model_calls'], e['model_answer'], e['divergence'], e['prefix_ok'], e['n_tool'],
                       e['n_model'])]
            L.append('')
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--limit', type=int, default=0, help='first N rows per panel (0 = all); quick checks only')
    args = ap.parse_args(argv)
    torch.set_num_threads(2)
    os.makedirs(args.out, exist_ok=True)

    sheet_rows = load_rows(SHEET_PANEL, lambda r: r['kind'] in SHEET_KINDS)
    rpn_rows = load_rows(RPN_PANEL, lambda r: r['kind'] != RPN_EXCLUDED)
    rpn_excluded = load_rows(RPN_PANEL, lambda r: r['kind'] == RPN_EXCLUDED)
    s_prep, s_checks = prepare(sheet_rows, 'sheet', args.limit)
    r_prep, r_checks = prepare(rpn_rows, 'rpn', args.limit)

    out = dict(
        meta=dict(
            panels=dict(sheet=SHEET_PANEL, rpn=RPN_PANEL), scored_sheet_kinds=list(SHEET_KINDS),
            rpn_excluded_kind=RPN_EXCLUDED, rpn_excluded_rows=len(rpn_excluded),
            rpn_excluded_mod_share_pct=pct(sum(1 for r in rpn_excluded if 'mod' in
                                               {s[0] for s in trace_rpn(r['prompt'])['steps']}), len(rpn_excluded)),
            checks=dict(sheet=s_checks, rpn=r_checks),
            definitions=dict(
                hit='model answer == tool value (strip)',
                prefix_ok='leading model calls whose op and operands equal the tool call (add/mul/min/max: a and b '
                          'may be swapped)',
                divergence='first differing call: wrong_op, wrong_operand, or stopped_early / extra_calls when all '
                           'compared calls matched; right_calls_wrong_answer when all calls matched and the answer '
                           'text did not',
                needs_untrainable='tool working uses op mod or cmp (domain.mode.NO_ROW_FORM)',
                operand_source='grid = the value is in the grid; prior_result = equals an earlier call result of '
                               'the model; prompt_number = a literal in the prompt; other = none of these',
                expected_source='grid_cell = the tool operand is a grid cell (traced by lab_eval); intermediate = a '
                                'tool result; const = a formula literal'),
            note='Shown: measured on the sealed panel rows and the checkpoints named. Suggested readings are '
                 'in the final message, not here.'),
        checkpoints={})
    for label, domain, path in CKPTS:
        rows = s_prep if domain == 'sheet' else r_prep
        out['checkpoints'][label] = run_one(label, domain, path, rows)
        print('done', label, flush=True)

    with open(os.path.join(args.out, 'anatomy.json'), 'w') as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(args.out, 'anatomy.md'), 'w') as f:
        f.write(render_md(out))
    print('wrote', args.out, flush=True)
    return out


if __name__ == '__main__':
    main()
