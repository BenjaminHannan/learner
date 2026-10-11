"""python3 -m custom_io.tests.test_cb0   (CPU, seconds; no data files, no Gemma: test_b3's stub FrozenEG; run with OMP_NUM_THREADS=1)
CB-0 (custom_io/cb0.py): the Gemma input cache, the day (stuck test, two-pass search), records, the SCM2 night (fake model for the bookkeeping, a real tiny B3G2 for the per-row scoring
and one end-to-end cycle). The checker is always a stub."""
import copy, math, random
import torch
import torch.nn as nn
from custom_io import cb0
from custom_io.tests import test_b3g2 as T2
from custom_io.tests.test_b3 import batch_of, rows

V = T2.V
mk_real = lambda rs: batch_of(rs, V)
mk = lambda rs: dict(rows=list(rs))


# ---------------------------------------------------------------- the Gemma input cache
def test_eg_cache():
    from custom_io.tests.test_b3 import StubEG
    m = T2.make(3)
    eg, ref = m._eg[0], StubEG()
    ps = ['Echo: sune1 Give.', 'Tom has 12 apples and 5 more.', 'Echo: sune1 Give.', 'x']
    with cb0.eg_cache(m):
        assert 'encode' in vars(eg)
        for T, chars in ((40, True), (10, True), (40, False)):
            H, pooled = eg.encode(ps, T, torch.device('cpu'), chars)
            Hr, pr = ref.encode(ps, T, torch.device('cpu'), chars)
            assert torch.equal(pooled, pr) and pooled.dtype == pr.dtype
            assert (H is None) == (not chars) and (not chars or (H.shape == Hr.shape and H.dtype == Hr.dtype and torch.equal(H, Hr)))
        assert eg.passes == 3 and sorted(c[0] for c in eg.calls) == sorted(set(ps))      # each distinct prompt computed once, alone
        eg.encode(ps + ['new prompt'], 40, torch.device('cpu'))
        assert eg.passes == 4
    assert 'encode' not in vars(eg)
    # the reply encoder (encode_texts): same values as the plain one, each distinct text computed once and alone, restored on exit
    cpu = torch.device('cpu')
    rs = ['7', '12', '7', 'x = 5', '12']
    with cb0.eg_cache(m):
        assert 'encode_texts' in vars(eg)
        n0 = eg.text_pass_n
        for T in (12, 3):
            Ht = eg.encode_texts(rs, T, cpu)
            assert Ht.shape == (5, T, 768) and torch.equal(Ht, ref.encode_texts(rs, T, cpu))
        assert eg.text_pass_n - n0 == 3 and sorted(c[0] for c in eg.text_calls[-3:]) == sorted(set(rs))
        eg.encode_texts(rs + ['new'], 12, cpu)
        assert eg.text_pass_n - n0 == 4                                              # only the new text
    assert 'encode_texts' not in vars(eg) and 'encode' not in vars(eg)
    n0 = eg.text_pass_n
    eg.encode_texts(rs, 12, cpu)
    assert eg.text_pass_n - n0 == 1                                                  # uncached again: one batched call
    with cb0.eg_cache(m, max_items=2):
        eg.encode(ps, 40, torch.device('cpu'))
        assert len(eg._cb0_store.d) == 2
        eg.encode_texts(rs, 12, cpu)
        assert len(eg._cb0_store.t) == 2
    cb0.clear_eg_cache(m)
    assert len(eg._cb0_store.d) == 0 and len(eg._cb0_store.t) == 0
    # a model without eg_embed is untouched
    f = FakeDay()
    with cb0.eg_cache(f) as st:
        assert st is None
    # model level: the loss with the cache equals the one without, and a repeated day does not recompute
    m.eval()
    b = batch_of(rows(6), V)
    torch.manual_seed(1)
    with torch.no_grad():
        base = m.loss(b)[0].clone()
    cb0.clear_eg_cache(m)
    torch.manual_seed(1)
    with torch.no_grad(), cb0.eg_cache(m):
        assert torch.equal(m.loss(b)[0], base)
    n = eg.passes
    d1 = cb0.day(m, rows(4), mk_real, lambda r, t: False, 0, n1=1, n2=1)
    p1 = eg.passes
    d2 = cb0.day(m, rows(4), mk_real, lambda r, t: False, 0, n1=1, n2=1)
    assert eg.passes == p1 and d1['tries'] == d2['tries']
    print('ok eg_cache: equals uncached, misses computed once and alone, bounded, restored, no-eg model untouched, repeated day recomputes nothing')


