"""python3 -m pytest creative/tests/test_bidc_load_gate.py   (CPU, a few minutes: every gate check is a fresh process)
Bid C draft, creative/bidc_load_gate.py, on tiny random Ledgers built here (real checkpoints are not available): all three checks pass; each fails when it should; a failed gate stops,
exits non-zero and cannot be retried over its report."""
import json, os, shutil, subprocess, sys, tempfile
import pytest
import torch
from custom_io import caps
from custom_io.data import CharVocab, DEV_SPLITS
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
    rows = os.path.join(d, 'rows.jsonl')
    with open(rows, 'w') as f:
        f.write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in R.load_split('creative/data/c2', 'dev')[:N + 4]))
    # what custom_io/train.py --record-eval does, on the in-memory model (the real thing is run in test_train_process_record_end_to_end)
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    torch.save(G.record_eval(new, v, G.load_rows(rows, N), caps.APPLIED, source='train_process', checkpoint_sha256=G.sha256_file(os.path.join(d, 'p0.pt')),
                         rows_sha256=G.sha256_file(rows)), os.path.join(d, 'rec_p0.pt'))
    torch.set_num_threads(threads)
    caps.apply(caps.TODAY)
    caps.APPLIED = None
    for name, ck, extra in (('rec_c2b.pt', 'c2b_s200.pt', []), ('rec_p0_reload.pt', 'p0.pt', ['--caps', BIDC])):
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


def test_a_json_record_is_refused_for_check_1(kit):
    """Review 2, B1: a C2b results .json (no row ids of its own, no floats) is no record any more, whatever rows the gate has."""
    rec = torch.load(os.path.join(kit, 'rec_c2b.pt'), weights_only=True)
    j = os.path.join(tempfile.mkdtemp(), 's200.json')
    json.dump({'N': {'per_q': {'right': rec['right'] + [0.0] * 4}}}, open(j, 'w'))
    p, rep = go(kit, extra=['--checks', '1'], recorded=j)
    assert p.returncode == 1 and not rep['results']['1']['ok'] and 'not a gate record' in rep['results']['1']['why_fail'] and 'ValueError' in rep['results']['1']['why_fail']
    with pytest.raises(ValueError):
        G.load_record(j)
    assert 'record-arm' not in sh('--help').stdout and 'recorded_arm' not in rep['results']['1']


def test_a_record_made_on_other_rows_is_refused(kit):
    """Review 2, B1: compare() checks the record's own ids and rows-file sha256 against the gate's rows."""
    # same ids, one row's text changed: only the rows-file sha256 can tell
    rows = [json.loads(l) for l in open(os.path.join(kit, 'rows.jsonl'))]
    rows[0]['prompt'] = rows[0]['prompt'] + ' '
    other = os.path.join(tempfile.mkdtemp(), 'other.jsonl')
    open(other, 'w').write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    p, rep = go(kit, extra=['--checks', '1', '--rows', other])
    assert p.returncode == 1 and any('rows file sha256' in x for x in rep['results']['1']['differences'])
    # different rows (other ids): the TEST-rows-record-vs-DEV-rows case
    rows2 = [json.loads(l) for l in open(os.path.join(kit, 'rows.jsonl'))][4:]
    other2 = os.path.join(tempfile.mkdtemp(), 'other2.jsonl')
    open(other2, 'w').write(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows2))
    p, rep = go(kit, extra=['--checks', '1', '--rows', other2])
    assert p.returncode == 1 and 'ids differ' in rep['results']['1']['differences'][0]
    # a record without a rows sha256 is refused too, and the same for check 3's P_0 record
    p, rep = go(kit, extra=['--checks', '1'], recorded=tampered(kit, 'rec_c2b.pt', lambda r: r.pop('rows_sha256')))
    assert p.returncode == 1 and 'rows file sha256' in rep['results']['1']['differences'][0]
    p, rep = go(kit, extra=['--checks', '3', '--bidc-rows', other], bidc_recorded='rec_p0.pt')
    assert p.returncode == 1 and any('rows file sha256' in x for x in rep['results']['3']['differences'])


