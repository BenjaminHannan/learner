"""Acceptance tests for the R1 switches in learn_probe: --seed and --first-call-weight
(pairing-map decisions U2 / U3, hidden_files/r1-pairing-map-decisions.md).

  python3 -m domain.far.test_learn_probe_r1     (CPU; needs torch; a couple of minutes)

Covers: same seed -> identical streams (batch order, KL draws, torch draws, ans_drill draws) and identical
initial loss; different seeds -> different init and data order; the KL replay stream follows the run seed
(the import-time trap); the eval fit sample is held across run seeds; seed omitted == the shipped trainer
(SEED 93301, KL_REPLAY_SEED 93312); first-call weight 1.0 == the unmodified loss on a fixed batch, exactly;
weight w, after the per-trace renormalisation renorm = n / (w + n - 1) over the n call rounds, gives round 0 renorm x w,
every later call round renorm and every NOOP round exactly 1.0 (op CE and operand NLL, decomposed by round); the same for
the T1S span terms on a span model: weight 1.0 bit-identical (total, span_call, span_ans, stop), weight w gives span_call's
call rounds renorm (round 0 renorm x w), per trace (mixed call-count batch), with span_ans / stop / span_share / Mn
untouched; L13's recorded invocation parses with the shipped defaults. The finer per-round / per-trace factor checks (n = 1..7,
U3) are in test_learn_probe_r1_renorm.py.
"""
import json
import os
import random
import tempfile

import numpy as np
import pytest
import torch

from domain.far import learn_probe as LP
from domain.far import sheet_probe as SP

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)


def snapshot(seed):
    """The run streams as train() consumes them under apply_run_seed(seed), reset to the shipped seed after."""
    try:
        LP.apply_run_seed(seed)
        snap = dict(seed=LP.SEED, kl_seed=LP.KL_REPLAY_SEED,
                    batches=[list(b) for b in LP.batch_order(97, 16, 4, LP.SEED)],
                    kl=np.random.RandomState(LP.KL_REPLAY_SEED).randint(0, 4096, size=32).tolist())
        torch.manual_seed(LP.SEED)
        snap['init_seed'] = torch.initial_seed()
        snap['torch_draws'] = torch.randn(6).tolist()
        drill = random.Random(f'ans_drill|{torch.initial_seed()}')   # tool.py line 151's construction, verbatim
        snap['drill_draws'] = [drill.random() for _ in range(8)]
    finally:
        LP.apply_run_seed(LP.SHIPPED_SEED)
    return snap


def test_shipped_defaults():
    assert LP.SEED == 93301 and LP.KL_REPLAY_SEED == 93312, (LP.SEED, LP.KL_REPLAY_SEED)   # as imported, before any apply
    via_module = [list(b) for b in LP.batch_order(97, 16, 4, LP.SEED)]
    via_constant = [list(b) for b in LP.batch_order(97, 16, 4, 93301)]
    assert via_module == via_constant
    kl = np.random.RandomState(LP.KL_REPLAY_SEED).randint(0, 4096, size=32).tolist()
    assert kl == np.random.RandomState(93312).randint(0, 4096, size=32).tolist()
    return 'SEED 93301, KL_REPLAY_SEED 93312 as imported; module-seed batch order == batch_order(..., 93301)'


def test_same_seed_identical_streams():
    a, b = snapshot(31001), snapshot(31001)
    assert a == b, 'same --seed twice must consume identical streams'
    return ('two snapshots at seed 31001 identical: first batches ' + str(a['batches'][0][:8]) +
            f", KL draws {a['kl'][:4]}, drill draws {[round(x, 4) for x in a['drill_draws'][:3]]}")


def test_different_seeds_diverge():
    a, c = snapshot(31001), snapshot(31002)
    assert a['batches'] != c['batches'], 'data order must differ across seeds'
    assert a['torch_draws'] != c['torch_draws'], 'torch draws must differ across seeds'
    assert a['drill_draws'] != c['drill_draws'], 'ans_drill draws must differ across seeds'
    return 'seed 31001 vs 31002: batch order, torch draws and ans_drill draws all differ'


