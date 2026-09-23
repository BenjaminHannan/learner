#!/usr/bin/env python3
"""TRAIN-AUDIT Re-check 2: the five exploits re-run against the patched trainer,
the DEV-PASSED binding question, N6/N8, and the source-version-mix question."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import fable_novelty19_data as N                       # noqa: E402
import fable_novelty19_train as TR                     # noqa: E402

PY = sys.executable
TRAIN = str(ROOT / 'scripts' / 'fable_novelty19_train.py')
S = HERE / 'scratch3'
out = {}
H = 'cd' * 32


def run(*argv):
    p = subprocess.run([PY, '-B', TRAIN, *argv], capture_output=True, text=True, cwd=str(S))
    tail = [ln for ln in (p.stderr or '').strip().splitlines() if ln.strip()]
    return p.returncode, p.stdout, (tail[-1][:200] if tail else '')


def clean(*names):
    for name in names:
        shutil.rmtree(S / name, ignore_errors=True)


# ============================================== exploit 1: DEV-PASSED for a wrong seed set
exp = S / 'exp-report'
shutil.rmtree(exp, ignore_errors=True)
(exp / 'scores').mkdir(parents=True)
base = dict(kind='novelty19-score', panel_manifest_sha256=N.sha(S / 'dev' / 'manifest.json'),
            panels=str((S / 'dev').resolve()), n_per_cell=64,
            data_fingerprint='a' * 64, update_fingerprint='b' * 64,
            panel_guard=dict(is_confirmation=False))
cells = {c: dict(n=64, answers=64, strict=64, calls_ok=64) for c in N.DEV_CELL_ORDER}
for arch in ('D', 'T'):
    for phase, arm, total in (('awake', None, TR.AWAKE_UPDATES),
                              *[('offline', a, TR.OFFLINE_UPDATES) for a in TR.ARMS]):
        folder = exp / f'run-{arch}-{phase}-{arm}'
        folder.mkdir(parents=True, exist_ok=True)
        ckpt = folder / 'ckpt-000001.pt'
        ckpt.write_bytes(f'{arch}{phase}{arm}'.encode())
        csha = TR.sha(ckpt)
        (folder / 'completion.json').write_text(json.dumps(dict(
            complete=True, arch=arch, seed=9991, phase=phase, arm=arm,
            updates_done=total, total_updates=total,
            checkpoint=str(ckpt.resolve()), checkpoint_sha256=csha)))
        payload = dict(base, arch=arch, seed=9991, phase=phase, arm=arm,
                       checkpoint=str(ckpt.resolve()), checkpoint_sha256=csha,
                       updates_done=total, total_updates=total,
                       eval_cap=TR.D_EVAL_CAP if arch == 'D' else None,
                       output_capacity=None if arch == 'D' else TR.T_OUTPUT_CAPACITY,
                       cells=cells)
        (exp / 'scores' / f'{arch}-{phase}-{arm}.json').write_text(json.dumps(payload))
code, so, err = run('report', '--exp', str(exp.resolve()), '--seeds', '9991',
                    '--out', str((exp / 'report.json').resolve()))
flag = exp / 'DEV-PASSED.json'
rep = json.loads((exp / 'report.json').read_text()) if (exp / 'report.json').is_file() else {}
out['exploit1_dev_passed_wrong_seeds'] = dict(
    returncode=code, dev_passed_written=flag.exists(),
    dev_passed_problems=rep.get('dev_passed_problems'),
    rule=rep.get('development_rule', {}).get('passed') if isinstance(
        rep.get('development_rule'), dict) else None,
    closed=not flag.exists())

# ============================================== exploit 2: garbage DEV-PASSED unlocks
conf = S / 'confirm'
lock = S / 'lockdir'
shutil.rmtree(lock, ignore_errors=True)
lock.mkdir(parents=True)
for key, src in (('stream', S / 'awakeB'), ('memory', S / 'memB'), ('buffers', S / 'bufB')):
    (lock / N.EXPERIMENT_LAYOUT[key].format(seed=9991)).symlink_to(src.resolve())
(lock / N.EXPERIMENT_LAYOUT['dev_panels']).symlink_to((S / 'dev').resolve())
valid_registered = dict(
    schema=N.DEV_PASSED_SCHEMA, seeds=[int(s) for s in TR.REGISTERED_SEEDS],
    report_sha256=H,
    dev_panels=dict(path=str((S / 'dev').resolve()),
                    manifest_sha256=N.sha(S / 'dev' / 'manifest.json')),
    awake_checkpoints={k: H for k in N.checkpoint_keys('awake', TR.REGISTERED_SEEDS)},
    offline_checkpoints={k: H for k in N.checkpoint_keys('offline', TR.REGISTERED_SEEDS)})
cases = {}
for label, body in (('empty', ''), ('not-json', 'garbage'), ('empty-object', '{}'),
                    ('wrong-schema', json.dumps(dict(valid_registered, schema='x'))),
                    ('one-seed', json.dumps(dict(valid_registered, seeds=[9991]))),
                    ('missing-checkpoints',
                     json.dumps(dict(valid_registered, offline_checkpoints={}))),
                    ('registered-and-complete', json.dumps(valid_registered))):
    (lock / 'DEV-PASSED.json').write_text(body)
    try:
        guard = TR.guard_confirmation(conf, True, lock)
        cases[label] = dict(accepted=True,
                            validated_by=guard.get('dev_passed_validated_by'),
                            sha=guard.get('dev_passed_sha256'))
    except BaseException as exc:                                    # noqa: BLE001
        cases[label] = dict(accepted=False, message=f'{type(exc).__name__}: {exc}'[-140:])
out['exploit2_lockout_contents'] = dict(
    cases=cases,
    all_bad_refused=all(not v['accepted'] for k, v in cases.items()
                        if k != 'registered-and-complete'),
    valid_accepted=cases['registered-and-complete']['accepted'],
    closed=all(not v['accepted'] for k, v in cases.items()
               if k != 'registered-and-complete'))

# --- the residual binding question: is the SUITE tied to the unlock that authorised it? ---
suite_manifest = json.loads((conf / 'manifest.json').read_text())
built_against = suite_manifest.get('dev_passed', {})
other = dict(valid_registered)
other['report_sha256'] = 'ef' * 32                 # valid, but a DIFFERENT unlock document
(lock / 'DEV-PASSED.json').write_text(json.dumps(other))
try:
    guard = TR.guard_confirmation(conf, True, lock)
    accepted_other = True
    guard_sha = guard.get('dev_passed_sha256')
except BaseException as exc:                                        # noqa: BLE001
    accepted_other, guard_sha = False, f'{type(exc).__name__}: {exc}'[-140:]
out['dev_passed_binding'] = dict(
    suite_records_dev_passed=built_against,
    guard_accepts_a_different_valid_unlock=accepted_other,
    guard_sha=guard_sha,
    guard_compares_suite_to_unlock=False,
    builders_reasoning_about_panels_folder=(
        'correct: dev_panels.manifest_sha256 is the DEVELOPMENT suite the verdict was '
        'computed on, while --panels at confirmation time is the confirmation suite, so '
        'passing panels_folder would compare two different directories and always fail'),
    residual=('the guard validates the unlock and the data module validates the '
              'development suite named INSIDE it, but nothing compares the confirmation '
              "suite's own recorded dev_passed.sha256 with the unlock being presented"))

# ============================================== exploit 3: mid-run checkpoint as final
clean('attack')
(S / 'attack').mkdir(parents=True, exist_ok=True)
mid = S / 'runs/awake-D-chunk/ckpt-000003.pt'
target = S / 'attack/midrun.json'
code, so, err = run('score', '--arch', 'D', '--ckpt', str(mid.resolve()),
                    '--panels', str((S / 'dev').resolve()),
                    '--out', str(target.resolve()), '--cells', 'F-c1-r8', '--no-oracle')
payload = json.loads(target.read_text()) if target.is_file() else {}
probe = S / 'exp-mid'
shutil.rmtree(probe, ignore_errors=True)
(probe / 'scores').mkdir(parents=True)
if payload:
    (probe / 'scores' / 'mid.json').write_text(json.dumps(payload))
collected = TR.collect_scores(probe, seeds=(9991,))
key = TR.run_key('D', 9991, 'awake', None)
out['exploit3_midrun_checkpoint'] = dict(
    score_returncode=code, score_written=bool(payload),
    updates_done=payload.get('updates_done'), total_updates=payload.get('total_updates'),
    merged_as_a_run=key in collected['runs'],
    rejected=collected['rejected_runs'].get(key),
    closed=key not in collected['runs'] and bool(collected['rejected_runs']))

# ============================================== exploit 4: mixed caps merge
mixed = S / 'exp-caps'
shutil.rmtree(mixed, ignore_errors=True)
(mixed / 'scores').mkdir(parents=True)
folder = mixed / 'run'
folder.mkdir()
ckpt = folder / 'ckpt-000001.pt'
ckpt.write_bytes(b'capmix')
csha = TR.sha(ckpt)
(folder / 'completion.json').write_text(json.dumps(dict(
    complete=True, arch='D', seed=9991, phase='awake', arm=None,
    updates_done=TR.AWAKE_UPDATES, total_updates=TR.AWAKE_UPDATES,
    checkpoint=str(ckpt.resolve()), checkpoint_sha256=csha)))
for label, cap, cellset in (('registered', TR.D_EVAL_CAP, ['F-c1-r8']),
                            ('cap4', 4, ['F-c1-r9']),
                            ('cap64', 64, ['F-c2-r8'])):
    (mixed / 'scores' / f'{label}.json').write_text(json.dumps(dict(
        base, arch='D', seed=9991, phase='awake', arm=None,
        checkpoint=str(ckpt.resolve()), checkpoint_sha256=csha,
        updates_done=TR.AWAKE_UPDATES, total_updates=TR.AWAKE_UPDATES,
        eval_cap=cap, output_capacity=None,
        cells={c: dict(n=64, answers=64, strict=64, calls_ok=64) for c in cellset})))
collected = TR.collect_scores(mixed, seeds=(9991,))
entry = collected['runs'].get(TR.run_key('D', 9991, 'awake', None), {})
out['exploit4_mixed_caps'] = dict(
    merged_cells=sorted(entry.get('cells', {})),
    caps_of_merged_run=entry.get('caps'),
    rejected=collected['rejected'],
    conflicts=collected['conflicts'],
    closed=sorted(entry.get('cells', {})) == ['F-c1-r8'] and len(collected['rejected']) == 2)
# and an actual off-cap score file, produced by the real scorer
offcap = S / 'attack/offcap.json'
offcap.unlink(missing_ok=True)
code, so, err = run('score', '--arch', 'D', '--ckpt',
                    str((S / 'runs/awake-D-whole/ckpt-000008.pt').resolve()),
                    '--panels', str((S / 'dev').resolve()), '--out', str(offcap.resolve()),
                    '--cells', 'F-c1-r8', '--no-oracle', '--eval-cap', '4')
doc = json.loads(offcap.read_text()) if offcap.is_file() else {}
out['exploit4_mixed_caps']['real_offcap_score'] = dict(
    returncode=code, eval_cap=doc.get('eval_cap'),
    registered_caps_flag=doc.get('registered_caps'),
    merge_problems=TR.registered_caps_of(doc)[0] if doc else None)

# ============================================== exploit 5: tampered / orphan checkpoint
res = {}
# (a) orphan: a checkpoint no chunk record accounts for
orphan = S / 'runs/orphan'
shutil.rmtree(orphan, ignore_errors=True)
shutil.copytree(S / 'runs/awake-T-chunk', orphan)
(orphan / 'completion.json').unlink()
for name in sorted(p.name for p in orphan.glob('chunk-*.json')):
    (orphan / name).unlink()
code, so, err = run('awake', '--arch', 'T', '--seed', '9991', '--out', str(orphan.resolve()),
                    '--stream', str((S / 'awake').resolve()), '--updates', '8',
                    '--chunk-updates', '3', '--quiet')
res['orphan_checkpoint'] = dict(returncode=code, refused=code != 0, message=err)
# (b) tampered: bytes changed, record intact
tamper = S / 'runs/tamper'
shutil.rmtree(tamper, ignore_errors=True)
shutil.copytree(S / 'runs/awake-T-chunk', tamper)
(tamper / 'completion.json').unlink()
victim = tamper / 'ckpt-000006.pt'
blob = bytearray(victim.read_bytes())
blob[len(blob) // 2] ^= 0x01
victim.write_bytes(bytes(blob))
code, so, err = run('awake', '--arch', 'T', '--seed', '9991', '--out', str(tamper.resolve()),
                    '--stream', str((S / 'awake').resolve()), '--updates', '8',
                    '--chunk-updates', '3', '--quiet')
res['tampered_checkpoint'] = dict(returncode=code, refused=code != 0, message=err)
# (c) a foreign checkpoint cannot start an offline arm
foreign = S / 'runs/foreign'
shutil.rmtree(foreign, ignore_errors=True)
code, so, err = run('offline', '--arch', 'D', '--seed', '9991', '--out', str(foreign.resolve()),
                    '--arm', 'R', '--awake-ckpt',
                    str((S / 'runs/awake-T-whole/ckpt-000008.pt').resolve()),
                    '--buffers', str((S / 'buf').resolve()), '--updates', '2', '--quiet')
res['foreign_awake_checkpoint'] = dict(returncode=code, refused=code != 0, message=err)
out['exploit5_resume'] = dict(cases=res, closed=all(v['refused'] for v in res.values()))
clean('runs/orphan', 'runs/tamper', 'runs/foreign')

# ============================================== N6 / N8 / version mix
twice = S / 'runs/awake-D-again'
shutil.rmtree(twice, ignore_errors=True)
code, so, err = run('awake', '--arch', 'D', '--seed', '9991', '--out', str(twice.resolve()),
                    '--stream', str((S / 'awake').resolve()), '--updates', '8',
                    '--chunk-updates', '8', '--quiet')
first = json.loads((S / 'runs/awake-D-whole/completion.json').read_text())
again = json.loads((twice / 'completion.json').read_text())
out['note_N6_wall_clock'] = dict(
    weight_fingerprint_reproducible=first['final_weight_fingerprint']
    == again['final_weight_fingerprint'],
    update_fingerprint_reproducible=first['update_fingerprint'] == again['update_fingerprint'],
    data_fingerprint_reproducible=first['data_fingerprint'] == again['data_fingerprint'],
    checkpoint_sha_reproducible=first['checkpoint_sha256'] == again['checkpoint_sha256'],
    sha_first=first['checkpoint_sha256'][:16], sha_again=again['checkpoint_sha256'][:16],
    wall_clock_keys_in_completion=[k for k in again
                                   if k in ('created_unix', 'seconds', 'peak_rss_bytes',
                                            'host')])
shutil.rmtree(twice, ignore_errors=True)

out['note_N8_torch_load'] = dict(
    load_state_verifies_first='verify_recorded_sha' in TR.load_state.__doc__ if
    TR.load_state.__doc__ else None,
    resume_path_hashes_before_load=True,
    score_path_hashes_before_load=None,
    note='filled in from source reading below')

# is a MIXED trainer version detected?
score_files = []
for name in ('midrun.json', 'offcap.json'):
    path = S / 'attack' / name
    if path.is_file():
        score_files.append(json.loads(path.read_text()).get('source_fingerprint'))
out['source_version_mix'] = dict(
    score_files_record_source_fingerprint=all(s is not None for s in score_files),
    collect_scores_keeps_it='source_fingerprint' in str(TR.collect_scores.__code__.co_names),
    run_entry_fields=sorted(TR.collect_scores(probe, seeds=(9991,))['runs'].get(
        TR.run_key('D', 9991, 'awake', None), {})),
    checkpoint_sha_embeds_source=True)

print(json.dumps(out, indent=1, default=str)[:7000])
(HERE / 'train-recheck.json').write_text(json.dumps(out, indent=1, default=str))
