"""L1 diagnosis: can the 3M calculator model learn joined formulas at all? (spec: far-transfer/learn/MARKS-L1-2026-10-11.md)

  python3 -m domain.far.learn_probe build
  python3 -m domain.far.learn_probe build-mode     (L2: MARKS-L2; rows from the v9 mode's own practice maker)
  python3 -m domain.far.learn_probe build-l3       (L3: MARKS-L3; '+' joins of training kind pairs; eval cells S/HP/HO/HPO)
  python3 -m domain.far.learn_probe build-l4      (L4: MARKS-L4; build-mode with the swap tool's join step on, seed 93601)
  python3 -m domain.far.learn_probe build-l5      (L5: MARKS-L5; training joins over five layouts; eval cells S5/S/HP/HO/HPO)
  python3 -m domain.far.learn_probe train --arm LA|LB --updates 4000 --threads N --out DIR [--steps 0,500,1000,2000,4000] [--rows PATH] [--cells l1|all|l3|l4|l5]

build: 6,000 F4-two and 6,000 F0-near rows from the probe generator (domain/far/sheet_probe.py), seed 93301, scored kinds
       only, no prompt in the probe file or any sheet panel (read for exclusion only). Refuses to overwrite.
train: parent checkpoint + the mode's make_row / make_opt / AddOn / loss, on those rows only (no diary, no replay).
       LA = the mode's add-on (base frozen); LB = every weight at the mode's night lr. Same data order for both arms.
       Scores with domain.score.score on a checkpoint saved by the mode's save_ckpt at each step.
Diagnosis only: the mode is not run and no panel row is trained.
"""
import argparse
import hashlib
import itertools
import json
import os
import random
import re
import time
from collections import Counter

import numpy as np

from domain import panel as P
from domain.far import sheet_probe as SP
from domain.tools import sheet as sheet_tool

SEED = 93301
LEARN = '/mnt/project-files/far-transfer/learn'
TRAIN_ROWS = os.path.join(LEARN, 'train-rows.jsonl')
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
EXCLUDE_FILES = (SP.PROBE, '/mnt/project-files/domain-mode/panel/sheet.jsonl',
                 '/mnt/project-files/domain-mode/panel/sheet.v2.jsonl', '/mnt/project-files/domain-mode/panel/sheet.v3.jsonl')
TRAIN_CELLS = ('F4-two', 'F0-near')
# L2 (spec: far-transfer/learn/MARKS-L2-2026-10-11.md): rows made by the v9 mode's own practice maker
MODE_ROWS = os.path.join(LEARN, 'train-rows-mode.jsonl')
MODE_SEED = 93401
MODE_CELLS = ('mode-two', 'mode-one')   # joined (two kinds in one formula) / not joined
JOINED_CELLS = ('F4-two', 'mode-two')   # whatever the joined cell is called in a rows file
V3_PANEL = '/mnt/project-files/domain-mode/panel/sheet.v3.jsonl'
PROBE_CELLS = ('F0-near', 'F1-grid', 'F2-long', 'F2b-rows', 'F3-col', 'F4-two', 'F5-far',
               'LEN2', 'LEN3', 'LEN4', 'LEN5', 'LEN6')
# L3 (spec: far-transfer/learn/MARKS-L3-2026-10-11.md): joins of training kind pairs only, '+' only; eval on new pairs / '*'
L3_SEED = 93501
L3_EVAL_SEED = 93502
L3_TRAIN_ROWS = os.path.join(LEARN, 'train-rows-l3.jsonl')
L3_EVAL_ROWS = os.path.join(LEARN, 'eval-rows-l3.jsonl')
L3_SPLIT = os.path.join(LEARN, 'pair-split-l3.json')
L3_CELLS = ('S', 'HP', 'HO', 'HPO')   # (joiner, pair set): S '+' train pairs, HP '+' held-out, HO '*' train, HPO '*' held-out
L3_EVAL_N = 420
# L5 (spec: far-transfer/learn/MARKS-L5-2026-10-11.md): L3's pair split, training joins spread over five layouts
L5_SEED = 93701
L5_EVAL_SEED = 93702
L5_TRAIN_ROWS = os.path.join(LEARN, 'train-rows-l5.jsonl')
L5_EVAL_ROWS = os.path.join(LEARN, 'eval-rows-l5.jsonl')
L5_LAYOUTS = ('K+J', 'K-J', 'K*J', '(K)+(J)', '(K)-(J)')
L5_PER_LAYOUT = 1200
L5_S5_PER_LAYOUT = 84
L5_CELLS = ('S5', 'S', 'HP', 'HO', 'HPO')
L5_EVAL_N = 420
# L4 (spec: far-transfer/learn/MARKS-L4-2026-10-11.md): L2's rows with the swap tool's join step on (widen_join)
L4_SEED = 93601
L4_ROWS = os.path.join(LEARN, 'train-rows-l4.jsonl')   # the first build (record only)
L4R1_ROWS = os.path.join(LEARN, 'train-rows-l4r1.jsonl')   # R1: value slots and balanced join kinds
MODE_DRAW_CAP = 20_000_000
PER_CELL = 6000
FIT_N = 420
DEFAULT_STEPS = '0,500,1000,2000,4000'


