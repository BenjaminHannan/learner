"""Far-transfer probe for the RPN calculator domain: which change breaks the model on far RPN questions (diagnosis).

Builds sealed-style rpn prompts from random.Random(93002), using domain/panel.py's helpers (rpn_expect, rpn_draw for the
near help shapes, RPN_SHAPE, the rpn_far_shape logic with the operator count fixed), and accepts a row only when it
passes the checks of panel.fill_panel. Scores the parent and the rpn v7 s200 checkpoint with domain.score.score. For the
v7 misses, finds the first call where the model's calls differ from the tool's working (domain.tools.rpn.evaluate).
No training, no edits to existing files. Operators: + - * / only (no %). Values 1-99.

Cells (60 rows each; R4 and R5 are split by operator count):
  R0    near: the seven help shapes (RPN_SHAPE without 'a b %'), new numbers (panel.rpn_draw near rule)
  R1    three operators, new order: random postfix shapes with 3 operators, not the help layout of 'a b + c d + *'
  R2    four operators, random valid postfix order
  R3    five operators, random valid postfix order
  R4    left chains 'a b op c op d op ...' with 3, 4, 5 operators (20 rows each)
  R5    late pairs: all operands pushed first, then the operators (3 and 4 operators, 30 rows each)

Run from the repo root (writes only the two JSON outputs, plus the row file in the scratch folder):
  PYTHONDONTWRITEBYTECODE=1 python3 -m domain.far.rpn_probe [--scratch DIR] [--out DIR]
"""
import argparse
import json
import os
import random
from collections import Counter, defaultdict

import torch

from custom_io.models import load_model
from domain import panel
from domain.mode import greedy
from domain.score import score as score_ckpt
from domain.tools import ASCII, MAX_ANS, MAX_PROMPT, N_NUM, N_RES
from domain.tools import rpn as rpn_tool

SEED = 93002
OPS = '+-*/'  # no % here: the calculator's mod has no row form (mode.NO_ROW_FORM), so this mode cannot teach it
MAX_TRIES = 200000
THREADS = 2
SCRATCH = '/tmp/claude-0/-home-user-learner/fb790cc1-3a66-56ad-bced-917dde5a53d7/scratchpad'
OUT = '/mnt/project-files/far-transfer/diag'
CKPTS = {
    'parent_s200': '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt',
    'rpn_v7_s200': '/mnt/project-files/domain-mode/runs/rpn-s200-v7/night_4/checkpoint.pt',
}
PANEL_RPN = ('/mnt/project-files/domain-mode/panel/rpn.jsonl', '/mnt/project-files/domain-mode/panel/rpn.v2.jsonl')
HELP_KINDS = [k for k in panel.RPN_SHAPE if k != 'a b %']
HELP_SHAPES = [panel.RPN_SHAPE[k] for k in HELP_KINDS]
HELP_PROMPTS = {h['prompt'] for h in rpn_tool.help()}


# ---------- shapes ----------

def structure(shape):
    """The operand/operator layout of a shape: every operator becomes o (which operator is ignored)."""
    return ''.join('n' if ch == 'n' else 'o' for ch in shape)


def left_struct(k):
    """'a b op c op d op ...' with k operators: n n (o n)^(k-1) o."""
    return 'nn' + 'on' * (k - 1) + 'o'


def late_struct(k):
    """All k+1 operands first, then the k operators: n^(k+1) o^k."""
    return 'n' * (k + 1) + 'o' * k


HELP_STRUCTS = {structure(s) for s in HELP_SHAPES}
HELP_STRUCTS_3 = structure(panel.RPN_SHAPE['a b + c d + *'])  # the only help layout with three operators


def fill_ops(struct, rng):
    """A layout with a random operator (from + - * /) in each operator slot."""
    return ''.join(rng.choice(OPS) if ch == 'o' else 'n' for ch in struct)


def postfix_shape(rng, k):
    """panel.rpn_far_shape with the operator count fixed at k and the operators + - * / (no %)."""
    shape, pushed, stack, ops_left = '', 0, 0, k
    while pushed < k + 1 or ops_left:
        can_op = stack >= 2 and ops_left > 0
        if pushed < k + 1 and (not can_op or rng.random() < 0.5):
            shape += 'n'
            pushed += 1
            stack += 1
        else:
            shape += rng.choice(OPS)
            stack -= 1
            ops_left -= 1
    return shape


def max_stack(shape):
    depth = top = 0
    for ch in shape:
        depth += 1 if ch == 'n' else -1
        top = max(top, depth)
    return top


