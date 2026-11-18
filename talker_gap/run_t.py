#!/usr/bin/env python3
"""T-arms (SPEC Amendment 2): t1, t1_nothinker and t2 = the T1 decoder (models_t1.T1Talker) fed by thinker notes.

  PYTHONPATH=/Users/ben-hannan/tf519 /Users/ben-hannan/ucv4/venv/bin/python run_t.py --arm t1 --seed 0
  PYTHONPATH=... run_t.py --arm t1_nothinker --seed 0
  PYTHONPATH=... run_t.py --arm t2 --seed 0 --pretrain-dir DIR --pretrain-steps N
  PYTHONPATH=... run_t.py --arm t1 --seed 0 --time-updates 20   (timing only: writes nothing)
  PYTHONPATH=... run_t.py --selftest

Arms
  t1           Thinker (768->256, 2 layers looped 3x). Memory = the three loop notes stacked (notes[1:]),
               mem_tok = reader-token index of each slot. The decoder cross-attends over all of them (SPEC T1 row).
  t1_nothinker Thinker with its core layers removed: memory = notes[0] = LayerNorm(Linear(768->256) + pos). Same decoder.
  t2           t1 after a pretraining stage on DIR's 'fw_pre' rows (fresh optimiser and schedule), then the TEACH stage.
  t1_long      t1 trained for T1_LONG_STEPS TEACH updates (one warm-up/cosine), T2's total update count without the
               FineWeb text (SPEC Amendment 2c control). Its default --steps is T1_LONG_STEPS.

Target (say-back), never truncated: question (verbatim) + ' ' + answer (verbatim for short answers;
en_norm'd 'yes'/'no' for yes/no rows). Rows whose target is longer than MAX_TGT are dropped from training and
counted in config.n_train_filtered. Pretraining rows may carry their own 'target' string; that is used as-is.
Scoring: the answer part is the text after the echoed question (else after the last '?', else the whole string),
then C.is_hit against the accepted answers.

Fixed config is run_arm's (batch 64, 3000 updates, AdamW 1e-3, betas, wd, warm-up 200, cosine, clip 1.0) and the same
24,000-row TEACH train rows as B0 (the cache). Reads only the cache directory; never touches sealed, GOLD, reserved,
blind or FRESH-R7 files.
"""
import argparse
import copy
import json
import os
import random
import string
import sys
import tempfile
import time

import numpy as np
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import run_arm as RA  # noqa: E402
import models_t1 as T1  # noqa: E402
from models import Thinker  # noqa: E402

ARMS = ('t1', 't1_nothinker', 't2', 't1_long')
T1_LONG_STEPS = 6000    # Amendment 2b/2c: same total updates as t2 (3000 pretrain + 3000 TEACH)
MAX_TGT = 160          # decoder max_target_len (pos_emb size, shared by every arm). Longer targets are filtered, never cut.
D_MEM = 256
PRE_SPLIT = 'fw_pre'
TIME_SKIP = 2          # first updates excluded from seconds/update (kernel warm-up)
TOP_KEYS = {'arm', 'config', 'decode_ms_per_answer', 'device', 'loss_check', 'n_params', 'seconds', 'seed',
            'splits', 'steps'}


# ============================================================ targets, scoring
def target_text(row):
    """Say-back target: question + ' ' + answer. Pretraining rows may carry their own 'target' string."""
    if 'target' in row:
        return row['target']
    a = C.en_norm(row['answer']) if row.get('type') == 'yes_no' else row['answer']
    return row['question'] + ' ' + a


def pretrain_target(row):
    """SPEC Amendment 2: FineWeb cloze target = '<cloze sentence> ? <span>' (say-back, never cut)."""
    return row['question'] + ' ? ' + row['answer']


def answer_part(gen, question):
    """Answer = text after the echoed question; else after the last '?'; else the whole string."""
    if gen.startswith(question):
        return gen[len(question):]
    if '?' in gen:
        return gen[gen.rfind('?') + 1:]
    return gen


