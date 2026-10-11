"""python3 -m custom_io.tests.test_reader_rule   (CPU, about a minute; no Gemma: the stub FrozenEG of test_b3 stands in)
Ben's RULE 1: "also for the calculator, it should be read by the reader. It is a fully external tool, just like minecraft." A tape string is read by the same
function as the question: letter window + (eg_embed) the Gemma term. Tests: (a) read_texts([s]) == the question reader on a one-row batch with prompt s;
(b) the Gemma output for s changes the reply's reading; (c) eg_embed off: the old letter-only path; (d) the question memo survives reply reading;
(e) the gradient reaches the Gemma adapter from reply positions; (f) the question path is bit-identical to the pre-change formula; the linear and mlp adapters (adapter 'none' needs d = 768 and shares eg_term)."""
import torch
from custom_io.tests.test_b3 import StubEG, make, rows, batch_of

S = ['add 12 5 = 17', 'mul 30 4 = 120', '?', 'sub 3 4 = -1']


def one_row(s):
    return batch_of([dict(id='x', family='copy_word', prompt=s, answer='a', steps=[])])


def randomise(m):
    with torch.no_grad():
        for n in ('eg_proj', 'eg_hid'):
            if hasattr(m, n):
                getattr(m, n).weight.normal_(0, 0.5)


def test_a_same_as_question():
    for kw in (dict(), dict(eg_adapter='mlp')):
        m = make(eg_embed=True, **kw)
        randomise(m)
        for s in S:
            b = one_row(s)
            xq, mq = m.read(b, talker=True)
            xr, ir, mr = m.read_texts([s], 'cpu', le=len(s))
            assert xq.shape == xr.shape and torch.equal(xq, xr) and torch.equal(mq, mr), (kw, s)
        # in a mixed batch with an empty string and padding, each row still equals its own read at the same width
        xr, _, _ = m.read_texts(S[:2] + [''], 'cpu', le=20)
        assert not xr[2].any()
        for i, s in enumerate(S[:2]):
            x1, _, _ = m.read_texts([s], 'cpu', le=20)
            assert torch.allclose(xr[i], x1[0], atol=1e-5), s
    print('ok (a) read_texts == question reader, bit exact (linear + mlp)')


def test_b_gemma_reaches_reply():
    m = make(eg_embed=True)
    randomise(m)
    x0, _, _ = m.read_texts([S[0]], 'cpu')
    eg = m._eg[0]
    old = eg.encode_texts
    eg.encode_texts = lambda texts, T, device: old(texts, T, device) * 2 + 1
    x1, _, _ = m.read_texts([S[0]], 'cpu')
    assert not torch.equal(x0, x1)
    print('ok (b) changing Gemma output changes the reply reading')


def test_c_off_is_old_path():
    m = make(eg_embed=False)
    assert not hasattr(m, 'eg_proj')
    for s in S:
        x, ids, mask = m.read_texts([s], 'cpu')
        b = one_row(s)
        xo, _ = m.reader({'prompt_ids': ids, 'prompt_mask': mask, 'rows': [{'prompt': s}]})
        assert torch.equal(x, xo)
    # eg_proj zero (step 0): on == off given the same weights
    on = make(eg_embed=True)
    off = make(eg_embed=False)
    off.load_state_dict(on.state_dict(), strict=False)
    for s in S:
        assert torch.equal(on.read_texts([s], 'cpu')[0], off.read_texts([s], 'cpu')[0])
    print('ok (c) eg_embed off unchanged; zero eg_proj equals off')


def test_d_memo():
    m = make(eg_embed=True)
    b = batch_of(rows(16))
    eg = m._eg[0]
    m.eval()
    with torch.no_grad():
        m.generate(b)
    assert eg.passes == 1 and eg.text_calls, (eg.passes, len(eg.text_calls))
    assert all(len(c) and all(isinstance(t, str) for t in c) for c in eg.text_calls)
    m.train()
    p0 = eg.passes
    m.loss(b)[0].backward()
    assert eg.passes - p0 <= 1
    # real FrozenEG: encode_texts never touches _last
    from custom_io.models.eg import FrozenEG
    f = FrozenEG.__new__(FrozenEG)
    f._last = ('k', 'v')
    f._compute = lambda p, T, d, chars: (torch.zeros(len(p), T, 4), None)
    f.encode_texts(['a'], 3, torch.device('cpu'))
    assert f._last == ('k', 'v')
    print('ok (d) question embedded once per batch; replies leave the memo alone; text_calls =', len(eg.text_calls))


def test_e_gradient():
    m = make(eg_embed=True)
    randomise(m)
    X, _, _ = m.read_texts(S, 'cpu')
    m.zero_grad()
    X.pow(2).sum().backward()
    assert m.eg_proj.weight.grad.abs().sum() > 0 and m.ln_eg.weight.grad.abs().sum() > 0
    print('ok (e) gradient reaches eg_proj / ln_eg from reply positions')


def test_f_question_bit_identical():
    import torch.nn.functional as F
    for kw in (dict(), dict(eg_adapter='mlp')):
        m = make(eg_embed=True, **kw)
        randomise(m)
        b = batch_of(rows(8))
        ids = b['prompt_ids']
        H, _ = m._eg[0].encode([r['prompt'] for r in b['rows']], ids.shape[1], ids.device)
        h = m.ln_eg(H.float())          # the pre-change body of Ledger.read
        if m.eg_adapter == 'mlp':
            h = F.gelu(m.eg_hid(h))
        want, _ = m.reader(b, extra=m.eg_proj(h))
        got, _ = m.read(b, talker=True)
        assert torch.equal(want, got)
    m = make(eg_embed=True)
    nc = batch_of([dict(id='n', family='copy_word', prompt='Echo: sune Give only the answer.', answer='sune', steps=[])])
    m.eval()
    with torch.no_grad():
        l1 = m.loss(nc)[0].item()
    print('ok (f) question path bit-identical; no-call loss', l1)
    return l1


if __name__ == '__main__':
    from custom_io.tests import legacy_widths
    legacy_widths.apply()
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            f()
    print('ALL OK')
