"""python3 -m mainbrain.test_kf_soft : checks of the graded mask (kf.mask_for soft=, kf.factors soft=, fullrun protect_soft).
No model, no training; one thread, random small statistics."""
import json
import os
import tempfile
from unittest import mock

import torch

from domain import mode
from mainbrain import fullrun, gp, kf

torch.set_num_threads(1)
ENERGY = 0.9


def old_mask(a, g, energy):   # the hard mask as it was before the soft option
    S = g[:, None] * a[None, :]
    flat = S.flatten()
    order = torch.argsort(flat, descending=True)
    cum = torch.cumsum(flat[order], 0) / flat.sum()
    k = int((cum < energy).sum().item()) + 1
    M = torch.ones_like(flat)
    M[order[:k]] = 0.0
    return M.view_as(S), k


def spectra(seed=0):
    t = torch.Generator().manual_seed(seed)
    a = torch.rand(9, generator=t).pow(3).sort(descending=True).values + 1e-4
    g = torch.rand(6, generator=t).pow(3).sort(descending=True).values + 1e-4
    return a, g


def main():
    a, g = spectra()
    p = (g[:, None] * a[None, :])
    M0, k0 = old_mask(a, g, ENERGY)
    # (a) soft None / 0 = the old mask, bit for bit
    for s in (None, 0, 0.0):
        M, k = kf.mask_for(a, g, ENERGY, s)
        assert torch.equal(M, M0) and k == k0, s
    assert torch.equal(kf.mask_for(a, g, ENERGY)[0], M0)
    print('(a) soft None/0 identical to the old hard mask, k =', k0)
    # (b) soft=1: boundary pair exactly 1, inside = min(1, tau/p) = tau/p, in (0, 1]
    M1, k1 = kf.mask_for(a, g, ENERGY, 1)
    assert k1 == k0
    inside = M0 == 0
    assert int(inside.sum()) == k0
    tau = p[inside].min()
    assert torch.equal(M1[~inside], torch.ones_like(M1[~inside])), 'outside must stay 1'
    assert float(M1[p == tau]) == 1.0, 'boundary pair must be exactly 1'
    assert torch.allclose(M1[inside], tau / p[inside], rtol=1e-6)
    assert (M1[inside] > 0).all() and (M1 <= 1).all()
    assert (M1[inside] < 1).any(), 'some protected pair is graded below 1'
    top = p.flatten().argmax()
    assert abs(float(M1.flatten()[top]) - float(tau / p.max())) < 1e-7
    print('(b) soft=1: boundary 1, inside tau/p in (0,1], outside 1; top pair M = %.4f' % float(M1.flatten()[top]))
    # (c) soft=10: everything <= soft=1, inside exactly tau/(10 p) or 1 where that exceeds 1 (never: 10p >= tau)
    M10, _ = kf.mask_for(a, g, ENERGY, 10)
    assert (M10 <= M1 + 1e-7).all()
    assert torch.allclose(M10[inside], M1[inside] / 10, rtol=1e-5)
    assert torch.equal(M10[~inside], torch.ones_like(M10[~inside]))
    print('(c) soft=10 <= soft=1 everywhere; boundary pair M = %.3f' % float(M10[p == tau]))
    # (d) project with an all-ones M leaves D unchanged
    A, G = torch.randn(30, 9), torch.randn(30, 6)
    _, U = kf.eig(A.T @ A)
    _, V = kf.eig(G.T @ G)
    D = torch.randn(6, 9)
    out = kf.project(D, (U, V, torch.ones(6, 9)))
    assert torch.allclose(out, D, atol=1e-5), float((out - D).abs().max())
    print('(d) project with all-ones M returns D (max dev %.1e)' % float((out - D).abs().max()))
    # (e) factors passes soft through and adds the summary keys; old keys unchanged
    stats = {'l1': (A.T @ A / 30, G.T @ G / 30), 'skip': (None, None)}
    F0, i0 = kf.factors(stats, ENERGY)
    F1, i1 = kf.factors(stats, ENERGY, soft=1)
    assert set(i0['l1']) == {'pairs', 'protected', 'free_share'}
    assert set(i1['l1']) == {'pairs', 'protected', 'free_share', 'm_median', 'frac_gt_0_1', 'soft'}
    assert all(i1['l1'][x] == i0['l1'][x] for x in i0['l1']) and i1['l1']['soft'] == 1
    assert 0 < i1['l1']['m_median'] <= 1 and 0 <= i1['l1']['frac_gt_0_1'] <= 1
    print('(e) factors(soft=1) info:', i1['l1'])
    # (f) fullrun: protect_soft reaches kf.factors; absent -> soft=None; soft with another method is refused
    seen = []
    base = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'constants-kf99n-kl10-lr3e4.json')))
    saved = (mode.train_night, mode.make_opt)
    try:
        for soft in (None, 1):
            cons = dict(base, replay_loss='ce')
            if soft is not None:
                cons['protect_soft'] = soft
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, 'c.json')
                json.dump(cons, open(path, 'w'))
                mode.train_night = lambda *a, **k: 'trained'
                mode.make_opt = lambda *a, **k: None
                fake = lambda stats, energy, soft=None: (seen.append(soft) or ({}, {}))
                with mock.patch.object(kf, 'factors', fake), mock.patch.object(kf, 'kfac_stats', lambda *a, **k: {}), \
                        mock.patch.object(gp, 'freeze_unprojected', lambda m: []):
                    fullrun.install(path, out=None, seed=1)
                    assert mode.train_night(torch.nn.Linear(2, 2), None, [], 1, cons, 1) == 'trained'
        assert seen == [None, 1], seen
        bad = dict(base, replay_loss='ce', protect='none', protect_soft=1)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'c.json')
            json.dump(bad, open(path, 'w'))
            try:
                fullrun.install(path, out=None, seed=1)
                raise SystemExit('protect_soft with protect=none was accepted')
            except AssertionError:
                pass
    finally:
        mode.train_night, mode.make_opt = saved
    print('(f) fullrun passes protect_soft to kf.factors:', seen, '; refused with protect=none')
    print('ALL PASS')


if __name__ == '__main__':
    main()
