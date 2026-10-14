"""P2 zero-GPU far diagnostics (scoring only, nothing is trained): marks in MARKS-P2-diagnostics-2026-10-14.md.

  python3 -m domain.far.p2_diag collect --ckpt PATH --probe sheet-probe.jsonl --label NAME --out DIR [--limit N]
  python3 -m domain.far.p2_diag report --raw DIR [--items L13=items.jsonl ...] [--out report.md]

collect: on the probe's joined cells (F4-two, F5-far) runs the model on the whole question, on each piece alone (same grid), and on the
join of its own two piece answers (as join_gap does), and KEEPS THE CALLS of every run. report: from the saved raw files only (no model):
answer-format check, the partial-credit ladder (in order and order-free), piece accuracy alone vs inside the join, the combine rate and
one merged error taxonomy of the failed whole rows. --items adds per-item files from dump_items (every cell) to the taxonomy only.
"""
import argparse
import glob
import json
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from domain.far import join_gap as JG
from domain.far import learn_probe as L
from domain.far import sheet_probe as SP
from domain.tools import sheet as sheet_tool

CELLS = ('F4-two', 'F5-far')
NUMS = re.compile(r'\d+')


def steps_of(prompt):
    r = sheet_tool.evaluate(prompt)
    return [tuple(s) for s in r['steps']], r['value']


def collect(ckpt, probe, cells=CELLS, threads=2, limit=None):
    """-> list of per-row dicts: the tool's working, the model's calls and answer on the whole question, on K alone, on J alone and on
    the join of its own piece answers (when both piece answers are right)."""
    import torch
    from custom_io.models import load_model
    from domain.mode import greedy
    torch.set_num_threads(threads)
    m = load_model(ckpt).eval()
    rows = [r for r in L.load_jsonl(probe) if r['kind'] in SP.SCORED and r['split'] in cells]
    if limit:
        rows = [r for c in cells for r in [x for x in rows if x['split'] == c][:limit]]
    recs, prompts = [], []
    for r in rows:
        f = r['prompt'].split(';', 1)[1].strip()[1:]
        st, val = steps_of(r['prompt'])
        rec = dict(id=r['id'], cell=r['split'], kind=r['kind'], prompt=r['prompt'], gold=r['answer'], steps=[list(s) for s in st],
                   tool_value=val, split=False)
        sp = JG.split_formula(f)
        if sp:
            op, K, J, strict = sp
            ks, kv = steps_of(JG.piece_prompt(r['prompt'], K))
            js, jv = steps_of(JG.piece_prompt(r['prompt'], J))
            rec.update(split=True, op=op, K=K, J=J, strict=strict, pair=JG.pair_type(K, J), k_steps=[list(s) for s in ks],
                       j_steps=[list(s) for s in js], k_val=kv, j_val=jv, refused=int('?' in (kv, jv)))
        recs.append(rec)
        prompts.append(r['prompt'])
    jobs = [rec for rec in recs if rec['split'] and not rec['refused']]
    for rec in jobs:
        prompts += [JG.piece_prompt(rec['prompt'], rec['K']), JG.piece_prompt(rec['prompt'], rec['J'])]
    out = greedy(m, prompts)
    for rec, (calls, pred) in zip(recs, out):
        rec['calls'], rec['pred'] = [list(c) for c in calls], pred.strip()
    for i, rec in enumerate(jobs):
        (kc, kp), (jc, jp) = out[len(recs) + 2 * i], out[len(recs) + 2 * i + 1]
        rec['k_alone'] = dict(calls=[list(c) for c in kc], pred=kp.strip())
        rec['j_alone'] = dict(calls=[list(c) for c in jc], pred=jp.strip())
    nxt = []
    for rec in jobs:
        if rec['k_alone']['pred'] == rec['k_val'] and rec['j_alone']['pred'] == rec['j_val']:
            jprompt = JG.join_prompt(rec['prompt'], rec['op'], rec['k_alone']['pred'], rec['j_alone']['pred'])
            _, gold = steps_of(jprompt)
            if gold != '?':
                nxt.append((rec, jprompt, gold))
    jout = greedy(m, [p for _, p, _ in nxt]) if nxt else []
    for (rec, jprompt, gold), (calls, pred) in zip(nxt, jout):
        rec['join_own'] = dict(prompt=jprompt, gold=gold, pred=pred.strip(), calls=[list(c) for c in calls])
    return recs


