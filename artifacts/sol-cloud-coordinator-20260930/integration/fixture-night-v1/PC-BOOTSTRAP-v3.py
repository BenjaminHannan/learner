#!/usr/bin/env python3
"""Stdlib verifier/transport for one watcher-owned PC fixture dispatch."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

JOB = 'sol-cloud-fixture-night-v3-benspc'
ROOT = Path('C:/Users/benja/sol-cloud-fixture-night-v3')
DEPLOY = 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1'
FLOOR = 1024 ** 3
CAP = 256 * 1024 ** 2

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
    return digest.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())

def main():
    package_sha, proof_b64 = sys.argv[1:3]
    package_path = ROOT / 'PACKAGE-v3.json'
    assert sha(package_path) == package_sha, 'sealed package bytes required'
    package = json.loads(package_path.read_text(encoding='utf8'))
    assert package['schema'] == 'sol.cloud.fixture-package.v1'
    assert Path(package['pc_root']).resolve() == ROOT.resolve()
    assert package['actual_user_day'] is False and package['activation_allowed'] is False
    assert sha(ROOT / 'payload-v3.tar.gz') == package['payload']['sha256']
    assert (ROOT / 'payload-v3.tar.gz').stat().st_size == package['payload']['bytes'] < 1024 ** 2
    proof = json.loads(base64.b64decode(proof_b64, validate=True))
    assert proof['job'] == JOB and proof['running_marker_exists'] and proof['copied_queue_equals_origin_main']
    assert proof['collector_v4_exit'] == 'rc=0'
    # Runner lookup is optional metadata; actual queue/claim/marker proofs gate execution.
    claim = Path('C:/Users/benja/claims/sol-cloud-fixture-night-v3')
    assert claim.is_dir(), 'watcher-created shared claim required; wrapper cannot create a lease'
    busy = Path('C:/Users/benja/GPU-BUSY.txt')
    for _ in range(20):
        if busy.is_file() and ('queue job ' + JOB + ' since ') in busy.read_text(encoding='utf8'):
            break
        time.sleep(.25)
    else:
        raise RuntimeError('exact existing watcher GPU marker required')
    assert shutil.disk_usage(ROOT).free >= FLOOR + CAP + 8 * 1024 ** 2
    with tarfile.open(ROOT / 'payload-v3.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(package['files']) and set(archive.getnames()) == set(package['files'])
        for member in members:
            path = Path(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
            assert not (ROOT / path).exists(), 'extract once; preserve any earlier partial deployment'
        assert sum(member.size for member in members) <= 4 * 1024 ** 2, 'sealed uncompressed package cap'
        for member in members:
            data = archive.extractfile(member).read()
            assert len(data) == member.size and hashlib.sha256(data).hexdigest() == package['files'][member.name]
            target = ROOT / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as destination:
                destination.write(data)
    for relative, expected in package['files'].items():
        assert sha(ROOT / relative) == expected, 'source closure hash changed: ' + relative
    binding_path = ROOT / DEPLOY / 'BINDING-v3.json'
    binding = json.loads(binding_path.read_text(encoding='utf8'))
    for record in binding['source'].values():
        if isinstance(record, dict) and set(record) == {'path', 'sha256'}:
            assert sha(record['path']) == record['sha256'], 'external exact source tuple changed'
    fixture = ROOT / 'artifacts/sol-cloud-fixture-20260930'
    night = ROOT / 'artifacts/sol-cloud-night-20260930'
    fixture.mkdir(parents=True, exist_ok=False)
    night.mkdir(parents=True, exist_ok=False)
    write(fixture / 'MAC-WATCHER-PROOF.json', proof)
    write(fixture / 'PC-CLAIM-PROOF.json', {'job': JOB, 'shared_claim_exists': True,
          'GPU_marker_matches_job': True, 'package_sha256': package_sha, 'source_tuple_hashes_verified': True,
          'launch_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'native_python': sys.executable, 'native_python_version': sys.version,
          'active_pointer_initialized_or_changed': False, 'actual_user_day': False})
    environment = dict(os.environ, JOB=JOB, TREE=str(ROOT.resolve()), PYTHONUTF8='1',
                       PYTHONPATH=str(ROOT.resolve()) + os.pathsep + str((ROOT / 'scripts').resolve()),
                       HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2')
    command = [sys.executable, '-X', 'utf8', '-B', str(ROOT / 'scripts/sol_cloud_fixture_v1.py'),
               '--spec', str(ROOT / DEPLOY / 'FIXTURE-SPEC-v3.json'), '--spec-sha256', package['spec_sha256'], 'cycle']
    result = {'job': JOB, 'returncode': None, 'actual_user_day': False, 'activated': False,
              'start_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'optimizer_updates': 'read saved ledger'}
    started = time.monotonic()
    try:
        with (fixture / 'cycle-stdout.log').open('x', encoding='utf8') as stream:
            result['returncode'] = subprocess.run(command, cwd=ROOT, env=environment, stdout=stream,
                                                  stderr=subprocess.STDOUT, timeout=1100).returncode
    except subprocess.TimeoutExpired:
        result['returncode'] = 124
        result['failure'] = 'owned fixture process exceeded outer budget; preserve candidate and prior pointer'
    finally:
        result['wall_seconds'] = time.monotonic() - started
        result['finish_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(fixture / 'TRANSPORT-v3.json', result)
        files = sorted(path for folder in [fixture, night] for path in folder.rglob('*') if path.is_file())
        inventory = [{'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in files]
        source_bytes = sum(record['bytes'] for record in inventory)
        project_bytes = sum(path.stat().st_size for path in ROOT.rglob('*') if path.is_file())
        estimate = source_bytes + 1024 ** 2
        assert project_bytes + estimate <= CAP, 'aggregate payload/output/return atomic cap; PC originals retained'
        assert shutil.disk_usage(ROOT).free >= FLOOR + estimate, 'reserve before return archive'
        write(fixture / 'RETURN-SOURCE-MANIFEST-v3.json', {'records': inventory, 'source_bytes': source_bytes,
              'no_source_deletions': True, 'actual_user_day': False, 'activated': False})
        archive_path = ROOT / 'fixture-return-v3.tar.gz'
        with tarfile.open(archive_path, 'x:gz') as archive:
            for path in files + [fixture / 'RETURN-SOURCE-MANIFEST-v3.json']:
                archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
        assert sum(path.stat().st_size for path in ROOT.rglob('*') if path.is_file()) <= CAP
        assert shutil.disk_usage(ROOT).free >= FLOOR
        output_manifest = {'archive': {'path': str(archive_path), 'bytes': archive_path.stat().st_size,
                           'sha256': sha(archive_path)}, 'records': inventory, 'source_files_preserved': True,
                           'actual_user_day': False, 'activated': False, 'transport': result}
        write(ROOT / 'RETURN-MANIFEST-v3.json', output_manifest)
        print(json.dumps(output_manifest), flush=True)
    return result['returncode']

if __name__ == '__main__':
    sys.exit(main())