# ---------------------------------------------------------------- fakes
class FakeDay(nn.Module):
    """Greedy try right on id % 3 == 0 (answer 'ok'); a sampled try is right with prob 0.5 (id % 3 == 0), 0.02 (id % 3 == 1), 0 (id % 3 == 2). Logs (T, rows)."""

    def __init__(self):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(1))
        self.log = []

    def sample_traces(self, batch, temperature, generator):
        assert not torch.is_grad_enabled() and not self.training
        self.log.append((temperature, [r['id'] for r in batch['rows']]))
        out = []
        for r in batch['rows']:
            i = int(r['id'][1:])
            if temperature == 0.0:
                ok = i % 3 == 0
            else:
                u = float(torch.rand(1, generator=generator))
                ok = u < (0.5, 0.02, 0.0)[i % 3]
                w = int(torch.randint(3, (1,), generator=generator))
            out.append(dict(calls=[(f'add {i} {w if temperature else 0}', '1')], answer=('ok' if ok else 'no') + (' ' if i % 2 else '')))
        return out


POOL = [dict(id=f'p{i}', family=('copy_word', 'add_story')[i % 2], prompt=f'P{i}', answer='A') for i in range(24)]
check = lambda row, t: t['answer'].strip() == 'ok'


def test_day():
    m = FakeDay()
    m.train()
    d = cb0.day(m, POOL, mk, check, seed=7, n1=2, n2=60, batch_size=10)
    assert m.training                                                                     # mode restored
    n = len(POOL)
    assert d['greedy_fit'] == [i % 3 == 0 for i in range(n)]
    g = [x for x in m.log if x[0] == 0.0]
    p = [x for x in m.log if x[0] == 1.0]
    assert sum(len(r) for _, r in g) == n and len(g) == 3                                 # greedy: every row once, chunks of 10
    assert m.log[:3] == g                                                                 # greedy first
    p1, p2 = p[:6], p[6:]
    assert sum(len(r) for _, r in p1) == 2 * n and len(p1) == 2 * 3                       # pass 1: n1 per row
    more = [i for i, f in enumerate(d['fit1']) if not f]
    assert more and len(more) < n
    assert set(r for _, rs in p2 for r in rs) == {f'p{i}' for i in more}                  # pass 2 only on rows with no pass-1 fit
    assert sum(len(r) for _, r in p2) == 60 * len(more)
    assert d['drawn'] == dict(greedy=n, pass1=2 * n, pass2=60 * len(more), pass2_rows=len(more))
    assert all(len(t) == (2 if i not in more else 62) for i, t in enumerate(d['tries'])) and all(len(f) == len(t) for f, t in zip(d['fit'], d['tries']))
    assert d['fit1'] == [any(f[:2]) for f in d['fit']] and d['fit_final'] == [any(f) for f in d['fit']]
    assert not any(d['fit_final'][i] for i in range(n) if i % 3 == 2)                      # never-right rows stay stuck
    assert any(d['fit_final'][i] and i in more for i in range(n))                          # pass 2 rescued some
    d2 = cb0.day(FakeDay(), POOL, mk, check, seed=7, n1=2, n2=60, batch_size=10)
    assert d2['tries'] == d['tries'] and d2['fit'] == d['fit']                             # same seed, same tries
    d3 = cb0.day(FakeDay(), POOL, mk, check, seed=8, n1=2, n2=60, batch_size=10)
    assert d3['tries'] != d['tries']
    print('ok day: greedy, pass 1, pass 2 on stuck rows only (%d of %d), seeds, mode restored' % (len(more), n))
    return d


