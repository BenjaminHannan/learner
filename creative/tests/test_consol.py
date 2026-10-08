"""python3 -m creative.tests.test_consol   (CPU, 2 threads, a couple of minutes; needs the raw B2 checkpoint ~/work/ckpt/B2_s200.pt and the skills train file)
Consolidation sleep (creative/consol.py): the pool split, fresh dreams (unique ids, new prompts that still fit their examples), fixed replay, sleep_mixed
(list and stream, replay without repetition, weighted families, checks and early stop), weight-space scaling, and the self-signals read no answer fields."""
import builtins, copy, os
import torch
from creative import consol as C, fewshot, repair7d, sleep
from creative import programs as P
from creative.rl.m import replay
from custom_io.data import Dataset, load_rows

CKPT = '~/work/ckpt/B2_s200.pt'
TRAIN = os.path.expanduser('~/work/data/train.jsonl')
SEALED = ('data/c2/test.jsonl', 'data/c2/labelled.jsonl', 'data/c2rl/holdout.jsonl', 'data/c2/dev.jsonl', 'in_dist.jsonl')
_CACHE = {}
torch.set_num_threads(2)


def _model():
    if 'm' not in _CACHE:
        m, vocab, meta = sleep.load_parent(os.path.expanduser(CKPT), 'cpu')
        m.eval()
        _CACHE['m'] = (m, vocab, meta)
    m, vocab, _ = _CACHE['m']
    return copy.deepcopy(m), vocab


def _skills():
    if 'rows' not in _CACHE:
        _CACHE['rows'] = load_rows(TRAIN)[::50]                 # all families
    return _CACHE['rows']


def _day(n=12):
    """n fake day questions whose rule is 'times 10' (3 examples + a query), prompts only."""
    out = []
    for i in range(n):
        xs = [2 + (7 * i + 5 * j) % 29 for j in range(4)]
        nums = [v for x in xs[:3] for v in (x, 10 * x)] + [xs[3]]
        out.append({'id': f'day:{i:03d}', 'nums': nums,
                    'prompt': 'Examples: ' + '; '.join(f'{x} -> {10 * x}' for x in xs[:3]) + f'. Now {xs[3]} -> ?'})
    return out


def _finds(n=3):
    t = P.Try.make([(P.MUL, 6, 18)], P.R0)                      # x_q (slot 6) times the constant 10 (slot 18)
    day = _day(12)
    recs = [fewshot._record(dict(r), t, 'S', 0) for r in day[:n]]
    return recs, day


def _spy_dataset(seen):
    class Spy(Dataset):
        def __init__(self, rows, vocab, strict=True):
            seen.append(list(rows))
            super().__init__(rows, vocab, strict)
    return Spy


def test_split_pool():
    pool = [{'id': f'p{i}', 'prompt': f'{i}'} for i in range(300)]
    tr, he = C.split_pool(pool, 3, 128)
    assert len(he) == 128 and len(tr) == 172 and not {r['id'] for r in tr} & {r['id'] for r in he}
    assert sorted(r['id'] for r in tr + he) == sorted(r['id'] for r in pool)
    assert (tr, he) == C.split_pool(pool, 3, 128) and he != C.split_pool(pool, 4, 128)[1]
    day = C.day_pool()
    assert len(day) == 1024 and set(day[0]) == {'id', 'prompt', 'nums'}


def test_dream_stream():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    gen = C.dream_stream(recs, 0, inputs, lo, hi)
    got = [next(gen) for _ in range(20)]                        # more than 6 passes over 3 records
    assert len({r['id'] for r in got}) == 20 and len({id(r) for r in got}) == 20 and all(r['id'].startswith('D:') for r in got)
    src = {r['id']: r['prompt'] for r in recs}
    for r in got:
        assert r['prompt'] != src[r['source']] and r['prompt'] != ''
        p = fewshot.parse(r['prompt'])
        assert fewshot.verdict(p, fewshot.record_try(r))[0] == 'accept'
        assert min(p['ys']) >= lo and max(p['ys']) <= hi and len(set(p['ys'])) > 1
    assert {r['source'] for r in got} == set(src)
    assert [r['prompt'] for r in got] == [next(g)['prompt'] for g in [C.dream_stream(recs, 0, inputs, lo, hi)] for _ in range(20)]
    assert [r['prompt'] for r in got] != [next(g)['prompt'] for g in [C.dream_stream(recs, 1, inputs, lo, hi)] for _ in range(20)]


def test_fixed_replay():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    out = C.fixed_replay(recs, 0, inputs, lo, hi, k=3)
    assert len(out) == 4 * len(recs) and out[:3] == recs and len({r['id'] for r in out}) == len(out)


def test_quota():
    q = C.quota({'a': 1.0, 'b': 1.0, 'c': 1.0}, 4)
    assert sum(q.values()) == 4 and sorted(q.values()) == [1, 1, 2]
    assert C.quota({'a': 3.0, 'b': 1.0, 'c': 0.0}, 8) == {'a': 6, 'b': 2, 'c': 0}
    assert sum(C.quota({f'f{i}': 1.0 + i for i in range(34)}, 512).values()) == 512


