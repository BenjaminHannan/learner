"""CB-0 (port of three proven B2-lineage pieces onto the B3 group 2 model, class B3G2 in models/b3g2.py): the Gemma input cache, the stuck-first search, and the SCM2 night.
Sources (read-only, branch claude/project-thread-2kevpk): creative/sleep7d.py (search, day_f, w_records), creative/night7d.py (sleep_sc with select=True, _sc_night),
creative/sleep.py (_order, check_visits). Self-contained: only custom_io, torch and the standard library. Draws only from torch.Generator(seed) (sampling), random.Random(seed ...)
(choices, picks), torch.manual_seed(seed) (the night's training draws); scoring is isolated (see row_losses).

THE CHECKER. `check(row, trace) -> bool` (does this try fit the question's OWN worked examples) is supplied by the caller and is a REQUIRED argument of day / cycle: there is no default,
so nothing here can fall back to reading the answer key. A trace is the dict ST1 uses: dict(calls=[(call text, reply)], answer=str).

1. THE GEMMA INPUT CACHE. B3 with eg_embed reads every question through models/eg.FrozenEG.encode, which memoises only the LAST call, so every try and every night recomputes Gemma.
eg_cache(model, max_items=20000) is a context manager that wraps that model's encoder (model._eg[0].encode, and encode_texts, the tool-reply encoder read like the question under Ben's rule 1, each with its own per-text store; patched on the instance, restored on exit) with a cache keyed per PROMPT (and device):
the H rows of the prompt (one per char, or per byte for ByteVocab, exactly as encode returns them, zero past the prompt) and its pooled vector. Only the missing prompts are computed, each ONE
PROMPT AT A TIME (batch of one, T = the prompt's own length), so batch composition and padding never enter a cached value; the batch result is stitched in encode's shape, dtype and device
(H [B, T, 768] zero-padded / truncated to T, pooled [B, 768]; H is None when chars=False). TOLERANCE (disclosed): a value computed alone can differ from the one encode would give inside a
padded batch by float rounding only (attention-masked padding), never by content; with the cache on, a prompt's value is always the batch-of-one value, whatever the batch. The store lives on
the encoder object (so it survives the context, and is shared by deepcopies of the model, which share the encoder), is least-recently-used bounded by max_items prompts, and is cleared by
clear_eg_cache(model). It holds tensors on the encoder's device. A model without eg_embed (no _eg) is untouched. day, night and row_losses use it internally.
There is NO creative adapter in this module (dropped by the owners): every try is plain sampling.

2. THE STUCK TEST AND STUCK-FIRST SEARCH (day_f). day(model, rows, make_batch, check, seed, T=1.0, n1=32, n2=480, batch_size=64): greedy first try
(sample_traces(batch, 0.0, gen); temperature 0 = argmax in ByteWriter.greedy); greedy_fit[i] = check(row, try); stuck = rows whose greedy try fails. Pass 1: n1 sampled tries per row,
torch.Generator().manual_seed(seed). Pass 2: n2 more tries, Generator seed + 1000, only for rows with no fitting try in pass 1. All plain sampling. Model in eval mode, no grad, the previous train / eval mode restored. T = 1.0 DISCLOSED: B2's T_POOL 3.0 was a temperature for its op / slot pointer heads; B3 samples bytes and ST1 uses
1.0; it is a parameter, not tuned. Rows go in chunks of batch_size; within a chunk each try is one sample_traces call (order of generator use: chunk, then try).

3. RECORDS (w_records). records(rows, day_result, seed, per_cap=2): at most per_cap DISTINCT fitting tries per row (distinct = same tuple of call texts and same answer.strip(); the first draw of
each is kept), chosen with random.Random(seed) when more than per_cap (random.sample, kept in draw order). Record id = f'{row id}|{k}'. Also returns the record count per kind (family or kind).

4. THE SCM2 NIGHT (sleep_sc with select=True, _sc_night). night(model, recs, replay_rows, make_batch, ...) trains a DEEP COPY of the model (the input is untouched; objects in model._eg, the frozen
Gemma, are shared, not copied) with a fresh AdamW (betas (0.9, 0.95); weight decay 0.1 on params with ndim >= 2 that are not nn.Embedding weights, none otherwise; lr custom_io.train.lr_at,
warmup 20; grad-norm clip 1.0). updates = visits * len(recs) // 32 unless given. Each update: 32 record slots (balanced epoch-wise shuffles `_order`, random.Random(seed)) and 32 replay slots; with
warm_rows the replay half is split evenly between replay_rows and warm_rows (sleep_sc's replay_extra); rng use as sleep_sc: rec_order, rep_order, ext_order from the one rng; torch.manual_seed(seed).
MODEL-PICKED REPLAY: at every update step >= every with step % every == 0, n_draw fresh replay rows (random.Random(seed + 5000 + step).sample) are scored under the current model and under a FROZEN deepcopy
taken before the night; the n_pick with the largest rise (now - then) are the replay slots for the next `every` updates in the order _order(len(picked), every * k, random.Random(seed + 6000 + step))
(k = replay slots from replay_rows per update); before the first pick they come from rep_order. COST (disclosed): each round = 2 * n_draw single-row forward passes (one per row per model).
PER-ROW LOSS: B3G2._loss returns a batch scalar and draws randomness (torch.randint for KS, the schedule in plan()); row_losses scores a batch of ONE row each, eval mode, no grad, inside
torch.random.fork_rng with torch.manual_seed(seed + i) per row, and snapshots / restores every model-held python / numpy RNG (random.Random, numpy RandomState / Generator found on any module;
for B3G2 these are _gap_rng and _drill_rng, which in eval mode are not drawn anyway) plus the global python and numpy states: the current and the frozen model see identical draws for the same
row, and scoring does not change the training run's random streams. Not restored (cosmetic): the model's counters (trace_stats, plan_stats, ...), the gold cache, capcount's global counters.
LOSS PER UPDATE (disclosed: B2 used one mean over one joint batch; B3 needs two calls): lt = model.trace_loss(make_batch(record rows), record traces); lo = model.loss(make_batch(replay rows));
loss = (half / batch) * lt + ((batch - half) / batch) * lo. Visits: counted per record id; asserted <= ceil(updates * half / len(recs)).

FIXED CONSTANTS (the proven recipe, not tuned): lr 3e-4, 32 visits per record, every 32 updates pick the 256 of 1,024 fresh replay rows whose loss rose most, 32 + 480 tries, per_cap 2.

5. cycle(...) = day -> records(seed + 1) -> night(seed): one day and night; two calls = SCM2's two nights."""
import collections, contextlib, copy, math, random, time
import numpy as np
import torch
import torch.nn as nn
from custom_io.train import lr_at