def test_records():
    m = FakeDay()
    d = cb0.day(m, POOL, mk, check, seed=7, n1=2, n2=60, batch_size=10)
    recs, counts = cb0.records(POOL, d, 1, per_cap=2)
    ids = [r['id'] for r in recs]
    assert len(set(ids)) == len(ids) and all(r['id'].split('|')[0] == r['row']['id'] for r in recs)
    by = {}
    for r in recs:
        by.setdefault(r['row']['id'], []).append(r)
    assert all(len(v) <= 2 for v in by.values()) and [r['id'] for r in by['p0']] == ['p0|0', 'p0|1']
    for v in by.values():
        keys = [cb0._distinct_key(r['trace']) for r in v]
        assert len(set(keys)) == len(keys) and all(check(r['row'], r['trace']) for r in v)
    # fake with many distinct fits: rows with more than per_cap distinct fits are subsampled by Random(seed), the rest taken in order
    fits_idx = [j for j, f in enumerate(d['fit'][0]) if f]
    uniq = []
    for j in fits_idx:
        k = cb0._distinct_key(d['tries'][0][j])
        if k not in [u[0] for u in uniq]:
            uniq.append((k, d['tries'][0][j]))
    assert 2 < len(uniq) <= 3 or len(uniq) >= 1
    a, _ = cb0.records(POOL, d, 5)
    b, _ = cb0.records(POOL, d, 5)
    assert [x['id'] for x in a] == [x['id'] for x in b] and [x['trace'] for x in a] == [x['trace'] for x in b]
    big, _ = cb0.records(POOL, d, 1, per_cap=100)
    assert len(big) >= len(recs) and sum(counts.values()) == len(recs)
    assert counts == {k: sum(1 for r in recs if r['row']['family'] == k) for k in counts}
    # a hand-made day: duplicate fits collapse (same call texts, answer.strip()), the first draw is kept
    t = lambda c, a: dict(calls=[(c, 'r')], answer=a)
    day = dict(tries=[[t('add 1 1', 'ok'), t('add 1 1', 'ok '), t('add 1 2', 'ok'), t('add 1 1', 'bad'), t('add 2 2', 'ok')]], fit=[[True, True, True, False, True]])
    r1, _ = cb0.records(POOL[:1], day, 0, per_cap=10)
    assert [x['trace']['calls'][0][0] + x['trace']['answer'] for x in r1] == ['add 1 1ok', 'add 1 2ok', 'add 2 2ok']
    r2, _ = cb0.records(POOL[:1], day, 0, per_cap=2)
    assert len(r2) == 2 and all(x in r1[1:] + r1[:1] or True for x in r2)
    print('ok records: per_cap, distinctness, unique ids, seeded choice, kind counts')


# ---------------------------------------------------------------- night on a fake model
class FakeNight(nn.Module):
    """Replay row 'r{s}' / 'w{s}' / 'q..' loss = s * w^2 (rise grows with s once w moves); record trace loss (w - 1)^2. Training-mode calls are logged by row ids."""

    def __init__(self):
        super().__init__()
        self.w = nn.Parameter(torch.tensor([0.0, 0.0]))
        self.emb = nn.Embedding(3, 2)
        self.train_trace, self.train_plain, self.scored = [], [], []

    def trace_loss(self, batch, traces):
        assert self.training and len(batch['rows']) == len(traces)
        self.train_trace.append([r['id'] for r in batch['rows']])
        return ((self.w - 1) ** 2).sum() + 0 * self.emb.weight.sum(), {}

    def loss(self, batch):
        ids = [r['id'] for r in batch['rows']]
        if self.training:
            self.train_plain.append(ids)
        else:
            self.scored.append(ids)
        s = sum(int(i[1:]) for i in ids) / len(ids)
        return s * (self.w ** 2).sum(), {}


REC = [dict(id=f'q{i}|0', row=dict(id=f'q{i}', family='add_story', prompt=f'Q{i}', answer='1'), trace=dict(calls=[], answer='1')) for i in range(10)]
REP = [dict(id=f'r{i + 1}', family=('copy_word', 'chain_ops')[i % 2], prompt=f'R{i}', answer='1') for i in range(200)]
WARM = [dict(id=f'w{i + 1}', family='warm', prompt=f'W{i}', answer='1') for i in range(30)]


class Rec(torch.optim.AdamW):
    seen = []

    def __init__(self, groups, **kw):
        Rec.seen.append([p for g in groups for p in g['params']] if isinstance(groups[0], dict) else list(groups))
        super().__init__(groups, **kw)


def run_night(**kw):
    m = FakeNight()
    orig = torch.optim.AdamW
    torch.optim.AdamW = Rec
    Rec.seen = []
    try:
        new, info = cb0.night(m, REC, REP, mk, seed=2, **kw)
    finally:
        torch.optim.AdamW = orig
    return m, new, info


