"""python3 -m custom_io.tests.test_tool_h1   (CPU; needs the skills data at data.DEFAULT_DATA / $CUSTOM_IO_DATA)
H1 (learned rounds on T1, PASS-MARKS.md addendum 21): size and same-seed init, K = 8 with the stop head ignored reproduces T1 exactly (forced
loops:8 and the adaptive loop with cap 8 and a stop that never fires), each row's state is the one at its own stop round, the training loss
and its stop labels, the checkpoint round trip, the loop sweep and the queue file."""
import json, os, tempfile
import torch
import torch.nn as nn
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, collate, load_rows
from custom_io.models import build, load_model
from custom_io.models import tool_h1 as H
from custom_io.models.tool import Tool

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAND = (3147208, 3341880)
n_train = lambda m: sum(p.numel() for p in m.parameters() if p.requires_grad)


def setup(k=40, seed=0, steps=2):
    v = CharVocab.get(DEFAULT_DATA)
    rows = load_rows(os.path.join(DEFAULT_DATA, 'train.jsonl'), limit=4000)[::97][:k]
    ds = Dataset(rows, v, strict=False)
    b = collate([ds[i] for i in range(len(rows))])
    torch.manual_seed(seed)
    t1 = Tool(v)
    opt = torch.optim.Adam(t1.parameters(), lr=1e-3)
    for _ in range(steps):                              # a few steps so the weights are not the init (outputs differ per row)
        l, _ = t1.loss(b)
        opt.zero_grad(); l.backward(); opt.step()
    t1.eval()
    h = H.ToolH1(v)
    missing, extra = h.load_state_dict(t1.state_dict(), strict=False)
    assert sorted(missing) == ['stop.bias', 'stop.weight'] and not extra
    h.eval()
    return v, rows, b, t1, h


def test_size_and_init():
    v = CharVocab.get(DEFAULT_DATA)
    torch.manual_seed(200); a = Tool(v)
    torch.manual_seed(200); h = H.ToolH1(v)
    sa, sh = a.state_dict(), h.state_dict()
    assert all(torch.equal(sa[k], sh[k]) for k in sa), 'a T1 weight starts differently at the same seed'
    assert sorted(set(sh) - set(sa)) == ['stop.bias', 'stop.weight']
    assert (n_train(a), n_train(h)) == (3277393, 3277650) and BAND[0] <= n_train(h) <= BAND[1], (n_train(a), n_train(h))
    print('ok size', n_train(h))


def same(o1, o2):
    return all(torch.equal(o1[k], o2[k]) for k in ('R', 'lmode', 'lword', 'X', 'xm', 'ids')) and o1['calls'] == o2['calls']


def test_k8_is_t1():
    v, rows, b, t1, h = setup()
    torch.set_grad_enabled(False)
    for les in (None, 'noexec', 'opswap', 'nocopy', 'nowordc'):
        assert same(t1.run(b, lesion=les), h.run(b, loops=8, lesion=les)), les
    for les in ('loops:0', 'loops:1', 'loops:16'):
        assert t1.generate(b, les) == h.generate(b, les), les
    assert t1.generate(b) == h.generate(b, 'loops:8')
    h.cap = 8                                           # the adaptive loop itself, cap 8, a stop that never fires = T1
    nn.init.constant_(h.stop.bias, -1e4); nn.init.zeros_(h.stop.weight)
    o1, o2 = t1.run(b), h.run(b)
    assert same(o1, o2) and h.last_rounds == [8] * len(rows)
    for les in (None, 'noexec', 'opswap', 'nocopy', 'nowordc', 'zero_state', 'shuffle_state'):
        assert t1.generate(b, les) == h.generate(b, les), les
    for (a1, p1), (a2, p2) in zip(o1['steps'], o2['steps']):
        assert torch.equal(a1, a2) and torch.equal(p1, p2)
    torch.set_grad_enabled(True)
    print('ok K=8 with the stop ignored reproduces T1')


class FakeStop(nn.Module):
    """Row i stops after round (i % 6) + 1 (rows 5, 11, ... after round 6); one call per round."""
    def __init__(self, B):
        super().__init__()
        self.B, self.t = B, 0

    def forward(self, zf):
        self.t += 1
        want = torch.arange(zf.shape[0]) % 6 + 1
        return torch.where(want <= self.t, 10.0, -10.0)[:, None]


