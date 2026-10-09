"""python3 -m custom_io.tests.test_moe   (CPU, a few minutes; design/8a-gx-experts-2026-10-09.md sections 2, 3, 4, 6)
(1) experts=0 reproduces gold_moe_base.json (made at ad93c24259, the code G1 runs): params, keys, every tensor's bytes, loss, aux, answers;
(2) experts>0 leaves every weight outside `moe` byte-identical at the same seed; (3) the dense layer equals a per-token loop (selection on logits + bias, gates from plain p);
(4) gradients: unpicked experts get exactly zero, the router gets some; (5) sizes and bands; (6) the balancing bias moves only in training-mode loss() calls, the right way;
(7) 30 CPU steps: loss falls, moe_lb >= 1, a skewed router gets balanced, every expert is used; (8) the routing report. Real rows are not on the Mac: fixed rows in moe_fp.py."""
import contextlib, json, math, os
import torch
import torch.nn.functional as F
from custom_io.g8a import caps as CP, configs as C
from custom_io.models.ledger import MoEMLP
from custom_io.tests import moe_fp as FP

HERE = os.path.dirname(__file__)
CAPS_G = os.path.join(HERE, '..', 'g8a', 'caps_g.json')
GOLD = json.load(open(os.path.join(HERE, 'gold_moe_base.json')))


def same(fp, gd, name):
    assert fp['n_params'] == gd['n_params'], (name, fp['n_params'], gd['n_params'])
    assert fp['keys'] == gd['keys'], name
    assert fp['hashes'] == gd['hashes'], (name, [k for k in gd['hashes'] if fp['hashes'].get(k) != gd['hashes'][k]][:5])
    assert fp['loss'] == gd['loss'] and fp['aux'] == gd['aux'], (name, fp['loss'], gd['loss'], fp['aux'], gd['aux'])
    assert fp['answers'] == gd['answers'], name


def test_off_is_base():
    b = FP.batch(tag='u')
    same(FP.fingerprint(FP.make(FP.SMALL, copy=True, experts=0), b), GOLD['small_copy'], 'small_copy')
    same(FP.fingerprint(FP.make(FP.SMALL, copy=True, eg_embed=True, experts=0), b), GOLD['small_eg'], 'small_eg')
    CP.apply(json.load(open(CAPS_G)))           # from here on every test runs with the 8a-G caps (36 registers, 12 rounds)
    same(FP.fingerprint(FP.make(FP.G3M, experts=0, top_k=8, moe_aux=0.01), FP.batch()), GOLD['g3m'], 'g3m')
    print('ok experts=0 reproduces the base (3 configs: params, keys, tensor bytes, loss, aux, answers)')


def test_shared_weights_identical():
    for kw in (dict(copy=True), dict(copy=True, eg_embed=True)):
        a, m = FP.make(FP.SMALL, 5, **kw), FP.make(FP.SMALL, 5, experts=6, top_k=2, **kw)
        sa, sm = a.state_dict(), m.state_dict()
        moe_keys = {k for k in sm if '.moe.' in k}
        assert set(sm) == {k for k in sa if not (k.startswith('core.') and k.split('.')[2] in ('fc', 'out'))} | moe_keys, set(sm) ^ set(sa)
        assert all(k.startswith('core.') and k.split('.')[2] == 'moe' for k in moe_keys) and len(moe_keys) == 6
        for k in sm:
            if k not in moe_keys:
                assert torch.equal(sa[k], sm[k]), k
    g = FP.make(FP.G3M, 3), FP.make(FP.G3M, 3, experts=52, top_k=8)
    assert all(torch.equal(g[0].state_dict()[k], t) for k, t in g[1].state_dict().items() if '.moe.' not in k)
    mo = g[1].core[0].moe
    assert (mo.router.weight != 0).any() and mo.b1.ndim == mo.b2.ndim == 1 and mo.b1.abs().sum() == 0 and mo.bias.abs().sum() == 0
    assert mo.w1.shape == (52, 256, 154) and mo.w2.shape == (52, 154, 256)
    assert not any(torch.equal(mo.w1[i], mo.w1[j]) for i in range(52) for j in range(i)) and not torch.equal(g[1].core[0].moe.w1, g[1].core[1].moe.w1)
    assert not any(torch.equal(mo.w2[i], mo.w2[j]) for i in range(52) for j in range(i))
    assert abs(mo.w2.std().item() / (0.02 / math.sqrt(3 * 2 * 12)) - 1) < 0.05 and abs(mo.w1.std().item() / 0.02 - 1) < 0.05
    print('ok shared weights identical, keys swap fc/out for moe, experts differ, router random')


