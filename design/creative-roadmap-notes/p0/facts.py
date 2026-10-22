"""Static facts for the creative-model roadmap (no training, CPU):
1. program coverage (progparse.row_targets) per family on train and on every dev split, with the talker mode the
   targets assign (NUM / WORD / GEN);
2. B2 parameter count per module (S cfg, copy=True) from the B2_s100 checkpoint;
3. held-out (dev/family) reachability: is the numeric answer the value of some program of <= 2 executor ops over the
   B2 workspace (16 prompt numbers + constants 1 2 10 100)? Non-numeric answers cannot come from the NUM path at all.
Run from the B2 worktree root: python facts.py DATA_DIR CKPT OUT.json
"""
import json, re, sys
from collections import Counter, defaultdict
import numpy as np
from custom_io.data import load_rows
from custom_io.models import progparse as pp

data, ckpt, out = sys.argv[1:4]
res = {}

# 1. coverage
cov = {}
for name in ['train'] + ['dev/' + s for s in ('in_dist', 'answer', 'frame', 'vocab', 'variant', 'family')]:
    rows = load_rows(f'{data}/{name}.jsonl')
    c = pp.coverage(rows)
    cov[name] = c
res['coverage'] = cov
tr = cov['train']['by_family']
res['train_families_with_programs'] = sorted(f for f, c in tr.items() if c['prog'] >= 50)
res['train_families_partial_programs'] = sorted(f for f, c in tr.items() if 0 < c['prog'] < 50)
res['train_families_no_programs'] = sorted(f for f, c in tr.items() if c['prog'] == 0)

# 2. params per module
import torch
from custom_io.models import load_model
m = load_model(ckpt)
groups = defaultdict(int)
for n, p in m.named_parameters():
    top = n.split('.')[0]
    g = {'reader': 'reader (char conv + embeddings; tok table also = GEN readout)', 'core': 'core (2 controller blocks, looped 8x)'}.get(top)
    if g is None:
        g = ('program heads (op_head, q_a, q_b, k_slot, ln_k, ln_z)' if top in ('op_head', 'q_a', 'q_b', 'k_slot', 'ln_k', 'ln_z') else
             'workspace / value codes (vcode, stype, ordinal, op_emb, step_emb, src, ctrl, res_from_z)' if top in ('vcode', 'stype', 'ordinal', 'op_emb', 'step_emb', 'src', 'ctrl', 'res_from_z') else
             'talker heads (mode, ans ptr, word ptr + keys, GEN readout bias/ln, copy)' )
    groups[g] += p.numel()
res['params'] = dict(total=m.n_params(), by_group=dict(groups))

# 3. reachability on the held-out families
OPF = [lambda a, b: a + b, lambda a, b: a - b, lambda a, b: a * b,
       lambda a, b: a // b if b and a % b == 0 else None, lambda a, b: a % b if b else None,
       min, max, lambda a, b: (a > b) - (a < b)]


def reach(nums, depth):
    base = set(nums[:pp.N_NUM]) | set(pp.CONSTS)
    lvl1 = {f(a, b) for a in base for b in base for f in OPF} - {None}
    if depth == 1:
        return base | lvl1
    lvl2 = set()
    for v in lvl1:
        pool = base | {v}
        for a in pool:
            for f in OPF:
                for x, y in ((a, v), (v, a)):
                    r = f(x, y)
                    if r is not None:
                        lvl2.add(r)
    return base | lvl1 | lvl2


fam = load_rows(f'{data}/dev/family.jsonl')
rr = defaultdict(lambda: Counter())
for r in fam:
    a = r['answer']
    c = rr[r['family']]
    c['n'] += 1
    if not re.fullmatch(r'-?\d+', a):
        c['non_numeric'] += 1
        q = r['prompt']
        if all(ch in q for ch in a):
            c['non_numeric_all_chars_in_prompt'] += 1
        continue
    nums = pp.prompt_numbers(r['prompt'])
    v = int(a)
    c['numeric'] += 1
    c['in_prompt'] += v in nums
    c['reach_1op'] += v in reach(nums, 1)
    c['reach_le2op'] += v in reach(nums, 2)
res['heldout_reachability'] = {f: dict(c) for f, c in rr.items()}
res['heldout_examples'] = {f: [dict(prompt=r['prompt'], answer=r['answer'], steps=r['steps'], variant=r.get('variant')) for r in fam if r['family'] == f][:3]
                           for f in sorted({r['family'] for r in fam})}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(dict(with_prog=res['train_families_with_programs'], partial=res['train_families_partial_programs'],
                      none=res['train_families_no_programs'], params=res['params'], reach=res['heldout_reachability'],
                      dev_family_cov=cov['dev/family']['by_family']), indent=1))
