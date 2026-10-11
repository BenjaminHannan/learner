"""L1 diagnosis: can the 3M calculator model learn joined formulas at all? (spec: far-transfer/learn/MARKS-L1-2026-10-11.md)

  python3 -m domain.far.learn_probe build
  python3 -m domain.far.learn_probe train --arm LA|LB --updates 4000 --threads N --out DIR [--steps 0,500,1000,2000,4000]

build: 6,000 F4-two and 6,000 F0-near rows from the probe generator (domain/far/sheet_probe.py), seed 93301, scored kinds
       only, no prompt in the probe file or any sheet panel (read for exclusion only). Refuses to overwrite.
train: parent checkpoint + the mode's make_row / make_opt / AddOn / loss, on those rows only (no diary, no replay).
       LA = the mode's add-on (base frozen); LB = every weight at the mode's night lr. Same data order for both arms.
       Scores with domain.score.score on a checkpoint saved by the mode's save_ckpt at each step.
Diagnosis only: the mode is not run and no panel row is trained.
"""
import argparse
import hashlib
import json
import os
import random
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


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def eval_sets(train_rows):
    """The scored cells: name -> rows (each row's id made unique across cells; the row's split is the cell name)."""
    probe = [r for r in load_jsonl(SP.PROBE) if r['kind'] in SP.SCORED]
    sets = {c: [dict(r, split=n) for r in probe if r['split'] == c] for n, c in
            (('F4-two', 'F4-two'), ('F0-near', 'F0-near'), ('F2b-rows', 'F2b-rows'))}
    f4 = [r for r in train_rows if r['split'] == 'F4-two']
    fit = random.Random(SEED).sample(f4, FIT_N)
    sets['fit'] = [dict(r, id='fit-' + r['id'], split='fit') for r in fit]
    return sets


def score_step(ck, m, addon, sets, out, arm, step, t_train, threads):
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
        f.write(json.dumps({'arm': arm, 'step': step, 'cells': cells, 'secs': secs, 'train_secs': round(t_train, 1)}) + '\n')
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


def train(arm, updates, threads, out, steps, parent=PARENT, train_path=TRAIN_ROWS, log_every=100):
    import torch
    from custom_io.data import Dataset, collate, to_device
    from custom_io.models import load_model
    from domain.mode import AddOn, CONST_PATH, make_opt
    torch.set_num_threads(threads)
    assert arm in ('LA', 'LB')
    assert steps and max(steps) <= updates and min(steps) >= 0, (steps, updates)
    cons = json.load(open(CONST_PATH))
    os.makedirs(out, exist_ok=True)
    if os.path.exists(os.path.join(out, 'scores.jsonl')):
        raise SystemExit(f'refusing to reuse {out}: scores.jsonl exists')
    train_rows = load_jsonl(train_path)
    sets = eval_sets(train_rows)
    ck = torch.load(parent, map_location='cpu', weights_only=True)
    torch.manual_seed(SEED)
    m = load_model(parent).eval()
    rows, drops = make_rows(m, train_rows, cons)
    print(f'{arm}: {len(rows)} of {len(train_rows)} rows usable; dropped {dict(drops)}', flush=True)
    ds = Dataset(rows, m.vocab)
    if arm == 'LA':
        addon = AddOn(m, cons['addon_rank'], cons['addon_alpha'], SEED)
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
        score_step(ck, m, addon, sets, out, arm, 0, t_train, threads)
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
            score_step(ck, m, addon, sets, out, arm, u, t_train, threads)
            t_seg = time.time()
    m.eval()
    print(f'{arm} done: {updates} updates, train {t_train:.1f}s ({t_train / max(updates, 1):.3f} s/update)', flush=True)
    return t_train / max(updates, 1)


def main(argv=None):
    a = argparse.ArgumentParser(description='L1: can the 3M model learn joined formulas? (diagnosis only)')
    a.add_argument('stage', choices=['build', 'train'])
    a.add_argument('--arm', choices=['LA', 'LB'])
    a.add_argument('--updates', type=int, default=4000)
    a.add_argument('--threads', type=int, default=1)
    a.add_argument('--out')
    a.add_argument('--steps', default=DEFAULT_STEPS, help='comma list of update counts to score at')
    a = a.parse_args(argv)
    if a.stage == 'build':
        build()
    else:
        assert a.arm and a.out, 'train needs --arm and --out'
        train(a.arm, a.updates, a.threads, a.out, [int(x) for x in a.steps.split(',')])


if __name__ == '__main__':
    main()
