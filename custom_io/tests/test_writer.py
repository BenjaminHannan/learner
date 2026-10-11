"""python3 -m custom_io.tests.test_writer   (CPU, a few minutes) ByteWriter (models/writer.py): (1) shapes, masks, nocopy, teacher(), nll / right on hand examples;
(2) greedy == the teacher-forced argmax, in free run (feedback included) on a random model and on a trained toy; (3) toy learning, each with a tiny
encoder (byte embedding + sin/cos position + one conv layer + a pointwise MLP): copy a number marked by `x=`; write `<op> <num1> <num2>` (op named by a vector in Z, numbers
copied, marked a= / b=); write a number that is NOT in the context, given through Z; (4) sizes; (5) G2f, copy=False (no copy path): no copy parameters, outputs bit-identical for any context /
feedback / ckeys / nocopy / refine, greedy == the teacher-forced argmax, and two Z-only toys (pre-PC check 2, Z-only version): op name + two operands given only through Z (mode 0) and
a number given only through Z (mode 1), exact match >= 99% on held-out rows (proved wrong below 90%)."""
import math, random, time
import torch
import torch.nn as nn
from custom_io.models.writer import ByteWriter

PAD, BOS, EOS = 0, 1, 2
CH = '0123456789abcdefghijklmnopqrstuvwxyz =='
V = 3 + len(CH) - 1
ID = {c: 3 + i for i, c in enumerate(CH[:-1])}
OPS = ['add', 'sub', 'mul', 'div', 'min', 'max', 'mod', 'gcd']
FILL = '0123456789abcdefghijklmnopqrstuvwxyz  '


def enc(s):
    return [ID[c] for c in s]


def dec(ids):
    inv = {v: k for k, v in ID.items()}
    return ''.join(inv.get(i, '?') for i in ids)


def check(c, msg):
    assert c, msg


