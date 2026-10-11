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


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
            print('ok', n)
