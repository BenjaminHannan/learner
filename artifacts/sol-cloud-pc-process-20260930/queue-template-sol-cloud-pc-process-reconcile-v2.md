BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-pc-process-reconcile-v2
PUSH: artifacts/sol-cloud-pc-process-20260930/collected-v2

Read-only process ownership/GPU/free-disk metadata and bytes+mtime for two exact V12 connected-resume checkpoints.
Requires successful collection watcher receipt rc=0 and no collection running marker. No PC writes or process stops.
Full arguments, unknown paths and raw diagnostics are suppressed. Native /usr/bin/python3 3.9.6; existing strict benspc SSH route.
Additive successor to preserved v1. Integrator publishes exactly this successor, never both process jobs.
Pinned source is materialized from fetched origin/main because the Mac watcher does not check out new source files.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 120 /usr/bin/python3 -B - <<'PROCESS_COLLECTOR_BOOTSTRAP'
import hashlib, os, pathlib, subprocess
source = pathlib.Path('artifacts/sol-cloud-pc-process-20260930/COLLECTOR-v2.py')
expected = '8c6bbe2924de5d1145c321d53caa8728fc5869535871814b68eb1085839143e2'
result = subprocess.run(['git', 'show', 'origin/main:' + str(source)], capture_output=True, timeout=15)
if result.returncode or len(result.stdout) > 65536 or hashlib.sha256(result.stdout).hexdigest() != expected:
    raise SystemExit('pinned collector source unavailable; diagnostics suppressed')
source.parent.mkdir(parents=True, exist_ok=True)
if source.exists():
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise SystemExit('existing collector differs; preserved without overwrite')
else:
    with source.open('xb') as stream:
        stream.write(result.stdout)
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-B', str(source), '--source-sha256', expected])
PROCESS_COLLECTOR_BOOTSTRAP
```