# ---------- scoring helpers (pure, no model) ----------

def norm_answer(s):
    """Answer text normalised for the format check: strip, drop thousands commas and a leading '+', numeric equality."""
    s = str(s).strip().replace(',', '')
    try:
        d = Decimal(s)
        return str(d.quantize(Decimal(1))) if d == d.to_integral_value() else str(d.normalize())
    except InvalidOperation:
        return s.lower()


def prefix_ok(calls, steps, lo, hi):
    """The model's calls lo..hi-1 equal the tool's steps in order (add/mul/min/max either operand order)."""
    return len(calls) >= hi and len(steps) >= hi and all(JG.same_call(tuple(calls[i]), tuple(steps[i])) for i in range(lo, hi))


def order_free(calls, steps):
    """-> one flag per tool step: some unused model call equals it (a multiset match, any order)."""
    used, flags = [False] * len(calls), []
    for t in steps:
        ok = False
        for i, c in enumerate(calls):
            if not used[i] and JG.same_call(tuple(c), tuple(t)):
                used[i], ok = True, True
                break
        flags.append(ok)
    return flags


def used_values(calls):
    """Every number the model's calls touch: operands and results (as numbers). A piece done by a shortcut (e.g. the larger of two cells written
    straight into the next call, no MAX call) still shows its value here."""
    out = set()
    for c in calls:
        out.update(str(JG.num(x)) for x in c[1:4])
    return out


def ladder(rec):
    """Nested-by-construction rungs for one row with a split: in order R1..R4 from the calls, R5 = the final answer; order-free O2..O4."""
    c, st, nK, nJ = rec['calls'], rec['steps'], len(rec['k_steps']), len(rec['j_steps'])
    fl = order_free(c, st)
    exact = rec['pred'] == rec['gold'].strip()
    return dict(R1=prefix_ok(c, st, 0, 1), R2=prefix_ok(c, st, 0, nK), R3=prefix_ok(c, st, 0, nK + nJ),
                R4=len(c) == len(st) and prefix_ok(c, st, 0, len(st)), R5=exact,
                W_norm=norm_answer(rec['pred']) == norm_answer(rec['gold']),
                O2=all(fl[:nK]), O3=all(fl[:nK + nJ]), O4=all(fl) and len(c) == len(st))


REF = re.compile(r'([A-Z])(\d+)(?::([A-Z])(\d+))?')


def grid_and_refs(prompt):
    """-> ({(col, row): value}, {cells the formula names}, {literal numbers in the formula}). Grid text: `A: 1 2 | B: 3 4 ; =FORMULA`."""
    head, formula = prompt.split(';', 1)
    grid = {}
    for seg in head.split('|'):
        lab, nums = seg.split(':', 1)
        for i, n in enumerate(nums.split()):
            grid[(lab.strip(), i + 1)] = int(n)
    refs, lits = set(), set()
    for m in REF.finditer(formula):
        c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        c2, r2 = (c2 or c1), int(r2 or r1)
        for c in range(ord(min(c1, c2)), ord(max(c1, c2)) + 1):
            for r in range(min(r1, r2), max(r1, r2) + 1):
                refs.add((chr(c), r))
    lits = {int(n) for n in NUMS.findall(REF.sub(' ', formula))}
    return grid, refs, lits


def number_spot(prompt, x):
    """Where a wrong operand number x comes from: a number in a cell the formula names (the wrong one of them), a number in a grid cell
    the formula does NOT name, a literal of the formula, or None (not a prompt number). Duplicated grid values count as named if any copy is."""
    try:
        grid, refs, lits = grid_and_refs(prompt)
        v = int(x)
    except Exception:
        return None
    pos = {k for k, val in grid.items() if val == v}
    if pos & refs:
        return "operand: a cell the formula names (the wrong one)"
    if pos:
        return "operand: a grid cell the formula does not name"
    if v in lits:
        return 'operand: a literal of the formula'
    return None


