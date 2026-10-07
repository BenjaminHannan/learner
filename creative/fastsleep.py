"""Fast sleep screen (thread "fast sleep", 10-07). CPU, DEV only: test and labelled are never opened; pool is the sleep pool, as in Mac job 6.
Question (Ben): the sleep step must learn quickly, with few FLOPs. "Fast" = DEV greedy first-try gain (fits every example AND right, the C2b mark)
per sleep FLOP, against job 6's plain fine-tune (fresh AdamW on every weight, half skills replay, lr {3e-4, 1e-3} x visits {4, 8, 16}).

  python3 -m creative.fastsleep setup  --ckpt B2_s100.pt --out DIR --skills-train train.jsonl --skills-data data_big [--floors dev_floors.json]
  python3 -m creative.fastsleep screen --out DIR --skills-train train.jsonl --skills-data data_big --tag T --sets PC,W --plan 'knn:c=50,cal=0.99,old=512;ft:lr=0.0003,visits=16'
  python3 -m creative.fastsleep posteval --out DIR --skills-train train.jsonl --tag T2 --sets W --plan '...'   (old-parts check + DEV search)
  python3 -m creative.fastsleep confirm --ckpt B2_s200.pt --out ROOT/s200 --skills-train train.jsonl --skills-data data_big --floors dev_floors.json
  python3 -m creative.fastsleep report --out ROOT                                                               (6-seed confirm marks)

setup = job 6 steps 0-2 exactly (c2_pilot's own functions): N = raw B2 -> warm-up -> stepping-stone sleep; pool temperature on DEV; N samples the pool
32 times; arms W (fits every example, <= 2 per question) and PC (reference programs, same count). Saved to DIR/setup.pt with the target cache entries.
screen = each sleep method on PC and on W from the same N; per method: sleep FLOPs (torch FlopCounterMode around the whole sleep, caching included),
seconds, DEV greedy first try (fits, right) per kind and pooled, pooled-5 skills harm vs N (points).

Methods (all from the same N; nothing changes job 6):
  ft     job 6's sleep (custom fine-tune of every weight). Its grid is the baseline curve.
  heads  "fast weights on the decision heads": freeze the reader and the looped thinker, cache the head inputs of each record under teacher forcing
         (ONE forward pass per record), then fit only the heads that read them (op, both operand queries, slot keys, answer query, mode) for many
         epochs on the cache. Exact: with the thinker frozen the head inputs do not depend on the heads (the forced op and operand values are fixed).
  knn    an episodic memory the heads read (v2): keys = the thinker state at each forced step, values = the forced op and the slot ids of both
         operands (plus an answer note); top-k cosine vote added to the op / slot logits. No gradient at all; a per-step gate (calibrated on
         skills TRAIN replay rows when cal > 0) keeps it silent on states far from every note. old = N also writes that many warm-split
         add/mult solver programs (keeps old parts). Results and marks: creative/results/fastsleep/.
  lora   rank-r adapters on the core linears and heads (written, not screened).
"""
import argparse, copy, json, math, os, random, time
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.flop_counter import FlopCounterMode
from creative import c2_dev, c2_pilot, c2_stones, fewshot, legal, rules_real as R, sleep, stones
from custom_io.data import Dataset, collate, load_rows, to_device
from custom_io.evalx import CHAIN5, evaluate
from custom_io.models import progparse as pp

