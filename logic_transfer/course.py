"""Continue training a parent checkpoint for a short 'course' (LT-1).

  python -m logic_transfer.course --parent CKPT --data SK200K_DIR [--mix ROWS.jsonl] [--mix-frac 0.25] --updates 4000
        --batch 64 --lr 1e-4 --warmup 100 --seed 1 --threads 4 --out DIR [--log-every 250] [--device cpu|cuda]
        [--eval NAME=ROWS.jsonl ...] [--eval-every 250] [--eval-n 400] [--stop-marks 'dev>=90,wording>=80'] [--abort-file PATH]

Loss, optimiser and model are those of custom_io.train for this cfg (model.loss incl. ans_drill; AdamW betas (0.9, 0.95), weight
decay 0.1 on matrices only, clip 1.0). lr: linear warmup, then constant.

Batch composition (the point of the design). k = round(batch * mix_frac) slots per batch come from --mix (arms L, P) or, with no
--mix (control arm C), from sk200k train. The other batch-k slots ALWAYS come from sk200k train, drawn from a stream seeded only
by --seed: arms with the same seed see identical sk200k rows in the same order, in the first batch-k positions of every batch.
The k extra slots use a separate stream (seed + MIX_STREAM). ans_drill's rng is re-seeded from (seed, update) before every
update, so the drill draws for those first rows are identical across arms too (the mix rows have no program, so they never draw).
Output: OUT/checkpoint.pt (same keys as the parent: model, name, cfg, chars, step = parent step + updates), OUT/checkpoint-<u>.pt every
--save-every updates (the final one is also linked as checkpoint-<updates>.pt when it falls on a multiple), OUT/log.jsonl (per
--log-every: window-mean loss, loss_cur / loss_mix = the curriculum slice and the mix slice measured separately every --slice-every
updates, s/update), OUT/run.json.
"""
import argparse
import gc
import hashlib
import json
import os
import random
import subprocess
import sys
import time

import numpy as np
import torch

MIX_STREAM = 1_000_003      # the extra-slot stream is RandomState(seed + MIX_STREAM)


def is_oom(e):
    return isinstance(e, torch.OutOfMemoryError) or 'out of memory' in str(e).lower()


def oom_retry(fn, counter, tries=80):
    """Run fn(); when the (shared) GPU is full, free this process's cache, wait a few seconds and run it again. Many small courses share one card
    (the first LT-2 waves lost half their runs to CUDA out-of-memory with 12 processes on a 24 GB card); a retry reproduces the same update
    (batch, schedule and answer-drill RNG are re-seeded inside fn), so waiting changes the speed, never the result. counter[0] counts the retries."""
    for _ in range(tries):
        try:
            return fn()
        except (torch.OutOfMemoryError, RuntimeError) as e:        # CUDA 'out of memory' also surfaces as AcceleratorError (a RuntimeError)
            if not is_oom(e):
                raise
            counter[0] += 1
            gc.collect()
            torch.cuda.empty_cache()
            time.sleep(3 + random.random() * 9)
    return fn()


def n_mix(batch, mix_frac):
    return int(round(batch * mix_frac))


def _perm_stream(rng, n, need):
    """`need` indices taken from successive fresh permutations of range(n) (no repeats inside an epoch)."""
    out, have = [], 0
    while have < need:
        p = rng.permutation(n)
        out.append(p)
        have += n
    return np.concatenate(out)[:need]


def schedule(seed, n_sk, n_mix_rows, batch, mix_frac, updates):
    """-> (sk_idx [updates, batch-k] int64, ex_idx [updates, k] int64). sk_idx depends only on (seed, n_sk, batch-k, updates).
    ex_idx indexes the mix file when n_mix_rows is not None, else sk200k train (control arm); it depends only on the seed and
    the pool size, never on the sk_idx stream."""
    k = n_mix(batch, mix_frac)
    m = batch - k
    sk = _perm_stream(np.random.RandomState(seed), n_sk, updates * m).reshape(updates, m)
    ex_pool = n_sk if n_mix_rows is None else n_mix_rows
    ex = _perm_stream(np.random.RandomState(seed + MIX_STREAM), ex_pool, updates * k).reshape(updates, k) if k else np.zeros((updates, 0), np.int64)
    return sk, ex


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def git_sha():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        sha = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=here).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', '.'], capture_output=True, text=True, cwd=here).stdout.strip()
        return sha + ('+dirty' if dirty else '')
    except Exception:
        return None


def make_optimizer(model, lr):
    """train.py's optimiser: no weight decay on biases, norms or embedding tables."""
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    return torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                             lr=lr, betas=(0.9, 0.95))