def classify(prompt, calls, steps, nK=None, nJ=None):
    """First differing call of a failed row -> (round, where, category, n_wrong_operands). Round None when no call differs."""
    where = lambda r: 'r0' if r == 0 else 'K' if nK is not None and r < nK else 'J' if nK is not None and r < nK + nJ else 'join' if nK is not None else 'later'
    for r, (m, t) in enumerate(zip(calls, steps)):
        if JG.same_call(tuple(m), tuple(t)):
            continue
        if any(JG.same_call(tuple(m), tuple(s)) for s in steps[r + 1:]):   # a later step of the tool's working, done now
            made_later = any(JG.same_call(tuple(c), tuple(steps[r])) for c in calls[r + 1:])
            return r, where(r), ('later step done first (order swapped)' if made_later else 'later step done first, this step skipped'), 0
        if m[0] != t[0]:
            return r, where(r), 'wrong op', 0
        want = [str(JG.num(x)) for x in t[1:3]]
        got = [str(JG.num(x)) for x in m[1:3]]
        if t[0] in JG.SYM:   # either order: what is left after crossing off the operands both calls share
            left_w, bad = list(want), []
            for x in got:
                left_w.remove(x) if x in left_w else bad.append(x)
        else:
            bad = [x for x, w in zip(got, want) if x != w]
        n_wrong = len(bad)
        x = bad[0]
        earlier = {str(JG.num(s[3])) for s in steps[:r]} | {str(JG.num(c[3])) for c in calls[:r]}
        spot = number_spot(prompt, x)
        cat = spot if spot else ('wrong earlier result' if x in earlier else 'number not in the question')
        return r, where(r), cat, n_wrong
    if not calls:
        return None, None, 'no calls', 0
    if len(calls) < len(steps):
        return len(calls), 'stop', 'stopped early', 0
    if len(calls) > len(steps):
        return len(steps), 'stop', 'extra calls', 0
    return None, None, 'answer only (all calls right)', 0



def teacher_forced(m, rows, bs=64):
    """The call the model writes at each round when the tool's own working is on the tape (the training targets, built by the mode's
    make_row, so exactly the tool's steps): the model has no history of its own mistakes. -> per row (gold [(op, a, b)], model [(op, a, b)]
    for rounds 0..N_RES-1), or None for a row the mode would not train on (negative number, a 7+ call cap)."""
    import torch
    from custom_io.data import Dataset, collate, to_device
    from custom_io.models.tool import NAMES
    from domain import mode
    cons = json.load(open(mode.CONST_PATH))
    gold_rows = [mode.make_row(m, 'domain_sheet', r['prompt'], r['tool_value'], [tuple(x) for x in r['steps']], cons, 'tool')[0] for r in rows]
    todo = [i for i, g in enumerate(gold_rows) if g is not None]
    out = [None] * len(rows)
    for s in range(0, len(todo), bs):
        idx = todo[s:s + bs]
        ds = Dataset([gold_rows[i] for i in idx], m.vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(idx))]), 'cpu')
        with torch.no_grad():
            g = m.gold(batch['rows'], 'cpu')
            o = m.run(batch, gold=g)
        wr = [m.written(st) for st in o['steps']]
        ops = [st[0].argmax(-1).tolist() for st in o['steps']]
        for j, i in enumerate(idx):
            gops, gopd = g['rowg'][j][0], g['rowg'][j][1]
            gold = [(NAMES[o_], a, b) for o_, (a, b) in zip(gops, gopd)]
            out[i] = (gold, [(NAMES[ops[k][j]] if ops[k][j] else 'noop', wr[k][j][0], wr[k][j][1]) for k in range(len(wr))])
    return out


def add_teacher_forced(path, ckpt, threads=2):
    """Adds rec['tf_gold'] / rec['tf_model'] to every split row of a collected raw file (same checkpoint)."""
    import torch
    from custom_io.models import load_model
    torch.set_num_threads(threads)
    j = json.load(open(path))
    m = load_model(ckpt).eval()
    rows = [r for r in j['rows'] if r['split'] and not r['refused']]
    for r, res in zip(rows, teacher_forced(m, rows)):
        if res:
            r['tf_gold'], r['tf_model'] = [list(c) for c in res[0]], [list(c) for c in res[1]]
    json.dump(j, open(path, 'w'))
    return len(rows)


