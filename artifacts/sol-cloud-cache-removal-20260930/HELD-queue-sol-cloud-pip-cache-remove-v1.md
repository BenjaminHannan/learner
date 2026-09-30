BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 2 minutes
LABEL: sol-cloud-pip-cache-remove-v1
PUSH: artifacts/sol-cloud-cache-removal-20260930/execution-v1

HELD. DO NOT copy to handoff/queue before explicit Ben approval reaches the parent. Approval placeholder refuses before dispatch. One fixed 2,753,152,602-byte pip HTTP cache .body only; no companion metadata, installed package, model, checkpoint, evidence or swap removal. Fresh stable exact Python-integer identity and package/process checks are repeated immediately before one unlink. Changed/active/failed checks refuse. Before-action stdout and after-action free-space/absence receipt preserved. No model or optimizer. No automatic retry after ambiguous action status.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 80 /usr/bin/python3 -B - <<'HELD_CACHE_REMOVE_MAC'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27');Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-pip-cache-remove-v1'
APPROVAL_SHA256='PENDING-BEN-APPROVAL'
assert len(APPROVAL_SHA256)==64 and all(c in '0123456789abcdef' for c in APPROVAL_SHA256),'Explicit Ben approval has not been supplied; no dispatch'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
assert (Q/(job+'.md')).read_bytes()==subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=10).stdout
pins=[{'path': 'artifacts/sol-cloud-cache-removal-20260930/PC-REMOVE-v1.py', 'sha256': 'bc894f5abe17fd8df8b12ebb4957570c3b8834634030aa5a423b45c08612198f'}, {'path': 'artifacts/sol-cloud-cache-removal-20260930/EXPECTED-IDENTITY.json', 'sha256': 'b5bf1e34e7e635a7476a6e334c3f42184b4fa3de7f7bc9d7d2d7d960d51a71e7'}, {'path': 'artifacts/sol-cloud-storage-inventory-20260930/PC-CACHE-SAFETY-v1.py', 'sha256': '6940b080a62d7816809fc84585536ec37c394b28ddb35f188c4dafac83ada132'}]
files={}
for pin in pins:
 b=subprocess.run(['git','show','origin/main:'+pin['path']],capture_output=True,check=True,timeout=10).stdout
 assert hashlib.sha256(b).hexdigest()==pin['sha256'],'exact source/identity pin differs'
 files[pin['path']]=b
approval_bytes=subprocess.run(['git','show','origin/main:artifacts/sol-cloud-cache-removal-20260930/APPROVAL.json'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(approval_bytes).hexdigest()==APPROVAL_SHA256,'exact explicit Ben approval receipt differs'
packet={'remover_source':files[pins[0]['path']].decode(),'expected':json.loads(files[pins[1]['path']]),'safety_source':files[pins[2]['path']].decode(),'approval':json.loads(approval_bytes)}
program='import json\npacket=json.loads('+repr(json.dumps(packet))+')\nnamespace={"__name__":"approved_cache_action"}\nexec(packet["remover_source"],namespace)\nraise SystemExit(namespace["perform"](packet["approval"],packet["safety_source"],packet["expected"]))\n'
compile(program,'<approved-cache-action>','exec')
out=W/'artifacts/sol-cloud-cache-removal-20260930/execution-v1';out.mkdir(parents=True,exist_ok=False)
started=time.monotonic();record={'schema':'sol.cloud.single-cache-removal.mac-transport.v1','approval_sha256':APPROVAL_SHA256,'source_pins':pins,'ssh_returncode':None,'timed_out':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'deletion_status':'not-dispatched'}
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe -X utf8 -B -']
try:
 with (out/'PC-STDOUT.jsonl').open('xb') as stdout,(out/'PC-STDERR.log').open('xb') as stderr:
  record['deletion_status']='unknown-after-dispatch'
  try:
   completed=subprocess.run(command,input=program.encode(),stdout=stdout,stderr=stderr,timeout=50);record['ssh_returncode']=completed.returncode
  except subprocess.TimeoutExpired:record['timed_out']=True
finally:
 record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
 record['streams']=[{'name':name,'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('PC-STDOUT.jsonl','PC-STDERR.log') if (out/name).is_file()]
 with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
raise SystemExit(0 if record['ssh_returncode']==0 else 1)
HELD_CACHE_REMOVE_MAC
```
