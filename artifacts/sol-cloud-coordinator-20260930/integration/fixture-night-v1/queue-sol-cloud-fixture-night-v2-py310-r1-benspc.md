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
import hashlib,pathlib,subprocess
pins={'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/MAC-LAUNCH-v2-py310-r1.py': 'd680fa01739f76b14b0698c65163863aabe86ed489d747b123f54259e955b35e', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/PC-BOOTSTRAP-v2-py310-r1.py': 'b13338abf668f40c537134c5d6e6cac34fe073b3ebaa9827b0852bcb706f26e3', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/PACKAGE-v2.json': '6d46498648c78d1d3382cb17bd8f90edfafc7ca81ca80be35a4c0773a0b09960', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/payload-v2.tar.gz': '31403dd127ff0bd340ba99e2eed2569a6d2b5692a96a3e1d5b7a986ce761a915'}
for relative,expected in pins.items():
 data=subprocess.check_output(['git','show','origin/main:'+relative])
 assert hashlib.sha256(data).hexdigest()==expected,'sealed origin/main bytes changed'
 path=pathlib.Path(relative)
 if path.exists():
  assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'preserve differing prior file'
 else:
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as stream:stream.write(data)
SOL_PREFLIGHT
/usr/bin/python3 -B artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/MAC-LAUNCH-v2-py310-r1.py
```
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/execution-v2