def score(rows, gens):
    aparts = [answer_part(g, r['question']) for g, r in zip(gens, rows)]
    hits = np.array([int(C.is_hit(a, r['accepted'])) for a, r in zip(aparts, rows)], np.int64)
    echo = np.array([g.startswith(r['question']) for g, r in zip(gens, rows)], bool)
    return aparts, hits, echo


# ============================================================ data
def load_split(cache, split, evaluate):
    with open(os.path.join(cache, f'rows_{split}.json')) as f:
        rows = json.load(f)
    d = {'rows': rows,
         'states': np.load(RA._path(cache, 'states', split), mmap_mode='r'),   # float16 [N,T,768]
         'lens': np.load(RA._path(cache, 'tok_len', split)).astype(np.int64),
         'toff': np.load(RA._path(cache, 'tok_off', split)).astype(np.int64)}  # char spans in row['prompt']
    assert d['states'].shape[0] == len(rows) == len(d['lens']) == len(d['toff']), split
    if evaluate:
        d['kind'] = [r['kind'] for r in rows]
        d['ans'] = [C.en_norm(r['answer']) for r in rows]
    return d


def prep(d, stoi, max_tgt, with_target):
    """Char ids for prompts and (optionally) targets. Rows whose target is too long go to n_filtered, not into 'ok'."""
    d['pids'] = [np.array(T1.encode_text(r['prompt'], stoi), np.int64) for r in d['rows']]
    allp = np.concatenate(d['pids']) if d['pids'] else np.zeros(0, np.int64)
    d['unk_prompt_char_frac'] = float((allp == T1.UNK).mean()) if allp.size else 0.0
    if with_target:
        tg = [T1.encode_text(target_text(r), stoi) for r in d['rows']]
        d['tids'] = tg
        d['ok'] = np.array([i for i, t in enumerate(tg) if len(t) <= max_tgt], np.int64)
        d['n_filtered'] = len(tg) - len(d['ok'])
        allt = [c for t in tg for c in t]
        d['unk_target_char_frac'] = float(np.mean(np.array(allt) == T1.UNK)) if allt else 0.0
    return d


def make_batch(d, idx, device, src_idx=None, teacher=False):
    """idx: rows that supply prompt, tok_off and target. src_idx: rows whose thinker states are used (lesion donors)."""
    src = idx if src_idx is None else src_idx
    lens_src = d['lens'][src]
    Tb = max(1, int(d['lens'][idx].max()), int(lens_src.max()))
    B = len(idx)
    states = torch.from_numpy(np.ascontiguousarray(d['states'][src, :Tb])).float().to(device)
    lens = torch.from_numpy(lens_src).to(device)
    ar = torch.arange(Tb, device=device)
    mem_mask = ar[None, :] < lens[:, None]
    mem_tok = ar[None, :].expand(B, Tb)                       # slot t of a note = reader token t
    toff = torch.from_numpy(np.ascontiguousarray(d['toff'][idx, :Tb])).to(device)
    P = max(len(d['pids'][i]) for i in idx)
    pids = torch.zeros(B, P, dtype=torch.long)
    pmask = torch.zeros(B, P, dtype=torch.bool)
    for b, i in enumerate(idx):
        p = d['pids'][i]
        pids[b, :len(p)] = torch.from_numpy(p)
        pmask[b, :len(p)] = True
    batch = {'states': states, 'lens': lens, 'mem_mask': mem_mask, 'mem_tok': mem_tok,
             'pids': pids.to(device), 'pmask': pmask.to(device), 'toff': toff}
    if teacher:
        tin, tout, tm = T1.make_teacher([d['tids'][i] for i in idx], MAX_TGT)   # raises if too long
        batch.update(tin=tin.to(device), tout=tout.to(device), tm=tm.to(device))
    return batch


