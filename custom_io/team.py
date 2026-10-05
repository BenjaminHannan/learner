"""Team of small models trained together (Ben's swarm idea, 2026-10-05).

python3 -m custom_io.team --route on --seed 100 --out runs/team_on_s100 --final-eval

Members are ordinary custom_io models (default: B2 = ledger+copy, worked steps = plain_tf_steps, plain answers =
plain_tf), each built right after torch.manual_seed(seed), so each starts bit-identical to its solo train.py run at the
same seed. A coach (a small char encoder over the question, ~0.4M) scores the members for every row.

One step:
  pool    = 2 * batch training rows (a fresh seeded permutation every epoch, like train.py)
  coach   -> pi [pool, members] (softmax, no grad)
  route on : member i trains on `batch` rows of the pool drawn without replacement with
             prob = (1 - mix) / pool + mix * pi[:, i] / sum(pi[:, i])   (the coach decides who practises what)
  route off: member i trains on `batch` rows drawn uniformly from the pool (independent training; the control)
  every --label-every steps: every member answers --label-rows pool rows greedily; the coach learns who was right
             (soft target = right / n_right; rows nobody got right are skipped). Same in both arms.
Each member keeps its own loss, AdamW and lr schedule exactly as train.py (warmup, cosine to 10%, clip 1, wd 0.1).

Team answer (fixed before any run): coach-weighted vote = every member's answer gets that member's coach probability;
the answer with the most total weight wins. Also reported: coach argmax, plain majority, any-member-right, each member.
"""
import argparse, contextlib, json, math, os, random, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.data import DEFAULT_DATA, DEV_SPLITS, MAX_PROMPT, PAD, CharVocab, Dataset, collate, load_rows, to_device
from custom_io.evalx import _dev_rows, evaluate, is_hit, norm
from custom_io.models import build
from custom_io.train import jprint, lr_at

MEMBERS = [['B2', 'ledger', {'copy': True}],
           ['tfsteps', 'plain_tf_steps', {}],
           ['tf', 'plain_tf', {'d_model': 256, 'n_layers': 4, 'n_heads': 4}]]


class Coach(nn.Module):
    """Question -> one logit per member. Bidirectional char encoder, mean-pooled over the prompt."""

    def __init__(self, n_vocab, n_members, d=128, layers=2, heads=4):
        super().__init__()
        self.tok, self.pos = nn.Embedding(n_vocab, d), nn.Embedding(MAX_PROMPT, d)
        layer = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.ln, self.head = nn.LayerNorm(d), nn.Linear(d, n_members)
        nn.init.zeros_(self.head.weight); nn.init.zeros_(self.head.bias)     # starts uniform: no routing before it has learned anything

    def forward(self, batch):
        p, m = batch['prompt_ids'], batch['prompt_mask']
        x = self.enc(self.tok(p) + self.pos(torch.arange(p.shape[1], device=p.device)), src_key_padding_mask=~m)
        x = (x * m[..., None]).sum(1) / m.sum(1, keepdim=True).clamp(min=1)
        return self.head(self.ln(x)).float()


