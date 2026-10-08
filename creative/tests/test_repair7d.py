"""python3 -m creative.tests.test_repair7d   (CPU, 2 threads, under a minute; uses ~/c7d/s100/Nprime.pt when present, else a tiny random Ledger)
The held slice (own TRAIN rows only, disjoint from the repair rows, 100 per family, deterministic); repair trains only on the firing family's non-held rows and stops when nothing fires;
spread draws evenly over all families with the given update count; no DEV / sealed file is opened inside repair / spread."""
import builtins, copy, os
import torch
from creative import repair7d as P, sleep
from custom_io.data import load_rows

CKPT = '~/c7d/s100/Nprime.pt'
TRAIN = os.path.expanduser('~/work/data/train.jsonl')
SEALED = ('data/c2/test.jsonl', 'data/c2/labelled.jsonl', 'data/c2rl/holdout.jsonl', 'knew/test.jsonl')
_CACHE = {}
torch.set_num_threads(2)


def _train():
    if 'rows' not in _CACHE:
        _CACHE['rows'] = load_rows(TRAIN)[::10]                 # every 10th row of the whole file: all 34 families
    return _CACHE['rows']


def _model():
    if 'm' not in _CACHE:
        path = os.path.expanduser(CKPT)
        if os.path.exists(path):
            m, vocab, _ = sleep.load_parent(path, 'cpu')
        else:
            from custom_io.data import CharVocab
            from custom_io.models.ledger import Ledger
            vocab = CharVocab.build(_train())
            torch.manual_seed(0)
            m = Ledger(vocab, d=32, n_heads=2, reader_layers=1, blocks=2, n_loops=8, mlp=2.0)
        m.eval()
        _CACHE['m'] = (m, vocab)
    m, vocab = _CACHE['m']
    return copy.deepcopy(m), vocab


class _Spy:
    """Stand-in for sleep.sleep: records (records, replay_rows, cfg) and trains nothing."""
    def __init__(self):
        self.calls = []

    def __call__(self, model, records, replay_rows, vocab, cfg, device='cpu', **kw):
        self.calls.append((list(records), list(replay_rows), cfg))
        return dict(loss=[], visits={}, updates=cfg.updates)


def _patched(fn, spy, hits=None):
    orig_s, orig_h = sleep.sleep, P.held_hits
    sleep.sleep = spy
    if hits:
        P.held_hits = hits
    try:
        return fn()
    finally:
        sleep.sleep, P.held_hits = orig_s, orig_h


def test_held_split():
    rows = _train()
    held, pool = P.held_split(rows, 5, seed=0)
    fams = {r['family'] for r in rows}
    assert len(fams) == 34 and set(pool) == fams and len(held) == 5 * 34
    ids = {r['id'] for r in rows}
    hid = {r['id'] for r in held}
    assert hid <= ids and len(hid) == len(held)                                   # own TRAIN rows only
    assert all(sum(r['family'] == f for r in held) == 5 for f in fams)
    pid = {r['id'] for v in pool.values() for r in v}
    assert not hid & pid and hid | pid == ids                                      # disjoint, and together the whole file
    assert all(r['family'] == f for f, v in pool.items() for r in v)
    h2, p2 = P.held_split(rows, 5, seed=0)
    assert [r['id'] for r in h2] == [r['id'] for r in held] and all([r['id'] for r in p2[f]] == [r['id'] for r in pool[f]] for f in pool)   # deterministic
    assert [r['id'] for r in P.held_split(rows, 5, seed=1)[0]] != [r['id'] for r in held]
    h100, _ = P.held_split(rows, 100, seed=0)
    assert len(h100) == 3400


def test_repair_trains_only_the_firing_family():
    rows = _train()
    held, pool = P.held_split(rows, 5, seed=0)
    m, vocab = _model()
    f = sorted(pool)[3]
    pre = [1 if r['family'] == f else 0 for r in held]                              # pre all 1s for f: the (all-0) post check makes it fire
    spy = _Spy()
    _, info = _patched(lambda: P.repair(m, pre, held, pool, vocab, 'cpu', 0, rounds=2, updates=7, n_records=40, log=lambda *a: None), spy, hits=lambda *a, **k: [0] * len(held))
    assert [x['fired'] for x in info['rounds']] == [[f], [f], [f]] and info['updates'] == 14 and len(spy.calls) == 2
    hid = {r['id'] for r in held}
    for recs, replay, cfg in spy.calls:
        assert replay == [] and cfg.updates == 7 and cfg.batch == 64 and cfg.lr == 1e-3 and cfg.warmup == 10   # replay-only: the whole batch is records
        assert len(recs) == 40 and {r['family'] for r in recs} == {f} and not {r['id'] for r in recs} & hid
        assert len({r['id'] for r in recs}) == 40 and cfg.max_visits * len(recs) >= cfg.updates * cfg.batch
    assert spy.calls[0][0] != spy.calls[1][0]                                       # a new seeded draw per round
    assert info['rounds'][0]['records_by_family'] == {f: 40} and info['rounds'][2]['updates'] == 0
    assert info['rounds'][0]['families'][f]['fires'] and info['rounds'][0]['in_dist'] == 0.0


