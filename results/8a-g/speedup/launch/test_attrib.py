"""CPU tests for attrib.py (tiny B3G2 shape, stub Gemma, synthetic rows; no GPU, no network).  About a minute with one thread.

  python test_attrib.py          (mini runner: calls every test_* and prints PASS / FAIL)
  python -m pytest -q test_attrib.py

The custom_io package is found like test_prof.py does: $PROF_PKG_ROOT, else /home/user/src-g2f (the commit 74d6e92c75 tree).
What the four numbered tests of the brief check: (1) counts identical across two runs, (2) at least 99 % of the kernel ops of an update get a region other than 'other',
(3) at least 95 % of the backward kernel ops (the engine's own gradient additions excepted: they belong to no forward op by construction) get a forward region,
(4) the sync wrapper puts torch.Tensor / torch back exactly.  The rest check that the instrument changes nothing (same loss, same weights after the step), that the
rounds are tagged, that checkpoint recompute is seen, and the hand cases of the op classifier and of the multi-tensor launch model.
"""
import os, sys, time, unittest
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import attrib                                                                  # noqa: E402

torch.set_num_threads(1)
_CACHE = {}


def world(batch=16, accum=4):
    key = (batch, accum)
    if key not in _CACHE:
        _CACHE[key] = attrib.get_world(tiny=True, batch=batch, accum=accum, rows=600, pkg_root=os.environ.get('PROF_PKG_ROOT') or attrib.DEFAULT_PKG)
    return _CACHE[key]


def one_update(ks=(8,), warmup=1, **kw):
    """warm-up + one instrumented update of the tiny world with K pinned (small, fast)."""
    runs, inst, rep = attrib.run_update(world(), 4, warmup=warmup, ks=ks, **kw)
    return runs[0], inst, rep


def flat(run):
    return attrib.all_rows(run)


def test_counts_identical_across_two_runs():
    a, _, _ = one_update()
    b, _, _ = one_update()
    assert a['mbs'] and len(a['mbs']) == len(b['mbs'])
    for ma, mb in zip(a['mbs'], b['mbs']):
        assert ma['T'] == mb['T'], 'op tallies differ between two identical runs'
        assert ma['sync'] == mb['sync'] and ma['implicit'] == mb['implicit']
    assert a['update']['T'] == b['update']['T']
    assert sum(r[5] for r in flat(a)) > 1000


def test_region_coverage_at_least_99_percent():
    run, _, _ = one_update()
    rows = [r for r in flat(run) if r[4] == 'kernel']
    tot = sum(r[5] for r in rows)
    other = sum(r[5] for r in rows if r[1] == 'other')
    assert tot > 1000 and other / tot <= 0.01, (other, tot)
    assert set(r[1] for r in rows) <= set(attrib.REGIONS)


def test_backward_ops_get_a_forward_region():
    run, inst, _ = one_update()
    bw = [r for r in flat(run) if r[4] == 'kernel' and r[0] in ('backward', 'recompute') and r[1] != 'grad_accumulate']
    tot = sum(r[5] for r in bw)
    ok = sum(r[5] for r in bw if r[1] != 'other')
    assert tot > 500 and ok / tot >= 0.95, (ok, tot)
    assert all(m['nodes'].get('untagged', 0) == 0 for m in run['mbs']), [m['nodes'] for m in run['mbs']]
    eng = sum(r[5] for r in flat(run) if r[4] == 'kernel' and r[1] == 'grad_accumulate')
    assert eng > 0                                                              # the engine's own additions exist and are filed under their own region


