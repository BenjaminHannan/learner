"""Roadmap 7d, the creative part of sleep (screens S1 and S3). CPU, DEV and pool only: C2 test / labelled and K_new test are never opened.
  python3 -m creative.sleep7d s1 --nprime ~/c7d/s100/Nprime.pt ~/c7d/s101/Nprime.pt --out DIR [--pool-limit N --dev-limit N --n2 480 --seed 0]
  python3 -m creative.sleep7d s1report --out DIR --parents s100 s101          (the verdict over both parents)
  python3 -m creative.sleep7d s3 --nprime ... --out DIR --skills-train train.jsonl --skills-data data_big
Pieces: a switchable low-rank adapter ("creative mode") on top of N' (adapter OFF = N' bit for bit, the worker); logp_tries (a teacher-forced copy of
sampler.sample_run's loop with gradients on); the day (worker first try = greedy with the adapter off, the example check says pass or fail, creative mode
searches the stuck rows only); loop 1 (reward sleep on the adapter only: fitting tries up, failing tries down, KL to the pre-night adapter);
S1 = does a night's reward sleep make creative mode find answers faster on the kinds it was stuck on (C2 DEV reach@32, roadmap ruling 13f4b987eb) than an untrained
adapter (U) or a reward-shuffled one (S); transfer to new kinds (the K_new candidates N' reached at 512 tries) is report-only;
S3 = does sleeping the worker on its own shaky passes (P) beat sleeping it on replay only (Z). Answer keys score; they never pick a record or a setting."""
import argparse, contextlib, copy, hashlib, json, math, os, pickle, random, time
import torch
import torch.nn as nn
import torch.nn.functional as F
from custom_io.models import progparse as pp
from custom_io.models.ledger import execute, value_code
from creative import c2_pilot, c2_stones, fewshot, legal, rules_real as R, sampler, sleep, stones
from creative.pilot import skills_eval
from creative.programs import N_RES, raw_key, result_key, run

DATA = 'creative/data/c2'
KNEW = 'creative/data/knew'
T_POOL = 3.0
LORA_LAYERS = ('q', 'kv', 'o', 'qkv', 'p', 'fc', 'out')          # per core block, as fastsleep.m_lora
LORA_HEADS = ('op_head', 'q_a', 'q_b', 'q_ans')
HEADS = ('lop', 'la', 'lb', 'lans')
GROUPS = dict(near_copy=c2_pilot.COPY_KINDS, multi_step=c2_pilot.HARD_KINDS)
TRANSFER_KINDS = ('sq_minus', 'triple_add', 'mult_sub')        # report-only transfer set: the K_new candidates N' reached at all at 512 tries (roadmap 13f4b987eb)


# ---------------------------------------------------------------- the example check (job 8's functions, copied: that file is not on this branch)
def pyfit(p, t):
    """Cheap exact prefilter for fewshot.verdict == 'accept': a try that fails the structure rules or the python executor's example check can never be accepted (the torch executor
    only adds an agreement test), so the 2.5 ms torch check runs on survivors only."""
    try:
        if not fewshot.structure(p, t)[0]:
            return False
        a = fewshot.outputs_py(p, t)
        return all(o is not None for o in a) and a[:-1] == p['ys']
    except Exception:
        return False


def fits(p, t):
    return pyfit(p, t) and fewshot.verdict(p, t)[0] == 'accept'


def has_fit(rows, tries):
    """Per question: does any try fit every example? Reads only the example check (not the key, not the kind)."""
    return [any(fits(fewshot.parse(r['prompt']), x.t) for x in tr) for r, tr in zip(rows, tries)]


def search(model, pool, vocab, device, seed, T=T_POOL, n1=32, n2=480):
    """Job 8's two-pass search on the model as it stands (S3's W night). -> (combined tries per question in sampling order, fit1, fit_final, drawn dict)."""
    t1 = legal.raw_samples(model, pool, vocab, device, n=n1, temperature=T, level=0, seed=seed)
    fit1 = has_fit(pool, t1)
    stuck = [i for i, f in enumerate(fit1) if not f]
    tries = [list(t) for t in t1]
    if stuck:
        t2 = legal.raw_samples(model, [pool[i] for i in stuck], vocab, device, n=n2, temperature=T, level=0, seed=seed + 1000)
        for i, t in zip(stuck, t2):
            tries[i] += t
    fit = has_fit(pool, tries)
    return tries, fit1, fit, dict(pass1=n1 * len(pool), pass2=n2 * len(stuck), stuck_questions=len(stuck))


def w_records(pool, tries, seed, per_cap=2, arm='W'):
    """At most `per_cap` distinct example-fitting tries per question, answered by the try's own output (same selection as fewshot.build_arms' W)."""
    rng = random.Random(seed)
    out, counts = [], {}
    for row, tr in zip(pool, tries):
        p = fewshot.parse(row['prompt'])
        kept = fewshot._distinct(p, [x for x in tr if pyfit(p, x.t)], rng, per_cap, lambda rules, full: full[0] == 'accept')
        for k, t in enumerate(kept):
            out.append(fewshot._record(row, t, arm, k))
        if kept:
            counts[row['id']] = len(kept)
    return out, counts


# ---------------------------------------------------------------- 1. the creative adapter
class _Flag:
    """One shared on/off switch (model._creative). Plain object so deepcopy keeps every wrapper pointing at its own model's flag."""
    on = False


class _SwLoRA(nn.Module):
    """fastsleep._LoRA with a switch: flag off returns exactly base(x) (no added zero term: bit-identical), on adds the low-rank term."""

    def __init__(self, base, r, alpha, flag, gen=None):
        super().__init__()
        self.base, self.scale, self.flag = base, alpha / r, flag
        self.A = nn.Parameter(torch.randn(r, base.in_features, generator=gen) / math.sqrt(base.in_features))
        self.B = nn.Parameter(torch.zeros(base.out_features, r))

    def forward(self, x):
        if not self.flag.on:
            return self.base(x)
        return self.base(x) + (x @ self.A.T @ self.B.T) * self.scale


def add_adapter(model, r=4, alpha=8.0, seed=0):
    """Wrap in place the layers fastsleep.m_lora wraps (every core block's q kv o qkv p fc out; op_head q_a q_b q_ans); one shared flag at model._creative (off);
    every base parameter frozen. -> the adapter parameters (A, B of each wrapper)."""
    assert not hasattr(model, '_creative'), 'adapter already added'
    flag = _Flag()
    model._creative = flag
    gen = torch.Generator().manual_seed(seed)
    for p in model.parameters():
        p.requires_grad_(False)
    for blk in model.core:
        for name in LORA_LAYERS:
            setattr(blk, name, _SwLoRA(getattr(blk, name), r, alpha, flag, gen))
    for name in LORA_HEADS:
        setattr(model, name, _SwLoRA(getattr(model, name), r, alpha, flag, gen))
    return adapter_params(model)


def _wrappers(model):
    return [(n, m) for n, m in model.named_modules() if isinstance(m, _SwLoRA)]


def adapter_params(model):
    return [p for _, m in _wrappers(model) for p in (m.A, m.B)]


@contextlib.contextmanager
def creative(model, on=True):
    """Creative mode (adapter on) or the worker (adapter off) inside the block; the previous setting comes back after."""
    flag = model._creative
    old, flag.on = flag.on, on
    try:
        yield model
    finally:
        flag.on = old


def adapter_state(model):
    return {f'{n}.{k}': getattr(m, k).detach().clone() for n, m in _wrappers(model) for k in ('A', 'B')}


def load_adapter_state(model, state):
    with torch.no_grad():
        for n, m in _wrappers(model):
            m.A.copy_(state[f'{n}.A'])
            m.B.copy_(state[f'{n}.B'])


def worker_untouched(model, ref, rows, vocab, device, perturb=False):
    """The worker-untouched test. With the adapter OFF, `model` must equal the unwrapped model `ref` bit for bit on `rows`: greedy tries (sampler.greedy_tries) AND the
    step-1 logits (sample_run stop_at=1) torch.equal. perturb=True first sets every B to random non-zero values (on a copy) and also demands that adapter ON differs.
    -> dict(passes, greedy_equal, logits_equal, [on_differs])."""
    m = copy.deepcopy(model) if perturb else model
    if perturb:
        g = torch.Generator().manual_seed(123)
        with torch.no_grad():
            for _, w in _wrappers(m):
                w.B.copy_(torch.randn(w.B.shape, generator=g) * 0.5)
    batch = sampler.make_batch(rows, vocab, device)
    with creative(m, False):
        g_off = sampler.greedy_tries(m, rows, vocab, device)
        l_off = sampler.sample_run(m, batch, stop_at=1)
    g_ref = sampler.greedy_tries(ref, rows, vocab, device)
    l_ref = sampler.sample_run(ref, batch, stop_at=1)
    out = dict(greedy_equal=g_off == g_ref, logits_equal=all(torch.equal(l_off[k], l_ref[k]) for k in ('lop', 'la', 'lb')))
    out['passes'] = out['greedy_equal'] and out['logits_equal']
    if perturb:
        with creative(m, True):
            l_on = sampler.sample_run(m, batch, stop_at=1)
            g_on = sampler.greedy_tries(m, rows, vocab, device)
        out['on_differs'] = not all(torch.equal(l_on[k], l_ref[k]) for k in ('lop', 'la', 'lb'))
        out['on_greedy_differs'] = g_on != g_ref
        out['passes'] = out['passes'] and out['on_differs']
    return out


# ---------------------------------------------------------------- 2. log-probability of a try
def logp_tries(model, rows, tries, T):
    """Teacher-forced copy of sampler.sample_run's loop (same code path, gradients ON, eval mode so no dropout): forces tries[i]'s (op, a, b) at each of the 7 steps and its
    answer pointer on rows[i] (a row may repeat; tries are TryRec or Try). The adapter flag stays as the caller set it. T = the sampling temperature.
    -> dict(lp [B] = sum over steps of log_softmax(lop/T)[op] + log_softmax(la/T)[a] + log_softmax(lb/T)[b], plus log_softmax(lans/T)[ans];
            lop [B,7,9], la / lb [B,7,M], lans [B,M]: each head's full log p_T at every step, for the KL)."""
    ts = [getattr(x, 't', x) for x in tries]
    was = model.training
    model.eval()
    dev = next(model.parameters()).device
    batch = sampler.make_batch(rows, model.vocab, dev)
    f_op, f_a, f_b = (torch.tensor([getattr(t, k) for t in ts], dtype=torch.long, device=dev) for k in ('ops', 'a', 'b'))
    f_ans = torch.tensor([t.ans for t in ts], dtype=torch.long, device=dev)
    X, xm = model.reader(batch)
    ns, ne, nv, ws, we = model.tokenize(batch)
    B, T_, _ = X.shape[0], X.shape[1], X.device
    t_ix = torch.arange(T_, device=dev)
    inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])
    cnt = inn.sum(-1)
    pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
    consts = torch.tensor(pp.CONSTS, device=dev).expand(B, -1)
    vals = torch.cat([nv, consts, torch.zeros(B, pp.N_RES, dtype=torch.long, device=dev)], 1)
    valid = torch.cat([cnt > 0, torch.ones_like(consts, dtype=torch.bool), torch.zeros(B, pp.N_RES, dtype=torch.bool, device=dev)], 1)
    R_ = pp.R0
    S0 = model.vcode(value_code(vals[:, :R_], valid[:, :R_])) * valid[:, :R_, None]
    S0 = torch.cat([S0[:, :sampler.N_NUM] + pool + model.ordinal.weight + model.stype.weight[0], S0[:, sampler.N_NUM:] + model.stype.weight[1]], 1)
    S0 = S0 * valid[:, :R_, None]
    Rs = torch.zeros(B, pp.N_RES, model.d, device=dev, dtype=S0.dtype)
    kvx = [b.kv_of(X + model.src.weight[1]) for b in model.core]
    Z = torch.cat([model.ctrl.weight, model.reader.place.weight[:sampler.N_REG]]).expand(B, -1, -1)
    lp = torch.zeros(B, device=dev)
    hop, ha, hb = [], [], []
    for t in range(model.n_loops):
        ts_ = min(t, model.n_loops - 1)
        S = torch.cat([S0, Rs], 1)
        kvs = [b.kv_of(S + model.src.weight[0]) for b in model.core]
        mask = torch.cat([valid, xm], 1)
        Z = Z + model.step_emb.weight[ts_]
        for b, kx, ks in zip(model.core, kvx, kvs):
            Z = b(Z, ks, kx, mask)
        if not 1 <= t <= pp.N_RES:
            continue
        z = model.ln_z(Z[:, 0])
        ks_ = model.k_slot(model.ln_k(torch.cat([S0, Rs], 1)))
        lop, la, lb = model.op_head(z), model.ptr(model.q_a(z), ks_, valid), model.ptr(model.q_b(z), ks_, valid)
        h = [F.log_softmax(l.float() / T, -1) for l in (lop, la, lb)]
        op, a, b = f_op[:, t - 1], f_a[:, t - 1], f_b[:, t - 1]
        for hh, x in zip(h, (op, a, b)):
            lp = lp + hh.gather(1, x[:, None])[:, 0]
        hop.append(h[0]); ha.append(h[1]); hb.append(h[2])
        v, ok = execute(op, vals.gather(1, a[:, None])[:, 0], vals.gather(1, b[:, None])[:, 0])
        vals, valid = vals.clone(), valid.clone()
        vals[:, R_ + t - 1], valid[:, R_ + t - 1] = v, ok
        new = (model.vcode(value_code(v, ok)) + model.stype.weight[2] + model.op_emb(op) + model.step_emb.weight[ts_] + model.res_from_z(z)) * ok[:, None]
        Rs = torch.cat([Rs[:, :t - 1], new[:, None].to(Rs.dtype), Rs[:, t:]], 1)
    zf = model.ln_z(Z[:, 1])
    ks_ = model.k_slot(model.ln_k(torch.cat([S0, Rs], 1)))
    lans = F.log_softmax(model.ptr(model.q_ans(zf), ks_, valid).float() / T, -1)
    lp = lp + lans.gather(1, f_ans[:, None])[:, 0]
    model.train(was)
    return dict(lp=lp, lop=torch.stack(hop, 1), la=torch.stack(ha, 1), lb=torch.stack(hb, 1), lans=lans)


def kl_to_ref(now, ref):
    """KL(pi_now || pi_ref) per try, summed over the 4 heads (op, a, b at each of 7 steps, and ans) along the teacher-forced path; each head at the temperature the two
    logp_tries dicts were computed at. Masked slots (probability 0) contribute 0."""
    tot = 0.0
    for k in HEADS:
        ln, lr = now[k], ref[k]
        term = torch.where(ln > -1e6, ln.exp() * (ln - lr), torch.zeros_like(ln))
        tot = tot + term.flatten(1).sum(1)
    return tot


