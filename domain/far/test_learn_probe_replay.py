"""Acceptance tests for the replay-only guard arm (C1) and the always-on harm instrument (C2) in learn_probe.

  python3 -m domain.far.test_learn_probe_replay     (CPU; needs torch; small models)

Covers: the check_guard_args matrix (every new refusal, the kf / kfsoft refusals and messages unchanged, L13's and L14's
invocations still validating and parsing); ce_replay_loss == plain(new) + w * plain(diary) on a fixed mixed batch, == the plain
loss with no diary rows / not training, aux carries replay_ce; kl_replay_loss untouched (source pinned to the R1 commit's text, and
== plain(new) + w * replay_kl on a fixed batch); apply_run_seed moves the replay stream for --guard replay; the RNG isolation of
the wrapped harm function (torch incl. initial_seed, python random, numpy global); the harm-steps default
([500,1000,2000,4000], [] with --no-harm); the DEV sha256 check; the paired per-row harm files; and the replay arm's setup
(no Guarded, every parameter trainable, the unguarded LB optimizer).
A1F (--replay-freeze): the check_guard_args refusals and the main() parse; the frozen set equals what Guarded freezes on the same model
(small test model: compared with a real Guarded built on a stub kf; the real parent: 41 tensors); the trainable set, the optimizer groups
and the clip set equal Guarded's; after 3 optimizer steps the frozen tensors are bit-identical and the rest changed (also with the
weight decay on). Futility stop (--stop-if-drop): parse_stop_if_drop (good and bad specs, non-harm steps refused), futility_stop (the
decision, boundary included), score_step writing futility_stop on the step's record, train() stopping with no further update or score,
and main() parsing it. guard_commit_check recorded for the replay-kl arm and kfsoft with --diary-cache (and absent for replay-ce, so the
shipped records are unchanged), with the A1F extras only on the A1F arm.
A1F is ONE change vs L11 (test_a1f_is_one_change_vs_l11): train() for A1F and for kfsoft with a pass-through KFOptimizer (real kfac_stats / factors, one
re-measure) gives equal state_dict hashes at every scored step. --stop-if-drop with --keep-final keeps the stopped step's checkpoint (score_step and train()).
Tests that need the guard source folder (GUARD_SRC) or the real parent are skipped (Skip: pytest.skip under pytest, a SKIP line in the __main__ runner) when
those are absent; the parts of a test that need the real skills DEV (REAL_DEV) say so in their PASS line when those are absent.
"""
import hashlib
import inspect
import json
import os
import random
import tempfile

import numpy as np
import torch

from domain.far import learn_probe as LP
from domain.far.test_learn_probe_r1 import SMALL, build_batch

GUARD_SRC = '/home/user/guardsrc'
FAR = '/home/user/farin/inputs/far-transfer/learn'
PARENT = '/home/user/farin/inputs/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
PROBE = '/home/user/farin/inputs/far-transfer/diag/sheet-probe.jsonl'
REAL_BIG = '/home/user/sk200k_big/dev/in_dist.jsonl'
REAL_TRAIN = '/home/user/sk200k/train.jsonl'
REAL_DEV = '/home/user/sk200k/dev/in_dist.jsonl'
try:
    import pytest
    Skip = pytest.skip.Exception   # under pytest a missing input is a reported skip, not a pass (a returned string is a pass there)
except ImportError:
    class Skip(Exception):
        pass
KL_REPLAY_LOSS_SHA256 = '4c71ae17525f2ca1883f5d45d73955dbc2a8cdffe0232df443fcd1618f4c149d'   # sha256 of inspect.getsource(kl_replay_loss) at 4d294b665 (R1)


def skip(why):
    raise Skip(why)


def raises(fn, needle):
    try:
        fn()
    except SystemExit as e:
        assert needle in str(e), (needle, str(e))
        return
    raise AssertionError(f'no SystemExit (wanted {needle!r})')


def tool(vocab, seed=4242):
    from custom_io.models.tool import Tool
    torch.manual_seed(seed)
    m = Tool(vocab, ans_drill=0.0, **SMALL)   # ans_drill 0: repeated training-mode loss() calls draw nothing, so values are comparable
    m.train()
    return m


def mixed_batch(n_new=3, n_diary=2):
    """A fixed batch: n_new rows with source 'tool' then n_diary rows with source 'diary' (real join rows through make_rows)."""
    from custom_io.data import CharVocab, Dataset, collate, to_device
    _, rows, _, _ = build_batch(n_rows=n_new + n_diary, n_calls=3)
    rows = [dict(r, source='diary' if i >= n_new else 'tool') for i, r in enumerate(rows)]
    vocab = CharVocab.build(rows)
    ds = Dataset(rows, vocab)
    return vocab, rows, to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')


def sub(b, idx):
    t = torch.tensor(idx)
    return {k: (v[t] if torch.is_tensor(v) else [v[i] for i in idx]) for k, v in b.items()}


def rng_state():
    n = np.random.get_state()
    return (torch.get_rng_state().clone(), torch.initial_seed(), random.getstate(), (n[0], n[1].copy(), n[2:]))


def same_state(a, b):
    return (torch.equal(a[0], b[0]) and a[1] == b[1] and a[2] == b[2] and a[3][0] == b[3][0]
            and np.array_equal(a[3][1], b[3][1]) and a[3][2] == b[3][2])


def run_main(argv):
    """main(argv) with train() stubbed -> the kwargs train would get, positional ones included under 'args'."""
    seen = {}
    real = LP.train
    LP.train = lambda *a, **kw: seen.update(kw, args=a)
    try:
        LP.main(argv)
    finally:
        LP.train = real
    return seen


def test_check_guard_args_matrix():
    with tempfile.TemporaryDirectory() as src:
        ok = [  # (kwargs) accepted
            dict(arm='LA', guard=None, guard_src=None),
            dict(arm='LB', guard=None, guard_src=None),
            dict(arm='LB', guard='kf', guard_src=src),
            dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0, soft=10.0),   # L13
            dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0, soft='hard'),   # L14
            dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0),
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0),
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=1, kl_weight=0.5, replay_loss='ce'),
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_loss='kl'),
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_freeze=True),   # A1F
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_loss='ce', replay_freeze=True),
            dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_freeze=False),
        ]
        for kw in ok:
            LP.check_guard_args(**kw)
        bad = [  # (kwargs, message fragment)
            (dict(arm='LB', guard='kf', guard_src=src, kl_rows=32), '--kl-replay-rows / --kl-weight / --guard-soft apply to --guard kfsoft only'),
            (dict(arm='LB', guard='kf', guard_src=src, kl_weight=3.0), '--kl-replay-rows / --kl-weight / --guard-soft apply to --guard kfsoft only'),
            (dict(arm='LB', guard=None, guard_src=None, soft=1.0), '--kl-replay-rows / --kl-weight / --guard-soft apply to --guard kfsoft only'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32), '--guard kfsoft needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=0, kl_weight=10.0), '--guard kfsoft needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=0.0), '--guard kfsoft needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0, soft=-1.0), "--guard-soft must be > 0 or 'hard'"),
            (dict(arm='LA', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0), '--guard applies to arm LB only'),
            (dict(arm='LB', guard='kf', guard_src=None), '--guard needs --guard-src DIR'),
            (dict(arm='LB', guard='kf', guard_src=src, energy=1.5), '--guard-energy must be in (0,1)'),
            (dict(arm='LB', guard='bogus', guard_src=src), 'unknown guard bogus'),
            # new: --guard replay
            (dict(arm='LA', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0), '--guard applies to arm LB only'),
            (dict(arm='LB', guard='replay', guard_src=src), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_weight=10.0), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=0, kl_weight=10.0), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=0.0), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=-1.0), '--guard replay needs --kl-replay-rows >= 1 and --kl-weight > 0'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, soft=1.0), '--guard-soft applies to --guard kfsoft only'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, soft='hard'), '--guard-soft applies to --guard kfsoft only'),
            (dict(arm='LB', guard='replay', guard_src=None, kl_rows=32, kl_weight=10.0), '--guard needs --guard-src DIR'),
            (dict(arm='LB', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_loss='mse'), '--replay-loss must be one of'),
            # new: --replay-loss only with replay
            (dict(arm='LB', guard=None, guard_src=None, replay_loss='ce'), '--replay-loss applies to --guard replay only'),
            (dict(arm='LB', guard='kf', guard_src=src, replay_loss='kl'), '--replay-loss applies to --guard replay only'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0, replay_loss='kl'), '--replay-loss applies to --guard replay only'),
            # new (A1F): --replay-freeze only with replay
            (dict(arm='LB', guard=None, guard_src=None, replay_freeze=True), '--replay-freeze applies to --guard replay only'),
            (dict(arm='LB', guard='kf', guard_src=src, replay_freeze=True), '--replay-freeze applies to --guard replay only'),
            (dict(arm='LB', guard='kfsoft', guard_src=src, kl_rows=32, kl_weight=10.0, replay_freeze=True), '--replay-freeze applies to --guard replay only'),
            (dict(arm='LA', guard='replay', guard_src=src, kl_rows=32, kl_weight=10.0, replay_freeze=True), '--guard applies to arm LB only'),
        ]
        for kw, needle in bad:
            raises(lambda: LP.check_guard_args(**kw), needle)
        # through main(): the refusals happen before train() is reached; L13 and L14 parse with the shipped defaults
        base = ['train', '--arm', 'LB', '--out', src, '--guard-src', src]
        raises(lambda: run_main(base + ['--guard', 'replay', '--kl-replay-rows', '32', '--kl-weight', '10', '--guard-soft', '10']), '--guard-soft applies to --guard kfsoft only')
        raises(lambda: run_main(base + ['--replay-loss', 'ce']), '--replay-loss applies to --guard replay only')
        raises(lambda: run_main(base + ['--guard', 'replay']), '--guard replay needs')
        l13 = run_main(base + ['--guard', 'kfsoft', '--guard-soft', '10', '--kl-replay-rows', '32', '--kl-weight', '10', '--cells', 'l5', '--updates', '4000'])
        l14 = run_main(base + ['--guard', 'kfsoft', '--guard-soft', 'hard', '--kl-replay-rows', '32', '--kl-weight', '10', '--cells', 'l5', '--updates', '4000'])
        rp = run_main(base + ['--guard', 'replay', '--kl-replay-rows', '32', '--kl-weight', '10', '--replay-loss', 'ce'])
        rp0 = run_main(base + ['--guard', 'replay', '--kl-replay-rows', '32', '--kl-weight', '10'])
        raises(lambda: run_main(base + ['--replay-freeze']), '--replay-freeze applies to --guard replay only')
        raises(lambda: run_main(base + ['--guard', 'kfsoft', '--kl-replay-rows', '32', '--kl-weight', '10', '--replay-freeze']), '--replay-freeze applies to --guard replay only')
        a1f = run_main(base + ['--guard', 'replay', '--kl-replay-rows', '32', '--kl-weight', '10', '--replay-freeze'])
    for r, soft in ((l13, 10.0), (l14, 'hard')):
        assert r['guard'] == 'kfsoft' and r['guard_soft'] == soft and r['kl_replay_rows'] == 32 and r['kl_weight'] == 10.0, r
        assert r['replay_loss'] is None and r['seed'] is None and r['first_call_weight'] == 1.0, r
    assert rp['guard'] == 'replay' and rp['replay_loss'] == 'ce' and rp['guard_soft'] is None, rp
    assert rp0['replay_loss'] is None, rp0   # None -> 'kl' inside train()
    assert a1f['replay_freeze'] is True and a1f['stop_if_drop'] is None and rp0['replay_freeze'] is False and l13['replay_freeze'] is False, (a1f, rp0)
    return f'{len(ok)} accepted, {len(bad)} refused with the expected messages; kf/kfsoft messages unchanged; L13 (soft 10) and L14 (soft hard) validate and parse'