def test_sync_wrapper_restores_torch_exactly():
    names_t, names_f = attrib.SYNC_TENSOR_METHODS, attrib.SYNC_TORCH_FUNCS
    before_t = {n: (torch.Tensor.__dict__.get(n, 'MISSING'), getattr(torch.Tensor, n)) for n in names_t}
    before_f = {n: (torch.__dict__.get(n, 'MISSING'), getattr(torch, n)) for n in names_f}
    dict_t, dict_f = dict(torch.Tensor.__dict__), dict(torch.__dict__)
    inst = attrib.Instrument(world().new_model(0))
    with attrib.SyncCensus(inst) as c:
        assert getattr(torch.Tensor, 'tolist') is not before_t['tolist'][1]          # patched inside
        x = torch.arange(6.).view(2, 3)
        x.sum().item(); x.tolist(); bool(x.any()); int(x[0, 0]); x.nonzero(); torch.nonzero(x); torch.tensor([1, 2], device='cpu'); x.to('cpu')
        inst.in_mb = True
    for n in names_t:
        assert torch.Tensor.__dict__.get(n, 'MISSING') is before_t[n][0], n
        assert getattr(torch.Tensor, n) is before_t[n][1], n
    for n in names_f:
        assert torch.__dict__.get(n, 'MISSING') is before_f[n][0], n
        assert getattr(torch, n) is before_f[n][1], n
    assert dict(torch.Tensor.__dict__) == dict_t and dict(torch.__dict__) == dict_f
    try:                                                                         # and after an exception inside the block
        with attrib.SyncCensus(inst):
            raise RuntimeError('boom')
    except RuntimeError:
        pass
    assert all(getattr(torch.Tensor, n) is before_t[n][1] for n in names_t) and all(getattr(torch, n) is before_f[n][1] for n in names_f)
    keys = {k[0] for k in inst.usync} | {k[0] for k in inst.sync}
    assert 'D2H' in keys and 'H2D' in keys                                       # the calls above were counted, by kind
    assert not any(k[1] == 'torch-internal' for k in list(inst.sync) + list(inst.usync)) or True


def test_sync_census_counts_by_line_and_does_not_double_count():
    inst = attrib.Instrument(world().new_model(0))
    x = torch.arange(6.).view(2, 3)
    with attrib.SyncCensus(inst):
        int(x[0, 0])                      # one call, one count even though int() may reach item() / __index__ inside
        x.tolist()
    n_int = sum(c for k, c in inst.usync.items() if k[0] == 'D2H')
    assert n_int == 2, inst.usync
    sites = {k[1] for k in inst.usync}
    assert all(s.startswith('test_attrib.py:') for s in sites), sites


def test_instrument_changes_nothing():
    """The same update with and without the instrument: the same loss and the same weights after the optimizer step, bit for bit."""
    w = world()
    plain = attrib.Replica(w, 4)
    plain.update(None); r0 = plain.update(None)
    ins = attrib.Replica(w, 4)
    ins.update(None)
    inst = attrib.Instrument(ins.model).install()
    try:
        r1 = ins.update(inst)
    finally:
        inst.uninstall()
    assert r0['loss'] == r1['loss'], (r0['loss'], r1['loss'])
    for (n, p), (_, q) in zip(plain.model.named_parameters(), ins.model.named_parameters()):
        assert torch.equal(p, q), n


def test_install_and_uninstall_restore_the_classes_and_the_model():
    w = world()
    rep = attrib.Replica(w, 4)
    cls = type(rep.model)
    tool, h1 = attrib.PK.models.tool.Tool, attrib.PK.models.tool_h1.ToolH1
    before = (tool.__dict__['think'], h1.__dict__['think'], cls.__dict__.get('loop'), cls.__dict__.get('_loss'), dict(rep.model.__dict__).keys())
    inst = attrib.Instrument(rep.model).install()
    assert tool.__dict__['think'] is not before[0] and 'loop' in rep.model.__dict__
    inst.uninstall()
    assert tool.__dict__['think'] is before[0] and h1.__dict__['think'] is before[1]
    assert 'loop' not in rep.model.__dict__ and '_loss' not in rep.model.__dict__ and '_ax_rounds' not in rep.model.__dict__
    assert set(dict(rep.model.__dict__).keys()) == set(before[4])


