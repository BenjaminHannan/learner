"""python3 -m pytest creative/tests/test_dream2.py   (CPU, about a minute; tiny random B2)
Dream rows for C2 sleep (creative/dream2.py) and their wiring into v1/creative_sleep.py behind --dream2.
Never opens creative/data/c2/test.jsonl."""
import builtins
import json
import os

import torch

from creative import dream2 as D, fewshot as F, rules_real as R, sleep
from creative.programs import Try
from custom_io.data import CharVocab
from custom_io.models import progparse as pp
from custom_io.models.ledger import Ledger
from creative import sampler

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
VOCAB = CharVocab.build([])
DATA = 'creative/data/c2'


def _key(rows):
    return [(r['id'], r['prompt'], r['answer'], r['dream']['steps'], r['dream']['ans']) for r in rows]


def test_deterministic_by_seed():
    a, b, c = D.dream_rows_c2(60, 3), D.dream_rows_c2(60, 3), D.dream_rows_c2(60, 4)
    assert _key(a) == _key(b)
    assert [r['prompt'] for r in a] != [r['prompt'] for r in c]
    assert [r['prompt'] for r in D.dream_rows_c2(20, 3, night=1)] != [r['prompt'] for r in a[:20]]       # a new night draws new dreams
    assert len({r['id'] for r in a}) == 60 and len({r['prompt'] for r in a}) == 60


def test_every_row_passes_the_checker_and_the_forced_program_reproduces_the_label():
    rows = D.dream_rows_c2(200, 1, max_steps=3)
    assert {r['dream']['length'] for r in rows} == {1, 2, 3}
    m = Ledger(VOCAB, copy=True, **SMALL).eval()
    for r in rows:
        p = F.parse(r['prompt'])
        t = F.record_try(r)                                       # the forced program, recovered from the registered slot ids
        v = F.verdict(p, t)                                       # both executors (python ints + B2's torch replay), structure, every example
        assert v[0] == 'accept' and str(v[2]) == r['answer'], (r['prompt'], v)
        assert F.outputs_py(p, t) == F.outputs_torch(p, t) == r['dream']['ys'] + [int(r['answer'])]
        assert r['accepted'] == [r['answer']] and r['id'].startswith('D2:') and pp._CACHE[r['id']]['mode'] == 0
        assert all(0 <= y <= D.MAX_OUT for y in r['dream']['ys']) and not set(r['dream']['ys']) & set(D.CONST_VALUES)
    batch = sampler.make_batch(rows[:40], VOCAB, 'cpu')            # B2's own gold forcing reads the registered slot ids and gets the answer
    g = m.gold(batch['rows'], 'cpu')
    with torch.no_grad():
        o = m.run(batch, gold=g)
    for i, r in enumerate(rows[:40]):
        k = int(g['ans'][i].nonzero()[0])
        assert int(o['vals'][i, k]) == int(r['answer']) and bool(o['valid'][i, k])


def test_disjoint_from_warm_pool_dev_and_never_opens_test(monkeypatch):
    opened = []
    real_open = builtins.open

    def spy(file, *a, **k):
        opened.append(str(file))
        return real_open(file, *a, **k)
    monkeypatch.setattr(builtins, 'open', spy)
    rows = D.dream_rows_c2(1500, 0)
    monkeypatch.undo()
    assert not any('test.jsonl' in f or 'labelled.jsonl' in f for f in opened), opened
    prompts, keys = set(), set()
    for s in ('warm', 'pool', 'dev'):
        for r in R.load_split(DATA, s):
            prompts.add(r['prompt'])
            p = F.parse(r['prompt'])
            keys.add(frozenset(zip(p['xs'], p['ys'])))
    for r in rows:
        assert r['prompt'] not in prompts
        assert frozenset(zip(r['dream']['xs'], r['dream']['ys'])) not in keys
    # an extra avoid list is honoured (prompts and their example sets)
    extra = [r['prompt'] for r in rows[:50]]
    again = D.dream_rows_c2(300, 0, avoid_prompts=extra)
    assert not set(extra) & {r['prompt'] for r in again}


