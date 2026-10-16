"""L1 diagnosis: can the 3M calculator model learn joined formulas at all? (spec: far-transfer/learn/MARKS-L1-2026-10-11.md)

  python3 -m domain.far.learn_probe build
  python3 -m domain.far.learn_probe build-mode     (L2: MARKS-L2; rows from the v9 mode's own practice maker)
  python3 -m domain.far.learn_probe build-l3       (L3: MARKS-L3; '+' joins of training kind pairs; eval cells S/HP/HO/HPO)
  python3 -m domain.far.learn_probe build-l4      (L4: MARKS-L4; build-mode with the swap tool's join step on, seed 93601)
  python3 -m domain.far.learn_probe build-l5      (L5: MARKS-L5; training joins over five layouts; eval cells S5/S/HP/HO/HPO)
  python3 -m domain.far.learn_probe build-l8 --rows-out PATH --parent CKPT --probe PATH --eval-rows PATH   (L8: MARKS-L8; the substitution ring's joins)
  python3 -m domain.far.learn_probe build-l9 --rows-out PATH --parent CKPT --probe PATH --eval-rows PATH   (L9: MARKS-L9; whole-formula joins)
  python3 -m domain.far.learn_probe train --arm LA|LB --updates 4000 --threads N --out DIR [--steps 0,500,1000,2000,4000] [--rows PATH] [--cells l1|all|l3|l4|l5|l8]
        [--harm-steps 1000,2000,4000 | --no-harm] [--dev PATH [--dev-any]] [--harm-dev-big PATH] [--keep-final]
        (L7 / C2: old-skill harm vs the parent, kept final checkpoint. C2: the harm instrument is ALWAYS ON - without --harm-steps it runs at every
        --steps entry > 0; --no-harm restores none. --dev defaults to $CUSTOM_IO_DATA/dev/in_dist.jsonl and its sha256 must be the skills DEV
        in_dist (f975d9fb...) unless --dev-any; --harm-dev-big scores a second, larger DEV as well (it must contain that DEV: its lines for the DEV's ids hash to the same sha256, unless --dev-any). Each harm step writes OUT/harm-rows-step{N}.json
        (and harm-rows-big-step{N}.json): the paired per-row hits, for pairing across arms and seeds. The whole harm call runs with torch / random /
        numpy RNG state saved and restored, so it cannot move a training stream.)
        [--guard kf|kfsoft --guard-energy 0.99 --guard-every 500 --guard-src DIR]        (L7, arm LB only: the main-brain K-FAC guard)
       [--kl-replay-rows 32 --kl-weight 10 [--guard-soft 10]]        (L11 / L13, only with --guard kfsoft: graded mask (soft 1; L13: 10) + KL-to-parent replay, Main brain c823e4b9a)
        [--guard replay --kl-replay-rows 32 --kl-weight 10 --guard-src DIR [--replay-loss kl|ce] [--diary-cache F --diary-compare none | --diary-any]]
        (C1, arm LB only: the replay ALONE - no K-FAC mask, no Guarded wrapper, nothing frozen (unless --replay-freeze, A1F), the unguarded LB optimizer. The diary is built as for
        kfsoft and each update appends --kl-replay-rows diary rows from RandomState(KL_REPLAY_SEED) (the stream follows --seed). --replay-loss kl
        (default) = weight x KL to the frozen parent (klreplay from --guard-src, commit-checked); ce = weight x the plain loss on the diary rows, whose
        targets are the parent's own greedy answers. --guard-soft is refused with it.)
        [--replay-freeze]        (A1F, only with --guard replay: before the optimizer is built, freeze exactly the tensors the K-FAC guard freezes -
        gp.freeze_unprojected from --guard-src (commit-checked) - so the trainable set and the clip set are L11's (Guarded's), with NO projection and
        NO mask and no Guarded wrapper; the optimizer is make_opt over the model as for the unguarded path, which leaves requires_grad False
        tensors out of its groups (so not even weight decay moves them). Records replay_freeze true and guard_frozen = the number of tensors frozen,
        with guard_commit_check / guard_src_commit as kfsoft records them. Against L11 (kfsoft soft 1, 32 diary rows, 10x KL) the weight update is the
        same but for the K-FAC projection: test_a1f_is_one_change_vs_l11 shows equal state_dict hashes at every scored step when kfsoft's KFOptimizer.step
        is a pass-through (real kfac_stats / factors, re-measures included). The only other differences are not in the weights: no F is ever measured
        for A1F (no measure_secs / measures on its records, and its run is that much cheaper), its records carry guard 'replay' (not 'kfsoft') and no
        guard_energy / guard_every / guard_soft / guard_norm keys, and the running replay_kl_mean rides on each step's record where kfsoft's does not.)
        [--stop-if-drop 1000:3.0,2000:3.0]        (futility stop, any arm: STEP:DROP pairs, each STEP a harm step. After the harm measure at STEP, if
        in_dist_drop >= DROP the step's record gets futility_stop {step, drop, limit}, a line is printed, and training stops there - no further
        update or score. Records stop_if_drop = {step: limit} on every record of a run that sets it. With --keep-final the step the run
        stops at keeps its checkpoint, as the last step does.)
       [--seed N] [--first-call-weight W]        (R1, Oct 2026: --seed re-points the run seed (module SEED and the import-derived
        KL_REPLAY_SEED together; the eval fit seed, chosen before it applies, and the build-time streams stay as shipped);
        --first-call-weight (default 1.0 = shipped) weights the first call's losses (the call writer's token losses
        and round 0's span_call term), renormalised per trace to the uniform-weight trace mean - see install_first_call_weight)

build: 6,000 F4-two and 6,000 F0-near rows from the probe generator (domain/far/sheet_probe.py), seed 93301, scored kinds
       only, no prompt in the probe file or any sheet panel (read for exclusion only). Refuses to overwrite.
train: parent checkpoint + the mode's make_row / make_opt / AddOn / loss, on those rows only (no diary, no replay).
       LA = the mode's add-on (base frozen); LB = every weight at the mode's night lr. Same data order for both arms.
       Scores with domain.score.score on a checkpoint saved by the mode's save_ckpt at each step.
Diagnosis only: the mode is not run and no panel row is trained.
"""
import argparse
import contextlib
import hashlib
import itertools
import json
import os
import random
import re
import time
from collections import Counter

