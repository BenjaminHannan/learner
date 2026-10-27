BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 25 minutes
LABEL: sol-cloud-fixture-night-v2-benspc

New authorized HUMAN TRAIN fixture capture -> actual2s idle -> immutable batch -> watcher dispatch ->25 core optimizer calls -> durable candidate validation ->explicit rollback. actual_user_day=false,activation_allowed=false. Fixed4 is unqualified learned stopping. Source0 engineering only; no meaningful grammatical chat or gain claim. Existing PC source checkpoints and frozen LM referenced by exact hashes, no mixed corpus/docs or holdout content. Fresh root; no rerun/restart. This packet remains held until independent full wrapper review and PC PID ownership reconciliation; its placement here is a review artifact, not a live queue.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
/usr/bin/python3 -B - <<'SOL_PREFLIGHT'
import hashlib,pathlib
base=pathlib.Path('artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1')
for name,expected in {'MAC-LAUNCH-v2.py': '59dc110f46cb2d4af9ac0fa221d3d5ba6202f64e27a332f14df6b7d886962ef7', 'PC-BOOTSTRAP-v2.py': 'f9a8a9e1d759420042f0d81533a80f768a9fdced001cdeb25f4bc58a0284e6b3'}.items():
 assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected,'sealed bootstrap source changed'
SOL_PREFLIGHT
/usr/bin/python3 -B artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/MAC-LAUNCH-v2.py
```
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/execution-v2