def test_kind_overlap_reports_planted_forms():
    # plant three dreams whose programs ARE a held-out / practised kind: x*x, x mod 10, x + 3 ... and check the counting
    def planted(steps, ans, f):
        xs = [5, 7, 9]
        q = 12
        t = Try.make(steps, ans)
        ys = [f(x) for x in xs]
        return dict(dream=dict(steps=steps, ans=ans, length=len(steps), xs=xs, ys=ys, q=q))
    rows = [planted([(3, 6, 6)], 20, lambda x: x * x), planted([(5, 6, 18)], 20, lambda x: x % 10), planted([(1, 6, 6), (1, 20, 17)], 21, lambda x: 2 * x + 2)]
    o = D.kind_overlap(rows)
    assert o['square']['n_same_function'] == 1 and o['last_digit']['n_same_function'] == 1
    assert o['affine']['n_same_function'] == 0 and o['sq_plus']['n_same_function'] == 0 and o['double_add']['n_same_function'] == 0
    o2 = D.kind_overlap(D.dream_rows_c2(100, 5))
    assert 0 <= o2['any_held_out_same_function'] <= 1 and o2['n'] == 100


def _tiny_workdir(tmp_path):
    torch.manual_seed(0)
    m = Ledger(VOCAB, copy=True, **SMALL)
    ck = str(tmp_path / 'b2.pt')
    sleep.save_parent(m, 'ledger', dict(copy=True, **SMALL), VOCAB, ck, step=0)
    sk = tmp_path / 'train.jsonl'
    with open(sk, 'w') as f:
        for i in range(64):
            f.write(json.dumps(dict(id=f'sk{i}', prompt=f'{i} + 1', answer=str(i + 1), accepted=[str(i + 1)], family='f', level=1, stage=1, variant='', steps=[])) + '\n')
    return ck, str(sk)


def test_flag_off_path_is_the_old_path(monkeypatch):
    from v1 import creative_sleep as CS
    import inspect
    assert inspect.signature(CS.run_creative).parameters['dream2'].default == 0
    recs = [{'id': 'W1:x:0'}]

    def boom(*a, **k):
        raise AssertionError('dream path touched with the flag off')
    monkeypatch.setattr(D, 'dream_rows_c2', boom)
    out, info = CS.add_dreams(recs, {}, [], 0, 0, 1)
    assert out is recs and info is None                     # the very same list: nothing copied, nothing appended


def test_flag_on_end_to_end_and_off_is_unchanged(tmp_path):
    """Tiny random B2, capped sleep. dream2=0 twice gives identical records and weights (nothing in the old path moved); dream2=N adds exactly N records per night,
    registered in the cache, within the visit cap, and the night sleeps on them."""
    from v1 import creative_sleep as CS
    ck, sk = _tiny_workdir(tmp_path)
    common = dict(device='cpu', seed=0, pool_limit=6, dev_limit=4, n1=2, n2=2, T=1.0, updates_cap=2)
    off1 = CS.run_creative(str(tmp_path / 'off1'), ck, sk, None, **common)
    off2 = CS.run_creative(str(tmp_path / 'off2'), ck, sk, None, dream2=0, **common)
    assert off1['stages'] == off2['stages'] and 'dream2' not in off1 and 'dream2' not in off2
    for night in (1,):
        pa, pb = tmp_path / 'off1' / f'rec_W{night}.pt', tmp_path / 'off2' / f'rec_W{night}.pt'
        if pa.exists() or pb.exists():
            a, b = torch.load(pa, weights_only=False), torch.load(pb, weights_only=False)
            assert [r['id'] for r in a['records']] == [r['id'] for r in b['records']] and a['info'] == b['info']
    on = CS.run_creative(str(tmp_path / 'on'), ck, sk, None, dream2=12, **common)
    assert on['night1_records'] >= 12 and on['dream2']['1']['n'] == 12
    d = torch.load(tmp_path / 'on' / 'rec_W1.pt', weights_only=False)
    dreams = [r for r in d['records'] if r['id'].startswith('D2:')]
    assert len(dreams) == 12 and all(r['id'] in d['cache'] for r in dreams) and d['info']['dream2']['n'] == 12
    assert (tmp_path / 'on' / 'W1.pt').exists()


def test_tiny_random_b2_overfits_a_few_dream_rows():
    rows = D.dream_rows_c2(8, 11, max_steps=2)
    torch.manual_seed(0)
    m = Ledger(VOCAB, copy=True, **SMALL)
    cfg = sleep.SleepCfg(updates=60, batch=8, lr=2e-3, warmup=3, seed=0, max_visits=10 ** 6)
    out = sleep.sleep(m, rows, [], VOCAB, cfg)
    loss = out['loss']
    assert out['updates'] == 60
    first, last = sum(loss[:5]) / 5, sum(loss[-5:]) / 5
    print('dream overfit loss', round(first, 3), '->', round(last, 3))
    assert last < 0.6 * first, (first, last)