def test_compare_unit():
    t = dict(x=torch.zeros(2, 3), y=torch.arange(4))
    rec = dict(ids=['a'], rows_sha256='h', right=[True], answers=['1'], tensors=t)
    same = dict(ids=['a'], rows_sha256='h', right=[True], answers=['1'], tensors={k: v.clone() for k, v in t.items()})
    assert G.compare(rec, same) == []
    assert 'x: shape' in G.compare(rec, dict(same, tensors=dict(same['tensors'], x=torch.zeros(3, 3))))[0]
    assert G.compare(rec, dict(same, answers=['2'])) == ['decoded answers differ']
    assert G.compare(rec, dict(same, ids=['b'])) == ['the recorded rows are not these rows (ids differ)']
    assert 'rows file sha256' in G.compare(rec, dict(same, rows_sha256='other'))[0] and 'rows file sha256' in G.compare(dict(rec, rows_sha256=None), dict(same, rows_sha256=None))[0]


# ------------------------------------------------------------------ code-review round 1
def test_check3_refuses_a_record_made_by_reload(kit):
    """B1: P_0's record must come from the training process; a `record` (reload) of the same checkpoint reproduces itself trivially and proves nothing."""
    assert torch.load(os.path.join(kit, 'rec_p0_reload.pt'), weights_only=True)['source'] == 'reload'
    assert torch.load(os.path.join(kit, 'rec_c2b.pt'), weights_only=True)['source'] == 'reload'
    assert torch.load(os.path.join(kit, 'rec_p0.pt'), weights_only=True)['source'] == 'train_process'
    p, rep = go(kit, bidc_recorded='rec_p0_reload.pt')
    assert p.returncode == 1 and rep['stopped_at'] == 3 and any("source is 'reload'" in x for x in rep['results']['3']['differences'])
    p, rep = go(kit, bidc_recorded=tampered(kit, 'rec_p0.pt', lambda r: r.pop('source')))
    assert p.returncode == 1 and any("source is None" in x for x in rep['results']['3']['differences'])
    p, rep = go(kit, bidc_recorded=tampered(kit, 'rec_p0.pt', lambda r: r.update(checkpoint_sha256='0' * 64)))      # a train-process record of some other checkpoint
    assert p.returncode == 1 and any('belongs to checkpoint' in x for x in rep['results']['3']['differences'])


def test_check3_refuses_a_c2b_results_json_as_p0_record(kit):
    j = os.path.join(tempfile.mkdtemp(), 's.json')
    json.dump({'N': {'per_q': {'right': [True] * N}}}, open(j, 'w'))
    p, rep = go(kit, bidc_recorded=j)
    assert p.returncode == 1 and 'not a gate record' in rep['results']['3']['why_fail']


def test_record_command_stamps_reload_and_the_checkpoint_sha(kit):
    rec = torch.load(os.path.join(kit, 'rec_p0_reload.pt'), weights_only=True)
    assert rec['source'] == 'reload' and rec['checkpoint_sha256'] == G.sha256_file(os.path.join(kit, 'p0.pt'))


def test_check3_refuses_a_checkpoint_without_a_caps_record(kit):
    """N8: a derived checkpoint that dropped its caps record is refused under the Bid C caps, not waved through."""
    ck = torch.load(os.path.join(kit, 'p0.pt'), weights_only=False)
    ck.pop('caps')
    d = tempfile.mkdtemp()
    torch.save(ck, os.path.join(d, 'derived.pt'))
    rec = torch.load(os.path.join(kit, 'rec_p0.pt'), weights_only=True)
    rec['checkpoint_sha256'] = G.sha256_file(os.path.join(d, 'derived.pt'))           # everything else about the record is in order
    torch.save(rec, os.path.join(d, 'rec.pt'))
    p, rep = go(kit, bidc_parent=os.path.join(d, 'derived.pt'), bidc_recorded=os.path.join(d, 'rec.pt'))
    assert p.returncode == 1 and rep['stopped_at'] == 3 and any('no caps record' in x for x in rep['results']['3']['differences'])


