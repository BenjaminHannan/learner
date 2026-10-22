#!/usr/bin/env python3
"""Train one talker-gap arm (b0, b0_nothinker or p0) on the cached EmbeddingGemma states, then evaluate it.

  /Users/ben-hannan/ucv4/venv/bin/python run_arm.py --arm b0 --seed 1 [--steps 3000] [--out DIR]
  /Users/ben-hannan/ucv4/venv/bin/python run_arm.py --selftest

Reads rows_<s>.json, states_<s>.npy, tok_len_<s>.npy, word_tok_<s>.npy from common.CACHE (prep_states.py output).
Trains on 'train'; evaluates on 'dev' and 'practised'. Writes into --out: log.txt, hits_<s>.json, errors_dev.json,
model.pt, results.json (written last).
"""
import argparse
import copy
import json
import math
import os
import random
import sys
import tempfile
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
from models import ARM_KINDS, Arm  # noqa: E402

# ---- fixed config: identical for every arm, no per-arm tuning ----
BATCH = 64
STEPS = 3000
LR = 1e-3
BETAS = (0.9, 0.95)
WEIGHT_DECAY = 0.01
WARMUP = 200
CLIP = 1.0
LOG_EVERY = 100
EVAL_BATCH = 256
TIME_ROWS = 200
TIME_WARMUP = 5
N_ERRORS = 15
SHORT_LEN = 8
EVAL_SPLITS = ('dev', 'practised')
ALL_SPLITS = ('train',) + EVAL_SPLITS
SELFTEST_N = {'train': 200, 'dev': 60, 'practised': 60}

REQUIRED_KEYS = ['arm', 'seed', 'steps', 'device', 'n_params', 'decode_ms_per_answer', 'loss_check',
                 'splits', 'seconds']
REQUIRED_SPLIT_KEYS = ['n', 'n_short', 'n_yesno', 'exact', 'short_em', 'yesno_em', 'hard_em', 'n_hard',
                       'short_em_le8', 'n_short_le8', 'short_em_gt8', 'n_short_gt8', 'errors_short',
                       'yesno_pred_span', 'oracle_short_em', 'lesion_short_em', 'lesion_yesno_em',
                       'lesion_no_donor']
ERROR_KEYS = ['total', 'unreachable', 'mode_error', 'wrong_location', 'wrong_edges', 'same_span_string_miss']


def missing_keys(res):
    miss = [k for k in REQUIRED_KEYS if k not in res]
    for s in EVAL_SPLITS:
        sp = res.get('splits', {}).get(s, {})
        miss += [f'{s}.{k}' for k in REQUIRED_SPLIT_KEYS if k not in sp]
        miss += [f'{s}.errors_short.{k}' for k in ERROR_KEYS if k not in sp.get('errors_short', {})]
    return miss


def _path(d, name, split):
    return os.path.join(d, f'{name}_{split}.npy')


def targets(rows):
    """mode: 0 yes, 1 no, 2 span (every short_answer row). start/end = gold_words or -1."""
    mode = np.zeros(len(rows), np.int64)
    se = np.full((len(rows), 2), -1, np.int64)
    for i, r in enumerate(rows):
        if r['type'] == 'short_answer':
            mode[i] = 2
            if r['gold_words'] is not None:
                se[i] = r['gold_words']
        else:
            a = C.en_norm(r['answer'])
            if a == 'yes':
                mode[i] = 0
            elif a == 'no':
                mode[i] = 1
            else:
                raise ValueError(f"yes/no row {r['id']} has answer {r['answer']!r}")
    return mode, se[:, 0].copy(), se[:, 1].copy()


def load_split(cache, split):
    with open(os.path.join(cache, f'rows_{split}.json')) as f:
        rows = json.load(f)
    d = {'rows': rows,
         'states': np.load(_path(cache, 'states', split)),          # float16 [N,T,768], kept as float16
         'lens': np.load(_path(cache, 'tok_len', split)).astype(np.int64),
         'word_tok': np.load(_path(cache, 'word_tok', split)).astype(np.int64)}
    assert d['states'].shape[0] == len(rows) == len(d['lens']) == len(d['word_tok']), split
    d['n_words'] = (d['word_tok'][:, :, 0] >= 0).sum(1).astype(np.int64)  # reachable words form a prefix
    d['mode'], d['start'], d['end'] = targets(rows)
    d['kind'] = [r['kind'] for r in rows]
    d['ans'] = [C.en_norm(r['answer']) for r in rows]
    return d


def _t(a, device):
    return torch.from_numpy(np.ascontiguousarray(a)).to(device)


def _states(d, idx, T, device):
    return torch.from_numpy(np.ascontiguousarray(d['states'][idx, :T])).float().to(device)