# ---------------------------------------------------------------- 3. the day
def day(model, rows, vocab, device, T=T_POOL, n1=32, n2=480, seed=0, bs=2048):
    """The worker's day. First try = greedy with the adapter OFF; the example check (fits) says pass or fail; fail = stuck. Only stuck rows get job 8's search, with the adapter ON:
    n1 plain samples at T (seed), then n2 more (seed + 1000) for the stuck rows with no fitting try among the n1.
    -> dict(greedy [TryRec], greedy_fit [bool], stuck [row index], tries {row index: [TryRec] in sampling order}, fit {row index: [bool per try]} (the example check, kept so
    nothing re-runs it), fit1 {row index: bool, a fit among the n1}, drawn dict)."""
    with creative(model, False):
        gt = sampler.greedy_tries(model, rows, vocab, device)
    gf = [fits(fewshot.parse(r['prompt']), t.t) for r, t in zip(rows, gt)]
    stuck = [i for i, f in enumerate(gf) if not f]
    tries, flags, fit1 = {}, {}, {}
    flag = lambda i, ts: [fits(fewshot.parse(rows[i]['prompt']), x.t) for x in ts]
    with creative(model, True):
        if stuck:
            t1 = legal.raw_samples(model, [rows[i] for i in stuck], vocab, device, n=n1, temperature=T, level=0, seed=seed, bs=bs)
            for i, t in zip(stuck, t1):
                tries[i] = list(t)
                flags[i] = flag(i, t)
                fit1[i] = any(flags[i])
            more = [i for i in stuck if not fit1[i]]
            if more:
                t2 = legal.raw_samples(model, [rows[i] for i in more], vocab, device, n=n2, temperature=T, level=0, seed=seed + 1000, bs=bs)
                for i, t in zip(more, t2):
                    tries[i] += t
                    flags[i] += flag(i, t)
        else:
            more = []
    return dict(greedy=gt, greedy_fit=gf, stuck=stuck, tries=tries, fit=flags, fit1=fit1,
                drawn=dict(greedy=len(rows), pass1=n1 * len(stuck), pass2=n2 * len(more), stuck_rows=len(stuck), pass2_rows=len(more)))


# ---------------------------------------------------------------- 4. loop 1, reward sleep on the adapter only
def kept_tries(rows, d, seed, k_fit=8, k_fail=8):
    """Per stuck row: distinct tries (programs.raw_key, first draw kept); up to k_fit fitting and k_fail failing ones chosen at random (seeded). Reward r = 1 if the try fits
    every example else 0; advantage = r - mean(r) over that row's kept tries. Rows with no fitting or no failing try have advantage 0 everywhere: dropped and counted.
    -> dict(items [dict(i, row, t, r, adv)], rows_stuck, rows_kept, dropped_no_fit, dropped_no_fail, n_fit, n_fail)."""
    rng = random.Random(seed)
    items, no_fit, no_fail = [], 0, 0
    for i in d['stuck']:
        p = fewshot.parse(rows[i]['prompt'])
        seen, fit, fail = set(), [], []
        fl = d['fit'][i] if d.get('fit') else [fits(p, rec.t) for rec in d['tries'][i]]
        for rec, f in zip(d['tries'][i], fl):
            k = raw_key(rec.t)
            if k in seen:
                continue
            seen.add(k)
            (fit if f else fail).append(rec.t)
        if not fit:
            no_fit += 1
            continue
        if not fail:
            no_fail += 1
            continue
        pick = [(t, 1.0) for t in rng.sample(fit, min(k_fit, len(fit)))] + [(t, 0.0) for t in rng.sample(fail, min(k_fail, len(fail)))]
        mean = sum(r for _, r in pick) / len(pick)
        items += [dict(i=i, row=rows[i], t=t, r=r, adv=r - mean) for t, r in pick]
    return dict(items=items, rows_stuck=len(d['stuck']), rows_kept=len({it['i'] for it in items}), dropped_no_fit=no_fit, dropped_no_fail=no_fail,
                n_fit=sum(it['r'] for it in items), n_fail=sum(1 - it['r'] for it in items))


def advantages(items, shuffle=False, seed=0):
    """Per-try advantages. shuffle=True (placebo S): rewards permuted at random among ALL kept tries (seeded), advantages recomputed per row from the permuted rewards."""
    rew = [it['r'] for it in items]
    if shuffle:
        random.Random(seed).shuffle(rew)
    by = {}
    for it, r in zip(items, rew):
        by.setdefault(it['i'], []).append(r)
    mean = {i: sum(v) / len(v) for i, v in by.items()}
    return [r - mean[it['i']] for it, r in zip(items, rew)]


def _ref_dists(ref, items, T, bs=256):
    """pi_ref's log p_T of every head along every kept try's path (no grad), cached on the CPU."""
    out = {k: [] for k in HEADS}
    with torch.no_grad():
        for s in range(0, len(items), bs):
            ch = items[s:s + bs]
            o = logp_tries(ref, [it['row'] for it in ch], [it['t'] for it in ch], T)
            for k in HEADS:
                out[k].append(o[k].cpu())
    return {k: torch.cat(v) for k, v in out.items()}


def loop1(model, kept, lr, passes, T, seed, batch=64, kl=0.1, shuffle=False, log=None):
    """Reward sleep on the adapter only (the model's base weights stay frozen; Adam, grad clip 1.0, constant lr). Loss per batch = mean over tries of (-A * logp_T(try)) +
    kl * mean over tries of KL(pi_now || pi_ref); pi_ref = a frozen copy of the model as it enters the night (its adapter state from before this night), both in creative mode.
    passes = epochs over the kept tries in a seeded order. shuffle=True: the placebo (see advantages). -> dict(updates, loss [per update], pg, kl, grad_norm)."""
    items = kept['items']
    if not items or passes <= 0:
        return dict(updates=0, loss=[], pg=[], kl=[], grad_norm=[])
    adv = torch.tensor(advantages(items, shuffle, seed + 17), dtype=torch.float32)
    ref = copy.deepcopy(model)
    for p in ref.parameters():
        p.requires_grad_(False)
    with creative(ref, True):
        refd = _ref_dists(ref, items, T)
    del ref
    params = adapter_params(model)
    opt = torch.optim.Adam(params, lr=lr)
    rng = random.Random(seed)
    losses, pgs, kls, gns = [], [], [], []
    with creative(model, True):
        for ep in range(passes):
            order = list(range(len(items)))
            rng.shuffle(order)
            for s in range(0, len(order), batch):
                ix = order[s:s + batch]
                o = logp_tries(model, [items[j]['row'] for j in ix], [items[j]['t'] for j in ix], T)
                pg = (-adv[ix] * o['lp']).mean()
                kv = kl_to_ref(o, {k: refd[k][ix] for k in HEADS}).mean()
                loss = pg + kl * kv
                opt.zero_grad(set_to_none=True)
                loss.backward()
                gns.append(float(torch.nn.utils.clip_grad_norm_(params, 1.0)))
                opt.step()
                losses.append(float(loss.detach())); pgs.append(float(pg.detach())); kls.append(float(kv.detach()))
                if log and len(losses) % 20 == 0:
                    log('loop1', dict(update=len(losses), loss=round(sum(losses[-20:]) / 20, 4), kl=round(sum(kls[-20:]) / 20, 4)))
    return dict(updates=len(losses), loss=losses, pg=pgs, kl=kls, grad_norm=gns)


def fit_at(model, rows, vocab, device, T, n=32, seed=0):
    """Creative mode (adapter on): the share of rows with a fitting try among n plain samples (the example check only; no key). -> (share, [bool per row])."""
    if not rows:
        return 0.0, []
    with creative(model, True):
        smp = legal.raw_samples(model, rows, vocab, device, n=n, temperature=T, level=0, seed=seed)
    f = has_fit(rows, smp)
    return sum(f) / len(f), f


def pick_setting(model, init, kept, stuck_rows, vocab, device, T, seed, lrs=(1e-3, 3e-3), passes=(1, 2, 4), kl=0.1, n=32, log=None):
    """Arm C's setting on C2 DEV, by example fits only: grid lr x passes, each trained from `init` (the pre-night adapter); score = fit_at on the DEV rows whose worker greedy
    try fails the check; best score wins, ties go to the fewer updates then the lower lr. -> (best dict, adapter state of the best, all results)."""
    res, states = [], {}
    for lr in lrs:
        for ps in passes:
            load_adapter_state(model, init)
            info = loop1(model, kept, lr, ps, T, seed, kl=kl)
            score, _ = fit_at(model, stuck_rows, vocab, device, T, n, seed + 555)
            r = dict(lr=lr, passes=ps, updates=info['updates'], score=score, last_loss=info['loss'][-1] if info['loss'] else None, kl_end=info['kl'][-1] if info['kl'] else None)
            res.append(r)
            states[(lr, ps)] = adapter_state(model)
            if log:
                log('grid', r)
    best = min(res, key=lambda r: (-r['score'], r['updates'], r['lr']))
    load_adapter_state(model, init)
    return best, states[(best['lr'], best['passes'])], res


# ---------------------------------------------------------------- measures
def score_rows(rows, samples, ks=(32,)):
    """Per row, over its plain samples in sampling order: fits (example check), right (a fitting try whose answer is in `accepted`: the key only scores), first = 1-based index of the
    first fit, first_right = of the first right fit, distinct = distinct fitting programs (score_samples' distinct_accepted: result_key of the answer cone); right{k} / fit{k} = within the
    first k samples, for k in ks. -> list of dicts."""
    out = []
    for row, tr in zip(rows, samples):
        p = fewshot.parse(row['prompt'])
        fit, right, keys, first, first_right = 0, False, set(), None, None
        keys_at = {}
        for j, rec in enumerate(tr):
            for k in ks:
                if j == k:
                    keys_at[k] = set(keys)
            if not pyfit(p, rec.t):
                continue
            v = fewshot.verdict(p, rec.t)
            if v[0] != 'accept':
                continue
            fit += 1
            first = j + 1 if first is None else first
            if str(v[2]) in row['accepted']:
                right = True
                first_right = j + 1 if first_right is None else first_right
            keys.add(result_key(rec.t, run(p['nums'], rec.t)[1]))
        d = dict(id=row['id'], kind=row['kind'], n=len(tr), n_fit=fit, fit=fit > 0, right=right, first=first, first_right=first_right, distinct=len(keys))
        for k in ks:
            d[f'right{k}'] = first_right is not None and first_right <= k
            d[f'fit{k}'] = first is not None and first <= k
            d[f'distinct{k}'] = len(keys_at[k]) if k < len(tr) else len(keys)
        out.append(d)
    return out


def summarize(per):
    """Pooled aggregates of score_rows: reach{k} (a right fitting try within the first k samples) and fit{k} for every k scored, reach_all / fit_all over all samples, rows with a fit,
    mean 1-based index of the first fit among rows with a fit, mean distinct fitting programs per row (all rows, all samples)."""
    n = max(len(per), 1)
    fi = [d['first'] for d in per if d['first'] is not None]
    ks = sorted({int(k[5:]) for d in per[:1] for k in d if k.startswith('right') and k[5:].isdigit()})
    out = dict(n=len(per), n_samples=max((d['n'] for d in per), default=0), reach_all=sum(d['right'] for d in per) / n, fit_all=sum(d['fit'] for d in per) / n,
               rows_with_fit=len(fi), tries_to_first_fit=sum(fi) / len(fi) if fi else None, distinct_fitting=sum(d['distinct'] for d in per) / n)
    for k in ks:
        out[f'reach{k}'] = sum(d[f'right{k}'] for d in per) / n
        out[f'fit{k}'] = sum(d[f'fit{k}'] for d in per) / n
        out[f'distinct{k}'] = sum(d.get(f'distinct{k}', 0) for d in per) / n
    return out


def summarize_by_kind(per):
    return dict(pooled=summarize(per), by_kind={k: summarize([d for d in per if d['kind'] == k]) for k in sorted({d['kind'] for d in per})})


def measure(model, rows, vocab, device, T, n, seed):
    """Creative mode (adapter as loaded, on): n plain samples per row at T, scored at 32 and at n tries. -> (summary dict pooled + per kind, per-row list)."""
    with creative(model, True):
        smp = legal.raw_samples(model, rows, vocab, device, n=n, temperature=T, level=0, seed=seed)
    per = score_rows(rows, smp, ks=sorted({32, n}))
    return summarize_by_kind(per), per


def _limit(rows, n):
    return rows[:n] if n else rows


def _log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)