def stack_before(shape, i):
    """Values on the stack just before the i-th operator (0-based) runs; None when there is no such operator."""
    pushed = ops = 0
    for ch in shape:
        if ch == 'n':
            pushed += 1
        else:
            if ops == i:
                return pushed - ops
            ops += 1
    return None


# ---------- draws (each returns prompt, panel-style expect value, shape, help kind) ----------

def draw_help(i, rng):
    kind = HELP_KINDS[i % len(HELP_KINDS)]  # rows rotate over the seven help kinds
    prompt, expect, shape = panel.rpn_draw(kind, 'near', rng)
    return prompt, expect, shape, kind


def draw_shape(make):
    def draw(i, rng):
        tokens = [str(rng.randint(1, 99)) if ch == 'n' else ch for ch in make(rng)]
        return 'rpn: ' + ' '.join(tokens), panel.rpn_expect(tokens), ''.join(
            'n' if t.isdigit() else t for t in tokens), None
    return draw


def specs():
    """(cell, split, rows, draw, shape_ok)."""
    anything = lambda shape: True
    not_help_layout = lambda shape: structure(shape) not in HELP_STRUCTS
    return [
        ('R0', 'near', 60, draw_help, anything),
        ('R1', 'far', 60, draw_shape(lambda rng: postfix_shape(rng, 3)), not_help_layout),
        ('R2', 'far', 60, draw_shape(lambda rng: postfix_shape(rng, 4)), anything),
        ('R3', 'far', 60, draw_shape(lambda rng: postfix_shape(rng, 5)), anything),
        ('R4-3', 'far', 20, draw_shape(lambda rng: fill_ops(left_struct(3), rng)), anything),
        ('R4-4', 'far', 20, draw_shape(lambda rng: fill_ops(left_struct(4), rng)), anything),
        ('R4-5', 'far', 20, draw_shape(lambda rng: fill_ops(left_struct(5), rng)), anything),
        ('R5-3', 'far', 30, draw_shape(lambda rng: fill_ops(late_struct(3), rng)), anything),
        ('R5-4', 'far', 30, draw_shape(lambda rng: fill_ops(late_struct(4), rng)), anything),
        # Added after the nine cells above (so their rows are unchanged): controls that keep a HELP layout but draw
        # random operators, to separate "new layout" from "new operators". Not part of the original spec.
        ('C1', 'control', 30, draw_shape(lambda rng: fill_ops(HELP_STRUCTS_3, rng)), anything),
        ('C2-left2', 'control', 15, draw_shape(lambda rng: fill_ops(left_struct(2), rng)), anything),
        ('C2-late2', 'control', 15, draw_shape(lambda rng: fill_ops(late_struct(2), rng)), anything),
    ]


# ---------- checks (the panel.fill_panel checks, plus the operator and value rules of this probe) ----------

def panel_prompts():
    out = set()
    for path in PANEL_RPN:
        with open(path) as f:
            out |= {json.loads(line)['prompt'] for line in f if line.strip()}
    return out


def check(prompt, expect, shape, ok_shape, seen, banned):
    """(reason or None, tool result). A row is kept only when every check passes."""
    res = rpn_tool.evaluate(prompt)
    value = res['value']
    if value == '?':
        return 'tool ?', res
    if expect is None or str(expect) != value:
        return 'python disagrees', res
    if len(res['steps']) > N_RES:
        return 'steps over 7', res
    if len(prompt) > MAX_PROMPT:
        return 'prompt over 208', res
    if panel.numbers(prompt) > N_NUM:
        return 'numbers over 16', res
    if len(value) > MAX_ANS:
        return 'answer over 8', res
    if not set(prompt + value) <= ASCII:
        return 'not ascii', res
    tokens = prompt.split()[1:]
    if any(t.isdigit() and not 1 <= int(t) <= 99 for t in tokens) or any(t not in OPS and not t.isdigit() for t in tokens):
        return 'value or operator rule', res
    if not ok_shape(shape):
        return 'shape', res
    if prompt in HELP_PROMPTS:
        return 'help example', res
    if prompt in banned:
        return 'in panel rpn files', res
    if prompt in seen:
        return 'duplicate', res
    return None, res


def fill(cell, split, n, draw, ok_shape, rng, seen, banned):
    rows, st = [], Counter()
    while len(rows) < n:
        st['tries'] += 1
        if st['tries'] > MAX_TRIES:
            raise RuntimeError(f'{cell}: not full after {MAX_TRIES} draws')
        prompt, expect, shape, help_kind = draw(len(rows), rng)
        why, res = check(prompt, expect, shape, ok_shape, seen, banned)
        if why:
            st[why] += 1
            continue
        seen.add(prompt)
        rows.append(dict(id=f'rpnfar-{cell}-{len(rows):03d}', cell=cell, kind=cell, split=split, prompt=prompt,
                         answer=res['value'], shape=shape, help_kind=help_kind,
                         steps=[list(s) for s in res['steps']]))
    return rows, st


