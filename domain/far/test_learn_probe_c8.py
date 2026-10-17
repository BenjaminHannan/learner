"""Acceptance tests for C8: learn_probe train --log-update-rms (grad-norm stats + per-group update rms, opt-in, read-only).

  python3 -m pytest domain/far/test_learn_probe_c8.py -v     (CPU only; about two minutes)

The real parent (T1SDR_s200 checkpoint.pt) is not needed. A stand-in parent is built here: a tiny random `tool` model
(custom_io.models.tool.Tool, d=48, one reader layer, one block), saved in the trainer's own checkpoint format
(dict(model, name, cfg, chars, step), the one custom_io.train writes and load_model reads). Training rows are generated
with sheet_probe.candidate in the F4-two cell (the far join format) and go through the trainer's own make_rows / verify:
verify() checks the TOOL's working against row_gold (not the model's output), so a random model keeps its rows.

Test-only stand-ins, each commented where it is used: LP.FIT_N is lowered (the eval 'fit' sample needs >= FIT_N joined rows;
the real value is 420); the scored probe file is the first training rows relabelled to the probe cells (only the
scores.jsonl record is affected); the guard test builds its diary from the tool's working instead of the parent's own answers
(a random parent answers nothing usable). Nothing in the trainer's code path is patched except load_model, wrapped to
RECORD each loss (a read of the loss value, no change).
"""
import json
import math
import os
import random
import subprocess

import numpy as np
import pytest
import torch

from domain.far import learn_probe as LP
from domain.far import sheet_probe as SP

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)   # the same tiny Tool test_learn_probe_r1 uses
UPDATES, EVERY = 20, 5
GUARD_COMMIT = LP.GUARD_COMMIT_SOFT
GUARD_FILES = ('kf.py', 'gp.py', 'klreplay.py', 'fullrun.py', 'common.py', 'constants-kf99n-lr3e4.json')


# ---------------------------------------------------------------- the stand-in world

@pytest.fixture(scope='module')
def world(tmp_path_factory):
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    td = tmp_path_factory.mktemp('c8')
    rng, rows = random.Random(20261017), []
    while len(rows) < 64:
        prompt, fn, g, formula = SP.candidate(SP.SCORED[len(rows) % len(SP.SCORED)], 'F4-two', rng)
        value = fn(g)
        if value is not None:   # a division can come out None
            rows.append(dict(id=f'c8-{len(rows):03d}', kind=SP.SCORED[len(rows) % len(SP.SCORED)], split='F4-two',
                             prompt=prompt, answer=str(value)))
    vocab = CharVocab.build(rows)
    torch.manual_seed(1)
    ck = dict(model=Tool(vocab, **SMALL).state_dict(), name='tool', cfg=SMALL, chars=vocab.chars, step=0)
    w = dict(td=td, rows=rows, parent=str(td / 'parent.pt'), train=str(td / 'rows.jsonl'), probe=str(td / 'probe.jsonl'))
    torch.save(ck, w['parent'])
    with open(w['train'], 'w') as f:
        f.writelines(json.dumps(r) + '\n' for r in rows[:48])
    with open(w['probe'], 'w') as f:   # stand-in scored panel: training rows relabelled to the probe cells (scores.jsonl only)
        f.writelines(json.dumps(dict(r, id=f'p{i}', split=('F4-two', 'F0-near', 'F2b-rows')[i % 3])) + '\n' for i, r in enumerate(rows[48:60]))
    w['ck'] = ck
    return w