def make_batch(d, idx, device):
    lens = d['lens'][idx]
    T = max(1, int(lens.max()))                     # trim padding: masked everywhere, outputs unchanged
    return (_states(d, idx, T, device), _t(lens, device), _t(d['word_tok'][idx], device),
            _t(d['n_words'][idx], device), _t(d['mode'][idx], device),
            _t(d['start'][idx], device), _t(d['end'][idx], device))


def lr_mult(step, steps):
    if step < WARMUP:
        return (step + 1) / WARMUP
    prog = (step - WARMUP) / max(1, steps - WARMUP)
    return 0.5 * (1.0 + math.cos(math.pi * min(1.0, prog)))


def batches(n, rng):
    while True:
        perm = rng.permutation(n)
        for i in range(0, n - BATCH + 1, BATCH):
            yield perm[i:i + BATCH]


@torch.no_grad()
def batch_loss(model, d, idx, device):
    model.eval()
    st, ln, wt, nw, my, sy, ey = make_batch(d, idx, device)
    return float(model.head.loss(model(st, ln, wt, nw), my, sy, ey))


def train(model, tr, steps, device, seed, say):
    opt = torch.optim.AdamW(model.parameters(), lr=LR, betas=BETAS, weight_decay=WEIGHT_DECAY)
    gen = batches(len(tr['rows']), np.random.default_rng(seed))
    model.train()
    for step in range(steps):
        lr = LR * lr_mult(step, steps)
        for g in opt.param_groups:
            g['lr'] = lr
        st, ln, wt, nw, my, sy, ey = make_batch(tr, next(gen), device)
        loss = model.head.loss(model(st, ln, wt, nw), my, sy, ey)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), CLIP)
        opt.step()
        if step % LOG_EVERY == 0 or step == steps - 1:
            say(f'step {step} train_batch_loss {loss.item():.4f} lr {lr:.3e}')


def pred_string(row, mode, s, e):
    if mode == 0:
        return 'yes'
    if mode == 1:
        return 'no'
    s, e = int(s), int(e)
    if s < 0:
        return ''
    spans = C.word_spans(row['passage'])
    return ' '.join(row['passage'][a:b] for a, b in spans[s:e + 1])


@torch.no_grad()
def predict(model, d, device, donor=None):
    """Mode, start, end per row. With donor (index array), notes (or states for p0) come from the donor row."""
    model.eval()
    n = len(d['rows'])
    mode = np.zeros(n, np.int64)
    S = np.full(n, -1, np.int64)
    E = np.full(n, -1, np.int64)
    for i0 in range(0, n, EVAL_BATCH):
        idx = np.arange(i0, min(n, i0 + EVAL_BATCH))
        didx = idx if donor is None else donor[idx]
        T = max(1, int(d['lens'][idx].max()), int(d['lens'][didx].max()))
        lens, wt, nw = _t(d['lens'][idx], device), _t(d['word_tok'][idx], device), _t(d['n_words'][idx], device)
        if donor is None:
            out = model(_states(d, idx, T, device), lens, wt, nw)
        elif model.thinker is None:
            out = model(_states(d, didx, T, device), lens, wt, nw)
        else:
            notes = model.notes_of(_states(d, didx, T, device), _t(d['lens'][didx], device))
            out = model(None, lens, wt, nw, notes=notes)
        m, s, e = model.head.decode(out, nw)
        mode[idx] = m.cpu().numpy()
        S[idx] = s.cpu().numpy()
        E[idx] = e.cpu().numpy()
    return mode, S, E


def score(rows, mode, S, E):
    hits = np.zeros(len(rows), np.int64)
    preds = []
    for i, r in enumerate(rows):
        p = pred_string(r, mode[i], S[i], E[i])
        ok = (int(mode[i]) != 2 or int(S[i]) >= 0) and C.is_hit(p, r['accepted'])
        hits[i] = int(ok)
        preds.append(p)
    return hits, preds


def donor_index(d):
    """Lesion donors: within each kind, roll 1, 2, ... until a row with a different canonical answer."""
    kinds = np.array(d['kind'])
    donor = np.arange(len(kinds))
    missing = 0
    for k in np.unique(kinds):
        g = np.where(kinds == k)[0]
        L = len(g)
        for j, i in enumerate(g):
            found = None
            for o in range(1, L):
                c = g[(j + o) % L]
                if d['ans'][c] != d['ans'][i]:
                    found = c
                    break
            if found is None:
                missing += 1
            else:
                donor[i] = found
    return donor, missing


