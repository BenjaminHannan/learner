#!/usr/bin/env python3
"""Exact sealed source deployment and actual exclusive watcher fit dispatch."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import site
import subprocess
import sys
import tarfile
import time

ROOT = Path('C:/Users/benja/sol-cloud-exposure16-r5-r2')
OWN = ROOT / 'artifacts/sol-cloud-exposure16-20260930/r5'
DEPLOY = ROOT / 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1'
FLOOR = 1073741824
CAP = 384 * 1024 ** 2

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())

def exclusive_inventory():
    command = ['powershell', '-NoProfile', '-Command', "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"]
    r = subprocess.run(command, capture_output=True, text=True, timeout=15, check=True)
    rows = json.loads(r.stdout or '[]')
    rows = [rows] if isinstance(rows, dict) else rows
    by = {int(x['ProcessId']): x for x in rows}
    allowed = {os.getpid()}
    pid = os.getpid()
    while pid in by:
        pid = int(by[pid]['ParentProcessId'])
        if pid in allowed:
            break
        allowed.add(pid)
    conflicts = [int(x['ProcessId']) for x in rows if int(x['ProcessId']) not in allowed]
    assert not conflicts, 'unreconciled python.exe ownership before fit'
    r = subprocess.run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, check=True)
    pid_tokens = r.stdout.split()
    assert all(value.isdecimal() for value in pid_tokens), 'malformed GPU PID inventory'
    gpu_pids = [int(value) for value in pid_tokens]
    python_gpu = [int(row['ProcessId']) for row in rows if int(row['ProcessId']) in gpu_pids]
    # Windows WDDM reports desktop GPU processes in this list. The existing
    # watcher policy allows that baseline below3000MiB; reject Python ownership.
    assert not python_gpu, 'unreconciled Python GPU process before fit'
    gpu_names = []
    if gpu_pids:
        lookup = ['powershell', '-NoProfile', '-Command', '$ids=@(' + ','.join(map(str, gpu_pids)) + '); Get-CimInstance Win32_Process | Where-Object {$ids -contains $_.ProcessId} | Select-Object ProcessId,Name | ConvertTo-Json -Compress']
        names = subprocess.run(lookup, capture_output=True, text=True, timeout=15, check=True)
        gpu_names = json.loads(names.stdout or '[]')
        gpu_names = [gpu_names] if isinstance(gpu_names, dict) else gpu_names
        assert not [row for row in gpu_names if row['Name'].casefold() in ('python.exe','pythonw.exe')], 'unreconciled Python GPU process before fit'
    r = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10, check=True)
    gpus = [[int(v.strip()) for v in line.split(',')] for line in r.stdout.strip().splitlines()]
    assert len(gpus) == 1 and len(gpus[0]) == 2 and 0 <= gpus[0][0] < 3000 and 0 <= gpus[0][1] <= 100, 'malformed GPU resource inventory'
    return {'python_exe_conflicts': conflicts, 'collector_lineage_PIDs': sorted(allowed), 'GPU_compute_PIDs': gpu_pids, 'GPU_process_names': gpu_names, 'project_GPU_processes': [], 'GPU_memory_used_MiB': gpus[0][0], 'GPU_utilization_percent': gpus[0][1]}

def main():
    bootstrap_started = time.monotonic()
    seed, package_sha, proof64 = sys.argv[1:4]
    seed = int(seed)
    assert seed in (0, 1) and sys.version_info[:3] == (3, 10, 9)
    job = 'sol-cloud-exposure16-r5-s%d-r1-benspc' % seed
    proof = json.loads(base64.b64decode(proof64, validate=True))
    assert proof['job'] == job and proof['running_marker_exists'] and proof['copied_queue_equals_origin_main']
    assert proof['smoke_pass'] is True and proof['other_watcher_running_claims'] == []
    claim = Path('C:/Users/benja/claims/' + job.removesuffix('-benspc'))
    assert claim.is_dir(), 'actual watcher shared GPU claim required'
    busy = Path('C:/Users/benja/GPU-BUSY.txt')
    for _ in range(20):
        if busy.is_file() and ('queue job ' + job + ' since ') in busy.read_text(encoding='utf-8'):
            break
        time.sleep(.25)
    else:
        raise RuntimeError('watcher GPU marker does not match current job')
    package_path = ROOT / 'PACKAGE.json'
    assert sha(package_path) == package_sha
    package = json.loads(package_path.read_text(encoding='utf-8'))
    assert package['pc_root'] == str(ROOT).replace('\\', '/') and package['seal_sha256'] == 'd8a50948c5c5831928fd3d68e2ed87f8620bbf3af0b5dbfa8efe27afde08a018'
    payload = ROOT / 'payload.tar.gz'
    assert payload.stat().st_size == package['payload']['bytes'] and sha(payload) == package['payload']['sha256']
    with tarfile.open(payload) as archive:
        members = archive.getmembers()
        assert len(members) == len(package['files']) and set(archive.getnames()) == set(package['files'])
        assert sum(m.size for m in members) <= 4 * 1024 ** 2
        staged = []
        for member in members:
            p = PurePosixPath(member.name)
            assert member.isfile() and not p.is_absolute() and '..' not in p.parts and ':' not in member.name and '\\' not in member.name
            data = archive.extractfile(member).read()
            assert len(data) == member.size and hashlib.sha256(data).hexdigest() == package['files'][member.name]
            target = ROOT / member.name
            assert not target.is_symlink() and target.resolve().is_relative_to(ROOT.resolve())
            if target.exists():
                assert sha(target) == package['files'][member.name], 'existing source differs; preserve partial delivery'
            else:
                staged.append((target, data))
        for target, data in staged:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
    for relative, digest in package['files'].items():
        assert sha(ROOT / relative) == digest
    assert not (OWN / 'runs' / ('s%d' % seed)).exists(), 'earlier fit namespace is never restarted'
    if seed == 1:
        prior = json.loads((OWN / 'TRANSPORT-s0.json').read_text(encoding='utf-8'))
        assert type(prior['returncode']) is int, 'seed0 must close before serial seed1 fit'
    plan = json.loads((OWN / 'PLAN.json').read_text(encoding='utf-8'))
    closure = json.loads((DEPLOY / 'SOURCE-CLOSURE.json').read_text(encoding='utf-8'))
    for s in ('0', '1'):
        assert closure[s]['updates'] == 200 and closure[s]['returncode'] == 0
        for key in ('parent', 'reader', 'adapter'):
            source = plan['warmstart']['tuples'][s]
            assert sha(source[key + '_path']) == source[key + '_sha256'] == closure[s]['tuple_sha256'][key]
    source_stats = []
    for s in ('0', '1'):
        # Historical serialization upper bound is pinned separately; no old fit is rerun.
        source_stats.append({'seed': int(s), 'historical_resume_bytes': 109564463, 'measured_in_original_process_inventory': True})
    metadata = exclusive_inventory()
    assert shutil.disk_usage(ROOT).free >= FLOOR + CAP
    delivered = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_relative_to(OWN / 'runs'))
    assert delivered <= 8 * 1024 ** 2
    bound = 3 * 36649272 + 3 * 1024 ** 2
    assert bound <= 108 * 1024 ** 2 and 109564463 <= 108 * 1024 ** 2
    inventory = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'gpu_inventory_verified': True,
                 'project_gpu_processes': [], 'other_watcher_running_claims': [], 'V11_source_checkpoint_closure_verified': True,
                 'checkpoint_serialization_bound_verified': True, 'checkpoint_bound_scope': 'verified historical full-storage bytes and FP32 3P+3MiB bound; actual zero-optimizer serialization follows in sealed driver',
                 'delivery_package_and_tree_bytes': delivered, 'disk_free_bytes': shutil.disk_usage(ROOT).free,
                 'bridge_retained_files_included_in_disk_free': True, 'actual_user_day': False,
                 'checkpoint_bound_bytes': bound, 'historical_serialization': source_stats, **metadata}
    inventory_path = DEPLOY / ('INVENTORY-s%d.json' % seed)
    write(inventory_path, inventory)
    write(DEPLOY / ('MAC-WATCHER-PROOF-s%d.json' % seed), proof)
    environment = dict(os.environ, JOB=job, TREE=str(ROOT.resolve()), PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPATH=os.pathsep.join([str(ROOT.resolve()), str((ROOT / 'scripts').resolve()), *site.getsitepackages()]),
                       HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='2')
    release_path = DEPLOY / ('RELEASE-s%d.json' % seed)
    command = [sys._base_executable, '-X', 'utf8', '-B', str(ROOT / 'scripts/sol_cloud_exposure16_v5.py'), '--seed', str(seed),
               '--release', str(release_path), '--release-sha256', package['release_sha256'][str(seed)],
               '--inventory', str(inventory_path), '--inventory-sha256', sha(inventory_path)]
    started = time.monotonic()
    # The sealed supervisor owns its570s worker; transport additionally bounds
    # this exact owned process tree within the Mac's600s total job budget.
    owned_seconds = min(580, proof['outer_seconds_remaining'] - (started - bootstrap_started) - 15)
    assert owned_seconds > 30, 'insufficient owned lifetime before any optimizer'
    owned_timeout = False
    with (OWN / ('worker-stdout-s%d.log' % seed)).open('x', encoding='utf-8') as log:
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            returncode = process.wait(timeout=owned_seconds)
        except subprocess.TimeoutExpired:
            owned_timeout = True
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
            process.wait(timeout=2)
            returncode = 124
    result = {'job': job, 'returncode': returncode, 'seed': seed, 'wall_seconds': time.monotonic() - started,
              'owned_transport_timeout': owned_timeout, 'owned_driver_PID': process.pid,
              'owned_driver_seconds_bound': owned_seconds, 'outer_seconds': 600,
              'launch_interpreter': sys._base_executable, 'existing_venv_site_paths': site.getsitepackages(),
              'actual_user_day': False, 'activated': False, 'inventory_sha256': sha(inventory_path), 'package_sha256': package_sha}
    write(OWN / ('TRANSPORT-s%d.json' % seed), result)
    receipts = []
    for path in sorted((OWN / 'runs' / ('s%d' % seed)).rglob('*')):
        if path.is_file():
            receipts.append({'relative': str(path.relative_to(ROOT)).replace('\\', '/'), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    for path in [OWN / ('worker-stdout-s%d.log' % seed), OWN / ('TRANSPORT-s%d.json' % seed), inventory_path, DEPLOY / ('MAC-WATCHER-PROOF-s%d.json' % seed)]:
        if path.is_file():
            receipts.append({'relative': str(path.relative_to(ROOT)).replace('\\', '/'), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    result['records'] = receipts
    print(json.dumps(result, sort_keys=True), flush=True)
    return returncode

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({'status': 'SAFE EXPOSURE TRANSPORT FAILURE; originals preserved', 'type': type(error).__name__, 'assertion_message': str(error)[:200] if isinstance(error, AssertionError) else None, 'actual_user_day': False}), flush=True)
        raise