def make_opt(model, lr, device):
    emb = {id(m.weight) for m in model.modules() if isinstance(m, nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    return torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                             lr=lr, betas=(0.9, 0.95), fused=device.type == 'cuda')


def pools(n, size, seed):
    rng = np.random.RandomState(seed)
    while True:
        idx = rng.permutation(n)
        for s in range(0, n - size + 1, size):
            yield idx[s:s + size]


@torch.no_grad()
def coach_probs(coach, ds, idx, device, amp, bs=512):
    out = []
    for s in range(0, len(idx), bs):
        with amp():
            out.append(coach(to_device(collate([ds[i] for i in idx[s:s + bs]]), device)).softmax(-1))
    return torch.cat(out)


@torch.no_grad()
def answers(member, batch):
    was = member.training
    member.eval()
    out = member.generate(batch)
    member.train(was)
    return out


def team_scores(names, preds, probs, rows):
    """preds {name: {id: str}}, probs [N, M] (row order) -> per-rule exact % and per-row hits."""
    rules = {k: 0 for k in ('team_vote', 'coach_argmax', 'majority', 'any_right')}
    hits = {k: {} for k in rules}
    for i, r in enumerate(rows):
        ans = [preds[n][r['id']] for n in names]
        right = [bool(is_hit(a, r)) for a in ans]
        w = {}
        for a, p in zip(ans, probs[i].tolist()):
            w[norm(a)] = w.get(norm(a), 0.0) + p
        c = {}
        for a in ans:
            c[norm(a)] = c.get(norm(a), 0) + 1
        top = max(c.values())
        tied = [a for a, k in c.items() if k == top]
        got = dict(team_vote=is_hit(max(w, key=w.get), r), coach_argmax=right[int(probs[i].argmax())],
                   majority=sum(is_hit(a, r) for a in tied) / len(tied), any_right=any(right))
        for k, v in got.items():
            rules[k] += float(v)
            hits[k][r['id']] = float(v)
    return {k: 100 * v / max(len(rows), 1) for k, v in rules.items()}, hits


def final_eval(members, names, coach, args, device, amp):
    out = {}
    for split in DEV_SPLITS:
        rows = _dev_rows(args.data, split, args.eval_max)
        if not rows:
            continue
        ds = Dataset(rows, members[0].vocab, strict=False)
        probs = coach_probs(coach, ds, list(range(len(rows))), device, amp).cpu()
        preds, res = {}, {'members': {}}
        for n, m in zip(names, members):
            with amp():
                r = evaluate(m, rows, args.eval_batch, device, return_preds=True)
            preds[n] = r.pop('preds')
            res['members'][n] = {'exact': r['exact'], 'by_family': r['by_family']}
        res['team'], hits = team_scores(names, preds, probs, rows)
        res['coach_share'] = {n: float(probs[:, i].mean()) for i, n in enumerate(names)}
        res['rows'] = {r['id']: {'family': r['family'], **{n: [preds[n][r['id']], int(is_hit(preds[n][r['id']], r))] for n in names},
                                 'coach': [round(x, 3) for x in probs[i].tolist()]} for i, r in enumerate(rows)}
        out[split] = res
        jprint(event='eval', split=split, n=len(rows), **{k: round(v, 2) for k, v in res['team'].items()},
               **{n: round(res['members'][n]['exact'], 2) for n in names})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', choices=['on', 'off'], required=True)
    ap.add_argument('--members', default=json.dumps(MEMBERS), help='JSON [[name, model, cfg], ...]')
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--steps', type=int, default=24000)
    ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--coach-lr', type=float, default=1e-3)
    ap.add_argument('--warmup', type=int, default=300)
    ap.add_argument('--grad-clip', type=float, default=1.0)
    ap.add_argument('--mix', type=float, default=0.5, help='route on: share of the sampling prob that follows the coach')
    ap.add_argument('--label-every', type=int, default=8)
    ap.add_argument('--label-rows', type=int, default=64)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--device', default='auto')
    ap.add_argument('--bf16', action='store_true')
    ap.add_argument('--log-every', type=int, default=500)
    ap.add_argument('--final-eval', action='store_true')
    ap.add_argument('--eval-max', type=int)
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--minutes', type=float)
    ap.add_argument('--out')
    args = ap.parse_args(argv)
    spec = json.loads(args.members)
    names = [s[0] for s in spec]
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if args.bf16 and device.type == 'cuda' else contextlib.nullcontext
    random.seed(args.seed); np.random.seed(args.seed)
    t_start = time.time()

    rows = load_rows(os.path.join(args.data, 'train.jsonl'))
    vocab = CharVocab.get(args.data, None, rows)
    ds = Dataset(rows, vocab)
    members = []
    for _, model, cfg in spec:          # same init as the member's solo train.py run at this seed
        torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
        members.append(build(model, vocab, **cfg).to(device))
    torch.manual_seed(args.seed + 7919)
    coach = Coach(len(vocab), len(members)).to(device)
    opts = [make_opt(m, args.lr, device) for m in members]
    copt = make_opt(coach, args.coach_lr, device)
    gen = torch.Generator().manual_seed(args.seed + 1)
    jprint(event='start', route=args.route, members=names, n_params={n: m.n_params() for n, m in zip(names, members)},
           coach_params=sum(p.numel() for p in coach.parameters()), device=str(device), rows=len(rows))

    P, B, M = 2 * args.batch, args.batch, len(members)
    pool_it = pools(len(ds), P, args.seed)
    cap = args.minutes * 60 if args.minutes else None
    t0, step, status = time.time(), 0, 'ok'
    run = {n: 0.0 for n in names} | {'coach': 0.0, 'coach_n': 0, 'n': 0}
    right = torch.zeros(M); labelled = 0; share = torch.zeros(M); peak = 0.0
    for m in members:
        m.train()
    coach.train()
    while step < args.steps:
        elapsed = time.time() - t0
        if cap and elapsed >= cap:
            status = 'time_cap'
            break
        lr = lr_at(step, args.steps, args.warmup, args.lr, elapsed, cap)
        clr = lr_at(step, args.steps, args.warmup, args.coach_lr, elapsed, cap)
        for o in opts:
            for g in o.param_groups:
                g['lr'] = lr
        for g in copt.param_groups:
            g['lr'] = clr
        idx = next(pool_it)
        pi = coach_probs(coach, ds, idx, device, amp).cpu()
        share += pi.mean(0); peak += float(pi.max(1).values.mean())
        for i, (n, m, o) in enumerate(zip(names, members, opts)):
            if args.route == 'on':
                q = (1 - args.mix) / P + args.mix * pi[:, i] / pi[:, i].sum()
                sel = torch.multinomial(q, B, replacement=False, generator=gen)
            else:
                sel = torch.randperm(P, generator=gen)[:B]
            batch = to_device(collate([ds[j] for j in idx[sel.numpy()]]), device)
            with amp():
                out = m.loss(batch)
            loss = out[0] if isinstance(out, tuple) else out
            loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), args.grad_clip)
            o.step(); o.zero_grad(set_to_none=True)
            run[n] += float(loss.detach())
        run['n'] += 1
        if step % args.label_every == 0:
            lab = idx[torch.randperm(P, generator=gen)[:args.label_rows].numpy()]
            lb = to_device(collate([ds[j] for j in lab]), device)
            with amp():
                outs = [answers(m, lb) for m in members]
            hit = torch.tensor([[float(is_hit(outs[k][r], rows[j])) for k in range(M)] for r, j in enumerate(lab)])
            right += hit.sum(0); labelled += len(lab)
            keep = hit.sum(1) > 0
            if keep.any():
                tgt = (hit[keep] / hit[keep].sum(1, keepdim=True)).to(device)
                with amp():
                    lg = coach(lb)
                closs = -(tgt * lg[keep.to(device)].log_softmax(-1)).sum(1).mean()
                closs.backward()
                torch.nn.utils.clip_grad_norm_(coach.parameters(), args.grad_clip)
                copt.step(); copt.zero_grad(set_to_none=True)
                run['coach'] += float(closs.detach()); run['coach_n'] += 1
        step += 1
        if step % args.log_every == 0 or step == args.steps:
            jprint(event='train', step=step, lr=round(lr, 7), elapsed=round(time.time() - t0, 1),
                   **{f'loss_{n}': round(run[n] / max(run['n'], 1), 5) for n in names},
                   coach_loss=round(run['coach'] / max(run['coach_n'], 1), 4), coach_max=round(peak / max(run['n'], 1), 3),
                   **{f'right_{n}': round(float(right[k]) / max(labelled, 1), 3) for k, n in enumerate(names)},
                   **{f'share_{n}': round(float(share[k]) / max(run['n'], 1), 3) for k, n in enumerate(names)})
            run = {n: 0.0 for n in names} | {'coach': 0.0, 'coach_n': 0, 'n': 0}
            right.zero_(); labelled = 0; share.zero_(); peak = 0.0
    if device.type == 'cuda':
        torch.cuda.synchronize()
    train_s = time.time() - t0
    result = dict(config=dict(vars(args), members=spec), n_params={n: m.n_params() for n, m in zip(names, members)},
                  coach_params=sum(p.numel() for p in coach.parameters()), steps=step, status=status, train_s=train_s,
                  steps_per_s=step / max(train_s, 1e-9), final_eval=None)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        torch.save(dict(members=[dict(model=m.state_dict(), name=s[1], cfg=s[2], label=s[0]) for s, m in zip(spec, members)],
                        coach=coach.state_dict(), chars=vocab.chars, step=step), os.path.join(args.out, 'checkpoint.pt'))
    def write():
        result['wall_s'] = time.time() - t_start
        if args.out:
            json.dump(result, open(os.path.join(args.out, 'RESULT.json'), 'w'))
    write()
    if args.final_eval:
        result['final_eval'] = final_eval(members, names, coach, args, device, amp)
        write()
    jprint(event='done', steps=step, status=status, steps_per_s=round(result['steps_per_s'], 3), wall_s=round(result['wall_s'], 1))
    return result


if __name__ == '__main__':
    main()
