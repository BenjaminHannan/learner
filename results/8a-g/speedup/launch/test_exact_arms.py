"""CPU tests for exact_arms.py (the candidate-EXACT arms 'kvcat' and 'fastteach'): fp32 on the CPU at 1 thread, stub Gemma, synthetic rows; no GPU, no network. The tiny tests take about 1.5 minutes.

  python test_exact_arms.py                    (a mini runner calls every test_* and prints PASS / FAIL / SKIP and a summary of passed / skipped / failed / selected; no pytest needed)
  EXACT_ARMS_REAL=1 python test_exact_arms.py  also runs the REAL 3M shape tests: ONE micro-batch of 64 rows, K pinned to 16 (about 3 minutes at 1 thread, more while the box is busy)
  EXACT_ARMS_WRITE=1 ...                       the counts are written to exact_arms_counts.json ONLY with this set (that file is the record the report cites); otherwise to a scratch file in the temp dir
  python test_exact_arms.py --box-ckpt <prof_launch arguments>
                                               the CHECK FOR THE CUDA BOX (see box_ckpt_check): K forced to 32 so that rounds t >= n_loops are checkpointed, bf16 autocast, baseline vs baseline, then baseline vs kvcat

What is shown here (and only here): for each arm separately against train.py's own code, same seed, same batches, fp32 on the CPU at 1 thread: loss tensors and aux, every parameter gradient, three full
updates (split -> micro-batch loss -> backward -> clip_grad_norm_ -> AdamW, fused=False on the CPU) and all parameters afterwards, BITWISE each time (same() compares the int bit patterns, so -0.0 and +0.0 differ); with K forced to 4, 32 (checkpointed rounds)
and to the tiny model's own draws; the free run (run / talk / generate, no_grad, eval) with calls written so that the tape K/V is rebuilt; teardown identity; ATen dispatch and host-sync
call-site counts. What is NOT shown: anything on CUDA (kernel selection, timing, launches, memory), bf16 on CUDA, bit-equality at 2 or more CPU threads (the unmodified code is not run-to-run bitwise there: test_7b records it). bf16 here means torch.autocast('cpu', dtype=torch.bfloat16).

The package is found through $PROF_PKG_ROOT / $CUSTOM_IO_ROOT (the folder that CONTAINS custom_io/), else /home/user/src-g2f (custom_io at 74d6e92c75), else the tests skip.
"""
import collections, contextlib, json, os, random, sys, tempfile, time, types, unittest
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exact_arms as ea                                                      # noqa: E402
import prof_launch                                                           # noqa: E402  (registers the arms the way the launch runner does)
prof = ea.prof

OUT = os.path.join(HERE, 'exact_arms_counts.json')
SCRATCH_OUT = os.path.join(tempfile.gettempdir(), 'exact_arms_counts_scratch.json')
_CACHE = {}
ARMS = ('kvcat', 'fastteach')
DEFAULT_PKG = '/home/user/src-g2f'


def _find_pkg():
    for var in ('PROF_PKG_ROOT', 'CUSTOM_IO_ROOT'):
        p = os.environ.get(var)
        if p and os.path.isdir(os.path.join(p, 'custom_io')):
            return p
    if os.path.isdir(os.path.join(DEFAULT_PKG, 'custom_io')):
        return DEFAULT_PKG
    raise unittest.SkipTest('no custom_io package: set PROF_PKG_ROOT to the folder that contains custom_io/ at commit 74d6e92c75')


def _load():
    if 'pkg' not in _CACHE:
        torch.set_num_threads(1)
        prof.load_pkg(_find_pkg())
        prof_launch.register(ea.NEW_VARIANTS)
        _CACHE['pkg'] = True


def world(arm='B3G2'):
    """The tiny CPU world of test_prof.py (d 48, 1 block, batch 16, accum 4 -> 4 rows per micro-batch)."""
    key = ('tiny', arm)
    if key not in _CACHE:
        _load()
        a = prof.build_parser().parse_args(['--arm', arm, '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--out', os.devnull])
        a.accum = a.accum or prof.ARM_INFO[a.arm]['accum']
        _CACHE[key] = (prof.World(a), a)
    return _CACHE[key]


def world_real():
    """The REAL 3M shape on the CPU (4,023,302 trained params), batch 256, accum 4 -> 64 rows per micro-batch. Prompts at most 300 letters (--synth-letters 300): the 2000-letter default needs about 10 GB for the baseline alone
    (17 rounds x 2 blocks of 129 MB concatenated K and V), more than this box has free; the op and sync counts do not depend on the prompt width, only the sizes do."""
    if 'real' not in _CACHE:
        _load()
        a = prof.build_parser().parse_args(['--arm', 'B3G2', '--rung', '3M', '--accum', '4', '--batch', '256', '--data', 'synthetic', '--rows', '2000', '--synth-letters', '300', '--eg', 'stub', '--device', 'cpu',
                                            '--caps', os.path.join(prof.PK.root, 'custom_io', 'g8a', 'caps_b3g2.json'), '--out', os.devnull])
        _CACHE['real'] = (prof.World(a), a)
    return _CACHE['real']


def b3g2_mod():
    return sys.modules['custom_io.models.b3g2']


@contextlib.contextmanager
def forced_K(k):
    """Monkeypatch the KS tuple in custom_io.models.b3g2's module namespace (B3G2._loss reads it there): every micro-batch draws K = k (the torch.randint draw still happens, so the RNG stream is unchanged)."""
    mod = b3g2_mod()
    old = mod.KS
    if k is not None:
        mod.KS = (k,)
    try:
        yield
    finally:
        mod.KS = old


def cpu_batch(w, seed=7):
    return next(w.batches(seed))


def micro_batches(w, a, cpu, accum=4):
    dev = prof.PK.D.to_device(cpu, w.device)
    return [{k: v for k, v in mb.items() if not k.startswith('_')} for mb in prof.PK.TR.split_batch(dev, accum)]


_INT_OF = {2: torch.int16, 4: torch.int32, 8: torch.int64}


def bits(x):
    """The tensor's bit pattern as integers (a float tensor is viewed as an int of the same width), so -0.0 and +0.0, and NaNs with different payloads, are different."""
    x = x.detach().contiguous()
    return x.view(_INT_OF[x.element_size()]) if (x.is_floating_point() or x.is_complex()) else x


def same(x, y):
    """BITWISE-equal values for tensors (same dtype, same shape, same bit pattern: -0.0 != +0.0); plain == for other values (a nan float equals a nan float); None == None."""
    if torch.is_tensor(x) or torch.is_tensor(y):
        if not (torch.is_tensor(x) and torch.is_tensor(y)) or x.dtype != y.dtype or x.shape != y.shape:
            return False
        return bool(torch.equal(bits(x), bits(y)))
    if isinstance(x, float) and isinstance(y, float) and x != x and y != y:
        return True
    return x == y


def aux_same(a, b):
    return sorted(a) == sorted(b) and all(same(a[k], b[k]) for k in a)


def micro_pass(w, a, names, K=None, amp=contextlib.nullcontext, seed=1234, mbs=None, batch_seed=7, accum=4):
    """One update's micro-batch loop of train.py without clip / optimizer, on a fresh model of the same seeded init with the variants `names`: -> dict(loss [per micro-batch tensors], aux [dicts],
    grads [per parameter, after (loss / k).backward() of every micro-batch, accumulated like train.py], stats)."""
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=accum)
    try:
        mbs = micro_batches(w, a, cpu_batch(w, batch_seed), accum) if mbs is None else mbs
        tr.model.zero_grad(set_to_none=True)
        out = dict(loss=[], aux=[])
        with forced_K(K):
            torch.manual_seed(seed)
            for mb in mbs:
                with amp():
                    l, aux = tr.model.loss(mb)
                (l / len(mbs)).backward()
                out['loss'].append(l.detach()); out['aux'].append(aux)
        out['grads'] = [None if p.grad is None else p.grad.detach().clone() for p in tr.model.parameters()]
        out['stats'] = tr.variant_stats()
        return out
    finally:
        tr.close()


