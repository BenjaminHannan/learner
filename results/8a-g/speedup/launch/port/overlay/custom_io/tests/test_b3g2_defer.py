"""CPU tests of the b3g2 deferred batched writer port (models/b3g2_defer.py, B3G2.speed_defer, train.py --speed-arms defer). DRAFT until the coordinator has code-reviewed it.

  PYTHONPATH=<port tree> python <port tree>/custom_io/tests/test_b3g2_defer.py      (plain-python runner: prints PASS / FAIL / SKIP per test and a summary; exit 1 on any FAIL; a SKIP is not a pass)
  env: BASE_TREE=<folder holding the UNMODIFIED custom_io of 74d6e92c75> (T1; else the test builds one with `git archive 74d6e92c75 custom_io`, needs a git checkout with that commit: BASE_REPO),
       G2FA4_TRAIN=<g2fa4 overlay/train.py> (T4 b / e; else looked for above this file), DEFER_T4=0 skips the train.py subprocess tests.
  Build the port tree with port/make_port_tree.py OUT_DIR first (this file is part of it).

  T1 flag-off bitwise: the port's b3g2.py with speed_defer False == the UNMODIFIED b3g2.py (loss, aux, every gradient, RNG states, final weights, state_dict keys / shapes) over 3 AdamW updates,
     two subprocesses on two trees, gap_p and ans_drill on (the draws matter).
  T2 deferred vs original (CPU fp32, one thread): loss rel <= 1e-6, EVERY parameter gradient rel L2 <= 1e-6 and cosine >= 0.999999, aux keys equal and values within 1e-6 relative (counts and plan_* exact),
     RNG states equal; K pinned small / large, no-call rows, gap rows, drill rows, an over-cap answer, a NON-TRIVIAL ByteWriter.right (so the hit counters, the right[] scatter and the stop label are exercised).
  T3 fallbacks (eval, no_grad, talk_rounds 'all') are bitwise the original and counted.
  T4 train.py: --speed-arms on a non-b3g2 model exits with a message; flag-off config hash == g2fa4 train.py's; a change of speed arms is refused at --resume both ways; a speed run resumes after a kill,
     RESULT.json has config.speed_arms and defer_stats; flag-off RESULT.json / trace equal the g2fa4 train.py's.
"""
import contextlib, hashlib, importlib.util, json, os, random, shutil, subprocess, sys, tempfile, textwrap, time, unittest
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(os.path.dirname(HERE))                              # the tree under test (holds custom_io/), when this file sits in custom_io/tests of a built tree
if '--dump' not in sys.argv[1:2] and os.path.exists(os.path.join(TREE, 'custom_io', '__init__.py')):
    sys.path.insert(0, TREE)
torch.set_num_threads(1)                                                    # bitwise comparisons need one thread (the harness found a thread-order dependence in a gradient accumulate)
COMMIT = '74d6e92c75'
SCRATCH = None if '--dump' in sys.argv[1:2] else tempfile.mkdtemp(prefix='b3g2-defer-test-')

CFG = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0, n_loops=12, label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.5, any_round=True,
           gap_p=0.5, no_slots=True, no_place=True, bytes=True, as_written=True, writer_inner=24)