import numpy as np

from custom_io.data import DEFAULT_DATA
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


def parse_stop_if_drop(spec, harm_steps=None):
    """--stop-if-drop 'STEP:DROP[,STEP:DROP...]' (e.g. '1000:3.0,2000:3.0') -> {step: limit} (int -> float), None for no spec.
    Refused (SystemExit): a malformed pair, a STEP given twice, a DROP that is not a number > 0, and (when harm_steps is given) a STEP that
    is not a harm step - the stop reads the harm measure of that step, which exists only at the harm steps."""
    if spec is None:
        return None
    out = {}
    for tok in spec.split(','):
        try:
            k, v = tok.split(':')
            step, limit = int(k), float(v)
        except ValueError:
            raise SystemExit(f"--stop-if-drop wants 'STEP:DROP[,STEP:DROP...]', got {tok!r}") from None
        if not limit > 0 or limit == float('inf'):
            raise SystemExit(f'--stop-if-drop {tok!r}: DROP must be a number > 0')
        if step in out:
            raise SystemExit(f'--stop-if-drop names step {step} twice')
        out[step] = limit
    if harm_steps is not None:
        bad = sorted(set(out) - set(harm_steps))
        if bad:
            raise SystemExit(f'--stop-if-drop steps {bad} are not harm steps (harm steps: {sorted(harm_steps)})')
    return out


def futility_stop(limits, step, harm):
    """The futility-stop decision: -> {'step', 'drop', 'limit'} when `step` has a limit in `limits` ({step: limit}, from
    parse_stop_if_drop) and the harm record's in_dist_drop (the main DEV's, 2 dp as recorded) is >= it; else None."""
    if not limits or harm is None or step not in limits:
        return None
    drop, limit = harm['in_dist_drop'], limits[step]
    return {'step': step, 'drop': drop, 'limit': limit} if drop >= limit else None


def score_step(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False, stop_limits=None, keep_final=False):
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
            harm = dict(harm)
            big = harm.pop('harm_big', None)   # --harm-dev-big: the bigger DEV's record sits beside 'harm', not inside it
            rec['harm'] = harm
            if big is not None:
                rec['harm_big'] = big
        stop = futility_stop(stop_limits, step, harm)   # --stop-if-drop: rides on this step's record
        if stop:
            rec['futility_stop'] = stop
        f.write(json.dumps(rec) + '\n')
    print(f'{arm} step {step}: ' + ' '.join(f'{k} {v["pct"]:.1f}' for k, v in cells.items()) + f' (score {secs}s)', flush=True)
    if stop:
        print(f'{arm} FUTILITY STOP at step {step}: in_dist_drop {stop["drop"]} >= limit {stop["limit"]}; training stops here', flush=True)
    if not (keep or (stop and keep_final)):   # --keep-final: the last step's checkpoint stays, and so does the step a futility stop ends the run at
        os.remove(path)   # the checkpoint is only a vehicle for the scorer
        os.rmdir(os.path.dirname(path))
    return stop


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


