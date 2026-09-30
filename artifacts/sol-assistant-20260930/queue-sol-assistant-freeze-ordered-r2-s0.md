BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 10 minutes
LABEL: sol-assistant-freeze-ordered-r2-s0

READY exact CLOSED500 r2 seed0 immutable freeze. CPU tensor/storage verification,
no generation/optimizer/holdout. Checkpoint hardlinks on same PC volume; no LM copy.
Explicit final DURABLE parent/resume equality, five actual receipt pins, source seals.
Day bridge sources installed only; no day capture or learning falsely claimed.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 600 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-assistant-20260930
SOL_PC=C:/Users/benja/sol-translator-ordered-v10r2
scp "$SOL_ART/freeze-ordered-r2-s0-payload.tar.gz" benspc:"$SOL_PC/assistant-freeze-r2-s0.tar.gz"
scp "$SOL_ART/FREEZE-ORDERED-R2-S0-PACKAGE.json" benspc:"$SOL_PC/assistant-freeze-r2-s0-package.json"
scp artifacts/sol-compose-20260929/ordered-v10r2-s0-PC.log benspc:"$SOL_PC/assistant-ordered-r2-s0-stdout.log"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_ART/freeze-ordered-r2-s0-PC.log"
import os,sys,json,hashlib,tarfile,subprocess,shutil
from pathlib import Path
root=Path('C:/Users/benja/sol-translator-ordered-v10r2');os.chdir(root)
own=root/'artifacts/sol-assistant-20260930'
m=json.loads((root/'assistant-freeze-r2-s0-package.json').read_text(encoding='utf-8'))
assert hashlib.sha256((root/'assistant-freeze-r2-s0.tar.gz').read_bytes()).hexdigest()==m['sha256']=='d06b1de43158bfa7e9f92c98000c9929088899132b1550d19038accfc8bb701a'
with tarfile.open(root/'assistant-freeze-r2-s0.tar.gz') as t:
 for member in t.getmembers():
  assert member.isfile() and member.name in m['files'] and '..' not in Path(member.name).parts and not member.name.startswith('/')
  dest=root/member.name
  if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==m['files'][member.name],'preserve existing differing source'
 t.extractall(root)
for path,h in m['files'].items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h
own.mkdir(parents=True,exist_ok=True)
source=root/'assistant-ordered-r2-s0-stdout.log';target=own/'ordered-v10r2-s0-final-stdout.log'
with source.open('rb') as f,target.open('xb') as g:shutil.copyfileobj(f,g)
env=dict(os.environ,JOB='sol-assistant-freeze-ordered-r2-s0',TREE=str(root),PYTHONUTF8='1',PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2')
rc=1
try:
 rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_assistant_freeze_ordered_r2.py'],env=env,timeout=420).returncode
finally:
 with tarfile.open(own/'freeze-ordered-r2-s0-raw.tar.gz','w:gz') as t:
  for pattern in ('freeze-ordered-r2-s0-*.json','frozen-ordered-v10r2-s0-u500/*.json'):
   for p in own.glob(pattern):t.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
 print(json.dumps({'returncode':rc,'optimizer_steps':0,'generation_calls':0}),flush=True)
sys.exit(rc)
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/$SOL_ART/freeze-ordered-r2-s0-raw.tar.gz" "$SOL_ART/freeze-ordered-r2-s0-raw.tar.gz" || true
if [ -f "$SOL_ART/freeze-ordered-r2-s0-raw.tar.gz" ]; then tar -xzf "$SOL_ART/freeze-ordered-r2-s0-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
printf '%s\n' "$SOL_RC" > "$SOL_ART/freeze-ordered-r2-s0-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-assistant-20260930/freeze-ordered-r2-s0-PC.log artifacts/sol-assistant-20260930/freeze-ordered-r2-s0-PC.exit artifacts/sol-assistant-20260930/freeze-ordered-r2-s0-receipt.json artifacts/sol-assistant-20260930/frozen-ordered-v10r2-s0-u500/bundle.json