def run(world, name, log, arm='LB', updates=UPDATES, every=EVERY, grad_sink=None, **kw):
    """One LP.train run in a fresh out dir with losses recorded exactly. -> dict(state, losses, rng, out). The patches live for this run only."""
    import custom_io.models as M
    losses = []
    real_load = M.load_model

    def load_recording(path, device='cpu'):
        m = real_load(path, device)
        inner = m.loss

        def loss(b):
            o = inner(b)
            if m.training and torch.is_grad_enabled():
                losses.append(float((o[0] if isinstance(o, tuple) else o).detach()))
            return o
        m.loss = loss
        return m
    out = str(world['td'] / name)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(M, 'load_model', load_recording)   # train() imports load_model from here at call time
        mp.setattr(LP, 'FIT_N', 4)   # test only: the real 420 needs 420 joined rows
        if grad_sink is not None:   # independent pre-clip norm: sqrt(sum |g|^2) of the grads, computed by the test, then the real clip
            real_clip = torch.nn.utils.clip_grad_norm_

            def clip(params, max_norm, *a, **k):
                ps = list(params)
                with torch.no_grad():
                    grad_sink.append(math.sqrt(sum(float(p.grad.double().pow(2).sum()) for p in ps if p.grad is not None)))
                return real_clip(ps, max_norm, *a, **k)
            mp.setattr(torch.nn.utils, 'clip_grad_norm_', clip)
        LP.train(arm, updates, 1, out, [updates], parent=world['parent'], train_path=world['train'], log_every=every, cells='l1',
                 probe=world['probe'], keep_final=True, log_update_rms=log, **kw)
    state = torch.load(os.path.join(out, f'step_{updates}', 'checkpoint.pt'), weights_only=True)['model']
    return dict(state=state, losses=losses, out=out, rng=(torch.get_rng_state(), random.getstate(), np.random.get_state()[1].copy()))


def assert_identical(a, b, what):
    assert a['state'].keys() == b['state'].keys()
    bad = [k for k in a['state'] if not torch.equal(a['state'][k], b['state'][k])]
    assert not bad, f'{what}: {len(bad)} tensors differ, e.g. {bad[:3]}'
    assert a['losses'] == b['losses'] and len(a['losses']) > 0, f'{what}: losses differ'   # exact float equality
    assert torch.equal(a['rng'][0], b['rng'][0]) and a['rng'][1] == b['rng'][1] and (a['rng'][2] == b['rng'][2]).all(), f'{what}: RNG state differs'


def history(out):
    return json.load(open(os.path.join(out, 'update-rms.json')))


def check_log(log, updates=UPDATES, every=EVERY, min_groups=3):
    assert [r['update'] for r in log] == list(range(every, updates + 1, every)), [r['update'] for r in log]
    for r in log:
        for k in ('grad_norm_mean', 'grad_norm_max', 'upd_rms_all'):
            assert math.isfinite(r[k]) and r[k] > 0, (r['update'], k, r[k])
        assert r['grad_norm_max'] >= r['grad_norm_mean'] > 0
        assert math.isfinite(r['clip_frac']) and 0 <= r['clip_frac'] <= 1
        assert len(r['upd_rms']) >= min_groups
        assert all(v is not None and math.isfinite(v) and v >= 0 for v in r['upd_rms'].values()), r['upd_rms']
        assert sum(v > 0 for v in r['upd_rms'].values()) >= len(r['upd_rms']) * 0.75, r['upd_rms']   # a few unused params update by exactly 0


# ---------------------------------------------------------------- the helpers on toy tensors

def test_update_group_and_update_rms_on_toy():
    assert LP.update_group('blocks.0.qkv.weight') == 'blocks.0'
    assert LP.update_group('tok.weight') == 'tok'
    assert LP.update_group('bias') == 'bias'
    assert LP.update_group('reader.layers.1.attn.q.weight') == 'reader.layers'
    a, b, z = (torch.nn.Parameter(torch.tensor(v)) for v in ([3., 4.], [6., 8.], [0., 0.]))
    named = [('g1.weight', a), ('g1.bias', b), ('g2.w', z)]   # g1 = {a, b}, g2 = {z, before-norm 0}
    for _, p in named:
        p.grad = torch.ones_like(p)
    snap = LP.snapshot_params(named)
    with torch.no_grad():
        a += torch.tensor([0.3, 0.4])
        b += torch.tensor([0.6, 0.8])
        z += 1.0
    allr, groups = LP.update_rms(snap)
    assert groups == {'g1': pytest.approx(0.1, rel=1e-5)}, groups   # sqrt((0.25 + 1) / (25 + 100)) = 0.1; g2 skipped (before-norm 0)
    assert allr == pytest.approx(math.sqrt((0.25 + 1 + 2) / 125), rel=1e-5)   # the all-model ratio keeps g2's delta in the numerator
    assert [t.grad.tolist() for _, t in named] == [[1., 1.]] * 3, 'update_rms / snapshot_params must not touch grads'
    assert not any(c is p for _, p, c in snap), 'the snapshot is a copy'