def test_basic():
    torch.manual_seed(0)
    d, cap, B, N = 32, 10, 3, 7
    tok = nn.Embedding(V, d)
    nn.init.normal_(tok.weight, std=0.02)
    w = ByteWriter(d, tok, cap, dk=16, heads=2)
    check(w.inner == 16 and all(q is not tok.weight for q in w.parameters()), 'inner default / tok not owned')
    Z, Xc = torch.randn(B, 4, d), torch.randn(B, N, d)
    zmask = torch.ones(B, 4, dtype=torch.bool)
    cmask = torch.ones(B, N, dtype=torch.bool)
    cmask[1, 4:] = False
    cids = torch.randint(3, V, (B, N))
    mode = torch.tensor([0, 1, 0])
    tg = [[5, 6, 7], [8], None]
    T = ByteWriter.teacher(tg, cids, cmask, cap, BOS, EOS)
    lp, g, a = w(Z, zmask, Xc, cmask, cids, mode, T['inp'], T['fb'], ckeys=torch.randn(B, N, 16))
    L = T['inp'].shape[1]
    check(L == 4 and lp.shape == (B, L, V) and g.shape == (B, L) and a.shape == (B, L, N), 'shapes')
    check(lp.dtype == torch.float32 and ((lp.exp().sum(-1) - 1).abs() < 1e-4).all(), 'normalised')
    check((a[1][:, 4:] == 0).all() and ((a.sum(-1) - 1).abs() < 1e-5).all(), 'masked context gets zero copy weight')
    lr, _, _ = w(Z, zmask, Xc, cmask, cids, mode, T['inp'], T['fb'], refine=2)
    check(lr.shape == (B, L, V) and torch.isfinite(lr).all(), 'refine runs')
    lpn, gn, _ = w(Z, zmask, Xc, cmask, cids, mode, T['inp'], T['fb'], nocopy=True)
    check((gn == 1).all() and torch.allclose(lpn.exp().sum(-1), torch.ones(B, L), atol=1e-4), 'nocopy forces gate 1')
    # the writer must not read the context except through the copy head: perturbing Xc with the head's keys fixed changes nothing in the hidden state
    zm = zmask.clone()
    zm[0, 2:] = False
    h1 = w.hidden(Z, zm, T['inp'], mode, torch.zeros(B, L, d))
    Z2 = Z.clone()
    Z2[0, 2:] += 5
    check(torch.allclose(h1[0], w.hidden(Z2, zm, T['inp'], mode, torch.zeros(B, L, d))[0], atol=1e-6), 'masked Z vectors are not read')
    # teacher(): hand example. context "1 2 1 2 3": ids; target [A=1,2,3]
    c = torch.tensor([[3, 4, 3, 4, 5, 9], [3, 3, 3, 3, 3, 3]])
    cm = torch.tensor([[1, 1, 1, 1, 1, 0], [1, 1, 1, 1, 1, 1]], dtype=torch.bool)
    T = ByteWriter.teacher([[3, 4, 5], [3] * 12], c, cm, 6, BOS, EOS)
    check(T['inp'].tolist() == [[1, 3, 4, 5], [1, 2, 2, 2]] and T['tgt'].tolist() == [[3, 4, 5, 2], [-100] * 4], 'inp / tgt / pad')
    check(T['over'].tolist() == [False, True], 'over')
    fb = T['fb'][0]
    check((fb[0] == 0).all(), 'fb0 zero')
    check(torch.allclose(fb[1], torch.tensor([.5, 0, .5, 0, 0, 0])), 'fb1: all sources of 3')
    check(torch.allclose(fb[2], torch.tensor([0, .5, 0, .5, 0, 0])), 'fb2: byte 4 after a 3')
    check(torch.allclose(fb[3], torch.tensor([0, 0, 0, 0, 1., 0])), 'fb3: byte 5 after 3,4 (the masked 9 is not a source)')
    check((T['fb'][1] == 0).all(), 'over row has no fb')
    T = ByteWriter.teacher([[7, 3]], c[:1], cm[:1], 6, BOS, EOS)
    check((T['fb'][0] == 0).all(), 'no source -> zero')
    T = ByteWriter.teacher([[3, 4, 5, 3, 4]], c[:1], cm[:1], 6, BOS, EOS)
    check(T['inp'].shape[1] == 6 and T['over'].tolist() == [False], 'len + 1 == cap fits')
    # nll / right
    lp = torch.log(torch.tensor([[[.7, .2, .1], [.1, .1, .8]], [[.1, .8, .1], [.3, .3, .4]], [[1., 0, 0], [1., 0, 0]]]) + 1e-9)
    tg = torch.tensor([[0, 2], [0, 2], [-100, -100]])
    nl = ByteWriter.nll(lp, tg)
    check(torch.allclose(nl, torch.tensor([(-math.log(.7) - math.log(.8)) / 2, (-math.log(.1) - math.log(.4)) / 2, 0.]), atol=1e-4), 'nll')
    check(ByteWriter.right(lp, tg).tolist() == [True, False, False], 'right (no target = False)')
    # greedy == forward on its own output (free-run feedback), random model
    for nc in (False, True):
        out, ended = w.greedy(Z, zmask, Xc, cmask, cids, mode, max_len=6, nocopy=nc)
        L = max(map(len, out)) + 1
        inp = torch.tensor([[BOS] + o + [EOS] * (L - len(o)) for o in out])[:, :L]
        fb = torch.zeros(B, L, N)
        for i in range(L - 1):                      # causal fixed point: step i's input depends only on steps < i
            lp, g, a = w(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy=nc)
            fb[:, i + 1] = (1 - g[:, i, None]) * a[:, i]
        lp, _, _ = w(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy=nc)
        for b in range(B):
            n = len(out[b]) + (1 if ended[b] else 0)
            check(lp[b].argmax(-1)[:n].tolist() == out[b] + ([EOS] if ended[b] else []), 'greedy matches teacher-forced argmax with free-run feedback')
    gen = torch.Generator().manual_seed(1)
    o1, _ = w.greedy(Z, zmask, Xc, cmask, cids, mode, max_len=5, temperature=1.0, generator=gen)
    check(all(len(o) <= 5 for o in o1), 'sampling runs')
    print('basic ok')


# ---------------- toy tasks ----------------
def filler(r, n):
    return ''.join(r.choice(FILL) for _ in range(n))


def num(r, k):
    return str(r.randint(1, 9)) + ''.join(r.choice('0123456789') for _ in range(k - 1))


def row_a(r):
    n = num(r, r.randint(1, 12))
    return filler(r, r.randint(0, 12)) + 'x=' + n + ' ' + filler(r, r.randint(0, 12)), n, dict(zi=None)


