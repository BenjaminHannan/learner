BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-numeric-v1-s0-plain-benspc
PUSH: artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v1/execution-s0-plain

HELD serial template; sole integrator owns actual main/queue publication. Fixed order s0-loop, s0-plain, s1-loop, s1-plain; only first job live initially. Previous physical watcher exits and exact PC transport dispositions must already be closed. No retries or altered sealed model/objective/scoring. Complete canonical numeric target plus EOS is scored without number extraction.
NativeMac3.9.6 /usr/bin/python3 and verifiedPC3.10.9; actual copied-main running claim/shared GPUclaim required. Same600second deadline covers source staging, bounded driver and small return. No archive extraction, weight copies or deletion. Exact PCstdout/stderr/SSHrc preserved even absent manifest; optional PID metadata cannot abort. Large states/raw evidence stay onPC if outside bounded small return.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'NUMERIC_MAC_BOOTSTRAP'
import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=[{'path': 'artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v1/MAC-LAUNCH-v1.py', 'sha256': '83f6257513ab4b9e0a085ea5cd031e705ea5520c115cb079a88fc9c95eedbb07'}, {'path': 'artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v1/SPEC-s0-plain.json', 'sha256': 'd29141136502d4ccd3bfd40180475cf33e8f02fcff92cd50d2aa85d37ec9267c'}]
for pin in files:
 result=subprocess.run(['git','show','origin/main:'+pin['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)),check=True)
 assert hashlib.sha256(result.stdout).hexdigest()==pin['sha256'],'sealed source unavailable/different'
 path=pathlib.Path(pin['path']);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256'],'existingsource differs; preserve it'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B','artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v1/MAC-LAUNCH-v1.py','--seed','0','--arm','plain','--spec','artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v1/SPEC-s0-plain.json','--spec-sha256','d29141136502d4ccd3bfd40180475cf33e8f02fcff92cd50d2aa85d37ec9267c','--started-monotonic',str(started)])
NUMERIC_MAC_BOOTSTRAP
```
