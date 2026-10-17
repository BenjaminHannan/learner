"""CPU tests for defer.py (the deferred batched writer, attack A) and prof_launch.py. Tiny shape, stub Gemma, synthetic rows, fp32 on the CPU; no GPU, no network.

  python test_defer.py                         (a mini runner calls every test_* and prints PASS / FAIL / SKIP; no pytest needed)
  DEFER_REAL_SHAPE=1 python test_defer.py      (adds two tests at the REAL 3M model shape (4,023,302 params): T5 counts, one 64-row micro-batch of batch 256 / accum 4, K pinned to 16, and the saved-for-backward bytes at K 16 (64 rows) and K 32 (16 rows): about 3 minutes, 5 GB, 2 threads;
                                                the synthetic prompts are cut at 700 letters (DEFER_REAL_LETTERS=0: the caps' full 2000, about 11 GB peak, which the shared 16 GB box killed once);
                                                op and sync-site counts do not depend on the prompt width)
  python -m pytest -q test_defer.py            (works too)

What is measured: values (loss, auxiliaries, gradients, RNG states), ATen dispatches and host-sync CALL SITES per micro-batch, on the CPU. What is NOT measured: any CUDA time, kernel launches,
bf16 on a GPU, GPU memory. A "sync call site" here is a call of tolist / item / __bool__ / __int__ / __float__ / __index__ / cpu / numpy / nonzero / a device-targeted .to / torch.tensor(device=) /
torch.nonzero made from Python; on the CPU nothing waits, so the count says how many calls WOULD wait on a GPU if their tensor lived there. Host-only calls (for example the micro-batch's one
`int(torch.randint(...))`, a CPU generator draw) are counted too; the per-site table in the report tells them apart.

The custom_io package is found as in test_prof.py: $PROF_PKG_ROOT or $CUSTOM_IO_ROOT (the folder that CONTAINS custom_io/), else an importable one, else `git archive 74d6e92c75 custom_io`.
Tests T1-T8 are those of the S2 task: T1 values, T2 RNG, T3 coverage, T4 fallbacks, T5 counts, T6 teardown, T7 20-update run, T8 the runner. Added after review: the same T1 / T3 with a NON-TRIVIAL ByteWriter.right
(the real one is all False at init, which hides the right[] scatter, the hit counters and the stop label), a mutation test of those marks, saved-for-backward bytes (memory proxy), op counts by prompt width,
the instance-_loss fallback, and registration of the real exact arms. The runner prints passed / skipped / failed apart (a skip is not a pass).
"""
import collections, contextlib, importlib.util, inspect, json, math, os, random, subprocess, sys, tempfile, time, types, unittest
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
PROFDIR = os.path.normpath(os.path.join(HERE, '..', 'prof'))
for _p in (PROFDIR, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import prof_train as prof                                                    # noqa: E402
import defer                                                                 # noqa: E402
import prof_launch                                                           # noqa: E402

torch.set_num_threads(1)                                                      # the bitwise comparisons below need one thread (with 2 threads even baseline vs baseline can differ in the last bit); only the real-shape test uses DEFER_THREADS
COMMIT = '74d6e92c75'
_CACHE = {}
G_MOD = 'custom_io.models.b3g2'


def _find_pkg():
    for var in ('PROF_PKG_ROOT', 'CUSTOM_IO_ROOT'):
        p = os.environ.get(var)
        if p and os.path.isdir(os.path.join(p, 'custom_io')):
            return p
    if importlib.util.find_spec('custom_io') is not None:
        return None
    tmp = tempfile.mkdtemp(prefix='defer_pkg_')
    try:
        top = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True).stdout.strip()
        arc = subprocess.run(['git', '-C', top, 'archive', COMMIT, 'custom_io'], check=True, capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', tmp, '--wildcards', 'custom_io/*.py', 'custom_io/g8a/caps*.json'], input=arc, check=True, capture_output=True)
        return tmp
    except Exception as e:                                                   # noqa: BLE001
        raise unittest.SkipTest(f'no custom_io package: set PROF_PKG_ROOT (git archive {COMMIT} failed: {e!r})')


def _load():
    if 'pkg' not in _CACHE:
        prof.load_pkg(_find_pkg())
        prof_launch.register(defer.NEW_VARIANTS)
        _CACHE['pkg'] = True
    return prof.PK


def argv(arm='B3G2', *extra, out=None):
    return ['--arm', arm, '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--updates', '3', '--warmup', '1', '--out',
            out or os.path.join(tempfile.gettempdir(), f'defer_test_{os.getpid()}.json'), *extra]


def world(arm='B3G2', *extra):
    key = (arm, extra)
    if key not in _CACHE:
        _load()
        a = prof.build_parser().parse_args(argv(arm, *extra))
        a.accum = a.accum or prof.ARM_INFO[a.arm]['accum']
        _CACHE[key] = (prof.World(a), a)
    return _CACHE[key]


def full_batch(w, seed=7):
    return prof.PK.D.to_device(next(w.batches(seed)), w.device)


def micro_batch(w, i, seed=7, k=4):
    return prof.PK.TR.split_batch(full_batch(w, seed), k)[i]


def pick_rows(mb, idx):
    return {k: ([v[i] for i in idx] if isinstance(v, list) else v[torch.tensor(idx)] if torch.is_tensor(v) else v) for k, v in mb.items()}


@contextlib.contextmanager
def forced_ks(k):
    G = sys.modules[G_MOD]
    old = G.KS
    if k is not None:
        G.KS = (k,) if isinstance(k, int) else tuple(k)
    try:
        yield
    finally:
        G.KS = old


def flat(grads):
    return torch.cat([g.flatten() for g in grads])


def run_one(w, a, names, mb, K=None, seed=5, tweak=None, amp=contextlib.nullcontext, backward=True, spy=None):
    """A fresh Trainer (same init, same gap / drill streams) with `names`, ONE m.loss(mb) (+ backward), RNG states right after the loss. -> dict."""
    tr = prof.Trainer(w, a, names, accum=4)
    try:
        m = tr.model
        if tweak:
            tweak(m)
        if spy:
            spy(m)
        torch.manual_seed(seed)
        with forced_ks(K), amp():
            loss, aux = m.loss(mb)
        rng = (torch.get_rng_state(), m._gap_rng.getstate(), m._drill_rng.getstate())
        grads = None
        if backward:
            loss.backward()
            grads = [p.grad.detach().double().clone() if p.grad is not None else torch.zeros(p.shape, dtype=torch.float64) for p in m.parameters()]
        return dict(loss=loss.detach(), aux=aux, grads=grads, rng=rng, stats=tr.variant_stats(), model=m, variants=list(tr.variants))
    finally:
        tr.close()


def f(x):
    return None if x is None else float(x)


def compare(r0, r1):
    """The T1 numbers of two run_one results."""
    l0, l1 = float(r0['loss']), float(r1['loss'])
    out = dict(loss_rel=abs(l1 - l0) / max(abs(l0), 1e-300), loss_bitwise=bool(torch.equal(r0['loss'], r1['loss'])), aux_keys_equal=sorted(r0['aux']) == sorted(r1['aux']), aux_bad=[])
    for k in r0['aux']:
        x, y = f(r0['aux'][k]), f(r1['aux'][k])
        if (x is None) != (y is None) or (x is not None and abs(x - y) > 1e-6 * max(1.0, abs(x))):
            out['aux_bad'].append((k, x, y))
        if isinstance(r0['aux'][k], (int, bool)) or (not torch.is_tensor(r0['aux'][k]) and isinstance(r0['aux'][k], float) and k in ('rounds', 'stop_w')):
            if r0['aux'][k] != r1['aux'][k]:
                out['aux_bad'].append((k, 'ints differ', r0['aux'][k], r1['aux'][k]))
    if r0['grads'] is not None:
        coss, mx, mxrel = [], 0.0, 0.0
        for g0, g1 in zip(r0['grads'], r1['grads']):
            n0, n1 = g0.norm().item(), g1.norm().item()
            coss.append(1.0 if n0 == 0 and n1 == 0 else 0.0 if n0 == 0 or n1 == 0 else float(g0.flatten() @ g1.flatten() / (n0 * n1)))
            mx = max(mx, float((g1 - g0).abs().max()))
        a0, a1 = flat(r0['grads']), flat(r1['grads'])
        out.update(grad_cos_min=min(coss), grad_cos_all=float(a0 @ a1 / (a0.norm() * a1.norm())), grad_max_abs=mx, grad_max_rel=mx / max(float(a0.abs().max()), 1e-300),
                   grad_rel_l2=float((a1 - a0).norm() / a0.norm()), grad_bitwise=bool(torch.equal(a0, a1)), n_params_tensors=len(coss))
    out['rng_equal'] = bool(torch.equal(r0['rng'][0], r1['rng'][0])) and r0['rng'][1] == r1['rng'][1] and r0['rng'][2] == r1['rng'][2]
    return out


def say(*a):
    print('   ', *a, flush=True)


def check_close(c, what, loss_rel=1e-6, cos=0.999999):
    assert c['aux_keys_equal'], what
    assert not c['aux_bad'], (what, c['aux_bad'])
    assert c['loss_rel'] <= loss_rel, (what, c['loss_rel'])
    assert c['grad_cos_min'] >= cos, (what, c['grad_cos_min'])
    assert c['rng_equal'], what


RIGHT_MARGIN = []                                                              # smallest distance of nll * 10 to an integer seen by nontrivial_right's stand-in (see there)


@contextlib.contextmanager
def nontrivial_right():
    """ByteWriter.right made NON-TRIVIAL for BOTH arms (class-level, restored on exit; defer's source-hash guard for `right` is moved with it).

    Why: at init no writer is right about anything, so the real `right` is False for every pair and call_acc = eos_acc = right_last = 0 and the stop label (`settled(right)`) is all True in both
    arms. Then a scrambled right[] scatter, swapped call / EOS hit counters or a wrong stop label still give "every aux key equal". This stand-in is a deterministic function of the target AND of
    the pair's mean target nll, quantised at 0.1, so it differs from pair to pair (rounds, rows, call vs EOS-only) and mixes True and False. It is a TEST DEVICE for the bookkeeping (scatter,
    counters, label), not a statement about the real writer's accuracy.
    Fragility, and the guard: a pair whose nll * 10 sits within rounding of an integer could flip between the arms (the arms differ by about 1e-7 relative). The stand-in records the smallest
    distance of nll * 10 to an integer in RIGHT_MARGIN; the tests assert it is >= 5e-5 (that is 5e-6 in nll, about 8 times the rounding between the arms, which is 6e-7 in nll), so a flip fails loudly as a
    margin error and not as a mystery."""
    import custom_io.models.writer as W
    BW = W.ByteWriter
    orig, old_hash = BW.__dict__['right'], defer.SRC_HASH_WRITER['right']

    def right(logp, tgt):
        v = tgt != -100
        lp = logp.gather(-1, tgt.clamp(min=0)[..., None])[..., 0]
        q = -(lp * v).sum(1) / v.sum(1).clamp(min=1) * 10.0
        if bool(v.any(1).any()):
            RIGHT_MARGIN.append(float((q - q.round()).abs()[v.any(1)].min().detach()))
        return v.any(1) & (((tgt.clamp(min=0).sum(1) + q.floor().long()) % 3) != 2)
    BW.right = staticmethod(right)
    defer.SRC_HASH_WRITER['right'] = defer.src_hash(right)
    del RIGHT_MARGIN[:]
    try:
        yield
    finally:
        BW.right = orig
        defer.SRC_HASH_WRITER['right'] = old_hash


AUX_LOG = []                                                                  # the baseline aux of every T3 scenario run (filled by test_t3_coverage_...)
AUX_BOOKKEEPING = ('call_acc', 'eos_acc', 'right_last', 'stop_y', 'stop_acc')


def assert_margin():
    """The guard of nontrivial_right: no pair sat within 5e-5 (in nll * 10) of a quantisation edge."""
    assert RIGHT_MARGIN and min(RIGHT_MARGIN) >= 5e-5, ('a pair of the nontrivial-right stand-in is too close to its quantisation edge; the arms could flip on rounding', min(RIGHT_MARGIN or [None]))
    say(f'nontrivial right: smallest distance of nll*10 to an edge over {len(RIGHT_MARGIN)} passes: {min(RIGHT_MARGIN):.2e} (>= 5e-5 required; rounding between the arms is about 6e-6 in these units)')


def nontrivial_keys(auxes):
    """Which of call_acc / eos_acc / right_last / stop_y / stop_acc are strictly between 0 and 1 in at least one of the aux dicts (so they cannot be matched by a 0 / 1 constant)."""
    return {k for k in AUX_BOOKKEEPING if any(0.0 < f(x[k]) < 1.0 for x in auxes)}


# ---------------------------------------------------------------------------------------------------------------------------------- pure functions
def test_teacher_np_equals_bytewriter_teacher_including_none_empty_and_over_cap():
    w, a = world()
    m = w.new_model(400)
    BW = type(m.writer)
    G = sys.modules[G_MOD]
    ids = [[5, 6, 7], [], None, [9] * 68, [9] * 69, [9] * 70, [13], [3, 4], None, []]        # cap 69: len 68 fits (68 + 1 EOS), 69 and 70 are over
    Z = torch.zeros(len(ids), 17, m.d)
    ref = m.answer_teacher(Z, ids)                                                # ByteWriter.teacher over line_context's empty context
    assert sorted(ref) == ['fb', 'inp', 'over', 'tgt']
    inp, tgt, over = defer.teacher_np(ids, m.WCAP, G.BOS, G.EOS)
    assert torch.equal(torch.from_numpy(inp), ref['inp']) and torch.equal(torch.from_numpy(tgt), ref['tgt']) and torch.equal(torch.from_numpy(over), ref['over'])
    assert ref['fb'].shape == (len(ids), inp.shape[1], 1) and not ref['fb'].any(), 'with line_context\'s all-False mask the original fb is always zero'
    assert ref['inp'].dtype == torch.from_numpy(inp).dtype and ref['tgt'].dtype == torch.from_numpy(tgt).dtype
    assert over.tolist() == [False, False, False, False, True, True, False, False, False, False] and (tgt[over] == -100).all() and (inp[over][:, 1:] == G.EOS).all()
    for cap in (3, 5, 69):                                                        # a few caps, a few lengths
        for tg in ([[1, 2], [], None, [1, 2, 3, 4]], [None, None], [[]], [[7] * 4, [7] * 3]):
            Zt = torch.zeros(len(tg), 1, m.d)
            _, cmask, cids = m.line_context(Zt)
            r = BW.teacher(tg, cids, cmask, cap, G.BOS, G.EOS)
            i2, t2, o2 = defer.teacher_np(tg, cap, G.BOS, G.EOS)
            assert torch.equal(torch.from_numpy(i2), r['inp']) and torch.equal(torch.from_numpy(t2), r['tgt']) and torch.equal(torch.from_numpy(o2), r['over']) and not r['fb'].any(), (cap, tg)
    # no targets at all: L = 1, all rows empty
    i0, t0, o0 = defer.teacher_np([], 69, G.BOS, G.EOS)
    assert i0.shape == (0, 1) and t0.shape == (0, 1) and o0.shape == (0,)


def test_pack_roundtrip():
    arrs = dict(a=np.arange(6).reshape(2, 3), b=np.zeros((0, 4)), c=np.array([5, 6, 7]), d=np.arange(8).reshape(2, 2, 2) * 3)
    pk = defer.Pack()
    for k, v in arrs.items():
        pk.add(k, v)
    pk.send(torch.device('cpu'))
    for k, v in arrs.items():
        got = pk[k]
        assert got.dtype == torch.int64 and tuple(got.shape) == v.shape and got.tolist() == v.tolist(), k


def test_shown_cround_and_lists_equal_the_original_loops_reads():
    """The original loop's shown / cround after every round, its Z after every round, and the three host lists it reads back, against the numpy versions (spec b, c)."""
    w, a = world()
    _load()
    G = sys.modules[G_MOD]
    tr = prof.Trainer(w, a, ['defer'], accum=4)
    try:
        m = tr.model
        mb = full_batch(w)
        golds = m.train_golds(mb['rows'])
        Ls = [len(x['texts']) for x in golds]
        B, dev = len(Ls), w.device
        assert 0 in Ls and max(Ls) >= 2, Ls
        st0 = m._gap_rng.getstate()
        sched_dev, last_dev = type(m).plan(m, Ls, B, dev)                      # the original plan
        st_orig = m._gap_rng.getstate()
        m._gap_rng.setstate(st0)
        sched_np, none = m._defer_plan(Ls, B, dev)                              # the numpy plan: same draws
        assert none is None and isinstance(sched_np, np.ndarray) and m._gap_rng.getstate() == st_orig
        assert torch.equal(torch.from_numpy(sched_np), sched_dev.cpu()) and torch.equal(torch.from_numpy(defer.last_of(sched_np)), last_dev.cpu())
        n = 14
        g = dict(L=Ls, ids=[x['ids'] for x in golds], tape=[x['tape'] for x in golds], has=torch.tensor([bool(L) for L in Ls]))
        rec = []
        o = type(m).loop(m, mb, n, g=g, sched=sched_dev, each=lambda t, st: rec.append((t, st['Z'].detach().clone(), st['shown'].clone(), st['cround'].clone())) and False)
        assert [r[0] for r in rec] == list(range(n))
        for t, Z, shown, cround in rec:
            sh, cr = defer.shown_cround(sched_np, t, G.FAR)
            assert torch.equal(torch.from_numpy(sh), shown.cpu()) and torch.equal(torch.from_numpy(cr), cround.cpu()), t
            sh2, cr2 = defer.shown_cround(sched_dev, t, G.FAR)                  # the same formula on a tensor
            assert torch.equal(sh2, shown) and torch.equal(cr2, cround), t
        # the defer thinker: every Z_t bit-identical to the original's
        zs = tr.variants[0].thinker(m, mb, Ls, g['tape'], sched_dev, n)
        assert len(zs) == n and all(torch.equal(z.detach(), r[1]) for z, r in zip(zs, rec)), 'the thinker half is bit-identical'
        assert torch.equal(zs[-1].detach(), o['Z'])
        # the three lists the original reads back per round, from numpy
        last_np, per_round = defer.schedule_lists(sched_np, g['ids'], n)
        by_t = {t: (rows, tg, ic) for t, rows, tg, ic in per_round}
        for t in range(1, n):
            at = sched_dev == t
            call, kk = at.any(1), at.int().argmax(1)
            cl, kl, aft = call.tolist(), kk.tolist(), (t > last_dev).tolist()
            tgt = [g['ids'][i][kl[i]] if cl[i] else ([] if aft[i] else None) for i in range(B)]
            sel = [i for i in range(B) if tgt[i] is not None]
            if not sel:
                assert t not in by_t, t
                continue
            rows, tg, ic = by_t[t]
            assert rows == sel and tg == [tgt[i] for i in sel] and ic == [cl[i] for i in sel], t
    finally:
        tr.close()


def test_answer_pairs_order_and_the_last_round_always_has_every_row_ok():
    rng = np.random.RandomState(0)
    for _ in range(200):
        B = int(rng.randint(1, 12))
        last = rng.randint(0, 9, B)
        has = rng.rand(B) < 0.7
        last = np.where(has, np.maximum(last, 1), 0)
        n = max(int(rng.choice([4, 8, 16, 32])), int(last.max()) + 2)               # _loss's own rule
        t, i, ok = defer.answer_pairs(last, has, n)
        assert ok.shape == (n, B) and ok[n - 1].all(), 'n >= last + 2: the last round has every row ok, so share is never None through _loss'
        assert list(zip(t.tolist(), i.tolist())) == sorted(zip(t.tolist(), i.tolist())) and len(t) == int(ok.sum())
        for tt in range(n):
            for ii in range(B):
                assert ok[tt, ii] == ((tt > last[ii]) or not has[ii])


# ---------------------------------------------------------------------------------------------------------------------------------- T1 / T2
def test_t1_t2_values_aux_gradients_and_rng_match_on_a_fixed_batch():
    w, a = world()
    cases = [('16 rows, K 8', full_batch(w), 8), ('16 rows, K drawn (KS default)', full_batch(w), None), ('4 rows (micro-batch 1), K 16', micro_batch(w, 1), 16)]
    for name, mb, K in cases:
        r0 = run_one(w, a, [], mb, K)
        r1 = run_one(w, a, ['defer'], mb, K)
        c = compare(r0, r1)
        check_close(c, name)
        assert r1['stats']['defer']['deferred_losses'] == 1 and r1['stats']['defer']['fallback_losses'] == 0 and 'NUMERICS-CHANGING' in r1['stats']['defer']['numerics']
        say(f'T1/T2 {name}: loss rel diff {c["loss_rel"]:.2e} (bitwise {c["loss_bitwise"]}); aux equal; grad cos min over {c["n_params_tensors"]} tensors {c["grad_cos_min"]:.10f}, all {c["grad_cos_all"]:.10f}, '
            f'max abs {c["grad_max_abs"]:.2e}, max rel to max|g| {c["grad_max_rel"]:.2e}, rel L2 {c["grad_rel_l2"]:.2e}, grad bitwise {c["grad_bitwise"]}; RNG states equal {c["rng_equal"]}')
    # the rerun noise floor of the baseline (bit for bit) so the numbers above are the arm's, not the harness's
    r0b = run_one(w, a, [], full_batch(w), 8)
    c0 = compare(run_one(w, a, [], full_batch(w), 8), r0b)
    assert c0['loss_bitwise'] and c0['grad_bitwise'], 'baseline vs baseline is bit for bit'


def test_t1_bf16_on_the_cpu_is_informational_only():
    """CPU bf16 autocast as a stand-in for the GPU's bf16 (suggested only: not the GPU's kernels). Reported, not asserted beyond 'runs and is close'."""
    w, a = world()
    amp = lambda: torch.autocast('cpu', dtype=torch.bfloat16)
    mb = full_batch(w)
    try:
        r0 = run_one(w, a, [], mb, 8, amp=amp)
        r1 = run_one(w, a, ['defer'], mb, 8, amp=amp)
    except Exception as e:                                                       # noqa: BLE001
        raise unittest.SkipTest(f'bf16 autocast on this CPU build failed: {e!r}')
    c = compare(r0, r1)
    say(f'T1 (informational) CPU bf16 autocast: loss rel diff {c["loss_rel"]:.2e}, grad cos {c["grad_cos_all"]:.8f}, rel L2 {c["grad_rel_l2"]:.2e}, rng equal {c["rng_equal"]}')
    assert c['rng_equal'] and c['loss_rel'] < 1e-2 and c['grad_cos_all'] > 0.99


# ---------------------------------------------------------------------------------------------------------------------------------- T3
class Spy:
    """Record the batch size of every call_pass / ans_pass of a model (the original's subsets: full = every row, else a subset)."""

    def __init__(self):
        self.call, self.ans = [], []

    def __call__(self, m):
        oc, oa = m.call_pass, m.ans_pass
        m.call_pass = lambda Z, *x, **k: (self.call.append(Z.shape[0]), oc(Z, *x, **k))[1]
        m.ans_pass = lambda Z, *x, **k: (self.ans.append(Z.shape[0]), oa(Z, *x, **k))[1]


def test_t3_coverage_rounds_gaps_drill_nocall_rows_full_and_subset_overcap():
    w, a = world()
    mb16 = full_batch(w)
    mb4 = micro_batch(w, 1)
    G_ = sys.modules[G_MOD]
    seen = dict(full_call=0, subset_call=0, full_ans=0, subset_ans=0, gapped=0, drilled=0, nocall_rows=0, over=0, n_max=0, n_min=99)
    CKPT, NL = G_.CKPT_FROM, None

    def scenario(name, mb, K, tweak=None, rows=None):
        nonlocal NL
        if rows is not None:
            mb = pick_rows(mb, rows)
        B = len(mb['rows'])
        spy = Spy()
        r0 = run_one(w, a, [], mb, K, tweak=tweak, spy=spy)
        r1 = run_one(w, a, ['defer'], mb, K, tweak=tweak)
        c = compare(r0, r1)
        check_close(c, name)
        AUX_LOG.append(r0['aux'])
        n = int(r0['aux']['rounds'])
        NL = r0['model'].n_loops
        seen['full_call'] += sum(s == B for s in spy.call); seen['subset_call'] += sum(s < B for s in spy.call)
        seen['full_ans'] += sum(s == B for s in spy.ans); seen['subset_ans'] += sum(s < B for s in spy.ans)
        seen['gapped'] += int(r0['aux']['plan_gapped']); seen['drilled'] += int(round(float(r0['aux'].get('drill_share', 0)) * B))
        seen['n_max'] = max(seen['n_max'], n); seen['n_min'] = min(seen['n_min'], n)
        Ls = [len(x['texts']) for x in r0['model'].plain_golds(mb['rows'])]
        seen['nocall_rows'] += sum(L == 0 for L in Ls)
        say(f'T3 {name}: rows {B} n {n} loss rel {c["loss_rel"]:.1e} grad cos min {c["grad_cos_min"]:.9f} rel L2 {c["grad_rel_l2"]:.1e} | call passes full/subset {sum(s == B for s in spy.call)}/{sum(s < B for s in spy.call)}, '
            f'answer passes {sum(s == B for s in spy.ans)}/{sum(s < B for s in spy.ans)}, gapped {int(r0["aux"]["plan_gapped"])}, call_acc {r0["aux"]["call_acc"]:.3f} eos_acc {r0["aux"]["eos_acc"]:.3f} right_last {f(r0["aux"]["right_last"]):.3f} stop_y {f(r0["aux"]["stop_y"]):.3f} stop_acc {f(r0["aux"]["stop_acc"]):.3f} share {f(r0["aux"]["copy_share"])}')
        return r0, r1, c

    scenario('K=4 (short: n = max(4, last + 2))', mb16, 4)
    r0, r1, c = scenario('K=32 (rounds past CKPT_FROM 8 and n_loops)', mb16, 32)
    assert int(r0['aux']['rounds']) == 32 > CKPT and 32 > NL
    scenario('K=16, 4-row micro-batch (subsets)', mb4, 16)
    scenario('gap_p = 1 (every call row gapped)', mb16, 16, tweak=lambda m: setattr(m, 'gap_p', 1.0))
    scenario('ans_drill = 1 (drilled rows)', mb16, 8, tweak=lambda m: setattr(m, 'ans_drill', 1.0))
    scenario('gap_p = 1 and ans_drill = 1, K 32', mb16, 32, tweak=lambda m: (setattr(m, 'gap_p', 1.0), setattr(m, 'ans_drill', 1.0)))
    calling = [i for i, r in enumerate(mb16['rows']) if r.get('steps')]
    nocall = [i for i, r in enumerate(mb16['rows']) if not r.get('steps')]
    assert calling and nocall
    scenario('only rows with calls (every row selected at the call rounds)', mb16, 8, tweak=lambda m: setattr(m, 'gap_p', 0.0), rows=calling)
    scenario('only rows without calls (EOS-only targets, every round)', mb16, 8, rows=nocall)
    scenario('writer cap 7: calls and answers over the cap get no target', mb16, 8, tweak=lambda m: setattr(m, 'WCAP', 7))
    # the over-cap targets really were over
    m = w.new_model(400)
    m.WCAP = 7
    golds = m.plain_golds(mb16['rows'])
    seen['over'] = sum(len(t) + 1 > 7 for x in golds for t in x['ids'] + [x['ans_ids']])
    assert seen['over'] > 0
    assert seen['full_call'] > 0 and seen['subset_call'] > 0 and seen['full_ans'] > 0 and seen['subset_ans'] > 0, seen
    assert seen['gapped'] > 0 and seen['drilled'] > 0 and seen['nocall_rows'] > 0 and seen['n_max'] == 32 and seen['n_min'] <= 8, seen
    say(f'T3 coverage reached: {seen}')


def test_t3_last_round_with_no_ok_rows_is_unreachable_through_loss_but_handled_at_a_forced_short_n():
    """_loss's n >= last + 2 makes round n - 1 an ok round for EVERY row, so share is never None there (proved in test_answer_pairs_...). Forcing n (the variant's test-only n_override against the
    original _loss rebuilt with the same edit) reaches the branch: rows that all still call at the last round have no ok row anywhere: Q = 0, lans = 0, share None, both arms."""
    w, a = world()
    mb = full_batch(w)
    calling = [i for i, r in enumerate(mb['rows']) if r.get('steps')]
    sub = pick_rows(mb, calling)

    # run_one hides the Trainer; build both by hand
    for n_forced, expect_none in ((2, True), (3, True), (4, False), (5, False)):
        out = []
        for names in ([], ['defer']):
            tr = prof.Trainer(w, a, names, accum=4)
            try:
                m = tr.model
                m.gap_p = 0.0
                if names:
                    tr.variants[0].n_override = n_forced
                else:
                    m._test_n = n_forced
                    m._loss = types.MethodType(prof.patched_fn(type(m)._loss, [('n = max(K, int(last.max()) + 2)', 'n = self._test_n')]), m)
                torch.manual_seed(5)
                loss, aux = m.loss(sub)
                loss.backward()
                grads = [p.grad.double().clone() if p.grad is not None else torch.zeros(p.shape, dtype=torch.float64) for p in m.parameters()]
                out.append(dict(loss=loss.detach(), aux=aux, grads=grads, rng=(torch.get_rng_state(), m._gap_rng.getstate(), m._drill_rng.getstate())))
            finally:
                tr.close()
        c = compare(*out)
        check_close(c, f'forced n {n_forced}')
        share = out[0]['aux']['copy_share']
        assert (share is None) == expect_none and (out[1]['aux']['copy_share'] is None) == expect_none, (n_forced, share)
        say(f'T3 forced n={n_forced}: copy_share {f(share)} in both arms, loss rel {c["loss_rel"]:.1e}, grad cos min {c["grad_cos_min"]:.9f}')


def test_t1_t3_with_a_nontrivial_right_the_scatter_counters_and_stop_label_are_really_compared():
    """The reviewer's defect: with the real `right` (all False at init) 'every aux key equal' says nothing about the right[] scatter, the call / EOS hit counters or the stop label. Here BOTH
    arms run with `nontrivial_right()`. Asserted: the bookkeeping aux values are not all 0 / 1 (so they can be matched only by being computed right), then they are equal arm to arm."""
    w, a = world()
    cases = [('16 rows, K 8', full_batch(w), 8, None), ('16 rows, K 32 (rounds past CKPT_FROM)', full_batch(w), 32, None), ('4 rows, K 16', micro_batch(w, 1), 16, None),
             ("16 rows, K 16, label 'right' (stop_w = 1)", full_batch(w), 16, lambda m: setattr(m, 'label', 'right'))]
    seen = []
    with nontrivial_right():
        for name, mb, K, tweak in cases:
            r0 = run_one(w, a, [], mb, K, tweak=tweak)
            r1 = run_one(w, a, ['defer'], mb, K, tweak=tweak)
            c = compare(r0, r1)
            check_close(c, name)
            assert r1['stats']['defer']['deferred_losses'] == 1
            seen.append(r0['aux'])
            say(f'T1 nontrivial right, {name}: ' + ', '.join(f'{k} {f(r0["aux"][k]):.4f}/{f(r1["aux"][k]):.4f}' for k in AUX_BOOKKEEPING) + f'; loss rel {c["loss_rel"]:.1e}, grad rel L2 {c["grad_rel_l2"]:.1e}')
    assert_margin()
    nt = nontrivial_keys(seen)
    assert nt >= {'call_acc', 'right_last', 'stop_y', 'stop_acc'}, ('these must be strictly between 0 and 1 in some case', nt)
    say(f'T1 nontrivial right: strictly between 0 and 1 in at least one case: {sorted(nt)}')


def test_t3_coverage_scenarios_again_with_a_nontrivial_right():
    """The nine T3 scenarios, both arms with `nontrivial_right()`; the bookkeeping aux values must be non-trivial somewhere in them (call_acc, eos_acc, right_last, stop_y, stop_acc)."""
    del AUX_LOG[:]
    with nontrivial_right():
        test_t3_coverage_rounds_gaps_drill_nocall_rows_full_and_subset_overcap()
    assert_margin()
    nt = nontrivial_keys(AUX_LOG)
    assert nt >= set(AUX_BOOKKEEPING), ('every one of these must be strictly between 0 and 1 in some scenario', nt, [{k: f(x[k]) for k in AUX_BOOKKEEPING} for x in AUX_LOG])
    say(f'T3 nontrivial right: {len(AUX_LOG)} scenarios; strictly between 0 and 1 somewhere: {sorted(nt)}')
    del AUX_LOG[:]


def test_t3_forced_short_n_again_with_a_nontrivial_right():
    with nontrivial_right():
        test_t3_last_round_with_no_ok_rows_is_unreachable_through_loss_but_handled_at_a_forced_short_n()


def test_the_t1_marks_catch_a_scrambled_scatter_swapped_counters_and_a_wrong_stop_label():
    """Mutation check of the test itself (the reviewer's mut.py, kept): Defer.loss is replaced, by prof.patched_fn (a rebuild from its own source with exact edits; no file is edited), by
    five WRONG versions. Under `nontrivial_right()` the T1 marks (check_close) must FAIL on every one; the unmutated loss passes them. (With the real all-False `right` they would pass: that is
    why the test above exists.)"""
    w, a = world()
    mb = full_batch(w)
    orig = defer.Defer.loss
    mutations = [
        ('answer right[] scatter reversed', [("right.view(-1)[pk['a_flat']] = rt_a", "right.view(-1)[pk['a_flat'].flip(0)] = rt_a")]),
        ('call / EOS hit counters swapped', [("hits['call_n'], hits['call_hit'] = n_call, sum(rc[:n_call])", "hits['call_n'], hits['call_hit'] = n_call, sum(rc[n_call:])")]),
        ('stop label ignores settled()', [("y = (settled(right) if m.label == 'settled' else right).to(dev).float()", "y = right.to(dev).float()")]),
        ('call nll left in bucket order (c_inv dropped)', [(".index_select(0, pk['c_inv'])", "")]),
        ('stop head reads the wrong round', [("zst = Zall.view(n, B, nz, d)[:, :, 1].detach()", "zst = Zall.view(n, B, nz, d)[:, :, 1].detach().flip(0)")]),
    ]
    try:
        with nontrivial_right():
            r0 = run_one(w, a, [], mb, 8)
            c = compare(r0, run_one(w, a, ['defer'], mb, 8))
            check_close(c, 'unmutated')
            for name, edits in mutations:
                defer.Defer.loss = prof.patched_fn(orig, edits)
                try:
                    cm = compare(r0, run_one(w, a, ['defer'], mb, 8))
                    try:
                        check_close(cm, name)
                    except AssertionError as e:
                        say(f'mutation "{name}": caught ({str(e)[:110]})')
                    else:
                        raise AssertionError(f'the T1 marks did NOT catch the mutation "{name}"')
                finally:
                    defer.Defer.loss = orig
    finally:
        defer.Defer.loss = orig


# ---------------------------------------------------------------------------------------------------------------------------------- T4
def test_t4_fallbacks_are_bitwise_the_original():
    w, a = world()
    mb = full_batch(w)
    base, dfr = prof.Trainer(w, a, [], accum=4), prof.Trainer(w, a, ['defer'], accum=4)
    try:
        v = dfr.variants[0]
        mA, mB = base.model, dfr.model

        def same(x, y, what):
            if torch.is_tensor(x):
                assert torch.equal(x, y), what
            elif isinstance(x, dict):
                assert sorted(x) == sorted(y), what
                for k in x:
                    same(x[k], y[k], f'{what}.{k}')
            elif isinstance(x, (list, tuple)):
                assert len(x) == len(y), what
                for i, (p, q) in enumerate(zip(x, y)):
                    same(p, q, f'{what}[{i}]')
            else:
                assert x == y, (what, x, y)

        def both(fn, what):
            outs = []
            for m in (mA, mB):
                torch.manual_seed(11)
                outs.append(fn(m))
            same(outs[0], outs[1], what)

        def loss_grad(m):
            loss, aux = m.loss(mb)
            loss.backward() if loss.requires_grad else None
            return dict(loss=loss.detach(), aux={k: val for k, val in aux.items()}, grads=[p.grad.clone() if p.grad is not None else torch.zeros(1) for p in m.parameters()])

        def eval_loss(m):
            m.eval()
            try:
                l, aux = m.loss(mb)
            finally:
                m.train()
            return dict(loss=l.detach(), aux=aux)

        def nograd_loss(m):
            with torch.no_grad():
                l, aux = m.loss(mb)
            return dict(loss=l, aux=aux)

        def rec_loop(m):
            golds = m.plain_golds(mb['rows'])
            Ls = [len(x['texts']) for x in golds]
            sched, last = m.plan(Ls, len(Ls), w.device)
            g = dict(L=Ls, ids=[x['ids'] for x in golds], tape=[x['tape'] for x in golds], has=torch.tensor([bool(L) for L in Ls]))
            o = m.loop(mb, max(max(Ls) + 1, 2), g=g, sched=sched, rec=True)
            return dict(Z=o['Z'], lcall=o['lcall'], crec=o['crec'], hits=[o[k] for k in ('call_hit', 'call_n', 'eos_hit', 'eos_n')], cround=o['cround'])

        def all_rounds_loss(m):
            m.talk_rounds = 'all'
            try:
                return loss_grad(m)
            finally:
                m.talk_rounds = 'last'

        def free_run(m):
            m.eval()
            try:
                with torch.no_grad():
                    o = m.run(mb)
                    ans = m.talk(m.state_of(o), mb)
                    o2 = m.run(mb, loops=3)
                    gen = m.generate(mb)
            finally:
                m.train()
            return dict(Z=o['Z'], records=o['records'], rounds=o['rounds'], ans=ans, Z2=o2['Z'], gen=gen)

        # the REAL fallbacks (they go through defer's _loss and back to the original): eval-mode loss, no_grad loss, talk_rounds='all' loss. The loop(rec=True) and free-run checks only show that
        # setup() left those methods alone (defer replaces neither), so they are labelled UNTOUCHED.
        both(eval_loss, 'eval-mode loss')
        both(nograd_loss, 'training mode, no_grad loss')
        both(rec_loop, 'UNTOUCHED loop(rec=True) (the call_evals path): defer does not replace loop, so this only shows setup() left it alone')
        both(all_rounds_loss, "talk_rounds='all' loss + gradient")
        both(free_run, 'UNTOUCHED free run (run / talk / loops:3 / generate): same, only shows setup() left these methods alone')
        assert v.n_deferred == 0 and v.n_fallback == 3, (v.n_deferred, v.n_fallback)       # eval, no_grad, talk_rounds all: three losses; the loop / free-run paths never reach _loss
        assert v.n_deferred == 0
    finally:
        base.close(); dfr.close()


def test_t4_applicable_rule_and_fallback_counter():
    w, a = world()
    tr = prof.Trainer(w, a, ['defer'], accum=4)
    try:
        m, v = tr.model, tr.variants[0]
        assert v.applicable(m)
        with torch.no_grad():
            assert not v.applicable(m)
        m.eval(); assert not v.applicable(m); m.train()
        m.talk_rounds = 'all'; assert not v.applicable(m); m.talk_rounds = 'last'
        m.writer.copy = True; assert not v.applicable(m); m.writer.copy = False
        assert v.applicable(m)
    finally:
        tr.close()


def test_t4_fallback_goes_to_an_instance_loss_set_before_defer_not_to_the_class():
    """The fallback must be the _loss the instance had when defer was set up (a variant set up earlier may have wrapped it), and teardown must put that wrapper back."""
    w, a = world()
    _load()
    m = w.new_model(400)
    mb = full_batch(w)
    calls = []
    cls_loss = type(m)._loss

    def wrapped(batch, golds):
        calls.append(1)
        return cls_loss(m, batch, golds)
    m._loss = wrapped
    v = defer.Defer(types.SimpleNamespace(model=m, a=a))
    v.setup()
    try:
        m.eval()
        torch.manual_seed(3)
        m.loss(mb)                                                                # eval -> fallback -> the instance wrapper
        assert calls == [1] and v.n_fallback == 1 and v.n_deferred == 0, (calls, v.n_fallback)
    finally:
        m.train()
        v.teardown()
    assert m.__dict__['_loss'] is wrapped, 'teardown puts the earlier instance _loss back'


def test_saved_for_backward_bytes_tiny_defer_is_close_to_the_baseline():
    """The reviewer's memory worry (shown on the tiny shape, CPU): the bytes of the unique storages autograd saves for backward in one forward. First version of defer (no answer-pass
    checkpoint, every call pair padded to the longest call): 1.07x at K 8, 1.59x at K 32. With the checkpoint for rounds >= 8 and the EOS-only pairs at width 1 the ratio must stay <= 1.15.
    GPU peak memory is a different number and is untested."""
    w, a = world()
    mb = full_batch(w)
    out = {}
    for K in (8, 32):
        b = saved_bytes(w, a, [], mb, K)
        d = saved_bytes(w, a, ['defer'], mb, K)
        out[K] = d[0] / b[0]
        say(f'memory (tiny, 16 rows, K {K}, rounds {b[1]}): saved-for-backward baseline {b[0] / 1e6:.2f} MB, defer {d[0] / 1e6:.2f} MB, ratio {d[0] / b[0]:.3f}; defer stats call pairs {d[2]}, EOS-only {d[3]}, answer pairs {d[4]}, call width {d[5]}')
        assert d[0] / b[0] <= 1.15, (K, d[0] / b[0])


def saved_bytes(w, a, names, mb, K):
    """-> (bytes of the unique storages saved for backward during ONE forward m.loss(mb), rounds, call pairs, EOS-only pairs, answer pairs, max call width) (the last four None for the baseline)."""
    tr = prof.Trainer(w, a, names, accum=4)
    try:
        m = tr.model
        seen = {}

        def pack(t):
            try:
                seen[(t.untyped_storage().data_ptr(), t.untyped_storage().nbytes())] = t.untyped_storage().nbytes()
            except Exception:                                                  # noqa: BLE001
                pass
            return t
        torch.manual_seed(5)
        with forced_ks(K), torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
            loss, aux = m.loss(mb)
        st = tr.variant_stats().get('defer', {})
        return (sum(seen.values()), int(aux['rounds']), st.get('call_pairs_per_micro_batch'), st.get('eos_only_pairs_per_micro_batch'), st.get('answer_pairs_per_micro_batch'), st.get('max_call_width'))
    finally:
        tr.close()


def test_t5_op_counts_do_not_move_with_the_prompt_width():
    """Tiny model, synthetic prompts cut at 60 and at 280 letters, the same K: the ATen op counts of defer (and of the baseline) are the same to within 1 percent. (Was an unlogged ad hoc run.)"""
    res = {}
    for letters in (60, 280):
        w, a = world('B3G2', '--synth-letters', str(letters))
        mb = full_batch(w)
        res[letters] = (counts_of(w, a, [], mb, 16)['ops'], counts_of(w, a, ['defer'], mb, 16)['ops'])
    say(f'T5 op counts (baseline, defer) by prompt width: 60 letters {res[60]}, 280 letters {res[280]}')
    for i in (0, 1):
        assert abs(res[60][i] - res[280][i]) <= 0.01 * res[280][i], res


# ---------------------------------------------------------------------------------------------------------------------------------- T5
class OpCount(torch.utils._python_dispatch.TorchDispatchMode):
    """Count ATen dispatches (forward, backward, checkpoint recompute) that are not views (an op whose returns alias an input without writing: view, slice, select, detach ... is counted apart)."""

    def __init__(self):
        super().__init__()
        self.n, self.views, self.by, self.host, self.host_depth = 0, 0, collections.Counter(), 0, 0

    def __torch_dispatch__(self, func, types_, args=(), kwargs=None):
        if any(r.alias_info is not None and not r.alias_info.is_write for r in func._schema.returns):
            self.views += 1
        elif self.host_depth:
            self.host += 1                                                     # inside ByteWriter.teacher: tensors built and read on the HOST, never a GPU kernel (it .cpu()s its context first)
        else:
            self.n += 1
            self.by[str(func)] += 1
        return func(*args, **(kwargs or {}))


@contextlib.contextmanager
def host_region(oc, owner, name):
    """Ops dispatched inside owner.name (a staticmethod) are counted as host ops of `oc`, not as ops that would launch a GPU kernel."""
    orig = owner.__dict__[name]
    fn = orig.__func__

    def wrapped(*a, **k):
        oc.host_depth += 1
        try:
            return fn(*a, **k)
        finally:
            oc.host_depth -= 1
    setattr(owner, name, staticmethod(wrapped))
    try:
        yield
    finally:
        setattr(owner, name, orig)


_MISSING = object()


@contextlib.contextmanager
def count_syncs():
    """Wrap the Python-visible host-sync calls and record (kind, file, line) of every caller. -> Counter."""
    sites = collections.Counter()
    undo = []

    def wrap(owner, name, kind, pred=None):
        orig = owner.__dict__.get(name, _MISSING)
        fn = getattr(owner, name)

        def w(*args, **kw):
            if pred is None or pred(*args, **kw):
                fr = sys._getframe(1)
                sites[(kind, os.path.basename(fr.f_code.co_filename), fr.f_lineno)] += 1
            return fn(*args, **kw)
        w.__name__ = name
        undo.append((owner, name, orig))
        setattr(owner, name, w)
    tgt_arg = lambda *args, **kw: kw.get('device') is not None or (len(args) > 1 and isinstance(args[1], (torch.device, str, torch.Tensor)))
    for name in ('tolist', 'item', '__bool__', '__int__', '__float__', '__index__', 'cpu', 'numpy', 'nonzero'):
        wrap(torch.Tensor, name, name)
    wrap(torch.Tensor, 'to', 'to(device)', tgt_arg)
    wrap(torch, 'tensor', 'torch.tensor(device=)', lambda *args, **kw: kw.get('device') is not None)
    wrap(torch, 'nonzero', 'torch.nonzero')
    try:
        yield sites
    finally:
        for owner, name, orig in reversed(undo):
            if orig is _MISSING:
                delattr(owner, name)
            else:
                setattr(owner, name, orig)


def counts_of(w, a, names, mb, K):
    """Dispatch / sync counts of ONE micro-batch forward + backward (Trainer built before counting; the counters see m.loss(mb) and .backward() only)."""
    tr = prof.Trainer(w, a, names, accum=4)
    try:
        m = tr.model
        prof.cold_eg(w)                                                         # the shared stub Gemma memoises the last question: a second run on the same rows would skip that pass
        torch.manual_seed(5)
        oc = OpCount()
        with forced_ks(K), count_syncs() as sites, host_region(oc, type(m.writer), 'teacher'), oc:
            loss, aux = m.loss(mb)
            loss.backward()
        return dict(ops=oc.n, host_ops=oc.host, views=oc.views, by_op=oc.by, sites=sites, syncs=sum(sites.values()), rounds=int(aux['rounds']), rows=len(mb['rows']), loss=float(loss.detach()))
    finally:
        tr.close()


def site_table(c0, c1, top=40):
    keys = sorted(set(c0['sites']) | set(c1['sites']), key=lambda k: -(c0['sites'].get(k, 0)))
    rows = [(k, c0['sites'].get(k, 0), c1['sites'].get(k, 0)) for k in keys]
    return rows[:top]


# Sites in the files the arm touches (b3g2.py, writer.py, defer.py) that can NOT wait on a GPU, found by the text of their line: a Python bool of a tensor that ByteWriter.teacher built on the host
# (`if hit.any():`: after its .cpu() the context is a host tensor), the micro-batch's one host-generator draw (`int(torch.randint(...))`), a .to(dev) of a tensor already on dev (`y = (settled(...)).to(dev)`).
# prof_train.py's to_device_async is the pinned non_blocking copy (a plain .to on the CPU): on CUDA it does not wait.
HOST_ONLY_TEXT = ('if hit.any():', 'int(torch.randint', '.to(dev).float()')
ARM_FILES = ('b3g2.py', 'writer.py', 'defer.py')


def split_sites(c):
    """The counted sites of a micro-batch split into: gpu_waits (in ARM_FILES, on a tensor that would live on the GPU: each of these waits for the stream), host_only (ARM_FILES, cannot wait), nonblocking (the pack
    copy), other (every other file: the reader, Gemma front, tape reads ... identical in both arms)."""
    import linecache
    out = dict(gpu_waits=0, host_only=0, nonblocking=0, other=0)
    for (kind, fl, ln), n_ in c['sites'].items():
        if fl in ARM_FILES:
            path = {'b3g2.py': 'custom_io/models/b3g2.py', 'writer.py': 'custom_io/models/writer.py', 'defer.py': 'defer.py'}[fl]
            full = os.path.join(HERE, 'defer.py') if fl == 'defer.py' else os.path.join(prof.PK.root, path)
            text = linecache.getline(full, ln)
            out['host_only' if any(t in text for t in HOST_ONLY_TEXT) else 'gpu_waits'] += n_
        elif fl == 'prof_train.py' and kind == 'to(device)' and 'return v.to(device)' in linecache.getline(os.path.join(PROFDIR, 'prof_train.py'), ln):      # to_device_async's CPU branch
            out['nonblocking'] += n_
        else:
            out['other'] += n_
    return out


def report_counts(tag, c0, c1):
    say(f'T5 {tag}: rows {c0["rows"]}, rounds n {c0["rounds"]}')
    say(f'    non-view ATen ops (fwd+bwd), device-side (ByteWriter.teacher\'s host-tensor ops excluded): baseline {c0["ops"]:,}   defer {c1["ops"]:,}   ratio {c1["ops"] / c0["ops"]:.3f}   '
        f'(host ops in teacher: {c0["host_ops"]:,} / {c1["host_ops"]:,}; view ops: {c0["views"]:,} / {c1["views"]:,})')
    say(f'    host-sync call sites hit:     baseline {c0["syncs"]:,}   defer {c1["syncs"]:,}   (per round: {c0["syncs"] / c0["rounds"]:.2f} / {c1["syncs"] / c1["rounds"]:.2f})')
    s0, s1 = split_sites(c0), split_sites(c1)
    say(f'    split of those sites:          baseline {s0}   defer {s1}')
    say(f'    -> sites that would WAIT on a GPU in b3g2/writer/defer: baseline {s0["gpu_waits"]} ({s0["gpu_waits"] / c0["rounds"]:.2f} per round), defer {s1["gpu_waits"]} ({s1["gpu_waits"] / c1["rounds"]:.3f} per round)')
    for (kind, fl, ln), x, y in site_table(c0, c1, 30):
        if x != y:
            say(f'      {kind:22s} {fl}:{ln:<5d} baseline {x:6d}  defer {y:6d}')
    ref = collections.Counter()
    for (kind, fl, ln), n_ in c0['sites'].items():
        ref[fl] += n_
    mid = collections.Counter()
    for (kind, fl, ln), n_ in c1['sites'].items():
        mid[fl] += n_
    say('    by file (baseline -> defer): ' + ', '.join(f'{fl} {ref[fl]}->{mid[fl]}' for fl in sorted(set(ref) | set(mid)) if ref[fl] or mid[fl]))
    return s0, s1


def test_t5_counts_tiny():
    w, a = world()
    for name, mb in (('4-row micro-batch', micro_batch(w, 1)), ('16-row batch', full_batch(w))):
        c0 = counts_of(w, a, [], mb, 16)
        c1 = counts_of(w, a, ['defer'], mb, 16)
        s0, s1 = report_counts(f'tiny, {name}, K 16', c0, c1)
        assert c1['ops'] < c0['ops'] and c1['syncs'] < c0['syncs'], (c0['ops'], c1['ops'], c0['syncs'], c1['syncs'])
        assert s1['gpu_waits'] <= 2 and s0['gpu_waits'] >= 10 * c0['rounds'], (s0, s1)         # defer: a constant per micro-batch (the one .tolist()); the original: >= 10 per round
        assert abs(c0['loss'] - c1['loss']) <= 1e-6 * abs(c0['loss'])
        wsites = lambda c: sum(n_ for (kind, fl, ln), n_ in c['sites'].items() if fl in ('b3g2.py', 'writer.py'))
        assert wsites(c1) < wsites(c0) / 2, (wsites(c0), wsites(c1))


def real_world():
    if 'real' not in _CACHE:
        _load()
        root = prof.PK.root
        caps = os.path.join(root, 'custom_io', 'g8a', 'caps_b3g2.json')
        letters = int(os.environ.get('DEFER_REAL_LETTERS', '700'))              # 0 = the caps' full prompt width (about 11 GB peak for 64 rows; the shared 16 GB box killed that run once)
        args = ['--arm', 'B3G2', '--rung', '3M', '--accum', '4', '--batch', '256', '--data', 'synthetic', '--rows', '2000', '--eg', 'stub', '--device', 'cpu', '--caps', caps, '--updates', '1',
                '--warmup', '0', '--out', os.path.join(tempfile.gettempdir(), f'defer_real_{os.getpid()}.json')] + (['--synth-letters', str(letters)] if letters else [])
        a = prof.build_parser().parse_args(args)
        a.accum = 4
        _CACHE['real'] = (prof.World(a), a)
    return _CACHE['real']


def test_t5_counts_real_3m_shape():
    if os.environ.get('DEFER_REAL_SHAPE') != '1':
        raise unittest.SkipTest('set DEFER_REAL_SHAPE=1 (4-6 minutes, 2 threads): ONE 64-row micro-batch of the real 3M shape (batch 256, accum 4), K pinned to 16')
    torch.set_num_threads(int(os.environ.get('DEFER_THREADS', '2')))
    try:
        return _t5_real()
    finally:
        torch.set_num_threads(1)


def _t5_real():
    w, a = real_world()
    assert w.n_params == 4_023_302, w.n_params
    mb = prof.PK.TR.split_batch(full_batch(w, seed=400), 4)[0]
    assert len(mb['rows']) == 64
    t0 = time.time()
    r0 = run_one(w, a, [], mb, 16)
    t1 = time.time()
    r1 = run_one(w, a, ['defer'], mb, 16)
    t2 = time.time()
    c = compare(r0, r1)
    say(f'T5 real 3M shape, values: loss {float(r0["loss"]):.6f} vs {float(r1["loss"]):.6f} rel diff {c["loss_rel"]:.2e}; grad cos min {c["grad_cos_min"]:.9f} all {c["grad_cos_all"]:.10f} rel L2 {c["grad_rel_l2"]:.2e} '
        f'max abs {c["grad_max_abs"]:.2e}; aux bad {c["aux_bad"]}; rng equal {c["rng_equal"]}; CPU wall fwd+bwd (2 threads, includes model build) baseline {t1 - t0:.1f}s defer {t2 - t1:.1f}s')
    say(f'    defer stats: {r1["stats"]["defer"]}')
    assert not c['aux_bad'] and c['rng_equal'] and c['loss_rel'] <= 1e-6
    c0 = counts_of(w, a, [], mb, 16)
    c1 = counts_of(w, a, ['defer'], mb, 16)
    s0, s1 = report_counts('REAL 3M shape (4,023,302 params), 64 rows, K 16', c0, c1)
    top = (c0['by_op'] - c1['by_op']).most_common(8)
    say('    ops removed most: ' + ', '.join(f'{k} {v:,}' for k, v in top))
    assert c1['ops'] < c0['ops'] and c1['syncs'] < c0['syncs'] and s1['gpu_waits'] <= 2 and s0['gpu_waits'] >= 10 * c0['rounds'], (s0, s1)
    _CACHE['real_counts'] = (c0, c1)


def test_t5_saved_for_backward_bytes_real_3m_shape_k16_and_k32():
    """DEFER_REAL_SHAPE=1 only. The real 3M model (WCAP 96, V 269), 700-letter synthetic prompts: bytes saved for backward in one forward (no backward), baseline vs defer, for K 16 on the first
    32 rows of the real 64-row micro-batch and K 32 (the largest of KS, the worst case for the pairs kept alive) on its first 16 rows (64 rows needs about 5 GB at K 16 and 10 GB at K 32, and the
    shared 16 GB box has killed these runs when other jobs were running; a 64-row K 16 run measured ratio 1.006 once, not logged). 2 threads, a few minutes. The synthetic calls are short (the longest call of the micro-batch gives call width 16); the
    real pool's calls go up to WCAP - 1 = 95 bytes, so the real width, and with it the call logp tensors, are larger than measured here. The GPU peak is not this number; this is the closest
    thing measurable here."""
    if os.environ.get('DEFER_REAL_SHAPE') != '1':
        raise unittest.SkipTest('set DEFER_REAL_SHAPE=1 (a few minutes, 2 threads, about 5 GB)')
    torch.set_num_threads(int(os.environ.get('DEFER_THREADS', '2')))
    try:
        w, a = real_world()
        prof.PK.CP.apply(json.load(open(w.caps_path)))                          # World() applies its caps GLOBALLY; worlds built since (the tiny ones) left theirs: the real model needs the real position table
        mb = prof.PK.TR.split_batch(full_batch(w, seed=400), 4)[0]
        for K, rows in ((16, 32), (32, 16)):
            sub = mb if rows == len(mb['rows']) else pick_rows(mb, list(range(rows)))
            b = saved_bytes(w, a, [], sub, K)
            d = saved_bytes(w, a, ['defer'], sub, K)
            say(f'memory REAL 3M shape, {rows} rows, K {K} (rounds {b[1]}): saved-for-backward baseline {b[0] / 1e6:.1f} MB, defer {d[0] / 1e6:.1f} MB, ratio {d[0] / b[0]:.3f}; '
                f'defer call pairs {d[2]}, EOS-only {d[3]}, answer pairs {d[4]}, call width {d[5]}')
            assert d[0] / b[0] <= 1.25, (K, d[0] / b[0])
    finally:
        torch.set_num_threads(1)


# ---------------------------------------------------------------------------------------------------------------------------------- T6
def test_t6_teardown_restores_the_patched_attributes_by_identity():
    w, a = world()
    _load()
    m = w.new_model(400)
    snap = dict(m.__dict__)
    cls_before = {n: getattr(type(m), n) for n in ('_loss', 'plan', 'loop', 'call_pass', 'ans_pass', 'answer_teacher')}
    v = defer.Defer(types.SimpleNamespace(model=m, a=a))
    v.setup()
    assert '_loss' in m.__dict__ and '_defer_plan' in m.__dict__ and set(m.__dict__) - set(snap) == {'_loss', '_defer_plan'}
    assert m._loss.__func__ is not cls_before['_loss'] and type(m)._loss is cls_before['_loss'], 'only the instance is patched'
    v.teardown()
    assert set(m.__dict__) == set(snap) and all(m.__dict__[k] is snap[k] for k in snap), 'the instance dict is exactly what it was'
    assert all(getattr(type(m), n) is f_ for n, f_ in cls_before.items())
    assert m._loss.__func__ is cls_before['_loss']
    v.teardown()                                                                  # idempotent
    assert set(m.__dict__) == set(snap)
    # after a normal Trainer.close, with the other B3G2 variants composed
    ref = set(w.new_model(400).__dict__)
    for names in (['defer'], ['nosync', 'defer'], ['defer', 'pad64p'], ['nosync', 'pad64', 'defer']):
        tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
        mm = tr.model
        assert '_loss' in mm.__dict__
        tr.close()
        assert set(mm.__dict__) == ref, (names, set(mm.__dict__) ^ ref)
    # a setup that is refused (other source / other arm) leaves nothing behind
    old = dict(defer.SRC_HASH)
    defer.SRC_HASH['loop'] = 'deadbeef0000'
    try:
        tr = None
        try:
            tr = prof.Trainer(w, a, ['defer'], accum=4)
        except prof.Skip as e:
            assert 'not the custom_io' in str(e) and 'loop' in str(e)
        else:
            raise AssertionError('a changed source must be refused')
    finally:
        defer.SRC_HASH.update(old)
    wp, ap = world('PTS')
    try:
        prof.Trainer(wp, ap, ['defer'], accum=4)
    except prof.Skip as e:
        assert 'B3G2' in str(e)
    else:
        raise AssertionError('defer on a plain arm must say it does not apply')


def test_defer_composes_with_nosync_and_pad64p_and_is_registered():
    w, a = world()
    assert 'defer' in prof.VARIANTS and len(prof.VARIANTS['defer'].doc) > 300 and 'NUMERICS-CHANGING' in prof.VARIANTS['defer'].doc
    assert prof.parse_variants('defer,nosync') == ['nosync', 'defer'] and prof.AB_CPU_RULE['defer'] == 'equal_to_rounding'
    mb = full_batch(w)
    r = run_one(w, a, ['defer'], mb, 8)
    r2 = run_one(w, a, ['nosync', 'defer'], mb, 8)
    c = compare(r, r2)
    assert c['loss_bitwise'] and c['grad_bitwise'], 'nosync only changes the original paths, which defer does not use'
    r3 = run_one(w, a, ['defer', 'pad64p'], mb, 8)
    check_close(compare(run_one(w, a, ['pad64p'], mb, 8), r3), 'defer + pad64p vs pad64p')


# ---------------------------------------------------------------------------------------------------------------------------------- T7
def test_t7_twenty_updates_baseline_vs_defer_same_seed():
    w, a = world()
    old = (a.lr_steps, a.lr_warmup)
    a.lr_steps, a.lr_warmup = 60, 2                                               # a schedule that moves the weights within 20 updates
    try:
        res = {}
        for tag, names in (('base', []), ('defer', ['defer'])):
            tr = prof.Trainer(w, a, names, accum=4)
            try:
                losses = []
                for _ in range(20):
                    loss, _s, _t = tr.update()
                    losses.append(float(loss))
                res[tag] = (losses, torch.cat([p.detach().double().flatten() for p in tr.model.parameters()]), tr.variant_stats())
            finally:
                tr.close()
    finally:
        a.lr_steps, a.lr_warmup = old
    l0, l1 = np.array(res['base'][0]), np.array(res['defer'][0])
    d = np.abs(l1 - l0)
    pmax = float((res['defer'][1] - res['base'][1]).abs().max())
    prel = float((res['defer'][1] - res['base'][1]).norm() / res['base'][1].norm())
    say(f'T7 20 updates (tiny, accum 4, lr over 60 steps): per-update |loss diff| max {d.max():.3e} mean {d.mean():.3e} (loss range {l0.min():.3f}..{l0.max():.3f}); relative max {np.max(d / np.abs(l0)):.2e}; '
        f'final parameters: max abs diff {pmax:.3e}, rel L2 {prel:.3e}; first-update diff {d[0]:.2e}; defer stats {res["defer"][2]["defer"]["deferred_losses"]} deferred, {res["defer"][2]["defer"]["fallback_losses"]} fallback')
    assert res['defer'][2]['defer']['deferred_losses'] == 80 and res['defer'][2]['defer']['fallback_losses'] == 0
    assert np.all(np.isfinite(l1)) and np.max(d / np.abs(l0)) < 1e-3 and pmax < 1e-3


# ---------------------------------------------------------------------------------------------------------------------------------- T8
def test_t8_the_runner_runs_abequiv_for_defer_and_registers_the_exact_arms_of_the_folder():
    _load()
    d = tempfile.mkdtemp(prefix='defer_t8_')
    out = os.path.join(d, 'ab.json')
    prof.AB_STATE.clear()
    res = prof_launch.main(['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--pkg-root', prof.PK.root,
                            '--sections', 'abequiv', '--ab-variants', 'defer', '--out', out])
    S = res['sections']['abequiv']
    assert 'error' not in S, S.get('error')
    v = S['variants']['defer']
    assert 'error' not in v and 'skipped' not in v, v
    mk = v['mark6']
    assert mk['cpu_fp32_rule'] == 'equal_to_rounding' and mk['label'] == 'bar_and_cpu_fp32' and mk['holds'] and mk['bar_holds'] and mk['cpu_fp32_checked'] and mk['bit_exact_cpu_fp32'] is False
    assert mk['equal_to_rounding_cpu_fp32'] is True and mk['cpu_fp32_clause_holds'] is True, mk
    assert v['fp32']['rel_loss_diff'] <= prof.AB_ROUND_REL and v['fp32']['grad_rel_l2'] <= prof.AB_ROUND_REL
    assert S['mark6_by_variant'] == {'defer': True} and S['errors'] == []
    say(f'T8 abequiv defer (tiny, fp32 CPU): rel loss {v["fp32"]["rel_loss_diff"]:.2e}, grad cos {v["fp32"]["grad_cos"]:.12f}, rel L2 {v["fp32"]["grad_rel_l2"]:.2e}, step cos {v["fp32"]["step_cos"]:.12f}, '
        f'bit exact {v["fp32"]["bit_exact"]}, mark 6 {mk["verdict"]} [{mk["label"]}]; rerun floor bit exact {S["reference"]["fp32"]["rerun"]["bit_exact"]}')
    md = open(os.path.splitext(out)[0] + '.md').read()
    assert 'defer' in md and '## abequiv' in md
    # abbench with defer as an arm (2 updates, 1 round): the variant arm runs end to end
    out2 = os.path.join(d, 'bench.json')
    res2 = prof_launch.main(['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--pkg-root', prof.PK.root,
                             '--sections', 'abbench', '--ab-variants', 'defer', '--ab-accums', '', '--ab-rounds', '1', '--ab-warmup', '1', '--ab-updates', '2', '--chunk', '2', '--out', out2])
    arm = res2['sections']['abbench']['arms']['defer']
    assert 'error' not in arm and arm['rounds_completed'] == 1 and arm['b_runs'][0]['variant_stats']['defer']['deferred_losses'] == 12, arm.get('error')
    # the profiler-style use: --variant defer through the breakdown section
    out3 = os.path.join(d, 'bd.json')
    res3 = prof_launch.main(['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--pkg-root', prof.PK.root,
                             '--variant', 'defer', '--sections', 'breakdown', '--updates', '2', '--warmup', '1', '--out', out3])
    assert 'error' not in res3['sections']['breakdown'], res3['sections']['breakdown'].get('error')


@contextlib.contextmanager
def registries_restored():
    saved = (dict(prof.VARIANTS), prof.SETUP_ORDER, dict(prof.AB_CPU_RULE), prof.AB_ARM_ORDER)
    try:
        yield
    finally:
        prof.VARIANTS.clear(); prof.VARIANTS.update(saved[0]); prof.SETUP_ORDER = saved[1]; prof.AB_CPU_RULE.clear(); prof.AB_CPU_RULE.update(saved[2]); prof.AB_ARM_ORDER = saved[3]


def test_t8_fake_exact_arms_module_is_registered_and_a_broken_one_is_survived():
    """Under a module name that is NOT 'exact_arms' (prof_launch.register_all(exact_module=...)), loaded from a temp dir, so this test never depends on what sits in the launch folder."""
    _load()
    d = tempfile.mkdtemp(prefix='defer_exact_')
    mod = 'fake_exact_arms_for_test'
    sys.modules.pop(mod, None)
    sys.path.insert(0, d)
    try:
        with registries_restored():
            open(os.path.join(d, mod + '.py'), 'w').write(
                'import prof_train as prof\n'
                'class FakeExact(prof.Variant):\n    name = "fake_exact"\n    doc = "a fake"\n    ab_cpu_rule = "bit_exact"\n'
                'NEW_VARIANTS = [FakeExact]\n')
            names = prof_launch.register_all(lambda *x: None, exact_module=mod)
            assert 'defer' in names and 'fake_exact' in names
            assert prof.VARIANTS['fake_exact'].name == 'fake_exact' and prof.AB_CPU_RULE['fake_exact'] == 'bit_exact' and prof.AB_CPU_RULE['defer'] == 'equal_to_rounding'
            assert prof.SETUP_ORDER.index('fake_exact') < prof.SETUP_ORDER.index('baseline') and prof.AB_ARM_ORDER.index('fake_exact') < prof.AB_ARM_ORDER.index('accum 8')
            assert 'fake_exact' in prof.ab_default_variants().split(',') and prof.parse_variants('fake_exact,defer,nosync') == ['nosync', 'fake_exact', 'defer']
            assert prof.parse_ab_variants('defer,fake_exact') == ['defer', 'fake_exact']
            names2 = prof_launch.register_all(lambda *x: None, exact_module=mod)     # idempotent
            assert names2 == names and prof.SETUP_ORDER.count('defer') == 1 and prof.AB_ARM_ORDER.count('defer') == 1
            # a broken module: reported, defer still registered
            sys.modules.pop(mod, None)
            open(os.path.join(d, mod + '.py'), 'w').write('raise RuntimeError("boom")\n')
            msgs = []
            assert prof_launch.load_exact_arms(msgs.append, mod) == [] and msgs and 'NOT registered' in msgs[0]
            # a missing module: silently no arms
            assert prof_launch.load_exact_arms(msgs.append, 'no_such_exact_arms_module') == []
    finally:
        sys.path.remove(d)
        sys.modules.pop(mod, None)


def test_t8_the_real_exact_arms_of_the_folder_are_registered_with_their_rules_and_positions():
    """If exact_arms.py sits in this folder (another agent's file, only READ here): every class of its NEW_VARIANTS is registered under its name, with AB_CPU_RULE equal to the class's ab_cpu_rule
    (default bar_only), SETUP_ORDER after its anchor (setup_after, default nosync) and before 'baseline', AB_ARM_ORDER after 'unfused' and before 'accum 8'. Skipped (and counted as skipped)
    when there is no exact_arms.py."""
    _load()
    if not os.path.exists(os.path.join(HERE, 'exact_arms.py')):
        raise unittest.SkipTest('no exact_arms.py in the launch folder')
    with registries_restored():
        names = prof_launch.register_all(lambda *x: None)
        mod = importlib.import_module('exact_arms')
        arms = list(mod.NEW_VARIANTS)
        assert arms and set(c.name for c in arms) <= set(names), (names, [c.name for c in arms])
        for cls in arms:
            n = cls.name
            assert prof.VARIANTS[n] is cls, n
            assert prof.AB_CPU_RULE[n] == (getattr(cls, 'ab_cpu_rule', None) or 'bar_only'), (n, prof.AB_CPU_RULE[n])
            anchor = getattr(cls, 'setup_after', 'nosync')
            assert prof.SETUP_ORDER.index(anchor) < prof.SETUP_ORDER.index(n) < prof.SETUP_ORDER.index('baseline'), (n, prof.SETUP_ORDER)
            assert prof.AB_ARM_ORDER.index('unfused') < prof.AB_ARM_ORDER.index(n) < prof.AB_ARM_ORDER.index('accum 8'), (n, prof.AB_ARM_ORDER)
            assert n in prof.ab_default_variants().split(',')
        say('T8 real exact arms registered: ' + ', '.join(f'{c.name} (rule {prof.AB_CPU_RULE[c.name]}, setup index {prof.SETUP_ORDER.index(c.name)}, ab index {prof.AB_ARM_ORDER.index(c.name)})' for c in arms))


ALL = [(n, fn) for n, fn in sorted(globals().items()) if n.startswith('test_') and callable(fn)]


def main():
    """Runs every test_*; prints PASS / SKIP / FAIL; the last line counts the three APART (a skipped test did not run: it is not a pass)."""
    bad, skipped, passed, t_all = 0, 0, 0, time.time()
    for n, fn in ALL:
        t0 = time.time()
        try:
            fn()
            passed += 1
            print(f'PASS {n} ({time.time() - t0:.1f}s)', flush=True)
        except unittest.SkipTest as e:
            skipped += 1
            print(f'SKIP {n}: {e}', flush=True)
        except Exception:                                                        # noqa: BLE001
            import traceback
            bad += 1
            print(f'FAIL {n} ({time.time() - t0:.1f}s)', flush=True)
            traceback.print_exc()
    print(f'{passed} passed, {skipped} skipped, {bad} failed (of {len(ALL)}) in {time.time() - t_all:.1f}s', flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
