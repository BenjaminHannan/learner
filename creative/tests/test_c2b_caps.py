"""python3 -m pytest creative/tests/test_c2b_caps.py   (CPU, about 1 minute; tiny random Ledger parents, no real checkpoints)
Bid C draft, creative/c2b.py: --caps (applied before load_parent; every train / score entry point asserts it ran, by sha256), --parents, --test. The defaults are the C2b behaviour."""
import hashlib, json, os, tempfile
import pytest
import torch
from custom_io import caps
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import c2_stones, c2b as C, rules_real as R, sleep, stones
from creative.tests.test_c2b import _fake_parent

BIDC = os.path.join(os.path.dirname(caps.__file__), 'caps', 'caps-bidc.json')
OLD = os.path.join(os.path.dirname(caps.__file__), 'caps', 'caps-old-defaults.json')
SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, copy=True)
KINDS = ('affine', 'square', 'sq_plus', 'last_digit', 'double_add')


@pytest.fixture(autouse=True)
def fresh_globals():
    caps.APPLIED = None
    yield
    caps.apply(caps.TODAY)
    caps.APPLIED = None


def test_defaults_are_c2b():
    a = C.parse_args(['score', '--root', 'x'])
    assert a.parents == C.PARENTS == ('s200', 's201', 's202', 's203', 's204', 's205') and a.caps is None and a.test is None
    assert C.test_path() == os.path.abspath('creative/data/c2/test.jsonl')
    a = C.parse_args(['check', '--root', 'x', '--parents', 's700,s701', '--caps', BIDC])
    assert a.parents == ('s700', 's701') and a.caps == BIDC
    for bad in (['train', '--parents', 's1'], ['train', '--test', 'a.jsonl'], ['check', '--test', 'a.jsonl'], ['score', '--parents', ',']):
        with pytest.raises(SystemExit):
            C.parse_args(bad)


def test_caps_info_asserts_the_given_file_was_applied():
    assert C.caps_info(None) is None
    with pytest.raises(AssertionError, match='has not run'):
        C.caps_info(BIDC)
    caps.apply_file(OLD)
    with pytest.raises(AssertionError):
        C.caps_info(BIDC)
    caps.apply_file(BIDC)
    rec = C.caps_info(BIDC)
    assert rec['sha256'] == hashlib.sha256(open(BIDC, 'rb').read()).hexdigest() and rec['values']['n_reg'] == 36 and rec['path'] == os.path.abspath(BIDC)


def test_every_entry_point_asserts_before_loading_anything():
    with tempfile.TemporaryDirectory() as root:
        calls = (lambda: C.train_parent(os.path.join(root, 'p'), '/nonexistent.pt', caps=BIDC),
                 lambda: C.score_test(root, caps=BIDC),
                 lambda: C.score_parent(root, 's700', None, None, [], [], 'cpu', 0, caps=BIDC))
        for call in calls:
            with pytest.raises(AssertionError, match='has not run'):
                call()
        assert os.listdir(root) == []                                   # nothing created, nothing read
        caps.apply_file(OLD)
        for call in calls:
            with pytest.raises(AssertionError):
                call()


def test_main_applies_caps_before_the_entry_point(monkeypatch):
    seen = {}
    monkeypatch.setattr(C, 'train_parent', lambda *a, **k: seen.update(applied=caps.APPLIED and caps.APPLIED['sha256'], caps=k['caps']))
    C.main(['train', '--out', 'x', '--ckpt', 'y', '--caps', BIDC])
    assert seen == dict(applied=hashlib.sha256(open(BIDC, 'rb').read()).hexdigest(), caps=BIDC)


def test_train_parent_records_caps_and_refuses_other_caps(monkeypatch):
    class Stop(Exception):
        pass
    def stop(*a, **k):
        raise Stop
    monkeypatch.setattr(C.R, 'warm_records', lambda rows: [])
    monkeypatch.setattr(C.c2_stones, '_warm', stop)
    caps.apply_file(BIDC)
    with tempfile.TemporaryDirectory() as root:
        out = os.path.join(root, 's700')
        with pytest.raises(Stop):                                       # the assert passed; it died at the first checkpoint load
            C.train_parent(out, '/nonexistent.pt', caps=BIDC, pool_limit=4)
        info = json.load(open(os.path.join(out, 'train.json')))
        assert info['caps']['sha256'] == caps.APPLIED['sha256'] and info['caps']['values']['max_ans'] == 35
        caps.apply_file(OLD)                                            # same dir, other caps
        with pytest.raises(SystemExit, match='REFUSED'):
            C.train_parent(out, '/nonexistent.pt', caps=OLD)
        with pytest.raises(SystemExit, match='REFUSED'):                # and no caps at all
            C.train_parent(out, '/nonexistent.pt')


def write_test_dir(rows):
    d = tempfile.mkdtemp()
    path = os.path.join(d, 'test.jsonl')
    with open(path, 'w') as f:
        f.write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    man = {'test': dict(n=len(rows), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(), kinds={})}
    json.dump(man, open(os.path.join(d, 'MANIFEST.json'), 'w'))
    return path


