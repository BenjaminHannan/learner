"""The shared sampler (D4, try time): sample B2's op and operand heads at a DEV-chosen temperature, branch over the top first steps,
and drop duplicate programs. Used by C1 and C2 alike (the checker is the only thing that differs).

sample_run() re-implements the loop of custom_io.models.ledger.Ledger.run (which cannot be edited from here) with a sampling decision
where run() takes argmax; its greedy mode is tested to reproduce run()'s program and answer pointer exactly.

A try = the written steps (op, operand slot a, operand slot b) plus the answer pointer. B2's heads choose the op and the two operand
pointers independently at each step, so the first-step candidates are ranked by log p(op) + log p(a) + log p(b) (NOOP excluded)."""
import math
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn.functional as F
from custom_io.data import Dataset, collate, to_device
from custom_io.models.ledger import ADD, SUB, execute, value_code
from custom_io.models import progparse as pp
from creative.programs import COMM, M, N_RES, R0, Try, raw_key

N_NUM, N_REG = pp.N_NUM, 9


@dataclass
class TryRec:
    t: Try
    mode: int = 0
    branch: int = -1            # which first-step branch produced it (-1 = free sample)


def make_batch(rows, vocab, device):
    ds = Dataset(rows, vocab, strict=False)
    return to_device(collate([ds[i] for i in range(len(rows))]), device)


def _pick(logits, temperature, greedy, gen):
    if greedy or temperature <= 0:
        return logits.argmax(-1)
    p = F.softmax(logits.float() / temperature, -1)
    return torch.multinomial(p, 1, generator=gen)[:, 0]


@torch.no_grad()
def sample_run(model, batch, temperature=1.0, greedy=False, gen=None, first=None, stop_at=None, loops=None):
    """One pass of a Ledger / B2 with sampled decisions.
    first: optional (op [B], a [B], b [B]) long tensors forced at step 1 (rows where op < 0 are sampled normally).
    loops: run this many loops instead of model.n_loops (the 'loops:K' lesion; loops=0 writes no steps).
    stop_at=1: return the step-1 logits (dict(lop, la, lb)) right after computing them (no sampling, no execution).
    -> dict(ops [B,7], a [B,7], b [B,7], ans [B], mode [B], vals [B,M], valid [B,M])."""
    was = model.training
    model.eval()
    X, xm = model.reader(batch)
    ns, ne, nv, ws, we = model.tokenize(batch)
    B, T, dev = X.shape[0], X.shape[1], X.device
    t_ix = torch.arange(T, device=dev)
    inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])
    cnt = inn.sum(-1)
    pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
    consts = torch.tensor(pp.CONSTS, device=dev).expand(B, -1)
    vals = torch.cat([nv, consts, torch.zeros(B, pp.N_RES, dtype=torch.long, device=dev)], 1)
    valid = torch.cat([cnt > 0, torch.ones_like(consts, dtype=torch.bool), torch.zeros(B, pp.N_RES, dtype=torch.bool, device=dev)], 1)
    R_ = pp.R0
    S0 = model.vcode(value_code(vals[:, :R_], valid[:, :R_])) * valid[:, :R_, None]
    S0 = torch.cat([S0[:, :N_NUM] + pool + model.ordinal.weight + model.stype.weight[0], S0[:, N_NUM:] + model.stype.weight[1]], 1)
    S0 = S0 * valid[:, :R_, None]
    Rs = torch.zeros(B, pp.N_RES, model.d, device=dev, dtype=S0.dtype)
    kvx = [b.kv_of(X + model.src.weight[1]) for b in model.core]
    Z = torch.cat([model.ctrl.weight, model.reader.place.weight[:N_REG]]).expand(B, -1, -1)
    ops, As, Bs = [], [], []
    for t in range(model.n_loops if loops is None else loops):
        ts = min(t, model.n_loops - 1)
        S = torch.cat([S0, Rs], 1)
        kvs = [b.kv_of(S + model.src.weight[0]) for b in model.core]
        mask = torch.cat([valid, xm], 1)
        Z = Z + model.step_emb.weight[ts]
        for b, kx, ks in zip(model.core, kvx, kvs):
            Z = b(Z, ks, kx, mask)
        if not 1 <= t <= pp.N_RES:
            continue
        z = model.ln_z(Z[:, 0])
        ks_ = model.k_slot(model.ln_k(torch.cat([S0, Rs], 1)))
        lop, la, lb = model.op_head(z), model.ptr(model.q_a(z), ks_, valid), model.ptr(model.q_b(z), ks_, valid)
        if stop_at == 1 and t == 1:
            model.train(was)
            return dict(lop=lop.float(), la=la.float(), lb=lb.float())
        op, a, b = (_pick(l, temperature, greedy, gen) for l in (lop, la, lb))
        if t == 1 and first is not None:
            f_op, f_a, f_b = (x.to(dev) for x in first)
            m = f_op >= 0
            op, a, b = torch.where(m, f_op, op), torch.where(m, f_a, a), torch.where(m, f_b, b)
        ops.append(op); As.append(a); Bs.append(b)
        v, ok = execute(op, vals.gather(1, a[:, None])[:, 0], vals.gather(1, b[:, None])[:, 0])
        vals, valid = vals.clone(), valid.clone()
        vals[:, R_ + t - 1], valid[:, R_ + t - 1] = v, ok
        new = (model.vcode(value_code(v, ok)) + model.stype.weight[2] + model.op_emb(op) + model.step_emb.weight[ts] + model.res_from_z(z)) * ok[:, None]
        Rs = torch.cat([Rs[:, :t - 1], new[:, None].to(Rs.dtype), Rs[:, t:]], 1)
    zf = model.ln_z(Z[:, 1])
    ks_ = model.k_slot(model.ln_k(torch.cat([S0, Rs], 1)))
    lans = model.ptr(model.q_ans(zf), ks_, valid)
    ans = _pick(lans, temperature, greedy, gen)
    mode = model.mode_head(zf).argmax(-1)
    pad = lambda xs: torch.stack(xs + [torch.zeros(B, dtype=torch.long, device=dev)] * (pp.N_RES - len(xs)), 1)
    model.train(was)
    return dict(ops=pad(ops), a=pad(As), b=pad(Bs), ans=ans, mode=mode, vals=vals, valid=valid)


