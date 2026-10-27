#!/usr/bin/env python3
"""Read-only PC receipt/hash recovery; all copies and archives live on Mac."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tarfile

W = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q = Path('/Users/ben-hannan/premonition-watch/queue')
OWN = 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1'
OUT = W / OWN / 'recovered-v3-small'
PC = 'C:/Users/benja/sol-cloud-fixture-night-v3'
PCPY = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
STRICT = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15']
REMOTE = r'''
import datetime,hashlib,json,os,pathlib,shutil,stat,subprocess,sys
root=pathlib.Path('C:/Users/benja/sol-cloud-fixture-night-v3').resolve()
folders=[root/'artifacts/sol-cloud-fixture-20260930',root/'artifacts/sol-cloud-night-20260930']
records=[]
for folder in folders:
 if not folder.exists():continue
 for p in sorted(folder.rglob('*')):
  if not p.is_file():continue
  assert not p.is_symlink() and p.resolve().is_relative_to(root),'owned regular sources only'
  st=p.stat();assert stat.S_ISREG(st.st_mode) and st.st_size<=256*1024**2
  digest=hashlib.sha256()
  with p.open('rb') as stream:
   for block in iter(lambda:stream.read(1024**2),b''):digest.update(block)
  records.append({'relative':p.relative_to(root).as_posix(),'path':str(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest.hexdigest(),'small_receipt':p.suffix.lower() in ('.json','.jsonl','.log','.txt','.sqlite3')})
assert len(records)<=128 and sum(x['bytes'] for x in records)<=320*1024**2
project_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
source_bytes=sum(x['bytes'] for x in records)
z=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"@(Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%.exe'\" | Select-Object ProcessId,ParentProcessId,Name) | ConvertTo-Json -Compress"],capture_output=True,text=True,timeout=20)
processes=json.loads(z.stdout or '[]') if z.returncode==0 else []
processes=[processes] if isinstance(processes,dict) else processes
safe_processes=[{'pid':int(x['ProcessId']),'ppid':int(x['ParentProcessId']),'image':str(x['Name'])} for x in processes]
g=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=20)
gpu=[]
if g.returncode==0:
 for line in g.stdout.splitlines():
  values=[x.strip() for x in line.split(',')]
  if len(values)==2 and all(x.isdigit() for x in values):gpu.append({'memory_used_MiB':int(values[0]),'utilization_percent':int(values[1])})
print(json.dumps({'schema':'sol.cloud.v3-receipt-source-manifest.v1','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':records,'project_bytes':project_bytes,'source_bytes':source_bytes,'rejected_archive_estimate_bytes':project_bytes+source_bytes+1024**2,'old_archive_created':(root/'fixture-return-v3.tar.gz').exists(),'disk_free_bytes':shutil.disk_usage(root).free,'runtime':list(sys.version_info[:3]),'inventory_pid':os.getpid(),'python_processes':safe_processes,'gpus':gpu,'GPU_busy_marker_exists':pathlib.Path('C:/Users/benja/GPU-BUSY.txt').exists(),'read_only':True,'PC_writes':0,'model_calls':0,'optimizer_updates':0,'source_deletions':0}),flush=True)
'''

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            digest.update(block)
    return digest.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')

def manifest():
    result = subprocess.run(['ssh', '-T', *STRICT, 'benspc', PCPY + ' -X utf8 -'], input=REMOTE.encode(), capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError('read-only PC manifest failed; raw diagnostics suppressed')
    value = json.loads(result.stdout)
    assert value['schema'] == 'sol.cloud.v3-receipt-source-manifest.v1' and value['PC_writes'] == value['model_calls'] == value['optimizer_updates'] == 0
    return value

def main():
    assert platform.system() == 'Darwin' and sys.version_info[:3] == (3, 9, 6)
    assert Path.cwd().resolve() == W.resolve()
    assert (Q / 'sol-cloud-fixture-night-v3-benspc.exit').read_text().strip() == 'rc=1'
    assert not (Q / 'sol-cloud-fixture-night-v3-benspc.running').exists()
    assert shutil.disk_usage(W).free >= 1024 ** 3
    OUT.mkdir(parents=True, exist_ok=False)
    before = manifest()
    write(OUT / 'SOURCE-MANIFEST-BEFORE.json', before)
    selected = [record for record in before['records'] if record['small_receipt']]
    assert sum(record['bytes'] for record in selected) <= 32 * 1024 ** 2
    copied = OUT / 'copied'
    for record in selected:
        relative = PurePosixPath(record['relative'])
        assert not relative.is_absolute() and '..' not in relative.parts and re.fullmatch(r'[A-Za-z0-9_./-]+', record['relative'])
        destination = copied.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        assert not destination.exists()
        result = subprocess.run(['scp', *STRICT, 'benspc:' + PC + '/' + record['relative'], str(destination)], capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError('exact receipt copy failed; raw diagnostics suppressed')
        assert destination.stat().st_size == record['bytes'] and sha(destination) == record['sha256']
    after = manifest()
    assert before['records'] == after['records'], 'source bytes/mtime changed; preserve partial copy, no rerun'
    write(OUT / 'SOURCE-MANIFEST-AFTER.json', after)
    archive = OUT / 'small-receipts-v3.tar.gz'
    with tarfile.open(archive, 'x:gz') as stream:
        for path in sorted(copied.rglob('*')):
            if path.is_file():
                stream.add(path, arcname=path.relative_to(copied).as_posix(), recursive=False)
    assert archive.stat().st_size <= 32 * 1024 ** 2
    parts = []
    with archive.open('rb') as stream:
        for index in range(8):
            block = stream.read(4 * 1024 ** 2)
            if not block:
                break
            path = OUT / ('small-receipts-v3.tar.gz.part%03d' % index)
            with path.open('xb') as destination:
                destination.write(block)
            parts.append({'path': str(path.relative_to(W)), 'bytes': len(block), 'sha256': sha(path)})
        assert not stream.read(1)
    result = {'schema': 'sol.cloud.v3-small-receipt-collection.v1', 'source_records': before['records'],
              'copied_receipts': selected, 'archive': {'bytes': archive.stat().st_size, 'sha256': sha(archive)},
              'parts': parts, 'PC_originals_preserved': True, 'PC_archive_created_by_collection': False,
              'prior_PC_archive_created': before['old_archive_created'],
              'rejected_archive_estimate_bytes': before['rejected_archive_estimate_bytes'],
              'actual_user_day': False, 'model_calls': 0, 'optimizer_updates': 0}
    write(OUT / 'COLLECTION-RECEIPT.json', result)
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if OUT.is_dir() and not (OUT / 'FAILURE.json').exists():
            write(OUT / 'FAILURE.json', {'exception_type': type(error).__name__, 'PC_originals_preserved': True, 'new_optimizer_updates': 0})
        raise SystemExit('SAFE RECEIPT COLLECTION FAILURE: ' + type(error).__name__)
