"""python3 -m creative.tests.test_sleep7d   (CPU, about a minute; uses ~/c7d/s100/Nprime.pt or ~/rl/parents/s100/N_ss.pt when present, else a tiny random Ledger)
The adapter is bit-identical when off; logp_tries is the sampler's own log-probability and trains only the adapter; the day / kept-tries / advantage plumbing; no sealed file is opened."""
import builtins, copy, os, random
import torch
import torch.nn.functional as F
from creative import c2_stones, fewshot, rules_real as R, sampler, sleep, sleep7d as S
from creative.programs import Try, raw_key

CKPTS = ('~/c7d/s100/Nprime.pt', '~/rl/parents/s100/N_ss.pt')
DATA = 'creative/data/c2'
SEALED = ('data/c2/test.jsonl', 'data/c2/labelled.jsonl', 'data/c2rl/holdout.jsonl', 'knew/test.jsonl')
_CACHE = {}
torch.set_num_threads(2)


def _rows(n=16):
    return c2_stones._with_nums(R.load_split(DATA, 'dev')[:n])


def _model():
    """-> (model with adapter added (flag off), unwrapped reference copy, vocab). Cached: tests copy before changing anything."""
    if 'm' not in _CACHE:
        path = next((os.path.expanduser(p) for p in CKPTS if os.path.exists(os.path.expanduser(p))), None)
        if path:
            m, vocab, _ = sleep.load_parent(path, 'cpu')
        else:
            from custom_io.data import CharVocab
            from custom_io.models.ledger import Ledger
            vocab = CharVocab.build(_rows(8))
            torch.manual_seed(0)
            m = Ledger(vocab, d=32, n_heads=2, reader_layers=1, blocks=2, n_loops=8, mlp=2.0)
        m.eval()
        ref = copy.deepcopy(m)
        S.add_adapter(m, seed=0)
        _CACHE['m'] = (m, ref, vocab)
    return _CACHE['m']


def _fresh():
    m, ref, vocab = _model()
    return copy.deepcopy(m), ref, vocab


def test_worker_untouched():
    m, ref, vocab = _model()
    rows = _rows(16)
    out = S.worker_untouched(m, ref, rows, vocab, 'cpu', perturb=True)
    assert out['greedy_equal'] and out['logits_equal'], out           # adapter off, every B random non-zero: bit-identical to the unwrapped model
    assert out['on_differs'], out                                      # adapter on: the logits move
    assert S.worker_untouched(m, ref, rows, vocab, 'cpu')['passes']    # untouched adapter (B = 0) off: identical too
    flag = m._creative
    assert flag.on is False
    with S.creative(m, True) as mm:
        assert mm is m and flag.on
        with S.creative(m, False):
            assert not flag.on
        assert flag.on
    assert flag.on is False


def test_adapter_layers_and_state():
    m, ref, vocab = _fresh()
    names = {n for n, _ in S._wrappers(m)}
    blocks = len(m.core)
    assert len(names) == blocks * len(S.LORA_LAYERS) + len(S.LORA_HEADS), names
    assert all(not p.requires_grad for n, p in m.named_parameters() if not (n.endswith('.A') or n.endswith('.B')))
    assert len(S.adapter_params(m)) == 2 * len(names)
    st = S.adapter_state(m)
    for _, w in S._wrappers(m):
        w.B.data += 1.0
    S.load_adapter_state(m, st)
    assert all(float(w.B.detach().abs().sum()) == 0.0 for _, w in S._wrappers(m))        # round trip restores B = 0
    d = copy.deepcopy(m)                                                           # a deep copy owns its own flag (shared by its wrappers only)
    assert d._creative is not m._creative and all(w.flag is d._creative for _, w in S._wrappers(d))


