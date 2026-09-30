BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 5 minutes
LABEL: sol-cloud-capability256-r2-preflight-probe-v1
PUSH: artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/progress/execution-sol-cloud-capability256-r2-preflight-probe-v1

Run the pinned read-only CPU preflight probe for the already failed r2 arm. Verify the source through `git show origin/main` and its exact SHA before sending it by SSH stdin. The probe replays package/checkpoint hashes, frozen helper checks, native Python import/help, and bounded process/GPU/disk inventory; it stops before inventory writes and before runner invocation. Capture complete stdout/stderr (each capped at 2 MiB). No PC staging writes, training retries, model construction, optimizer calls, or evidence deletion.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 300 /usr/bin/python3 -B - <<'CAP256_PREFLIGHT_PROBE'
import datetime,hashlib,json,pathlib,platform,subprocess,sys,time
W=pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27');Q=pathlib.Path('/Users/ben-hannan/premonition-watch/queue');job='sol-cloud-capability256-r2-preflight-probe-v1';queue=Q/(job+'.md');src='scripts/sol_cloud_capability256_preflight_probe_v1.py';expected='f363fc5c2159890e88a3e4c86d202c0750eacf9a53839cbba9457284728d91de';size=22480
assert platform.system()=='Darwin' and sys.version_info[:3]==(3,9,6) and pathlib.Path.cwd().resolve()==W.resolve()
assert queue.is_file() and (Q/(job+'.running')).is_file() and not (Q/(job+'.exit')).exists()
tracked=subprocess.run(['git','show','origin/main:'+src],capture_output=True,check=True,timeout=10).stdout
assert len(tracked)==size and hashlib.sha256(tracked).hexdigest()==expected
out=W/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/progress/execution-'+job;out.mkdir(parents=True,exist_ok=False);started=time.monotonic()
command=['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','benspc','C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -B -']
try:p=subprocess.run(command,input=tracked,capture_output=True,timeout=240);rc=p.returncode;stdout=p.stdout;stderr=p.stderr;timed=False
except subprocess.TimeoutExpired as e:rc=None;stdout=e.stdout or b'';stderr=e.stderr or b'';timed=True
assert len(stdout)<=2*1024*1024 and len(stderr)<=2*1024*1024
for name,data in (('PC-STDOUT.log',stdout),('PC-STDERR.log',stderr)):
 with (out/name).open('xb') as f:f.write(data)
record={'schema':'sol.cloud.capability256.readonly-probe-transport.v1','job':job,'probe_path':src,'probe_sha256':expected,'probe_bytes':len(tracked),'PC_returncode':rc,'timed_out':timed,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-started,'stdout_bytes':len(stdout),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_bytes':len(stderr),'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'PC_file_writes':0,'model_calls':0,'optimizer_calls':0}
with (out/'TRANSPORT.json').open('x') as f:f.write(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps(record,sort_keys=True),flush=True)
CAP256_PREFLIGHT_PROBE
```