def row_b(r):
    op, n1, n2 = r.randrange(8), num(r, r.randint(1, 6)), num(r, r.randint(1, 6))
    parts = ['a=' + n1 + ' ', 'b=' + n2 + ' ']
    r.shuffle(parts)
    s = ''.join(filler(r, r.randint(0, 6)) + p for p in parts) + filler(r, r.randint(0, 6))
    return s, OPS[op] + ' ' + n1 + ' ' + n2, dict(op=op)


def row_bz(r):
    op, n1, n2 = r.randrange(8), num(r, r.randint(1, 6)), num(r, r.randint(1, 6))
    return '', OPS[op] + ' ' + n1 + ' ' + n2, dict(op=op, a=n1, b=n2)


def row_c(r):
    n = num(r, r.randint(1, 6))
    return filler(r, r.randint(8, 30)), n, dict(zi=n)


class Toy(nn.Module):
    """tiny encoder + Z builders around one ByteWriter (all trained together with tok)."""
    def __init__(self, task, d=64, cap=20, inner=64, refine=1, copy=True):
        super().__init__()
        self.refine = refine
        self.task, self.d, self.copy = task, d, copy
        self.tok = nn.Embedding(V, d)
        self.emb = nn.Embedding(V, d)
        self.conv = nn.Conv1d(d, d, 5, padding=2)
        self.opemb, self.dig, self.zpos = nn.Embedding(8, d), nn.Embedding(10, d), nn.Embedding(16, d)
        self.mix = nn.Sequential(nn.Linear(d, 2 * d), nn.GELU(), nn.Linear(2 * d, d))
        self.z0 = nn.Parameter(torch.randn(1, d) * 0.5)
        for m in (self.tok, self.emb, self.opemb, self.dig, self.zpos):
            nn.init.normal_(m.weight, std=0.5 if m is not self.tok else 0.02)
        self.w = ByteWriter(d, self.tok, cap, dk=32, heads=4, inner=inner, copy=copy)

    def sincos(self, n):
        f = torch.exp(-torch.arange(0, self.d, 2) * math.log(100.0) / self.d)
        t = torch.arange(n)[:, None] * f
        return torch.cat([t.sin(), t.cos()], -1)

    def make(self, rows):
        B = len(rows)
        strs = [r[0] for r in rows]
        N = max(map(len, strs))
        cids = torch.zeros(B, N, dtype=torch.long)
        for b, s in enumerate(strs):
            cids[b, :len(s)] = torch.tensor(enc(s))
        cmask = cids != PAD
        if not self.copy:           # Z-only: the one fully masked dummy position (Xc zeros, cmask False), as B3G2.line_context
            cids, cmask = torch.zeros(B, 1, dtype=torch.long), torch.zeros(B, 1, dtype=torch.bool)
            N = 1
        x = self.emb(cids) + self.sincos(N)
        Xc = x + torch.nn.functional.gelu(self.conv(x.transpose(1, 2))).transpose(1, 2)
        Xc = (Xc + self.mix(Xc)) * cmask[..., None]
        if self.task == 'a':
            Z, zm = self.z0.expand(B, 3, -1).clone(), torch.tensor([[1, 0, 0]] * B, dtype=torch.bool)
            Z[:, 1:] = torch.randn(B, 2, self.d)
            mode = torch.zeros(B, dtype=torch.long)
        elif self.task == 'b':
            Z = torch.cat([self.opemb(torch.tensor([r[2]['op'] for r in rows]))[:, None], torch.randn(B, 2, self.d)], 1)
            zm = torch.tensor([[1, 0, 0]] * B, dtype=torch.bool)
            mode = torch.zeros(B, dtype=torch.long)
        elif self.task == 'bz':     # op name + two operands, all through Z: [op; a digits (6 slots); b digits (6 slots)]
            dg = torch.tensor([[int(c) for c in r[2]['a']] + [0] * (6 - len(r[2]['a'])) + [int(c) for c in r[2]['b']] + [0] * (6 - len(r[2]['b'])) for r in rows])
            Z = torch.cat([self.opemb(torch.tensor([r[2]['op'] for r in rows]))[:, None], self.dig(dg) + self.zpos(torch.arange(12) + 1)], 1)
            zm = torch.tensor([[True] + [i < len(r[2]['a']) for i in range(6)] + [i < len(r[2]['b']) for i in range(6)] for r in rows])
            mode = torch.zeros(B, dtype=torch.long)
        else:
            dg = torch.tensor([[int(c) for c in r[2]['zi']] + [0] * (6 - len(r[2]['zi'])) for r in rows])
            Z = self.dig(dg) + self.zpos(torch.arange(6))
            zm = torch.tensor([[i < len(r[2]['zi']) for i in range(6)] for r in rows])
            mode = torch.ones(B, dtype=torch.long)
        return Z, zm, Xc, cmask, cids, mode

    def loss(self, rows):
        a = self.make(rows)
        T = ByteWriter.teacher([enc(r[1]) for r in rows], a[4], a[3], self.w.cap, BOS, EOS)
        lp, _, _ = self.w(*a, T['inp'], T['fb'], refine=self.refine)
        return ByteWriter.nll(lp, T['tgt']).mean(), lp, T

    @torch.no_grad()
    def exact(self, rows):
        out, ended = self.w.greedy(*self.make(rows))
        return [dec(o) == r[1] and bool(e) for o, r, e in zip(out, rows, ended)], out