def test_ce_replay_loss():
    vocab, rows, batch = mixed_batch(3, 2)
    m = tool(vocab)
    plain = m.loss
    w = 7.5
    ces = []
    loss = LP.ce_replay_loss(m, w, ces)
    out = loss(batch)
    assert isinstance(out, tuple) and isinstance(out[1], dict)
    new_ix, dia_ix = [0, 1, 2], [3, 4]
    p_new, aux_new = plain(sub(batch, new_ix))
    p_dia, _ = plain(sub(batch, dia_ix))
    expect = p_new + w * p_dia
    assert abs(float(out[0]) - float(expect.detach())) < 1e-6, (float(out[0]), float(expect))
    assert abs(float(out[0]) - (float(p_new) + w * float(p_dia))) < 1e-3   # the float64 sum, to float32 rounding
    assert ces == [float(p_dia.detach())] and abs(out[1]['replay_ce'] - float(p_dia)) < 1e-6, (ces, out[1].get('replay_ce'))
    assert set(out[1]) == set(aux_new) | {'replay_ce'}, 'aux keys: the new rows\' plus replay_ce only'
    assert out[0].requires_grad
    # the replay half really enters the gradient: backward reaches every parameter that the diary rows reach
    out[0].backward()
    assert any(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in m.parameters())
    # no diary rows / no new rows / not training / no grad: the plain loss, untouched
    only_new = sub(batch, new_ix)
    only_dia = sub(batch, dia_ix)
    n0 = len(ces)
    for b in (only_new, only_dia):
        assert float(loss(b)[0]) == float(plain(b)[0])
    m.eval()
    assert float(loss(batch)[0]) == float(plain(batch)[0])
    m.train()
    with torch.no_grad():
        assert float(loss(batch)[0]) == float(plain(batch)[0])
    assert len(ces) == n0, 'plain-loss passes must not log a replay value'
    # weight 0-ish limit and the sum structure: weight scales only the diary half
    out2 = LP.ce_replay_loss(m, 2 * w, [])(batch)
    assert abs(float(out2[0]) - float(p_new + 2 * w * p_dia)) < 1e-6
    return (f'w={w}: loss {float(out[0]):.6f} == plain(new) {float(p_new):.6f} + {w} x plain(diary) {float(p_dia):.6f} (|diff| < 1e-6); '
            f'aux gains replay_ce only; plain loss exactly with no diary rows / no new rows / eval / no_grad')


def test_kl_replay_loss_untouched():
    src = inspect.getsource(LP.kl_replay_loss)
    sha = hashlib.sha256(src.encode()).hexdigest()
    assert sha == KL_REPLAY_LOSS_SHA256, f'kl_replay_loss source changed (sha256 {sha})'
    if not os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
        return f'kl_replay_loss source pinned to the R1 commit (sha256 {sha[:12]}); value check SKIPPED: no guard source at {GUARD_SRC}'
    klreplay = LP.load_klreplay(GUARD_SRC)
    vocab, rows, batch = mixed_batch(3, 2)
    m = tool(vocab)
    parent = klreplay.frozen_copy(m)
    with torch.no_grad():   # move the model off the parent so the KL is live
        g = torch.Generator().manual_seed(3)
        for p in m.parameters():
            p.add_(0.02 * torch.randn(p.shape, generator=g))
    plain = m.loss
    w, kls = 10.0, []
    out = LP.kl_replay_loss(m, parent, w, kls, klreplay)(batch)
    p_new, _ = plain(sub(batch, [0, 1, 2]))
    kl, _ = klreplay.replay_kl(m, parent, sub(batch, [3, 4]))
    expect = p_new + w * kl
    assert float(kl) > 0 and abs(float(out[0]) - float(expect.detach())) < 1e-6, (float(out[0]), float(expect))
    assert kls == [float(kl.detach())] and abs(out[1]['replay_kl'] - float(kl)) < 1e-6
    only_new = sub(batch, [0, 1, 2])
    assert float(LP.kl_replay_loss(m, parent, w, [], klreplay)(only_new)[0]) == float(plain(only_new)[0])
    return (f'kl_replay_loss source pinned (sha256 {sha[:12]}); w={w}: {float(out[0]):.6f} == plain(new) {float(p_new):.6f} '
            f'+ {w} x replay_kl {float(kl):.6f}; plain on new-only batch')


def test_seed_moves_replay_stream():
    try:
        LP.apply_run_seed(31001)
        assert LP.KL_REPLAY_SEED == 31012 and LP.SEED == 31001
        draws = np.random.RandomState(LP.KL_REPLAY_SEED).randint(0, 4096, size=32).tolist()
        assert draws == np.random.RandomState(31012).randint(0, 4096, size=32).tolist()
        assert draws != np.random.RandomState(93312).randint(0, 4096, size=32).tolist()
        # the replay arm reads the module global at train time, after apply_run_seed (source-level: the same expression as kfsoft's)
        body = inspect.getsource(LP.train)
        assert body.count('np.random.RandomState(KL_REPLAY_SEED)') == 2 and 'if replay_arm:' in body, 'both arms must draw from RandomState(KL_REPLAY_SEED)'
        assert body.index('apply_run_seed(seed)') < body.index('np.random.RandomState(KL_REPLAY_SEED)'), 'seed must apply before the stream is built'
        seen = run_main(['train', '--arm', 'LB', '--out', '/tmp', '--guard-src', '/tmp', '--guard', 'replay', '--kl-replay-rows', '4',
                         '--kl-weight', '1', '--seed', '31001'])
        assert seen['seed'] == 31001 and seen['guard'] == 'replay', seen
    finally:
        LP.apply_run_seed(93301)
    assert LP.KL_REPLAY_SEED == 93312
    return 'apply_run_seed(31001): KL_REPLAY_SEED 31012, replay draws == RandomState(31012) != RandomState(93312); --seed reaches train() for --guard replay'


def write_dev(path, n=6):
    fams = ['arith_bare', 'chain_ops']
    with open(path, 'w') as f:
        for i in range(n):
            f.write(json.dumps({'id': f'x{i}', 'family': fams[i % 2], 'prompt': f'{i}+1', 'answer': str(i + 1), 'accepted': [str(i + 1)], 'level': 1}) + '\n')


def test_rng_isolation():
    from domain import harm
    real = harm.in_dist_hits

    def noisy(ckpt, rows):   # a stub that consumes every RNG, and moves torch's initial seed too
        torch.manual_seed(12345)
        torch.rand(7)
        random.random()
        random.seed(99)
        np.random.rand(5)
        np.random.seed(7)
        return [int(i % 2 == 0) if ckpt == 'parent' else int(i % 3 == 0) for i in range(len(rows))], 50.0

    with tempfile.TemporaryDirectory() as td:
        dev = os.path.join(td, 'dev.jsonl')
        write_dev(dev)
        harm.in_dist_hits = noisy
        try:
            torch.manual_seed(2024); random.seed(5); np.random.seed(6)
            control = rng_state()
            noisy('x', [{}] * 3)
            assert not same_state(control, rng_state()), 'control: the stub must move the RNG states'
            torch.manual_seed(2024); random.seed(5); np.random.seed(6)
            before = rng_state()
            fn = LP.make_harm_fn('parent', dev, td, dev_any=True, dev_big=dev)   # builds (parent hits) under isolation too
            assert same_state(before, rng_state()), 'building the harm fn (parent hits) moved an RNG state'
            res = fn('child', 500)
            assert same_state(before, rng_state()), 'calling the harm fn moved an RNG state'
            res2 = fn('child', 1000)
            assert same_state(before, rng_state())
        finally:
            harm.in_dist_hits = real
        assert res['n'] == 6 and 'harm_big' in res and res['harm_big']['n'] == 6, res
        assert res['dev_sha256'] == LP.file_sha256(dev) and res['dev_sha256_checked'] is False, res
        assert res['harm_big']['dev_sha256_checked'] is False and res['harm_big']['dev_sha256'] == res['dev_sha256']   # dev_any: both unchecked
        for name in ('harm-rows-step500.json', 'harm-rows-big-step500.json', 'harm-rows-step1000.json'):
            d = json.load(open(os.path.join(td, name)))
            assert set(d) == {'step', 'dev', 'dev_sha256', 'ids', 'family', 'parent_hits', 'child_hits'}, set(d)
            assert d['ids'] == [f'x{i}' for i in range(6)] and d['family'][:2] == ['arith_bare', 'chain_ops']
            assert d['parent_hits'] == [int(i % 2 == 0) for i in range(6)] and d['child_hits'] == [int(i % 3 == 0) for i in range(6)]
            assert d['dev_sha256'] == res['dev_sha256']
        ph = json.load(open(os.path.join(td, 'parent-hits.json')))
        assert ph['dev_sha256'] == res['dev_sha256'] and ph['hits'] == [int(i % 2 == 0) for i in range(6)]
        assert os.path.exists(os.path.join(td, 'parent-hits-big.json'))
    return ('torch (state and initial_seed), python random and numpy global states identical before/after building the harm fn and '
            'after each call, with a stub that seeds and draws from all three (control: unwrapped stub moves them); '
            'harm-rows-step{N} / harm-rows-big-step{N} / parent-hits.json carry the paired rows and the DEV sha')


