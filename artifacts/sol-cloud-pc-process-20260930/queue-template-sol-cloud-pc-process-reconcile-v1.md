BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-pc-process-reconcile-v1
PUSH: artifacts/sol-cloud-pc-process-20260930/collected-v1

Read-only Python PID/PPID/start/image and whitelisted ownership metadata, GPU compute-app metadata and free disk.
Requires prior collection exit0 and no collection running marker. No PC writes or process stops.
Full arguments, unknown paths and raw diagnostics are suppressed. Native /usr/bin/python3 3.9.6; existing strict benspc SSH route.
Template only; designated integrator owns live queue publication.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 120 /usr/bin/python3 -B artifacts/sol-cloud-pc-process-20260930/COLLECTOR.py --source-sha256 60d8ff63f55884a245e319ca93d27e975a9a8bb44c2f09c8964c8083aeb9b483
```
