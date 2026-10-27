BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 0
TIME CAP: 6 minutes
LABEL: sol-cloud-fixture-v3-small-receipts-collect
PUSH: artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/recovered-v3-small

Routine read-only receipt recovery from the closed v3 PC job. Hash all exact new owned fixture/night files; copy small saved JSON/JSONL/log/SQLite receipts first. No model/optimizer/receipt writer rerun or PC archive creation. PC originals retained; Mac-side compressed transport capped32MiB and4MiB parts. Existing strict benspc auth and verified native Mac3.9.6; actual source PC3.10.9. Raw diagnostics suppressed.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
perl -e 'alarm shift; exec @ARGV' 330 /usr/bin/python3 -B - <<'RECEIPT_BOOTSTRAP'
import hashlib,pathlib,subprocess,os
source=pathlib.Path('artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/RECEIPT-COLLECTOR-v3.py')
expected='6f5d70f4037301ff3e7bb0ed89380558b323db041d64622caeb67f107c3bfe62'
data=subprocess.check_output(['git','show','origin/main:'+str(source)])
assert hashlib.sha256(data).hexdigest()==expected
source.parent.mkdir(parents=True,exist_ok=True)
if source.exists():assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
else:
 with source.open('xb') as f:f.write(data)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',str(source)])
RECEIPT_BOOTSTRAP
```
