"""python3 -m custom_io.tests.test_gain   (CPU; the real-data checks need the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
U0 (prompt BPE on plain_tf_steps, PASS-MARKS.md addendum 18) and W1 (global attention in B2's reader, addendum 19): sizes, the
same-seed init of every shared weight, the BPE itself, a train step, generation, the checkpoint round trip and the queue files."""
import json, os, tempfile
import torch
from custom_io.bpe import BPE, pretok, train
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, collate, load_rows
from custom_io.models import build, load_model

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAND = (3147208, 3341880)
n_train = lambda m: sum(p.numel() for p in m.parameters() if p.requires_grad)


def vocab():
    return CharVocab.get(DEFAULT_DATA)


def rows(k=48):
    return load_rows(os.path.join(DEFAULT_DATA, 'train.jsonl'), limit=k)


def batch(v, rs):
    ds = Dataset(rs, v, strict=False)
    return collate([ds[i] for i in range(len(rs))])


def same_seed(name, base, extra, seed=200):
    v = vocab()
    torch.manual_seed(seed); a = build(name, v, **base)
    torch.manual_seed(seed); b = build(name, v, **base, **extra)
    sa, sb = a.state_dict(), b.state_dict()
    assert all(torch.equal(sa[k], sb[k]) for k in sa), 'a shared weight starts differently at the same seed'
    return a, b, [k for k in sb if k not in sa]


def test_sizes_and_init():
    a, u, new = same_seed('plain_tf_steps', {}, {'bpe': 308})
    assert (n_train(a), n_train(u)) == (3260928, 3339776) and new == ['tok_m.weight'], (n_train(a), n_train(u), new)
    b, w, new = same_seed('ledger', {'copy': True}, {'gattn': 32})
    assert (n_train(b), n_train(w)) == (3302481, 3336113), (n_train(b), n_train(w))
    assert all(k.startswith('reader.glob.') for k in new) and len(new) == 10, new
    assert all(BAND[0] <= n <= BAND[1] for n in (n_train(u), n_train(w)))
    v = vocab()
    torch.manual_seed(200); a = build('plain_tf_steps', v)
    torch.manual_seed(200); c = build('plain_tf_steps', v, cap=107)
    sa, sc = a.state_dict(), c.state_dict()
    assert n_train(c) == 3271424 and c.pos.num_embeddings == 329 and c.max_new == 119 and (a.pos.num_embeddings, a.max_new) == (288, 76)
    assert all(torch.equal(sa[k], sc[k]) for k in sa if k != 'pos.weight') and BAND[0] <= n_train(c) <= BAND[1]
    print('ok sizes', n_train(u), n_train(w), n_train(c))


def test_bpe():
    texts = ['the cat sat on the mat', 'the cat ate 12 rats', 'then the rat sat']
    m1, m2 = train(texts, 6), train(list(texts), 6)
    assert m1 == m2 and len({a + b for a, b in m1}) == 6, m1          # deterministic, 6 new tokens
    assert ''.join(pretok('Facts: Nia had 85 pears.\nThen?')) == 'Facts: Nia had 85 pears.\nThen?'
    v = vocab()
    bpe = BPE(v)
    d = json.load(open(os.path.join(HERE, 'models', 'bpe_prompt.json')))
    assert bpe.n_new == 308 and bpe.base == len(v) == 108 and d['train_sha256'].startswith('010af671'), (bpe.n_new, bpe.base)
    for r in rows(200):
        ids = bpe.encode(r['prompt'])
        assert ''.join(bpe.tokens(r['prompt'])) == r['prompt'] and max(ids) < 416 and min(ids) >= 13
        assert all(i == v.stoi[c] for i, c in zip(ids, r['prompt']) if i < 108) or len(ids) < len(r['prompt'])
    print('ok bpe')


def check_model(m, v, rs):
    b = batch(v, rs)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    l0 = m.loss(b)
    l0 = l0[0] if isinstance(l0, tuple) else l0         # Ledger returns (loss, parts)
    assert torch.isfinite(l0)
    opt.zero_grad(); l0.backward(); opt.step()
    out = m.generate(b)
    assert len(out) == len(rs) and all(isinstance(x, str) for x in out)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'checkpoint.pt')
        torch.save(dict(name=m._name, chars=v.chars, cfg=m._cfg, model=m.state_dict()), p)
        m2 = load_model(p)
        m.eval()
        assert m2.generate(b) == m.generate(b)
    return out