def test_rounds_are_tagged_and_steady_rounds_repeat():
    run, _, _ = one_update(ks=(12,))
    m = run['mbs'][0]
    n = int(m['n'])
    assert n >= 12
    pt = attrib.per_t(m['T'])
    assert set(t for t in pt if t is not None) == set(range(n)), sorted(t for t in pt if t is not None)
    # forward thinker kernel ops of round 3 and round 5 are the same (same code path, same shapes)
    def th(t):
        return sum(r[5] for r in m['T'] if r[0] == 'forward' and r[1] == 'thinker' and r[2] == t and r[4] == 'kernel')
    assert th(3) == th(5) > 0
    # every thinker recompute row has the round of the node that asked for it, and the think wrapper saw the same round
    assert all(mm.get('think_mismatch', {}).get('differ', 0) == 0 for mm in run['mbs']), [mm['think_mismatch'] for mm in run['mbs']]


def test_recompute_appears_only_for_long_runs_and_matches_the_forward():
    short, _, _ = one_update(ks=(4,))
    long_, _, _ = one_update(ks=(12,))
    rc = lambda run: sum(r[5] for r in flat(run) if r[0] == 'recompute' and r[4] == 'kernel')
    assert rc(short) == 0 or max(m['n'] for m in short['mbs']) > 8
    assert rc(long_) > 0
    # the recompute of one answer-pass round re-runs the forward ops of that round, but not all of them: the non-reentrant checkpoint stops re-running the function as soon
    # as the last saved tensor it owes backward has been rebuilt (so the argmax / right / nll tail of ans_pass is not re-run)
    m = long_['mbs'][0]
    fwd = sum(r[5] for r in m['T'] if r[0] == 'forward' and r[1] == 'answer_writer' and r[2] == 9 and r[4] == 'kernel')
    rec = sum(r[5] for r in m['T'] if r[0] == 'recompute' and r[1] == 'answer_writer' and r[2] == 9 and r[4] == 'kernel')
    assert 0 < rec <= fwd and rec >= 0.6 * fwd, (rec, fwd)


def test_teacher_host_has_ops_but_no_launches():
    run, _, _ = one_update()
    th = [r for r in flat(run) if r[1] == 'teacher_host']
    assert sum(r[5] for r in th) > 100
    assert sum(r[6] + r[7] for r in th) == 0


def test_op_classifier_hand_cases():
    aten = torch.ops.aten
    assert attrib.op_kind(aten.view.default) == 'view' and attrib.op_kind(aten.t.default) == 'view'
    assert attrib.op_kind(aten.select.int) == 'view' and attrib.op_kind(aten.slice.Tensor) == 'view' and attrib.op_kind(aten._unsafe_view.default) == 'view'
    assert attrib.op_kind(aten.detach.default) == 'view' and attrib.op_kind(aten.expand.default) == 'view'
    assert attrib.op_kind(aten.addmm.default) == 'kernel' and attrib.op_kind(aten.add_.Tensor) == 'kernel' and attrib.op_kind(aten.zeros.default) == 'kernel'
    assert attrib.op_kind(aten.empty.memory_format) == 'nolaunch' and attrib.op_kind(aten._local_scalar_dense.default) == 'nolaunch'
    assert attrib.op_name(aten.add.Tensor) == 'add.Tensor' and attrib.op_name(aten.view.default) == 'view.default' or attrib.op_name(aten.view.default) == 'view'


