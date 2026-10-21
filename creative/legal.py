"""Rule-masked try sampling for C1 (read-only probe; nothing here trains). A copy of sampler.sample_run's loop where each written step is drawn
from B2's own heads restricted to what the C1 rules allow, at a chosen strictness level. B2's weights and logits are unchanged; only the
choice among them is masked, so the model still decides WHICH legal step to take.

Levels (each adds to the one before):
  0  no mask (= sampler.sample_run)
  1  ops: + - x / on the k-1 real steps, NOOP after them; the answer pointer is the last result (k = given numbers)
  2  operands: given numbers or written results only (no constant, no target slot), the two operands differ
  3  each slot used once: operands come from the unspent pool (given numbers not yet used, results not yet used)
  4  exact division (a step whose result the executor marks invalid is masked): every try follows the rules
The joint of a step is log p(op) + log p(a) + log p(b) at temperature T (each head divided by T), renormalised over the allowed triples."""
import math
import torch
import torch.nn.functional as F
from custom_io.models.ledger import execute, value_code
from custom_io.models import progparse as pp
from creative.programs import ARITH, COMM, M, N_RES, R0, raw_key
from creative.sampler import N_NUM, N_REG, TryRec, _tries_from, make_batch

ARITH_T = torch.tensor(ARITH)


def _allowed(level, k, s, avail, written, vals, valid):
    """-> bool [B, 9, M, M] of allowed (op, a, b) for step s of rows with k given numbers (k [B]); rows with s >= k-1 get NOOP only."""
    B, dev = k.shape[0], k.device
    real = s < (k - 1)                                                                  # [B]
    op_ok = torch.zeros(B, len(pp.OPS), dtype=torch.bool, device=dev)
    op_ok[:, ARITH_T.to(dev)] = True
    allow = op_ok[:, :, None, None].expand(B, len(pp.OPS), M, M).clone()
    if level >= 2:
        slot_ok = written.clone()                                                          # given numbers 0..k-1 and written results
        allow &= slot_ok[:, None, :, None] & slot_ok[:, None, None, :]
        allow &= ~torch.eye(M, dtype=torch.bool, device=dev)[None, None]
    if level >= 3:
        allow &= avail[:, None, :, None] & avail[:, None, None, :]
    if level >= 4:
        a_v, b_v = vals[:, :, None].expand(B, M, M), vals[:, None, :].expand(B, M, M)
        for op in ARITH:
            _, ok = execute(torch.full((B * M * M,), op, dtype=torch.long, device=dev), a_v.reshape(-1), b_v.reshape(-1))
            allow[:, op] &= ok.view(B, M, M) & valid[:, :, None] & valid[:, None, :]
    noop = torch.zeros_like(allow)
    noop[:, 0, 0, 0] = True
    return torch.where(real[:, None, None, None], allow, noop)


@torch.no_grad()
def sample_run_masked(model, batch, k, level=4, temperature=1.0, greedy=False, gen=None, first=None, stop_at=None):
    """Like sampler.sample_run, with level-`level` masks. k: LongTensor [B] of given-number counts. stop_at=1 returns the masked step-1 joint."""
    if level == 0:
        from creative.sampler import sample_run
        return sample_run(model, batch, temperature, greedy, gen, first, stop_at)
    was = model.training
    model.eval()
    X, xm = model.reader(batch)
    ns, ne, nv, ws, we = model.tokenize(batch)
    B, T, dev = X.shape[0], X.shape[1], X.device
    k = k.to(dev)
    t_ix = torch.arange(T, device=dev)
    inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])
    cnt = inn.sum(-1)
    pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
    consts = torch.tensor(pp.CONSTS, device=dev).expand(B, -1)
    vals = torch.cat([nv, consts, torch.zeros(B, pp.N_RES, dtype=torch.long, device=dev)], 1)
    valid = torch.cat([cnt > 0, torch.ones_like(consts, dtype=torch.bool), torch.zeros(B, pp.N_RES, dtype=torch.bool, device=dev)], 1)
    slot = torch.arange(M, device=dev)
    written = slot[None] < k[:, None]                                                    # given numbers (not the target slot k)
    avail = written.clone()
    R_ = pp.R0
    S0 = model.vcode(value_code(vals[:, :R_], valid[:, :R_])) * valid[:, :R_, None]
    S0 = torch.cat([S0[:, :N_NUM] + pool + model.ordinal.weight + model.stype.weight[0], S0[:, N_NUM:] + model.stype.weight[1]], 1)
    S0 = S0 * valid[:, :R_, None]
    Rs = torch.zeros(B, pp.N_RES, model.d, device=dev, dtype=S0.dtype)
    kvx = [b.kv_of(X + model.src.weight[1]) for b in model.core]
    Z = torch.cat([model.ctrl.weight, model.reader.place.weight[:N_REG]]).expand(B, -1, -1)
    ops, As, Bs = [], [], []
    for t in range(model.n_loops):
        ts = min(t, model.n_loops - 1)
        S = torch.cat([S0, Rs], 1)
        kvs = [b.kv_of(S + model.src.weight[0]) for b in model.core]
        mask = torch.cat([valid, xm], 1)
        Z = Z + model.step_emb.weight[ts]
        for b, kx, ks in zip(model.core, kvx, kvs):
            Z = b(Z, ks, kx, mask)
        if not 1 <= t <= pp.N_RES:
            continue
        s = t - 1
        z = model.ln_z(Z[:, 0])
        ks_ = model.k_slot(model.ln_k(torch.cat([S0, Rs], 1)))
        lop, la, lb = model.op_head(z), model.ptr(model.q_a(z), ks_, valid), model.ptr(model.q_b(z), ks_, valid)
        Tm = 1.0 if (greedy or temperature <= 0) else temperature
        joint = ((lop.float() / Tm).log_softmax(-1)[:, :, None, None] + (la.float() / Tm).log_softmax(-1)[:, None, :, None]
                 + (lb.float() / Tm).log_softmax(-1)[:, None, None, :])
        allow = _allowed(level, k, s, avail, written, vals, valid)
        joint = joint.masked_fill(~allow, -1e30)
        if stop_at == 1 and t == 1:
            model.train(was)
            return dict(joint=joint, allow=allow)
        flat = joint.reshape(B, -1)
        if greedy or temperature <= 0:
            idx = flat.argmax(-1)
        else:
            idx = torch.multinomial(flat.softmax(-1), 1, generator=gen)[:, 0]
        op, rem = idx // (M * M), idx % (M * M)
        a, b = rem // M, rem % M
        if t == 1 and first is not None:
            f_op, f_a, f_b = (x.to(dev) for x in first)
            fm = f_op >= 0
            op, a, b = torch.where(fm, f_op, op), torch.where(fm, f_a, a), torch.where(fm, f_b, b)
        ops.append(op); As.append(a); Bs.append(b)
        v, ok = execute(op, vals.gather(1, a[:, None])[:, 0], vals.gather(1, b[:, None])[:, 0])
        vals, valid = vals.clone(), valid.clone()
        vals[:, R_ + s], valid[:, R_ + s] = v, ok
        realstep = op != 0
        written = written.clone(); avail = avail.clone()
        written[:, R_ + s] |= realstep & ok
        ar = torch.arange(B, device=dev)
        avail[ar, a] &= ~realstep; avail[ar, b] &= ~realstep
        avail[:, R_ + s] |= realstep & ok
        new = (model.vcode(value_code(v, ok)) + model.stype.weight[2] + model.op_emb(op) + model.step_emb.weight[ts] + model.res_from_z(z)) * ok[:, None]
        Rs = torch.cat([Rs[:, :t - 1], new[:, None].to(Rs.dtype), Rs[:, t:]], 1)
    ans = R_ + (k - 2).clamp(min=0)                                                      # the last result
    pad = lambda xs: torch.stack(xs + [torch.zeros(B, dtype=torch.long, device=dev)] * (pp.N_RES - len(xs)), 1)
    model.train(was)
    return dict(ops=pad(ops), a=pad(As), b=pad(Bs), ans=ans, mode=torch.zeros_like(ans), vals=vals, valid=valid)