DATA = 'creative/data/c2'
log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- setup (job 6 steps 0-2)
def setup(ckpt, out, skills_train, skills_data, floors_path=None, device='cpu', seed=0, n=32, temps=c2_pilot.TEMPS, T=None):
    os.makedirs(out, exist_ok=True)
    replay = sleep.load_replay(skills_train, None, seed)
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool'))
    fp = os.path.join(out, 'dev_floors.json')
    if floors_path and not os.path.exists(fp):
        import shutil
        shutil.copy(floors_path, fp)
    floors = c2_dev.floors_for(dev, fp)
    t0 = time.time()
    m0, vocab, meta, w = c2_stones._warm(ckpt, R.warm_records(R.load_split(DATA, 'warm')), replay, 4, 3e-4, seed, device)
    log('warm', w, round(time.time() - t0))
    sleep.save_parent(m0, meta['name'], meta['cfg'], vocab, os.path.join(out, 'warm.pt'), step=(meta['step'] or 0), warmup=True)
    ss_rows, ss_info = stones.make_stone_rows(2048, seed)
    N, ss = c2_stones._arm(m0, stones.solver_records(ss_rows), replay, vocab, 4, 3e-4, seed, device)
    log('N built', ss, round(time.time() - t0))
    sleep.save_parent(N, meta['name'], meta['cfg'], vocab, os.path.join(out, 'N_ss.pt'), step=(meta['step'] or 0), warmup=True)
    res = dict(ckpt=ckpt, warm=w, ss=ss)
    if T is None:
        rep = c2_dev.dev_report(N, vocab, dev, floors, device, n, seed, temps=temps, extend=(), log=log)
        ok = {t: g for t, g in rep['temps'].items() if g['sameness_ok']}
        T = float(max(ok, key=lambda t: ok[t]['reach32']))
        res['pool_temperature'] = {t: dict(reach32=g['reach32'], sameness_ok=g['sameness_ok']) for t, g in rep['temps'].items()}
    res['T'] = T
    log('pool T', T)
    samples = legal.raw_samples(N, pool, vocab, device, n=n, temperature=T, level=0, seed=seed + 1)
    arms = fewshot.build_arms(pool, samples, samples, seed=seed)
    PC = c2_pilot.pc_records(pool, arms['counts'])
    recs = dict(W=arms['W'], R=arms['R'], H=arms['H'], PC=PC)
    cache = {r['id']: pp._CACHE[r['id']] for v in recs.values() for r in v}
    res['arm_build'] = dict(diag=arms['diag'], n_W=len(arms['W']), n_PC=len(PC), questions_with_W=len(arms['counts']))
    torch.save(dict(records=recs, cache=cache, T=T, res=res), os.path.join(out, 'setup.pt'))
    json.dump(res, open(os.path.join(out, 'setup.json'), 'w'), indent=1)
    log('setup done', res['arm_build'], round(time.time() - t0))
    return res


def load_setup(out, device='cpu'):
    s = torch.load(os.path.join(out, 'setup.pt'), weights_only=False)
    pp._CACHE.update(s['cache'])
    N, vocab, meta = sleep.load_parent(os.path.join(out, 'N_ss.pt'), device)
    return N, vocab, meta, s


# ---------------------------------------------------------------- evaluation
def skills5(m, skills_data, device, bs=256):
    """Pooled-5 exact (the skills-harm measure of job 6: chain families of data_big dev/in_dist), as a fraction."""
    rows = [r for r in load_rows(os.path.join(skills_data, 'dev', 'in_dist.jsonl')) if r['family'] in CHAIN5]
    was = m.training
    m.eval()
    r = evaluate(m, rows, bs, device)
    m.train(was)
    return r['exact'] / 100


def dev_eval(m, dev, vocab, device):
    g = c2_pilot.greedy_eval(m, dev, vocab, device)
    return dict(right=g['right'], fits=g['fits'], by_kind={k: round(v['right'], 4) for k, v in g['by_kind'].items()}), g['per_q_right']


def count_flops(fn):
    with FlopCounterMode(display=False) as fc:
        t0 = time.time()
        out = fn()
    return out, fc.get_total_flops(), time.time() - t0


