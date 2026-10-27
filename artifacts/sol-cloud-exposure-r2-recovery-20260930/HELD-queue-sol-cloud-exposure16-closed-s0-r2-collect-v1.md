BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 20 minutes
LABEL: sol-cloud-exposure16-closed-s0-r2-collect-v1
PUSH: artifacts/sol-cloud-exposure-r2-recovery-20260930/collected-sol-cloud-exposure16-closed-s0-r2-collect-v1

HELD template outside handoff. The sole integrator publishes this routine authorized read-only transport; no extra model/review gate is introduced.
Exactly three manifest-pinned CLOSED r2 files: final connected-resume.pt and both initial PARITY JSONs. PC originals retained. No PC archive/write/delete/model/optimizer/inference. Native Mac3.9.6 and proven PC3.10.9 stdlib SSH route unchanged. Before/local/after SHA equality, 4MiB parts, 1GiB Mac reserve, <=128MiB per seed and <=256MiB for both seeds. Saved generated diagnostic text is never training material.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 1200 /usr/bin/python3 -B - <<'CLOSED_R2_COLLECT_BOOTSTRAP'
import hashlib,os,pathlib,re,subprocess
source_pin={'path': 'artifacts/sol-cloud-exposure-r2-recovery-20260930/collect_closed_r2_v1.py', 'sha256': 'f3dfc14209efdadca729104e55f03e15a2409e95fc093148ff844880bb7df030'}
spec_pin={'path': 'artifacts/sol-cloud-exposure-r2-recovery-20260930/SPEC-s0-r2-v1.json', 'sha256': '24d8eeef77392757530aa5bc4a7d0adede9c25eec99be9ed5059b224d626f04b'}
assert re.fullmatch('[0-9a-f]{64}',spec_pin['sha256'])
for record in [source_pin,spec_pin]:
 path=pathlib.Path(record['path'])
 result=subprocess.run(['git','show','origin/main:'+record['path']],capture_output=True,timeout=15)
 assert result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==record['sha256'],'pinned source/spec unavailable; diagnostics suppressed'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'existing source/spec differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',source_pin['path'],'--spec',spec_pin['path'],'--spec-sha256',spec_pin['sha256']])
CLOSED_R2_COLLECT_BOOTSTRAP
```