def tf_summary(recs):
    """Teacher-forced call accuracy by role (K rounds, J rounds, join call), per round count: rows where the gold program has the same
    number of calls as the tool's working (others are counted and left out)."""
    ok = [r for r in recs if r.get('tf_gold') is not None]
    use = [r for r in ok if len(r['tf_gold']) == len(r['steps'])]
    ev = lambda r, lo, hi: all(JG.same_call(tuple(r['tf_model'][i]) + ('',), tuple(r['tf_gold'][i]) + ('',)) for i in range(lo, hi))
    s = dict(rows=len(ok), same_len=len(use))
    s['K'] = sum(1 for r in use if ev(r, 0, len(r['k_steps'])))
    s['J'] = sum(1 for r in use if ev(r, len(r['k_steps']), len(r['k_steps']) + len(r['j_steps'])))
    s['join'] = sum(1 for r in use if ev(r, len(r['steps']) - 1, len(r['steps'])))
    s['all'] = sum(1 for r in use if ev(r, 0, len(r['steps'])))
    s['r0'] = sum(1 for r in use if ev(r, 0, 1))
    s['by_round'] = {k: [sum(1 for r in use if len(r['steps']) > k and ev(r, k, k + 1)), sum(1 for r in use if len(r['steps']) > k)] for k in range(7)}
    return s


def pct(h, n):
    return None if not n else round(100.0 * h / n, 1)


def boot(vals, reps=1000, seed=0):
    """95% bootstrap interval of the mean of 0/1 values, in percent (rows resampled; one training run, so NOT a seed spread)."""
    import numpy as np
    v = np.asarray(vals, float)
    if not len(v):
        return None
    rng = np.random.default_rng(seed)
    m = v[rng.integers(0, len(v), (reps, len(v)))].mean(1) * 100
    return round(float(np.percentile(m, 2.5)), 1), round(float(np.percentile(m, 97.5)), 1)


def cell_summary(recs):
    """One checkpoint x cell: W, W_norm, ladder, alone, in-context, combine, taxonomy counts (rows with a split and both pieces answerable)."""
    ok = [r for r in recs if r['split'] and not r['refused']]
    n = len(ok)
    L_ = [ladder(r) for r in ok]
    g = lambda k: sum(1 for x in L_ if x[k])
    s = dict(rows=len(recs), usable=n, W=g('R5'), W_norm=g('W_norm'), W_ci=boot([x['R5'] for x in L_]))
    for k in ('R1', 'R2', 'R3', 'R4', 'O2', 'O3', 'O4'):
        s[k] = g(k)
    s['W_not_R4'] = sum(1 for x in L_ if x['R5'] and not x['R4'])
    s['W_and_R3'] = sum(1 for x in L_ if x['R5'] and x['R3'])
    jal = [prefix_ok(r['j_alone']['calls'], r['j_steps'], 0, len(r['j_steps'])) and len(r['j_alone']['calls']) == len(r['j_steps']) for r in ok]
    kal = [prefix_ok(r['k_alone']['calls'], r['k_steps'], 0, len(r['k_steps'])) and len(r['k_alone']['calls']) == len(r['k_steps']) for r in ok]
    s['K_alone_calls'], s['J_alone_calls'] = sum(kal), sum(jal)
    s['K_alone_val'] = sum(1 for r in ok if r['k_alone']['pred'] == r['k_val'])
    s['J_alone_val'] = sum(1 for r in ok if r['j_alone']['pred'] == r['j_val'])
    s['P'] = sum(1 for r in ok if r['k_alone']['pred'] == r['k_val'] and r['j_alone']['pred'] == r['j_val'])
    uv = [used_values(r['calls']) for r in ok]
    s['VK'] = sum(1 for r, u in zip(ok, uv) if str(JG.num(r['k_val'])) in u)
    s['VJ'] = sum(1 for r, u in zip(ok, uv) if str(JG.num(r['j_val'])) in u)
    s['VK_given_alone'] = sum(1 for r, u in zip(ok, uv) if r['k_alone']['pred'] == r['k_val'] and str(JG.num(r['k_val'])) in u)
    s['VJ_given_alone'] = sum(1 for r, u in zip(ok, uv) if r['j_alone']['pred'] == r['j_val'] and str(JG.num(r['j_val'])) in u)
    s['VKJ'] = sum(1 for r, u in zip(ok, uv) if str(JG.num(r['k_val'])) in u and str(JG.num(r['j_val'])) in u)
    s['VKJ_W'] = sum(1 for r, u in zip(ok, uv) if str(JG.num(r['k_val'])) in u and str(JG.num(r['j_val'])) in u and r['pred'] == r['gold'].strip())
    s['K_ctx_given_alone'] = sum(1 for x, a in zip(L_, kal) if a and x['R2'])
    s['J_ctx_given_alone'] = sum(1 for r, a in zip(ok, jal) if a and prefix_ok(r['calls'], r['steps'], len(r['k_steps']), len(r['k_steps']) + len(r['j_steps'])))
    s['J_ctx_given_K'] = sum(1 for x in L_ if x['R3'])   # of R2 rows
    s['T'] = sum(1 for r in ok if r.get('join_own') and r['join_own']['pred'] == r['join_own']['gold'])
    s['W_given_P'] = sum(1 for r in ok if r['k_alone']['pred'] == r['k_val'] and r['j_alone']['pred'] == r['j_val'] and r['pred'] == r['gold'].strip())
    fails = [(r, classify(r['prompt'], r['calls'], r['steps'], len(r['k_steps']), len(r['j_steps']))) for r in ok if r['pred'] != r['gold'].strip()]
    s['fails'] = len(fails)
    s['first_where'] = dict(Counter(c[1] for _, c in fails))
    s['first_cat'] = dict(Counter(c[2] for _, c in fails))
    s['r0_cat'] = dict(Counter(c[2] for _, c in fails if c[0] == 0))
    s['by_pair'] = {p: dict(rows=sum(1 for r in ok if r['pair'] == p), W=sum(1 for r, x in zip(ok, L_) if r['pair'] == p and x['R5']),
                            R2=sum(1 for r, x in zip(ok, L_) if r['pair'] == p and x['R2']),
                            K_alone=sum(1 for r, a in zip(ok, kal) if r['pair'] == p and a)) for p in JG.PAIRS}
    return s