def test_kl_stream_follows_seed():
    s = snapshot(31001)
    assert s['kl_seed'] == 31012, s['kl_seed']   # SEED + 11 of the RUN seed, not the shipped 93312
    assert s['kl'] == np.random.RandomState(31012).randint(0, 4096, size=32).tolist()
    assert s['kl'] != np.random.RandomState(93312).randint(0, 4096, size=32).tolist(), 'KL stream left at the shipped seed: the trap'
    assert LP.L5_SEED == 93701 and LP.L3_SEED == 93501 and LP.DIARY_SEED == 200, 'held constants must not move'
    return 'apply_run_seed(31001) -> KL_REPLAY_SEED 31012, draws == RandomState(31012), != RandomState(93312); held constants unmoved'


def test_fit_sample_held():
    rows = [{'id': f'r{i}', 'kind': 'SUM', 'split': 'F4-two', 'prompt': f'p{i}', 'answer': '1'} for i in range(500)]
    probe = [{'id': f'pr{i}', 'kind': k, 'split': s, 'prompt': f'pp{i}', 'answer': '1'}
             for i, (k, s) in enumerate([('SUM', 'F4-two'), ('MAX', 'F0-near'), ('MIN', 'F2b-rows')])]
    with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as f:
        for r in probe:
            f.write(json.dumps(r) + '\n')
        probe_path = f.name
    try:
        fits = []
        for seed in (93301, 31001, 31002):
            LP.apply_run_seed(seed)
            sets = LP.eval_sets(rows, 'l1', fit_seed=LP.L5_SEED, probe_path=probe_path)
            fits.append([r['id'] for r in sets['fit']])
    finally:
        LP.apply_run_seed(LP.SHIPPED_SEED)
        os.unlink(probe_path)
    assert fits[0] == fits[1] == fits[2], 'fit sample must be identical across run seeds'
    joined = [r for r in rows if r['split'] in LP.JOINED_CELLS]
    expect = ['fit-' + r['id'] for r in random.Random(93701).sample(joined, LP.FIT_N)]
    assert fits[0] == expect, 'fit sample must be Random(93701).sample(joined, 420), as shipped'
    return f'fit ids identical at run seeds 93301/31001/31002 and == Random(L5_SEED=93701).sample (n={len(fits[0])})'


def batch_of(rows):
    """(vocab, collated CPU batch) of exactly these rows."""
    from custom_io.data import CharVocab, Dataset, collate, to_device
    vocab = CharVocab.build(rows)
    ds = Dataset(rows, vocab)
    return vocab, to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')


def probe_rows(cells=('F4-two',), per_cell=300):
    """(probe model, usable rows, make_rows drop counts): per_cell candidates from each probe cell in turn (one shared Random(20261016), so the draw
    is deterministic; the kind index starts at 1, as the committed test's `tries` counter did) through the trainer's own make_rows. The generator
    raises nothing on these draws (no try: an exception here is a bug to see, not a candidate to skip)."""
    from collections import Counter
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    from domain import mode
    cons = json.load(open(mode.CONST_PATH))
    torch.manual_seed(777)
    probe_m = Tool(CharVocab.build([{'prompt': 'x', 'answer': '1'}]), **SMALL)
    rng = random.Random(20261016)
    rows, drops = [], Counter()
    for cell in cells:
        prompts = [{'prompt': SP.candidate(SP.SCORED[tries % len(SP.SCORED)], cell, rng)[0]} for tries in range(1, per_cell + 1)]
        got, dropped = LP.make_rows(probe_m, prompts, cons)
        rows += got
        drops.update(dropped)
    return probe_m, rows, drops