def assert_micro_equal(base, got, what):
    assert all(same(x, y) for x, y in zip(base['loss'], got['loss'])), f'{what}: loss tensors differ'
    assert all(aux_same(x, y) for x, y in zip(base['aux'], got['aux'])), f'{what}: aux differs'
    bad = [i for i, (x, y) in enumerate(zip(base['grads'], got['grads'])) if not same(x, y)]
    assert not bad, f'{what}: {len(bad)} of {len(base["grads"])} parameter gradients differ (first: {bad[:5]})'
    assert sum(g is None for g in base['grads']) == sum(g is None for g in got['grads'])


def train_updates(w, a, names, n=3, K=None, amp=contextlib.nullcontext):
    """n full updates through Trainer.update (train.py's sequence: split, micro-batches, clip_grad_norm_ 1.0, AdamW, fused=False on the CPU) -> (losses, state_dict, stats)."""
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
    try:
        losses = []
        with forced_K(K):
            for _ in range(n):
                with amp():
                    l, _, _ = tr.update()
                losses.append(l.detach().clone() if torch.is_tensor(l) else torch.tensor(float(l)))
        return losses, {k: v.detach().clone() for k, v in tr.model.state_dict().items()}, tr.variant_stats()
    finally:
        tr.close()


# ---------------------------------------------------------------------------------------------------------------------------------- counters
class OpCounter(torch.utils._python_dispatch.TorchDispatchMode):
    """Counts every ATen dispatch by op name, split into view ops (the schema's return aliases an input read-only: select, slice, view, permute, expand, detach ...) and the rest. In-place ops count as
    non-view (they run a kernel). Forward and backward ops are both seen while the mode is active."""

    def __init__(self):
        super().__init__()
        self.ops, self.views = collections.Counter(), collections.Counter()
        self.in_teacher, self.teacher_ops = False, collections.Counter()     # non-view ops dispatched while ByteWriter.teacher runs (count_micro sets the flag)

    def __torch_dispatch__(self, func, types_, args=(), kwargs=None):
        sch = func._schema
        name = sch.name
        if any(r.alias_info is not None and not r.alias_info.is_write for r in sch.returns):
            self.views[name] += 1
        else:
            self.ops[name] += 1
            if self.in_teacher:
                self.teacher_ops[name] += 1
        return func(*args, **(kwargs or {}))

    @property
    def total(self):
        return sum(self.ops.values())


class SyncCounter:
    """Counts the CALLS of the methods that read a device value on the host or move data across devices, by kind and call site (file:line of the caller): Tensor.tolist / item / cpu / nonzero /
    numpy / __bool__ / __int__ / __float__ / __index__, Tensor.to with a device target (blocking vs non_blocking=True), torch.tensor(..., device=...). On the CPU none of them waits; each is a place that
    WOULD wait on a CUDA tensor (a call on a tensor that was built on the host counts too: an upper bound, the call sites tell which). Not counted: torch.zeros(..., device=) (a device fill, no host data),
    .to(dtype), .to(other tensor), kernels that sync inside torch (cudaStreamSynchronize from the caching allocator)."""
    NAMES = ('tolist', 'item', 'cpu', 'nonzero', 'numpy', '__bool__', '__int__', '__float__', '__index__')

    def __init__(self):
        self.kinds, self.sites = collections.Counter(), collections.Counter()
        self._orig = []

    def _hit(self, kind):
        f = sys._getframe(2)
        if os.path.basename(f.f_code.co_filename) == 'prof_train.py':        # StubEG (the stand-in for the frozen Gemma): its first call fills a cache, later ones do not; identical in every arm, not the model's
            return
        self.kinds[kind] += 1
        self.sites[f'{kind} @ {os.path.basename(f.f_code.co_filename)}:{f.f_lineno}'] += 1

    def __enter__(self):
        me = self

        def wrap(orig, kind):
            def w(*a, **kw):
                me._hit(kind)
                return orig(*a, **kw)
            return w
        for n in self.NAMES:
            o = getattr(torch.Tensor, n)
            self._orig.append((torch.Tensor, n, o)); setattr(torch.Tensor, n, wrap(o, n))
        o_to = torch.Tensor.to

        def to(self_, *a, **kw):
            tgt = kw.get('device', a[0] if a else None)
            if isinstance(tgt, (torch.device, str)) or (isinstance(tgt, int) and not isinstance(tgt, bool)):
                me._hit('to_nonblocking' if (kw.get('non_blocking') or (len(a) > 2 and a[2])) else 'to_blocking')
            return o_to(self_, *a, **kw)
        self._orig.append((torch.Tensor, 'to', o_to)); torch.Tensor.to = to
        o_t = torch.tensor

        def tensor(*a, **kw):
            if kw.get('device') is not None:
                me._hit('torch.tensor(device=)')
            return o_t(*a, **kw)
        self._orig.append((torch, 'tensor', o_t)); torch.tensor = tensor
        return self

    def __exit__(self, *exc):
        for obj, n, o in reversed(self._orig):
            setattr(obj, n, o)
        self._orig.clear()


@contextlib.contextmanager
def pretend_cuda_copies():
    """On the CPU prof_train.to_device_async is a plain .to; on CUDA it is pinned + non_blocking. For COUNTING, make it the CUDA flavour (the values are the same) so a pinned non_blocking copy is not
    counted as a blocking one."""
    old = prof.to_device_async
    prof.to_device_async = lambda v, device: v.to(device, non_blocking=True)
    try:
        yield
    finally:
        prof.to_device_async = old


def count_micro(w, a, names, mb, K, amp=contextlib.nullcontext, grads=False):
    """ONE micro-batch `mb` (forward, then backward of loss / 4) with the arms `names` and K pinned: ATen dispatches (non-view and view, forward and backward) and host-sync call sites."""
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
    try:
        if getattr(w, 'eg', None) is not None:
            w.eg._last = None; w.eg.load(w.device)                          # the stub front memoises its last call: forget it, so every counted pass does the same front work
        tr.model.zero_grad(set_to_none=True)
        fo, bo, sc = OpCounter(), OpCounter(), SyncCounter()
        BW = prof.PK.models.writer.ByteWriter
        orig_teacher = BW.__dict__['teacher']                              # installed AFTER the arms' setup (their source-hash guard reads the original text); restored below

        def counted_teacher(*a, **kw):
            fo.in_teacher = True
            try:
                return orig_teacher.__func__(*a, **kw)
            finally:
                fo.in_teacher = False
        BW.teacher = staticmethod(counted_teacher)
        t0 = time.time()
        with forced_K(K), pretend_cuda_copies():
            torch.manual_seed(1234)
            with sc, fo:
                with amp():
                    l, aux = tr.model.loss(mb)
            t1 = time.time()
            with bo:
                (l / 4).backward()
        t2 = time.time()
        g = [None if p.grad is None else p.grad.detach().clone() for p in tr.model.parameters()] if grads else None
        return dict(fwd_ops=dict(fo.ops), fwd_views=dict(fo.views), bwd_ops=dict(bo.ops), bwd_views=dict(bo.views), n_fwd=fo.total, n_bwd=bo.total, teacher_ops=dict(fo.teacher_ops),
                    syncs=dict(sc.kinds), sync_sites=dict(sc.sites), rounds=float(aux['rounds']), loss=l.detach(), grads=g, stats=tr.variant_stats(), fwd_s=t1 - t0, bwd_s=t2 - t1)
    finally:
        BW.teacher = orig_teacher
        tr.close()