def save(out, name, model, ck, updates):
    """Same keys as the parent's checkpoint (train.py): model replaced, step = parent step + updates so far."""
    o = dict(ck)
    o['model'] = {kk: v.detach().cpu().clone() for kk, v in model.state_dict().items()}
    o['step'] = int(ck.get('step', 0)) + updates
    tmp = os.path.join(out, name + '.tmp')
    torch.save(o, tmp)
    os.replace(tmp, os.path.join(out, name))        # atomic: a driver watching for the file never sees a half-written one


def parse_marks(spec):
    """'dev>=90,gate@2>=65' -> [(file name, by_level key or None, threshold in percent)]."""
    out = []
    for part in (spec or '').split(','):
        part = part.strip()
        if not part:
            continue
        lhs, thr = part.split('>=')
        name, _, lvl = lhs.partition('@')
        out.append((name.strip(), lvl.strip() or None, float(thr)))
    return out


def mark_value(res, level):
    """Accuracy in percent from an evalx result: the whole file, or one by_level cell."""
    if level is None:
        return res['exact']
    c = res['by_level'].get(level)
    return 100.0 * c['correct'] / c['n'] if c and c['n'] else float('nan')


def marks_hold(results, marks):
    """results {file name: evalx result}; all marks must be satisfied (missing file or empty cell = not satisfied)."""
    return bool(marks) and all(n in results and mark_value(results[n], l) >= t for n, l, t in marks)


def summarise(full):
    """{file: evalx result} -> compact JSON-able {file: {correct, n, exact, by_level}}."""
    return {n: dict(correct=r['correct'], n=r['n'], exact=round(r['exact'], 3),
                    by_level={lv: [c['correct'], c['n']] for lv, c in sorted(r['by_level'].items())}) for n, r in full.items()}