def _run(rec_source, updates=3, batch=8, **kw):
    m, vocab = _model()
    seen = []
    orig, C.Dataset = C.Dataset, _spy_dataset(seen)
    try:
        info = C.sleep_mixed(m, rec_source, _skills(), vocab, updates, batch=batch, seed=0, **kw)
    finally:
        C.Dataset = orig
    return m, info, seen


def _check_batches(seen, half, rec_prefixes=('S:', 'Y:', 'D:')):
    reps = [r['id'] for rows in seen for r in rows[half:]]
    assert all(len(rows) == 2 * half and all(r['id'].startswith(rec_prefixes) for r in rows[:half]) for rows in seen)
    assert not any(i.startswith(rec_prefixes) for i in reps) and len(reps) == len(set(reps))


def test_sleep_mixed_list():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    rs = C.fixed_replay(recs, 0, inputs, lo, hi)
    m0, _ = _model()
    m, info, seen = _run(rs)
    assert info['updates_done'] == 3 and len(info['loss']) == 3 and info['rows_seen'] == 24 and len(seen) == 3
    assert info['record_visits']['max'] <= 1 and info['record_visits']['n'] == 12
    _check_batches(seen, 4)
    assert any(not torch.equal(a, b) for a, b in zip(m0.parameters(), m.parameters()))
    try:
        C.sleep_mixed(m, rs, _skills()[:10], _model()[1], 3, batch=8)
    except ValueError:
        pass
    else:
        raise AssertionError('exhausted replay must raise')


def test_sleep_mixed_stream():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    m, info, seen = _run(C.dream_stream(recs, 0, inputs, lo, hi))
    assert info['updates_done'] == 3 and info['record_visits']['max'] == 1 and info['record_visits']['n'] == 12
    _check_batches(seen, 4)
    ids = [r['id'] for rows in seen for r in rows[:4]]
    assert len(ids) == len(set(ids))


def test_sleep_mixed_weighted():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    fams = sorted({r['family'] for r in _skills()})
    calls = []

    def wfn(model, step):
        calls.append((step, model.training))
        return {f: (3.0 if f == fams[0] else 1.0 if f == fams[1] else 0.0) for f in fams}
    m, info, seen = _run(C.dream_stream(recs, 0, inputs, lo, hi), updates=5, check_every=2, replay_weight_fn=wfn)
    assert calls == [(0, False), (2, False), (4, False)] and m.training
    _check_batches(seen, 4)
    for rows in seen:
        c = {}
        for r in rows[4:]:
            c[r['family']] = c.get(r['family'], 0) + 1
        assert c == {fams[0]: 3, fams[1]: 1}, c
    assert [s for s, _ in info['weights']] == [0, 2, 4]


def test_checks_and_stop():
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    steps = []

    def fn(model, step):
        steps.append((step, model.training))
        return None
    m, info, _ = _run(C.dream_stream(recs, 0, inputs, lo, hi), updates=5, check_every=2, check_fn=fn)
    assert steps == [(2, False), (4, False), (5, False)] and m.training and info['updates_done'] == 5
    steps.clear()
    _run(C.dream_stream(recs, 0, inputs, lo, hi), updates=4, check_every=2, check_fn=fn)
    assert [s for s, _ in steps] == [2, 4]
    m, info, seen = _run(C.dream_stream(recs, 0, inputs, lo, hi), updates=6, check_every=2, check_fn=lambda mo, s: 'stop' if s == 4 else None)
    assert info['updates_done'] == 4 and len(info['loss']) == 4 and len(seen) == 4 and [c['step'] for c in info['checks']] == [2, 4]
    m, info, _ = _run(C.dream_stream(recs, 0, inputs, lo, hi), updates=3, check_every=0, check_fn=fn)
    assert info['checks'] == []


def test_scaled():
    N, _ = _model()
    W = copy.deepcopy(N)
    g = torch.Generator().manual_seed(0)
    with torch.no_grad():
        for p in W.parameters():
            p.add_(torch.randn(p.shape, generator=g))
    sn, sw = N.state_dict(), W.state_dict()
    for a, ref in ((0.0, sn), (1.0, sw)):
        s = C.scaled(N, W, a).state_dict()
        assert all(torch.equal(s[k], ref[k]) for k in ref)
    h = C.scaled(N, W, 0.5).state_dict()
    for k in sn:
        if sn[k].is_floating_point():
            assert torch.allclose(h[k], (sn[k] + sw[k]) / 2, atol=1e-6)
        else:
            assert torch.equal(h[k], sw[k])
    assert all(torch.equal(a, b) for a, b in zip(N.state_dict().values(), sn.values()))


class _Strict(dict):
    """A row that fails on any read of an answer field."""
    BAD = ('answer', 'accepted', 'kind', 'params', 'steps')

    def __getitem__(self, k):
        assert k not in self.BAD, k
        return super().__getitem__(k)

    def get(self, k, d=None):
        assert k not in self.BAD, k
        return super().get(k, d)


