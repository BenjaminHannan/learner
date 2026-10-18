"""Tests for the R1 renormalisation fix in learn_probe.install_first_call_weight (pairing-map decision U3). Random-init span
Tool, CPU, no training, no data files (rows come from the trainer's own make_rows over the sheet-probe generator).

  python3 -m domain.far.test_learn_probe_r1_renorm        (or: python -m pytest -q domain/far/test_learn_probe_r1_renorm.py)

Method: for each trace (a B=1 batch) run the model once with gold, then for every round s take the round's contribution to a
term as f(steps[:s+1]) - f(steps[:s]) (op CE, operand NLL and span_call are sums over rounds), once with the unmodified
Tool.call_loss / Tool.span_terms and once with the installed weighted copy. weighted / unweighted is that round's factor,
measured and not read off the code.

Fixed behaviour asserted: call rounds carry renorm = n / (W + n - 1), round 0 carries renorm x W, NOOP rounds (gold op == 0)
carry exactly 1.0, on op CE, operand NLL and span_call alike; so each call-round total is the uniform-weight total (n), the
NOOP total is untouched (N_RES - n), and first-call / later-call is W. W = 1.0 stays bit-identical to the unmodified trainer.

Also (U3, 'weight w scales the first call only; no other term changes'): the K-FAC guard measures F on the SHIPPED loss at setup
and on every refresh, and the frozen KL parent is the shipped model - section 9, with stub kf / gp / klreplay modules (the real
guard source is not needed): the stub kfac_stats calls m.loss exactly as mainbrain kf.kfac_stats does and records the value.
"""
import contextlib
import copy
import sys
import types

import pytest
import torch

from domain.far import learn_probe as LP

from custom_io.models.tool import N_RES, Tool
from domain.far import test_learn_probe_r1 as T

SMALL = T.SMALL
THREADS0 = 3   # the thread count this module runs under (see the fixtures)


@pytest.fixture(scope='module', autouse=True)
def _baseline_threads():
    """Run the module under a known torch thread count and put the process's own back afterwards."""
    n = torch.get_num_threads()
    torch.set_num_threads(THREADS0)
    yield
    torch.set_num_threads(n)


@pytest.fixture(autouse=True)
def _restore_threads():
    """Every test that calls the real LP.train (threads=1) leaves torch's global thread count as it found it (train() calls torch.set_num_threads)."""
    n = torch.get_num_threads()
    yield
    torch.set_num_threads(n)
_cache = {}


make_batch = T.batch_of
span_model = T.build_span_model   # a T1S model (span_copy + span_idx + span_end); ans_drill=0 so the golds are fixed across repeated loss() calls
CALL_CELLS = ('F0-near', 'F2-long', 'F4-two', 'F5-far')   # 1-3, 4-5, 3-7, 4-7 calls


def rows_by_calls():
    """{n_calls: [row]} for n = 1..7, real rows (T.probe_rows over CALL_CELLS: the trainer's make_rows from the probe generator)."""
    if 'by' not in _cache:
        probe_m, rows, _ = T.probe_rows(CALL_CELLS)
        by = {}
        for r in rows:
            by.setdefault(len(probe_m.row_gold(r)[0]), []).append(r)
        _cache['by'] = by
    return _cache['by']


def rows_for(ns, k=2):
    by = rows_by_calls()
    for n in ns:
        assert len(by.get(n, [])) >= k, f'only {len(by.get(n, []))} usable {n}-call rows'
    return {n: by[n][:k] for n in ns}


def mixed_rows():
    by = rows_for((1, 2, 3, 4, 5, 7))
    return [by[n][0] for n in (1, 2, 3, 4, 5, 7)] + [by[3][1]]


def weighted_fns(m, w):
    """The installed (call_loss, span_terms) closures for weight w, taken off the instance and the instance restored."""
    LP.install_first_call_weight(m, float(w))
    cl, st = m.call_loss, m.span_terms
    del m.call_loss, m.span_terms
    return cl, st


def round_contribs(cl, st, o, g, batch, B=1):
    """ONE pass over the rounds -> {term: [contribution of round s]} for the call_loss `cl` and span_terms `st` given: each
    term is a sum over rounds, so a round's contribution is the difference of consecutive prefix totals, and each prefix
    total is computed once and carried (prefix totals cached, not recomputed per round). Terms: opce (op CE, all rounds), nll
    (operand-string NLL) and span (span_call); the last two are nonzero on call rounds only."""
    steps = o['steps']
    f = lambda x: float(torch.as_tensor(x).detach())
    prev, out = (0.0, 0.0, 0.0), {'opce': [], 'nll': [], 'span': []}
    for s in range(len(steps)):
        c = cl(steps[:s + 1], g, B)
        cur = (f(c[0]), f(c[1]), f(st(dict(o, steps=steps[:s + 1]), g, batch, B)[0]['span_call']))
        for k, a, b in zip(out, cur, prev):
            out[k].append(a - b)
        prev = cur
    return out