LR, VISITS, EVERY, N_DRAW, N_PICK = 3e-4, 32, 32, 1024, 256         # the SCM2 recipe
N1, N2, PER_CAP, T_SAMPLE = 32, 480, 2, 1.0


def kind_of(row):
    return row.get('family') or row.get('kind') or '?'


# ---------------------------------------------------------------- 1. the Gemma input cache
class _EGStore:
    """prompt -> (H row [n, 768], pooled [768]) per device, least recently used, at most max_items."""

    def __init__(self, orig, max_items, orig_texts=None):
        self.orig, self.orig_texts, self.max_items, self.d = orig, orig_texts, max_items, collections.OrderedDict()
        self.t = collections.OrderedDict()                                        # text -> H row [n, 768] (the reply encoder, FrozenEG.encode_texts)
        self.misses = self.hits = 0

    def row(self, eg, prompt, device):
        key = (prompt, str(device))
        v = self.d.get(key)
        if v is not None:
            self.d.move_to_end(key)
            self.hits += 1
            return v
        self.misses += 1
        n = max(int(len(eg.align(prompt)[1])), 1)                                  # chars (bytes for ByteVocab): the prompt's own length
        H, pooled = self.orig([prompt], n, device)
        v = self.d[key] = (H[0], pooled[0])
        while len(self.d) > self.max_items:
            self.d.popitem(last=False)
        return v

    def text_row(self, eg, text, device):
        key = (text, str(device))
        v = self.t.get(key)
        if v is not None:
            self.t.move_to_end(key)
            self.hits += 1
            return v
        self.misses += 1
        n = max(int(len(eg.align(text)[1])), 1)
        v = self.t[key] = self.orig_texts([text], n, device)[0]
        while len(self.t) > self.max_items:
            self.t.popitem(last=False)
        return v

    def encode_texts(self, eg, texts, T, device):
        rows = [self.text_row(eg, x, device) for x in texts]
        H = rows[0].new_zeros(len(rows), T, rows[0].shape[-1])
        for b, h in enumerate(rows):
            n = min(h.shape[0], T)
            H[b, :n] = h[:n]
        return H

    def encode(self, eg, prompts, T, device, chars=True):
        rows = [self.row(eg, p, device) for p in prompts]
        pooled = torch.stack([r[1] for r in rows])
        if not chars:
            return None, pooled
        H = rows[0][0].new_zeros(len(rows), T, rows[0][0].shape[-1])
        for b, (h, _) in enumerate(rows):
            n = min(h.shape[0], T)
            H[b, :n] = h[:n]
        return H, pooled