def test_harm_steps_default():
    with tempfile.TemporaryDirectory() as td:
        base = ['train', '--arm', 'LB', '--out', td]
        d = run_main(base)
        assert d['harm_steps'] == [500, 1000, 2000, 4000] and d['args'][4] == [0, 500, 1000, 2000, 4000], d['harm_steps']
        assert run_main(base + ['--no-harm'])['harm_steps'] == []
        assert run_main(base + ['--harm-steps', '1000,4000'])['harm_steps'] == [1000, 4000]
        assert run_main(base + ['--harm-steps', ''])['harm_steps'] == [], "explicit '' keeps the old none"
        assert run_main(base + ['--steps', '0,100,300'])['harm_steps'] == [100, 300]
        raises(lambda: run_main(base + ['--no-harm', '--harm-steps', '500']), '--no-harm and --harm-steps are exclusive')
        raises(lambda: run_main(base + ['--no-harm', '--harm-dev-big', '/x']), '--harm-dev-big needs harm steps')
        k = run_main(base + ['--dev-any', '--harm-dev-big', '/x', '--dev', '/y'])
        assert k['dev_any'] is True and k['harm_dev_big'] == '/x' and k['dev'] == '/y'
        k0 = run_main(base)
        assert k0['dev_any'] is False and k0['harm_dev_big'] is None
    assert LP.resolve_harm_steps([0, 500], None, False) == [500]
    return 'default --steps -> harm steps [500, 1000, 2000, 4000]; --no-harm -> []; explicit lists / "" as given; --no-harm with --harm-steps refused'


def test_dev_sha_check():
    assert LP.DEV_IN_DIST_SHA256 == 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'
    with tempfile.TemporaryDirectory() as td:
        wrong = os.path.join(td, 'dev.jsonl')
        write_dev(wrong)
        raises(lambda: LP.dev_provenance(os.path.join(td, 'nope.jsonl')), 'not found')   # a SystemExit, not a FileNotFoundError traceback
        raises(lambda: LP.dev_provenance(wrong), 'not the skills DEV in_dist')
        sha, checked = LP.dev_provenance(wrong, dev_any=True)
        assert sha == LP.file_sha256(wrong) and checked is False
        raises(lambda: LP.make_harm_fn('p', wrong, td), 'not the skills DEV in_dist')   # refused before any scoring
        # train() refuses before any work (before the out dir is made)
        out = os.path.join(td, 'run')
        raises(lambda: LP.train('LB', 1, 1, out, [0, 1], harm_steps=[1], dev=wrong), 'not the skills DEV in_dist')
        assert not os.path.exists(out)
        # a stale parent-hits cache for another DEV file / parent is refused, not paired against
        from domain import harm
        real = harm.in_dist_hits
        harm.in_dist_hits = lambda c, rows: ([1] * len(rows), 1.0)
        try:
            LP.make_harm_fn('p', wrong, td, dev_any=True)
            other = os.path.join(td, 'other.jsonl')
            write_dev(other, n=4)
            raises(lambda: LP.make_harm_fn('p', other, td, dev_any=True), 'refusing to pair')
            raises(lambda: LP.make_harm_fn('q', wrong, td, dev_any=True), 'refusing to pair')
        finally:
            harm.in_dist_hits = real
    if not os.path.exists(REAL_DEV):
        return f'wrong file refused, --dev-any accepted and recorded unchecked; real DEV accept SKIPPED: {REAL_DEV} absent'
    sha, checked = LP.dev_provenance(REAL_DEV)
    assert sha == LP.DEV_IN_DIST_SHA256 and checked is True
    return f'wrong file refused (also at train() entry and make_harm_fn), --dev-any accepted unchecked, stale caches refused; real DEV {REAL_DEV} accepted (sha {sha[:12]})'


def test_replay_arm_setup():
    vocab, rows, batch = mixed_batch(3, 2)
    from domain.mode import make_opt
    real_guarded = LP.Guarded

    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError('the replay arm must not build a Guarded wrapper')
    LP.Guarded = Boom
    try:
        kinds = ['ce']
        if os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
            kinds.append('kl')
        out = []
        for kind in kinds:
            m = tool(vocab)
            plain_loss_fn = m.__dict__.get('loss')
            log = []
            klreplay = LP.load_klreplay(GUARD_SRC) if kind == 'kl' else None
            ref = make_opt(tool(vocab), 3e-4)
            opt, params = LP.setup_replay_arm(m, {'lr': 3e-4}, make_opt, kind, 10.0, log, klreplay)
            assert plain_loss_fn is None and 'loss' in m.__dict__, 'm.loss is replaced on the instance'
            n_all = len(list(m.parameters()))
            assert len(params) == n_all and all(p.requires_grad for p in m.parameters()), 'nothing frozen'
            assert type(opt) is type(ref) and opt.defaults == ref.defaults, 'the unguarded LB optimizer'
            assert [len(g['params']) for g in opt.param_groups] == [len(g['params']) for g in ref.param_groups]
            assert sum(len(g['params']) for g in opt.param_groups) == n_all
            assert [g['weight_decay'] for g in opt.param_groups] == [g['weight_decay'] for g in ref.param_groups]
            assert not hasattr(opt, 'kf') and type(opt).__name__ == 'AdamW'
            o = m.loss(batch)
            assert len(log) == 1 and 'replay_' + kind in o[1], (kind, log)
            o[0].backward()
            opt.step()
            out.append(f'{kind}: {n_all} params all trainable, AdamW groups as make_opt, loss logs {log[0]:.4f}')
    finally:
        LP.Guarded = real_guarded
    return '; '.join(out) + ('' if 'kl' in kinds else '; kl SKIPPED: no guard source')


def test_big_dev_provenance():
    """--harm-dev-big must contain the checked main DEV: its raw lines for the main DEV's ids, in the main DEV's order, hash to the main
    DEV's sha256 (train() checks it before any work, make_harm_fn again)."""
    assert LP.big_dev_provenance
    with tempfile.TemporaryDirectory() as td:
        dev = os.path.join(td, 'dev.jsonl')
        write_dev(dev)
        lines = open(dev).read().splitlines()
        want = LP.file_sha256(dev)
        extra = [json.dumps({'id': f'y{i}', 'family': 'arith_bare', 'prompt': f'{i}*2', 'answer': str(2 * i), 'accepted': [str(2 * i)], 'level': 1}) for i in range(4)]

        def big(name, ls):
            path = os.path.join(td, name)
            open(path, 'w').write(''.join(l + '\n' for l in ls))
            return path
        ok = big('ok.jsonl', lines[:3] + extra[:2] + lines[3:] + extra[2:])   # a superset: extra rows anywhere
        assert LP.big_dev_provenance(ok, dev, expected=want) == (LP.file_sha256(ok), True)
        shuffled = big('shuf.jsonl', extra + lines[::-1])   # order in the big file does not matter: the main DEV's order is used
        assert LP.big_dev_provenance(shuffled, dev, expected=want)[1] is True
        changed = big('changed.jsonl', [lines[0].replace('0+1', '0+9')] + lines[1:] + extra)   # same ids, other content
        raises(lambda: LP.big_dev_provenance(changed, dev, expected=want), 'does not contain the skills DEV')
        raises(lambda: LP.big_dev_provenance(big('short.jsonl', lines[:-1] + extra), dev, expected=want), 'lack 1 of them')
        raises(lambda: LP.big_dev_provenance(os.path.join(td, 'nope.jsonl'), dev, expected=want), 'not found')
        assert LP.big_dev_provenance(changed, dev, dev_any=True, expected=want) == (LP.file_sha256(changed), False)
        # train() refuses a bad / missing big DEV before any work (dev_any only waives the content check, not the missing file)
        out = os.path.join(td, 'run')
        raises(lambda: LP.train('LB', 1, 1, out, [0, 1], harm_steps=[1], dev=dev, dev_any=True, harm_dev_big=os.path.join(td, 'nope.jsonl')), 'not found')
        assert not os.path.exists(out)
        # and make_harm_fn records the flag on harm_big
        from domain import harm
        real = harm.in_dist_hits
        harm.in_dist_hits = lambda c, rows: ([1] * len(rows), 1.0)
        try:
            fn = LP.make_harm_fn('p', dev, td, dev_any=True, dev_big=ok)
            assert fn('c', 1)['harm_big']['dev_sha256_checked'] is False
        finally:
            harm.in_dist_hits = real
    if not (os.path.exists(REAL_BIG) and os.path.exists(REAL_DEV)):
        return 'content check on synthetic files; real big DEV SKIPPED: files absent'
    sha, checked = LP.big_dev_provenance(REAL_BIG, REAL_DEV)
    assert checked is True
    return f'superset accepted in any order, changed content / missing ids / missing file refused, --dev-any records unchecked; real big DEV accepted (sha {sha[:12]})'


def test_diary_train_pin():
    """A rebuilt diary refuses a train.jsonl that is not the seed-1 build (before anything else is read); --diary-any waives it."""
    assert LP.DIARY_TRAIN_SHA256 == '010af67124544bda9d4f26d8bd2801427770f1bb38f8c7b79921a36c87b244f5'
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, 'train.jsonl'), 'w').write(json.dumps({'prompt': '1+1'}) + '\n')
        raises(lambda: LP.build_parent_diary(None, None, td, td, data=td, log_path='none'), 'diary pool')
        try:
            LP.build_parent_diary(None, None, td, td, data=td, log_path='none', data_any=True)   # passes the pin, then needs the guard constants
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('data_any should get past the pin')
    ns = run_main(['train', '--arm', 'LB', '--out', 'x', '--diary-any'])
    assert ns['diary_any'] is True and run_main(['train', '--arm', 'LB', '--out', 'x'])['diary_any'] is False
    if not os.path.exists(REAL_TRAIN):
        return 'pin enforced, --diary-any waives it; real train.jsonl accept SKIPPED: file absent'
    assert LP.file_sha256(REAL_TRAIN) == LP.DIARY_TRAIN_SHA256
    return f'rebuild refused for another train file, --diary-any waives; real {REAL_TRAIN} matches the pin'