def build_batch(n_rows=4, n_calls=3, cells=('F4-two',)):
    """A fixed batch of real rows (probe-cell candidates through the trainer's own make_rows), every row with
    exactly n_calls calls so the per-trace renormalisation is one uniform factor. Join rows (F4-two, the default cell) decompose
    into 3-7 calls (each sheet piece is itself several calculator calls); n_calls=3 is the commonest count. `cells` widens the
    pool (F0-near 1-3 calls, F2-long 4-5, F5-far 4-7)."""
    probe_m, rows, drops = probe_rows(cells)
    sel = [r for r in rows if len(probe_m.row_gold(r)[0]) == n_calls]
    assert len(sel) >= n_rows, f'only {len(sel)} usable {n_calls}-call rows from {300 * len(cells)} candidates in cells {cells} (drops {dict(drops)})'
    rows = sel[:n_rows]
    vocab, batch = batch_of(rows)
    return vocab, rows, batch, n_calls


def test_probe_rows_f4_two_is_the_committed_draw():
    """probe_rows(('F4-two',)) draws exactly what the committed test file's build_batch drew (HEAD's `tries` counter: kind index 1..300 on one
    Random(20261016)), so build_batch() yields the same rows; and make_rows' drop counts come back for the assertion message."""
    rng = random.Random(20261016)
    want = [SP.candidate(SP.SCORED[tries % len(SP.SCORED)], 'F4-two', rng)[0] for tries in range(1, 301)]
    probe_m, rows, drops = probe_rows(('F4-two',))
    kept = {r['prompt'] for r in rows}
    assert kept <= set(want) and len(rows) + sum(drops.values()) == len(want), (len(rows), dict(drops))
    assert [r['prompt'] for r in rows] == [p for p in want if p in kept]    # in the committed order
    assert dict(drops) == {'calc_?_or_negative': 81}


def test_seed_model_init_and_initial_loss():
    from custom_io.models.tool import Tool
    vocab, rows, batch, _ = build_batch()
    losses, inits = {}, {}
    try:
        for seed in (31001, 31001, 31002):
            LP.apply_run_seed(seed)
            torch.manual_seed(LP.SEED)   # as train() does before load_model
            m = Tool(vocab, **SMALL)
            m.train()
            with torch.no_grad():
                losses.setdefault(seed, []).append(float(m.loss(batch)[0]))
            inits.setdefault(seed, []).append({k: v.detach().clone() for k, v in m.state_dict().items()})
    finally:
        LP.apply_run_seed(LP.SHIPPED_SEED)
    same = all(torch.equal(inits[31001][0][k], inits[31001][1][k]) for k in inits[31001][0])
    ndiff = sum(not torch.equal(inits[31001][0][k], inits[31002][0][k]) for k in inits[31001][0])
    assert losses[31001][0] == losses[31001][1], 'same seed: initial loss must be identical'
    assert same, 'same seed: init must be identical'
    assert losses[31001][0] != losses[31002][0], 'different seeds: initial loss must differ'
    assert ndiff > 0, 'different seeds: init must differ'
    return (f'seed 31001 initial loss {losses[31001][0]:.6f} twice, init identical over all {len(inits[31001][0])} tensors; '
            f'seed 31002 loss {losses[31002][0]:.6f}, {ndiff} tensors differ')


