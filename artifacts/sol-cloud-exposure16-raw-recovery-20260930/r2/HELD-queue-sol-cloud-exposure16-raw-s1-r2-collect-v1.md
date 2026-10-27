BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 20 minutes
LABEL: sol-cloud-exposure16-raw-s1-r2-collect-v1
PUSH: artifacts/sol-cloud-exposure16-raw-recovery-20260930/collected-sol-cloud-exposure16-raw-s1-r2-collect-v1

HELD only: no actual manifest is yet available. Integrator must create immutable r2/SPEC-ACTUAL-s1-r2-v1.json from saved actual watcher hashes, replace its SHA below and publish source/spec together before this queue.
Read-only exact binary recovery of fixed r5 TRAIN/DIAGNOSTIC JSONL, INPUT-FRAMES and four diagnostic tensor-frame files. No checkpoint/other files admitted. Saved generated diagnostics NEVER training material.
Before/local/after size+SHA equality; native Mac3.9.6/PC3.10.9; strict existing benspcSSH route. Mac4MiB parts and1GiBfree reserve. Max8MiBraw+16MiBframes; no PCwrite/archive/delete/model/optimizer/inference.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 1200 /usr/bin/python3 -B - <<'EXPOSURE_RAW_COLLECT_BOOTSTRAP'
import hashlib,os,pathlib,re,subprocess
source_pin={'path': 'scripts/sol_cloud_exposure16_raw_collect_v1.py', 'sha256': 'f9bf539f5aba415144e21a9f2c102a7cc7109db1e821364526d2c7a7e7f7051f'}
spec_pin={'path':'artifacts/sol-cloud-exposure16-raw-recovery-20260930/r2/SPEC-ACTUAL-s1-r2-v1.json','sha256':'d255dd35a56d675899027cd538fb0535cd02eb03b219869f85a60bcb7025e9c4'}
assert re.fullmatch('[0-9a-f]{64}',spec_pin['sha256']),'HELD: actual immutable watcher specification is not pinned'
for record in [source_pin,spec_pin]:
 path=pathlib.Path(record['path'])
 result=subprocess.run(['git','show','origin/main:'+record['path']],capture_output=True,timeout=15)
 assert result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==record['sha256'],'pinned source/spec unavailable; diagnostics suppressed'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'existing source/spec differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',source_pin['path'],'--spec',spec_pin['path'],'--spec-sha256',spec_pin['sha256']])
EXPOSURE_RAW_COLLECT_BOOTSTRAP
```