def test_self_signals():
    m, vocab = _model()
    orig, seen = builtins.open, []

    def spy(f, *a, **k):
        seen.append(str(f))
        return orig(f, *a, **k)
    builtins.open = spy
    try:
        ctx, held = C.make_day(0, vocab, 'cpu', 16)
    finally:
        builtins.open = orig
    assert len(held) == 16 and len(ctx.pool) == 1008 and not [s for s in seen if any(s.endswith(x) for x in SEALED)], seen
    f = C.held_fits(m, [_Strict(r) for r in held], vocab)
    assert 0.0 <= f <= 1.0 and f == C.held_fits(m, held, vocab)
    rows = _skills()
    held_rows, rest = repair7d.held_split(rows, per_family=2, seed=0)
    assert len(held_rows) == 68 and not {r['id'] for r in held_rows} & {r['id'] for f in rest.values() for r in f}
    sc = C.selfcheck(m, held_rows[:34])
    assert len(sc['hits']) == 34 and set(sc['by_family']) == {r['family'] for r in held_rows[:34]} and 0 <= sc['in_dist'] <= 100
    fl = C.family_loss(m, held_rows, vocab, batch=16)
    assert set(fl) == {r['family'] for r in held_rows} and all(v == v for v in fl.values()) and not m.training
    f0 = max(fl, key=fl.get)
    w = C.interference_weights(held_rows, vocab, 'cpu', {f: v * (0.5 if f == f0 else 2.0) for f, v in fl.items()}, floor=1e-6)(m, 0)
    assert abs(sum(w.values()) - 1) < 1e-9
    others = [v for f, v in w.items() if f != f0]
    assert abs(w[f0] / others[0] - 4.0) < 1e-6 and max(others) - min(others) < 1e-12
    w = C.interference_weights(held_rows, vocab, 'cpu', {f: 0.0 for f in fl})(m, 0)          # start losses ~0: the floor keeps tiny wobbles from dominating
    assert max(w.values()) / min(w.values()) <= (max(fl.values()) / 0.05) ** 2 + 1e-9
    W = copy.deepcopy(m)
    with torch.no_grad():
        for p in W.parameters():
            p.add_(0.05 * torch.randn(p.shape, generator=torch.Generator().manual_seed(1)))
    a, table = C.pick_scale(m, W, held[:8], held_rows[:34], vocab, 'cpu', grid=(0.5, 1.0), max_drop=100.0)
    assert a in (0.5, 1.0) and [t['a'] for t in table] == [0.0, 0.5, 1.0] and all(t['allowed'] for t in table)
    a, table = C.pick_scale(m, W, held[:8], held_rows[:34], vocab, 'cpu', grid=(0.5, 1.0), max_drop=-1000.0)
    assert not any(t['allowed'] for t in table[1:]) and a == min(table[1:], key=lambda t: (t['drop'], t['a']))['a']


def test_finds_smoke():
    m, vocab = _model()
    ctx, _ = C.make_day(0, vocab, 'cpu', 128)
    ctx.pool = ctx.pool[:24]
    recs, info = C.finds(m, ctx)
    assert set(info) >= {'n_W', 'n_C', 'T', 'seconds'} and len(recs) == info['n_W'] + info['n_C']
    assert len({r['id'] for r in recs}) == len(recs) and all(r['source'].startswith('c2:pool') for r in recs)


def test_trim_replay():
    rows = [{'id': f'r{i}', 'family': f'f{i % 5}'} for i in range(5000)]
    a, b = C._Replay(rows, 3), C._Replay(C.trim_replay(rows, 3, 900), 3, True)
    for _ in range(9):
        assert [r['id'] for r in a.draw(100)] == [r['id'] for r in b.draw(100)]


def test_rp_rows_and_dream_cache():
    """rp = fd's replay rows with the C2 half removed (batch 4 of replay = fd batch 8's replay half), and a dream's target is dropped after its update."""
    from custom_io.models import progparse as pp
    recs, day = _finds(3)
    inputs, lo, hi = replay.experience(day)
    _, _, seen_fd = _run(C.dream_stream(recs, 0, inputs, lo, hi), batch=8, replay_ordered=False)
    m, vocab = _model()
    rows = C.trim_replay(_skills(), 0, 3 * 4)
    seen = []
    orig, C.Dataset = C.Dataset, _spy_dataset(seen)
    try:
        C.sleep_mixed(m, None, rows, vocab, 3, batch=4, seed=0, replay_ordered=True)
    finally:
        C.Dataset = orig
    assert [[r['id'] for r in b] for b in seen] == [[r['id'] for r in b[4:]] for b in seen_fd]
    ids = [r['id'] for b in seen_fd for r in b[:4]]
    assert all(i.startswith('D:') for i in ids) and not any(i in pp._CACHE for i in ids)


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k, flush=True)