def test_train_harm_leaves_training_untouched():
    """train() end to end (3 updates, scoring stubbed to a parameter hash): the model after every update is bit-identical with harm off
    and with harm on at every step, with an in_dist_hits stub that seeds and draws from every RNG - for --guard none, the replay arm
    (ce; kl too when the guard source is there), and kfsoft (when the guard source is there).
    Measured: with the isolation removed this test still passes - the shipped tool parent draws nothing from the global torch / random /
    numpy streams during training (ans_drill 0.25 draws from the model's private _drill_rng, not the global streams; own batch-order seed) - so it guards the wiring (use_replay / rlog / ex() / harm hooks leave
    the update stream alone); the RNG sensitivity itself is test_rng_isolation's job."""
    if not all(os.path.exists(x) for x in (PARENT, PROBE, os.path.join(FAR, 'train-rows-l5.jsonl'), os.path.join(FAR, 'eval-rows-l5.jsonl'))):
        skip(f'parent / far-transfer rows absent ({PARENT})')
    from domain import harm
    real_hits, real_score = harm.in_dist_hits, LP.score_step

    def noisy(ckpt, rows):
        torch.manual_seed(12345); torch.rand(7); random.seed(99); random.random(); np.random.seed(7); np.random.rand(5)
        return [1] * len(rows), 1.0

    def param_hash(m):
        h = hashlib.sha256()
        for k, v in m.state_dict().items():
            h.update(k.encode())
            h.update(v.detach().numpy().tobytes())
        return h.hexdigest()

    def run(td, tag, harm_on, **kw):
        seen = {}

        def stub(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False):
            seen[step] = param_hash(m)
            if harm_fn is not None:
                seen[f'harm{step}'] = harm_fn('child', step)['n']
        LP.score_step = stub
        harm.in_dist_hits = noisy
        try:
            LP.train('LB', 3, 1, os.path.join(td, tag), [0, 1, 3], parent=PARENT, train_path=os.path.join(FAR, 'train-rows-l5.jsonl'), cells='l5',
                     eval_rows=os.path.join(FAR, 'eval-rows-l5.jsonl'), probe=PROBE, log_every=1, harm_steps=[1, 3] if harm_on else [], dev=dev, dev_any=True,
                     diary_compare='none', **kw)
        finally:
            LP.score_step, harm.in_dist_hits = real_score, real_hits
        return seen

    arms = [('none', {})]
    with tempfile.TemporaryDirectory() as td:
        dev = os.path.join(td, 'dev.jsonl')
        write_dev(dev)
        diary = os.path.join(td, 'diary.jsonl')
        with open(os.path.join(FAR, 'train-rows-l5.jsonl')) as f, open(diary, 'w') as g:   # a small diary pool: the cache path, no parent-answer build
            for i, line in zip(range(24), f):
                r = json.loads(line)
                g.write(json.dumps(dict(r, source='diary', accepted=[r['answer']], steps=[], family='diary')) + '\n')
        have_src = os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain'))
        arms.append(('replay-ce', dict(guard='replay', replay_loss='ce', guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=2.0)))
        if have_src:
            arms.append(('replay-kl', dict(guard='replay', replay_loss='kl', guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=2.0)))
            arms.append(('kfsoft', dict(guard='kfsoft', guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=2.0)))
        for name, kw in arms:
            off = run(td, name + '-off', False, **kw)
            on = run(td, name + '-on', True, **kw)
            assert set(off) == {0, 1, 3} and {0, 1, 3} <= set(on) and on['harm1'] == on['harm3'] == 6, (name, set(off), set(on))
            assert all(off[k] == on[k] for k in (0, 1, 3)), f'{name}: harm on moved the training stream'
            assert off[0] != off[3], f'{name}: the model did not train'
    return f'{len(arms)} arms ({", ".join(n for n, _ in arms)}): model hash after 0 / 1 / 3 updates identical with harm off and on (stub reseeds torch, random, numpy)' + ('' if have_src else '; kl / kfsoft SKIPPED: no guard source')


class StubKF:
    """kf stand-in so a real Guarded can be built without measuring anything: it freezes via the real gp.freeze_unprojected."""
    @staticmethod
    def kfac_stats(m, diary, norm='example'):
        return {}

    @staticmethod
    def factors(stats, energy, soft=None):
        return {}, {}

    class KFOptimizer:
        def __init__(self, m, base, F):
            self.base, self.param_groups = base, base.param_groups


def group_names(m, opt):
    idn = {id(p): n for n, p in m.named_parameters()}
    return [[idn[id(p)] for p in g['params']] for g in opt.param_groups]


def test_replay_freeze_setup():
    """A1F on the small test model: setup_replay_arm(..., freeze=gp.freeze_unprojected) freezes what a real Guarded freezes on an identical
    model, the optimizer groups and the clip set are the ones Guarded's make_base / trainable list give, and 3 AdamW steps (weight decay
    0.1 on) leave every frozen tensor bit-identical while every trainable one moves; the same 3 steps with nothing frozen do move
    the tensors that would have been frozen (so the test can tell)."""
    if not os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
        skip(f'no guard source at {GUARD_SRC}')
    from domain.mode import make_opt
    _, gp = LP.load_guard(GUARD_SRC)
    vocab, rows, batch = mixed_batch(3, 2)
    lr = 3e-3
    kinds = ['ce', 'kl']
    out = []
    mg = tool(vocab)
    g = LP.Guarded(StubKF, gp, mg, [], 0.99, lambda: make_opt(mg, lr))
    want_frozen = sorted(n for n, p in mg.named_parameters() if not p.requires_grad)
    assert sorted(g.frozen) == want_frozen and 0 < len(want_frozen) < len(list(mg.parameters())), (len(g.frozen), len(want_frozen))
    want_groups = group_names(mg, g.base)
    want_clip = [n for n, p in mg.named_parameters() if p.requires_grad]
    m = tool(vocab)   # control: the same steps with nothing frozen move the would-be-frozen tensors
    opt, params = LP.setup_replay_arm(m, {'lr': lr}, make_opt, 'ce', 10.0, [], None)
    before = {n: p.detach().clone() for n, p in m.named_parameters()}
    for _ in range(3):
        o = m.loss(batch)
        o[0].backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
    moved_ctl = {n for n, p in m.named_parameters() if not torch.equal(before[n], p.detach())}   # structurally dead biases (zero gradient) stay put even unfrozen
    moved = sorted(moved_ctl & set(want_frozen))
    assert moved, 'control: with nothing frozen the would-be-frozen tensors should move'
    for kind in kinds:
        m = tool(vocab)
        log = []
        klreplay = LP.load_klreplay(GUARD_SRC) if kind == 'kl' else None
        opt, params = LP.setup_replay_arm(m, {'lr': lr}, make_opt, kind, 10.0, log, klreplay, gp.freeze_unprojected)
        frozen = sorted(n for n, p in m.named_parameters() if not p.requires_grad)
        assert frozen == want_frozen, (kind, len(frozen), len(want_frozen))
        assert group_names(m, opt) == want_groups, 'optimizer groups differ from Guarded\'s make_base'
        assert [n for n, p in m.named_parameters() if any(p is q for q in params)] == want_clip and len(params) == len(want_clip), 'clip set'
        assert type(opt).__name__ == 'AdamW' and not hasattr(opt, 'kf') and [g_['weight_decay'] for g_ in opt.param_groups] == [0.1, 0.0]
        before = {n: p.detach().clone() for n, p in m.named_parameters()}
        for _ in range(3):
            m.train()
            o = m.loss(batch)
            o[0].backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
        now = dict(m.named_parameters())
        assert all(torch.equal(before[n], now[n].detach()) for n in frozen), [n for n in frozen if not torch.equal(before[n], now[n].detach())]
        assert all(now[n].grad is None for n in frozen)
        still = {n for n in want_clip if torch.equal(before[n], now[n].detach())}
        assert still == set(want_clip) - moved_ctl, f'{kind}: trainable tensors that did not move: {sorted(still)} (control: {sorted(set(want_clip) - moved_ctl)})'
        out.append(f'{kind}: {len(frozen)} frozen tensors == Guarded\'s, {len(want_clip) - len(still)} of {len(want_clip)} trainable moved (the {len(still)} that did not move have zero gradient in the nothing-frozen control too), frozen bit-identical')
    return '; '.join(out) + f'; groups and clip set equal Guarded\'s; control (nothing frozen) moves {len(moved)} of those {len(want_frozen)}'