def per_round_factors(m, w, batch):
    """ONE trace (a B=1 batch) -> ({term: [measured factor per round]}, n gold calls, gold ops): the weighted contribution over
    the shipped one, round by round. nll and span are None off call rounds (no contribution to divide)."""
    from custom_io.models.tool import Tool
    g = m.gold(batch['rows'], 'cpu', None)
    o = m.run(batch, gold=g)
    n = int((g['op'] > 0).sum())
    base = round_contribs(lambda *a: Tool.call_loss(m, *a), lambda *a: Tool.span_terms(m, *a), o, g, batch)
    cl_w, st_w = weighted_fns(m, w)
    wt = round_contribs(cl_w, st_w, o, g, batch)
    out = {k: [(wt[k][s] / base[k][s]) if (k == 'opce' or int(g['op'][0, s]) > 0) and abs(base[k][s]) > 1e-9 else None
               for s in range(N_RES)] for k in base}
    return out, n, [int(x) for x in g['op'][0]]


def need(fac, k, i):
    """fac[k][i], which must have been measurable: a None means the shipped contribution of that round was ~0 (nothing to divide)."""
    v = fac[k][i]
    assert v is not None, f'term {k}: no measurable shipped contribution on round {i} (factor is None), measured {fac[k]}'
    return v


def trace_totals(fac, ops):
    """Per-trace totals of the measured round factors: op CE over call rounds, op CE over NOOP rounds, operand NLL, span_call,
    and the first-call / later-call factor ratio on each call term (None for a one-call trace)."""
    call = [i for i, o in enumerate(ops) if o > 0]
    noop = [i for i, o in enumerate(ops) if o == 0]
    return dict(opce_call=sum(need(fac, 'opce', i) for i in call), opce_noop=sum(need(fac, 'opce', i) for i in noop),
                nll=sum(need(fac, 'nll', i) for i in call), span=sum(need(fac, 'span', i) for i in call),
                ratio={k: need(fac, k, call[0]) / need(fac, k, call[1]) for k in ('opce', 'nll', 'span')} if len(call) > 1 else None)


# ---- 1. weight 1.0 is bit-identical to the shipped trainer ----
@pytest.mark.parametrize('which', ['uniform', 'mixed'])
def test_w1_bit_identical(which):
    rows = T.build_batch(n_rows=3, n_calls=3)[1] if which == 'uniform' else mixed_rows()
    vocab, batch = make_batch(rows)
    m = span_model(vocab)
    plain, aux = m.loss(batch)
    LP.install_first_call_weight(m, 1.0)
    try:
        w1, aux1 = m.loss(batch)
    finally:
        del m.call_loss, m.span_terms
    assert torch.equal(plain, w1), (float(plain), float(w1))
    assert set(aux) == set(aux1)
    for k in aux:
        a, b = aux[k], aux1[k]
        assert (torch.equal(a, b) if torch.is_tensor(a) else a == b), (k, a, b)
    # gradients identical too (the backward graph is the shipped one up to multiplication by an exact 1.0)
    m.zero_grad()
    plain.backward()
    g0 = [p.grad.clone() for p in m.parameters() if p.grad is not None]
    m.zero_grad()
    LP.install_first_call_weight(m, 1.0)
    try:
        m.loss(batch)[0].backward()
    finally:
        del m.call_loss, m.span_terms
    g1 = [p.grad for p in m.parameters() if p.grad is not None]
    assert all(torch.equal(a, b) for a, b in zip(g0, g1))