def build(seed=SEED):
    rng = random.Random(seed)
    banned = panel_prompts()
    seen, rows, stats = set(), [], {}
    for cell, split, n, draw, ok_shape in specs():
        cell_rows, st = fill(cell, split, n, draw, ok_shape, rng, seen, banned)
        rows += cell_rows
        stats[cell] = dict(st)
    return rows, stats, len(banned)


# ---------- per-row features and the first divergence from the tool's working ----------

def features(row):
    shape, steps = row['shape'], row['steps']
    k = sum(ch in OPS for ch in shape)
    s = structure(shape)
    cls = 'left' if s == left_struct(k) else 'late' if s == late_struct(k) else 'other'
    mix = 'has - or /' if any(ch in '-/' for ch in shape) else '+ and * only'
    return dict(k=k, cls=cls, mix=mix, k_mix=f'{k} ops, {mix}', max_stack=max_stack(shape), final_op=shape[-1],
                max_digits=max(len(st[3]) for st in steps), ans_digits=len(row['answer']))


def operand_src(steps, i):
    """'R' when an operand equals an earlier call's result, else 'P' (a prompt number). Approximate: a prompt number
    equal to an earlier result is counted as R."""
    earlier = {st[3] for st in steps[:i]}
    return ['R' if x in earlier else 'P' for x in (steps[i][1], steps[i][2])]


def first_divergence(shape, model_calls, tool_steps):
    m = [tuple(map(str, c)) for c in model_calls]
    t = [tuple(map(str, c)) for c in tool_steps]
    if m == t:
        return None  # the calls match the tool's working; the miss (if any) is in the answer
    for i in range(max(len(m), len(t))):
        if i >= len(m):
            kind = 'stopped early'
        elif i >= len(t):
            kind = 'extra call'
        elif m[i] != t[i]:
            kind = '+'.join(f for f, x, y in zip(('op', 'a', 'b', 'result'), m[i], t[i]) if x != y)
        else:
            continue
        has_tool = i < len(t)
        return dict(index=i, kind=kind, model=list(m[i]) if i < len(m) else None,
                    tool=list(t[i]) if has_tool else None,
                    tool_op=t[i][0] if has_tool else None,
                    tool_src=operand_src(t, i) if has_tool else None,
                    stack_before=stack_before(shape, i) if has_tool else None)
    return None


# ---------- scoring ----------

def score_all(rows):
    torch.set_num_threads(THREADS)
    srows = [dict(id=r['id'], prompt=r['prompt'], answer=r['answer'], kind=r['cell'], split=r['split']) for r in rows]
    return {label: score_ckpt(ck, srows, label) for label, ck in CKPTS.items()}


def pct(hits):
    return round(100.0 * sum(hits) / len(hits), 1) if hits else None


def by_factor(rows, hit_of, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r['feat'][key]].append(hit_of[r['id']])
    return {str(k): dict(n=len(v), hit_pct=pct(v)) for k, v in sorted(groups.items(), key=lambda kv: str(kv[0]))}


