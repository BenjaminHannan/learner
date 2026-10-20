"""test_port_vs_harness.py: the port IS the GPU-tested code (DRAFT until the coordinator has code-reviewed the pack). CPU, fp32, one thread.

  python test_port_vs_harness.py          (env: BASE_TREE=<folder with the UNMODIFIED custom_io of 74d6e92c75>, else built with git archive; PORT_TREE=<a tree made by make_port_tree.py>, else built into a temp dir)

What it compares: model A = the harness's variant (launch/defer.py, `Defer`, set up exactly as launch/test_defer.py does through prof_train.Trainer(..., ['defer'])) on the BASE tree; model B = the
same model on the PORT tree with `speed_defer = True` and NO harness variant. defer.py's source-hash guard checks B3G2.plan / _loss, which the port edits, so it would refuse on the port tree:
the two models therefore run in two subprocesses on two trees (the harness world is built by launch/test_defer.py's own world() / full_batch() / run_one() in both), with identical seeds, and the
results are dumped and compared BIT FOR BIT here: per scenario the loss, every aux value, every parameter gradient (torch.equal) and the RNG states (torch default generator, gap rng, drill rng),
then 3 optimizer updates through Trainer.update() (loss of each update, final state_dict). Scenarios: the T1 / T3 / nontrivial-right ones of test_defer.py (K pinned 4 / 8 / 16 / 32, K drawn,
4-row micro-batch, gap_p 1, ans_drill 1, only call rows, only no-call rows, writer cap 7, label 'right'), each with the real ByteWriter.right and with the non-trivial stand-in.
A SKIP is not a pass; exit code 1 on any FAIL.
"""
import contextlib, os, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.normpath(os.path.join(HERE, '..'))
PROFDIR = os.path.normpath(os.path.join(LAUNCH, '..', 'prof'))
COMMIT = '74d6e92c75'


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
            assert r['variants'] == [] and r['model'].defer_stats == dict(deferred=1, fallback=0), (r['variants'], r['model'].defer_stats)
        else:
            assert r['stats']['defer']['deferred_losses'] == 1 and r['stats']['defer']['fallback_losses'] == 0, r['stats']
        return dict(loss=r['loss'], aux={k: (v.detach().clone() if torch.is_tensor(v) else v) for k, v in r['aux'].items()}, grads=r['grads'], rng=r['rng'])

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
    with TD.nontrivial_right():
        for name, mb, K, tw in scen:
            res['nontrivial'][name] = run(mb, K, tw)
    # 3 optimizer updates through the harness's Trainer.update() (fetch, prep, split into accum micro-batches, loss + backward each, clip, AdamW)
    tr = TD.prof.Trainer(w, a, names, accum=4)
    try:
        if role == 'port':
            tr.model.speed_defer = True
        losses = [tr.update()[0].detach().clone() for _ in range(3)]
        sd = {k: v.detach().clone() for k, v in tr.model.state_dict().items()}
        stats = tr.model.defer_stats if role == 'port' else tr.variant_stats()['defer']
    finally:
        tr.close()
    res['updates'] = dict(losses=losses, final_sd=sd, deferred=(stats['deferred'] if role == 'port' else stats['deferred_losses']))
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


def test_port_equals_the_gpu_tested_harness_variant_bitwise():
    scratch = tempfile.mkdtemp(prefix='port-vs-harness-')
    try:
        base, port = tree_base(scratch), tree_port(scratch)
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
                n += 1
        ua, ub = a['updates'], b['updates']
        same(ua['losses'], ub['losses'], 'update losses')
        same(ua['final_sd'], ub['final_sd'], 'final state_dict')
        assert ua['deferred'] == ub['deferred'] == 12, (ua['deferred'], ub['deferred'])          # 3 updates x accum 4 micro-batches, every loss deferred
        say(f'{n} scenarios ({len(a["real"])} with the real ByteWriter.right, {len(a["nontrivial"])} with the non-trivial one): loss, every aux value, every gradient tensor and the RNG states BIT-EQUAL; '
            f'3 AdamW updates through Trainer.update(): per-update losses {[float(x) for x in ua["losses"]]} and the final {len(ua["final_sd"])} state_dict tensors BIT-EQUAL; deferred losses {ua["deferred"]} / {ub["deferred"]}')
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)


ALL = [(n, fn) for n, fn in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno if callable(kv[1]) and hasattr(kv[1], '__code__') else 0) if n.startswith('test_') and callable(fn)]


def main():
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
    if sys.argv[1:2] == ['--child']:
        child(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
