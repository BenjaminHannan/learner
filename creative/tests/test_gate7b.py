"""python3 -m pytest creative/tests/test_gate7b.py   (CPU, seconds): marks / verdict logic, features and votes, leave-one-out, the learned boost = gate(features) x votes, the audit
(no hand constant on the gate path), frozen-cache training on synthetic data."""
import torch
import torch.nn as nn
from creative import gate7b as G
from custom_io.models import progparse as pp

NO, NS = len(pp.OPS), pp.M
D = 12


def _book(E=40, seed=0):
    g = torch.Generator().manual_seed(seed)
    keys = torch.nn.functional.normalize(torch.randn(E, D, generator=g), dim=-1)
    return keys, torch.randint(0, NO, (E,), generator=g), torch.randint(0, NS, (E,), generator=g), torch.randint(0, NS, (E,), generator=g)


# ---- marks (pure)
def _x(**kw):
    x = dict(gain_H=10.0, gain_L=9.0, hurt_H=20, hurt_L=27, harm_L=dict(chain5=2.0, nonchain=1.0), reach_H=50.0, reach_L=48.0, audit=True)
    x.update(kw)
    return x


def test_marks_edges():
    assert G.parent_marks(_x())['passes']                                           # all four exactly at their marks
    assert not G.parent_marks(_x(gain_L=8.99))['gain']                              # under 0.9 x H's gain
    assert not G.parent_marks(_x(hurt_L=28))['harm']                                # H + 7 is the limit
    assert not G.parent_marks(_x(harm_L=dict(chain5=2.01, nonchain=0.0)))['harm']   # 2.0 points each set
    assert G.parent_marks(_x(harm_L=dict(chain5=-3.0, nonchain=2.0)))['harm']
    assert not G.parent_marks(_x(reach_L=47.99))['recall'] and G.parent_marks(_x(reach_L=48.0))['recall']
    assert not G.parent_marks(_x(audit=False))['passes']
    assert G.parent_marks(_x(gain_H=0.0, gain_L=0.0))['gain']                       # nothing to keep


def test_proved_wrong_and_verdict():
    w = G.parent_marks(_x(gain_L=4.9, hurt_L=20))
    assert w['proved_wrong']                                                        # under 0.5 x, hurt not below H's
    assert not G.parent_marks(_x(gain_L=4.9, hurt_L=19))['proved_wrong']            # fewer hurt rows
    assert not G.parent_marks(_x(gain_L=5.0, hurt_L=25))['proved_wrong']            # exactly 0.5 x keeps
    ok = G.parent_marks(_x())
    assert G.verdict({'s100': ok, 's101': ok}) == 'PASS'
    assert G.verdict({'s100': ok, 's101': w}) == 'FAIL'                             # proved wrong needs BOTH parents
    assert G.verdict({'s100': w, 's101': w}) == 'PROVED WRONG'
    assert G.verdict({'s100': ok}).startswith('incomplete')


def test_compare():
    none_h, h = [1, 1, 0, 0, 1], [1, 0, 1, 0, 1]
    c = G.compare(none_h, h, list('abcde'), list('abxdz'))
    assert (c['helped'], c['hurt'], c['changed']) == (1, 1, 2) and c['net_points'] == 0.0 and abs(c['coverage'] - 0.4) < 1e-9
    assert G.compare([1, 0], [0, 0], ['a', 'b'], ['a', 'b'])['net_points'] == -50.0


