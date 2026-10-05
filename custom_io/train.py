"""CLI trainer.  python3 -m custom_io.train --model plain_tf --cfg '{"d_model":256}' --steps 3000 --out runs/x --final-eval"""
import argparse, contextlib, json, math, os, random, sys, time
import numpy as np
import torch
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, load_rows, to_device, train_batches
from custom_io.evalx import eval_all, evaluate, short, subsample
from custom_io.models import MODELS, build


def lr_at(step, steps, warmup, base, elapsed=0.0, cap=None):
    """Linear warmup, then cosine to 10% of base. Progress = max(step/steps, elapsed/cap) so a --minutes
    cap still anneals the lr to its floor by the time training stops."""
    if step < warmup:
        return base * (step + 1) / warmup
    q = max(step / steps, elapsed / cap if cap else 0.0)
    p = min(1.0, max(0.0, (q - warmup / steps) / max(1 - warmup / steps, 1e-8)))
    return base * (0.1 + 0.45 * (1 + math.cos(math.pi * p)))


def jprint(**kw):
    print(json.dumps(kw), flush=True)


def final_eval(model, args, device, amp):
    """Full eval_all, then every lesion the model supports (+ loops:K sweep for models with n_loops)."""
    names = [l for l in model.LESIONS if l.split(':')[0] != 'loops']
    if hasattr(model, 'n_loops'):
        names += [f'loops:{k}' for k in sorted({0, 1, 2, 2 * model.n_loops})]
    runs = {}
    for lesion in [None] + names:
        with amp():
            runs[lesion] = eval_all(model, args.data, args.eval_max, lesion, args.eval_batch, device)
        jprint(event='eval', lesion=lesion, **short(runs[lesion]))
    return runs.pop(None), runs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True, choices=sorted(MODELS))
    ap.add_argument('--cfg', default='{}', help='JSON dict of model kwargs')
    ap.add_argument('--data', default=DEFAULT_DATA, help='dir with train.jsonl and dev/')
    ap.add_argument('--vocab', help='vocab json (default: DATA/charvocab.json, built from DATA/train.jsonl if absent)')
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=64)
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
    ap.add_argument('--eval-max', type=int, help='cap rows per dev split in the final eval')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--minutes', type=float, help='wall-clock cap on training; still evals afterwards')
    ap.add_argument('--out', help='dir for RESULT.json and checkpoint.pt')
    args = ap.parse_args(argv)
    cfg = json.loads(args.cfg)
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if args.bf16 and device.type == 'cuda' else contextlib.nullcontext
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
    t_start = time.time()

    rows = load_rows(os.path.join(args.data, 'train.jsonl'))
    vocab = CharVocab.get(args.data, args.vocab, rows)
    batches = train_batches(Dataset(rows, vocab), args.batch, args.order, args.seed)
    dev = subsample(load_rows(os.path.join(args.data, 'dev', 'in_dist.jsonl')), 200)
    model = build(args.model, vocab, **cfg).to(device)
    # no weight decay on biases, norms or embedding tables (so ids never seen in training keep their init scale)
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=args.lr, betas=(0.9, 0.95), fused=device.type == 'cuda')
    jprint(event='start', model=args.model, cfg=cfg, n_params=model.n_params(), device=str(device), vocab=len(vocab), rows=len(rows))

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
            jprint(event='train', step=step, loss=round(last_loss, 5), lr=round(lr, 7), elapsed=round(time.time() - t0, 1),
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
                  train_s=train_s, steps_per_s=step / max(train_s, 1e-9), final_eval=None, lesions={})
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        torch.save(dict(model=model.state_dict(), name=args.model, cfg=cfg, chars=vocab.chars, step=step), os.path.join(args.out, 'checkpoint.pt'))
    def write():
        result['wall_s'] = time.time() - t_start
        if args.out:
            json.dump(result, open(os.path.join(args.out, 'RESULT.json'), 'w'), indent=1)
    write()                                           # trained model + stats survive even if the eval below dies
    if args.final_eval:
        result['final_eval'], result['lesions'] = final_eval(model, args, device, amp)
    write()
    jprint(event='done', steps=step, status=status, steps_per_s=round(result['steps_per_s'], 3), wall_s=round(result['wall_s'], 1),
           **(short(result['final_eval']) if result['final_eval'] else {}))
    return result


if __name__ == '__main__':
    main()
