STATUS: HELD
DEFERRED: direct human awake-model/minimal-actual-sleep priority; original sealed V7 artifact unchanged, no claimed completion.
BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 66 minutes
LABEL: sol-translator-prefix-v7-s0-d0-embedding-pc

READY sealed TRAIN-only; no DEV/stop/sleep. Closed source tuple pinned.
Read cached FP32 LFM and CLOSED parent/reader in place; no downloads/copies.
1GiB free floor,256MiB aggregate new outputs. Queues serialized by watcher.
Plain human parent not yet available; no plain comparison claimed.
Runtime prefix selection predeclared loop/source0+1/decoder0 before DEV.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 3950 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-followup-v7
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY'
from pathlib import Path
import shutil
p=Path('C:/Users/benja/sol-translator-followup-v7')
assert shutil.disk_usage('C:/').free>=1024**3,'DISK FLOOR'
p.mkdir(exist_ok=True)
assert not (p/'artifacts/sol-translator-20260929/prefix-v7-s0-d0-embedding/TRANSPORT-LAUNCH.json').exists(),'DUPLICATE; new version/resume job needed'
PY
scp "$SOL_ART/translator-followup-v7-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/FOLLOWUP-V7-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY' 2>&1 | tee "$SOL_ART/prefix-v7-s0-d0-embedding-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-followup-v7')
m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_followup_deploy_v7 import run
sys.exit(run(SimpleNamespace(root=str(r),seed=0,decoder_seed=0,arm='embedding',mode='prefix',job='sol-translator-prefix-v7-s0-d0-embedding-pc')))
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/prefix-v7-s0-d0-embedding-raw.tar.gz" "$SOL_ART/prefix-v7-s0-d0-embedding-raw.tar.gz" || true
if [ -f "$SOL_ART/prefix-v7-s0-d0-embedding-raw.tar.gz" ]; then tar -xzf "$SOL_ART/prefix-v7-s0-d0-embedding-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
mkdir -p "$SOL_ART/prefix-v7-s0-d0-embedding"
scp benspc:"$SOL_PC/$SOL_ART/prefix-v7-s0-d0-embedding/English.pt" "$SOL_ART/prefix-v7-s0-d0-embedding/English.pt" || true
printf '%s\n' "$SOL_RC" > "$SOL_ART/prefix-v7-s0-d0-embedding-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/prefix-v7-s0-d0-embedding artifacts/sol-translator-20260929/prefix-v7-s0-d0-embedding-PC.log artifacts/sol-translator-20260929/prefix-v7-s0-d0-embedding-PC.exit