def lr_at(step, warmup, base):
    return base * min(1.0, (step + 1) / warmup) if warmup else base


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--parent', required=True)
    ap.add_argument('--data', required=True, help='sk200k build dir (train.jsonl)')
    ap.add_argument('--mix', help='converted rows (rows.py) for the k mix slots; omitted = control arm (sk200k rows, separate stream)')
    ap.add_argument('--mix-frac', type=float, default=0.25)
    ap.add_argument('--updates', type=int, default=4000)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--warmup', type=int, default=100)
    ap.add_argument('--grad-clip', type=float, default=1.0)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    ap.add_argument('--out', required=True)
    ap.add_argument('--log-every', type=int, default=250)
    ap.add_argument('--save-every', type=int, default=0, help='save OUT/checkpoint-<update>.pt every N updates (0 = only the final checkpoint.pt)')
    ap.add_argument('--slice-every', type=int, default=5, help='every N updates also measure the loss of the curriculum slice and of the mix slice of that '
                    'batch separately (extra no-grad forwards, ~3%% of the time at 5); 0 = off')
    ap.add_argument('--eval', action='append', default=[], metavar='NAME=ROWS.jsonl', help='converted rows scored every --eval-every updates (repeatable)')
    ap.add_argument('--eval-every', type=int, default=250)
    ap.add_argument('--eval-n', type=int, default=0, help='periodic evals use the first N rows of each file (0 = the whole file); stop checks always confirm on the whole file')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--gpu-mem-gb', type=float, default=0, help='cuda: cap this process caching allocator at N GB (0 = no cap); the allocator then frees cached blocks before it fails')
    ap.add_argument('--abort-file', help='stop (reason abort) at the next periodic eval once this file exists')
    ap.add_argument('--stop-marks', default='', help="'NAME>=X,NAME@L>=Y' percent marks; stop when they hold at two consecutive evals and the full files confirm")
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    dev = torch.device(a.device)
    assert a.device == 'cpu' or torch.cuda.is_available(), 'no CUDA device'
    ooms = [0]
    if a.device == 'cuda' and a.gpu_mem_gb:
        torch.cuda.set_per_process_memory_fraction(min(1.0, a.gpu_mem_gb * (1 << 30) / torch.cuda.get_device_properties(0).total_memory))
    from custom_io import data as D
    from custom_io.data import Dataset, collate, load_rows, to_device
    from custom_io.evalx import evaluate
    from custom_io.models import load_model
    D.set_max_ans(8)
    os.makedirs(a.out, exist_ok=True)
    t_start = time.time()
    ck = torch.load(a.parent, map_location='cpu', weights_only=True)
    torch.manual_seed(a.seed); random.seed(a.seed); np.random.seed(a.seed)
    model = oom_retry(lambda: load_model(a.parent).to(dev), ooms)
    model.train()
    train_path = os.path.join(a.data, 'train.jsonl')
    sk_rows = load_rows(train_path)
    mix_rows = load_rows(a.mix) if a.mix else None
    if mix_rows is not None:
        clash = {r['id'] for r in mix_rows} & {r['id'] for r in sk_rows}
        assert not clash, f'mix ids collide with sk200k ids (progparse caches by id): {sorted(clash)[:3]}'
    sk_ds = Dataset(sk_rows, model.vocab)
    mix_ds = Dataset(mix_rows, model.vocab) if mix_rows is not None else sk_ds
    evals = {}
    for spec in a.eval:
        name, _, path = spec.partition('=')
        assert name and path, f'--eval wants NAME=PATH, got {spec!r}'
        evals[name] = (path, load_rows(path, keep=None))
        if mix_rows is not None:
            clash = {r['id'] for r in evals[name][1]} & {r['id'] for r in mix_rows}
            assert not clash, f'eval file {name} shares ids with the mix file: {sorted(clash)[:3]}'
    marks = parse_marks(a.stop_marks)
    assert all(n in evals for n, _, _ in marks), f'--stop-marks names a file not given with --eval: {marks}'
    k = n_mix(a.batch, a.mix_frac)
    need = a.updates * k
    if mix_rows is not None and need > len(mix_rows):
        print(f'warning: {need} mix draws from {len(mix_rows)} rows: rows repeat', flush=True)
    sk_idx, ex_idx = schedule(a.seed, len(sk_rows), None if mix_rows is None else len(mix_rows), a.batch, a.mix_frac, a.updates)
    opt = make_optimizer(model, a.lr)
    n_params = model.n_params()
    log = open(os.path.join(a.out, 'log.jsonl'), 'w')
    elog = open(os.path.join(a.out, 'eval.jsonl'), 'w')

    def run_evals(u, n):
        """Score every eval file on its first n rows (0 = all) -> {name: evalx result}; one line each in eval.jsonl."""
        res = {}
        for name, (_, rows) in evals.items():
            t = time.time()
            sub = rows[:n] if n else rows
            r = oom_retry(lambda: evaluate(model, sub, a.eval_batch, dev, by_label=True), ooms)
            res[name] = r
            elog.write(json.dumps(dict(update=u, name=name, n=r['n'], correct=r['correct'], exact=round(r['exact'], 3),
                                       by_level={lv: [c['correct'], c['n']] for lv, c in sorted(r['by_level'].items())},
                                       by_label={lb: [c['correct'], c['n']] for lb, c in sorted(r['by_label'].items())},
                                       full=(n == 0 or n >= len(rows)), eval_s=round(time.time() - t, 1))) + '\n')
        elog.flush()
        return res

    t_all, win_loss, win_t, last = [], [], [], None
    win_cur, win_mix, saved = [], [], []
    streak, stop, last_full, eval_s_total, done = 0, None, None, 0.0, 0
    for u in range(1, a.updates + 1):
        t0 = time.time()
        for g in opt.param_groups:
            g['lr'] = lr_at(u - 1, a.warmup, a.lr)
        items = [sk_ds[int(i)] for i in sk_idx[u - 1]] + [mix_ds[int(i)] for i in ex_idx[u - 1]]

        def fwd_bwd():
            opt.zero_grad(set_to_none=True)                  # a retry after an out-of-memory error starts from clean gradients
            model._drill_rng = random.Random(f'ans_drill|{a.seed}|{u}')
            batch = to_device(collate(items), dev)
            out = model.loss(batch)
            l_ = out[0] if isinstance(out, tuple) else out
            l_.backward()
            return l_
        loss = oom_retry(fwd_bwd, ooms) if a.device == 'cuda' else fwd_bwd()
        if a.slice_every and u % a.slice_every == 0 and k:
            keep_rng = model._drill_rng
            with torch.no_grad():
                for name, sl, acc in (('cur', items[:a.batch - k], win_cur), ('mix', items[a.batch - k:], win_mix)):
                    model._drill_rng = random.Random(f'slice|{a.seed}|{u}|{name}')
                    o2 = oom_retry(lambda: model.loss(to_device(collate(sl), dev)), ooms)
                    acc.append(float((o2[0] if isinstance(o2, tuple) else o2).detach()))
            model._drill_rng = keep_rng
        torch.nn.utils.clip_grad_norm_(model.parameters(), a.grad_clip)
        opt.step(); opt.zero_grad(set_to_none=True)
        dt = time.time() - t0
        lv = float(loss.detach())
        if not np.isfinite(lv):
            sys.exit(f'non-finite loss at update {u}')
        win_loss.append(lv); win_t.append(dt); t_all.append(dt)
        done = u
        if a.save_every and u % a.save_every == 0 and u < a.updates:
            was = model.training
            model.eval(); save(a.out, f'checkpoint-{u}.pt', model, ck, u); model.train(was)
            saved.append(u)
        if evals and a.eval_every and u % a.eval_every == 0 and u < a.updates:
            te = time.time()
            res = run_evals(u, a.eval_n)
            streak = streak + 1 if marks_hold(res, marks) else 0
            if a.abort_file and os.path.exists(a.abort_file):
                stop = dict(reason='abort', update=u)
                last_full = summarise(res)
            elif streak >= 2:
                full = res if a.eval_n == 0 else run_evals(u, 0)
                if marks_hold(full, marks):
                    stop = dict(reason='marks', update=u)
                    last_full = summarise(full)
                else:
                    streak = 0
            eval_s_total += time.time() - te
        if u % a.log_every == 0 or u == a.updates or stop:
            last = float(np.mean(win_loss))
            rec = dict(update=u, loss=round(last, 5),
                       loss_cur=round(float(np.mean(win_cur)), 5) if win_cur else None,
                       loss_mix=round(float(np.mean(win_mix)), 5) if win_mix else None, n_slice=len(win_cur), lr=opt.param_groups[0]['lr'], s_per_update=round(float(np.mean(win_t)), 4),
                       s_per_update_median=round(float(np.median(win_t)), 4), elapsed=round(time.time() - t_start, 1),
                       oom_retries=ooms[0], gpu_peak_alloc_mb=(round(torch.cuda.max_memory_allocated() / 2**20) if a.device == 'cuda' else None),
                       gpu_peak_reserved_mb=(round(torch.cuda.max_memory_reserved() / 2**20) if a.device == 'cuda' else None))
            log.write(json.dumps(rec) + '\n'); log.flush()
            print(json.dumps(rec), flush=True)
            win_loss, win_t, win_cur, win_mix = [], [], [], []
        if stop:
            break
    model.eval()
    if evals:
        te = time.time()
        if stop is None:                                    # ran the full budget: the last word is a whole-file eval of everything
            full = run_evals(done, 0)
            last_full = summarise(full)
            stop = dict(reason='max_updates', update=done, marks_hold=marks_hold(full, marks) if marks else None)
        stop['full_eval'] = last_full
        stop['marks'] = a.stop_marks
        eval_s_total += time.time() - te
        json.dump(stop, open(os.path.join(a.out, 'stop.json'), 'w'), indent=1)
        print('stop ' + json.dumps({k2: v for k2, v in stop.items() if k2 != 'full_eval'}), flush=True)
    save(a.out, 'checkpoint.pt', model, ck, done)
    if done in saved or (a.save_every and done % a.save_every == 0):
        last_ck = os.path.join(a.out, f'checkpoint-{done}.pt')
        if not os.path.exists(last_ck):
            os.link(os.path.join(a.out, 'checkpoint.pt'), last_ck)
    run = dict(args=vars(a), argv=sys.argv, git_sha=git_sha(), torch=torch.__version__, n_params=n_params, device=a.device,
               arm='C' if not a.mix else 'mix', k_mix_slots=k, sk_slots=a.batch - k, updates_done=done,
               parent_sha256=sha256(a.parent), sk_train_sha256=sha256(train_path),
               mix_sha256=sha256(a.mix) if a.mix else None, n_sk_rows=len(sk_rows), n_mix_rows=len(mix_rows) if mix_rows else None,
               eval_files_sha256={n: sha256(p) for n, (p, _) in evals.items()},
               sk_idx_sha256=hashlib.sha256(sk_idx.tobytes()).hexdigest(), ex_idx_sha256=hashlib.sha256(ex_idx.tobytes()).hexdigest(),
               final_loss_window=last, steady_median_s_per_update=round(float(np.median(t_all[min(5, len(t_all) - 1):])), 4),
               oom_retries=ooms[0], gpu_peak_alloc_mb=(round(torch.cuda.max_memory_allocated() / 2**20) if a.device == 'cuda' else None),
               gpu_peak_reserved_mb=(round(torch.cuda.max_memory_reserved() / 2**20) if a.device == 'cuda' else None),
               train_s=round(sum(t_all), 1), eval_s=round(eval_s_total, 1), wall_s=round(time.time() - t_start, 1),
               drill_stats=getattr(model, 'drill_stats', None))
    json.dump(run, open(os.path.join(a.out, 'run.json'), 'w'), indent=1)
    print(f'done {done} updates, median {run["steady_median_s_per_update"]} s/update, wall {run["wall_s"]}s', flush=True)
    return run


if __name__ == '__main__':
    main()
