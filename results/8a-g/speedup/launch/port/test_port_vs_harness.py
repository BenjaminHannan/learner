"""test_port_vs_harness.py: the port IS the GPU-tested code (DRAFT until the coordinator has code-reviewed the pack). CPU, fp32, one thread.

  python test_port_vs_harness.py          (env: BASE_TREE=<folder with the UNMODIFIED custom_io of 74d6e92c75>, else built with git archive; PORT_TREE=<a tree made by make_port_tree.py>, else built into a temp dir;
   both are checked first: the base pins and the overlay sha256 values; ALLOW_SKIP=1 lets a SKIP pass)

What it compares: model A = the harness's variant (launch/defer.py, `Defer`, set up exactly as launch/test_defer.py does through prof_train.Trainer(..., ['defer'])) on the BASE tree; model B = the
same model on the PORT tree with `speed_defer = True` and NO harness variant. defer.py's source-hash guard checks B3G2.plan / _loss, which the port edits, so it would refuse on the port tree:
the two models therefore run in two subprocesses on two trees (the harness world is built by launch/test_defer.py's own world() / full_batch() / run_one() in both), with identical seeds, and the
results are dumped and compared BIT FOR BIT here: per scenario the loss, every aux value, every parameter gradient (torch.equal) and the RNG states (torch default generator, gap rng, drill rng),
then 3 optimizer updates through Trainer.update() (loss of each update, final state_dict). Scenarios: the T1 / T3 / nontrivial-right ones of test_defer.py (K pinned 4 / 8 / 16 / 32, K drawn,
4-row micro-batch, gap_p 1, ans_drill 1, only call rows, only no-call rows, writer cap 7, label 'right'), each with the real ByteWriter.right and with the non-trivial stand-in.
A SKIP is not a pass; exit code 1 on any FAIL.
"""
import contextlib, hashlib, os, shutil, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.normpath(os.path.join(HERE, '..'))
PROFDIR = os.path.normpath(os.path.join(LAUNCH, '..', 'prof'))
COMMIT = '74d6e92c75'
OVERLAY = os.path.join(HERE, 'overlay')
BASE_PINS = {'custom_io/models/b3g2.py': 'a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce', 'custom_io/train.py': 'e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d'}
TREES = {}                                                                     # scratch / base / port, made (and checked) once by test_000 and reused by the test