def test_repair_stops_when_nothing_fires():
    rows = _train()
    held, pool = P.held_split(rows, 5, seed=0)
    m, vocab = _model()
    spy = _Spy()
    ones = [1] * len(held)
    _, info = _patched(lambda: P.repair(m, ones, held, pool, vocab, 'cpu', 0, log=lambda *a: None), spy, hits=lambda *a, **k: list(ones))
    assert not spy.calls and info['updates'] == 0 and len(info['rounds']) == 1 and info['rounds'][0]['fired'] == [] and info['rounds'][0]['passes']


def test_repair_two_families_evenly():
    rows = _train()
    held, pool = P.held_split(rows, 5, seed=0)
    m, vocab = _model()
    fs = sorted(pool)[:2]
    pre = [1 if r['family'] in fs else 0 for r in held]
    spy = _Spy()
    _patched(lambda: P.repair(m, pre, held, pool, vocab, 'cpu', 0, rounds=1, updates=3, n_records=40, log=lambda *a: None), spy, hits=lambda *a, **k: [0] * len(held))
    recs = spy.calls[0][0]
    assert {f: sum(r['family'] == f for r in recs) for f in fs} == {fs[0]: 20, fs[1]: 20} and len(recs) == 40


def test_spread_even_over_all_families():
    rows = _train()
    held, pool = P.held_split(rows, 5, seed=0)
    m, vocab = _model()
    spy = _Spy()
    _patched(lambda: P.spread(m, 12, pool, vocab, 'cpu', 0, n_records=34 * 3), spy)
    recs, replay, cfg = spy.calls[0]
    assert cfg.updates == 12 and replay == [] and len(recs) == 102
    assert {r['family'] for r in recs} == set(pool) and all(sum(r['family'] == f for r in recs) == 3 for f in pool)
    assert not {r['id'] for r in recs} & {r['id'] for r in held}
    spy = _Spy()
    m2, info = _patched(lambda: P.spread(m, 0, pool, vocab, 'cpu', 0), spy)
    assert not spy.calls and info['updates'] == 0                                  # R used 0 updates: E does nothing
    assert all(torch.equal(a, b) for a, b in zip(m.state_dict().values(), m2.state_dict().values()))


def test_real_sleep_plumbing():
    """Unpatched: two real replay-only updates on skills rows move the model and leave the argument alone."""
    rows = _train()
    held, pool = P.held_split(rows, 2, seed=0)
    m, vocab = _model()
    before = copy.deepcopy(m.state_dict())
    m2, info = P.spread(m, 2, pool, vocab, 'cpu', 0, n_records=64)
    assert info['updates'] == 2 and any(not torch.equal(before[k], v) for k, v in m2.state_dict().items())
    assert all(torch.equal(before[k], v) for k, v in m.state_dict().items()) and not m2.training


def test_no_dev_or_sealed_reads():
    """repair / spread open no file at all (so no DEV, no sealed file); the held check itself is the real evaluate."""
    rows = _train()
    held, pool = P.held_split(rows, 1, seed=0)
    m, vocab = _model()
    seen = []
    orig = builtins.open

    def spy(f, *a, **k):
        seen.append(str(f))
        return orig(f, *a, **k)
    builtins.open = spy
    try:
        pre = P.held_hits(m, held)
        _patched(lambda: P.repair(m, [1] * len(held), held, pool, vocab, 'cpu', 0, rounds=1, updates=2, n_records=8, log=lambda *a: None), _Spy())
        P.spread(m, 1, pool, vocab, 'cpu', 0, n_records=34)
    finally:
        builtins.open = orig
    assert len(pre) == len(held) and not [s for s in seen if 'dev' in s or 'in_dist' in s or any(s.endswith(x) for x in SEALED)], seen


if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'):
            v()
            print('ok', k)