def summarize(d, mode, S, E, hits, preds, lhits, missing):
    rows = d['rows']
    n = len(rows)
    short = np.array([r['type'] == 'short_answer' for r in rows])
    hard = np.array([C.hard_row(r) for r in rows])
    alen = np.array([len(r['answer']) for r in rows])
    le8 = short & (alen <= SHORT_LEN)
    gt8 = short & ~le8
    allm = np.ones(n, bool)

    def em(h, mask):
        return float(h[mask].mean()) if mask.any() else None

    err = {k: 0 for k in ERROR_KEYS}
    for i in np.where(short & (hits == 0))[0]:
        err['total'] += 1
        g = rows[i]['gold_words']
        if g is None:
            key = 'unreachable'
        elif int(mode[i]) != 2 or int(S[i]) < 0:
            key = 'mode_error'
        else:
            s, e = int(S[i]), int(E[i])
            gs, ge = int(g[0]), int(g[1])
            if max(s, gs) > min(e, ge):
                key = 'wrong_location'
            elif (s, e) != (gs, ge):
                key = 'wrong_edges'
            else:
                key = 'same_span_string_miss'
        err[key] += 1
    orc = [C.is_hit(pred_string(rows[i], 2, *rows[i]['gold_words']), rows[i]['accepted'])
           for i in np.where(short)[0] if rows[i]['gold_words'] is not None]
    return {'n': n, 'n_short': int(short.sum()), 'n_yesno': int((~short).sum()),
            'exact': em(hits, allm), 'short_em': em(hits, short), 'yesno_em': em(hits, ~short),
            'hard_em': em(hits, hard), 'n_hard': int(hard.sum()),
            'short_em_le8': em(hits, le8), 'n_short_le8': int(le8.sum()),
            'short_em_gt8': em(hits, gt8), 'n_short_gt8': int(gt8.sum()),
            'errors_short': err,
            'yesno_pred_span': int(((~short) & (mode == 2)).sum()),
            'oracle_short_em': float(np.mean(orc)) if orc else None,
            'lesion_short_em': em(lhits, short), 'lesion_yesno_em': em(lhits, ~short),
            'lesion_no_donor': int(missing)}


def time_decode(model, d):
    """Milliseconds per answer at batch 1 on CPU: thinker + head + decode + string, after a few warm-up rows."""
    cpu = copy.deepcopy(model).cpu().eval()
    n = min(TIME_ROWS, len(d['rows']))

    def one(i):
        idx = np.array([i])
        T = max(1, int(d['lens'][i]))
        out = cpu(_states(d, idx, T, 'cpu'), _t(d['lens'][idx], 'cpu'), _t(d['word_tok'][idx], 'cpu'),
                  _t(d['n_words'][idx], 'cpu'))
        m, s, e = cpu.head.decode(out, _t(d['n_words'][idx], 'cpu'))
        return pred_string(d['rows'][i], int(m[0]), int(s[0]), int(e[0]))

    with torch.no_grad():
        for i in range(min(TIME_WARMUP, n)):
            one(i)
        t0 = time.perf_counter()
        for i in range(n):
            one(i)
        return (time.perf_counter() - t0) * 1000.0 / n


def run(arm_kind, seed, steps, cache_dir, out_dir, verbose=True):
    t0 = time.time()
    if arm_kind not in ARM_KINDS:
        raise ValueError(f'unknown arm {arm_kind!r}')
    os.makedirs(out_dir, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    log = open(os.path.join(out_dir, 'log.txt'), 'w')

    def say(msg):
        log.write(msg + '\n')
        log.flush()
        if verbose:
            print(msg, flush=True)

    try:
        say(f'arm {arm_kind} seed {seed} steps {steps} device {device}')
        data = {s: load_split(cache_dir, s) for s in ALL_SPLITS}
        tr = data['train']
        model = Arm(arm_kind).to(device)
        n_params = model.n_params()
        fixed = np.arange(min(BATCH, len(tr['rows'])))
        loss_start = batch_loss(model, tr, fixed, device)
        train(model, tr, steps, device, seed, say)
        loss_end = batch_loss(model, tr, fixed, device)
        say(f'fixed-batch loss start {loss_start:.4f} end {loss_end:.4f}')
        decode_ms = time_decode(model, data['dev'])
        splits = {}
        for s in EVAL_SPLITS:
            d = data[s]
            mode, S, E = predict(model, d, device)
            hits, preds = score(d['rows'], mode, S, E)
            donor, missing = donor_index(d)
            lmode, lS, lE = predict(model, d, device, donor=donor)
            lhits, _ = score(d['rows'], lmode, lS, lE)
            splits[s] = summarize(d, mode, S, E, hits, preds, lhits, missing)
            with open(os.path.join(out_dir, f'hits_{s}.json'), 'w') as f:
                json.dump([int(x) for x in hits], f)
            if s == 'dev':
                errs = [{'id': r['id'], 'kind': r['kind'], 'prompt': r['prompt'], 'gold': r['answer'],
                         'pred': preds[i]} for i, r in enumerate(d['rows']) if hits[i] == 0][:N_ERRORS]
                with open(os.path.join(out_dir, 'errors_dev.json'), 'w') as f:
                    json.dump(errs, f, indent=1)
            say(f"{s}: exact {splits[s]['exact']:.4f} short {splits[s]['short_em']} "
                f"yesno {splits[s]['yesno_em']} lesion_short {splits[s]['lesion_short_em']}")
        torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()},
                   os.path.join(out_dir, 'model.pt'))
        results = {'arm': arm_kind, 'seed': seed, 'steps': steps, 'device': str(device),
                   'n_params': n_params, 'decode_ms_per_answer': decode_ms,
                   'config': {'batch': BATCH, 'lr': LR, 'betas': list(BETAS), 'weight_decay': WEIGHT_DECAY,
                              'warmup': WARMUP, 'clip': CLIP},
                   'loss_check': {'fixed_batch_loss_start': loss_start, 'fixed_batch_loss_end': loss_end},
                   'splits': splits, 'seconds': round(time.time() - t0, 1)}
        miss = missing_keys(results)
        if miss:
            raise KeyError(f'results missing {miss}')
        with open(os.path.join(out_dir, 'results.json'), 'w') as f:
            json.dump(results, f, indent=2)
        say(f'wrote {out_dir}/results.json')
        return results
    finally:
        log.close()


