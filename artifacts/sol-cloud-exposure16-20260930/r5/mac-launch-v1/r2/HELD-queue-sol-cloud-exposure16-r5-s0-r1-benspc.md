BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-exposure16-r5-s0-r1-benspc
PUSH: artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/execution-s0-r1

HELD successor template; integrator owns live publication. Original failure/namespace retained; PC postmortem proved no driver or optimizer launch. Seed0 first, seed1 after actual closed seed0 disposition.
Unchanged r5 driver/seal/protocol;600 seconds total includes570-second owned supervisor and transport. Fresh PC rootC:/Users/benja/sol-cloud-exposure16-r5-r1. Exact stdout/stderr/exit/stage retained even absent or malformed final manifest; unknown steps after dispatch until original evidence proves otherwise.
Small JSON/log returns only; no PC archive, weight copy, deletion or activation.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'EXPOSURE_R1_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=[{'path': 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/MAC-LAUNCH-v2.py', 'sha256': '450daab0443ad19198f01ecc314fdc448b8d8a8ff80c9e2f9b32cf257a52a82f'}, {'path': 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/SPEC-s0-r1.json', 'sha256': 'e128b8b97d35eeca8218bae7b29641a97925d2ccefeb1f22424f6db17c08f282'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r1/PACKAGE.json', 'sha256': '0b07199bb6c27ff76eb0ae4286571999556996bd0eb707aba21cd1f17c673c67'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r1/payload.tar.gz', 'sha256': '13d074dbb07712c1b07b27e941f18c7e5d737a39c4aecd5b5eb59fcac4672b95'}, {'path': 'artifacts/sol-cloud-coordinator-20260930/integration/exposure16-r5-r1/PC-BOOTSTRAP.py', 'sha256': '60baca3b9007adc4aa6a69688ff19315faaa20447ea2eac4e6754331951b6553'}]
for record in files:
 path=pathlib.Path(record['path'])
 result=subprocess.run(['git','show','origin/main:'+record['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)))
 assert result.returncode==0 and hashlib.sha256(result.stdout).hexdigest()==record['sha256'],'pinned source unavailable; diagnostics suppressed'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],'existing source differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3', '-B', 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/MAC-LAUNCH-v2.py', '--seed', '0', '--spec', 'artifacts/sol-cloud-exposure16-20260930/r5/mac-launch-v1/r2/SPEC-s0-r1.json', '--spec-sha256', 'e128b8b97d35eeca8218bae7b29641a97925d2ccefeb1f22424f6db17c08f282', '--started-monotonic', str(started)])
EXPOSURE_R1_MAC_BOOTSTRAP
```