# ---------------------------------------------------------------------------------------------------------------------------------- child
def child(role, out):
    """role 'harness': the harness's Defer on this tree (the base); role 'port': speed_defer True on this tree (the port), no variant. Runs every scenario, dumps the results to `out`."""
    import torch
    for p in (PROFDIR, LAUNCH):
        if p not in sys.path:
            sys.path.insert(0, p)
    import test_defer as TD                                                    # noqa: E402  (the harness's own world / batches / run_one / nontrivial_right)
    torch.set_num_threads(1)
    w, a = TD.world()
    names = ['defer'] if role == 'harness' else []

    def flag(tw):
        def tweak(m):
            if tw:
                tw(m)
            if role == 'port':
                assert hasattr(m, 'speed_defer') and m.speed_defer is False
                m.speed_defer = True
        return tweak

    def run(mb, K, tw=None):
        r = TD.run_one(w, a, names, mb, K, tweak=flag(tw))
        if role == 'port':
            import custom_io.models.b3g2_defer as DF
            st = DF.stats(r['model'])
            assert r['variants'] == [] and r['model'].defer_counts['deferred'] == 1 and r['model'].defer_counts['fallback'] == 0, (r['variants'], r['model'].defer_counts)
        else:
            st = r['stats']['defer']
            assert st['deferred_losses'] == 1 and st['fallback_losses'] == 0, r['stats']
        return dict(loss=r['loss'], aux={k: (v.detach().clone() if torch.is_tensor(v) else v) for k, v in r['aux'].items()}, grads=r['grads'], rng=r['rng'], stats=st)

    @contextlib.contextmanager
    def port_guard_knows_right(role):
        """TD.nontrivial_right moves the harness's source-hash guard for ByteWriter.right to its stand-in; the port's own guard (b3g2_defer.SRC_HASH_WRITER) is moved the same way."""
        if role != 'port':
            yield
            return
        import custom_io.models.b3g2_defer as DF
        from custom_io.models.writer import ByteWriter
        old = DF.SRC_HASH_WRITER['right']
        DF.SRC_HASH_WRITER['right'] = DF.src_hash(ByteWriter.__dict__['right'])
        try:
            yield
        finally:
            DF.SRC_HASH_WRITER['right'] = old

    mb16, mb4 = TD.full_batch(w), TD.micro_batch(w, 1)
    calling = [i for i, r in enumerate(mb16['rows']) if r.get('steps')]
    nocall = [i for i, r in enumerate(mb16['rows']) if not r.get('steps')]
    assert calling and nocall
    setg = lambda **kw: (lambda m: [setattr(m, k, v) for k, v in kw.items()])
    scen = [('16 rows, K 8', mb16, 8, None), ('16 rows, K drawn (KS)', mb16, None, None), ('4 rows, K 16', mb4, 16, None), ('K 4', mb16, 4, None), ('K 32', mb16, 32, None),
            ('gap_p 1', mb16, 16, setg(gap_p=1.0)), ('ans_drill 1', mb16, 8, setg(ans_drill=1.0)), ('gap_p 1 + ans_drill 1, K 32', mb16, 32, setg(gap_p=1.0, ans_drill=1.0)),
            ('only call rows', TD.pick_rows(mb16, calling), 8, setg(gap_p=0.0)), ('only no-call rows', TD.pick_rows(mb16, nocall), 8, None), ('writer cap 7', mb16, 8, setg(WCAP=7)),
            ("label 'right'", mb16, 16, setg(label='right'))]
    res = dict(real={}, nontrivial={}, updates=None)
    for name, mb, K, tw in scen:
        res['real'][name] = run(mb, K, tw)
    with TD.nontrivial_right(), port_guard_knows_right(role):
        for name, mb, K, tw in scen:
            res['nontrivial'][name] = run(mb, K, tw)
    # 3 optimizer updates through the harness's Trainer.update() (fetch, prep, split into accum micro-batches, loss + backward each, clip, AdamW)
    tr = TD.prof.Trainer(w, a, names, accum=4)
    try:
        if role == 'port':
            tr.model.speed_defer = True
        losses = [tr.update()[0].detach().clone() for _ in range(3)]
        sd = {k: v.detach().clone() for k, v in tr.model.state_dict().items()}
        if role == 'port':
            import custom_io.models.b3g2_defer as DF
            stats = DF.stats(tr.model)
        else:
            stats = tr.variant_stats()['defer']
    finally:
        tr.close()
    res['updates'] = dict(losses=losses, final_sd=sd, deferred=stats['deferred_losses'], stats=stats)
    torch.save(res, out)


# ---------------------------------------------------------------------------------------------------------------------------------- parent
def say(*a):
    print('   ', *a, flush=True)


def tree_base(scratch):
    if os.environ.get('BASE_TREE'):
        return os.environ['BASE_TREE']
    d = os.path.join(scratch, 'base')
    os.makedirs(d)
    top = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
    p = subprocess.run(f'git -C "{top}" archive {COMMIT} custom_io | tar -x -C "{d}"', shell=True, capture_output=True, text=True)
    if p.returncode:
        raise unittest.SkipTest(f'no base tree (set BASE_TREE): {p.stderr}')
    return d


def tree_port(scratch):
    if os.environ.get('PORT_TREE'):
        return os.environ['PORT_TREE']
    d = os.path.join(scratch, 'port')
    p = subprocess.run([sys.executable, os.path.join(HERE, 'make_port_tree.py'), d], capture_output=True, text=True)
    if p.returncode:
        raise unittest.SkipTest(f'make_port_tree.py failed: {p.stdout[-500:]} {p.stderr[-800:]}')
    return d