# ---------------------------------------------------------------- 6. S1
def s1_parent(nprime, out, pool_limit=None, dev_limit=None, n1=32, n2=480, seed=0, T=T_POOL, lrs=(1e-3, 3e-3), passes=(1, 2, 4), kl=0.1, n=32, n_eval=512, device='cpu',
              knew_dir=KNEW, transfer_kinds=TRANSFER_KINDS, name=None, resume=True, log=_log, allres=None):
    """One parent's S1. After every stage DIR/s1.json (all parents so far, `allres`) and DIR/<name>/s1.json are written; the day is cached (DIR/<name>/day.pkl) when the same arguments come back."""
    from creative import knew
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir = os.path.join(out, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    res = dict(nprime=nprime, name=name, seed=seed, T=T, n_pick=n, n_eval=n_eval, spec=__doc__.split('\n')[0],
               args=dict(pool_limit=pool_limit, dev_limit=dev_limit, n1=n1, n2=n2, lrs=list(lrs), passes=list(passes), kl=kl),
               note='C2 DEV, C2 pool and K_new DEV only; test / labelled / K_new test never opened; keys score, never pick (the setting pick and the records use the example check only)')
    allres = {} if allres is None else allres
    allres[name] = res
    save = lambda: (json.dump(res, open(os.path.join(pdir, 's1.json'), 'w'), indent=1), json.dump(allres, open(os.path.join(out, 's1.json'), 'w'), indent=1))
    model, vocab, meta = sleep.load_parent(nprime, device)
    model.eval()
    ref = copy.deepcopy(model)                                  # the unwrapped N': what the worker must stay equal to
    add_adapter(model, seed=seed)
    init = adapter_state(model)
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    cpath = os.path.join(knew_dir, 'candidates_dev.jsonl')
    raw = open(cpath, 'rb').read()
    kdev = c2_stones._with_nums(_limit([r for r in map(json.loads, raw.decode().splitlines()) if r['kind'] in transfer_kinds], dev_limit))
    res['transfer_source'] = dict(path=cpath, sha256=hashlib.sha256(raw).hexdigest(), kinds=list(transfer_kinds),
                                  note='report-only transfer set (roadmap ruling 13f4b987eb): the K_new candidates N\' reached at all at 512 tries; DEV rows only, no K_new set written or sealed')
    res['sizes'] = dict(pool=len(pool), c2_dev=len(dev), knew_dev=len(kdev), knew_kinds=sorted({r['kind'] for r in kdev}))
    # 1. the worker-untouched test, once
    t0 = time.time()
    ut = worker_untouched(model, ref, dev[:64], vocab, device, perturb=True)
    res['unit_test_before'] = ut
    log('worker-untouched test (adapter off == N\', B randomised)', ut)
    secs['unit_test'] = time.time() - t0
    save()
    assert ut['passes'], 'worker-untouched test failed'
    # 2. the day
    dpath = os.path.join(pdir, 'day.pkl')
    key = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    d = None
    if resume and os.path.exists(dpath):
        c = pickle.load(open(dpath, 'rb'))
        if c['key'] == key:
            d = c['day']
            log('day: loaded', dpath)
    if d is None:
        t0 = time.time()
        d = day(model, pool, vocab, device, T, n1, n2, seed)
        secs['day'] = time.time() - t0
        pickle.dump(dict(key=key, day=d), open(dpath, 'wb'))
    res['day'] = dict(drawn=d['drawn'], worker_pass=sum(d['greedy_fit']) / len(pool), stuck_rows=len(d['stuck']),
                      stuck_with_fit_in_n1=sum(d['fit1'].values()), stuck_with_fit_after_pass2=sum(any(d['fit'][i]) for i in d['stuck']))
    log('day', res['day'])
    save()
    # 3. kept tries
    kept = kept_tries(pool, d, seed)
    res['kept'] = {k: v for k, v in kept.items() if k != 'items'}
    res['kept']['n_tries'] = len(kept['items'])
    log('kept', res['kept'])
    save()
    if not kept['items']:
        res['stop'] = 'no kept rows (no stuck row had both a fitting and a failing try)'
        res['seconds'] = secs
        save()
        log('STOP', res['stop'])
        return res
    # 4. C: the grid, picked on C2 DEV rows the worker fails (cached in DIR/<name>/adapters.pt with S, so a restart resumes after training)
    apath = os.path.join(pdir, 'adapters.pt')
    akey = key + (dev_limit, tuple(lrs), tuple(passes), kl, n)
    ac = torch.load(apath, weights_only=False) if resume and os.path.exists(apath) else None
    if ac is not None and ac.get('key') == akey:
        c_state, s_state, best = ac['C'], ac['S'], ac['setting']
        res['pick_rows'], res['grid'], res['pick'], res['S_train'] = ac['pick_rows'], ac['grid'], best, ac['S_train']
        log('grid + S: loaded', apath, best)
        save()
    else:
        t0 = time.time()
        with creative(model, False):
            dgt = sampler.greedy_tries(model, dev, vocab, device)
        dev_stuck = [r for r, t in zip(dev, dgt) if not fits(fewshot.parse(r['prompt']), t.t)]
        res['pick_rows'] = len(dev_stuck)
        best, c_state, grid = pick_setting(model, init, kept, dev_stuck, vocab, device, T, seed, lrs, passes, kl, n, log)
        res['grid'], res['pick'] = grid, best
        secs['grid'] = time.time() - t0
        log('pick', best)
        save()
        # S at C's setting (same updates), U = untrained
        t0 = time.time()
        load_adapter_state(model, init)
        sinfo = loop1(model, kept, best['lr'], best['passes'], T, seed, kl=kl, shuffle=True)
        s_state = adapter_state(model)
        res['S_train'] = dict(updates=sinfo['updates'], last_loss=sinfo['loss'][-1], kl_end=sinfo['kl'][-1])
        secs['train_S'] = time.time() - t0
        torch.save(dict(C=c_state, S=s_state, setting=best, init=init, key=akey, pick_rows=res['pick_rows'], grid=grid, S_train=res['S_train']), apath)
    # 5. measures per arm, one sampling seed for every arm
    mseed = seed + 777
    states = dict(U=init, C=c_state, S=s_state)
    res['arms'], per = {}, {}
    t0 = time.time()
    for arm, st in states.items():
        mpath, mkey = os.path.join(pdir, f'measure_{arm}.pkl'), akey + (arm, n_eval, mseed, res['transfer_source']['sha256'])
        mc = pickle.load(open(mpath, 'rb')) if resume and os.path.exists(mpath) else None
        if mc is not None and mc['key'] == mkey:
            kn, kp, c2, cp = mc['m']
            log('arm', arm, 'measures: loaded', mpath)
        else:
            load_adapter_state(model, st)
            kn, kp = measure(model, kdev, vocab, device, T, n_eval, mseed)
            c2, cp = measure(model, dev, vocab, device, T, n_eval, mseed)
            pickle.dump(dict(key=mkey, m=(kn, kp, c2, cp)), open(mpath, 'wb'))
        res['arms'][arm] = dict(knew=kn, c2_dev=c2)
        per[arm] = dict(knew=kp, c2_dev=cp)
        show = ('reach32', f'reach{n_eval}', f'fit{n_eval}', 'tries_to_first_fit', 'distinct_fitting')
        log('arm', arm, 'K_new', {k: kn['pooled'].get(k) for k in show}, 'C2 DEV', {k: c2['pooled'].get(k) for k in show})
        res['seconds'] = secs
        save()
    secs['measure'] = time.time() - t0
    json.dump(per, open(os.path.join(pdir, 'per_row.json'), 'w'))
    # paired bootstrap per row (roadmap ruling 13f4b987eb): primary = C2 DEV reach@32 in creative mode; reach@n_eval beside it; transfer (K_new subset) report-only at n_eval
    vec = lambda arm, ds, k, kinds=None: [float(x[f'right{k}']) for x in per[arm][ds] if kinds is None or x['kind'] in kinds]
    bt = lambda a, b, ds, k, kinds=None: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(vec(a, ds, k, kinds), vec(b, ds, k, kinds))))
    E = n_eval
    res['boot'] = dict(c2_C_minus_U=bt('C', 'U', 'c2_dev', 32), c2_C_minus_S=bt('C', 'S', 'c2_dev', 32),
                       c2_at_eval_C_minus_U=bt('C', 'U', 'c2_dev', E), c2_at_eval_C_minus_S=bt('C', 'S', 'c2_dev', E),
                       groups={g: dict(C_minus_U=bt('C', 'U', 'c2_dev', 32, ks), C_minus_S=bt('C', 'S', 'c2_dev', 32, ks)) for g, ks in GROUPS.items()},
                       transfer_C_minus_U=bt('C', 'U', 'knew', E), transfer_C_minus_S=bt('C', 'S', 'knew', E),
                       transfer32_C_minus_U=bt('C', 'U', 'knew', 32), transfer32_C_minus_S=bt('C', 'S', 'knew', 32))
    log('boot', res['boot'])
    # 6. the worker-untouched test again, with each trained adapter loaded (flag off)
    after = {}
    for arm in ('C', 'S'):
        load_adapter_state(model, states[arm])
        after[arm] = worker_untouched(model, ref, dev[:64], vocab, device, perturb=False)
    res['unit_test_after'] = after
    log('worker-untouched after training', after)
    # 7. marks (roadmap ruling 13f4b987eb). The 'beyond near-copy' label pools both parents: `s1report`.
    a = res['arms']
    cC, cU = (a[x]['c2_dev']['pooled'] for x in 'CU')
    b = res['boot']
    res['marks'] = dict(
        primary=dict(C_minus_U_points=b['c2_C_minus_U']['points'], C_minus_S_points=b['c2_C_minus_S']['points'],
                     passes=b['c2_C_minus_U']['points'] >= 5.0 and b['c2_C_minus_S']['points'] >= 3.0, rule='C2 DEV reach@32 in creative mode, pooled: C - U >= +5 and C - S >= +3 points'),
        variety=dict(C=cC['distinct32'], U=cU['distinct32'], passes=cC['distinct32'] >= 0.8 * cU['distinct32'], rule='C2 DEV distinct fitting programs per question within 32 tries: C >= 0.8 x U'),
        unit_test=dict(passes=bool(ut['passes'] and all(x['passes'] for x in after.values()))),
        proved_wrong=dict(flag=b['c2_C_minus_S']['hi'] < 1.0, rule='C2 DEV reach@32: C - S upper end of the paired 95% interval < +1 point (both parents needed)'),
        transfer_report_only=dict(C_minus_U=b['transfer_C_minus_U'], C_minus_S=b['transfer_C_minus_S'], rule=f'K_new subset reach@{E} (report only)'))
    res['marks']['passes'] = all(res['marks'][k]['passes'] for k in ('primary', 'variety', 'unit_test'))
    secs['total'] = time.time() - t00
    res['seconds'] = secs
    save()
    log('MARKS', res['marks'])
    return res


def s1(nprimes, out, **kw):
    os.makedirs(out, exist_ok=True)
    allres = {}
    for p in nprimes:
        s1_parent(p, out, allres=allres, **kw)
    return allres


def s1report(out, parents=('s100', 's101')):
    """S1 verdict over both parents (roadmap ruling 13f4b987eb): pass = every parent passes primary, variety and the unit test; label 'beyond near-copy' only if the multi-step C - U
    paired interval (C2 DEV reach@32), pooled over both parents' rows, is above 0; proved wrong = C - S upper end < +1 on both parents. -> dict, also DIR/s1-report.json."""
    res = {p: json.load(open(os.path.join(out, p, 's1.json'))) for p in parents}
    per = {p: json.load(open(os.path.join(out, p, 'per_row.json'))) for p in parents}
    pooled = lambda arm: [float(x['right32']) for p in parents for x in per[p][arm]['c2_dev'] if x['kind'] in c2_pilot.HARD_KINDS]
    multi = dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(pooled('C'), pooled('U'))))
    rep = dict(parents=list(parents), per_parent={p: dict(marks=res[p].get('marks'), groups=res[p].get('boot', {}).get('groups')) for p in parents},
               passes=all((res[p].get('marks') or {}).get('passes') for p in parents),
               multi_step_pooled_C_minus_U=multi, label='beyond near-copy' if multi['lo'] > 0 else 'near-copy only (multi-step interval not above 0)',
               proved_wrong=all((res[p].get('marks') or {}).get('proved_wrong', {}).get('flag') for p in parents),
               wording='a pass reads "finds answers faster on the kinds it was stuck on", never "more creative in general" (roadmap 13f4b987eb)')
    json.dump(rep, open(os.path.join(out, 's1-report.json'), 'w'), indent=1)
    return rep


# ---------------------------------------------------------------- 6b. S1b (roadmap 7d, 083303c493): no training; F = trained adapter for tries 1-32, untrained (U) for tries 33-512
def try_marks(rows, samples):
    """Per row, per try in sampling order: (fit, right, result key or None), by score_rows' rules. -> [dict(id, kind, tries)]."""
    out = []
    for row, tr in zip(rows, samples):
        p = fewshot.parse(row['prompt'])
        recs = []
        for rec in tr:
            v = fewshot.verdict(p, rec.t) if pyfit(p, rec.t) else None
            if v is None or v[0] != 'accept':
                recs.append((0, 0, None))
            else:
                recs.append((1, int(str(v[2]) in row['accepted']), result_key(rec.t, run(p['nums'], rec.t)[1])))
        out.append(dict(id=row['id'], kind=row['kind'], tries=recs))
    return out


def score_marks(pm, ks=(32,)):
    """score_rows on try_marks output (same fields, same rules)."""
    out = []
    for r in pm:
        fit, right, keys, first, first_right, keys_at = 0, False, set(), None, None, {}
        for j, (f, rt, key) in enumerate(r['tries']):
            for k in ks:
                if j == k:
                    keys_at[k] = set(keys)
            if not f:
                continue
            fit += 1
            first = j + 1 if first is None else first
            if rt:
                right = True
                first_right = j + 1 if first_right is None else first_right
            keys.add(key)
        n = len(r['tries'])
        d = dict(id=r['id'], kind=r['kind'], n=n, n_fit=fit, fit=fit > 0, right=right, first=first, first_right=first_right, distinct=len(keys))
        for k in ks:
            d[f'right{k}'] = first_right is not None and first_right <= k
            d[f'fit{k}'] = first is not None and first <= k
            d[f'distinct{k}'] = len(keys_at[k]) if k < n else len(keys)
        out.append(d)
    return out


def switch_marks(on, off, k=32):
    """F: `on`'s tries 1..k, then `off`'s tries k+1.. (each row's tries are independent draws, so this is a fair draw paired with `off`)."""
    assert [r['id'] for r in on] == [r['id'] for r in off]
    return [dict(id=a['id'], kind=a['kind'], tries=a['tries'][:k] + b['tries'][k:]) for a, b in zip(on, off)]