def test_run_fails_on_a_nonzero_child_exit_even_if_it_printed_ok(monkeypatch):
    """N9: the child's returncode counts, not only the line it printed."""
    class P:
        returncode, stderr = 7, 'boom'
        stdout = G.TOK + json.dumps(dict(ok=True)) + '\n'
    monkeypatch.setattr(G.subprocess, 'run', lambda *a, **k: P)
    a = G.parser().parse_args(['run', '--checks', '2', '--c2b-parent', 'x.pt', '--report', 'unused'])
    code, rep = G.run(a)
    assert code == 1 and not rep['results'][2]['ok'] and 'exited with code 7' in rep['results'][2]['why_fail']


def synthetic_rows(n, seed):
    import random
    rng, out = random.Random(seed), []
    for i in range(n):
        a, b = rng.randrange(2, 90), rng.randrange(2, 90)
        out.append(dict(id=f'syn:{seed}:{i}', prompt=f'What is {a} plus {b}?', answer=str(a + b), accepted=[str(a + b)], family='arith_bare', level=1, stage=1, variant='', steps=[f'{a} + {b} = {a + b}']))
    return out


def test_train_process_record_end_to_end(kit):
    """B1: custom_io/train.py --record-eval writes the record from the training process (source train_process, the checkpoint's sha256) and gate check 3 accepts exactly that,
    in a fresh process, bit for bit; the `record` command's reload record of the same checkpoint is refused."""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, 'data', 'dev'))
    for name, n, seed in (('train.jsonl', 32, 1), (os.path.join('dev', 'in_dist.jsonl'), 8, 2)):
        with open(os.path.join(d, 'data', name), 'w') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in synthetic_rows(n, seed)))
    out, rec = os.path.join(d, 'out'), os.path.join(d, 'rec.pt')
    argv = [sys.executable, '-m', 'custom_io.train', '--model', 'ledger', '--cfg', json.dumps(SMALL), '--data', os.path.join(d, 'data'), '--steps', '2', '--batch', '8', '--warmup', '1',
            '--device', 'cpu', '--caps', BIDC, '--out', out, '--record-eval', rec, '--record-rows', os.path.join(kit, 'rows.jsonl'), '--record-n', str(N)]
    p = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stderr[-2000:]
    r = torch.load(rec, weights_only=True)
    ckpt = os.path.join(out, 'checkpoint.pt')
    assert r['source'] == 'train_process' and r['checkpoint_sha256'] == G.sha256_file(ckpt) and r['caps']['sha256'] == G.sha256_file(BIDC) and len(r['ids']) == N
    assert json.load(open(os.path.join(out, 'RESULT.json')))['record_eval']['checkpoint_sha256'] == r['checkpoint_sha256']
    p, rep = go(kit, extra=['--checks', '3'], bidc_parent=ckpt, bidc_recorded=rec)
    assert rep['results']['3']['ok'], rep['results']['3'] and rep['results']['3']['record_source'] == 'train_process'
    reload_rec = os.path.join(d, 'reload.pt')
    q = sh('record', '--ckpt', ckpt, '--out', reload_rec, '--rows', os.path.join(kit, 'rows.jsonl'), '--n', str(N), '--caps', BIDC)
    assert q.returncode == 0, q.stderr[-1500:]
    p, rep = go(kit, extra=['--checks', '3'], bidc_parent=ckpt, bidc_recorded=reload_rec)
    assert p.returncode == 1 and any("source is 'reload'" in x for x in rep['results']['3']['differences'])
    again = subprocess.run(argv[:-6] + ['--out', os.path.join(d, 'out2'), '--record-eval', rec] + argv[-4:], capture_output=True, text=True, cwd=ROOT)
    assert again.returncode != 0 and 'REFUSED' in again.stderr and not os.path.exists(os.path.join(d, 'out2'))             # a record is not overwritten, and nothing trains first