def test_replay_freeze_real_parent_count():
    """On the real s200 parent the guard freezes 41 of 101 tensors; --replay-freeze freezes the same 41 (the same names)."""
    if not (os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')) and os.path.exists(PARENT)):
        skip(f'guard source / parent absent ({GUARD_SRC}, {PARENT})')
    from custom_io.models import load_model
    from domain.mode import make_opt
    _, gp = LP.load_guard(GUARD_SRC)
    mg = load_model(PARENT)
    g = LP.Guarded(StubKF, gp, mg, [], 0.99, lambda: make_opt(mg, 3e-4))
    m = load_model(PARENT).eval()
    opt, params = LP.setup_replay_arm(m, {'lr': 3e-4}, make_opt, 'ce', 10.0, [], None, gp.freeze_unprojected)
    frozen = sorted(n for n, p in m.named_parameters() if not p.requires_grad)
    n_all = len(list(m.parameters()))
    assert len(frozen) == len(g.frozen) == 41 and frozen == sorted(g.frozen) and n_all == 101 and len(params) == 60, (len(frozen), len(g.frozen), n_all)
    assert group_names(m, opt) == group_names(mg, g.base)
    return f'real parent: {len(frozen)} of {n_all} tensors frozen, the same names as Guarded\'s; {len(params)} trainable; optimizer groups equal'


def test_stop_if_drop_parse_and_decision():
    ok = LP.parse_stop_if_drop('1000:3.0,2000:3.0', [500, 1000, 2000, 4000])
    assert ok == {1000: 3.0, 2000: 3.0} and all(isinstance(k, int) and isinstance(v, float) for k, v in ok.items()), ok
    assert LP.parse_stop_if_drop('10:50') == {10: 50.0} and LP.parse_stop_if_drop('10:50', [10]) == {10: 50.0}
    assert LP.parse_stop_if_drop(None, [10]) is None
    bad = [('1000', "wants 'STEP:DROP"), ('1000:x', "wants 'STEP:DROP"), (':3', "wants 'STEP:DROP"), ('', "wants 'STEP:DROP"), ('1000:3:4', "wants 'STEP:DROP"),
           ('1000:3.0,', "wants 'STEP:DROP"), ('1000:0', 'DROP must be a number > 0'), ('1000:-1', 'DROP must be a number > 0'),
           ('1000:nan', 'DROP must be a number > 0'), ('1000:inf', 'DROP must be a number > 0'), ('1000:3,1000:4', 'step 1000 twice')]
    for spec, needle in bad:
        raises(lambda: LP.parse_stop_if_drop(spec, [1000]), needle)
    raises(lambda: LP.parse_stop_if_drop('3000:3.0', [500, 1000]), 'are not harm steps')
    raises(lambda: LP.parse_stop_if_drop('1000:3.0,3000:3.0', [500, 1000]), '[3000] are not harm steps')
    raises(lambda: LP.parse_stop_if_drop('1000:3.0', []), 'are not harm steps')   # --no-harm
    lim = {1000: 3.0, 2000: 3.0}
    assert LP.futility_stop(lim, 1000, {'in_dist_drop': 3.0}) == {'step': 1000, 'drop': 3.0, 'limit': 3.0}   # >=: the boundary stops
    assert LP.futility_stop(lim, 2000, {'in_dist_drop': 41.5}) == {'step': 2000, 'drop': 41.5, 'limit': 3.0}
    assert LP.futility_stop(lim, 1000, {'in_dist_drop': 2.99}) is None
    assert LP.futility_stop(lim, 1000, {'in_dist_drop': -5.0}) is None
    assert LP.futility_stop(lim, 4000, {'in_dist_drop': 90.0}) is None   # no limit at that step
    assert LP.futility_stop(lim, 1000, None) is None and LP.futility_stop(None, 1000, {'in_dist_drop': 90.0}) is None and LP.futility_stop({}, 1000, {'in_dist_drop': 90.0}) is None
    r = run_main(['train', '--arm', 'LB', '--out', 'x', '--steps', '0,1000,2000', '--stop-if-drop', '1000:3.0,2000:3.0'])
    assert r['stop_if_drop'] == {1000: 3.0, 2000: 3.0} and r['harm_steps'] == [1000, 2000], r
    assert run_main(['train', '--arm', 'LB', '--out', 'x'])['stop_if_drop'] is None
    raises(lambda: run_main(['train', '--arm', 'LB', '--out', 'x', '--steps', '0,1000', '--stop-if-drop', '2000:3.0']), 'are not harm steps')
    raises(lambda: run_main(['train', '--arm', 'LB', '--out', 'x', '--steps', '0,1000', '--no-harm', '--stop-if-drop', '1000:3.0']), 'are not harm steps')
    raises(lambda: run_main(['train', '--arm', 'LB', '--out', 'x', '--steps', '0,1000', '--harm-steps', '1000', '--stop-if-drop', '1000:zero']), "wants 'STEP:DROP")
    return f'{len(bad) + 3} bad specs refused with their own message; boundary drop == limit stops, 2.99 < 3.0 does not; no limit / no harm / no spec -> no stop; main() parses 1000:3.0,2000:3.0 and refuses non-harm steps'


def test_score_step_futility_record():
    """The real score_step (scorer and checkpoint writer stubbed): the step's record carries futility_stop and the return value is the stop
    when the harm drop reaches the limit; below the limit, at a step with no limit, and with no limits set, the record has no such key and
    the return is None - and every other field of the record is the same in all four."""
    import domain.mode as DM
    import domain.score as DS
    real = DM.save_ckpt, DS.score

    def save(ck, m, path, addon):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w').write('x')
    DM.save_ckpt, DS.score = save, lambda path, rows, name: {'rows': [{'id': r['id'], 'hit': 1} for r in rows]}
    sets = {'S': [{'id': 'a'}, {'id': 'b'}]}
    harm = lambda d: (lambda path, step: {'in_dist_a': 80.0, 'in_dist_b': 80.0 - d, 'in_dist_drop': d, 'n': 2, 'harm_big': {'in_dist_drop': 99.0}})
    try:
        with tempfile.TemporaryDirectory() as td:
            res = {}
            for tag, step, drop, lim in (('hit', 1000, 3.0, {1000: 3.0}), ('under', 1000, 2.99, {1000: 3.0}), ('nolimit', 500, 90.0, {1000: 3.0}), ('off', 1000, 90.0, None)):
                out = os.path.join(td, tag)
                os.makedirs(out)
                r = LP.score_step({}, torch.nn.Linear(1, 1), None, sets, out, 'LB', step, 0.0, 1, {'k': 1}, harm(drop), False, **({} if lim is None else {'stop_limits': lim}))
                recs = [json.loads(x) for x in open(os.path.join(out, 'scores.jsonl'))]
                assert len(recs) == 1 and not os.path.exists(os.path.join(out, f'step_{step}')), tag
                res[tag] = (r, recs[0])
            assert res['hit'][0] == {'step': 1000, 'drop': 3.0, 'limit': 3.0} and res['hit'][1]['futility_stop'] == res['hit'][0]
            for tag in ('under', 'nolimit', 'off'):
                assert res[tag][0] is None and 'futility_stop' not in res[tag][1], tag
            for tag, kf, keep, lim, drop, kept in (('stopkeep', True, False, {1000: 3.0}, 3.0, True), ('stopnokeep', False, False, {1000: 3.0}, 3.0, False),
                                                  ('nostopkeep', True, False, {1000: 3.0}, 2.0, False), ('lastkeep', True, True, {1000: 3.0}, 2.0, True)):
                out = os.path.join(td, tag)
                os.makedirs(out)
                LP.score_step({}, torch.nn.Linear(1, 1), None, sets, out, 'LB', 1000, 0.0, 1, {'k': 1}, harm(drop), keep, stop_limits=lim, keep_final=kf)
                assert os.path.exists(os.path.join(out, 'step_1000', 'checkpoint.pt')) == kept, tag   # --keep-final keeps the step a futility stop ends the run at
            strip = lambda r: {k: v for k, v in r.items() if k not in ('futility_stop', 'secs', 'harm', 'step')}
            assert len({json.dumps(strip(v[1]), sort_keys=True) for v in res.values()}) == 1 and res['hit'][1]['harm_big'] == {'in_dist_drop': 99.0}
    finally:
        DM.save_ckpt, DS.score = real
    return 'futility_stop rides on the stopping step\'s record only (value == the return); under / no-limit / no-limits-set: no key, return None, other fields identical; a stop with keep_final keeps its checkpoint, without keep_final / without a stop / not last it is deleted'


def test_train_a1f_stop_and_commit_check():
    """train() end to end (2-3 updates, scoring stubbed to a parameter snapshot), real parent:
    (1) --replay-freeze (kl and ce): records replay_freeze true and guard_frozen 41 (= kfsoft's guard_frozen), the 41 tensors are bit-identical
        at the last step and the other 60 moved; the plain replay arms carry neither key;
    (2) guard_commit_check with --diary-cache: 'verified' on replay-kl and kfsoft, absent on replay-ce, none of the new keys on kfsoft;
    (3) --stop-if-drop: the stopping step is the last one scored and the last update run (clip calls counted), a drop under the limit runs on,
        and stop_if_drop is recorded only on the runs that set it."""
    if not all(os.path.exists(x) for x in (PARENT, PROBE, os.path.join(FAR, 'train-rows-l5.jsonl'), os.path.join(FAR, 'eval-rows-l5.jsonl'))) \
            or not os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
        skip('parent / far-transfer rows / guard source absent')
    from domain import harm
    real_hits, real_score, real_clip = harm.in_dist_hits, LP.score_step, torch.nn.utils.clip_grad_norm_
    clips = []
    FAKE = {1: 1.0, 2: 4.0, 3: 9.0}

    def run(td, tag, steps, updates, harm_steps=(), stop=None, **kw):
        seen = {'calls': [], 'extra': {}, 'params': {}, 'stops': {}, 'keep': {}}
        clips.clear()

        def stub(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False, stop_limits=None, keep_final=False):
            seen['calls'].append(step)
            seen['keep'][step] = (keep, keep_final)
            seen['extra'][step] = dict(extra)
            seen['params'][step] = {n: p.detach().clone() for n, p in m.named_parameters()}
            seen['req'] = {n: p.requires_grad for n, p in m.named_parameters()}
            r = LP.futility_stop(stop_limits, step, {'in_dist_drop': FAKE[step]} if step in harm_steps else None)
            seen['stops'][step] = r
            return r
        LP.score_step = stub
        harm.in_dist_hits = lambda ckpt, rows: ([1] * len(rows), 1.0)
        torch.nn.utils.clip_grad_norm_ = lambda *a, **k: (clips.append(1), real_clip(*a, **k))[1]
        try:
            LP.train('LB', updates, 1, os.path.join(td, tag), steps, parent=PARENT, train_path=os.path.join(FAR, 'train-rows-l5.jsonl'), cells='l5',
                     eval_rows=os.path.join(FAR, 'eval-rows-l5.jsonl'), probe=PROBE, log_every=1, harm_steps=list(harm_steps), dev=dev, dev_any=True,
                     diary_compare='none', stop_if_drop=stop, **kw)
        finally:
            LP.score_step, harm.in_dist_hits, torch.nn.utils.clip_grad_norm_ = real_score, real_hits, real_clip
        seen['clips'] = len(clips)
        return seen

    with tempfile.TemporaryDirectory() as td:
        dev = os.path.join(td, 'dev.jsonl')
        write_dev(dev)
        diary = os.path.join(td, 'diary.jsonl')
        with open(os.path.join(FAR, 'train-rows-l5.jsonl')) as f, open(diary, 'w') as g:
            for i, line in zip(range(24), f):
                r = json.loads(line)
                g.write(json.dumps(dict(r, source='diary', accepted=[r['answer']], steps=[], family='diary')) + '\n')
        rk = dict(guard='replay', guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=2.0)
        res = {}
        for name, kw in (('kl', dict(rk, replay_loss='kl')), ('ce', dict(rk, replay_loss='ce')), ('kl-freeze', dict(rk, replay_loss='kl', replay_freeze=True)),
                         ('ce-freeze', dict(rk, replay_loss='ce', replay_freeze=True)), ('kfsoft', dict(guard='kfsoft', guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=2.0))):
            res[name] = run(td, name, [0, 2], 2, **kw)
            assert res[name]['calls'] == [0, 2] and res[name]['clips'] == 2, name
        ex = {k: v['extra'][2] for k, v in res.items()}
        # (2) commit check
        for k in ('kl', 'kfsoft', 'kl-freeze', 'ce-freeze'):
            assert ex[k]['guard_commit_check'] == 'verified', (k, ex[k].get('guard_commit_check', 'ABSENT'))
        assert 'guard_commit_check' not in ex['ce'], 'replay-ce records no commit check (shipped record unchanged)'
        for k in ('kl', 'kl-freeze', 'ce-freeze', 'kfsoft'):   # which commit the check was against: A1F vs L11 shows one gp.freeze_unprojected source
            assert ex[k]['guard_src_commit'] == LP.GUARD_COMMIT_SOFT, k
        assert 'guard_src_commit' not in ex['ce']
        # (1) A1F
        for k in ('kl', 'ce', 'kfsoft'):
            assert 'replay_freeze' not in ex[k] and 'stop_if_drop' not in ex[k], k
        assert 'guard_frozen' not in ex['kl'] and 'guard_frozen' not in ex['ce']
        n_moved = {}
        for k in ('kl-freeze', 'ce-freeze'):
            assert ex[k]['replay_freeze'] is True and ex[k]['guard_frozen'] == 41 == ex['kfsoft']['guard_frozen'] and ex[k]['guard'] == 'replay', k
            p0, p2, req = res[k]['params'][0], res[k]['params'][2], res[k]['req']
            frozen = [n for n in p0 if not req[n]]
            assert len(frozen) == 41 and all(torch.equal(p0[n], p2[n]) for n in frozen), k
            plain = res[k.split('-')[0]]['params']   # the same replay loss with nothing frozen: tensors with a zero gradient do not move there either
            moved = {n for n in p0 if req[n] and not torch.equal(p0[n], p2[n])}
            assert moved == {n for n in p0 if n not in frozen and not torch.equal(plain[0][n], plain[2][n])} and len(moved) >= 55, (k, len(moved), sorted(set(p0) - set(frozen) - moved))
            n_moved[k] = len(moved)
        for k in ('kl', 'ce'):   # unfrozen replay: everything trainable
            assert all(res[k]['req'].values())
        # (3) futility stop
        hs = (1, 2, 3)
        a = run(td, 'stop', [0, 1, 2, 3], 3, hs, {2: 4.0})
        assert a['calls'] == [0, 1, 2] and a['clips'] == 2 and a['stops'][2] == {'step': 2, 'drop': 4.0, 'limit': 4.0} and a['stops'][1] is None, a['calls']
        assert a['extra'][1]['stop_if_drop'] == {'2': 4.0}
        b = run(td, 'nostop', [0, 1, 2, 3], 3, hs, {2: 4.1})
        assert b['calls'] == [0, 1, 2, 3] and b['clips'] == 3 and all(v is None for v in b['stops'].values())
        c = run(td, 'nolimit', [0, 1, 2, 3], 3, hs, None)
        assert c['calls'] == [0, 1, 2, 3] and c['clips'] == 3 and 'stop_if_drop' not in c['extra'][3]
        assert all(torch.equal(a['params'][2][n], b['params'][2][n]) and torch.equal(b['params'][3][n], c['params'][3][n]) for n in a['params'][2]), 'stopping changes nothing before the stop'
        d = run(td, 'stopkeep', [0, 1, 2, 3], 3, hs, {2: 4.0}, keep_final=True)
        assert d['calls'] == [0, 1, 2] and d['keep'] == {0: (False, True), 1: (False, True), 2: (False, True)}, d['keep']   # keep_final reaches score_step on a stop run: the stopped step is not the last, so keep is False
        assert a['keep'] == {0: (False, False), 1: (False, False), 2: (False, False)}, a['keep']
        e = run(td, 'nostopkeep', [0, 1, 2, 3], 3, hs, None, keep_final=True)
        assert e['keep'] == {0: (False, False), 1: (False, False), 2: (False, False), 3: (True, False)}, e['keep']   # no limits: the shipped call, last step keeps
        raises(lambda: run(td, 'badstop', [0, 1, 2, 3], 3, (1, 2, 3), {5: 1.0}), 'are not harm steps')
    return (f'A1F kl/ce: replay_freeze true, guard_frozen 41 (= kfsoft\'s), 41 bit-identical / {n_moved['ce-freeze']} of the 60 others moved (the rest have zero gradient unfrozen too); commit check verified on replay-kl, kfsoft, A1F and absent on replay-ce; '
            f'stop at step 2 of 3: scored [0,1,2], 2 updates; limit 4.1 runs all 3; pre-stop weights identical')


def test_a1f_is_one_change_vs_l11():
    """The A1F claim: against L11 (kfsoft, soft 1 + KL) it is ONE change, the K-FAC projection. train() end to end (4 updates, scoring stubbed
    to a state_dict hash at steps 0 / 2 / 4), real parent, the same small diary pool and seeds: A1F (replay kl + --replay-freeze) vs kfsoft whose
    LP.load_guard is patched to a kf with the REAL kfac_stats / factors (so the diary is measured, the freeze and the clip set are Guarded's, and
    --guard-every 2 makes it re-measure once) but a KFOptimizer.step that only calls base.step() (no projection). The hashes must be equal at every
    scored step: the diary draw, the parent copy timing, the freeze order, the clip set, the optimizer groups, the weight decay and the RNG streams
    are all shared, so a change to either path that is not the projection (nor the mask, which only feeds it) fails here."""
    if not all(os.path.exists(x) for x in (PARENT, PROBE, os.path.join(FAR, 'train-rows-l5.jsonl'), os.path.join(FAR, 'eval-rows-l5.jsonl'))) \
            or not os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
        skip('parent / far-transfer rows / guard source absent')
    real_load, real_score = LP.load_guard, LP.score_step
    real_kf, gp = real_load(GUARD_SRC)

    class PassKF:
        kfac_stats = staticmethod(real_kf.kfac_stats)
        factors = staticmethod(real_kf.factors)

        class KFOptimizer:
            def __init__(self, m, base, F):
                self.base, self.param_groups = base, base.param_groups

            def step(self):
                self.base.step()

            def zero_grad(self, set_to_none=True):
                self.base.zero_grad(set_to_none=set_to_none)

    def run(td, tag, **kw):
        seen = {'hash': {}, 'extra': {}}

        def stub(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False, stop_limits=None, keep_final=False):
            h = hashlib.sha256()
            for k, v in m.state_dict().items():
                h.update(k.encode())
                h.update(v.detach().numpy().tobytes())
            seen['hash'][step], seen['extra'][step] = h.hexdigest(), dict(extra)
        LP.score_step = stub
        try:
            LP.train('LB', 4, 1, os.path.join(td, tag), [0, 2, 4], parent=PARENT, train_path=os.path.join(FAR, 'train-rows-l5.jsonl'), cells='l5',
                     eval_rows=os.path.join(FAR, 'eval-rows-l5.jsonl'), probe=PROBE, log_every=1, harm_steps=[], diary_compare='none', **kw)
        finally:
            LP.score_step = real_score
        return seen

    with tempfile.TemporaryDirectory() as td:
        diary = os.path.join(td, 'diary.jsonl')
        with open(os.path.join(FAR, 'train-rows-l5.jsonl')) as f, open(diary, 'w') as g:
            for i, line in zip(range(24), f):
                r = json.loads(line)
                g.write(json.dumps(dict(r, source='diary', accepted=[r['answer']], steps=[], family='diary')) + '\n')
        common = dict(guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=10.0)
        a1f = run(td, 'a1f', guard='replay', replay_loss='kl', replay_freeze=True, **common)
        LP.load_guard = lambda src: (PassKF, gp)
        try:
            l11 = run(td, 'l11', guard='kfsoft', guard_every=2, **common)
        finally:
            LP.load_guard = real_load
        assert l11['extra'][4]['measures'] == 2, l11['extra'][4]   # the initial measure and the one after update 2
        assert a1f['hash'][0] == l11['hash'][0] and a1f['hash'][0] != a1f['hash'][4]
        for st in (2, 4):
            assert a1f['hash'][st] == l11['hash'][st], f'A1F and L11 (projection off) differ at step {st}'
        for k in ('guard_frozen', 'guard_commit_check', 'guard_src_commit', 'guard_diary_sha256', 'kl_replay_rows', 'kl_weight', 'kl_replay_seed', 'kl_replay_pool'):
            assert a1f['extra'][4][k] == l11['extra'][4][k], k
        assert 'replay_kl_mean' in a1f['extra'][4] and 'replay_kl_mean' not in l11['extra'][4]   # record-only difference: the replay arm logs the running KL mean on each step, kfsoft only at the end
    return 'A1F vs kfsoft with a pass-through KFOptimizer (real kfac_stats / factors, one re-measure): state_dict hashes equal at steps 0 / 2 / 4; guard_frozen, commit, diary sha, replay rows / weight / seed / pool equal on the records (record-only differences: A1F carries replay_kl_mean per step, kfsoft measure_secs / measures)'


def test_replay_priority_probs():
    """--replay-priority: replay_priority_probs sums to 1, is uniform when every KL is 0 (or frac 0), puts 0.5 + 0.5 * n_f / N on a family that
    has all the KL at frac 0.5, orders families by their KL, and replay_priority_shares adds the rows up per family."""
    fam = ['a'] * 6 + ['b'] * 3 + ['c'] * 1
    N = len(fam)
    P = lambda fam, kl, frac: LP.replay_priority_probs(fam, kl, frac, min_rows=1)   # these families are 1-6 rows: below the default floor
    p0 = P(fam, {'a': 0.0, 'b': 0.0, 'c': 0.0}, 0.5)
    assert p0.dtype == np.float64 and np.allclose(p0, 1.0 / N) and abs(p0.sum() - 1) < 1e-15, p0
    assert np.allclose(P(fam, {}, 0.9), 1.0 / N), 'no KL given: uniform'
    assert np.allclose(P(fam, {'a': 1.0, 'b': 2.0, 'c': 3.0}, 0.0), 1.0 / N), 'frac 0: uniform'
    p = P(fam, {'a': 0.0, 'b': 1.5, 'c': 0.0}, 0.5)
    assert abs(p.sum() - 1) < 1e-12 and (p > 0).all()
    sh = LP.replay_priority_shares(fam, p)
    assert abs(sh['b'] - (0.5 + 0.5 * 3 / N)) < 1e-4 and abs(sh['a'] - 0.5 * 6 / N) < 1e-4 and abs(sh['c'] - 0.5 * 1 / N) < 1e-4, sh
    assert list(sh)[0] == 'b' and abs(sum(sh.values()) - 1) < 1e-3
    q = P(fam, {'a': 1.0, 'b': 2.0, 'c': 4.0}, 0.8)   # per-row mass follows (kl_f / S) / n_f
    S = 7.0
    for f, kl in (('a', 1.0), ('b', 2.0), ('c', 4.0)):
        row = [i for i, x in enumerate(fam) if x == f][0]
        assert abs(q[row] - (0.2 / N + 0.8 * (kl / S) / fam.count(f))) < 1e-12, f
    sq = LP.replay_priority_shares(fam, q)
    assert abs(sq['a'] - (0.2 * 6 / N + 0.8 * 1 / 7)) < 1e-4 and abs(sq['c'] - (0.2 / N + 0.8 * 4 / 7)) < 1e-4
    assert sq['c'] > sq['b'] > sq['a'], sq   # shares follow the KL here (the 6-row family has the least KL)
    r = P(['x', 'y'], {'x': 1.0, 'y': 2.0}, 0.6)   # equal row counts: the order of the probabilities is the order of the KLs
    assert r[1] > r[0] and abs(r.sum() - 1) < 1e-15
    # a NaN / inf / negative KL counts 0 (finite, sums to 1); all bad -> uniform; never a NaN probability
    for bad in (float('nan'), float('inf'), -1.0):
        z = P(fam, {'a': bad, 'b': 1.5, 'c': 0.0}, 0.5)
        assert np.isfinite(z).all() and abs(z.sum() - 1) < 1e-12 and np.allclose(z, p), (bad, z)
        assert np.allclose(P(fam, {'a': bad, 'b': bad, 'c': bad}, 0.5), 1.0 / N), bad
    rs = np.random.RandomState(0).choice(N, size=5, p=P(fam, {'a': float('nan'), 'b': float('nan'), 'c': float('nan')}, 0.5))   # what crashed before
    assert len(rs) == 5
    # the default floor: a family under REPLAY_PRIORITY_MIN_ROWS rows gets no priority mass, however large its KL
    big = ['a'] * 20 + ['tiny'] * 2
    d = LP.replay_priority_probs(big, {'a': 1.0, 'tiny': 100.0}, 0.5)
    assert LP.replay_priority_weights(big, {'a': 1.0, 'tiny': 100.0}) == {'a': 1.0, 'tiny': 0.0}
    assert LP.replay_priority_weights(big, {'a': float('nan'), 'tiny': 1.0}) == {'a': 0.0, 'tiny': 0.0}
    assert LP.REPLAY_PRIORITY_MIN_ROWS == 8 and abs(d[-1] - 0.5 / 22) < 1e-12 and abs(d[0] - (0.5 / 22 + 0.5 / 20)) < 1e-12, d
    return 'sums to 1; uniform for KL 0 / empty / frac 0; one family with all the KL at frac 0.5 gets 0.5 + 0.5 n_f/N; per-row mass = (1-f)/N + f (kl_f/S)/n_f; order follows the KL; NaN/inf/negative KL counts 0 (no NaN p, choice works); families under 8 rows get no priority mass'


def test_replay_priority_check_guard_args():
    with tempfile.TemporaryDirectory() as src:
        kw = dict(arm='LB', guard_src=src, kl_rows=32, kl_weight=10.0)
        for g, extra in (('kfsoft', {}), ('replay', {}), ('replay', dict(replay_loss='kl'))):
            LP.check_guard_args(guard=g, replay_priority=0.5, replay_priority_every=100, **kw, **extra)
            LP.check_guard_args(guard=g, replay_priority=0.0, **kw, **extra)
        LP.check_guard_args(guard='replay', replay_priority=0.999, **kw)
        for bad_frac in (-0.1, 1.0, 1.5):
            raises(lambda: LP.check_guard_args(guard='kfsoft', replay_priority=bad_frac, **kw), '--replay-priority must be in [0, 1)')
            raises(lambda: LP.check_guard_args(arm='LB', guard=None, guard_src=None, replay_priority=bad_frac), '--replay-priority must be in [0, 1)')
        raises(lambda: LP.check_guard_args(arm='LB', guard=None, guard_src=None, replay_priority=0.5), '--replay-priority needs --guard kfsoft or --guard replay')
        raises(lambda: LP.check_guard_args(arm='LB', guard='kf', guard_src=src, replay_priority=0.5), '--replay-priority needs --guard kfsoft or --guard replay')
        raises(lambda: LP.check_guard_args(guard='replay', replay_loss='ce', replay_priority=0.5, **kw), '--replay-loss kl')
        raises(lambda: LP.check_guard_args(guard='kfsoft', replay_priority=0.5, replay_priority_every=0, **kw), '--replay-priority-every must be >= 1')
        # through main(): refused before train(); parsed otherwise; the default is off
        base = ['train', '--arm', 'LB', '--out', src, '--guard-src', src, '--kl-replay-rows', '32', '--kl-weight', '10']
        raises(lambda: run_main(base + ['--guard', 'kfsoft', '--replay-priority', '1.0']), '--replay-priority must be in [0, 1)')
        raises(lambda: run_main(base[:-4] + ['--replay-priority', '0.5']), '--replay-priority needs --guard kfsoft or --guard replay')
        raises(lambda: run_main(base + ['--guard', 'replay', '--replay-loss', 'ce', '--replay-priority', '0.5']), '--replay-loss kl')
        on = run_main(base + ['--guard', 'kfsoft', '--replay-priority', '0.5', '--replay-priority-every', '250'])
        off = run_main(base + ['--guard', 'kfsoft'])
    assert on['replay_priority'] == 0.5 and on['replay_priority_every'] == 250 and off['replay_priority'] == 0.0 and off['replay_priority_every'] == 500, (on, off)
    return 'frac outside [0,1), frac > 0 without kfsoft / replay, with replay-loss ce, every < 1 refused (also through main()); the default is 0.0 / 500'


def test_replay_priority_measure_isolated():
    """measure_family_kl with a mocked replay_kl that draws from torch, python random, numpy and the model's ans_drill stream: afterwards all four
    are where they were (the model stream too, which rng_isolated alone does not cover), the result is the batch-size-weighted mean per family over
    the first 128 rows in batches of 64, and it runs under no_grad."""
    from custom_io.data import CharVocab, Dataset
    _, rows, _, _ = build_batch(n_rows=5, n_calls=3)
    rows = [dict(r, source='diary') for r in rows]
    vocab = CharVocab.build(rows)
    ds = Dataset(rows, vocab)
    big = [ds[i % 5] for i in range(300)]   # 300 diary rows (items repeat): family 'a' 250 rows (cap 128 -> batches 64, 64), 'b' 50 rows (one batch of 50)
    fam = ['a'] * 250 + ['b'] * 50
    m = tool(vocab)
    m._drill_rng = random.Random('drill')
    calls = []

    class KR:
        @staticmethod
        def replay_kl(mm, parent, b):
            assert not torch.is_grad_enabled(), 'measure runs under no_grad'
            n = len(b['rows'])
            calls.append(n)
            torch.randn(3), random.random(), np.random.rand(), mm._drill_rng.random(); mm.drill_stats['rows'] += n
            return torch.tensor(0.5 if len(calls) <= 2 else 2.0), {}
    before, drill, stats = rng_state(), m._drill_rng.getstate(), dict(m.drill_stats)
    out = LP.measure_family_kl(m, None, KR, big, fam)
    assert same_state(before, rng_state()), 'global torch / python / numpy RNG moved'
    assert m._drill_rng.getstate() == drill and m.drill_stats == stats, "the model's ans_drill stream moved"
    assert calls == [64, 64, 50], calls
    assert abs(out['a'] - 0.5) < 1e-6 and abs(out['b'] - 2.0) < 1e-6 and list(out) == ['a', 'b'], out
    calls.clear()
    KR.replay_kl = staticmethod(lambda mm, parent, b: (calls.append(len(b['rows'])), (torch.tensor(1.0), {}))[1])
    out = LP.measure_family_kl(m, None, KR, big, fam, cap=70, bs=64)
    assert calls == [64, 6, 50] and out == {'a': 1.0, 'b': 1.0}, (calls, out)
    calls.clear()   # a family under min_rows is not measured (no tiny batches); a NaN KL comes back as measured
    KR.replay_kl = staticmethod(lambda mm, parent, b: (calls.append(len(b['rows'])), (torch.tensor(float('nan')), {}))[1])
    out = LP.measure_family_kl(m, None, KR, big[:257], fam[:250] + ['c'] * 7)
    assert calls == [64, 64] and list(out) == ['a'] and np.isnan(out['a']), (calls, out)
    return 'mocked replay_kl drew from torch / random / numpy / the model drill stream: all restored; batches 64+64 (cap 128) and 50, size-weighted mean; families under 8 rows skipped; NaN returned as measured'


def test_diary_families_real_lookup():
    """diary_families without a stub: labels by prompt from <data>/train.jsonl, the first row of a repeated prompt wins, the sha256 of
    that train.jsonl comes back; a diary row whose prompt is not there stops (SystemExit with the count); a missing train.jsonl stops."""
    with tempfile.TemporaryDirectory() as td:
        tr = [dict(prompt='p1', family='fa'), dict(prompt='p2', family='fb'), dict(prompt='p1', family='LATER'), dict(prompt='p3', family='fc')]
        with open(os.path.join(td, 'train.jsonl'), 'w') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in tr))
        want_sha = hashlib.sha256(open(os.path.join(td, 'train.jsonl'), 'rb').read()).hexdigest()
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fam, sha = LP.diary_families([dict(prompt='p2'), dict(prompt='p1'), dict(prompt='p1')], data=td)
        assert fam == ['fb', 'fa', 'fa'] and sha == want_sha, (fam, sha)
        assert '1 diary prompts appear' in buf.getvalue() and 'more than one family' in buf.getvalue(), buf.getvalue()
        raises(lambda: LP.diary_families([dict(prompt='p1'), dict(prompt='zz'), dict(prompt='yy')], data=td), '2 of 3 diary rows have no family')
        empty = os.path.join(td, 'nothing')
        os.mkdir(empty)
        raises(lambda: LP.diary_families([dict(prompt='p1')], data=empty), 'does not exist')
    return 'labels by prompt (first row wins), sha256 of train.jsonl returned; unlabelled diary rows and a missing train.jsonl stop'