def test_logp_matches_sampling():
    """Spy on sampler._pick (the sampling loop's own pick) and compare with logp_tries on the tries that were drawn."""
    m, ref, vocab = _fresh()
    rows = _rows(12)
    T = 3.0
    rec = []
    orig = sampler._pick

    def spy(logits, temperature, greedy, gen):
        idx = orig(logits, temperature, greedy, gen)
        rec.append(F.log_softmax(logits.float() / T, -1).gather(1, idx[:, None])[:, 0])
        return idx
    gen = torch.Generator().manual_seed(5)
    sampler._pick = spy
    try:
        out = sampler.sample_run(m, sampler.make_batch(rows, vocab, 'cpu'), T, False, gen)
    finally:
        sampler._pick = orig
    assert len(rec) == 3 * 7 + 1
    want = torch.stack(rec).sum(0)
    tries = sampler._tries_from(out)
    with torch.no_grad():
        got = S.logp_tries(m, rows, tries, T)
    assert torch.allclose(got['lp'], want, atol=1e-4, rtol=1e-5), (got['lp'], want)
    assert (got['lp'] < 0).all()
    # with the adapter on and random B the sampler and logp_tries still agree (the same code path through the adapter)
    g = torch.Generator().manual_seed(1)
    for _, w in S._wrappers(m):
        w.B.data = torch.randn(w.B.shape, generator=g) * 0.3
    rec.clear()
    sampler._pick = spy
    try:
        with S.creative(m, True):
            out = sampler.sample_run(m, sampler.make_batch(rows, vocab, 'cpu'), T, False, torch.Generator().manual_seed(6))
    finally:
        sampler._pick = orig
    want = torch.stack(rec).sum(0)
    with torch.no_grad(), S.creative(m, True):
        got = S.logp_tries(m, rows, sampler._tries_from(out), T)
    assert torch.allclose(got['lp'], want, atol=1e-4, rtol=1e-5), (got['lp'], want)


def test_logp_greedy_is_argmax():
    m, ref, vocab = _fresh()
    rows = _rows(12)
    g = sampler.greedy_tries(m, rows, vocab, 'cpu')
    with torch.no_grad():
        o = S.logp_tries(m, rows, g, 3.0)
    t = [x.t for x in g]
    f = lambda k: torch.tensor([getattr(x, k) for x in t])
    assert torch.equal(o['lop'].argmax(-1), f('ops')) and torch.equal(o['la'].argmax(-1), f('a')) and torch.equal(o['lb'].argmax(-1), f('b'))
    assert torch.equal(o['lans'].argmax(-1), torch.tensor([x.ans for x in t]))
    assert torch.allclose(o['lop'].exp().sum(-1), torch.ones(12, 7), atol=1e-5)         # each head is a normalised distribution
    assert torch.allclose(o['lans'].exp().sum(-1), torch.ones(12), atol=1e-5)


def test_logp_gradients_reach_only_the_adapter():
    m, ref, vocab = _fresh()
    rows = _rows(8)
    tries = sampler.greedy_tries(m, rows, vocab, 'cpu')
    g = torch.Generator().manual_seed(2)
    for _, w in S._wrappers(m):
        w.B.data = torch.randn(w.B.shape, generator=g) * 0.3
    with S.creative(m, True):
        S.logp_tries(m, rows, tries, 3.0)['lp'].sum().backward()
    ad = {id(p) for p in S.adapter_params(m)}
    base = [p for p in m.parameters() if id(p) not in ad]
    assert all(p.grad is None for p in base)
    assert all(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in S.adapter_params(m)), 'an adapter parameter got no gradient'


def test_kl():
    m, ref, vocab = _fresh()
    rows = _rows(8)
    tries = sampler.greedy_tries(m, rows, vocab, 'cpu')
    with torch.no_grad(), S.creative(m, True):
        a = S.logp_tries(m, rows, tries, 3.0)
        assert float(S.kl_to_ref(a, a).abs().max()) == 0.0
        g = torch.Generator().manual_seed(3)
        for _, w in S._wrappers(m):
            w.B.data = torch.randn(w.B.shape, generator=g) * 0.3
        b = S.logp_tries(m, rows, tries, 3.0)
    kl = S.kl_to_ref(b, a)
    assert torch.isfinite(kl).all() and (kl > 0).all()


