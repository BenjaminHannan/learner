"""Consolidation sleep (roadmap: fast sleep without forgetting). Question: can the fast sleep (creative.rl.method.train: the model's own night, chain records,
execution replay, 80 visits at batch 1024) keep its C2 gain with less skills forgetting, when the C2 half of every batch is FRESH (a new prompt of each found
program on new inputs, never the same prompt twice) and the skills half is drawn WITHOUT repetition? Nothing here reads an answer key or DEV: the sleep and the
self-signals use only the day's questions (prompts), the model's own tries, and skills TRAIN rows. DEV is read only by `measure` (never fed back).

  python3 -m creative.consol run   --parent-dir ~/rl/parents/s200 --out DIR --arm rlc|fd|fdw|ro --updates U --seed S [--check-every 16] [--save-at 32,64,128]
  python3 -m creative.consol scale --parent-dir ~/rl/parents/s200 --out DIR --arm ARM

Arms: rlc = the research loop's data (finds + 3 fixed replays per find, reused), fd = a fresh dream per update row, fdw = fd with the skills half weighted
toward families whose held loss has risen (interference), ro = replay-only control (the record half is more skills rows: plain extra practice).
The target cache (custom_io.models.progparse._CACHE) is keyed by record id: every dream has a globally unique id."""
import argparse, copy, itertools, json, os, pickle, random, sys, time
from dataclasses import dataclass
import numpy as np
import torch
from creative import c2_stones, fastsleep as fs, fewshot, repair7d, rules_real as R, sampler, sleep
from creative import programs as P
from creative.harm_look import harm_measure, skills_hits
from creative.rl import method
from creative.rl.m import fast, replay, selfnight
from custom_io.data import Dataset, collate, load_rows, to_device
from custom_io.models import progparse as pp
from custom_io.train import lr_at

SKILLS_TRAIN = os.environ.get('RL_SKILLS_TRAIN', os.path.expanduser('~/work/data/train.jsonl'))
SKILLS_DATA = os.environ.get('RL_SKILLS_DATA', os.path.expanduser('~/work/data_big'))
log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---------------------------------------------------------------- the day: pool prompts, a held set
@dataclass
class DayCtx:
    """What selfnight.night needs of a ctx: seed, device, vocab and the day's questions as prompts only (id, prompt, nums; no answer, kind or params)."""
    seed: int
    device: str
    vocab: object
    pool: list


def split_pool(pool, seed, n_held=128):
    """-> (train_pool, held_pool): a seeded split of the day's questions, both in the pool's own order. The held questions never make a training record."""
    held = set(random.Random(f'pool-held|{seed}').sample(range(len(pool)), n_held))
    return [r for i, r in enumerate(pool) if i not in held], [r for i, r in enumerate(pool) if i in held]


def day_pool():
    """The C2 pool split as prompts only (the same rows eval_c2.Ctx hands a method)."""
    return [{'id': r['id'], 'prompt': r['prompt'], 'nums': r['nums']} for r in c2_stones._with_nums(R.load_split(fs.DATA, 'pool'))]


def make_day(seed, vocab, device='cpu', n_held=128, pool=None):
    """-> (DayCtx on the train part of the pool, held_pool)."""
    train, held = split_pool(day_pool() if pool is None else pool, seed, n_held)
    return DayCtx(seed, device, vocab, train), held


# ---------------------------------------------------------------- the data: finds, dreams, fixed replay
def finds(N, ctx):
    """creative.rl.method.train's data part on ctx.pool (the train part only): the model's own night W (selfnight.night) and the chain records C.
    -> (W + C, info)."""
    t0 = time.time()
    fast.prefill(N, ctx.pool)
    W, ni = selfnight.night(N, ctx)
    C = method.chain_records(W, ctx.pool)
    return W + C, dict(n_W=len(W), n_C=len(C), T=ni['T'], probe={str(k): v for k, v in ni['probe'].items()}, seconds=round(time.time() - t0, 1))


