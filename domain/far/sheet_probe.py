"""Far-transfer probes for the spreadsheet mode: which far change breaks the model (diagnosis; scoring only).

Each probe cell moves ONE thing away from the near help shapes, except F4 (two kinds, near grid) and F5 (the far
generator minus MOD/COUNTIF/IF partners and minus the MOD join), which are the two-kind controls. Rows are built from
domain/panel.py's own pieces (piece, combine, render, sheet_candidate) and accepted only when they pass the same checks
as panel.fill_panel. The probe seed is 93001; no row is in the sealed panel (sheet.jsonl, sheet.v2.jsonl). No training.

  python3 -m domain.far.sheet_probe build [--raw DIR]   writes DIAG/sheet-probe.jsonl (refuses to overwrite), prints counts
  python3 -m domain.far.sheet_probe score [--raw DIR]   scores 5 checkpoints on that file; writes sheet-factors.json and .md
"""
import argparse
import json
import os
import random
import re
from collections import Counter

from domain import panel as P
from domain.tools import ASCII, MAX_ANS, MAX_PROMPT, N_NUM, N_RES
from domain.tools import sheet as sheet_tool

SEED = 93001
DIAG = '/mnt/project-files/far-transfer/diag'
PROBE = os.path.join(DIAG, 'sheet-probe.jsonl')
FACTORS_JSON = os.path.join(DIAG, 'sheet-factors.json')
FACTORS_MD = os.path.join(DIAG, 'sheet-factors.md')
PANEL_FILES = ('/mnt/project-files/domain-mode/panel/sheet.jsonl', '/mnt/project-files/domain-mode/panel/sheet.v2.jsonl')
MAX_TRIES = 200000  # a cell not full after this many draws is reported as not fillable

CHECKPOINTS = [
    ('parent s200', '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'),
    ('parent s201', '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s201/T1SDR_s201/checkpoint.pt'),
    ('v7 s200', '/mnt/project-files/domain-mode/runs/sheet-s200-v7/night_7/checkpoint.pt'),
    ('v7 s201', '/mnt/project-files/domain-mode/runs/sheet-s201-v7/night_8/checkpoint.pt'),
    ('v2 s200', '/mnt/project-files/domain-mode/runs/sheet-s200-v2/night_8/checkpoint.pt'),
]

# The seven scored kinds (MOD, COUNTIF and IF are not scored: no trainable row form in this mode).
SCORED = ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'ABS']
AGG_KINDS = ['SUM', 'MAX', 'MIN', 'PRODUCT']
CELL_KINDS = ['cell arithmetic', 'division', 'ABS']
FAR_CELLS = ['F0-near', 'F1-grid', 'F2-long', 'F2b-rows', 'F3-col', 'F4-two', 'F5-far']
LEN_CELLS = ['LEN2', 'LEN3', 'LEN4', 'LEN5', 'LEN6']
CELLS = FAR_CELLS + LEN_CELLS
ROWS_PER_CELL, ROWS_PER_LEN = 60, 40

CELL_DESC = {
    'F0-near': 'near, unchanged (panel.sheet_candidate)',
    'F1-grid': 'grid 5-6 rows; every reference in rows 1-4',
    'F2-long': 'SUM/MAX/MIN/PRODUCT only: grid 5-6, range length 5-6, either column',
    'F2b-rows': 'cell kinds only: grid 5-6, at least one reference in row 5 or 6',
    'F3-col': 'near rows; every reference in the other column (HELP_COLS swapped)',
    'F4-two': 'near grid; two kinds joined with + or *; partner from the other 6 scored kinds',
    'F5-far': 'far generator minus MOD/COUNTIF/IF partners and minus MOD join',
    'LEN2': 'AGG only: grid 6, range length 2',
    'LEN3': 'AGG only: grid 6, range length 3',
    'LEN4': 'AGG only: grid 6, range length 4',
    'LEN5': 'AGG only: grid 6, range length 5',
    'LEN6': 'AGG only: grid 6, range length 6',
}


def cells_for(kind):
    """The probe cells that a kind is scored in."""
    out = []
    for cell in CELLS:
        if cell == 'F2-long' or cell in LEN_CELLS:
            ok = kind in AGG_KINDS
        elif cell == 'F2b-rows':
            ok = kind in CELL_KINDS
        else:
            ok = True
        if ok:
            out.append(cell)
    return out


def refs(formula):
    """The cell references of a formula, as (column, row) pairs."""
    return [(c, int(r)) for c, r in re.findall(r'([AB])([0-9]+)', formula)]