# ---- 2. decision U3 on measured round factors: per-trace totals, NOOP untouched, first-call ratio ----
def check_trace(row, w):
    """U3, stated on one trace's measured round factors (weighted contribution / shipped contribution, round by round): call rounds
    carry renorm = n / (W + n - 1), round 0 renorm x W, NOOP rounds exactly 1.0; and so, against the W = 1 run of the same trace,
    the per-trace total over call rounds (op CE, operand NLL, span_call) and over NOOP rounds (op CE) is unchanged, the W = 1
    totals are the uniform ones (n and N_RES - n), and the first-call / later-call factor ratio is W on every call term."""
    vocab, batch = make_batch([row])
    m = span_model(vocab)
    fac, n, ops = per_round_factors(m, w, batch)
    f1, n1, ops1 = per_round_factors(m, 1.0, batch)
    assert n1 == n and ops1 == ops
    call = [i for i, o in enumerate(ops) if o > 0]
    noop = [i for i, o in enumerate(ops) if o == 0]
    assert call == list(range(n)), ops   # calls are rounds 0..n-1, NOOP after
    renorm = n / (w + n - 1)
    for k in ('opce', 'nll', 'span'):
        # per-trace total over call rounds is preserved (= n, the uniform-weight total)
        assert sum(need(fac, k, i) for i in call) == pytest.approx(n, rel=1e-5), (k, n, w, fac[k])
        # round 0 = renorm x W, every later call round = renorm (mean-preserving, ratio W)
        assert abs(need(fac, k, 0) - renorm * w) < 1e-4, (k, n, w, fac[k][0])
        for i in call[1:]:
            assert abs(need(fac, k, i) - renorm) < 1e-4, (k, n, w, i, fac[k][i])
        if n > 1:
            assert need(fac, k, 0) / need(fac, k, 1) == pytest.approx(w, rel=1e-5)
    for i in noop:   # stop / NOOP supervision: factor exactly 1
        assert need(fac, 'opce', i) == pytest.approx(1.0, rel=1e-5), (n, w, i, fac['opce'][i])
    assert sum(need(fac, 'opce', i) for i in noop) == pytest.approx(N_RES - n, rel=1e-5)
    # against W = 1: the totals do not move
    t1, tw = trace_totals(f1, ops1), trace_totals(fac, ops)
    assert (t1['opce_call'], t1['opce_noop']) == pytest.approx((n, N_RES - n), rel=1e-5)   # the W = 1 totals are the uniform ones
    for k in ('opce_call', 'opce_noop', 'nll', 'span'):
        assert tw[k] == pytest.approx(t1[k], rel=1e-5), (n, w, k, tw[k], t1[k])
    if n > 1:
        for k in ('opce', 'nll', 'span'):
            assert tw['ratio'][k] == pytest.approx(w, rel=1e-5), (n, w, k, tw['ratio'][k])
    else:
        assert tw['opce_call'] == pytest.approx(1.0, rel=1e-5)   # a one-call trace: the single call is the first call, renorm x W = 1
    return n


@pytest.mark.parametrize('w', [2.0, 3.0])
@pytest.mark.parametrize('n', [1, 2, 3, 4, 5, 6, 7])
def test_u3_per_trace_totals_noop_and_first_call_ratio(n, w):
    """U3 ('weight w scales the first call only; no other term changes'): per trace, call-round and NOOP-round totals equal the
    W = 1 totals, NOOP rounds are exactly 1.0, call rounds carry renorm and the first call renorm x W (ratio W)."""
    for row in rows_for([n])[n]:
        assert check_trace(row, w) == n


# ---- 3. a row with no call at all: every round is NOOP, so the weighted call_loss is the shipped one, bit for bit ----
def test_no_call_row_untouched():
    from custom_io.models.tool import Tool
    vocab, batch = make_batch(rows_for([3])[3])
    m = span_model(vocab)
    g = m.gold(batch['rows'], 'cpu', None)
    o = m.run(batch, gold=g)
    g0 = dict(g, op=torch.zeros_like(g['op']), has=torch.zeros_like(g['has']))   # synthetic: no call anywhere
    ref = Tool.call_loss(m, o['steps'], g0, 2)
    cl, _ = weighted_fns(m, 3.0)
    got = cl(o['steps'], g0, 2)
    assert torch.equal(torch.as_tensor(ref[0]), torch.as_tensor(got[0])) and float(ref[1]) == float(got[1]) == 0.0


# ---- 4. batch aggregate == mean of per-trace values (mixed call counts) ----
def test_batch_aggregate_is_mean_of_traces():
    from custom_io.data import Dataset, collate, to_device
    rows = mixed_rows()
    vocab, batch = make_batch(rows)
    m = span_model(vocab)
    B = len(rows)
    LP.install_first_call_weight(m, 2.0)
    try:
        _, aggx = m.loss(batch)
        per = {'prog': 0.0, 'call': 0.0, 'span_call': 0.0}
        for r in rows:
            b1 = to_device(collate([Dataset([r], vocab)[0]]), 'cpu')   # the same vocab: the same model
            _, a1 = m.loss(b1)
            for k in per:
                per[k] += float(a1[k]) / B
    finally:
        del m.call_loss, m.span_terms
    for k in per:
        assert abs(per[k] - float(aggx[k])) < 1e-4, (k, per[k], float(aggx[k]))