def save_counts(key, data):
    """The record file exact_arms_counts.json is written ONLY when EXACT_ARMS_WRITE=1; otherwise the numbers (timings are noisy) go to a scratch file in the temp dir."""
    path = OUT if os.environ.get('EXACT_ARMS_WRITE') == '1' else SCRATCH_OUT
    cur = json.load(open(path)) if os.path.exists(path) else {}
    cur[key] = data
    json.dump(cur, open(path, 'w'), indent=1, sort_keys=True)


SYNC_KINDS = ('tolist', 'item', 'cpu', 'nonzero', 'numpy', 'to_blocking', 'torch.tensor(device=)')        # calls that wait for the device (or copy pageable host memory to it) when the tensor is on CUDA
TRUTH_KINDS = ('__bool__', '__int__', '__float__', '__index__')                                          # python reading a tensor as bool / int: a sync only when that tensor is on the device (many here are CPU tensors)


def summarize(c):
    sy = collections.Counter(c['syncs'])
    sites = collections.Counter(c['sync_sites'])
    return dict(rounds=c['rounds'], nonview_aten_ops_inside_bytewriter_teacher=sum(c['teacher_ops'].values()), nonview_aten_ops_outside_bytewriter_teacher=c['n_fwd'] + c['n_bwd'] - sum(c['teacher_ops'].values()),
                nonview_aten_ops_forward=c['n_fwd'], nonview_aten_ops_backward=c['n_bwd'], nonview_aten_ops_total=c['n_fwd'] + c['n_bwd'],
                aten_cat_forward=c['fwd_ops'].get('aten::cat', 0), aten_cat_backward=c['bwd_ops'].get('aten::cat', 0),
                host_sync_call_sites_executed={k: sy[k] for k in SYNC_KINDS if sy.get(k)}, host_sync_total=sum(sy[k] for k in SYNC_KINDS),
                blocking_h2d_to_calls=sy.get('to_blocking', 0), nonblocking_h2d_to_calls=sy.get('to_nonblocking', 0),
                tensor_truth_value_reads={k: sy[k] for k in TRUTH_KINDS if sy.get(k)}, tensor_truth_value_total=sum(sy[k] for k in TRUTH_KINDS),
                sync_sites={k: v for k, v in sorted(sites.items()) if k.split(' @ ')[0] in SYNC_KINDS}, truth_value_sites={k: v for k, v in sorted(sites.items()) if k.split(' @ ')[0] in TRUTH_KINDS},
                nonblocking_sites={k: v for k, v in sorted(sites.items()) if k.startswith('to_nonblocking')},
                variant_stats={k: {kk: vv for kk, vv in v.items() if kk != 'exact'} for k, v in c['stats'].items()},
                forward_seconds_with_counters=round(c['fwd_s'], 2), backward_seconds_with_counters=round(c['bwd_s'], 2))


def op_delta(base, arm, n=12):
    ops = collections.Counter()
    for part in ('fwd_ops', 'bwd_ops'):
        for k in set(base[part]) | set(arm[part]):
            ops[k] += arm[part].get(k, 0) - base[part].get(k, 0)
    return dict(sorted(((k, v) for k, v in ops.items() if v), key=lambda kv: -abs(kv[1]))[:n])


# ================================================================================================================================ fastteach: the tensors
def random_targets(rng, cap, B):
    """Target lists the way B3G2 passes them: None (no target), [] (a row that is asked to stop), normal, exactly len + 1 == cap, over-cap len + 1 == cap + 1 and longer; ids anywhere in 0..299 incl. BOS / EOS."""
    out = []
    for _ in range(B):
        kind = rng.choice(['none', 'empty', 'short', 'short', 'normal', 'normal', 'fit', 'over', 'long'])
        n = dict(none=0, empty=0, short=rng.randint(1, 4), normal=rng.randint(1, max(1, cap - 2)), fit=cap - 1, over=cap, long=cap + rng.randint(1, 40))[kind]
        out.append(None if kind == 'none' else [rng.randint(0, 299) for _ in range(n)])
    return out


def test_teacher_np_equals_bytewriter_teacher_for_random_targets():
    _load()
    BW, D = prof.PK.models.writer.ByteWriter, prof.PK.D
    bos, eos = D.BOS, D.EOS
    rng = random.Random(0)
    n_cases = 0
    for cap in (1, 2, 3, 9, 69, 70):
        for it in range(300):
            B = rng.randint(1, 9)
            tg = random_targets(rng, cap, B)
            cids, cmask = torch.zeros(B, 1, dtype=torch.long), torch.zeros(B, 1, dtype=torch.bool)
            want = BW.teacher(tg, cids, cmask, cap, bos, eos)
            np_ = ea.teacher_np(tg, cap, bos, eos)
            got = dict(inp=torch.from_numpy(np_['inp']), tgt=torch.from_numpy(np_['tgt']), over=torch.from_numpy(np_['over']), fb=torch.zeros(B, np_['inp'].shape[1], 1))
            assert sorted(want) == sorted(got) == ['fb', 'inp', 'over', 'tgt']
            for k in want:
                assert want[k].dtype == got[k].dtype and want[k].shape == got[k].shape and want[k].stride() == got[k].stride() and torch.equal(want[k], got[k]), (cap, tg, k, want[k], got[k])
            n_cases += 1
    # the corners by hand
    for tg in ([None], [None, None, None], [[]], [[], None, [5]], [[1] * 8, [2] * 9, [3] * 10], [(4, 5), np.array([6, 7])]):
        for cap in (1, 9, 10):
            B = len(tg)
            want = BW.teacher(tg, torch.zeros(B, 1, dtype=torch.long), torch.zeros(B, 1, dtype=torch.bool), cap, bos, eos)
            np_ = ea.teacher_np(tg, cap, bos, eos)
            assert torch.equal(want['inp'], torch.from_numpy(np_['inp'])) and torch.equal(want['tgt'], torch.from_numpy(np_['tgt'])) and torch.equal(want['over'], torch.from_numpy(np_['over']))
            assert want['fb'].shape == (B, np_['inp'].shape[1], 1) and not want['fb'].any()
    assert n_cases == 1800


def test_the_original_teacher_feedback_is_zero_for_line_context():
    # the premise of fastteach: with line_context's cids / cmask, ByteWriter.teacher's fb is all zero whatever the targets are (so a writer that ignores fb, copy False, cannot see a difference)
    _load()
    w, a = world()
    m = w.new_model(0)
    rng = random.Random(1)
    Z = torch.zeros(7, 3, m.d)
    for _ in range(50):
        tg = random_targets(rng, m.WCAP, 7)
        te = type(m).answer_teacher(m, Z, tg)
        assert not te['fb'].any() and te['fb'].shape[2] == 1
    assert m.writer.copy is False


def test_answer_teacher_variant_returns_the_same_four_tensors():
    w, a = world()
    tr = prof.Trainer(w, a, ['fastteach'], accum=4)
    try:
        m = tr.model
        assert 'answer_teacher' in m.__dict__
        rng = random.Random(2)
        Z = torch.zeros(8, 5, m.d)
        for _ in range(200):
            tg = random_targets(rng, m.WCAP, 8)
            got, want = m.answer_teacher(Z, tg), type(m).answer_teacher(m, Z, tg)
            assert sorted(got) == sorted(want)
            assert all(got[k].dtype == want[k].dtype and got[k].shape == want[k].shape and got[k].stride() == want[k].stride() and got[k].device == want[k].device and torch.equal(got[k], want[k]) for k in want)
        assert tr.variant_stats()['fastteach']['teacher_calls_numpy'] == 200
    finally:
        tr.close()


