BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 2 minutes
LABEL: sol-cloud-storage-inventory-v1
PUSH: artifacts/sol-cloud-storage-inventory-20260930/execution-v1

HELD routine read-only template; sole integrator owns publication. Ben authorized local model catalog/manifests/config metadata plus file sizes/mtime/stat only, and bounded Temp/pip cache/recognizable Downloads installer metadata. No tensor contents, inference, PC writes, cleanup/deletion, personal Documents/photos/Desktop, credentials or security changes.
45-second/50000-entry scan; return catalog upfront, largest10 models and top30 cleanup file/dir candidates; incomplete/denied counts preserved. AllpossibleQwen aliases conservatively protected while exactQwen27B/QwenNextFlash mapping unresolved; activeLFM+reader/core/evidence roots protected. Apparent/exclusive logical sizes are not authorized/reclaimable deletion bytes; active/lastcopy/backup unknown, mtime notlastuse. Binary stdout/stderr and SSHexit preserved; nativeMac3.9.6 and verified directPC3.10.9 only. No independent review gate required.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 90 /usr/bin/python3 -B - <<'READONLY_STORAGE_MAC'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-storage-inventory-v1'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
queue=(Q/(job+'.md')).read_bytes()
tracked=subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=10).stdout
assert tracked==queue,'actual copied queue differs'
source=subprocess.run(['git','show','origin/main:'+'artifacts/sol-cloud-storage-inventory-20260930/PC-INVENTORY-v1.py'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(source).hexdigest()=='80a0e5d4a2332f2c1c9d3e2636208741b35272bbb3b364f9d60dcdb515db5541','pinned read-only source differs'
out=W/'artifacts/sol-cloud-storage-inventory-20260930/execution-v1';out.mkdir(parents=True,exist_ok=False)
started=time.monotonic();record={'schema':'sol.cloud.storage-inventory.mac-transport.v1','source_sha256':'80a0e5d4a2332f2c1c9d3e2636208741b35272bbb3b364f9d60dcdb515db5541','ssh_returncode':None,'timed_out':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_writes':0,'deletions':0}
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe -X utf8 -B -']
try:
 with (out/'PC-STDOUT.jsonl').open('xb') as stdout,(out/'PC-STDERR.log').open('xb') as stderr:
  try:
   completed=subprocess.run(command,input=source,stdout=stdout,stderr=stderr,timeout=70);record['ssh_returncode']=completed.returncode
  except subprocess.TimeoutExpired:record['timed_out']=True
finally:
 record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
 record['streams']=[{'name':name,'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('PC-STDOUT.jsonl','PC-STDERR.log') if (out/name).is_file()]
 with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
raise SystemExit(0 if record['ssh_returncode']==0 else 1)
READONLY_STORAGE_MAC
```
