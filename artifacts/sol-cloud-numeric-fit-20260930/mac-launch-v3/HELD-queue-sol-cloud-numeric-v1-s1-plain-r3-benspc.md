BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-numeric-v1-s1-plain-r3-benspc
PUSH: artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v3/execution-r3-s1-plain

HELD serial template; sole integrator owns actual main/queue publication. Fixed order s0-loop, s0-plain, s1-loop, s1-plain; only first job live initially. Previous physical watcher exits and exact PC transport dispositions must already be closed. No retries or altered sealed model/objective/scoring. Complete canonical numeric target plus EOS is scored without number extraction.
NativeMac3.9.6 /usr/bin/python3 and verifiedPC3.10.9; actual copied-main running claim/shared GPUclaim required. Same600second deadline covers source staging, bounded driver and small return. No archive extraction, weight copies or deletion. Exact PCstdout/stderr/SSHrc preserved even absent manifest; optional PID metadata cannot abort. Large states/raw evidence stay onPC if outside bounded small return.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'NUMERIC_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=[{'path': 'artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v3/MAC-LAUNCH-v3.py', 'sha256': 'd174dab39b94741e9c680a51a3595ada75a29a7188e4ef3a738d24f87ba55daa'}, {'path': 'artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v3/SPEC-s1-plain.json', 'sha256': 'f5e313186ed9f3fca97628894a2ee8aa1ef20faa7fabc0eb0d1b76763df3d52a'}]
for pin in files:
 result=subprocess.run(['git','show','origin/main:'+pin['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)),check=True)
 assert hashlib.sha256(result.stdout).hexdigest()==pin['sha256'],'sealed source unavailable/different'
 path=pathlib.Path(pin['path']);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256'],'existingsource differs; preserve it'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B','artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v3/MAC-LAUNCH-v3.py','--seed','1','--arm','plain','--spec','artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v3/SPEC-s1-plain.json','--spec-sha256','f5e313186ed9f3fca97628894a2ee8aa1ef20faa7fabc0eb0d1b76763df3d52a','--started-monotonic',str(started)])
NUMERIC_MAC_BOOTSTRAP
```
