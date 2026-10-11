"""CPU, seconds, no data files. Run: python -m pytest cohesive/tests/test_shelf.py  (or python cohesive/tests/test_shelf.py)"""
import os
import sys
import tempfile

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from custom_io.data import CharVocab  # noqa: E402
from custom_io.models import build  # noqa: E402
from cohesive import shelf as S  # noqa: E402

CHARS = list('abcdefghijklmnopqrstuvwxyz0123456789 +-*/=().,:?')
CFG = {'span_copy': True, 'span_idx': True, 'span_end': True, 'ans_drill': 0.25}


def tiny():
    torch.manual_seed(0)
    return build('tool', CharVocab(CHARS), **CFG)


def rand_delta(shape, r, seed):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(shape[0], r, generator=g) @ torch.randn(r, shape[1], generator=g)


def test_piece_from_exact_and_refuses():
    m = tiny()
    lin = S.linear_names(m)
    P = {k: v.clone() for k, v in m.state_dict().items()}
    F = {k: v.clone() for k, v in P.items()}
    for i, k in enumerate(['core.0.fc.weight', 'op_head.weight', 'g_cp.weight']):
        F[k] = P[k] + rand_delta(P[k].shape, 8, i).float()
    piece, rep = S.piece_from(P, F, lin, with_report=True)
    assert set(piece) == {'core.0.fc.weight', 'op_head.weight', 'g_cp.weight'} and rep['changed'] == 3
    assert piece['g_cp.weight'][0].shape == (1, 1) and piece['core.0.fc.weight'][0].shape[1] == 8
    for k, (B, A) in piece.items():
        assert (P[k] + B @ A - F[k]).abs().max() < 1e-4
    nonlin = next(k for k in P if k not in lin and P[k].dim() == 2)
    F2 = dict(F)
    F2[nonlin] = P[nonlin] + 1.0
    try:
        S.piece_from(P, F2, lin)
        assert False, 'should refuse'
    except AssertionError as e:
        assert 'other than a Linear' in str(e)


def test_fit_router_separates_toy_classes():
    g = torch.Generator().manual_seed(1)
    cents = torch.randn(6, 20, generator=g) * 3
    y = torch.arange(6).repeat_interleave(torch.tensor([200, 30, 30, 30, 30, 30]))
    X = cents[y] + torch.randn(len(y), 20, generator=g)
    r = S.fit_router(X, y)
    assert r['train_acc'] > 0.97
    Xt = cents.repeat_interleave(10, 0) + torch.randn(60, 20, generator=g)
    assert (S.route(r, Xt) == torch.arange(6).repeat_interleave(10)).float().mean() > 0.95


def make_shelf():
    m = tiny()
    ck = dict(model=m.state_dict(), name='tool', cfg=CFG, chars=CHARS, step=1)
    names = ['core.0.fc.weight', 'op_head.weight']
    sd = m.state_dict()
    pieces = []
    for k in range(5):
        pc = {n: (torch.randn(sd[n].shape[0], 8) * 0.01, torch.randn(8, sd[n].shape[1])) for n in names}
        pieces.append(pc)
    router = S.fit_router(torch.randn(60, 16), torch.arange(60) % 6)
    return S.Shelf(ck, pieces, router)


def test_use_restores_bit_identically():
    sh = make_shelf()
    before = {k: v.clone() for k, v in sh.m.state_dict().items()}
    with sh.use(3) as m:
        d = m.state_dict()['core.0.fc.weight'] - before['core.0.fc.weight']
        B, A = sh.pieces[2]['core.0.fc.weight']
        assert (d - B @ A).abs().max() < 1e-5 and d.abs().max() > 0
    assert all(torch.equal(v, sh.m.state_dict()[k]) for k, v in before.items())
    with sh.use(0):
        pass


def test_save_load_roundtrip():
    sh = make_shelf()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'shelf.pt')
        sh.save(p)
        b = S.Shelf.load(p)
    assert all(torch.equal(sh.m.state_dict()[k], v) for k, v in b.m.state_dict().items())
    for pa, pb in zip(sh.pieces, b.pieces):
        assert set(pa) == set(pb) and all(torch.equal(pa[n][0], pb[n][0]) and torch.equal(pa[n][1], pb[n][1]) for n in pa)
    for k in ('mu', 'sd', 'W', 'b'):
        assert torch.equal(sh.router[k], b.router[k])
    assert b.router['classes'] == list(S.CLASSES) and b.numbers() == sh.numbers()