def s1b_parent(nprime, s1dir, out, n_eval=512, k=32, device='cpu', knew_dir=KNEW, transfer_kinds=TRANSFER_KINDS, dev_limit=None, name=None, resume=True, log=_log):
    """One parent: re-draw U's and C's S1 measures with S1's adapters and sampling seed (no training), keep per-try records, check they equal S1's per-row scores, then score F."""
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, sdir = os.path.join(out, name), os.path.join(s1dir, name)
    os.makedirs(pdir, exist_ok=True)
    s1r = json.load(open(os.path.join(sdir, 's1.json')))
    s1per = json.load(open(os.path.join(sdir, 'per_row.json')))
    ad = torch.load(os.path.join(sdir, 'adapters.pt'), weights_only=False)
    seed, T, mseed = s1r['seed'], s1r['T'], s1r['seed'] + 777
    assert s1r['n_eval'] == n_eval
    res = dict(nprime=nprime, name=name, s1=sdir, seed=seed, T=T, sampling_seed=mseed, n_eval=n_eval, switch_after=k, spec='S1b (roadmap 7d 083303c493): F = C for tries 1-32, U for tries 33-512; no training; C2 DEV and K_new DEV only')
    model, vocab, meta = sleep.load_parent(nprime, device)
    model.eval()
    add_adapter(model, seed=seed)
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    cpath = os.path.join(knew_dir, 'candidates_dev.jsonl')
    raw = open(cpath, 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == s1r['transfer_source']['sha256'], 'K_new DEV file changed since S1'
    kdev = c2_stones._with_nums(_limit([r for r in map(json.loads, raw.decode().splitlines()) if r['kind'] in transfer_kinds], dev_limit))
    ks = sorted({k, n_eval})
    marks, check = {}, {}
    for arm, st in (('U', ad['init']), ('C', ad['C'])):
        mpath = os.path.join(pdir, f'tries_{arm}.pkl')
        mc = pickle.load(open(mpath, 'rb')) if resume and os.path.exists(mpath) else None
        if mc is not None and mc['key'] == (mseed, n_eval, len(dev), len(kdev)):
            marks[arm] = mc['m']
            log(arm, 'per-try records: loaded', mpath)
        else:
            t0 = time.time()
            load_adapter_state(model, st)
            m = {}
            with creative(model, True):
                for ds, rows in (('knew', kdev), ('c2_dev', dev)):        # the order and seed S1's measure used
                    smp = legal.raw_samples(model, rows, vocab, device, n=n_eval, temperature=T, level=0, seed=mseed)
                    m[ds] = try_marks(rows, smp)
            marks[arm] = m
            pickle.dump(dict(key=(mseed, n_eval, len(dev), len(kdev)), m=m), open(mpath, 'wb'))
            log(arm, 'redrawn', round(time.time() - t0), 's')
        # S1's per-row scores must come back exactly from the redrawn tries (then F is computed from S1's own draws)
        check[arm] = {}
        for ds in ('knew', 'c2_dev'):
            a, b = score_marks(marks[arm][ds], ks), s1per[arm][ds]
            diff = [i for i, (x, y) in enumerate(zip(a, b)) if any(x[f] != y[f] for f in x)]
            check[arm][ds] = dict(rows=len(a), rows_differing=len(diff), equal=len(a) == len(b) and not diff)
    res['reproduces_s1'] = check
    exact = all(v['equal'] for c in check.values() for v in c.values())
    res['draws'] = 'S1\'s own draws (redrawn with S1\'s seed; every per-row score equals S1\'s)' if exact else 'fresh draws with S1\'s seed (NOT identical to S1\'s per-row scores; see reproduces_s1)'
    log('reproduces S1', exact, check)
    per = {arm: {ds: score_marks(marks[arm][ds], ks) for ds in ('knew', 'c2_dev')} for arm in ('U', 'C')}
    per['F'] = {ds: score_marks(switch_marks(marks['C'][ds], marks['U'][ds], k), ks) for ds in ('knew', 'c2_dev')}
    json.dump(per['F'], open(os.path.join(pdir, 'per_row_F.json'), 'w'))
    res['arms'] = {arm: {ds: summarize_by_kind(per[arm][ds]) for ds in ('knew', 'c2_dev')} for arm in per}
    vec = lambda arm, ds, kk, kinds=None: [float(x[f'right{kk}']) for x in per[arm][ds] if kinds is None or x['kind'] in kinds]
    bt = lambda a, b, ds, kk, kinds=None: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(vec(a, ds, kk, kinds), vec(b, ds, kk, kinds))))
    E = n_eval
    res['boot'] = dict(knew_F_minus_U=bt('F', 'U', 'knew', E), c2_F_minus_U=bt('F', 'U', 'c2_dev', E), c2_32_F_minus_C=bt('F', 'C', 'c2_dev', k),
                       c2_32_F_minus_U=bt('F', 'U', 'c2_dev', k), c2_F_minus_C=bt('F', 'C', 'c2_dev', E),
                       groups={g: dict(F_minus_U=bt('F', 'U', 'c2_dev', E, kk)) for g, kk in GROUPS.items()})
    P = lambda arm, ds: res['arms'][arm][ds]['pooled']
    b = res['boot']
    res['marks'] = dict(
        reach32_equals_C=dict(F=P('F', 'c2_dev')[f'reach{k}'], C=P('C', 'c2_dev')[f'reach{k}'], S1_C=s1r['arms']['C']['c2_dev']['pooled'][f'reach{k}'],
                              passes=P('F', 'c2_dev')[f'reach{k}'] == s1r['arms']['C']['c2_dev']['pooled'][f'reach{k}'], rule=f'C2 DEV reach@{k}: F equals S1\'s C'),
        new_kind_guard=dict(F=P('F', 'knew')[f'reach{E}'], U=P('U', 'knew')[f'reach{E}'], F_minus_U=b['knew_F_minus_U'],
                            passes=b['knew_F_minus_U']['points'] >= -1.0, rule=f'K_new DEV ({"/".join(transfer_kinds)}) reach@{E}: F >= U - 1 point'),
        in_kind_guard=dict(F=P('F', 'c2_dev')[f'reach{E}'], U=P('U', 'c2_dev')[f'reach{E}'], F_minus_U=b['c2_F_minus_U'],
                           passes=b['c2_F_minus_U']['points'] >= -2.0, rule=f'C2 DEV reach@{E}: F >= U - 2 points'),
        report={arm: {ds: {x: P(arm, ds)[x] for x in ('tries_to_first_fit', 'distinct_fitting', f'distinct{k}', 'rows_with_fit')} for ds in ('knew', 'c2_dev')} for arm in ('U', 'C', 'F')},
        proved_wrong_here=dict(flag=P('F', 'knew')[f'reach{E}'] == 0 and P('U', 'knew')[f'reach{E}'] > 0.01, rule=f'F\'s K_new reach@{E} is 0 while U\'s > 1% (both parents needed)'))
    res['marks']['passes'] = all(res['marks'][x]['passes'] for x in ('reach32_equals_C', 'new_kind_guard', 'in_kind_guard'))
    json.dump(res, open(os.path.join(pdir, 's1b.json'), 'w'), indent=1)
    log('MARKS', {x: (v.get('passes'), v.get('F'), v.get('U')) for x, v in res['marks'].items() if isinstance(v, dict) and 'rule' in v})
    return res


def s1b(nprimes, s1dir, out, **kw):
    os.makedirs(out, exist_ok=True)
    allres = {}
    for p in nprimes:
        r = s1b_parent(p, s1dir, out, **kw)
        allres[r['name']] = r
    m = {n: r['marks'] for n, r in allres.items()}
    allres['verdict'] = dict(passes=all(x['passes'] for x in m.values()), proved_wrong=bool(m) and all(x['proved_wrong_here']['flag'] for x in m.values()),
                             rule='marks 1-3 on both parents; proved wrong when F\'s new-kind reach@512 is 0 on both while U\'s > 1%')
    json.dump(allres, open(os.path.join(out, 's1b.json'), 'w'), indent=1)
    return allres


# ---------------------------------------------------------------- 7. S3


def sleep_on(base, recs, vocab, replay, warm_rows, lr, visits, seed, device):
    """c2_stuck.sleep_on, exactly: a copy of `base` sleeps on `recs` at lr x `visits` (updates = visits x records / 32; batch 64, warmup 20; skills replay + warm-row replay)."""
    m = copy.deepcopy(base)
    u = visits * len(recs) // 32
    per = 32 if replay else 64
    mv = max(visits, math.ceil(u * per / max(len(recs), 1)))
    so = sleep.sleep(m, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows)
    m.eval()
    return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / max(len(recs), 1), last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1) if so['loss'] else None)


def shaky_records(model, pool, vocab, device, seed, n=8, T=1.0):
    """P's records. The worker's day on the pool, adapter off: greedy first try + the example check; for the passing rows n plain samples at T (legal.raw_samples); pass rate = share of
    the n that fit; the record = the passing greedy try (fewshot._record(row, t, 'P', 0)) for rows with 1/n <= rate <= (n-1)/n. Reads the example check only, never the key or the kind.
    -> (records, info dict with the rate histogram)."""
    gt = sampler.greedy_tries(model, pool, vocab, device)
    ps = [fewshot.parse(r['prompt']) for r in pool]
    passing = [i for i, (p, t) in enumerate(zip(ps, gt)) if fits(p, t.t)]
    smp = legal.raw_samples(model, [pool[i] for i in passing], vocab, device, n=n, temperature=T, level=0, seed=seed) if passing else []
    hist, recs, by_kind = {k: 0 for k in range(n + 1)}, [], {}
    for i, s in zip(passing, smp):
        k = sum(fits(ps[i], x.t) for x in s)
        hist[k] += 1
        if 1 <= k <= n - 1:
            recs.append(fewshot._record(pool[i], gt[i].t, 'P', 0))
            by_kind[pool[i]['kind']] = by_kind.get(pool[i]['kind'], 0) + 1
    return recs, dict(pool_rows=len(pool), passing_greedy=len(passing), rate_histogram={f'{k}/{n}': v for k, v in hist.items()}, records=len(recs), records_by_kind=by_kind)


def replay_only_records(replay, warm_rows, n, seed):
    """Z's records: an equal-size seeded draw of skills replay rows and warm rows, half each (n // 2 skills, the rest warm)."""
    rng = random.Random(seed)
    k = n // 2
    return rng.sample(list(replay), min(k, len(replay))) + rng.sample(list(warm_rows), min(n - k, len(warm_rows)))


def greedy_rows(model, rows, vocab, device):
    """The worker's greedy first try per row (adapter-free model). Per row: fit (example check), right (fits and in `accepted`; the key only scores), written steps (non-NOOP ops),
    cone steps (steps that feed the answer)."""
    from creative.programs import cone
    out = []
    for r, g in zip(rows, sampler.greedy_tries(model, rows, vocab, device)):
        p = fewshot.parse(r['prompt'])
        fit = right = False
        if pyfit(p, g.t):
            v = fewshot.verdict(p, g.t)
            fit = v[0] == 'accept'
            right = fit and str(v[2]) in r['accepted']
        out.append(dict(kind=r['kind'], fit=fit, right=right, written=sum(1 for o in g.t.ops if o), cone=len(cone(g.t) or [])))
    return out


def s3_measures(dev_per, fresh_per):
    """Next-day numbers for one model: stuck rate (greedy try fails the check) on C2 DEV; first try right per group (near-copy, multi-step, practised = the fresh add/mult rows);
    written steps per right answer (DEV pooled, and practised)."""
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    right = lambda ds: mean([float(d['right']) for d in ds])
    steps = lambda ds, k: mean([d[k] for d in ds if d['right']])
    return dict(stuck_rate=1 - mean([float(d['fit']) for d in dev_per]), first_try_right=dict(
        {g: right([d for d in dev_per if d['kind'] in ks]) for g, ks in GROUPS.items()}, practised=right(fresh_per), pooled_dev=right(dev_per)),
        written_steps_per_right=dict(dev=steps(dev_per, 'written'), practised=steps(fresh_per, 'written')),
        cone_steps_per_right=dict(dev=steps(dev_per, 'cone'), practised=steps(fresh_per, 'cone')),
        n_right=dict(dev=sum(d['right'] for d in dev_per), practised=sum(d['right'] for d in fresh_per)))


def w1_tries_from_day(day_path, key, N, pool, vocab, device, seed, T, n1, n2):
    """W1's search tries taken from S1's day on the same parent (roadmap ruling b69b136446): that day is N' with an untrained adapter (= N'), job 8's search at the same T, n1, n2
    and seed, run on the rows whose greedy try fails the check. The rows whose greedy try passes got no samples there, so they get job 8's two-pass search here (seed + 2000),
    as job 8 gives every pool row. -> (tries per pool row, fit1, fit, drawn, note) or None when the day's key differs."""
    c = pickle.load(open(day_path, 'rb'))
    if c['key'] != key:
        return None
    d = c['day']
    tries, fit1 = [None] * len(pool), [False] * len(pool)
    for i in d['stuck']:
        tries[i], fit1[i] = list(d['tries'][i]), d['fit1'][i]
    rest = [i for i in range(len(pool)) if tries[i] is None]
    extra = dict(pass1=0, pass2=0, stuck_questions=0)
    if rest:
        t2, f1, _, extra = search(N, [pool[i] for i in rest], vocab, device, seed + 2000, T, n1, n2)
        for i, t, f in zip(rest, t2, f1):
            tries[i], fit1[i] = t, f
    fit = has_fit(pool, tries)
    drawn = dict(pass1=d['drawn']['pass1'] + extra['pass1'], pass2=d['drawn']['pass2'] + extra['pass2'], stuck_questions=d['drawn']['pass2_rows'] + extra['stuck_questions'])
    note = f'from S1 day {day_path} ({len(d["stuck"])} rows); {len(rest)} greedy-passing rows searched here (seed {seed + 2000})'
    return tries, fit1, fit, drawn, note


