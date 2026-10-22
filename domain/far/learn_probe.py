"""L1 diagnosis: can the 3M calculator model learn joined formulas at all? (spec: far-transfer/learn/MARKS-L1-2026-10-11.md)

  python3 -m domain.far.learn_probe build
  python3 -m domain.far.learn_probe build-mode     (L2: MARKS-L2; rows from the v9 mode's own practice maker)
  python3 -m domain.far.learn_probe build-l3       (L3: MARKS-L3; '+' joins of training kind pairs; eval cells S/HP/HO/HPO)
  python3 -m domain.far.learn_probe build-l4      (L4: MARKS-L4; build-mode with the swap tool's join step on, seed 93601)
  python3 -m domain.far.learn_probe build-l5      (L5: MARKS-L5; training joins over five layouts; eval cells S5/S/HP/HO/HPO)
  python3 -m domain.far.learn_probe build-l8 --rows-out PATH --parent CKPT --probe PATH --eval-rows PATH   (L8: MARKS-L8; the substitution ring's joins)
  python3 -m domain.far.learn_probe build-l9 --rows-out PATH --parent CKPT --probe PATH --eval-rows PATH   (L9: MARKS-L9; whole-formula joins)
  python3 -m domain.far.learn_probe train --arm LA|LB --updates 4000 --threads N --out DIR [--steps 0,500,1000,2000,4000] [--rows PATH] [--cells l1|all|l3|l4|l5|l8]
        [--harm-steps 1000,2000,4000 [--dev PATH]] [--keep-final]                 (L7: old-skill harm vs the parent, kept final checkpoint)
        [--guard kf|kfsoft --guard-energy 0.99 --guard-every 500 --guard-src DIR]        (L7, arm LB only: the main-brain K-FAC guard)
       [--kl-replay-rows 32 --kl-weight 10 [--guard-soft 10]]        (L11 / L13, only with --guard kfsoft: graded mask (soft 1; L13: 10) + KL-to-parent replay, Main brain c823e4b9a)
       [--seed N] [--first-call-weight W]        (R1, Oct 2026: --seed re-points the run seed (module SEED and the import-derived
        KL_REPLAY_SEED together; the eval fit seed, chosen before it applies, and the build-time streams stay as shipped);
        --first-call-weight (default 1.0 = shipped) weights the first call's losses (the call writer's token losses
        and round 0's span_call term), renormalised per trace to the uniform-weight trace mean - see install_first_call_weight)
        [--log-update-rms]        (C8, opt-in, read-only: grad-norm and per-group update-rms history -> OUT/update-rms.json; off = unchanged)

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
import math
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
L8_SEED = 93801   # L8 (spec: MARKS-L8-2026-10-12.md): joined rows only from widen.subst_ring, not-joined from rings 1-3
L8_TAG = 'learn8'
L8_SUBST_DEPTH = 3
L9_SEED = 93901   # L9 (spec: MARKS-L9-2026-10-12.md): joined rows only from widen.whole_join_ring, not-joined from rings 1-3
L9_TAG = 'learn9'
L10_SEED = 94001   # L10 (spec: MARKS-L10-2026-10-12.md): joined rows from joinlast.join_last_draft, not-joined from rings 1-3
L10_TAG = 'learn10'
L12_SEED = L10_SEED + 1   # L12 (spec: MARKS-L12-2026-10-12.md): join-last with piece 1 drawn from the v9 widened rings 1-3
L12_TAG = 'learn12'
L9_ROWS = os.path.join(LEARN, 'train-rows-l9.jsonl')
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


class Pick(list):
    """A list of prompts that remembers the index rng.choice last took (so the host's kind can be recovered after mode.draft)."""
    last = None

    def __getitem__(self, i):
        self.last = i
        return super().__getitem__(i)


def fn_op_fn(prompt):
    """True when the formula's top level (bracket depth 0, after the first '=') is exactly two parts joined by one '+' or one
    '*' and both parts are a single function call NAME(...)."""
    body = prompt.partition(';')[2].strip().lstrip('=')
    depth, ops = 0, []
    for k, c in enumerate(body):
        depth += (c == '(') - (c == ')')
        if depth == 0 and c in '+*':
            ops.append(k)
    if len(ops) != 1:
        return False
    def call(t):
        if not re.fullmatch(r'[A-Z]+\(.*\)', t.strip()):
            return False
        d = 0
        for k, c in enumerate(t.strip()):
            d += (c == '(') - (c == ')')
            if d == 0 and c == ')':
                return k == len(t.strip()) - 1
        return False
    return call(body[:ops[0]]) and call(body[ops[0] + 1:])


def build_l8_rows(m, parent_chars, cons, exclude, per_cell=PER_CELL, seed=L8_SEED, draw_cap=MODE_DRAW_CAP, tag=L8_TAG,
                  join_kinds=None, census=None):
    """-> (rows, stats). Joined rows ('mode-two') are drafted only from the substitution ring (widen.subst_ring; the host's
    kind is recorded), not-joined rows ('mode-one') from rings 1-3 by kind round robin as build_mode_rows does. The two draws
    alternate until both cells hold per_cell rows or draw_cap draws. cons must hold widen_subst (or widen_join_whole).
    L10: join_kinds (the accepted join kinds [(form, symbol)]) makes the joined draws joinlast.join_last_draft instead (no
    join ring is read; cons holds no ring flag); census (a Census) then counts each of those attempts."""
    from domain import mode
    from domain.far import widen
    tool = sheet_tool
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ctx = dict(vchars=set(parent_chars), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    rings, wst = widen.build(tool, helps, lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(f'{seed}-widen'), cons)
    sr = cons['widen_rings'] + 1
    ex = widen.by_kind({r: v for r, v in rings.items() if r < sr}, kinds)
    assert all(k in ex for k in SP.SCORED), 'a scored kind is not on the help page'
    if join_kinds is None:
        host = Pick(p for _, p in rings[sr])
        host_kind = [k for k, _ in rings[sr]]
        jex = {sr: host}
    can_join = bool(host) if join_kinds is None else bool(join_kinds)
    rng = random.Random(f'{seed}-train')
    rows, drops, per = [], Counter(), {c: 0 for c in MODE_CELLS}
    draws = nj = shown = 0

    def keep(item, kind, cell):
        prompt = item['prompt']
        if prompt in exclude:
            ctx['seen'].add(prompt)
            drops['in_probe_or_panel'] += 1
            return
        row, why = mode.make_row(m, 'domain_sheet', prompt, item['value'], item['steps'], cons, 'tool')
        if row is None:
            drops['make_row_' + why] += 1
            return
        ctx['seen'].add(prompt)
        rows.append({'id': f'{tag}-{cell}-{per[cell]:05d}', 'kind': kind, 'split': cell, 'cell': cell, 'prompt': prompt,
                     'answer': item['value'], 'n_steps': len(item['steps']), 'ring': item['ring']})
        per[cell] += 1

    while min(per.values()) < per_cell and draws < draw_cap and can_join:
        if per[MODE_CELLS[0]] < per_cell and join_kinds is not None:   # one joined try: join-last (L10)
            from domain.far import joinlast
            draws += 1
            item, why = joinlast.join_last_draft(tool, helps, join_kinds, rng, ctx)
            if census is not None:
                census.add(item, why)
            if item is None:
                drops[why] += 1
            elif not far_props(item['prompt'])['two_kinds']:
                drops['join_not_joined'] += 1
            else:
                keep(item, item['kind'], MODE_CELLS[0])
        elif per[MODE_CELLS[0]] < per_cell:   # one joined try: the substitution ring only
            draws += 1
            item, why = mode.draft(tool, jex, None, rng, ctx)
            if item is None:
                drops[why] += 1
            elif not far_props(item['prompt'])['two_kinds']:
                drops['subst_not_joined'] += 1
            else:
                keep(item, host_kind[host.last], MODE_CELLS[0])
        if per[MODE_CELLS[1]] < per_cell:   # one not-joined try: rings 1-3, kinds round robin
            draws += 1
            kind = SP.SCORED[nj % len(SP.SCORED)]
            nj += 1
            item, why = mode.draft(tool, ex[kind], kind, rng, ctx)
            if item is None:
                drops[why] += 1
            elif far_props(item['prompt'])['two_kinds']:
                drops['swap_joined'] += 1
            else:
                keep(item, kind, MODE_CELLS[1])
        if draws >= shown + 1_000_000:
            shown = draws
            print(f'  {draws} draws: kept {per}', flush=True)
    stats = dict(draws=draws, drops=dict(drops), per=per, widen_kept=wst['kept'], widen_sha256=wst['sha256'], widen=wst,
                 complete=min(per.values()) >= per_cell)
    return rows, stats


def build_l8(rows_out, parent, probe, eval_rows, draw_cap=MODE_DRAW_CAP):
    build_ring_rows(rows_out, parent, probe, eval_rows, L8_SEED, L8_TAG, dict(widen_subst=L8_SUBST_DEPTH), print_subst_ring, draw_cap)


def build_l9(rows_out, parent, probe, eval_rows, draw_cap=MODE_DRAW_CAP):
    build_ring_rows(rows_out, parent, probe, eval_rows, L9_SEED, L9_TAG, dict(widen_join_whole=True), print_whole_join_ring, draw_cap)


def build_l10(rows_out, parent, probe, eval_rows, draw_cap=MODE_DRAW_CAP):
    build_ring_rows(rows_out, parent, probe, eval_rows, L10_SEED, L10_TAG, {}, None, draw_cap, join_last=True)


def l9_join_kinds(parent_chars):
    """The accepted (form, symbol) join kinds of L9's ring: widen.build with widen_join_whole, L9's seed and constants (as
    build-l9 builds them). -> [(form, symbol)], printed."""
    import json as _json
    from domain import mode
    from domain.far import widen
    cons = dict(_json.load(open(mode.CONST_PATH)), widen_join_whole=True)
    tool = sheet_tool
    helps = tool.help()
    ctx = dict(vchars=set(parent_chars), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    _, wst = widen.build(tool, helps, lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(f'{L9_SEED}-widen'), cons)
    jw = wst['join_whole']
    kinds = [(int(k.split(':', 1)[0]), k.split(':', 1)[1]) for k in jw['accepted']]
    print(f'L9 ring accepted join kinds (form:symbol), {len(kinds)}: {jw["accepted"]}; kept per kind {jw["kept"]}', flush=True)
    return kinds


def _is_call(t):
    """True when t is exactly one function call NAME(...) (its first bracket closes at the end)."""
    t = t.strip()
    if not re.fullmatch(r'[A-Z]+\(.*\)', t):
        return False
    d = 0
    for k, c in enumerate(t):
        d += (c == '(') - (c == ')')
        if d == 0 and c == ')':
            return k == len(t) - 1
    return False


def two_calls(prompt):
    """True when the formula (after ';' and '=') is two function calls side by side, bare or each in one pair of round brackets,
    joined by exactly one top-level symbol (a character that is not a letter, digit, space or bracket)."""
    body = prompt.partition(';')[2].strip().lstrip('=')
    depth, syms = 0, []
    for k, c in enumerate(body):
        depth += (c == '(') - (c == ')')
        if depth == 0 and not c.isalnum() and c not in ' ()':
            syms.append(k)
    if len(syms) != 1:
        return False
    def unit(t):
        t = t.strip()
        if t.startswith('(') and t.endswith(')') and _is_call(t[1:-1]):
            d = 0
            for k, c in enumerate(t):
                d += (c == '(') - (c == ')')
                if d == 0:
                    return k == len(t) - 1
        return _is_call(t)
    return unit(body[:syms[0]]) and unit(body[syms[0] + 1:])


class Census:
    """L10 census of join_last_draft attempts: keep-rate, drop reasons, and the far properties of the kept drafts."""

    def __init__(self):
        self.attempts, self.reasons = 0, Counter()
        self.kept, self.props = 0, Counter()
        self.layouts, self.arr, self.digit_runs, self.n_steps = Counter(), Counter(), Counter(), Counter()

    def add(self, item, why):
        from domain.far import widen
        self.attempts += 1
        if item is None:
            self.reasons[why] += 1
            return
        p = item['prompt']
        self.kept += 1
        self.props.update(k for k, v in far_props(p).items() if v)
        self.props.update(k for k, v in (('two_calls', two_calls(p)), ('fn_op_fn', fn_op_fn(p))) if v)
        self.layouts[widen.layout(p.partition(';')[2])] += 1
        self.arr[arrangement(p)] += 1
        self.digit_runs[len(re.findall(r'\d+', p))] += 1
        self.n_steps[len(item['steps'])] += 1

    def report(self):
        n = max(self.kept, 1)
        return dict(attempts=self.attempts, kept=self.kept, keep_rate=self.kept / max(self.attempts, 1),
                    reasons=dict(self.reasons.most_common()),
                    share={k: self.props[k] / n for k in ('grid_rows', 'max_range_cells', 'max_row_ref', 'two_kinds', 'two_calls', 'fn_op_fn')},
                    arrangement={a: self.arr[a] / n for a in ('plus', 'bracket-times', 'other')},
                    top_layouts=[(l, c, c / n) for l, c in self.layouts.most_common(15)], n_layouts=len(self.layouts),
                    digit_runs=dict(sorted(self.digit_runs.items())), n_steps=dict(sorted(self.n_steps.items())))

    def print(self):
        r = self.report()
        print(f'census: {r["attempts"]} join-last attempts, kept {r["kept"]} (keep-rate {100.0 * r["keep_rate"]:.2f}%)')
        print('  drop reasons (share of attempts): ' + ', '.join(f'{k} {100.0 * v / max(r["attempts"], 1):.2f}% ({v})' for k, v in r['reasons'].items()))
        print('  among kept: ' + ', '.join(f'{k}{"" if k in ("two_kinds", "two_calls", "fn_op_fn") else ">=5"} {100.0 * v:.1f}%' for k, v in r['share'].items()))
        print('  among kept, arrangement: ' + ', '.join(f'{a} {100.0 * v:.1f}%' for a, v in r['arrangement'].items()))
        print(f'  among kept, top 15 layouts of {r["n_layouts"]} (after the ";"):')
        for l, c, f in r['top_layouts']:
            print(f'    {100.0 * f:5.1f}% ({c:5d})  {l}')
        print('  among kept, digit runs per prompt: ' + ', '.join(f'{k}: {v}' for k, v in r['digit_runs'].items()))
        print('  among kept, n_steps: ' + ', '.join(f'{k}: {v}' for k, v in r['n_steps'].items()))


def census_l10(parent, attempts, out):
    """Stage census-l10: join_last_draft `attempts` times (ctx as build_l8_rows builds it, from the parent's chars)."""
    import torch
    from domain import mode
    cons = json.load(open(mode.CONST_PATH))
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    kinds = l9_join_kinds(ck['chars'])
    tool = sheet_tool
    helps = tool.help()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    from domain.far import joinlast
    rng = random.Random(f'{L10_SEED}-census')
    cen = Census()
    for n in range(attempts):
        item, why = joinlast.join_last_draft(tool, helps, kinds, rng, ctx)
        cen.add(item, why)
        if item is not None:
            ctx['seen'].add(item['prompt'])
        if (n + 1) % 2000 == 0:
            print(f'  {n + 1} attempts: kept {cen.kept}', flush=True)
    cen.print()
    rep = dict(cen.report(), seed=L10_SEED, kinds=[f'{f}:{s}' for f, s in kinds])
    with open(out, 'w') as f:
        json.dump(rep, f, indent=1)
    print('wrote', out)


def far_factors(prompt):
    """How many of grid_rows>=5, max_range_cells>=5, max_row_ref>=5 the prompt has (0-3)."""
    p = far_props(prompt)
    return sum(p[k] for k in ('grid_rows', 'max_range_cells', 'max_row_ref'))


def l12_pick(tool, helps, ctx, cons, seed_str):
    """L12: piece 1 drawn the way the v9 mode draws every practice example. Builds the widened rings exactly as build_mode_rows
    does (widen.build with ctx's accept, random.Random(seed_str)), then returns (pick, wst). pick(rng) -> (prompt, kind): kind
    round robin over SP.SCORED (a counter in the closure), then mode.pick_example(ex[kind], rng); pick.last_ring is the ring."""
    from domain import mode
    from domain.far import widen
    kinds = [h['kind'] for h in helps]
    rings, wst = widen.build(tool, helps, lambda p: mode.accept(tool, p, ctx)[2] is None, random.Random(seed_str), cons)
    ex = widen.by_kind(rings, kinds)
    assert all(k in ex for k in SP.SCORED), 'a scored kind is not on the help page'
    count = [0]

    def pick(rng):
        kind = SP.SCORED[count[0] % len(SP.SCORED)]
        count[0] += 1
        prompt, ring = mode.pick_example(ex[kind], rng)
        pick.last_ring = ring
        return prompt, kind
    pick.last_ring = None
    return pick, wst


class Census12(Census):
    """Census plus L12's columns: share of kept with two or more far factors; ring of piece 1 for attempts and for kept."""

    def __init__(self):
        super().__init__()
        self.far2 = 0
        self.ring_attempts, self.ring_kept = Counter(), Counter()

    def add(self, item, why, ring=None):
        super().add(item, why)
        self.ring_attempts[ring] += 1
        if item is not None:
            self.ring_kept[ring] += 1
            self.far2 += far_factors(item['prompt']) >= 2

    def report(self):
        r = super().report()
        n = max(self.kept, 1)
        na = max(self.attempts, 1)
        r['share']['two_or_more_far'] = self.far2 / n
        r['ring_attempts'] = {str(k): v / na for k, v in sorted(self.ring_attempts.items(), key=lambda kv: str(kv[0]))}
        r['ring_kept'] = {str(k): v / n for k, v in sorted(self.ring_kept.items(), key=lambda kv: str(kv[0]))}
        r['ring_kept_counts'] = {str(k): v for k, v in sorted(self.ring_kept.items(), key=lambda kv: str(kv[0]))}
        return r

    def print(self):
        super().print()
        r = self.report()
        print(f'  among kept: two or more far factors {100.0 * r["share"]["two_or_more_far"]:.1f}%')
        print('  piece-1 ring, share of attempts: ' + ', '.join(f'{k} {100.0 * v:.1f}%' for k, v in r['ring_attempts'].items()))
        print('  piece-1 ring, share of kept: ' + ', '.join(f'{k} {100.0 * v:.1f}% ({r["ring_kept_counts"][k]})' for k, v in r['ring_kept'].items()))


def census_l12(parent, attempts, out):
    """Stage census-l12: census-l10 with piece 1 from the v9 widened rings (l12_pick); seed as L10."""
    import torch
    from domain import mode
    cons = json.load(open(mode.CONST_PATH))
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    kinds = l9_join_kinds(ck['chars'])
    tool = sheet_tool
    helps = tool.help()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    pick, wst = l12_pick(tool, helps, ctx, cons, f'{L10_SEED}-widen')
    print(f'widen kept {wst["kept"]} sha {wst["sha256"][:12]}; per kind {wst["per_kind"]}', flush=True)
    from domain.far import joinlast
    rng = random.Random(f'{L10_SEED}-census')
    cen = Census12()
    for n in range(attempts):
        item, why = joinlast.join_last_draft(tool, helps, kinds, rng, ctx, pick=pick)
        cen.add(item, why, pick.last_ring)
        if item is not None:
            ctx['seen'].add(item['prompt'])
        if (n + 1) % 2000 == 0:
            print(f'  {n + 1} attempts: kept {cen.kept}', flush=True)
    cen.print()
    rep = dict(cen.report(), seed=L10_SEED, kinds=[f'{f}:{s}' for f, s in kinds], widen_sha256=wst['sha256'])
    with open(out, 'w') as f:
        json.dump(rep, f, indent=1)
    print('wrote', out)


def build_l12(rows_out, parent, probe, eval_rows, base_rows, draw_cap=MODE_DRAW_CAP, per_cell=PER_CELL):
    """Stage build-l12: PER_CELL joined rows (join-last, piece 1 from l12_pick; ids learn12-mode-two-NNNNN) + the 'mode-one'
    rows of base_rows (L9's file) copied unchanged. Excludes the probe, the L5 eval rows and the other exclusion files."""
    if os.path.exists(rows_out):
        raise SystemExit(f'refusing to overwrite {rows_out}')
    import torch
    from domain import mode
    from domain.mode import CONST_PATH
    cons = json.load(open(CONST_PATH))
    random.seed(L12_SEED)
    torch.manual_seed(L12_SEED)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    base = [r for r in load_jsonl(base_rows) if r['cell'] == MODE_CELLS[1]]
    assert len(base) == per_cell, f'{base_rows}: {len(base)} rows of cell {MODE_CELLS[1]}, wanted {per_cell}'
    exclude, missed = read_prompts([probe, eval_rows]), []
    for path in EXCLUDE_FILES[1:]:
        try:
            exclude |= read_prompts([path])
        except OSError:
            missed.append(path)
    if missed:
        print('NOT excluded (unreadable): ' + ', '.join(missed))
    kinds = l9_join_kinds(ck['chars'])
    tool = sheet_tool
    helps = tool.help()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    pick, wst = l12_pick(tool, helps, ctx, cons, f'{L12_SEED}-widen')
    from domain.far import joinlast, widen
    from custom_io.models import load_model
    torch.manual_seed(L12_SEED)
    m = load_model(parent).eval()
    rng = random.Random(f'{L12_SEED}-train')
    cen, drops, rows = Census12(), Counter(), []
    draws = 0
    while len(rows) < per_cell and draws < draw_cap:
        draws += 1
        item, why = joinlast.join_last_draft(tool, helps, kinds, rng, ctx, pick=pick)
        cen.add(item, why, pick.last_ring)
        if item is None:
            drops[why] += 1
            continue
        prompt = item['prompt']
        if not far_props(prompt)['two_kinds']:
            drops['join_not_joined'] += 1
            continue
        if prompt in exclude:
            ctx['seen'].add(prompt)
            drops['in_probe_or_panel'] += 1
            continue
        row, why = mode.make_row(m, 'domain_sheet', prompt, item['value'], item['steps'], cons, 'tool')
        if row is None:
            drops['make_row_' + why] += 1
            continue
        ctx['seen'].add(prompt)
        rows.append({'id': f'{L12_TAG}-{MODE_CELLS[0]}-{len(rows):05d}', 'kind': item['kind'], 'split': MODE_CELLS[0], 'cell': MODE_CELLS[0],
                     'prompt': prompt, 'answer': item['value'], 'n_steps': len(item['steps']), 'ring': item['ring']})
        if draws % 1_000_000 == 0:
            print(f'  {draws} draws: kept {len(rows)}', flush=True)
    complete = len(rows) >= per_cell
    print(f'excluded prompts: {len(exclude)}; draws {draws}; widen kept {wst["kept"]} sha {wst["sha256"][:12]}')
    print(f'widen tries {wst["tries"]}; per kind {wst["per_kind"]}')
    cen.print()
    print('drops:', dict(drops))
    print('per cell:', {MODE_CELLS[0]: len(rows), MODE_CELLS[1]: len(base)})
    if not complete:
        print(f'INCOMPLETE: found {len(rows)} joined rows (wanted {per_cell}) after {draws} draws; nothing written')
    if rows:
        lay = Counter(widen.layout(r['prompt'].partition(';')[2]) for r in rows)
        print(f'  joined rows: top 15 layouts of {len(lay)} (after the ";"):')
        for l, n in lay.most_common(15):
            print(f'    {100.0 * n / len(rows):5.1f}% ({n:5d})  {l}')
        arr = Counter(arrangement(r['prompt']) for r in rows)
        print('  joined rows per arrangement: ' + ', '.join(f'{a} {100.0 * arr[a] / len(rows):.1f}% ({arr[a]})' for a in ('plus', 'bracket-times', 'other')))
        f = sum(fn_op_fn(r['prompt']) for r in rows)
        print(f'  joined rows fn-op-fn (top level exactly two single calls joined by one + or one *): {100.0 * f / len(rows):.1f}% ({f})')
        print('  joined rows per ring: ' + str(dict(sorted(Counter(r['ring'] for r in rows).items(), key=lambda kv: str(kv[0])))) +
              '; per host kind: ' + str(dict(Counter(r['kind'] for r in rows))))
        fp = [far_props(r['prompt']) for r in rows]
        print('  joined rows far-factor shares: ' + ', '.join(f'{k}>=5 {100.0 * sum(p[k] for p in fp) / len(rows):.1f}%' for k in ('grid_rows', 'max_range_cells', 'max_row_ref')) +
              f', two or more far factors {100.0 * sum(far_factors(r["prompt"]) >= 2 for r in rows) / len(rows):.1f}%')
    allrows = rows + base
    for c in MODE_CELLS:
        rs = [r for r in allrows if r['split'] == c]
        print(f'  {c}: {len(rs)} rows; kinds {dict(Counter(r["kind"] for r in rs))}; rings {dict(sorted(Counter(r["ring"] for r in rs).items(), key=lambda kv: str(kv[0])))}')
    props = [far_props(r['prompt']) for r in allrows]
    for k in ('grid_rows', 'max_range_cells', 'max_row_ref', 'two_kinds'):
        print(f'  share {k}{">=5" if k != "two_kinds" else ""}: ' +
              ', '.join(f'{c} {100.0 * sum(p[k] for p, r in zip(props, allrows) if r["split"] == c) / max(sum(r["split"] == c for r in allrows), 1):.1f}%' for c in MODE_CELLS) +
              f', all {100.0 * sum(p[k] for p in props) / max(len(allrows), 1):.1f}%')
    if not complete:
        raise SystemExit(1)
    assert not {r['prompt'] for r in rows} & exclude and len({r['prompt'] for r in allrows}) == len(allrows)
    tmp = rows_out + '.tmp'
    with open(tmp, 'w') as fh:
        for r in allrows:
            fh.write(json.dumps(r) + '\n')
    os.rename(tmp, rows_out)
    print(f'wrote {len(allrows)} rows to {rows_out}')
    print('sha256', sha256_file(rows_out))


def print_subst_ring(w):
    sb = w['subst']
    print(f'subst ring: accepted layouts {sb["accepted"]}; depth {sb["depth"]}; value pieces {sb["vq"]}; top 20 layouts (kept):')
    for lay, n in sb['top_layouts']:
        print(f'    {n:5d}  {lay}')


def print_whole_join_ring(w):
    jw = w['join_whole']
    print('whole piece of each help example:')
    for prompt, piece in jw['wholes'].items():
        print(f'    {prompt!r} -> {piece!r}' + ('' if piece else '  (no whole piece: left out of host and Q choices)'))
    print(f'whole join ring: {len(jw["accepted"])} accepted join kinds (form:symbol), tries {jw["tries"]}; kept per kind:')
    for k, n in jw['kept'].items():
        print(f'    {k!r}: {n}' + ('' if k in jw['accepted'] else '  (not accepted)'))


def build_ring_rows(rows_out, parent, probe, eval_rows, seed, tag, cons_extra, print_ring, draw_cap=MODE_DRAW_CAP, join_last=False):
    if os.path.exists(rows_out):
        raise SystemExit(f'refusing to overwrite {rows_out}')
    import torch
    from custom_io.models import load_model
    from domain.far import widen
    from domain.mode import CONST_PATH
    cons = dict(json.load(open(CONST_PATH)), **cons_extra)
    random.seed(seed)
    torch.manual_seed(seed)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(seed)
    m = load_model(parent).eval()
    exclude, missed = read_prompts([probe, eval_rows]), []
    for path in EXCLUDE_FILES[1:]:
        try:
            exclude |= read_prompts([path])
        except OSError:
            missed.append(path)
    if missed:
        print('NOT excluded (unreadable): ' + ', '.join(missed))
    kinds, cen = None, None
    if join_last:   # L10: the joined rows are join-last drafts; the join kinds are L9's accepted ones
        kinds, cen = l9_join_kinds(ck['chars']), Census()
    rows, st = build_l8_rows(m, ck['chars'], cons, exclude, seed=seed, tag=tag, draw_cap=draw_cap, join_kinds=kinds, census=cen)
    w = st['widen']
    print(f'excluded prompts: {len(exclude)}; draws {st["draws"]}; widen kept {st["widen_kept"]} sha {st["widen_sha256"][:12]}')
    print(f'widen tries {w["tries"]}; per kind {w["per_kind"]}')
    if print_ring:
        print_ring(w)
    if cen is not None:
        cen.print()
    print('drops:', st['drops'])
    print('per cell:', st['per'])
    if not st['complete']:
        print(f'INCOMPLETE: found {st["per"]} (wanted {PER_CELL} each) after {st["draws"]} draws; nothing written')
    two = [r for r in rows if r['split'] == MODE_CELLS[0]]
    if two:
        lay = Counter(widen.layout(r['prompt'].partition(';')[2]) for r in two)
        print(f'  joined rows: top 15 layouts of {len(lay)} (after the ";"):')
        for l, n in lay.most_common(15):
            print(f'    {100.0 * n / len(two):5.1f}% ({n:5d})  {l}')
        arr = Counter(arrangement(r['prompt']) for r in two)
        print('  joined rows per arrangement: ' + ', '.join(f'{a} {100.0 * arr[a] / len(two):.1f}% ({arr[a]})'
                                                           for a in ('plus', 'bracket-times', 'other')))
        f = sum(fn_op_fn(r['prompt']) for r in two)
        print(f'  joined rows fn-op-fn (top level exactly two single calls joined by one + or one *): {100.0 * f / len(two):.1f}% ({f})')
        print('  joined rows per ring: ' + str(dict(sorted(Counter(r['ring'] for r in two).items()))) + '; per host kind: ' + str(dict(Counter(r['kind'] for r in two))))
    for c in MODE_CELLS:
        rs = [r for r in rows if r['split'] == c]
        print(f'  {c}: {len(rs)} rows; kinds {dict(Counter(r["kind"] for r in rs))}; rings {dict(sorted(Counter(r["ring"] for r in rs).items()))}')
    props = [far_props(r['prompt']) for r in rows]
    for k in ('grid_rows', 'max_range_cells', 'max_row_ref', 'two_kinds'):
        print(f'  share {k}{">=5" if k != "two_kinds" else ""}: ' +
              ', '.join(f'{c} {100.0 * sum(p[k] for p, r in zip(props, rows) if r["split"] == c) / max(sum(r["split"] == c for r in rows), 1):.1f}%' for c in MODE_CELLS) +
              f', all {100.0 * sum(p[k] for p in props) / max(len(rows), 1):.1f}%')
    if not st['complete']:
        raise SystemExit(1)
    assert not {r['prompt'] for r in rows} & exclude and len({r['prompt'] for r in rows}) == len(rows)
    tmp = rows_out + '.tmp'
    with open(tmp, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    os.rename(tmp, rows_out)
    print(f'wrote {len(rows)} rows to {rows_out}')
    print('sha256', sha256_file(rows_out))


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_sets(train_rows, cells='l1', fit_seed=SEED, v3_path=V3_PANEL, l3_path=L3_EVAL_ROWS, l5_path=L5_EVAL_ROWS, probe_path=None):
    """The scored cells: name -> rows (each row's id made unique across cells; the row's split is the cell name).
    cells 'l1': F4-two, F0-near, F2b-rows, fit (L1, unchanged). cells 'all' (L2): every probe split (scored kinds), fit,
    and the sealed sheet.v3 panel (scored kinds) as v3-near / v3-far (scoring only). cells 'l3': S, HP, HO, HPO (from the L3 eval
    file), probe F0-near and F4-two, fit. cells 'l4': everything in 'all' plus S, HP, HO, HPO.
    cells 'l5': S5, S, HP, HO, HPO (from the L5 eval file), probe F0-near and F4-two, fit.
    cells 'l8': S5, S, HP, HO, HPO, every probe cell, F4-plus / F4-times (F4-two without / with ')*('), fit; no v3 panel."""
    assert cells in ('l1', 'all', 'l3', 'l4', 'l5', 'l8'), cells
    probe = [r for r in load_jsonl(probe_path or SP.PROBE) if r['kind'] in SP.SCORED]
    names = {'l1': ('F4-two', 'F0-near', 'F2b-rows'), 'all': PROBE_CELLS, 'l4': PROBE_CELLS, 'l3': ('F0-near', 'F4-two'), 'l5': ('F0-near', 'F4-two'), 'l8': PROBE_CELLS}[cells]
    sets = {}
    if cells in ('l3', 'l4'):
        l3 = load_jsonl(l3_path)
        sets = {c: [r for r in l3 if r['split'] == c] for c in L3_CELLS}
        assert all(len(v) == L3_EVAL_N for v in sets.values()), {k: len(v) for k, v in sets.items()}
    if cells in ('l5', 'l8'):
        l5 = load_jsonl(l5_path)
        sets = {c: [r for r in l5 if r['split'] == c] for c in L5_CELLS}
        assert all(len(v) == L5_EVAL_N for v in sets.values()), {k: len(v) for k, v in sets.items()}
    sets.update({c: [dict(r, split=c) for r in probe if r['split'] == c] for c in names})
    if cells == 'l8':
        f4 = [r for r in probe if r['split'] == 'F4-two']
        sets['F4-plus'] = [dict(r, id='plus-' + r['id'], split='F4-plus') for r in f4 if ')*(' not in r['prompt']]
        sets['F4-times'] = [dict(r, id='times-' + r['id'], split='F4-times') for r in f4 if ')*(' in r['prompt']]
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


def score_step(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False):
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
    harm = harm_fn(path, step) if harm_fn else None   # before the checkpoint is deleted
    with open(os.path.join(out, 'scores.jsonl'), 'a') as f:
        rec = {'arm': arm, 'step': step, 'cells': cells, 'secs': secs, 'train_secs': round(t_train, 1)}
        rec.update(extra or {})
        if harm is not None:
            rec['harm'] = harm
        f.write(json.dumps(rec) + '\n')
    print(f'{arm} step {step}: ' + ' '.join(f'{k} {v["pct"]:.1f}' for k, v in cells.items()) + f' (score {secs}s)', flush=True)
    if keep:   # --keep-final: the last step's checkpoint stays
        return
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


def check_guard_args(arm, guard, guard_src, energy=0.99, every=500, kl_rows=None, kl_weight=None, soft=None):
    """The guard is for arm LB only and needs its source folder; refuse otherwise, before any work.
    kl_rows / kl_weight (None = not given) are for --guard kfsoft only; kfsoft needs both, rows >= 1 and weight > 0.
    soft (None = not given, 1 is used) is the graded-mask softness of --guard kfsoft (L13: 10), > 0, or 'hard' (L14: the hard
    mask, kf.factors soft=None, with the KL replay)."""
    if guard != 'kfsoft' and (kl_rows is not None or kl_weight is not None or soft is not None):
        raise SystemExit('--kl-replay-rows / --kl-weight / --guard-soft apply to --guard kfsoft only')
    if soft is not None and soft != 'hard' and soft <= 0:
        raise SystemExit("--guard-soft must be > 0 or 'hard'")
    if not guard:
        return
    if arm != 'LB':
        raise SystemExit('--guard applies to arm LB only')
    if guard == 'kfsoft' and (kl_rows is None or kl_weight is None or kl_rows < 1 or kl_weight <= 0):
        raise SystemExit('--guard kfsoft needs --kl-replay-rows >= 1 and --kl-weight > 0')
    if guard not in ('kf', 'kfsoft'):
        raise SystemExit(f'unknown guard {guard}')
    if not guard_src or not os.path.isdir(guard_src):
        raise SystemExit('--guard needs --guard-src DIR (the folder holding mainbrain/)')
    if not 0 < energy < 1 or every < 1:
        raise SystemExit('--guard-energy must be in (0,1) and --guard-every >= 1')


def check_diary_data(guard, data, cache):
    """--diary-data is read only by the guard's diary build: refuse it without --guard, and refuse a given folder with no train.jsonl
    before any work (unless an existing --diary-cache means the folder is never read). The default path is not checked, so the
    default behaviour is unchanged."""
    if not guard:
        if data != DIARY_DATA:
            raise SystemExit('--diary-data applies to --guard only')
        return
    if data != DIARY_DATA and not (cache and os.path.exists(cache)) and not os.path.isfile(os.path.join(data, 'train.jsonl')):
        raise SystemExit(f'--diary-data {data}: no train.jsonl there (and no existing --diary-cache)')


def addon_size(arm, cons, rank=None, alpha=None):
    """(rank, alpha) for arm LA: the mode's constants unless overridden. LB has no add-on: overrides are refused."""
    if arm != 'LA':
        if rank is not None or alpha is not None:
            raise SystemExit('--addon-rank/--addon-alpha apply to arm LA only')
        return None, None
    return (cons['addon_rank'] if rank is None else rank), (cons['addon_alpha'] if alpha is None else alpha)


DEV_IN_DIST = '/tmp/claude-0/-home-user-learner/fb790cc1-3a66-56ad-bced-917dde5a53d7/scratchpad/sk200k/dev/in_dist.jsonl'
GUARD_COMMIT = '5ca34e99938981a6448ba298a1a2127c468a46b0'
GUARD_COMMIT_SOFT = 'c823e4b9a49c477751f6ad95e764097258b1aece'   # --guard kfsoft: Main brain's shipped guard (graded mask + KL replay)
GUARD_SOFT_FILES = ('kf.py', 'gp.py', 'klreplay.py', 'fullrun.py')
KL_REPLAY_SEED = SEED + 11   # RandomState drawing the diary rows for the KL replay, one draw of --kl-replay-rows per update
GUARD_CONSTANTS = 'constants-kf99n-lr3e4.json'   # in the guard source folder's mainbrain/: the s200 sheet run's constants (diary 4096, check 512)
DIARY_DATA = '/tmp/claude-0/-home-user-learner/fb790cc1-3a66-56ad-bced-917dde5a53d7/scratchpad/sk200k'
DIARY_SEED = 200
DIARY_LOG = '/mnt/project-files/main-brain/runs/sheet-s200-kf99n/log.jsonl'


def make_harm_fn(parent, dev, out):
    """-> f(ckpt_path, step) -> dict: old-skill harm of the checkpoint against the parent on the DEV in_dist rows (domain/harm.py).
    The parent's hits are computed once and cached to OUT/parent-hits.json."""
    from custom_io.data import load_rows
    from domain import harm
    rows = load_rows(dev)
    cache = os.path.join(out, 'parent-hits.json')
    t0 = time.time()
    if os.path.exists(cache):
        parent_hits = json.load(open(cache))['hits']
    else:
        parent_hits, acc = harm.in_dist_hits(parent, rows)
        with open(cache, 'w') as f:
            json.dump({'parent': parent, 'dev': dev, 'n': len(rows), 'exact': acc, 'ids': [r['id'] for r in rows], 'hits': parent_hits}, f)
    print(f'harm: parent hits on {len(rows)} in_dist rows ({time.time() - t0:.1f}s)', flush=True)

    def fn(path, step):
        t = time.time()
        hits, _ = harm.in_dist_hits(path, rows)
        h = harm.harm_measure(parent_hits, hits, rows, 5.0, 1.5)
        res = {'in_dist_a': round(h['in_dist_a'], 2), 'in_dist_b': round(h['in_dist_b'], 2), 'in_dist_drop': round(h['in_dist_drop'], 2),
               'fired': h['fired'], 'passes': bool(h['passes']), 'n': len(rows),
               'family_drops': {f: round(v['drop'], 1) for f, v in h['families'].items()}, 'secs': round(time.time() - t, 1)}
        print(f'harm step {step}: in_dist {res["in_dist_a"]} -> {res["in_dist_b"]} (drop {res["in_dist_drop"]}), '
              f'fired {res["fired"]}, {"PASS" if res["passes"] else "FAIL"}, n {res["n"]}', flush=True)
        return res
    return fn


def load_guard(src):
    """Put the guard source folder first on sys.path; -> (kf, gp) from it."""
    import importlib
    import sys
    sys.path.insert(0, os.path.abspath(src))
    for name in ('mainbrain.kf', 'mainbrain.gp', 'mainbrain'):
        sys.modules.pop(name, None)
    kf, gp = importlib.import_module('mainbrain.kf'), importlib.import_module('mainbrain.gp')
    for mod in (kf, gp):
        assert os.path.abspath(mod.__file__).startswith(os.path.abspath(src)), (mod.__file__, src)
    return kf, gp


def verify_guard_commit(src, commit=GUARD_COMMIT_SOFT, files=GUARD_SOFT_FILES):
    """Check the guard source folder's mainbrain/ files are byte-identical to `commit` (git blob hashes, looked up in this repo).
    -> 'verified' when all match; 'unverified (...)' when git cannot resolve the commit here; a mismatch refuses."""
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    for f in files:
        path = os.path.join(src, 'mainbrain', f)
        try:
            mine = subprocess.run(['git', 'hash-object', path], capture_output=True, text=True, check=True).stdout.strip()
            want = subprocess.run(['git', '-C', here, 'rev-parse', f'{commit}:mainbrain/{f}'], capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, OSError) as e:
            return f'unverified ({f}: {type(e).__name__})'
        if mine != want:
            raise SystemExit(f'guard source {path} does not match commit {commit[:9]} ({mine[:9]} != {want[:9]})')
    return 'verified'


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def compare_diary(diary, log_path, cmp):
    """Fill cmp with how the diary's prompts/answers compare with the main-brain run's day-0 diary rows in log_path.
    log_path None / 'none' -> 'skipped'; a missing file -> ref_n None."""
    if log_path is None or str(log_path).lower() == 'none':
        cmp['log'] = None
        cmp['compare'] = 'skipped'
    elif os.path.exists(log_path):
        ref = [(r['prompt'], r['answer']) for r in load_jsonl(log_path) if r.get('event') == 'row' and r.get('kind') == 'diary' and r.get('day') == 0]
        mine = [(r['prompt'], r['answer']) for r in diary]
        rp, mp = {p for p, _ in ref}, {p for p, _ in mine}
        ra = dict(ref)
        cmp.update(ref_n=len(ref), same_prompt_set=len(rp & mp), only_mine=len(mp - rp), only_ref=len(rp - mp),
                   same_position=sum(a[0] == b[0] for a, b in zip(ref, mine)),
                   same_answer_on_shared=sum(ra.get(p) == a for p, a in mine if p in rp))
    else:
        cmp['ref_n'] = None
    return cmp


def build_parent_diary(m, ck, src, out, data=DIARY_DATA, seed=DIARY_SEED, log_path=DIARY_LOG, cache=None):
    """The parent's own answers on training prompts, rebuilt as domain/mode.py main does (pool of the data folder's train file,
    shuffled by Random(f'{seed}-diary'), the first `check` held out, then build_diary). Diary size/check from the guard
    source's kf99n constants (the s200 sheet run's). Written to OUT/diary.jsonl; prompts compared with the run's diary rows
    (log_path 'none' skips the comparison). cache: an existing diary.jsonl is loaded instead of rebuilding (nothing else read).
    -> (diary rows, compare dict; has 'sha256' of the diary file used)."""
    if cache and os.path.exists(cache):
        diary = load_jsonl(cache)
        cmp = {'n': len(diary), 'cache': cache, 'sha256': file_sha256(cache), 'log': log_path}
        compare_diary(diary, log_path, cmp)
        with open(os.path.join(out, 'diary-compare.json'), 'w') as f:
            json.dump(cmp, f, indent=1)
        print(f'diary: loaded {len(diary)} rows from {cache} (sha256 {cmp["sha256"][:12]}); {cmp}', flush=True)
        return diary, cmp
    from domain import mode
    cons = dict(json.load(open(os.path.join(src, 'mainbrain', GUARD_CONSTANTS))))
    helps = sheet_tool.help()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    pool = []
    with open(mode.guard(os.path.join(data, 'train.jsonl'))) as f:
        for line in f:
            p = json.loads(line)['prompt']
            if len(p) <= mode.MAX_PROMPT and set(p) <= ctx['vchars']:
                pool.append(p)
    pool = list(dict.fromkeys(pool))
    random.Random(f'{seed}-diary').shuffle(pool)
    t0 = time.time()
    events = []
    diary, check, pos = mode.build_diary(m, pool, cons, ctx, lambda ev, **kw: events.append((ev, kw)), lambda **kw: None)
    secs = round(time.time() - t0, 1)
    dpath = os.path.join(out, 'diary.jsonl')
    with open(dpath, 'w') as f:
        for r in diary:
            f.write(json.dumps(r) + '\n')
    cmp = {'n': len(diary), 'check': len(check), 'scanned': pos, 'secs': secs, 'log': log_path, 'sha256': file_sha256(dpath)}
    compare_diary(diary, log_path, cmp)
    with open(os.path.join(out, 'diary-compare.json'), 'w') as f:
        json.dump(cmp, f, indent=1)
    print(f'diary: built {len(diary)} rows (check {len(check)}, scanned {pos}) in {secs}s; vs {log_path}: {cmp}', flush=True)
    return diary, cmp


def apply_run_seed(seed):
    """R1 (pairing-map decisions U2): point the train run's seed at `seed`. Sets the module SEED and KL_REPLAY_SEED together,
    before train() consumes either: KL_REPLAY_SEED is derived from SEED at import time (module level, above), so a patch of
    SEED alone would silently leave the KL replay stream at the shipped SEED + 11, shared across all seeds. Streams that read
    the module SEED at call time follow the run seed: torch.manual_seed(SEED) at both sites, batch_order(..., SEED) (data
    order), AddOn(..., SEED) (arm LA only), and through torch.initial_seed() at model construction the model's ans_drill
    stream. Held streams do not move: the eval fit seed is chosen in train() before this is called, the diary pool shuffle is
    random.Random('200-diary'), and the build-time streams hang off their own constants (93501 / 93701 / 93702)."""
    global SEED, KL_REPLAY_SEED
    SEED = seed
    KL_REPLAY_SEED = seed + 11


def install_first_call_weight(m, weight):
    """R1 (pairing-map decisions U3): replace m.call_loss and m.span_terms with copies of Tool.call_loss and
    Tool.span_terms (custom_io/models/tool.py) in which the FIRST call's losses carry `weight`, renormalised per trace
    by the trace's inverse mean call weight, renorm = n_calls / (weight + n_calls - 1) (the pairing map: 'loss
    renormalised per trace to the uniform-weight trace mean'; a trace whose calls all lost the same amount contributes
    exactly its uniform-weight loss, and the effective learning rate is unchanged across arms). Weighted: round 0's op
    CE and operand-string NLL in call_loss, and round 0's span_call contribution in span_terms — the whole of the first
    call's loss. In call_loss every round carries renorm and round 0 carries renorm x weight; in span_terms ONLY round
    0 changes (fac0 = renorm x weight there) — later span rounds, the stop term, span_share and the returned Mn (which
    span_loss turns into span_ans) are the shipped computations, unweighted, and span_ans itself is never weighted. The
    mode / word / gen terms are not call losses and are untouched. A row with no call is untouched: its round-0 op CE
    predicts NOOP, which is not a first call, and all its span rounds are off. hits / tot are computed from the
    unweighted quantities, exactly as shipped. At weight 1.0 every factor is exactly 1.0 and the arithmetic is the
    shipped arithmetic in the shipped order, so the result is bit-identical to the unmodified trainer (train() still
    installs this only for weight != 1.0)."""
    import torch
    import torch.nn.functional as F
    from custom_io.models.ledger import COMM
    from custom_io.models.tool import CELLS

    def factors(g):
        """Per trace: (renorm, first) — renorm = n_calls / (weight + n_calls - 1), the inverse mean call weight;
        first = `weight` on rows whose round 0 is a real call, else 1."""
        n_calls = (g['op'] > 0).sum(1)
        renorm = torch.where(n_calls > 0, n_calls.float() / (weight + (n_calls - 1).float()),
                             torch.ones_like(n_calls, dtype=torch.float32))   # per trace: 1 / mean call weight
        first = torch.where(g['op'][:, 0] > 0, float(weight), 1.0)   # rows whose round 0 is a real call
        return renorm, first

    def call_loss(steps, g, B):
        dev = g['op'].device
        w_row = torch.where(g['has'], 1.0, m.w_noop)
        comm = torch.isin(g['op'], torch.tensor(COMM, device=dev))
        renorm, first = factors(g)
        lop = lcall = 0.0
        hits = tot = 0
        sc = lambda lp, tg: (lp.gather(2, tg.clamp(min=0)[..., None])[..., 0] * (tg >= 0)).sum(1)
        for s, st in enumerate(steps):
            fac = renorm * first if s == 0 else renorm
            lg, p = st[0].float(), st[1]
            lop = lop + (F.cross_entropy(lg, g['op'][:, s], reduction='none') * w_row * fac).mean()
            lp = torch.log(p + 1e-6)
            la, lb = lp[:, :CELLS], lp[:, CELLS:]
            ta, tb = g['ca'][:, s], g['cb'][:, s]
            lab, lba = sc(la, ta) + sc(lb, tb), sc(la, tb) + sc(lb, ta)
            nll = -torch.where(comm[:, s], torch.logaddexp(lab, lba), lab)
            lcall = lcall + (nll * (g['op'][:, s] > 0) * fac).sum() / B
            hits += ((lg.argmax(-1) == g['op'][:, s]) & g['has']).sum()
            tot += g['has'].sum()
        return lop, lcall, hits, tot

    def span_terms(o, g, batch, B):
        """A copy of Tool.span_terms (custom_io/models/tool.py) with one change: round 0's span_call contribution
        carries fac0 = renorm x first, the same per-trace factor round 0's call terms carry in call_loss above.
        Everything else — later rounds, the stop term, span_share, the returned Mn — is the shipped computation,
        unweighted. Reached exactly where the shipped method is: Tool.loss calls span_loss, which calls
        self.span_terms (and ToolH1's loss calls self.span_terms directly), so the instance attribute is picked up."""
        dev, T = batch['prompt_ids'].device, batch['prompt_ids'].shape[1]
        Ma, Mb, Mn, (cs, ts, ys) = m.span_gold(batch['rows'], T, o['le'], o['K'], g.get('rowg'))
        Ma, Mb, Mn = (torch.from_numpy(x).to(dev) for x in (Ma, Mb, Mn))
        lse = lambda lg, M: torch.logsumexp(lg.masked_fill(~M, -1e9), -1) - torch.logsumexp(lg, -1)
        side = lambda lg, gl, M: torch.where(M.any(-1), F.logsigmoid(gl) + lse(lg, M), F.logsigmoid(-gl))
        comm = torch.isin(g['op'], torch.tensor(COMM, device=dev))
        renorm, first = factors(g)
        fac0 = renorm * first
        lsc, n_span, n_side = 0.0, 0, 0
        for s, st in enumerate(o['steps']):
            sp, ma, mb, on = st[2], Ma[:, s], Mb[:, s], g['op'][:, s] > 0
            lab = side(sp['la'], sp['ga'], ma) + side(sp['lb'], sp['gb'], mb)
            lba = side(sp['la'], sp['ga'], mb) + side(sp['lb'], sp['gb'], ma)
            nll = -torch.where(comm[:, s] & (ma != mb).any(-1), torch.logaddexp(lab, lba), lab)     # same string twice: one order
            lsc = lsc + ((nll * on * fac0).sum() if s == 0 else (nll * on).sum()) / B
            n_span += int((ma.any(-1) & on).sum() + (mb.any(-1) & on).sum()); n_side += 2 * int(on.sum())
        if cs:
            lstop = F.binary_cross_entropy_with_logits(m.stop_logit(torch.tensor(cs, device=dev), torch.tensor(ts, device=dev)),
                                                       torch.tensor(ys, device=dev))
        else:
            lstop = torch.zeros((), device=dev)
        return dict(span_call=lsc, stop=lstop, span_share=n_span / max(n_side, 1)), Mn

    m.call_loss = call_loss
    m.span_terms = span_terms
    return call_loss


def kl_replay_loss(m, parent, weight, kls, klreplay):
    """Instance-level loss for --guard kfsoft. Same logic as klreplay.wrap (split the batch by row source 'diary'; the plain loss
    when not training / no grad / no diary or no new rows; tuple shape and aux 'replay_kl' kept; every KL appended to kls), but
    combined as Main brain's answer (L11) says: plain loss on the new rows at weight 1 + weight x klreplay.replay_kl's KL
    (the mean over the diary rows), NOT wrap's (n_new/B, n_rep/B) split. replay_kl itself is Main brain's (c823e4b9a)."""
    plain = m.loss

    def part(b, idx):
        import torch
        t = torch.tensor(idx)
        return {k: (v[t] if torch.is_tensor(v) else [v[i] for i in idx]) for k, v in b.items()}

    def loss(b):
        import torch
        rows = b['rows']
        ri = [i for i, r in enumerate(rows) if r.get('source') == 'diary']
        rs = set(ri)
        ni = [i for i in range(len(rows)) if i not in rs]
        if not m.training or not torch.is_grad_enabled() or not ri or not ni:
            return plain(b)
        out_n = plain(part(b, ni))
        kl, _ = klreplay.replay_kl(m, parent, part(b, ri))
        kls.append(float(kl.detach()))
        if isinstance(out_n, tuple):
            aux = out_n[1]
            if isinstance(aux, dict):
                aux = dict(aux, replay_kl=float(kl.detach()))
            return (out_n[0] + weight * kl, aux) + tuple(out_n[2:])
        return out_n + weight * kl
    return loss


# C8 (opt-in, --log-update-rms): grad-norm and per-group update-size logging. Mirrors custom_io/train.py's update_group / GradStats /
# snapshot_params / update_rms. Copied, not imported, on purpose: the far trainer is locked at claude/project-thread-94a956, whose
# custom_io/train.py does not carry the C8 draft, so an import would tie the locked trainer to an unreviewed file. Keep the two in step.
# Read-only: every function runs under no_grad, draws no random numbers and never writes a param, a grad or optimizer state.
GRAD_CLIP = 1.0   # train()'s clip_grad_norm_ max norm; GradStats counts against the same value


def update_group(name):
    """Parameter name -> its module path cut after the first numeric (layer index) component, else to two components:
    'blocks.0.qkv.weight' -> 'blocks.0', 'reader.blocks.1.conv.weight' -> 'reader.blocks.1', 'tok.weight' -> 'tok'."""
    path = name.split('.')[:-1]
    i = next((k for k, c in enumerate(path) if c.isdigit()), None)
    return '.'.join(path[:i + 1] if i is not None else path[:2]) or name


def sig6(x):
    return float(f'{x:.6g}')


class GradStats:
    """Grad norms over one log interval -> mean, max and the fraction of steps above `clip`. Same as custom_io.train.GradStats."""
    def __init__(self, clip):
        self.clip, self.n = clip, 0

    def add(self, gn):
        import torch
        with torch.no_grad():
            gn = gn.detach().float()
            z = torch.zeros_like(gn)
            if not self.n:
                self.sum, self.max, self.fired = z, z, z.clone()
            self.sum, self.max, self.fired = self.sum + gn, torch.maximum(self.max, gn), self.fired + (gn > self.clip).float()
            self.n += 1

    def pop(self):
        import torch
        s, m, f = torch.stack([self.sum, self.max, self.fired]).tolist()
        n, self.n = self.n, 0
        return dict(grad_norm_mean=sig6(s / n), grad_norm_max=sig6(m), clip_frac=sig6(f / n))


def snapshot_params(named):
    """Copies of the trainable tensors in `named` (an iterable of (name, tensor)) as they are now: [(name, tensor, copy)]."""
    import torch
    with torch.no_grad():
        return [(n, p, p.detach().clone()) for n, p in named if p.requires_grad]


def update_rms(snap):
    """After opt.step(): rms(delta) / rms(param before) over everything snapshotted and per update_group; a group whose before-norm is 0
    is skipped. -> (all, {group: ratio}). Same as custom_io.train.update_rms."""
    import torch
    with torch.no_grad():
        ss = {}
        for n, p, b in snap:
            ss.setdefault(update_group(n), []).append(torch.stack([torch.linalg.vector_norm(p.detach() - b, dtype=torch.float64).square(),
                                                                   torch.linalg.vector_norm(b, dtype=torch.float64).square()]))
        ss = {g: torch.stack(v).sum(0) for g, v in ss.items()}
        vals = dict(zip(ss, torch.stack(list(ss.values())).tolist()))
    ratio = lambda d, b: sig6(math.sqrt(d / b)) if b > 0 else None
    tot = [sum(v[i] for v in vals.values()) for i in (0, 1)]
    return ratio(*tot), {g: ratio(d, b) for g, (d, b) in vals.items() if b > 0}


class Guarded:
    """The kf guard around one base AdamW: measure F (kf.factors of kfac_stats, norm 'example'), freeze what cannot be projected,
    wrap as kf.KFOptimizer. refresh() re-measures on the current weights and rebuilds only the wrapper (same base, same state)."""

    def __init__(self, kf, gp, m, diary, energy, make_base, soft=None):
        self.kf, self.gp, self.m, self.diary, self.energy, self.soft = kf, gp, m, diary, energy, soft
        self.measure_secs, self.measures = 0.0, 0
        F = self.measure()
        self.frozen = gp.freeze_unprojected(m)
        self.base = make_base()   # after freezing
        self.opt = kf.KFOptimizer(m, self.base, F)

    def measure(self):
        t = time.time()
        for p in self.m.parameters():
            p.requires_grad_(True)
        stats = self.kf.kfac_stats(self.m, self.diary, norm='example')
        F, info = self.kf.factors(stats, self.energy) if self.soft is None else self.kf.factors(stats, self.energy, soft=self.soft)
        self.gp.freeze_unprojected(self.m)   # kfac_stats switched to eval mode and set requires_grad
        self.m.train()
        self.info = info
        self.measures += 1
        dt = time.time() - t
        self.measure_secs += dt
        print(f'guard: measured F #{self.measures} in {dt:.1f}s; mean free share {np.mean([v["free_share"] for v in info.values()]):.4f}', flush=True)
        return F

    def refresh(self):
        self.opt = self.kf.KFOptimizer(self.m, self.base, self.measure())
        return self.opt


def train(arm, updates, threads, out, steps, parent=PARENT, train_path=TRAIN_ROWS, log_every=100, cells='l1',
          addon_rank=None, addon_alpha=None, harm_steps=(), dev=DEV_IN_DIST, keep_final=False, guard=None, guard_energy=0.99,
          guard_every=500, guard_src=None, probe=None, eval_rows=None, diary_compare=DIARY_LOG, diary_cache=None,
          kl_replay_rows=None, kl_weight=None, guard_soft=None, seed=None, first_call_weight=1.0, log_update_rms=False,
          diary_data=DIARY_DATA):
    import torch
    from custom_io.data import Dataset, collate, to_device
    from custom_io.models import load_model
    from domain.mode import AddOn, CONST_PATH, make_opt
    torch.set_num_threads(threads)
    assert arm in ('LA', 'LB')
    assert seed is None or isinstance(seed, int), seed
    assert first_call_weight > 0, first_call_weight
    assert steps and max(steps) <= updates and min(steps) >= 0, (steps, updates)
    cons = json.load(open(CONST_PATH))
    rank, alpha = addon_size(arm, cons, addon_rank, addon_alpha)
    extra = {'addon_rank': rank, 'addon_alpha': alpha}
    harm_steps = set(harm_steps)
    assert harm_steps <= set(steps), ('--harm-steps must be among --steps', sorted(harm_steps), sorted(steps))
    check_guard_args(arm, guard, guard_src, guard_energy, guard_every, kl_replay_rows, kl_weight, guard_soft)
    check_diary_data(guard, diary_data, diary_cache)
    soft_value = (1 if guard_soft is None else None if guard_soft == 'hard' else
                  int(guard_soft) if float(guard_soft).is_integer() else float(guard_soft))   # 1 = L11; None = the hard mask (L14)
    soft_guard = guard == 'kfsoft'
    guard_commit = GUARD_COMMIT_SOFT if soft_guard else GUARD_COMMIT
    commit_check = verify_guard_commit(guard_src) if soft_guard else None
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, 'scores.jsonl')):
        raise SystemExit(f'refusing to reuse {out}: scores.jsonl exists')
    train_rows = load_jsonl(train_path)
    fit_seed = L8_SEED if cells == 'l8' else L5_SEED if cells == 'l5' else L4_SEED if cells == 'l4' else L3_SEED if cells == 'l3' else MODE_SEED if os.path.abspath(train_path) == MODE_ROWS else SEED
    if seed is not None:
        apply_run_seed(seed)   # after fit_seed is chosen: the eval fit sample is a held stream, identical across run seeds (U2)
    extra.update(seed=SEED, first_call_weight=first_call_weight)
    ev = {'l3_path': eval_rows or L3_EVAL_ROWS, 'l5_path': eval_rows or L5_EVAL_ROWS}
    sets = eval_sets(train_rows, cells, fit_seed, probe_path=probe, **ev)
    print(f'{arm}: rows {train_path}; scored cells {cells}: ' + ', '.join(f'{k} {len(v)}' for k, v in sets.items()), flush=True)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(SEED)
    m = load_model(parent).eval()
    if first_call_weight != 1.0:
        install_first_call_weight(m, float(first_call_weight))
    rows, drops = make_rows(m, train_rows, cons)
    print(f'{arm}: {len(rows)} of {len(train_rows)} rows usable; dropped {dict(drops)}', flush=True)
    ds = Dataset(rows, m.vocab)
    harm_fn = make_harm_fn(parent, dev, out) if harm_steps else None
    guarded = None
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
        if guard:
            kf, gp = load_guard(guard_src)
            diary, dcmp = build_parent_diary(m, ck, guard_src, out, data=diary_data, log_path=diary_compare, cache=diary_cache)
            m.eval()
            if soft_guard:   # frozen parent for the KL replay, taken before any update; Main brain's own klreplay (c823e4b9a)
                import importlib
                klreplay = importlib.import_module('mainbrain.klreplay')
                assert os.path.abspath(klreplay.__file__).startswith(os.path.abspath(guard_src)), klreplay.__file__
                kl_parent = klreplay.frozen_copy(m)
                kl_ds = Dataset(diary, m.vocab)
                kl_rng = np.random.RandomState(KL_REPLAY_SEED)
                kls = []
            guarded = Guarded(kf, gp, m, diary, guard_energy, lambda: make_opt(m, cons['lr']), soft=soft_value if soft_guard else None)
            opt = guarded.opt
            if soft_guard:
                m.loss = kl_replay_loss(m, kl_parent, float(kl_weight), kls, klreplay)   # not klreplay.wrap: weights 1 + kl_weight, see its docstring
            params = [p for p in m.parameters() if p.requires_grad]   # clip over the trainable params
            extra.update(guard=guard, guard_energy=guard_energy, guard_every=guard_every, guard_src_commit=guard_commit,
                         guard_norm='example', guard_replay=None, guard_parent_factors=False, guard_diary_n=len(diary), guard_diary_sha256=dcmp['sha256'], guard_diary_cache=diary_cache, guard_diary_data=None if 'cache' in dcmp else diary_data,   # None: the diary came from the cache, not a folder read
                         guard_frozen=len(guarded.frozen))
            if soft_guard:
                extra.update(guard_soft=soft_value, guard_commit_check=commit_check, kl_replay_rows=kl_replay_rows, kl_weight=kl_weight,
                             kl_replay_seed=KL_REPLAY_SEED, kl_replay_pool=len(diary))
            print(f'LB+{guard} guard' + (f' ({'hard mask' if soft_value is None else f'graded mask soft={soft_value}'}, {kl_replay_rows} diary rows/update at {kl_weight}x KL, source {commit_check})' if soft_guard else '') + f': trainable params {sum(p.numel() for p in params)} (frozen {len(guarded.frozen)} tensors), lr {cons["lr"]}', flush=True)
        else:
            opt = make_opt(m, cons['lr'])
            print(f'LB full fine-tune params {sum(p.numel() for p in params)}, lr {cons["lr"]}', flush=True)
    torch.manual_seed(SEED)   # ans_drill draws from the model's own RNG in train mode
    t_train, t_seg, losses = 0.0, time.time(), []
    steps = set(steps)
    last = max(steps)
    ex = lambda: dict(extra, measure_secs=round(guarded.measure_secs, 1), measures=guarded.measures) if guarded else extra
    hf = lambda u: harm_fn if u in harm_steps else None
    gstats, update_log, rms_path, rms_secs = None, [], os.path.join(out, 'update-rms.json'), 0.0
    if log_update_rms:   # C8, opt-in and read-only. Cadence: the progress-print points (every log_every updates, 100 from the CLI, and the last)
        gstats = GradStats(GRAD_CLIP)
        if arm == 'LA':   # the add-on's A / B are bare tensors, not module parameters: name them by the Linear they sit on
            rms_named = lambda: [(f'{name}.{t}', x) for name, _, A, B in addon.layers for t, x in (('A', A), ('B', B))]
        else:
            rms_named = m.named_parameters   # evaluated at the snapshot, so tensors --guard froze are skipped
        extra['update_rms_log'] = update_log   # the history so far rides on every scores.jsonl record; OUT/update-rms.json holds it whole
    if 0 in steps:
        score_step(ck, m, addon, sets, out, arm, 0, t_train, threads, ex(), hf(0), keep_final and last == 0)
    t_seg = time.time()
    for u, ni in enumerate(batch_order(len(rows), cons['batch'], updates, SEED), 1):
        t0 = time.time()
        m.train()
        items = [ds[i] for i in ni]
        if soft_guard:   # + diary rows (source 'diary'), told apart by kl_replay_loss
            items += [kl_ds[int(j)] for j in kl_rng.randint(0, len(diary), size=kl_replay_rows)]
        b = to_device(collate(items), 'cpu')
        o = m.loss(b)
        loss = o[0] if isinstance(o, tuple) else o
        loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(params, GRAD_CLIP)   # the return value is the total grad norm BEFORE clipping
        log_now = u % log_every == 0 or u == updates
        if log_update_rms:
            gstats.add(gn)
            snap = None
            if log_now:   # CPU only, so time.time() brackets the work; it is kept out of t_train and the s/update print
                ts = time.time()
                snap = snapshot_params(rms_named())
                dt = time.time() - ts
                rms_secs += dt
                t0 += dt
                t_seg += dt
        # Grad norm = gn, the raw total norm BEFORE the clip. With --guard (kf / kfsoft) nothing rewrites the gradients between here and
        # the optimizer: mainbrain KFOptimizer.step() (kf.py, c823e4b9a) runs base.step() on the clipped p.grad as it is and projects
        # the weight CHANGE [W|b] afterwards. So there is no guard-modified gradient to measure; the gradient the optimizer uses is this
        # one, clipped (norm min(gn, 1.0)). The projection does land inside the snapshot/update_rms window, so upd_rms is the update
        # as applied, after the guard. If a guard that masks p.grad is ever used, measure the norm here, after it, right before opt.step().
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        t_train += time.time() - t0
        if soft_guard and kls and u % log_every == 0:
            print(f'{arm} replay KL mean over last {min(len(kls), log_every)} updates: {np.mean(kls[-log_every:]):.5f}', flush=True)
        if log_now:
            k = u % log_every or log_every
            print(f'{arm} update {u}: {time.time() - t_seg:.1f}s for last {k} ({(time.time() - t_seg) / k:.3f} s/update), '
                  f'loss {np.mean(losses[-k:]):.4f}', flush=True)
            if log_update_rms:
                ts = time.time()
                rec = dict(update=u, **gstats.pop())
                rec['upd_rms_all'], rec['upd_rms'] = update_rms(snap)   # rms(delta) / rms(param before) of this one update
                update_log.append(rec)
                with open(rms_path, 'w') as f:
                    json.dump(update_log, f, indent=1)
                print(f'{arm} update_rms {json.dumps(rec)}', flush=True)
                rms_secs += time.time() - ts
                extra['update_rms_secs'] = round(rms_secs, 2)   # C8 work, outside train_secs and the s/update print
            t_seg = time.time()
        if guarded and u % guard_every == 0 and u < updates:   # re-measure F on the current weights; same base AdamW and state
            opt = guarded.refresh()
        if u in steps:
            score_step(ck, m, addon, sets, out, arm, u, t_train, threads, ex(), hf(u), keep_final and u == last)
            t_seg = time.time()
    m.eval()
    if soft_guard and kls:
        extra['replay_kl_mean'] = round(float(np.mean(kls)), 6)
        print(f'replay_kl {json.dumps(dict(mean=extra["replay_kl_mean"], n=len(kls), weight=kl_weight, rows=kl_replay_rows))}', flush=True)
    print(f'{arm} done: {updates} updates, train {t_train:.1f}s ({t_train / max(updates, 1):.3f} s/update)'
          + (f'; guard measuring {guarded.measure_secs:.1f}s in {guarded.measures} measures' if guarded else ''), flush=True)
    return t_train / max(updates, 1)


def main(argv=None):
    a = argparse.ArgumentParser(description='L1: can the 3M model learn joined formulas? (diagnosis only)')
    a.add_argument('stage', choices=['build', 'build-mode', 'build-l3', 'build-l4', 'build-l5', 'build-l8', 'build-l9', 'build-l10', 'census-l10', 'build-l12', 'census-l12', 'train'])
    a.add_argument('--rows-out', default=None, help='build-l8 / build-l9 / build-l10: where to write the rows (required; refuses to overwrite)')
    a.add_argument('--draw-cap', type=int, default=MODE_DRAW_CAP, help='build-l8 / build-l9 / build-l10: stop after this many draws')
    a.add_argument('--base-rows', default=L9_ROWS, help="build-l12: rows file whose 'mode-one' rows are copied unchanged (L9's train-rows-l9.jsonl)")
    a.add_argument('--arm', choices=['LA', 'LB'])
    a.add_argument('--updates', type=int, default=4000)
    a.add_argument('--threads', type=int, default=1)
    a.add_argument('--out')
    a.add_argument('--attempts', type=int, default=10000, help='census-l10: join-last attempts (--out: the JSON file)')
    a.add_argument('--rows', default=TRAIN_ROWS, help='training rows (default: the L1 file)')
    a.add_argument('--cells', choices=['l1', 'all', 'l3', 'l4', 'l5', 'l8'], default='l1',
               help='scored sets: l1 = four cells; all = L2 (probe splits, fit, v3); l3 = S, HP, HO, HPO, F0-near, F4-two, fit; l4 = all + S, HP, HO, HPO; l5 = S5, S, HP, HO, HPO, F0-near, F4-two, fit; l8 = S5, S, HP, HO, HPO, every probe cell, F4-plus, F4-times, fit')
    a.add_argument('--addon-rank', type=int, default=None, help="arm LA only: add-on rank (default: the mode's constant)")
    a.add_argument('--addon-alpha', type=float, default=None, help="arm LA only: add-on alpha (default: the mode's constant)")
    a.add_argument('--steps', default=DEFAULT_STEPS, help='comma list of update counts to score at')
    a.add_argument('--harm-steps', default='', help='comma list of steps (among --steps) at which to measure old-skill harm against the parent')
    a.add_argument('--dev', default=DEV_IN_DIST, help='DEV in_dist.jsonl for the harm measure')
    a.add_argument('--keep-final', action='store_true', help="do not delete the last step's checkpoint")
    a.add_argument('--guard', choices=['kf', 'kfsoft'], default=None,
               help='arm LB only: the main-brain K-FAC guard; kfsoft = graded mask (soft=1) + KL replay (needs --kl-replay-rows, --kl-weight; source commit ' + GUARD_COMMIT_SOFT[:9] + ')')
    a.add_argument('--kl-replay-rows', type=int, default=None, help='--guard kfsoft only: diary rows added to every update (seeded draw)')
    a.add_argument('--kl-weight', type=float, default=None, help='--guard kfsoft only: weight on the KL to the frozen parent over those rows')
    a.add_argument('--guard-soft', default=None, help="--guard kfsoft only: softness of the graded mask (kf.factors soft=); default 1 (L11); L13 uses 10; 'hard' = the hard mask with the KL replay (L14)")
    a.add_argument('--log-update-rms', action='store_true', help="train only (C8): log pre-clip grad-norm stats and per-group update rms (rms(delta)/rms(param before) of one update, groups = module path cut after the layer index) every 100 updates (train()'s log_every; the CLI has no --log-every) and at the last update; arm LA's figures are the add-on A/B factors' own change, not the effective weight's, so they are not comparable with LB's; with --guard the update rms is the update as applied, after the guard's projection; history in OUT/update-rms.json and on each scores.jsonl record; default off = training unchanged")
    a.add_argument('--guard-energy', type=float, default=0.99)
    a.add_argument('--guard-every', type=int, default=500, help='re-measure the guard factors every this many updates')
    a.add_argument('--parent', default=PARENT, help='parent checkpoint (default: the s200 parent)')
    a.add_argument('--probe', default=SP.PROBE, help='sheet probe file (default: the shared probe)')
    a.add_argument('--eval-rows', default=None, help='eval file for --cells l3/l4 (default eval-rows-l3) or l5 (default eval-rows-l5)')
    a.add_argument('--diary-compare', default=DIARY_LOG, help="main-brain log to compare the diary with; 'none' skips (recorded as skipped)")
    a.add_argument('--diary-cache', default=None, help='arm LB guard: load the diary rows from this file if it exists instead of rebuilding')
    a.add_argument('--diary-data', default=DIARY_DATA, help='--guard only: folder whose train.jsonl is the diary prompt pool (the seed-1 200k skills build); default the original path; checked before any work unless --diary-cache exists')
    a.add_argument('--guard-src', default=None, help='folder holding mainbrain/ (kf.py, gp.py) at commit ' + GUARD_COMMIT)
    a.add_argument('--seed', type=int, default=None, help='train only (R1): the run seed, driving the torch seedings, the data order and the KL replay stream; default None = the shipped module SEED (93301), every stream as shipped')
    a.add_argument('--first-call-weight', type=float, default=1.0, help="train only (R1): weight on the first call's token losses in the call writer's loss, renormalised per trace to the uniform-weight trace mean; default 1.0 = uniform (shipped)")
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
    elif a.stage == 'build-l8':
        assert a.rows_out, 'build-l8 needs --rows-out'
        build_l8(a.rows_out, a.parent, a.probe, a.eval_rows or L5_EVAL_ROWS, a.draw_cap)
    elif a.stage == 'build-l9':
        assert a.rows_out, 'build-l9 needs --rows-out'
        build_l9(a.rows_out, a.parent, a.probe, a.eval_rows or L5_EVAL_ROWS, a.draw_cap)
    elif a.stage == 'build-l10':
        assert a.rows_out, 'build-l10 needs --rows-out'
        build_l10(a.rows_out, a.parent, a.probe, a.eval_rows or L5_EVAL_ROWS, a.draw_cap)
    elif a.stage == 'census-l10':
        assert a.out, 'census-l10 needs --out'
        census_l10(a.parent, a.attempts, a.out)
    elif a.stage == 'build-l12':
        assert a.rows_out, 'build-l12 needs --rows-out'
        build_l12(a.rows_out, a.parent, a.probe, a.eval_rows or L5_EVAL_ROWS, a.base_rows, a.draw_cap)
    elif a.stage == 'census-l12':
        assert a.out, 'census-l12 needs --out'
        census_l12(a.parent, a.attempts, a.out)
    else:
        assert a.arm and a.out, 'train needs --arm and --out'
        if a.first_call_weight <= 0:
            raise SystemExit('--first-call-weight must be > 0')
        a.guard_soft = None if a.guard_soft is None else 'hard' if a.guard_soft in ('hard', 'none') else float(a.guard_soft)
        check_guard_args(a.arm, a.guard, a.guard_src, a.guard_energy, a.guard_every, a.kl_replay_rows, a.kl_weight, a.guard_soft)   # refuse before any work
        check_diary_data(a.guard, a.diary_data, a.diary_cache)
        from domain.mode import CONST_PATH
        addon_size(a.arm, json.load(open(CONST_PATH)), a.addon_rank, a.addon_alpha)   # refuse LB overrides before any work
        train(a.arm, a.updates, a.threads, a.out, [int(x) for x in a.steps.split(',')],
              train_path=a.rows, cells=a.cells, addon_rank=a.addon_rank, addon_alpha=a.addon_alpha,
              harm_steps=[int(x) for x in a.harm_steps.split(',') if x], dev=a.dev, keep_final=a.keep_final, guard=a.guard,
              guard_energy=a.guard_energy, guard_every=a.guard_every, guard_src=a.guard_src,
              parent=a.parent, probe=a.probe, eval_rows=a.eval_rows, diary_compare=a.diary_compare, diary_cache=a.diary_cache,
              kl_replay_rows=a.kl_replay_rows, kl_weight=a.kl_weight, guard_soft=a.guard_soft,
              seed=a.seed, first_call_weight=a.first_call_weight, log_update_rms=a.log_update_rms, diary_data=a.diary_data)


if __name__ == '__main__':
    main()