def test_replay_priority_train_end_to_end():
    """train() end to end (replay kl and kfsoft, real parent, 3 updates, scoring stubbed to a state_dict hash + the step's extra):
    (1) OFF: the draw is kl_rng.randint (the recorded calls equal a fresh RandomState(KL_REPLAY_SEED) randint sequence, choice never called),
        the records carry no replay_priority key, and the flag at 0.0 equals the flag absent;
    (2) ON (families faked by diary index): choice is used, the records carry replay_priority / _every / _shares (sum 1) / _secs, the 'replay priority @' line;
    (3) the measurement moves no training stream: with replay_priority_probs forced uniform, a run with the real measurement and a run with the
        measurement stubbed to zeros end on equal state_dict hashes (the draws are the same choice calls; only the measurement differs);
    (4) the replay arm with --replay-loss ce is refused."""
    if not all(os.path.exists(x) for x in (PARENT, PROBE, os.path.join(FAR, 'train-rows-l5.jsonl'), os.path.join(FAR, 'eval-rows-l5.jsonl'))) \
            or not os.path.isdir(os.path.join(GUARD_SRC, 'mainbrain')):
        skip('parent / far-transfer rows / guard source absent')
    import contextlib
    import io
    real_score, real_fam, real_probs, real_meas, RS = LP.score_step, LP.diary_families, LP.replay_priority_probs, LP.measure_family_kl, np.random.RandomState
    draws = []
    labels = {'sha': LP.DIARY_TRAIN_SHA256}

    class RecRS(RS):
        def randint(self, *a, **k):
            r = super().randint(*a, **k)
            draws.append(('randint', a, dict(k), [int(x) for x in r]))
            return r

        def choice(self, *a, **k):
            r = super().choice(*a, **k)
            draws.append(('choice', a[:1], {x: y for x, y in k.items() if x != 'p'}, [int(x) for x in r]))
            return r

    def run(td, tag, **kw):
        seen = {'hash': {}, 'extra': {}}
        draws.clear()

        def stub(ck, m, addon, sets, out, arm, step, t_train, threads, extra=None, harm_fn=None, keep=False, stop_limits=None, keep_final=False):
            h = hashlib.sha256()
            for k, v in m.state_dict().items():
                h.update(k.encode())
                h.update(v.detach().numpy().tobytes())
            seen['hash'][step], seen['extra'][step] = h.hexdigest(), dict(extra)
        LP.score_step, LP.diary_families, np.random.RandomState = stub, (lambda diary, data=None: ([f'f{i % 3}' for i in range(len(diary))], labels['sha'])), RecRS
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                LP.train('LB', 3, 1, os.path.join(td, tag), [0, 3], parent=PARENT, train_path=os.path.join(FAR, 'train-rows-l5.jsonl'), cells='l5',
                         eval_rows=os.path.join(FAR, 'eval-rows-l5.jsonl'), probe=PROBE, log_every=1, harm_steps=[], diary_compare='none',
                         guard_src=GUARD_SRC, diary_cache=diary, kl_replay_rows=4, kl_weight=10.0, **kw)
        finally:
            LP.score_step, LP.diary_families, np.random.RandomState = real_score, real_fam, RS
        seen['out'], seen['draws'] = buf.getvalue(), list(draws)
        return seen

    with tempfile.TemporaryDirectory() as td:
        diary = os.path.join(td, 'diary.jsonl')
        with open(os.path.join(FAR, 'train-rows-l5.jsonl')) as f, open(diary, 'w') as g:
            for i, line in zip(range(24), f):
                r = json.loads(line)
                g.write(json.dumps(dict(r, source='diary', accepted=[r['answer']], steps=[], family='diary')) + '\n')
        absent = run(td, 'absent', guard='replay', replay_loss='kl')
        zero = run(td, 'zero', guard='replay', replay_loss='kl', replay_priority=0.0, replay_priority_every=1)
        ref = RS(LP.KL_REPLAY_SEED)
        want = [[int(x) for x in ref.randint(0, 24, size=4)] for _ in range(3)]
        for r in (absent, zero):
            assert [d[0] for d in r['draws']] == ['randint'] * 3 and [d[3] for d in r['draws']] == want, r['draws']
            assert 'replay_priority' not in r['extra'][3] and 'replay_priority_shares' not in r['extra'][3] and 'replay priority' not in r['out']
        assert absent['hash'] == zero['hash'] and absent['hash'][0] != absent['hash'][3], 'FRAC 0 == flag absent'
        assert absent['extra'][3].keys() == zero['extra'][3].keys()
        for guard_kw in (dict(guard='replay', replay_loss='kl'), dict(guard='kfsoft')):
            on = run(td, 'on', replay_priority=0.5, replay_priority_every=1, **guard_kw)
            e = on['extra'][3]
            assert e['replay_priority'] == 0.5 and e['replay_priority_every'] == 1 and set(e['replay_priority_shares']) == {'f0', 'f1', 'f2'}, e
            assert abs(sum(e['replay_priority_shares'].values()) - 1) < 2e-4 and e['replay_priority_secs'] >= 0, e
            assert on['extra'][0]['replay_priority_shares'] == {'f0': 0.3333, 'f1': 0.3333, 'f2': 0.3333}, on['extra'][0]['replay_priority_shares']   # uniform before update 1
            assert [d[0] for d in on['draws']] == ['randint', 'choice', 'choice'] and 'replay priority @1:' in on['out'] and 'replay priority @2:' in on['out'] and 'replay priority @3' not in on['out'], on['out']
            assert on['draws'][0][3] == want[0], 'before the first measurement ON draws exactly what the control draws'
            assert on['extra'][0]['replay_priority_measures'] == 0 and e['replay_priority_measures'] == 2 and e['replay_priority_labels_sha256'] == LP.DIARY_TRAIN_SHA256, e
            assert 'diary families 3' in on['out']
            # (3) isolation, end to end: weights forced on and probs forced uniform, so both runs draw with choice at the same p
            real_w = LP.replay_priority_weights
            LP.replay_priority_probs = lambda fam, kl, frac, **k: np.full(len(fam), 1.0 / len(fam))
            LP.replay_priority_weights = lambda fam, kl, **k: {f: 1.0 for f in dict.fromkeys(fam)}
            try:
                a = run(td, 'iso-real', replay_priority=0.5, replay_priority_every=1, **guard_kw)
                LP.measure_family_kl = lambda m, parent, klreplay, kl_ds, fam, **k: {f: 0.0 for f in dict.fromkeys(fam)}
                b = run(td, 'iso-zero', replay_priority=0.5, replay_priority_every=1, **guard_kw)
            finally:
                LP.replay_priority_probs, LP.measure_family_kl, LP.replay_priority_weights = real_probs, real_meas, real_w
            assert a['hash'] == b['hash'], f'{guard_kw}: the measurement moved a training stream'
            assert [d[0] for d in a['draws']] == ['randint', 'choice', 'choice'], a['draws']
            # (5) a measurement with no priority mass (every KL 0 or NaN) keeps the control's randint draw, so the run equals the control
            for zero in (0.0, float('nan')):
                LP.measure_family_kl = lambda m, parent, klreplay, kl_ds, fam, **k: {f: zero for f in dict.fromkeys(fam)}
                try:
                    z = run(td, 'zero-kl', replay_priority=0.5, replay_priority_every=1, **guard_kw)
                finally:
                    LP.measure_family_kl = real_meas
                assert [d[0] for d in z['draws']] == ['randint'] * 3 and [d[3] for d in z['draws']] == want, (zero, z['draws'])
                assert 'none (KL 0: uniform)' in z['out'], z['out']
        # (6) labels from another build than the pinned diary pool are refused, unless --diary-any
        labels['sha'] = 'f' * 64
        raises(lambda: run(td, 'other-build', guard='kfsoft', replay_priority=0.5, replay_priority_every=1), 'not the skills seed-1 build')
        ok = run(td, 'other-build-any', guard='kfsoft', replay_priority=0.5, replay_priority_every=1, diary_any=True)
        assert ok['extra'][3]['replay_priority_labels_sha256'] == 'f' * 64
        labels['sha'] = LP.DIARY_TRAIN_SHA256
        raises(lambda: LP.train('LB', 1, 1, os.path.join(td, 'ce'), [0], parent=PARENT, guard='replay', replay_loss='ce', guard_src=GUARD_SRC,
                                kl_replay_rows=4, kl_weight=1.0, replay_priority=0.5), '--replay-loss kl')
    return 'OFF: randint draws equal a fresh RandomState sequence, FRAC 0 == flag absent (hashes, record keys); ON: choice draws, shares / secs on the records, "replay priority @1/@2" lines; the measurement leaves the weights identical to a zero-KL (no-measure) run for replay-kl and kfsoft; replay-ce refused'


TESTS = [test_check_guard_args_matrix, test_ce_replay_loss, test_kl_replay_loss_untouched, test_seed_moves_replay_stream,
         test_rng_isolation, test_harm_steps_default, test_dev_sha_check, test_big_dev_provenance, test_diary_train_pin, test_replay_arm_setup,
         test_train_harm_leaves_training_untouched, test_replay_freeze_setup, test_replay_freeze_real_parent_count,
         test_stop_if_drop_parse_and_decision, test_score_step_futility_record, test_train_a1f_stop_and_commit_check,
         test_a1f_is_one_change_vs_l11, test_replay_priority_probs, test_replay_priority_check_guard_args, test_replay_priority_measure_isolated,
         test_diary_families_real_lookup, test_replay_priority_train_end_to_end]

if __name__ == '__main__':
    passed = skipped = 0
    for t in TESTS:
        try:
            msg = t()
        except Skip as e:
            skipped += 1
            print(f'SKIP {t.__name__}: {e}', flush=True)
            continue
        passed += 1
        print(f'PASS {t.__name__}: {msg}', flush=True)
    print(f'all {passed} tests passed' + (f' ({skipped} skipped)' if skipped else ''))