# ---- features and votes
def test_votes_features():
    keys, op, a, b = _book()
    z = torch.randn(5, D)
    f, vop, va, vb = G.neighbour_votes(z, keys, op, a, b, 3)
    assert f.shape == (5, G.N_FEAT) and vop.shape == (5, NO) and va.shape == (5, NS)
    assert torch.allclose(vop.sum(-1), torch.ones(5), atol=1e-5) and torch.allclose(va.sum(-1), torch.ones(5), atol=1e-5)
    sims = f[:, :G.K]
    assert (sims[:, :-1] >= sims[:, 1:]).all()                                      # sorted descending
    assert torch.allclose(f[:, G.K], vop.max(-1).values) and torch.allclose(f[:, G.K + 1], va.max(-1).values) and torch.allclose(f[:, G.K + 2], vb.max(-1).values)
    assert (f[:, G.N_CONT:].argmax(-1) == 3).all() and (f[:, G.N_CONT:].sum(-1) == 1).all()   # step one-hot
    f2 = G.neighbour_votes(z, keys[:5], op[:5], a[:5], b[:5], 0)[0]                  # fewer notes than k: sims padded with -1
    assert f2.shape == (5, G.N_FEAT) and (f2[:, 5:G.K] == -1).all()


def test_leave_one_out():
    keys, op, a, b = _book()
    z = keys[:4].clone() * 3.0                                                      # queries ARE entries 0..3
    f, vop, *_ = G.neighbour_votes(z, keys, op, a, b, 0)
    assert torch.allclose(f[:, 0], torch.ones(4), atol=1e-5)                        # without masking: itself at similarity 1
    drop = G.loo_drop(torch.arange(4), torch.arange(40))
    assert drop.sum() == 4 and drop[torch.arange(4), torch.arange(4)].all()
    f, vop2, *_ = G.neighbour_votes(z, keys, op, a, b, 0, drop=drop)
    assert (f[:, 0] < 0.999).all()                                                  # itself is gone: best similarity is another note's
    for i in range(4):                                                              # masking entry i == deleting it from the notebook (each query its own)
        keep = torch.arange(40) != i
        fi, voi, *_ = G.neighbour_votes(z[i:i + 1], keys[keep], op[keep], a[keep], b[keep], 0)
        assert torch.allclose(f[i:i + 1], fi, atol=1e-6) and torch.allclose(vop2[i:i + 1], voi, atol=1e-6)
    assert not G.loo_drop(torch.tensor([-1, 2]), torch.tensor([-1, 2, 3]))[0].any()  # group -1 never dropped
    d = G.loo_drop(torch.tensor([7, 7, 8]), torch.tensor([7, 8, -1]))
    assert d.tolist() == [[True, False, False], [True, False, False], [False, True, False]]   # same-question siblings leave together


# ---- the learned boost is gate(features) x votes at ANY similarity (no threshold, no fixed boost)
class _Const(nn.Module):
    def __init__(self, v):
        super().__init__()
        self.v = v

    def forward(self, feats):
        return torch.full(feats.shape[:-1], self.v)


class _Base(nn.Module):
    def __init__(self):
        super().__init__()
        self.lin = nn.Linear(D, NO)

    def forward(self, z):
        return self.lin(z)


def test_boost_is_gate_times_votes():
    keys, op, a, b = _book()
    steps = [(keys, op, a, b)] * G.N_STEPS
    z = torch.randn(6, D)
    for w in (0.0, 0.37, 80.0):
        mem = G.GateMemory(steps, _Const(w))
        f, vop, va, vb = G.neighbour_votes(z, mem.steps[0]['keys'], op, a, b, 0)
        bias = mem.op_bias(z)
        assert torch.allclose(bias, w * vop, atol=1e-6)                             # op logits
        ptr = mem.wrap_ptr(lambda q, k, ok: torch.zeros(6, NS))
        la, lb = ptr(None, None, None), ptr(None, None, None)
        assert torch.allclose(la, w * va, atol=1e-6) and torch.allclose(lb, w * vb, atol=1e-6)
        assert torch.allclose(ptr(None, None, None), torch.zeros(6, NS))            # a third pointer call (the answer pointer) is untouched
    far = torch.nn.functional.normalize(torch.randn(6, D), dim=-1)                  # low similarity: still fully boosted (no theta)
    mem = G.GateMemory(steps, _Const(2.0))
    assert mem.op_bias(far).abs().sum() > 0