def test_train_record_eval_argument_errors():
    base = [sys.executable, '-m', 'custom_io.train', '--steps', '1', '--device', 'cpu', '--record-eval', os.path.join(tempfile.mkdtemp(), 'r.pt')]
    p = subprocess.run(base + ['--model', 'ledger'], capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 2 and '--record-eval needs --out' in p.stderr
    p = subprocess.run(base + ['--model', 'plain_tf', '--out', tempfile.mkdtemp()], capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 2 and 'must be ledger' in p.stderr


# ------------------------------------------------------------------ code-review round 2
def with_machine(**kw):
    def edit(rec):
        rec['machine'] = dict(rec['machine'], **kw)
    return edit


@pytest.mark.parametrize('field,value', [('torch', '0.0.1'), ('platform', 'Windows-11-other'), ('processor', 'another cpu'), ('threads', 8), ('mkldnn', False), ('cpu', 'other cpu model')])
def test_a_record_from_another_machine_is_refused_not_failed(kit, field, value):
    """Review 2, B2: check 1 and check 3 compare the machine block BEFORE the bit-exact comparison; a mismatch is REFUSED (exit 4, verdict REFUSED), not FAIL (exit 1)."""
    p, rep = go(kit, recorded=tampered(kit, 'rec_c2b.pt', with_machine(**{field: value})))
    r = rep['results']['1']
    assert p.returncode == 4 == G.REFUSED_CODE and rep['verdict'].startswith('REFUSED') and rep['stopped_at'] == 1 and rep['not_run'] == [2, 3]
    assert r['refused'] and not r['ok'] and any(x.startswith(field) for x in r['differences']) and 'same machine' in r['why_fail'] and 'compared' not in r
    p, rep = go(kit, extra=['--checks', '3'], bidc_recorded=tampered(kit, 'rec_p0.pt', with_machine(**{field: value})))
    r = rep['results']['3']
    assert p.returncode == 4 and rep['verdict'].startswith('REFUSED') and r['refused'] and any(x.startswith(field) for x in r['differences']) and 'same machine' in r['why_fail']


def test_machine_refusal_comes_before_the_bit_exact_comparison(kit):
    """a record that is BOTH from another machine and numerically different is REFUSED (nothing compared), not FAIL with float differences."""
    def edit(rec):
        rec['machine']['torch'] = '0.0.1'
        rec['tensors']['R'].view(-1)[0] += 1
    p, rep = go(kit, recorded=tampered(kit, 'rec_c2b.pt', edit))
    assert p.returncode == 4 and rep['results']['1']['refused'] and not any('not bit-identical' in x for x in rep['results']['1']['differences'])
    p, rep = go(kit, recorded=tampered(kit, 'rec_c2b.pt', lambda r: r.pop('machine')))        # an old-format record has no machine block: also refused
    assert p.returncode == 4 and 'no machine block' in rep['results']['1']['differences'][0]


def test_records_carry_the_machine_and_the_rows_sha(kit):
    here = G.machine_info()
    assert {'torch', 'platform', 'processor', 'machine', 'threads', 'mkldnn', 'mkl'} <= set(here)
    for name in ('rec_c2b.pt', 'rec_p0.pt', 'rec_p0_reload.pt'):
        rec = torch.load(os.path.join(kit, name), weights_only=True)
        assert rec['machine']['threads'] == 1 and rec['machine']['torch'] == str(torch.__version__) and rec['machine']['platform'] == here['platform']
        assert rec['rows_sha256'] == G.sha256_file(os.path.join(kit, 'rows.jsonl'))
    assert G.machine_mismatch(here) == [] and G.machine_mismatch(dict(here, threads=2))[0].startswith('threads')


def run_train(d, kit, extra, rows=None, n=N, record=None, final=False):
    out = os.path.join(d, 'out')
    argv = [sys.executable, '-m', 'custom_io.train', '--model', 'ledger', '--cfg', json.dumps(SMALL), '--data', os.path.join(d, 'data'), '--steps', '2', '--batch', '8', '--warmup', '1',
            '--device', 'cpu', '--out', out, '--record-eval', record or os.path.join(d, 'rec.pt'), '--record-rows', rows or os.path.join(kit, 'rows.jsonl'), '--record-n', str(n)] + extra
    return subprocess.run(argv, capture_output=True, text=True, cwd=ROOT), out


def tiny_data(d):
    os.makedirs(os.path.join(d, 'data', 'dev'))
    for name, n, seed in [('train.jsonl', 32, 1)] + [(os.path.join('dev', f'{sp}.jsonl'), 4, 2 + i) for i, sp in enumerate(DEV_SPLITS)]:      # all six dev splits: final_eval reads each
        with open(os.path.join(d, 'data', name), 'w') as f:
            f.write(''.join(json.dumps(r) + '\n' for r in synthetic_rows(n, seed)))


def test_train_record_eval_guard_needs_caps_and_valid_rows(kit):
    """Review 2, B3: --record-eval without --caps, or with --record-rows that is missing / too short / fails its MANIFEST sha256, stops before any training or checkpoint."""
    d = tempfile.mkdtemp()
    tiny_data(d)
    p, out = run_train(d, kit, [])
    assert p.returncode == 2 and '--record-eval needs --caps' in p.stderr and not os.path.exists(out)
    p, out = run_train(d, kit, ['--caps', BIDC], rows=os.path.join(d, 'nope.jsonl'))
    assert p.returncode != 0 and 'does not exist' in p.stderr and not os.path.exists(out)
    p, out = run_train(d, kit, ['--caps', BIDC], n=N + 100)                               # the kit rows file has N + 4 rows
    assert p.returncode != 0 and 'REFUSED' in p.stderr and 'needs' in p.stderr and not os.path.exists(out) and '"event": "train"' not in p.stdout
    # a rows file named in a MANIFEST whose bytes do not match its sha256
    md = tempfile.mkdtemp()
    shutil.copy(os.path.join(kit, 'rows.jsonl'), os.path.join(md, 'rows.jsonl'))
    json.dump({'rows': {'sha256': '0' * 64}}, open(os.path.join(md, 'MANIFEST.json'), 'w'))
    p, out = run_train(d, kit, ['--caps', BIDC], rows=os.path.join(md, 'rows.jsonl'))
    assert p.returncode != 0 and 'REFUSED' in p.stderr and 'sealed hash' in p.stderr and not os.path.exists(out) and '"event": "train"' not in p.stdout


def test_a_failed_record_write_still_leaves_result_json_and_the_final_eval(kit, monkeypatch):
    """Review 2, B3: the post-training record write failing is recorded in RESULT.json, the checkpoint and the final eval are still written, and the exit is non-zero at the end."""
    from custom_io import train
    d = tempfile.mkdtemp()
    tiny_data(d)
    out, rec = os.path.join(d, 'out'), os.path.join(d, 'rec.pt')
    def boom(*a, **k):
        raise RuntimeError('disk full (test)')
    monkeypatch.setattr(G, 'record_eval', boom)
    with pytest.raises(SystemExit) as e:
        train.main(['--model', 'ledger', '--cfg', json.dumps(SMALL), '--data', os.path.join(d, 'data'), '--steps', '2', '--batch', '8', '--warmup', '1', '--device', 'cpu', '--caps', BIDC,
                    '--out', out, '--record-eval', rec, '--record-rows', os.path.join(kit, 'rows.jsonl'), '--record-n', str(N), '--final-eval', '--eval-max', '4'])
    assert e.value.code not in (0, None) and 'NOT written' in str(e.value.code)
    r = json.load(open(os.path.join(out, 'RESULT.json')))
    assert 'disk full (test)' in r['record_eval_error'] and 'record_eval' not in r and r['final_eval'] is not None and r['lesions']
    assert os.path.exists(os.path.join(out, 'checkpoint.pt')) and not os.path.exists(rec)