def _dreamers(recs):
    """[(record, Try, parsed source prompt)] for the records whose program and prompt can be replayed (as replay.replay_per_record skips the rest)."""
    out = []
    for r in recs:
        tf = P.train_form(fewshot.record_try(r))
        p0 = fewshot.parse(r['prompt'])
        if tf is not None and p0 is not None:
            out.append((r, P.Try.make(*tf), p0))
    return out


def _dream(r, t, p0, rng, inputs, lo, hi, tries=40):
    """One fresh prompt of record r's program on new inputs (replay.replay_per_record's acceptance checks for one replay, plus: not the source prompt). -> prompt or None."""
    for _ in range(tries):
        xs = rng.sample(inputs, len(p0['xs']) + 1)
        ys = [replay._value(t, x, p0['q_slot']) for x in xs]
        if None in ys or len(set(ys)) == 1 or min(ys) < lo or max(ys) > hi:
            continue
        n_ex = len(p0['xs'])
        nums = [v for x, y in zip(xs[:n_ex], ys[:n_ex]) for v in (x, y)] + [xs[n_ex]]
        prompt = replay.reprompt(r['prompt'], nums)
        if prompt != r['prompt'] and fewshot.structure(fewshot.parse(prompt), t)[0]:
            return prompt
    return None


def dream_stream(recs, seed, inputs, lo, hi):
    """Infinite generator of FRESH records: the records in a seeded shuffled order (reshuffled every pass), one new prompt of the record's program on fresh
    inputs each (a record with no acceptable prompt in 40 tries is skipped for that pass). Ids 'D:...' carry a counter that never repeats."""
    rng = random.Random(f'dream|{seed}')
    dr = _dreamers(recs)
    count = 0
    while True:
        order = list(range(len(dr)))
        rng.shuffle(order)
        made = 0
        for i in order:
            r, t, p0 = dr[i]
            prompt = _dream(r, t, p0, rng, inputs, lo, hi)
            if prompt is None:
                continue
            yield fewshot._record({'id': r['id'], 'prompt': prompt}, t, 'D', count)
            count += 1
            made += 1
        if not made:
            raise RuntimeError('dream_stream: no record could make a fresh prompt')


def fixed_replay(recs, seed, inputs, lo, hi, k=3):
    """The research loop's data: the records plus k fixed replays of each (replay.replay_per_record)."""
    return recs + replay.replay_per_record(recs, k, seed, inputs, lo, hi)


# ---------------------------------------------------------------- the sleep
class _Replay:
    """Skills rows drawn WITHOUT repetition: one seeded shuffle consumed in order, or (with weights) one seeded shuffled queue per family, each consumed in order.
    Raises when a queue runs out."""

    def __init__(self, rows, seed):
        self.rows, self.seed = rows, seed
        self.order = list(range(len(rows)))
        random.Random(f'replay|{seed}').shuffle(self.order)
        self.pos, self.queues, self.fpos = 0, None, {}

    def draw(self, n, weights=None):
        if weights is None:
            if self.pos + n > len(self.order):
                raise ValueError(f'replay rows exhausted ({len(self.rows)} rows, {self.pos + n} wanted)')
            self.pos += n
            return [self.rows[i] for i in self.order[self.pos - n:self.pos]]
        if self.queues is None:
            self.queues = {}
            for i, r in enumerate(self.rows):
                self.queues.setdefault(r['family'], []).append(i)
            for f, q in self.queues.items():
                random.Random(f'replay|{self.seed}|{f}').shuffle(q)
            self.fpos = {f: 0 for f in self.queues}
        out = []
        for f, k in quota({f: weights.get(f, 1.0) for f in sorted(self.queues)}, n).items():
            if self.fpos[f] + k > len(self.queues[f]):
                raise ValueError(f'replay rows exhausted in family {f} ({len(self.queues[f])} rows)')
            out += [self.rows[i] for i in self.queues[f][self.fpos[f]:self.fpos[f] + k]]
            self.fpos[f] += k
        return out


