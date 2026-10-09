"""python3 -m custom_io.tests.test_tok_think   (CPU, about a minute; no data files, no Gemma: a stub FrozenEG stands in)
tok_think (TOKENS-EXPERIMENT-2026-10-09.md sec. 8): (a) tok_think off is bit-identical to the ledger.py of commit ad93c2425 (the G1 code): the same fixed rows, seed and
50 AdamW steps give torch.equal losses and parameters; (b) tok_think on: spot shapes, token mask, padding rows, a hand-worked prompt (pooled spot = mean of its letters at
w = b = 0), a first token that merges with the prefix, a dense reference for non-zero weights, gradients to the pool, the thinker's K/V and mask see only the spots,
everything else stays letter-level, the eg_thinker assert, counters; (c) TKN trained count within 0.5% of TK (default caps in process, caps_g.json in a subprocess).
The stub's align() puts a new token at each space and each digit, after 7 prefix tokens (like the real one: token indices do not start at 0)."""
import hashlib, importlib.util, json, subprocess, sys, types
import numpy as np
import torch
import torch.nn.functional as F
from custom_io.data import CharVocab, Dataset, collate
from custom_io.models import ledger as NEW
from custom_io.models import progparse as pp

BASE_SHA = 'ad93c2425'
CFG = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, copy=True, eg_embed=True)
VOCAB = CharVocab.build([])


def rule_map(p, first=7):
    """char -> token: a new token at each space and each digit (never at char 0); token indices start at `first` (the prefix tokens come before)."""
    c, t = [], first
    for i, ch in enumerate(p):
        if i and (ch == ' ' or ch.isdigit()):
            t += 1
        c.append(t)
    return c


class StubEG:
    """Stand-in for models/eg.FrozenEG: deterministic per-prompt states; align() from c2t_fn (default rule_map). encode() is like the real one for chars=True."""

    def __init__(self, c2t_fn=rule_map):
        self.c2t_fn = c2t_fn

    def align(self, prompt):
        return np.zeros(3, np.int32), np.asarray(self.c2t_fn(prompt), np.int16)

    def encode(self, prompts, T, device, chars=True):
        H = torch.zeros(len(prompts), T, 768)
        for b, p in enumerate(prompts):
            g = torch.Generator().manual_seed(int(hashlib.sha1(p.encode()).hexdigest()[:8], 16))
            n = min(len(p), T)
            H[b, :n] = torch.randn(n, 768, generator=g)
        return H.to(device), torch.zeros(len(prompts), 768)


def rows(n=16):
    rs = []
    for i in range(n):
        a, b = 10 + 7 * i, 100 + 13 * i
        k = i % 4
        if k == 0:
            rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'Tom has {a} apples and buys {b} more. How many apples now?', answer=str(a + b), steps=[f'{a} + {b} = {a + b}']))
        elif k == 1:
            rs.append(dict(id=f't{i}', family='copy_word', prompt=f'Echo: sune{i} Give only the answer.', answer=f'sune{i}', steps=[]))
        elif k == 2:
            rs.append(dict(id=f't{i}', family='cipher_map', prompt=f'Shift by {a}: ab', answer='xyz', steps=[]))
        else:
            rs.append(dict(id=f't{i}', family='chain_ops', prompt=f'{a} + {b} * 2', answer=str(a + 2 * b), steps=[f'{a} + {b} * 2 = {a + 2 * b}']))
    return rs


def batches(rs, bs=8):
    ds = Dataset(rs, VOCAB, strict=False)
    return [collate([ds[i] for i in range(s, s + bs)]) for s in range(0, len(rs), bs)]


def make(mod, seed=0, c2t_fn=rule_map, **kw):
    torch.manual_seed(seed)
    m = mod.Ledger(VOCAB, **{**CFG, **kw})
    m._eg = [StubEG(c2t_fn)]
    return m


def load_base():
    src = subprocess.check_output(['git', 'show', f'{BASE_SHA}:custom_io/models/ledger.py'], text=True)
    mod = types.ModuleType('ledger_base_ad93c2425')
    mod.__package__ = 'custom_io.models'
    exec(compile(src, f'{BASE_SHA}:ledger.py', 'exec'), mod.__dict__)
    return mod