def redraw(kind, rng, n, cols, L, ok):
    """panel.piece, drawn again until every reference of the formula passes ok(refs)."""
    while True:
        formula, fn = P.piece(kind, rng, n, cols, L)
        if ok(refs(formula)):
            return formula, fn


def rows_up_to(top):
    return lambda rs: all(r <= top for _, r in rs)


def some_row_from(low):
    return lambda rs: any(r >= low for _, r in rs)


def far_cols(kind):
    """The other column for each reference, in help order (as panel.sheet_candidate's far split does)."""
    return ''.join(P.other(c) for c in P.HELP_COLS[kind])


def candidate(kind, cell, rng):
    """One candidate for (kind, cell): (prompt, value function of the grid, grid, formula)."""
    if cell == 'F0-near':
        return P.sheet_candidate(kind, 'near', rng)
    agg = kind in P.AGG
    if cell == 'F1-grid':
        n = rng.choice([5, 6])
        formula, fn = redraw(kind, rng, n, None, rng.choice([2, 3, 4]) if agg else None, rows_up_to(4))
    elif cell == 'F2-long':
        n = rng.choice([5, 6])
        formula, fn = P.piece(kind, rng, n, None, rng.choice([x for x in (5, 6) if x <= n]))
    elif cell == 'F2b-rows':
        n = rng.choice([5, 6])
        formula, fn = redraw(kind, rng, n, None, None, some_row_from(5))
    elif cell == 'F3-col':
        L = rng.choice([2, 3, 4]) if agg else None
        n = rng.randint(L, 4) if agg else rng.choice([2, 3, 4])
        formula, fn = P.piece(kind, rng, n, far_cols(kind), L)
    elif cell == 'F4-two':
        n = rng.choice([2, 3, 4])
        K = P.piece(kind, rng, n, None, rng.randint(2, n) if agg else None)
        partner = rng.choice([k for k in SCORED if k != kind])
        J = P.piece(partner, rng, n, None, 2 if partner in P.AGG else None)
        formula, fn = P.combine(rng.choice(['+', '*']), K, J)
    elif cell == 'F5-far':
        n = rng.choice([5, 6])
        K = P.piece(kind, rng, n, far_cols(kind), rng.randint(5, n) if agg else None)
        partner = rng.choice([k for k in SCORED if k != kind])
        J = P.piece(partner, rng, n, None, rng.choice([2, 3]) if partner in P.AGG else None)
        formula, fn = P.combine(rng.choice(['+', '*']), K, J)
    else:  # LENn: one range of length n, grid 6, either column, random start row
        n = 6
        formula, fn = P.piece(kind, rng, n, None, int(cell[3:]))
    g = {c: [rng.randint(1, 99) for _ in range(n)] for c in 'AB'}
    return P.render(g, formula), fn, g, formula


def check(prompt, expect, help_prompts, panel_prompts, seen):
    """fill_panel's checks, in its order, plus the vocabulary and the sealed-panel and probe duplicate rules.
    Returns (reason or None, tool result)."""
    res = sheet_tool.evaluate(prompt)
    steps = len(res['steps'])
    if res['value'] == '?':
        return 'tool ?', res
    if expect is None or str(expect) != res['value']:
        return 'python disagrees', res
    if steps > N_RES:
        return 'steps over 7', res
    if len(prompt) > MAX_PROMPT:
        return 'prompt over cap', res
    if P.numbers(prompt) > N_NUM:
        return 'numbers over 16', res
    if len(res['value']) > MAX_ANS:
        return 'answer over 8', res
    if not set(prompt + res['value']) <= ASCII or steps < 1:
        return 'vocab or no steps', res
    if prompt in help_prompts:
        return 'help example', res
    if prompt in panel_prompts:
        return 'in sealed panel', res
    if prompt in seen:
        return 'duplicate', res
    return None, res


def read_panel_prompts():
    out = set()
    for path in PANEL_FILES:
        with open(path) as f:
            for line in f:
                if line.strip():
                    out.add(json.loads(line)['prompt'])
    return out