def test_gradstats_is_pre_clip():
    p = torch.nn.Parameter(torch.zeros(2))
    st = LP.GradStats(1.0)
    for gnorm in (5.0, 0.5):
        p.grad = torch.tensor([3., 4.]) * gnorm / 5
        gn = torch.nn.utils.clip_grad_norm_([p], 1.0)
        assert float(gn) == pytest.approx(gnorm), 'clip_grad_norm_ returns the norm BEFORE clipping'
        st.add(gn)
    assert st.pop() == dict(grad_norm_mean=2.75, grad_norm_max=5.0, clip_frac=0.5)
    assert st.n == 0


def test_flag_is_off_by_default_and_reaches_train():
    seen = []
    real = LP.train
    LP.train = lambda *a, **kw: seen.append(kw)
    try:
        base = ['train', '--arm', 'LB', '--out', 'x', '--updates', '5']
        LP.main(base)
        LP.main(base + ['--log-update-rms'])
    finally:
        LP.train = real
    assert seen[0]['log_update_rms'] is False and seen[1]['log_update_rms'] is True


# ---------------------------------------------------------------- arm LB, no guard

def test_lb_off_vs_on_bit_identical_and_logged(world):
    off = run(world, 'lb_off', False)
    norms = []
    off2 = run(world, 'lb_off2', False, grad_sink=norms)   # control: determinism, and an independent norm recorder
    on = run(world, 'lb_on', True)
    assert_identical(off, off2, 'control: OFF twice (one run with a passive norm recorder)')
    assert_identical(off, on, 'flag OFF vs ON (final weights, per-update losses, RNG state)')
    # OFF leaves no trace
    assert not os.path.exists(os.path.join(off['out'], 'update-rms.json'))
    rec_off = json.loads(open(os.path.join(off['out'], 'scores.jsonl')).readline())
    assert 'update_rms_log' not in rec_off
    # (b) ON: keys present, finite, positive; cadence = the progress print points
    log = history(on['out'])
    check_log(log)
    rec_on = json.loads(open(os.path.join(on['out'], 'scores.jsonl')).readline())
    assert rec_on['update_rms_log'] == log, 'scores.jsonl carries the same history'
    assert {k: v for k, v in rec_on.items() if k not in ('update_rms_log', 'secs', 'train_secs')} == \
           {k: v for k, v in rec_off.items() if k not in ('secs', 'train_secs')}, 'the rest of the score record is unchanged'
    # the grad stats are the PRE-clip norms: compare with the test's own sqrt(sum g^2) taken before the clip (OFF2, same trajectory)
    assert len(norms) == UPDATES
    for r in log:
        w = norms[r['update'] - EVERY:r['update']]
        assert r['grad_norm_mean'] == pytest.approx(sum(w) / EVERY, rel=1e-4)
        assert r['grad_norm_max'] == pytest.approx(max(w), rel=1e-4)
        assert r['clip_frac'] == sum(x > 1.0 for x in w) / EVERY
    assert max(norms) > 1.0, 'the stand-in must actually clip, or the pre-clip check says nothing'


def test_update_rms_matches_a_by_hand_recompute_after_one_update(world):
    one = run(world, 'lb_one', True, updates=1, every=1)
    (rec,) = history(one['out'])
    before, after = world['ck']['model'], one['state']
    from custom_io.models import load_model
    names = [n for n, _ in load_model(world['parent']).named_parameters()]
    ss = {}
    for n in names:
        d, b = (after[n].double() - before[n].double()), before[n].double()
        g = ss.setdefault('.'.join(n.split('.')[:-1][:2]) or n, [0.0, 0.0])
        g[0] += float(d.pow(2).sum()); g[1] += float(b.pow(2).sum())
    want = {g: math.sqrt(a / b) for g, (a, b) in ss.items() if b > 0}
    assert want.keys() == rec['upd_rms'].keys()
    for g in want:
        assert rec['upd_rms'][g] == pytest.approx(want[g], rel=1e-4, abs=1e-12), g
    assert rec['upd_rms_all'] == pytest.approx(math.sqrt(sum(a for a, _ in ss.values()) / sum(b for _, b in ss.values())), rel=1e-4)


