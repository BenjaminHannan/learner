"""python3 -m pytest creative/tests/test_bidc_caps.py   (CPU, about 30 s; a tiny random Ledger, C2 dev rows)
Bid C draft: the creative samplers re-run the Ledger's loop and used a hard-coded 9 register tokens, so under custom_io/caps/caps-bidc.json (36 registers) they
computed something else than Ledger.run without any error. They now read ledger.N_REG at call time."""
import os
import pytest
import torch
from custom_io import caps
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import c2_stones, legal, rules_real as R, sampler

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
VOCAB = CharVocab.build([])
BIDC = os.path.join(os.path.dirname(caps.__file__), 'caps', 'caps-bidc.json')


@pytest.fixture(autouse=True)
def fresh_globals():
    caps.APPLIED = None
    yield
    caps.apply(caps.TODAY)
    caps.APPLIED = None


def model():
    torch.manual_seed(0)
    return Ledger(VOCAB, copy=True, **SMALL).eval()


def check_equal_to_run(m, rows):
    batch = sampler.make_batch(rows, VOCAB, 'cpu')
    with torch.no_grad():
        o = m.run(batch)
        g = sampler.sample_run(m, batch, greedy=True)
        g0 = legal.sample_run_masked(m, batch, legal._k(rows), 0, greedy=True)
        lo = sampler.sample_run(m, batch, stop_at=1)
    for x in (g, g0):
        assert torch.equal(x['ops'], o['prog'][0]) and torch.equal(x['a'], o['prog'][1]) and torch.equal(x['b'], o['prog'][2])
        assert torch.equal(x['ans'], o['lans'].argmax(-1)) and torch.equal(x['vals'], o['vals'])
    assert torch.equal(lo['lop'], o['steps'][0][0].float()) and torch.equal(lo['la'], o['steps'][0][1].float())
    return o


def test_sampler_equals_ledger_run_at_today_and_under_bidc_caps():
    rows = c2_stones._with_nums(R.load_split('creative/data/c2', 'dev')[:6])
    m = model()
    check_equal_to_run(m, rows)
    caps.apply_file(BIDC)
    m2 = model()                                         # place table 37 rows, 36 register tokens
    assert m2.reader.place.weight.shape[0] == 37
    check_equal_to_run(m2, rows)


def test_masked_sampler_step1_uses_the_same_register_tokens():
    """legal.sample_run_masked has its own copy of the loop: its level-4 step-1 joint is the plain sampler's step-1 logits, masked."""
    rows = c2_stones._with_nums(R.load_split('creative/data/c2', 'dev')[:4])
    caps.apply_file(BIDC)
    m = model()
    b = sampler.make_batch(rows, VOCAB, 'cpu')
    lo = sampler.sample_run(m, b, stop_at=1)
    masked = legal.sample_run_masked(m, b, legal._k(rows), 4, stop_at=1)
    joint = (lo['lop'].log_softmax(-1)[:, :, None, None] + lo['la'].log_softmax(-1)[:, None, :, None] + lo['lb'].log_softmax(-1)[:, None, None, :])
    ok = masked['allow']
    assert ok.any() and torch.allclose(masked['joint'][ok], joint[ok], atol=1e-6)
