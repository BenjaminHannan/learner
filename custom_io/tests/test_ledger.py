"""python3 -m custom_io.tests.test_ledger   (CPU, about 2 minutes; needs the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)"""
import collections, json, os, random, tempfile, time
import torch
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, collate, load_rows, word_spans
from custom_io.evalx import donor_eval, evaluate, is_hit
from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger, R0, replay

S_CFG = dict(d=256, n_heads=4, reader_layers=2, blocks=2, n_loops=8, mlp=4.8)
M_CFG = dict(d=384, n_heads=6, reader_layers=2, blocks=3, n_loops=8, mlp=6.0)
SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
_ROWS = {}


def train_rows(n, seed=0):
    if 'rows' not in _ROWS:
        _ROWS['rows'] = load_rows(os.path.join(DEFAULT_DATA, 'train.jsonl'))
    return random.Random(seed).sample(_ROWS['rows'], n)


def vocab():
    return CharVocab.get(DEFAULT_DATA)


def batch_of(rows, v):
    ds = Dataset(rows, v, strict=False)
    return collate([ds[i] for i in range(len(rows))])


def test_executor():
    """The exact executor reproduces every gold intermediate value and the answer slot of every program parsed from steps."""
    v, rows = vocab(), train_rows(2000)
    m = Ledger(v, **SMALL).eval()
    ok, n, nprog = collections.Counter(), collections.Counter(), collections.Counter()
    with torch.no_grad():
        for s in range(0, len(rows), 250):
            b = batch_of(rows[s:s + 250], v)
            o = m.run(b, gold=m.gold(b['rows'], 'cpu'))
            for i, r in enumerate(b['rows']):
                t, f = pp.row_targets(r), r['family']
                n[f] += 1
                if not t['prog']:
                    continue
                nprog[f] += 1
                good = all(int(o['vals'][i, R0 + k]) == val and bool(o['valid'][i, R0 + k]) for k, (*_, val) in enumerate(t['prog']))
                if t['mode'] == 0:
                    good &= any(int(o['vals'][i, j]) == int(r['answer']) and bool(o['valid'][i, j]) for j in t['ans'])
                ok[f] += good
    print('  coverage (rows with a program / rows) and executor reproduction by family:')
    for f in sorted(n):
        if nprog[f]:
            print(f'    {f:16s} {nprog[f]:4d}/{n[f]:4d} programs ({100 * nprog[f] / n[f]:5.1f}%)  reproduced {ok[f]}/{nprog[f]}')
    print(f'  total: {sum(nprog.values())}/{sum(n.values())} rows have a program ({100 * sum(nprog.values()) / sum(n.values()):.1f}%), reproduced {sum(ok.values())}')
    assert sum(ok.values()) == sum(nprog.values()) > 400, 'executor failed on a gold program'
    print('ok executor')


def test_no_leak():
    v, rows = vocab(), train_rows(24, 1)
    m = Ledger(v, **SMALL).eval()
    b1, b2 = batch_of(rows, v), batch_of(rows, v)
    b2['rows'] = [{k: x for k, x in r.items() if k not in ('answer', 'steps', 'accepted')} for r in rows]
    b2['ans_ids'], b2['ans_mask'] = torch.zeros_like(b2['ans_ids']), torch.zeros_like(b2['ans_mask'])
    for kw in (dict(), dict(loops=0), dict(loops=1), dict(loops=2), dict(lesion='noexec'), dict(lesion='opswap')):
        s1, s2 = m.state(b1, **kw), m.state(b2, **kw)
        assert all(torch.equal(x, y) for x, y in zip(s1, s2)), kw
    assert m.talk(m.state(b1), b1) == m.talk(m.state(b2), b2)
    print('ok no_leak')


def test_word_pointer_content_free():
    """Relabel every letter by a bijection: the word keys are identical, and a given state copies the relabelled word."""
    v = vocab()
    rows = [r for r in train_rows(400, 2) if pp.row_targets(r)['mode'] == 1][:16]
    letters = [c for c in 'abcdefghijklmnopqrstuvwxyz']
    sh = letters[7:] + letters[:7]
    tr = str.maketrans(''.join(letters) + ''.join(letters).upper(), ''.join(sh) + ''.join(sh).upper())
    rows2 = [dict(r, prompt=r['prompt'].translate(tr)) for r in rows]
    m = Ledger(v, **SMALL).eval()
    b1, b2 = batch_of(rows, v), batch_of(rows2, v)
    with torch.no_grad():
        k1, k2 = (m.word_keys(*m.tokenize(b)[3:]) for b in (b1, b2))
        assert torch.equal(k1, k2)
        st = list(m.state(b1))
        st[3] = torch.tensor([0., 1, 0]).expand(len(rows), -1).clone()             # force WORD mode
        for w in (0, 3, 7):
            st[5] = torch.full_like(st[5], -1e9)
            st[5][:, w] = 0
            o1, o2 = m.talk(tuple(st), b1), m.talk(tuple(st), b2)
            for r, x, y in zip(rows, o1, o2):
                has = w < len(word_spans(r['prompt']))
                assert (x.translate(tr) == y) if has else (x == y), (w, x, y)
            assert any(w < len(word_spans(r['prompt'])) for r in rows)
    print('ok word_pointer_content_free')


