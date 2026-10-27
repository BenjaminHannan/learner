#!/usr/bin/env python3
"""Actual Mac watcher attestations and strict existing-auth PC transport."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

W = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q = Path('/Users/ben-hannan/premonition-watch/queue')
JOB = 'sol-cloud-fixture-night-v3-benspc'
DEPLOY = Path('artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1')
PC = 'C:/Users/benja/sol-cloud-fixture-night-v3'
PCPY = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
STRICT = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15']
CURRENT_STAGE = 'Mac preflight'
PC_BOOTSTRAP_DISPATCHED = False
PACKAGE_SHA = '7f5faf6d9a82ca9c713fca61b5697ab7fe5c76d31743157e65ee8131bd852b0a'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
    return digest.hexdigest()

def write(path, value):
    with path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')

def run(command, stage, **kwargs):
    global CURRENT_STAGE
    CURRENT_STAGE = stage
    return subprocess.run(command, check=True, capture_output=True, timeout=60, **kwargs)

def main():
    global CURRENT_STAGE, PC_BOOTSTRAP_DISPATCHED
    assert platform.system() == 'Darwin' and sys.version_info[:3] == (3, 9, 6)
    assert Path.cwd().resolve() == W.resolve()
    assert (Q / (JOB + '.running')).is_file() and not (Q / (JOB + '.exit')).exists()
    output = W / DEPLOY / 'execution-v3'
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'MAC-LAUNCH-START.json', {'job': JOB, 'actual_user_day': False, 'PC_bootstrap_dispatched': False})
    copied = (Q / (JOB + '.md')).read_bytes()
    tracked = run(['git', 'show', 'origin/main:handoff/queue/' + JOB + '.md'], 'verify copied queue against main').stdout
    assert copied == tracked, 'actual copied queue must equal fetched main'
    pattern = r'rungo[45]\.sh ' + re.escape(str(Q / (JOB + '.md')))
    runner, lookup_returncode = [], None
    try:
        lookup = subprocess.run(['pgrep', '-f', pattern], capture_output=True, timeout=15)
        lookup_returncode = lookup.returncode
        if lookup.returncode == 0:
            runner = [pid for pid in lookup.stdout.decode('ascii', errors='ignore').split() if pid.isdigit()]
    except subprocess.TimeoutExpired:
        pass
    CURRENT_STAGE = 'verify source package and prior collection'
    collector_exit = (Q / 'sol-cloud-static-night-raw-collect-v4.exit').read_text().strip()
    assert collector_exit == 'rc=0'
    package_path = W / DEPLOY / 'PACKAGE-v3.json'
    assert sha(package_path) == PACKAGE_SHA
    package = json.loads(package_path.read_text())
    assert sha(W / DEPLOY / 'payload-v3.tar.gz') == package['payload']['sha256']
    assert shutil.disk_usage(W).free >= 512 * 1024 ** 2
    proof = {'job': JOB, 'running_marker_exists': True, 'copied_queue_equals_origin_main': True,
             'actual_runner_pids': [int(pid) for pid in runner], 'runner_lookup_available': bool(runner),
             'runner_lookup_returncode': lookup_returncode, 'collector_v4_exit': collector_exit,
             'queue_sha256': hashlib.sha256(copied).hexdigest(), 'package_sha256': PACKAGE_SHA,
             'publisher_worktree': str(W), 'watcher_queue': str(Q), 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'native_python': sys.executable, 'python_version': sys.version, 'actual_user_day': False}
    write(output / 'MAC-WATCHER-PROOF.json', proof)
    create = '''import os,pathlib,shutil,subprocess,json
r=pathlib.Path('C:/Users/benja/sol-cloud-fixture-night-v3')
assert not pathlib.Path('C:/Users/benja/sol-cloud-fixture-night-v2').exists(),'preserve/reconcile any prior PC deployment before new fixture'
assert not r.exists(),'fresh PC root required; no silent resume'
assert shutil.disk_usage('C:/').free>=1073741824+268435456+8388608,'reserve plus aggregate budget'
cmd=['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"]
z=subprocess.run(cmd,capture_output=True,text=True,timeout=20,check=True)
rows=json.loads(z.stdout or '[]');rows=[rows] if isinstance(rows,dict) else rows
by={int(x['ProcessId']):x for x in rows};allowed={os.getpid()};p=os.getpid()
while p in by:
 p=int(by[p]['ParentProcessId'])
 if p in allowed:break
 allowed.add(p)
assert not [x for x in rows if int(x['ProcessId']) not in allowed],'unreconciled python.exe process; hold new GPU run'
r.mkdir()
print(json.dumps({'fresh_root_created':True,'python_exe_conflicts':0,'free_disk_bytes':shutil.disk_usage(r).free,'actual_user_day':False}))
'''
    result = run(['ssh', '-T', *STRICT, 'benspc', PCPY + ' -X utf8 -'], input=create.encode(), stage='fresh PC root and resource preflight')
    write(output / 'PC-PREFLIGHT.json', json.loads(result.stdout))
    for name in ['payload-v3.tar.gz', 'PACKAGE-v3.json']:
        run(['scp', *STRICT, str(W / DEPLOY / name), 'benspc:' + PC + '/' + name], 'upload sealed ' + name)
    proof_b64 = base64.b64encode(json.dumps(proof, sort_keys=True).encode()).decode()
    bootstrap = (W / DEPLOY / 'PC-BOOTSTRAP-v3.py').read_bytes()
    CURRENT_STAGE = 'dispatch pinned PC bootstrap'
    PC_BOOTSTRAP_DISPATCHED = True
    with (output / 'PC-stdout.log').open('xb') as log:
        completed = subprocess.run(['ssh', '-T', *STRICT, '-o', 'ServerAliveInterval=20', 'benspc',
                                    PCPY + ' -X utf8 - ' + PACKAGE_SHA + ' ' + proof_b64],
                                   input=bootstrap, stdout=log, stderr=subprocess.STDOUT, timeout=1350)
    write(output / 'PC-TRANSPORT-EXIT.json', {'returncode': completed.returncode, 'actual_user_day': False, 'activated': False})
    # Saved failure evidence is also returned. An unavailable return keeps PC evidence intact.
    run(['scp', *STRICT, 'benspc:' + PC + '/RETURN-MANIFEST-v3.json', str(output / 'RETURN-MANIFEST-v3.json')], 'return saved manifest')
    manifest = json.loads((output / 'RETURN-MANIFEST-v3.json').read_text())
    assert manifest['archive']['bytes'] <= 256 * 1024 ** 2
    archive = output / 'fixture-return-v3.tar.gz'
    run(['scp', *STRICT, 'benspc:' + PC + '/fixture-return-v3.tar.gz', str(archive)], 'return saved archive')
    assert archive.stat().st_size == manifest['archive']['bytes'] and sha(archive) == manifest['archive']['sha256']
    parts = []
    with archive.open('rb') as stream:
        for index in range(64):
            block = stream.read(4 * 1024 ** 2)
            if not block:
                break
            path = output / ('fixture-return-v3.tar.gz.part%03d' % index)
            with path.open('xb') as destination:
                destination.write(block)
            parts.append({'path': str(path.relative_to(W)), 'bytes': len(block), 'sha256': sha(path)})
        assert not stream.read(1), '64part aggregate return cap'
    write(output / 'CLOUD-RETURN-PARTS-v3.json', {'parts': parts, 'archive': manifest['archive'], 'original_PC_files_preserved': True})
    print(json.dumps({'returncode': completed.returncode, 'archive': manifest['archive'], 'parts': parts, 'actual_user_day': False, 'activated': False}), flush=True)
    return completed.returncode

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        failure = {'job': JOB, 'stage': CURRENT_STAGE, 'exception_type': type(exc).__name__,
                   'subprocess_returncode': getattr(exc, 'returncode', None),
                   'PC_bootstrap_dispatched': PC_BOOTSTRAP_DISPATCHED, 'actual_user_day': False,
                   'optimizer_updates': 'unknown; inspect saved night ledger' if PC_BOOTSTRAP_DISPATCHED else 0,
                   'raw_diagnostics_suppressed': True}
        destination = W / DEPLOY / 'execution-v3' / 'MAC-FAILURE.json'
        if destination.parent.is_dir() and not destination.exists():
            write(destination, failure)
        raise SystemExit('SAFE TRANSPORT FAILURE: stage=' + CURRENT_STAGE + ', exception=' + type(exc).__name__ + ', rc=' + str(getattr(exc, 'returncode', None)))