# ---------------------------------------------------------------- arm LA

def test_la_off_vs_on_bit_identical_and_logged(world):
    off = run(world, 'la_off', False, arm='LA', updates=10)
    on = run(world, 'la_on', True, arm='LA', updates=10)
    assert_identical(off, on, 'arm LA, flag OFF vs ON')
    log = history(on['out'])
    check_log(log, updates=10, min_groups=2)
    # the add-on's A / B are named by the Linear they sit on, so the groups are module paths of the model, as for LB
    assert set(log[0]['upd_rms']) <= model_groups(world) and len(log[0]['upd_rms']) >= 2


def model_groups(world):
    from custom_io.models import load_model
    return {LP.update_group(n) for n, _ in load_model(world['parent']).named_parameters()}


# ---------------------------------------------------------------- arm LB + --guard kfsoft (real mainbrain code at the pinned commit)

@pytest.fixture(scope='module')
def guard_world(world):
    """The guard source is main brain's kf.py / gp.py / klreplay.py at the commit train() pins, exported from this repo's git
    history to a temp dir (train() byte-checks it against that commit). Skipped if git cannot supply it."""
    here = os.path.dirname(os.path.abspath(LP.__file__))
    src = world['td'] / 'guard-src'
    (src / 'mainbrain').mkdir(parents=True)
    for f in GUARD_FILES:
        r = subprocess.run(['git', '-C', here, 'show', f'{GUARD_COMMIT}:mainbrain/{f}'], capture_output=True)
        if r.returncode:
            pytest.skip(f'guard source unavailable: git cannot show mainbrain/{f} at {GUARD_COMMIT[:9]} here ({r.stderr.decode().strip()[:120]})')
        (src / 'mainbrain' / f).write_bytes(r.stdout)
    # Stand-in diary (--diary-cache): the real one is the PARENT'S OWN answers on the old-skill prompts (DIARY_DATA, not available
    # here), and a random stand-in parent answers nothing usable. So: rows made by the mode's make_row from the TOOL's working on
    # prompts that are not training rows, tagged source 'diary' as the KL replay needs. Not the parent's behaviour.
    from domain import mode
    from domain.tools import sheet as sheet_tool
    from custom_io.models import load_model
    m, cons, diary = load_model(world['parent']), json.load(open(mode.CONST_PATH)), []
    for r in world['rows'][48:]:
        res = sheet_tool.evaluate(r['prompt'])
        row, why = mode.make_row(m, 'diary', r['prompt'], res['value'], [tuple(s) for s in res['steps']], cons, 'diary', allow_zero=True)
        if row:
            diary.append(row)
    assert len(diary) >= 4, 'stand-in diary too small'
    cache = world['td'] / 'diary.jsonl'
    cache.write_text(''.join(json.dumps(r) + '\n' for r in diary))
    return dict(src=str(src), cache=str(cache))


def test_lb_kfsoft_off_vs_on_bit_identical_and_logged(world, guard_world):
    kw = dict(guard='kfsoft', guard_src=guard_world['src'], guard_every=8, kl_replay_rows=4, kl_weight=10, guard_soft=10,   # --guard-every 8 so F is re-measured twice inside 20 updates
              diary_cache=guard_world['cache'], diary_compare='none')
    off = run(world, 'g_off', False, **kw)
    on = run(world, 'g_on', True, **kw)
    assert_identical(off, on, 'kfsoft guard, flag OFF vs ON')
    log = history(on['out'])
    check_log(log)
    assert set(log[0]['upd_rms']) <= model_groups(world)   # the guard freezes what it cannot project: fewer groups than unguarded LB