def test_memorise():
    """16 rows (programs, word copies, generated answers) memorised to 100% by the whole model, greedy decode."""
    v = vocab()
    rows = train_rows(300, 3)
    pick = {0: [], 1: [], 2: []}
    for r in rows:
        pick[pp.row_targets(r)['mode']].append(r)
    rows = pick[0][:7] + pick[1][:4] + pick[2][:5]
    torch.manual_seed(0)
    m = Ledger(v, **SMALL)
    opt = torch.optim.AdamW(m.parameters(), lr=4e-3, weight_decay=0.0)
    b, t0 = batch_of(rows, v), time.time()
    for step in range(900):
        loss, aux = m.loss(b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad()
        if step % 25 == 24:
            m.eval()
            hit = sum(is_hit(p, r) for p, r in zip(m.generate(b), rows))
            m.train()
            if hit == len(rows) or time.time() - t0 > 150:
                break
    print(f'  {step + 1} steps, loss {loss.item():.4f}, exact {hit}/{len(rows)}, {time.time() - t0:.0f}s')
    assert hit == len(rows), f'memorised only {hit}/{len(rows)}'
    print('ok memorise')


def test_params():
    v = vocab()
    for name, cfg, target in (('S', S_CFG, 3244544), ('M', M_CFG, 10775040)):
        n = Ledger(v, **cfg).n_params()
        print(f'  {name}: {n:,} params ({100 * (n / target - 1):+.2f}% vs {target:,})')
        assert abs(n / target - 1) <= 0.03, name
    print('ok params')


def test_lesions_donor_extra():
    v, rows = vocab(), train_rows(48, 4)
    m = Ledger(v, **SMALL).eval()
    assert m.supports_donor() and m.n_loops == 8
    for les in [None] + m.LESIONS + [f'loops:{k}' for k in (0, 1, 2, 16)]:
        r = evaluate(m, rows, 32, 'cpu', les)
        assert r['n'] == 48
    b = batch_of(rows[:8], v)
    for loops in (0, 1, 2):                                   # K iterations = K-1 written results
        valid = m.run(b, loops=loops)['valid'][:, R0:]
        assert not valid[:, max(loops - 1, 0):].any()
    with torch.no_grad():
        g = m.gold(b['rows'], 'cpu')
        o = m.run(b, gold=g)
        nv = (o['valid'][:, R0:].sum(1) == torch.tensor([len(pp.row_targets(r)['prog']) for r in b['rows']]))
        assert nv.all()                                       # teacher-forced: exactly the gold program's results are valid
        assert not m.run(b, lesion='noexec')['valid'][:, R0:].any()
        o = m.run(b, gold=g, lesion='opswap')                 # the swapped run's results = its own program replayed with ADD<->SUB
        v2, ok2 = replay(o['vals'], o['valid'], *o['prog'], swap=True)
        assert torch.equal(v2[:, R0:] * ok2[:, R0:], o['vals'][:, R0:] * o['valid'][:, R0:])
        o0 = m.run(b, gold=g)
        v3, _ = replay(o0['vals'], o0['valid'], *o0['prog'])
        assert torch.equal(v3, o0['vals'])
    d = donor_eval(m, rows, 32, 'cpu')
    assert 'exact' in d and 'donor_match' in d
    tmp = tempfile.mkdtemp()
    os.makedirs(tmp + '/dev')
    dev = load_rows(os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl'))
    with open(tmp + '/dev/in_dist.jsonl', 'w') as f:
        for r in random.Random(0).sample(dev, 200):
            f.write(json.dumps(r) + '\n')
    import contextlib
    ex = m.extra_evals(dict(data=tmp, big=None, device=torch.device('cpu'), batch_size=64, amp=contextlib.nullcontext))
    json.dumps(ex)
    assert {'coverage', 'op_acc', 'noexec', 'opswap'} <= set(ex), set(ex)
    print('  extra_evals keys:', sorted(ex), '| op_acc', json.dumps(ex['op_acc']), '| opswap', json.dumps(ex['opswap']))
    print('ok lesions_donor_extra')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))      # small models: more threads only fight over a shared CPU
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