def s3_parent(nprime, out, skills_train=None, skills_data=None, pool_limit=None, dev_limit=None, n1=32, n2=480, seed=0, T=T_POOL, lr=1e-3, visits=32, replay_n=None, device='cpu',
              name=None, resume=True, log=_log, allres=None, day_from=None, control='replay', w1_from=None):
    """One parent's S3. After every stage DIR/s3.json (all parents so far, `allres`) and DIR/<name>/s3.json are written; W1 is cached (DIR/<name>/W1.pt) when the same arguments come back.
    day_from = an S1 output dir: W1's records come from S1's day on this parent when its key matches (else W1 runs its own search; s3.json says which).
    control = 'replay' (S3's Z: half skills, half warm rows) or 'w1' (S3', roadmap 36d3fc2d14: Z' = a seeded draw of W1's own previous-night records, the same dose).
    w1_from = an earlier S3 output dir whose W1 (same arguments) is reused; W1's records are then rebuilt from the same day and seeds and checked against its counts."""
    assert control in ('replay', 'w1')
    zl = "Z'" if control == 'w1' else 'Z'
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir = os.path.join(out, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    args = dict(pool_limit=pool_limit, dev_limit=dev_limit, n1=n1, n2=n2, lr=lr, visits=visits, replay_n=replay_n, day_from=day_from)
    res = dict(nprime=nprime, name=name, seed=seed, T=T, spec=__doc__.split('\n')[0], args=args,
               note='C2 DEV and C2 pool only; test / labelled never opened; no kind label and no key touches an allocation or a record (the example check only)')
    allres = {} if allres is None else allres
    allres[name] = res
    save = lambda: (json.dump(res, open(os.path.join(pdir, 's3.json'), 'w'), indent=1), json.dump(allres, open(os.path.join(out, 's3.json'), 'w'), indent=1))
    replay = sleep.load_replay(skills_train, replay_n, seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    fresh = c2_stones._with_nums(stones.fresh_practised(256, 1, 'fresh-check')[0])[:dev_limit or 256]
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    res['sizes'] = dict(pool=len(pool), c2_dev=len(dev), fresh_practised=len(fresh), replay=len(replay), warm_rows=len(warm_rows))
    res['control'] = dict(arm=zl, kind=control, w1_from=w1_from,
                          rule='Z = seeded half skills / half warm-row draw' if control == 'replay' else "Z' = seeded draw of W1's own previous-night records (roadmap 36d3fc2d14)")

    def w1_search():
        got, source = None, 'own search (seed %d)' % (seed + 10)
        dp = os.path.join(day_from, name, 'day.pkl') if day_from else None
        if dp and os.path.exists(dp):
            got = w1_tries_from_day(dp, (os.path.abspath(nprime), pool_limit, n1, n2, seed, T), N, pool, vocab, device, seed, T, n1, n2)
            if got is None:
                source = 'own search (seed %d): S1 day key differs' % (seed + 10)
        if got is not None:
            tries, fit1, fit, drawn, source = got
        else:
            tries, fit1, fit, drawn = search(N, pool, vocab, device, seed + 10, T, n1, n2)
        recs, counts = w_records(pool, tries, seed + 1)
        kind_of = {r['id']: r['kind'] for r in pool}
        return recs, dict(source=source, samples=drawn, records=len(recs), records_by_kind={k: sum(c for i, c in counts.items() if kind_of[i] == k) for k in sorted(set(kind_of.values()))},
                          pool_with_fit_pass1=sum(fit1), pool_with_fit_final=sum(fit))
    # 1. W1 = one C2b W night from N' (job 8's two-pass search at T, <= 2 distinct fitting tries per row, the frozen dose)
    wsrc = os.path.join(w1_from, name) if w1_from else pdir
    wpath = os.path.join(wsrc, 'W1.pt')
    prev = json.load(open(os.path.join(wsrc, 's3.json'))) if (resume or w1_from) and os.path.exists(os.path.join(wsrc, 's3.json')) else {}
    w1_recs = None
    if (resume or w1_from) and os.path.exists(wpath) and prev.get('args') == args and 'W1_night' in prev:
        W1, _, _ = sleep.load_parent(wpath, device)
        W1.eval()
        res['W1_night'], res['W1_from'] = prev['W1_night'], wpath
        log('W1: loaded', wpath)
    else:
        assert not w1_from, f'w1_from: no W1 with the same arguments in {wsrc}'
        t0 = time.time()
        recs, info = w1_search()
        w1_recs = recs
        log('W1 search', info)
        secs['W1_search'] = time.time() - t0
        if len(recs) < 1:
            res['stop'] = 'W1: no records'
            save()
            return res
        t0 = time.time()
        W1, sinfo = sleep_on(N, recs, vocab, replay, warm_rows, lr, visits, seed, device)
        info['sleep'] = sinfo
        secs['W1_sleep'] = time.time() - t0
        res['W1_night'] = info
        sleep.save_parent(W1, meta['name'], meta['cfg'], vocab, wpath, step=(meta['step'] or 0), warmup=True)
        log('W1 sleep', sinfo)
    res['seconds'] = secs
    save()
    # 2. W1's day on the pool: the shaky passes
    t0 = time.time()
    precs, pinfo = shaky_records(W1, pool, vocab, device, seed + 2)
    res['P_records'] = pinfo
    secs['shaky'] = time.time() - t0
    log('P records', pinfo)
    save()
    if len(precs) < 1:
        res['stop'] = 'P: no rows with a pass rate in [1/8, 7/8]: nothing to sleep on'
        save()
        return res
    # 3. P and Z at the same dose, the same replay
    t0 = time.time()
    P, pi = sleep_on(W1, precs, vocab, replay, warm_rows, lr, visits, seed, device)
    if control == 'w1':
        if w1_recs is None:                                     # W1 reused: rebuild its records from the same day and seeds, and check them against W1's own counts
            w1_recs, rinfo = w1_search()
            same = all(rinfo[k] == res['W1_night'][k] for k in ('records', 'records_by_kind', 'pool_with_fit_pass1', 'pool_with_fit_final'))
            res['W1_records_rebuilt'] = dict(records=rinfo['records'], same_counts_as_W1_night=same)
            log("Z': W1's records rebuilt", res['W1_records_rebuilt'])
            assert same, "rebuilt W1 records differ from W1's night"
        assert len(w1_recs) >= len(precs), "Z' needs as many W1 records as P has"
        zrecs = random.Random(seed + 4).sample(list(w1_recs), len(precs))
    else:
        zrecs = replay_only_records(replay, warm_rows, len(precs), seed + 4)
    Z, zi = sleep_on(W1, zrecs, vocab, replay, warm_rows, lr, visits, seed, device)
    for arm, m in (('P', P), ('Z', Z)):
        sleep.save_parent(m, meta['name'], meta['cfg'], vocab, os.path.join(pdir, f'{arm}.pt'), step=(meta['step'] or 0), warmup=True)
    assert pi['updates'] == zi['updates'], 'P and Z must get the same number of updates'
    res['P_sleep'], res['Z_sleep'] = pi, zi
    secs['sleep_PZ'] = time.time() - t0
    log('P sleep', pi, 'Z sleep', zi)
    save()
    # 4. the next day: C2 DEV and fresh practised, greedy first try; skills harm vs W1
    t0 = time.time()
    sk = {}
    models = dict(W1=W1, P=P, Z=Z)
    per, perf, res['arms'] = {}, {}, {}
    for arm, m in models.items():
        dp, fp = greedy_rows(m, dev, vocab, device), greedy_rows(m, fresh, vocab, device)
        per[arm], perf[arm] = dp, fp
        sk[arm] = skills_eval(m, skills_data, device)
        res['arms'][arm] = dict(s3_measures(dp, fp), skills=sk[arm])
        if sk['W1'] and sk[arm]:
            res['arms'][arm]['skills_harm_vs_W1_points'] = 100 * (sk['W1']['pooled5'] - sk[arm]['pooled5'])
        log('arm', arm, {k: res['arms'][arm][k] for k in ('stuck_rate', 'first_try_right')})
        save()
    secs['measure'] = time.time() - t0
    json.dump(dict(dev_ids=[r['id'] for r in dev], fresh_ids=[r['id'] for r in fresh], dev={k: per[k] for k in models}, fresh={k: perf[k] for k in models}),
              open(os.path.join(pdir, 'per_row.json'), 'w'))
    stuck = lambda arm: [0.0 if d['fit'] else 1.0 for d in per[arm]]
    zp = c2_pilot.boot(stuck('Z'), stuck('P'))
    bd = lambda a_, b_: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(a_, b_)))
    rv = lambda ds, kinds=None: [float(d['right']) for d in ds if kinds is None or d['kind'] in kinds]
    both = [(x['written'], y['written']) for x, y in zip(per['P'], per['W1']) if x['right'] and y['right']]
    res['boot'] = dict(stuck_Z_minus_P=dict(zip(('points', 'lo', 'hi'), zp)),
                       stuck_W1_minus_P=bd(stuck('W1'), stuck('P')),
                       first_try_P_minus_W1=dict({g: bd(rv(per['P'], ks), rv(per['W1'], ks)) for g, ks in GROUPS.items()},
                                                 practised=bd(rv(perf['P']), rv(perf['W1'])), pooled_dev=bd(rv(per['P']), rv(per['W1']))),
                       first_try_P_minus_Z=dict({g: bd(rv(per['P'], ks), rv(per['Z'], ks)) for g, ks in GROUPS.items()}, practised=bd(rv(perf['P']), rv(perf['Z']))),
                       written_steps_P_minus_W1_on_rows_both_right=dict(rows=len(both), **(dict(zip(('mean_x100', 'lo_x100', 'hi_x100'), c2_pilot.boot([x for x, _ in both], [y for _, y in both])))
                                                                                         if both else {})))
    # 5. marks
    a = res['arms']
    gap = {g: 100 * (a['P']['first_try_right'][g] - a['Z']['first_try_right'][g]) for g in list(GROUPS) + ['practised']}
    harm, zharm = a['P'].get('skills_harm_vs_W1_points'), a['Z'].get('skills_harm_vs_W1_points')
    hm = dict(P_points=harm, Z_points=zharm, passes=None if harm is None else harm <= 2.0, rule='P skills harm vs W1 <= 2 points (100 x pooled-5 drop)')
    if control == 'w1':
        hm['second_night_harm'] = bool(harm is not None and zharm is not None and harm > 2.0 and abs(harm - zharm) <= 0.5)
        hm['rule'] += f"; if P > 2 but within 0.5 of {zl}'s: 'practice passes; second-night harm is a separate blocker' (roadmap 36d3fc2d14)"
    res['marks'] = dict(
        stuck=dict(Z_minus_P_points=zp[0], passes=zp[0] >= 3.0, rule=f'P stuck rate <= {zl} stuck rate - 3 points (C2 DEV greedy try fails the example check)'),
        groups=dict(P_minus_Z_first_try_points=gap, passes=all(v >= -2.0 for v in gap.values()), rule=f'no group more than 2 points below {zl} on first try right'),
        harm=hm,
        proved_wrong=dict(flag=zp[2] < 1.0, rule=f'{zl} - P stuck-rate upper end of the paired 95% interval < +1 point'))
    ok = res['marks']['stuck']['passes'] and res['marks']['groups']['passes']
    res['marks']['passes'] = bool(ok and hm['passes'])
    if control == 'w1':
        res['marks']['ruling'] = ('practice passes' if ok and hm['passes'] else
                                  'practice passes; second-night harm is a separate blocker' if ok and hm.get('second_night_harm') else 'fails')
    secs['total'] = time.time() - t00
    res['seconds'] = secs
    save()
    log('MARKS', res['marks'])
    return res


def s3(nprimes, out, **kw):
    os.makedirs(out, exist_ok=True)
    allres = {}
    for p in nprimes:
        s3_parent(p, out, allres=allres, **kw)
    return allres


# ---------------------------------------------------------------- 8. Test J (roadmap 7d, 10-08): the creative part's own sleep. W = loop 2 alone (the worker sleeps on its search records); J = loop 1 + loop 2 (each night first trains the creative adapter on that day's kept tries); two days and nights from N', night 1 shared (S3's W1, S1's day), creative mode F (adapter on for tries 1-32, off after)
def day_f(model, pool, vocab, device, T, n1, n2, seed, bs=2048):
    """Day 2 on ALL pool rows (job 8's two-pass search, `search`'s shape): greedy first try with the adapter OFF (greedy_fit by the example check); pass 1 = n1 samples per row,
    adapter ON (seed); pass 2 = n2 samples, adapter OFF (seed + 1000), only for rows with no fitting try in pass 1. With B = 0 on == off, so the worker's F is plain sampling.
    -> dict(greedy_fit [bool per row], tries [list per row, sampling order], fit [bool per try, per row] (the example check), fit1 [pass 1 has a fit], fit_final, drawn)."""
    with creative(model, False):
        gt = sampler.greedy_tries(model, pool, vocab, device)
    ps = [fewshot.parse(r['prompt']) for r in pool]
    gf = [fits(p, t.t) for p, t in zip(ps, gt)]
    with creative(model, True):
        t1 = legal.raw_samples(model, pool, vocab, device, n=n1, temperature=T, level=0, seed=seed, bs=bs)
    tries = [list(t) for t in t1]
    fit = [[fits(p, x.t) for x in t] for p, t in zip(ps, tries)]
    fit1 = [any(f) for f in fit]
    more = [i for i, f in enumerate(fit1) if not f]
    if more:
        with creative(model, False):
            t2 = legal.raw_samples(model, [pool[i] for i in more], vocab, device, n=n2, temperature=T, level=0, seed=seed + 1000, bs=bs)
        for i, t in zip(more, t2):
            tries[i] += t
            fit[i] += [fits(ps[i], x.t) for x in t]
    return dict(greedy_fit=gf, tries=tries, fit=fit, fit1=fit1, fit_final=[any(f) for f in fit],
                drawn=dict(greedy=len(pool), pass1=n1 * len(pool), pass2=n2 * len(more), pass2_rows=len(more)))


def stuck_day(d):
    """A day_f result as kept_tries reads a day: stuck = the rows whose greedy try fails; tries and fit as dicts keyed by row index (those rows only)."""
    st = [i for i, f in enumerate(d['greedy_fit']) if not f]
    return dict(stuck=st, tries={i: d['tries'][i] for i in st}, fit={i: d['fit'][i] for i in st})


def _h(*xs):
    return hashlib.sha256(repr(xs).encode()).hexdigest()


def _hstate(st):
    h = hashlib.sha256()
    for k in sorted(st):
        h.update(k.encode()); h.update(st[k].numpy().tobytes())
    return h.hexdigest()


def _sha_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _cached(path, key, fn, resume, log, what):
    """pickle cache {key, v}: reload when the key matches (and resume), else compute and store."""
    if resume and os.path.exists(path):
        c = pickle.load(open(path, 'rb'))
        if c['key'] == key:
            log(what, 'loaded', path)
            return c['v']
    v = fn()
    pickle.dump(dict(key=key, v=v), open(path, 'wb'))
    return v


def _arm_model(base, state, seed):
    m = copy.deepcopy(base)
    add_adapter(m, seed=seed)
    load_adapter_state(m, state)
    m.eval()
    return m


def _by_kind(pool, counts):
    kind_of = {r['id']: r['kind'] for r in pool}
    return {k: sum(c for i, c in counts.items() if kind_of[i] == k) for k in sorted(set(kind_of.values()))}


def skills_look(m, skills_data, device):
    """One greedy pass on skills DEV in_dist (harm_look.skills_hits). -> dict(hits [0/1 per in_dist row], pooled5 %, in_dist %); None without data."""
    if not skills_data:
        return None
    from creative.harm_look import skills_hits
    _, h, p5, ia = skills_hits(m, skills_data, device)
    return dict(hits=h, pooled5=p5, in_dist=ia)


def kept_origin(kept, tries, n1):
    """Where a night's kept tries were drawn: share of kept rows whose kept FITTING tries all come from index >= n1 (pass 2, adapter off), and share of kept tries at index >= n1
    (index = the try's first draw in the row's sampling order, found by raw_key). Report only."""
    first, fit_late, rows, late, tot = {}, {}, set(), 0, 0
    for it in kept['items']:
        i = it['i']
        if i not in first:
            first[i] = {}
            for j, rec in enumerate(tries[i]):
                first[i].setdefault(raw_key(rec.t), j)
        j = first[i][raw_key(it['t'])]
        rows.add(i)
        tot += 1
        late += j >= n1
        if it['r']:
            fit_late[i] = fit_late.get(i, True) and j >= n1
    return dict(kept_rows=len(rows), rows_fit_only_from_pass2=sum(fit_late.values()), share_rows_fit_only_from_pass2=sum(fit_late.values()) / max(len(rows), 1),
                kept_tries=tot, tries_from_pass2=late, share_tries_from_pass2=late / max(tot, 1))


def j_measure(m, dev, kdev, vocab, device, T, n_eval, k, mseed):
    """One arm's next-day measures on its model (worker + adapter): greedy rows (adapter off); C2 DEV creative reach@k (adapter on, mseed); K_new F mode to n_eval (k on at mseed,
    the rest off at mseed + 1000). -> dict(greedy, c32, knew) per-row lists."""
    with creative(m, False):
        g = greedy_rows(m, dev, vocab, device)
    with creative(m, True):
        s = legal.raw_samples(m, dev, vocab, device, n=k, temperature=T, level=0, seed=mseed)
        on = legal.raw_samples(m, kdev, vocab, device, n=k, temperature=T, level=0, seed=mseed)
    off = [[] for _ in kdev]
    if n_eval > k:
        with creative(m, False):
            off = legal.raw_samples(m, kdev, vocab, device, n=n_eval - k, temperature=T, level=0, seed=mseed + 1000)
    return dict(greedy=g, c32=score_rows(dev, s, ks=(k,)), knew=score_rows(kdev, [a + b for a, b in zip(on, off)], ks=sorted({k, n_eval})))