def check_guard_args(arm, guard, guard_src, energy=0.99, every=500, kl_rows=None, kl_weight=None, soft=None, replay_loss=None, replay_freeze=False):
    """The guard is for arm LB only and needs its source folder; refuse otherwise, before any work.
    kl_rows / kl_weight (None = not given) are for --guard kfsoft and --guard replay only; both need both, rows >= 1 and weight > 0.
    soft (None = not given, 1 is used) is the graded-mask softness of --guard kfsoft (L13: 10), > 0, or 'hard' (L14: the hard
    mask, kf.factors soft=None, with the KL replay); --guard replay has no mask, so --guard-soft is refused with it.
    replay_loss (None = not given; 'kl' is used) is --replay-loss of --guard replay: 'kl' or 'ce'; refused with any other guard.
    replay_freeze (False = not given) is --replay-freeze (A1F): valid only with --guard replay, refused with any other guard or none."""
    if guard not in ('kfsoft', 'replay') and (kl_rows is not None or kl_weight is not None or soft is not None):
        raise SystemExit('--kl-replay-rows / --kl-weight / --guard-soft apply to --guard kfsoft only')
    if guard == 'replay' and soft is not None:
        raise SystemExit('--guard-soft applies to --guard kfsoft only: --guard replay has no mask')
    if replay_loss is not None and guard != 'replay':
        raise SystemExit('--replay-loss applies to --guard replay only')
    if replay_freeze and guard != 'replay':
        raise SystemExit('--replay-freeze applies to --guard replay only')
    if replay_loss is not None and replay_loss not in REPLAY_LOSSES:
        raise SystemExit(f'--replay-loss must be one of {REPLAY_LOSSES}')
    if soft is not None and soft != 'hard' and soft <= 0:
        raise SystemExit("--guard-soft must be > 0 or 'hard'")
    if not guard:
        return
    if arm != 'LB':
        raise SystemExit('--guard applies to arm LB only')
    if guard == 'kfsoft' and (kl_rows is None or kl_weight is None or kl_rows < 1 or kl_weight <= 0):
        raise SystemExit('--guard kfsoft needs --kl-replay-rows >= 1 and --kl-weight > 0')
    if guard == 'replay' and (kl_rows is None or kl_weight is None or kl_rows < 1 or kl_weight <= 0):
        raise SystemExit('--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0')
    if guard not in ('kf', 'kfsoft', 'replay'):
        raise SystemExit(f'unknown guard {guard}')
    if not guard_src or not os.path.isdir(guard_src):
        raise SystemExit('--guard needs --guard-src DIR (the folder holding mainbrain/)')
    if guard != 'replay' and (not 0 < energy < 1 or every < 1):
        raise SystemExit('--guard-energy must be in (0,1) and --guard-every >= 1')


def addon_size(arm, cons, rank=None, alpha=None):
    """(rank, alpha) for arm LA: the mode's constants unless overridden. LB has no add-on: overrides are refused."""
    if arm != 'LA':
        if rank is not None or alpha is not None:
            raise SystemExit('--addon-rank/--addon-alpha apply to arm LA only')
        return None, None
    return (cons['addon_rank'] if rank is None else rank), (cons['addon_alpha'] if alpha is None else alpha)


DEV_IN_DIST = os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl')   # custom_io.data.DEFAULT_DATA honours $CUSTOM_IO_DATA (read at import)
DEV_IN_DIST_SHA256 = 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'   # the skills seed-1 DEV in_dist file (1,360 rows) the harm numbers are quoted on
GUARD_COMMIT = '5ca34e99938981a6448ba298a1a2127c468a46b0'
GUARD_COMMIT_SOFT = 'c823e4b9a49c477751f6ad95e764097258b1aece'   # --guard kfsoft: Main brain's shipped guard (graded mask + KL replay)
GUARD_SOFT_FILES = ('kf.py', 'gp.py', 'klreplay.py', 'fullrun.py')
REPLAY_LOSSES = ('kl', 'ce')   # --guard replay: the replay half is weight x KL to the frozen parent, or weight x the model's own loss on the diary rows
KL_REPLAY_SEED = SEED + 11   # RandomState drawing the diary rows for the KL replay, one draw of --kl-replay-rows per update
GUARD_CONSTANTS = 'constants-kf99n-lr3e4.json'   # in the guard source folder's mainbrain/: the s200 sheet run's constants (diary 4096, check 512)
DIARY_DATA = DEFAULT_DATA   # the skills build whose train.jsonl the diary pool is read from ($CUSTOM_IO_DATA)
DIARY_TRAIN_SHA256 = '010af67124544bda9d4f26d8bd2801427770f1bb38f8c7b79921a36c87b244f5'   # the skills seed-1 200k build's train.jsonl (q33's file, custom_io/PASS-MARKS.md): the diary pool must come from it
DIARY_SEED = 200
DIARY_LOG = '/mnt/project-files/main-brain/runs/sheet-s200-kf99n/log.jsonl'


@contextlib.contextmanager
def rng_isolated():
    """C2: run a block without moving any training stream. torch's global generator (state AND initial_seed, which
    torch.manual_seed inside the block would move and which model construction reads), python's random and numpy's global
    state are saved before and restored after, so the old-skill harm instrument cannot change a training stream. Measured: a
    harm.in_dist_hits call (load_model builds the net before loading the weights) DOES advance torch's global RNG; evaluate()'s
    greedy decoding draws nothing."""
    import torch
    t_state, t_seed, py_state, np_state = torch.get_rng_state(), torch.initial_seed(), random.getstate(), np.random.get_state()
    try:
        yield
    finally:
        torch.manual_seed(t_seed)
        torch.set_rng_state(t_state)
        random.setstate(py_state)
        np.random.set_state(np_state)


def isolate_rng(fn):
    """fn wrapped in rng_isolated()."""
    def wrapped(*a, **kw):
        with rng_isolated():
            return fn(*a, **kw)
    return wrapped


def dev_provenance(dev, dev_any=False, expected=DEV_IN_DIST_SHA256):
    """-> (sha256 of the DEV file, checked). A file that is not the expected skills DEV in_dist is refused (SystemExit) unless
    dev_any (--dev-any), which records checked False: the harm numbers are then on a file nobody has vouched for. A missing
    file is a SystemExit naming the ways out (the default --dev needs $CUSTOM_IO_DATA, which is read when custom_io.data is
    imported)."""
    if not os.path.isfile(dev):
        raise SystemExit(f'--dev {dev} not found (set CUSTOM_IO_DATA to the skills build, pass --dev, or pass --no-harm / --harm-steps "")')
    sha = file_sha256(dev)
    if sha != expected and not dev_any:
        raise SystemExit(f'--dev {dev} has sha256 {sha}, not the skills DEV in_dist {expected} (pass --dev-any to measure harm on another file)')
    return sha, not dev_any


