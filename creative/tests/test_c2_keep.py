"""python3 -m creative.tests.test_c2_keep   (CPU, ~1 min) job 7 pieces: replay half-batch split, default sleep unchanged, per-parent verdicts, PC' covers multi-step pool questions only."""
import random
import torch
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import c2_keep as K, c2_stones, fewshot as F, rules_real as R, sleep

SMALL = dict(d=48, n_heads=2, reach_layers=None)


def test_verdicts():
    assert K.verdict_parent(True, False, (0, 0, 0)).startswith('parts not kept')
    assert K.verdict_parent(False, True, (0, 0, 0)).startswith('feasibility miss')
    assert K.verdict_parent(True, True, (12.0, 4.0, 19.0)) == 'climb pass (this parent)'
    assert K.verdict_parent(True, True, (12.0, -1.0, 19.0)).startswith('between')
    assert K.verdict_parent(True, True, (0.5, -2.0, 2.5)).startswith('proved wrong')


def test_pc_multi_only_multistep():
    pool = c2_stones._with_nums(R.load_split('creative/data/c2', 'pool')[:200])
    pc = K.pc_multi(pool)
    assert len(pc) == sum(r['kind'] in K.MULTI for r in pool) and pc
    by = {r['id']: r for r in pool}
    for rec in pc[:30]:
        r = by[rec['source']]
        assert F.verdict(F.parse(r['prompt']), F.record_try(rec))[0] == 'accept'


def test_replay_split_half_and_half():
    """Each batch: 32 puzzle rows, 16 skills replay rows, 16 extra rows (the warm add/mult rows); without replay_extra it stays 32 + 32."""
    seen = []
    real = sleep.Dataset

    class Spy:
        def __init__(self, rows, vocab, strict=False):
            seen.append([r['id'][0] for r in rows])
            raise StopIteration

    vocab = CharVocab.build([])
    m = Ledger(vocab, d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
    rows = lambda tag, k: [dict(id=f'{tag}{i}', prompt='1 + 1', answer='2', accepted=['2'], family='f', level=1, stage=1, variant='', steps=[]) for i in range(k)]
    cfg = sleep.SleepCfg(updates=1, batch=64, lr=1e-4, warmup=1, seed=0, max_visits=10 ** 6)
    sleep.Dataset = Spy
    try:
        for extra in (rows('e', 40), None):
            try:
                sleep.sleep(m, rows('p', 64), rows('s', 50), vocab, cfg, 'cpu', replay_extra=extra)
            except StopIteration:
                pass
    finally:
        sleep.Dataset = real
    a, b = seen
    assert (a.count('p'), a.count('s'), a.count('e')) == (32, 16, 16), a
    assert (b.count('p'), b.count('s'), b.count('e')) == (32, 32, 0), b


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