def j_parent(nprime, out, s1dir, s3dir, skills_train=None, skills_data=None, pool_limit=None, dev_limit=None, n1=32, n2=480, seed=0, T=T_POOL, lr_w=1e-3, visits=32, replay_n=None,
             lr1=1e-3, passes1=1, kl=0.1, n_eval=512, k=32, knew_dir=KNEW, transfer_kinds=TRANSFER_KINDS, device='cpu', name=None, resume=True, log=_log, b2=None):
    """One parent's Test J (W = loop 2 alone, J = loop 1 + loop 2; two days and nights from N', night 1 reused from S1 / S3). DIR/<name>/j.json is written after every stage (b2 = the parent's B2 checkpoint, report-only harm comparison; no combined
    file: parents run as parallel processes; `jreport` joins them). Day 2 and the measures are cached per arm (day2_{arm}.pkl, measure_{arm}.pkl); night 2 in W2.pt / J2.pt / adapters_j.pt."""
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s1d, s3d = os.path.join(out, name), os.path.join(s1dir, name), os.path.join(s3dir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs, s2, mseed = time.time(), {}, seed + 1, seed + 777
    args = dict(pool_limit=pool_limit, dev_limit=dev_limit, n1=n1, n2=n2, lr=lr_w, visits=visits, replay_n=replay_n, day_from=s1dir)
    res = dict(nprime=nprime, name=name, seed=seed, T=T, day2_seed=s2, measure_seed=mseed, spec=__doc__.split('\n')[0], args=dict(args, lr1=lr1, passes1=passes1, kl=kl, n_eval=n_eval, k=k, s1=s1dir, s3=s3dir, b2=b2),
               note='C2 DEV, C2 pool and K_new DEV only; test / labelled / K_new test never opened; keys score, never pick (records and kept tries use the example check only)')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'j.json'), 'w'), indent=1)
    replay = sleep.load_replay(skills_train, replay_n, seed) if skills_train else []
    warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    cpath = os.path.join(knew_dir, 'candidates_dev.jsonl')
    raw = open(cpath, 'rb').read()
    kdev = c2_stones._with_nums(_limit([r for r in map(json.loads, raw.decode().splitlines()) if r['kind'] in transfer_kinds], dev_limit))
    ksha = hashlib.sha256(raw).hexdigest()
    res['transfer_source'] = dict(path=cpath, sha256=ksha, kinds=list(transfer_kinds))
    res['sizes'] = dict(pool=len(pool), c2_dev=len(dev), knew_dev=len(kdev), replay=len(replay), warm_rows=len(warm_rows))
    N, vocab, meta = sleep.load_parent(nprime, device)
    N.eval()
    # 1. night 1, shared: W1 from S3 (args checked as s3_parent's w1_from does), C1 = S1's day + loop 1 on N' + adapter
    s3j = json.load(open(os.path.join(s3d, 's3.json')))
    assert s3j.get('args') == args and 'W1_night' in s3j, f'S3 args {s3j.get("args")} differ from J\'s {args}: W1 is not the same night'
    wpath = os.path.join(s3d, 'W1.pt')
    assert os.path.exists(wpath), f'no {wpath}'
    W1, _, _ = sleep.load_parent(wpath, device)
    W1.eval()
    w1sha = _sha_file(wpath)
    log('W1: loaded', wpath)
    m1 = copy.deepcopy(N)
    add_adapter(m1, seed=seed)
    init = adapter_state(m1)
    dpath = os.path.join(s1d, 'day.pkl')
    assert os.path.exists(dpath), f'no S1 day {dpath}'
    c = pickle.load(open(dpath, 'rb'))
    skey = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    assert c['key'] == skey, f'S1 day key {c["key"]} != {skey}'
    kept1 = kept_tries(pool, c['day'], seed)
    t0 = time.time()
    c1path, c1key = os.path.join(pdir, 'c1.pt'), _h(skey, lr1, passes1, kl, _hstate(init))
    cc = torch.load(c1path, weights_only=False) if resume and os.path.exists(c1path) else None
    if cc is not None and cc['key'] == c1key:
        C1, i1 = cc['C1'], cc['info']
        log('C1: loaded', c1path)
    else:
        i1 = loop1(m1, kept1, lr1, passes1, T, seed, kl=kl)
        i1 = dict(updates=i1['updates'], last_loss=i1['loss'][-1] if i1['loss'] else None, kl_end=i1['kl'][-1] if i1['kl'] else None)
        C1 = adapter_state(m1)
        torch.save(dict(key=c1key, C1=C1, info=i1), c1path)
    secs['C1'] = time.time() - t0
    vs = dict(compared=False)
    apath = os.path.join(s1d, 'adapters.pt')
    if os.path.exists(apath):
        ac = torch.load(apath, weights_only=False)
        st = ac['setting']
        if st['lr'] == lr1 and st['passes'] == passes1:
            diff = max(float((C1[x] - ac['C'][x]).abs().max()) for x in C1)
            vs = dict(compared=True, max_abs_diff=diff, equal=diff == 0.0)
        else:
            vs = dict(compared=False, s1_setting=dict(lr=st['lr'], passes=st['passes']))
    res['night1'] = dict(W1_night=s3j['W1_night'], W1_sha256=w1sha, C1=dict(info=i1, kept={x: v for x, v in kept1.items() if x != 'items'}, n_tries=len(kept1['items']), vs_S1_C=vs))
    log('night 1: C1', res['night1']['C1'])
    save()
    # 2. day 2 per arm (cached): W = W1 + untrained adapter, J = W1 + C1
    states = dict(W=init, J=C1)
    mods = {a: _arm_model(W1, st, seed) for a, st in states.items()}
    days, dkeys = {}, {}
    res['day2'] = {}
    for a in ('W', 'J'):
        t0 = time.time()
        dkeys[a] = (skey, s2, w1sha, _hstate(states[a]), a)
        days[a] = _cached(os.path.join(pdir, f'day2_{a}.pkl'), dkeys[a], lambda a=a: day_f(mods[a], pool, vocab, device, T, n1, n2, s2), resume, log, f'day 2 {a}')
        d = days[a]
        res['day2'][a] = dict(drawn=d['drawn'], greedy_pass=sum(d['greedy_fit']) / len(pool), pool_with_fit_pass1=sum(d['fit1']), pool_with_fit_final=sum(d['fit_final']))
        secs[f'day2_{a}'] = time.time() - t0
        log('day 2', a, res['day2'][a])
        save()
    # 3. night 2: W = sleep on its records; J = loop 1 on its day, then sleep on its records (both from the plain W1)
    nkey = _h(dkeys, lr_w, visits, replay_n, skills_train, lr1, passes1, kl)
    npath, files = os.path.join(pdir, 'night2.json'), {x: os.path.join(pdir, x) for x in ('W2.pt', 'J2.pt', 'adapters_j.pt')}
    nj = json.load(open(npath)) if resume and os.path.exists(npath) else {}
    if nj.get('key') == nkey and all(os.path.exists(p) for p in files.values()):
        W2, _, _ = sleep.load_parent(files['W2.pt'], device)
        J2, _, _ = sleep.load_parent(files['J2.pt'], device)
        C2 = torch.load(files['adapters_j.pt'], weights_only=False)['C2']
        res['night2'] = nj['info']
        log('night 2: loaded', files)
    else:
        t0 = time.time()
        info = {}
        recs, cnt = w_records(pool, days['W']['tries'], s2 + 1)
        if len(recs) < 1:
            res['stop'] = 'W: no day-2 records'
            save()
            return res
        W2, si = sleep_on(W1, recs, vocab, replay, warm_rows, lr_w, visits, s2, device)
        info['W'] = dict(records=len(recs), records_by_kind=_by_kind(pool, cnt), sleep=si)
        log('W night 2', info['W'])
        kept2 = kept_tries(pool, stuck_day(days['J']), s2)
        l1 = loop1(mods['J'], kept2, lr1, passes1, T, s2, kl=kl)
        C2 = adapter_state(mods['J'])
        recs, cnt = w_records(pool, days['J']['tries'], s2 + 1)
        info['J'] = dict(kept_origin=kept_origin(kept2, days['J']['tries'], n1), loop1=dict(updates=l1['updates'], last_loss=l1['loss'][-1] if l1['loss'] else None, kl_end=l1['kl'][-1] if l1['kl'] else None,
                                    kept={x: v for x, v in kept2.items() if x != 'items'}, n_tries=len(kept2['items'])), records=len(recs), records_by_kind=_by_kind(pool, cnt))
        log('J loop 1', info['J']['loop1'])
        if len(recs) < 1:
            res['stop'] = 'J: no day-2 records'
            res['night2'] = info
            save()
            return res
        J2, si = sleep_on(W1, recs, vocab, replay, warm_rows, lr_w, visits, s2, device)
        info['J']['sleep'] = si
        log('J night 2', info['J']['records'], si)
        for x, m in (('W2.pt', W2), ('J2.pt', J2)):
            sleep.save_parent(m, meta['name'], meta['cfg'], vocab, files[x], step=(meta['step'] or 0), warmup=True)
        torch.save(dict(C1=C1, C2=C2, init=init), files['adapters_j.pt'])
        json.dump(dict(key=nkey, info=info), open(npath, 'w'))
        res['night2'] = info
        secs['night2'] = time.time() - t0
    save()
    # 4. measures per arm: W2 + adapter(init), J2 + adapter(C2); one sampling seed
    plain = dict(W=W2, J=J2)
    mstates = dict(W=init, J=C2)
    sk = dict(N=_cached(os.path.join(pdir, 'skills_base.pkl'), ('N', skills_data, os.path.abspath(nprime)), lambda: skills_look(N, skills_data, device), resume, log, 'skills N\''),
              W1=_cached(os.path.join(pdir, 'skills_W1.pkl'), ('W1', skills_data, w1sha), lambda: skills_look(W1, skills_data, device), resume, log, 'skills W1'))
    if b2:
        b2p = os.path.expanduser(b2)
        B2, _, _ = sleep.load_parent(b2p, device)
        B2.eval()
        sk['B2'] = _cached(os.path.join(pdir, 'skills_B2.pkl'), ('B2', skills_data, _sha_file(b2p)), lambda: skills_look(B2, skills_data, device), resume, log, 'skills B2')
        del B2
    per, res['arms'] = {}, {}
    for a in ('W', 'J'):
        t0 = time.time()
        mkey = (nkey, a, n_eval, k, mseed, ksha, dev_limit, skills_data)

        def fn(a=a):
            r = j_measure(_arm_model(plain[a], mstates[a], seed), dev, kdev, vocab, device, T, n_eval, k, mseed)
            r['skills'] = skills_look(plain[a], skills_data, device)
            return r
        mm = _cached(os.path.join(pdir, f'measure_{a}.pkl'), mkey, fn, resume, log, f'measures {a}')
        per[a] = mm
        g = s3_measures(mm['greedy'], [])
        res['arms'][a] = dict(stuck_rate=g['stuck_rate'], first_try_right=g['first_try_right'], creative=summarize_by_kind(mm['c32']), knew=summarize_by_kind(mm['knew']), skills=mm['skills'] and {y: z for y, z in mm['skills'].items() if y != 'hits'})
        secs[f'measure_{a}'] = time.time() - t0
        log('arm', a, dict(stuck=g['stuck_rate'], first=g['first_try_right']['pooled_dev'], reach32=res['arms'][a]['creative']['pooled'][f'reach{k}'],
                           knew=res['arms'][a]['knew']['pooled'][f'reach{n_eval}']))
        save()
    res['skills'] = {x: v and {y: z for y, z in v.items() if y != 'hits'} for x, v in sk.items()}
    json.dump(dict(dev_ids=[r['id'] for r in dev], knew_ids=[r['id'] for r in kdev], greedy={a: per[a]['greedy'] for a in per}, creative32={a: per[a]['c32'] for a in per},
                   knew={a: per[a]['knew'] for a in per}), open(os.path.join(pdir, 'per_row.json'), 'w'))
    # 5. paired bootstraps, J against W, same row order
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    stuck = lambda a: [0.0 if d['fit'] else 1.0 for d in per[a]['greedy']]
    right = lambda a, kinds=None: [float(d['right']) for d in per[a]['greedy'] if kinds is None or d['kind'] in kinds]
    reach = lambda a, ds, kk: [float(d[f'right{kk}']) for d in per[a][ds]]
    res['boot'] = dict(stuck_W_minus_J=bd(stuck('W'), stuck('J')), creative32_J_minus_W=bd(reach('J', 'c32', k), reach('W', 'c32', k)),
                       knew_reach_J_minus_W=bd(reach('J', 'knew', n_eval), reach('W', 'knew', n_eval)),
                       first_try_J_minus_W=dict(pooled=bd(right('J'), right('W')), **{g: bd(right('J', ks), right('W', ks)) for g, ks in GROUPS.items()}))
    log('boot', res['boot'])
    # 6. marks (roadmap 7d, 10-08)
    b, ar = res['boot'], res['arms']
    harm = None
    if sk['N'] and per['W']['skills'] and per['J']['skills']:
        from creative.harm_look import harm_measure
        from custom_io.data import load_rows
        rows = load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl'))
        hit = dict(N=sk['N']['hits'], W=per['W']['skills']['hits'], J=per['J']['skills']['hits'], **({'B2': sk['B2']['hits']} if 'B2' in sk else {}))
        p5 = dict(N=sk['N']['pooled5'], W=per['W']['skills']['pooled5'], J=per['J']['skills']['pooled5'], **({'B2': sk['B2']['pooled5']} if 'B2' in sk else {}))
        harm = dict(J_vs_W=harm_measure(hit['W'], hit['J'], rows), pooled5_points={x: p5[x] for x in p5},
                    pooled5_harm_vs_N={a: p5['N'] - p5[a] for a in ('W', 'J')}, pooled5_J_minus_W_harm=(p5['N'] - p5['J']) - (p5['N'] - p5['W']),
                    report_only={f'{a}_vs_{r}': harm_measure(hit[r], hit[a], rows) for r in ('N', 'B2') if r in hit for a in ('W', 'J')})
    res['marks'] = dict(
        stuck=dict(W_minus_J_points=b['stuck_W_minus_J']['points'], passes=b['stuck_W_minus_J']['points'] >= 3.0, rule='C2 DEV stuck rate (adapter-off greedy try fails the example check): W - J >= +3 points'),
        creative32=dict(J_minus_W_points=b['creative32_J_minus_W']['points'], passes=b['creative32_J_minus_W']['points'] >= 5.0, rule=f'C2 DEV creative reach@{k} (F mode): J - W >= +5 points'),
        new_kind_guard=dict(J_minus_W_points=b['knew_reach_J_minus_W']['points'], passes=b['knew_reach_J_minus_W']['points'] >= -1.0, rule=f'K_new DEV reach@{n_eval} (F mode): J - W >= -1 point (point estimate)'),
        first_try=dict(J_minus_W_points=b['first_try_J_minus_W']['pooled']['points'], passes=b['first_try_J_minus_W']['pooled']['points'] >= -2.0, rule='C2 DEV first try right (adapter off, pooled): J - W >= -2 points'),
        harm=dict(detail=harm, passes=None if harm is None else harm['J_vs_W']['passes'], rule='J in_dist exact at most 1.5 points below W AND no skills family fires against W (a family fires when its exact drops > 5 points and the paired 95% interval of J - W over its rows has hi < 0); W and J against N\' and B2, and pooled-5, are report only'),
        proved_wrong_here=dict(flag=b['stuck_W_minus_J']['hi'] < 1.0 and b['creative32_J_minus_W']['hi'] < 1.0, rule='stuck W - J upper end < +1 and creative reach@32 J - W upper end < +1 (paired 95% intervals; both parents needed)'))
    res['marks']['passes'] = all(res['marks'][x]['passes'] is True for x in ('stuck', 'creative32', 'new_kind_guard', 'first_try', 'harm'))
    secs['total'] = time.time() - t00
    res['seconds'] = secs
    save()
    log('MARKS', {x: v.get('passes', v.get('flag')) for x, v in res['marks'].items() if isinstance(v, dict)}, res['marks']['passes'])
    return res


def j(nprimes, out, s1dir, s3dir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: j_parent(p, out, s1dir, s3dir, **kw) for p in nprimes}