def big_dev_provenance(dev_big, dev, dev_any=False, expected=DEV_IN_DIST_SHA256):
    """-> (sha256 of the --harm-dev-big file, checked). The big DEV must contain the main DEV: its raw lines for the main DEV's
    ids, taken in the main DEV's order, must hash to `expected` (the main DEV file's sha256; true of the skills big DEV, whose
    1,360 rows are the per-family prefix of its 6,800). Refused (SystemExit) otherwise, or when the file is missing or lacks an
    id, unless dev_any, which records checked False. Ids are compared as the DEV rows' 'id' field."""
    if not os.path.isfile(dev_big):
        raise SystemExit(f'--harm-dev-big {dev_big} not found')
    sha = file_sha256(dev_big)
    if dev_any:
        return sha, False
    by_id = {}
    for line in open(dev_big, 'rb').read().split(b'\n'):
        if line.strip():
            by_id[json.loads(line)['id']] = line
    ids = [json.loads(line)['id'] for line in open(dev, 'rb').read().split(b'\n') if line.strip()]
    missing = [i for i in ids if i not in by_id]
    got = None if missing else hashlib.sha256(b''.join(by_id[i] + b'\n' for i in ids)).hexdigest()
    if got != expected:
        raise SystemExit(f'--harm-dev-big {dev_big} does not contain the skills DEV in_dist: its lines for the {len(ids)} DEV ids '
                         + (f'lack {len(missing)} of them' if missing else f'hash to {got}, not {expected}') + ' (pass --dev-any to score another file)')
    return sha, True


def make_harm_fn(parent, dev, out, dev_any=False, dev_big=None):
    """-> f(ckpt_path, step) -> dict: old-skill harm of the checkpoint against the parent on the DEV in_dist rows (domain/harm.py).
    The parent's hits are computed once and cached to OUT/parent-hits.json (with the DEV file's sha256, which must be
    DEV_IN_DIST_SHA256 unless dev_any; every harm record carries dev_sha256 and dev_sha256_checked). At each call the paired per-row
    result is written to OUT/harm-rows-step{N}.json = {step, dev, dev_sha256, ids, family, parent_hits, child_hits}, so
    arms and seeds can be paired later. dev_big (--harm-dev-big): a second, larger DEV scored the same way (its parent hits cached
    in OUT/parent-hits-big.json, its rows in OUT/harm-rows-big-step{N}.json); its result is the 'harm_big' key of the returned dict. It must contain the checked DEV
    (big_dev_provenance) unless dev_any, and carries dev_sha256_checked like the main one.
    All of it runs under rng_isolated(): switching harm on cannot change any training stream."""
    from custom_io.data import load_rows
    from domain import harm

    def prepare(path, cache_name, tag, sha, checked):
        rows = load_rows(path)
        ids = [r['id'] for r in rows]
        cache = os.path.join(out, cache_name)
        t0 = time.time()
        if os.path.exists(cache):
            c = json.load(open(cache))
            if c.get('ids', ids) != ids or c.get('parent', parent) != parent or c.get('dev_sha256', sha) != sha:
                raise SystemExit(f'{cache} was made for another parent / DEV file: refusing to pair against it')
            parent_hits = c['hits']
        else:
            parent_hits, acc = harm.in_dist_hits(parent, rows)
            with open(cache, 'w') as f:
                json.dump({'parent': parent, 'dev': path, 'dev_sha256': sha, 'n': len(rows), 'exact': acc, 'ids': ids, 'hits': parent_hits}, f)
        print(f'harm{tag}: parent hits on {len(rows)} in_dist rows ({time.time() - t0:.1f}s)', flush=True)
        return dict(path=path, rows=rows, ids=ids, sha=sha, checked=checked, parent_hits=parent_hits, tag=tag)

    def measure(d, ckpt, step, rows_name):
        t = time.time()
        rows, parent_hits = d['rows'], d['parent_hits']
        hits, _ = harm.in_dist_hits(ckpt, rows)
        h = harm.harm_measure(parent_hits, hits, rows, 5.0, 1.5)
        res = {'in_dist_a': round(h['in_dist_a'], 2), 'in_dist_b': round(h['in_dist_b'], 2), 'in_dist_drop': round(h['in_dist_drop'], 2),
               'fired': h['fired'], 'passes': bool(h['passes']), 'n': len(rows),
               'family_drops': {f: round(v['drop'], 1) for f, v in h['families'].items()}, 'secs': round(time.time() - t, 1),
               'dev': d['path'], 'dev_sha256': d['sha']}
        if d['checked'] is not None:
            res['dev_sha256_checked'] = d['checked']
        with open(os.path.join(out, f'{rows_name}{step}.json'), 'w') as f:
            json.dump({'step': step, 'dev': d['path'], 'dev_sha256': d['sha'], 'ids': d['ids'], 'family': [r['family'] for r in rows],
                       'parent_hits': parent_hits, 'child_hits': hits}, f)
        print(f'harm{d["tag"]} step {step}: in_dist {res["in_dist_a"]} -> {res["in_dist_b"]} (drop {res["in_dist_drop"]}), '
              f'fired {res["fired"]}, {"PASS" if res["passes"] else "FAIL"}, n {res["n"]}', flush=True)
        return res

    with rng_isolated():
        main_dev = prepare(dev, 'parent-hits.json', '', *dev_provenance(dev, dev_any))
        big_dev = prepare(dev_big, 'parent-hits-big.json', '-big', *big_dev_provenance(dev_big, dev, dev_any)) if dev_big else None   # must contain the checked main DEV unless dev_any

    def fn(path, step):
        res = measure(main_dev, path, step, 'harm-rows-step')
        if big_dev:
            res['harm_big'] = measure(big_dev, path, step, 'harm-rows-big-step')
        return res
    return isolate_rng(fn)


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