# ================================================================================================================================ tests 1 + 2: one micro-batch, loss / aux / gradients
def test_1_2_loss_aux_and_every_gradient_bit_equal_each_arm():
    w, a = world()
    base = micro_pass(w, a, [])
    assert len(base['loss']) == 4 and all(g is not None for g in base['grads'][:3])
    for arm in ARMS + ('kvcat,fastteach', 'nosync,fastteach,kvcat'):
        got = micro_pass(w, a, arm.split(','))
        assert_micro_equal(base, got, arm)
        st = got['stats']
        if 'kvcat' in arm:
            assert st['kvcat']['cat_cache_hits'] > 0, f'{arm}: the kvcat cache really hit (else equality is vacuous)'
        if 'fastteach' in arm:
            assert st['fastteach']['teacher_calls_numpy'] > 0, f'{arm}: fastteach really ran'


def test_2b_a_second_batch_and_seed_also_equal():
    w, a = world()
    for batch_seed, seed in ((11, 5), (12, 6)):
        base = micro_pass(w, a, [], batch_seed=batch_seed, seed=seed)
        for arm in ARMS:
            assert_micro_equal(base, micro_pass(w, a, [arm], batch_seed=batch_seed, seed=seed), f'{arm} batch {batch_seed}')


# ================================================================================================================================ test 4: K forced, checkpointed rounds
def test_4_k_forced_32_and_4_cover_checkpointed_rounds():
    w, a = world()
    seen_ckpt = False
    for K in (32, 4):
        base = micro_pass(w, a, [], K=K)
        assert all(float(x['rounds']) >= K for x in base['aux']), 'K is forced'
        for arm in ARMS:
            got = micro_pass(w, a, [arm], K=K)
            assert_micro_equal(base, got, f'{arm} K={K}')
            if arm == 'kvcat' and K == 32:
                s = got['stats']['kvcat']
                # rounds t >= n_loops (12 on the tiny model) are recomputed by the non-reentrant checkpoint inside backward: the cache is bypassed there and the values still match
                assert s['cat_cache_bypassed_in_backward'] > 0, s
                seen_ckpt = True
    assert seen_ckpt


def test_4b_checkpoint_recompute_does_not_use_or_fill_the_cache():
    w, a = world()
    tr = prof.Trainer(w, a, ['kvcat'], accum=4)
    try:
        mb = micro_batches(w, a, cpu_batch(w))[0]
        v = tr.variants[0]
        with forced_K(32):
            torch.manual_seed(3)
            l, _ = tr.model.loss(mb)
            assert v.cache == {}, 'cleared when loss returns'
            h0, m0, b0 = v.hits, v.misses, v.bypass
            l.backward()
        assert v.bypass > b0 and v.hits == h0 and v.misses == m0, 'inside backward: neither a hit nor a miss'
        assert v.cache == {}, 'backward leaves nothing behind'
    finally:
        tr.close()


# ================================================================================================================================ test 3: three full updates
def test_3_three_full_updates_all_parameters_equal_each_arm():
    w, a = world()
    l0, p0, _ = train_updates(w, a, [])
    for arm in ARMS + ('kvcat,fastteach',):
        l1, p1, st = train_updates(w, a, arm.split(','))
        assert all(same(x, y) for x, y in zip(l0, l1)), f'{arm}: update losses differ'
        assert sorted(p0) == sorted(p1) and all(same(p0[k], p1[k]) for k in p0), f'{arm}: parameters differ after 3 updates: {[k for k in p0 if not same(p0[k], p1[k])][:5]}'


def test_3b_three_updates_k_forced_32_and_4_each_arm():
    w, a = world()
    for K in (32, 4):
        l0, p0, _ = train_updates(w, a, [], K=K)
        for arm in ARMS:
            l1, p1, _ = train_updates(w, a, [arm], K=K)
            assert all(same(x, y) for x, y in zip(l0, l1)) and all(same(p0[k], p1[k]) for k in p0), f'{arm} K={K}'


def test_3c_parameters_really_moved():
    w, a = world()
    _, p0, _ = train_updates(w, a, [], n=3)
    init = w.new_model(a.seed).state_dict()
    assert sum(not torch.equal(p0[k], init[k]) for k in p0) > 10, 'the updates changed the weights (so equality of weights after 3 updates is not vacuous)'


# ================================================================================================================================ test 5: the free run
def fake_call_greedy(m):
    """A deterministic stand-in for the writer's call (an untrained model never writes a call): at some rounds some rows write `add 12 5`, so the tape is rebuilt in the free run."""
    st = dict(i=0)

    def call_greedy(Z, temperature=0.0, generator=None, zm=None):
        i = st['i']; st['i'] += 1
        B = Z.shape[0]
        outs = [m.vocab.encode('add 12 5') if (i + j) % 3 == 0 else [] for j in range(B)]
        return outs, torch.ones(B, dtype=torch.bool)
    return call_greedy


def no_call_greedy(m):
    """The same stand-in with a writer that never writes a call: the tape (and so its K/V) is never rebuilt."""
    def call_greedy(Z, temperature=0.0, generator=None, zm=None):
        return [[] for _ in range(Z.shape[0])], torch.ones(Z.shape[0], dtype=torch.bool)
    return call_greedy


def free_run_results(w, a, names, writes_calls=True):
    mk = fake_call_greedy if writes_calls else no_call_greedy
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
    try:
        m = tr.model
        m.eval()
        m.call_greedy = mk(m)
        res = []
        mbs = micro_batches(w, a, cpu_batch(w))
        with torch.no_grad():
            for mb in mbs[:2]:
                o = m.run(mb)                                               # the learned stop
                ans = m.talk(m.state_of(o), mb)
                res.append(('run', o['Z'], o['tape'], o['calls'], o['rounds'], ans))
                o2 = m.run(mb, loops=6)                                     # a forced run (settles)
                res.append(('run6', o2['Z'], o2['tape'], o2['calls'], o2['records'], m.talk(m.state_of(o2), mb)))
                res.append(('generate', m.generate(mb)))
            m.call_greedy = mk(m)
            res.append(('loop-direct', m.loop(mbs[2], 5)['Z']))              # a direct loop() call (call_evals does this)
        return res, tr.variant_stats(), [len(c) for r in res if r[0] in ('run', 'run6') for c in r[3]]
    finally:
        tr.close()


def deep_same(x, y):
    if isinstance(x, (list, tuple)):
        return isinstance(y, (list, tuple)) and len(x) == len(y) and all(deep_same(p, q) for p, q in zip(x, y))
    return same(x, y)


def test_5_free_run_bitwise_identical_with_kvcat_and_cache_invalidated_after_calls():
    w, a = world()
    base, _, ncalls0 = free_run_results(w, a, [])
    assert sum(ncalls0) > 0, 'the fake writer wrote calls: the tape K/V was rebuilt during the free run'
    for arm in (['kvcat'], ['fastteach'], ['kvcat', 'fastteach']):
        got, st, _ = free_run_results(w, a, arm)
        assert deep_same(base, got), f'{arm}: free run differs'
        if 'kvcat' in arm:
            s = st['kvcat']
            # The EQUALITY above is what proves a rebuilt tape is not served stale (a stale-cache mutant, key = block only, fails it). The counts only show that the rebuild happens: the same free run with a
            # writer that writes NO call (tape K/V never rebuilt) must miss strictly less than the run with calls. (Each entry point clears the cache when it starts, so the miss count alone proves nothing.)
            _, st0, n0 = free_run_results(w, a, arm, writes_calls=False)
            assert sum(n0) == 0 and s['cat_cache_hits'] > 0 and s['cat_cache_misses'] > st0['kvcat']['cat_cache_misses'], (s, st0['kvcat'])