# ---- 5. the defects of the earlier trainer are gone (n = 3, W = 2, the numbers the unfixed code gave are asserted away) ----
def test_defects_are_gone():
    row = rows_for([3])[3][0]
    vocab, batch = make_batch([row])
    m = span_model(vocab)
    fac, n, ops = per_round_factors(m, 2.0, batch)
    assert n == 3
    assert abs(sum(need(fac, 'opce', i) for i in range(N_RES)) - N_RES) < 1e-4, fac['opce']   # unfixed: 6.0 (1.5 + 0.75 x 6), NOOP rounds cut to 0.75
    assert abs(sum(need(fac, 'opce', i) for i in range(3, N_RES)) - (N_RES - 3)) < 1e-4       # unfixed: 3.0; the N_RES - 3 NOOP rounds at exactly 1
    assert abs(sum(need(fac, 'span', i) for i in range(3)) - 3.0) < 1e-4                      # unfixed: 3.5 (renorm x W + (n - 1))
    assert abs(need(fac, 'span', 0) / need(fac, 'span', 1) - 2.0) < 1e-4                      # unfixed: 1.5 = W n / (W + n - 1)


# ---- 6. a real mixed batch: call rows of several lengths + no-call rows (has=False, w_row = w_noop), W = 2 ----
def test_mixed_batch_with_no_call_rows():
    """Rows 1 and 5 of the mixed batch are made genuine no-call rows (empty gold program, so op all 0, ca / cb unset, has False
    and span gold empty - not just zeroed op), the rest keep their calls. Per row (B=1 slices, w_noop still applies to the
    no-call rows): a no-call row's op CE, operand NLL, span_call, stop, span_share and Mn are bit-identical to the shipped
    methods; a call row's op CE / operand NLL / span_call equal the shipped per-round contributions times the documented factors
    (call rounds renorm, round 0 renorm x W, NOOP rounds 1.0); the batch aggregate is the mean of the per-row values."""
    from custom_io.models.tool import Tool
    w, nocall = 2.0, {1, 5}
    rows = mixed_rows()
    vocab, batch = make_batch(rows)
    m = span_model(vocab)
    B = len(rows)
    golds = [m.row_gold(r) + (r['answer'], False) for r in rows]
    golds = [(([], []) + g[2:]) if i in nocall else g for i, g in enumerate(golds)]
    golds = [(g[0], g[1], [''] * N_RES) + g[3:] if i in nocall else g for i, g in enumerate(golds)]   # an empty program has an empty tape
    g = m.gold(batch['rows'], 'cpu', golds)
    o = m.run(batch, gold=g)
    ncalls = [int(x) for x in (g['op'] > 0).sum(1)]
    assert [bool(h) for h in g['has']] == [i not in nocall for i in range(B)] and all(ncalls[i] == 0 for i in nocall), ncalls
    assert len({n for i, n in enumerate(ncalls) if i not in nocall}) >= 4   # several call-row lengths in the one batch
    cl_w, st_w = weighted_fns(m, w)
    eq = lambda a, b: torch.equal(torch.as_tensor(a), torch.as_tensor(b))
    base_agg, wt_agg = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for i in range(B):
        bi, gi, oi = T._slice_batch(batch, i), T._slice_g(g, i), T._slice_o(o, i)
        assert bool(gi['has'][0]) == (i not in nocall)
        steps = oi['steps']
        shipped_cl, shipped_st = Tool.call_loss(m, steps, gi, 1), Tool.span_terms(m, oi, gi, bi, 1)
        got_cl, got_st = cl_w(steps, gi, 1), st_w(oi, gi, bi, 1)
        for k in (0, 1):
            wt_agg[k] += float(got_cl[k]) / B
        wt_agg[2] += float(got_st[0]['span_call']) / B
        if i in nocall:
            assert eq(shipped_cl[0], got_cl[0]) and eq(shipped_cl[1], got_cl[1]), (i, shipped_cl[:2], got_cl[:2])   # op CE (x w_noop), NLL
            assert eq(shipped_cl[2], got_cl[2]) and eq(shipped_cl[3], got_cl[3])                                    # hits / tot
            assert float(got_cl[0]) > 0 and float(got_cl[1]) == 0.0   # the op CE is live (w_noop x NOOP CE), there is no operand NLL
            for k in ('span_call', 'stop', 'span_share'):
                assert eq(shipped_st[0][k], got_st[0][k]), (i, k, shipped_st[0][k], got_st[0][k])
            assert eq(shipped_st[1], got_st[1]), (i, 'Mn')
        else:
            n = ncalls[i]
            renorm = n / (w + n - 1)
            fac = lambda s: (renorm * w if s == 0 else renorm) if s < n else 1.0
            c = round_contribs(lambda *a: Tool.call_loss(m, *a), lambda *a: Tool.span_terms(m, *a), oi, gi, bi)
            for k, got in (('opce', float(got_cl[0])), ('nll', float(got_cl[1])), ('span', float(got_st[0]['span_call']))):
                expect = sum(fac(s) * c[k][s] for s in range(N_RES))
                assert abs(got - expect) < 1e-4, (i, n, k, got, expect)
            for k in ('stop', 'span_share'):
                assert eq(shipped_st[0][k], got_st[0][k]), (i, k)   # unweighted terms are the shipped ones
            assert eq(shipped_st[1], got_st[1]), (i, 'Mn')
    full_cl, full_st = cl_w(o['steps'], g, B), st_w(o, g, batch, B)
    for k, got in ((0, float(full_cl[0])), (1, float(full_cl[1])), (2, float(full_st[0]['span_call']))):
        assert abs(got - wt_agg[k]) < 1e-4, (k, got, wt_agg[k])