# ---------------------------------------------------------------- method: ft (job 6's sleep)
def m_ft(N, recs, replay, vocab, device, n_w, lr=3e-4, visits=4, use_replay=True, seed=0, batch=64):
    """Job 6's sleep_arm: updates = visits x |W| / 32 (with replay; half the batch is records), the same updates for every record set.
    use_replay=False: the whole batch is records; updates = visits x |W| / 64 (the same visits per record, half the rows)."""
    m = copy.deepcopy(N)
    rp = replay if use_replay else []
    per = batch // 2 if rp else batch
    u = max(1, visits * n_w // per)
    mv = max(visits, math.ceil(u * per / max(len(recs), 1)))
    so = sleep.sleep(m, recs, rp, vocab, sleep.SleepCfg(updates=u, batch=batch, lr=lr, warmup=min(20, max(1, u // 5)), seed=seed, max_visits=mv), device)
    return m, dict(updates=u, rows_per_update=batch, last_loss=sum(so['loss'][-10:]) / max(len(so['loss'][-10:]), 1))


# ---------------------------------------------------------------- head inputs under teacher forcing
HEADS = ('op_head', 'q_a', 'q_b', 'k_slot', 'q_ans', 'mode_head')


@torch.no_grad()
def head_inputs(m, rows, vocab, device, bs=256):
    """One teacher-forced forward per row; captures what the heads read. -> dict of tensors:
    z [n,7,d] (control token 0 after ln_z at each of the 7 write steps), S [n,8,M,d] (ln_k(slot states) at each write step and after the last loop),
    ok [n,8,M] (valid slots at each), zf [n,d], and the gold targets op [n,7], a/b [n,7,M], ans [n,M], mode [n], w_row [n], has [n]."""
    m.eval()
    keep = {k: [] for k in ('z', 'S', 'ok', 'zf', 'op', 'a', 'b', 'ans', 'mode', 'has')}
    for s in range(0, len(rows), bs):
        rs = rows[s:s + bs]
        b = to_device(collate([Dataset(rs, vocab, strict=False)[i] for i in range(len(rs))]), device)
        g = m.gold(rs, device)
        cap = dict(z=[], S=[], zf=[], ok=[])
        hs = [m.op_head.register_forward_pre_hook(lambda mod, inp: cap['z'].append(inp[0])),
              m.k_slot.register_forward_pre_hook(lambda mod, inp: cap['S'].append(inp[0])),
              m.mode_head.register_forward_pre_hook(lambda mod, inp: cap['zf'].append(inp[0]))]
        ptr0 = m.ptr
        m.ptr = lambda q, k, ok: (cap['ok'].append(ok), ptr0(q, k, ok))[1]
        try:
            m.run(b, gold=g)
        finally:
            m.ptr = ptr0
            for h in hs:
                h.remove()
        # ptr calls per write step: a, b (same ok); then ans (valid) and word (wvalid): keep one per step + the ans one
        oks = cap['ok']
        okk = [oks[2 * i] for i in range(len(cap['z']))] + [oks[2 * len(cap['z'])]]
        keep['z'].append(torch.stack(cap['z'], 1)); keep['S'].append(torch.stack(cap['S'], 1)); keep['ok'].append(torch.stack(okk, 1))
        keep['zf'].append(cap['zf'][0])
        for k in ('op', 'a', 'b', 'ans', 'mode', 'has'):
            keep[k].append(g[k])
    return {k: torch.cat(v, 0) for k, v in keep.items()}


def head_loss(heads, f, idx, w_noop, dk):
    """Ledger.loss restricted to the parts the heads produce (program ops and operands, mode, answer pointer), on cached inputs f[idx].
    heads = dict of nn.Linear (op_head, q_a, q_b, k_slot, q_ans, mode_head)."""
    z, S, ok, zf = f['z'][idx], f['S'][idx], f['ok'][idx], f['zf'][idx]
    op, A, Bm, ans, mode, has = (f[k][idx] for k in ('op', 'a', 'b', 'ans', 'mode', 'has'))
    B = z.shape[0]
    w_row = torch.where(has, 1.0, w_noop)
    comm = torch.isin(op, torch.tensor(pp.COMM))
    K = heads['k_slot'](S)                                                       # [B,8,M,dk]
    ptr = lambda q, k, okm: (torch.einsum('bk,bmk->bm', q, k) / math.sqrt(dk)).masked_fill(~okm, -1e9)
    lop = lptr = 0.0
    for s in range(z.shape[1]):
        lg = heads['op_head'](z[:, s])
        lop = lop + (F.cross_entropy(lg, op[:, s], reduction='none') * w_row).mean()
        la, lb = ptr(heads['q_a'](z[:, s]), K[:, s], ok[:, s]), ptr(heads['q_b'](z[:, s]), K[:, s], ok[:, s])
        pa, pb = la.log_softmax(-1), lb.log_softmax(-1)
        ga, gb = A[:, s], Bm[:, s]
        lab = torch.logsumexp(pa.masked_fill(~ga, -1e9), -1) + torch.logsumexp(pb.masked_fill(~gb, -1e9), -1)
        lba = torch.logsumexp(pa.masked_fill(~gb, -1e9), -1) + torch.logsumexp(pb.masked_fill(~ga, -1e9), -1)
        nll = -torch.where(comm[:, s], torch.logaddexp(lab, lba), lab)
        lptr = lptr + (nll * (op[:, s] > 0)).sum() / B
    lmode = F.cross_entropy(heads['mode_head'](zf), mode)
    lans_all = ptr(heads['q_ans'](zf), K[:, -1], ok[:, -1])
    lans = torch.where(mode == 0, -(torch.logsumexp(lans_all.masked_fill(~ans, -1e9), -1) - torch.logsumexp(lans_all, -1)), torch.zeros(B)).sum() / B
    return lop + lptr + lmode + lans


# ---------------------------------------------------------------- method: heads (fast weights on the decision heads)
def m_heads(N, recs, replay, vocab, device, n_w, epochs=30, lr=3e-3, n_replay=None, anchor=0.0, bs=64, seed=0, which=HEADS):
    """Freeze everything but the heads; cache their inputs with one forward per record (and per replay row used); fit the heads on the cache
    (Adam, `epochs` passes, minibatches mixing records and replay 1:1 when replay is used); anchor = L2 pull toward N's head weights."""
    m = copy.deepcopy(N)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    fr = head_inputs(m, recs, vocab, device)
    rp = rng.sample(replay, n_replay if n_replay is not None else len(recs)) if replay and n_replay != 0 else []
    fp = head_inputs(m, rp, vocab, device) if rp else None
    heads = {k: getattr(m, k) for k in HEADS}
    params = [p for k in which for p in heads[k].parameters()]
    ref = [p.detach().clone() for p in params]
    opt = torch.optim.Adam(params, lr=lr)
    n, nr = len(recs), len(rp)
    steps = 0
    for ep in range(epochs):
        order = list(range(n))
        rng.shuffle(order)
        for s in range(0, n, bs):
            loss = head_loss(heads, fr, torch.tensor(order[s:s + bs]), m.w_noop, m.dk)
            if fp is not None:
                loss = loss + head_loss(heads, fp, torch.tensor([rng.randrange(nr) for _ in range(min(bs, n - s))]), m.w_noop, m.dk)
            if anchor:
                loss = loss + anchor * sum(((p - q) ** 2).sum() for p, q in zip(params, ref))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            steps += 1
    return m, dict(epochs=epochs, steps=steps, lr=lr, n_replay=nr, anchor=anchor, trained=sum(p.numel() for p in params), last_loss=float(loss.detach()))


# ---------------------------------------------------------------- method: knn (episodic memory the heads read)
class _MemOp(nn.Module):
    def __init__(self, base, mem):
        super().__init__()
        self.base, self.mem = base, mem

    def forward(self, z):
        return self.base(z) + self.mem.op_bias(z)


class Memory:
    """Per write step t (1..7): keys (unit thinker states at that forced step) -> forced op (NOOP included) and forced operand slot ids a, b; plus the
    answer memory (final state -> forced answer slot id). The step is tracked by call order: the reader runs once per pass (reset), op_head once per
    write step and the two operand pointers right after it; q_ans once after the loop, then its pointer.
    Query: top-k cosine neighbours among the same step's entries, weights softmax(sim / tau), gate = 1 if the best similarity >= theta.
    op logits += gate * c * sum_i w_i onehot(op_i); operand / answer pointer logits += gate * c * sum_i w_i onehot(slot_i).
    v1 (first screen) shifted the operand QUERY toward the stored slot's key instead; it could not tell the constants apart (10 vs 2), so v2 uses slot ids."""

    def __init__(self, steps, ans, n_ops, n_slots, k=16, tau=0.05, theta=0.9, c=20.0):
        self.steps = [dict(keys=F.normalize(K, dim=-1), op=o, a=a, b=b) for K, o, a, b in steps]
        self.ans = dict(keys=F.normalize(ans[0], dim=-1), slot=ans[1])
        self.n_ops, self.n_slots, self.k, self.tau, self.theta, self.c = n_ops, n_slots, k, tau, theta, c
        self.t, self.pending, self.fired = 0, [], [0, 0]
        self.theta_t, self.theta_ans = [theta] * len(self.steps), theta

    def reset(self, *_):
        self.t, self.pending = 0, []

    def _nbrs(self, z, keys, theta=None):
        sim = F.normalize(z.float(), dim=-1) @ keys.T
        top, ix = sim.topk(min(self.k, sim.shape[1]), -1)
        return (top / self.tau).softmax(-1), ix, (top[:, 0] >= (self.theta if theta is None else theta)).float()

    def calibrate(self, f, q):
        """Gate thresholds from skills rows (cached head inputs f of replay rows, never DEV): per step, theta_t = max(theta, the q-quantile of the best
        similarity of a skills state to that step's memory), so the memory stays silent on all but about (1 - q) of skills decisions."""
        best = lambda z, keys: (F.normalize(z.float(), dim=-1) @ keys.T).max(-1).values
        for t, e in enumerate(self.steps):
            self.theta_t[t] = max(self.theta, float(torch.quantile(best(f['z'][:, t], e['keys']), q)))
        self.theta_ans = max(self.theta, float(torch.quantile(best(f['zf'], self.ans['keys']), q)))

    def _vote(self, vals, w, ix, gate, n):
        return gate[:, None] * self.c * torch.zeros(w.shape[0], n).scatter_add_(1, vals[ix], w)

    def op_bias(self, z):
        t = min(self.t, len(self.steps) - 1)
        e = self.steps[t]
        self.t += 1
        w, ix, gate = self._nbrs(z, e['keys'], self.theta_t[t])
        self.fired[0] += int(gate.sum()); self.fired[1] += gate.numel()
        self.pending = [self._vote(e['a'], w, ix, gate, self.n_slots), self._vote(e['b'], w, ix, gate, self.n_slots)]
        return self._vote(e['op'], w, ix, gate, self.n_ops).to(z.dtype)

    def ans_hook(self, mod, inp):
        w, ix, gate = self._nbrs(inp[0], self.ans['keys'], self.theta_ans)
        self.pending = [self._vote(self.ans['slot'], w, ix, gate, self.n_slots)]

    def wrap_ptr(self, ptr):
        def f(q, k, ok):
            out = ptr(q, k, ok)
            if self.pending and out.shape[-1] == self.n_slots:
                out = out + self.pending.pop(0).to(out.dtype)
            return out
        return f


def build_memory(m, recs, vocab, device):
    """One teacher-forced forward per record (head_inputs) -> per-step entries (keys, op, a slot, b slot) and the answer entries (zf, answer slot)."""
    f = head_inputs(m, recs, vocab, device)
    first = lambda mask: mask.float().argmax(-1)                                 # the first allowed slot
    has = f['has']
    steps = [(f['z'][has, t], f['op'][has, t], first(f['a'][has, t]), first(f['b'][has, t])) for t in range(f['op'].shape[1])]
    return steps, (f['zf'][has], first(f['ans'][has]))


_WARM = {}


def m_knn(N, recs, replay, vocab, device, n_w, k=16, tau=0.05, theta=0.9, c=20.0, cal=0.0, seed=0, old=0):
    """cal > 0: gate thresholds calibrated on as many skills replay rows as records (one forward each, counted), quantile `cal` (added after the first screen).
    old > 0: the memory also holds `old` practised-kind solver records (the warm split's add/mult reference programs), so a practised question finds its
    own kind's entries (added after the old-parts check; their forward passes are counted here, though with frozen weights they are made once per parent)."""
    m = copy.deepcopy(N)
    n_cal = len(recs)
    if old:
        if 'w' not in _WARM:
            _WARM['w'] = R.warm_records(R.load_split(DATA, 'warm'))
        recs = list(recs) + _WARM['w'][:old]
    steps, ans = build_memory(m, recs, vocab, device)
    mem = Memory(steps, ans, m.op_head.out_features, pp.M, k, tau, theta, c)
    if cal:
        mem.calibrate(head_inputs(m, random.Random(seed).sample(replay, n_cal), vocab, device), cal)
    m.reader.register_forward_pre_hook(mem.reset)
    m.q_ans.register_forward_pre_hook(mem.ans_hook)
    m.op_head = _MemOp(m.op_head, mem)
    m.ptr = mem.wrap_ptr(m.ptr)
    m._mem = mem
    return m, dict(memory=int(ans[0].shape[0]), k=k, tau=tau, theta=theta, c=c, version=2, cal=cal, old=old, theta_t=[round(x, 4) for x in mem.theta_t], theta_ans=round(mem.theta_ans, 4))


# ---------------------------------------------------------------- method: lora (low-rank adapters on the thinker, everything else frozen)
class _LoRA(nn.Module):
    def __init__(self, base, r, alpha):
        super().__init__()
        self.base, self.scale = base, alpha / r
        self.A = nn.Parameter(torch.randn(r, base.in_features) / math.sqrt(base.in_features))
        self.B = nn.Parameter(torch.zeros(base.out_features, r))

    def forward(self, x):
        return self.base(x) + (x @ self.A.T @ self.B.T) * self.scale


def m_lora(N, recs, replay, vocab, device, n_w, r=4, alpha=8.0, lr=3e-3, visits=2, use_replay=False, seed=0, batch=64):
    """Rank-r adapters on every linear layer of the looped thinker's blocks and on the heads; all base weights frozen; Adam; visits per record as ft."""
    m = copy.deepcopy(N)
    for p in m.parameters():
        p.requires_grad_(False)
    for blk in m.core:
        for name in ('q', 'kv', 'o', 'qkv', 'p', 'fc', 'out'):
            setattr(blk, name, _LoRA(getattr(blk, name), r, alpha))
    for name in ('op_head', 'q_a', 'q_b', 'q_ans'):
        setattr(m, name, _LoRA(getattr(m, name), r, alpha))
    params = [p for p in m.parameters() if p.requires_grad]
    rp = replay if use_replay else []
    per = batch // 2 if rp else batch
    u = max(1, visits * n_w // per)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    order = sleep._order(len(recs), u * per, rng)
    rorder = sleep._order(len(rp), u * (batch - per), rng) if rp else []
    opt = torch.optim.Adam(params, lr=lr)
    m.train()
    for step in range(u):
        rows = [recs[i] for i in order[step * per:(step + 1) * per]] + [rp[i] for i in rorder[step * (batch - per):(step + 1) * (batch - per)]]
        b = to_device(collate([Dataset(rows, vocab, strict=False)[i] for i in range(len(rows))]), device)
        loss = m.loss(b)[0]
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
    return m, dict(updates=u, trained=sum(p.numel() for p in params), last_loss=float(loss.detach()))


METHODS = dict(ft=m_ft, heads=m_heads, knn=m_knn, lora=m_lora)


# ---------------------------------------------------------------- screen
def screen(out, skills_data, skills_train, plan, device='cpu', seed=0, tag='screen', sets=('PC', 'W')):
    N, vocab, meta, s = load_setup(out, device)
    recs = s['records']
    n_w = len(recs['W'])
    replay = sleep.load_replay(skills_train, None, seed)
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
    path = os.path.join(out, f'{tag}.json')
    res = json.load(open(path)) if os.path.exists(path) else dict(runs=[])
    done = {(r['set'], r['method'], json.dumps(r['kw'], sort_keys=True)) for r in res['runs']}
    if 'N' not in res:
        d, _ = dev_eval(N, dev, vocab, device)
        res['N'] = dict(dev=d, skills5=skills5(N, skills_data, device), n_W=n_w, n_PC=len(recs['PC']), T=s['T'])
        json.dump(res, open(path, 'w'), indent=1)
        log('N', res['N'])
    base5 = res['N']['skills5']
    for set_name in sets:
        for name, kw in plan:
            key = (set_name, name, json.dumps(kw, sort_keys=True))
            if key in done:
                continue
            (m, info), flops, secs = count_flops(lambda: METHODS[name](N, recs[set_name], replay, vocab, device, n_w, **kw))
            d, _ = dev_eval(m, dev, vocab, device)
            sk = skills5(m, skills_data, device)
            run = dict(set=set_name, method=name, kw=kw, info=info, sleep_flops=flops, sleep_tflops=flops / 1e12, seconds=round(secs, 1), dev=d,
                       gain_points=100 * (d['right'] - res['N']['dev']['right']), skills_harm_points=100 * (base5 - sk))
            if hasattr(m, '_mem'):
                run['memory_fired'] = m._mem.fired
            res['runs'].append(run)
            json.dump(res, open(path, 'w'), indent=1)
            log(set_name, name, kw, {k: run[k] for k in ('sleep_tflops', 'seconds', 'gain_points', 'skills_harm_points')}, d['by_kind'])
    return res


def practised_and_reach(m, vocab, device, dev, T, fresh, n=32, seed=0):
    """Old-parts check (job 6's `practised`: 256 fresh add/mult questions, 32 plain samples at T = 1.0, reach@32 and first sample; plus greedy first try
    fits-and-right) and DEV search (reach@4 / reach@32 over 32 plain samples at the pool temperature T, repeats counted)."""
    m.eval()
    out = {}
    smp = legal.raw_samples(m, fresh, vocab, device, n=n, temperature=1.0, level=0, seed=seed)
    sc = fewshot.score_samples(fresh, smp, ks=(1, 4, 32))
    g = c2_pilot.greedy_eval(m, fresh, vocab, device)
    out['practised'] = dict(reach32=sc['reach32'], first_sample=sc['reach1'], greedy_right=g['right'])
    smp = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
    sc = fewshot.score_samples(dev, smp, ks=(4, 32))
    out['dev_search'] = dict(reach4=sc['reach4'], reach32=sc['reach32'], luck=sc['luck'])
    return out


def posteval(out, skills_train, plan, device='cpu', seed=0, tag='posteval', sets=('W',)):
    """Re-make each (deterministic) slept model of `plan` and add the old-parts check and DEV search to it; N first."""
    N, vocab, meta, s = load_setup(out, device)
    recs, n_w = s['records'], len(s['records']['W'])
    replay = sleep.load_replay(skills_train, None, seed)
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
    fresh = c2_stones._with_nums(stones.fresh_practised(256, 1, 'fresh-check')[0])
    path = os.path.join(out, f'{tag}.json')
    res = json.load(open(path)) if os.path.exists(path) else dict(runs=[])
    if 'N' not in res:
        res['N'] = practised_and_reach(N, vocab, device, dev, s['T'], fresh, seed=seed)
        json.dump(res, open(path, 'w'), indent=1)
        log('N', res['N'])
    done = {(r['set'], r['method'], json.dumps(r['kw'], sort_keys=True)) for r in res['runs']}
    for set_name in sets:
        for name, kw in plan:
            if (set_name, name, json.dumps(kw, sort_keys=True)) in done:
                continue
            m, info = METHODS[name](N, recs[set_name], replay, vocab, device, n_w, **kw)
            r = dict(set=set_name, method=name, kw=kw, **practised_and_reach(m, vocab, device, dev, s['T'], fresh, seed=seed))
            res['runs'].append(r)
            json.dump(res, open(path, 'w'), indent=1)
            log(set_name, name, kw, r['practised'], r['dev_search'])
    return res


# ---------------------------------------------------------------- 6-seed confirm (marks: results/fastsleep/RESULTS-2026-10-06.md, "Confirm marks")
MEMORY_OLD = ('knn', dict(c=50.0, theta=0.9, cal=0.99, old=512))
B_GRID = [('ft', dict(lr=0.0003, visits=16)), ('ft', dict(lr=0.001, visits=16))]
_key = lambda kw: json.dumps(kw, sort_keys=True)


def dev_reach4(m, vocab, device, dev, T, n=32, seed=0):
    m.eval()
    smp = legal.raw_samples(m, dev, vocab, device, n=n, temperature=T, level=0, seed=seed)
    return fewshot.score_samples(dev, smp, ks=(4,))['reach4']


def confirm(ckpt, out, skills_train, skills_data, floors_path=None, device='cpu', seed=0):
    """One parent of the confirm, resumable: setup (keeps warm.pt and N_ss.pt for C2b) -> B = job 6's rule over B_GRID on PC (best DEV first
    try within 2 points of harm, then DEV reach@4) -> memory+old and B on W -> memory+old on R (placebo) -> old-parts check of both on W."""
    if not os.path.exists(os.path.join(out, 'setup.pt')):
        setup(ckpt, out, skills_train, skills_data, floors_path, device, seed)
    res = screen(out, skills_data, skills_train, B_GRID, device, seed, 'confirm', ('PC',))
    path = os.path.join(out, 'confirm.json')
    if 'B' not in res:
        pc = {_key(r['kw']): r for r in res['runs'] if r['set'] == 'PC' and r['method'] == 'ft'}
        ok = [kw for _, kw in B_GRID if pc[_key(kw)]['skills_harm_points'] <= 2] or [min((kw for _, kw in B_GRID), key=lambda kw: pc[_key(kw)]['skills_harm_points'])]
        best = max(pc[_key(kw)]['dev']['right'] for kw in ok)
        tied = [kw for kw in ok if pc[_key(kw)]['dev']['right'] == best]
        r4 = {}
        if len(tied) > 1:
            N, vocab, meta, s = load_setup(out, device)
            replay = sleep.load_replay(skills_train, None, seed)
            dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
            for kw in tied:
                m, _ = m_ft(N, s['records']['PC'], replay, vocab, device, len(s['records']['W']), **kw)
                r4[_key(kw)] = dev_reach4(m, vocab, device, dev, s['T'], seed=seed)
        kw = max(tied, key=lambda kw: r4.get(_key(kw), 0.0))
        res = json.load(open(path))
        res['B'] = dict(method='ft', kw=kw, within_harm=bool(pc[_key(kw)]['skills_harm_points'] <= 2), tie_reach4=r4)
        json.dump(res, open(path, 'w'), indent=1)
        log('B', res['B'])
    B = (res['B']['method'], res['B']['kw'])
    screen(out, skills_data, skills_train, [MEMORY_OLD, B], device, seed, 'confirm', ('W',))
    screen(out, skills_data, skills_train, [MEMORY_OLD], device, seed, 'confirm', ('R',))
    posteval(out, skills_train, [MEMORY_OLD, B], device, seed, 'confirm-old', ('W',))
    log('CONFIRM PARENT DONE', out)


def confirm_report(root):
    """Pool the parents under root/s* against the confirm marks. Mark 4 is reported as recall of stored programs (the old notes), not as parts
    kept in the weights (roadmap ruling 10-06)."""
    rows = []
    for d in sorted(os.path.join(root, x) for x in os.listdir(root) if x.startswith('s')):
        try:
            c, o = json.load(open(os.path.join(d, 'confirm.json'))), json.load(open(os.path.join(d, 'confirm-old.json')))
        except (OSError, ValueError):
            continue
        get = lambda st, m, kw: next((r for r in c['runs'] if r['set'] == st and r['method'] == m and _key(r['kw']) == _key(kw)), None)
        getp = lambda m, kw: next((r for r in o['runs'] if r['method'] == m and _key(r['kw']) == _key(kw)), None)
        mem, b, plc = get('W', *MEMORY_OLD), get('W', c['B']['method'], c['B']['kw']), get('R', *MEMORY_OLD)
        pm, pb = getp(*MEMORY_OLD), getp(c['B']['method'], c['B']['kw'])
        if not (mem and b and plc and pm and pb):
            continue
        rows.append(dict(parent=os.path.basename(d), B=c['B']['kw'], B_tflops=b['sleep_tflops'], B_gain=b['gain_points'], B_harm=b['skills_harm_points'],
                         M_tflops=mem['sleep_tflops'], M_gain=mem['gain_points'], M_harm=mem['skills_harm_points'], placebo_gain=plc['gain_points'],
                         recall_N=o['N']['practised']['reach32'], recall_M=pm['practised']['reach32'], recall_B=pb['practised']['reach32'],
                         reach4_N=o['N']['dev_search']['reach4'], reach4_M=pm['dev_search']['reach4'], reach4_B=pb['dev_search']['reach4']))
    n = len(rows)
    if not n:
        return dict(n=0)
    mean = lambda k: sum(r[k] for r in rows) / n
    marks = {'1 FLOPs <= B/10 on every parent': all(r['M_tflops'] <= r['B_tflops'] / 10 for r in rows),
             '2 pooled W gain >= 0.8 x B': mean('M_gain') >= 0.8 * mean('B_gain'),
             '3 harm <= 2 on every parent': all(r['M_harm'] <= 2 for r in rows),
             '4 recall of stored programs (practised reach@32) >= N on 5 of 6': sum(r['recall_M'] >= r['recall_N'] for r in rows) >= 5,
             'placebo (R) pooled gain <= +3': mean('placebo_gain') <= 3}
    wrong = mean('M_gain') < 0.5 * mean('B_gain') or sum(r['M_harm'] > 2 for r in rows) >= 2
    rep = dict(n=n, rows=rows, pooled=dict(M_gain=mean('M_gain'), B_gain=mean('B_gain'), ratio=mean('M_gain') / mean('B_gain') if mean('B_gain') else None,
               placebo_gain=mean('placebo_gain')), marks=marks, proved_wrong=wrong,
               verdict=('PROVED WRONG' if wrong else 'PASS' if (n >= 6 and all(marks.values())) else 'FAIL' if n >= 6 else f'incomplete ({n} of 6)'))
    json.dump(rep, open(os.path.join(root, 'REPORT.json'), 'w'), indent=1)
    return rep


def parse_plan(text):
    """'ft:lr=3e-4,visits=4;heads:epochs=30' -> [(name, kw)]"""
    out = []
    for part in text.split(';'):
        name, _, args = part.partition(':')
        kw = {}
        for a in filter(None, args.split(',')):
            k, v = a.split('=')
            kw[k] = (v == 'True') if v in ('True', 'False') else (int(v) if v.lstrip('-').isdigit() else float(v))
        out.append((name.strip(), kw))
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('cmd', choices=['setup', 'screen', 'posteval', 'confirm', 'report'])
    a.add_argument('--ckpt'); a.add_argument('--out', required=True); a.add_argument('--skills-train'); a.add_argument('--skills-data'); a.add_argument('--floors')
    a.add_argument('--plan', default='ft:lr=0.0003,visits=4'); a.add_argument('--tag', default='screen'); a.add_argument('--sets', default='PC,W')
    a.add_argument('--T', type=float); a.add_argument('--device', default='cpu'); a.add_argument('--seed', type=int, default=0)
    a = a.parse_args()
    if a.cmd == 'setup':
        setup(a.ckpt, a.out, a.skills_train, a.skills_data, a.floors, a.device, a.seed, T=a.T)
    elif a.cmd == 'confirm':
        confirm(a.ckpt, a.out, a.skills_train, a.skills_data, a.floors, a.device, a.seed)
    elif a.cmd == 'report':
        print(json.dumps(confirm_report(a.out), indent=1))
    elif a.cmd == 'posteval':
        posteval(a.out, a.skills_train, parse_plan(a.plan), a.device, a.seed, a.tag, tuple(a.sets.split(',')))
    else:
        screen(a.out, a.skills_data, a.skills_train, parse_plan(a.plan), a.device, a.seed, a.tag, tuple(a.sets.split(',')))