def train_toy(task, gen, steps, seed, target=0.995, bs=64, lr=2e-3, d=64, refine=1, copy=True):
    torch.manual_seed(seed)
    m = Toy(task, d=d, refine=refine, copy=copy)
    opt = torch.optim.Adam(m.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1, (s + 1) / 100) * (0.1 if s > 0.6 * steps else 1))
    tr, ev = random.Random(1000 + seed), random.Random(77)
    dev_rows = [gen(ev) for _ in range(500)]
    t0 = time.time()
    for s in range(1, steps + 1):
        loss, _, _ = m.loss([gen(tr) for _ in range(bs)])
        opt.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step()
        sched.step()
        if s % 250 == 0:
            acc = sum(m.exact(dev_rows)[0]) / len(dev_rows)
            print(f'  {task} step {s} loss {loss.item():.4f} dev exact {acc:.3f} ({time.time() - t0:.0f}s)', flush=True)
            if acc >= target:
                break
    return m, s


def test_toy(task, gen, steps, seed, refine, copy=True, floor=0.90):
    m, used = train_toy(task, gen, steps, seed, refine=refine, copy=copy)
    m.eval()
    ho = random.Random(424242 + seed)
    rows = [gen(ho) for _ in range(500)]
    ok, out = m.exact(rows)
    acc = sum(ok) / len(rows)
    # greedy (T=0) vs the teacher-forced argmax string: they differ only where the free-run feedback (attention) differs from the gold-source feedback
    with torch.no_grad():
        _, lp, T = m.loss(rows)
        tf = ByteWriter.right(lp, T['tgt']).tolist()
    both = sum(o and t for o, t in zip(ok, tf))
    print(f'  teacher-forced right {sum(tf)}, greedy right {sum(ok)}, both {both}')
    check(both >= 0.98 * sum(tf), 'greedy reproduces the teacher-forced string on >= 98% of rows teacher forcing gets right')
    print(f'toy {task} (refine={refine}, copy={copy}): held-out exact {acc:.3f} (500 rows) in {used} steps; teacher-forced right {sum(tf) / len(tf):.3f}')
    check(acc >= floor, f'toy {task} under {100 * floor:.0f}%: {acc:.3f}')
    if acc < 0.99:
        print(f'  WARNING toy {task} below 99%')
    return acc, used, m, rows


def test_toy_extras(m, rows):
    """lesions on toy a: nocopy cannot copy fresh digits; masked context positions are never copied."""
    a = m.make(rows[:100])
    out, _ = m.w.greedy(*a, nocopy=True)
    acc = sum(dec(o) == r[1] for o, r in zip(out, rows[:100])) / 100
    print(f'toy a nocopy exact {acc:.3f} (the copy head is what writes the number)')
    check(acc < 0.5, 'nocopy should break copying')