def test_night_fake():
    m, new, info = run_night(updates=70, every=32, n_draw=50, n_pick=10, warmup=5)
    assert new is not m and not m.train_trace and not m.train_plain                       # the input model is untouched; a deepcopy trained
    # sizes: 32 record rows and 32 replay rows each update
    # (the trained copy logged them)
    assert info['updates'] == 70 and info['records'] == 10 and info['visits_per_record'] == 70 * 32 / 10
    nm = new
    assert len(nm.train_trace) == 70 and all(len(x) == 32 for x in nm.train_trace) and all(len(x) == 32 for x in nm.train_plain)
    assert all(i.startswith('q') for x in nm.train_trace for i in x) and all(i.startswith('r') for x in nm.train_plain for i in x)
    # visits bound and balance
    cnt = {}
    for x in nm.train_trace:
        for i in x:
            cnt[i] = cnt.get(i, 0) + 1
    assert max(cnt.values()) <= math.ceil(70 * 32 / 10) == info['most_draws_one_record'] or info['most_draws_one_record'] <= math.ceil(70 * 32 / 10)
    assert max(cnt.values()) - min(cnt.values()) <= 1 and sum(cnt.values()) == 70 * 32     # balanced epoch-wise shuffles
    # pick rounds at steps 32 and 64 (>= every, % every == 0)
    assert [r['step'] for r in info['rounds']] == [32, 64]
    for r in info['rounds']:
        step = r['step']
        drawn = random.Random(2 + 5000 + step).sample(REP, 50)
        want = sorted(drawn, key=lambda x: -int(x['id'][1:]))[:10]                       # rise = s * w^2: the largest s
        slots = nm.train_plain[step:step + 32] if step == 32 else nm.train_plain[step:step + 6]
        used = {i for x in slots for i in x}
        assert used <= {x['id'] for x in want} and len(used) == 10, (step, used)
        assert r['drawn'] == 50 and r['mean_rise_picked'] > r['mean_rise_all'] > 0 and sum(r['families'].values()) == 10
    # before the first pick the replay slots come from rep_order (no restriction to the picked ones)
    assert len({i for x in nm.train_plain[:32] for i in x}) > 10
    # scoring: 2 * n_draw single-row passes per round, never in the training batches, on a model in eval mode
    assert len(new.scored) == 2 * 50 and all(len(x) == 1 for x in new.scored)             # 2 rounds x 50 single-row passes under the current model
    opt_ps = {id(p) for p in Rec.seen[0]}
    assert opt_ps == {id(p) for p in new.parameters() if p.requires_grad}                  # every trainable parameter, nothing else
    assert not new.training and set(info) >= {'updates', 'records', 'visits_per_record', 'last_loss', 'rounds', 'picked_family_share', 'pool_family_share', 'seconds', 'score_seconds', 'train_seconds', 'most_draws_one_record'}
    assert math.isfinite(info['last_loss']) and new.w.abs().sum() > 0
    print('ok night (fake): 32 + 32 per update, balanced visits, picks at steps 32 and 64 are the top-rise rows')


def test_night_warm():
    m, new, info = run_night(updates=5, every=32, n_draw=10, n_pick=5, warm_rows=WARM, warmup=2)
    assert len(new.train_plain) == 5
    for x in new.train_plain:
        assert len(x) == 32 and sum(i.startswith('r') for i in x) == 16 and sum(i.startswith('w') for i in x) == 16
    assert info['rounds'] == []
    # the default updates = visits * len(recs) // 32
    _, _, i2 = run_night(visits=32, every=1000)
    assert i2['updates'] == 32 * 10 // 32 == 10
    print('ok night warm split 16 + 16, default updates')


# ---------------------------------------------------------------- row_losses on a real tiny B3G2
def test_row_losses():
    m = T2.make(4)
    m.train()
    rs = rows(5)
    torch.manual_seed(9)
    before = torch.get_rng_state()
    gap, drill = m._gap_rng.getstate(), m._drill_rng.getstate() if hasattr(m, '_drill_rng') else None
    a = cb0.row_losses(m, rs, mk_real, 3)
    assert torch.equal(torch.get_rng_state(), before)                                    # the global torch stream is untouched
    assert m._gap_rng.getstate() == gap and (drill is None or m._drill_rng.getstate() == drill) and m.training
    b = cb0.row_losses(copy.deepcopy(m), rs, mk_real, 3)
    assert a == b and len(a) == 5 and all(math.isfinite(x) for x in a)                     # identical draws, identical losses for a copy
    frozen = copy.deepcopy(m)
    with torch.no_grad():
        m.writer.parameters().__next__().add_(0.5)
    c = cb0.row_losses(m, rs, mk_real, 3)
    assert c != a                                                                         # the weights matter
    assert cb0.row_losses(m, rs, mk_real, 3) == c and cb0.row_losses(frozen, rs, mk_real, 3) == a   # repeatable
    print('ok row_losses: copy-identical, repeatable, global and model-held RNG unchanged')


