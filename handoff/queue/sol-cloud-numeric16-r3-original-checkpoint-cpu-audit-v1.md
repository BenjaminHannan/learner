BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 10 minutes
LABEL: sol-cloud-numeric16-r3-original-checkpoint-cpu-audit-v1
PUSH: artifacts/sol-cloud-verifier-20260930/numeric16-checkpoint-audit-r1

One bounded, read-only CPU audit of the four exact final-resume checkpoints after all four r3 arms closed. Stage only the pinned v2 auditor and its pinned saved-reader into their exact PC paths. Confirm fresh C-free, sanitized Python PID/PPID/name and project-root-match metadata, read-only GPU process/utilization metadata, and each checkpoint/CLOSED size, SHA256, and mtime before and after. Run the exact four pinned commands serially, using native PC Python `-X utf8 -B`, `weights_only=True`, CPU map location, no unsafe fallback, no model/optimizer construction, no CUDA, no RNG restore, and no training. Stop later audit commands at the first nonzero rc. Preserve every checkpoint and raw artifact. Output only the four bounded proof JSONs and sanitized manifests/logs; retain any failure without a retry.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'NUMERIC16_CPU_AUDIT_TRANSPORT
import hashlib, os, pathlib, subprocess
source=pathlib.Path('artifacts/sol-cloud-verifier-20260930/run_numeric_checkpoint_audit_transport_v1.py')
expected='5ec11d5e156744b2f0b65426dc609cdd77a4af4bc9275d65e3d5c5fbe3f92ffa'
result=subprocess.run(['git','show','origin/main:'+str(source)],capture_output=True,timeout=15)
if result.returncode or len(result.stdout)>65536 or hashlib.sha256(result.stdout).hexdigest()!=expected:
 raise SystemExit('pinned CPU audit transport unavailable or different')
source.parent.mkdir(parents=True,exist_ok=True)
if source.exists():
 if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise SystemExit('existing transport differs; preserved')
else:
 with source.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',str(source)])
NUMERIC16_CPU_AUDIT_TRANSPORT
```
