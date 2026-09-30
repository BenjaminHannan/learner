BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 2 minutes
LABEL: sol-cloud-lmstudio-downloadsfolder-models-v5
PUSH: artifacts/sol-cloud-storage-inventory-20260930/execution-lmstudio-downloadsfolder-models-v5

HELD standalone newactualsettings schema followup: pinned3476B C:/Users/benja/.lmstudio/settings.json SHA1e37e73877413d62998d2be2ff56af5d07bedc49ebb8fcacc9472f73b35c44bf; outputONLYdownloadsFolder actualkeyvalue. Thenstat model files GGUF/safetensors plusknownlocalmodelmanifestJSON onlywhenobservedGGUF/safetensorssiblings only insideexactconfiguredfolder,25sec10000entries/depth5; no genericotherroot/personal/docs/Temp/cache scan, tensors/GGUFheaders/CLI/daemon/GPU/inference/delete. AllQwen/LFMprotected andprojectevidencepaths excluded. Stat uses actual os.stat forlink/fileIDmetadata; allocated/reclaimable/lastuse unknownunlessavailable; quantfilename notheaderproof. Freshresourcev4alreadyseparatelyqueued—no duplicate/combine. NativeMac3.9.6/directPC3.10.9 strictSSHstdin, savedstdout/stderr/SSHexit; no broaderreviewgate.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 60 /usr/bin/python3 -B - <<'READONLY_STORAGE_MAC'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-lmstudio-downloadsfolder-models-v5'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
queue=(Q/(job+'.md')).read_bytes()
tracked=subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=10).stdout
assert tracked==queue,'actual copied queue differs'
source=subprocess.run(['git','show','origin/main:'+'artifacts/sol-cloud-storage-inventory-20260930/PC-LMSTUDIO-DOWNLOADSFOLDER-v5.py'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(source).hexdigest()=='2a6e7da244c33f6fb28f94af488f820f13179a8ddae224a2c639c8d2d1895ee4','pinned read-only source differs'
out=W/'artifacts/sol-cloud-storage-inventory-20260930/execution-lmstudio-downloadsfolder-models-v5';out.mkdir(parents=True,exist_ok=False)
started=time.monotonic();record={'schema':'sol.cloud.storage-inventory.mac-transport.v1','source_sha256':'2a6e7da244c33f6fb28f94af488f820f13179a8ddae224a2c639c8d2d1895ee4','ssh_returncode':None,'timed_out':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_writes':0,'deletions':0}
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe -X utf8 -B -']
try:
 with (out/'PC-STDOUT.jsonl').open('xb') as stdout,(out/'PC-STDERR.log').open('xb') as stderr:
  try:
   completed=subprocess.run(command,input=source,stdout=stdout,stderr=stderr,timeout=45);record['ssh_returncode']=completed.returncode
  except subprocess.TimeoutExpired:record['timed_out']=True
finally:
 record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
 record['streams']=[{'name':name,'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('PC-STDOUT.jsonl','PC-STDERR.log') if (out/name).is_file()]
 with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
raise SystemExit(0 if record['ssh_returncode']==0 else 1)
READONLY_STORAGE_MAC
```