def test_5b_cache_cleared_after_every_entry_point_and_after_an_exception():
    w, a = world()
    tr = prof.Trainer(w, a, ['kvcat'], accum=4)
    try:
        m, v = tr.model, tr.variants[0]
        mb = micro_batches(w, a, cpu_batch(w))[0]
        with torch.no_grad():
            m.eval()
            m.run(mb, loops=3); assert v.cache == {}
            m.loop(mb, 3); assert v.cache == {}
            m.talk(m.state_of(m.run(mb, loops=2)), mb); assert v.cache == {}
        orig = m.core[0].__dict__['_kvcat_get']

        def boom(kvs, kvx):
            r = orig(kvs, kvx)
            if v.hits >= 1:
                raise RuntimeError('boom')
            return r
        m.core[0]._kvcat_get = boom
        try:
            with torch.no_grad():
                m.run(mb, loops=4)
        except RuntimeError:
            pass
        else:
            raise AssertionError('the injected error did not fire')
        assert v.cache == {}, 'an exception leaves nothing behind either'
    finally:
        tr.close()


def test_5c_stale_cache_is_impossible_for_inplace_or_new_tensors():
    # the key: identity of kvs / kvx, their _version, grad mode. Changing any of them misses.
    w, a = world()
    tr = prof.Trainer(w, a, ['kvcat'], accum=4)
    try:
        m, v = tr.model, tr.variants[0]
        blk = m.core[0]
        kvs, kvx = torch.randn(2, 2, 2, 5, 24), torch.randn(2, 2, 2, 7, 24)
        Z, mask = torch.randn(2, 3, m.d), torch.ones(2, 12, dtype=torch.bool)
        ref = lambda: torch.cat([kvs[0], kvx[0]], 2)
        blk(Z, kvs, kvx, mask); h, mi = v.hits, v.misses
        blk(Z, kvs, kvx, mask); assert (v.hits, v.misses) == (h + 1, mi)
        kvs.add_(1.0)                                                        # an in-place write: version changes -> miss
        out = blk(Z, kvs, kvx, mask); assert v.misses == mi + 1
        with torch.no_grad():                                                # another grad mode: miss
            blk(Z, kvs, kvx, mask)
        assert v.misses == mi + 2
        kvs2 = kvs.clone()                                                   # same values, another object: miss
        blk(Z, kvs2, kvx, mask); assert v.misses == mi + 3
        e = v.cache[id(blk)]
        assert torch.equal(e[4], torch.cat([kvs2[0], kvx[0]], 2)) and torch.equal(e[5], torch.cat([kvs2[1], kvx[1]], 2))
    finally:
        tr.close()


# ================================================================================================================================ test 6: teardown
def snapshot(m):
    return {id(o): dict(o.__dict__) for o in [m] + list(m.core) + [m.writer]}


def test_6_teardown_restores_everything_by_identity():
    w, a = world()
    cls_fwd = type(w.new_model(0).core[0]).forward
    cls_at = type(w.new_model(0)).answer_teacher
    for arm in ARMS + ('both',):
        tr = prof.Trainer(w, a, [], accum=4)
        try:
            m = tr.model
            before = snapshot(m)
            vs = [ea.KvCat(tr), ea.FastTeach(tr)] if arm == 'both' else [dict(kvcat=ea.KvCat, fastteach=ea.FastTeach)[arm](tr)]
            for v in vs:
                v.setup()
            after = snapshot(m)
            assert after != before and (any('forward' in d for k, d in after.items()) or 'answer_teacher' in after[id(m)]), 'setup changed something'
            for v in reversed(vs):
                v.teardown()
            restored = snapshot(m)
            for k in before:
                assert sorted(before[k]) == sorted(restored[k]), (arm, sorted(set(before[k]) ^ set(restored[k])))
                assert all(before[k][n] is restored[k][n] for n in before[k]), arm
            assert type(m.core[0]).forward is cls_fwd and type(m).answer_teacher is cls_at
            assert not any(n in m.__dict__ for n in ea.ENTRY_POINTS + ('answer_teacher',)) and not any('forward' in b.__dict__ or '_kvcat_get' in b.__dict__ for b in m.core)
        finally:
            tr.close()
    # through the Trainer: close() does it too, and a second trainer on a fresh model is untouched
    tr = prof.Trainer(w, a, ['kvcat', 'fastteach'], accum=4)
    m = tr.model
    assert 'forward' in m.core[0].__dict__ and 'answer_teacher' in m.__dict__
    tr.close()
    assert 'forward' not in m.core[0].__dict__ and 'answer_teacher' not in m.__dict__ and 'loss' not in m.__dict__ and tr.variants == []


def test_6b_skips_when_not_applicable_and_registry():
    _load()
    wp, ap = world('PTS')
    for n in ARMS:
        try:
            prof.Trainer(wp, ap, [n], accum=4)
        except prof.Skip as e:
            assert n in str(e)
        else:
            raise AssertionError(f'{n} on a plain arm must say it does not apply')
    w, a = world()
    tr = prof.Trainer(w, a, [], accum=4)
    try:
        tr.model.writer.copy = True                                          # a copy writer: fb is not zero
        try:
            ea.FastTeach(tr).setup()
        except prof.Skip as e:
            assert 'copy path' in str(e)
        else:
            raise AssertionError('fastteach must refuse a writer with a copy path')
        assert 'answer_teacher' not in tr.model.__dict__
        tr.model.writer.copy = False
    finally:
        tr.close()
    assert [c.name for c in ea.NEW_VARIANTS] == ['kvcat', 'fastteach'] and all(prof.VARIANTS[n] is c for n, c in zip(ARMS, ea.NEW_VARIANTS))
    assert all(prof.AB_CPU_RULE[n] == 'bit_exact' for n in ARMS) and all(n in prof.SETUP_ORDER and n in prof.AB_ARM_ORDER for n in ARMS)
    assert prof.SETUP_ORDER.index('nosync') < prof.SETUP_ORDER.index('fastteach') < prof.SETUP_ORDER.index('baseline') and prof.SETUP_ORDER.index('kvcat') < prof.SETUP_ORDER.index('baseline')
    assert prof.parse_variants('fastteach,kvcat,nosync')[:1] == ['nosync'] and all(len(prof.VARIANTS[n].doc) > 200 for n in ARMS)


def test_6c_source_guard_refuses_other_code():
    w, a = world()
    tr = prof.Trainer(w, a, [], accum=4)
    old = dict(ea.SRC_HASH)
    try:
        ea.SRC_HASH['CBlock_forward'] = '000000000000'
        try:
            ea.KvCat(tr).setup()
        except prof.Skip as e:
            assert 'not the custom_io' in str(e)
        else:
            raise AssertionError('a different CBlock.forward source must be a Skip')
        assert 'forward' not in tr.model.core[0].__dict__
    finally:
        ea.SRC_HASH.clear(); ea.SRC_HASH.update(old)
        tr.close()