def test_u0_runs():
    v = vocab()
    torch.manual_seed(0)
    m = build('plain_tf_steps', v, bpe=308)
    m._name, m._cfg = 'plain_tf_steps', {'bpe': 308}
    rs = rows(16)
    b = m._prompt(batch(v, rs))
    assert all(b['prompt_mask'][i].sum() == len(m.bpe.encode(r['prompt'])) for i, r in enumerate(rs))
    assert (b['prompt_ids'] >= 108).any()                                  # merged tokens are used
    check_model(m, v, rs)
    m.generate(batch(v, rs), 'calc')
    print('ok u0')


def test_w1_runs():
    v = vocab()
    torch.manual_seed(0)
    m = build('ledger', v, copy=True, gattn=32)
    m._name, m._cfg = 'ledger', {'copy': True, 'gattn': 32}
    rs = rows(16)
    check_model(m, v, rs)
    X, mask = m.reader(batch(v, rs))
    assert torch.isfinite(X).all() and (X[~mask] == 0).all()
    b = batch(v, rs[:2])                                                   # global: a far-away char now changes the first char's reading
    p = rs[0]['prompt']
    q = p[:-1] + ('?' if p[-1] != '?' else '.')
    X1, _ = m.reader(batch(v, [dict(rs[0], prompt=p)]))
    X2, _ = m.reader(batch(v, [dict(rs[0], prompt=q)]))
    assert len(p) > 12 and not torch.allclose(X1[0, 0], X2[0, 0])
    m.reader.glob = None
    X1, _ = m.reader(batch(v, [dict(rs[0], prompt=p)]))
    X2, _ = m.reader(batch(v, [dict(rs[0], prompt=q)]))
    assert torch.allclose(X1[0, 0], X2[0, 0])                              # without it the window is +-4 chars
    print('ok w1')


def test_c0_cap():
    from custom_io.models.plain_tf_steps import STEP_FAMILIES, target_text
    rs = [r for r in load_rows(os.path.join(DEFAULT_DATA, 'train.jsonl'), keep=('prompt', 'answer', 'family', 'steps'))
          if r.get('family') in STEP_FAMILIES and r.get('steps')]
    longest = max(len('; '.join(r['steps']) + ' # ' + r['answer']) for r in rs)
    assert longest == 107, longest                                                # the cap is the longest step target on train
    assert all(target_text(r, 107) != r['answer'] for r in rs)                    # no step row falls back to the answer alone
    assert sum(target_text(r) == r['answer'] for r in rs) == 840                  # 840 var_chain rows did at the old 64
    v = vocab()
    torch.manual_seed(0)
    m = build('plain_tf_steps', v, cap=107)
    m._name, m._cfg = 'plain_tf_steps', {'cap': 107}
    long = [r for r in rs if len(target_text(r, 107)) > 100][:8]
    b = batch(v, long)
    ids, _ = m._targets(b)
    assert ids.shape[1] == max(len(target_text(r, 107)) for r in long) + 1      # whole target + EOS, nothing cut
    check_model(m, v, long)
    print('ok c0')


def test_queues():
    from custom_io.local_runner import parse_queue
    q33 = {r[0]: r[2] for r in parse_queue(os.path.join(HERE, 'queue_local', '33-pc-confirm-b2.txt'))}
    for qf, arm, base, model, cfg in (('41-pc-gain-u0.txt', 'U0', 'tfsteps', 'plain_tf_steps', {'bpe': 308}),
                                      ('42-pc-gain-w1.txt', 'W1', 'B2', 'ledger', {'copy': True, 'gattn': 32}),
                                      ('43-pc-c0.txt', 'C0', 'tfsteps', 'plain_tf_steps', {'cap': 107})):
        q = parse_queue(os.path.join(HERE, 'queue_local', qf))
        assert [r[0] for r in q] == [f'{arm}_s200', f'{arm}_s201'], q
        for name, _, args, _ in q:
            assert args[-1] == '--save-preds'
            args = args[:-1]
            ref = q33[name.replace(arm, base)]
            strip = lambda xs: [x for i, x in enumerate(xs) if i == 0 or xs[i - 1] != '--cfg']
            assert strip(args) == strip(ref), (args, ref)
            assert args[args.index('--model') + 1] == model and json.loads(args[args.index('--cfg') + 1]) == cfg
    print('ok queues')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