def load_raw(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, 'p2-*.json'))):
        j = json.load(open(p))
        out[j['label']] = j
    return out


def md_table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])


def items_records(path):
    """dump_items JSONL -> records for the taxonomy (every cell the run scored)."""
    out = []
    for l in open(path):
        r = json.loads(l)
        nK = nJ = None
        try:
            f = r['prompt'].split(';', 1)[1].strip()[1:]
            sp = JG.split_formula(f)
            if sp:
                nK = len(steps_of(JG.piece_prompt(r['prompt'], sp[1]))[0])
                nJ = len(steps_of(JG.piece_prompt(r['prompt'], sp[2]))[0])
        except Exception:
            pass
        out.append(dict(cell=r['cell'], prompt=r['prompt'], hit=r['hit'], calls=r['model_calls'], steps=r['tool_steps'], nK=nK, nJ=nJ))
    return out


def report(raws, items=None):
    sm = {lab: {c: cell_summary([r for r in j['rows'] if r['cell'] == c]) for c in CELLS} for lab, j in raws.items()}
    L_ = []
    p = lambda h, n: f'{pct(h, n)}'
    L_.append('## 1. Answer-format check and the scores (usable rows = joined rows the tool can evaluate)\n')
    L_.append(md_table(['run', 'cell', 'rows', 'W (exact)', '95% rows', 'W_norm', 'W_norm - W', 'W right, calls differ', 'W as ladder R4'],
                       [[lab, c, s['usable'], p(s['W'], s['usable']), s['W_ci'], p(s['W_norm'], s['usable']),
                         round(pct(s['W_norm'], s['usable']) - pct(s['W'], s['usable']), 1), s['W_not_R4'], p(s['R4'], s['usable'])]
                        for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n## 2. Partial-credit ladder, % of rows (in order; R5 = final answer; O = order-free)\n')
    L_.append(md_table(['run', 'cell', 'R1 first call', 'R2 K done', 'R3 K+J done', 'R4 all calls', 'R5 answer', 'O2 K any order', 'O3 K+J any order', 'O4 all any order'],
                       [[lab, c] + [p(s[k], s['usable']) for k in ('R1', 'R2', 'R3', 'R4', 'W', 'O2', 'O3', 'O4')] for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n## 3. Piece accuracy alone vs inside the join (% of rows; calls compared in order)\n')
    L_.append(md_table(['run', 'cell', 'K alone (calls)', 'K in join', 'K in join given K alone ok', 'J alone (calls)', 'J in join given J alone ok', 'J in join given K in join (n)', 'both alone (value) P', 'T own join', 'T/P', 'W given P'],
                       [[lab, c, p(s['K_alone_calls'], s['usable']), p(s['R2'], s['usable']), p(s['K_ctx_given_alone'], s['K_alone_calls']),
                         p(s['J_alone_calls'], s['usable']), p(s['J_ctx_given_alone'], s['J_alone_calls']),
                         f"{p(s['R3'], s['R2'])} ({s['R2']})", p(s['P'], s['usable']), p(s['T'], s['usable']), p(s['T'], s['P']), p(s['W_given_P'], s['P'])]
                        for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n## 3b. The same, by VALUE (route-free): does the piece\'s value show up among the numbers the model\'s calls touch? (% of rows)\n')
    L_.append(md_table(['run', 'cell', 'K alone (value)', 'K value in the join', 'in the join given alone ok', 'J alone (value)', 'J value in the join', 'in the join given alone ok', 'both values in the join', 'of those, answer right'],
                       [[lab, c, p(s['K_alone_val'], s['usable']), p(s['VK'], s['usable']), p(s['VK_given_alone'], s['K_alone_val']), p(s['J_alone_val'], s['usable']),
                         p(s['VJ'], s['usable']), p(s['VJ_given_alone'], s['J_alone_val']), p(s['VKJ'], s['usable']), p(s['VKJ_W'], s['VKJ'])]
                        for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n## 4. After K and J are right in the join: is the join call right? (rows, % )\n')
    L_.append(md_table(['run', 'cell', 'rows with K+J right in the join', 'of those, all calls right', 'of those, answer right'],
                       [[lab, c, s['R3'], p(s['R4'], s['R3']), p(s['W_and_R3'], s['R3'])] for lab, v in sm.items() for c, s in v.items()]))
    if any(r.get('tf_gold') for j in raws.values() for r in j['rows']):
        tfs = {lab: {c: tf_summary([r for r in j['rows'] if r['cell'] == c]) for c in CELLS} for lab, j in raws.items()}
        L_.append('\n## 4b. Teacher-forced: the tool\'s own working is on the tape, so no history of the model\'s own mistakes (% of rows)\n')
        L_.append(md_table(['run', 'cell', 'rows', 'first call', 'all K calls', 'all J calls', 'the join call (combine rate)', 'every call'],
                           [[lab, c, s['same_len'], p(s['r0'], s['same_len']), p(s['K'], s['same_len']), p(s['J'], s['same_len']),
                             p(s['join'], s['same_len']), p(s['all'], s['same_len'])] for lab, v in tfs.items() for c, s in v.items()]))
        L_.append('\nTeacher-forced call accuracy by round number (the call at round k, tool history on the tape; rows with more than k calls; % and n):\n')
        L_.append(md_table(['run', 'cell'] + [f'round {k}' for k in range(7)],
                           [[lab, c] + [f"{p(s['by_round'][k][0], s['by_round'][k][1])} ({s['by_round'][k][1]})" for k in range(7)] for lab, v in tfs.items() for c, s in v.items()]))
    L_.append('\n## 5. Taxonomy of failed whole rows: where the first wrong call sits, % of failed rows\n')
    wh = ('r0', 'K', 'J', 'join', 'stop')
    L_.append(md_table(['run', 'cell', 'failed rows'] + ['round 0', 'inside K (round > 0)', 'inside J', 'join call', 'stopped/extra', 'no differing call'],
                       [[lab, c, s['fails']] + [p(s['first_where'].get('r0', 0), s['fails']), p(s['first_where'].get('K', 0), s['fails']),
                                                p(s['first_where'].get('J', 0), s['fails']), p(s['first_where'].get('join', 0), s['fails']),
                                                p(s['first_where'].get('stop', 0), s['fails']), p(s['first_where'].get(None, 0), s['fails'])]
                        for lab, v in sm.items() for c, s in v.items()]))
    cats = sorted({k for v in sm.values() for s in v.values() for k in s['first_cat']})
    L_.append('\n### First-wrong-call type, % of failed rows\n')
    L_.append(md_table(['run', 'cell'] + cats, [[lab, c] + [p(s['first_cat'].get(k, 0), s['fails']) for k in cats] for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n### Round-0 errors only (the routing claim): type, % of round-0 errors\n')
    c0 = sorted({k for v in sm.values() for s in v.values() for k in s['r0_cat']})
    L_.append(md_table(['run', 'cell', 'round-0 errors'] + c0,
                       [[lab, c, sum(s['r0_cat'].values())] + [p(s['r0_cat'].get(k, 0), sum(s['r0_cat'].values())) for k in c0] for lab, v in sm.items() for c, s in v.items()]))
    L_.append('\n### By pair type (W / K in join / K alone, % of rows)\n')
    L_.append(md_table(['run', 'cell', 'pair', 'rows', 'W', 'K in join', 'K alone'],
                       [[lab, c, pt, v2['rows'], p(v2['W'], v2['rows']), p(v2['R2'], v2['rows']), p(v2['K_alone'], v2['rows'])]
                        for lab, v in sm.items() for c, s in v.items() for pt, v2 in s['by_pair'].items()]))
    if items:
        L_.append('\n## 6. Merged taxonomy over the per-item files (every cell; first wrong call, % of failed rows)\n')
        rows6, cats6 = [], set()
        agg = {}
        for lab, recs in items.items():
            for cell in sorted({r['cell'] for r in recs}):
                fs = [classify(r['prompt'], r['calls'], r['steps'], r['nK'], r['nJ']) for r in recs if r['cell'] == cell and not r['hit']]
                tot = sum(1 for r in recs if r['cell'] == cell)
                cat = Counter(c[2] for c in fs)
                r0 = Counter(c[2] for c in fs if c[0] == 0)
                agg[(lab, cell)] = (tot, len(fs), cat, r0, sum(1 for r in recs if r['cell'] == cell and r['hit'] and not (len(r['calls']) == len(r['steps']) and prefix_ok(r['calls'], r['steps'], 0, len(r['steps'])))))
                cats6 |= set(cat)
        cats6 = sorted(cats6)
        L_.append(md_table(['run', 'cell', 'rows', 'failed', 'hit by another route'] + cats6,
                           [[lab, cell, t, f, alt] + [p(cat.get(k, 0), f) for k in cats6] for (lab, cell), (t, f, cat, r0, alt) in agg.items()]))
        L_.append('\nRound-0 first errors only (% of that cell\'s round-0 errors):\n')
        c06 = sorted({k for a in agg.values() for k in a[3]})
        L_.append(md_table(['run', 'cell', 'round-0 errors'] + c06, [[lab, cell, sum(r0.values())] + [p(r0.get(k, 0), sum(r0.values())) for k in c06] for (lab, cell), (t, f, cat, r0, alt) in agg.items()]))
    return '\n'.join(L_), sm


def main(argv=None):
    a = argparse.ArgumentParser(description='P2 zero-GPU far diagnostics (scoring only).')
    sub = a.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--ckpt', required=True)
    c.add_argument('--probe', required=True)
    c.add_argument('--label', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--threads', type=int, default=2)
    c.add_argument('--limit', type=int, default=None, help='rows per cell (smoke test)')
    t = sub.add_parser('tf', help='add the teacher-forced calls to a collected raw file')
    t.add_argument('--raw', required=True)
    t.add_argument('--ckpt', required=True)
    t.add_argument('--threads', type=int, default=2)
    r = sub.add_parser('report')
    r.add_argument('--raw', required=True)
    r.add_argument('--items', nargs='*', default=[], help='LABEL=dump_items.jsonl')
    r.add_argument('--out', default=None)
    a = a.parse_args(argv)
    if a.cmd == 'collect':
        recs = collect(a.ckpt, a.probe, CELLS, a.threads, a.limit)
        os.makedirs(a.out, exist_ok=True)
        path = os.path.join(a.out, f'p2-{a.label}.json')
        json.dump(dict(label=a.label, ckpt=a.ckpt, probe=a.probe, cells=list(CELLS), rows=recs), open(path, 'w'))
        print(a.label, {c: f"W {sum(1 for r in recs if r['cell'] == c and r['pred'] == r['gold'].strip())}/{sum(1 for r in recs if r['cell'] == c)}" for c in CELLS})
        print('wrote', path)
    elif a.cmd == 'tf':
        print('teacher-forced rows:', add_teacher_forced(a.raw, a.ckpt, a.threads), a.raw)
    else:
        items = {kv.split('=', 1)[0]: items_records(kv.split('=', 1)[1]) for kv in a.items}
        text, _ = report(load_raw(a.raw), items)
        if a.out:
            open(a.out, 'w').write(text + '\n')
        print(text)


if __name__ == '__main__':
    main()