# ============================================================ model
class TArm(nn.Module):
    def __init__(self, kind, vocab_size):
        super().__init__()
        if kind not in ARMS:
            raise ValueError(f'unknown arm {kind!r}')
        self.kind = kind
        self.thinker = Thinker(d=D_MEM, use_layers=(kind != 't1_nothinker'))
        self.talker = T1.T1Talker(vocab_size, max_target_len=MAX_TGT)

    def encode(self, b):
        notes = self.thinker(b['states'], b['lens'])
        if self.kind == 't1_nothinker':
            mem, mm, mt = notes[0], b['mem_mask'], b['mem_tok']
        else:                                                   # all loop notes, stacked along the slot axis
            k = len(notes) - 1
            mem = torch.cat(notes[1:], dim=1)
            mm = b['mem_mask'].repeat(1, k)
            mt = b['mem_tok'].repeat(1, k)
        return self.talker.encode(mem, mm, mt, b['pids'], b['pmask'], b['toff'])

    def loss(self, b):
        return self.talker.nll(self.encode(b), b['tin'], b['tout'], b['tm'])

    def n_params(self):
        return sum(p.numel() for p in self.parameters())


# ============================================================ training
def _sync(device):
    if device.type == 'mps':
        torch.mps.synchronize()


@torch.no_grad()
def batch_loss(model, d, idx, device):
    model.eval()
    return float(model.loss(make_batch(d, idx, device, teacher=True)))


def train_stage(model, d, steps, device, seed, say, tag, times=None):
    """One optimiser + warm-up/cosine stage (run_arm's settings). times: list to fill with seconds per update."""
    opt = torch.optim.AdamW(model.parameters(), lr=RA.LR, betas=RA.BETAS, weight_decay=RA.WEIGHT_DECAY)
    pool = d['ok']
    if len(pool) < RA.BATCH:
        raise ValueError(f"need at least {RA.BATCH} usable rows, got {len(pool)}")
    gen = RA.batches(len(pool), np.random.default_rng(seed))
    model.train()
    for step in range(steps):
        lr = RA.LR * RA.lr_mult(step, steps)
        for g in opt.param_groups:
            g['lr'] = lr
        t0 = time.perf_counter()
        loss = model.loss(make_batch(d, pool[next(gen)], device, teacher=True))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), RA.CLIP)
        opt.step()
        if times is not None:
            _sync(device)
            times.append(time.perf_counter() - t0)
        if step % RA.LOG_EVERY == 0 or step == steps - 1:
            say(f'{tag} step {step} train_batch_loss {loss.item():.4f} lr {lr:.3e}')


# ============================================================ evaluation
@torch.no_grad()
def predict(model, d, device, itos, donor=None):
    """Greedy say-back per row. With donor, the thinker reads the donor row's states (shuffled-state check)."""
    model.eval()
    n = len(d['rows'])
    out = [''] * n
    for i0 in range(0, n, RA.EVAL_BATCH):
        idx = np.arange(i0, min(n, i0 + RA.EVAL_BATCH))
        b = make_batch(d, idx, device, src_idx=None if donor is None else donor[idx])
        ids = model.talker.greedy(model.encode(b))
        for j, i in enumerate(idx):
            out[i] = T1.decode_ids(ids[j], itos)
    return out


