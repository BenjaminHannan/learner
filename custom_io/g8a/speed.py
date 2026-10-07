"""Speed probe for the 8a ladder (addendum B3 / C): `--updates` timed updates (default 200) of every arm at the 3M, 10M and 30M shapes, with 256 rows per update.
Prints seconds per update, torch.cuda.max_memory_allocated and, when an arm's peak passes --mem-gb (15), how many gradient-accumulation micro-batches
make it fit (train.py --accum; still 256 rows per update). Then the hours and dollars each rung's schedule would take at those speeds.

  python -m custom_io.g8a.speed --data WORK/data --out OUT [--rungs 3M 10M 30M] [--arms B2 PT LLM] [--updates 200] [--mem-gb 15] [--dph 0] [--public pythia31m smollm360]

Rows: needs no web data. Half the rows (by count; 38% by word pieces) are real skills rows from DATA/train.jsonl, half are cloze rows made by g8a.cloze from
pseudo-documents (concatenated skills prompts), so the row lengths and the copy-heavy cloze shape are those of the real pool; content does not matter for speed.
Writes OUT/speed.json (and OUT/RESULT.json, so local_runner counts the probe as done). GPU-time only: no dataset, nothing is saved but the numbers.
"""
import argparse, contextlib, gc, json, math, os, sys, time
import numpy as np
import torch
from custom_io.data import CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.g8a import caps as CP
from custom_io.g8a import cloze as Z
from custom_io.g8a import configs as C
from custom_io.g8a.pool import schedule
from custom_io.models import build
from custom_io.train import split_batch


def probe_rows(data_dir, n=3000, seed=0):
    own = load_rows(os.path.join(data_dir, 'train.jsonl'), limit=60000)
    rng = np.random.RandomState(seed)
    own = [own[i] for i in rng.permutation(len(own))[:n]]
    docs = []
    for i in range(0, len(own) - 12, 12):                  # a pseudo-document = 12 skills prompts joined (about 1,000 chars)
        t = ' '.join(r['prompt'] for r in own[i:i + 12])
        docs.append(dict(id=f'probe{i}', text=t, token_count=len(t) / 4.2))
    cz = [{k: v for k, v in r.items() if k != '_np'} for r in Z.cloze_rows(docs, 1)]
    k = min(len(own), len(cz))
    rows = own[:k] + cz[:k]
    return [rows[i] for i in rng.permutation(len(rows))]


def time_arm(model_name, cfg, rows, batch, accum, updates, warmup, device, bf16, lr):
    vocab = CharVocab.build([])
    torch.manual_seed(0)
    model = build(model_name, vocab, **cfg).to(device)
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2]
    rest = [p for p in model.parameters() if p.requires_grad and p.ndim < 2]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': rest, 'weight_decay': 0.0}], lr=lr, betas=(0.9, 0.95), fused=device.type == 'cuda')
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if bf16 and device.type == 'cuda' else contextlib.nullcontext
    batches = train_batches(Dataset(rows, vocab), batch, 'shuffled', 0)
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    model.train()
    t0 = None
    for step in range(warmup + updates):
        if step == warmup:
            if device.type == 'cuda':
                torch.cuda.synchronize()
            t0 = time.time()
        b = to_device(next(batches), device)
        parts = split_batch(b, accum) if accum > 1 else [b]
        for mb in parts:
            with amp():
                out = model.loss(mb)
            loss = out[0] if isinstance(out, tuple) else out
            (loss / len(parts)).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    dt = (time.time() - t0) / updates
    peak = torch.cuda.max_memory_allocated() / 2 ** 30 if device.type == 'cuda' else None
    n = model.n_params()
    del model, opt
    return dt, peak, n