# ---- 7. the run record states the trainer semantics ----
@pytest.mark.parametrize('w', [1.0, 2.0])
def test_run_record_states_renorm_version(w):
    ex = LP.run_record_extras(31003, w)
    assert ex == dict(seed=31003, first_call_weight=w, first_call_renorm='call-rounds-v3')   # also at W = 1.0
    assert LP.FIRST_CALL_RENORM == 'call-rounds-v3'


@pytest.mark.parametrize('w', [1.0, 2.0])
def test_train_records_renorm_version(w, monkeypatch, tmp_path):
    """train() merges run_record_extras into the extras every score record carries. train() cannot run here (parent checkpoint, rows),
    so, as test_l13_invocation_parses stubs train, stub what it reaches first: the rows loader, and eval_sets (the first call after
    the extras are built) to stop the run there; capture what run_record_extras handed back."""
    seen = {}

    class Stop(Exception):
        pass

    def stop(*a, **k):
        raise Stop

    real = LP.run_record_extras
    monkeypatch.setattr(LP, 'load_jsonl', lambda path: [])
    monkeypatch.setattr(LP, 'eval_sets', stop)
    monkeypatch.setattr(LP, 'run_record_extras', lambda *a: seen.setdefault('ex', real(*a)))
    monkeypatch.setattr(LP, 'SEED', LP.SEED)   # train() re-points the module seed when seed is given: restored by monkeypatch
    monkeypatch.setattr(LP, 'KL_REPLAY_SEED', LP.KL_REPLAY_SEED)
    with pytest.raises(Stop):
        LP.train('LB', 10, 1, str(tmp_path / 'run'), [0, 10], first_call_weight=w, seed=31003)
    assert seen['ex'] == dict(seed=31003, first_call_weight=w, first_call_renorm='call-rounds-v3'), seen   # also at W = 1.0


def test_seed_none_after_seeded_call_is_the_shipped_seed(monkeypatch, tmp_path):
    """train(seed=None) always applies the shipped seed: after a seeded call in the same process, the next seed=None call records
    SHIPPED_SEED (93301) and leaves LP.SEED / KL_REPLAY_SEED at the shipped streams (before: the previous run's seed stayed in force)."""
    assert LP.SHIPPED_SEED == 93301
    seen = []

    class Stop(Exception):
        pass

    def stop(*a, **k):
        raise Stop

    real = LP.run_record_extras

    def spy(seed, w):
        seen.append((real(seed, w), LP.SEED, LP.KL_REPLAY_SEED))
        return seen[-1][0]

    monkeypatch.setattr(LP, 'load_jsonl', lambda path: [])
    monkeypatch.setattr(LP, 'eval_sets', stop)
    monkeypatch.setattr(LP, 'run_record_extras', spy)
    monkeypatch.setattr(LP, 'SEED', LP.SEED)   # restored by monkeypatch
    monkeypatch.setattr(LP, 'KL_REPLAY_SEED', LP.KL_REPLAY_SEED)
    for i, seed in enumerate((31003, None)):
        with pytest.raises(Stop):
            LP.train('LB', 10, 1, str(tmp_path / f'run{i}'), [0, 10], seed=seed)
    assert seen[0][0]['seed'] == 31003 and seen[0][1:] == (31003, 31014), seen
    assert seen[1][0]['seed'] == 93301 and seen[1][1:] == (93301, 93312), seen
    assert LP.SEED == 93301 and LP.KL_REPLAY_SEED == 93312


def test_train_validates_before_set_num_threads(monkeypatch, tmp_path):
    """All argument validation (first_call_weight, seed type) runs before torch.set_num_threads: a refused call leaves the process alone."""
    calls = []
    monkeypatch.setattr(torch, 'set_num_threads', lambda n: calls.append(n))
    with pytest.raises(ValueError, match='finite number > 0'):
        LP.train('LB', 10, 7, str(tmp_path / 'a'), [0, 10], first_call_weight=float('nan'))
    for bad in ('31003', 1.5, True):
        with pytest.raises(TypeError, match='seed'):
            LP.train('LB', 10, 7, str(tmp_path / 'b'), [0, 10], seed=bad)
    assert calls == [], calls