def test_load_test_default_and_path():
    rows, info = C.load_test(limit=5)
    assert len(rows) == 5 and info['n'] == 512 and info['sha256'] == json.load(open('creative/data/c2/MANIFEST.json'))['test']['sha256']
    some = R.load_split('creative/data/c2', 'dev')[:7]
    path = write_test_dir(some)
    rows, info = C.load_test(path)
    assert [r['id'] for r in rows] == [r['id'] for r in some] and info == dict(path=path, sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(), n=7)
    assert all('nums' in r for r in rows)
    with open(path, 'a') as f:
        f.write('\n')
    with pytest.raises(AssertionError, match='sealed hash'):
        C.load_test(path)
    with pytest.raises(AssertionError, match='jsonl'):
        C.load_test(path + '.txt')


def fake_root(parents):
    root = tempfile.mkdtemp()
    for p in parents:
        os.makedirs(os.path.join(root, p))
        for f in C.FILES:
            open(os.path.join(root, p, f), 'w').close()
    return root


def test_score_test_parents_test_and_caps_in_the_outputs(monkeypatch):
    parents = ('s700', 's701')
    some = R.load_split('creative/data/c2', 'dev')[:20]
    path = write_test_dir(some)
    with pytest.raises(SystemExit) as e:                                # --parents: the missing list names these, not s200..s205
        C.score_test(fake_root(()), parents=parents)
    assert 's700' in str(e.value) and 's200' not in str(e.value)
    per = [_fake_parent(p, 0.3) for p in parents]
    for p in per:
        for a in ('N', 'W', 'R', 'H', 'M'):
            p[a]['by_kind'] = {k: dict(first_try=p[a]['first_try'], reach4=0, reach32=0) for k in KINDS}
    got = {}
    def fake_score_parent(root, parent, st, sd, test, fresh, device, seed, caps=None, test_rec=None):
        got[parent] = (caps, test_rec, len(test))
        return dict(next(x for x in per if x['parent'] == parent), caps=C.caps_info(caps), test=test_rec)
    monkeypatch.setattr(C, 'score_parent', fake_score_parent)
    monkeypatch.setattr(C.blind_baseline, 'score_rows', lambda rows, workers=1: dict(n=len(rows)))
    monkeypatch.setattr(C.stones, 'fresh_practised', lambda *a: ([], None))
    caps.apply_file(BIDC)
    root = fake_root(parents)
    rep = C.score_test(root, parents=parents, caps=BIDC, test_file=path)
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    assert rep['test'] == dict(path=path, sha256=sha, n=20) and rep['caps']['sha256'] == caps.APPLIED['sha256'] and rep['blind_baseline'] == dict(n=20, test_sha256=sha)
    assert rep['parents'] == list(parents) and rep['n_questions'] == 20 and got['s700'][2] == 20
    assert json.load(open(os.path.join(root, 'TEST-OPENED.json')))['caps']['sha256'] == caps.APPLIED['sha256']
    assert json.load(open(os.path.join(root, 'REPORT.json')))['test']['sha256'] == sha


def tiny_parent(root, name, test_rec_caps):
    """A parent dir with the files score_parent reads, from one tiny random Ledger (all five arms are the same weights)."""
    torch.manual_seed(1)
    v = CharVocab.build([])
    m = Ledger(v, **SMALL)
    d = os.path.join(root, name)
    os.makedirs(d)
    for f in ('Nprime', 'W2', 'R2', 'H2'):
        sleep.save_parent(m, 'ledger', SMALL, v, os.path.join(d, f + '.pt'), step=0)
    C.save_recs(os.path.join(d, 'M_final.pt'), [], rep=dict(recall_on=False))
    json.dump(dict(T=1.0, base5=None), open(os.path.join(d, 'setup.json'), 'w'))
    json.dump(dict(caps=test_rec_caps), open(os.path.join(d, 'train.json'), 'w'))
    return d


def test_score_parent_end_to_end_under_the_bidc_caps():
    """A tiny parent built and scored under the Bid C caps (36 register tokens through sampler, legal and measure); recorded; refused under other caps."""
    caps.apply_file(BIDC)
    rec = C.caps_info(BIDC)
    test, test_rec = C.load_test(write_test_dir(R.load_split('creative/data/c2', 'dev')[:6]))
    fresh = c2_stones._with_nums(stones.fresh_practised(6, 1, 'fresh-check')[0])
    with tempfile.TemporaryDirectory() as root:
        tiny_parent(root, 's700', rec)
        res = C.score_parent(root, 's700', None, None, test, fresh, 'cpu', 0, caps=BIDC, test_rec=test_rec)
        assert res['caps'] == rec and res['test'] == test_rec and set(('N', 'W', 'R', 'H', 'M')) <= set(res)
        assert 0 <= res['N']['first_try'] <= 1 and len(res['N']['per_q']['right']) == 6
        assert C.score_parent(root, 's700', None, None, test, fresh, 'cpu', 0, caps=BIDC, test_rec=test_rec) == json.load(open(os.path.join(root, 'test', 's700.json')))
        other = dict(test_rec, sha256='0' * 64)                         # same scored file, different test
        with pytest.raises(SystemExit, match='REFUSED'):
            C.score_parent(root, 's700', None, None, test, fresh, 'cpu', 0, caps=BIDC, test_rec=other)
        tiny_parent(root, 's701', None)                                 # trained without caps, scored with them
        with pytest.raises(SystemExit, match='REFUSED'):
            C.score_parent(root, 's701', None, None, test, fresh, 'cpu', 0, caps=BIDC, test_rec=test_rec)