def test_router_feats_decide_what_answer_reads():
    g = torch.Generator().manual_seed(2)
    prompts = [f'{i}+{i}=' for i in range(12)]
    X = torch.randn(12, 24, generator=g)
    y = torch.arange(60) % 6
    sh = make_shelf()
    sh.router = S.fit_router(torch.randn(60, 24, generator=g), y, feats='reader+workspace')
    assert sh.router['feats'] == 'reader+workspace'
    glance = [([], 'x')] * 12
    _, r = sh.answer(prompts, features=(X, glance))
    assert r == S.route(sh.router, X).tolist() and len(set(r)) > 1
    # no features given: the shelf computes the ones its router reads
    called = []
    saved = S.workspace_features, S.reader_features, S.both_features
    try:
        S.both_features = lambda m, ps, bs=64: (called.append('both') or (X, glance))
        S.workspace_features = lambda m, ps, bs=64: (called.append('workspace') or (X, glance))
        S.reader_features = lambda m, ps: (called.append('reader') or X)
        _, r2 = sh.answer(prompts)
        assert called == ['both'] and r2 == r
        old = {k: v for k, v in sh.router.items() if k != 'feats'}
        assert 'feats' not in old
        sh.router = old
        called.clear()
        _, r3 = sh.answer(prompts)
        assert called == ['workspace'] and r3 == S.route(old, X).tolist()
        sh.router = dict(old, feats='reader')
        called.clear()
        sh.answer(prompts)
        assert called == ['workspace', 'reader']
    finally:
        S.workspace_features, S.reader_features, S.both_features = saved


def test_two_pieces_three_class_router():
    """M1c shape: classes none, sheet, py; the shelf takes its piece count from the pieces, not from the module constants."""
    g = torch.Generator().manual_seed(3)
    cents = torch.randn(3, 24, generator=g) * 4
    y = torch.arange(3).repeat_interleave(torch.tensor([40, 20, 20]))
    Xtr = cents[y] + torch.randn(len(y), 24, generator=g)
    router = S.fit_router(Xtr, y, classes=('none', 'sheet', 'py'))
    assert router['classes'] == ['none', 'sheet', 'py'] and router['W'].shape == (3, 24) and router['train_acc'] > 0.97
    m = tiny()
    ck = dict(model=m.state_dict(), name='tool', cfg=CFG, chars=CHARS, step=1)
    sd = m.state_dict()
    names = ['core.0.fc.weight', 'op_head.weight']
    pieces = [{n: (torch.randn(sd[n].shape[0], 8) * 0.01, torch.randn(8, sd[n].shape[1])) for n in names} for _ in range(2)]
    sh = S.Shelf(ck, pieces, router)
    assert sh.router['classes'] == ['none', 'sheet', 'py']
    before = {k: v.clone() for k, v in sh.m.state_dict().items()}
    with sh.use(2) as mm:
        B, A = pieces[1]['op_head.weight']
        assert ((mm.state_dict()['op_head.weight'] - before['op_head.weight']) - B @ A).abs().max() < 1e-5
    assert all(torch.equal(v, sh.m.state_dict()[k]) for k, v in before.items())
    prompts = [f'{i}+{i}=' for i in range(9)]
    Xt = cents.repeat_interleave(3, 0) + torch.randn(9, 24, generator=g) * 0.1
    glance = [([], 'none-answer')] * 9
    used = []
    import domain.mode as dm
    saved = dm.greedy
    try:
        def fake(mm, ps, bs=64):
            used.append(len(ps))
            return [([], 'k') for _ in ps]
        dm.greedy = fake
        ans, r = sh.answer(prompts, features=(Xt, glance))
    finally:
        dm.greedy = saved
    assert r == [0, 0, 0, 1, 1, 1, 2, 2, 2] and used == [3, 3]
    assert ans == ['none-answer'] * 3 + ['k'] * 6
    assert sh.numbers()['pieces'] == 2 * sum(B.numel() + A.numel() for B, A in pieces[0].values())


def test_look_loops_one_round_vs_full_pass():
    """Real toy model: loops=1 features equal Z after round 1 of a full pass; the router's look_loops decides what answer computes."""
    sh = make_shelf()
    prompts = [f'{i}+{i}=' for i in range(6)]
    seen = {}

    def grab(t, state):
        seen.setdefault(t, state['Z'][:, :S.N_CTRL].flatten(1).float().clone())
        return False
    with torch.no_grad():
        sh.m.run(S._batch(sh.m, prompts), each=grab)
    X1, g1 = S.workspace_features(sh.m, prompts, loops=1)
    Xf, gf = S.workspace_features(sh.m, prompts)
    assert g1 is None and gf is not None and len(gf) == 6
    assert torch.allclose(X1, seen[0], atol=1e-5) and X1.shape == Xf.shape and not torch.allclose(X1, Xf)
    # Shelf.answer: look_loops=1 -> one-round features, no glance; missing key -> full pass
    called = []
    saved = S.workspace_features
    import domain.mode as dm
    saved_g = dm.greedy
    try:
        S.workspace_features = lambda m, ps, bs=64, loops=None: (called.append(loops) or (torch.zeros(len(ps), 16), None if loops else [([], 'g')] * len(ps)))
        dm.greedy = lambda m, ps, bs=64: [([], 'parent-full') for _ in ps]
        sh.router = S.fit_router(torch.randn(60, 16), torch.arange(60) % 6, look_loops=1)
        assert sh.router['look_loops'] == 1
        ans, r = sh.answer(prompts)
        assert called == [1] and all(a == 'parent-full' for a, c in zip(ans, r) if c == 0)
        called.clear()
        sh.router = {k: v for k, v in sh.router.items() if k != 'look_loops'}
        ans, r = sh.answer(prompts)
        assert called == [None] and all(a == 'g' for a, c in zip(ans, r) if c == 0)
    finally:
        S.workspace_features, dm.greedy = saved, saved_g


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
            print('ok', n)