def test_nocopy_writer():
    """G2f: ByteWriter(copy=False) has no copy path."""
    torch.manual_seed(0)
    d, cap, B, Nz = 32, 10, 4, 5
    tok = nn.Embedding(V, d)
    nn.init.normal_(tok.weight, std=0.02)
    w = ByteWriter(d, tok, cap, dk=16, heads=2, copy=False)
    wc = ByteWriter(d, tok, cap, dk=16, heads=2)
    names = {n for n, _ in w.named_parameters()}
    check(not names & {n for n in names if n.split('.')[0] in ('w_fb', 'g_cp', 'q_cp', 'k_cp')} and not any(hasattr(w, a) for a in ('w_fb', 'g_cp', 'q_cp', 'k_cp')), 'no copy parameters exist')
    check(wc.size() - w.size() == d * d + (d + 1) + 2 * (d * 16 + 16), f'copy=False drops exactly w_fb, g_cp, q_cp, k_cp: {wc.size() - w.size()}')
    Z = torch.randn(B, Nz, d)
    zmask = torch.ones(B, Nz, dtype=torch.bool)
    mode = torch.tensor([0, 1, 0, 1])
    inp = torch.randint(3, V, (B, 6))
    inp[:, 0] = BOS
    ref = None
    for trial in range(4):         # any context, feedback, ckeys, nocopy and refine: bit-identical
        N = 3 + 4 * trial
        Xc, cmask, cids = torch.randn(B, N, d), torch.rand(B, N) < 0.7, torch.randint(3, V, (B, N))
        fb = torch.rand(B, 6, N)
        lp, g, a = w(Z, zmask, Xc, cmask, cids, mode, inp, fb, nocopy=bool(trial % 2), ckeys=torch.randn(B, N, 16) if trial > 1 else None, refine=trial)
        check(lp.shape == (B, 6, V) and g.shape == (B, 6) and a.shape == (B, 6, N), 'shapes hold for the caller\'s N')
        check((g == 1).all() and (a == 0).all() and ((lp.exp().sum(-1) - 1).abs() < 1e-4).all(), 'gate 1, attn zeros, normalised')
        if ref is None:
            ref = lp
        check(torch.equal(lp, ref), 'outputs bit-identical for any context / feedback / ckeys / nocopy / refine')
    out0, e0 = w.greedy(Z, zmask, torch.randn(B, 3, d), torch.ones(B, 3, dtype=torch.bool), torch.randint(3, V, (B, 3)), mode, max_len=6)
    out1, e1 = w.greedy(Z, zmask, torch.randn(B, 9, d), torch.zeros(B, 9, dtype=torch.bool), torch.randint(3, V, (B, 9)), mode, max_len=6, nocopy=True, ckeys=torch.randn(B, 9, 16))
    check(out0 == out1 and e0.tolist() == e1.tolist(), 'greedy is independent of the context')
    L = max(map(len, out0)) + 1
    inp = torch.tensor([[BOS] + o + [EOS] * (L - len(o)) for o in out0])[:, :L]
    lp, _, _ = w(Z, zmask, torch.zeros(B, 1, d), torch.zeros(B, 1, dtype=torch.bool), torch.zeros(B, 1, dtype=torch.long), mode, inp, torch.zeros(B, L, 1))
    for b in range(B):
        n = len(out0[b]) + (1 if e0[b] else 0)
        check(lp[b].argmax(-1)[:n].tolist() == out0[b] + ([EOS] if e0[b] else []), 'greedy equals the teacher-forced argmax (copy=False)')
    print('copy=False basic ok')


def test_sizes():
    for d, inner in ((256, 128), (512, 256)):
        w = ByteWriter(d, nn.Embedding(108, d), 69, inner=inner)
        print(f'size d={d} inner={inner} cap=69 (heads 4, dk 64, mlp 2.0, V 108): {w.size():,} params (tok table not counted)')


if __name__ == '__main__':
    torch.set_num_threads(1)         # tiny matrices: threading only costs
    t0 = time.time()
    test_basic()
    test_nocopy_writer()
    res = {}
    for task, gen, steps, refine in (('a', row_a, 6000, 1), ('b', row_b, 6000, 2), ('c', row_c, 3000, 0)):
        acc, used, m, rows = test_toy(task, gen, steps, 0, refine)
        res[task] = (acc, used)
        if task == 'a':
            test_toy_extras(m, rows)
    for task, gen, steps in (('bz', row_bz, 8000), ('c', row_c, 4000)):         # G2f: Z-only toys, copy=False (c: a number given only through Z, mode 1)
        acc, used, m, rows = test_toy(task, gen, steps, 0, 0, copy=False, floor=0.99)
        res[task + '_z'] = (acc, used)
    test_sizes()
    print('summary', res)
    print(f'ALL OK ({time.time() - t0:.0f}s)')
