"""CPU tests for prof_train.py (tiny shapes, stub Gemma, synthetic rows; no GPU, no network, no model download). Under 30 s.

  python -m pytest -q test_prof.py        (pytest-style: plain test_* functions with asserts)
  python test_prof.py                     (no pytest needed: a mini runner calls every test_* and prints PASS / FAIL)

The custom_io package is found, in this order: $PROF_PKG_ROOT or $CUSTOM_IO_ROOT (the folder that CONTAINS custom_io/, e.g. the PC job's src-b3g2 / src-ptc),
a custom_io already importable, then `git archive 74d6e92c75 custom_io` of the repo this file sits in (py + caps json only, into a temp dir; offline). Else the tests skip.
What is NOT testable here: CUDA timing, the profiler's CUDA kernels, set_sync_debug_mode, torch.compile with inductor, the real EmbeddingGemma 2.
"""
import contextlib, importlib.util, json, math, os, subprocess, sys, tempfile, time, types, unittest
import numpy as np
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import prof_train as prof                                                    # noqa: E402

COMMIT = '74d6e92c75'
_CACHE = {}


def _find_pkg():
    for var in ('PROF_PKG_ROOT', 'CUSTOM_IO_ROOT'):
        p = os.environ.get(var)
        if p and os.path.isdir(os.path.join(p, 'custom_io')):
            return p
    if importlib.util.find_spec('custom_io') is not None:
        return None                                                          # importable as is
    tmp = tempfile.mkdtemp(prefix='prof_pkg_')
    try:
        top = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True).stdout.strip()
        arc = subprocess.run(['git', '-C', top, 'archive', COMMIT, 'custom_io'], check=True, capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', tmp, '--wildcards', 'custom_io/*.py', 'custom_io/g8a/caps*.json'], input=arc, check=True, capture_output=True)
        return tmp
    except Exception as e:                                                   # noqa: BLE001
        raise unittest.SkipTest(f'no custom_io package: set PROF_PKG_ROOT (git archive {COMMIT} failed: {e!r})')


def argv(arm='PTS', *extra, out=None):
    return ['--arm', arm, '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--updates', '3', '--warmup', '1', '--out',
            out or os.path.join(tempfile.gettempdir(), f'prof_test_{os.getpid()}.json'), *extra]


def world(arm='PTS', *extra):
    key = (arm, extra)
    if key not in _CACHE:
        if 'pkg' not in _CACHE:
            prof.load_pkg(_find_pkg())
            _CACHE['pkg'] = True
        a = prof.build_parser().parse_args(argv(arm, *extra))
        a.accum = a.accum or prof.ARM_INFO[a.arm]['accum']
        _CACHE[key] = (prof.World(a), a)
    return _CACHE[key]


def first_batch(w, a, seed=7):
    return next(w.batches(seed))


# ---------------------------------------------------------------------------------------------------------------------------------- pure functions
def test_pad_counts_hand_example():
    # lens in a random order [4,1,3,2], width 4, k=2: micro-batches [4,1] (widest 4) and [3,2] (widest 3); sorted: [1,2] (2) and [3,4] (4)
    c = prof.pad_counts([4, 1, 3, 2], 4, 2)
    assert (c['real'], c['full'], c['own'], c['sorted']) == (10, 16, 14, 12)
    assert (c['real2'], c['full2'], c['own2'], c['sorted2']) == (30, 64, 50, 40)
    assert [round(x, 6) for x in c['mb_frac']['full']] == [round(5 / 8, 6)] * 2
    assert [round(x, 6) for x in c['mb_frac']['own']] == [round(5 / 8, 6), round(5 / 6, 6)]
    assert [round(x, 6) for x in c['mb_frac']['sorted']] == [0.75, round(7 / 8, 6)]
    one = prof.pad_counts([4, 1, 3, 2], 4, 1)                                # k = 1: every column is the batch's own widest
    assert one['own'] == one['full'] == one['sorted'] == 16


class FakeClock:
    def __init__(self, ts):
        self.ts = list(ts)

    def now(self):
        return self.ts.pop(0)


def test_recorder_exclusive_inclusive():
    rec = prof.Recorder(FakeClock([0.0, 1.0, 3.0, 6.0]))
    assert rec.enter('a') is None                                            # inactive: no clock read, no record
    rec.active = True
    ta = rec.enter('a')                                                      # t = 0
    tb = rec.enter('b')                                                      # t = 1
    rec.exit(tb)                                                             # t = 3   b: 2
    rec.exit(ta)                                                             # t = 6   a: 6 inclusive, 4 exclusive
    assert rec.incl['a'] == 6.0 and rec.incl['b'] == 2.0
    assert rec.excl['a'] == 4.0 and rec.excl['b'] == 2.0
    assert rec.calls['a'] == rec.calls['b'] == 1
    rec.phase = 'bwd'                                                        # hooks firing during backward (checkpoint recompute) are counted, not timed
    assert rec.enter('a') is None and rec.bwd_calls['a'] == 1


class Ev:
    def __init__(self, name, dev, start=None, end=None, cpu_self=0.0):
        self.name, self.device_type, self.self_cpu_time_total = name, dev, cpu_self
        self.time_range = types.SimpleNamespace(start=start, end=end) if start is not None else None


def test_analyze_events_fake_cuda():
    evs = [Ev('gemm', 'DeviceType.CUDA', 0, 10), Ev('softmax', 'DeviceType.CUDA', 5, 20), Ev('gemm', 'DeviceType.CUDA', 30, 40),
           Ev('Memcpy DtoH (Device -> Pageable)', 'DeviceType.CUDA', 45, 46)]
    evs += [Ev('cudaLaunchKernel', 'DeviceType.CPU', cpu_self=2.0) for _ in range(3)] + [Ev('cudaStreamSynchronize', 'DeviceType.CPU', cpu_self=1.0)]
    out = prof.analyze_events(evs, n_updates=1, wall_s=62e-6, is_cuda=True)
    c = out['cuda']
    assert c['kernels_per_update'] == 3                                      # the memcpy is not a kernel
    assert abs(c['kernel_time_ms_per_update'] - 36e-3) < 1e-9                # 10 + 15 + 10 + 1 us
    assert abs(c['gpu_busy_ms_per_update'] - 31e-3) < 1e-9                   # union: [0,20] + [30,40] + [45,46]
    assert abs(c['gpu_busy_fraction_of_wall'] - 0.5) < 1e-9 and abs(c['idle_gap_fraction_of_wall'] - 0.5) < 1e-9
    assert abs(c['mean_kernel_us'] - 35 / 3) < 1e-9
    assert c['cuda_launch_calls_per_update'] == 3 and c['stream_syncs_per_update'] == 1 and c['dtoh_copies_per_update'] == 1
    assert c['top_kernels'][0]['name'] == 'gemm' and c['top_kernels'][0]['count'] == 2
    assert 'verdict' in out['launch_bound']
    cpu_only = prof.analyze_events(evs[4:], 1, 1e-3, is_cuda=False)
    assert cpu_only['cuda'] is None


def test_analyze_events_kernels_only_on_cpu_ops():
    cpu_op = Ev('aten::mm', 'DeviceType.CPU', cpu_self=3.0)
    cpu_op.kernels = [types.SimpleNamespace(name='gemm', device=0, duration=10.0), types.SimpleNamespace(name='gemm', device=0, duration=14.0)]
    out = prof.analyze_events([cpu_op], 1, 1e-4, is_cuda=True)
    c = out['cuda']
    assert 'warning' in out and c['kernels_per_update'] == 2 and c['gpu_busy_fraction_of_wall'] is None
    assert out['launch_bound']['verdict'].startswith('GPU mostly idle')              # 24 us of kernels in 100 us of wall
    none = prof.analyze_events([Ev('aten::mm', 'DeviceType.CPU', cpu_self=3.0)], 1, 1e-4, is_cuda=True)
    assert none['cuda'] is None and 'no CUDA kernels' in none['warning']


def test_aggregate_sync_warnings():
    recs = [('/a/f.py', 10, 'x')] * 4 + [('/a/g.py', 5, 'y')]
    rows = prof.aggregate_sync_warnings(recs, 2)
    assert rows[0]['where'] == 'f.py:10' and rows[0]['per_update'] == 2.0 and rows[1]['per_update'] == 0.5


def test_parse_variants():
    assert prof.parse_variants('prefetch,sortpad+bigmb') == ['bigmb', 'sortpad', 'prefetch']
    assert prof.parse_variants('') == [] and prof.parse_variants('baseline') == []
    for bad in ('nope', 'sortpad,sortpad_tokw', 'compile,compile_ro'):
        try:
            prof.parse_variants(bad)
        except SystemExit:
            continue
        raise AssertionError(f'{bad!r} should be refused')


def test_instrument_wrap_load_and_restore():
    class FakeEG:
        def load(self, device):
            self.m = nn.Linear(2, 2)
    rec = prof.Recorder(prof.Clock(torch.device('cpu')))
    rec.active = True
    inst = prof.Instrument(nn.Linear(1, 1), rec)
    eg = FakeEG()
    inst._wrap_load(eg)
    eg.load('cpu')
    eg.m(torch.zeros(1, 2))
    assert rec.calls['eg.gemma_forward'] == 1
    inst.remove()
    assert 'load' not in eg.__dict__                                         # the instance attribute is gone, the class method is back
    eg.m(torch.zeros(1, 2))
    assert rec.calls['eg.gemma_forward'] == 1                                # hook removed
    # the whole model: install + remove leaves no hooks and no instance attributes behind
    w, a = world('PTS')
    m = w.new_model(0)
    before = set(m.__dict__)
    inst = prof.Instrument(m, prof.Recorder(prof.Clock(w.device))).install()
    assert any(mod._forward_hooks for mod in m.modules()) and inst.names
    inst.remove()
    assert not any(mod._forward_hooks or mod._forward_pre_hooks for mod in m.modules())
    assert set(m.__dict__) == before


# ---------------------------------------------------------------------------------------------------------------------------------- sortpad
def _ids(parts):
    return [[r['id'] for r in p['rows']] for p in parts]


def test_sortpad_same_rows_and_widths():
    w, a = world('PTS')
    b = first_batch(w, a)
    base = prof.Trainer(w, a, [], accum=4)
    sp = prof.Trainer(w, a, ['sortpad'], accum=4)
    try:
        pb = base._split(prof.PK.D.to_device(base._prep(b), w.device))
        ps = sp._split(prof.PK.D.to_device(sp._prep(b), w.device))
        ib, is_ = _ids(pb), _ids(ps)
        assert sorted(sum(ib, [])) == sorted(sum(is_, [])) == sorted(r['id'] for r in b['rows']), 'the same 16 rows'
        assert [len(x) for x in ib] == [len(x) for x in is_], 'same micro-batch sizes'
        T = b['prompt_ids'].shape[1]
        widths = [p['prompt_ids'].shape[1] for p in ps]
        assert widths == sorted(widths) and widths[-1] <= T, 'sorted: widths non-decreasing'
        lens = {r['id']: int(m.sum()) for r, m in zip(b['rows'], b['prompt_mask'])}
        for p in ps:
            assert p['prompt_ids'].shape[1] == max(lens[i] for i in [r['id'] for r in p['rows']]), 'trimmed to its own widest row'
            assert p['prompt_mask'].shape == p['prompt_ids'].shape
        by_id = {r['id']: i for i, r in enumerate(b['rows'])}
        for p in ps:                                                          # each row keeps its own ids; only padding columns were cut
            for j, r in enumerate(p['rows']):
                n = int(p['prompt_mask'][j].sum())
                assert torch.equal(p['prompt_ids'][j, :n], b['prompt_ids'][by_id[r['id']], :n])
        assert any(x['prompt_ids'].shape[1] < T for x in ps)
    finally:
        base.close(); sp.close()


def nll_sum(tr, cpu_batch, rows_weighted=False):
    """sum over micro-batches of loss_k * n_k (n_k = supervised tokens of the micro-batch: what a token-mean loss multiplies back to), fp32, no grad.
    rows_weighted: n_k = rows in the micro-batch (a per-row mean loss)."""
    dev = prof.PK.D.to_device(tr._prep(cpu_batch), tr.device)
    tot, n_all = 0.0, 0
    with torch.no_grad():
        for mb in tr._split(dev):
            mb = {k: v for k, v in mb.items() if not k.startswith('_')}
            box = []
            with prof.count_ce_tokens(box):
                l = tr.model.loss(mb)
            l = l[0] if isinstance(l, tuple) else l
            n = len(mb['rows']) if rows_weighted else int(sum(box).item())
            tot += float(l) * n
            n_all += n
    return tot, n_all


def test_sortpad_total_nll_matches_plain_arm():
    w, a = world('PTS')
    b = first_batch(w, a)
    base, sp = prof.Trainer(w, a, [], accum=4), prof.Trainer(w, a, ['sortpad'], accum=4)
    try:
        assert all(torch.equal(p, q) for p, q in zip(base.model.parameters(), sp.model.parameters())), 'same seeded init'
        tb, nb = nll_sum(base, b)
        ts, ns = nll_sum(sp, b)
        assert nb == ns > 0, 'same number of supervised tokens'
        assert abs(tb - ts) <= 1e-4 * abs(tb), (tb, ts)
    finally:
        base.close(); sp.close()


def test_sortpad_row_loss_sum_matches_b3g2_pinned():
    w, a = world('B3G2')
    b = first_batch(w, a)
    base, sp = prof.Trainer(w, a, [], accum=4), prof.Trainer(w, a, ['sortpad'], accum=4)
    try:
        k0 = prof.rounds_needed(w, [b])
        undo = [prof.pin_stochastic(base, k0), prof.pin_stochastic(sp, k0)]
        tb, nb = nll_sum(base, b, rows_weighted=True)
        ts, ns = nll_sum(sp, b, rows_weighted=True)
        for u in undo:
            u()
        assert nb == ns == len(b['rows'])
        assert abs(tb - ts) <= 1e-4 * max(abs(tb), 1.0), (tb, ts)
    finally:
        base.close(); sp.close()


# ---------------------------------------------------------------------------------------------------------------------------------- timers
def test_timers_nonnegative_and_sum_to_wall():
    w, a = world('PTS')
    tr = prof.Trainer(w, a, [], accum=4, batch_seed=3)
    try:
        tr.update(); tr.update()
        tr.instrument('top')
        for _ in range(3):
            t0 = time.perf_counter()
            _, st, sec = tr.update(timed=True)
            outer = time.perf_counter() - t0
            assert all(v >= 0 for v in st.values()), st
            parts = sum(v for k, v in st.items() if k != 'wall')
            assert abs(parts - outer) <= 0.05 * outer, (parts, outer)          # fetch + prep + h2d + split + forward + backward + clip + opt + other
            assert abs(st['wall'] - outer) <= 0.05 * outer
            assert all(s['excl'] >= 0 and s['incl'] >= s['excl'] - 1e-12 for s in sec.values())
            assert sum(s['excl'] for s in sec.values()) <= st['forward'] * 1.02, 'sections are inside the forward stage'
            assert st['forward'] > 0 and st['backward'] > 0 and st['opt'] > 0
    finally:
        tr.close()


# ---------------------------------------------------------------------------------------------------------------------------------- variants
def test_every_variant_runs_one_update_on_cpu():
    w, a = world('PTS')
    for name in prof.VARIANTS:
        if name in ('baseline',) or name.startswith('compile'):
            continue
        tr = prof.Trainer(w, a, [name], accum=4, batch_seed=5)
        try:
            loss, _, _ = tr.update()
            assert math.isfinite(float(loss)), name
        finally:
            tr.close()


def test_compile_skips_cleanly_on_cpu():
    w, a = world('PTS')
    for name in ('compile', 'compile_ro'):
        try:
            prof.Trainer(w, a, [name], accum=4).close()
        except prof.Skip as e:
            assert 'CPU' in str(e)
        else:
            raise AssertionError('compile should skip on CPU without --compile-cpu')
    out = prof.sec_bench(w, prof.build_parser().parse_args(argv('PTS', '--bench-list', 'baseline;compile', '--bench-rounds', '1')))
    assert 'skipped' in out['specs']['compile']['runs'][0] and out['specs']['baseline']['s_per_update_median'] > 0


def test_prefetch_identical_and_same_losses():
    w, a = world('PTS')
    assert prof.check_prefetch_identical(w, a, 4)
    t1, t2 = prof.Trainer(w, a, [], accum=4, batch_seed=9), prof.Trainer(w, a, ['prefetch'], accum=4, batch_seed=9)
    try:
        for _ in range(2):
            assert abs(float(t1.update()[0]) - float(t2.update()[0])) < 1e-6
    finally:
        t1.close(); t2.close()


def test_sweep_catches_oom():
    w, a = world('PTS')
    a2 = prof.build_parser().parse_args(argv('PTS', '--sweep-warmup', '1', '--sweep-updates', '1'))
    a2.accum = 4
    orig = prof.Trainer.update

    def update(self, timed=False):
        if self.accum == 8:
            raise RuntimeError('CUDA out of memory. Tried to allocate 20.00 GiB')
        return orig(self, timed)
    prof.Trainer.update = update
    try:
        out = prof.sec_sweep(w, a2)
    finally:
        prof.Trainer.update = orig
    by = {p['accum']: p for p in out['points']}
    assert sorted(by) == [1, 2, 4, 8, 16, 32]
    assert by[8]['oom'] is True and by[8]['s_per_update'] is None
    assert all(by[k]['oom'] is False and by[k]['s_per_update'] > 0 for k in (1, 2, 4, 16, 32))


# ---------------------------------------------------------------------------------------------------------------------------------- end to end
def test_main_sections_and_equiv_end_to_end():
    w, a = world('PTS')
    d = tempfile.mkdtemp(prefix='prof_out_')
    out = os.path.join(d, 'r.json')
    res = prof.main(argv('PTS', '--sections', 'breakdown,throughput,profiler,padding,syncs', '--pad-updates', '6', '--equiv-check', '--equiv-list',
                         'sortpad;sortpad_tokw;eg_sorted;eg_once;sortpad,oldw', '--curve-updates', '4', '--equiv-accum1', 'yes', '--equiv-precisions', 'fp32,bf16', out=out))
    S = res['sections']
    assert all('error' not in S[k] for k in S), {k: S[k].get('error') for k in S}
    assert 'skipped' in S['syncs'] and S['profiler']['cuda'] is None                  # CPU: no sync audit, no CUDA kernels
    for k in ('arm', 'rung', 'accum', 'batch', 'device', 'torch'):                      # every number carries its labels
        assert k in res['meta'] and all(k in S[s]['tag'] for s in ('breakdown', 'throughput', 'profiler', 'padding', 'equiv'))
    assert S['padding']['by_accum']['4']['prompt']['frac_real_sorted_own_widest'] > S['padding']['by_accum']['4']['prompt']['frac_real_full_width']
    for f in ('r.json', 'r.md', 'r.profiler.json', 'r.profiler.md'):
        assert os.path.getsize(os.path.join(d, f)) > 100, f
    eq = S['equiv']['specs']
    ref = S['equiv']['reference']['fp32']
    assert ref['baseline_rerun']['grad_rel_l2'] < 1e-12                                # deterministic on CPU
    assert eq['eg_sorted']['fp32']['grad_rel_l2'] < 1e-5 and eq['eg_sorted']['fp32']['abs_loss_diff'] < 1e-5
    # the maths the README states: token-mean models change the weighting when the partition changes; sortpad_tokw restores accum=1's gradient exactly
    assert abs(eq['sortpad_tokw']['fp32']['grad_cos'] - ref['baseline_accum1_fullbatch']['grad_cos']) < 1e-6
    assert eq['sortpad']['fp32']['grad_cos'] < 1 - 1e-6 and eq['sortpad']['fp32']['grad_cos'] > 0.9
    assert 'curve' in eq['sortpad'] and eq['sortpad']['curve']['updates'] == 4
    # PREREG-eg-once.md checks: E1 / E2 ran because eg_once is in the list (stub front: plumbing), E3 verdicts, E4 not the registered window with 4 updates
    assert S['equiv']['E1']['passed'] and S['equiv']['E2']['passed'] and S['equiv']['E1']['eg_once_stats']['misses'] == 0
    assert eq['eg_once']['E3_verdict'] == 'PASS' and eq['eg_sorted']['E3_verdict'] == 'PASS'
    assert eq['sortpad']['E3_verdict'].startswith('NOT EXACT') and eq['sortpad']['weighting']['weighting_changes'] is True
    assert eq['sortpad,oldw']['E3_verdict'] == 'PASS' and eq['sortpad,oldw']['fp32']['grad_cos'] >= 1 - 1e-9
    assert eq['sortpad']['curve']['E4']['registered_window'] is False and eq['eg_once']['curve']['E4']['mean_abs_diff'] < 1e-6
    assert os.path.getsize(os.path.join(d, 'r.md')) > 1000 and 'E1: eg_once' in open(os.path.join(d, 'r.md')).read()


def test_b3g2_padding_has_round_stats():
    w, a = world('B3G2')
    a2 = prof.build_parser().parse_args(argv('B3G2', '--pad-updates', '4', '--pad-rounds-updates', '3'))
    a2.accum = 4
    out = prof.sec_padding(w, a2)
    assert 'b3g2_rounds' in out and out['b3g2_rounds']['random']['mean_rounds_per_row'] >= 4 and out['units'] == 'bytes'


# ---------------------------------------------------------------------------------------------------------------------------------- PREREG-eg-once.md
def _noisy_pair(eps_old, eps_once, seed=0):
    g = torch.Generator().manual_seed(seed)
    P, D, R = 800, 64, 8
    a = torch.randn(P, D, generator=g)
    mk = lambda eps, sd: a + eps * torch.randn(P, D, generator=torch.Generator().manual_seed(sd))
    return a, mk(eps_old, 1), mk(eps_once, 2), torch.arange(R).repeat_interleave(P // R), R


def test_e1_rules_as_registered():
    ok = prof.e1_metrics(*_noisy_pair(0.02, 0.02))
    assert ok['passed'] and ok['rule3_gap_le_1_5x_old_spread'] and 0.5 < ok['gap_over_spread'] < 1.5
    r3 = prof.e1_metrics(*_noisy_pair(0.02, 0.025))                                  # positions and rows fine, but the gap is 1.55 x the old path's own spread
    assert r3['rule1_every_position_cos_ge_0_998'] and r3['rule2_every_row_mean_cos_ge_0_9995'] and not r3['rule3_gap_le_1_5x_old_spread'] and not r3['passed']
    bad = prof.e1_metrics(*_noisy_pair(0.02, 0.05))
    assert not bad['rule1_every_position_cos_ge_0_998'] and not bad['rule2_every_row_mean_cos_ge_0_9995'] and bad['once_vs_old']['rows_below_limit'] > 0
    a, _, _, rid, R = _noisy_pair(0, 0)
    same = prof.e1_metrics(a, a.clone(), a.clone(), rid, R)                          # identical everywhere: spread 0 and gap 0 pass
    assert same['passed'] and same['gap_over_spread'] is None


def test_e2_e4_metrics():
    a = torch.randn(10, 4)
    assert prof.e2_metrics(a, a + 5e-5)['passed'] and not prof.e2_metrics(a, a + 2e-4)['passed']
    old = np.linspace(5, 0.3, 300)
    assert prof.e4_metrics(old, old + 0.005)['passed']
    off = prof.e4_metrics(old, old + 0.03)
    assert not off['passed'] and abs(off['mean_abs_diff'] - 0.03) < 1e-9 and off['window_updates'] == [101, 300]
    jitter = old + np.where(np.arange(300) % 2, 0.019, -0.019)                       # mean |d| 0.019 <= 0.02 and the means agree: passes
    assert prof.e4_metrics(old, jitter)['passed']
    bias = prof.e4_metrics(old, old + np.where(np.arange(300) < 100, 0.0, 0.015))     # mean |d| 0.015 <= 0.02 but the means differ by 0.015 > 0.01: fails
    assert not bias['passed'] and bias['mean_abs_diff'] <= 0.02 < 0.5 and bias['diff_of_means'] > 0.01
    short = prof.e4_metrics(old[:50], old[:50])
    assert short['registered_window'] is False and short['passed'] is False


def test_eg_once_serves_exactly_the_old_tensors_and_falls_back():
    w, a = world('PTS')
    b = first_batch(w, a)
    eg = w.eg
    prompts, T = [r['prompt'] for r in b['rows']], b['prompt_ids'].shape[1]
    dev = torch.device('cpu')
    old = [eg.encode(prompts[i:i + 4], T, dev) for i in range(0, 16, 4)]
    old = [(h.clone(), p.clone()) for h, p in old]
    oc = prof.OnceCache(eg, budget=64).install()                                      # 64 padded tokens per Gemma chunk: several chunks
    try:
        oc.precompute(prompts, dev)
        assert oc.chunks > 1 and oc.prompts == len(set(prompts))
        for i, (h0, p0) in zip(range(0, 16, 4), old):
            h, p = eg.encode(prompts[i:i + 4], T, dev)
            assert h.dtype == h0.dtype and h.shape == h0.shape == (4, T, 768) and torch.equal(h, h0) and torch.equal(p, p0)
        assert oc.hits == 4 and oc.misses == 0
        h, _ = eg.encode(prompts[:3], T, dev, chars=False)[0], None                  # pooled only
        assert h is None
        eg.encode(prompts[:2] + ['a prompt that was never encoded'], T, dev)         # one uncached prompt: the whole call takes the old path
        assert oc.misses == 1
        assert 'encode_texts' not in eg.__dict__                                       # tape strings are never intercepted
    finally:
        oc.uninstall()
    assert 'encode' not in eg.__dict__
    # chunking: ascending token length, padded size of every chunk <= budget unless one row alone is longer
    al = {p: len(eg.align(p)[0]) for p in prompts}
    oc2 = prof.OnceCache(eg, budget=80)
    sizes = []
    orig = oc2.orig_compute
    oc2.orig_compute = lambda ch, T_, d, chars: (sizes.append((len(ch), max(al[p] for p in ch))), orig(ch, T_, d, chars))[1]
    oc2.precompute(prompts, dev)
    assert all(n * L <= 80 or n == 1 for n, L in sizes) and sum(n for n, _ in sizes) == len(set(prompts))


def test_eg_once_same_loss_and_gradient_and_stats():
    w, a = world('PTS')
    b = first_batch(w, a)
    base = prof.Trainer(w, a, [], accum=4)                    # one Trainer at a time: eg_once patches the EG object that every Trainer of this world shares
    try:
        lb, gb = base.loss_and_grad(b)
    finally:
        base.close()
    once = prof.Trainer(w, a, ['eg_once'], accum=4)
    try:
        lo, go = once.loss_and_grad(b)
        assert lb == lo and torch.equal(gb, go)
        st = once.variant_stats()['eg_once']
        assert st['encode_calls_old_path'] == 0 and st['encode_calls_from_cache'] == 4 and st['gemma_chunks'] >= 1 and st['prompts_encoded'] == len(set(r['prompt'] for r in b['rows']))
    finally:
        once.close()
    try:
        prof.parse_variants('eg_once,eg_sorted')
    except SystemExit:
        pass
    else:
        raise AssertionError('eg_once and eg_sorted both replace encode')


def test_oldw_restores_old_weights_and_sortpad_is_flagged():
    w, a = world('PTS')
    b = first_batch(w, a)
    base = prof.Trainer(w, a, [], accum=4)
    lb, gb = base.loss_and_grad(b)
    base.close()
    for spec in ('sortpad,oldw', 'bigmb,oldw', 'sortpad,bigmb,oldw'):
        tr = prof.Trainer(w, a, prof.parse_variants(spec), accum=4)
        try:
            l, g = tr.loss_and_grad(b)
        finally:
            tr.close()
        assert abs(l - lb) <= 1e-6 * abs(lb), spec
        assert prof.grad_compare(gb, g)['grad_rel_l2'] < 1e-5, spec
    plain = prof.weighting_report(w, a, b, 'sortpad')
    assert plain['token_mean_per_micro_batch'] and plain['weighting_changes'] and plain['verdict'].startswith('NOT EXACT') and plain['weight_ratio_max'] > 1.001
    assert prof.weighting_report(w, a, b, 'sortpad,oldw')['verdict'] == 'per-token weights restored by oldw'
    assert prof.weighting_report(w, a, b, 'eg_once')['weighting_changes'] is False
    assert prof.weighting_report(w, a, b, 'sortpad_tokw')['weighting_changes'] is True
    w2, a2 = world('B3G2')
    try:
        prof.Trainer(w2, a2, ['oldw'], accum=4).close()
    except prof.Skip:
        pass
    else:
        raise AssertionError('oldw is for the plain arms')
    rep = prof.weighting_report(w2, a2, first_batch(w2, a2), 'sortpad')
    assert rep['token_mean_per_micro_batch'] is False and rep['weighting_changes'] is None


def test_count_pass_matches_real_forward_and_restores_model():
    w, a = world('PTS')
    b = first_batch(w, a)
    tr = prof.Trainer(w, a, [], accum=1)
    try:
        dev = prof.PK.D.to_device(b, w.device)
        before = {k: id(v) for k, v in tr.model.__dict__.items()}
        cnt, red = prof.count_pass(tr.model, dev)
        assert {k: id(v) for k, v in tr.model.__dict__.items()} == before and red == 'mean'
        box = []
        with torch.no_grad(), prof.count_ce_tokens(box):
            tr.model.loss(dev)
        assert int(cnt.sum()) == int(sum(box)) and cnt.shape == (len(b['rows']),) and int(cnt.min()) > 0
    finally:
        tr.close()


def test_run_e1_e2_with_a_batch_shape_dependent_gemma():
    """A stub Gemma whose output shifts a little with the padded batch length (like kernel rounding does): the old path then has a spread, and eg_once a gap of its own."""
    class Noisy(prof._StubGemma):
        def forward(self, input_ids, attention_mask):
            out = super().forward(input_ids, attention_mask)
            m = attention_mask[..., None].to(out.last_hidden_state.dtype)
            out.last_hidden_state = out.last_hidden_state + 2e-3 * math.cos(0.37 * input_ids.shape[1]) * m
            return out
    w, a = world('PTS')
    b = first_batch(w, a)
    a2 = prof.build_parser().parse_args(argv('PTS'))
    a2.accum = 4
    w.eg.load(w.device)
    saved = w.eg.m
    w.eg.m = Noisy().eval()
    try:
        e1 = prof.run_e1(w, a2, b)
    finally:
        w.eg.m = saved
    assert e1['old_vs_old_half_accum']['max_row_gap'] > 0 and e1['once_vs_old']['max_row_gap'] > 0, 'the noise reached the vectors'
    assert e1['eg_once_stats']['misses'] == 0 and e1['registered_setting'] is False
    for k in ('rule1_every_position_cos_ge_0_998', 'rule2_every_row_mean_cos_ge_0_9995', 'rule3_gap_le_1_5x_old_spread', 'passed', 'gap_over_spread'):
        assert k in e1
    e2 = prof.run_e2(w, a2, b)
    assert e2['passed'] and e2['rows'] == min(64, len(b['rows']))


ALL = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]


def main():
    bad, t_all = 0, time.time()
    for n, f in ALL:
        t0 = time.time()
        try:
            f()
            print(f'PASS {n} ({time.time() - t0:.1f}s)', flush=True)
        except unittest.SkipTest as e:
            print(f'SKIP {n}: {e}', flush=True)
        except Exception:                                                    # noqa: BLE001
            import traceback
            bad += 1
            print(f'FAIL {n} ({time.time() - t0:.1f}s)', flush=True)
            traceback.print_exc()
    print(f'{len(ALL) - bad} of {len(ALL)} passed in {time.time() - t_all:.1f}s', flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