# ================================================================================================================================ bf16 CPU autocast
def test_bf16_cpu_autocast_kvcat_bit_equality():
    """Reported, not assumed: bf16 autocast on the CPU. K/V come out of the Linear in bf16; the cat is a copy; the gradient accumulation is bf16 on both sides. Writes the result to exact_arms_counts.json."""
    w, a = world()
    amp = lambda: torch.autocast('cpu', dtype=torch.bfloat16)
    res = {}
    for K in (None, 32):
        base = micro_pass(w, a, [], K=K, amp=amp)
        for arm in ARMS + ('kvcat,fastteach',):
            got = micro_pass(w, a, arm.split(','), K=K, amp=amp)
            lo = all(same(x, y) for x, y in zip(base['loss'], got['loss']))
            gr = [i for i, (x, y) in enumerate(zip(base['grads'], got['grads'])) if not same(x, y)]
            mx = max([float((x.double() - y.double()).abs().max()) for x, y in zip(base['grads'], got['grads']) if x is not None] + [0.0])
            res[f'{arm}|K={K or "model draw"}'] = dict(loss_bit_equal=lo, grads_differing=len(gr), n_grads=len(base['grads']), max_abs_grad_diff=mx)
    dt = [str(g.dtype) for g in base['grads'][:3]]
    save_counts('bf16_cpu_autocast', dict(results=res, grad_dtype=dt, note='torch.autocast(cpu, bfloat16) over model.loss, tiny shape'))
    assert all(r['loss_bit_equal'] and r['grads_differing'] == 0 for r in res.values()), res


def test_bf16_cpu_autocast_three_updates_kvcat():
    w, a = world()
    amp = lambda: torch.autocast('cpu', dtype=torch.bfloat16)
    l0, p0, _ = train_updates(w, a, [], amp=amp)
    for arm in ARMS:
        l1, p1, _ = train_updates(w, a, [arm], amp=amp)
        assert all(same(x, y) for x, y in zip(l0, l1)) and all(same(p0[k], p1[k]) for k in p0), arm


# ================================================================================================================================ test 7: op and sync counts
def test_7_tiny_op_and_sync_counts_baseline_vs_each_arm():
    w, a = world()
    mb = micro_batches(w, a, cpu_batch(w))[0]
    K = 16
    base = count_micro(w, a, [], mb, K)
    out = dict(baseline=summarize(base))
    for arm in ARMS + ('kvcat,fastteach',):
        c = count_micro(w, a, arm.split(','), mb, K)
        out[arm] = summarize(c); out[arm]['top_op_deltas_vs_baseline'] = op_delta(base, c)
    # kvcat: exactly two cats (k and v) fewer per cache hit; nothing else changes in the count of cats
    hits = out['kvcat']['variant_stats']['kvcat']['cat_cache_hits']
    cat0, cat1 = out['baseline']['aten_cat_forward'] + out['baseline']['aten_cat_backward'], out['kvcat']['aten_cat_forward'] + out['kvcat']['aten_cat_backward']
    assert hits > 0 and cat0 - cat1 == 2 * hits, (cat0, cat1, hits)
    assert out['kvcat']['nonview_aten_ops_total'] < out['baseline']['nonview_aten_ops_total']
    assert out['kvcat']['host_sync_total'] == out['baseline']['host_sync_total'], 'kvcat touches no host read'
    # fastteach: far fewer ATen ops (the per-byte loop), the two .cpu() and the four blocking .to per teacher call gone
    t_calls = out['fastteach']['variant_stats']['fastteach']['teacher_calls_numpy']
    b, f = collections.Counter(out['baseline']['host_sync_call_sites_executed']), collections.Counter(out['fastteach']['host_sync_call_sites_executed'])
    b['to_nonblocking'], f['to_nonblocking'] = out['baseline']['nonblocking_h2d_to_calls'], out['fastteach']['nonblocking_h2d_to_calls']
    assert out['fastteach']['nonview_aten_ops_total'] < out['baseline']['nonview_aten_ops_total']
    assert b.get('cpu', 0) - f.get('cpu', 0) == 2 * t_calls, (b, f, t_calls)
    assert b.get('to_blocking', 0) - f.get('to_blocking', 0) == 4 * t_calls and f.get('to_nonblocking', 0) - b.get('to_nonblocking', 0) == 3 * t_calls, (b, f, t_calls)
    out['K'] = K; out['rows_per_micro_batch'] = len(mb['rows'])
    save_counts('tiny_k16_4rows', out)


def test_7_real_3m_shape_one_micro_batch_of_64_rows_k16():
    if not os.environ.get('EXACT_ARMS_REAL'):
        raise unittest.SkipTest('set EXACT_ARMS_REAL=1 (about 1 minute at 1 thread: 3 passes at the real 3M shape)')
    w, a = world_real()
    cpu = next(w.batches(7))
    mb = micro_batches(w, a, cpu)[0]
    assert len(mb['rows']) == 64
    K = 16
    runs = {}
    base = count_micro(w, a, [], mb, K, grads=True)
    runs['baseline'] = base
    for arm in ARMS:
        runs[arm] = count_micro(w, a, [arm], mb, K, grads=True)
    out = {n: summarize(c) for n, c in runs.items()}
    for arm in ARMS:
        out[arm]['top_op_deltas_vs_baseline'] = op_delta(base, runs[arm], 14)
        c = runs[arm]
        out[arm]['loss_bit_equal'] = bool(same(base['loss'], c['loss']))
        gd = [i for i, (x, y) in enumerate(zip(base['grads'], c['grads'])) if not same(x, y)]
        out[arm]['grads_differing'] = len(gd); out[arm]['n_grads'] = len(base['grads'])
    out['n_trained_params'] = w.n_params; out['K'] = K; out['rows_per_micro_batch'] = 64; out['blocks'] = len(w.new_model(0).core)
    save_counts('real_3m_k16_64rows', out)
    for arm in ARMS:
        assert out[arm]['loss_bit_equal'] and out[arm]['grads_differing'] == 0, (arm, out[arm])
        assert out[arm]['nonview_aten_ops_total'] < out['baseline']['nonview_aten_ops_total']
    # the 2-block, K = 16 shape is the only place the per-block key id(blk) is exercised and rounds 12..15 are checkpointed: assert that the cache hit and that the recompute bypassed it
    ks = out['kvcat']['variant_stats']['kvcat']
    assert out['blocks'] == 2 and ks['cat_cache_hits'] > 0 and ks['cat_cache_bypassed_in_backward'] > 0, ks


def test_7b_real_two_threads_is_the_baseline_itself_run_to_run_bitwise():
    """RECORDS (no assertion on the outcome) what happens at 2 CPU threads, real 3M shape, ONE 64-row micro-batch, K = 16: the unmodified code against ITSELF (base vs base2), then kvcat and fastteach against the
    first baseline, by bit pattern. If base vs base2 already differs, no arm can be bit-identical at 2 threads and the 1-thread result is the one that proves the arm."""
    if not os.environ.get('EXACT_ARMS_REAL'):
        raise unittest.SkipTest('set EXACT_ARMS_REAL=1')
    w, a = world_real()
    mbs = micro_batches(w, a, cpu_batch(w))[:1]
    torch.set_num_threads(2)
    try:
        runs = {n: micro_pass(w, a, names, K=16, mbs=mbs) for n, names in (('base', []), ('base2', []), ('kvcat', ['kvcat']), ('fastteach', ['fastteach']))}
    finally:
        torch.set_num_threads(1)

    def cmp(x, y):
        bad = [i for i, (p, q) in enumerate(zip(x['grads'], y['grads'])) if not same(p, q)]
        mx = max([float((p.double() - q.double()).abs().max()) for p, q in zip(x['grads'], y['grads']) if p is not None] + [0.0])
        return dict(loss_bit_equal=bool(same(x['loss'][0], y['loss'][0])), grads_differing=len(bad), n_grads=len(x['grads']), max_abs_grad_diff=mx)
    save_counts('real_3m_k16_64rows_TWO_threads', dict(base_vs_base2=cmp(runs['base'], runs['base2']), base_vs_kvcat=cmp(runs['base'], runs['kvcat']), base_vs_fastteach=cmp(runs['base'], runs['fastteach']),
                                                        base2_vs_kvcat=cmp(runs['base2'], runs['kvcat']), threads=2, K=16, rows=64))