def jreport(out, parents):
    """Test J verdict over the parents' DIR/<name>/j.json -> DIR/j-report.json: passes = every parent passes all five marks; proved_wrong = every parent's proved_wrong_here."""
    res = {p: json.load(open(os.path.join(out, p, 'j.json'))) for p in parents}
    mk = {p: r.get('marks') or {} for p, r in res.items()}
    rep = dict(parents=list(parents), passes=all(m.get('passes') is True for m in mk.values()), proved_wrong=all(m.get('proved_wrong_here', {}).get('flag') is True for m in mk.values()), per_parent=mk,
               rule='passes: all five marks on every parent; proved wrong: stuck and creative reach@32 upper ends < +1 on every parent')
    json.dump(rep, open(os.path.join(out, 'j-report.json'), 'w'), indent=1)
    return rep


# ---- 9. Test S1w (roadmap 7d, 10-08): loop 1 trains the adapter on the slept worker W1 from day 1's kept tries
def s1w_parent(nprime, out, s1dir, s3dir, pool_limit=None, dev_limit=None, n1=32, n2=480, seed=0, T=T_POOL, lr1=1e-3, passes1=1, kl=0.1, n_eval=512, k=32,
               knew_dir=KNEW, transfer_kinds=TRANSFER_KINDS, device='cpu', name=None, resume=True, log=_log):
    """One parent's Test S1w (S1 with W1 as the model the adapter trains on: loop 1 on W1 from day 1's kept tries, S1's setting, no grid; arms U, C and report-only C1 = S1's N'-trained adapter, all measured on W1).
    DIR/<name>/s1w.json is written after every stage (no combined file: parents run as separate processes; `s1wreport` joins them). Adapter in adapters_w.pt, measures in measure_{arm}.pkl."""
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s1d, s3d = os.path.join(out, name), os.path.join(s1dir, name), os.path.join(s3dir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs, mseed = time.time(), {}, seed + 777
    args = dict(pool_limit=pool_limit, dev_limit=dev_limit, n1=n1, n2=n2)
    res = dict(nprime=nprime, name=name, seed=seed, T=T, measure_seed=mseed, spec=__doc__.split('\n')[0], args=dict(args, lr1=lr1, passes1=passes1, kl=kl, n_eval=n_eval, k=k, s1=s1dir, s3=s3dir),
               note='C2 DEV, C2 pool and K_new DEV only; test / labelled / K_new test never opened; keys score, never pick (records and kept tries use the example check only)')
    save = lambda: json.dump(res, open(os.path.join(pdir, 's1w.json'), 'w'), indent=1)
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    cpath = os.path.join(knew_dir, 'candidates_dev.jsonl')
    raw = open(cpath, 'rb').read()
    kdev = c2_stones._with_nums(_limit([r for r in map(json.loads, raw.decode().splitlines()) if r['kind'] in transfer_kinds], dev_limit))
    ksha = hashlib.sha256(raw).hexdigest()
    res['transfer_source'] = dict(path=cpath, sha256=ksha, kinds=list(transfer_kinds))
    res['sizes'] = dict(pool=len(pool), c2_dev=len(dev), knew_dev=len(kdev))
    # 1. W1 (S3's night 1) and day 1 (S1's day, drawn by N')
    wpath = os.path.join(s3d, 'W1.pt')
    assert os.path.exists(wpath), f'no {wpath}'
    W1, vocab, _ = sleep.load_parent(wpath, device)
    W1.eval()
    w1sha = _sha_file(wpath)
    s3p = os.path.join(s3d, 's3.json')
    res['W1'] = dict(path=wpath, sha256=w1sha, W1_night=json.load(open(s3p)).get('W1_night') if os.path.exists(s3p) else None)
    dpath = os.path.join(s1d, 'day.pkl')
    assert os.path.exists(dpath), f'no S1 day {dpath}'
    c = pickle.load(open(dpath, 'rb'))
    skey = (os.path.abspath(nprime), pool_limit, n1, n2, seed, T)
    assert c['key'] == skey, f'S1 day key {c["key"]} != {skey}'
    kept1 = kept_tries(pool, c['day'], seed)
    res['kept'] = dict({x: v for x, v in kept1.items() if x != 'items'}, n_tries=len(kept1['items']))
    log('kept', res['kept'])
    # 2. loop 1 on W1 + zero adapter
    m = copy.deepcopy(W1)
    add_adapter(m, seed=seed)
    init = adapter_state(m)
    ut = worker_untouched(m, W1, dev[:64], vocab, device, perturb=True)
    assert ut['passes'], f'worker-untouched test failed: {ut}'
    res['unit_test_before'] = ut
    save()
    t0 = time.time()
    akey = _h(skey, w1sha, lr1, passes1, kl, _hstate(init))
    apath = os.path.join(pdir, 'adapters_w.pt')
    ac = torch.load(apath, weights_only=False) if resume and os.path.exists(apath) else None
    if ac is not None and ac['key'] == akey:
        C, info = ac['C'], ac['info']
        log('C: loaded', apath)
    else:
        li = loop1(m, kept1, lr1, passes1, T, seed, kl=kl)
        info = dict(updates=li['updates'], last_loss=li['loss'][-1] if li['loss'] else None, kl_end=li['kl'][-1] if li['kl'] else None)
        C = adapter_state(m)
        torch.save(dict(key=akey, C=C, init=init, info=info), apath)
    secs['loop1'] = time.time() - t0
    res['loop1'] = info
    log('loop 1 on W1', info)
    load_adapter_state(m, C)
    res['unit_test_after'] = worker_untouched(m, W1, dev[:64], vocab, device, perturb=False)
    log('worker-untouched after', res['unit_test_after'])
    save()
    # 3. arms on W1: U untrained, C trained on W1, C1 (report only) S1's adapter trained on N'
    states = dict(U=init, C=C)
    s1apath = os.path.join(s1d, 'adapters.pt')
    if os.path.exists(s1apath):
        sc = torch.load(s1apath, weights_only=False)
        st = sc['setting']
        res['S1_setting'] = dict(lr=st['lr'], passes=st['passes'])
        if st['lr'] == lr1 and st['passes'] == passes1:
            states['C1'] = sc['C']
        else:
            res['C1_skipped'] = f'S1 picked lr {st["lr"]}, passes {st["passes"]}, not lr1 {lr1}, passes1 {passes1}'
    else:
        res['C1_skipped'] = f'no {s1apath}'
    per, res['arms'] = {}, {}
    for a, st in states.items():
        t0 = time.time()
        mkey = (akey, a, n_eval, k, mseed, ksha, dev_limit, _hstate(st))
        mm = _cached(os.path.join(pdir, f'measure_{a}.pkl'), mkey, lambda st=st: j_measure(_arm_model(W1, st, seed), dev, kdev, vocab, device, T, n_eval, k, mseed), resume, log, f'measures {a}')
        per[a] = mm
        g = s3_measures(mm['greedy'], [])
        res['arms'][a] = dict(stuck_rate=g['stuck_rate'], first_try_right=g['first_try_right'], creative=summarize_by_kind(mm['c32']), knew=summarize_by_kind(mm['knew']))
        secs[f'measure_{a}'] = time.time() - t0
        log('arm', a, dict(reach32=res['arms'][a]['creative']['pooled'][f'reach{k}'], knew=res['arms'][a]['knew']['pooled'][f'reach{n_eval}']))
        save()
    res['greedy_equal_across_arms'] = all(per[a]['greedy'] == per['U']['greedy'] for a in per)
    json.dump(dict(dev_ids=[r['id'] for r in dev], knew_ids=[r['id'] for r in kdev], creative32={a: per[a]['c32'] for a in per}, knew={a: per[a]['knew'] for a in per}), open(os.path.join(pdir, 'per_row.json'), 'w'))
    # 4. paired bootstraps, same row order
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    reach = lambda a, ds, kk, kinds=None: [float(d[f'right{kk}']) for d in per[a][ds] if kinds is None or d['kind'] in kinds]
    res['boot'] = dict(c2_C_minus_U=bd(reach('C', 'c32', k), reach('U', 'c32', k)),
                       groups={g: bd(reach('C', 'c32', k, ks), reach('U', 'c32', k, ks)) for g, ks in GROUPS.items()},
                       knew_F_minus_U=bd(reach('C', 'knew', n_eval), reach('U', 'knew', n_eval)), knew32_C_minus_U=bd(reach('C', 'knew', k), reach('U', 'knew', k)))
    if 'C1' in per:
        res['boot']['c2_C_minus_C1'] = bd(reach('C', 'c32', k), reach('C1', 'c32', k))
    log('boot', res['boot'])
    # 5. S1's own numbers on N', for context
    s1p = os.path.join(s1d, 's1.json')
    if os.path.exists(s1p):
        s1r = json.load(open(s1p))
        res['s1_on_nprime'] = dict(c2_C_minus_U=(s1r.get('boot') or {}).get('c2_C_minus_U'),
                                   reach32={a: ((s1r.get('arms') or {}).get(a, {}).get('c2_dev') or {}).get('pooled', {}).get('reach32') for a in ('U', 'C')})
    # 6. marks (roadmap 7d, 10-08)
    b = res['boot']
    res['marks'] = dict(
        primary=dict(C_minus_U_points=b['c2_C_minus_U']['points'], passes=b['c2_C_minus_U']['points'] >= 5.0, rule=f'C2 DEV creative reach@{k} on W1: C - U >= +5 points'),
        new_kind_guard=dict(C_F_minus_U_points=b['knew_F_minus_U']['points'], passes=b['knew_F_minus_U']['points'] >= -1.0, rule=f'K_new DEV reach@{n_eval} (F mode) on W1: C - U >= -1 point (point estimate)'),
        unit_test=dict(passes=bool(res['unit_test_before']['passes'] and res['unit_test_after']['passes'])),
        proved_wrong_here=dict(flag=b['c2_C_minus_U']['hi'] < 1.0, rule=f'C2 DEV creative reach@{k}: C - U upper end of the paired 95% interval < +1 point (both parents needed)'))
    res['marks']['passes'] = all(res['marks'][x]['passes'] is True for x in ('primary', 'new_kind_guard', 'unit_test'))
    secs['total'] = time.time() - t00
    res['seconds'] = secs
    save()
    log('MARKS', {x: v.get('passes', v.get('flag')) for x, v in res['marks'].items() if isinstance(v, dict)}, res['marks']['passes'])
    return res


def s1w(nprimes, out, s1dir, s3dir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: s1w_parent(p, out, s1dir, s3dir, **kw) for p in nprimes}


def s1wreport(out, parents):
    """Test S1w verdict over the parents' DIR/<name>/s1w.json -> DIR/s1w-report.json: passes = every parent passes (primary, new-kind guard, unit test); proved_wrong = every parent's proved_wrong_here."""
    res = {p: json.load(open(os.path.join(out, p, 's1w.json'))) for p in parents}
    mk = {p: r.get('marks') or {} for p, r in res.items()}
    rep = dict(parents=list(parents), passes=all(m.get('passes') is True for m in mk.values()), proved_wrong=all(m.get('proved_wrong_here', {}).get('flag') is True for m in mk.values()), per_parent=mk,
               rule='passes: primary (C2 DEV reach@32 C - U >= +5), new-kind guard (K_new reach@512 F mode >= -1) and unit test on every parent; proved wrong: C - U upper end < +1 on every parent')
    json.dump(rep, open(os.path.join(out, 's1w-report.json'), 'w'), indent=1)
    return rep


# ---- 10. Test S1f (roadmap 377df3fc2c): loop 1 on W1 from fresh on-policy night tries (32 per still-stuck pool question)
def night_f(model, pool, vocab, device, T, n, seed, bs=2048):
    """The night draw on W1: greedy try on every pool row with the adapter OFF (example check: fits); on the stuck rows only, n tries each with the adapter ON at its current state (seed); one round.
    -> dict(stuck, tries, fit) as kept_tries reads a day, plus drawn (rows / samples) and cost (wall and CPU seconds)."""
    t0, c0 = time.time(), time.process_time()
    with creative(model, False):
        gt = sampler.greedy_tries(model, pool, vocab, device)
    stuck = [i for i, (r, t) in enumerate(zip(pool, gt)) if not fits(fewshot.parse(r['prompt']), t.t)]
    tries, fit = {}, {}
    if stuck:
        with creative(model, True):
            ts = legal.raw_samples(model, [pool[i] for i in stuck], vocab, device, n=n, temperature=T, level=0, seed=seed, bs=bs)
        for i, t in zip(stuck, ts):
            tries[i] = list(t)
            fit[i] = [fits(fewshot.parse(pool[i]['prompt']), x.t) for x in t]
    return dict(stuck=stuck, tries=tries, fit=fit, drawn=dict(rows=len(pool), samples=len(pool) + n * len(stuck), greedy=len(pool), night=n * len(stuck), stuck_rows=len(stuck)),
                cost=dict(wall_seconds=time.time() - t0, cpu_seconds=time.process_time() - c0))


def s1f_parent(nprime, out, s1wdir, s3dir, pool_limit=None, dev_limit=None, n_night=32, seed=0, T=T_POOL, lr1=1e-3, passes1=1, kl=0.1, n_eval=512, k=32,
               knew_dir=KNEW, transfer_kinds=TRANSFER_KINDS, device='cpu', name=None, resume=True, log=_log):
    """One parent's Test S1f (S1w with fresh on-policy tries: W1's own night draw, n_night tries per still-stuck pool question, replaces day 1's N'-drawn tries; loop 1 on W1 at S1's setting, no grid; arms U, C and report-only W = S1w's adapter, all on W1).
    DIR/<name>/s1f.json is written after every stage (parents run as separate processes; `s1freport` joins them). Night draw in night_f.pkl, adapter in adapters_f.pt, measures in measure_{arm}.pkl (U and W reused from S1w's when they are the same measure)."""
    name = name or os.path.basename(os.path.dirname(os.path.abspath(nprime)))
    pdir, s1wd, s3d = os.path.join(out, name), os.path.join(s1wdir, name), os.path.join(s3dir, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs, mseed = time.time(), {}, seed + 777
    res = dict(nprime=nprime, name=name, seed=seed, T=T, night_seed=seed + 2000, measure_seed=mseed, spec=__doc__.split('\n')[0],
               args=dict(pool_limit=pool_limit, dev_limit=dev_limit, n_night=n_night, lr1=lr1, passes1=passes1, kl=kl, n_eval=n_eval, k=k, s1w=s1wdir, s3=s3dir),
               note='C2 DEV, C2 pool and K_new DEV only; test / labelled / K_new test never opened; keys score, never pick (kept tries use the example check only)')
    save = lambda: json.dump(res, open(os.path.join(pdir, 's1f.json'), 'w'), indent=1)
    pool = c2_stones._with_nums(_limit(R.load_split(DATA, 'pool'), pool_limit))
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    cpath = os.path.join(knew_dir, 'candidates_dev.jsonl')
    raw = open(cpath, 'rb').read()
    kdev = c2_stones._with_nums(_limit([r for r in map(json.loads, raw.decode().splitlines()) if r['kind'] in transfer_kinds], dev_limit))
    ksha = hashlib.sha256(raw).hexdigest()
    res['transfer_source'] = dict(path=cpath, sha256=ksha, kinds=list(transfer_kinds))
    res['sizes'] = dict(pool=len(pool), c2_dev=len(dev), knew_dev=len(kdev))
    wpath = os.path.join(s3d, 'W1.pt')
    assert os.path.exists(wpath), f'no {wpath}'
    W1, vocab, _ = sleep.load_parent(wpath, device)
    W1.eval()
    w1sha = _sha_file(wpath)
    s3p = os.path.join(s3d, 's3.json')
    res['W1'] = dict(path=wpath, sha256=w1sha, W1_night=json.load(open(s3p)).get('W1_night') if os.path.exists(s3p) else None)
    m = copy.deepcopy(W1)
    add_adapter(m, seed=seed)
    init = adapter_state(m)
    ut = worker_untouched(m, W1, dev[:64], vocab, device, perturb=True)
    assert ut['passes'], f'worker-untouched test failed: {ut}'
    res['unit_test_before'] = ut
    # 1. the night draw on W1 (adapter at its untrained state), cached
    t0 = time.time()
    nkey = (w1sha, pool_limit, n_night, seed + 2000, T)
    d = _cached(os.path.join(pdir, 'night_f.pkl'), nkey, lambda: night_f(m, pool, vocab, device, T, n_night, seed + 2000), resume, log, 'night draw')
    kept = kept_tries(pool, d, seed)
    res['night_cost'] = dict(d['drawn'], **d['cost'], cpu_seconds_per_sample=d['cost']['cpu_seconds'] / max(d['drawn']['samples'], 1), stuck_with_fit_in_draw=sum(any(f) for f in d['fit'].values()))
    res['kept'] = dict({x: v for x, v in kept.items() if x != 'items'}, n_tries=len(kept['items']))
    secs['night_draw'] = time.time() - t0
    log('night', res['night_cost'], 'kept', res['kept'])
    save()
    if not kept['items']:
        res['stop'] = 'no kept rows (no stuck row had both a fitting and a failing try)'
        res['seconds'] = secs
        save()
        return res
    # 2. loop 1 on W1 + zero adapter
    t0 = time.time()
    akey = _h(nkey, lr1, passes1, kl, _hstate(init))
    apath = os.path.join(pdir, 'adapters_f.pt')
    ac = torch.load(apath, weights_only=False) if resume and os.path.exists(apath) else None
    if ac is not None and ac['key'] == akey:
        C, info = ac['C'], ac['info']
        log('C: loaded', apath)
    else:
        li = loop1(m, kept, lr1, passes1, T, seed, kl=kl)
        info = dict(updates=li['updates'], last_loss=li['loss'][-1] if li['loss'] else None, kl_end=li['kl'][-1] if li['kl'] else None)
        C = adapter_state(m)
        torch.save(dict(key=akey, C=C, init=init, info=info), apath)
    secs['loop1'] = time.time() - t0
    res['loop1'] = info
    log('loop 1 on W1 (fresh tries)', info)
    load_adapter_state(m, C)
    res['unit_test_after'] = worker_untouched(m, W1, dev[:64], vocab, device, perturb=False)
    log('worker-untouched after', res['unit_test_after'])
    save()
    # 3. arms on W1: U, C, report-only W = S1w's adapter (U and W reuse S1w's measures when the same measure)
    states = dict(U=init, C=C)
    wp = os.path.join(s1wd, 'adapters_w.pt')
    if os.path.exists(wp):
        states['W'] = torch.load(wp, weights_only=False)['C']
    else:
        res['W_skipped'] = f'no {wp}'
    s1wj = os.path.join(s1wd, 's1w.json')
    w1_same = os.path.exists(s1wj) and (json.load(open(s1wj)).get('W1') or {}).get('sha256') == w1sha
    reuse_src = dict(U='measure_U.pkl', W='measure_C.pkl')
    per, res['arms'], res['reused'] = {}, {}, {}
    for a, st in states.items():
        t0 = time.time()
        mm = None
        if a in reuse_src and w1_same and os.path.exists(os.path.join(s1wd, reuse_src[a])):
            c = pickle.load(open(os.path.join(s1wd, reuse_src[a]), 'rb'))
            ky = c['key']
            if isinstance(ky, tuple) and len(ky) == 8 and ky[2:7] == (n_eval, k, mseed, ksha, dev_limit) and ky[7] == _hstate(st):
                mm = c['v']
                res['reused'][a] = os.path.join(s1wd, reuse_src[a])
                log('arm', a, 'reused from', res['reused'][a])
        if mm is None:
            mkey = (akey, a, n_eval, k, mseed, ksha, dev_limit, _hstate(st))
            mm = _cached(os.path.join(pdir, f'measure_{a}.pkl'), mkey, lambda st=st: j_measure(_arm_model(W1, st, seed), dev, kdev, vocab, device, T, n_eval, k, mseed), resume, log, f'measures {a}')
        per[a] = mm
        g = s3_measures(mm['greedy'], [])
        res['arms'][a] = dict(stuck_rate=g['stuck_rate'], first_try_right=g['first_try_right'], creative=summarize_by_kind(mm['c32']), knew=summarize_by_kind(mm['knew']))
        secs[f'measure_{a}'] = time.time() - t0
        log('arm', a, dict(reach32=res['arms'][a]['creative']['pooled'][f'reach{k}'], knew=res['arms'][a]['knew']['pooled'][f'reach{n_eval}']))
        save()
    res['greedy_equal_across_arms'] = all(per[a]['greedy'] == per['U']['greedy'] for a in per)
    json.dump(dict(dev_ids=[r['id'] for r in dev], knew_ids=[r['id'] for r in kdev], creative32={a: per[a]['c32'] for a in per}, knew={a: per[a]['knew'] for a in per}), open(os.path.join(pdir, 'per_row.json'), 'w'))
    # 4. paired bootstraps, same row order
    bd = lambda x, y: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(x, y)))
    reach = lambda a, ds, kk, kinds=None: [float(d[f'right{kk}']) for d in per[a][ds] if kinds is None or d['kind'] in kinds]
    res['boot'] = dict(c2_C_minus_U=bd(reach('C', 'c32', k), reach('U', 'c32', k)),
                       groups={g: bd(reach('C', 'c32', k, ks), reach('U', 'c32', k, ks)) for g, ks in GROUPS.items()},
                       knew_F_minus_U=bd(reach('C', 'knew', n_eval), reach('U', 'knew', n_eval)), knew32_C_minus_U=bd(reach('C', 'knew', k), reach('U', 'knew', k)))
    if 'W' in per:
        res['boot']['c2_C_minus_W'] = bd(reach('C', 'c32', k), reach('W', 'c32', k))
    log('boot', res['boot'])
    # 5. marks (roadmap 377df3fc2c)
    b, ar = res['boot'], res['arms']
    dC, dU = (ar[x]['creative']['pooled'][f'distinct{k}'] for x in 'CU')
    res['marks'] = dict(
        primary=dict(C_minus_U_points=b['c2_C_minus_U']['points'], passes=b['c2_C_minus_U']['points'] >= 5.0, rule=f'C2 DEV creative reach@{k} on W1: C - U >= +5 points'),
        variety=dict(C=dC, U=dU, passes=dC >= 0.8 * dU, rule=f'C2 DEV distinct fitting programs per question within {k} tries: C >= 0.8 x U'),
        new_kind_guard=dict(C_F_minus_U_points=b['knew_F_minus_U']['points'], passes=b['knew_F_minus_U']['points'] >= -1.0, rule=f'K_new DEV reach@{n_eval} (F mode) on W1: C - U >= -1 point (point estimate)'),
        unit_test=dict(passes=bool(res['unit_test_before']['passes'] and res['unit_test_after']['passes'])),
        proved_wrong_here=dict(flag=b['c2_C_minus_U']['hi'] < 1.0, rule=f'C2 DEV creative reach@{k}: C - U upper end of the paired 95% interval < +1 point (both parents needed; loop 1 is then parked)'))
    res['marks']['passes'] = all(res['marks'][x]['passes'] is True for x in ('primary', 'variety', 'new_kind_guard', 'unit_test'))
    secs['total'] = time.time() - t00
    res['seconds'] = secs
    save()
    log('MARKS', {x: v.get('passes', v.get('flag')) for x, v in res['marks'].items() if isinstance(v, dict)}, res['marks']['passes'])
    return res