def test_one_weight_rule_for_main_train_install(tmp_path):
    """One helper holds the finite > 0 rule: SystemExit from main, ValueError from the others, same wording."""
    for ok in (1, 2.5, 1e-9):
        assert LP.check_first_call_weight(ok) == ok
    for bad in (float('inf'), float('nan'), 0, -1.0, True, '2', None):
        with pytest.raises(ValueError, match='finite number > 0'):
            LP.check_first_call_weight(bad)
        with pytest.raises(SystemExit, match='finite number > 0'):
            LP.check_first_call_weight(bad, SystemExit, '--first-call-weight')
    assert not hasattr(LP, 'file_sha256') or LP.file_sha256 is LP.sha256_file   # one hashing implementation


# ---- 8. the weight must be finite and > 0, in main() and in train() ----
@pytest.mark.parametrize('bad', ['inf', '-inf', 'nan', '0', '-1'])
def test_main_rejects_bad_weight(bad, tmp_path):
    with pytest.raises(SystemExit, match='finite number > 0'):
        LP.main(['train', '--arm', 'LB', '--out', str(tmp_path / 'run'), f'--first-call-weight={bad}'])


@pytest.mark.parametrize('bad', [float('inf'), float('nan'), 0.0, -1.0])
def test_train_and_install_reject_bad_weight(bad, tmp_path):
    with pytest.raises(ValueError, match='finite number > 0'):
        LP.train('LB', 10, 1, str(tmp_path / 'run'), [0, 10], first_call_weight=bad)
    vocab, _ = make_batch(rows_for([3])[3])
    with pytest.raises(ValueError, match='finite number > 0'):
        LP.install_first_call_weight(span_model(vocab), bad)
    assert not (tmp_path / 'run').exists()   # refused before any work


def test_bad_weight_is_refused_under_python_O(tmp_path):
    """The guards are explicit raises, not asserts: with `python -O` (asserts stripped) a bad weight is still refused, in train() and in
    install_first_call_weight, before any work (no output folder)."""
    import os
    import subprocess
    code = '''
import sys
from domain.far import learn_probe as LP
for bad in (float("nan"), float("inf"), 0.0, -1.0):
    try:
        LP.train("LB", 10, 1, sys.argv[1], [0, 10], first_call_weight=bad)
    except ValueError as e:
        print("train", bad, "ValueError")
    try:
        LP.install_first_call_weight(object(), bad)
    except ValueError as e:
        print("install", bad, "ValueError")
'''
    out = str(tmp_path / 'run')
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    r = subprocess.run([sys.executable, '-O', '-c', code, out], capture_output=True, text=True, cwd=repo, env=dict(os.environ, PYTHONPATH=repo))
    lines = r.stdout.split('\n')
    assert sum(l.endswith('ValueError') for l in lines) == 8 and not os.path.exists(out), (r.stdout, r.stderr[-800:])


# ---- 9. U3 for the guard: F is measured on the SHIPPED loss, and the KL parent is the shipped model ----
# Stubs for the guard source (mainbrain kf / gp / klreplay), which is not needed here. StubKf.kfac_stats does what the real
# kf.kfac_stats does with the loss (git show f59a7caa3:mainbrain/kf.py): eval mode, m.loss(collated batch), backward, clear grads;
# it records the loss value and whether the weighted closures were on the instance, and logs begin / end into `events`.
class StubKf:
    def __init__(self, events=None, fail=False):
        self.losses, self.on_instance, self.events, self.fail = [], [], events if events is not None else [], fail

    def kfac_stats(self, m, rows, bs=64, norm=None, pad_mask=False, report=None):
        from custom_io.data import Dataset, collate, to_device
        self.events.append('kfac_begin')
        self.on_instance.append(tuple(k in m.__dict__ for k in LP.FirstCallWeight.NAMES))
        m.eval()
        ds = Dataset(rows, m.vocab)
        out = m.loss(to_device(collate([ds[i] for i in range(len(rows))]), 'cpu'))
        if self.fail:
            raise RuntimeError('measure failed')
        self.losses.append(torch.as_tensor(out[0] if isinstance(out, tuple) else out).detach().clone())
        (out[0] if isinstance(out, tuple) else out).backward()
        m.zero_grad(set_to_none=True)
        self.events.append('kfac_end')
        return {'lin': (0, 0)}

    def factors(self, stats, energy, soft=None):
        return {'lin': (0, 0)}, {'lin': {'free_share': 0.5}}

    class KFOptimizer:
        def __init__(self, m, base, F):
            self.base = base

        def step(self):
            self.base.step()

        def zero_grad(self, set_to_none=True):
            self.base.zero_grad(set_to_none=set_to_none)


class StubGp:
    @staticmethod
    def freeze_unprojected(m):
        return []


