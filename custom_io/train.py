"""CLI trainer.  python3 -m custom_io.train --model plain_tf --cfg '{"d_model":256}' --steps 3000 --out runs/x --final-eval"""
import argparse, contextlib, json, math, os, random, sys, time
import numpy as np
import torch
from custom_io import capcount, data as D
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.evalx import can_donor, chain_panel, donor_all, eval_all, evaluate, short, subsample, _dev_rows, is_hit
from custom_io.models import NAMES, build

PLAIN_TF_S = 3244544                                                     # plain_tf S, the size every 3M design is matched to
SIZE_BAND = (round(PLAIN_TF_S * 0.97), round(PLAIN_TF_S * 1.03))        # the sealed +-3% band: 3,147,208 .. 3,341,880


def lr_at(step, steps, warmup, base, elapsed=0.0, cap=None):
    """Linear warmup, then cosine to 10% of base. Progress = max(step/steps, elapsed/cap) so a --minutes
    cap still anneals the lr to its floor by the time training stops."""
    if step < warmup:
        return base * (step + 1) / warmup
    q = max(step / steps, elapsed / cap if cap else 0.0)
    p = min(1.0, max(0.0, (q - warmup / steps) / max(1 - warmup / steps, 1e-8)))
    return base * (0.1 + 0.45 * (1 + math.cos(math.pi * p)))


def split_batch(batch, k):
    """k row-slices of a collated batch (every tensor is cut along dim 0, `rows` along with it); the padded width is kept, so micro-batches line up with the full batch."""
    n = len(batch['rows'])
    cuts = [round(i * n / k) for i in range(k + 1)]
    return [{key: (v[a:b] if torch.is_tensor(v) or isinstance(v, list) else v) for key, v in batch.items()} for a, b in zip(cuts, cuts[1:]) if b > a]


def jprint(**kw):
    print(json.dumps(kw), flush=True)


def lesion_names(model):
    """Every generate() lesion final_eval runs: the model's own (not loops) + loops:K for K in {0,1,2,2n}."""
    names = [l for l in model.LESIONS if l.split(':')[0] != 'loops']
    if getattr(model, 'n_loops', 1) > 1:    # a 1-loop model's sweep is only a format check (loops:1 = intact); skip it
        names += [f'loops:{k}' for k in sorted({0, 1, 2, 2 * model.n_loops})]
    return names


def chain5_eval(model, args, device, amp):
    """chain-5 panel (big build) for the intact model and every lesion -> {'intact': {..., 'hits': {id: 0/1}}, lesion: {...}}."""
    rows = {r['id']: r for r in _dev_rows(args.big_data, 'in_dist', None)}
    out = {}
    for lesion in [None] + lesion_names(model):
        with amp():
            r = chain_panel(model, args.big_data, lesion, args.eval_batch, device, return_preds=lesion is None)
        if lesion is None:
            r['hits'] = {i: int(is_hit(p, rows[i])) for i, p in r.pop('preds').items()}
        out[lesion or 'intact'] = r
        jprint(event='eval', lesion=lesion, chain5=round(r['exact'], 2), n=r['n'])
    return out


def run_extra(model, args, device, amp, result):
    """model.extra_evals(ctx) -> result['extra']; a failure is recorded in result['extra_error'], never raised."""
    try:
        ctx = dict(data=args.data, big=args.big_data, device=device, batch_size=args.eval_batch, amp=amp)
        result['extra'] = model.extra_evals(ctx)
        json.dumps(result['extra'])
        jprint(event='extra', **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in result['extra'].items()
                                 if isinstance(v, (int, float, str, bool))}, keys=sorted(result['extra']))
    except Exception:
        import traceback
        result.pop('extra', None)
        result['extra_error'] = traceback.format_exc()
        jprint(event='extra_error', error=result['extra_error'].strip().splitlines()[-1])


def final_eval(model, args, device, amp):
    """Full eval_all, then every lesion the model supports (+ loops:K sweep for models with n_loops, + the donor swap
    for models with state/talk, stored under lesions['donor'] as {split: donor_eval result})."""
    names = lesion_names(model)
    runs = {}
    for lesion in [None] + names:
        with amp():
            runs[lesion] = eval_all(model, args.data, args.eval_max, lesion, args.eval_batch, device, return_preds=lesion is None and args.save_preds)
        if lesion is None and args.save_preds:      # per-row intact dev predictions of all 6 splits -> PREDS.json beside RESULT.json
            preds = {s: r.pop('preds') for s, r in runs[None].items()}
            if args.out:
                os.makedirs(args.out, exist_ok=True)
                json.dump(preds, open(os.path.join(args.out, 'PREDS.json'), 'w'))
            jprint(event='preds', n={s: len(p) for s, p in preds.items()})
        jprint(event='eval', lesion=lesion, **short(runs[lesion]))
    if can_donor(model):
        with amp():
            runs['donor'] = donor_all(model, args.data, args.eval_max, args.eval_batch, device)
        jprint(event='eval', lesion='donor', **{s: {k: round(v[k], 2) for k in ('exact', 'donor_match')} for s, v in runs['donor'].items()})
    return runs.pop(None), runs