def test_day_contract():
    m, ref, vocab = _fresh()
    rows = _rows(8)
    d = S.day(m, rows, vocab, 'cpu', T=3.0, n1=4, n2=6, seed=0)
    g = sampler.greedy_tries(ref, rows, vocab, 'cpu')
    assert d['greedy'] == g                                                              # the worker's first try is the unwrapped model's greedy try
    assert d['stuck'] == [i for i, t in enumerate(g) if not S.fits(fewshot.parse(rows[i]['prompt']), t.t)]
    assert set(d['tries']) == set(d['stuck']) and all(not d['greedy_fit'][i] for i in d['stuck'])
    for i in d['stuck']:
        assert len(d['tries'][i]) == (4 if d['fit1'][i] else 4 + 6)                      # pass 2 only where pass 1 found no fit
    assert d['drawn']['pass1'] == 4 * len(d['stuck']) and d['drawn']['pass2'] == 6 * sum(not f for f in d['fit1'].values())
    assert m._creative.on is False                                                       # the day leaves the adapter as it found it


def _fake_day(rows):
    """A day with hand-made tries: row 0 has fits and fails, row 1 only fails, row 2 only fits, row 3 fits and fails (with duplicates)."""
    def tr(rows_i, good):
        p = fewshot.parse(rows_i['prompt'])
        q = p['q_slot']
        # good: x (add 1 const) is not a fit in general; build fits from the reference program of the row's own kind
        t, _, qs = R.reference(rows_i['kind'], tuple(rows_i['params']))
        t = R.remap(t, qs, q)
        return t if good else Try.make([(1, q, q)], 20)                                 # x + x: a fail (unless it happens to be the rule)
    fits_, fails_ = [tr(r, True) for r in rows], [tr(r, False) for r in rows]
    t = {}
    t[0] = [sampler.TryRec(x) for x in [fails_[0], fits_[0], fails_[0], Try.make([(3, rows[0]['nums'][0], rows[0]['nums'][0])], 20)]]
    t[1] = [sampler.TryRec(fails_[1])]
    t[2] = [sampler.TryRec(fits_[2])]
    t[3] = [sampler.TryRec(x) for x in [fits_[3], fits_[3], fails_[3]]]
    return dict(stuck=[0, 1, 2, 3], tries=t), fits_, fails_