def quota(weights, n):
    """{family: count} summing to exactly n, proportional to the weights (largest-remainder rounding; ties go to the family name)."""
    tot = sum(weights.values())
    raw = {f: n * w / tot for f, w in weights.items()}
    out = {f: int(x) for f, x in raw.items()}
    for f in sorted(raw, key=lambda f: (-(raw[f] - out[f]), f))[:n - sum(out.values())]:
        out[f] += 1
    return out


def sleep_mixed(model, rec_source, replay_rows, vocab, updates, batch=1024, lr=1e-3, warmup=None, seed=0, device='cpu', check_every=0, check_fn=None,
                replay_weight_fn=None, log=None, save_at=(), save_fn=None):
    """sleep.sleep's fresh AdamW, lr schedule and clip, with each update half record rows, half skills replay rows (batch // 2 each).
    rec_source: a list (rows drawn with sleep._order: balanced reuse) or an iterator (dream_stream: the next batch // 2 rows). replay_rows: drawn without
    repetition (raises when used up). replay_weight_fn(model, step) -> {family: weight}, called at step 0 and every check_every steps (model in eval mode): the replay
    half is then split over families by those weights. check_fn(model, step) after updates check_every, 2 * check_every, ... and the last (eval mode);
    returning 'stop' ends the sleep. save_fn(model, step) after the updates in save_at. -> dict(updates_done, rows_seen, record_visits, loss, checks, weights)."""
    half = batch // 2
    warmup = min(20, max(1, updates // 5)) if warmup is None else warmup
    rng = random.Random(seed)
    torch.manual_seed(seed)
    if isinstance(rec_source, (list, tuple)):
        if not rec_source or len({r['id'] for r in rec_source}) != len(rec_source):
            raise ValueError('records must be non-empty with unique ids (the target cache is keyed by id)')
        order = sleep._order(len(rec_source), updates * half, rng)
        next_records = lambda s: [rec_source[i] for i in order[s * half:(s + 1) * half]]
    else:
        def next_records(s):
            rs = list(itertools.islice(rec_source, half))
            if len(rs) < half:
                raise ValueError('record stream ran dry')
            return rs
    if replay_weight_fn is None and updates * half > len(replay_rows):
        raise ValueError(f'{updates} updates draw {updates * half} replay rows without repetition from {len(replay_rows)}')
    rep = _Replay(replay_rows, seed)
    emb = {id(m.weight) for m in model.modules() if isinstance(m, torch.nn.Embedding)}
    decay = [p for p in model.parameters() if p.requires_grad and p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in model.parameters() if p.requires_grad and (p.ndim < 2 or id(p) in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': no_decay, 'weight_decay': 0.0}],
                            lr=lr, betas=(0.9, 0.95), fused=torch.device(device).type == 'cuda')
    visits, losses, checks, wlog, weights, done = {}, [], [], [], None, 0
    model.train()
    for step in range(updates):
        if replay_weight_fn and (step == 0 or (check_every and step % check_every == 0)):
            model.eval()
            weights = replay_weight_fn(model, step)
            model.train()
            wlog.append((step, dict(weights)))
        recs = next_records(step)
        rows = recs + rep.draw(half, weights)
        for r in recs:
            visits[r['id']] = visits.get(r['id'], 0) + 1
        fast.prefill(model, rows)
        ds = Dataset(rows, vocab, strict=False)
        b = to_device(collate([ds[i] for i in range(len(rows))]), device)
        for g in opt.param_groups:
            g['lr'] = lr_at(step, updates, warmup, lr)
        out = model.loss(b)
        loss = out[0] if isinstance(out, tuple) else out
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(float(loss.detach()))
        done = step + 1
        if log and done % 10 == 0:
            log(dict(event='sleep', step=done, loss=round(float(np.mean(losses[-10:])), 4)))
        if save_fn and done in save_at:
            save_fn(model, done)
        if check_fn and check_every > 0 and (done % check_every == 0 or done == updates):
            model.eval()
            res = check_fn(model, done)
            model.train()
            checks.append(dict(step=done, result=res))
            if res == 'stop':
                break
    v = list(visits.values())
    return dict(updates_done=done, rows_seen=done * batch, loss=losses, checks=checks, weights=wlog,
                record_visits=dict(max=max(v) if v else 0, mean=float(np.mean(v)) if v else 0.0, n=len(v)))


# ---------------------------------------------------------------- self-signals (no answers, no DEV)
def held_fits(model, held_pool, vocab, device='cpu'):
    """Greedy first try on held practice questions: the fraction whose program fits every example in the prompt. Reads only id and prompt (the Dataset's
    answer slot gets a placeholder, as selfnight does)."""
    rows = [{'id': r['id'], 'prompt': r['prompt'], 'answer': '0'} for r in held_pool]
    was = model.training
    model.eval()
    gt = sampler.greedy_tries(model, rows, vocab, device, level=0)
    model.train(was)
    return sum(fewshot.verdict(fewshot.parse(r['prompt']), t.t)[0] == 'accept' for r, t in zip(rows, gt)) / max(len(rows), 1)


def selfcheck(model, held_rows, device='cpu'):
    """Greedy exact on held skills TRAIN rows (repair7d.held_split's held). -> dict(hits [0/1 per row], in_dist %, by_family {family: %})."""
    was = model.training
    model.eval()
    h = repair7d.held_hits(model, held_rows, device)
    model.train(was)
    fam = {}
    for r, x in zip(held_rows, h):
        fam.setdefault(r['family'], []).append(x)
    return dict(hits=h, in_dist=100 * sum(h) / max(len(h), 1), by_family={f: 100 * sum(v) / len(v) for f, v in sorted(fam.items())})


@torch.no_grad()
def family_loss(model, rows, vocab, device='cpu', batch=128):
    """{family: mean model.loss over that family's rows} (eval mode, no grad; the mode is restored)."""
    was = model.training
    model.eval()
    fam = {}
    for r in rows:
        fam.setdefault(r['family'], []).append(r)
    out = {}
    for f, rs in sorted(fam.items()):
        tot = 0.0
        for s in range(0, len(rs), batch):
            ch = rs[s:s + batch]
            ds = Dataset(ch, vocab, strict=False)
            o = model.loss(to_device(collate([ds[i] for i in range(len(ch))]), device))
            tot += float(o[0] if isinstance(o, tuple) else o) * len(ch)
        out[f] = tot / len(rs)
    model.train(was)
    return out


def interference_weights(held_rows, vocab, device, start_losses, floor=0.05):
    """-> fn(model, step) = {family: w}, w_f = max(loss_f(now) / max(loss_f(start), floor), 1) ** 2, normalised to sum 1: replay leans on the families that have got
    worse. Most families' loss is ~1e-5 (some below 0), so the floor (the spec's 1e-6 makes any wobble a 1e4-fold ratio) keeps those from taking all the weight."""
    def fn(model, step):
        now = family_loss(model, held_rows, vocab, device)
        w = {f: max(now[f] / max(start_losses[f], floor), 1.0) ** 2 for f in now}
        tot = sum(w.values())
        return {f: v / tot for f, v in w.items()}
    return fn


# ---------------------------------------------------------------- weight-space scaling
def scaled(N, W, a):
    """A copy of N with state N + a * (W - N) for float tensors (torch.lerp: a = 0 is N and a = 1 is W exactly); other buffers are W's."""
    m = copy.deepcopy(N)
    sn, sw = N.state_dict(), W.state_dict()
    m.load_state_dict({k: torch.lerp(v, sw[k], a) if v.is_floating_point() else sw[k].clone() for k, v in sn.items()})
    return m


def pick_scale(N, W, held_pool, held_rows, vocab, device, grid=(0.25, 0.5, 0.75, 1.0), max_drop=1.0):
    """For each a in grid: held_fits and selfcheck in_dist of scaled(N, W, a). Allowed = in_dist at most max_drop points below N's; pick the allowed a with the
    largest held_fits (ties -> smaller a); none allowed -> the a with the smallest drop. -> (a, table): table[0] is N itself (a = 0, not a candidate)."""
    def row(a, m):
        return dict(a=a, held_fits=held_fits(m, held_pool, vocab, device), in_dist=selfcheck(m, held_rows, device)['in_dist'])
    table = [row(0.0, N)]
    for a in grid:
        table.append(row(a, scaled(N, W, a)))
    for t in table:
        t['drop'] = table[0]['in_dist'] - t['in_dist']
        t['allowed'] = t['drop'] <= max_drop
    cand = table[1:]
    ok = [t for t in cand if t['allowed']]
    best = max(ok, key=lambda t: (t['held_fits'], -t['a'])) if ok else min(cand, key=lambda t: (t['drop'], t['a']))
    return best['a'], table


# ---------------------------------------------------------------- measures (never used by the sleep)
def measure(model, vocab, device, skills_data):
    """C2 DEV greedy first try (per-question right list kept) and skills DEV hits (per-row). For reporting only."""
    was = model.training
    dev = c2_stones._with_nums(R.load_split(fs.DATA, 'dev'))
    d, per = fs.dev_eval(model, dev, vocab, device)
    rows, hits, p5, idd = skills_hits(model, skills_data, device)
    model.train(was)
    return dict(c2=dict(right=100 * d['right'], fits=100 * d['fits'], by_kind={k: 100 * v for k, v in d['by_kind'].items()}, per_q_right=[int(x) for x in per]),
                skills=dict(in_dist=idd, pooled5=p5, hits=hits, ids=[r['id'] for r in rows], families=[r['family'] for r in rows]))


# ---------------------------------------------------------------- CLI
def _dump(obj, path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    json.dump(obj, open(path + '.tmp', 'w'), indent=1)
    os.replace(path + '.tmp', path)


def _cached(path, key, fn):
    """fn() cached as JSON at path while the stored key matches."""
    if os.path.exists(path):
        d = json.load(open(path))
        if d.get('key') == key:
            return d['value']
    v = fn()
    _dump(dict(key=key, value=v), path)
    return v


def _cached_finds(N, ctx, out, parent_dir, n_held):
    """finds(N, ctx) cached in OUT/finds.pkl on parent + seed (+ target-cache entries); arms on the same parent share the night."""
    path = os.path.join(out, 'finds.pkl')
    key = dict(parent=os.path.abspath(parent_dir), seed=ctx.seed, n_held=n_held)
    if os.path.exists(path):
        d = pickle.load(open(path, 'rb'))
        if d['key'] == key:
            pp._CACHE.update(d['cache'])
            return d['records'], d['info']
    recs, info = finds(N, ctx)
    pickle.dump(dict(key=key, records=recs, info=info, cache={r['id']: pp._CACHE[r['id']] for r in recs}), open(path, 'wb'))
    return recs, info


def _setup(a):
    """-> N, vocab, meta, held_rows, rest, day ctx, held_pool (shared by run and scale)."""
    N, vocab, meta, _ = fs.load_setup(os.path.expanduser(a.parent_dir), a.device)
    held_rows, rest = repair7d.held_split(load_rows(os.path.expanduser(a.skills_train)), 100, a.seed)
    ctx, held_pool = make_day(a.seed, vocab, a.device, a.n_held)
    return N, vocab, meta, held_rows, [r for f in sorted(rest) for r in rest[f]], ctx, held_pool


def _save(m, meta, vocab, path):
    sleep.save_parent(m, meta['name'], meta['cfg'], vocab, path, step=(meta.get('step') or 0), warmup=True)


def _n_ref(a, N, vocab, held_pool, held_rows, out):
    """N's measure (cached in OUT/N_measure.json) and N's self-signals (OUT/N_self.json, per seed)."""
    pd = os.path.abspath(os.path.expanduser(a.parent_dir))
    nm = _cached(os.path.join(out, 'N_measure.json'), pd, lambda: measure(N, vocab, a.device, os.path.expanduser(a.skills_data)))

    def selfn():
        sc = selfcheck(N, held_rows, a.device)
        return dict(held_fits=held_fits(N, held_pool, vocab, a.device), in_dist=sc['in_dist'], by_family=sc['by_family'], family_loss=family_loss(N, held_rows, vocab, a.device))
    return nm, _cached(os.path.join(out, f'N_self_s{a.seed}.json'), [pd, a.n_held], selfn)


def _harm(nm, lm):
    rows = [{'family': f} for f in lm['skills']['families']]
    assert nm['skills']['ids'] == lm['skills']['ids']
    return harm_measure(nm['skills']['hits'], lm['skills']['hits'], rows)


def cmd_run(a):
    torch.set_num_threads(a.threads)
    sys.setrecursionlimit(10000)
    out = os.path.expanduser(a.out)
    adir = os.path.join(out, a.arm)
    os.makedirs(adir, exist_ok=True)
    res, secs = dict(args=vars(a), seconds={}), {}
    rp = os.path.join(adir, 'result.json')
    save = lambda: _dump(res, rp)
    t0 = time.time()
    N, vocab, meta, held_rows, rest, ctx, held_pool = _setup(a)
    N.eval()
    half = a.batch // 2
    res['seconds']['load'] = round(time.time() - t0, 1)
    nm, nself = _n_ref(a, N, vocab, held_pool, held_rows, out)
    res.update(N_self=dict((k, v) for k, v in nself.items() if k != 'family_loss'), N_measure=dict(c2_right=nm['c2']['right'], in_dist=nm['skills']['in_dist'], pooled5=nm['skills']['pooled5']))
    res['seconds']['N_ref'] = round(time.time() - t0, 1)
    save()
    rng = random.Random(f'consol|{a.seed}')
    rec_source, wfn = None, None
    if a.arm == 'ro':
        mix = list(rest)
        rng.shuffle(mix)
        replay_rows, rec_source = mix[:a.updates * half], mix[a.updates * half:]
    else:
        replay_rows = rest
        t1 = time.time()
        recs, res['finds'] = _cached_finds(N, ctx, out, a.parent_dir, a.n_held)
        res['seconds']['finds'] = round(time.time() - t1, 1)
        save()
        inputs, lo, hi = replay.experience(ctx.pool)
        if a.arm == 'rlc':
            rec_source = fixed_replay(recs, a.seed, inputs, lo, hi)
        else:
            rec_source = dream_stream(recs, a.seed, inputs, lo, hi)
        if a.arm == 'fdw':
            wfn = interference_weights(held_rows, vocab, a.device, nself['family_loss'])
    checks = []
    state = dict(best=-1.0, stale=0, sd=None)

    def check_fn(m, step):
        t = time.time()
        sc = selfcheck(m, held_rows, a.device)
        hf = held_fits(m, held_pool, vocab, a.device)
        checks.append(dict(step=step, held_fits=hf, in_dist=sc['in_dist'], by_family=sc['by_family'], seconds=round(time.time() - t, 1)))
        res['checks'] = checks
        save()
        log('check', step, 'held_fits', round(hf, 4), 'in_dist', round(sc['in_dist'], 2))
        if not a.self_stop:
            return None
        if hf > state['best']:
            state.update(best=hf, stale=0, sd=copy.deepcopy(m.state_dict()))
        else:
            state['stale'] += 1
        return 'stop' if state['stale'] >= 2 else None

    saves = {int(s) for s in a.save_at.split(',') if s}
    L = copy.deepcopy(N)
    t1 = time.time()
    info = sleep_mixed(L, rec_source, replay_rows, vocab, a.updates, a.batch, a.lr, None, a.seed, a.device, a.check_every,
                       check_fn if a.check_every > 0 else None, wfn, log, saves, lambda m, s: _save(m, meta, vocab, os.path.join(adir, f'learner_s{s}.pt')))
    if a.self_stop and state['sd'] is not None:
        L.load_state_dict(state['sd'])
        info['kept_best_held_fits'] = state['best']
    res['sleep'] = info
    res['seconds']['sleep'] = round(time.time() - t1, 1)
    L.eval()
    _save(L, meta, vocab, os.path.join(adir, 'learner.pt'))
    save()
    t1 = time.time()
    lm = measure(L, vocab, a.device, os.path.expanduser(a.skills_data))
    res['learner'] = dict(c2_right=lm['c2']['right'], c2_fits=lm['c2']['fits'], by_kind=lm['c2']['by_kind'], per_q_right=lm['c2']['per_q_right'],
                          in_dist=lm['skills']['in_dist'], pooled5=lm['skills']['pooled5'])
    _dump(dict(ids=lm['skills']['ids'], families=lm['skills']['families'], N=nm['skills']['hits'], learner=lm['skills']['hits']), os.path.join(adir, 'hits.json'))
    res['harm_vs_N'] = _harm(nm, lm)
    res['seconds']['measure'] = round(time.time() - t1, 1)
    save()
    log('done', a.arm, 'c2', round(lm['c2']['right'], 2), 'N', round(nm['c2']['right'], 2), 'in_dist', round(lm['skills']['in_dist'], 2), 'N', round(nm['skills']['in_dist'], 2))
    return res


def cmd_scale(a):
    torch.set_num_threads(a.threads)
    out = os.path.expanduser(a.out)
    adir = os.path.join(out, a.arm)
    prev = json.load(open(os.path.join(adir, 'result.json')))['args']
    for k in ('seed', 'n_held', 'skills_train', 'skills_data'):
        setattr(a, k, prev[k])
    N, vocab, meta, held_rows, rest, ctx, held_pool = _setup(a)
    N.eval()
    W, _, _ = sleep.load_parent(os.path.join(adir, 'learner.pt'), a.device)
    W.eval()
    t0 = time.time()
    s, table = pick_scale(N, W, held_pool, held_rows, vocab, a.device, tuple(float(x) for x in a.grid.split(',')), a.max_drop)
    m = scaled(N, W, s)
    _save(m, meta, vocab, os.path.join(adir, 'learner_scaled.pt'))
    nm, _ = _n_ref(a, N, vocab, held_pool, held_rows, out)
    lm = measure(m, vocab, a.device, os.path.expanduser(a.skills_data))
    res = dict(a=s, table=table, grid=a.grid, max_drop=a.max_drop, c2_right=lm['c2']['right'], by_kind=lm['c2']['by_kind'], per_q_right=lm['c2']['per_q_right'],
               in_dist=lm['skills']['in_dist'], pooled5=lm['skills']['pooled5'], harm_vs_N=_harm(nm, lm), seconds=round(time.time() - t0, 1))
    _dump(res, os.path.join(adir, 'scale.json'))
    _dump(dict(ids=lm['skills']['ids'], families=lm['skills']['families'], N=nm['skills']['hits'], learner=lm['skills']['hits']), os.path.join(adir, 'hits_scaled.json'))
    log('scale', s, 'c2', round(lm['c2']['right'], 2), 'in_dist', round(lm['skills']['in_dist'], 2))
    return res


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'scale'):
        s = sub.add_parser(name)
        s.add_argument('--parent-dir', required=True); s.add_argument('--out', required=True); s.add_argument('--arm', required=True, choices=('rlc', 'fd', 'fdw', 'ro'))
        s.add_argument('--seed', type=int, default=0); s.add_argument('--n-held', type=int, default=128)
        s.add_argument('--skills-train', default=SKILLS_TRAIN); s.add_argument('--skills-data', default=SKILLS_DATA)
        s.add_argument('--threads', type=int, default=4); s.add_argument('--device', default='cpu')
        if name == 'run':
            s.add_argument('--updates', type=int, required=True); s.add_argument('--batch', type=int, default=1024); s.add_argument('--lr', type=float, default=1e-3)
            s.add_argument('--check-every', type=int, default=16); s.add_argument('--save-at', default=''); s.add_argument('--self-stop', action='store_true')
        else:
            s.add_argument('--grid', default='0.25,0.5,0.75,1.0'); s.add_argument('--max-drop', type=float, default=1.0)
    a = p.parse_args(argv)
    return cmd_run(a) if a.cmd == 'run' else cmd_scale(a)


if __name__ == '__main__':
    main()