def make_selftest_cache(cache, dest):
    """First rows of the real cache (train 200, dev 60, practised 60); arrays are sliced via mmap, never fully loaded."""
    for s, n in SELFTEST_N.items():
        with open(os.path.join(cache, f'rows_{s}.json')) as f:
            rows = json.load(f)[:n]
        with open(os.path.join(dest, f'rows_{s}.json'), 'w') as f:
            json.dump(rows, f)
        for name in ('states', 'tok_len', 'word_tok'):
            arr = np.load(_path(cache, name, s), mmap_mode='r')[:n]
            np.save(_path(dest, name, s), np.ascontiguousarray(arr))


def selftest():
    failures = []

    def check(name, ok, detail=''):
        print(f"{'ok  ' if ok else 'FAIL'} {name}{' ' + detail if detail else ''}", flush=True)
        if not ok:
            failures.append(name)

    tmp = tempfile.mkdtemp(prefix='run_arm_selftest_')
    cache = os.path.join(tmp, 'cache')
    os.makedirs(cache)
    make_selftest_cache(C.CACHE, cache)
    check('fake cache written', all(os.path.exists(_path(cache, 'states', s)) for s in ALL_SPLITS))
    for kind in ARM_KINDS:
        out = os.path.join(tmp, f'out_{kind}')
        run(kind, 1, 40, cache, out, verbose=False)
        with open(os.path.join(out, 'results.json')) as f:
            res = json.load(f)
        miss = missing_keys(res)
        check(f'{kind} results keys', not miss, str(miss[:5]))
        for s in EVAL_SPLITS:
            with open(os.path.join(out, f'hits_{s}.json')) as f:
                hl = json.load(f)
            check(f'{kind} hits_{s} length', len(hl) == res['splits'][s]['n'] == SELFTEST_N[s],
                  f'{len(hl)}')
            e = res['splits'][s]['errors_short']
            check(f'{kind} {s} error buckets sum', sum(e[k] for k in ERROR_KEYS[1:]) == e['total'],
                  f"total {e['total']}")
        check(f'{kind} errors_dev.json', os.path.exists(os.path.join(out, 'errors_dev.json')))
        check(f'{kind} model.pt', os.path.exists(os.path.join(out, 'model.pt')))
        lc = res['loss_check']
        check(f'{kind} loss step40 < step0', lc['fixed_batch_loss_end'] < lc['fixed_batch_loss_start'],
              f"{lc['fixed_batch_loss_start']:.4f} -> {lc['fixed_batch_loss_end']:.4f}")
        check(f'{kind} decode timed', res['decode_ms_per_answer'] > 0,
              f"{res['decode_ms_per_answer']:.2f} ms/answer, n_params {res['n_params']}")
    if failures:
        print('run_arm selftest FAILED: ' + ', '.join(failures), flush=True)
        sys.exit(1)
    print('run_arm selftest OK', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=ARM_KINDS)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--steps', type=int, default=STEPS)
    ap.add_argument('--out')
    ap.add_argument('--cache', default=C.CACHE)
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not a.arm or a.seed is None:
        ap.error('--arm and --seed are required')
    out = a.out or os.path.join(HERE, 'results', f'{a.arm}_s{a.seed}')
    run(a.arm, a.seed, a.steps, a.cache, out)


if __name__ == '__main__':
    main()
