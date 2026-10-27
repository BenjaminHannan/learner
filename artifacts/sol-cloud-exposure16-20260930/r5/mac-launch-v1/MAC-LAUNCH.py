#!/usr/bin/env python3
"""Watcher-owned r5 transport;600s total per seed, small receipts, no PC archive."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time

W = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q = Path('/Users/ben-hannan/premonition-watch/queue')
PC = 'C:/Users/benja/sol-cloud-exposure16-r5'
PCPY = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
DEPLOY = Path('artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1')
OWN = Path('artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1')
EXPOSURE = 'artifacts/sol-cloud-exposure16-20260930/r5'
STRICT = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
          '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2']
STARTED = None
STAGE = 'initial'
DISPATCHED = False
OUT = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')
        stream.flush()


def remaining(reserve=0):
    seconds = 600 - (time.monotonic() - STARTED) - reserve
    if seconds <= 0:
        raise TimeoutError('sealed total600second budget exhausted; preserve original evidence')
    return seconds


def run(command, stage, *, cap=10, reserve=0, **kwargs):
    global STAGE
    STAGE = stage
    return subprocess.run(command, check=True, capture_output=True,
                          timeout=min(cap, remaining(reserve)), **kwargs)


def rpc(source, stage, *, cap=10, reserve=0):
    result = run(['ssh', '-T', *STRICT, 'benspc', PCPY + ' -X utf8 -B -'], stage,
                 input=source.encode('utf-8'), cap=cap, reserve=reserve)
    return result.stdout


def check_pin(record):
    path = W / record['path']
    assert sha(path) == record['sha256'], 'pinned source differs: ' + record['path']
    return path


def running_gpu_jobs(job):
    return sorted(marker.stem for marker in Q.glob('*.running') if marker.stem != job
                  and 'GPU: yes' in (Q / (marker.stem + '.md')).read_text(encoding='utf-8').splitlines())


def optional_runner_metadata(job):
    pattern = r'rungo[45]\.sh ' + re.escape(str(Q / (job + '.md')))
    try:
        result = subprocess.run(['pgrep', '-f', pattern], capture_output=True,
                                timeout=min(2, remaining()))
        pids = [int(pid) for pid in result.stdout.decode('ascii', errors='ignore').split() if pid.isdigit()] if result.returncode == 0 else []
        return {'actual_runner_pids': pids, 'runner_lookup_returncode': result.returncode,
                'runner_lookup_available': bool(pids)}
    except subprocess.TimeoutExpired:
        return {'actual_runner_pids': [], 'runner_lookup_available': False}


def prerequisites(spec):
    assert (Q / 'sol-cloud-fixture-night-v3-benspc.exit').read_text().strip() == 'rc=1'
    assert not (Q / 'sol-cloud-fixture-night-v3-benspc.running').exists()
    assert (Q / 'sol-cloud-fixture-v3-small-receipts-collect.exit').read_text().strip() == 'rc=0'
    assert not (Q / 'sol-cloud-fixture-v3-small-receipts-collect.running').exists()
    collection = json.loads(check_pin(spec['collection_receipt']).read_text())
    assert collection['PC_originals_preserved'] is True and collection['PC_archive_created_by_collection'] is False
    copied = W / spec['collection_copied_root']
    for relative in ('artifacts/sol-cloud-fixture-20260930/TRANSPORT-v3.json',
                     'artifacts/sol-cloud-fixture-20260930/run-v3/completion.json'):
        expected = next(row for row in collection['copied_receipts'] if row['relative'] == relative)
        path = copied / relative
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256']
        record = json.loads(path.read_text())
        assert record['actual_user_day'] is False and record['activated'] is False
        if relative.endswith('TRANSPORT-v3.json'):
            assert record['returncode'] == 0
        else:
            assert record['schema'] == 'sol.cloud.fixture-completion.v1' and record['eligible_rows'] == 16
    assert (Q / 'sol-cloud-offline-launch-smoke-r5-v2.exit').read_text().strip() == 'rc=0'
    for host in ('Mac', 'PC'):
        smoke = json.loads(check_pin(spec['smoke'][host]).read_text())
        assert smoke['pass'] is True and smoke['actual_host_import_execution'] is True
        assert smoke['source_seal_reference']['sha256'] == spec['exposure_seal_sha256']


def preflight_source(seed, spec):
    return '''import hashlib,json,pathlib,shutil
root=pathlib.Path(ROOT)
assert shutil.disk_usage('C:/').free>=1073741824+402653184,'reserve plus bounded run output'
if SEED==0:
 assert not root.exists(),'freshseed0root required; no partial restart'
 root.mkdir()
else:
 assert root.is_dir(),'existing serialseed0root required'
 for name,expected in PINS.items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,'delivered package differs'
 prior=json.loads((root/'artifacts/sol-cloud-exposure16-20260930/r5/TRANSPORT-s0.json').read_text())
 assert type(prior['returncode']) is int,'seed0 must have a closed transport disposition'
print(json.dumps({'seed':SEED,'fresh_root_created':SEED==0,'disk_free_bytes':shutil.disk_usage(root).free,'actual_user_day':False}))
'''.replace('ROOT', repr(PC)).replace('SEED', repr(seed)).replace('PINS', repr({
        'PACKAGE.json': spec['package']['sha256'], 'payload.tar.gz': spec['payload']['sha256']}))


def validate_small_records(records, seed):
    prefix = EXPOSURE + '/runs/s%d/' % seed
    selected = []
    for record in records:
        path = PurePosixPath(record['relative'])
        assert not path.is_absolute() and '..' not in path.parts and ':' not in record['relative'] and '\\' not in record['relative']
        assert record['relative'].startswith(prefix)
        assert type(record['bytes']) is int and record['bytes'] >= 0
        assert re.fullmatch('[0-9a-f]{64}', record['sha256'])
        if path.suffix in ('.json', '.log') and record['bytes'] <= 1024 ** 2:
            selected.append(record)
    assert len({record['relative'] for record in selected}) == len(selected)
    assert sum(record['bytes'] for record in selected) <= 4 * 1024 ** 2
    return selected


def collect_source(records, seed):
    extras = [EXPOSURE + '/TRANSPORT-s%d.json' % seed, EXPOSURE + '/worker-stdout-s%d.log' % seed,
              DEPLOY.as_posix() + '/INVENTORY-s%d.json' % seed, DEPLOY.as_posix() + '/MAC-WATCHER-PROOF-s%d.json' % seed]
    return '''import base64,hashlib,json,pathlib
root=pathlib.Path(ROOT).resolve()
expected=RECORDS
paths=[record['relative'] for record in expected]+EXTRAS
assert len(paths)==len(set(paths))
result=[];total=0
for relative in paths:
 path=root/relative
 assert not path.is_symlink() and path.resolve().is_relative_to(root)
 metadata=path.stat();assert metadata.st_size<=1048576
 total+=metadata.st_size;assert total<=8388608
 data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
 assert len(data)==metadata.st_size
 matches=[r for r in expected if r['relative']==relative]
 if matches:assert digest==matches[0]['sha256'] and len(data)==matches[0]['bytes']
 result.append({'relative':relative,'bytes':len(data),'sha256':digest,'data_b64':base64.b64encode(data).decode('ascii')})
print(json.dumps({'schema':'sol.cloud.exposure16.small-return.v1','records':result,'source_deletions':0,'PC_archive_created':False,'actual_user_day':False}),flush=True)
'''.replace('ROOT', repr(PC)).replace('RECORDS', repr(records)).replace('EXTRAS', repr(extras))


def main():
    global STARTED, OUT, DISPATCHED, STAGE
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--started-monotonic', type=float, required=True)
    args = parser.parse_args()
    STARTED = args.started_monotonic
    assert platform.system() == 'Darwin' and sys.version_info[:3] == (3, 9, 6)
    assert Path.cwd().resolve() == W.resolve()
    assert sha(args.spec) == args.spec_sha256
    spec = json.loads(Path(args.spec).read_text())
    job = 'sol-cloud-exposure16-r5-s%d-benspc' % args.seed
    assert spec['seed'] == args.seed and spec['job'] == job
    assert (Q / (job + '.running')).is_file() and not (Q / (job + '.exit')).exists()
    OUT = W / OWN / ('execution-s%d' % args.seed)
    OUT.mkdir(parents=True, exist_ok=False)
    write_new(OUT / 'MAC-LAUNCH-START.json', {'job': job, 'actual_user_day': False, 'outer_seconds': 600})
    copied = (Q / (job + '.md')).read_bytes()
    tracked = run(['git', 'show', 'origin/main:handoff/queue/' + job + '.md'], 'verify actual copied queue').stdout
    assert copied == tracked
    prerequisites(spec)
    assert running_gpu_jobs(job) == [], 'another GPU watcher claim is running'
    package = json.loads(check_pin(spec['package']).read_text())
    check_pin(spec['payload']);bootstrap_path = check_pin(spec['bootstrap'])
    proof = {'job': job, 'running_marker_exists': True, 'copied_queue_equals_origin_main': True,
             'other_watcher_running_claims': [], 'smoke_pass': True,
             'prior_fixture_inner_completion_rc': 0, 'prior_fixture_outer_rc': 1,
             'small_receipt_collector_rc': 0, 'package_sha256': spec['package']['sha256'],
             'queue_sha256': hashlib.sha256(copied).hexdigest(), 'actual_user_day': False,
             'native_python': sys.executable, 'python_version': sys.version,
             'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             **optional_runner_metadata(job)}
    write_new(OUT / 'MAC-WATCHER-PROOF.json', proof)
    preflight = rpc(preflight_source(args.seed, spec), 'prepare exact PC source root', reserve=575)
    write_new(OUT / 'PC-STAGING-PREFLIGHT.json', json.loads(preflight))
    if args.seed == 0:
        for name, record in [('PACKAGE.json', spec['package']), ('payload.tar.gz', spec['payload'])]:
            run(['scp', *STRICT, str(check_pin(record)), 'benspc:' + PC + '/' + name],
                'upload pinned ' + name, reserve=575)
    assert remaining() >= 580, 'transport staging consumed owned570s worker headroom'
    proof['Mac_elapsed_seconds_before_dispatch'] = time.monotonic() - STARTED
    proof['outer_seconds_remaining'] = remaining()
    proof64 = base64.b64encode(json.dumps(proof, sort_keys=True).encode()).decode('ascii')
    STAGE = 'dispatch sealed PC supervisor'
    DISPATCHED = True
    with (OUT / 'PC-stdout.log').open('xb') as log:
        completed = subprocess.run(['ssh', '-T', *STRICT, 'benspc',
                                    PCPY + ' -X utf8 -B - ' + str(args.seed) + ' ' + spec['package']['sha256'] + ' ' + proof64],
                                   input=bootstrap_path.read_bytes(), stdout=log,
                                   stderr=subprocess.DEVNULL, timeout=remaining(5))
    write_new(OUT / 'PC-SSH-EXIT.json', {'returncode': completed.returncode, 'seed': args.seed,
                                       'actual_user_day': False, 'activated': False})
    stdout = (OUT / 'PC-stdout.log').read_bytes()
    assert len(stdout) <= 256 * 1024, 'small bootstrap stdout bound'
    final = json.loads(stdout.decode('utf-8').splitlines()[-1])
    assert final['job'] == job and final['seed'] == args.seed and type(final['returncode']) is int
    write_new(OUT / 'PC-FINAL-MANIFEST.json', final)
    records = validate_small_records(final['records'], args.seed)
    returned = json.loads(rpc(collect_source(records, args.seed), 'return exact small JSON/log receipts',
                              cap=remaining(), reserve=0))
    assert returned['schema'] == 'sol.cloud.exposure16.small-return.v1' and returned['PC_archive_created'] is False
    for record in returned['records']:
        data = base64.b64decode(record.pop('data_b64'), validate=True)
        assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
        destination = OUT / 'copied' / record['relative']
        assert destination.resolve().is_relative_to(OUT.resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(data)
    returned.update(outer_wall_seconds=time.monotonic() - STARTED, seed=args.seed,
                    transport_returncode=final['returncode'], large_weights_retained_on_PC=True)
    assert returned['outer_wall_seconds'] <= 600
    write_new(OUT / 'SMALL-RETURN.json', returned)
    print(json.dumps({'job': job, 'returncode': final['returncode'], 'small_receipts': len(returned['records']),
                      'large_weights_retained_on_PC': True, 'actual_user_day': False, 'activated': False}), flush=True)
    return final['returncode']


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        failure = {'stage': STAGE, 'exception_type': type(error).__name__,
                   'subprocess_returncode': getattr(error, 'returncode', None),
                   'PC_bootstrap_dispatched': DISPATCHED, 'PC_originals_preserved': True,
                   'actual_user_day': False, 'activated': False,
                   'optimizer_updates': 'unknown; inspect original saved ledger' if DISPATCHED else 0,
                   'raw_diagnostics_suppressed': True}
        if OUT is not None and OUT.is_dir() and not (OUT / 'MAC-FAILURE.json').exists():
            write_new(OUT / 'MAC-FAILURE.json', failure)
        print(json.dumps(failure, sort_keys=True), flush=True)
        raise SystemExit(1)