class StubKlreplay:
    """frozen_copy as mainbrain/klreplay.py (git show f59a7caa3:mainbrain/klreplay.py lines 33-42): deep copy, pops only these three
    instance attributes. replay_kl records what the parent carries and returns a differentiable zero."""
    parents = []

    @staticmethod
    def frozen_copy(m):
        p = copy.deepcopy(m)
        for k in ('loss', 'load_state_dict', '_guess_lsd'):
            p.__dict__.pop(k, None)
        p.eval()
        for q in p.parameters():
            q.requires_grad_(False)
        return p

    @staticmethod
    def replay_kl(m, parent, b):
        StubKlreplay.parents.append(tuple(k in parent.__dict__ for k in LP.FirstCallWeight.NAMES))
        return sum(p.sum() for p in m.parameters()) * 0.0, {}


def guard_fixture(w=2.0):
    """(model with weight w installed, handle, rows, batch, the shipped eval-mode loss of an uninstalled model on that batch)."""
    vocab, rows, batch, _ = T.build_batch(n_rows=3, n_calls=3)
    m = span_model(vocab)
    m.eval()
    ref = m.loss(batch)[0].detach().clone()
    fcw = LP.install_first_call_weight(m, w)
    return m, fcw, rows, batch, ref


def test_shipped_context_removes_and_restores_even_on_error():
    m, fcw, _, batch, ref = guard_fixture()
    weighted = m.loss(batch)[0].detach().clone()
    assert not torch.equal(weighted, ref)   # W = 2 really changes the loss, or the tests below prove nothing
    with fcw.shipped():
        assert not any(k in m.__dict__ for k in LP.FirstCallWeight.NAMES)
        assert torch.equal(m.loss(batch)[0], ref)   # bit-identical to the uninstalled model
    assert m.call_loss is fcw.call_loss and m.span_terms is fcw.span_terms
    assert torch.equal(m.loss(batch)[0], weighted)
    with pytest.raises(RuntimeError):
        with fcw.shipped():
            raise RuntimeError('boom')
    assert m.call_loss is fcw.call_loss and m.span_terms is fcw.span_terms   # restored although the block raised
    assert torch.equal(m.loss(batch)[0], weighted)


def test_guard_measure_raising_restores_the_weighted_methods():
    m, fcw, rows, batch, _ = guard_fixture()
    kf = StubKf(fail=True)
    with pytest.raises(RuntimeError, match='measure failed'):
        LP.Guarded(kf, StubGp, m, rows, 0.99, lambda: None, shipped=fcw.shipped)
    assert m.call_loss is fcw.call_loss and m.span_terms is fcw.span_terms
    assert kf.on_instance == [(False, False)]   # the measure ran on the shipped methods


def test_guard_measures_the_shipped_loss_on_setup_and_refresh_at_w2():
    m, fcw, rows, batch, ref = guard_fixture(2.0)
    weighted = m.loss(batch)[0].detach().clone()
    kf = StubKf()
    g = LP.Guarded(kf, StubGp, m, rows, 0.99, lambda: torch.optim.SGD(m.parameters(), lr=0.0), shipped=fcw.shipped)
    g.refresh()
    g.refresh()
    assert len(kf.losses) == 3 and g.measures == 3                       # setup + two refreshes
    assert kf.on_instance == [(False, False)] * 3
    for got in kf.losses:
        assert torch.equal(got, ref), (float(got), float(ref))           # exactly the uninstalled model's loss, setup and every refresh
        assert not torch.equal(got, weighted)
    # the training loss keeps the weighting, after the measures
    assert m.call_loss is fcw.call_loss and m.span_terms is fcw.span_terms
    m.train()
    assert torch.equal(m.loss(batch)[0], weighted)


def test_guard_without_shipped_context_would_measure_the_weighted_loss():
    """The defect, kept as a control: with no shipped context (an unfixed caller) the measure sees the W-weighted loss."""
    m, fcw, rows, batch, ref = guard_fixture(2.0)
    kf = StubKf()
    LP.Guarded(kf, StubGp, m, rows, 0.99, lambda: None)
    assert kf.on_instance == [(True, True)] and not torch.equal(kf.losses[0], ref)


def test_kl_parent_is_the_shipped_model():
    m, fcw, rows, batch, ref = guard_fixture(2.0)
    raw = StubKlreplay.frozen_copy(m)   # frozen_copy alone leaves the trainee-bound closures on the parent: the latent hazard
    assert all(k in raw.__dict__ for k in LP.FirstCallWeight.NAMES)
    parent = LP.make_kl_parent(StubKlreplay, m)
    assert not any(k in parent.__dict__ for k in LP.FirstCallWeight.NAMES)
    assert parent.call_loss.__func__ is Tool.call_loss and parent.span_terms.__func__ is Tool.span_terms
    assert torch.equal(parent.loss(batch)[0], ref)                      # the parent computes the shipped loss
    assert m.call_loss is fcw.call_loss and m.span_terms is fcw.span_terms   # the trainee keeps the weighting


