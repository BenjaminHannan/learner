"""python3 -m pytest creative/tests/test_bidc_load_gate.py   (CPU, a few minutes: every gate check is a fresh process)
Bid C draft, creative/bidc_load_gate.py, on tiny random Ledgers built here (real checkpoints are not available): all three checks pass; each fails when it should; a failed gate stops,
exits non-zero and cannot be retried over its report."""
import json, os, shutil, subprocess, sys, tempfile
import pytest
import torch
from custom_io import caps
from custom_io.data import CharVocab
from custom_io.models.ledger import Ledger
from creative import bidc_load_gate as G, rules_real as R, sleep

ROOT = os.getcwd()
BIDC, OLD = (os.path.abspath(os.path.join(os.path.dirname(caps.__file__), 'caps', f)) for f in ('caps-bidc.json', 'caps-old-defaults.json'))
SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, copy=True)
N = 8


@pytest.fixture(autouse=True)
def fresh_globals():
    caps.APPLIED = None
    yield
    caps.apply(caps.TODAY)
    caps.APPLIED = None


def sh(*argv):
    p = subprocess.run([sys.executable, '-m', 'creative.bidc_load_gate', *argv], capture_output=True, text=True, cwd=ROOT)
    return p


@pytest.fixture(scope='module')
def kit():
    """A C2b-like parent (built under today's caps), a Bid C parent, a rows file and a recorded eval of each."""
    d = tempfile.mkdtemp()
    v = CharVocab.build([])
    torch.manual_seed(3)
    old = Ledger(v, **SMALL)
    sleep.save_parent(old, 'ledger', SMALL, v, os.path.join(d, 'c2b_s200.pt'), step=0)
    caps.apply_file(BIDC)
    torch.manual_seed(4)
    new = Ledger(v, **SMALL)
    sleep.save_parent(new, 'ledger', SMALL, v, os.path.join(d, 'p0.pt'), step=0, caps=caps.APPLIED)
    caps.apply(caps.TODAY)
    caps.APPLIED = None
    rows = os.path.join(d, 'rows.jsonl')
    with open(rows, 'w') as f:
        f.write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in R.load_split('creative/data/c2', 'dev')[:N + 4]))
    for name, ck, extra in (('rec_c2b.pt', 'c2b_s200.pt', []), ('rec_p0.pt', 'p0.pt', ['--caps', BIDC])):
        p = sh('record', '--ckpt', os.path.join(d, ck), '--out', os.path.join(d, name), '--rows', rows, '--n', str(N), *extra)
        assert p.returncode == 0, p.stderr[-2000:]
    yield d
    shutil.rmtree(d)


def args(kit, report, **kw):
    a = dict(c2b_parent='c2b_s200.pt', recorded='rec_c2b.pt', bidc_parent='p0.pt', bidc_recorded='rec_p0.pt')
    a.update(kw)
    out = ['run', '--rows', os.path.join(kit, 'rows.jsonl'), '--n', str(N), '--caps-old', OLD, '--caps-bidc', BIDC, '--report', report]
    for k, v in a.items():
        if v is not None:
            out += [f'--{k.replace("_", "-")}', v if os.path.isabs(v) else os.path.join(kit, v)]
    return out


def go(kit, **kw):
    report = os.path.join(tempfile.mkdtemp(), 'gate.json')
    kws = {k: v for k, v in kw.items() if k != 'extra'}
    p = sh(*args(kit, report, **kws), *kw.get('extra', []))
    return p, json.load(open(report))


def tampered(kit, name, edit):
    rec = torch.load(os.path.join(kit, name), weights_only=True)
    edit(rec)
    path = os.path.join(tempfile.mkdtemp(), name)
    torch.save(rec, path)
    return path


def test_all_three_pass(kit):
    p, rep = go(kit)
    assert p.returncode == 0, p.stdout + p.stderr[-1500:]
    assert rep['verdict'] == 'PASS' and rep['not_run'] == [] and all(r['ok'] for r in rep['results'].values()) and sorted(rep['results']) == ['1', '2', '3']
    assert rep['results']['1']['compared'] == 'torch.equal on floats' and rep['results']['2']['shape_error'] and 'place' in rep['results']['2']['message']
    assert rep['results']['1']['caps_sha256'] == rep['caps_old_sha256'] and rep['results']['3']['caps_sha256'] == rep['caps_bidc_sha256']
    assert rep['results']['3']['checkpoint_caps_sha256'] == rep['caps_bidc_sha256']


def test_check1_fails_on_one_changed_bit_and_stops(kit):
    def edit(rec):
        t = rec['tensors']['R']
        t.view(-1)[0] = torch.nextafter(t.view(-1)[0], torch.tensor(float('inf')))             # one ulp
    p, rep = go(kit, recorded=tampered(kit, 'rec_c2b.pt', edit))
    assert p.returncode == 1 and rep['verdict'] == 'FAIL' and rep['stopped_at'] == 1 and rep['not_run'] == [2, 3] and list(rep['results']) == ['1']
    assert any('R: not bit-identical' in x for x in rep['results']['1']['differences'])


