BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-exposure16-r5-s1-r2-benspc
PUSH: artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/execution-s1-r2

HELD successor template; integrator owns live publication. Original failure/namespace retained; PC postmortem proved no driver or optimizer launch. Seed0 first, seed1 after actual closed seed0 disposition.
Unchanged r5 driver/seal/protocol;600 seconds total includes570-second owned supervisor and transport. Fresh PC rootC:/Users/benja/sol-cloud-exposure16-r5-r2. Exact stdout/stderr/exit/stage retained even absent or malformed final manifest; unknown steps after dispatch until original evidence proves otherwise.
Small JSON/log returns only; no PC archive, weight copy, deletion or activation.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'EXPOSURE_R1_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=[{'path': 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/MAC-LAUNCH-v2.py', 'sha256': '450daab0443ad19198f01ecc314fdc448b8d8a8ff80c9e2f9b32cf257a52a82f'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2/SPEC-s1-r2.json', 'sha256': 'bee1de65c7942fc7b50112fda206d9ee5064b02b77287eda7239a1b26b195213'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2/PACKAGE.json', 'sha256': 'a0c69a3de93b41e23991e8a2f002310e93b87cea3de92e9687221cda1d5caeda'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2/payload.tar.gz', 'sha256': '3aaa286b717456dfe30ead1c7d8c1076d9f721e53e64f260bcb9c116d71e302a'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2/PC-BOOTSTRAP.py', 'sha256': 'cf3fa71c8ae9275b40f38e011a8c56a0e444a53232ad39393767dbb5183fcb7c'}]
for record in files:
 path=pathlib.Path(record['path'])
 result=subprocess.run(['git','show','origin/main:'+record['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)))
 assert result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==record['sha256'],'pinned source unavailable; diagnostics suppressed'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'existing source differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3', '-B', 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/MAC-LAUNCH-v2.py', '--seed', '1', '--spec', 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r2/SPEC-s1-r2.json', '--spec-sha256', 'bee1de65c7942fc7b50112fda206d9ee5064b02b77287eda7239a1b26b195213', '--started-monotonic', str(started)])
EXPOSURE_R1_MAC_BOOTSTRAP
```