@contextlib.contextmanager
def eg_cache(model, max_items=20000):
    """Cache the model's Gemma encoder per prompt for the duration of the block (see the module docstring). A model without _eg is untouched; nesting reuses the open cache."""
    egs = list(getattr(model, '_eg', None) or [])
    if not egs:
        yield None
        return
    eg = egs[0]
    if 'encode' in vars(eg) and hasattr(eg, '_cb0_store'):
        yield eg._cb0_store
        return
    has_t = hasattr(eg, 'encode_texts')
    store = getattr(eg, '_cb0_store', None) or _EGStore(eg.encode, max_items, eg.encode_texts if has_t else None)
    store.max_items = max_items
    for d in (store.d, store.t):
        while len(d) > max_items:
            d.popitem(last=False)
    eg._cb0_store = store
    eg.encode = lambda prompts, T, device, chars=True: store.encode(eg, prompts, T, device, chars)
    if has_t:
        eg.encode_texts = lambda texts, T, device: store.encode_texts(eg, texts, T, device)
    try:
        yield store
    finally:
        del eg.encode                     # back to the class method; the store stays on the encoder
        if has_t:
            del eg.encode_texts


def clear_eg_cache(model):
    for eg in getattr(model, '_eg', None) or []:
        if hasattr(eg, '_cb0_store'):
            eg._cb0_store.d.clear()
            eg._cb0_store.t.clear()


# ---------------------------------------------------------------- 2. the stuck test and the stuck-first search
def _sample(model, rows, make_batch, n, T, seed, batch_size):
    """n sampled tries per row -> [list per row, sampling order]. One Generator(seed); chunks of batch_size rows; within a chunk one sample_traces call per try."""
    gen = torch.Generator().manual_seed(seed)
    out = [[] for _ in rows]
    for a in range(0, len(rows), batch_size):
        chunk = rows[a:a + batch_size]
        for _ in range(n):
            ts = model.sample_traces(make_batch(chunk), T, gen)
            assert len(ts) == len(chunk), (len(ts), len(chunk))
            for j, t in enumerate(ts):
                out[a + j].append(t)
    return out


def day(model, rows, make_batch, check, seed, T=T_SAMPLE, n1=N1, n2=N2, batch_size=64):
    """day_f on a B3G2: greedy try, pass 1 (n1 tries, seed), pass 2 (n2 tries, seed + 1000, only rows with no pass-1 fit); plain sampling.
    -> dict(greedy_fit [bool per row], tries [list per row, sampling order], fit [bool per try, per row], fit1 [pass 1 has a fit], fit_final, drawn=dict(greedy, pass1, pass2, pass2_rows))."""
    rows = list(rows)
    was = model.training
    model.eval()
    try:
        with torch.no_grad(), eg_cache(model):
            gen, gt = torch.Generator().manual_seed(seed), []
            for a in range(0, len(rows), batch_size):
                ts = model.sample_traces(make_batch(rows[a:a + batch_size]), 0.0, gen)
                assert len(ts) == len(rows[a:a + batch_size])
                gt += ts
            gf = [bool(check(r, t)) for r, t in zip(rows, gt)]
            t1 = _sample(model, rows, make_batch, n1, T, seed, batch_size)
            tries = [list(t) for t in t1]
            fit = [[bool(check(r, x)) for x in t] for r, t in zip(rows, tries)]
            fit1 = [any(f) for f in fit]
            more = [i for i, f in enumerate(fit1) if not f]
            if more:
                t2 = _sample(model, [rows[i] for i in more], make_batch, n2, T, seed + 1000, batch_size)
                for i, t in zip(more, t2):
                    tries[i] += t
                    fit[i] += [bool(check(rows[i], x)) for x in t]
    finally:
        model.train(was)
    return dict(greedy_fit=gf, tries=tries, fit=fit, fit1=fit1, fit_final=[any(f) for f in fit],
                drawn=dict(greedy=len(rows), pass1=n1 * len(rows), pass2=n2 * len(more), pass2_rows=len(more)))


# ---------------------------------------------------------------- 3. records
def _distinct_key(t):
    return (tuple(c for c, _ in t['calls']), str(t['answer']).strip())