# ================================================================================================================================ host time of one teacher call
def teacher_target_sets(m, rows):
    gold = m.train_golds(rows)
    first_call = [(x['ids'][0] if x['ids'] else None) for x in gold]
    after = [([] if x['ids'] else None) for x in gold]
    return {'answers (ans_ids, every row)': [x['ans_ids'] for x in gold], 'first calls (None for rows without a call)': first_call, 'stop lines ([] for rows with calls, None else)': after}


def host_time_of_teacher(w, a, rows, reps=40):
    """Median wall time of ONE answer_teacher call on the CPU (host python + CPU tensor work only; no device exists here), original vs fastteach vs nosync, for gold targets of `rows`."""
    out = {}
    trs = {n: prof.Trainer(w, a, prof.parse_variants(n), accum=4) for n in ('', 'nosync', 'fastteach')}
    try:
        sets = teacher_target_sets(trs[''].model, rows)
        Z = torch.zeros(len(rows), 4, trs[''].model.d)
        for label, ids in sets.items():
            row = {}
            for n, tr in trs.items():
                f = tr.model.answer_teacher
                ts = []
                for _ in range(reps):
                    t0 = time.perf_counter(); f(Z, ids); ts.append(time.perf_counter() - t0)
                row[n or 'baseline'] = round(float(np.median(ts)) * 1e3, 3)
            row['n_bytes'] = int(sum(len(t) + 1 for t in ids if t is not None)); row['rows_with_target'] = sum(t is not None for t in ids)
            out[label] = row
        return out
    finally:
        for tr in trs.values():
            tr.close()


def test_8_host_time_of_one_teacher_call_cpu():
    w, a = world()
    rows = w.rows[:64]
    res = host_time_of_teacher(w, a, rows)
    for label, r in res.items():
        assert r['fastteach'] < r['baseline'], (label, r)
    save_counts('host_ms_per_teacher_call_cpu_64_rows_tiny_world', res)


def test_8_real_host_time_of_one_teacher_call_cpu_real_golds():
    if not os.environ.get('EXACT_ARMS_REAL'):
        raise unittest.SkipTest('set EXACT_ARMS_REAL=1')
    w, a = world_real()
    res = host_time_of_teacher(w, a, w.rows[:64])
    for label, r in res.items():
        assert r['fastteach'] < r['baseline'], (label, r)
    save_counts('host_ms_per_teacher_call_cpu_64_rows_real_3m_golds', res)


def teacher_time_inside_micro_batch(w, a, names, mb, K):
    """Seconds of host time spent INSIDE answer_teacher during one forward pass of the micro-batch `mb` (K pinned) and the number of calls: wall time of the calls themselves, on the CPU."""
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
    try:
        m = tr.model
        inner, acc = m.answer_teacher, dict(s=0.0, n=0)

        def timed(Z, ids):
            t0 = time.perf_counter()
            try:
                return inner(Z, ids)
            finally:
                acc['s'] += time.perf_counter() - t0; acc['n'] += 1
        m.answer_teacher = timed
        w.eg._last = None; w.eg.load(w.device)
        t0 = time.perf_counter()
        with forced_K(K), torch.no_grad():
            torch.manual_seed(1234)
            m.loss(mb)
        return dict(teacher_seconds=round(acc['s'], 4), teacher_calls=acc['n'], forward_seconds_total=round(time.perf_counter() - t0, 3))
    finally:
        tr.close()


def test_8_teacher_time_inside_one_micro_batch_cpu():
    w, a = world()
    mb = micro_batches(w, a, cpu_batch(w))[0]
    best = lambda names: min((teacher_time_inside_micro_batch(w, a, names, mb, 16) for _ in range(5)), key=lambda r: r['teacher_seconds'])      # best of 5: a shared box makes one tiny timing noisy
    base, fast = best([]), best(['fastteach'])
    assert fast['teacher_calls'] == base['teacher_calls'] and fast['teacher_seconds'] < base['teacher_seconds']
    save_counts('teacher_time_in_one_forward_cpu_tiny_4rows_k16', dict(baseline=base, fastteach=fast))


def test_8_real_teacher_time_inside_one_micro_batch_cpu():
    if not os.environ.get('EXACT_ARMS_REAL'):
        raise unittest.SkipTest('set EXACT_ARMS_REAL=1')
    w, a = world_real()
    mb = micro_batches(w, a, cpu_batch(w))[0]
    teacher_time_inside_micro_batch(w, a, [], mb, 16)                          # warm-up (allocator, stub front)
    best = lambda names: min((teacher_time_inside_micro_batch(w, a, names, mb, 16) for _ in range(3)), key=lambda r: r['teacher_seconds'])
    base, fast = best([]), best(['fastteach'])
    assert fast['teacher_calls'] == base['teacher_calls'] and fast['teacher_seconds'] < base['teacher_seconds']
    save_counts('teacher_time_in_one_forward_cpu_real_3m_64rows_k16', dict(baseline=base, fastteach=fast))


def _proc_kb(field):
    for line in open('/proc/self/status'):
        if line.startswith(field + ':'):
            return int(line.split()[1])


def rss_child(names):
    """Run in a fresh process: ONE forward + backward of the first 64-row micro-batch of the real 3M shape (prompts <= 300 letters, K 16) with the arms `names`; print the resident set (kB) before the
    forward, after it (the autograd graph with its saved tensors is alive), after the backward, and the peak (VmHWM) reached since the forward began is not separable from the build, so the figures are
    the deltas of the CURRENT resident set."""
    w, a = world_real()
    mb = micro_batches(w, a, cpu_batch(w))[0]
    tr = prof.Trainer(w, a, prof.parse_variants(','.join(names)), accum=4)
    w.eg._last = None; w.eg.load(w.device)
    r0 = _proc_kb('VmRSS')
    with forced_K(16):
        torch.manual_seed(1234)
        l, _ = tr.model.loss(mb)
    r1 = _proc_kb('VmRSS')
    (l / 4).backward()
    print('RSS_JSON ' + json.dumps(dict(arms=names, rss_before_forward_kb=r0, rss_after_forward_kb=r1, retained_by_forward_graph_kb=r1 - r0, rss_after_backward_kb=_proc_kb('VmRSS'))))


def test_9_real_resident_memory_of_the_forward_graph_baseline_vs_kvcat():
    if not os.environ.get('EXACT_ARMS_REAL'):
        raise unittest.SkipTest('set EXACT_ARMS_REAL=1')
    import subprocess
    out = {}
    for names in ([], ['kvcat']):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), '--rss', ','.join(names)], capture_output=True, text=True, env=dict(os.environ, OMP_NUM_THREADS='1'))
        line = [x for x in r.stdout.splitlines() if x.startswith('RSS_JSON ')]
        assert line, r.stdout[-500:] + r.stderr[-500:]
        out['+'.join(names) or 'baseline'] = json.loads(line[0][9:])
    save_counts('resident_memory_cpu_fp32_forward_graph_real_3m_64rows_width300_k16', out)
    assert out['kvcat']['retained_by_forward_graph_kb'] < out['baseline']['retained_by_forward_graph_kb']