def _k(rows):
    return torch.tensor([len(r['nums']) for r in rows], dtype=torch.long)


@torch.no_grad()
def first_step_candidates_masked(model, rows, vocab, device, level, k=8, bs=256):
    """Top-k ALLOWED first steps per row by joint log-probability at T = 1, commutative operand orders merged (level 0 = the plain sampler's)."""
    if level == 0:
        from creative.sampler import first_step_candidates
        return first_step_candidates(model, rows, vocab, device, k, bs)
    out = []
    for s in range(0, len(rows), bs):
        rs = rows[s:s + bs]
        batch = make_batch(rs, vocab, device)
        lg = sample_run_masked(model, batch, _k(rs), level, 1.0, stop_at=1)
        joint = lg['joint']
        for i in range(joint.shape[0]):
            flat = joint[i].reshape(-1)
            seen, cands = set(), []
            for idx in torch.topk(flat, min(flat.numel(), 12 * k)).indices.tolist():
                if flat[idx] < -1e29:
                    break
                op, rem = divmod(idx, M * M)
                a, b = divmod(rem, M)
                key = (op, min(a, b), max(a, b)) if op in COMM else (op, a, b)
                if key not in seen:
                    seen.add(key)
                    cands.append((op, a, b))
                if len(cands) == k:
                    break
            out.append(cands)
    return out


@torch.no_grad()
def sample_tries_masked(model, rows, vocab, device, n_tries=32, temperature=1.0, level=4, branch=8, max_rounds=4, seed=0, bs=2048):
    """sampler.sample_tries with level-`level` masks (same branching, dedup and top-up rounds). -> (tries, raw)."""
    gen = torch.Generator(device=device)
    gen.manual_seed(seed)
    cands = first_step_candidates_masked(model, rows, vocab, device, level, branch) if branch else [[] for _ in rows]
    tries, keys, raw = [[] for _ in rows], [set() for _ in rows], [0] * len(rows)

    def draw(plan):
        for s in range(0, len(plan), bs):
            chunk = plan[s:s + bs]
            rs = [rows[i] for i, _, _ in chunk]
            batch = make_batch(rs, vocab, device)
            first = tuple(torch.tensor([(f[j] if f else -1) for _, f, _ in chunk]).long() for j in range(3))
            out = sample_run_masked(model, batch, _k(rs), level, temperature, False, gen, first)
            for (i, _, br), rec in zip(chunk, _tries_from(out)):
                raw[i] += 1
                kk = raw_key(rec.t)
                if kk not in keys[i] and len(tries[i]) < n_tries:
                    keys[i].add(kk)
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
def raw_samples(model, rows, vocab, device, n=32, temperature=1.0, level=0, seed=0, bs=2048):
    """n independent samples per row, NO dedup and NO branching: the model's own per-sample distribution. -> tries[i] = list of TryRec."""
    gen = torch.Generator(device=device)
    gen.manual_seed(seed)
    plan = [i for i in range(len(rows)) for _ in range(n)]
    out = []
    for s in range(0, len(plan), bs):
        rs = [rows[i] for i in plan[s:s + bs]]
        out += _tries_from(sample_run_masked(model, make_batch(rs, vocab, device), _k(rs), level, temperature, False, gen))
    return [out[i * n:(i + 1) * n] for i in range(len(rows))]