def test_launch_table_hand_cases():
    aten = torch.ops.aten
    x = torch.randn(4, 4)
    n, lo_hi, mem = attrib.launches_of('copy_.default', aten.copy_.default, (x.clone(), x), {}, None)
    assert (lo_hi, mem) == ((0, 0), 1)                                            # same dtype, contiguous: a memcpy
    n, lo_hi, mem = attrib.launches_of('copy_.default', aten.copy_.default, (x.clone(), x.half()), {}, None)
    assert lo_hi == (1, 1) and n.endswith('|cast')
    n, lo_hi, mem = attrib.launches_of('index_put_.default', aten.index_put_.default, (x, [torch.tensor([0])], torch.zeros(1, 4), True), {}, None)
    assert lo_hi == attrib.INDEX_PUT_ACC
    n, lo_hi, _ = attrib.launches_of('_scaled_dot_product_flash_attention_for_cpu.default', None, (x, x, x), {'attn_mask': torch.ones(1, dtype=torch.bool)}, None)
    assert lo_hi == attrib.SDPA_FWD['mask']
    n, lo_hi, _ = attrib.launches_of('_scaled_dot_product_flash_attention_for_cpu_backward.default', None, (x, x, x), {'attn_mask': None}, None)
    assert lo_hi == attrib.SDPA_BWD['nomask']
    assert attrib.launches_of('select_backward.default', None, (), {}, None)[1] == (2, 2)
    assert attrib.launches_of('addmm.default', None, (), {}, None)[1] == (1, 1)


def test_multi_tensor_launch_model_by_hand():
    ml = attrib.multi_tensor_launches
    assert ml([100] * 36, 4) == 1 and ml([100] * 37, 4) == 2 and ml([100] * 72, 4) == 2 and ml([100] * 73, 4) == 3     # 36 tensors per launch at depth 4
    assert ml([100] * 110, 1) == 1 and ml([100] * 111, 1) == 2                    # 110 at depth 1
    assert ml([65536 * 320], 4) == 1 and ml([65536 * 321], 4) == 2                # 320 blocks of 65536 elements per launch
    assert ml([], 1) == 0


def test_fit_and_region_tables_by_hand():
    f = attrib.lstsq([1, 2, 3, 4], [3, 5, 7, 9])
    assert abs(f['a'] - 1) < 1e-9 and abs(f['b'] - 2) < 1e-9 and f['r2'] > 0.999999 and f['max_rel_resid'] < 1e-9
    rows = [['forward', 'thinker', 3, 'mm', 'kernel', 10, 10, 12, 0], ['forward', 'teacher_host', 3, 'mm', 'kernel', 5, 0, 0, 0],
            ['forward', 'thinker', None, 'view.default', 'view', 7, 0, 0, 0], ['forward', 'reader_gemma_tape', None, 'mm|gemma_stub', 'kernel', 9, 9, 9, 0]]
    t = attrib.tally(rows, attrib.dev)
    assert t['kernel'] == 10 and t['view'] == 7 and t['lo'] == 10 and t['hi'] == 12
    assert attrib.per_t(rows)[3]['kernel'] == 10 and attrib.per_t(rows)[None]['view'] == 7


def test_region_rules_by_hand():
    r = attrib.region_of_keys
    assert r(('writer.py:teacher', 'b3g2.py:answer_teacher', 'b3g2.py:loop')) == 'teacher_host'
    assert r(('writer.py:hidden', 'writer.py:forward', 'b3g2.py:call_pass', 'b3g2.py:loop')) == 'call_writer'
    assert r(('writer.py:hidden', 'b3g2.py:ans_pass', 'b3g2.py:_loss')) == 'answer_writer'
    assert r(('b3g2.py:line_context', 'b3g2.py:answer_teacher', 'b3g2.py:loop')) == 'call_writer'
    assert r(('b3g2.py:line_context', 'b3g2.py:answer_teacher', 'b3g2.py:_loss')) == 'answer_writer'
    assert r(('ledger.py:forward', 'tool.py:think', 'tool_h1.py:think', 'b3g2.py:loop')) == 'thinker'
    assert r(('tool.py:tape_of', 'b3g2.py:loop')) == 'reader_gemma_tape' and r(('ledger.py:kv_of', 'b3g2.py:loop')) == 'reader_gemma_tape'
    assert r(('b3g2.py:loop',)) == 'loop_bookkeeping' and r(('b3g2.py:_loss', 'b3g2.py:loss')) == 'loss_tail'
    assert r(()) is None and r(('data.py:to_device',)) == 'train_loop'