def train(m, bl, steps=50, lr=1e-3):
    opt = torch.optim.AdamW(m.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    m.train()
    losses = []
    for s in range(steps):
        out = m.loss(bl[s % len(bl)])
        loss = out[0] if isinstance(out, tuple) else out
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        losses.append(loss.detach().clone())
    return losses


def test_a_off_bit_identical():
    bl = batches(rows())
    base = load_base()
    assert not hasattr(base.Ledger(VOCAB, **{**CFG}), 'tok_think')
    mb, mn = make(base), make(NEW)
    sb, sn = mb.state_dict(), mn.state_dict()
    assert list(sb) == list(sn) and all(torch.equal(sb[k], sn[k]) for k in sb), 'init differs'
    lb, ln = train(mb, bl), train(mn, bl)
    assert all(torch.equal(a, b) for a, b in zip(lb, ln)), [(float(a), float(b)) for a, b in zip(lb, ln) if not torch.equal(a, b)][:3]
    sb, sn = mb.state_dict(), mn.state_dict()
    assert list(sb) == list(sn) and all(torch.equal(sb[k], sn[k]) for k in sb), 'parameters differ after training'
    assert float(ln[0]) > float(ln[-1]), 'loss did not fall'
    print(f'ok a: tok_think off == {BASE_SHA} ledger.py: 50 steps, {len(ln)} losses and {len(sn)} tensors torch.equal (loss {float(ln[0]):.4f} -> {float(ln[-1]):.4f})')


def test_b_tok_think_on():
    rs = rows()[:8] + [dict(id='hand', family='cipher_map', prompt='ab cd 12', answer='xyz', steps=[])]
    b = batches(rs, 9)[0]
    m = make(NEW, tok_think=True)
    assert m.tok_pool.weight.abs().sum() == 0 and m.tok_pool.bias.abs().sum() == 0
    mo = make(NEW)          # tok_think off, same seed: every shared weight identical, tok_pool is the only new tensor
    so, sn = mo.state_dict(), m.state_dict()
    assert [k for k in sn if k not in so] == ['tok_pool.weight', 'tok_pool.bias'] and all(torch.equal(so[k], sn[k]) for k in so)
    assert m.n_params() - mo.n_params() == CFG['d'] + 1
    X, xm = m.read(b, talker=True)
    B, T, d = X.shape
    Xk, km = m.tok_spots(X, xm, b)
    nt = [len(set(rule_map(r['prompt']))) for r in b['rows']]
    K = max(nt)
    assert Xk.shape == (B, K, d) and km.shape == (B, K) and km.sum(1).tolist() == nt, (Xk.shape, km.sum(1).tolist(), nt)
    assert (km == (torch.arange(K)[None] < torch.tensor(nt)[:, None])).all()
    assert (Xk[~km] == 0).all() and K < T and min(nt) < K, 'padding spots must be zero and some rows must be padded'
    # hand-worked prompt "ab cd 12" by the stub rule: letters 0-1 | 2-4 (" cd") | 5 (" ") | 6 ("1") | 7 ("2") -> 5 spots
    hi = len(rs) - 1
    assert rule_map('ab cd 12', 0) == [0, 0, 1, 1, 1, 2, 3, 4]
    assert km[hi].tolist()[:5] == [True] * 5 and not km[hi, 5:].any() and Xk[hi, 5:].abs().sum() == 0
    for k, (s, e) in enumerate([(0, 2), (2, 5), (5, 6), (6, 7), (7, 8)]):
        assert torch.allclose(Xk[hi, k], X[hi, s:e].mean(0), atol=1e-6), k
    # dense reference with non-zero pool weights: softmax over each token's letters
    with torch.no_grad():
        m.tok_pool.weight.normal_(0, 1.0); m.tok_pool.bias.normal_(0, 1.0)
    Xk, km2 = m.tok_spots(X, xm, b)
    assert torch.equal(km, km2)
    for i, r in enumerate(b['rows']):
        c = np.array(rule_map(r['prompt']))
        for k, t in enumerate(sorted(set(c))):
            ix = torch.from_numpy(np.flatnonzero(c == t))
            w = F.softmax(m.tok_pool(X[i, ix])[:, 0], 0)
            assert torch.allclose(Xk[i, k], (w[:, None] * X[i, ix]).sum(0), atol=1e-5), (i, k)
    with torch.no_grad():
        m.tok_pool.weight.zero_(); m.tok_pool.bias.zero_()
    # first token merges with the prefix (token 6 covers the prefix tail and the first chars), and indices with gaps: compaction starts at 0
    for fn in (lambda p: [6 if i < 3 else 6 + 2 * (1 + (i - 3) // 2) for i in range(len(p))], lambda p: [i // 3 + 6 for i in range(len(p))]):
        mm = make(NEW, tok_think=True, c2t_fn=fn)
        X2, xm2 = mm.read(b, talker=True)
        Xk2, km2 = mm.tok_spots(X2, xm2, b)
        c = np.array(fn('ab cd 12'))
        n_hand = len(set(c.tolist()))
        assert km2[hi].sum() == n_hand and km2[hi, :n_hand].all()
        first = X2[hi, :int((c == c[0]).sum())].mean(0)
        assert torch.allclose(Xk2[hi, 0], first, atol=1e-6), 'first spot must be the mean of the letters of the prefix-merged token'
    # gradients flow to the pool weights (the bias gets exactly 0: softmax is shift-invariant); counters count letters and spots of training passes
    m.train(); m._tk_letters = m._tk_spots = 0
    out = m.loss(b)
    loss = out[0] if isinstance(out, tuple) else out
    loss.backward()
    assert m.tok_pool.weight.grad.abs().sum() > 0 and m.tok_pool.bias.grad.abs().max() < 1e-6, (m.tok_pool.weight.grad.abs().sum(), m.tok_pool.bias.grad)
    assert m.reader.tok.weight.grad.abs().sum() > 0
    assert m._tk_letters == sum(len(r['prompt']) for r in b['rows']) and m._tk_spots == sum(nt), (m._tk_letters, m._tk_spots)
    m.eval(); m._tk_letters = 0
    with torch.no_grad():
        m.run(b)
    assert m._tk_letters == 0, 'eval passes are not counted'
    # the thinker's K/V and mask see only the spots; everything else stays letter-level
    seen = {}
    m.core[0].register_forward_hook(lambda mod, a, o: seen.update(kvx=a[2], mask=a[3]))
    with torch.no_grad():
        o = m.run(b)
    Mws = pp.M
    assert seen['kvx'][0].shape[2] == K and seen['mask'].shape == (B, Mws + K) and torch.equal(seen['mask'][:, Mws:], km), (seen['kvx'][0].shape, seen['mask'].shape)
    assert o['X'].shape == (B, T, d) and torch.equal(o['xm'], b['prompt_mask']) and torch.equal(o['X'], X)
    assert o['wvalid'].shape[1] == pp.W_MAX
    # off: the thinker sees the letters (T keys) and the same mask as before
    mo.eval()
    seen.clear()
    mo.core[0].register_forward_hook(lambda mod, a, o: seen.update(kvx=a[2], mask=a[3]))
    with torch.no_grad():
        mo.run(b)
    assert seen['kvx'][0].shape[2] == T and seen['mask'].shape == (B, Mws + T)
    # at init (w = b = 0) a one-token-per-letter map makes tok_think reproduce the letter model exactly
    one = make(NEW, tok_think=True, c2t_fn=lambda p: list(range(7, 7 + len(p))))
    one.eval(); mo.eval()
    with torch.no_grad():
        l_one, l_off = one.run(b), mo.run(b)
    assert torch.allclose(l_one['lmode'], l_off['lmode'], atol=1e-5) and torch.allclose(l_one['R'], l_off['R'], atol=1e-5)
    try:
        make(NEW, tok_think=True, eg_thinker=True)
        raise SystemExit('eg_thinker + tok_think must assert')
    except AssertionError:
        pass
    try:
        NEW.Ledger(VOCAB, **{**CFG, 'eg_embed': False, 'tok_think': True})
        raise SystemExit('tok_think without eg_embed must assert')
    except AssertionError:
        pass
    print(f'ok b: shapes {tuple(Xk.shape)}, mask, padding, hand-worked "ab cd 12" (5 spots = letter means), prefix-merge compaction, dense reference, pool grad, K/V + mask, letter-level X/xm, asserts, counters')


def test_c_tkn_size():
    from custom_io.g8a import configs as C
    mlp, tkn, c_tk, c_tkn = C.tkn_mlp('3M', {'eg_embed': True, 'tok_think': True})
    assert abs(c_tkn / c_tk - 1) <= 0.005
    print(f'ok c (default caps, n_loops 8): TK {c_tk:,}  TKN {c_tkn:,} ({100 * (c_tkn / c_tk - 1):+.3f}%)  {json.dumps(tkn)}')
    out = subprocess.check_output([sys.executable, '-m', 'custom_io.g8a.configs', '--tkn', 'custom_io/g8a/caps_g.json'], text=True)       # caps_g patches module globals: own process
    tk, tn = (int(l.split('trained ')[1].split(' ')[0].replace(',', '')) for l in out.splitlines() if l.startswith(('TK:', 'TKN:')))
    assert abs(tn / tk - 1) <= 0.005 and 'bands ok' in out
    print('ok c (caps_g.json, n_loops 12, job.py 3% band + PT 2% band):\n' + out.rstrip())


if __name__ == '__main__':
    for t in (test_a_off_bit_identical, test_b_tok_think_on, test_c_tkn_size):
        t()
    print('ALL OK')