def time_public(key, rows, batch, updates, warmup, device, bf16):
    from custom_io.hf_baseline import HFLM
    pb = C.PUBLIC[key]
    vocab = CharVocab.build([])
    q = [r for r in rows if not Z.is_cloze(r)]
    model = HFLM(vocab, pb['hf_id'], pb['revision'], 0, q, 0, 'steps').to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=pb['lr'], betas=(0.9, 0.95), weight_decay=0.0, fused=device.type == 'cuda')
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if bf16 and device.type == 'cuda' else contextlib.nullcontext
    batches = train_batches(Dataset(q, vocab), batch, 'shuffled', 0)
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    model.train()
    for step in range(warmup + updates):
        if step == warmup:
            if device.type == 'cuda':
                torch.cuda.synchronize()
            t0 = time.time()
        with amp():
            loss = model.loss(to_device(next(batches), device))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    return (time.time() - t0) / updates, (torch.cuda.max_memory_allocated() / 2 ** 30 if device.type == 'cuda' else None), model.n_params()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True, help='skills build dir with train.jsonl (WORK/data)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--rungs', nargs='+', default=list(C.RUNGS), choices=list(C.RUNGS))
    ap.add_argument('--arms', nargs='+', default=list(C.ARMS), choices=list(C.ARMS))
    ap.add_argument('--public', nargs='*', default=[], choices=list(C.PUBLIC))
    ap.add_argument('--updates', type=int, default=200)
    ap.add_argument('--warmup', type=int, default=10)
    ap.add_argument('--batch', type=int, default=C.BATCH)
    ap.add_argument('--mem-gb', type=float, default=15.0)
    ap.add_argument('--max-accum', type=int, default=16)
    ap.add_argument('--dph', type=float, default=0.0, help='dollars per hour, for the cost lines only (0 = home GPU)')
    ap.add_argument('--seeds', type=int, default=6)
    ap.add_argument('--device', default='auto')
    a = ap.parse_args(argv)
    device = torch.device('cuda' if a.device == 'auto' and torch.cuda.is_available() else 'cpu' if a.device == 'auto' else a.device)
    os.makedirs(a.out, exist_ok=True)
    rows = probe_rows(a.data)
    caps = CP.compute_rows(rows)                    # sized from the probe rows, at least the spec's worst cases (cloze prompt 280, answers to 32 chars), as the real jobs size theirs
    caps = CP.apply(dict(caps, max_prompt=max(caps['max_prompt'], 280), max_ans=max(caps['max_ans'], 32), n_reg=max(caps['n_reg'], 33)))
    b2_extra = dict(n_loops=CP.n_loops_needed(caps)) if CP.n_loops_needed(caps) > 8 else None
    mean_chars = sum(len(r['prompt']) + len(r['answer']) + 1 for r in rows) / len(rows)
    gpu = torch.cuda.get_device_name(0) if device.type == 'cuda' else str(device)
    print(json.dumps(dict(event='start', gpu=gpu, probe_rows=len(rows), mean_row_chars=round(mean_chars, 1), updates=a.updates, batch=a.batch, mem_gb=a.mem_gb)), flush=True)
    out = dict(caps=caps, gpu=gpu, updates=a.updates, batch=a.batch, mem_gb=a.mem_gb, rungs={}, public={})
    for rung in a.rungs:
        cfgs, counts = C.sizes(rung, b2_extra)
        C.check_bands(rung, cfgs, counts, exact_3m=False)
        out['rungs'][rung] = {}
        for arm in a.arms:
            res, accum = None, 1
            tries = []
            while accum <= a.max_accum:
                try:
                    dt, peak, n = time_arm(C.MODEL_OF[arm], cfgs[arm], rows, a.batch, accum, a.updates, a.warmup, device, True, C.RUNGS[rung]['lr'])
                    tries.append(dict(accum=accum, s_per_update=dt, peak_gb=peak))
                    res = dict(accum=accum, micro_batch=a.batch // accum, s_per_update=dt, peak_gb=peak, n_params=n)
                    if peak is None or peak <= a.mem_gb:
                        break
                except torch.cuda.OutOfMemoryError:
                    tries.append(dict(accum=accum, oom=True))
                    res = None
                gc.collect()
                if device.type == 'cuda':
                    torch.cuda.empty_cache()
                accum *= 2
            r = dict(res or dict(accum=None, s_per_update=None, peak_gb=None, n_params=counts[arm]), tries=tries, fits=bool(res and (res['peak_gb'] is None or res['peak_gb'] <= a.mem_gb)))
            out['rungs'][rung][arm] = r
            print(json.dumps(dict(event='speed', rung=rung, arm=arm, **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != 'tries'})), flush=True)
        # the schedule this rung would run (mean row pieces from the probe rows' own accounting) and its cost at the measured speeds
        mean_pieces = 40.0
        sch = schedule(rung, mean_pieces, 10 ** 9)
        out['rungs'][rung]['_schedule'] = dict(steps=sch['steps'], assumed_mean_row_pieces=mean_pieces)
        for arm in a.arms:
            r = out['rungs'][rung][arm]
            if r['s_per_update']:
                r['hours_per_run'] = sch['steps'] * r['s_per_update'] / 3600
                r['usd_per_run'] = r['hours_per_run'] * a.dph
        tot = sum(out['rungs'][rung][arm].get('hours_per_run') or 0 for arm in a.arms)
        out['rungs'][rung]['_per_seed_hours_all_arms'] = tot
        out['rungs'][rung]['_six_seed_hours'] = tot * a.seeds
        print(json.dumps(dict(event='rung', rung=rung, steps=sch['steps'], hours_per_seed_all_arms=round(tot, 2), six_seed_hours=round(tot * a.seeds, 1), usd_six_seeds=round(tot * a.seeds * a.dph, 2))), flush=True)
    for key in a.public:
        try:
            dt, peak, n = time_public(key, rows, a.batch, a.updates, a.warmup, device, True)
            out['public'][key] = dict(s_per_update=dt, peak_gb=peak, n_params=n)
        except Exception as e:           # transformers missing, hub unreachable, OOM: the number is simply absent
            out['public'][key] = dict(error=repr(e)[:300])
        print(json.dumps(dict(event='public', key=key, **out['public'][key])), flush=True)
    json.dump(out, open(os.path.join(a.out, 'speed.json'), 'w'), indent=1)
    json.dump(dict(status='ok', speed=out), open(os.path.join(a.out, 'RESULT.json'), 'w'), indent=1)
    print(json.dumps(dict(event='done', out=os.path.join(a.out, 'speed.json'))), flush=True)
    return out


if __name__ == '__main__':
    main()