def english_eval(model, args, device, amp):
    """english.eval_english on the held-out in-dist slice (DATA/dev/in_dist.jsonl, every key kept) + the eval dir; one event line per set and lesion."""
    from custom_io import english
    held = load_rows(os.path.join(args.data, 'dev', 'in_dist.jsonl'), keep=None)
    r = english.eval_english(model, args.english_eval, held, device, args.eval_batch, amp)
    json.dumps(r)
    for k, v in (r.get('intact') or {}).items():
        if isinstance(v, dict) and 'exact' in v:
            jprint(event='eval', set=k, exact=round(v['exact'], 2), n=v.get('n'))
    for k1, v1 in (r.get('lesions') or {}).items():
        for k2, v2 in (v1 or {}).items():
            e = v2.get('exact', (v2.get('judged') or {}).get('exact')) if isinstance(v2, dict) else None
            jprint(event='eval', lesion=f'{k1}/{k2}', exact=None if e is None else round(e, 2))
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, choices=NAMES)
    ap.add_argument('--cfg', default='{}', help='JSON dict of model kwargs')
    ap.add_argument('--data', default=DEFAULT_DATA, help='dir with train.jsonl and dev/')
    ap.add_argument('--big-data', default=None, help='data root with a 200-per-cell dev/ (chain-5 panel + extra_evals)')
    ap.add_argument('--vocab', help='vocab json (default: DATA/charvocab.json, built from DATA/train.jsonl if absent)')
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--accum', type=int, default=1, help='gradient accumulation: split every batch into this many micro-batches (same 256 rows per update; the loss is the mean of the micro-batch losses, so a token-mean loss differs slightly from the full-batch one)')
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--warmup', type=int, default=300)
    ap.add_argument('--grad-clip', type=float, default=1.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--order', choices=['shuffled', 'curriculum'], default='shuffled')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--bf16', action='store_true', help='autocast bf16 (cuda only)')
    ap.add_argument('--log-every', type=int, default=100)
    ap.add_argument('--eval-every', type=int, default=0, help='quick eval on 200 rows of dev/in_dist every N steps')
    ap.add_argument('--final-eval', action='store_true')
    ap.add_argument('--english-eval', help='dir of the four English eval sets: with --final-eval run english.eval_english (needs DATA/dev/in_dist.jsonl, vocab of 108) instead of eval_all, chain-5 and extra_evals')
    ap.add_argument('--max-ans', type=int, default=8, help='answer chars before EOS (data.set_max_ans); a model with a smaller max_ans is refused')
    ap.add_argument('--caps', help='caps.json from custom_io.g8a.caps: sizes the prompt / answer / workspace / target caps from the data (8A addendum E); applied before any data or model is built')
    ap.add_argument('--eval-max', type=int, help='cap rows per dev split in the final eval')
    ap.add_argument('--save-preds', action='store_true', help='with --final-eval: write the intact per-row dev predictions of all 6 splits to OUT/PREDS.json')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--minutes', type=float, help='wall-clock cap on training; still evals afterwards')
    ap.add_argument('--out', help='dir for RESULT.json and checkpoint.pt')
    args = ap.parse_args(argv)
    cfg = json.loads(args.cfg)
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if args.bf16 and device.type == 'cuda' else contextlib.nullcontext
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    t_start = time.time()
    D.set_max_ans(args.max_ans)         # before any data or model is built
    if args.caps:
        from custom_io.g8a import caps as _caps
        _c = _caps.apply(json.load(open(args.caps)))
        args.max_ans = _c['max_ans']
        jprint(event='caps', **_c)

    rows = load_rows(os.path.join(args.data, 'train.jsonl'))
    vocab = CharVocab.get(args.data, args.vocab, rows)
    batches = train_batches(Dataset(rows, vocab), args.batch, args.order, args.seed)
    dev = subsample(load_rows(os.path.join(args.data, 'dev', 'in_dist.jsonl')), 200)
    model = build(args.model, vocab, **cfg).to(device)
    if args.caps and hasattr(model, '_targets'):    # plain_tf_steps family: its answer slots are the steps+answer target (caps plain_target), not max_ans
        model.max_ans = args.max_ans
    if getattr(model, 'max_ans', args.max_ans) < args.max_ans:
        sys.exit(f'--max-ans {args.max_ans} but the model has max_ans {model.max_ans}: its answer slots cannot hold the targets')
    if args.english_eval and args.final_eval:
        assert len(vocab) == 108, f'english eval needs the 108-id vocab, got {len(vocab)}'
    # no weight decay on biases, norms or embedding tables (so ids never seen in training keep their init scale)
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=args.lr, betas=(0.9, 0.95), fused=device.type == 'cuda')
    jprint(event='start', model=args.model, cfg=cfg, n_params=model.n_params(), device=str(device), vocab=len(vocab), rows=len(rows))
    n, (lo, hi) = model.n_params(), SIZE_BAND
    jprint(event='cap_hits', step=0, **capcount.snapshot())
    jprint(event='size', n_params=n, band=[lo, hi], inside=lo <= n <= hi, headroom_to_top=hi - n, vs_plain_tf_pct=round(100 * (n / PLAIN_TF_S - 1), 2))

    cap = args.minutes * 60 if args.minutes else None
    t0, eval_s, step, run_loss, run_n, last_loss, status = time.time(), 0.0, 0, 0.0, 0, None, 'ok'
    model.train()
    while step < args.steps:
        elapsed = time.time() - t0
        if cap and elapsed >= cap:
            status = 'time_cap'
            break
        lr = lr_at(step, args.steps, args.warmup, args.lr, elapsed, cap)
        for g in opt.param_groups:
            g['lr'] = lr
        batch = to_device(next(batches), device)
        if args.accum > 1:
            parts = split_batch(batch, args.accum)
            loss, aux = 0.0, {}
            for mb in parts:
                with amp():
                    out = model.loss(mb)
                l_i, a_i = out if isinstance(out, tuple) else (out, {})
                (l_i / len(parts)).backward()
                loss = loss + l_i.detach() / len(parts)
                for k_, v_ in a_i.items():
                    aux[k_] = aux.get(k_, 0.0) + v_.detach() / len(parts) if torch.is_tensor(v_) else aux.get(k_, 0.0) + v_ / len(parts)
        else:
            with amp():
                out = model.loss(batch)
            loss, aux = out if isinstance(out, tuple) else (out, {})
            loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step(); opt.zero_grad(set_to_none=True)
        step += 1
        run_loss += loss.detach(); run_n += 1
        if step % args.log_every == 0 or step == args.steps:
            last_loss = float(run_loss) / run_n
            jprint(event='train', step=step, loss=round(last_loss, 5), lr=round(lr, 7), elapsed=round(time.time() - t0, 1), cap_hits=capcount.snapshot()['total'],
                   **{k: round(float(v), 5) for k, v in aux.items()})
            run_loss, run_n = 0.0, 0
            if not math.isfinite(last_loss):
                status = 'nonfinite_loss'
                break
        if args.eval_every and step % args.eval_every == 0:
            te = time.time()
            with amp():
                r = evaluate(model, dev, args.eval_batch, device)
            eval_s += time.time() - te
            jprint(event='quick_eval', step=step, dev_in_dist_200=round(r['exact'], 2), loss=last_loss)
    if device.type == 'cuda':
        torch.cuda.synchronize()
    train_s = time.time() - t0 - eval_s
    result = dict(config=dict(vars(args), cfg=cfg), n_params=model.n_params(), steps=step, status=status, final_train_loss=last_loss,
                  train_s=train_s, steps_per_s=step / max(train_s, 1e-9), final_eval=None, lesions={}, cap_hits=capcount.snapshot())
    jprint(event='cap_hits', step=step, **result['cap_hits'])       # scorecard row 6: every count must be 0 (see custom_io/capcount.py)
    mf = os.path.join(args.data, 'MANIFEST.json')       # the English adapter's manifest: its sha256 travels with the result (analyze_b1 checks it)
    if os.path.exists(mf):
        import hashlib
        result['data_manifest_sha256'] = hashlib.sha256(open(mf, 'rb').read()).hexdigest()
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        torch.save(dict(model=model.state_dict(), name=args.model, cfg=cfg, chars=vocab.chars, step=step), os.path.join(args.out, 'checkpoint.pt'))
    def write():
        result['wall_s'] = time.time() - t_start
        if device.type == 'cuda':       # peaks so far (training, then evals): later queues size --par and # MEM from these
            result['peak_mem_mib'], result['peak_reserved_mib'] = (round(f(device) / 2 ** 20, 1) for f in (torch.cuda.max_memory_allocated, torch.cuda.max_memory_reserved))
        if args.out:
            json.dump(result, open(os.path.join(args.out, 'RESULT.json'), 'w'), indent=1)
    write()                                           # trained model + stats survive even if the eval below dies
    if args.final_eval and args.english_eval:
        result['english'] = english_eval(model, args, device, amp)
        write()
    elif args.final_eval:
        result['final_eval'], result['lesions'] = final_eval(model, args, device, amp)
        write()
        if args.big_data:
            result['chain5'] = chain5_eval(model, args, device, amp)
            write()
        if hasattr(model, 'extra_evals'):
            run_extra(model, args, device, amp, result)
    result['cap_hits'] = capcount.snapshot()      # again after the final evaluations
    jprint(event='cap_hits', step=step, final=True, **result['cap_hits'])
    write()
    jprint(event='done', steps=step, status=status, steps_per_s=round(result['steps_per_s'], 3), wall_s=round(result['wall_s'], 1),
           **{k: result[k] for k in ('peak_mem_mib', 'peak_reserved_mib') if k in result},
           **(short(result['final_eval']) if result['final_eval'] else {}))
    return result


if __name__ == '__main__':
    main()