def mk_rows(n, off=0):
    """Rows of three kinds: a one-call row (chain_ops), a no-call row (copy_word), a two-call row (chain_story2). Answers of chain rows are a call's result (drill-eligible)."""
    rs = []
    for i in range(n):
        a, b, c = 10 + 7 * (i + off), 100 + 13 * (i + off), 3 + i % 5
        k = i % 3
        if k == 0:
            rs.append(dict(id=f'a{i + off}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), accepted=[str(a + b)], level=1, variant='v', stage=1, steps=[f'{a} + {b} = {a + b}']))
        elif k == 1:
            rs.append(dict(id=f'a{i + off}', family='copy_word', prompt=f'Echo: sune{i + off} Give only the answer.', answer=f'sune{i + off}', accepted=[f'sune{i + off}'], level=1, variant='v', stage=1, steps=[]))
        else:
            rs.append(dict(id=f'a{i + off}', family='chain_story2', prompt=f'Facts: Xavi had {a} cards. Then Xavi got {b} more. After that, Xavi lost {c}. How many now?', answer=str(a + b - c),
                           accepted=[str(a + b - c)], level=2, variant='v', stage=1, steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    return rs


def batch_of(rows):
    from custom_io import data as D
    ds = D.Dataset(rows, D.ByteVocab())
    return D.collate([ds[j] for j in range(len(rows))])


def build_model(seed=0, **over):
    from custom_io.models import build
    from custom_io import data as D
    torch.manual_seed(seed)                                                  # the gap / drill streams are seeded from torch.initial_seed(): same seed, same streams
    m = build('b3g2', D.ByteVocab(), **dict(CFG, **over))
    m.train()
    return m


# ---------------------------------------------------------------------------------------------------------------------------------- T1 (child process)
def dump(out):
    """Child process: 3 AdamW updates (2 micro-batches of 6 rows each) on whatever custom_io is on PYTHONPATH; everything that decides the next update goes to `out`."""
    torch.manual_seed(1234)
    m = build_model(0)
    has_flag = hasattr(m, 'speed_defer')
    if has_flag:
        assert m.speed_defer is False and m.defer_stats == dict(deferred=0, fallback=0)
    decay = [p for p in m.parameters() if p.ndim >= 2]
    rest = [p for p in m.parameters() if p.ndim < 2]
    opt = torch.optim.AdamW([{'params': decay, 'weight_decay': 0.1}, {'params': rest, 'weight_decay': 0.0}], lr=3e-3, betas=(0.9, 0.95))
    rows = mk_rows(36)
    steps = []
    for u in range(3):
        opt.zero_grad(set_to_none=True)
        losses, auxes = [], []
        for h in range(2):
            mb = batch_of(rows[12 * u + 6 * h: 12 * u + 6 * h + 6])
            loss, aux = m.loss(mb)
            (loss / 2).backward()
            losses.append(loss.detach().clone())
            auxes.append({k: (v.detach().clone() if torch.is_tensor(v) else v) for k, v in aux.items()})
        grads = [None if p.grad is None else p.grad.detach().clone() for p in m.parameters()]
        rng = (torch.get_rng_state(), m._gap_rng.getstate(), m._drill_rng.getstate())
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        steps.append(dict(losses=losses, aux=auxes, grads=grads, rng=rng))
    sd = m.state_dict()
    torch.save(dict(has_flag=has_flag, steps=steps, final_sd={k: v.clone() for k, v in sd.items()}, sd_meta=[(k, tuple(v.shape), str(v.dtype)) for k, v in sd.items()],
                    param_names=[n for n, _ in m.named_parameters()], buffer_names=[n for n, _ in m.named_buffers()], n_params=m.n_params()), out)


def base_tree():
    if os.environ.get('BASE_TREE'):
        return os.environ['BASE_TREE']
    d = os.path.join(SCRATCH, 'base')
    if not os.path.exists(d):
        os.makedirs(d)
        repo = os.environ.get('BASE_REPO') or subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
        p = subprocess.run(f'git -C "{repo}" archive {COMMIT} custom_io | tar -x -C "{d}"', shell=True, capture_output=True, text=True)
        if p.returncode or not os.path.exists(os.path.join(d, 'custom_io', 'train.py')):
            shutil.rmtree(d, ignore_errors=True)
            raise unittest.SkipTest(f'no base tree: set BASE_TREE or BASE_REPO ({p.stderr.strip()})')
    return d


def need_tree():
    if not os.path.exists(os.path.join(TREE, 'custom_io', 'models', 'b3g2_defer.py')) or not os.path.exists(os.path.join(TREE, 'custom_io', '__init__.py')):
        raise unittest.SkipTest(f'{TREE} is not a built port tree (run make_port_tree.py OUT_DIR and run the copy of this test inside it)')
    return TREE


def child(tree, out):
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONPATH=tree, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    p = subprocess.run([sys.executable, os.path.abspath(__file__), '--dump', out], env=env, capture_output=True, text=True, cwd=SCRATCH)
    assert p.returncode == 0, f'child on {tree}: rc {p.returncode}\n{p.stdout[-2000:]}\n{p.stderr[-3000:]}'
    return torch.load(out, map_location='cpu', weights_only=False)


def same(x, y, what):
    """Bitwise equality of nested tensors / dicts / lists / numbers (NaN != NaN is not expected here)."""
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


def say(*a):
    print('   ', *a, flush=True)


def test_t1_flag_off_is_bitwise_the_unmodified_b3g2():
    tree, base = need_tree(), base_tree()
    r0 = child(base, os.path.join(SCRATCH, 'dump_base.pt'))
    r1 = child(tree, os.path.join(SCRATCH, 'dump_port.pt'))
    assert not r0['has_flag'] and r1['has_flag'], 'the base has no speed_defer, the port has (and it is False)'
    assert r0['sd_meta'] == r1['sd_meta'], 'state_dict keys / shapes / dtypes (in order) must be identical'
    assert r0['param_names'] == r1['param_names'] and r0['buffer_names'] == r1['buffer_names'] and r0['n_params'] == r1['n_params']
    same(r0['steps'], r1['steps'], 'steps')                                  # per micro-batch loss and aux, per update every gradient and the three RNG states
    same(r0['final_sd'], r1['final_sd'], 'final_sd')
    g = r0['steps'][0]['aux'][0]
    assert 0 < g['plan_gapped'] and any(s['aux'][i]['drill_share'] > 0 for s in r0['steps'] for i in range(2)) and g['plan_rows'] > 0, 'gap and drill draws must have happened'
    say(f'T1: 3 updates x 2 micro-batches: loss, aux, {len(r0["steps"][0]["grads"])} gradient tensors, RNG states (torch, gap, drill) and the final {len(r0["final_sd"])} state_dict tensors BITWISE equal; '
        f'plan_gapped {[int(s["aux"][1]["plan_gapped"]) for s in r0["steps"]]}, drill_share {[[s["aux"][i]["drill_share"] for i in range(2)] for s in r0["steps"]]}')


# ---------------------------------------------------------------------------------------------------------------------------------- T2 helpers
def G():
    import custom_io.models.b3g2 as g
    return g


@contextlib.contextmanager
def forced_ks(k):
    g = G()
    old = g.KS
    if k is not None:
        g.KS = (k,) if isinstance(k, int) else tuple(k)
    try:
        yield
    finally:
        g.KS = old


RIGHT_MARGIN = []


@contextlib.contextmanager
def nontrivial_right():
    """ByteWriter.right made NON-TRIVIAL for both arms (class level, restored on exit), as launch/test_defer.py does: at init no writer is right about anything, which hides the right[] scatter, the
    call / EOS hit counters and the stop label. A deterministic function of the target and of the pair's mean nll quantised at 0.1; a TEST DEVICE for the bookkeeping, not a statement about accuracy.
    Guard: the smallest distance of nll * 10 to a quantisation edge must be >= 5e-5 (about 8x the rounding between the arms), else a flip could be mistaken for a defect."""
    from custom_io.models.writer import ByteWriter as BW
    orig = BW.__dict__['right']

    def right(logp, tgt):
        v = tgt != -100
        lp = logp.gather(-1, tgt.clamp(min=0)[..., None])[..., 0]
        q = -(lp * v).sum(1) / v.sum(1).clamp(min=1) * 10.0
        if bool(v.any(1).any()):
            RIGHT_MARGIN.append(float((q - q.round()).abs()[v.any(1)].min().detach()))
        return v.any(1) & (((tgt.clamp(min=0).sum(1) + q.floor().long()) % 3) != 2)
    BW.right = staticmethod(right)
    del RIGHT_MARGIN[:]
    try:
        yield
    finally:
        BW.right = orig


def assert_margin():
    assert RIGHT_MARGIN and min(RIGHT_MARGIN) >= 5e-5, ('a pair of the nontrivial-right stand-in is too close to its quantisation edge', min(RIGHT_MARGIN or [None]))


def one(m, mb, K, seed=5, backward=True):
    """ONE m.loss(mb) (+ backward) from torch seed `seed`; -> dict(loss, aux, grads (float64 clones), rng states right after the loss)."""
    torch.manual_seed(seed)
    with forced_ks(K):
        loss, aux = m.loss(mb)
    rng = (torch.get_rng_state(), m._gap_rng.getstate(), m._drill_rng.getstate())
    grads = None
    if backward and loss.requires_grad:
        loss.backward()
        grads = [p.grad.detach().double().clone() if p.grad is not None else torch.zeros(p.shape, dtype=torch.float64) for p in m.parameters()]
    return dict(loss=loss.detach(), aux=aux, grads=grads, rng=rng, names=[n for n, _ in m.named_parameters()])


AUX_EXACT = ('rounds', 'stop_w', 'drill_share', 'call_acc', 'eos_acc', 'right_last', 'stop_y', 'stop_acc')       # counts / ratios of counts: no rounding is allowed to move them (plan_* below)
LOSS_REL, GRAD_REL, COS = 1e-6, 1e-6, 0.999999
# FINDING (see README): the bar 'every gradient tensor rel L2 <= 1e-6' is met by every tensor but writer.ln_z.weight / .bias, whose fp32 gradient is summed in ONE LayerNorm backward over all pairs
# (the original sums per round): measured against a float64 run of both paths (which agree to 1e-15) the deferred fp32 error is 1.5e-6 / 2.2e-6 at K 32 (original: 1.4e-7). The main T2 tests
# therefore hold those two tensors to LN_NOISE_REL (10x the bar) and every other tensor to GRAD_REL; test_t2_strict_per_tensor_gradient_bar holds ALL tensors to GRAD_REL and FAILS until
# the coordinator rules on it. Nothing else is relaxed.
LN_NOISE = ('writer.ln_z.weight', 'writer.ln_z.bias')
LN_NOISE_REL = 1e-5
STRICT = dict(on=False, violations=[])
BOOKKEEPING = ('call_acc', 'eos_acc', 'right_last', 'stop_y', 'stop_acc')


def fl(x):
    return None if x is None else float(x)


def compare(r0, r1):
    """-> dict of the T2 numbers of two `one` results (r0 original, r1 deferred)."""
    l0, l1 = float(r0['loss']), float(r1['loss'])
    out = dict(loss_rel=abs(l1 - l0) / max(abs(l0), 1e-300), loss_bitwise=bool(torch.equal(r0['loss'], r1['loss'])), aux_keys_equal=list(r0['aux']) == list(r1['aux']), aux_bad=[])
    for k in r0['aux']:
        x, y = fl(r0['aux'][k]), fl(r1['aux'][k])
        if (x is None) != (y is None):
            out['aux_bad'].append((k, x, y))
        elif x is not None:
            exact = k in AUX_EXACT or k.startswith('plan_')
            if (x != y) if exact else (abs(x - y) > 1e-6 * abs(x)):
                out['aux_bad'].append((k, x, y))
    coss, rels = [], []
    for g0, g1 in zip(r0['grads'], r1['grads']):
        n0, n1 = g0.norm().item(), g1.norm().item()
        if n0 == 0 or n1 == 0:
            coss.append(1.0 if n0 == n1 else 0.0)
            rels.append(0.0 if n0 == n1 else float('inf'))
        else:
            coss.append(float(g0.flatten() @ g1.flatten() / (n0 * n1)))
            rels.append(float((g1 - g0).norm() / n0))
    a0, a1 = torch.cat([g.flatten() for g in r0['grads']]), torch.cat([g.flatten() for g in r1['grads']])
    names = r0['names']
    others = [r for r, n in zip(rels, names) if n not in LN_NOISE]
    out.update(n_tensors=len(coss), grad_cos_min=min(coss), grad_rel_max=max(rels), grad_rel_max_others=max(others), grad_cos_all=float(a0 @ a1 / (a0.norm() * a1.norm())), grad_rel_all=float((a1 - a0).norm() / a0.norm()),
               worst=names[int(np.argmax(rels))], rel_by_name=dict(zip(names, rels)), grad_bitwise=bool(torch.equal(a0, a1)))
    out['rng_equal'] = bool(torch.equal(r0['rng'][0], r1['rng'][0])) and r0['rng'][1] == r1['rng'][1] and r0['rng'][2] == r1['rng'][2]
    return out


def check_close(c, what):
    assert c['aux_keys_equal'], what
    assert not c['aux_bad'], (what, c['aux_bad'])
    assert c['loss_rel'] <= LOSS_REL, (what, 'loss rel', c['loss_rel'])
    assert c['grad_rel_all'] <= GRAD_REL, (what, 'flat gradient rel L2', c['grad_rel_all'])
    assert c['grad_rel_max_others'] <= GRAD_REL, (what, 'worst per-tensor gradient rel L2 outside LN_NOISE', c['grad_rel_max_others'])
    for n in LN_NOISE:
        assert c['rel_by_name'][n] <= LN_NOISE_REL, (what, n, c['rel_by_name'][n])
        if c['rel_by_name'][n] > GRAD_REL and STRICT['on']:
            STRICT['violations'].append((what, n, c['rel_by_name'][n]))
    assert c['grad_cos_min'] >= COS and c['grad_cos_all'] >= COS, (what, c['grad_cos_min'], c['grad_cos_all'])
    assert c['rng_equal'], (what, 'RNG states differ after the call')


def pair(rows, tweak=None, seed=0):
    """Two fresh models of the same init and streams: m0 original (speed_defer False), m1 deferred (True). tweak(m) is applied to both."""
    m0, m1 = build_model(seed), build_model(seed)
    m1.speed_defer = True
    for m in (m0, m1):
        if tweak:
            tweak(m)
    sd0, sd1 = m0.state_dict(), m1.state_dict()
    assert all(torch.equal(sd0[k], sd1[k]) for k in sd0) and m0._gap_rng.getstate() == m1._gap_rng.getstate() and m0._drill_rng.getstate() == m1._drill_rng.getstate()
    return m0, m1


def scenario(name, rows, K, tweak=None, seen=None):
    mb = batch_of(rows)
    m0, m1 = pair(rows, tweak)
    r0, r1 = one(m0, mb, K), one(m1, mb, K)
    c = compare(r0, r1)
    check_close(c, name)
    assert m1.defer_stats == dict(deferred=1, fallback=0) and m0.defer_stats == dict(deferred=0, fallback=0), (m0.defer_stats, m1.defer_stats)
    if seen is not None:
        B = len(rows)
        seen['aux'].append(r0['aux'])
        seen['gapped'] += int(r0['aux']['plan_gapped'])
        seen['drilled'] += int(round(float(r0['aux'].get('drill_share', 0)) * B))
        seen['nocall'] += sum(not r.get('steps') for r in rows)
        seen['n_max'] = max(seen['n_max'], int(r0['aux']['rounds'])); seen['n_min'] = min(seen['n_min'], int(r0['aux']['rounds']))
    say(f'{name}: rows {len(rows)} n {int(r0["aux"]["rounds"])} | loss rel {c["loss_rel"]:.1e} (bitwise {c["loss_bitwise"]}), grad rel L2 per tensor max {c["grad_rel_max"]:.1e} ({c["worst"]}; others {c["grad_rel_max_others"]:.1e}), flat {c["grad_rel_all"]:.1e}, '
        f'cos min {c["grad_cos_min"]:.10f} (all {c["grad_cos_all"]:.10f}) over {c["n_tensors"]} tensors, grad bitwise {c["grad_bitwise"]}, RNG equal {c["rng_equal"]}, aux call_acc/eos_acc/right_last/stop_y/stop_acc '
        + '/'.join(f'{fl(r0["aux"][k]):.3f}' for k in BOOKKEEPING) + f', gapped {int(r0["aux"]["plan_gapped"])}')
    return r0, r1, c


def scenarios(seen):
    rows16 = mk_rows(16)
    calling = [r for r in rows16 if r.get('steps')]
    nocall = [r for r in rows16 if not r.get('steps')]
    assert calling and nocall
    scenario('K=4 pinned (short: n = max(4, last + 2))', rows16, 4, seen=seen)
    r0, _, _ = scenario('K=32 pinned (rounds past CKPT_FROM 8 and n_loops 12)', rows16, 32, seen=seen)
    assert int(r0['aux']['rounds']) == 32 > G().CKPT_FROM and float(r0['aux']['stop_w']) == 1.0
    scenario('K=16, 4 rows', rows16[3:7], 16, seen=seen)
    scenario('K drawn from KS (default generator)', rows16, None, seen=seen)
    scenario('gap_p = 1 (every call row gapped)', rows16, 16, tweak=lambda m: setattr(m, 'gap_p', 1.0), seen=seen)
    scenario('ans_drill = 1 (drilled rows)', rows16, 8, tweak=lambda m: setattr(m, 'ans_drill', 1.0), seen=seen)
    scenario('gap_p = 1 and ans_drill = 1, K 32', rows16, 32, tweak=lambda m: (setattr(m, 'gap_p', 1.0), setattr(m, 'ans_drill', 1.0)), seen=seen)
    scenario('only rows with calls (no gap)', calling, 8, tweak=lambda m: setattr(m, 'gap_p', 0.0), seen=seen)
    scenario('only rows WITHOUT calls (EOS-only call pairs and answers every round)', nocall, 8, seen=seen)
    scenario('writer cap 7: calls and answers over the cap get no target', rows16, 8, tweak=lambda m: setattr(m, 'WCAP', 7), seen=seen)
    scenario("label 'right' (stop_w = 1)", rows16, 16, tweak=lambda m: setattr(m, 'label', 'right'), seen=seen)
    m = build_model(0)
    m.WCAP = 7
    golds = [m.trace_of(r)['gold'] for r in rows16]
    over = sum(len(t) + 1 > 7 for x in golds for t in x['ids'] + [x['ans_ids']])
    assert over > 0, 'the over-cap scenario must have over-cap targets'
    return over


def new_seen():
    return dict(aux=[], gapped=0, drilled=0, nocall=0, n_max=0, n_min=99)


def test_t2_deferred_vs_original_real_right():
    seen = new_seen()
    over = scenarios(seen)
    assert seen['gapped'] > 0 and seen['drilled'] > 0 and seen['nocall'] > 0 and seen['n_max'] == 32 and seen['n_min'] <= 8, seen
    say(f'T2 coverage: gapped rows {seen["gapped"]}, drilled rows {seen["drilled"]}, no-call rows {seen["nocall"]}, rounds {seen["n_min"]}..{seen["n_max"]}, over-cap targets (cap 7) {over}')


def test_t2_deferred_vs_original_nontrivial_right():
    """The same scenarios with `nontrivial_right()` in both arms: the right[] scatter, the call / EOS hit counters, right_last and the stop label are compared on values that are not all 0 / 1."""
    seen = new_seen()
    with nontrivial_right():
        scenarios(seen)
    assert_margin()
    mixed = {k for k in BOOKKEEPING if any(0.0 < fl(x[k]) < 1.0 for x in seen['aux'])}
    assert mixed >= set(BOOKKEEPING), ('each of these must be strictly between 0 and 1 in some scenario', mixed)
    say(f'T2 nontrivial right: smallest distance of nll*10 to an edge {min(RIGHT_MARGIN):.2e} (>= 5e-5); strictly between 0 and 1 somewhere: {sorted(mixed)}')


def test_t2_strict_per_tensor_gradient_bar():
    """The stated bar, unrelaxed: EVERY gradient tensor (writer.ln_z.weight / .bias included) within 1e-6 relative L2 in every T2 scenario. Fails until ruled on (see LN_NOISE above)."""
    STRICT['on'], STRICT['violations'] = True, []
    try:
        scenarios(new_seen())
    finally:
        STRICT['on'] = False
    v = STRICT['violations']
    assert not v, f'{len(v)} (scenario, tensor) pairs above {GRAD_REL}: ' + '; '.join(f'{w[:30]} / {n}: {r:.2e}' for w, n, r in v)


def test_t2_the_marks_catch_a_wrong_deferred_loss():
    """Mutation check of the test itself: a deferred_loss rebuilt with a reversed right[] scatter, swapped hit counters or a wrong stop label must FAIL check_close under nontrivial_right()."""
    import inspect
    import custom_io.models.b3g2_defer as DF
    src = textwrap.dedent(inspect.getsource(DF.deferred_loss))
    muts = [('answer right[] scatter reversed', "right.view(-1)[pk['a_flat']] = rt_a", "right.view(-1)[pk['a_flat'].flip(0)] = rt_a"),
            ('call / EOS hit counters swapped', "hits['call_n'], hits['call_hit'] = n_call, sum(rc[:n_call])", "hits['call_n'], hits['call_hit'] = n_call, sum(rc[n_call:])"),
            ('stop label ignores settled()', "y = (settled(right) if m.label == 'settled' else right).to(dev).float()", "y = right.to(dev).float()"),
            ('call nll left in bucket order', ".index_select(0, pk['c_inv'])", "")]
    rows = mk_rows(16)
    mb = batch_of(rows)
    orig = DF.deferred_loss
    try:
        with nontrivial_right():
            m0, m1 = pair(rows)
            r0 = one(m0, mb, 8)
            check_close(compare(r0, one(m1, mb, 8)), 'unmutated')
            for name, a, b in muts:
                assert src.count(a) == 1, name
                ns = {}
                exec(compile(src.replace(a, b), DF.__file__, 'exec'), DF.__dict__, ns)
                DF.deferred_loss = ns['deferred_loss']
                m0, m1 = pair(rows)
                cm = compare(one(m0, mb, 8), one(m1, mb, 8))
                try:
                    check_close(cm, name)
                except AssertionError as e:
                    say(f'mutation "{name}": caught ({str(e)[:100]})')
                else:
                    raise AssertionError(f'the T2 marks did NOT catch the mutation "{name}"')
                finally:
                    DF.deferred_loss = orig
    finally:
        DF.deferred_loss = orig


# ---------------------------------------------------------------------------------------------------------------------------------- T3
def test_t3_fallbacks_are_bitwise_the_original_and_counted():
    rows = mk_rows(16)
    mb = batch_of(rows)
    m0, m1 = pair(rows)

    def train_loss(m):
        return one(m, mb, 8)

    def eval_loss(m):
        m.eval()
        try:
            return one(m, mb, 8)
        finally:
            m.train()

    def nograd_loss(m):
        with torch.no_grad():
            return one(m, mb, 8)

    def all_rounds(m):
        m.talk_rounds = 'all'
        try:
            return one(m, mb, 8)
        finally:
            m.talk_rounds = 'last'
    # the fallbacks first (m1 has speed_defer True and must act as m0), then the training path
    n_fb = 0
    for name, fn in (('eval-mode loss', eval_loss), ('training mode, no_grad loss', nograd_loss), ("talk_rounds='all' loss + gradient", all_rounds)):
        a, b = fn(m0), fn(m1)
        same({k: v for k, v in a.items()}, {k: v for k, v in b.items()}, name)
        n_fb += 1
        assert m1.defer_stats == dict(deferred=0, fallback=n_fb) and m0.defer_stats == dict(deferred=0, fallback=0), (name, m1.defer_stats, m0.defer_stats)
        say(f'T3 {name}: bitwise the original; defer_stats {m1.defer_stats}')
    # the model that took the fallbacks has had the same draws as its twin: the training path now runs the deferred loss, close to the original
    m0.zero_grad(set_to_none=True); m1.zero_grad(set_to_none=True)
    r0, r1 = train_loss(m0), train_loss(m1)
    check_close(compare(r0, r1), 'training path after the fallbacks')
    assert m1.defer_stats == dict(deferred=1, fallback=3), m1.defer_stats
    # a copy writer is a fallback too (the rule only; its original body is not run: B3G2 never has a copy writer)
    m2 = build_model(0)
    m2.speed_defer = True
    m2.writer.copy = True
    try:
        m2.loss(mb)
    except Exception:                                                           # noqa: BLE001 - the original body may not support a copy writer; the counter is what is asserted
        pass
    assert m2.defer_stats == dict(deferred=0, fallback=1), m2.defer_stats
    say(f'T3 training path: defer_stats {m1.defer_stats}; writer.copy True: counted as a fallback ({m2.defer_stats})')


# ---------------------------------------------------------------------------------------------------------------------------------- pieces
def test_attributes_are_plain_and_the_state_dict_is_unchanged():
    m = build_model(0)
    assert m.speed_defer is False and m.defer_stats == dict(deferred=0, fallback=0)
    assert not any('defer' in k for k in m.state_dict()) and not any('defer' in n for n, _ in m.named_parameters()) and not any('defer' in n for n, _ in m.named_buffers())
    assert 'speed_defer' not in m._parameters and 'speed_defer' not in m._buffers and 'defer_stats' not in m._modules


def test_plan_np_is_plan_without_the_device_copy():
    rows = mk_rows(16)
    m0, m1 = build_model(0), build_model(0)
    Ls = [len(m0.trace_of(r)['gold']['texts']) for r in rows]
    Ls1 = [len(m1.trace_of(r)['gold']['texts']) for r in rows]
    assert Ls == Ls1
    for _ in range(3):
        sched, last = m0.plan(Ls, len(Ls), torch.device('cpu'))
        sn = m1.plan_np(Ls, len(Ls))
        assert isinstance(sn, np.ndarray) and sn.dtype == np.int64 and torch.equal(torch.from_numpy(sn), sched) and m0._gap_rng.getstate() == m1._gap_rng.getstate() and m0.plan_stats == m1.plan_stats
        assert torch.equal(last, sched.max(1).values.clamp(min=0)) and sched.dtype == torch.int64
    assert m0.plan_stats['gapped'] > 0


def test_teacher_np_equals_bytewriter_teacher():
    import custom_io.models.b3g2_defer as DF
    from custom_io.models.writer import ByteWriter as BW
    m = build_model(0)
    g = G()
    ids = [[5, 6, 7], [], None, [9] * (m.WCAP - 1), [9] * m.WCAP, [9] * (m.WCAP + 1), [13], [3, 4], None, []]
    Z = torch.zeros(len(ids), 17, m.d)
    ref = m.answer_teacher(Z, ids)
    inp, tgt, over = DF.teacher_np(ids, m.WCAP, g.BOS, g.EOS)
    assert torch.equal(torch.from_numpy(inp), ref['inp']) and torch.equal(torch.from_numpy(tgt), ref['tgt']) and torch.equal(torch.from_numpy(over), ref['over']) and not ref['fb'].any()
    assert over.tolist() == [False, False, False, False, True, True, False, False, False, False]
    for cap in (3, 5, 69):
        for tg in ([[1, 2], [], None, [1, 2, 3, 4]], [None, None], [[]], [[7] * 4, [7] * 3]):
            _, cmask, cids = m.line_context(torch.zeros(len(tg), 1, m.d))
            r = BW.teacher(tg, cids, cmask, cap, g.BOS, g.EOS)
            i2, t2, o2 = DF.teacher_np(tg, cap, g.BOS, g.EOS)
            assert torch.equal(torch.from_numpy(i2), r['inp']) and torch.equal(torch.from_numpy(t2), r['tgt']) and torch.equal(torch.from_numpy(o2), r['over']), (cap, tg)


def test_schedule_lists_and_answer_pairs_equal_the_loops_host_reads():
    import custom_io.models.b3g2_defer as DF
    rows = mk_rows(16)
    m = build_model(0)
    golds = m.train_golds(batch_of(rows)['rows'])
    Ls = [len(x['texts']) for x in golds]
    sched_dev, last_dev = m.plan(Ls, len(Ls), torch.device('cpu'))
    sched_np = sched_dev.numpy()
    ids = [x['ids'] for x in golds]
    assert torch.equal(torch.from_numpy(DF.last_of(sched_np)), last_dev)
    n = 14
    last, per_round = DF.schedule_lists(sched_np, ids, n)
    by_t = {t: (r, tg, ic) for t, r, tg, ic in per_round}
    B = len(Ls)
    for t in range(1, n):                                                      # what B3G2.loop reads back each round
        at = sched_dev == t
        call, kk = at.any(1), at.int().argmax(1)
        cl, kl, aft = call.tolist(), kk.tolist(), (t > last_dev).tolist()
        tgt = [ids[i][kl[i]] if cl[i] else ([] if aft[i] else None) for i in range(B)]
        sel = [i for i in range(B) if tgt[i] is not None]
        if not sel:
            assert t not in by_t
            continue
        rows_, tg, ic = by_t[t]
        assert rows_ == sel and tg == [tgt[i] for i in sel] and ic == [cl[i] for i in sel], t
    has = np.array([bool(L) for L in Ls])
    t_, i_, ok = DF.answer_pairs(last, has, n)
    for tt in range(n):
        for ii in range(B):
            assert ok[tt, ii] == ((tt > last[ii]) or not has[ii])
    assert list(zip(t_.tolist(), i_.tolist())) == sorted(zip(t_.tolist(), i_.tolist())) and ok[n - 1].all()
    pk = DF.Pack()
    arrs = dict(a=np.arange(6).reshape(2, 3), b=np.zeros((0, 4)), c=np.array([5, 6, 7]))
    for k, v in arrs.items():
        pk.add(k, v)
    pk.send(torch.device('cpu'))
    assert all(pk[k].tolist() == v.tolist() and pk[k].dtype == torch.int64 for k, v in arrs.items())


# ---------------------------------------------------------------------------------------------------------------------------------- T4 train.py
ENV = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')


def make_data(name='data', n=48):
    d = os.path.join(SCRATCH, name)
    if os.path.exists(d):
        return d
    os.makedirs(os.path.join(d, 'dev'))
    with open(os.path.join(d, 'train.jsonl'), 'w') as f:
        for r in mk_rows(n):
            f.write(json.dumps(r) + '\n')
    for s in ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']:
        with open(os.path.join(d, 'dev', s + '.jsonl'), 'w') as f:
            for r in mk_rows(12, 100):
                f.write(json.dumps(dict(r, id=r['id'] + s)) + '\n')
    json.dump(dict(max_prompt=400, max_ans=12, n_num=16, w_max=80, n_res=11, n_reg=13, plain_target=64, le=95), open(os.path.join(d, 'caps.json'), 'w'))
    return d


def targs(data, out, steps, extra=(), model='b3g2', cfg=None):
    return ['--model', model, '--cfg', json.dumps(cfg if cfg is not None else dict(CFG, ans_drill=0.25, gap_p=0.25)), '--data', data, '--steps', str(steps), '--batch', '8', '--lr', '3e-3', '--warmup', '2',
            '--seed', '1', '--out', out, '--eval-batch', '8', '--caps', os.path.join(data, 'caps.json'), '--accum', '2', '--log-every', '1'] + list(extra)


def trun(tree, args, kill_after=None, timeout=1800):
    """python -m custom_io.train ARGS in `tree`; kill_after=K: os._exit(137) right after the step-K checkpoint is completely written. -> (rc, stdout, stderr)."""
    if kill_after is None:
        cmd = [sys.executable, '-m', 'custom_io.train'] + args
    else:
        drv = ('import os, sys\nimport custom_io.train as T\norig = T.save_ckpt\n'
               'def save(ckdir, step, payload, side):\n    r = orig(ckdir, step, payload, side)\n'
               f'    if step == {kill_after}:\n        sys.stdout.flush(); os._exit(137)\n    return r\n'
               'T.save_ckpt = save\nT.main(sys.argv[1:])\n')
        cmd = [sys.executable, '-c', drv] + args
    p = subprocess.run(cmd, cwd=tree, env=dict(ENV, PYTHONPATH=tree), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def events(stdout):
    out = []
    for ln in stdout.splitlines():
        if ln.startswith('{'):
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
    return out


def trace(stdout):
    return [{k: v for k, v in e.items() if k != 'elapsed'} for e in events(stdout) if e.get('event') == 'train']


def fresh(name):
    d = os.path.join(SCRATCH, name)
    shutil.rmtree(d, ignore_errors=True)
    return d


def t4_on():
    if os.environ.get('DEFER_T4') == '0':
        raise unittest.SkipTest('DEFER_T4=0')
    return need_tree()


def g2fa4_train():
    p = os.environ.get('G2FA4_TRAIN')
    d = HERE
    while not p or not os.path.exists(p):
        up = os.path.dirname(d)
        if up == d:
            raise unittest.SkipTest('g2fa4 overlay/train.py not found: set G2FA4_TRAIN')
        d = up
        p = os.path.join(d, 'results', '8a-g', 'pc-job-cards', 'g2fa4', 'overlay', 'train.py')
    return p


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_t4a_speed_arms_on_a_model_without_the_writer_exits_with_a_message():
    tree = t4_on()
    data = make_data()
    rc, so, se = trun(tree, targs(data, fresh('t4a'), 2, ['--speed-arms', 'defer'], model='plain_tf', cfg=dict(d_model=32, n_layers=1, n_heads=2)))
    assert rc != 0 and 'speed-arms defer needs a model with the deferred writer (b3g2)' in se, (rc, so[-500:], se[-1500:])
    rc, so, se = trun(tree, targs(data, fresh('t4a2'), 2, ['--speed-arms', 'nonsense']))
    assert rc == 2 and 'invalid choice' in se, (rc, se[-500:])
    say('T4a: plain_tf + --speed-arms defer exits non-zero with "needs a model with the deferred writer (b3g2)"; an unknown arm is an argparse error (rc 2)')


def test_t4b_flag_off_config_hash_equals_g2fa4_trains():
    tree = t4_on()
    old = load_module(g2fa4_train(), 'g2fa4_train_mod')
    sys.path.insert(0, tree)
    try:
        new = load_module(os.path.join(tree, 'custom_io', 'train.py'), 'port_train_mod')
    finally:
        sys.path.remove(tree)
    import argparse
    caps = os.path.join(make_data(), 'caps.json')
    base = dict(model='b3g2', steps=6, batch=8, lr=3e-3, warmup=2, grad_clip=1.0, seed=1, order='shuffled', bf16=False, max_ans=12, minutes=None, caps=caps)
    cfg = dict(CFG)
    h_old, d_old = old.config_id(argparse.Namespace(**base), cfg)
    h_off, d_off = new.config_id(argparse.Namespace(**base, speed_arms=''), cfg)
    h_on, d_on = new.config_id(argparse.Namespace(**base, speed_arms='defer'), cfg)
    assert h_old == h_off and d_old == d_off and 'speed_arms' not in d_off, (h_old, h_off)
    assert h_on != h_off and d_on['speed_arms'] == 'defer' and {k: v for k, v in d_on.items() if k != 'speed_arms'} == d_off
    assert new.CONFIG_KEYS == old.CONFIG_KEYS
    say(f'T4b: flag-off hash {h_off[:16]} == g2fa4 train.py\'s {h_old[:16]}; with defer {h_on[:16]}')


def test_t4c_a_change_of_speed_arms_is_refused_at_resume_both_ways():
    tree, data = t4_on(), make_data()
    out = fresh('t4c_off')                                                      # flag-off run, checkpoints every 2, then --resume WITH the speed arm
    rc, so, se = trun(tree, targs(data, out, 4, ['--ckpt-every', '2']))
    assert rc == 0, (so[-800:], se[-2500:])
    rc, so, se = trun(tree, targs(data, out, 6, ['--ckpt-every', '2', '--resume', '--speed-arms', 'defer']))
    assert rc == 1 and '--resume refused' in se and 'config hash' in se and 'speed-arms' in se, (rc, se[-800:])
    ok_msg = se.strip().splitlines()[-1][:100]
    rc, so, se = trun(tree, targs(data, out, 4, ['--ckpt-every', '2', '--resume']))     # the same flags resume (nothing left to do, but accepted: the hash matches)
    assert rc == 0 and any(e.get('event') == 'resumed' for e in events(so)), (rc, so[-800:], se[-800:])
    out2 = fresh('t4c_on')                                                      # speed run, then --resume WITHOUT it
    rc, so, se = trun(tree, targs(data, out2, 4, ['--ckpt-every', '2', '--speed-arms', 'defer']))
    assert rc == 0, (so[-800:], se[-2500:])
    rc, so, se = trun(tree, targs(data, out2, 6, ['--ckpt-every', '2', '--resume']))
    assert rc == 1 and '--resume refused' in se and 'config hash' in se, (rc, se[-800:])
    say(f'T4c: flag-off checkpoints + --resume --speed-arms defer: refused (rc 1: "{ok_msg}..."); speed checkpoints + --resume without it: refused (rc 1); same flags resume')


def test_t4d_a_speed_run_resumes_after_a_kill_and_reports_its_arm():
    tree, data = t4_on(), make_data()
    N = 6
    out = fresh('t4d_on')
    a = targs(data, out, N, ['--ckpt-every', '2', '--resume', '--speed-arms', 'defer'])
    rc, so1, se1 = trun(tree, a, kill_after=4)
    assert rc == 137 and os.path.exists(os.path.join(out, 'ckpt', 'step-4.pt')), (rc, so1[-800:], se1[-2000:])
    assert any(e.get('event') == 'start' and e.get('speed_arms') == 'defer' for e in events(so1))
    rc, so2, se2 = trun(tree, a)
    assert rc == 0, (so2[-800:], se2[-2500:])
    ev = events(so2)
    assert any(e.get('event') == 'resumed' and e['step'] == 4 for e in ev), [e for e in ev if e.get('event') in ('resumed', 'resume_warning')]
    assert [e['step'] for e in trace(so2)] == [5, 6]
    res = json.load(open(os.path.join(out, 'RESULT.json')))
    assert res['config']['speed_arms'] == 'defer' and res['steps'] == N and res['resumed_from'] == [4], res['config']
    ds = res['defer_stats']
    assert ds['deferred'] > 0 and ds['fallback'] == 0, ds
    # an uninterrupted speed run: the same trace (the checkpoint restores weights, optimizer, every RNG incl. the model's own streams, defer_stats)
    out_u = fresh('t4d_on_straight')
    rc, so_u, se_u = trun(tree, targs(data, out_u, N, ['--ckpt-every', '2', '--speed-arms', 'defer']))
    assert rc == 0, (so_u[-800:], se_u[-2500:])
    res_u = json.load(open(os.path.join(out_u, 'RESULT.json')))
    t_all = [e for e in trace(so1) if e['step'] <= 4] + trace(so2)
    assert t_all == trace(so_u), 'speed run: kill + resume trace differs from the uninterrupted run'
    assert res['defer_stats'] == res_u['defer_stats'], (res['defer_stats'], res_u['defer_stats'])
    # flag off: no speed_arms key anywhere, no defer_stats
    out_off = fresh('t4d_off')
    rc, so_f, se_f = trun(tree, targs(data, out_off, 4, ['--ckpt-every', '2']))
    assert rc == 0, (so_f[-800:], se_f[-2500:])
    res_f = json.load(open(os.path.join(out_off, 'RESULT.json')))
    assert 'speed_arms' not in res_f['config'] and 'defer_stats' not in res_f and not any('speed_arms' in e for e in events(so_f)), res_f['config']
    say(f'T4d: speed run killed after the step-4 checkpoint, resumed from 4: steps 5..6, trace == uninterrupted speed run, RESULT.json config.speed_arms {res["config"]["speed_arms"]!r}, defer_stats {ds} '
        f'(uninterrupted: {res_u["defer_stats"]}); flag-off RESULT.json has no speed_arms / defer_stats')


def test_t4e_flag_off_run_equals_the_g2fa4_train_py_run():
    tree, data = t4_on(), make_data()
    base = base_tree()
    g2 = os.path.join(SCRATCH, 'g2fa4_tree')                                    # the base package with ONLY the g2fa4 train.py replaced = what src-b3g2ck is
    if not os.path.exists(g2):
        shutil.copytree(base, g2, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(g2fa4_train(), os.path.join(g2, 'custom_io', 'train.py'))
    N = 4
    r = []
    for name, tr in (('g2fa4', g2), ('port', tree)):
        out = fresh('t4e_' + name)
        rc, so, se = trun(tr, targs(data, out, N, ['--ckpt-every', '2']))
        assert rc == 0, (name, so[-800:], se[-2500:])
        r.append((trace(so), json.load(open(os.path.join(out, 'RESULT.json'))), torch.load(os.path.join(out, 'checkpoint.pt'), map_location='cpu', weights_only=False)['model'], [e for e in events(so) if e.get('event') == 'start']))
    (t0, r0, w0, s0), (t1, r1, w1, s1) = r
    assert t0 == t1, 'train lines differ'
    assert s0 == s1, (s0, s1)
    same(w0, w1, 'final weights')
    keys0, keys1 = list(r0), list(r1)
    nop = lambda c: {k: v for k, v in c.items() if k != 'out'}        # the two runs write to different folders
    assert keys0 == keys1 and list(r0['config']) == list(r1['config']) and nop(r0['config']) == nop(r1['config']), (keys0, keys1, r0['config'], r1['config'])
    assert r0['ckpt']['config_hash'] == r1['ckpt']['config_hash']
    say(f'T4e: flag-off port train.py vs g2fa4 train.py ({N} updates, --ckpt-every 2): train lines, start event, RESULT.json keys / config, config hash and final weights identical')


def test_t4f_an_old_g2fa4_checkpoint_resumes_in_the_port_tree_with_the_flag_off():
    """The flag-off hash is the g2fa4 one, so a checkpoint written by the g2fa4 train.py (killed after the step-4 checkpoint) resumes in the port tree and finishes as the uninterrupted g2fa4 run does."""
    tree, data = t4_on(), make_data()
    g2 = os.path.join(SCRATCH, 'g2fa4_tree')
    if not os.path.exists(g2):
        shutil.copytree(base_tree(), g2, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(g2fa4_train(), os.path.join(g2, 'custom_io', 'train.py'))
    N = 6
    out = fresh('t4f_mixed')
    a = targs(data, out, N, ['--ckpt-every', '2', '--resume'])
    rc, so1, se1 = trun(g2, a, kill_after=4)
    assert rc == 137 and os.path.exists(os.path.join(out, 'ckpt', 'step-4.pt')), (rc, se1[-1500:])
    rc, so2, se2 = trun(tree, a)
    assert rc == 0 and any(e.get('event') == 'resumed' and e['step'] == 4 for e in events(so2)), (rc, so2[-800:], se2[-2000:])
    out_s = fresh('t4f_straight')
    rc, so_s, se_s = trun(g2, targs(data, out_s, N, ['--ckpt-every', '2', '--resume']))
    assert rc == 0, (so_s[-800:], se_s[-1500:])
    merged = [e for e in trace(so1) if e['step'] <= 4] + trace(so2)
    assert merged == trace(so_s), 'g2fa4 checkpoint resumed in the port tree: trace differs from the uninterrupted g2fa4 run'
    same(torch.load(os.path.join(out, 'checkpoint.pt'), map_location='cpu', weights_only=False)['model'], torch.load(os.path.join(out_s, 'checkpoint.pt'), map_location='cpu', weights_only=False)['model'], 'final weights')
    say('T4f: g2fa4 train.py killed after its step-4 checkpoint, resumed by the port train.py (flag off): steps 5..6 and the final weights equal the uninterrupted g2fa4 run')

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
    shutil.rmtree(SCRATCH, ignore_errors=True)
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--dump']:
        dump(sys.argv[2])
    else:
        sys.exit(main())
