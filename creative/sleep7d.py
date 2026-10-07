"""Roadmap 7d, the creative part of sleep (screens S1 and S3). CPU, DEV and pool only: C2 test / labelled and K_new test are never opened.
  python3 -m creative.sleep7d s1 --nprime ~/c7d/s100/Nprime.pt ~/c7d/s101/Nprime.pt --out DIR [--pool-limit N --dev-limit N --n2 480 --seed 0]
  python3 -m creative.sleep7d s3 --nprime ... --out DIR --skills-train train.jsonl --skills-data data_big
Pieces: a switchable low-rank adapter ("creative mode") on top of N' (adapter OFF = N' bit for bit, the worker); logp_tries (a teacher-forced copy of
sampler.sample_run's loop with gradients on); the day (worker first try = greedy with the adapter off, the example check says pass or fail, creative mode
searches the stuck rows only); loop 1 (reward sleep on the adapter only: fitting tries up, failing tries down, KL to the pre-night adapter);
S1 = does a night's reward sleep make creative mode better at NEW rule kinds (K_new) than an untrained adapter (U) or a reward-shuffled one (S);
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
        for j, rec in enumerate(tr):
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
              knew_dir=KNEW, name=None, resume=True, log=_log, allres=None):
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
    kdev = c2_stones._with_nums(_limit(knew.load_dev(knew_dir), dev_limit))
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
    # 4. C: the grid, picked on C2 DEV rows the worker fails
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
    torch.save(dict(C=c_state, S=s_state, setting=best, init=init), os.path.join(pdir, 'adapters.pt'))
    # 5. measures per arm, one sampling seed for every arm
    mseed = seed + 777
    states = dict(U=init, C=c_state, S=s_state)
    res['arms'], per = {}, {}
    t0 = time.time()
    for arm, st in states.items():
        load_adapter_state(model, st)
        kn, kp = measure(model, kdev, vocab, device, T, n_eval, mseed)
        c2, cp = measure(model, dev, vocab, device, T, n_eval, mseed)
        res['arms'][arm] = dict(knew=kn, c2_dev=c2)
        per[arm] = dict(knew=kp, c2_dev=cp)
        show = ('reach32', f'reach{n_eval}', f'fit{n_eval}', 'tries_to_first_fit', 'distinct_fitting')
        log('arm', arm, 'K_new', {k: kn['pooled'].get(k) for k in show}, 'C2 DEV', {k: c2['pooled'].get(k) for k in show})
        res['seconds'] = secs
        save()
    secs['measure'] = time.time() - t0
    json.dump({arm: {ds: [{k: v for k, v in x.items() if k != 'kind'} for x in rows] for ds, rows in d_.items()} for arm, d_ in per.items()}, open(os.path.join(pdir, 'per_row.json'), 'w'))
    # paired bootstrap per row: K_new reach@n_eval (the primary measure, roadmap ruling 71050e463c), reach@32 reported; C2 DEV reach@32 (the in-kind mark) and reach@n_eval
    vec = lambda arm, ds, k: [float(x[f'right{k}']) for x in per[arm][ds]]
    bt = lambda a, b, ds, k: dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(vec(a, ds, k), vec(b, ds, k))))
    E = n_eval
    res['boot'] = dict(knew_C_minus_U=bt('C', 'U', 'knew', E), knew_C_minus_S=bt('C', 'S', 'knew', E), knew32_C_minus_U=bt('C', 'U', 'knew', 32),
                       knew32_C_minus_S=bt('C', 'S', 'knew', 32), c2_dev_C_minus_U=bt('C', 'U', 'c2_dev', 32), c2_dev_at_eval_C_minus_U=bt('C', 'U', 'c2_dev', E))
    log('boot', res['boot'])
    # 6. the worker-untouched test again, with each trained adapter loaded (flag off)
    after = {}
    for arm in ('C', 'S'):
        load_adapter_state(model, states[arm])
        after[arm] = worker_untouched(model, ref, dev[:64], vocab, device, perturb=False)
    res['unit_test_after'] = after
    log('worker-untouched after training', after)
    # 7. marks
    a = res['arms']
    kC, kU, kS = (a[x]['knew']['pooled'] for x in 'CUS')
    b = res['boot']
    res['marks'] = dict(
        transfer=dict(C_minus_U_points=b['knew_C_minus_U']['points'], C_minus_S_points=b['knew_C_minus_S']['points'],
                      passes=b['knew_C_minus_U']['points'] >= 5.0 and b['knew_C_minus_S']['points'] >= 3.0, rule=f'K_new reach@{E}: C - U >= +5 and C - S >= +3 points'),
        variety=dict(C=kC['distinct_fitting'], U=kU['distinct_fitting'], passes=kC['distinct_fitting'] >= 0.8 * kU['distinct_fitting'],
                     rule=f'K_new distinct fitting programs per row over {E} tries: C >= 0.8 x U'),
        in_kind=dict(C=a['C']['c2_dev']['pooled']['reach32'], U=a['U']['c2_dev']['pooled']['reach32'], passes=a['C']['c2_dev']['pooled']['reach32'] >= a['U']['c2_dev']['pooled']['reach32'],
                     rule='C2 DEV reach@32: C >= U'),
        unit_test=dict(passes=bool(ut['passes'] and all(x['passes'] for x in after.values()))),
        proved_wrong=dict(flag=b['knew_C_minus_S']['hi'] < 1.0, rule=f'K_new reach@{E}: C - S upper end of the paired 95% interval < +1 point'))
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


# ---------------------------------------------------------------- 7. S3
GROUPS = dict(near_copy=c2_pilot.COPY_KINDS, multi_step=c2_pilot.HARD_KINDS)


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
              name=None, resume=True, log=_log, allres=None, day_from=None):
    """One parent's S3. After every stage DIR/s3.json (all parents so far, `allres`) and DIR/<name>/s3.json are written; W1 is cached (DIR/<name>/W1.pt) when the same arguments come back.
    day_from = an S1 output dir: W1's records come from S1's day on this parent when its key matches (else W1 runs its own search; s3.json says which)."""
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
    # 1. W1 = one C2b W night from N' (job 8's two-pass search at T, <= 2 distinct fitting tries per row, the frozen dose)
    wpath = os.path.join(pdir, 'W1.pt')
    prev = json.load(open(os.path.join(pdir, 's3.json'))) if resume and os.path.exists(os.path.join(pdir, 's3.json')) else {}
    if resume and os.path.exists(wpath) and prev.get('args') == args and 'W1_night' in prev:
        W1, _, _ = sleep.load_parent(wpath, device)
        W1.eval()
        res['W1_night'] = prev['W1_night']
        log('W1: loaded', wpath)
    else:
        t0 = time.time()
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
        info = dict(source=source, samples=drawn, records=len(recs), records_by_kind={k: sum(c for i, c in counts.items() if kind_of[i] == k) for k in sorted(set(kind_of.values()))},
                    pool_with_fit_pass1=sum(fit1), pool_with_fit_final=sum(fit))
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
    zrecs = replay_only_records(replay, warm_rows, len(precs), seed + 4)
    Z, zi = sleep_on(W1, zrecs, vocab, replay, warm_rows, lr, visits, seed, device)
    assert pi['updates'] == zi['updates'], 'P and Z must get the same number of updates'
    res['P_sleep'], res['Z_sleep'] = pi, zi
    secs['sleep_PZ'] = time.time() - t0
    log('P sleep', pi, 'Z sleep', zi)
    save()
    # 4. the next day: C2 DEV and fresh practised, greedy first try; skills harm vs W1
    t0 = time.time()
    sk = {}
    models = dict(W1=W1, P=P, Z=Z)
    per, res['arms'] = {}, {}
    for arm, m in models.items():
        dp, fp = greedy_rows(m, dev, vocab, device), greedy_rows(m, fresh, vocab, device)
        per[arm] = dp
        sk[arm] = skills_eval(m, skills_data, device)
        res['arms'][arm] = dict(s3_measures(dp, fp), skills=sk[arm])
        if sk['W1'] and sk[arm]:
            res['arms'][arm]['skills_harm_vs_W1_points'] = 100 * (sk['W1']['pooled5'] - sk[arm]['pooled5'])
        log('arm', arm, {k: res['arms'][arm][k] for k in ('stuck_rate', 'first_try_right')})
        save()
    secs['measure'] = time.time() - t0
    stuck = lambda arm: [0.0 if d['fit'] else 1.0 for d in per[arm]]
    zp = c2_pilot.boot(stuck('Z'), stuck('P'))
    res['boot'] = dict(stuck_Z_minus_P=dict(zip(('points', 'lo', 'hi'), zp)))
    # 5. marks
    a = res['arms']
    gap = {g: 100 * (a['P']['first_try_right'][g] - a['Z']['first_try_right'][g]) for g in list(GROUPS) + ['practised']}
    harm = a['P'].get('skills_harm_vs_W1_points')
    res['marks'] = dict(
        stuck=dict(Z_minus_P_points=zp[0], passes=zp[0] >= 3.0, rule='P stuck rate <= Z stuck rate - 3 points (C2 DEV greedy try fails the example check)'),
        groups=dict(P_minus_Z_first_try_points=gap, passes=all(v >= -2.0 for v in gap.values()), rule='no group more than 2 points below Z on first try right'),
        harm=dict(P_points=harm, Z_points=a['Z'].get('skills_harm_vs_W1_points'), passes=None if harm is None else harm <= 2.0, rule='P skills harm vs W1 <= 2 points (100 x pooled-5 drop)'),
        proved_wrong=dict(flag=zp[2] < 1.0, rule='Z - P stuck-rate upper end of the paired 95% interval < +1 point'))
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


def _floats(s):
    return tuple(float(x) for x in s.split(','))


def _ints(s):
    return tuple(int(x) for x in s.split(','))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
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
    a = a.parse_args()
    if a.threads:
        torch.set_num_threads(a.threads)
    if a.cmd == 's1':
        s1(a.nprime, a.out, pool_limit=a.pool_limit, dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed, lrs=a.lrs, passes=a.passes, kl=a.kl, n_eval=a.n_eval, device=a.device,
           knew_dir=a.knew, resume=not a.no_resume)
    else:
        s3(a.nprime, a.out, skills_train=a.skills_train, skills_data=a.skills_data, pool_limit=a.pool_limit, dev_limit=a.dev_limit, n1=a.n1, n2=a.n2, seed=a.seed,
           replay_n=a.replay_n, device=a.device, resume=not a.no_resume, day_from=os.path.expanduser(a.day_from) if a.day_from else None)
