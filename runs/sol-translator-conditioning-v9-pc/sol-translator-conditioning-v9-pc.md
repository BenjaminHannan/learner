BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 5 minutes
LABEL: sol-translator-conditioning-v9-pc

TRAIN512 tokenizer-only coverage; fixed256prefix, no oraclecrop, no LM/CUDA/optimizer/DEV inference.3/3 numeric HUMAN shift/mask/gradient checks. Cachedfilesverifiedunchangedpins. No generated adaptationtext.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 280 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-conditioning-v9
ssh -T -o BatchMode=yes benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY'
from pathlib import Path
p=Path('C:/Users/benja/sol-translator-conditioning-v9');p.mkdir(exist_ok=True)
assert not (p/'artifacts/sol-translator-20260929/CONDITIONING-V9-PC.json').exists(),'NO DUPLICATE'
PY
scp "$SOL_ART/translator-conditioning-v9-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/CONDITIONING-V9-PACKAGE.json" benspc:"$SOL_PC/package.json"
ssh -T -o BatchMode=yes benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY' 2>&1 | tee "$SOL_ART/conditioning-v9-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-conditioning-v9')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((r/'package.json').read_text());assert sha(r/'payload.tar.gz')==m['sha256']
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
s=json.loads((r/'artifacts/sol-translator-20260929/CONDITIONING-V9-SEAL.json').read_text())
for name,want in s['files'].items():assert sha(r/name)==want,name
os.chdir(r);os.environ.update(JOB='sol-translator-conditioning-v9-pc',TREE=str(r),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_conditioning_audit_v9 import coverage
coverage(SimpleNamespace(model='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b',corpus=str(r/'artifacts/sol-translator-20260929/corpus'),out=str(r/'artifacts/sol-translator-20260929/CONDITIONING-V9-PC.json')))
PY
scp benspc:"$SOL_PC/$SOL_ART/CONDITIONING-V9-PC.json" "$SOL_ART/CONDITIONING-V9-PC.json"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/CONDITIONING-V9-PC.json artifacts/sol-translator-20260929/conditioning-v9-PC.log