def slow(mo, x):
    out = torch.zeros_like(x)
    for b in range(x.shape[0]):
        for n in range(x.shape[1]):
            v = x[b, n]
            logits = mo.router.weight @ v
            p = logits.softmax(-1)
            sel = (logits + mo.bias).topk(mo.k).indices
            w = mo.k * p[sel] / p[sel].sum()
            for e, we in zip(sel.tolist(), w):
                hid = F.gelu(v @ mo.w1[e] + mo.b1.view(mo.E, -1)[e])
                out[b, n] += we * (hid @ mo.w2[e] + mo.b2.view(mo.E, -1)[e])
    return out


def test_layer_matches_loop():
    torch.manual_seed(1)
    mo = MoEMLP(16, 7, 3, 10, 0.3)
    with torch.no_grad():
        mo.router.weight.normal_(0, 1.0); mo.b1.normal_(0, 0.1); mo.b2.normal_(0, 0.1)
        mo.bias.copy_(torch.tensor([2.0, -1, 0, 0.5, 0, -3, 1]))        # selection uses logits + bias; gates use the plain softmax
    x = torch.randn(2, 5, 16)
    y = mo(x)
    assert (y - slow(mo, x)).abs().max() < 1e-5, (y - slow(mo, x)).abs().max()
    lg = x @ mo.router.weight.T
    assert not torch.equal((lg + mo.bias).topk(3).indices, lg.topk(3).indices), 'the bias must change some picks'
    print('ok MoE layer == per-token loop (nonzero bias), max err', float((y - slow(mo, x)).abs().max().detach()))


def tiny(E=8, k=2, **kw):
    return FP.make(FP.SMALL, 0, copy=True, experts=E, top_k=k, **kw)


def test_gradients():
    m = tiny(24, 3)
    m.core[0].moe.bias[:5] = -100.0          # these five are never picked
    loss, aux = m.loss(FP.batch())
    loss.backward()
    mo = m.core[0].moe
    for e in range(24):
        gs = [mo.w1.grad[e], mo.w2.grad[e], mo.b1.grad.view(24, -1)[e], mo.b2.grad.view(24, -1)[e]]
        if e < 5:
            assert all((g == 0).all() for g in gs), e
        else:
            assert any((g != 0).any() for g in gs), e
    assert not mo.bias.requires_grad
    assert mo.router.weight.grad.abs().sum() > 0
    print('ok unpicked experts have exactly zero grad, the router has grad')


def test_checkpoint_same():
    """moe_ckpt True vs False (fp32): same loss, same gradient on every parameter (<= 1e-6), and one log entry per block and round either way."""
    b = FP.batch()
    out = []
    for ck in (True, False):
        m = tiny(8, 2, moe_ckpt=ck)
        loss, aux = m.loss(b)
        assert all(len(blk.moe.log) == m.n_loops for blk in m.core) and m.core[0].moe.ckpt == ck
        loss.backward()
        out.append((loss.item(), {k: p.grad.clone() for k, p in m.named_parameters() if p.grad is not None}, float(aux['moe_top'])))
    assert out[0][2] == out[1][2] and abs(out[0][0] - out[1][0]) <= 1e-6 and set(out[0][1]) == set(out[1][1])
    worst = max(float((out[0][1][k] - out[1][1][k]).abs().max()) for k in out[0][1])
    assert worst <= 1e-6, worst
    m = tiny(8, 2, moe_ckpt=True).eval()
    with torch.no_grad():
        m.loss(b)
    print('ok checkpoint: loss and all grads equal, max grad diff %.2e, %d log entries per block' % (worst, m.n_loops))


def test_sizes():
    ex = dict(eg_embed=True, n_loops=12)
    got = {}
    for name, rung, e in (('B2-3M', '3M', ex), ('GX-3M', '3M', dict(ex, experts=52, top_k=8)), ('B2-10M', '10M', ex), ('GX-10M', '10M', dict(ex, experts=52, top_k=8, moe_gamma=1e-3))):
        cfgs, cnt = C.sizes(rung, e)
        b2 = cfgs['B2']
        got[name] = (cnt['B2'], C.n_active('ledger', b2), b2['blocks'])
        try:
            C.check_bands(rung, cfgs, cnt, exact_3m=False)
            band = 'passes'
        except AssertionError as err:
            band = 'FAILS: %s' % err
        print('  ', name, got[name], 'check_bands', band, 'PT', cnt['PT'])
        assert band == 'passes', band
    assert got['B2-3M'][:2] == (3_544_913,) * 2 and got['B2-10M'][:2] == (10_496_537,) * 2
    assert got['GX-3M'][:2] == (10_553_929, 3_579_225) and got['GX-10M'] == (38_532_601, 10_633_785, 8), got
    assert C.b2_cfg('3M', ex)['blocks'] == 2 and C.b2_cfg('10M', dict(ex, experts=52))['blocks'] == 8
    print('ok sizes; active vs dense twin: GX-3M %+.2f%%, GX-10M %+.2f%%' % (100 * (got['GX-3M'][1] / got['B2-3M'][0] - 1), 100 * (got['GX-10M'][1] / got['B2-10M'][0] - 1)))