def test_weight_1_exact_and_scaling():
    from custom_io.models.tool import Tool
    vocab, rows, batch, n_calls = build_batch()
    torch.manual_seed(4242)
    m = Tool(vocab, **SMALL)
    m.train()
    B = len(rows)
    plain, aux = m.loss(batch)
    plain = float(plain)
    g = m.gold(batch['rows'], 'cpu', None)
    o = m.run(batch, gold=g)
    n, T = n_calls, len(o['steps'])
    assert ((g['op'] > 0).sum(1) == n).all(), 'the decomposition test needs a uniform call count per row'
    assert n < T, 'the decomposition test needs NOOP rounds after the program'

    def part(fn, a, b):
        """(op CE, operand NLL) summed over rounds [a, b): the difference of two prefix evaluations, the full gold passed
        throughout (the per-trace factors are computed from it), so it works for the shipped and the weighted call_loss."""
        tot = lambda k: (0.0, 0.0) if k == 0 else tuple(float(x) for x in fn(o['steps'][:k], g, B)[:2])
        hi, lo = tot(b), tot(a)
        return hi[0] - lo[0], hi[1] - lo[1]

    # decomposition of the plain call loss into round 0 (first call), later call rounds and NOOP rounds, unmodified code only
    F, Rc, Rn = (part(lambda *a: Tool.call_loss(m, *a), a_, b_) for a_, b_ in ((0, 1), (1, n), (n, T)))
    callsum = sum(F) + sum(Rc) + sum(Rn)
    rest = plain - callsum
    assert abs(callsum - float(aux['prog'])) < 1e-4, (callsum, float(aux['prog']))
    out = [f'plain loss {plain:.6f} = first-call {sum(F):.6f} + later calls {sum(Rc):.6f} + NOOP rounds {sum(Rn):.6f} '
           f'+ non-call terms {rest:.6f}']
    # weight 1.0 through the wrapper: bit-exact against the unmodified trainer
    LP.install_first_call_weight(m, 1.0)
    try:
        w1, aux1 = m.loss(batch)
        assert float(w1) == plain and float(aux1['prog']) == float(aux['prog']), (float(w1), plain)
        out.append('weight 1.0 == unmodified loss exactly (bit-identical, aux prog identical)')
        # weight w: the call rounds are renormalised per trace by renorm = n / (w + n - 1): round 0 carries renorm x w, each
        # later call round renorm, and the NOOP rounds exactly 1.0, on the op CE and on the operand NLL alike
        for w in (2.0, 3.0):
            LP.install_first_call_weight(m, w)
            renorm = n / (w + n - 1)
            W0, Wc, Wn = (part(m.call_loss, a_, b_) for a_, b_ in ((0, 1), (1, n), (n, T)))
            for k, name in ((0, 'op CE'), (1, 'operand NLL')):
                assert abs(W0[k] - renorm * w * F[k]) < 1e-4, (w, name, W0[k], renorm * w * F[k])
                assert abs(Wc[k] - renorm * Rc[k]) < 1e-4, (w, name, 'later call rounds', Wc[k], renorm * Rc[k])
                assert Wn[k] == pytest.approx(Rn[k], rel=1e-5, abs=1e-6), (w, name, 'NOOP rounds changed', Wn[k], Rn[k])
            call_w = sum(W0) + sum(Wc) + sum(Wn)
            expect = renorm * (w * sum(F) + sum(Rc)) + sum(Rn)
            assert abs(call_w - expect) < 1e-4, (w, call_w, expect)
            assert abs((float(m.loss(batch)[0]) - rest) - expect) < 1e-4, 'total loss: non-call terms moved'
            out.append(f'weight {w:g}: renorm {renorm:.4f}; round 0 x {renorm * w:.4f}, later calls x {renorm:.4f}, NOOP rounds x 1 '
                       f'(op CE and operand NLL); call term {call_w:.6f} = {renorm:.4f} x ({w:g} x first {sum(F):.6f} + later {sum(Rc):.6f}) '
                       f'+ NOOP {sum(Rn):.6f}')
    finally:
        del m.call_loss, m.span_terms   # back to the class methods (install_first_call_weight sets both)
    return '; '.join(out)


def build_span_model(vocab, seed=4242):
    """A T1S model (the T1SD stack: span_copy + span_idx + span_end, L13's lineage). ans_drill=0.0 so the golds are
    fixed across repeated loss() calls (drills would draw from the model's own stream on each training-mode call)."""
    from custom_io.models.tool import Tool
    torch.manual_seed(seed)
    m = Tool(vocab, span_copy=True, span_idx=True, span_end=True, ans_drill=0.0, **SMALL)
    m.train()
    return m