def test_real_gate_path_and_nonnegative():
    keys, op, a, b = _book()
    torch.manual_seed(1)
    gate = G.Gate()
    f = torch.randn(10, G.N_FEAT) * 5
    assert (gate(f) >= 0).all()
    mem = G.GateMemory([(keys, op, a, b)] * G.N_STEPS, gate)
    z = torch.randn(4, D)
    ft, vop, *_ = G.neighbour_votes(z, mem.steps[0]['keys'], op, a, b, 0)
    assert torch.allclose(mem.op_bias(z), gate(ft)[:, None] * vop, atol=1e-6)
    assert mem.mean_weights()[0] is not None and mem.mean_weights()[1] is None


def test_hooks_reset_and_step_counter():
    keys, op, a, b = _book()
    mem = G.GateMemory([(keys, op, a, b)] * G.N_STEPS, _Const(1.0))
    z = torch.randn(3, D)
    for _ in range(3):
        mem.op_bias(z)
    assert mem.t == 3
    mem.reset(None, None)
    assert mem.t == 0 and mem.pending == []
    for _ in range(G.N_STEPS + 2):                                                  # a longer pass clamps to the last step, never raises
        mem.op_bias(z)


def test_audit_no_hand_constant():
    rep = G.audit_gate_path()
    assert rep['ok'], rep['problems']
    keys, op, a, b = _book()
    mem = G.GateMemory([(keys, op, a, b)] * G.N_STEPS, G.Gate())
    for attr in ('theta', 'theta_t', 'theta_ans', 'c', 'cal', 'agree', 'row_fired'):
        assert not hasattr(mem, attr), attr                                         # the hand gate's constants do not exist on the learned memory
    assert not hasattr(mem.gate, 'theta') and not hasattr(mem.gate, 'c')
    assert set(vars(mem)) == {'steps', 'gate', 'n_ops', 'n_slots', 'k', 'tau', 't', 'pending', 'wsum', 'wn'}
    assert set(mem.gate.state_dict()) == {'mu', 'sd', 'net.0.weight', 'net.0.bias', 'net.2.weight', 'net.2.bias'}   # standardisation stats + a 26-16-1 MLP only
    # the check does bite: a gate path that reads theta / compares a similarity is caught
    import ast, inspect, textwrap
    bad = ast.parse(textwrap.dedent('def f(self, sim):\n    return (sim >= self.theta).float() * self.c'))
    names = {n.attr for n in ast.walk(bad) if isinstance(n, ast.Attribute)}
    assert {'theta', 'c'} <= names and G.FORBIDDEN >= {'theta', 'c'}
    assert any(isinstance(n, ast.Compare) and not all(isinstance(o, (ast.Is, ast.IsNot)) for o in n.ops) for n in ast.walk(bad))
    # and the hand gate's code does read them (the audit would fail on it)
    from creative import fastsleep as fs
    assert 'theta' in inspect.getsource(fs.Memory.op_bias) + inspect.getsource(fs.Memory._nbrs)


# ---- frozen-cache training on synthetic rows
def _synthetic(n, informative, seed):
    """Cache with the gate-relevant structure: base logits uninformative, votes right (informative) or wrong; features carry the similarity."""
    g = torch.Generator().manual_seed(seed)
    op = torch.randint(1, NO, (n, G.N_STEPS), generator=g)
    A = torch.zeros(n, G.N_STEPS, NS, dtype=torch.bool)
    A[..., 3] = True
    B = A.clone()
    B[..., 3], B[..., 4] = False, True
    vop = torch.nn.functional.one_hot(op if informative else (op % (NO - 1)) + 1, NO).float()
    va = torch.nn.functional.one_hot(torch.full((n, G.N_STEPS), 3 if informative else 5), NS).float()
    vb = torch.nn.functional.one_hot(torch.full((n, G.N_STEPS), 4 if informative else 6), NS).float()
    feats = torch.zeros(n, G.N_STEPS, G.N_FEAT)
    feats[..., :G.K] = 0.95 if informative else 0.55                              # high similarity <=> the votes are right
    feats[..., G.K:G.K + 3] = 1.0
    feats[..., G.N_CONT:] = torch.eye(G.N_STEPS)[None]
    z = lambda *s: torch.zeros(*s)
    return dict(feats=feats, vop=vop, va=va, vb=vb, lop=z(n, G.N_STEPS, NO), la=z(n, G.N_STEPS, NS), lb=z(n, G.N_STEPS, NS), op=op, A=A, B=B, has=torch.ones(n, dtype=torch.bool))