def spawn(role, tree, out):
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PROF_PKG_ROOT=tree, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('CUSTOM_IO_ROOT', None)
    env['PYTHONPATH'] = tree
    p = subprocess.run([sys.executable, os.path.abspath(__file__), '--child', role, out], env=env, capture_output=True, text=True, cwd=os.path.dirname(out))
    assert p.returncode == 0, f'{role} child on {tree}: rc {p.returncode}\n{p.stdout[-2500:]}\n{p.stderr[-3500:]}'
    import torch
    return torch.load(out, map_location='cpu', weights_only=False)


def same(x, y, what):
    import torch
    if torch.is_tensor(x):
        assert torch.is_tensor(y) and x.dtype == y.dtype and x.shape == y.shape and torch.equal(x, y), what
    elif isinstance(x, dict):
        assert list(x) == list(y), (what, list(x), list(y))
        for k in x:
            same(x[k], y[k], f'{what}.{k}')
    elif isinstance(x, (list, tuple)):
        assert type(x) == type(y) and len(x) == len(y), what
        for i, (p, q) in enumerate(zip(x, y)):
            same(p, q, f'{what}[{i}]')
    else:
        assert x == y and type(x) == type(y), (what, x, y)


def sha_file(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def test_000_the_trees_under_test_are_the_pinned_ones():
    """Before anything runs (BASE_TREE / PORT_TREE if given, else the trees this test builds): the base b3g2.py / train.py are the 74d6e92c75 pins and every overlay file has the sha256 of port/overlay (FAIL on a mismatch)."""
    scratch = tempfile.mkdtemp(prefix='port-vs-harness-')
    TREES['scratch'] = scratch
    base, port = tree_base(scratch), tree_port(scratch)
    TREES['base'], TREES['port'] = base, port
    bad = [f'base {rel}: sha256 {sha_file(os.path.join(base, rel))[:16]} != pin {pin[:16]}' for rel, pin in BASE_PINS.items() if sha_file(os.path.join(base, rel)) != pin]
    n = 0
    for dp, dn, fn in os.walk(os.path.join(OVERLAY, 'custom_io')):
        dn[:] = [d for d in dn if d != '__pycache__']
        for f in fn:
            if f.endswith('.pyc'):
                continue
            rel = os.path.relpath(os.path.join(dp, f), OVERLAY)
            n += 1
            if not os.path.exists(os.path.join(port, rel)) or sha_file(os.path.join(port, rel)) != sha_file(os.path.join(dp, f)):
                bad.append(f'port tree {rel}: differs from {os.path.join(OVERLAY, rel)}')
    assert not bad, '; '.join(bad)
    say(f'trees: base b3g2.py / train.py match the 74d6e92c75 pins; {n} overlay files match the port tree {port}')


def test_make_port_tree_refuses_src_b3g2_folders_in_any_case():
    scratch = tempfile.mkdtemp(prefix='mpt-names-')
    try:
        for name in ('SRC-B3G2CK', 'src-b3g2ck', 'Src-B3g2', 'src-b3g2'):
            for sub in ('x', ''):
                out = os.path.join(scratch, name, sub) if sub else os.path.join(scratch, name)
                p = subprocess.run([sys.executable, os.path.join(HERE, 'make_port_tree.py'), out], capture_output=True, text=True)
                assert p.returncode != 0 and 'REFUSED' in (p.stderr + p.stdout) and not os.path.exists(out), (name, sub, p.returncode, p.stderr[-300:])
        assert not os.path.exists(os.path.join(scratch, 'SRC-B3G2CK')), 'nothing may be created'
        say('make_port_tree.py refuses SRC-B3G2CK/x, src-b3g2ck/x, Src-B3g2/x, src-b3g2 (and the folders themselves), nothing created')
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_port_equals_the_gpu_tested_harness_variant_bitwise():
    if 'port' not in TREES:
        raise unittest.SkipTest('the trees were not made (see test_000)')
    scratch, base, port = TREES['scratch'], TREES['base'], TREES['port']
    a = spawn('harness', base, os.path.join(scratch, 'harness.pt'))
    b = spawn('port', port, os.path.join(scratch, 'port.pt'))
    n = 0
    for kind in ('real', 'nontrivial'):
        assert list(a[kind]) == list(b[kind])
        for name in a[kind]:
            ra, rb = a[kind][name], b[kind][name]
            same(ra['loss'], rb['loss'], f'{kind}/{name}: loss')
            same(ra['aux'], rb['aux'], f'{kind}/{name}: aux')
            same(ra['grads'], rb['grads'], f'{kind}/{name}: gradients')
            same(ra['rng'], rb['rng'], f'{kind}/{name}: RNG states')
            same({k: v for k, v in ra['stats'].items() if k != 'numerics'}, {k: v for k, v in rb['stats'].items() if k != 'numerics'}, f'{kind}/{name}: per-micro-batch counters (Defer.stats vs b3g2_defer.stats)')
            n += 1
    ua, ub = a['updates'], b['updates']
    same(ua['losses'], ub['losses'], 'update losses')
    same(ua['final_sd'], ub['final_sd'], 'final state_dict')
    same({k: v for k, v in ua['stats'].items() if k != 'numerics'}, {k: v for k, v in ub['stats'].items() if k != 'numerics'}, 'counters after 3 updates')
    assert ua['deferred'] == ub['deferred'] == 12, (ua['deferred'], ub['deferred'])          # 3 updates x accum 4 micro-batches, every loss deferred
    say(f'{n} scenarios ({len(a["real"])} with the real ByteWriter.right, {len(a["nontrivial"])} with the non-trivial one): loss, every aux value, every gradient tensor and the RNG states BIT-EQUAL, and the per-micro-batch counters (call / EOS-only / answer pairs, call width, rounds, rows) equal the harness Defer.stats; '
        f'3 AdamW updates through Trainer.update(): per-update losses {[float(x) for x in ua["losses"]]} and the final {len(ua["final_sd"])} state_dict tensors BIT-EQUAL; deferred losses {ua["deferred"]} / {ub["deferred"]}')


ALL = [(n, fn) for n, fn in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno if callable(kv[1]) and hasattr(kv[1], '__code__') else 0) if n.startswith('test_') and callable(fn)]