def test_span_weight_1_exact_and_scaling():
    from custom_io.models.tool import Tool
    vocab, rows, batch, n_calls = build_batch()
    m = build_span_model(vocab)
    B = len(rows)
    plain, aux = m.loss(batch)
    plain = float(plain)
    sc_p, sa_p, st_p = float(aux['span_call']), float(aux['span_ans']), float(aux['stop'])
    assert sc_p > 0, 'the span terms must be live in this test'
    # decomposition of span_call into round 0 and later rounds, unmodified code only (truncated step lists)
    g = m.gold(batch['rows'], 'cpu', None)
    o = m.run(batch, gold=g)
    full, Mn_f = Tool.span_terms(m, o, g, batch, B)
    r0, Mn_0 = Tool.span_terms(m, dict(o, steps=o['steps'][:1]), g, batch, B)
    SC, SC0 = float(full['span_call']), float(r0['span_call'])
    REST = SC - SC0
    assert abs(SC - sc_p) < 1e-4 and SC0 > 0.01, (SC, sc_p, SC0)
    assert torch.equal(Mn_f, Mn_0), 'Mn must not depend on the step list'
    out = [f'plain loss {plain:.6f}; span_call {SC:.6f} = round 0 {SC0:.6f} + later rounds {REST:.6f}; '
           f'span_ans {sa_p:.6f}, stop {st_p:.6f}']
    LP.install_first_call_weight(m, 1.0)
    try:
        w1, aux1 = m.loss(batch)
        assert float(w1) == plain, (float(w1), plain)
        assert float(aux1['span_call']) == sc_p and float(aux1['span_ans']) == sa_p and float(aux1['stop']) == st_p
        out.append('weight 1.0 == unmodified loss exactly (total, span_call, span_ans, stop all bit-identical)')
        for w in (2.0, 3.0):
            LP.install_first_call_weight(m, w)
            terms, Mn_w = m.span_terms(o, g, batch, B)
            renorm = n_calls / (w + n_calls - 1)   # per trace, uniform over this batch
            expect = renorm * (w * SC0 + REST)   # round 0 renorm x w, later call rounds renorm
            assert abs(float(terms['span_call']) - expect) < 1e-4, (w, float(terms['span_call']), expect)
            assert float(terms['stop']) == float(full['stop']), 'stop term changed'
            assert float(terms['span_share']) == float(full['span_share']), 'span_share changed'
            assert torch.equal(Mn_w, Mn_f), 'Mn changed: span_ans would move'
            tw, auxw = m.loss(batch)
            assert float(auxw['span_ans']) == sa_p and float(auxw['stop']) == st_p, 'span_ans / stop moved in the total loss'
            assert abs(float(auxw['span_call']) - float(terms['span_call'])) < 1e-4
            delta = float(tw) - plain
            parts = (float(auxw['prog']) - float(aux['prog'])) + (float(auxw['span_call']) - sc_p)
            assert abs(delta - parts) < 1e-4, (w, delta, parts)   # the total moves by exactly the call + span deltas
            out.append(f'weight {w:g}: span_call {float(terms["span_call"]):.6f} = {renorm:.4f} x ({w:g} x round 0 {SC0:.6f} + '
                       f'later call rounds {REST:.6f}) (span_ans, stop, span_share unchanged); '
                       f'total delta {delta:.6f} == call delta + span delta')
    finally:
        del m.call_loss, m.span_terms   # back to the class methods
    return '; '.join(out)


def build_mixed_batch():
    """Rows with two different call counts (3 and 4) in one batch, so the per-trace renormalisation differs by row."""
    _, rows3, _, _ = build_batch(n_rows=3, n_calls=3)
    _, rows4, _, _ = build_batch(n_rows=2, n_calls=4)
    rows = rows3 + rows4
    vocab, batch = batch_of(rows)
    return vocab, rows, batch


def _slice_batch(batch, i):
    return {'prompt_ids': batch['prompt_ids'][i:i + 1], 'rows': batch['rows'][i:i + 1]}


def _slice_g(g, i):
    return {k: (v[i:i + 1] if torch.is_tensor(v) else [v[i]] if isinstance(v, list) else v) for k, v in g.items()}


def _slice_o(o, i):
    def sl_step(st):
        return tuple({k: (v[i:i + 1] if torch.is_tensor(v) else v) for k, v in x.items()} if isinstance(x, dict)
                     else x[i:i + 1] for x in st)
    return {**o, 'steps': [sl_step(st) for st in o['steps']]}