def test_own_stop_round():
    v, rows, b, t1, h = setup()
    torch.set_grad_enabled(False)
    h.stop = FakeStop(len(rows))
    o = h.run(b)
    u = h.last_rounds
    assert u == [i % 6 + 1 for i in range(len(rows))] and o['rounds'] == u
    full = h.run(b, loops=8)
    for k in sorted(set(u)):
        f = t1.run(b, loops=k)                          # rows are independent: row i's state = the forced run of its own length
        for i in [i for i in range(len(rows)) if u[i] == k]:
            for key in ('R', 'lmode', 'lword', 'X', 'xm', 'ids'):
                assert torch.equal(o[key][i], f[key][i]), (key, i, k)
            assert o['calls'][i] == f['calls'][i] == [c for c in full['calls'][i] if c[0] < k]
    for s, (lop, _) in enumerate(o['steps']):           # a stopped row makes no later call
        stopped = torch.tensor([x <= s + 1 for x in u])
        assert (lop[stopped].argmax(-1) == 0).all()
    h.stop = FakeStop(len(rows))
    ans = h.generate(b)
    assert len(ans) == len(rows)
    torch.set_grad_enabled(True)
    print('ok each row keeps its own stop round', sorted(set(u)))


def test_labels():
    r = torch.tensor([[0, 0, 0, 1], [0, 1, 0, 0], [1, 0, 1, 0], [1, 0, 0, 1]], dtype=torch.bool)   # [n=4 rounds, B=4 rows]
    want = torch.tensor([[0, 0, 0, 1], [0, 1, 0, 0], [1, 1, 1, 0], [1, 1, 1, 1]], dtype=torch.bool)
    assert torch.equal(H.settled(r), want), H.settled(r)
    assert torch.equal(H.settled(r[:1]), torch.ones(1, 4, dtype=torch.bool))
    print('ok settled labels')


def test_loss_and_roundtrip():
    v, rows, b, t1, h = setup(k=24, steps=1)
    for lab in H.LABELS:
        torch.manual_seed(0)
        m = build('tool_h1', v, label=lab)
        m._name, m._cfg = 'tool_h1', {'label': lab}
        opt = torch.optim.Adam(m.parameters(), lr=1e-3)
        seen = set()
        for _ in range(6):
            l, aux = m.loss(b)
            assert torch.isfinite(l) and 0 <= float(aux['stop_y']) <= 1, aux
            seen.add(int(aux['rounds']))
            opt.zero_grad(); l.backward(); opt.step()
        lmax = int((m.gold(rows, 'cpu')['op'] > 0).sum(1).max())
        assert seen == {max(k, lmax + 1) for k in H.KS} or seen < {max(k, lmax + 1) for k in H.KS}, (seen, lmax)   # n = max(K, longest program + 1)
        m.eval()
        out = m.generate(b)
        assert len(out) == len(rows) and all(1 <= u <= 32 for u in m.last_rounds)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'checkpoint.pt')
            torch.save(dict(name=m._name, chars=v.chars, cfg=m._cfg, model=m.state_dict()), p)
            m2 = load_model(p)
            assert m2.generate(b) == out and m2.last_rounds == m.last_rounds and m2.label == lab
    print('ok loss, labels and round trip')


def test_stop_loss_does_not_move_the_loop():
    """loss() with two different stop heads gives the same gradient on every other weight (the stop head's input is detached)."""
    v, rows, b, t1, h = setup(k=16, steps=0)
    h.train()
    ks, H.KS = H.KS, (16,)
    try:
        grads = []
        for w in (0.0, 3.0):
            nn.init.constant_(h.stop.weight, w)
            h.zero_grad()
            l, aux = h.loss(b)
            l.backward()
            grads.append({n: p.grad.clone() for n, p in h.named_parameters() if not n.startswith('stop.') and p.grad is not None})
            assert int(aux['rounds']) == 16
        assert grads[0].keys() == grads[1].keys() and all(torch.equal(grads[0][n], grads[1][n]) for n in grads[0])
    finally:
        H.KS = ks
    print('ok the stop loss reaches only the stop head')


def test_lesion_names_and_queue():
    from custom_io.train import lesion_names
    from custom_io.local_runner import parse_queue
    v = CharVocab.get(DEFAULT_DATA)
    torch.manual_seed(0)
    assert [x for x in lesion_names(Tool(v)) if x.startswith('loops')] == ['loops:0', 'loops:1', 'loops:2', 'loops:16']
    assert [x for x in lesion_names(H.ToolH1(v)) if x.startswith('loops')] == ['loops:0', 'loops:1', 'loops:2', 'loops:8', 'loops:16', 'loops:32']
    q40 = {r[0]: r[2] for r in parse_queue(os.path.join(HERE, 'queue_local', '40-pc-t1-screen.txt'))}
    q = parse_queue(os.path.join(HERE, 'queue_local', '49-pc-h1-screen.txt'))
    assert [r[0] for r in q] == ['H1_s200', 'H1_s201'], q
    for name, _, args, _ in q:
        ref = q40[name.replace('H1', 'T1')]
        i = args.index('--model')
        assert args[i + 1] == 'tool_h1' and json.loads(args[args.index('--cfg') + 1]) == {}
        swap = lambda xs: [('tool' if x == 'tool_h1' else x) for x in xs]
        assert swap(args) == ref, (args, ref)
    print('ok lesion names and queue 49')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