def build_rows(rng):
    """All probe rows, and per (kind, cell) the fill statistics."""
    help_list = sheet_tool.help()
    help_prompts = {h['prompt'] for h in help_list}
    help_skel = {h['kind']: P.skeleton(h['prompt'].split('; =')[1]) for h in help_list}
    panel_prompts = read_panel_prompts()
    rows, stats, seen = [], {}, set()
    for ki, kind in enumerate(SCORED, 1):
        for cell in cells_for(kind):
            target = ROWS_PER_LEN if cell in LEN_CELLS else ROWS_PER_CELL
            st = Counter()
            while st['accepted'] < target:
                st['tries'] += 1
                if st['tries'] > MAX_TRIES:
                    raise RuntimeError(f'{kind} {cell}: not full after {MAX_TRIES} draws')
                prompt, fn, g, formula = candidate(kind, cell, rng)
                expect = fn(g)
                reason, res = check(prompt, expect, help_prompts, panel_prompts, seen)
                if reason is None and cell == 'F0-near' and P.skeleton(formula) != help_skel[kind]:
                    reason = 'near shape'
                if reason:
                    st[reason] += 1
                    continue
                seen.add(prompt)
                rows.append({'id': f'probe-{cell}-{ki:02d}-{st["accepted"]:03d}', 'kind': kind, 'split': cell,
                             'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])})
                st['accepted'] += 1
            stats[(kind, cell)] = st
    return rows, stats


def write_rows(rows):
    os.makedirs(DIAG, exist_ok=True)
    if os.path.exists(PROBE):
        raise SystemExit(f'refusing to overwrite {PROBE}')
    with open(PROBE, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def print_counts(rows, stats):
    print(f'probe rows: {len(rows)} (unique prompts {len({r["prompt"] for r in rows})})')
    for cell in CELLS:
        cr = [r for r in rows if r['split'] == cell]
        if not cr:
            continue
        per = Counter(r['kind'] for r in cr)
        rej = Counter()
        tries = 0
        for (kind, c), st in stats.items():
            if c == cell:
                tries += st['tries']
                rej.update({k: v for k, v in st.items() if k not in ('tries', 'accepted')})
        steps = sum(r['n_steps'] for r in cr) / len(cr)
        print(f'  {cell:9s} rows {len(cr):4d} kinds {len(per)} mean_steps {steps:.2f} tries {tries} '
              f'rejected {dict(rej)}')
        print('            ' + ', '.join(f'{k} {v}' for k, v in per.items()))


def build(raw_dir=None):
    rows, stats = build_rows(random.Random(SEED))
    write_rows(rows)
    print_counts(rows, stats)
    print('wrote', PROBE)
    return rows


def load_rows():
    with open(PROBE) as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(h, n):
    return round(100.0 * h / n, 2) if n else None


def summarize(rows, run):
    """Pooled per cell (over the kinds in it), per kind x cell, and the overall, from one score() run."""
    hit = {o['id']: o['hit'] for o in run['rows']}
    assert len(hit) == len(rows), 'score rows do not match the probe rows'
    pooled, per = {}, {}
    for r in rows:
        h = hit[r['id']]
        p = pooled.setdefault(r['split'], [0, 0])
        p[0] += 1
        p[1] += h
        q = per.setdefault(r['kind'], {}).setdefault(r['split'], [0, 0])
        q[0] += 1
        q[1] += h
    fmt = lambda nh: {'n': nh[0], 'hits': nh[1], 'pct': pct(nh[1], nh[0])}
    overall = pct(sum(hit.values()), len(rows))
    assert overall == run['overall'], (overall, run['overall'])
    return {'overall': overall, 'pooled': {c: fmt(v) for c, v in pooled.items()},
            'by_kind': {k: {c: fmt(v) for c, v in d.items()} for k, d in per.items()}}


def score_all(rows, raw_dir=None):
    import torch
    from domain.score import score
    torch.set_num_threads(2)
    out = {}
    for label, ck in CHECKPOINTS:
        run = score(ck, rows, label)
        s = summarize(rows, run)
        s['ckpt'] = ck
        out[label] = s
        print(label, 'overall', s['overall'], {c: v['pct'] for c, v in s['pooled'].items()}, flush=True)
        if raw_dir:
            os.makedirs(raw_dir, exist_ok=True)
            with open(os.path.join(raw_dir, 'sheet-probe-' + label.replace(' ', '-') + '.json'), 'w') as f:
                json.dump(run['rows'], f)
    return out


def cell_info(rows):
    """Per cell: the kinds, rows, mean steps, and the median answer (the value-size confound of the far PRODUCT rows)."""
    info = {}
    for cell in CELLS:
        cr = [r for r in rows if r['split'] == cell]
        if cr:
            median_answer = {}
            for kind in sorted({r['kind'] for r in cr}, key=SCORED.index):
                vals = sorted(int(r['answer']) for r in cr if r['kind'] == kind)
                median_answer[kind] = vals[len(vals) // 2]
            info[cell] = {'desc': CELL_DESC[cell], 'kinds': sorted({r['kind'] for r in cr}, key=SCORED.index),
                          'rows': len(cr), 'mean_steps': round(sum(r['n_steps'] for r in cr) / len(cr), 3),
                          'median_answer': median_answer}
    return info


def fmt_cell(s, cell):
    v = s['pooled'].get(cell)
    return '-' if v is None else f"{v['pct']:.1f}"


def write_factors(rows, scores):
    info = cell_info(rows)
    out = {'probe': PROBE, 'seed': SEED, 'n_rows': len(rows), 'cells': info,
           'checkpoints': scores,
           'note': 'pct = 100*hits/n; pooled = over the kinds present in the cell; hit = greedy answer equals the tool'}
    with open(FACTORS_JSON, 'w') as f:
        json.dump(out, f, indent=1)
    lines = ['# Sheet far-factor probes (seed 93001)', '',
             f'{len(rows)} rows; greedy answers with the calculator on; hit = answer equals the tool value. '
             'Shown (measured), not trained.', '',
             '## Pooled accuracy per cell (%, over the kinds in the cell)', '',
             '| cell | what changes | kinds | rows | mean steps | ' + ' | '.join(c for c, _ in CHECKPOINTS) + ' |',
             '|---|---|---|---|---|' + '---|' * len(CHECKPOINTS)]
    for cell in CELLS:
        if cell not in info:
            continue
        i = info[cell]
        lines.append(f"| {cell} | {i['desc']} | {len(i['kinds'])} | {i['rows']} | {i['mean_steps']:.2f} | "
                     + ' | '.join(fmt_cell(scores[c], cell) for c, _ in CHECKPOINTS) + ' |')
    prod = ', '.join(f"{c} {info[c]['median_answer']['PRODUCT']}" for c in CELLS
                     if c in info and 'PRODUCT' in info[c]['median_answer'])
    lines += ['', f'Median PRODUCT answer per cell (value-size check; the 1e9 calculator limit and 8-char answers select small '
                  f'operands): {prod}.']
    far_cols = [c for c in FAR_CELLS if c in info]
    for label in ('v7 s200', 'v7 s201'):
        lines += ['', f'## Per kind, {label} (%, 60 rows per cell; F0-F5)', '',
                  '| kind | ' + ' | '.join(far_cols) + ' |', '|---|' + '---|' * len(far_cols)]
        for kind in SCORED:
            cells = [c for c in far_cols if kind in info[c]['kinds']]
            vals = [scores[label]['by_kind'].get(kind, {}).get(c) for c in far_cols]
            lines.append(f'| {kind} | ' + ' | '.join('-' if (c not in cells or v is None) else f"{v['pct']:.1f}"
                                                     for c, v in zip(far_cols, vals)) + ' |')
    lines += ['', '## LEN ladder per kind (%, grid 6, one range of length L, 40 rows per cell)', '',
              '| checkpoint | kind | ' + ' | '.join(LEN_CELLS) + ' |', '|---|---|' + '---|' * len(LEN_CELLS)]
    for label in ('v7 s200', 'v7 s201', 'v2 s200'):
        for kind in AGG_KINDS:
            vals = [scores[label]['by_kind'].get(kind, {}).get(c) for c in LEN_CELLS]
            lines.append(f'| {label} | {kind} | ' + ' | '.join('-' if v is None else f"{v['pct']:.1f}" for v in vals) + ' |')
    lines += ['', '## Pooled LEN per checkpoint (%)', '',
              '| checkpoint | ' + ' | '.join(LEN_CELLS) + ' |', '|---|' + '---|' * len(LEN_CELLS),
              ]
    for label, _ in CHECKPOINTS:
        lines.append(f'| {label} | ' + ' | '.join(fmt_cell(scores[label], c) for c in LEN_CELLS) + ' |')
    with open(FACTORS_MD, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', FACTORS_JSON, FACTORS_MD)


def main(argv=None):
    a = argparse.ArgumentParser(description='Far-factor probes for the sheet mode (scoring only).')
    a.add_argument('stage', choices=['build', 'score'])
    a.add_argument('--raw', help='directory for the raw per-row predictions (scratch, not the diag folder)')
    a = a.parse_args(argv)
    if a.stage == 'build':
        build(a.raw)
    else:
        rows = load_rows()
        scores = score_all(rows, a.raw)
        write_factors(rows, scores)


if __name__ == '__main__':
    main()