def test_kept_tries_and_advantages():
    rows = [r for r in _rows(40) if r['kind'] in ('square', 'last_digit')][:4]
    d, fits_, fails_ = _fake_day(rows)
    for i, (f, x) in enumerate(zip(fits_, fails_)):
        p = fewshot.parse(rows[i]['prompt'])
        assert S.fits(p, f) and not S.fits(p, x), i                                      # the hand-made tries are what they say
    k = S.kept_tries(rows, d, seed=0)
    assert k['rows_stuck'] == 4 and k['rows_kept'] == 2 and k['dropped_no_fit'] == 1 and k['dropped_no_fail'] == 1      # row 1: no fit, row 2: no fail
    by = {}
    for it in k['items']:
        by.setdefault(it['i'], []).append(it)
    assert set(by) == {0, 3}
    assert len({raw_key(it['t']) for it in by[3]}) == len(by[3]) == 2                    # duplicates dropped: one fit, one fail
    for its in by.values():
        assert abs(sum(it['adv'] for it in its)) < 1e-9 and {it['r'] for it in its} == {0.0, 1.0}
        assert all(it['adv'] > 0 for it in its if it['r'] == 1) and all(it['adv'] < 0 for it in its if it['r'] == 0)
    k2 = S.kept_tries(rows, d, seed=0)
    assert [(it['i'], it['t'], it['adv']) for it in k['items']] == [(it['i'], it['t'], it['adv']) for it in k2['items']]     # seeded
    big = [sampler.TryRec(Try.make([(1, 0, j % 16), (2, 1, j // 16 % 16)] + [(1, 16, 17)] * (j // 256), 20)) for j in range(300)]
    big_fit = [sampler.TryRec(fits_[0])]
    d2 = dict(stuck=[0], tries={0: big + big_fit})
    k3 = S.kept_tries(rows, d2, seed=1, k_fit=8, k_fail=8)
    assert k3['n_fail'] == 8 and k3['n_fit'] == 1
    # the placebo: the multiset of rewards is unchanged, advantages are recomputed per row (zero mean), and the reward-try link is broken
    items = k['items'] * 3
    a0, a1 = S.advantages(items), S.advantages(items, shuffle=True, seed=4)
    assert a0 != a1 and S.advantages(items, True, 4) == a1
    for i in {it['i'] for it in items}:
        assert abs(sum(a for a, it in zip(a1, items) if it['i'] == i)) < 1e-9


def test_loop1_trains_only_the_adapter():
    m, ref, vocab = _fresh()
    rows = _rows(6)
    p = [fewshot.parse(r['prompt']) for r in rows]
    items = []
    with S.creative(m, True):
        smp = sampler.sample_run(m, sampler.make_batch(rows * 8, vocab, 'cpu'), 3.0, False, torch.Generator().manual_seed(0))
    tr = sampler._tries_from(smp)
    items = [dict(i=j % 6, row=rows[j % 6], t=x.t, r=float(j % 2), adv=0.0) for j, x in enumerate(tr)]
    kept = dict(items=items)
    before = {n: q.detach().clone() for n, q in m.named_parameters() if not (n.endswith('.A') or n.endswith('.B'))}
    a0 = S.adapter_state(m)
    out = S.loop1(m, kept, lr=3e-3, passes=2, T=3.0, seed=0, batch=24)
    assert out['updates'] == 2 * 2 and all(map(lambda x: x == x, out['loss']))
    assert all(torch.equal(before[n], q) for n, q in m.named_parameters() if n in before)       # base weights bit-identical
    a1 = S.adapter_state(m)
    assert any(not torch.equal(a0[k], a1[k]) for k in a0) and any(float(a1[k].abs().sum()) > 0 for k in a1 if k.endswith('.B'))
    assert m._creative.on is False
    assert S.worker_untouched(m, ref, rows, vocab, 'cpu')['passes']                              # still the worker, bit for bit
    # shuffle placebo trains too (same updates)
    S.load_adapter_state(m, a0)
    out2 = S.loop1(m, kept, lr=3e-3, passes=2, T=3.0, seed=0, batch=24, shuffle=True)
    assert out2['updates'] == out['updates']
    assert S.loop1(m, dict(items=[]), 1e-3, 1, 3.0, 0)['updates'] == 0


def test_measures():
    rows = _rows(4)
    row = rows[0]
    p = fewshot.parse(row['prompt'])
    t, _, qs = R.reference(row['kind'], tuple(row['params']))
    good = sampler.TryRec(R.remap(t, qs, p['q_slot']))
    bad = sampler.TryRec(Try.make([(1, p['q_slot'], p['q_slot'])], 20))
    per = S.score_rows([row, rows[1]], [[bad, bad, good, good], [bad, bad]])
    assert per[0]['fit'] and per[0]['right'] and per[0]['first'] == 3 and per[0]['n_fit'] == 2 and per[0]['distinct'] == 1
    assert not per[1]['fit'] and per[1]['first'] is None
    s = S.summarize(per)
    assert s['reach32'] == 0.5 and s['rows_with_fit'] == 1 and s['tries_to_first_fit'] == 3 and s['distinct_fitting'] == 0.5


def test_no_sealed_reads():
    """Everything S1 reads before the model runs (C2 dev / pool, K_new dev) opens no sealed file."""
    seen = []
    orig = builtins.open

    def spy(f, *a, **k):
        seen.append(str(f))
        return orig(f, *a, **k)
    builtins.open = spy
    try:
        R.load_split(DATA, 'dev'); R.load_split(DATA, 'pool')
        S.day(*_fresh()[:1], _rows(2), _fresh()[2], 'cpu', n1=2, n2=2)
        if os.path.exists(os.path.join(S.KNEW, 'MANIFEST.json')):
            from creative import knew
            knew.load_dev(S.KNEW)
    finally:
        builtins.open = orig
    assert seen and not [s for s in seen if any(s.endswith(x) for x in SEALED)], seen


def test_knew_questions_and_reference():
    from creative import fewshot as fs, knew
    r = knew.reference('cube', ())
    assert r is not None and r[1] == 2 and knew.reference('sq_minus', (3,))[1] <= 4
    avoid = set()
    rows = knew.make_questions('sq_minus', knew.PARAMS['sq_minus'], 24, 'kdev', avoid, idx0=64)
    assert [x['id'] for x in rows][:2] == ['knew:kdev:00064', 'knew:kdev:00065'] and len({x['id'] for x in rows}) == 24 and len(avoid) == 24
    for x in rows:
        p = fs.parse(x['prompt'])
        f = knew.fn(x['kind'], tuple(x['params']))
        assert len(p['xs']) == 3 and set(p['xs'] + [p['q']]) <= set(R.DOMAIN) and len(set(p['xs'] + [p['q']])) == 4
        assert p['ys'] == [f(a) for a in p['xs']] and int(x['answer']) == f(p['q']) >= 0 and x['accepted'] == [x['answer']]
        assert not set(p['ys']) & {1, 2, 10, 100}
        assert knew.predictions(p['xs'], p['ys'], p['q']) == {int(x['answer'])}                    # the examples pin the query among ALL rules
    again = knew.make_questions('sq_minus', knew.PARAMS['sq_minus'], 24, 'kdev', set(), idx0=64)
    assert again == rows                                                                           # salt + seed: deterministic
    other = knew.make_questions('sq_minus', knew.PARAMS['sq_minus'], 24, 'ktest', avoid)
    keys = lambda rs: {(x['kind'], tuple(x['params']), tuple(fs.parse(x['prompt'])['xs']), fs.parse(x['prompt'])['q']) for x in rs}
    assert not keys(rows) & keys(other)                                                            # `avoid` keeps TEST off DEV


def test_knew_write_never_reads_test():
    import json, tempfile
    from creative import knew
    kinds = ['sq_minus', 'cube']
    usable = {k: knew.PARAMS[k] for k in kinds}
    avoid, dev_by = set(), {}
    for i, k in enumerate(kinds):
        dev_by[k] = knew.make_questions(k, usable[k], knew.N_DEV, 'kdev', avoid, idx0=i * knew.N_DEV)
    opens, orig = [], builtins.open

    def spy(f, mode='r', *a, **k):
        opens.append((str(f), mode))
        return orig(f, mode, *a, **k)
    with tempfile.TemporaryDirectory() as d:
        builtins.open = spy
        try:
            man = knew.write_data(d, kinds, usable, dev_by, {}, 'unit test', None, smoke=True)
            rows = knew.load_dev(d)
        finally:
            builtins.open = orig
        assert [m for f, m in opens if f.endswith('test.jsonl')] == ['wb']                         # written, never read
        assert len(rows) == 2 * knew.N_DEV and man['test']['n'] == 2 * knew.N_TEST and man['test']['kinds'] == dict(sq_minus=knew.N_TEST, cube=knew.N_TEST)
        assert man['_spec']['kind_hash'] and len(man['test']['sha256']) == 64 and man['dev']['sha256'] != man['test']['sha256']
        assert [r['kind'] for r in rows[:2]] == kinds                                              # interleaved
        with orig(os.path.join(d, 'dev.jsonl'), 'a') as f:
            f.write('{}\n')
        try:
            knew.load_dev(d)
            raise SystemExit('a tampered dev file loaded')
        except AssertionError:
            pass


def _good_bad(rows):
    """Per row: (a try that fits every example, a try that does not), from the row's own kind's reference program."""
    out = []
    for r in rows:
        p = fewshot.parse(r['prompt'])
        t, _, qs = R.reference(r['kind'], tuple(r['params']))
        out.append((sampler.TryRec(R.remap(t, qs, p['q_slot'])), sampler.TryRec(Try.make([(1, p['q_slot'], p['q_slot'])], 20))))
    return out


def test_s3_shaky_window_and_replay_only():
    rows = [r for r in _rows(60) if r['kind'] in ('square', 'last_digit')][:6]
    gb = _good_bad(rows)
    for r, (g, b) in zip(rows, gb):
        p = fewshot.parse(r['prompt'])
        assert S.fits(p, g.t) and not S.fits(p, b.t)
    greedy = [gb[0][0], gb[1][0], gb[2][0], gb[3][0], gb[4][1], gb[5][0]]            # rows 0-3 and 5 pass, row 4 fails
    nfit = {0: 8, 1: 1, 2: 4, 3: 7, 5: 0}                                              # pass rates of the passing rows over 8 samples
    samples = [[gb[i][0]] * nfit[i] + [gb[i][1]] * (8 - nfit[i]) for i in (0, 1, 2, 3, 5)]
    og, orw = S.sampler.greedy_tries, S.legal.raw_samples
    S.sampler.greedy_tries = lambda *a, **k: greedy
    S.legal.raw_samples = lambda m, rs, v, d, n=32, temperature=1.0, level=0, seed=0, bs=2048: samples
    try:
        recs, info = S.shaky_records(None, rows, None, 'cpu', 0)
    finally:
        S.sampler.greedy_tries, S.legal.raw_samples = og, orw
    assert [r['source'] for r in recs] == [rows[i]['id'] for i in (1, 2, 3)]            # 1/8 .. 7/8 kept; 8/8 (too easy), 0/8 (never) and the failing row are not
    assert info['rate_histogram']['8/8'] == 1 and info['rate_histogram']['0/8'] == 1 and info['passing_greedy'] == 5 and info['records'] == 3
    for r in recs:
        assert r['id'].startswith('P:') and r['id'].endswith(':0') and r['accepted'] == [r['answer']]
    # Z's records: an equal-size seeded draw, half skills replay rows and half warm rows, no id twice
    replay = [dict(id=f'sk:{i}') for i in range(50)]
    warm = [dict(id=f'WU2:{i}') for i in range(50)]
    z = S.replay_only_records(replay, warm, 7, seed=3)
    assert len(z) == 7 and sum(r['id'].startswith('sk') for r in z) == 3 and sum(r['id'].startswith('WU2') for r in z) == 4 and len({r['id'] for r in z}) == 7
    assert z == S.replay_only_records(replay, warm, 7, seed=3) and z != S.replay_only_records(replay, warm, 7, seed=4)


def test_s3_measures():
    mk = lambda kind, fit, right, w=2: dict(kind=kind, fit=fit, right=right, written=w, cone=w)
    dev = [mk('square', True, True), mk('last_digit', True, False), mk('affine', False, False), mk('sq_plus', True, True, 4), mk('double_add', False, False)]
    fresh = [mk('add', True, True, 1), mk('mult', True, False)]
    m = S.s3_measures(dev, fresh)
    assert m['stuck_rate'] == 0.4 and m['first_try_right']['near_copy'] == 0.5 and m['first_try_right']['multi_step'] == 1 / 3
    assert m['first_try_right']['practised'] == 0.5 and m['first_try_right']['pooled_dev'] == 0.4
    assert m['written_steps_per_right']['dev'] == 3.0 and m['written_steps_per_right']['practised'] == 1.0 and m['n_right'] == dict(dev=2, practised=1)


def test_s1b_try_marks_match_score_rows():
    m, _, vocab = _fresh()
    rows = _rows(6)
    with S.creative(m, True):
        smp = S.legal.raw_samples(m, rows, vocab, 'cpu', n=40, temperature=3.0, level=0, seed=5)
    pm = S.try_marks(rows, smp)
    assert S.score_marks(pm, (32, 40)) == S.score_rows(rows, smp, ks=(32, 40))
    off = [dict(r, tries=[(0, 0, None)] * 40) for r in pm]
    f = S.score_marks(S.switch_marks(pm, off, 32), (32, 40))
    a = S.score_marks(pm, (32, 40))
    assert [x['right32'] for x in f] == [x['right32'] for x in a] and all(x['n_fit'] <= y['n_fit'] for x, y in zip(f, a))
    assert all(len(r['tries']) == 40 for r in S.switch_marks(pm, off, 32))

def test_day_f_pass1_on_pass2_off():
    m, ref, vocab = _fresh()
    g = torch.Generator().manual_seed(7)
    with torch.no_grad():
        for _, w in S._wrappers(m):
            w.B.copy_(torch.randn(w.B.shape, generator=g) * 0.5)                       # on != off
    rows = _rows(8)
    d = S.day_f(m, rows, vocab, 'cpu', 3.0, 4, 6, seed=5)
    with S.creative(m, True):
        on = S.legal.raw_samples(m, rows, vocab, 'cpu', n=4, temperature=3.0, level=0, seed=5)
    with S.creative(m, False):
        g_off = sampler.greedy_tries(m, rows, vocab, 'cpu')
    assert d['greedy_fit'] == [S.fits(fewshot.parse(r['prompt']), t.t) for r, t in zip(rows, g_off)]
    assert [[x.t for x in t[:4]] for t in d['tries']] == [[x.t for x in t] for t in on]                    # pass 1: adapter on, seed
    more = [i for i, f in enumerate(d['fit1']) if not f]
    assert more and d['drawn']['pass2_rows'] == len(more)
    with S.creative(m, False):
        off = S.legal.raw_samples(m, [rows[i] for i in more], vocab, 'cpu', n=6, temperature=3.0, level=0, seed=1005)
    assert [[x.t for x in d['tries'][i][4:]] for i in more] == [[x.t for x in t] for t in off]            # pass 2: adapter off, seed + 1000
    assert all(len(d['tries'][i]) == (4 if d['fit1'][i] else 10) and len(d['fit'][i]) == len(d['tries'][i]) for i in range(len(rows)))
    assert d['fit_final'] == [any(f) for f in d['fit']] and m._creative.on is False


def test_day_f_feeds_kept_tries():
    m, ref, vocab = _fresh()
    rows = _rows(8)
    d = S.day_f(m, rows, vocab, 'cpu', 3.0, 4, 6, seed=3)
    sd = S.stuck_day(d)
    assert sd['stuck'] == [i for i, f in enumerate(d['greedy_fit']) if not f] and set(sd['tries']) == set(sd['fit']) == set(sd['stuck'])
    kept = S.kept_tries(rows, sd, 0)
    assert kept['rows_stuck'] == len(sd['stuck']) and all(it['i'] in sd['stuck'] for it in kept['items'])
    o = S.kept_origin(kept, d['tries'], 4)
    assert o['kept_tries'] == len(kept['items']) and 0 <= o['share_tries_from_pass2'] <= 1


def test_s1wreport_joins_parents():
    import json, pathlib, tempfile
    tmp_path = pathlib.Path(tempfile.mkdtemp())
    ok = dict(passes=True, proved_wrong_here=dict(flag=False))
    bad = dict(passes=False, proved_wrong_here=dict(flag=True))
    for n, mk in (('a', ok), ('b', bad)):
        (tmp_path / n).mkdir()
        json.dump(dict(marks=mk), open(tmp_path / n / 's1w.json', 'w'))
    r = S.s1wreport(str(tmp_path), ('a', 'b'))
    assert r['passes'] is False and r['proved_wrong'] is False and set(r['per_parent']) == {'a', 'b'}
    assert S.s1wreport(str(tmp_path), ('a',))['passes'] is True and json.load(open(tmp_path / 's1w-report.json'))['parents'] == ['a']


def test_s1freport_joins_parents():
    import json, pathlib, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    for n, p in (('a', True), ('b', False)):
        (tmp / n).mkdir()
        json.dump(dict(marks=dict(passes=p, proved_wrong_here=dict(flag=not p)), night_cost=dict(samples=10 + len(n))), open(tmp / n / 's1f.json', 'w'))
    r = S.s1freport(str(tmp), ('a', 'b'))
    assert r['passes'] is False and r['proved_wrong'] is False and r['night_cost']['a']['samples'] == 11
    assert S.s1freport(str(tmp), ('a',))['passes'] is True and S.s1freport(str(tmp), ('b',))['proved_wrong'] is True


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