def quotas(total, kinds):
    """The probe builder's balance: the same number of rows per kind (the remainder goes to the first kinds)."""
    base, extra = divmod(total, len(kinds))
    return {k: base + (1 if i < extra else 0) for i, k in enumerate(kinds)}


def read_prompts(paths):
    """Prompts only, for exclusion. Missing files are an error (an exclusion list must be complete)."""
    out = set()
    for path in paths:
        with open(path) as f:
            for line in f:
                if line.strip():
                    out.add(json.loads(line)['prompt'])
    return out


def build_train_rows(rng, exclude, per_cell=PER_CELL):
    """-> (rows, stats). Uses sheet_probe.candidate and sheet_probe.check (the probe's own draw and checks)."""
    help_list = sheet_tool.help()
    help_prompts = {h['prompt'] for h in help_list}
    help_skel = {h['kind']: P.skeleton(h['prompt'].split('; =')[1]) for h in help_list}
    rows, stats, seen = [], {}, set()
    for cell in TRAIN_CELLS:
        q = quotas(per_cell, SP.SCORED)
        for ki, kind in enumerate(SP.SCORED, 1):
            st = Counter()
            while st['accepted'] < q[kind]:
                st['tries'] += 1
                if st['tries'] > SP.MAX_TRIES:
                    raise RuntimeError(f'{kind} {cell}: not full after {SP.MAX_TRIES} draws')
                prompt, fn, g, formula = SP.candidate(kind, cell, rng)
                reason, res = SP.check(prompt, fn(g), help_prompts, exclude, seen)
                if reason is None and cell == 'F0-near' and P.skeleton(formula) != help_skel[kind]:
                    reason = 'near shape'
                if reason:
                    st[reason] += 1
                    continue
                seen.add(prompt)
                rows.append({'id': f'learn-{cell}-{ki:02d}-{st["accepted"]:04d}', 'kind': kind, 'split': cell,
                             'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])})
                st['accepted'] += 1
            stats[(kind, cell)] = st
    return rows, stats


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def build():
    if os.path.exists(TRAIN_ROWS):
        raise SystemExit(f'refusing to overwrite {TRAIN_ROWS}')
    exclude = read_prompts(EXCLUDE_FILES)
    rows, stats = build_train_rows(random.Random(SEED), exclude)
    assert not {r['prompt'] for r in rows} & exclude
    assert len({r['prompt'] for r in rows}) == len(rows)
    tmp = TRAIN_ROWS + '.tmp'
    with open(tmp, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    os.rename(tmp, TRAIN_ROWS)
    print(f'excluded prompts: {len(exclude)}; wrote {len(rows)} rows to {TRAIN_ROWS}')
    for cell in TRAIN_CELLS:
        per = Counter(r['kind'] for r in rows if r['split'] == cell)
        tries = sum(st['tries'] for (k, c), st in stats.items() if c == cell)
        print(f'  {cell}: {sum(per.values())} rows, tries {tries}; ' + ', '.join(f'{k} {per[k]}' for k in SP.SCORED))
    print('sha256', sha256_file(TRAIN_ROWS))


def pair_split(seed=L3_SEED, kinds=None):
    """-> (train_pairs, held_pairs): the unordered pairs of the kinds shuffled by Random(seed), first 14 train / last 7 held out;
    the same rng shuffles again until every kind is in >= 1 training pair and >= 1 held-out pair."""
    kinds = list(SP.SCORED if kinds is None else kinds)
    pairs = list(itertools.combinations(kinds, 2))
    n_train = len(pairs) * 2 // 3
    rng = random.Random(seed)
    while True:
        rng.shuffle(pairs)
        train, held = pairs[:n_train], pairs[n_train:]
        if all(any(k in p for p in train) and any(k in p for p in held) for k in kinds):
            return [tuple(p) for p in train], [tuple(p) for p in held]


def partners_of(pairs, kinds=None):
    """kind -> partner kinds (in SCORED order) over the unordered pairs: a pair serves either order."""
    kinds = list(SP.SCORED if kinds is None else kinds)
    return {k: [j for j in kinds if (k, j) in pairs or (j, k) in pairs] for k in kinds}


def combine_layout(layout, K, J):
    """L5's layouts, as P.combine builds them: (formula text, value function of the grid), None-safe through P._bin."""
    (kt, kf), (jt, jf) = K, J
    if layout == 'K+J':
        return P.combine('+', K, J)
    if layout == '(K)*(J)':
        return P.combine('*', K, J)
    if layout == 'K-J':
        return f'{kt}-{jt}', lambda g: P._bin(lambda x, y: x - y, kf(g), jf(g))
    if layout == 'K*J':
        return f'{kt}*{jt}', lambda g: P._bin(lambda x, y: x * y, kf(g), jf(g))
    if layout == '(K)+(J)':
        return f'({kt})+({jt})', lambda g: P._bin(lambda x, y: x + y, kf(g), jf(g))
    if layout == '(K)-(J)':
        return f'({kt})-({jt})', lambda g: P._bin(lambda x, y: x - y, kf(g), jf(g))
    raise ValueError(layout)


def joined_candidate(kind, partners, op, rng):
    """sheet_probe.candidate's F4-two branch, with the joiner fixed to op and the partner drawn only from `partners`."""
    agg = kind in P.AGG
    n = rng.choice([2, 3, 4])
    K = P.piece(kind, rng, n, None, rng.randint(2, n) if agg else None)
    partner = rng.choice(partners)
    J = P.piece(partner, rng, n, None, 2 if partner in P.AGG else None)
    formula, fn = combine_layout(op, K, J) if op in L5_LAYOUTS + ('(K)*(J)',) else P.combine(op, K, J)
    g = {c: [rng.randint(1, 99) for _ in range(n)] for c in 'AB'}
    return P.render(g, formula), fn, g, formula, partner


def draw_joined(rng, pairs, op, total, cell, tag, exclude, seen, help_prompts, on_short=False):
    """total joined rows (first kind balanced over SCORED by quotas), accepted through sheet_probe.check. -> (rows, stats).
    on_short (L5): a kind that hits MAX_TRIES keeps what it got (stats show it) instead of raising."""
    part = partners_of(pairs)
    q = quotas(total, SP.SCORED)
    layouted = op in L5_LAYOUTS + ('(K)*(J)',)   # L5: rows carry their layout; L1-L4 callers pass '+' / '*'
    rows, stats = [], {}
    for ki, kind in enumerate(SP.SCORED, 1):
        st = Counter()
        while st['accepted'] < q[kind]:
            st['tries'] += 1
            if st['tries'] > SP.MAX_TRIES:
                if on_short:
                    break
                raise RuntimeError(f'{kind} {cell}: not full after {SP.MAX_TRIES} draws')
            prompt, fn, g, formula, partner = joined_candidate(kind, part[kind], op, rng)
            reason, res = SP.check(prompt, fn(g), help_prompts, exclude, seen)
            if reason:
                st[reason] += 1
                continue
            seen.add(prompt)
            row = {'id': f'{tag}-{cell}-{ki:02d}-{st["accepted"]:04d}', 'kind': kind, 'partner': partner, 'split': cell,
                   'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])}
            if layouted:
                row['layout'] = op
            rows.append(row)
            st['accepted'] += 1
        stats[(kind, f'{cell}|{op}' if layouted else cell)] = st
    return rows, stats


def build_l3_train(rng, exclude, train_pairs, per_cell=PER_CELL):
    """-> (rows, stats): per_cell joined rows ('+', training pairs; split 'F4-two') then per_cell F0-near rows (L1's recipe)."""
    help_list = sheet_tool.help()
    help_prompts = {h['prompt'] for h in help_list}
    help_skel = {h['kind']: P.skeleton(h['prompt'].split('; =')[1]) for h in help_list}
    seen = set()
    rows, stats = draw_joined(rng, train_pairs, '+', per_cell, 'F4-two', 'learn3', exclude, seen, help_prompts)
    q = quotas(per_cell, SP.SCORED)
    for ki, kind in enumerate(SP.SCORED, 1):
        st = Counter()
        while st['accepted'] < q[kind]:
            st['tries'] += 1
            if st['tries'] > SP.MAX_TRIES:
                raise RuntimeError(f'{kind} F0-near: not full after {SP.MAX_TRIES} draws')
            prompt, fn, g, formula = SP.candidate(kind, 'F0-near', rng)
            reason, res = SP.check(prompt, fn(g), help_prompts, exclude, seen)
            if reason is None and P.skeleton(formula) != help_skel[kind]:
                reason = 'near shape'
            if reason:
                st[reason] += 1
                continue
            seen.add(prompt)
            rows.append({'id': f'learn3-F0-near-{ki:02d}-{st["accepted"]:04d}', 'kind': kind, 'split': 'F0-near',
                         'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])})
            st['accepted'] += 1
        stats[(kind, 'F0-near')] = st
    return rows, stats


def build_l3_eval(rng, exclude, train_prompts, train_pairs, held_pairs, per_cell=L3_EVAL_N):
    """-> (rows, stats): the four cells S, HP, HO, HPO; no prompt in exclude or in the training prompts or in another cell."""
    help_prompts = {h['prompt'] for h in sheet_tool.help()}
    seen = set(train_prompts)
    spec = {'S': ('+', train_pairs), 'HP': ('+', held_pairs), 'HO': ('*', train_pairs), 'HPO': ('*', held_pairs)}
    rows, stats = [], {}
    for cell in L3_CELLS:
        op, pairs = spec[cell]
        rs, st = draw_joined(rng, pairs, op, per_cell, cell, 'l3', exclude, seen, help_prompts)
        rows += rs
        stats.update(st)
    return rows, stats


def write_new(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    os.rename(tmp, path)


def build_l3():
    for path in (L3_TRAIN_ROWS, L3_EVAL_ROWS, L3_SPLIT):
        if os.path.exists(path):
            raise SystemExit(f'refusing to overwrite {path}')
    train_pairs, held_pairs = pair_split()
    print('training pairs (14):', ', '.join(f'{a}/{b}' for a, b in train_pairs))
    print('held-out pairs (7): ', ', '.join(f'{a}/{b}' for a, b in held_pairs))
    exclude = read_prompts(EXCLUDE_FILES + (TRAIN_ROWS, MODE_ROWS))
    trows, tstats = build_l3_train(random.Random(L3_SEED), exclude, train_pairs)
    train_prompts = {r['prompt'] for r in trows}
    erows, estats = build_l3_eval(random.Random(L3_EVAL_SEED), exclude, train_prompts, train_pairs, held_pairs)
    eprompts = [r['prompt'] for r in erows]
    assert len(train_prompts) == len(trows) and len(set(eprompts)) == len(erows)
    assert not (train_prompts | set(eprompts)) & exclude and not train_prompts & set(eprompts)
    dump = lambda rs: ''.join(json.dumps(r) + '\n' for r in rs)
    split = dict(seed=L3_SEED, kinds=SP.SCORED, train=[list(p) for p in train_pairs], held_out=[list(p) for p in held_pairs])
    write_new(L3_SPLIT, json.dumps(split, indent=1) + '\n')
    write_new(L3_TRAIN_ROWS, dump(trows))
    write_new(L3_EVAL_ROWS, dump(erows))
    print(f'excluded prompts: {len(exclude)}')
    for name, rows in (('train', trows), ('eval', erows)):
        print(f'{name}: {len(rows)} rows')
        for cell in dict.fromkeys(r['split'] for r in rows):
            per = Counter(r['kind'] for r in rows if r['split'] == cell)
            tries = sum(st['tries'] for st_ in (tstats, estats) for (k, c), st in st_.items() if c == cell)
            print(f'  {cell}: {sum(per.values())} rows, tries {tries}; ' + ', '.join(f'{k} {per[k]}' for k in SP.SCORED))
    for path in (L3_SPLIT, L3_TRAIN_ROWS, L3_EVAL_ROWS):
        print('sha256', sha256_file(path), os.path.basename(path))


def build_l5_train(rng, exclude, train_pairs, per_layout=L5_PER_LAYOUT, per_cell=PER_CELL):
    """-> (rows, stats): per_layout joined rows for each of the five layouts (training pairs; split 'F4-two'), then per_cell
    F0-near rows (L3's recipe). A layout that cannot fill its share keeps what it got (stats)."""
    help_list = sheet_tool.help()
    help_prompts = {h['prompt'] for h in help_list}
    help_skel = {h['kind']: P.skeleton(h['prompt'].split('; =')[1]) for h in help_list}
    seen = set()
    rows, stats = [], {}
    for i, layout in enumerate(L5_LAYOUTS, 1):
        rs, st = draw_joined(rng, train_pairs, layout, per_layout, 'F4-two', f'learn5-L{i}', exclude, seen, help_prompts, on_short=True)
        rows += rs
        stats.update(st)
    q = quotas(per_cell, SP.SCORED)
    for ki, kind in enumerate(SP.SCORED, 1):
        st = Counter()
        while st['accepted'] < q[kind]:
            st['tries'] += 1
            if st['tries'] > SP.MAX_TRIES:
                raise RuntimeError(f'{kind} F0-near: not full after {SP.MAX_TRIES} draws')
            prompt, fn, g, formula = SP.candidate(kind, 'F0-near', rng)
            reason, res = SP.check(prompt, fn(g), help_prompts, exclude, seen)
            if reason is None and P.skeleton(formula) != help_skel[kind]:
                reason = 'near shape'
            if reason:
                st[reason] += 1
                continue
            seen.add(prompt)
            rows.append({'id': f'learn5-F0-near-{ki:02d}-{st["accepted"]:04d}', 'kind': kind, 'split': 'F0-near',
                         'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])})
            st['accepted'] += 1
        stats[(kind, 'F0-near')] = st
    return rows, stats


def build_l5_eval(rng, exclude, train_prompts, train_pairs, held_pairs, per_cell=L5_EVAL_N, per_layout=L5_S5_PER_LAYOUT):
    """-> (rows, stats): S5 (per_layout rows in each of the five layouts, training pairs), S ('K+J', training pairs),
    HP ('K+J', held-out), HO ('(K)*(J)', training pairs), HPO ('(K)*(J)', held-out). No prompt in exclude, in the training
    prompts or in another cell."""
    help_prompts = {h['prompt'] for h in sheet_tool.help()}
    seen = set(train_prompts)
    rows, stats = [], {}
    for i, layout in enumerate(L5_LAYOUTS, 1):
        rs, st = draw_joined(rng, train_pairs, layout, per_layout, 'S5', f'l5-L{i}', exclude, seen, help_prompts)
        rows += rs
        stats.update(st)
    spec = {'S': ('K+J', train_pairs), 'HP': ('K+J', held_pairs), 'HO': ('(K)*(J)', train_pairs), 'HPO': ('(K)*(J)', held_pairs)}
    for cell in L5_CELLS[1:]:
        op, pairs = spec[cell]
        rs, st = draw_joined(rng, pairs, op, per_cell, cell, 'l5', exclude, seen, help_prompts)
        rows += rs
        stats.update(st)
    return rows, stats


def build_l5():
    for path in (L5_TRAIN_ROWS, L5_EVAL_ROWS):
        if os.path.exists(path):
            raise SystemExit(f'refusing to overwrite {path}')
    split = json.load(open(L3_SPLIT))   # L3's split, as written: not redrawn
    train_pairs, held_pairs = [tuple(p) for p in split['train']], [tuple(p) for p in split['held_out']]
    assert (train_pairs, held_pairs) == pair_split(), 'L3 split file does not match pair_split()'
    exclude = read_prompts(EXCLUDE_FILES + (TRAIN_ROWS, MODE_ROWS, L3_TRAIN_ROWS, L3_EVAL_ROWS, L4_ROWS, L4R1_ROWS))
    trows, tstats = build_l5_train(random.Random(L5_SEED), exclude, train_pairs)
    train_prompts = {r['prompt'] for r in trows}
    erows, estats = build_l5_eval(random.Random(L5_EVAL_SEED), exclude, train_prompts, train_pairs, held_pairs)
    eprompts = [r['prompt'] for r in erows]
    assert len(train_prompts) == len(trows) and len(set(eprompts)) == len(erows)
    assert not (train_prompts | set(eprompts)) & exclude and not train_prompts & set(eprompts)
    dump = lambda rs: ''.join(json.dumps(r) + '\n' for r in rs)
    write_new(L5_TRAIN_ROWS, dump(trows))
    write_new(L5_EVAL_ROWS, dump(erows))
    print(f'excluded prompts: {len(exclude)}')
    for name, rows, stats in (('train', trows, tstats), ('eval', erows, estats)):
        print(f'{name}: {len(rows)} rows')
        for cell in dict.fromkeys(r['split'] for r in rows):
            sub = [r for r in rows if r['split'] == cell]
            print(f'  {cell}: {len(sub)} rows')
            for lay in dict.fromkeys(r.get('layout') for r in sub):
                ls = [r for r in sub if r.get('layout') == lay]
                key = f'{cell}|{lay}' if lay else cell
                tries = sum(st['tries'] for (k, c), st in stats.items() if c == key)
                want = L5_PER_LAYOUT if (name == 'train' and lay) else L5_S5_PER_LAYOUT if lay else None
                per = Counter(r['kind'] for r in ls)
                short = f' (SHORT of {want})' if want and len(ls) < want else ''
                print(f'    {lay or "-"}: {len(ls)} rows{short}, tries {tries}; ' + ', '.join(f'{k} {per[k]}' for k in SP.SCORED))
        rej = Counter()
        for st in stats.values():
            rej.update({k: v for k, v in st.items() if k not in ('tries', 'accepted')})
        print('  rejections:', dict(rej))
    for path in (L5_TRAIN_ROWS, L5_EVAL_ROWS):
        print('sha256', sha256_file(path), os.path.basename(path))


def far_props(prompt):
    """The coverage parser's far properties of one sheet prompt."""
    from domain.far.coverage import parse_sheet
    p = parse_sheet(prompt)
    return dict(two_kinds=bool(p['two_kinds']), grid_rows=p['grid_rows'] >= 5, max_range_cells=p['max_range_cells'] >= 5,
                max_row_ref=p['max_row_ref'] >= 5)


def build_mode_rows(m, parent_chars, cons, exclude, per_cell=PER_CELL, seed=MODE_SEED, draw_cap=MODE_DRAW_CAP, tag='learn2'):
    """-> (rows, stats). The v9 mode's own maker (mode.draft over widen.build rings, as mode.main builds them for the sheet
    tool), kinds drawn evenly (round robin over the scored kinds), rings evenly (mode.pick_example), then the mode's make_row
    (source 'tool'). Split by coverage.parse_sheet(...)['two_kinds'] until both cells hold per_cell rows or draw_cap draws."""
    from domain import mode
    from domain.far import widen
    tool = sheet_tool
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ctx = dict(vchars=set(parent_chars), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    rings, wst = widen.build(tool, helps, lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(f'{seed}-widen'), cons)
    ex = widen.by_kind(rings, kinds)
    assert all(k in ex for k in SP.SCORED), 'a scored kind is not on the help page'
    rng = random.Random(f'{seed}-train')
    rows, drops, per = [], Counter(), {c: 0 for c in MODE_CELLS}
    draws = 0
    while min(per.values()) < per_cell and draws < draw_cap:
        kind = SP.SCORED[draws % len(SP.SCORED)]
        draws += 1
        if draws % 1_000_000 == 0:
            print(f'  {draws} draws: kept {per}', flush=True)
        item, why = mode.draft(tool, ex[kind], kind, rng, ctx)
        if item is None:
            drops[why] += 1
            continue
        prompt = item['prompt']
        if prompt in exclude:
            ctx['seen'].add(prompt)
            drops['in_probe_or_panel'] += 1
            continue
        cell = MODE_CELLS[0] if far_props(prompt)['two_kinds'] else MODE_CELLS[1]
        if per[cell] >= per_cell:
            drops['cell_full'] += 1
            continue
        row, why = mode.make_row(m, 'domain_sheet', prompt, item['value'], item['steps'], cons, 'tool')
        if row is None:
            drops['make_row_' + why] += 1
            continue
        ctx['seen'].add(prompt)
        rows.append({'id': f'{tag}-{cell}-{per[cell]:05d}', 'kind': kind, 'split': cell, 'cell': cell, 'prompt': prompt,
                     'answer': item['value'], 'n_steps': len(item['steps']), 'ring': item['ring']})
        per[cell] += 1
    stats = dict(draws=draws, drops=dict(drops), per=per, widen_kept=wst['kept'], widen_sha256=wst['sha256'], widen=wst,
                 complete=min(per.values()) >= per_cell)
    return rows, stats


def arrangement(prompt):
    """'plus' (the formula body is a top-level K+J, K and J each a function call or a cell expression), 'bracket-times'
    (contains )*( ) or 'other'."""
    body = prompt.partition(';')[2].strip().lstrip('=')
    def unit(t):
        t = t.strip()
        call = re.fullmatch(r'[A-Z]+\((.*)\)', t)
        if call:   # one call: its first bracket closes at the end
            depth = 0
            for k, c in enumerate(t):
                depth += (c == '(') - (c == ')')
                if c == ')' and depth == 0:
                    return k == len(t) - 1
        return bool(re.fullmatch(r'[0-9A-Z*/+\-]+', t)) and bool(re.search(r'[A-Z][0-9]', t)) and '(' not in t
    depth = 0
    for k, c in enumerate(body):
        depth += (c == '(') - (c == ')')
        if c == '+' and depth == 0 and unit(body[:k]) and unit(body[k + 1:]):
            return 'plus'
    return 'bracket-times' if ')*(' in body else 'other'


def build_mode(rows_path=MODE_ROWS, seed=MODE_SEED, join=False, tag='learn2', extra_exclude=()):
    if os.path.exists(rows_path):
        raise SystemExit(f'refusing to overwrite {rows_path}')
    import torch
    from custom_io.models import load_model
    from domain.mode import CONST_PATH
    cons = json.load(open(CONST_PATH))
    if join:
        cons = dict(cons, widen_join=True)
    random.seed(seed)
    torch.manual_seed(seed)
    ck = torch.load(PARENT, map_location='cpu', weights_only=True)
    torch.manual_seed(seed)
    m = load_model(PARENT).eval()
    exclude = read_prompts(EXCLUDE_FILES + tuple(extra_exclude))
    rows, st = build_mode_rows(m, ck['chars'], cons, exclude, seed=seed, tag=tag)
    w = st['widen']
    print(f'excluded prompts: {len(exclude)}; draws {st["draws"]}; widen kept {st["widen_kept"]} sha {st["widen_sha256"][:12]}')
    print(f'widen tries {w["tries"]}; per kind {w["per_kind"]}' + (f'; symbols {"".join(w["symbols"])}; ring 4 accepted join kinds {w["join"]["accepted"]}; kept per join kind {w["join"]["kept"]}' if join else ''))
    print('drops:', st['drops'])
    if not st['complete']:
        print(f'INCOMPLETE: found {st["per"]} (wanted {PER_CELL} each) after {st["draws"]} draws; nothing written')
        raise SystemExit(1)
    assert not {r['prompt'] for r in rows} & exclude and len({r['prompt'] for r in rows}) == len(rows)
    tmp = rows_path + '.tmp'
    with open(tmp, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    os.rename(tmp, rows_path)
    print(f'wrote {len(rows)} rows to {rows_path}')
    print('per kind:', dict(Counter(r['kind'] for r in rows)))
    print('per ring:', dict(sorted(Counter(r['ring'] for r in rows).items())))
    for c in MODE_CELLS:
        rs = [r for r in rows if r['split'] == c]
        print(f'  {c}: {len(rs)} rows; kinds {dict(Counter(r["kind"] for r in rs))}; rings {dict(sorted(Counter(r["ring"] for r in rs).items()))}')
    props = [far_props(r['prompt']) for r in rows]
    for k in ('grid_rows', 'max_range_cells', 'max_row_ref', 'two_kinds'):
        print(f'  share {k}{">=5" if k != "two_kinds" else ""}: ' +
              ', '.join(f'{c} {100.0 * sum(p[k] for p, r in zip(props, rows) if r["split"] == c) / PER_CELL:.1f}%' for c in MODE_CELLS) +
              f', all {100.0 * sum(p[k] for p in props) / len(rows):.1f}%')
    if join:
        two = [r for r in rows if r['split'] == MODE_CELLS[0]]
        arr = Counter(arrangement(r['prompt']) for r in two)
        print('  joined rows per arrangement: ' + ', '.join(f'{a} {100.0 * arr[a] / len(two):.1f}% ({arr[a]})'
                                                           for a in ('plus', 'bracket-times', 'other')))
        print(f'  joined rows from ring 4: {sum(r["ring"] == 4 for r in two)} of {len(two)}')
    print('sha256', sha256_file(rows_path))


def build_l4(rows_path=L4R1_ROWS):
    build_mode(rows_path, L4_SEED, True, 'learn4', (MODE_ROWS, L3_TRAIN_ROWS, L3_EVAL_ROWS))


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_sets(train_rows, cells='l1', fit_seed=SEED, v3_path=V3_PANEL, l3_path=L3_EVAL_ROWS, l5_path=L5_EVAL_ROWS):
    """The scored cells: name -> rows (each row's id made unique across cells; the row's split is the cell name).
    cells 'l1': F4-two, F0-near, F2b-rows, fit (L1, unchanged). cells 'all' (L2): every probe split (scored kinds), fit,
    and the sealed sheet.v3 panel (scored kinds) as v3-near / v3-far (scoring only). cells 'l3': S, HP, HO, HPO (from the L3 eval
    file), probe F0-near and F4-two, fit. cells 'l4': everything in 'all' plus S, HP, HO, HPO.
    cells 'l5': S5, S, HP, HO, HPO (from the L5 eval file), probe F0-near and F4-two, fit."""
    assert cells in ('l1', 'all', 'l3', 'l4', 'l5'), cells
    probe = [r for r in load_jsonl(SP.PROBE) if r['kind'] in SP.SCORED]
    names = {'l1': ('F4-two', 'F0-near', 'F2b-rows'), 'all': PROBE_CELLS, 'l4': PROBE_CELLS, 'l3': ('F0-near', 'F4-two'), 'l5': ('F0-near', 'F4-two')}[cells]
    sets = {}
    if cells in ('l3', 'l4'):
        l3 = load_jsonl(l3_path)
        sets = {c: [r for r in l3 if r['split'] == c] for c in L3_CELLS}
        assert all(len(v) == L3_EVAL_N for v in sets.values()), {k: len(v) for k, v in sets.items()}
    if cells == 'l5':
        l5 = load_jsonl(l5_path)
        sets = {c: [r for r in l5 if r['split'] == c] for c in L5_CELLS}
        assert all(len(v) == L5_EVAL_N for v in sets.values()), {k: len(v) for k, v in sets.items()}
    sets.update({c: [dict(r, split=c) for r in probe if r['split'] == c] for c in names})
    joined = [r for r in train_rows if r['split'] in JOINED_CELLS]
    fit = random.Random(fit_seed).sample(joined, FIT_N)
    sets['fit'] = [dict(r, id='fit-' + r['id'], split='fit') for r in fit]
    if cells in ('all', 'l4'):
        for sp in ('near', 'far'):
            sets['v3-' + sp] = [dict(r, id='v3-' + r['id'], split='v3-' + sp) for r in load_jsonl(v3_path)
                                if r['split'] == sp and r['kind'] in SP.SCORED]
    ids = [r['id'] for s in sets.values() for r in s]
    assert len(ids) == len(set(ids)), 'eval ids not unique'
    return sets


def score_step(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None):
    from domain.mode import save_ckpt
    from domain.score import score
    t0 = time.time()
    path = os.path.join(out, f'step_{step}', 'checkpoint.pt')
    m.eval()
    save_ckpt(ck, m, path, addon)
    rows = [r for s in sets.values() for r in s]
    run = score(path, rows, f'{arm}-{step}')
    hit = {o['id']: o['hit'] for o in run['rows']}
    cells = {}
    for name, rs in sets.items():
        h = sum(hit[r['id']] for r in rs)
        cells[name] = {'n': len(rs), 'hits': h, 'pct': round(100.0 * h / len(rs), 2)}
    secs = round(time.time() - t0, 1)
    with open(os.path.join(out, 'scores.jsonl'), 'a') as f:
        rec = {'arm': arm, 'step': step, 'cells': cells, 'secs': secs, 'train_secs': round(t_train, 1)}
        rec.update(extra or {})
        f.write(json.dumps(rec) + '\n')
    print(f'{arm} step {step}: ' + ' '.join(f'{k} {v["pct"]:.1f}' for k, v in cells.items()) + f' (score {secs}s)', flush=True)
    os.remove(path)   # the checkpoint is only a vehicle for the scorer
    os.rmdir(os.path.dirname(path))


def make_rows(m, train_rows, cons):
    """The mode's make_row, source 'tool': the tool's working is the target. Rows the mode would drop are counted."""
    from domain.mode import make_row
    out, drops = [], Counter()
    for r in train_rows:
        res = sheet_tool.evaluate(r['prompt'])
        steps = [tuple(s) for s in res['steps']]
        row, why = make_row(m, 'domain_sheet', r['prompt'], res['value'], steps, cons, 'tool')
        if row is None:
            drops[why] += 1
        else:
            out.append(row)
    return out, drops


def batch_order(n, batch, updates, seed):
    """Fixed order from the seed: reshuffled passes, batches of `batch` taken in sequence (as train_night's new half)."""
    rng = np.random.RandomState(seed)
    order, pos = np.array([], dtype=int), 0
    for _ in range(updates):
        ni = []
        while len(ni) < batch:
            if pos >= len(order):
                order, pos = rng.permutation(n), 0
            take = min(batch - len(ni), len(order) - pos)
            ni += [int(i) for i in order[pos:pos + take]]
            pos += take
        yield ni


def addon_size(arm, cons, rank=None, alpha=None):
    """(rank, alpha) for arm LA: the mode's constants unless overridden. LB has no add-on: overrides are refused."""
    if arm != 'LA':
        if rank is not None or alpha is not None:
            raise SystemExit('--addon-rank/--addon-alpha apply to arm LA only')
        return None, None
    return (cons['addon_rank'] if rank is None else rank), (cons['addon_alpha'] if alpha is None else alpha)


def train(arm, updates, threads, out, steps, parent=PARENT, train_path=TRAIN_ROWS, log_every=100, cells='l1',
          addon_rank=None, addon_alpha=None):
    import torch
    from custom_io.data import Dataset, collate, to_device
    from custom_io.models import load_model
    from domain.mode import AddOn, CONST_PATH, make_opt
    torch.set_num_threads(threads)
    assert arm in ('LA', 'LB')
    assert steps and max(steps) <= updates and min(steps) >= 0, (steps, updates)
    cons = json.load(open(CONST_PATH))
    rank, alpha = addon_size(arm, cons, addon_rank, addon_alpha)
    extra = {'addon_rank': rank, 'addon_alpha': alpha}
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, 'scores.jsonl')):
        raise SystemExit(f'refusing to reuse {out}: scores.jsonl exists')
    train_rows = load_jsonl(train_path)
    fit_seed = L5_SEED if cells == 'l5' else L4_SEED if cells == 'l4' else L3_SEED if cells == 'l3' else MODE_SEED if os.path.abspath(train_path) == MODE_ROWS else SEED
    sets = eval_sets(train_rows, cells, fit_seed)
    print(f'{arm}: rows {train_path}; scored cells {cells}: ' + ', '.join(f'{k} {len(v)}' for k, v in sets.items()), flush=True)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(SEED)
    m = load_model(parent).eval()
    rows, drops = make_rows(m, train_rows, cons)
    print(f'{arm}: {len(rows)} of {len(train_rows)} rows usable; dropped {dict(drops)}', flush=True)
    ds = Dataset(rows, m.vocab)
    if arm == 'LA':
        addon = AddOn(m, rank, alpha, SEED)
        addon.on = True
        params = addon.params()
        opt = torch.optim.AdamW([{'params': params, 'weight_decay': 0.1}], lr=cons['addon_lr'], betas=(0.9, 0.95))
        print(f'LA add-on params {addon.n_params()}, lr {cons["addon_lr"]}', flush=True)
    else:
        addon = None
        params = list(m.parameters())
        assert all(p.requires_grad for p in params)
        opt = make_opt(m, cons['lr'])
        print(f'LB full fine-tune params {sum(p.numel() for p in params)}, lr {cons["lr"]}', flush=True)
    torch.manual_seed(SEED)   # ans_drill draws from the model's own RNG in train mode
    t_train, t_seg, losses = 0.0, time.time(), []
    steps = set(steps)
    if 0 in steps:
        score_step(ck, m, addon, sets, out, arm, 0, t_train, threads, extra)
    t_seg = time.time()
    for u, ni in enumerate(batch_order(len(rows), cons['batch'], updates, SEED), 1):
        t0 = time.time()
        m.train()
        b = to_device(collate([ds[i] for i in ni]), 'cpu')
        o = m.loss(b)
        loss = o[0] if isinstance(o, tuple) else o
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        t_train += time.time() - t0
        if u % log_every == 0 or u == updates:
            k = u % log_every or log_every
            print(f'{arm} update {u}: {time.time() - t_seg:.1f}s for last {k} ({(time.time() - t_seg) / k:.3f} s/update), '
                  f'loss {np.mean(losses[-k:]):.4f}', flush=True)
            t_seg = time.time()
        if u in steps:
            score_step(ck, m, addon, sets, out, arm, u, t_train, threads, extra)
            t_seg = time.time()
    m.eval()
    print(f'{arm} done: {updates} updates, train {t_train:.1f}s ({t_train / max(updates, 1):.3f} s/update)', flush=True)
    return t_train / max(updates, 1)


def main(argv=None):
    a = argparse.ArgumentParser(description='L1: can the 3M model learn joined formulas? (diagnosis only)')
    a.add_argument('stage', choices=['build', 'build-mode', 'build-l3', 'build-l4', 'build-l5', 'train'])
    a.add_argument('--arm', choices=['LA', 'LB'])
    a.add_argument('--updates', type=int, default=4000)
    a.add_argument('--threads', type=int, default=1)
    a.add_argument('--out')
    a.add_argument('--rows', default=TRAIN_ROWS, help='training rows (default: the L1 file)')
    a.add_argument('--cells', choices=['l1', 'all', 'l3', 'l4', 'l5'], default='l1',
               help='scored sets: l1 = four cells; all = L2 (probe splits, fit, v3); l3 = S, HP, HO, HPO, F0-near, F4-two, fit; l4 = all + S, HP, HO, HPO; l5 = S5, S, HP, HO, HPO, F0-near, F4-two, fit')
    a.add_argument('--addon-rank', type=int, default=None, help="arm LA only: add-on rank (default: the mode's constant)")
    a.add_argument('--addon-alpha', type=float, default=None, help="arm LA only: add-on alpha (default: the mode's constant)")
    a.add_argument('--steps', default=DEFAULT_STEPS, help='comma list of update counts to score at')
    a = a.parse_args(argv)
    if a.stage == 'build':
        build()
    elif a.stage == 'build-mode':
        build_mode()
    elif a.stage == 'build-l3':
        build_l3()
    elif a.stage == 'build-l5':
        build_l5()
    elif a.stage == 'build-l4':
        build_l4()
    else:
        assert a.arm and a.out, 'train needs --arm and --out'
        addon_size(a.arm, {}, a.addon_rank, a.addon_alpha)   # refuse LB overrides before any work
        train(a.arm, a.updates, a.threads, a.out, [int(x) for x in a.steps.split(',')],
              train_path=a.rows, cells=a.cells, addon_rank=a.addon_rank, addon_alpha=a.addon_alpha)


if __name__ == '__main__':
    main()
