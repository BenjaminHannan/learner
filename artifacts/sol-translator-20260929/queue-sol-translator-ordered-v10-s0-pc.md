BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 66 minutes
LABEL: sol-translator-ordered-v10-s0-pc

READY NEWordered HUMAN jointTRAIN500, full512context, final4CE/mean8aux. Actualwarmclosed500core/read+500frozenprefix exactbytes pinned; no semantic/sourceproof transfer. FP32 cachedLM reused/frozen, thinreader/core/prefix optimization.350s numericfull49query/512book/64target2rowgraph preflight noopt + actualnativeMATHparity MUSTPASS beforeTRAIN. 2GiBfloor512MiBnewoutputcap bothseeds; noLMcopies/downloads. Canonicalfinalquery only toEnglish, notebookinternal. NoDEV100/stop88/sleep work. Subsequentactualhumanexperience/replay nightlytraining required; engineeringgainproof deferred.3950wrapper bounded, same16predeclaredTRAINinputs×5 unchanged-adapter controls diagnostic. No hiddenbudgetcuts: partialweightsraw retained, no diagnostic on partialTRAIN.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 3950 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-ordered-v10
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-ordered-v10');assert shutil.disk_usage('C:/').free>=2*1024**3,'DISK FLOOR';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop/LAUNCH.json').exists(),'DUPLICATE: newexplicitresumejob required'
PY
scp "$SOL_ART/translator-ordered-v10-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/ORDERED-GROUND-V10-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_ART/ground-ordered-v10-s0-loop-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-ordered-v10');m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_ordered_deploy_v10 import run
sys.exit(run(SimpleNamespace(root=str(r),seed=0,job='sol-translator-ordered-v10-s0-pc')))
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/ordered-raw-s0.tar.gz" "$SOL_ART/ordered-v10-s0-raw.tar.gz" || true
if [ -f "$SOL_ART/ordered-v10-s0-raw.tar.gz" ]; then tar -xzf "$SOL_ART/ordered-v10-s0-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
mkdir -p "$SOL_ART/ordered-v10-weights-s0"
for SOL_NAME in parent-s0.pt input-s0.pt bootstrap-English-s0.pt; do
 scp benspc:"$SOL_PC/$SOL_ART/ground-ordered-v10-s0-loop/$SOL_NAME" "$SOL_ART/ordered-v10-weights-s0/$SOL_NAME" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_ART/ground-ordered-v10-s0-loop-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop artifacts/sol-translator-20260929/ordered-diagnostic-v10-s0 artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop-PC.log artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop-PC.exit