def build_parent_diary(m, ck, src, out, data=DIARY_DATA, seed=DIARY_SEED, log_path=DIARY_LOG, cache=None, data_any=False):
    """The parent's own answers on training prompts, rebuilt as domain/mode.py main does (pool of the data folder's train file,
    shuffled by Random(f'{seed}-diary'), the first `check` held out, then build_diary). Diary size/check from the guard
    source's kf99n constants (the s200 sheet run's). Written to OUT/diary.jsonl; prompts compared with the run's diary rows
    (log_path 'none' skips the comparison). cache: an existing diary.jsonl is loaded instead of rebuilding (nothing else read).
    A rebuild refuses (SystemExit) a train file whose sha256 is not DIARY_TRAIN_SHA256 unless data_any (--diary-any): $CUSTOM_IO_DATA
    decides which build the pool is read from, and the log comparison alone would not notice another build; the train file's
    sha256 and whether it was checked go into the compare dict.
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
    tpath = mode.guard(os.path.join(data, 'train.jsonl'))
    tsha = file_sha256(tpath)
    if tsha != DIARY_TRAIN_SHA256 and not data_any:
        raise SystemExit(f'diary pool: {tpath} has sha256 {tsha}, not the skills seed-1 build {DIARY_TRAIN_SHA256} (set CUSTOM_IO_DATA, use --diary-cache, or pass --diary-any)')
    cons = dict(json.load(open(os.path.join(src, 'mainbrain', GUARD_CONSTANTS))))
    helps = sheet_tool.help()
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    pool = []
    with open(tpath) as f:
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
    cmp = {'n': len(diary), 'check': len(check), 'scanned': pos, 'secs': secs, 'log': log_path, 'sha256': file_sha256(dpath),
           'train_sha256': tsha, 'train_sha256_checked': not data_any}
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


def ce_replay_loss(m, weight, ces):
    """Instance-level loss for --guard replay --replay-loss ce. The structure of kl_replay_loss with the KL swapped for the
    plain loss on the diary rows: split the batch by row source 'diary'; the plain loss when not training / no grad / no diary or
    no new rows; tuple shape kept, aux gets 'replay_ce'; every replay loss appended to ces. Combined as plain loss on the new
    rows (weight 1) + weight x plain loss on the diary rows (the mean over them), where plain is the model's own Tool loss and
    the diary rows' targets are the parent's own greedy answers (build_parent_diary). No frozen parent is needed."""
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
        out_r = plain(part(b, ri))
        ce = out_r[0] if isinstance(out_r, tuple) else out_r
        ces.append(float(ce.detach()))
        if isinstance(out_n, tuple):
            aux = out_n[1]
            if isinstance(aux, dict):
                aux = dict(aux, replay_ce=float(ce.detach()))
            return (out_n[0] + weight * ce, aux) + tuple(out_n[2:])
        return out_n + weight * ce
    return loss


def load_klreplay(src):
    """Main brain's klreplay (c823e4b9a) from the guard source folder: src first on sys.path, the module's file asserted to lie under src."""
    import importlib
    import sys
    sys.path.insert(0, os.path.abspath(src))
    for name in ('mainbrain.klreplay', 'mainbrain'):
        sys.modules.pop(name, None)
    klreplay = importlib.import_module('mainbrain.klreplay')
    assert os.path.abspath(klreplay.__file__).startswith(os.path.abspath(src)), klreplay.__file__
    return klreplay


def setup_replay_arm(m, cons, make_opt, replay_loss, weight, log, klreplay=None, freeze=None):
    """--guard replay (arm LB): no K-FAC mask, no Guarded wrapper, nothing frozen (unless freeze=..., A1F / --replay-freeze). m.loss becomes the replay loss ('kl':
    kl_replay_loss against klreplay.frozen_copy(m), taken now, before any update; 'ce': ce_replay_loss); every replay value is
    appended to `log`. The optimizer is make_opt(m, cons['lr']) exactly as the unguarded LB path builds it. -> (opt, params).
    freeze (A1F, --replay-freeze; None = nothing frozen, as shipped): a callable m -> frozen names, i.e. the guard source's
    gp.freeze_unprojected. It runs after the KL parent copy is taken and BEFORE the optimizer is built, so make_opt (which keeps only
    requires_grad parameters, as under Guarded, whose make_base is called after its freeze) builds its groups from the trainable set alone and the
    frozen tensors are in no group - no gradient, no weight decay. params (the clip set) is then the trainable set, as under Guarded."""
    assert replay_loss in REPLAY_LOSSES, replay_loss
    if replay_loss == 'kl':
        m.loss = kl_replay_loss(m, klreplay.frozen_copy(m), float(weight), log, klreplay)
    else:
        m.loss = ce_replay_loss(m, float(weight), log)
    params = list(m.parameters())
    assert all(p.requires_grad for p in params)
    if freeze is not None:
        frozen = freeze(m)
        params = [p for p in m.parameters() if p.requires_grad]
        assert len(frozen) == len(list(m.parameters())) - len(params), (len(frozen), len(params))
    return make_opt(m, cons['lr']), params


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
          kl_replay_rows=None, kl_weight=None, guard_soft=None, seed=None, first_call_weight=1.0, replay_loss=None, dev_any=False,
          harm_dev_big=None, diary_any=False, replay_freeze=False, stop_if_drop=None):
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
    check_guard_args(arm, guard, guard_src, guard_energy, guard_every, kl_replay_rows, kl_weight, guard_soft, replay_loss, replay_freeze)
    stop_limits = None if stop_if_drop is None else dict(stop_if_drop)   # {step: limit} from parse_stop_if_drop; None = no futility stop
    if stop_limits is not None:
        bad = sorted(set(stop_limits) - harm_steps)
        if bad:
            raise SystemExit(f'--stop-if-drop steps {bad} are not harm steps (harm steps: {sorted(harm_steps)})')
    if harm_steps:
        dev_provenance(dev, dev_any)   # refuse a DEV file that is not the expected one before any work
        if harm_dev_big:
            big_dev_provenance(harm_dev_big, dev, dev_any)   # likewise the big DEV: it must contain the checked one
    soft_value = (1 if guard_soft is None else None if guard_soft == 'hard' else
                  int(guard_soft) if float(guard_soft).is_integer() else float(guard_soft))   # 1 = L11; None = the hard mask (L14)
    soft_guard = guard == 'kfsoft'
    replay_arm = guard == 'replay'   # C1: replay only, no mask, no Guarded wrapper, nothing frozen (unless --replay-freeze, A1F)
    replay_kind = (replay_loss or 'kl') if replay_arm else None
    use_replay = soft_guard or replay_arm
    guard_commit = GUARD_COMMIT_SOFT if soft_guard else GUARD_COMMIT
    commit_check = verify_guard_commit(guard_src) if soft_guard or replay_kind == 'kl' or replay_freeze else None   # replay_freeze: gp.freeze_unprojected comes from the source
    kls, ces = [], []   # replay values per update: the KL (kfsoft, replay kl) or the replay-row loss (replay ce)
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, 'scores.jsonl')):
        raise SystemExit(f'refusing to reuse {out}: scores.jsonl exists')
    train_rows = load_jsonl(train_path)
    fit_seed = L8_SEED if cells == 'l8' else L5_SEED if cells == 'l5' else L4_SEED if cells == 'l4' else L3_SEED if cells == 'l3' else MODE_SEED if os.path.abspath(train_path) == MODE_ROWS else SEED
    if seed is not None:
        apply_run_seed(seed)   # after fit_seed is chosen: the eval fit sample is a held stream, identical across run seeds (U2)
    extra.update(seed=SEED, first_call_weight=first_call_weight)
    if stop_limits:
        extra['stop_if_drop'] = {str(k): v for k, v in sorted(stop_limits.items())}
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
    harm_fn = make_harm_fn(parent, dev, out, dev_any, harm_dev_big) if harm_steps else None
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
        if replay_arm:
            diary, dcmp = build_parent_diary(m, ck, guard_src, out, log_path=diary_compare, cache=diary_cache, data_any=diary_any)
            m.eval()
            klreplay = load_klreplay(guard_src) if replay_kind == 'kl' else None
            kl_ds = Dataset(diary, m.vocab)
            kl_rng = np.random.RandomState(KL_REPLAY_SEED)
            freeze = load_guard(guard_src)[1].freeze_unprojected if replay_freeze else None   # A1F: the guard source's own freeze, before the optimizer
            opt, params = setup_replay_arm(m, cons, make_opt, replay_kind, kl_weight, ces if replay_kind == 'ce' else kls, klreplay, freeze)
            extra.update(guard='replay', replay_loss=replay_kind, kl_replay_rows=kl_replay_rows, kl_weight=kl_weight,
                         kl_replay_seed=KL_REPLAY_SEED, kl_replay_pool=len(diary), guard_diary_n=len(diary),
                         guard_diary_sha256=dcmp['sha256'], guard_diary_cache=diary_cache)
            if replay_kind == 'kl' or replay_freeze:   # guard_src_commit as kfsoft records it: A1F vs L11 shows gp.freeze_unprojected is from one source
                extra.update(guard_commit_check=commit_check, guard_src_commit=GUARD_COMMIT_SOFT)
            n_frozen = sum(1 for p in m.parameters() if not p.requires_grad)
            if replay_freeze:
                extra.update(replay_freeze=True, guard_frozen=n_frozen)
            print(f'LB+replay ({replay_kind}, {kl_replay_rows} diary rows/update at {kl_weight}x'
                  + (f', source {commit_check}' if replay_kind == 'kl' or replay_freeze else '')
                  + (f'; no mask, frozen as the guard freezes: {n_frozen} tensors' if replay_freeze else '; no mask, nothing frozen')
                  + f'): trainable params {sum(p.numel() for p in params)}, lr {cons["lr"]}', flush=True)
        elif guard:
            kf, gp = load_guard(guard_src)
            diary, dcmp = build_parent_diary(m, ck, guard_src, out, log_path=diary_compare, cache=diary_cache, data_any=diary_any)
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
                         guard_norm='example', guard_replay=None, guard_parent_factors=False, guard_diary_n=len(diary), guard_diary_sha256=dcmp['sha256'], guard_diary_cache=diary_cache,
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
    rlog = ces if replay_kind == 'ce' else kls
    rkey = 'replay_ce_mean' if replay_kind == 'ce' else 'replay_kl_mean'
    ex = lambda: dict(extra, measure_secs=round(guarded.measure_secs, 1), measures=guarded.measures) if guarded else (
        dict(extra, **{rkey: round(float(np.mean(rlog)), 6)}) if replay_arm and rlog else extra)   # replay arm: the running mean so far rides on each step's record
    hf = lambda u: harm_fn if u in harm_steps else None
    sk = {'stop_limits': stop_limits, 'keep_final': keep_final} if stop_limits else {}   # passed only when a futility stop is set: score_step's other callers see the shipped call; keep_final lets a stopped run keep the checkpoint it stopped at
    stopped = None
    if 0 in steps:
        score_step(ck, m, addon, sets, out, arm, 0, t_train, threads, ex(), hf(0), keep_final and last == 0, **sk)   # step 0 is the parent: drop 0, it can never reach a limit > 0
    t_seg = time.time()
    done = updates
    for u, ni in enumerate(batch_order(len(rows), cons['batch'], updates, SEED), 1):
        t0 = time.time()
        m.train()
        items = [ds[i] for i in ni]
        if use_replay:   # + diary rows (source 'diary'), told apart by kl_replay_loss / ce_replay_loss
            items += [kl_ds[int(j)] for j in kl_rng.randint(0, len(diary), size=kl_replay_rows)]
        b = to_device(collate(items), 'cpu')
        o = m.loss(b)
        loss = o[0] if isinstance(o, tuple) else o
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        t_train += time.time() - t0
        if use_replay and rlog and u % log_every == 0:
            print(f'{arm} replay {"CE" if replay_kind == "ce" else "KL"} mean over last {min(len(rlog), log_every)} updates: {np.mean(rlog[-log_every:]):.5f}', flush=True)
        if u % log_every == 0 or u == updates:
            k = u % log_every or log_every
            print(f'{arm} update {u}: {time.time() - t_seg:.1f}s for last {k} ({(time.time() - t_seg) / k:.3f} s/update), '
                  f'loss {np.mean(losses[-k:]):.4f}', flush=True)
            t_seg = time.time()
        if guarded and u % guard_every == 0 and u < updates:   # re-measure F on the current weights; same base AdamW and state
            opt = guarded.refresh()
        if u in steps:
            stopped = score_step(ck, m, addon, sets, out, arm, u, t_train, threads, ex(), hf(u), keep_final and u == last, **sk)
            t_seg = time.time()
            if stopped:   # futility stop: its record is written; no further update, no further score
                done = u
                break
    m.eval()
    if use_replay and rlog:
        extra[rkey] = round(float(np.mean(rlog)), 6)
        print(f'{rkey[:-5]} {json.dumps(dict(mean=extra[rkey], n=len(rlog), weight=kl_weight, rows=kl_replay_rows))}', flush=True)
    print(f'{arm} done: {done} updates' + (f' of {updates} (futility stop)' if stopped else '')
          + f', train {t_train:.1f}s ({t_train / max(done, 1):.3f} s/update)'
          + (f'; guard measuring {guarded.measure_secs:.1f}s in {guarded.measures} measures' if guarded else ''), flush=True)
    return t_train / max(done, 1)


def resolve_harm_steps(steps, harm_steps=None, no_harm=False):
    """C2: the harm instrument is always on. --no-harm -> [] (and refuses --harm-steps beside it); an explicit --harm-steps list
    (comma string, '' = none) is used as given; otherwise every entry of `steps` that is > 0 (step 0 is the parent itself)."""
    if no_harm:
        if harm_steps:
            raise SystemExit('--no-harm and --harm-steps are exclusive')
        return []
    if harm_steps is None:
        return [s for s in steps if s > 0]
    return [int(x) for x in harm_steps.split(',') if x]


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
    a.add_argument('--harm-steps', default=None, help='comma list of steps (among --steps) at which to measure old-skill harm against the parent; default: every --steps entry > 0 (the harm instrument is always on)')
    a.add_argument('--no-harm', action='store_true', help='no old-skill harm measure at all (the pre-C2 default)')
    a.add_argument('--dev', default=DEV_IN_DIST, help='DEV in_dist.jsonl for the harm measure (default: $CUSTOM_IO_DATA/dev/in_dist.jsonl); its sha256 must be ' + DEV_IN_DIST_SHA256[:12] + ' unless --dev-any')
    a.add_argument('--dev-any', action='store_true', help='allow a --dev file whose sha256 is not the skills DEV in_dist (recorded as dev_sha256_checked false)')
    a.add_argument('--harm-dev-big', default=None, help='a second, larger DEV (e.g. the 6,800-row in_dist) also scored at every harm step: record key harm_big, parent hits cached in OUT/parent-hits-big.json')
    a.add_argument('--keep-final', action='store_true', help="do not delete the last step's checkpoint")
    a.add_argument('--guard', choices=['kf', 'kfsoft', 'replay'], default=None,
               help='arm LB only: the main-brain K-FAC guard; kfsoft = graded mask (soft=1) + KL replay (needs --kl-replay-rows, --kl-weight; source commit ' + GUARD_COMMIT_SOFT[:9] + '); replay = the replay alone (no mask, nothing frozen unless --replay-freeze, every weight at the unguarded LB lr; needs --kl-replay-rows, --kl-weight, --guard-src for the diary; --replay-loss picks the form)')
    a.add_argument('--replay-loss', choices=list(REPLAY_LOSSES), default=None, help='--guard replay only: kl (default) = weight x KL to the frozen parent over the diary rows; ce = weight x the plain loss on the diary rows (targets: the parent\'s own greedy answers)')
    a.add_argument('--replay-freeze', action='store_true', help="--guard replay only (A1F): freeze exactly the tensors the K-FAC guard freezes (gp.freeze_unprojected from --guard-src), before the optimizer is built; no projection, no mask, no Guarded; records replay_freeze and guard_frozen")
    a.add_argument('--stop-if-drop', default=None, help="futility stop, 'STEP:DROP[,STEP:DROP...]' (e.g. 1000:3.0,2000:3.0): each STEP must be a harm step; if the harm measure at STEP has in_dist_drop >= DROP the step's record gets futility_stop and training stops there (with --keep-final the stopped step's checkpoint is kept)")
    a.add_argument('--kl-replay-rows', type=int, default=None, help='--guard kfsoft / replay only: diary rows added to every update (seeded draw)')
    a.add_argument('--kl-weight', type=float, default=None, help='--guard kfsoft / replay only: weight on the KL to the frozen parent (replay: or the CE) over those rows')
    a.add_argument('--guard-soft', default=None, help="--guard kfsoft only: softness of the graded mask (kf.factors soft=); default 1 (L11); L13 uses 10; 'hard' = the hard mask with the KL replay (L14)")
    a.add_argument('--guard-energy', type=float, default=0.99)
    a.add_argument('--guard-every', type=int, default=500, help='re-measure the guard factors every this many updates')
    a.add_argument('--parent', default=PARENT, help='parent checkpoint (default: the s200 parent)')
    a.add_argument('--probe', default=SP.PROBE, help='sheet probe file (default: the shared probe)')
    a.add_argument('--eval-rows', default=None, help='eval file for --cells l3/l4 (default eval-rows-l3) or l5 (default eval-rows-l5)')
    a.add_argument('--diary-compare', default=DIARY_LOG, help="main-brain log to compare the diary with; 'none' skips (recorded as skipped)")
    a.add_argument('--diary-cache', default=None, help='arm LB guard: load the diary rows from this file if it exists instead of rebuilding')
    a.add_argument('--diary-any', action='store_true', help='arm LB guard: allow a rebuilt diary pool from a train.jsonl whose sha256 is not the skills seed-1 build (' + DIARY_TRAIN_SHA256[:12] + '; recorded as train_sha256_checked false)')
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
        check_guard_args(a.arm, a.guard, a.guard_src, a.guard_energy, a.guard_every, a.kl_replay_rows, a.kl_weight, a.guard_soft, a.replay_loss, a.replay_freeze)   # refuse before any work
        steps = [int(x) for x in a.steps.split(',')]
        harm_steps = resolve_harm_steps(steps, a.harm_steps, a.no_harm)
        stop_if_drop = parse_stop_if_drop(a.stop_if_drop, harm_steps)
        if a.harm_dev_big and not harm_steps:
            raise SystemExit('--harm-dev-big needs harm steps (--harm-steps, or --steps with an entry > 0, and not --no-harm)')
        from domain.mode import CONST_PATH
        addon_size(a.arm, json.load(open(CONST_PATH)), a.addon_rank, a.addon_alpha)   # refuse LB overrides before any work
        train(a.arm, a.updates, a.threads, a.out, steps,
              train_path=a.rows, cells=a.cells, addon_rank=a.addon_rank, addon_alpha=a.addon_alpha,
              harm_steps=harm_steps, dev=a.dev, keep_final=a.keep_final, guard=a.guard,
              guard_energy=a.guard_energy, guard_every=a.guard_every, guard_src=a.guard_src,
              parent=a.parent, probe=a.probe, eval_rows=a.eval_rows, diary_compare=a.diary_compare, diary_cache=a.diary_cache, diary_any=a.diary_any,
              kl_replay_rows=a.kl_replay_rows, kl_weight=a.kl_weight, guard_soft=a.guard_soft,
              seed=a.seed, first_call_weight=a.first_call_weight, replay_loss=a.replay_loss, dev_any=a.dev_any, harm_dev_big=a.harm_dev_big,
              replay_freeze=a.replay_freeze, stop_if_drop=stop_if_drop)


if __name__ == '__main__':
    main()