def s1f(nprimes, out, s1wdir, s3dir, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: s1f_parent(p, out, s1wdir, s3dir, **kw) for p in nprimes}


def s1freport(out, parents):
    """Test S1f verdict over the parents' DIR/<name>/s1f.json -> DIR/s1f-report.json: passes = every parent passes (primary, variety, new-kind guard, unit test); proved_wrong = every parent's proved_wrong_here; night_cost per parent."""
    res = {p: json.load(open(os.path.join(out, p, 's1f.json'))) for p in parents}
    mk = {p: r.get('marks') or {} for p, r in res.items()}
    rep = dict(parents=list(parents), passes=all(m.get('passes') is True for m in mk.values()), proved_wrong=all(m.get('proved_wrong_here', {}).get('flag') is True for m in mk.values()), per_parent=mk,
               night_cost={p: r.get('night_cost') for p, r in res.items()},
               rule='passes: primary (C2 DEV reach@32 C - U >= +5), variety (distinct32 C >= 0.8 U), new-kind guard (K_new reach@512 F mode >= -1) and unit test on every parent; proved wrong: C - U upper end < +1 on every parent')
    json.dump(rep, open(os.path.join(out, 's1f-report.json'), 'w'), indent=1)
    return rep


def _floats(s):
    return tuple(float(x) for x in s.split(','))


def _ints(s):
    return tuple(int(x) for x in s.split(','))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('s1report'); r.add_argument('--out', required=True); r.add_argument('--parents', nargs='+', default=['s100', 's101'])
    b = sub.add_parser('s1b'); b.add_argument('--nprime', nargs='+', required=True); b.add_argument('--s1', required=True); b.add_argument('--out', required=True)
    b.add_argument('--knew', default=KNEW); b.add_argument('--dev-limit', type=int); b.add_argument('--device', default='cpu'); b.add_argument('--threads', type=int); b.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('j'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--out', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True)
    q.add_argument('--skills-train'); q.add_argument('--skills-data'); q.add_argument('--pool-limit', type=int); q.add_argument('--dev-limit', type=int); q.add_argument('--n1', type=int, default=32)
    q.add_argument('--n2', type=int, default=480); q.add_argument('--seed', type=int, default=0); q.add_argument('--n-eval', type=int, default=512); q.add_argument('--replay-n', type=int); q.add_argument('--b2', help='the parent\'s B2 checkpoint (report-only harm comparison)')
    q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('jreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', required=True)
    q = sub.add_parser('s1w'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--out', required=True); q.add_argument('--s1', required=True); q.add_argument('--s3', required=True)
    q.add_argument('--pool-limit', type=int); q.add_argument('--dev-limit', type=int); q.add_argument('--n1', type=int, default=32); q.add_argument('--n2', type=int, default=480); q.add_argument('--seed', type=int, default=0)
    q.add_argument('--n-eval', type=int, default=512); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('s1wreport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', required=True)
    q = sub.add_parser('s1f'); q.add_argument('--nprime', nargs='+', required=True); q.add_argument('--out', required=True); q.add_argument('--s1w', required=True); q.add_argument('--s3', required=True)
    q.add_argument('--pool-limit', type=int); q.add_argument('--dev-limit', type=int); q.add_argument('--n-night', type=int, default=32); q.add_argument('--seed', type=int, default=0)
    q.add_argument('--n-eval', type=int, default=512); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int); q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('s1freport'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', required=True)
    for c in ('s1', 's3'):
        s = sub.add_parser(c)
        s.add_argument('--nprime', nargs='+', required=True); s.add_argument('--out', required=True)
        s.add_argument('--pool-limit', type=int); s.add_argument('--dev-limit', type=int)
        s.add_argument('--n1', type=int, default=32); s.add_argument('--n2', type=int, default=480); s.add_argument('--seed', type=int, default=0)
        s.add_argument('--device', default='cpu'); s.add_argument('--threads', type=int); s.add_argument('--no-resume', action='store_true')
        if c == 's1':
            s.add_argument('--knew', default=KNEW); s.add_argument('--lrs', type=_floats, default=(1e-3, 3e-3)); s.add_argument('--passes', type=_ints, default=(1, 2, 4))
            s.add_argument('--kl', type=float, default=0.1); s.add_argument('--n-eval', type=int, default=512, help='tries per row in the arm measures (roadmap ruling 71050e463c: 512)')
        else:
            s.add_argument('--skills-train'); s.add_argument('--skills-data'); s.add_argument('--replay-n', type=int)
            s.add_argument('--day-from', help="an S1 output dir: W1's search tries come from S1's day on the same parent when its key matches")
            s.add_argument('--control', choices=('replay', 'w1'), default='replay', help="replay = S3's Z; w1 = S3''s Z' (W1's own previous-night records)")
            s.add_argument('--w1-from', help='an earlier S3 output dir whose W1 is reused (same arguments)')
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 's1report':
        print(json.dumps(s1report(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 'jreport':
        print(json.dumps(jreport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 's1wreport':
        print(json.dumps(s1wreport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 's1freport':
        print(json.dumps(s1freport(a.out, tuple(a.parents)), indent=1))
    elif a.cmd == 's1f':
        ex = os.path.expanduser
        s1f(a.nprime, a.out, ex(a.s1w), ex(a.s3), pool_limit=a.pool_limit, dev_limit=a.dev_limit, n_night=a.n_night, seed=a.seed, n_eval=a.n_eval, device=a.device, resume=not a.no_resume)
    elif a.cmd == 's1w':
        ex = os.path.expanduser
        s1w(a.nprime, a.out, ex(a.s1), ex(a.s3), pool_limit=a.pool_limit, dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed, n_eval=a.n_eval, device=a.device, resume=not a.no_resume)
    elif a.cmd == 'j':
        ex = os.path.expanduser
        j(a.nprime, a.out, ex(a.s1), ex(a.s3), skills_train=ex(a.skills_train) if a.skills_train else None, skills_data=ex(a.skills_data) if a.skills_data else None, pool_limit=a.pool_limit,
          dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed, replay_n=a.replay_n, n_eval=a.n_eval, device=a.device, resume=not a.no_resume, b2=a.b2)
    elif a.cmd == 's1b':
        print(json.dumps(s1b(a.nprime, os.path.expanduser(a.s1), a.out, device=a.device, knew_dir=a.knew, dev_limit=a.dev_limit, resume=not a.no_resume)['verdict'], indent=1))
    elif a.cmd == 's1':
        s1(a.nprime, a.out, pool_limit=a.pool_limit, dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed, lrs=a.lrs, passes=a.passes, kl=a.kl, n_eval=a.n_eval, device=a.device,
           knew_dir=a.knew, resume=not a.no_resume)
    else:
        s3(a.nprime, a.out, skills_train=a.skills_train, skills_data=a.skills_data, pool_limit=a.pool_limit, dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed,
           replay_n=a.replay_n, device=a.device, resume=not a.no_resume, day_from=os.path.expanduser(a.day_from) if a.day_from else None,
           control=a.control, w1_from=os.path.expanduser(a.w1_from) if a.w1_from else None)
