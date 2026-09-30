BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 66 minutes
LABEL: sol-translator-human-v4-s0-pc

READY transport; TRAIN only, no DEV evaluation. Original200-minute queue WITHDRAWN.
Own DEPLOYMENT-V4-SEAL, PLAN, ADDENDUM pin code/data/marks; cached LFM reused.
Two seed jobs serialized; this is seed 0. Overall3950 seconds (<4000),
TRAIN3000 seconds/500updates/batch2/4rounds/zero sleep. Disk floor2GiB;
512MiB output cap; no install/download/rental. Partial checkpoints not proof.
James sole integrator publishes; watcher owns GPU claim. No duplicate launch.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 3950 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-human-v4
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY'
from pathlib import Path
import shutil
p=Path('C:/Users/benja/sol-translator-human-v4')
assert shutil.disk_usage('C:/').free >= 2*1024**3,'LOW DISK'
p.mkdir(exist_ok=True)
assert not (p/'artifacts/sol-translator-20260929/ground-v3-s0/LAUNCH.json').exists(),'DUPLICATE TRAIN: new explicit-resume job required'
PY
scp "$SOL_ART/translator-v4-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/DEPLOYMENT-V4-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY' 2>&1 | tee "$SOL_ART/ground-v3-s0-PC.log"
from pathlib import Path
import hashlib,json,os,sys,tarfile
from types import SimpleNamespace
root=Path('C:/Users/benja/sol-translator-human-v4')
m=json.loads((root/'package.json').read_text())
assert hashlib.sha256((root/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(root/'payload.tar.gz') as archive:
    for x in archive.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
    archive.extractall(root)
os.chdir(root);sys.path.insert(0,str(root/'scripts'))
from sol_translator_deploy_v4 import run
sys.exit(run(SimpleNamespace(root=str(root),seed=0,job='sol-translator-human-v4-s0-pc',resume=False)))
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/raw-s0.tar.gz" "$SOL_ART/ground-v3-s0-raw.tar.gz" || true
if [ -f "$SOL_ART/ground-v3-s0-raw.tar.gz" ]; then tar -xzf "$SOL_ART/ground-v3-s0-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
mkdir -p "$SOL_ART/ground-v3-weights-s0"
for SOL_NAME in parent-s0.pt input-s0.pt bootstrap-English-s0.pt; do
  scp benspc:"$SOL_PC/$SOL_ART/ground-v3-s0/$SOL_NAME" "$SOL_ART/ground-v3-weights-s0/$SOL_NAME" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_ART/ground-v3-s0-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/ground-v3-s0 artifacts/sol-translator-20260929/ground-v3-s0-PC.log artifacts/sol-translator-20260929/ground-v3-s0-PC.exit
