BASH-ONLY: yes
GPU: no
DISK: 0
TIME CAP: 3 minutes
LABEL: sol-cloud-numeric-resource-prep-v4
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/numeric-resource-v1/execution-v4

Read-only current disk/PID/GPU baseline for a storage proposal. No PC writes, model, optimizer, source removal, argument/environment output or security changes.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 180 /usr/bin/python3 -B - <<'NUMERIC_RESOURCE_NATIVE'
import hashlib,subprocess
relative='artifacts/sol-cloud-coordinator-20260930/integration/numeric-resource-v1/MAC-RESOURCE-v4.py'
data=subprocess.run(['git','show','origin/main:'+relative],capture_output=True,check=True,timeout=10).stdout
assert hashlib.sha256(data).hexdigest()=='48a65be50d3c5b1a17f05a2c011d18591064d7ad59f6d262a039fc7320600390'
exec(compile(data,relative,'exec'),{'__name__':'__main__','__file__':relative})
NUMERIC_RESOURCE_NATIVE
```
