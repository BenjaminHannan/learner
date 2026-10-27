BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 1 minute
LABEL: sol-cloud-approved-qwen-remove-v1
PUSH: artifacts/sol-cloud-qwen-removal-20260930/execution-v1

Explicit Ben-approved ONLY fixed Qwen GGUF removal after original exact Python-integer identity and native exclusive-share-zero DELETE/attributes handle checks. Same handle performs native disposition; refuse changed/open/mapped/active model process. No tensor read or full hash, pip cache or other models/evidence removal, daemon start or process stop. Originalv5metadata preserved. No automatic retry on ambiguous removal.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 60 /usr/bin/python3 -B - <<'READONLY_STORAGE_MAC'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-approved-qwen-remove-v1'
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
queue=(Q/(job+'.md')).read_bytes()
tracked=subprocess.run(['git','show','origin/main:handoff/queue/'+job+'.md'],capture_output=True,check=True,timeout=10).stdout
assert tracked==queue,'actual copied queue differs'
source=subprocess.run(['git','show','origin/main:'+'artifacts/sol-cloud-qwen-removal-20260930/PC-REMOVE-v1.py'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(source).hexdigest()=='ae926d8d3f49e7b167c0b708c201e54f6fff0ca53346d9cc7e3b1e9347fb800f','pinned read-only source differs'
out=W/'artifacts/sol-cloud-qwen-removal-20260930/execution-v1';out.mkdir(parents=True,exist_ok=False)
started=time.monotonic();record={'schema':'sol.cloud.storage-inventory.mac-transport.v1','source_sha256':'ae926d8d3f49e7b167c0b708c201e54f6fff0ca53346d9cc7e3b1e9347fb800f','ssh_returncode':None,'timed_out':False,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'PC_writes':0,'deletions':0}
expected_bytes=subprocess.run(['git','show','origin/main:artifacts/sol-cloud-qwen-removal-20260930/EXPECTED.json'],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(expected_bytes).hexdigest()=='bcf61ffad888083356210636b7192f7fe7f996d9d0066fea81521b3491488bfe'
expected=json.loads(expected_bytes)
program=source+b'\nexpected=json.loads('+repr(json.dumps(expected)).encode()+b')\nraise SystemExit(run(expected))\n'
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe -X utf8 -B -']
try:
 with (out/'PC-STDOUT.jsonl').open('xb') as stdout,(out/'PC-STDERR.log').open('xb') as stderr:
  try:
   completed=subprocess.run(command,input=program,stdout=stdout,stderr=stderr,timeout=35);record['ssh_returncode']=completed.returncode
  except subprocess.TimeoutExpired:record['timed_out']=True
finally:
 record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-started)
 record['streams']=[{'name':name,'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('PC-STDOUT.jsonl','PC-STDERR.log') if (out/name).is_file()]
 with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
raise SystemExit(0 if record['ssh_returncode']==0 else 1)
READONLY_STORAGE_MAC
```
