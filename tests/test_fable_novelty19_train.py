"""Checks for scripts/fable_novelty19_train.py.  Plain script; no pytest.

Run:
    OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
        python3.12 -B tests/test_fable_novelty19_train.py

These are the TRAINING-SIDE preflight checks of section 9 of
`design/v3/19-novelty-experiment-preregistration-draft.md`.  They establish, on tiny
disposable fixtures, the properties the registered runs depend on and that nothing else
verifies: a chunked run is bit-identical to an uninterrupted one and a resumed run is
bit-identical to both; D and T consume byte-identical questions for the same seed; the
three offline arms start from identical weights and differ only in which buffer they
read; the optimizer really is reset at the offline boundary; the canonical operator is
frozen in weights and is refused outright if its bytes change; the confirmation suite
cannot be scored before development passes; and the report calls a run that is not on
disk "(missing)" rather than a zero or a pass.  The registered numbers are asserted
against the sentences of the preregistration itself, so drifting one without the other
fails here.

Fixtures use seeds >= 999000 and a few updates.  The registered seeds 1900/1901/1902 are
never trained here, the real development panels are never generated, and no `test.pt` is
read.  The frozen canonical operator is opened read-only; the corruption check works on a
copy inside a temporary directory.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))

import fable_novelty19_data as N                                            # noqa: E402
import fable_novelty19_train as TR                                          # noqa: E402

torch = N.torch

FIXTURE_SEED = 999311            # disposable; far from 1900/1901/1902
FIXTURE_NAMESPACE = 'astra-novelty19-trainfixture-999311'
SPEC = HERE.parent / 'design' / 'v3' / '19-novelty-experiment-preregistration-draft.md'

PASSED = 0
FAILED = []
SKIPPED = []
TEMP = []
_CACHE = {}


class _Skip(Exception):
    pass


def check(name, function):
    global PASSED
    try:
        detail = function()
    except _Skip as skip:
        SKIPPED.append((name, str(skip)))
        print(f'skip  {name}: {skip}', flush=True)
        return
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        FAILED.append((name, repr(exc)))
        print(f'FAIL  {name}: {exc!r}', flush=True)
        return
    PASSED += 1
    print(f'ok    {name}' + (f'  {detail}' if detail else ''), flush=True)


def scratch(name):
    folder = Path(tempfile.mkdtemp(prefix=f'novelty19-train-{name}-'))
    TEMP.append(folder)
    return folder


def spec_text():
    if 'spec' not in _CACHE:
        if not SPEC.exists():
            raise _Skip(f'no {SPEC}')
        _CACHE['spec'] = SPEC.read_text()
    return _CACHE['spec']


AWAKE_FIXTURE_UPDATES = 8
OFFLINE_FIXTURE_UPDATES = 6




def fixture():
    """One tiny stream + memory + buffers + dev panels, built once and shared."""
    if 'fixture' not in _CACHE:
        root = scratch('fixture')
        # ruling 2 makes the operator-history reconstruction a prerequisite for any
        # panel; a one-update fixture copy is enough here, and the data module refuses
        # to let a partial one back a REGISTERED namespace, which is why these panels
        # carry a fixture namespace.
        N.build_operator_history(root / 'operator-history', updates=1, visits=1)
        # the panels come first: the awake stream and the buffers must exclude them
        N.build_dev_panels(root / 'panels', n=4, namespace=FIXTURE_NAMESPACE,
                           operator_history=root / 'operator-history',
                           require_full_history=False,
                           cells={k: N.DEV_CELLS[k] for k in ('F-c1-r8', 'N-c4-p6')},
                           progress=False)
        N.build_awake_stream(root / 'stream', FIXTURE_SEED, AWAKE_FIXTURE_UPDATES, chunk=3,
                             dev_panels=root / 'panels', progress=False)
        N.build_memory(root / 'memory', FIXTURE_SEED, root / 'stream', worlds=32)
        N.build_buffers(root / 'buffers', FIXTURE_SEED, root / 'memory',
                        dev_panels=root / 'panels',
                        offline_updates=OFFLINE_FIXTURE_UPDATES, progress=False)
        _CACHE['fixture'] = root
    return _CACHE['fixture']


def awake_args(arch, out, *, updates=AWAKE_FIXTURE_UPDATES, chunk=None, budget=None,
               seed=FIXTURE_SEED, stream=None):
    return TR.build_parser().parse_args([
        'awake', '--arch', arch, '--seed', str(seed), '--quiet',
        '--stream', str(stream if stream is not None else fixture() / 'stream'),
        '--out', str(out), '--updates', str(updates),
        '--chunk-updates', str(chunk if chunk is not None else updates),
        '--budget-seconds', str(TR.WAVE_DEADLINE if budget is None else budget)])


def offline_args(arch, arm, out, awake_ckpt, *, updates=OFFLINE_FIXTURE_UPDATES, chunk=None,
                 budget=None, seed=FIXTURE_SEED):
    return TR.build_parser().parse_args([
        'offline', '--arch', arch, '--seed', str(seed), '--arm', arm, '--quiet',
        '--awake-ckpt', str(awake_ckpt), '--buffers', str(fixture() / 'buffers'),
        '--out', str(out), '--updates', str(updates),
        '--chunk-updates', str(chunk if chunk is not None else updates),
        '--budget-seconds', str(TR.WAVE_DEADLINE if budget is None else budget)])


def trained_awake(arch):
    """One finished unchunked awake run per architecture, reused by several checks."""
    key = f'awake-{arch}'
    if key not in _CACHE:
        out = scratch(f'awake-{arch}') / 'run'
        _CACHE[key] = (TR.awake(awake_args(arch, out)), out)
    return _CACHE[key]


# --------------------------------------------------------------- registered numbers


def test_registered_numbers_match_the_preregistration():
    text = spec_text()
    sentences = {
        'awake updates 6,000': ('Ordinary training is 6,000 updates', TR.AWAKE_UPDATES, 6000),
        'offline updates 2,000': ('exactly **2,000** solver optimizer updates'.replace('**', ''),
                                  TR.OFFLINE_UPDATES, 2000),
        'D train cap 8': ('common cap of eight primitive calls', TR.D_TRAIN_CAP, 8),
        'D eval cap 16': ('Native evaluation uses the existing cap 16', TR.D_EVAL_CAP, 16),
        'T capacity 12': ('T uses common output capacity 12', TR.T_OUTPUT_CAPACITY, 12),
        'fit mark 61': ('61/64 final answers', TR.AWAKE_FIT_MARK, 61),
        'primary mark 58': ('58/64 answers', TR.PRIMARY_MARK, 58),
        'primary gain 13': ('13/64', TR.PRIMARY_GAIN, 13),
        'awake chunk 750': ('chunks of at most **750** updates'.replace('**', ''),
                            TR.AWAKE_CHUNK, 750),
        'offline chunk 500': ('offline work in chunks of at most **500**'.replace('**', ''),
                              TR.OFFLINE_CHUNK, 500),
        'compute budget 1,200 s': ('1,200-second compute budget', TR.CHUNK_SECONDS, 1200),
        'wave deadline 1,500 s': ('1,500-second wave deadline', TR.WAVE_DEADLINE, 1500),
        'K = 16': ('16 sampled episodes/question', TR.D_K, 16),
        'call cost 0.01': ('0.01 × executed calls', TR.D_CALL_COST, 0.01),
    }
    flat = text.replace('**', '')
    missing = [k for k, (needle, _, _) in sentences.items() if needle not in flat]
    assert not missing, f'the preregistration no longer says: {missing}'
    wrong = {k: (have, want) for k, (_, have, want) in sentences.items() if have != want}
    assert not wrong, f'constants drifted from the spec: {wrong}'
    assert TR.REGISTERED_SEEDS == (1900, 1901, 1902)
    assert 'seeds **1900, 1901, 1902**' in text
    assert TR.D_LR == 0.003 and TR.T_LR == 0.001 and TR.T_LR_FINAL == 0.0001
    assert TR.D_BETAS == (0.9, 0.99) and TR.T_BETAS == (0.9, 0.99)
    assert TR.D_WEIGHT_DECAY == 0.01 and TR.T_WEIGHT_DECAY == 0.1
    assert TR.D_WARMUP == 100 and TR.T_WARMUP == 100 and TR.D_CLIP == 1.0 and TR.T_CLIP == 1.0
    assert (TR.D_ENTROPY, TR.D_ENTROPY_FINAL) == (0.2, 0.02)
    assert len(TR.FIT_CELLS) == 7 and len(TR.PRIMARY_CELLS) == 4
    assert TR.FAMILY_MARK['H'] is None, 'H is descriptive; it must not carry a pass mark'
    assert TR.FAMILY_MARK['F'] == 61 and TR.FAMILY_MARK['L'] == 58
    return (f'{len(sentences)} registered numbers quoted from the spec, '
            f'{len(TR.FIT_CELLS)} fit cells, {len(TR.PRIMARY_CELLS)} primary cells')


def test_chunk_ceilings_are_enforced_by_the_parser():
    for phase, ceiling in (('awake', TR.AWAKE_CHUNK), ('offline', TR.OFFLINE_CHUNK)):
        base = (['awake', '--stream', 'x'] if phase == 'awake'
                else ['offline', '--arm', 'R', '--awake-ckpt', 'x', '--buffers', 'x'])
        for bad in (0, ceiling + 1):
            argv = base + ['--arch', 'D', '--seed', '999', '--out', 'x',
                           '--chunk-updates', str(bad)]
            try:
                TR.build_parser().parse_args(argv)
            except SystemExit:
                continue
            raise AssertionError(f'{phase} accepted --chunk-updates {bad}')
        TR.build_parser().parse_args(base + ['--arch', 'D', '--seed', '999', '--out', 'x',
                                             '--chunk-updates', str(ceiling)])
    return f'awake capped at {TR.AWAKE_CHUNK}, offline at {TR.OFFLINE_CHUNK}'


# --------------------------------------------------------------- the frozen operator


def test_operator_bytes_match_the_registered_sha256():
    if not TR.OPERATOR_PATH.exists():
        raise _Skip(f'no {TR.OPERATOR_PATH}')
    assert TR.OPERATOR_SHA256 in spec_text(), 'the registered sha is not in the spec'
    operator = TR.verified_operator()
    assert operator.sha256 == TR.OPERATOR_SHA256
    assert TR.sha(TR.OPERATOR_PATH) == TR.OPERATOR_SHA256
    return f'{TR.OPERATOR_PATH.name} sha256 {operator.sha256[:16]}...'


def test_operator_sha_check_aborts_on_a_corrupted_copy():
    if not TR.OPERATOR_PATH.exists():
        raise _Skip(f'no {TR.OPERATOR_PATH}')
    folder = scratch('operator')
    good = folder / 'final.pt'
    shutil.copy2(TR.OPERATOR_PATH, good)
    assert TR.verified_operator(good).sha256 == TR.OPERATOR_SHA256, 'a faithful copy was refused'
    bad = folder / 'corrupt.pt'
    raw = bytearray(good.read_bytes())
    raw[len(raw) // 2] ^= 0x01                      # one flipped bit, nothing else
    bad.write_bytes(bytes(raw))
    assert TR.sha(bad) != TR.OPERATOR_SHA256
    try:
        TR.verified_operator(bad)
    except SystemExit as exc:
        assert 'sha-256 mismatch' in str(exc).lower(), str(exc)
        assert TR.OPERATOR_PATH.exists() and TR.sha(TR.OPERATOR_PATH) == TR.OPERATOR_SHA256
        return f'one flipped bit is refused: {str(exc).splitlines()[0][:70]}'
    raise AssertionError('a corrupted operator was accepted')


def test_operator_weights_are_frozen_across_training():
    completion, _out = trained_awake('D')
    assert completion['operator_sha256_expected'] == TR.OPERATOR_SHA256
    assert completion['operator']['sha256'] == TR.OPERATOR_SHA256
    assert completion['operator_weights_unchanged'] is True
    fresh = TR.verified_operator()
    assert completion['operator']['fingerprint'] == fresh.fingerprint, \
        'the operator weights moved during training'
    assert all(not p.requires_grad for p in fresh.model.parameters()), \
        'the operator exposes trainable parameters'
    return f'operator fingerprint {fresh.fingerprint[:16]}... unchanged after ' \
           f'{completion["updates_done"]} D updates'


# --------------------------------------------------------------- chunking and resume


def weights_of(path):
    saved = torch.load(Path(path), map_location='cpu', weights_only=False)
    return saved['state_dict'], saved


def identical_tensors(left, right):
    assert set(left) == set(right), 'different parameter names'
    for key in left:
        a, b = left[key], right[key]
        assert a.dtype == b.dtype and a.shape == b.shape, key
        assert torch.equal(a, b), f'{key} differs by up to {(a - b).abs().max().item():.3e}'
    return True


def _chunked_matches_unchunked(arch, chunk=3):
    whole, whole_out = trained_awake(arch)
    parts_out = scratch(f'chunked-{arch}') / 'run'
    parts = TR.awake(awake_args(arch, parts_out, chunk=chunk))
    assert whole['chunks'] == 1 and parts['chunks'] == 3, (whole['chunks'], parts['chunks'])
    assert parts['updates_done'] == whole['updates_done'] == AWAKE_FIXTURE_UPDATES
    for field in ('initial_weight_fingerprint', 'final_weight_fingerprint',
                  'data_fingerprint', 'update_fingerprint'):
        assert parts[field] == whole[field], f'{arch}: {field} differs when chunked'
    identical_tensors(weights_of(whole['checkpoint'])[0], weights_of(parts['checkpoint'])[0])
    return whole, parts


def test_dispatcher_chunked_run_is_bit_identical():
    whole, parts = _chunked_matches_unchunked('D')
    return (f'D {AWAKE_FIXTURE_UPDATES} updates in 1 chunk vs 3: identical weights and '
            f'update fingerprint {whole["update_fingerprint"][:16]}...')


def test_transformer_chunked_run_is_bit_identical():
    whole, parts = _chunked_matches_unchunked('T')
    return (f'T {AWAKE_FIXTURE_UPDATES} updates in 1 chunk vs 3: identical weights and '
            f'update fingerprint {whole["update_fingerprint"][:16]}...')


def test_resume_after_a_simulated_kill_is_bit_identical():
    whole, _ = trained_awake('D')
    out = scratch('killed') / 'run'
    # A budget of zero seconds stops after the first chunk, exactly as an interrupted
    # wave would: a partial directory with checkpoints and no completion.json.
    partial = TR.awake(awake_args('D', out, chunk=3, budget=0))
    assert partial['complete'] is False and partial['updates_done'] == 3
    assert not (out / 'completion.json').exists(), 'an interrupted wave claimed a result'
    survivors = sorted(p.name for p in out.glob('ckpt-*.pt'))
    assert survivors == ['ckpt-000003.pt'], survivors
    # A harsher kill: drop everything the interrupted process had in memory and re-run
    # the SAME command.  Two more waves finish the phase.
    again = TR.awake(awake_args('D', out, chunk=3, budget=0))
    assert again['complete'] is False and again['updates_done'] == 6
    done = TR.awake(awake_args('D', out, chunk=3, budget=0))
    assert done['complete'] is True and done['updates_done'] == AWAKE_FIXTURE_UPDATES
    assert done['resumed_from'] == 'ckpt-000006.pt'
    for field in ('initial_weight_fingerprint', 'final_weight_fingerprint',
                  'data_fingerprint', 'update_fingerprint'):
        assert done[field] == whole[field], f'resume changed {field}'
    identical_tensors(weights_of(whole['checkpoint'])[0], weights_of(done['checkpoint'])[0])
    # A finished directory is idempotent: re-running returns the record, retrains nothing.
    repeat = TR.awake(awake_args('D', out, chunk=3))
    assert repeat['checkpoint_sha256'] == done['checkpoint_sha256']
    return (f'3 waves of 3/3/2 updates resume to the same weights as one run of '
            f'{AWAKE_FIXTURE_UPDATES}; {done["chunks"]} chunk records kept')


def test_a_checkpoint_is_never_silently_overwritten():
    whole, out = trained_awake('D')
    copied = scratch('overwrite') / 'run'
    copied.mkdir(parents=True)
    shutil.copy2(Path(out) / 'ckpt-000003.pt', copied / 'ckpt-000003.pt') \
        if (Path(out) / 'ckpt-000003.pt').exists() else None
    shutil.copy2(Path(out) / TR.checkpoint_name(AWAKE_FIXTURE_UPDATES),
                 copied / TR.checkpoint_name(AWAKE_FIXTURE_UPDATES))
    try:
        TR.awake(awake_args('D', copied))
    except SystemExit as exc:
        assert 'nothing left to train' in str(exc), str(exc)
        return 'a run directory holding all its updates but no completion.json is refused'
    raise AssertionError('an already-trained directory was retrained')


def test_both_architectures_consume_identical_questions():
    d_run, _ = trained_awake('D')
    t_run, _ = trained_awake('T')
    assert d_run['data_fingerprint'] == t_run['data_fingerprint'], \
        'D and T saw different questions for the same seed'
    assert d_run['inputs']['stream_fingerprint'] == t_run['inputs']['stream_fingerprint']
    assert d_run['inputs']['stream_chunks'] == t_run['inputs']['stream_chunks']
    # and the same claim made directly on the records, not only on their digests
    left = list(TR.awake_feed(FIXTURE_SEED, 0, 4, fixture() / 'stream'))
    right = list(TR.awake_feed(FIXTURE_SEED, 0, 4, fixture() / 'stream'))
    seen = set()
    for a, b in zip(left, right):
        assert TR.question_digest(a['items']) == TR.question_digest(b['items'])
        seen.add(TR.question_digest(a['items']))
    assert len(seen) == 4, 'the awake stream repeats an update'
    assert d_run['update_fingerprint'] != t_run['update_fingerprint'], \
        'two different architectures produced the same training trace'
    return (f'shared question digest {d_run["data_fingerprint"][:16]}... over '
            f'{AWAKE_FIXTURE_UPDATES} updates')


# --------------------------------------------------------------- the offline boundary


def offline_runs(arch='D'):
    key = f'offline-{arch}'
    if key not in _CACHE:
        awake_run, _ = trained_awake(arch)
        root = scratch(f'offline-{arch}')
        _CACHE[key] = {arm: TR.offline(offline_args(arch, arm, root / arm,
                                                    awake_run['checkpoint']))
                       for arm in TR.ARMS}
    return _CACHE[key]


def test_offline_arms_start_from_identical_weights():
    awake_run, _ = trained_awake('D')
    runs = offline_runs('D')
    starts = {arm: run['initial_weight_fingerprint'] for arm, run in runs.items()}
    assert len(set(starts.values())) == 1, f'the arms began from different weights: {starts}'
    assert set(starts.values()) == {awake_run['final_weight_fingerprint']}, \
        'the offline arms did not begin at the awake endpoint'
    assert len({run['awake_checkpoint_sha256'] for run in runs.values()}) == 1
    finals = {arm: run['final_weight_fingerprint'] for arm, run in runs.items()}
    assert len(set(finals.values())) == 3, f'two arms ended identical: {finals}'
    return (f'R/G/U all start at {awake_run["final_weight_fingerprint"][:16]}... '
            f'and end apart')


def test_offline_arms_differ_only_in_the_buffer_they_read():
    runs = offline_runs('D')
    varies = {'buffer_file', 'buffer_sha256'}
    shared = {arm: {k: v for k, v in run['inputs'].items() if k not in varies}
              for arm, run in runs.items()}
    assert shared['R'] == shared['G'] == shared['U'], \
        'the arms disagree about something other than the buffer'
    files = {arm: run['inputs']['buffer_file'] for arm, run in runs.items()}
    assert files == {'R': 'buffer-R.pt', 'G': 'buffer-G.pt', 'U': 'buffer-U.pt'}, files
    digests = {arm: run['inputs']['buffer_sha256'] for arm, run in runs.items()}
    assert len(set(digests.values())) == 3, f'two arms read the same bytes: {digests}'
    orders = {arm: run['inputs']['offline_order_digest'] for arm, run in runs.items()}
    assert len(set(orders.values())) == 1, f'the arms used different world orders: {orders}'
    assert len({run['inputs']['worlds'] for run in runs.values()}) == 1
    assert len({run['inputs']['questions'] for run in runs.values()}) == 1
    hyper = [json.dumps(run['hyperparameters'], sort_keys=True) for run in runs.values()]
    assert len(set(hyper)) == 1, 'the arms used different hyper-parameters'
    assert len({run['total_updates'] for run in runs.values()}) == 1
    data = {arm: run['data_fingerprint'] for arm, run in runs.items()}
    assert len(set(data.values())) == 3, f'two arms trained on the same questions: {data}'
    return (f'identical order {orders["R"][:16]}..., {len(set(digests.values()))} distinct '
            f'buffers, {len(set(hyper))} hyper-parameter set')


def _optimizer_steps(path):
    saved = torch.load(Path(path), map_location='cpu', weights_only=False)
    state = saved['optimizer']['state']
    steps = sorted({int(torch.as_tensor(row['step']).item()) for row in state.values()})
    moments = {k: row['exp_avg'] for k, row in state.items()}
    return steps, moments, saved


def test_optimizer_is_reset_at_the_offline_boundary():
    detail = []
    for arch in ('D', 'T'):
        awake_run, _ = trained_awake(arch)
        if arch == 'D':
            run = offline_runs('D')['R']
        else:
            out = scratch('offline-T-reset') / 'run'
            run = TR.offline(offline_args('T', 'R', out, awake_run['checkpoint']))
        awake_steps, awake_moments, _ = _optimizer_steps(awake_run['checkpoint'])
        offline_steps, offline_moments, saved = _optimizer_steps(run['checkpoint'])
        assert awake_steps == [AWAKE_FIXTURE_UPDATES], awake_steps
        assert offline_steps == [OFFLINE_FIXTURE_UPDATES], \
            (f'{arch}: the offline optimizer counted {offline_steps} steps, so it continued '
             f'the awake one instead of being reset')
        assert run['optimizer_reset_at_offline_boundary'] is True
        moved = [k for k in offline_moments
                 if k in awake_moments and torch.equal(offline_moments[k], awake_moments[k])]
        assert not moved, f'{arch}: {len(moved)} moment buffers survived the reset'
        detail.append(f'{arch} {awake_steps[0]}->{offline_steps[0]}')
    return 'optimizer step counts restart at the boundary: ' + ', '.join(detail)


def test_offline_refuses_a_mismatched_awake_checkpoint():
    awake_run, _ = trained_awake('D')
    out = scratch('mismatch') / 'run'
    try:
        TR.offline(offline_args('T', 'R', out, awake_run['checkpoint']))
    except SystemExit as exc:
        assert 'architecture' in str(exc), str(exc)
    else:
        raise AssertionError("T accepted D's awake checkpoint")
    offline_run = offline_runs('D')['R']
    out2 = scratch('mismatch2') / 'run'
    try:
        TR.offline(offline_args('D', 'R', out2, offline_run['checkpoint']))
    except SystemExit as exc:
        assert 'awake' in str(exc), str(exc)
        return 'a cross-architecture and a non-awake checkpoint are both refused'
    raise AssertionError('an offline checkpoint was accepted as the awake starting point')


# --------------------------------------------------------------- scoring and its guards


def score_args(arch, ckpt, out, *, panels=None, cells=None, confirmation=False,
               experiment=None, extra=()):
    argv = ['score', '--arch', arch, '--ckpt', str(ckpt),
            '--panels', str(panels if panels is not None else fixture() / 'panels'),
            '--out', str(out), '--no-oracle']
    if cells:
        argv += ['--cells', cells]
    if confirmation:
        argv += ['--confirmation']
    if experiment:
        argv += ['--experiment', str(experiment)]
    return TR.build_parser().parse_args(argv + list(extra))


def scored(arch):
    key = f'score-{arch}'
    if key not in _CACHE:
        run, _ = trained_awake(arch)
        out = scratch(f'score-{arch}') / 'score.json'
        _CACHE[key] = TR.score(score_args(arch, run['checkpoint'], out))
    return _CACHE[key]


def test_scoring_uses_each_architectures_native_measure():
    d_report, t_report = scored('D'), scored('T')
    assert d_report['phase'] == 'awake' and d_report['arm'] is None, \
        'the awake-final checkpoint must be scoreable, ruling 7 depends on it'
    assert d_report['eval_cap'] == TR.D_EVAL_CAP and d_report['output_capacity'] is None
    assert t_report['output_capacity'] == TR.T_OUTPUT_CAPACITY and t_report['eval_cap'] is None
    for report in (d_report, t_report):
        assert set(report['cells']) == {'F-c1-r8', 'N-c4-p6'}, sorted(report['cells'])
        for cell, row in report['cells'].items():
            assert row['n'] == 4 and 0 <= row['answers'] <= 4 and 0 <= row['strict'] <= 4
            assert row['strict'] <= row['answers'], f'{cell}: strict exceeds answers'
            assert row['mark'] == TR.FAMILY_MARK[cell.split('-')[0]]
            assert 'failure_shapes' in row
    assert 'mean_calls' in d_report['cells']['F-c1-r8'] and \
           'over_cap' in d_report['cells']['F-c1-r8']
    assert 'mean_output_tokens' in t_report['cells']['F-c1-r8'] and \
           'no_end' in t_report['cells']['F-c1-r8']
    limits = t_report['cells']['N-c4-p6']['limits']
    assert limits['unscorable_reason'] is None, limits
    assert d_report['operator']['sha256'] == TR.OPERATOR_SHA256
    return (f'D scored at cap {d_report["eval_cap"]} with a strict path, T at capacity '
            f'{t_report["output_capacity"]} with strict steps')


def test_a_real_score_binds_to_its_real_run():
    """The binding of must-fix 3 read against ACTUAL artifacts, not synthetic JSON.

    A fixture run is 8 updates, not the registered 6,000, so the two update-count
    problems are expected and are exactly what must be left: everything else -- the
    completion.json beside the checkpoint, the sha256 it recorded, the architecture,
    seed, phase and arm, and the re-hash of the checkpoint file still on disk -- has to
    pass on real files, or the registered runs would all be rejected.
    """
    seen = {}
    for arch in TR.ARCHES:
        report = scored(arch)
        run, out = trained_awake(arch)
        assert Path(report['run_dir']) == Path(out).resolve()
        assert report['checkpoint_sha256'] == run['checkpoint_sha256'] == \
            TR.sha(Path(run['checkpoint']))
        assert report['is_final_checkpoint'] is True
        assert report['expected_updates'] == TR.AWAKE_UPDATES
        assert report['registered_caps'] is True
        caps, _ = TR.registered_caps_of(report)
        assert caps == [], caps
        problems = TR.checkpoint_binding(report)
        # the score's updates_done, its total_updates, and the run's own record
        assert len(problems) == 3, problems
        assert all(str(AWAKE_FIXTURE_UPDATES) in p and str(TR.AWAKE_UPDATES) in p
                   for p in problems[:2]), problems
        assert 'the run itself recorded' in problems[2], problems
        seen[arch] = report['checkpoint_sha256'][:16]
    return ('a real score file binds to its run directory, sha256 and completion record; '
            f'only the fixture\'s update count differs  {seen}')


def test_scoring_refuses_a_partial_cell():
    run, _ = trained_awake('T')
    folder = scratch('partial')
    shutil.copytree(fixture() / 'panels', folder / 'panels')
    manifest = json.loads((folder / 'panels' / 'manifest.json').read_text())
    victim = sorted(manifest['cells'])[0]
    path = Path(manifest['cells'][victim]['path'])
    panel = json.loads((folder / 'panels' / path.name).read_text())
    panel['units'] = panel['units'][:2]                     # a prefix, not a smaller cell
    (folder / 'panels' / path.name).write_text(json.dumps(panel))
    manifest['cells'][victim]['sha256'] = TR.sha(folder / 'panels' / path.name)
    (folder / 'panels' / 'manifest.json').write_text(json.dumps(manifest))
    try:
        TR.score(score_args('T', run['checkpoint'], folder / 'score.json',
                            panels=folder / 'panels'))
    except SystemExit as exc:
        assert 'partial' in str(exc) or 'unit index' in str(exc), str(exc)
        return f'a {len(panel["units"])}-unit prefix of {victim} is refused, not scored'
    raise AssertionError('a prefix of a cell was scored as if it were the cell')


def test_scoring_needs_the_new_cells_visible_to_the_v3_auditor():
    # V3.audit_unit looks a cell up by NAME; without the lending context the novelty-19
    # names are simply absent from V3.CELLS and nothing could be scored.
    for cell in TR.FORGET_CELLS + TR.PRIMARY_CELLS:
        assert cell not in TR.V3.CELLS, f'{cell} leaked into the frozen v3 table'
    with N.registered_cells():
        assert all(cell in TR.V3.CELLS for cell in N.DEV_CELL_ORDER)
    for cell in N.DEV_CELL_ORDER:
        assert cell not in TR.V3.CELLS, f'{cell} was left behind in V3.CELLS'
    assert scored('D')['cells_scored'] == 2, 'scoring did not run under the context'
    return f'{len(N.DEV_CELL_ORDER)} cell names lent to V3.CELLS and restored'


def valid_dev_passed(experiment, panels_folder):
    """A DEV-PASSED.json that `fable_novelty19_data.validate_dev_passed` accepts.

    Built by hand so the guard can be attacked with damaged copies of it.  The seed
    numbers are the registered ones because the schema pins them; nothing is trained,
    and the checkpoint hashes are hashes of their own key names.
    """
    manifest = Path(panels_folder) / 'manifest.json'
    return dict(
        schema=N.DEV_PASSED_SCHEMA, seeds=[int(s) for s in N.REGISTERED_SEEDS],
        report_sha256=fake_sha('report'),
        dev_panels=dict(path=str(Path(panels_folder).resolve()),
                        manifest_sha256=TR.sha(manifest)),
        awake_checkpoints={k: fake_sha(k) for k in N.AWAKE_CHECKPOINT_KEYS},
        offline_checkpoints={k: fake_sha(k) for k in N.OFFLINE_CHECKPOINT_KEYS})


def test_resume_refuses_a_checkpoint_that_changed_on_disk():
    """Must-fix 5: `chunk-*.json` records the checkpoint's sha256; resume must check it.

    Truncation is caught by torch's own container check, but a flipped byte inside a
    tensor blob is not, so the hash is compared before `torch.load` is reached at all.
    """
    out = scratch('tampered') / 'run'
    partial = TR.awake(awake_args('D', out, chunk=3, budget=0))
    assert partial['updates_done'] == 3
    ckpt = out / 'ckpt-000003.pt'
    recorded, source = TR.recorded_checkpoint_sha(ckpt)
    assert recorded == TR.sha(ckpt) and 'chunk-' in source
    with ckpt.open('ab') as handle:                 # one byte the writer never wrote
        handle.write(b'\x00')
    try:
        TR.awake(awake_args('D', out, chunk=3, budget=0))
    except SystemExit as exc:
        assert 'refusing to resume' in str(exc), str(exc)
    else:
        raise AssertionError('training resumed from a checkpoint that had changed on disk')
    # an orphan checkpoint that no record accounts for is refused just as firmly
    orphan = scratch('orphan') / 'run'
    orphan.mkdir(parents=True)
    shutil.copy2(out / 'ckpt-000003.pt', orphan / 'ckpt-000003.pt')
    try:
        TR.awake(awake_args('D', orphan, chunk=3, budget=0))
    except SystemExit as exc:
        assert 'unaccounted checkpoint' in str(exc), str(exc)
        return 'a tampered checkpoint and an unrecorded one are both refused before torch.load'
    raise AssertionError('an unrecorded checkpoint was resumed from')


def test_confirmation_is_refused_without_dev_passed():
    folder = scratch('confirm')
    # The guard reads manifest.json and nothing else -- that is the point: a confirmation
    # suite is refused BEFORE a single unit is loaded, let alone scored.  So the suite
    # here is the fixture's own panels re-labelled, rather than a real generation run
    # (which the data module rightly locks behind a full DEV-PASSED.json of its own).
    shutil.copytree(fixture() / 'panels', folder / 'confirm')
    manifest = json.loads((folder / 'confirm' / 'manifest.json').read_text())
    manifest.update(kind='confirmation', namespace=N.NS_CONFIRM)
    (folder / 'confirm' / 'manifest.json').write_text(json.dumps(manifest))
    run, _ = trained_awake('T')
    experiment = folder / 'exp'
    experiment.mkdir()
    # 1: a confirmation suite without the flag
    try:
        TR.score(score_args('T', run['checkpoint'], folder / 'a.json',
                            panels=folder / 'confirm', confirmation=True,
                            experiment=experiment))
    except SystemExit as exc:
        assert 'DEV-PASSED.json' in str(exc), str(exc)
    else:
        raise AssertionError('confirmation panels were scored without DEV-PASSED.json')
    # 2: a confirmation suite without even asking for it
    try:
        TR.score(score_args('T', run['checkpoint'], folder / 'b.json',
                            panels=folder / 'confirm'))
    except SystemExit as exc:
        assert 'CONFIRMATION' in str(exc), str(exc)
    else:
        raise AssertionError('a confirmation suite was scored as if it were development')
    # 3: --confirmation aimed at the development suite
    try:
        TR.score(score_args('T', run['checkpoint'], folder / 'c.json', confirmation=True,
                            experiment=experiment))
    except SystemExit as exc:
        assert 'confirmation' in str(exc)
    else:
        raise AssertionError('--confirmation was accepted for a development suite')
    # 4: a DEV-PASSED.json of the WRONG CONTENT unlocks nothing (must-fix 2).  An audit
    #    showed `{}`, a wrong schema, a one-seed payload and even non-JSON bytes all
    #    passing a Path.exists() check, so each of them is tried here.
    valid = valid_dev_passed(experiment, fixture() / 'panels')
    garbage = {
        'empty object': '{}',
        'not json at all': 'this is not json at all',
        'empty file': '',
        'wrong schema': json.dumps(dict(valid, schema='something-else')),
        'one seed': json.dumps(dict(valid, seeds=[9991])),
        'no report hash': json.dumps({k: v for k, v in valid.items() if k != 'report_sha256'}),
        'short checkpoint table': json.dumps(dict(
            valid, offline_checkpoints={k: v for k, v in
                                        list(valid['offline_checkpoints'].items())[:5]})),
        'not a sha': json.dumps(dict(valid, awake_checkpoints=dict(
            valid['awake_checkpoints'], **{N.AWAKE_CHECKPOINT_KEYS[0]: 'nope'}))),
        'wrong panel hash': json.dumps(dict(
            valid, dev_panels=dict(valid['dev_panels'], manifest_sha256='0' * 64))),
    }
    refused = []
    for label, text in garbage.items():
        (experiment / 'DEV-PASSED.json').write_text(text)
        try:
            TR.guard_confirmation(folder / 'confirm', True, experiment)
        except SystemExit:
            refused.append(label)
        else:
            raise AssertionError(f'a DEV-PASSED.json that is {label} unlocked confirmation')
    # 5: only the real thing steps aside, and it is validated by the data module itself.
    #    M-1 additionally requires the suite to name the verdict it was generated from,
    #    which `build_dev_panels(confirmation=True)` writes into the manifest.
    (experiment / 'DEV-PASSED.json').write_text(json.dumps(valid))
    manifest['dev_passed'] = dict(sha256=TR.sha(experiment / 'DEV-PASSED.json'))
    (folder / 'confirm' / 'manifest.json').write_text(json.dumps(manifest))
    guard = TR.guard_confirmation(folder / 'confirm', True, experiment)
    assert guard['is_confirmation'] is True and guard['dev_passed_sha256']
    assert guard['dev_passed_validated_by'] == 'fable_novelty19_data.validate_dev_passed'
    assert guard['dev_passed_record']['awake_checkpoints'] == 6
    assert guard['dev_passed_record']['offline_checkpoints'] == 18
    assert not list((folder / 'confirm').glob('*.scored')), 'the guard wrote into the suite'
    return (f'confirmation refused three ways and for {len(refused)} bad unlock files '
            f'({", ".join(refused)}), then opened only by a valid one')


def test_confirmation_is_bound_to_the_verdict_that_unlocked_it():
    """M-1: a VALID DEV-PASSED.json is not enough; it must be THE one, by hash.

    Validating the presented file proves only that some development run passed.  A second,
    equally valid verdict -- a re-run, a later generation, another experiment's copy --
    would sail through, which is exactly how a confirmation suite generated under one set
    of results gets scored under another.  `build_dev_panels(confirmation=True)` records
    the verdict it unlocked on in the suite manifest, so the two hashes must agree.
    """
    folder = scratch('bound')
    shutil.copytree(fixture() / 'panels', folder / 'confirm')
    path = folder / 'confirm' / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest.update(kind='confirmation', namespace=N.NS_CONFIRM)
    path.write_text(json.dumps(manifest))
    experiment = folder / 'exp'
    experiment.mkdir()
    flag = experiment / 'DEV-PASSED.json'
    valid = valid_dev_passed(experiment, fixture() / 'panels')
    flag.write_text(json.dumps(valid))
    first = TR.sha(flag)

    # (a) missing field: the suite records no verdict at all
    try:
        TR.guard_confirmation(folder / 'confirm', True, experiment)
    except SystemExit as exc:
        assert 'records no dev_passed.sha256' in str(exc), str(exc)
    else:
        raise AssertionError('a suite that names no verdict unlocked confirmation')

    # (b) matching: the recorded hash is this file's hash
    path.write_text(json.dumps(dict(manifest, dev_passed=dict(sha256=first))))
    guard = TR.guard_confirmation(folder / 'confirm', True, experiment)
    assert guard['dev_passed_bound_to_suite'] is True
    assert guard['dev_passed_sha256'] == first

    # (c) a DIFFERENT but perfectly valid verdict: the data module accepts it on its own,
    #     and the binding is what refuses it.  Only a byte the schema does not pin is
    #     changed, so this is not a malformed file -- it is the wrong one.
    other = dict(valid, report_sha256=fake_sha('a different development report'))
    flag.write_text(json.dumps(other))
    second = TR.sha(flag)
    assert second != first
    standalone = N.validate_dev_passed(experiment, seeds=N.REGISTERED_SEEDS)
    assert standalone['sha256'] == second, 'the second verdict is not valid on its own'
    try:
        TR.guard_confirmation(folder / 'confirm', True, experiment)
    except SystemExit as exc:
        assert 'VALID verdict but not' in str(exc), str(exc)
        assert first[:16] in str(exc) and second[:16] in str(exc), str(exc)
    else:
        raise AssertionError('a valid but unrelated DEV-PASSED.json unlocked confirmation')
    return ('confirmation opens only for the verdict the suite records: a missing binding '
            'and a second, independently valid verdict are both refused by name')


# --------------------------------------------------------------- report, ruling 7, ruling 8

FAKE_SEEDS = (991900, 991901, 991902)
FAKE_N = 64


def fake_cells(default=(64, 64), overrides=None):
    rows = {}
    for cell in N.DEV_CELL_ORDER:
        answers, strict = (overrides or {}).get(cell, default)
        cfg = N.DEV_CELLS[cell]
        mark = TR.FAMILY_MARK[cell.split('-')[0]]
        rows[cell] = dict(cell=cell, family=cell.split('-')[0], n=FAKE_N, hops=cfg['hops'],
                          people=cfg['people'], answers=int(answers), strict=int(strict),
                          mean_calls=float(cfg['hops']), mean_output_tokens=float(cfg['hops']),
                          over_cap=0, no_end=0, mark=mark,
                          marked=bool(mark is not None and answers >= mark and strict >= mark))
    return rows


def fake_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fake_panels(exp):
    """A real manifest file, because the unlock record is checked against the bytes."""
    folder = Path(exp) / 'dev-panels'
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / 'manifest.json'
    if not manifest.exists():
        manifest.write_text(json.dumps(dict(kind='development', n=FAKE_N,
                                            cell_order=list(N.DEV_CELL_ORDER))))
    return folder, TR.sha(manifest)


def fake_run_dir(exp, arch, seed, phase, arm, *, updates=None, ckpt_sha=None, complete=True):
    """A run directory carrying only its `completion.json`.

    `collect_scores` binds a score to the run it claims to come from, so a synthetic
    score needs a synthetic run: the checkpoint file itself is never written (nothing
    reads its bytes unless it exists), only the record that says what the run finished on.
    """
    name = TR.run_key(arch, seed, phase, arm)
    folder = Path(exp) / 'runs' / name
    folder.mkdir(parents=True, exist_ok=True)
    updates = updates if updates is not None else (TR.AWAKE_UPDATES if phase == 'awake'
                                                   else TR.OFFLINE_UPDATES)
    ckpt = folder / TR.checkpoint_name(updates)
    record = dict(kind='novelty19-run', arch=arch, seed=int(seed), phase=phase, arm=arm,
                  complete=bool(complete), updates_done=updates, total_updates=updates,
                  checkpoint=str(ckpt), checkpoint_sha256=ckpt_sha or fake_sha(name))
    (folder / 'completion.json').write_text(json.dumps(record))
    return record


# M-2: every real artifact carries `source_fingerprint()`, so every synthetic one must
# too -- a run without it is now a refusal, not an unknown.  `extra=` overrides it.
FAKE_FINGERPRINT = dict(fable_novelty19_train=fake_sha('trainer-v1'),
                        fable_novelty19_data=fake_sha('data-v1'),
                        fable_dispatcher_v4=fake_sha('dispatcher-v1'),
                        torch='0.0.0+fixture')


def fake_score(exp, arch, seed, phase, arm, cells, *, panels=None, panel_sha=None,
               updates=None, ckpt_updates=None, ckpt_sha=None, run=True, complete=True,
               extra=None, name=None):
    folder = Path(exp) / 'scores'
    folder.mkdir(parents=True, exist_ok=True)
    if panels is None:
        panels, disk_sha = fake_panels(exp)
        panel_sha = panel_sha or disk_sha
    key = TR.run_key(arch, seed, phase, arm)
    registered = TR.AWAKE_UPDATES if phase == 'awake' else TR.OFFLINE_UPDATES
    if run:
        fake_run_dir(exp, arch, seed, phase, arm, complete=complete)
    payload = dict(kind='novelty19-score', arch=arch, seed=int(seed), phase=phase, arm=arm,
                   updates_done=registered if updates is None else updates,
                   total_updates=registered,
                   checkpoint=str(Path(exp) / 'runs' / key / TR.checkpoint_name(
                       registered if ckpt_updates is None else ckpt_updates)),
                   checkpoint_sha256=ckpt_sha or fake_sha(key),
                   data_fingerprint=fake_sha(f'{phase}|{arm}|{int(seed)}'),
                   eval_cap=TR.D_EVAL_CAP if arch == 'D' else None,
                   output_capacity=TR.T_OUTPUT_CAPACITY if arch == 'T' else None,
                   oracle_operator_diagnostic=bool(arch == 'D'),
                   panels=str(Path(panels).resolve()),
                   panel_manifest_sha256=panel_sha, panel_guard=dict(is_confirmation=False),
                   source_fingerprint=dict(FAKE_FINGERPRINT),
                   n_per_cell=FAKE_N, cells=cells)
    payload.update(extra or {})
    (folder / f'{name or key}.json').write_text(json.dumps(payload))
    return payload


def fake_buffers(exp, seed, *, gate=True):
    folder = Path(exp) / 'buffers' / str(int(seed))
    folder.mkdir(parents=True, exist_ok=True)
    structures = {k: dict(distinct_questions=18, distinct_worlds=17, awake_instances=0,
                          required=16, passed=bool(gate))
                  for k in ('c=4,r=8', 'c=4,r=9', 'c=5,r=8', 'c=5,r=9')}
    per_arm = {}
    for arm, long_share in (('R', 0), ('G', 4), ('U', 26)):
        histogram = {'c=1,r=8': 20, 'c=2,r=9': 40 - long_share,
                     'c=4,r=8': long_share, 'c=5,r=9': long_share}
        per_arm[arm] = dict(arm=arm, fallbacks=0, length_histogram=histogram,
                            accepted={'total': sum(histogram.values())},
                            sha256=f'buffer-{arm}-s{int(seed)}')
    audit = dict(kind='buffers', seed=int(seed), arms=['R', 'G', 'U'], per_arm=per_arm,
                 identical_world_bytes=dict(identical=True),
                 generation_gate=dict(passed=bool(gate), structures=structures),
                 composite_r10_exposure=dict(zero_exposure=True))
    (folder / 'audit.json').write_text(json.dumps(audit))
    manifest = dict(kind='buffers', seed=int(seed), arms=['R', 'G', 'U'],
                    files={f'buffer-{a}.pt': per_arm[a]['sha256'] for a in per_arm},
                    audit_sha256=TR.sha(folder / 'audit.json'))
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return folder


REPLAY_N_FLOOR = {cell: (40, 40) for cell in TR.PRIMARY_CELLS}


def full_evidence(exp, *, awake_over=None, offline_over=None, gate=True, skip=(),
                  seeds=None, score_over=None):
    """Every registered run for both architectures, so a verdict can be decided.

    The replay arm is given a low but non-zero N-cell score, so that a default run is a
    clean primary PASS and each failure case below has to break exactly one thing.
    """
    for seed in (seeds or FAKE_SEEDS):
        fake_buffers(exp, seed, gate=gate)
        for arch in TR.ARCHES:
            if (arch, int(seed), 'awake', None) in skip:
                continue
            fake_score(exp, arch, seed, 'awake', None,
                       fake_cells(overrides=(awake_over or {}).get((arch, int(seed)))),
                       **((score_over or {}).get((arch, int(seed), 'awake', None)) or {}))
            for arm in TR.ARMS:
                if (arch, int(seed), 'offline', arm) in skip:
                    continue
                over = dict(REPLAY_N_FLOOR if arm == 'R' else {})
                over.update((offline_over or {}).get((arch, int(seed), arm)) or {})
                fake_score(exp, arch, seed, 'offline', arm, fake_cells(overrides=over),
                           **((score_over or {}).get((arch, int(seed), 'offline', arm)) or {}))


def run_report(exp, seeds=FAKE_SEEDS):
    return TR.report(TR.build_parser().parse_args(
        ['report', '--exp', str(exp), '--seeds', ','.join(str(int(s)) for s in seeds)]))


def test_report_calls_an_absent_run_missing_and_never_a_zero():
    exp = scratch('report-missing')
    fake_score(exp, 'D', FAKE_SEEDS[0], 'awake', None, fake_cells())
    payload = run_report(exp)
    text = payload['text']
    assert TR.MISSING in text
    assert len(payload['missing_runs']) == 2 * 3 * 4 - 1, payload['missing_runs']
    assert payload['primary']['D-G']['passed'] is None, 'a missing arm produced a verdict'
    assert payload['primary']['T-G']['passed'] is None
    assert payload['development_rule']['passed'] is not True
    assert not (Path(exp) / 'DEV-PASSED.json').exists(), 'missing runs unlocked confirmation'
    assert payload['forgetting_screen']['D']['outcome'] == 'UNDETERMINED', \
        'missing evidence was read as no forgetting'
    assert ' 0/ 0' not in text, 'an absent run was printed as a zero'
    assert payload['awake_fit_gate'][TR.run_key('T', FAKE_SEEDS[0], 'awake', None)]['passed'] \
        is None
    assert payload['generation_gate'] == {} and all(
        payload['length_mix'][str(int(s))] is None for s in FAKE_SEEDS)
    return (f'{len(payload["missing_runs"])} absent runs printed as {TR.MISSING}, every '
            f'verdict null, no unlock file')


def test_forgetting_trigger_needs_one_fixed_cell_and_metric_twice():
    # one cell, one metric, one arm, a 9-point strict drop in two of the three seeds
    drops = {(a, int(s), 'G'): {'F-c2-r8': (64, 55)}
             for a in ('D',) for s in FAKE_SEEDS[:2]}
    exp = scratch('forget-trigger')
    full_evidence(exp, offline_over=drops)
    payload = run_report(exp)
    screen = payload['forgetting_screen']['D']
    assert screen['outcome'] == 'TRIGGER', screen['outcome']
    assert screen['triggered'] == ['G|F-c2-r8|strict'], screen['triggered']
    combo = screen['combos']['G|F-c2-r8|strict']
    assert combo['replications'] == 2 and combo['tally']['no_drop'] == 1
    assert combo['per_seed'][str(FAKE_SEEDS[0])]['delta'] == 9
    assert screen['combos']['G|F-c2-r8|answers']['replications'] == 0, \
        'the answer metric borrowed the strict drop'
    assert payload['forgetting_screen']['T']['outcome'] == 'NO-TRIGGER'
    # and the primary verdict is untouched by the screen
    assert payload['primary']['D-G']['passed'] is True
    # scattered drops in different cells never replicate
    exp2 = scratch('forget-scattered')
    full_evidence(exp2, offline_over={('D', int(FAKE_SEEDS[0]), 'G'): {'F-c2-r8': (64, 55)},
                                      ('D', int(FAKE_SEEDS[1]), 'G'): {'F-c3-r9': (64, 55)},
                                      ('D', int(FAKE_SEEDS[2]), 'R'): {'F-c2-r8': (55, 64)}})
    second = run_report(exp2)['forgetting_screen']['D']
    assert second['outcome'] == 'NO-TRIGGER', second['triggered'] + second['undetermined']
    return ('a fixed (arm, cell, metric) losing 9/64 in 2 of 3 seeds triggers; the same '
            'total spread over different cells, metrics and arms does not')


def test_forgetting_eligibility_and_missing_evidence():
    # an H cell whose awake answer count is below 58 is not eligible for that metric
    exp = scratch('forget-eligibility')
    full_evidence(exp, awake_over={('D', int(s)): {'H-c2-p6': (50, 64)} for s in FAKE_SEEDS},
                  offline_over={('D', int(s), 'G'): {'H-c2-p6': (20, 30)}
                                for s in FAKE_SEEDS[:2]})
    screen = run_report(exp)['forgetting_screen']['D']
    answers = screen['combos']['G|H-c2-p6|answers']
    strict = screen['combos']['G|H-c2-p6|strict']
    assert answers['tally']['not_eligible'] == 3, answers['tally']
    assert answers['replications'] == 0 and not answers['triggered']
    assert strict['replications'] == 2 and strict['triggered'], strict['tally']
    assert screen['outcome'] == 'TRIGGER'
    # a failed awake-fit gate disqualifies the seed and leaves the question open
    exp2 = scratch('forget-gate')
    full_evidence(exp2, awake_over={('D', int(s)): {'F-c1-r8': (40, 40)} for s in FAKE_SEEDS})
    gated = run_report(exp2)['forgetting_screen']['D']
    assert set(gated['awake_fit_gate'].values()) == {False}
    assert gated['outcome'] == 'UNDETERMINED', gated['outcome']
    # and one absent offline arm leaves it open rather than clearing it
    exp3 = scratch('forget-partial')
    full_evidence(exp3, skip={('D', int(FAKE_SEEDS[0]), 'offline', 'G'),
                              ('D', int(FAKE_SEEDS[1]), 'offline', 'G')})
    partial = run_report(exp3)['forgetting_screen']['D']
    assert partial['outcome'] == 'UNDETERMINED'
    assert partial['combos']['G|F-c1-r8|strict']['tally']['missing'] == 2
    assert all(v['denominator'] == 3 for v in [partial, gated, screen]), \
        'the three-seed denominator shrank'
    return ('H eligibility is per metric, a failed awake gate and an absent arm both leave '
            'the screen undetermined, denominator stays 3')


def test_length_mix_is_read_from_the_buffers():
    exp = scratch('mix')
    for seed in FAKE_SEEDS:
        fake_buffers(exp, seed)
    mixes = TR.length_mix(exp, seeds=FAKE_SEEDS)
    for seed in FAKE_SEEDS:
        row = mixes[str(int(seed))]
        assert row['audit_sha256_matches'] is True
        assert set(row['arms']) == {'R', 'G', 'U'}
        assert row['arms']['G']['four_or_five_share'] < row['arms']['U']['four_or_five_share']
        assert row['arms']['R']['four_or_five_calls'] == 0
        assert row['arms']['G']['four_or_five_calls'] == 8
    # the real fixture buffers parse the same way
    real = scratch('mix-real')
    shutil.copytree(fixture() / 'buffers', real / 'buffers' / 'seed')
    row = TR.length_mix(real, seeds=(FIXTURE_SEED,))[str(FIXTURE_SEED)]
    assert row is not None and row['audit_sha256_matches'] is True
    assert set(row['arms']) == {'R', 'G', 'U'}
    assert all(v['questions'] > 0 for v in row['arms'].values())
    return (f'G {mixes[str(FAKE_SEEDS[0])]["arms"]["G"]["four_or_five_share"]:.1%} vs U '
            f'{mixes[str(FAKE_SEEDS[0])]["arms"]["U"]["four_or_five_share"]:.1%} at c=4/5, '
            f'and the real buffer audit parses')


def test_dev_passed_is_written_only_when_the_registered_rule_passes():
    # The unlock record is pinned to the registered THREE-seed set, so the passing case
    # has to carry those seed NUMBERS.  Nothing is trained, loaded or scored here: these
    # are hand-written JSON documents in a temporary folder that is deleted afterwards.
    exp = scratch('dev-pass')
    seeds = N.REGISTERED_SEEDS
    full_evidence(exp, seeds=seeds)
    payload = run_report(exp, seeds=seeds)
    flag = Path(exp) / 'DEV-PASSED.json'
    assert payload['development_rule']['passed'] is True, payload['development_rule']['parts']
    assert flag.exists(), 'a passing development rule did not unlock confirmation'
    unlock = json.loads(flag.read_text())
    assert set(unlock) == {'schema', 'seeds', 'report_sha256', 'dev_panels',
                           'awake_checkpoints', 'offline_checkpoints'}, sorted(unlock)
    assert unlock['schema'] == N.DEV_PASSED_SCHEMA
    assert unlock['report_sha256'] == TR.sha(Path(exp) / 'report.json')
    assert unlock['seeds'] == [int(s) for s in seeds]
    _, disk_sha = fake_panels(exp)
    assert unlock['dev_panels']['manifest_sha256'] == disk_sha
    assert TR.sha(Path(unlock['dev_panels']['path']) / 'manifest.json') == disk_sha
    assert len(unlock['awake_checkpoints']) == 6 and len(unlock['offline_checkpoints']) == 18
    assert set(unlock['awake_checkpoints']) == set(N.AWAKE_CHECKPOINT_KEYS)
    assert set(unlock['offline_checkpoints']) == set(N.OFFLINE_CHECKPOINT_KEYS)
    for value in list(unlock['awake_checkpoints'].values()) \
            + list(unlock['offline_checkpoints'].values()):
        assert TR.HEX64.match(value), value
    assert (Path(exp) / 'DEV-PASSED.meta.json').exists(), 'no provenance sidecar'
    # every way the rule can fail keeps the flag unwritten -- still on the registered
    # seed set, so it is the RULE that refuses and not the seed-set guard
    cases = {
        'primary gain': dict(offline_over={('D', int(s), 'R'): {c: (64, 64) for c in
                                                                TR.PRIMARY_CELLS}
                                           for s in seeds}),
        'E guard': dict(offline_over={('D', int(seeds[0]), 'G'): {TR.E_CELLS[0]: (64, 50)}}),
        'F retention': dict(offline_over={('D', int(seeds[1]), 'G'): {'F-c1-r8': (60, 60)}}),
        'awake fit': dict(awake_over={('D', int(seeds[2])): {'F-c3-r8': (55, 55)}}),
        'generation gate': dict(gate=False),
        'mid-run checkpoint': dict(score_over={('D', int(seeds[0]), 'offline', 'G'):
                                               dict(updates=TR.OFFLINE_UPDATES // 2)}),
    }
    broke = []
    for label, kwargs in cases.items():
        folder = scratch('dev-fail')
        full_evidence(folder, seeds=seeds, **kwargs)
        result = run_report(folder, seeds=seeds)
        assert result['development_rule']['passed'] is not True, label
        assert not (Path(folder) / 'DEV-PASSED.json').exists(), f'{label} still unlocked'
        broke.append(label)
    return f'unlocked once on a full pass; refused by each of: {", ".join(broke)}'


def test_dev_passed_is_never_written_for_a_non_registered_seed_set():
    """Must-fix 1: `--seeds` is a working view, never the registered verdict.

    An audit showed `report --seeds 9991` printing PASS and writing the unlock file for a
    one-seed experiment, against a data module that demands exactly six awake and
    eighteen offline keys over 1900/1901/1902.
    """
    outcomes = []
    for label, chosen in (('three non-registered seeds', FAKE_SEEDS),
                          ('one seed', FAKE_SEEDS[:1]),
                          ('two registered seeds', N.REGISTERED_SEEDS[:2])):
        exp = scratch('dev-pass-seeds')
        full_evidence(exp, seeds=chosen)
        payload = run_report(exp, seeds=chosen)
        assert payload['development_rule']['passed'] is True, \
            f'{label}: the fixture was meant to satisfy the rule on its own seeds'
        assert not (Path(exp) / 'DEV-PASSED.json').exists(), f'{label} unlocked confirmation'
        assert not (Path(exp) / 'DEV-PASSED.meta.json').exists(), f'{label} wrote a sidecar'
        assert any('cannot unlock confirmation' in p
                   for p in payload['dev_passed_problems']), payload['dev_passed_problems']
        outcomes.append(f'{label}: refused')
        _, _, problems = TR.dev_passed_payload(exp, TR.collect_scores(exp, seeds=chosen),
                                               payload['development_rule'],
                                               Path(exp) / 'report.json', seeds=chosen)
        assert problems and 'registered development rule is over exactly' in problems[0]
    return '; '.join(outcomes)


def test_a_score_must_be_the_final_checkpoint_of_a_finished_run():
    """Must-fix 3: scoring a mid-run checkpoint is legal; calling it the run is not.

    An audit scored `ckpt-000003.pt` of an eight-update run and the report merged it as
    though it were the result, because nothing compared the score against the run's own
    `completion.json`.
    """
    base = dict(arch='D', seed=int(FAKE_SEEDS[0]), phase='offline', arm='G')
    forgeries = {
        'mid-run update count': dict(updates=TR.OFFLINE_UPDATES // 2,
                                     ckpt_updates=TR.OFFLINE_UPDATES // 2),
        'run never finished': dict(complete=False),
        'no run directory at all': dict(run=False),
        'checkpoint hash the run never wrote': dict(ckpt_sha=fake_sha('somewhere else')),
        'not the run\'s final checkpoint': dict(ckpt_updates=TR.OFFLINE_UPDATES // 4),
    }
    caught = []
    for label, kwargs in forgeries.items():
        exp = scratch('bind')
        fake_score(exp, cells=fake_cells(), **base, **kwargs)
        collected = TR.collect_scores(exp, seeds=FAKE_SEEDS)
        key = TR.run_key(**base)
        assert key not in collected['runs'], f'{label} was merged as a run'
        assert key in collected['missing'], f'{label} did not count as missing'
        assert key in collected['rejected_runs'], f'{label} was dropped without a reason'
        caught.append(label)
    # the same file, correctly bound, does merge -- so the check is the binding and not
    # some accident of the fixture
    good = scratch('bind-ok')
    fake_score(good, cells=fake_cells(), **base)
    collected = TR.collect_scores(good, seeds=FAKE_SEEDS)
    assert TR.run_key(**base) in collected['runs'] and not collected['rejected']
    # and the report prints it as "(wrong checkpoint)", not as a zero and not as a pass
    exp = scratch('bind-report')
    full_evidence(exp, seeds=FAKE_SEEDS,
                  score_over={('D', int(FAKE_SEEDS[0]), 'offline', 'G'):
                              dict(updates=TR.OFFLINE_UPDATES // 2)})
    payload = run_report(exp)
    assert TR.WRONG_CKPT in payload['text'], payload['text'][:600]
    assert payload['primary']['D-G']['passed'] is None, 'a forged score decided the primary'
    assert payload['development_rule']['parts']['evidence_complete']['passed'] is False
    return f'{len(caught)} forged bindings refused: ' + ', '.join(caught)


def test_a_score_at_a_non_registered_cap_never_merges():
    """Must-fix 4: D is scored at eval cap 16 and T at output capacity 12, or not at all."""
    refused = []
    for label, arch, extra in (
            ('D at eval cap 4', 'D', dict(eval_cap=4)),
            ('D at eval cap 64', 'D', dict(eval_cap=64)),
            ('D with no cap recorded', 'D', dict(eval_cap=None)),
            ('T at capacity 9', 'T', dict(output_capacity=9)),
            ('T carrying a D cap', 'T', dict(eval_cap=16)),
    ):
        exp = scratch('caps')
        key = dict(arch=arch, seed=int(FAKE_SEEDS[0]), phase='awake', arm=None)
        fake_score(exp, cells=fake_cells(), extra=extra, **key)
        collected = TR.collect_scores(exp, seeds=FAKE_SEEDS)
        assert TR.run_key(**key) not in collected['runs'], f'{label} merged'
        assert collected['rejected'] and any('cap' in r.lower() or 'capacity' in r.lower()
                                             for r in collected['rejected'][0]['reasons']), \
            collected['rejected']
        refused.append(label)
    # two partial files for one run that disagree about the scoring knobs are a conflict,
    # never a pooled number
    exp = scratch('caps-split')
    key = dict(arch='D', seed=int(FAKE_SEEDS[0]), phase='awake', arm=None)
    half = {c: r for c, r in fake_cells().items() if c.startswith('F-')}
    rest = {c: r for c, r in fake_cells().items() if not c.startswith('F-')}
    fake_score(exp, cells=half, name='wave-a', **key)
    fake_score(exp, cells=rest, name='wave-b', extra=dict(oracle_operator_diagnostic=False),
               **key)
    collected = TR.collect_scores(exp, seeds=FAKE_SEEDS)
    assert any(c['reason'] == 'two scoring caps for one run' for c in collected['conflicts']), \
        collected['conflicts']
    merged = collected['runs'][TR.run_key(**key)]['cells']
    assert set(merged) == set(half), 'the disagreeing wave was merged anyway'
    # ...while two agreeing waves of one run do merge by cell
    ok = scratch('caps-merge')
    fake_score(ok, cells=half, name='wave-a', **key)
    fake_score(ok, cells=rest, name='wave-b', **key)
    second = TR.collect_scores(ok, seeds=FAKE_SEEDS)
    assert not second['conflicts'] and not second['rejected']
    assert set(second['runs'][TR.run_key(**key)]['cells']) == set(N.DEV_CELL_ORDER)
    return f'{len(refused)} off-registry caps refused; a cap disagreement is a conflict'


def test_gates_reports_both_prerequisites_and_never_invents_a_pass():
    exp = scratch('gates')
    full_evidence(exp)
    out = Path(exp) / 'gates.json'
    verdict = TR.gates(TR.build_parser().parse_args(
        ['gates', '--exp', str(exp), '--out', str(out),
         '--seeds', ','.join(str(int(s)) for s in FAKE_SEEDS)]))
    assert verdict['awake_fit_gate_passed'] == {'D': True, 'T': True}
    assert verdict['generation_gate_passed'] == {int(s): True for s in FAKE_SEEDS}
    key = TR.run_key('D', FAKE_SEEDS[0], 'awake', None)
    assert len(verdict['awake_fit_gate'][key]['cells']) == len(TR.FIT_CELLS) == 7
    assert all(c['need'] == TR.AWAKE_FIT_MARK
               for c in verdict['awake_fit_gate'][key]['cells'].values())
    assert out.exists() and json.loads(out.read_text())['kind'] == 'novelty19-gates'
    # one F cell below the mark fails that arch, and an absent awake run stays null
    broken = scratch('gates-fail')
    full_evidence(broken, awake_over={('D', int(FAKE_SEEDS[1])): {'F-c2-r9': (60, 64)}},
                  skip={('T', int(FAKE_SEEDS[2]), 'awake', None)})
    second = TR.gates(TR.build_parser().parse_args(
        ['gates', '--exp', str(broken),
         '--seeds', ','.join(str(int(s)) for s in FAKE_SEEDS)]))
    assert second['awake_fit_gate_passed']['D'] is False
    assert second['awake_fit_gate_passed']['T'] is None, 'an absent run counted as a pass'
    missing = second['awake_fit_gate'][TR.run_key('T', FAKE_SEEDS[2], 'awake', None)]
    assert missing['present'] is False and missing['passed'] is None
    assert all(c['passed'] is None for c in missing['cells'].values())
    return ('awake-fit and generation gates both reported per seed; 60/64 fails, an '
            'absent run is null')


def test_merged_runs_must_come_from_one_frozen_script_version():
    """M-2: `source_fingerprint` was written into every artifact and read back nowhere.

    `checkpoint_sha256` embeds it, so two trainer versions make the checkpoint hashes of
    different runs incomparable -- a fact this session met head-on: a five-line edit that
    provably changed no weight, no datum and no RNG draw still changed all ten checkpoint
    hashes.  "One frozen script version" was a launch instruction; here it becomes a
    checked fact, over the whole fingerprint (this file, the seven frozen modules it
    imports, and torch) and over every merged run.
    """
    def gate(exp):
        return TR.gates(TR.build_parser().parse_args(
            ['gates', '--exp', str(exp), '--seeds',
             ','.join(str(int(s)) for s in FAKE_SEEDS)]))

    # (a) uniform: every run carries the same fingerprint, so nothing is in the way
    ok = scratch('one-version')
    full_evidence(ok)
    verdict = gate(ok)
    version = verdict['single_trainer_version']
    assert version['passed'] is True and version['distinct'] == 1, version
    assert not version['offending_runs'] and not version['runs_without_a_fingerprint']
    assert len(version['per_run']) == len(TR.ARCHES) * len(FAKE_SEEDS) * (1 + len(TR.ARMS))

    # (b) mixed: one run built by a trainer whose own file differs by a single byte
    odd = (('D', int(FAKE_SEEDS[1]), 'offline', 'G'),)
    other = dict(FAKE_FINGERPRINT, fable_novelty19_train=fake_sha('trainer-v2'))
    mixed = scratch('two-versions')
    full_evidence(mixed, score_over={odd[0]: dict(extra=dict(source_fingerprint=other))})
    try:
        gate(mixed)
    except SystemExit as exc:
        assert 'one frozen script version' in str(exc), str(exc)
        assert TR.run_key(*odd[0]) in str(exc), str(exc)
        assert 'fable_novelty19_train' in str(exc), str(exc)
    else:
        raise AssertionError('two trainer versions were merged into one verdict')
    collected = TR.collect_scores(mixed, seeds=FAKE_SEEDS)
    got = TR.trainer_version(collected, seeds=FAKE_SEEDS)
    assert got['passed'] is False and got['distinct'] == 2
    assert got['offending_runs'] == [TR.run_key(*odd[0])], got['offending_runs']
    assert got['differing_fields'] == ['fable_novelty19_train'], got['differing_fields']
    # and the report refuses too, after writing its evidence down
    target = Path(mixed) / 'report.json'
    try:
        run_report(mixed)
    except SystemExit as exc:
        assert 'one frozen script version' in str(exc), str(exc)
    else:
        raise AssertionError('report merged two trainer versions')
    assert target.exists(), 'report refused without writing the evidence of the mix'
    written = json.loads(target.read_text())
    assert written['single_trainer_version']['distinct'] == 2
    assert written['development_rule']['parts']['evidence_complete']['passed'] is False

    # (c) missing: a score file with no fingerprint was not written by this script
    absent = scratch('no-version')
    full_evidence(absent, score_over={odd[0]: dict(extra=dict(source_fingerprint=None))})
    try:
        gate(absent)
    except SystemExit as exc:
        assert 'without a fingerprint' in str(exc), str(exc)
        blank = TR.trainer_version(TR.collect_scores(absent, seeds=FAKE_SEEDS),
                                   seeds=FAKE_SEEDS)
        assert blank['passed'] is False
        assert blank['runs_without_a_fingerprint'] == [TR.run_key(*odd[0])]
        return ('one fingerprint across 18 runs passes; a second trainer version and a '
                'run with no fingerprint are both refused by name')
    raise AssertionError('a run with no source_fingerprint was merged')


def test_dev_passed_satisfies_the_data_modules_own_validator():
    """The unlock file is checked by `fable_novelty19_data.validate_dev_passed`.

    Its schema pins the seed list to the registered seeds, so the synthetic score files
    here carry those numbers.  Nothing is trained: these are hand-written JSON documents
    in a temporary folder, and no registered run, checkpoint or panel exists.
    """
    if not hasattr(N, 'validate_dev_passed'):
        raise _Skip('the data module has no validate_dev_passed yet')
    exp = scratch('dev-pass-schema')
    full_evidence(exp, seeds=N.REGISTERED_SEEDS)
    payload = run_report(exp, seeds=N.REGISTERED_SEEDS)
    assert payload['development_rule']['passed'] is True
    flag = Path(exp) / 'DEV-PASSED.json'
    assert flag.exists()
    verdict = N.validate_dev_passed(exp)
    assert verdict['awake_checkpoints'] == 6 and verdict['offline_checkpoints'] == 18
    assert verdict['sha256'] == TR.sha(flag)
    # and the validator is genuinely strict: one edited hash and it refuses
    doc = json.loads(flag.read_text())
    doc['offline_checkpoints'][N.OFFLINE_CHECKPOINT_KEYS[0]] = 'not-a-sha'
    flag.write_text(json.dumps(doc))
    try:
        N.validate_dev_passed(exp)
    except SystemExit as exc:
        assert 'not sha256' in str(exc), str(exc)
        return (f'{verdict["awake_checkpoints"]} awake + {verdict["offline_checkpoints"]} '
                f'offline hashes accepted by validate_dev_passed, and one bad hash refused')
    raise AssertionError('the validator accepted a corrupted unlock file')


# --------------------------------------------------------------- runner


def main():
    print(f'novelty19 training checks   fixture seed {FIXTURE_SEED}   '
          f'registered seeds {TR.REGISTERED_SEEDS} are NOT trained here', flush=True)
    names = sorted(n for n in globals() if n.startswith('test_'))
    for name in names:
        check(name.replace('test_', '', 1), globals()[name])
    for folder in TEMP:
        shutil.rmtree(folder, ignore_errors=True)
    print(f'\n{PASSED} passed, {len(FAILED)} failed, {len(SKIPPED)} skipped '
          f'out of {len(names)}', flush=True)
    for name, detail in FAILED:
        print(f'  FAIL {name}: {detail}', flush=True)
    for name, detail in SKIPPED:
        print(f'  skip {name}: {detail}', flush=True)
    if FAILED:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
