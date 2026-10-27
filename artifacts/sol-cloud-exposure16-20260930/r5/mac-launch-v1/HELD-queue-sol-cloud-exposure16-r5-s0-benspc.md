BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-exposure16-r5-s0-benspc
PUSH: artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/execution-s0

HELD template only; integrator owns release and live publication. Seed0 first; seed1 only after actual seed0 transport closure, including a preserved failure.
Exact unchanged r5 sealed HUMAN TRAIN diagnostic,800 intended connected updates; no activation or semantic qualification.
Existing shared GPU watcher claim and current copied-main queue required. Native Mac3.9.6, strict benspc SSH/SCP route, PC3.10.9.
600-second total per seed includes source staging,570-second owned PC supervisor and small return. Keep PC originals; no PC archive or weight return.
Prior fixture outerrc1 is retained; inner16-row completionrc0 and successful small-receipt collection required. Actual r5 native smoke must pass.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'EXPOSURE_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=[{'path': 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/MAC-LAUNCH.py', 'sha256': '1dff12fceffc88e8502d705e6422defec990988ca29bcc7ddcc8449c8fd5e8a7'}, {'path': 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/SPEC-s0.json', 'sha256': '2985b23fbe466dd8850107fe17295bff2fcdfadbe30306ecabdaea9e68f90d5a'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1/PACKAGE.json', 'sha256': 'dde4182f33ce36020db0be4bef5a0b5d8de3be1dcb4b41693b47540d0776ad0e'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1/payload.tar.gz', 'sha256': '7bdf9eacb831905dd960f7a7b3a5a8156660dccf597e3290b160cafcb2532afb'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-v1/PC-BOOTSTRAP.py', 'sha256': '8c24d91e418aafca58f5b876dc8be30bbdb402b494093388ff3ea6048de348c5'}]
for record in files:
 path=pathlib.Path(record['path'])
 result=subprocess.run(['git','show','origin/main:'+record['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)))
 assert result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==record['sha256'],'pinned source unavailable; diagnostics suppressed'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'existing source differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B','artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/MAC-LAUNCH.py','--seed','0','--spec','artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/SPEC-s0.json','--spec-sha256','2985b23fbe466dd8850107fe17295bff2fcdfadbe30306ecabdaea9e68f90d5a','--started-monotonic',str(started)])
EXPOSURE_MAC_BOOTSTRAP
```
