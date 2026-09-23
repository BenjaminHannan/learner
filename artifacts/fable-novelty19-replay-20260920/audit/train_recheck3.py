#!/usr/bin/env python3
"""TRAIN-AUDIT Re-check 3: M-1 (unlock binding), M-2 (one frozen version), N8.

Independent of the builder's tests.  Disposable seed 9991 only; the registered-seed
material in part 2 is fabricated JSON -- no model is trained on 1900/1901/1902.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19_data as N                          # noqa: E402
import fable_novelty19_train as TR                        # noqa: E402

S = HERE / 'scratch4'
PY = '/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12'
TRAIN = str(ROOT / 'scripts' / 'fable_novelty19_train.py')
SEEDS = (9991,)
out = {}


def run(*argv):
    p = subprocess.run([PY, '-B', TRAIN, *argv], capture_output=True, text=True, cwd=str(S))
    return p.returncode, p.stdout, p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ''


# ======================================================================== part 1: M-1
exp = S / 'exp9991'
shutil.rmtree(exp, ignore_errors=True)
exp.mkdir(parents=True)
for key, src in (('stream', S / 'awake'), ('memory', S / 'mem'), ('buffers', S / 'buf')):
    (exp / N.EXPERIMENT_LAYOUT[key].format(seed=9991)).symlink_to(src.resolve())
(exp / N.EXPERIMENT_LAYOUT['dev_panels']).symlink_to((S / 'dev').resolve())
(exp / N.EXPERIMENT_LAYOUT['operator_history']).symlink_to((S / 'ophist').resolve())


def unlock(report_sha):
    """A structurally VALID novelty19-dev-passed-v1 record."""
    h = 'cd' * 32
    return dict(schema=N.DEV_PASSED_SCHEMA, seeds=[9991], report_sha256=report_sha,
                dev_panels=dict(path=str((S / 'dev').resolve()),
                                manifest_sha256=N.sha(S / 'dev' / 'manifest.json')),
                awake_checkpoints={k: h for k in N.checkpoint_keys('awake', SEEDS)},
                offline_checkpoints={k: h for k in N.checkpoint_keys('offline', SEEDS)})


first = unlock('cd' * 32)
(exp / 'DEV-PASSED.json').write_text(json.dumps(first))
first_sha = N.sha(exp / 'DEV-PASSED.json')

CELLS = ['N-c4-p6', 'L-c6-prac']
conf = S / 'confirm'
shutil.rmtree(conf, ignore_errors=True)
N.build_dev_panels(conf, n=8, namespace=N.NS_CONFIRM,
                   cells={c: N.DEV_CELLS[c] for c in CELLS}, cell_order=CELLS,
                   confirmation=True, experiment=exp, seeds=SEEDS, progress=False)
man_path = conf / 'manifest.json'
manifest = json.loads(man_path.read_text())
bound = manifest.get('dev_passed', {}).get('sha256')


def guard(label):
    try:
        got = TR.guard_confirmation(conf, True, exp)
        return dict(case=label, accepted=True,
                    bound=got.get('dev_passed_bound_to_suite'),
                    sha=got.get('dev_passed_sha256'))
    except BaseException as exc:                                        # noqa: BLE001
        return dict(case=label, accepted=False, message=str(exc)[-190:])


cases = [guard('the original unlock (control)')]

# a SECOND, equally valid verdict -- a re-run after a recipe tweak
second = unlock('ab' * 32)
(exp / 'DEV-PASSED.json').write_text(json.dumps(second))
second_sha = N.sha(exp / 'DEV-PASSED.json')
cases.append(guard('a second, independently valid unlock'))
(exp / 'DEV-PASSED.json').write_text(json.dumps(first))

# a suite that records no binding at all
for label, mutate in (('manifest dev_passed.sha256 removed',
                       lambda m: m['dev_passed'].pop('sha256', None)),
                      ('manifest dev_passed.sha256 blank',
                       lambda m: m['dev_passed'].update(sha256='')),
                      ('manifest dev_passed block removed',
                       lambda m: m.pop('dev_passed', None))):
    doc = json.loads(man_path.read_text())
    mutate(doc)
    man_path.write_text(json.dumps(doc, indent=1))
    cases.append(guard(label))
    man_path.write_text(json.dumps(manifest, indent=1))

cases.append(guard('the original unlock again (control after restore)'))
out['M1_unlock_binding'] = dict(
    suite_records=bound, first_unlock_sha=first_sha, second_unlock_sha=second_sha,
    two_unlocks_are_both_valid_and_different=bool(first_sha != second_sha),
    cases=cases,
    legitimate_unlock_passes=bool(cases[0]['accepted'] and cases[-1]['accepted']),
    every_attack_refused=all(not c['accepted'] for c in cases[1:-1]),
    closed=bool(cases[0]['accepted'] and cases[-1]['accepted']
                and all(not c['accepted'] for c in cases[1:-1])))

# ======================================================================== part 2: M-2
# Real cell rows, so the report renders a real document rather than a stub.
(S / 'scoretmp').mkdir(exist_ok=True)
rows = {}
for arch in ('D', 'T'):
    dest = S / 'scoretmp' / f'{arch}.json'
    dest.unlink(missing_ok=True)
    code, _so, err = run('score', '--arch', arch, '--ckpt',
                         str((S / f'runs/awake-{arch}/ckpt-000008.pt').resolve()),
                         '--panels', str((S / 'dev').resolve()),
                         '--out', str(dest.resolve()), '--cells', 'F-c1-r8', '--no-oracle')
    payload = json.loads(dest.read_text()) if dest.is_file() else {}
    rows[arch] = dict(row=payload.get('cells', {}).get('F-c1-r8'), rc=code, err=err)
out['real_rows_available'] = {a: rows[a]['row'] is not None for a in rows}

REAL = TR.source_fingerprint()
FAKE = dict(REAL, novelty19_train='9' * 64)
DRIFT = dict(REAL, novelty19_data='7' * 64)


def build_experiment(folder, *, fingerprints):
    """18 fabricated finished runs + 24 score documents for the registered seeds."""
    folder = Path(folder)
    shutil.rmtree(folder, ignore_errors=True)
    (folder / 'scores').mkdir(parents=True)
    for key, src in (('stream', S / 'awake'), ('memory', S / 'mem'), ('buffers', S / 'buf')):
        (folder / N.EXPERIMENT_LAYOUT[key].format(seed=9991)).symlink_to(src.resolve())
    panel_sha = N.sha(S / 'dev' / 'manifest.json')
    made = []
    for seed in TR.REGISTERED_SEEDS:
        for arch in TR.ARCHES:
            for phase, arm in (('awake', None),) + tuple(('offline', a) for a in TR.ARMS):
                key = TR.run_key(arch, seed, phase, arm)
                total = TR.AWAKE_UPDATES if phase == 'awake' else TR.OFFLINE_UPDATES
                rundir = folder / 'runs' / key
                rundir.mkdir(parents=True, exist_ok=True)
                ckpt = rundir / f'ckpt-{total:06d}.pt'          # never written: no .pt on disk
                ckpt_sha = hashlib.sha256(key.encode()).hexdigest()
                (rundir / 'completion.json').write_text(json.dumps(dict(
                    complete=True, arch=arch, seed=int(seed), phase=phase, arm=arm,
                    total_updates=total, updates_done=total,
                    checkpoint=str(ckpt.resolve()), checkpoint_sha256=ckpt_sha)))
                payload = dict(
                    kind='novelty19-score', arch=arch, seed=int(seed), phase=phase, arm=arm,
                    checkpoint=str(ckpt.resolve()), checkpoint_sha256=ckpt_sha,
                    updates_done=total, total_updates=total,
                    panel_manifest_sha256=panel_sha, panels=str((S / 'dev').resolve()),
                    panel_guard=dict(is_confirmation=False), n_per_cell=8,
                    data_fingerprint='f8' * 32, update_fingerprint='ab' * 32,
                    cell_order=list(N.DEV_CELL_ORDER),
                    cells={c: rows[arch]['row'] for c in N.DEV_CELL_ORDER},
                    source_fingerprint=fingerprints(key))
                if arch == 'D':
                    payload['eval_cap'] = TR.D_EVAL_CAP
                else:
                    payload['output_capacity'] = TR.T_OUTPUT_CAPACITY
                (folder / 'scores' / f'{key}.json').write_text(json.dumps(payload))
                made.append(key)
    return made


ODD = TR.run_key('D', 1900, 'awake', None)
scenarios = {
    'uniform (control)': lambda key: REAL,
    'one run from another trainer version': lambda key: FAKE if key == ODD else REAL,
    'one run from a drifted DATA script': lambda key: DRIFT if key == ODD else REAL,
    'one run with a null fingerprint': lambda key: None if key == ODD else REAL,
    'one run with the field absent': lambda key: {} if key == ODD else REAL,
}
m2 = {}
for label, fn in scenarios.items():
    made = build_experiment(S / 'exp-mix', fingerprints=fn)
    collected = TR.collect_scores(S / 'exp-mix')
    version = TR.trainer_version(collected)
    gcode, _gso, gerr = run('gates', '--exp', str((S / 'exp-mix').resolve()),
                            '--seeds', '1900,1901,1902')
    rcode, rso, rerr = run('report', '--exp', str((S / 'exp-mix').resolve()),
                           '--seeds', '1900,1901,1902')
    line = [ln.strip() for ln in rso.splitlines() if 'trainer version across' in ln]
    named = [ln.strip() for ln in rso.splitlines()
             if 'another version' in ln or 'no fingerprint' in ln]
    m2[label] = dict(
        runs_merged=len(collected['runs']), conflicts=len(collected['conflicts']),
        version_passed=version['passed'], distinct=version['distinct'],
        differing_fields=version['differing_fields'],
        offending_runs=version['offending_runs'],
        runs_without_a_fingerprint=version['runs_without_a_fingerprint'],
        gates_returncode=gcode, gates_refusal=gerr[-190:],
        report_returncode=rcode, report_line=line, report_names=named,
        report_wrote_dev_passed=(S / 'exp-mix' / 'DEV-PASSED.json').exists())
out['M2_one_frozen_version'] = dict(
    fingerprint_fields=sorted(REAL),
    covers_the_data_script=('novelty19_data' in REAL),
    scenarios=m2,
    closed=bool(m2['uniform (control)']['version_passed'] is True
                and m2['uniform (control)']['gates_returncode'] == 0
                and all(v['version_passed'] is False and v['gates_returncode'] != 0
                        for k, v in m2.items() if k != 'uniform (control)')))

# ======================================================================== part 3: N8
src = (ROOT / 'scripts' / 'fable_novelty19_train.py').read_text().splitlines()
start = next(i for i, ln in enumerate(src) if ln.startswith('def load_run_checkpoint'))
body = src[start:start + 14]
hashes_at = next((i for i, ln in enumerate(body) if 'verify_recorded_sha' in ln), None)
loads_at = next((i for i, ln in enumerate(body) if 'torch.load' in ln), None)
out['N8_hash_before_load'] = dict(
    verify_line=None if hashes_at is None else body[hashes_at].strip(),
    torch_load_line=None if loads_at is None else body[loads_at].strip(),
    verify_precedes_load=bool(hashes_at is not None and loads_at is not None
                              and hashes_at < loads_at),
    resume_path_unchanged=all(
        'verify_recorded_sha' in '\n'.join(src[i:i + 8])
        for i, ln in enumerate(src) if ln.strip().startswith('def load_state')
        or ln.strip().startswith('def load_weights_only')))

# ======================================================================== part 4
out['training_path'] = {
    a: json.loads((S / f'runs/awake-{a}/completion.json').read_text())
    for a in ('D', 'T')}
out['training_path'] = dict(
    awake_D_weight=out['training_path']['D']['final_weight_fingerprint'][:16],
    awake_T_weight=out['training_path']['T']['final_weight_fingerprint'][:16],
    data_D=out['training_path']['D']['data_fingerprint'][:16],
    data_T=out['training_path']['T']['data_fingerprint'][:16])
out['training_path']['matches_earlier_evidence'] = bool(
    out['training_path']['awake_D_weight'] == 'e216551f9f8c85ae'
    and out['training_path']['awake_T_weight'] == '48e8d108a1dbf5a8'
    and out['training_path']['data_D'] == 'f8c846112ff72f15'
    and out['training_path']['data_T'] == 'f8c846112ff72f15')

print(json.dumps(out, indent=1, default=str)[:7000])
(HERE / 'train-recheck3.json').write_text(json.dumps(out, indent=1, default=str))
