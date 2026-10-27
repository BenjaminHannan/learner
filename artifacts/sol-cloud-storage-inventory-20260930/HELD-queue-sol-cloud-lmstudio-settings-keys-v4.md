BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 1 minute
LABEL: sol-cloud-lmstudio-settings-keys-v4
PUSH: artifacts/sol-cloud-storage-inventory-20260930/execution-lmstudio-settings-keys-v4

HELD metadata-only exact3476B C:/Users/benja/.lmstudio/settings.json SHA1e37e73877413d62998d2be2ff56af5d07bedc49ebb8fcacc9472f73b35c44bf. Output nonsecret model/storage keynames/types only; everysettingvalue withheld, credentialsubtrees omitted. No guessedroots/fullconfigdump/CLI/daemon/modelscan/inference/delete/PCwrite. Existing nativeMac3.9.6 andverified directPC3.10.9 strictSSHstdin; preservedstdout/stderr/SSHexit. No broadreviewgate.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 30 /usr/bin/python3 -B - <<'READONLY_STORAGE_MAC'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-lmstudio-settings-keys-v4'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
queue=(Q/(job+'.md')).read_bytes()
tracked=subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=10).stdout
assert tracked==queue,'actual copied queue differs'
source=subprocess.run(['git','show','origin/main:'+'artifacts/sol-cloud-storage-inventory-20260930/PC-LMSTUDIO-KEYS-v4.py'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(source).hexdigest()=='858dc1ec1f582cae7e3de16a5153ed98ec502d9111b5b31a19522cf6620c1b60','pinned read-only source differs'
out=W/'artifacts/sol-cloud-storage-inventory-20260930/execution-lmstudio-settings-keys-v4';out.mkdir(parents=True,exist_ok=False)
started=time.monotonic();record={'schema':'sol.cloud.storage-inventory.mac-transport.v1','source_sha256':'858dc1ec1f582cae7e3de16a5153ed98ec502d9111b5b31a19522cf6620c1b60','ssh_returncode':None,'timed_out':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_writes':0,'deletions':0}
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe -X utf8 -B -']
try:
 with (out/'PC-STDOUT.jsonl').open('xb') as stdout,(out/'PC-STDERR.log').open('xb') as stderr:
  try:
   completed=subprocess.run(command,input=source,stdout=stdout,stderr=stderr,timeout=20);record['ssh_returncode']=completed.returncode
  except subprocess.TimeoutExpired:record['timed_out']=True
finally:
 record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
 record['streams']=[{'name':name,'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('PC-STDOUT.jsonl','PC-STDERR.log') if (out/name).is_file()]
 with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
raise SystemExit(0 if record['ssh_returncode']==0 else 1)
READONLY_STORAGE_MAC
```