def test_train_gate_learns_to_listen_and_to_stay_quiet():
    torch.manual_seed(0)
    torch.set_num_threads(1)
    caches = dict(good=_synthetic(16, True, 0), bad=_synthetic(16, False, 1))
    gate, info = G.train_gate(caches, 0.1, dict(steps=150, lr=0.05, seed=0, hidden=8), log=lambda *a: None)
    gs, bs_ = info['per_set']['good'], info['per_set']['bad']
    assert gs['loss_gate'] < 0.1 * gs['loss_none'] and bs_['loss_gate'] <= 1.2 * bs_['loss_none']   # near-zero loss where the votes are right, no worse than none where they are wrong
    wg, wb = info['per_set']['good']['mean_weight_by_step'], info['per_set']['bad']['mean_weight_by_step']
    assert min(wg) > 5 * max(wb) and min(wg) > 3                                      # listens where similarity says the votes are right, quiet where not
    assert info['params'] == 26 * 8 + 8 + 8 + 1 and info['loss_curve'][0][0] == 0 and info['loss_curve'][-1][1] <= info['loss_curve'][0][1]
    assert all(p.requires_grad for p in gate.parameters())


def test_boosted_loss_matches_head_loss():
    """With w = 0 the cached loss equals fastsleep.head_loss (op + operand terms) computed from real heads on the same inputs; the mode term is taken out and
    the answer term is zero when mode != 0."""
    import math
    import torch.nn.functional as F
    from creative import fastsleep as fs
    torch.manual_seed(3)
    n, dk = 8, 6
    heads = dict(op_head=nn.Linear(D, NO), q_a=nn.Linear(D, dk), q_b=nn.Linear(D, dk), k_slot=nn.Linear(D, dk), q_ans=nn.Linear(D, dk), mode_head=nn.Linear(D, 3))
    c = _synthetic(n, True, 2)
    c['has'][::3] = False
    f = dict(z=torch.randn(n, G.N_STEPS, D), S=torch.randn(n, G.N_STEPS + 1, NS, D), ok=torch.rand(n, G.N_STEPS + 1, NS) > 0.3, zf=torch.randn(n, D),
             op=c['op'], a=c['A'], b=c['B'], ans=torch.zeros(n, NS, dtype=torch.bool), mode=torch.ones(n, dtype=torch.long), has=c['has'])
    f['ok'][..., 0] = True
    ptr = lambda q, k, ok: (torch.einsum('bk,bmk->bm', q, k) / math.sqrt(dk)).masked_fill(~ok, -1e9)
    K_ = heads['k_slot'](f['S'])
    with torch.no_grad():
        for s in range(G.N_STEPS):
            c['lop'][:, s] = heads['op_head'](f['z'][:, s])
            c['la'][:, s] = ptr(heads['q_a'](f['z'][:, s]), K_[:, s], f['ok'][:, s])
            c['lb'][:, s] = ptr(heads['q_b'](f['z'][:, s]), K_[:, s], f['ok'][:, s])
        want = fs.head_loss(heads, f, torch.arange(n), 0.1, dk) - F.cross_entropy(heads['mode_head'](f['zf']), f['mode'])
        got = G.boosted_loss(c, torch.zeros(n, G.N_STEPS), 0.1)
    assert abs(float(got) - float(want)) < 1e-4