def analyse(rows, scored):
    hits = {label: {x['id']: x['hit'] for x in scored[label]['rows']} for label in CKPTS}
    preds = {label: {x['id']: x['pred'] for x in scored[label]['rows']} for label in CKPTS}
    for r in rows:
        r['feat'] = features(r)
    cells = {}
    for cell in dict.fromkeys(r['cell'] for r in rows):
        cr = [r for r in rows if r['cell'] == cell]
        cells[cell] = dict(split=cr[0]['split'], n=len(cr), description=None,
                           **{f'{label}_hit_pct': pct([hits[label][r['id']] for r in cr]) for label in CKPTS})
    factor_keys = ['k', 'mix', 'k_mix', 'cls', 'max_stack', 'final_op', 'max_digits', 'ans_digits']
    factors = {label: {key: by_factor(rows, hits[label], key) for key in factor_keys} for label in CKPTS}
    # v7: greedy calls, cross-checked against the scorer's answers; first divergence on each miss
    v7 = load_model(CKPTS['rpn_v7_s200']).eval()
    res = greedy(v7, [r['prompt'] for r in rows])
    mismatch = sum(1 for r, (_, a) in zip(rows, res) if preds['rpn_v7_s200'][r['id']].strip() != a.strip())
    misses, div_by_cell, div_idx, div_kind, src_counts, subst, src_late = [], defaultdict(Counter), Counter(), Counter(), Counter(), Counter(), Counter()
    tool_src_all = Counter()
    for r, (calls, ans) in zip(rows, res):
        for i in range(len(r['steps'])):
            tool_src_all[('all', ''.join(operand_src(r['steps'], i)))] += 1
        if hits['rpn_v7_s200'][r['id']]:
            continue
        d = first_divergence(r['shape'], calls, r['steps'])
        if d is None:
            label = 'calls match, answer wrong'
            div_by_cell[r['cell']][label] += 1
            div_idx[label] += 1
        else:
            label = f"call {d['index']}"
            div_by_cell[r['cell']][label] += 1
            div_idx[label] += 1
            div_kind[d['kind']] += 1
            if d['tool_src']:
                src_counts[''.join(d['tool_src'])] += 1
                if d['index'] >= 1:
                    src_late[''.join(d['tool_src'])] += 1
            if d['tool_op'] is not None and d['model']:
                subst[f"{d['tool_op']}->{d['model'][0]}"] += 1
        misses.append(dict(id=r['id'], cell=r['cell'], prompt=r['prompt'], tool_answer=r['answer'],
                           model_answer=ans.strip(), model_calls=[list(c) for c in calls],
                           first_divergence=d))
    base = {k[1]: v for k, v in tool_src_all.items()}
    return dict(cells=cells, factors=factors, v7_scorer_vs_greedy_mismatch=mismatch, misses=misses,
                v7_divergence_by_cell={c: dict(v) for c, v in div_by_cell.items()},
                v7_divergence_index=dict(div_idx), v7_divergence_kind=dict(div_kind),
                v7_divergence_operand_sources=dict(src_counts),
                v7_divergence_operand_sources_index_ge1=dict(src_late),
                v7_op_substitution_at_divergence=dict(subst),
                all_tool_steps_operand_sources=base)


def main(argv=None):
    ap = argparse.ArgumentParser(description='RPN far-transfer probe (diagnosis; scoring only).')
    ap.add_argument('--scratch', default=SCRATCH, help='where the row file goes (not the project output folder)')
    ap.add_argument('--out', default=OUT, help='where rpn-factors.json goes')
    a = ap.parse_args(argv)
    rows, stats, n_banned = build()
    os.makedirs(a.scratch, exist_ok=True)
    rows_path = os.path.join(a.scratch, 'rpn-far-probe-rows.jsonl')
    with open(rows_path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    print('rows', len(rows), 'panel prompts banned', n_banned, 'wrote', rows_path, flush=True)
    for cell, st in stats.items():
        print(f"  {cell:5s} tries {st['tries']:6d} rejected {', '.join(f'{k} {v}' for k, v in st.items() if k not in ('tries',) and v)}")
    scored = score_all(rows)
    for label in CKPTS:
        print(label, 'overall', scored[label]['overall'], scored[label]['by_split'], flush=True)
    out = analyse(rows, scored)
    for r in rows:
        r.pop('feat', None)
    for cell, c in out['cells'].items():
        print(f"  {cell:5s} n {c['n']:3d}  parent {c['parent_s200_hit_pct']}  v7 {c['rpn_v7_s200_hit_pct']}"
              f"  v7 first divergence {out['v7_divergence_by_cell'].get(cell, {})}")
    print('v7 scorer vs greedy mismatches', out['v7_scorer_vs_greedy_mismatch'])
    print('v7 divergence kinds', out['v7_divergence_kind'])
    print('v7 divergence operand sources (a,b)', out['v7_divergence_operand_sources'])
    print('all tool steps operand sources', out['all_tool_steps_operand_sources'])
    for label in CKPTS:
        print(label, 'by k', {k: v['hit_pct'] for k, v in out['factors'][label]['k'].items()})
        print(label, 'by cls', {k: v['hit_pct'] for k, v in out['factors'][label]['cls'].items()})
        print(label, 'by max_stack', {k: v['hit_pct'] for k, v in out['factors'][label]['max_stack'].items()})
    result = dict(seed=SEED, ops=OPS, n_rows=len(rows), cell_generation=stats, panel_prompts_banned=n_banned,
                  checkpoints=CKPTS, runs={label: dict(overall=scored[label]['overall'],
                                                       by_split=scored[label]['by_split'])
                                           for label in CKPTS},
                  **out)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, 'rpn-factors.json')
    with open(path, 'w') as f:
        json.dump(result, f, indent=1)
    print('wrote', path, flush=True)


if __name__ == '__main__':
    main()
