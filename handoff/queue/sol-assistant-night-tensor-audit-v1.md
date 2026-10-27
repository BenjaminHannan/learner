BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 5 minutes
LABEL: sol-assistant-night-tensor-audit-v1

READY CPU read-only actual closed night checkpoint audit. Exact final manifest,
resume, decision and baseline hashes presealed. No model forward/backward,
optimizer construction/steps, LM load/copy, weight copies, activation or holdout.
Read .pt in place; native core construction only for actual parameter order/shapes.
One actual trained seed0 artifact audit; no two-seed learning or retention claim.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 300 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-assistant-20260930/night-tensor-audit-v1
SOL_PC=C:/Users/benja/sol-compose-night-v2-s0
scp "$SOL_ART/payload.tar.gz" benspc:"$SOL_PC/assistant-night-tensor-audit-v1.tar.gz"
scp "$SOL_ART/PACKAGE.json" benspc:"$SOL_PC/assistant-night-tensor-audit-v1-package.json"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY' 2>&1 | tee "$SOL_ART/PC.log"
import os,sys,json,tarfile,hashlib,subprocess
from pathlib import Path
r=Path('C:/Users/benja/sol-compose-night-v2-s0');os.chdir(r)
m=json.loads((r/'assistant-night-tensor-audit-v1-package.json').read_text(encoding='utf-8'))
assert hashlib.sha256((r/'assistant-night-tensor-audit-v1.tar.gz').read_bytes()).hexdigest()==m['sha256']=='74235629f143e74e85a010157b63b89df25a98540baab943ae25529a8fc0caba'
with tarfile.open(r/'assistant-night-tensor-audit-v1.tar.gz') as t:
 assert set(t.getnames())==set(m['files'])
 for x in t.getmembers():
  assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
  p=r/x.name
  if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][x.name],'do not overwrite differing file'
 t.extractall(r)
for p,h in m['files'].items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h
base='artifacts/sol-assistant-20260930/night-tensor-audit-v1'
env=dict(os.environ,JOB='sol-assistant-night-tensor-audit-v1',TREE=str(r),PYTHONUTF8='1',PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),OMP_NUM_THREADS='2',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_assistant_night_tensor_audit_v1.py','--spec',base+'/SPEC.json','--out',base+'/actual-s0'],env=env,timeout=240).returncode
print(json.dumps({'returncode':rc,'model_forwards':0,'optimizer_steps':0}),flush=True)
sys.exit(rc)
PY
SOL_RC=${PIPESTATUS[0]}
set -e
mkdir -p "$SOL_ART/actual-s0"
scp benspc:"$SOL_PC/$SOL_ART/actual-s0/raw-audit.json" "$SOL_ART/actual-s0/raw-audit.json" || true
printf '%s\n' "$SOL_RC" > "$SOL_ART/PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-assistant-20260930/night-tensor-audit-v1/PC.log artifacts/sol-assistant-20260930/night-tensor-audit-v1/PC.exit artifacts/sol-assistant-20260930/night-tensor-audit-v1/actual-s0/raw-audit.json