def summarize(d, aparts, hits, echo, lhits, missing):
    rows = d['rows']
    n = len(rows)
    short = np.array([r['type'] == 'short_answer' for r in rows])
    hard = np.array([C.hard_row(r) for r in rows])
    alen = np.array([len(r['answer']) for r in rows])
    le8 = short & (alen <= RA.SHORT_LEN)
    gt8 = short & ~le8
    yn = ~short
    allm = np.ones(n, bool)

    def em(h, mask):
        return float(h[mask].mean()) if mask.any() else None

    # T arms have no spans: mode_error = empty answer part, wrong_location = non-empty wrong answer,
    # span-only buckets stay 0 (they keep the run_arm key layout and the sum invariant).
    err = {k: 0 for k in RA.ERROR_KEYS}
    for i in np.where(short & (hits == 0))[0]:
        err['total'] += 1
        err['mode_error' if C.en_norm(aparts[i]) == '' else 'wrong_location'] += 1
    malformed = sum(C.en_norm(aparts[i]) not in ('yes', 'no') for i in np.where(yn)[0])
    return {'n': n, 'n_short': int(short.sum()), 'n_yesno': int(yn.sum()),
            'exact': em(hits, allm), 'short_em': em(hits, short), 'yesno_em': em(hits, yn),
            'hard_em': em(hits, hard), 'n_hard': int(hard.sum()),
            'short_em_le8': em(hits, le8), 'n_short_le8': int(le8.sum()),
            'short_em_gt8': em(hits, gt8), 'n_short_gt8': int(gt8.sum()),
            'errors_short': err,
            'yesno_pred_span': int(malformed),          # T arms: yes/no rows whose answer part is not yes/no
            'oracle_short_em': None,                    # no spans, so no oracle
            'lesion_short_em': em(lhits, short), 'lesion_yesno_em': em(lhits, yn),
            'lesion_no_donor': int(missing),
            'echo_exact': float(echo.mean()) if n else None,
            'unk_prompt_char_frac': d['unk_prompt_char_frac']}


def time_decode(model, d, itos):
    """Milliseconds per answer at batch 1 on CPU (1 torch thread): thinker + encoder + greedy + string."""
    cpu = copy.deepcopy(model).cpu().eval()
    cpu_dev = torch.device('cpu')
    n = min(RA.TIME_ROWS, len(d['rows']))

    def one(i):
        b = make_batch(d, np.array([i]), cpu_dev)
        ids = cpu.talker.greedy(cpu.encode(b))
        return T1.decode_ids(ids[0], itos)

    prev = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with torch.no_grad():
            for i in range(min(RA.TIME_WARMUP, n)):
                one(i)
            t0 = time.perf_counter()
            for i in range(n):
                one(i)
            return (time.perf_counter() - t0) * 1000.0 / n
    finally:
        torch.set_num_threads(prev)