def records(rows, day_result, seed, per_cap=PER_CAP):
    """-> (recs [dict(id=f'{row id}|{k}', row, trace)], counts per kind). At most per_cap distinct fitting tries per row (first draw of each kept; random.Random(seed).sample when more)."""
    rng, out, counts = random.Random(seed), [], {}
    for row, tr, ft in zip(rows, day_result['tries'], day_result['fit']):
        seen, uniq = set(), []
        for t, f in zip(tr, ft):
            if not f:
                continue
            k = _distinct_key(t)
            if k not in seen:
                seen.add(k)
                uniq.append(t)
        if len(uniq) > per_cap:
            uniq = [uniq[i] for i in sorted(rng.sample(range(len(uniq)), per_cap))]
        for k, t in enumerate(uniq):
            out.append(dict(id=f"{row['id']}|{k}", row=row, trace=t))
            counts[kind_of(row)] = counts.get(kind_of(row), 0) + 1
    return out, counts


# ---------------------------------------------------------------- 4. the SCM2 night
def _order(n, draws, rng):
    """`draws` indices into range(n), balanced (every index drawn floor or ceil of draws / n times), epoch-wise shuffles (sleep._order)."""
    out = []
    while len(out) < draws:
        p = list(range(n))
        rng.shuffle(p)
        out += p
    return out[:draws]


def _rng_snapshot(model):
    """Every model-held python / numpy RNG state, plus the global python and numpy states, as restore() closures."""
    snaps = [(random, random.getstate())]
    snaps.append((np.random, np.random.get_state()))
    objs = []
    for mod in model.modules():
        for v in vars(mod).values():
            if isinstance(v, (random.Random, np.random.RandomState, np.random.Generator)):
                objs.append((v, copy.deepcopy(v.bit_generator.state) if isinstance(v, np.random.Generator) else (v.get_state() if isinstance(v, np.random.RandomState) else v.getstate())))

    def restore():
        random.setstate(snaps[0][1])
        np.random.set_state(snaps[1][1])
        for v, s in objs:
            if isinstance(v, np.random.Generator):
                v.bit_generator.state = s
            elif isinstance(v, np.random.RandomState):
                v.set_state(s)
            else:
                v.setstate(s)
    return restore


def row_losses(model, rows, make_batch, seed):
    """-> [float loss per row]: model.loss on a batch of ONE row each, eval mode, no grad, torch.manual_seed(seed + i) per row inside fork_rng; model-held RNGs restored after.
    The same (model weights, row, seed + i) always gives the same number; the caller's random streams are unchanged."""
    was = model.training
    model.eval()
    restore = _rng_snapshot(model)
    p = next(model.parameters(), None)
    devs = [p.device.index or 0] if p is not None and p.device.type == 'cuda' else []
    out = []
    try:
        with torch.no_grad(), eg_cache(model), torch.random.fork_rng(devices=devs):
            for i, r in enumerate(rows):
                torch.manual_seed(seed + i)
                out.append(float(model.loss(make_batch([r]))[0]))
    finally:
        restore()
        model.train(was)
    return out


def _share_eg(model):
    return {id(e): e for e in getattr(model, '_eg', None) or []}