def main():
    """test_000 (the trees are the pinned ones) first; a FAIL there stops everything. Exit 1 on any FAIL, and on any SKIP unless ALLOW_SKIP=1 (a skip is not a pass)."""
    bad, skipped, passed, t_all, why = 0, 0, 0, time.time(), []
    for n, fn in ALL:
        t0 = time.time()
        try:
            fn()
            passed += 1
            print(f'PASS {n} ({time.time() - t0:.1f}s)', flush=True)
        except unittest.SkipTest as e:
            skipped += 1
            why.append(f'{n}: {e}')
            print(f'SKIP {n}: {e}', flush=True)
        except Exception:                                                        # noqa: BLE001
            import traceback
            bad += 1
            print(f'FAIL {n} ({time.time() - t0:.1f}s)', flush=True)
            traceback.print_exc()
            if n.startswith('test_000'):
                print('the trees under test are not the pinned ones: nothing else was run', flush=True)
                break
    print(f'{passed} passed, {skipped} skipped, {bad} failed (of {len(ALL)}) in {time.time() - t_all:.1f}s', flush=True)
    rc = 1 if bad else 0
    if skipped and os.environ.get('ALLOW_SKIP') != '1':
        print(f'EXIT 1: {skipped} test(s) skipped, and a skip is not a pass (ALLOW_SKIP=1 to accept): ' + ' | '.join(why), flush=True)
        rc = 1
    if TREES.get('scratch'):
        shutil.rmtree(TREES['scratch'], ignore_errors=True)
    return rc


if __name__ == '__main__':
    if sys.argv[1:2] == ['--child']:
        child(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