@pytest.mark.parametrize('guard', ['kf', 'kfsoft'])
def test_train_guard_measures_shipped_and_parent_is_shipped(guard, monkeypatch, tmp_path):
    """train() end to end on a tiny model with stub guard modules and W = 2: the stub kfac_stats runs on the shipped methods at setup
    and at every refresh (no weighted closure fires between its begin and end, and the first measure equals the uninstalled model's
    loss on the diary batch bit for bit), the optimizer steps run on the weighted loss (the closures fire outside the measures, in
    training mode), the closures are back on the instance after each measure, and (kfsoft) replay_kl always sees a parent without them."""
    import custom_io.models
    from domain import mode
    vocab, rows, batch, _ = T.build_batch(n_rows=3, n_calls=3)
    m = span_model(vocab)
    m.eval()
    diary = [dict(r, source='diary') for r in rows]
    _, diary_batch = make_batch(diary)
    ref = m.loss(diary_batch)[0].detach().clone()   # shipped, the uninstalled model, before train() touches it
    events = []
    kf = StubKf(events)
    StubKlreplay.parents = []
    fired = []

    real_install = LP.install_first_call_weight

    def install_spy(model, weight):
        h = real_install(model, weight)
        for name in LP.FirstCallWeight.NAMES:   # a recorder around each weighted closure; shipped() pops / restores whatever is on the instance
            def rec(*a, _f=getattr(model, name), _n=name):
                events.append('weighted_' + _n)
                fired.append((_n, model.training))
                return _f(*a)
            setattr(model, name, rec)
        return h

    def fake_stub_klreplay():
        mod = types.ModuleType('mainbrain.klreplay')
        mod.__file__ = str(tmp_path / 'mainbrain' / 'klreplay.py')
        mod.frozen_copy, mod.replay_kl = StubKlreplay.frozen_copy, StubKlreplay.replay_kl
        return mod

    monkeypatch.setattr(LP, 'install_first_call_weight', install_spy)
    monkeypatch.setattr(torch, 'load', lambda *a, **k: {})
    monkeypatch.setattr(custom_io.models, 'load_model', lambda path: m)
    monkeypatch.setattr(LP, 'load_jsonl', lambda path: [])
    monkeypatch.setattr(LP, 'eval_sets', lambda *a, **k: {})
    monkeypatch.setattr(LP, 'make_rows', lambda *a, **k: (rows, {}))
    monkeypatch.setattr(LP, 'score_step', lambda *a, **k: None)
    monkeypatch.setattr(LP, 'load_guard', lambda src: (kf, StubGp))
    monkeypatch.setattr(LP, 'build_parent_diary', lambda *a, **k: (diary, {'sha256': 'stub'}))
    monkeypatch.setattr(LP, 'verify_guard_commit', lambda src: 'stub')
    monkeypatch.setattr(LP, 'batch_order', lambda n, b, updates, seed: iter([[0, 1, 2]] * updates))
    monkeypatch.setattr(mode, 'make_opt', lambda mm, lr: torch.optim.SGD(mm.parameters(), lr=1e-4))
    monkeypatch.setitem(sys.modules, 'mainbrain.klreplay', fake_stub_klreplay())
    soft = guard == 'kfsoft'
    kw = dict(kl_replay_rows=2, kl_weight=1.0) if soft else {}
    updates = 3
    LP.train('LB', updates, 1, str(tmp_path / 'run'), [updates], guard=guard, guard_every=1, guard_src=str(tmp_path),
             first_call_weight=2.0, **kw)
    assert len(kf.losses) == updates                                     # setup + a refresh after updates 1 and 2 (not after the last)
    assert torch.equal(kf.losses[0], ref), (float(kf.losses[0]), float(ref))
    assert kf.on_instance == [(False, False)] * updates
    # no weighted closure fired inside a measure; they did fire outside (the training steps), in training mode
    inside = False
    for e in events:
        inside = True if e == 'kfac_begin' else False if e == 'kfac_end' else inside
        assert not (inside and e.startswith('weighted_')), events
    assert fired and all(training for _, training in fired), fired
    assert events.count('kfac_begin') == events.count('kfac_end') == updates
    assert all(k in m.__dict__ for k in LP.FirstCallWeight.NAMES)       # still installed at the end
    if soft:
        assert StubKlreplay.parents and set(StubKlreplay.parents) == {(False, False)}, StubKlreplay.parents


def test_zz_train_tests_leave_the_thread_count_alone():
    """Runs after the tests above that call LP.train(threads=1): torch's thread count is still the module's."""
    assert torch.get_num_threads() == THREADS0


if __name__ == '__main__':
    raise SystemExit(pytest.main(['-q', __file__]))