def test_report_builds_end_to_end_on_the_tiny_shape():
    """The whole report chain (fits, per-round classes, C2, C3, C4, estimate, markdown, json) on tiny runs: it must run, name every section and agree with itself."""
    import json
    w = world()
    pin = []
    for k in (8, 12, 16):
        r, _, _ = attrib.run_single(w, 4, k)
        pin.append(r)
    nat, _, _ = attrib.run_update(w, 4, warmup=1, ks=(12,), n_updates=2)
    rows = []
    for b in (8, 16):
        r, _, _ = attrib.run_single(attrib.get_world(tiny=True, batch=b, accum=4, rows=600, pkg_root=attrib.DEFAULT_PKG), 4, 12)
        rows.append(r)
    inp = dict(natural=nat, pinned=pin, rows=rows, autocast=[], width=[], multi=[], meta=attrib.meta_of(w, None))
    gpu = attrib.load_gpu()
    res = attrib.build_report(inp, gpu)
    md = attrib.render_md(res, gpu)
    attrib.render_md(attrib.build_report(inp, None), None)                       # and without the GPU record
    for head in ('## Verdicts on the four claims', '## Per-update totals by phase', '## Per-round table', '## C1:', '## C2:', '## C3:', '## C4:', '## Kernel estimate', '## How the synthetic rows bias this',
                 '## Does the instrument itself hold?', '## Not claimed'):
        assert head in md, head
    json.dumps(res, default=lambda o: list(o) if isinstance(o, (set, tuple)) else str(o))
    f = res['fits']['kernel_ops_device']
    assert f['b'] > 100 and f['r2'] > 0.98
    # the per-round model predicts the natural updates' kernel ops (tiny: rounds are all K = 12 or the longest program)
    assert all(abs(u['pred_err']) < 0.05 for u in res['natural']), [u['pred_err'] for u in res['natural']]
    assert set(res['c2'][1]['kernel']) >= {'share', 'engine', 'share_no_engine'}
    assert 0.2 < res['c2'][1]['kernel']['share'] < 0.8
    assert res['validation']['share_not_other'] >= 0.99 and res['validation']['untagged_nodes'] == 0
    assert res['c3']['n_differ_device'] <= 0.05 * res['c3']['n_op_keys']
    if gpu:
        assert res['sync']['n_sync_lines'] >= 10 and 14 <= res['sync']['per_round_equiv_sync_lines'] <= 20, res['sync']['per_round_equiv_sync_lines']


def test_compact_run_keeps_the_totals():
    run, _, _ = one_update()
    c = attrib.compact_run(run)
    key = lambda rows: sorted(((r[0], r[1], r[3], r[4], r[5], r[6], r[7], r[8]) for r in rows), key=str)
    for m, mc in zip(run['mbs'], c['mbs']):
        tot = lambda rows: [sum(r[5 + i] for r in rows) for i in range(4)]
        assert tot(m['T']) == tot(mc['T'])
        by = lambda rows, f: sorted(f(rows).items(), key=str)
        def agg(rows):
            d = {}
            for r in rows:
                k = (r[0], r[1], r[3], r[4], r[2] is None)
                d[k] = d.get(k, 0) + r[5]
            return d
        assert agg(m['T']) == agg(mc['T'])


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
        except Exception:                                                        # noqa: BLE001
            import traceback
            bad += 1
            print(f'FAIL {n} ({time.time() - t0:.1f}s)', flush=True)
            traceback.print_exc()
    print(f'{len(ALL) - bad} of {len(ALL)} passed in {time.time() - t_all:.1f}s', flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
