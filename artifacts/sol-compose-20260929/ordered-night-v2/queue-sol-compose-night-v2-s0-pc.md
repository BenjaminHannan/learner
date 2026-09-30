BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 22 minutes
LABEL: sol-compose-night-v2-s0-pc

NEW static HUMAN replay engineering sleep25, seed0 exact awake tuple+nativefixed4 receipt. Seed1 HELD pending exact awake tuple. No day-data fulfillment/semantic/gain claim. No DEV/stop88; no model text targets. New1GiB floor+768MiB aggregate temporary/output cap, previous seals unchanged. Newroot, no rerun. 600s fit,900s training child,300s candidate CPU receipt,1300s outer. Original fixed4 explicitly unqualified learned stop. Guard failure retains prior bundle; no activation by static pipeline.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1300 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-compose-20260929/ordered-night-v2
SOL_PC=C:/Users/benja/sol-compose-night-v2-s0
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PRE'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-compose-night-v2-s0');assert not r.exists(),'NEW root only';assert shutil.disk_usage('C:/').free>=1073741824+805306368,'declared reserve+aggregate output budget';r.mkdir()
PRE
scp "$SOL_ART/payload-s0.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/PACKAGE-s0.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'RUN' 2>&1 | tee "$SOL_ART/PC-s0.log"
from pathlib import Path
import os,sys,subprocess,json,hashlib,tarfile,time
r=Path('C:/Users/benja/sol-compose-night-v2-s0');os.chdir(r);m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256']=='5c060378122edca61cd944384c7aeb350a5c505f6652053851ec9630d9b92ed1'
with tarfile.open(r/'payload.tar.gz') as t:
 assert set(t.getnames())==set(m['files'])
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
for p,h in m['files'].items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h
own=r/'artifacts/sol-compose-20260929/ordered-night-v2';out=own/'run-s0'
env=dict(os.environ,JOB='sol-compose-night-v2-s0-pc',TREE=str(r),PYTHONUTF8='1',PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2')
rc=1;started=time.monotonic()
try:
 rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_sleep_ordered_v2.py','--binding',str(own/'BINDING-s0.json'),'--plan',str(own/'PLAN.json'),'--seed','0','--out',str(out),'--device','cuda'],env=env,timeout=900).returncode
 if rc==0 and json.loads((out/'decision.json').read_text())['activation_eligible']:
  rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_assistant_candidate_pipeline_v2.py','--candidate-manifest',str(out/'candidate-manifest.json'),'--decision',str(out/'decision.json'),'--previous-bundle','C:/Users/benja/sol-translator-ordered-v10r2/artifacts/sol-assistant-20260930/frozen-ordered-v10r2-s0-u500/bundle.json','--package','artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/PACKAGE.json','--out','artifacts/sol-assistant-20260930/night-static-v2-s0','--receipt-out','artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0'],env=env,timeout=300).returncode
finally:
 result={'returncode':rc,'wall_seconds':time.monotonic()-started,'actual_day_experience':False,'automatic_activation':False}
 (own/'TRANSPORT-s0.json').write_text(json.dumps(result)+'\n')
 with tarfile.open(r/'raw-s0.tar.gz','w:gz') as t:
  for base in [own,r/'artifacts/sol-assistant-20260930/night-static-v2-s0',r/'artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0']:
   if base.exists():
    for p in base.rglob('*'):
     if p.is_file() and p.suffix in ('.json','.jsonl','.log'):t.add(p,arcname=p.relative_to(r).as_posix())
 print(json.dumps(result),flush=True)
sys.exit(rc)
RUN
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/raw-s0.tar.gz" "$SOL_ART/raw-s0.tar.gz" || true
mkdir -p "$SOL_ART/collected-s0"
if [ -f "$SOL_ART/raw-s0.tar.gz" ]; then tar -xzf "$SOL_ART/raw-s0.tar.gz" -C "$SOL_ART/collected-s0"; fi
printf '%s\n' "$SOL_RC" > "$SOL_ART/PC-s0.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-compose-20260929/ordered-night-v2/PC-s0.log artifacts/sol-compose-20260929/ordered-night-v2/PC-s0.exit artifacts/sol-compose-20260929/ordered-night-v2/collected-s0
