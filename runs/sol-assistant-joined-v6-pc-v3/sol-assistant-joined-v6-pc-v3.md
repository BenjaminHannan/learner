BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 20 minutes
LABEL: sol-assistant-joined-v6-pc-v3

SUPERSEDES UNRUN joined-v1/v2; metadata-only shared-TRAIN membership correction.
PRE-RUN addendum v3 records both ledger hashes and all4 membership checks.
Freeze v2 and r2 snapshot paths UNCHANGED; smoke/recovery outputs NEW v3.
READY after sol-assistant-freeze-v6-s0-pc-v2 SUCCESS and both closed500 tuples.
James publishes; watcher owns GPU. No direct SSH execution by worker.
Frozen seed0 bundle required, no replacement/fallback. Freeze seed1 same source
versions; then actual populated Adam/RNG restore (NO step) and actual joined
CUDA generation seeds0/1 sequentially, one LM resident. Two literal HUMAN TRAIN
rows only, no DEV/holdout. Outputs never training. Fixed4 unqualified stop/sleep.
No dense semantic claim. Source hashes, budgets/comparators and exact-storage
passmarks sealed in JOINED-PLAN-v3 before any generation. Main proof panels untouched.
Outer1200s; freeze300s; each recovery150s; each smoke260s (script240s mark).

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1200 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-assistant-20260930
SOL_PC=C:/Users/benja/sol-translator-human-v6
scp "$SOL_ART/joined-v3.tar.gz" benspc:"$SOL_PC/assistant-joined-v3.tar.gz"
scp "$SOL_ART/joined-v3-package.json" benspc:"$SOL_PC/assistant-joined-v3-package.json"
scp artifacts/sol-translator-20260929/ground-v6-s1-PC.log benspc:"$SOL_PC/assistant-v6-s1-stdout.log"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/joined-v6-r3-PC.log"
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile
root=Path('C:/Users/benja/sol-translator-human-v6');os.chdir(root)
own=root/'artifacts/sol-assistant-20260930'
assert (own/'frozen-v6-s0-u500-r2/freeze-receipt.json').is_file(),'real dependency: seed0 freeze has not succeeded'
m=json.loads((root/'assistant-joined-v3-package.json').read_text(encoding='utf-8'))
assert hashlib.sha256((root/'assistant-joined-v3.tar.gz').read_bytes()).hexdigest()==m['archive_sha256']=='ffc9ac916475f663c63066ed3a3a21e897bbe3694f8bf7005e93620622e11b19'
with tarfile.open(root/'assistant-joined-v3.tar.gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in m['files'] and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=root/member.name
  if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][member.name],'existing bytes differ, preserve'
 tar.extractall(root)
for name,h in m['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h
base=json.loads((root/'assistant-freeze-v1-package.json').read_text(encoding='utf-8'))
assert base['archive_sha256']=='5c50cc33bf85d83e8bad872b3a542c7b168f0bee3e34434f5eced3c8ca297c44'
for name,h in base['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h
fix=json.loads((root/'assistant-freeze-v2-package.json').read_text(encoding='utf-8'))
assert fix['archive_sha256']==m['freeze_v2_archive_sha256']
for name,h in fix['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h
lm='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
env=dict(os.environ,JOB='sol-assistant-joined-v6-pc-v3',TREE=str(root),PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONUTF8='1')
commands=[([sys.executable,'-X','utf8','-B','scripts/sol_assistant_freeze_v2.py','--run','artifacts/sol-translator-20260929/ground-v6-s1','--seed','1','--stdout','assistant-v6-s1-stdout.log','--model',lm,'--out',str(own/'frozen-v6-s1-u500-r2')],300)]
for seed in (0,1):
 bundle=str(own/f'frozen-v6-s{seed}-u500-r2/bundle.json')
 commands.append(([sys.executable,'-X','utf8','-B','scripts/sol_assistant_recovery.py','--bundle',bundle,'--out',str(own/f'recovery-v3-s{seed}')],150))
 commands.append(([sys.executable,'-X','utf8','-B','scripts/sol_assistant_joined_smoke_v2.py','--bundle',bundle,'--plan',str(own/'JOINED-PLAN-v3.json'),'--rows',str(own/'joined-TRAIN-v3.json'),'--out',str(own/f'joined-v3-s{seed}'),'--device','cuda'],260))
code=1
try:
 for command,timeout in commands:
  print(json.dumps({'command':command,'timeout':timeout}),flush=True)
  result=subprocess.run(command,env=env,timeout=timeout)
  if result.returncode:sys.exit(result.returncode)
 code=0
finally:
 with tarfile.open(own/'joined-v3-raw.tar.gz','w:gz') as tar:
  for pattern in ('recovery-v3-s*/*.json','joined-v3-s*/*.json','joined-v3-s*/final-payloads.pt','frozen-v6-s1-u500-r2/bundle.json','frozen-v6-s1-u500-r2/freeze-receipt.json'):
   for p in own.glob(pattern):tar.add(p,arcname=str(p.relative_to(root)))
 print(json.dumps({'status':'engineering transport','exit':code,'raw_archive_sha256':hashlib.sha256((own/'joined-v3-raw.tar.gz').read_bytes()).hexdigest(),'semantic_status':'UNQUALIFIED','optimizer_steps':0,'sleep':0}),flush=True)
sys.exit(code)
PYREMOTE
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/$SOL_ART/joined-v3-raw.tar.gz" "$SOL_ART/joined-v3-raw.tar.gz" || true
if [ -f "$SOL_ART/joined-v3-raw.tar.gz" ]; then tar -xzf "$SOL_ART/joined-v3-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
printf '%s\n' "$SOL_RC" > "$SOL_ART/joined-v6-r3-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-assistant-20260930/joined-v6-r3-PC.log artifacts/sol-assistant-20260930/joined-v6-r3-PC.exit artifacts/sol-assistant-20260930/joined-v3-s0 artifacts/sol-assistant-20260930/joined-v3-s1 artifacts/sol-assistant-20260930/recovery-v3-s0 artifacts/sol-assistant-20260930/recovery-v3-s1
