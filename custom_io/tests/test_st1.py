"""python3 -m custom_io.tests.test_st1   (CPU, seconds; no data files). ST1 against a fake model: keep / filter counts, the 1:1 mix, seeding, updates per round."""
import torch
import torch.nn as nn
from custom_io import st1

QA = [dict(id=f'q{i}', family=('copy_word', 'add_story', 'sum_list')[i % 3], prompt=f'Q{i}', answer=str(i), accepted=[str(i)] if i % 2 else None) for i in range(30)]
TR = [dict(id=f't{i}', family='chain_ops', prompt=f'T{i}', answer=str(i)) for i in range(40)]


class Fake(nn.Module):
    """Right on questions with id % 5 == 0 (every draw); on id % 5 == 1 right only when the generator draw is < 0.5; wrong otherwise."""

    def __init__(self):
        super().__init__()
        self.w = nn.Parameter(torch.zeros(1))
        self.seen_trace_rows, self.seen_plain_rows = [], []

    def sample_traces(self, batch, temperature, generator):
        assert not torch.is_grad_enabled() and not self.training
        out = []
        for r in batch['rows']:
            i, u = int(r['id'][1:]), float(torch.rand(1, generator=generator))
            ok = i % 5 == 0 or (i % 5 == 1 and u < 0.5)
            out.append(dict(calls=[(f'add {i} 1', str(i + 1))], answer=(str(i) if ok else 'x') + (' ' if i % 4 == 0 else '')))
        return out

    def trace_loss(self, batch, traces):
        assert len(traces) == len(batch['rows']) and self.training
        self.seen_trace_rows += [r['id'] for r in batch['rows']]
        assert all(str(int(r['id'][1:])) == t['answer'].strip() for r, t in zip(batch['rows'], traces))
        return (self.w - 1).pow(2).sum(), {}

    def loss(self, batch):
        self.seen_plain_rows += [r['id'] for r in batch['rows']]
        return (self.w - 0.5).pow(2).sum(), {}


class Opt(torch.optim.SGD):
    steps = 0

    def step(self, *a, **k):
        Opt.steps += 1
        return super().step(*a, **k)


mk = lambda rows: dict(rows=list(rows))


def run(seed, **kw):
    m = Fake()
    Opt.steps = 0
    o = Opt(m.parameters(), lr=0.5)
    logs = []
    s = st1.self_teach(m, QA, TR, mk, o, seed=seed, log=logs.append, **kw)
    return m, o, s, logs


def test_keep_and_mix():
    m, o, s, logs = run(0, rounds=3, k=4, updates=7, batch_size=8)
    assert Opt.steps == 3 * 7 and [r['updates'] for r in s['rounds']] == [7, 7, 7]          # the optimizer stepped `updates` times per round
    r = s['rounds'][0]
    sure = [q for q in QA if int(q['id'][1:]) % 5 == 0]
    assert r['kept']['copy_word'] + r['kept']['add_story'] + r['kept'].get('sum_list', 0) == r['kept_total']
    assert r['samples'] == {'copy_word': 40, 'add_story': 40, 'sum_list': 40} and r['asked'] == {'copy_word': 10, 'add_story': 10, 'sum_list': 10}
    # sure rows: right on all 4 draws but the 4 traces are identical -> kept once; i%5==1 rows: kept when some draw < 0.5 (also once); wrong rows never kept
    assert r['kept_total'] >= len(sure) and r['kept_total'] <= len(sure) + 6
    assert all(int(i[1:]) % 5 in (0, 1) for i in m.seen_trace_rows)
    assert r['questions_with_kept'] == r['kept_total']
    assert len(m.seen_trace_rows) == len(m.seen_plain_rows) == 3 * 7 * 4                  # 1:1 mix: batch 8 = 4 kept traces + 4 ordinary rows
    assert all(i.startswith('t') for i in m.seen_plain_rows) and all(i.startswith('q') for i in m.seen_trace_rows)
    assert any('round 1' in x and 'copy_word' in x for x in logs)
    assert abs(o.param_groups[0]['lr'] - 1e-4) < 1e-12                                     # the fixed lr, set from the default
    assert r['loss_last'] < r['loss_first']                                                # the fake loss (w-1)^2, (w-0.5)^2 mix is optimised
    print('ok keep_and_mix', r['kept_total'], r['kept'])


def test_checker():
    assert st1.right('7 ', dict(answer='7', accepted=['7'])) and not st1.right('8', dict(answer='7', accepted=['7']))
    assert st1.right(' Seven ', dict(answer='seven')) and not st1.right('six', dict(answer='seven'))
    assert st1.right('1,000', dict(answer='1000', accepted=['1,000', '1000']))
    print('ok checker')


def test_seed():
    a, b = run(3, rounds=2, updates=5, batch_size=8), run(3, rounds=2, updates=5, batch_size=8)
    c = run(4, rounds=2, updates=5, batch_size=8)
    assert a[0].seen_trace_rows == b[0].seen_trace_rows and a[0].seen_plain_rows == b[0].seen_plain_rows and a[2]['rounds'] == b[2]['rounds']
    assert torch.equal(a[0].w, b[0].w)
    assert a[0].seen_plain_rows != c[0].seen_plain_rows
    torch.manual_seed(0)
    x = torch.rand(1)
    torch.manual_seed(0)
    run(3, rounds=1, updates=2, batch_size=8)
    assert torch.equal(x, torch.rand(1))                                                   # the global torch stream is untouched
    print('ok seed')


def test_nothing_kept():
    class Wrong(Fake):
        def sample_traces(self, batch, temperature, generator):
            return [dict(calls=[], answer='nope') for _ in batch['rows']]
    m = Wrong()
    Opt.steps = 0
    s = st1.self_teach(m, QA, TR, mk, Opt(m.parameters(), lr=0.1), rounds=2, updates=5, batch_size=8, log=lambda *_: None)
    assert Opt.steps == 0 and all(r['stalled'] and r['kept_total'] == 0 for r in s['rounds'])
    print('ok nothing_kept')


if __name__ == '__main__':
    for f in (test_keep_and_mix, test_checker, test_seed, test_nothing_kept):
        f()
    print('ALL OK')