def test_check1_fails_when_the_caps_file_is_not_the_old_defaults(kit):
    p, rep = go(kit, extra=['--caps-old', BIDC])
    assert p.returncode == 1 and 'not the old defaults' in rep['results']['1']['why_fail']


def test_check1_fails_on_another_rows_set(kit):
    p, rep = go(kit, recorded=tampered(kit, 'rec_c2b.pt', lambda r: r.update(ids=r['ids'][::-1])))
    assert p.returncode == 1 and 'ids differ' in rep['results']['1']['differences'][0]


def test_check2_fails_if_the_parent_loads_under_the_bidc_caps(kit):
    p, rep = go(kit, extra=['--checks', '2'], c2b_parent='p0.pt')
    assert p.returncode == 1 and rep['results']['2']['raised'] is None and 'LOADED' in rep['results']['2']['why_fail']


def test_check2_fails_on_an_error_that_is_not_a_shape_error(kit):
    p, rep = go(kit, extra=['--checks', '2'], c2b_parent='nonexistent.pt')
    assert p.returncode == 1 and rep['results']['2']['raised'] in ('FileNotFoundError', 'OSError') and 'not a shape error' in rep['results']['2']['why_fail']


def test_check3_fails_on_a_changed_answer_pointer_and_on_wrong_caps_record(kit):
    p, rep = go(kit, bidc_recorded=tampered(kit, 'rec_p0.pt', lambda r: r['tensors']['ans'].view(-1).add_(1)))
    assert p.returncode == 1 and rep['stopped_at'] == 3 and rep['results']['1']['ok'] and rep['results']['2']['ok'] and any(x.startswith('ans:') for x in rep['results']['3']['differences'])
    p, rep = go(kit, bidc_recorded=tampered(kit, 'rec_p0.pt', lambda r: r.update(caps=None)))
    assert p.returncode == 1 and any('record was made under caps' in x for x in rep['results']['3']['differences'])


def test_partial_and_missing_inputs_are_not_a_pass(kit):
    p, rep = go(kit, extra=['--checks', '1,2'])
    assert p.returncode == 3 and rep['verdict'].startswith('PARTIAL') and rep['not_run'] == [3]
    p, rep = go(kit, bidc_parent=None, bidc_recorded=None)
    assert p.returncode == 1 and rep['stopped_at'] == 3 and 'missing --bidc-parent' in rep['results']['3']['why_fail']


def test_report_is_not_overwritten_and_records_are_exclusive(kit):
    report = os.path.join(tempfile.mkdtemp(), 'gate.json')
    open(report, 'w').write('{}')
    p = sh(*args(kit, report))
    assert p.returncode != 0 and 'REFUSED' in p.stderr and open(report).read() == '{}'
    p = sh('record', '--ckpt', os.path.join(kit, 'c2b_s200.pt'), '--out', os.path.join(kit, 'rec_c2b.pt'), '--rows', os.path.join(kit, 'rows.jsonl'), '--n', str(N))
    assert p.returncode != 0 and 'FileExistsError' in p.stderr


def test_c2b_results_json_record_compares_the_right_vector(kit):
    rec = torch.load(os.path.join(kit, 'rec_c2b.pt'), weights_only=True)
    j = os.path.join(tempfile.mkdtemp(), 's200.json')
    json.dump({'N': {'per_q': {'right': rec['right'] + [0.0] * 4}}}, open(j, 'w'))                 # more rows than the gate uses, as in a 512-row results file
    p, rep = go(kit, extra=['--checks', '1'], recorded=j)
    assert p.returncode == 3 and rep['results']['1']['ok'] and rep['results']['1']['compared'].startswith('per-row right only')
    j2 = j.replace('s200', 'flipped')
    json.dump({'N': {'per_q': {'right': [not x for x in rec['right']]}}}, open(j2, 'w'))
    p, rep = go(kit, extra=['--checks', '1'], recorded=j2)
    assert p.returncode == 1 and 'right differs' in rep['results']['1']['differences'][0]


def test_compare_unit():
    t = dict(x=torch.zeros(2, 3), y=torch.arange(4))
    rec = dict(ids=['a'], right=[True], answers=['1'], tensors=t)
    same = dict(ids=['a'], right=[True], answers=['1'], tensors={k: v.clone() for k, v in t.items()})
    assert G.compare(rec, same) == []
    assert 'x: shape' in G.compare(rec, dict(same, tensors=dict(same['tensors'], x=torch.zeros(3, 3))))[0]
    assert G.compare(rec, dict(same, answers=['2'])) == ['decoded answers differ']
    assert G.compare(rec, dict(same, ids=['b'])) == ['the recorded rows are not these rows (ids differ)']
