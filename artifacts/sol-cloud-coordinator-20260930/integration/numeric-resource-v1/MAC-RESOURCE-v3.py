#!/usr/bin/env python3
"""One bounded read-only PC inventory for preparing numeric experiment storage."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

W=Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=Path('/Users/ben-hannan/premonition-watch/queue')
JOB='sol-cloud-numeric-resource-prep-v3'
OWN='artifacts/sol-cloud-coordinator-20260930/integration/numeric-resource-v1'
PCPY=r'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
STRICT=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2']

PC_SOURCE=r'''import datetime,json,os,pathlib,shutil,subprocess,sys,time
started=time.monotonic()
def query(argv):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=15)
        if p.returncode: return {'available':False,'returncode':p.returncode}
        return {'available':True,'stdout':p.stdout}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'available':False,'error_type':type(e).__name__}
assert sys.version_info[:3]==(3,10,9)
process=query(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('python.exe','pythonw.exe')} | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"])
if process['available']:
    rows=json.loads(process.pop('stdout') or '[]');process['rows']=[rows] if isinstance(rows,dict) else rows
gpu=query(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'])
if gpu['available']:
    gpu['memory_used_MiB_utilization_percent']=[[int(x.strip()) for x in line.split(',')] for line in gpu.pop('stdout').strip().splitlines()]
apps=query(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'])
if apps['available']:
    tokens=apps.pop('stdout').split();assert all(x.isdecimal() for x in tokens);apps['PIDs']=[int(x) for x in tokens]
    if tokens:
        names=query(['powershell','-NoProfile','-Command','$ids=@('+','.join(tokens)+'); Get-CimInstance Win32_Process | Where-Object {$ids -contains $_.ProcessId} | Select-Object ProcessId,Name | ConvertTo-Json -Compress'])
        if names['available']:
            rows=json.loads(names.pop('stdout') or '[]');names['rows']=[rows] if isinstance(rows,dict) else rows
        apps['optional_process_names']=names
claims=pathlib.Path('C:/Users/benja/claims')
report={'schema':'sol.cloud.numeric-resource-preparation.v1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':sys.version,'executable':sys.executable,'base_executable':sys._base_executable,'probe_PID':os.getpid(),'probe_PPID':os.getppid(),'C_free_bytes':shutil.disk_usage('C:/').free,'known_project_claim_directory_names':sorted(p.name for p in claims.iterdir() if p.is_dir()) if claims.is_dir() else [],'python_processes':process,'GPU':gpu,'GPU_compute_apps':apps,'model_calls':0,'optimizer_updates':0,'GPU_model_calls':0,'PC_writes':0,'source_deletions':0,'report_training_eligible':False,'wall_seconds':time.monotonic()-started}
print(json.dumps(report,sort_keys=True))
'''

def main():
    started=time.monotonic()
    assert Path.cwd().resolve()==W.resolve() and platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6)
    assert (Q/(JOB+'.running')).is_file() and not (Q/(JOB+'.exit')).exists()
    copied=(Q/(JOB+'.md')).read_bytes()
    actual=subprocess.run(['git','show','origin/main:handoff/queue/'+JOB+'.md'],capture_output=True,timeout=10,check=True).stdout
    assert copied==actual
    out=W/OWN/'execution-v3';out.mkdir(parents=True)
    rc=None;stdout=b'';stderr=b'';error=None
    try:
        p=subprocess.run(['ssh','-T',*STRICT,'benspc',PCPY+' -X utf8 -B -'],input=PC_SOURCE.encode(),capture_output=True,timeout=100)
        rc=p.returncode;stdout=p.stdout;stderr=p.stderr
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout or b'';stderr=e.stderr or b'';error=type(e).__name__
    except OSError as e:error=type(e).__name__
    assert len(stdout)+len(stderr)<512*1024
    for name,data in [('PC-STDOUT.json',stdout),('PC-STDERR.log',stderr)]:
        with (out/name).open('xb') as f:f.write(data)
    report={'schema':'sol.cloud.numeric-resource-transport.v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ssh_returncode':rc,'error_type':error,'pc_stdout_sha256':hashlib.sha256(stdout).hexdigest(),'pc_stderr_sha256':hashlib.sha256(stderr).hexdigest(),'model_calls':0,'optimizer_updates':0,'PC_writes':0,'source_deletions':0,'wall_seconds':time.monotonic()-started}
    with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,sort_keys=True))
    return 0 if rc==0 else 1

if __name__=='__main__':raise SystemExit(main())