def _night(model, recs, replay_rows, make_batch, lr=LR, visits=VISITS, seed=0, warm_rows=None, every=EVERY, n_draw=N_DRAW, n_pick=N_PICK, batch=64, warmup=20,
          grad_clip=1.0, weight_decay=0.1, updates=None, log=None):
    """The SCM2 night (see the module docstring). -> (new model = deepcopy of the input after the night, in eval mode; info dict)."""
    assert replay_rows, 'the night needs replay rows (half of every batch)'
    t_start = time.time()
    m = copy.deepcopy(model, _share_eg(model))
    if not recs:
        m.eval()
        return m, dict(updates=0, records=0, visits_per_record=0.0, last_loss=None, rounds=[], picked_family_share={}, pool_family_share={}, seconds=0.0,
                       score_seconds=0.0, train_seconds=0.0, most_draws_one_record=0)
    assert len({r['id'] for r in recs}) == len(recs), 'record ids must be unique'
    half = batch // 2
    nrep = batch - half
    u = visits * len(recs) // 32 if updates is None else updates
    frozen = copy.deepcopy(model, _share_eg(model))
    frozen.eval()
    for p in frozen.parameters():
        p.requires_grad_(False)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    rec_order = _order(len(recs), u * half, rng)
    n_extra = nrep // 2 if warm_rows else 0
    k = nrep - n_extra
    rep_order = _order(len(replay_rows), u * k, rng)
    ext_order = _order(len(warm_rows), u * n_extra, rng) if n_extra else []
    emb = {id(x.weight) for x in m.modules() if isinstance(x, nn.Embedding)}
    ps = [p for p in m.parameters() if p.requires_grad]
    decay = [p for p in ps if p.ndim >= 2 and id(p) not in emb]
    no_decay = [p for p in ps if not (p.ndim >= 2 and id(p) not in emb)]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': weight_decay}, {'params': no_decay, 'weight_decay': 0.0}], lr=lr, betas=(0.9, 0.95))
    visit, losses, sel, slots, score_s = {}, [], [], None, 0.0
    m.train()
    for step in range(u):
        if step >= every and step % every == 0:
            t0 = time.time()
            drawn = random.Random(seed + 5000 + step).sample(replay_rows, min(n_draw, len(replay_rows)))
            now, then = row_losses(m, drawn, make_batch, seed + 5000 + step), row_losses(frozen, drawn, make_batch, seed + 5000 + step)
            rise = [a - b for a, b in zip(now, then)]
            top = sorted(range(len(drawn)), key=lambda i: -rise[i])[:n_pick]
            picked = [drawn[i] for i in top]
            slots = [picked[i] for i in _order(len(picked), every * k, random.Random(seed + 6000 + step))]
            dt = time.time() - t0
            score_s += dt
            sel.append(dict(step=step, families=dict(collections.Counter(kind_of(r) for r in picked)), mean_rise_picked=sum(rise[i] for i in top) / len(top),
                            mean_rise_all=sum(rise) / len(rise), drawn=len(drawn), score_seconds=dt))
            m.train()
            if log:
                log(f"[cb0] pick at step {step}: families {sel[-1]['families']}, rise picked {sel[-1]['mean_rise_picked']:.4f} / all {sel[-1]['mean_rise_all']:.4f}, {dt:.1f}s")
        rr = [recs[i] for i in rec_order[step * half:(step + 1) * half]]
        if slots is not None:
            j = (step % every) * k
            rep = slots[j:j + k]
        else:
            rep = [replay_rows[i] for i in rep_order[step * k:(step + 1) * k]]
        rep = rep + [warm_rows[i] for i in ext_order[step * n_extra:(step + 1) * n_extra]]
        for r in rr:
            visit[r['id']] = visit.get(r['id'], 0) + 1
        for g in opt.param_groups:
            g['lr'] = lr_at(step, u, warmup, lr)
        lt = m.trace_loss(make_batch([r['row'] for r in rr]), [r['trace'] for r in rr])[0]
        lo = m.loss(make_batch(rep))[0]
        loss = (half / batch) * lt + ((batch - half) / batch) * lo
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(ps, grad_clip)
        opt.step()
        losses.append(float(loss.detach()))
    cap = math.ceil(u * half / len(recs))
    assert max(visit.values(), default=0) <= cap, 'a record was seen too often'
    m.eval()
    fam = collections.Counter()
    for r in sel:
        fam.update(r['families'])
    pool = collections.Counter(kind_of(r) for r in replay_rows)
    npk = sum(fam.values())
    tot = time.time() - t_start
    return m, dict(updates=u, records=len(recs), visits_per_record=u * 32 / len(recs), last_loss=sum(losses[-10:]) / max(len(losses[-10:]), 1) if losses else None, rounds=sel,
                   picked_family_share={f: fam[f] / max(npk, 1) for f in sorted(pool)}, pool_family_share={f: pool[f] / len(replay_rows) for f in sorted(pool)},
                   seconds=tot, score_seconds=score_s, train_seconds=tot - score_s, most_draws_one_record=max(visit.values(), default=0), losses=losses)


def night(model, recs, replay_rows, make_batch, **kw):
    """The SCM2 night (_night's arguments: lr, visits, seed, warm_rows, every, n_draw, n_pick, batch, warmup, grad_clip, weight_decay, updates, log) inside eg_cache(model)."""
    with eg_cache(model):
        return _night(model, recs, replay_rows, make_batch, **kw)


# ---------------------------------------------------------------- 5. one day and night
def cycle(model, pool_rows, replay_rows, make_batch, check, seed, T=T_SAMPLE, n1=N1, n2=N2, warm_rows=None, **night_kw):
    """day -> records(seed + 1) -> night(seed). -> (model after the night, dict(day, records=dict(recs, counts, n), night))."""
    d = day(model, pool_rows, make_batch, check, seed, T=T, n1=n1, n2=n2)
    recs, counts = records(pool_rows, d, seed + 1)
    new, info = night(model, recs, replay_rows, make_batch, seed=seed, warm_rows=warm_rows, **night_kw)
    return new, dict(day=d, records=dict(recs=recs, counts=counts, n=len(recs)), night=info)