def _tries_from(out):
    ops, a, b, ans, mode = (out[k].cpu().tolist() for k in ('ops', 'a', 'b', 'ans', 'mode'))
    return [TryRec(Try(tuple(ops[i]), tuple(a[i]), tuple(b[i]), ans[i]), mode[i]) for i in range(len(ans))]


@torch.no_grad()
def first_step_candidates(model, rows, vocab, device, k=8, bs=256):
    """Top-k first steps per row by joint log-probability, NOOP excluded, commutative operand orders merged. -> list of [(op, a, b)]."""
    out = []
    for s in range(0, len(rows), bs):
        batch = make_batch(rows[s:s + bs], vocab, device)
        lg = sample_run(model, batch, stop_at=1)
        lop, la, lb = lg['lop'].log_softmax(-1), lg['la'].log_softmax(-1), lg['lb'].log_softmax(-1)
        joint = lop[:, 1:, None, None] + la[:, None, :, None] + lb[:, None, None, :]            # [B, ops-1, M, M]
        for i in range(joint.shape[0]):
            flat = joint[i].reshape(-1)
            seen, cands = set(), []
            for idx in torch.topk(flat, min(flat.numel(), 12 * k)).indices.tolist():
                op, rem = divmod(idx, M * M)
                a, b = divmod(rem, M)
                op += 1
                key = (op, min(a, b), max(a, b)) if op in COMM else (op, a, b)
                if key not in seen and flat[idx] > -1e8:
                    seen.add(key)
                    cands.append((op, a, b))
                if len(cands) == k:
                    break
            out.append(cands)
    return out


@torch.no_grad()
def sample_tries(model, rows, vocab, device, n_tries=32, temperature=1.0, branch=8, max_rounds=4, seed=0, bs=2048, loops=None):
    """The shared sampler. For each row: n_tries samples, the first round split evenly over the top-`branch` first steps (each branch forces
    its first step and samples the rest), duplicates dropped, then free top-up rounds (up to max_rounds in all) until n_tries distinct
    programs or the rounds run out. -> (tries, raw) with tries[i] = list of TryRec (<= n_tries distinct) and raw[i] = programs sampled."""
    gen = torch.Generator(device=device)
    gen.manual_seed(seed)
    cands = first_step_candidates(model, rows, vocab, device, branch) if branch and loops != 0 else [[] for _ in rows]
    branch = branch if loops != 0 else 0
    tries, keys, raw = [[] for _ in rows], [set() for _ in rows], [0] * len(rows)

    def draw(plan):
        """plan = [(row_idx, first_step_or_None, branch_id)] -> adds the new distinct tries."""
        for s in range(0, len(plan), bs):
            chunk = plan[s:s + bs]
            batch = make_batch([rows[i] for i, _, _ in chunk], vocab, device)
            first = tuple(torch.tensor([(f[j] if f else -1) for _, f, _ in chunk]) for j in range(3))
            first = tuple(x.long() for x in first)
            out = sample_run(model, batch, temperature, False, gen, first, loops=loops)
            for (i, _, br), rec in zip(chunk, _tries_from(out)):
                raw[i] += 1
                k = raw_key(rec.t)
                if k not in keys[i] and len(tries[i]) < n_tries:
                    keys[i].add(k)
                    rec.branch = br
                    tries[i].append(rec)

    per = math.ceil(n_tries / branch) if branch else 0
    draw([(i, c, bi) for i in range(len(rows)) for bi, c in enumerate(cands[i]) for _ in range(per)] if branch else
         [(i, None, -1) for i in range(len(rows)) for _ in range(n_tries)])
    for _ in range(max_rounds - 1):
        todo = [(i, None, -1) for i in range(len(rows)) for _ in range(2 * (n_tries - len(tries[i])))]
        if not todo:
            break
        draw(todo)
    return tries, raw


@torch.no_grad()
def greedy_tries(model, rows, vocab, device, bs=512):
    """The first try the user would see: one greedy pass per row. -> list of TryRec."""
    out = []
    for s in range(0, len(rows), bs):
        out += _tries_from(sample_run(model, make_batch(rows[s:s + bs], vocab, device), greedy=True))
    return out


def rule_follower_tries(rows, n_tries=32, seed=0, max_draws=2000):
    """The value-blind rule follower: random programs that obey the rules (each step takes two distinct unspent given numbers or results, op from
    + - x /, the last result is the answer), without looking at any target. Same dedup as the shared sampler (up to n_tries distinct).
    Its per-try luck equals puzzles.rules_only_floor. -> list of [TryRec]."""
    import random
    from creative.programs import ARITH
    rng = random.Random(seed)
    out = []
    for row in rows:
        k, keys, tr = len(row['nums']), set(), []
        for _ in range(max_draws):
            pool, steps = list(range(k)), []
            while len(pool) > 1:
                a, b = rng.sample(pool, 2)
                steps.append((rng.choice(ARITH), a, b))
                pool = [x for x in pool if x not in (a, b)] + [R0 + len(steps) - 1]
            t = Try.make(steps, pool[0])
            if raw_key(t) not in keys:
                keys.add(raw_key(t))
                tr.append(TryRec(t))
            if len(tr) == n_tries:
                break
        out.append(tr)
    return out
