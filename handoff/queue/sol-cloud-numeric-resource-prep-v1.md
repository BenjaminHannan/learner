BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-numeric-resource-prep-v1
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/numeric-resource-v1/execution-v1

Read-only current disk/PID/GPU baseline for a storage proposal. No PC writes, model, optimizer, source removal, argument/environment output or security changes.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 180 /usr/bin/python3 -B - <<'NUMERIC_RESOURCE_NATIVE'
import hashlib,subprocess
relative='artifacts/sol-cloud-coordinator-20260930/integration/numeric-resource-v1/MAC-RESOURCE.py'
data=subprocess.run(['git','show','origin/main:'+relative],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(data).hexdigest()=='7230c53f75a2288a1dd43dfbff6fb478ffd9deec8d6daab6750ac18c97933b51'
exec(compile(data,relative,'exec'),{'__name__':'__main__','__file__':relative})
NUMERIC_RESOURCE_NATIVE
```