def test_span_weight_per_trace_factor():
    from custom_io.models.tool import Tool
    vocab, rows, batch = build_mixed_batch()
    m = build_span_model(vocab)
    B = len(rows)
    g = m.gold(batch['rows'], 'cpu', None)
    o = m.run(batch, gold=g)
    counts = [int(x) for x in (g['op'] > 0).sum(1)]
    assert len(set(counts)) == 2, counts   # the batch really mixes two trace lengths
    w = 2.0
    LP.install_first_call_weight(m, w)
    worst = 0.0
    try:
        for i in range(B):
            bi, gi, oi = _slice_batch(batch, i), _slice_g(g, i), _slice_o(o, i)
            plain_i = float(Tool.span_terms(m, oi, gi, bi, 1)[0]['span_call'])
            r0_i = float(Tool.span_terms(m, dict(oi, steps=oi['steps'][:1]), gi, bi, 1)[0]['span_call'])
            assert r0_i > 0.01, (i, r0_i)
            got_i = float(m.span_terms(oi, gi, bi, 1)[0]['span_call'])
            n = counts[i]
            expect_i = (n / (w + n - 1)) * (w * r0_i + (plain_i - r0_i))   # round 0 renorm x w, later call rounds renorm
            worst = max(worst, abs(got_i - expect_i))
            assert abs(got_i - expect_i) < 1e-4, (i, n, got_i, expect_i)
        agg = float(m.span_terms(o, g, batch, B)[0]['span_call'])
        per = sum(float(m.span_terms(_slice_o(o, i), _slice_g(g, i), _slice_batch(batch, i), 1)[0]['span_call'])
                  for i in range(B)) / B
        assert abs(agg - per) < 1e-4, (agg, per)
    finally:
        del m.call_loss, m.span_terms
    return (f'mixed batch (call counts {counts}): every row\'s span_call is its own renorm n/(w+n-1) times (w x round 0 + later '
            f'call rounds) (worst per-row error {worst:.2e}); the batch aggregate equals the '
            f'mean of the per-row values')


def test_l13_invocation_parses():
    seen = {}
    real_train = LP.train
    LP.train = lambda *a, **kw: seen.update(kw)
    try:
        with tempfile.TemporaryDirectory() as td:
            LP.main(['train', '--arm', 'LB', '--guard', 'kfsoft', '--guard-soft', '10',
                     '--kl-replay-rows', '32', '--kl-weight', '10', '--cells', 'l5', '--updates', '4000',
                     '--out', td, '--guard-src', td])
            l13 = dict(seen)
            LP.main(['train', '--arm', 'LB', '--guard', 'kfsoft', '--guard-soft', '10',
                     '--kl-replay-rows', '32', '--kl-weight', '10', '--cells', 'l5', '--updates', '1000',
                     '--seed', '31003', '--first-call-weight', '2', '--out', td, '--guard-src', td])
            r1 = dict(seen)
    finally:
        LP.train = real_train
    assert l13['seed'] is None and l13['first_call_weight'] == 1.0 and l13['guard_soft'] == 10.0, l13
    assert r1['seed'] == 31003 and r1['first_call_weight'] == 2.0, r1
    return ("L13's invocation (LB, kfsoft, soft 10, 32 rows, 10x KL, l5, 4000) parses with seed=None, "
            'first_call_weight=1.0; the R1 form parses with seed=31003, first_call_weight=2.0')


TESTS = [test_shipped_defaults, test_same_seed_identical_streams, test_different_seeds_diverge,
         test_kl_stream_follows_seed, test_fit_sample_held, test_seed_model_init_and_initial_loss,
         test_weight_1_exact_and_scaling, test_span_weight_1_exact_and_scaling,
         test_span_weight_per_trace_factor, test_l13_invocation_parses]

if __name__ == '__main__':
    for t in TESTS:
        print(f'PASS {t.__name__}: {t()}', flush=True)
    print(f'all {len(TESTS)} tests passed')