def test_same_is_bitwise_signed_zero_and_nan_payload():
    z, nz = torch.zeros(3), torch.zeros(3)
    nz[1] = -0.0
    assert torch.equal(z, nz) and not same(z, nz), 'torch.equal calls -0.0 == +0.0; same() must not'
    assert same(z, torch.zeros(3)) and not same(z, torch.zeros(3, dtype=torch.float64)) and not same(z, torch.zeros(4))
    b = torch.tensor([1.0, 2.0], dtype=torch.bfloat16)
    assert same(b, b.clone()) and not same(b, b + 0.0078125)
    n1, n2 = torch.tensor([float('nan')]), torch.tensor([float('nan')]).view(torch.int32).add(1).view(torch.float32)
    assert same(n1, n1.clone()) and not same(n1, n2)
    assert same(torch.tensor([3, 4]), torch.tensor([3, 4])) and same(None, None) and not same(None, torch.zeros(1))


def box_ckpt_check(argv, K=32, n_micro=2, say=print):
    """THE CHECK FOR THE CUDA BOX that abequiv does NOT cover. abequiv pins K to K0 = max(8, longest gold program + 2); the real model has n_loops 12 and the thinker only checkpoints rounds t >= 12, so
    unless a row has a program of 11+ calls, abequiv never reaches kvcat's checkpoint path (the branch that reads torch._C._current_graph_task_id() on the autograd engine's device thread during the
    recompute), which is exactly what changes on CUDA. Here K is forced to `K` (32: rounds 12..31 are checkpointed) as test_4 does, under bf16 autocast of the arguments' device, on the first `n_micro`
    micro-batches of the arguments' data. Runs: base, base2, base3 (the same code three times), kvcat, fastteach. Reports, by bit pattern: the baseline against itself (the run-to-run noise of the unmodified code
    on this box: CUDA attention backward may be non-deterministic), base vs kvcat, base vs fastteach. PASS bar, fixed here before any CUDA number exists: let N = the set of gradient indices that differ in ANY
    pair of the three baselines, and M = the largest absolute gradient difference in any such pair; an arm passes if its differing gradients are all in N and its largest absolute difference is <= 4 M (so a
    baseline that repeats bitwise forces the arm to be bitwise equal; the factor 4 is a judgement, not derived), and its losses are bit-equal whenever the baseline's are; AND kvcat's
    cat_cache_bypassed_in_backward > 0 and cat_cache_hits > 0 (else the checkpoint path was not run and nothing was checked).
    argv: the prof_launch arguments (--arm B3G2 --rung 3M --accum 4 --batch 256 --data $POOL --pkg-root $S --caps ... [--device cuda]). -> (ok, dict)."""
    ap = prof.build_parser()
    a = ap.parse_args(list(argv))
    a.accum = a.accum or prof.ARM_INFO[a.arm]['accum']
    prof.load_pkg(a.pkg_root)
    prof_launch.register(ea.NEW_VARIANTS)
    w = prof.World(a)
    amp = lambda: torch.autocast(w.device.type, dtype=torch.bfloat16)
    mbs = micro_batches(w, a, cpu_batch(w), a.accum)[:n_micro]
    runs = {n: micro_pass(w, a, names, K=K, amp=amp, mbs=mbs, accum=a.accum) for n, names in (('base', []), ('base2', []), ('base3', []), ('kvcat', ['kvcat']), ('fastteach', ['fastteach']))}
    assert all(float(x['rounds']) >= K for x in runs['base']['aux']), 'K is forced'

    def diff(x, y):
        idx = {i for i, (p, q) in enumerate(zip(x['grads'], y['grads'])) if not same(p, q)}
        mx = max([float((p.double() - q.double()).abs().max()) for p, q in zip(x['grads'], y['grads']) if p is not None] + [0.0])
        return idx, mx, all(same(p, q) for p, q in zip(x['loss'], y['loss']))
    pairs = [diff(runs[p], runs[q]) for p, q in (('base', 'base2'), ('base', 'base3'), ('base2', 'base3'))]
    N, M, base_loss_eq = set().union(*[i for i, _, _ in pairs]), max(m for _, m, _ in pairs), all(l for _, _, l in pairs)
    res = dict(device=str(w.device), K=K, micro_batches=len(mbs), bf16_autocast=w.device.type, n_grads=len(runs['base']['grads']),
               baseline_vs_itself=dict(gradients_differing_in_any_pair=len(N), max_abs_grad_diff_any_pair=M, losses_bit_equal=base_loss_eq), kvcat_stats=runs['kvcat']['stats']['kvcat'])
    ok = True
    for arm in ('kvcat', 'fastteach'):
        idx, mx, leq = diff(runs['base'], runs[arm])
        c = dict(gradients_differing=len(idx), gradients_differing_outside_baseline_noise_set=len(idx - N), max_abs_grad_diff=mx, loss_bit_equal=leq)
        c['passes'] = bool(not (idx - N) and mx <= 4 * M and (leq or not base_loss_eq))
        res['base_vs_' + arm] = c
        ok &= c['passes']
    ks = res['kvcat_stats']
    res['checkpoint_path_ran'] = bool(ks['cat_cache_bypassed_in_backward'] > 0 and ks['cat_cache_hits'] > 0)
    ok &= res['checkpoint_path_ran']
    res['PASS'] = bool(ok)
    say('BOX_CKPT_JSON ' + json.dumps(res))
    return ok, res


def test_box_ckpt_check_runs_on_the_tiny_cpu_world():
    """The box check itself, exercised on the CPU (bf16 CPU autocast, tiny shape): it must run end to end, find the checkpoint path (bypass > 0), and pass at 1 thread."""
    _load()
    ok, res = box_ckpt_check(['--arm', 'B3G2', '--tiny', '--data', 'synthetic', '--rows', '600', '--batch', '16', '--accum', '4', '--eg', 'stub', '--device', 'cpu', '--out', os.devnull], say=lambda *x: None)
    assert res['checkpoint_path_ran'] and res['kvcat_stats']['cat_cache_bypassed_in_backward'] > 0, res
    assert ok, res
    save_counts('box_ckpt_check_run_on_tiny_cpu_bf16', res)


ALL = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]


def main():
    if sys.argv[1:2] == ['--rss']:
        rss_child([x for x in sys.argv[2].split(',') if x]) if len(sys.argv) > 2 else rss_child([])
        return 0
    if sys.argv[1:2] == ['--box-ckpt']:
        ok, _ = box_ckpt_check(sys.argv[2:])
        print('BOX CKPT CHECK: ' + ('PASS' if ok else 'FAIL'), flush=True)
        return 0 if ok else 1
    n_pass = n_skip = n_fail = 0
    t_all = time.time()
    only = sys.argv[1:]
    todo = [(n, f) for n, f in ALL if not only or any(o in n for o in only)]
    for n, f in todo:
        t0 = time.time()
        try:
            f()
            n_pass += 1
            print(f'PASS {n} ({time.time() - t0:.1f}s)', flush=True)
        except unittest.SkipTest as e:
            n_skip += 1
            print(f'SKIP {n}: {e}', flush=True)
        except Exception:                                                    # noqa: BLE001
            import traceback
            n_fail += 1
            print(f'FAIL {n} ({time.time() - t0:.1f}s)', flush=True)
            traceback.print_exc()
    print(f'{n_pass} passed, {n_skip} skipped, {n_fail} failed, of {len(todo)} selected ({len(ALL)} tests in the file) in {time.time() - t_all:.1f}s', flush=True)
    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(main())
