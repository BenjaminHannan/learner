#!/usr/bin/env python3
"""Follow-up training-side probes: the lockout's actual test, the trainer's own
partial-cell refusal, un-registered scoring knobs, and mid-run checkpoints."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import fable_dispatcher_v3 as V3                       # noqa: E402
import fable_novelty19_data as N                       # noqa: E402
import fable_novelty19_train as TR                     # noqa: E402

PY, TRAIN = sys.executable, str(ROOT / 'scripts' / 'fable_novelty19_train.py')
S = HERE / 'scratch2'
out = {}


def run(*argv):
    p = subprocess.run([PY, '-B', TRAIN, *argv], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


# ---- 1. what does the confirmation lockout actually test? --------------------------
lock = S / 'attack' / 'lock2'
shutil.rmtree(lock, ignore_errors=True)
lock.mkdir(parents=True)
conf = S / 'confirm-manifest-only'
shutil.rmtree(conf, ignore_errors=True)
conf.mkdir(parents=True)
(conf / 'manifest.json').write_text(json.dumps(dict(kind='confirmation',
                                                    namespace=N.NS_CONFIRM, n=512)))
cases = {}
for label, body in (('empty-object', '{}'),
                    ('wrong-schema', json.dumps(dict(schema='something-else'))),
                    ('one-seed', json.dumps(dict(schema=N.DEV_PASSED_SCHEMA, seeds=[9991],
                                                 awake_checkpoints={}, offline_checkpoints={},
                                                 dev_panels={}))),
                    ('not-json', 'this is not json at all')):
    (lock / 'DEV-PASSED.json').write_text(body)
    try:
        guard = TR.guard_confirmation(conf, True, lock)
        cases[label] = dict(accepted=True, guard=guard)
    except SystemExit as exc:
        cases[label] = dict(accepted=False, message=str(exc)[:160])
    except Exception as exc:                                        # noqa: BLE001
        cases[label] = dict(accepted=False, error=f'{type(exc).__name__}: {exc}'[:160])
out['lockout_contents_check'] = dict(
    cases=cases,
    verdict='guard_confirmation tests Path.exists() only; any bytes unlock confirmation')

# ---- 2. the trainer's OWN partial-cell refusal (manifest kept consistent) -----------
part = S / 'dev-partial2'
shutil.rmtree(part, ignore_errors=True)
shutil.copytree(S / 'dev', part)
victim = part / 'F-c1-r8.json'
data = json.loads(victim.read_text())
data['units'] = data['units'][:32]
victim.write_text(json.dumps(data, sort_keys=True))
man = json.loads((part / 'manifest.json').read_text())
before = json.dumps(man['files']['F-c1-r8.json'] if isinstance(man.get('files'), dict) else None)
if isinstance(man.get('files'), dict):
    man['files']['F-c1-r8.json'] = TR.sha(victim)
if 'cells' in man and 'F-c1-r8' in man['cells']:
    pass                       # leave manifest n at 64: the trainer must notice the mismatch
(part / 'manifest.json').write_text(json.dumps(man, sort_keys=True, indent=1))
code, so, se = run('score', '--arch', 'T', '--ckpt',
                   str(S / 'runs/awake-T-whole/ckpt-000008.pt'), '--panels', str(part),
                   '--out', str(S / 'attack' / 'partial2.json'), '--cells', 'F-c2-r8')
out['trainer_partial_cell_refusal'] = dict(
    manifest_hash_rewritten=before, returncode=code,
    stderr=(se.strip().splitlines() or [''])[-1][:300], refused=code != 0)
shutil.rmtree(part, ignore_errors=True)

# ---- 3. un-registered scoring knobs are accepted and never re-checked --------------
knobs = {}
for label, extra in (('eval-cap-64', ['--eval-cap', '64']),
                     ('eval-cap-4', ['--eval-cap', '4'])):
    target = S / 'attack' / f'knob-{label}.json'
    target.unlink(missing_ok=True)
    code, so, se = run('score', '--arch', 'D', '--ckpt',
                       str(S / 'runs/awake-D-whole/ckpt-000008.pt'), '--panels', str(S / 'dev'),
                       '--out', str(target), '--cells', 'F-c1-r8', '--no-oracle', *extra)
    payload = json.loads(target.read_text()) if target.exists() else {}
    knobs[label] = dict(returncode=code, eval_cap=payload.get('eval_cap'),
                        answers=payload.get('cells', {}).get('F-c1-r8', {}).get('answers'),
                        oracle=payload.get('oracle_operator_diagnostic'))
for label, extra in (('capacity-20', ['--capacity', '20']),
                     ('capacity-9', ['--capacity', '9'])):
    target = S / 'attack' / f'knob-{label}.json'
    target.unlink(missing_ok=True)
    code, so, se = run('score', '--arch', 'T', '--ckpt',
                       str(S / 'runs/awake-T-whole/ckpt-000008.pt'), '--panels', str(S / 'dev'),
                       '--out', str(target), '--cells', 'L-c8-held', *extra)
    payload = json.loads(target.read_text()) if target.exists() else {}
    knobs[label] = dict(returncode=code, output_capacity=payload.get('output_capacity'),
                        answers=payload.get('cells', {}).get('L-c8-held', {}).get('answers'),
                        stderr=(se.strip().splitlines() or [''])[-1][:160])
out['unregistered_scoring_knobs'] = dict(
    cases=knobs,
    collect_scores_checks_cap=False,
    note='score records eval_cap / output_capacity, but collect_scores, gates and report '
         'never read them back, so files produced at different caps merge silently; the '
         'ceiling diagnostic always divides by the registered constant')

# ---- 4. a MID-RUN checkpoint scores and merges as if it were the run ---------------
target = S / 'attack' / 'midrun.json'
target.unlink(missing_ok=True)
code, so, se = run('score', '--arch', 'D', '--ckpt', str(S / 'runs/awake-D-chunk/ckpt-000003.pt'),
                   '--panels', str(S / 'dev'), '--out', str(target), '--cells', 'F-c1-r8',
                   '--no-oracle')
payload = json.loads(target.read_text()) if target.exists() else {}
out['midrun_checkpoint'] = dict(
    returncode=code, accepted=code == 0, updates_done=payload.get('updates_done'),
    total_updates=payload.get('total_updates'), phase=payload.get('phase'),
    run_key=TR.run_key(payload.get('arch'), payload.get('seed'), payload.get('phase'),
                       payload.get('arm')) if payload else None,
    note='collect_scores keys only on arch/seed/phase/arm, so this file would be merged '
         'into the run as though it were the 6,000-update result')

# ---- 5. resume after a killed chunk -------------------------------------------------
killed = S / 'runs' / 'killed'
shutil.rmtree(killed, ignore_errors=True)
killed.mkdir(parents=True)
# simulate a chunk that died mid-way: its log exists, its checkpoint does not
(killed / 'log-000000-000003.jsonl').write_text('{"update": 0}\n')
code, so, se = run('awake', '--arch', 'T', '--seed', '9991', '--out', str(killed),
                   '--stream', str(S / 'awake'), '--updates', '6', '--chunk-updates', '3',
                   '--quiet')
out['killed_chunk_resume'] = dict(
    returncode=code, stderr=(se.strip().splitlines() or [''])[-1][:200],
    refuses_to_continue=code != 0,
    note='a half-written chunk cannot be silently accepted, but the operator must delete '
         'the stale log by hand before the wave can be resumed')

# corrupted checkpoint at a boundary
corrupt = S / 'runs' / 'corrupt'
shutil.rmtree(corrupt, ignore_errors=True)
shutil.copytree(S / 'runs' / 'awake-T-chunk', corrupt)
(corrupt / 'completion.json').unlink()
for p in corrupt.glob('ckpt-000006.pt'):
    p.write_bytes(p.read_bytes()[:-64])
code, so, se = run('awake', '--arch', 'T', '--seed', '9991', '--out', str(corrupt),
                   '--stream', str(S / 'awake'), '--updates', '8', '--chunk-updates', '3',
                   '--quiet')
out['corrupt_checkpoint_resume'] = dict(
    returncode=code, stderr=(se.strip().splitlines() or [''])[-1][:200],
    refused=code != 0,
    checkpoint_sha_verified_against_chunk_json=False,
    note='the chunk-*.json records checkpoint_sha256 but resume never re-checks it')
shutil.rmtree(corrupt, ignore_errors=True)
shutil.rmtree(killed, ignore_errors=True)

print(json.dumps(out, indent=1, default=str))
(HERE / 'train-probes2.json').write_text(json.dumps(out, indent=1, default=str))