# ============================================================ run
def run(arm, seed, steps, cache, out_dir, pretrain_dir=None, pretrain_steps=0, time_updates=0, verbose=True,
        eval_only=False):
    if arm not in ARMS:
        raise ValueError(f'unknown arm {arm!r}')
    if arm == 't2' and not (pretrain_dir and pretrain_steps > 0):
        raise ValueError('t2 needs --pretrain-dir and --pretrain-steps > 0')
    if arm != 't2' and pretrain_dir:
        raise ValueError('--pretrain-dir is only for t2')
    timing = time_updates > 0
    if eval_only and timing:
        raise ValueError('--eval-only and --time-updates do not combine')
    t0 = time.time()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    log = None
    if not timing:
        os.makedirs(out_dir, exist_ok=True)
        log = open(os.path.join(out_dir, 'log.txt'), 'a' if eval_only else 'w')

    def say(msg):
        if log is not None:
            log.write(msg + '\n')
            log.flush()
        if verbose:
            print(msg, flush=True)

    try:
        say(f'arm {arm} seed {seed} steps {steps} device {device} pretrain {pretrain_dir} {pretrain_steps}')
        tr = load_split(cache, 'train', evaluate=False)
        stoi, itos = T1.build_vocab([r['prompt'] for r in tr['rows']]
                                    + [target_text(r) for r in tr['rows']] + [string.printable])
        prep(tr, stoi, MAX_TGT, with_target=True)
        say(f"train rows {len(tr['rows'])} kept {len(tr['ok'])} filtered {tr['n_filtered']} vocab {len(itos)}")
        model = TArm(arm, len(itos)).to(device)
        n_params = model.n_params()
        fixed = tr['ok'][:RA.BATCH]
        loss_start = batch_loss(model, tr, fixed, device)
        pre_info = None
        if pretrain_dir:
            pre = load_split(pretrain_dir, PRE_SPLIT, evaluate=False)
            for r in pre['rows']:
                r['target'] = pretrain_target(r)
            pre = prep(pre, stoi, MAX_TGT, with_target=True)
            say(f"pretrain rows {len(pre['rows'])} kept {len(pre['ok'])} filtered {pre['n_filtered']} "
                f"unk_target_frac {pre['unk_target_char_frac']:.5f}")
            if not eval_only:
                train_stage(model, pre, pretrain_steps, device, seed, say, 'pretrain')
            pre_info = {'dir': pretrain_dir, 'steps': pretrain_steps, 'n_rows': len(pre['rows']),
                        'n_kept': len(pre['ok']), 'n_filtered': pre['n_filtered'],
                        'unk_target_char_frac': pre['unk_target_char_frac']}
        times = [] if timing else None
        if eval_only:
            # weights saved by an earlier run whose evaluation was killed; loss_start is reproduced by the seed
            ck = torch.load(os.path.join(out_dir, 'model.pt'), map_location='cpu')
            if ck['itos'] != itos or ck['arm'] != arm:
                raise ValueError('model.pt does not match this arm / vocabulary')
            model.load_state_dict(ck['state_dict'])
            say('eval-only: loaded model.pt, no training')
        else:
            train_stage(model, tr, time_updates if timing else steps, device, seed, say, 'teach', times=times)
        loss_end = batch_loss(model, tr, fixed, device)
        say(f'fixed-batch loss start {loss_start:.4f} end {loss_end:.4f}')
        if timing:
            per = times[TIME_SKIP:] or times
            mean_s = float(np.mean(per))
            say(f'TIMING arm {arm} device {device} updates {len(times)} skip {TIME_SKIP} '
                f'sec_per_update {mean_s:.4f} total_s {sum(times):.2f} '
                f'projected_3000_min {mean_s * RA.STEPS / 60:.1f}')
            return {'sec_per_update': mean_s, 'updates': len(times), 'device': str(device),
                    'per_update_s': times}

        # saved before evaluation so a killed eval does not lose the trained weights
        if not eval_only:
            torch.save({'state_dict': {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        'itos': itos, 'max_target_len': MAX_TGT, 'arm': arm},
                       os.path.join(out_dir, 'model.pt'))
        data = {s: prep(load_split(cache, s, evaluate=True), stoi, MAX_TGT, with_target=False)
                for s in RA.EVAL_SPLITS}
        decode_ms = time_decode(model, data['dev'], itos)
        splits = {}
        for s in RA.EVAL_SPLITS:
            d = data[s]
            gens = predict(model, d, device, itos)
            aparts, hits, echo = score(d['rows'], gens)
            donor, missing = RA.donor_index(d)
            lgens = predict(model, d, device, itos, donor=donor)
            _, lhits, _ = score(d['rows'], lgens)
            splits[s] = summarize(d, aparts, hits, echo, lhits, missing)
            with open(os.path.join(out_dir, f'hits_{s}.json'), 'w') as f:
                json.dump([int(x) for x in hits], f)
            if s == 'dev':
                errs = [{'id': r['id'], 'kind': r['kind'], 'prompt': r['prompt'], 'gold': r['answer'],
                         'pred': aparts[i]} for i, r in enumerate(d['rows']) if hits[i] == 0][:RA.N_ERRORS]
                with open(os.path.join(out_dir, 'errors_dev.json'), 'w') as f:
                    json.dump(errs, f, indent=1)
            say(f"{s}: exact {splits[s]['exact']:.4f} short {splits[s]['short_em']} "
                f"yesno {splits[s]['yesno_em']} lesion_short {splits[s]['lesion_short_em']} "
                f"echo {splits[s]['echo_exact']}")
        memory = 'notes[0] (projection only)' if arm == 't1_nothinker' else 'notes[1:] (3 loop notes stacked)'
        results = {'arm': arm, 'seed': seed, 'steps': steps, 'device': str(device), 'n_params': n_params,
                   'decode_ms_per_answer': decode_ms,
                   'config': {'batch': RA.BATCH, 'lr': RA.LR, 'betas': list(RA.BETAS),
                              'weight_decay': RA.WEIGHT_DECAY, 'warmup': RA.WARMUP, 'clip': RA.CLIP,
                              'max_target_len': MAX_TGT, 'vocab_size': len(itos), 'memory': memory,
                              'n_train_rows': len(tr['rows']), 'n_train_filtered': tr['n_filtered'],
                              'unk_train_target_char_frac': tr['unk_target_char_frac'],
                              'pretrain': pre_info},
                   'loss_check': {'fixed_batch_loss_start': loss_start, 'fixed_batch_loss_end': loss_end},
                   'splits': splits, 'seconds': round(time.time() - t0, 1)}
        miss = RA.missing_keys(results)
        if miss:
            raise KeyError(f'results missing {miss}')
        with open(os.path.join(out_dir, 'results.json'), 'w') as f:
            json.dump(results, f, indent=2)
        say(f'wrote {out_dir}/results.json')
        return results
    finally:
        if log is not None:
            log.close()


# ============================================================ self-test
def make_selftest_cache(cache, dest):
    """run_arm's small cache (train 200, dev 60, practised 60) + tok_off, and a synthetic 'fw_pre' split (128 rows; must be >= BATCH or batches() never yields)."""
    RA.make_selftest_cache(cache, dest)
    for s, n in RA.SELFTEST_N.items():
        arr = np.load(RA._path(cache, 'tok_off', s), mmap_mode='r')[:n]
        np.save(RA._path(dest, 'tok_off', s), np.ascontiguousarray(arr))
    with open(os.path.join(dest, 'rows_train.json')) as f:
        rows = json.load(f)[:128]
    with open(os.path.join(dest, f'rows_{PRE_SPLIT}.json'), 'w') as f:
        json.dump(rows, f)
    for name in ('states', 'tok_len', 'tok_off'):
        arr = np.load(RA._path(dest, name, 'train'))[:128]
        np.save(RA._path(dest, name, PRE_SPLIT), np.ascontiguousarray(arr))


def selftest():
    failures = []

    def check(name, ok, detail=''):
        print(f"{'ok  ' if ok else 'FAIL'} {name}{' ' + detail if detail else ''}", flush=True)
        if not ok:
            failures.append(name)

    check('answer_part echo', answer_part('who was near? hilda', 'who was near?') == ' hilda')
    check('answer_part after last ?', answer_part('x? no', 'who?') == ' no')
    check('answer_part whole string', answer_part('hilda', 'who?') == 'hilda')
    check('target short verbatim', target_text({'type': 'short_answer', 'question': 'Who was near?',
                                                'answer': 'Hilda'}) == 'Who was near? Hilda')
    check('target yes/no normalised', target_text({'type': 'yes_no', 'question': 'Did it go?',
                                                   'answer': 'No'}) == 'Did it go? no')

    toy = {'rows': [{'prompt': 'abc?', 'question': 'abc?', 'answer': 'x' * 5},
                    {'prompt': 'abc?', 'question': 'abc?', 'answer': 'x' * 200}]}
    stoi, _ = T1.build_vocab(['abc? x'])
    prep(toy, stoi, 50, with_target=True)
    check('long target filtered not truncated', list(toy['ok']) == [0] and toy['n_filtered'] == 1
          and len(toy['tids'][1]) == 205, f"ok {list(toy['ok'])} n_filtered {toy['n_filtered']}")

    tmp = tempfile.mkdtemp(prefix='run_t_selftest_')
    cache = os.path.join(tmp, 'cache')
    os.makedirs(cache)
    make_selftest_cache(C.CACHE, cache)
    check('fake cache written', all(os.path.exists(RA._path(cache, n, s)) for n in ('states', 'tok_off')
                                    for s in ('train', 'dev', 'practised', PRE_SPLIT)))
    n_par = {}
    for kind in ARMS:
        out = os.path.join(tmp, f'out_{kind}')
        pre_dir = cache if kind == 't2' else None
        run(kind, 1, 40, cache, out, pretrain_dir=pre_dir, pretrain_steps=(4 if kind == 't2' else 0),
            verbose=False)
        with open(os.path.join(out, 'results.json')) as f:
            res = json.load(f)
        miss = RA.missing_keys(res)
        check(f'{kind} results keys', not miss, str(miss[:5]))
        check(f'{kind} top-level keys equal B0', set(res) == TOP_KEYS, str(sorted(set(res) ^ TOP_KEYS)))
        for s in RA.EVAL_SPLITS:
            with open(os.path.join(out, f'hits_{s}.json')) as f:
                hl = json.load(f)
            sp = res['splits'][s]
            check(f'{kind} hits_{s} length', len(hl) == sp['n'] == RA.SELFTEST_N[s], f'{len(hl)}')
            e = sp['errors_short']
            check(f'{kind} {s} error buckets sum', sum(e[k] for k in RA.ERROR_KEYS[1:]) == e['total'])
            check(f'{kind} {s} echo in [0,1]', sp['echo_exact'] is not None and 0 <= sp['echo_exact'] <= 1)
        check(f'{kind} errors_dev.json', os.path.exists(os.path.join(out, 'errors_dev.json')))
        check(f'{kind} model.pt', os.path.exists(os.path.join(out, 'model.pt')))
        lc = res['loss_check']
        check(f'{kind} loss finite and step40 < step0',
              np.isfinite(lc['fixed_batch_loss_start']) and np.isfinite(lc['fixed_batch_loss_end'])
              and lc['fixed_batch_loss_end'] < lc['fixed_batch_loss_start'],
              f"{lc['fixed_batch_loss_start']:.4f} -> {lc['fixed_batch_loss_end']:.4f}")
        check(f'{kind} decode timed', res['decode_ms_per_answer'] > 0,
              f"{res['decode_ms_per_answer']:.2f} ms/answer, n_params {res['n_params']}")
        n_par[kind] = res['n_params']
        if kind == 't2':
            with open(os.path.join(out, 'log.txt')) as f:
                check('t2 pretrain stage logged', any(line.startswith('pretrain step') for line in f))
    check('t1 has more params than t1_nothinker', n_par['t1'] > n_par['t1_nothinker'], str(n_par))
    before = sorted(os.listdir(tmp))
    timed = run('t1', 1, 3, cache, os.path.join(tmp, 'timing_should_not_exist'), time_updates=3, verbose=False)
    check('timing-only writes nothing', sorted(os.listdir(tmp)) == before and timed['updates'] == 3)
    if failures:
        print('run_t selftest FAILED: ' + ', '.join(failures), flush=True)
        sys.exit(1)
    print('run_t selftest OK', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=ARMS)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--steps', type=int, default=None, help=f'default {RA.STEPS} ({T1_LONG_STEPS} for t1_long)')
    ap.add_argument('--out')
    ap.add_argument('--cache', default=C.CACHE)
    ap.add_argument('--pretrain-dir')
    ap.add_argument('--pretrain-steps', type=int, default=0)
    ap.add_argument('--time-updates', type=int, default=0, help='timing only: train N updates, write nothing')
    ap.add_argument('--eval-only', action='store_true', help='skip training; evaluate the saved <out>/model.pt')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not a.arm or a.seed is None:
        ap.error('--arm and --seed are required')
    out = a.out or os.path.join(HERE, 'results', f'{a.arm}_s{a.seed}')
    steps = a.steps if a.steps is not None else (T1_LONG_STEPS if a.arm == 't1_long' else RA.STEPS)
    run(a.arm, a.seed, steps, a.cache, out, pretrain_dir=a.pretrain_dir, pretrain_steps=a.pretrain_steps,
        time_updates=a.time_updates, eval_only=a.eval_only)


if __name__ == '__main__':
    main()
