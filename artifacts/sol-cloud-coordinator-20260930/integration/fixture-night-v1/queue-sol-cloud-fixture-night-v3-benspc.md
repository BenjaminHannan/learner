BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 25 minutes
LABEL: sol-cloud-fixture-night-v3-benspc

New authorized HUMAN TRAIN fixture capture -> actual2s idle -> immutable batch -> watcher dispatch ->25 core optimizer calls -> durable candidate validation ->explicit rollback. actual_user_day=false,activation_allowed=false. Fixed4 is unqualified learned stopping. Source0 engineering only; no meaningful grammatical chat or gain claim. Existing PC source checkpoints and frozen LM referenced by exact hashes, no mixed corpus/docs or holdout content. Fresh root; no rerun/restart. This packet remains held until independent full wrapper review and PC PID ownership reconciliation; its placement here is a review artifact, not a live queue.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
/usr/bin/python3 -B - <<'SOL_PREFLIGHT'
import hashlib,pathlib,subprocess
pins={'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/MAC-LAUNCH-v3.py': 'e7faf55b74d9e3787862a2c2215fe158231b3a51e60dd49fa441ed91ae853581', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/PC-BOOTSTRAP-v3.py': '26f8f32e58b3d996cf5525cde7754ca7da7de020a0c941cc9be00dfde9c6859b', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/PACKAGE-v3.json': '7f5faf6d9a82ca9c713fca61b5697ab7fe5c76d31743157e65ee8131bd852b0a', 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/payload-v3.tar.gz': 'cdaf8cbc23f4baefaa74a448f7ebefa1ebb09e833cb3076702fe80a7f57fd632'}
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
/usr/bin/python3 -B artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/MAC-LAUNCH-v3.py
```
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/execution-v3
