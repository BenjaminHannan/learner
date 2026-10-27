BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 66 minutes
LABEL: sol-compose-ordered-v10r2-s1-pc

ADDITIVE r2 missing sealed plain import dependency; newroot/job/results, original failed V10 preserved. READY NEWordered HUMAN jointTRAIN500, full512context, final4CE/mean8aux. Actualwarmclosed500core/read+500frozenprefix exactbytes pinned; no semantic/sourceproof transfer. FP32 cachedLM reused/frozen, thinreader/core/prefix optimization.350s numericfull49query/512book/64target2rowgraph preflight noopt + actualnativeMATHparity MUSTPASS beforeTRAIN. 2GiBfloor512MiBnewoutputcap bothseeds; noLMcopies/downloads. Canonicalfinalquery only toEnglish, notebookinternal. NoDEV100/stop88/sleep work. Subsequentactualhumanexperience/replay nightlytraining required; engineeringgainproof deferred.3950wrapper bounded, same16predeclaredTRAINinputs×5 unchanged-adapter controls diagnostic. No hiddenbudgetcuts: partialweightsraw retained, no diagnostic on partialTRAIN.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 3950 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_OWN=artifacts/sol-compose-20260929
SOL_COLLECT="$SOL_OWN/ordered-v10r2/seed1"
mkdir -p "$SOL_COLLECT"
SOL_PC=C:/Users/benja/sol-translator-ordered-v10r2
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-ordered-v10r2');assert shutil.disk_usage('C:/').free>=2*1024**3,'DISK FLOOR';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/ground-ordered-v10-s1-loop/LAUNCH.json').exists(),'DUPLICATE: newexplicitresumejob required'
PY
scp "$SOL_OWN/sol_compose_ordered-v10r2-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_OWN/sol_compose_ORDERED-V10R2-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_OWN/ordered-v10r2-s1-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-ordered-v10r2');m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
seal=json.loads((r/'artifacts/sol-compose-20260929/sol_compose_ORDERED-V10R2-SEAL.json').read_text())
for name,want in seal['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==want,'ADDITIVE PIN '+name
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_ordered_deploy_v10 import run
sys.exit(run(SimpleNamespace(root=str(r),seed=1,job='sol-compose-ordered-v10r2-s1-pc')))
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/ordered-raw-s1.tar.gz" "$SOL_OWN/ordered-v10r2-s1-raw.tar.gz" || true
if [ -f "$SOL_OWN/ordered-v10r2-s1-raw.tar.gz" ]; then tar -xzf "$SOL_OWN/ordered-v10r2-s1-raw.tar.gz" -C "$SOL_COLLECT"; fi
mkdir -p "$SOL_OWN/ordered-v10r2-weights-s1"
for SOL_NAME in parent-s1.pt input-s1.pt bootstrap-English-s1.pt; do
 scp benspc:"$SOL_PC/$SOL_ART/ground-ordered-v10-s1-loop/$SOL_NAME" "$SOL_OWN/ordered-v10r2-weights-s1/$SOL_NAME" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_OWN/ordered-v10r2-s1-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-compose-20260929/ordered-v10r2/seed1 artifacts/sol-compose-20260929/ordered-v10r2-s1-PC.log artifacts/sol-compose-20260929/ordered-v10r2-s1-PC.exit