def test_bias_moves_only_in_training():
    b = FP.batch()
    m = tiny(8, 2, moe_gamma=0.01)
    rw = m.core[0].moe.router.weight
    with torch.no_grad():
        rw[0] = 0.0
        m.eval(); m.loss(b); m.generate(b); m.run(b, gold=m.gold(b['rows'], 'cpu'))
        assert m.core[0].moe.bias.abs().sum() == 0, 'eval never updates'
        m.train(); m.run(b)
        assert m.core[0].moe.bias.abs().sum() == 0, 'no gold, no update'
        m.core[0].moe.bias[0] = 5.0                     # expert 0 is picked far above average
        m.loss(b)
    bias = m.core[0].moe.bias
    assert abs(bias[0].item() - 4.99) < 1e-6 and bias[1:].abs().max() <= 0.01 + 1e-9 and (bias[1:] != 0).any(), bias
    m0 = tiny(8, 2, moe_gamma=0.0)
    m0.loss(b)
    assert m0.core[0].moe.bias.abs().sum() == 0
    print('ok bias: eval / no-gold calls leave it, training loss() moves the overloaded expert down, gamma 0 disables, state_dict carries it:', 'core.0.moe.bias' in m.state_dict())


def skew(m, b, scale=3.0):
    """Point block 0's router row 0 along the mean router input, so expert 0 is picked for nearly every token."""
    xs = []
    h = m.core[0].moe.register_forward_pre_hook(lambda mod, a: xs.append(a[0].detach().flatten(0, 1)))
    with torch.no_grad():
        m.run(b)
    h.remove()
    mean = torch.cat(xs).mean(0)
    with torch.no_grad():
        m.core[0].moe.router.weight[0] = scale * mean / (mean @ mean)


def test_training():
    b = FP.batch()
    m = tiny(8, 2, moe_gamma=0.02)
    skew(m, b, 3.0)
    opt = torch.optim.AdamW(m.parameters(), lr=4e-3, weight_decay=0.0)
    seen, tops, lbs, losses = torch.zeros(8), [], [], []
    for step in range(30):
        loss, aux = m.loss(b)
        seen += sum(c for _, c in m.core[0].moe.log)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        losses.append(loss.item()); tops.append(float(aux['moe_top'])); lbs.append(float(aux['moe_lb']))
    assert all(math.isfinite(x) for x in losses + lbs) and losses[-1] < losses[0], (losses[0], losses[-1])
    assert min(lbs) >= 1 - 1e-4, min(lbs)
    assert tops[0] > 3.5 and tops[-1] < 0.75 * tops[0], tops
    assert (seen > 0).all(), seen
    print('ok 30 steps: loss %.2f -> %.2f, moe_lb %.3f -> %.3f, moe_top %.2f -> %.2f (skewed start), picks per expert min %d' % (losses[0], losses[-1], lbs[0], lbs[-1], tops[0], tops[-1], seen.min()))
    assert 'moe_low' in aux


def test_report():
    m = tiny(10, 2)
    rows = FP.batch()['rows']
    r = m.moe_report(rows, dict(batch_size=4, amp=contextlib.nullcontext, device='cpu'))
    assert len(r['blocks']) == 1 and r['n_rows'] == 8
    b = r['blocks'][0]
    assert len(b['rounds']) == 8 and all(len(x) == 10 and abs(sum(x) - 1) < 1e-5 for x in b['rounds']) and abs(sum(b['share']) - 1) < 1e-5
    for k in ('dead', 'top_share_x_even', 'share_min_x_even', 'share_max_x_even', 'n_in_half_to_double', 'entropy', 'round_overlap', 'bias'):
        assert k in b, k
    assert 0 <= b['round_overlap'] <= 1 and 0 < b['entropy'] <= math.log(10) + 1e-6 and set(b['bias']) == {'min', 'max', 'mean'}
    assert all(mm.moe.trace is None for mm in m.core)
    assert tiny(0).active_params() == tiny(0).n_params()
    print('ok routing report keys and shapes; entropy %.3f of max %.3f' % (b['entropy'], math.log(10)))


if __name__ == '__main__':
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    test_off_is_base()           # first: it applies the 8a-G caps for everything after
    for t in (test_shared_weights_identical, test_layer_matches_loop, test_gradients, test_checkpoint_same, test_sizes, test_bias_moves_only_in_training, test_training, test_report):
        t()
    print('ALL OK')