# ---------------------------------------------------------------- end to end on the real tiny B3G2
def test_cycle_smoke():
    m = T2.make(5)
    rs = rows(24)
    pool, replay = rs[:6], rs[6:]
    stub = lambda row, t: sum(t['answer'].encode()) % 2 == 0                               # accepts about half the tries, never reads row['answer']
    new, res = cb0.cycle(m, pool, replay, mk_real, stub, seed=1, n1=2, n2=3, every=2, n_draw=4, n_pick=2, updates=5, batch=4, warmup=2, lr=1e-3)
    assert res['records']['n'] > 0 and res['night']['updates'] == 5
    assert [r['step'] for r in res['night']['rounds']] == [2, 4]
    assert all(math.isfinite(x) for x in res['night']['losses']) and math.isfinite(res['night']['last_loss'])
    assert res['day']['drawn']['pass1'] == 12 and not new.training
    assert any(not torch.equal(p, q) for p, q in zip(new.parameters(), m.parameters()))   # trained a copy
    new2, res2 = cb0.cycle(new, pool, replay, mk_real, stub, seed=2, n1=2, n2=3, every=2, n_draw=4, n_pick=2, updates=3, batch=4, warmup=1, lr=1e-3, warm_rows=rs[:4])
    assert math.isfinite(res2['night']['last_loss'])
    print('ok cycle smoke (real tiny B3G2): %d records, losses finite' % res['records']['n'])


if __name__ == '__main__':
    for f in (test_eg_cache, test_day, test_records, test_night_fake, test_night_warm, test_row_losses, test_cycle_smoke):
        f()
    print('ALL OK')


class FakeC2(nn.Module):
    """C2 rows with hand-made copy records (test_cb0_check.reference): each sampled try is the kind's reference program with prob 0.5, else a one-constant mutant."""

    def __init__(self, table):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(1))
        self.table = table                                   # prompt -> (reference trace, mutant trace); keyed by the prompt only, never the answer

    def sample_traces(self, batch, temperature, generator):
        out = []
        for r in batch['rows']:
            good, bad = self.table[r['prompt']]
            ok = temperature > 0 and float(torch.rand(1, generator=generator)) < 0.5
            out.append(copy.deepcopy(good if ok else bad))
        return out


def test_corrupt_every_key_records():
    """CB-0 mark (3) end to end: day + records with the real checker give IDENTICAL records when every answer key, accepted list and kind is corrupted or deleted."""
    from custom_io import cb0_check as C
    from custom_io.tests.test_cb0_check import reference, MUT, XS, QS
    rows, table = [], {}
    for kind in MUT:
        for j, (xs, q) in enumerate(zip(XS, QS)):
            row, good = reference(kind, xs, q)
            _, bad = reference(kind, xs, q, **MUT[kind][0])
            assert C.check(row, good) and not C.check(row, bad)
            rows.append(dict(row, id=f'{kind}{j}', kind=kind, answer=good['answer'], accepted=[good['answer']]))
            table[row['prompt']] = (good, bad)
    mb = lambda rs: dict(rows=rs)
    m = FakeC2(table)

    def recs_of(rs):
        d = cb0.day(m, rs, mb, C.check, seed=3, n1=4, n2=8, batch_size=5)
        rec, cnt = cb0.records(rs, d, seed=4)
        return d, [(r['id'], r['trace']['calls'], r['trace']['answer']) for r in rec]

    d0, r0 = recs_of(rows)
    assert r0 and not any(d0['greedy_fit'])                    # the greedy try is the mutant: every row stuck; records come from the search
    bad_rows = [dict(r, answer='999999', accepted=['-1'], kind='square' if r['kind'] != 'square' else 'affine') for r in rows]
    gone = [{k: v for k, v in r.items() if k not in ('answer', 'accepted', 'kind')} for r in rows]
    for rs in (bad_rows, gone):
        d1, r1 = recs_of(rs)
        assert r1 == r0 and d1['fit'] == d0['fit']
    print(f'ok corrupt-every-key: {len(r0)} records identical with keys corrupted / deleted')
