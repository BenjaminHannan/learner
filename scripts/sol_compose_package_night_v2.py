"""Package a new bounded static-human replay night job; never runs optimization."""
from pathlib import Path
import hashlib,json,tarfile,io,subprocess
R=Path(__file__).resolve().parents[1];A=R/'artifacts/sol-compose-20260929/ordered-night-v2';A.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
pc='C:/Users/benja/sol-compose-night-v2-s0';job='sol-compose-night-v2-s0-pc';ar='artifacts/sol-compose-20260929/ordered-night-v2'
files={}
for archive in ['artifacts/sol-compose-20260929/sol_compose_ordered-v10r2-payload.tar.gz','artifacts/sol-assistant-20260930/freeze-ordered-r2-s0-payload.tar.gz','artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/packet-s0.tar.gz']:
 with tarfile.open(R/archive) as t:
  for m in t.getmembers():
   assert m.isfile();b=t.extractfile(m).read()
   assert m.name not in files or files[m.name]==b,m.name
   files[m.name]=b
for name in ['scripts/sol_sleep_ordered_v2.py','scripts/sol_assistant_candidate_pipeline_v2.py']:
 files[name]=(R/name).read_bytes()
plan=json.loads((A/'PLAN-DRAFT.json').read_text());plan['binding']='Exact actual ordered r2seed0+nativefixed4 receipt. Seed1 declared but HELD until its exact awake tuple qualified. Static replay only, no day learning claim.'
dump(A/'PLAN.json',plan);files[ar+'/PLAN.json']=(A/'PLAN.json').read_bytes()
config=json.loads((R/'artifacts/sol-compose-20260929/ordered-v10r2/seed0/artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop/runtime-config.json').read_text())
s={k:{'path':config[key+'_path'],'sha256':config[key+'_sha256']} for k,key in [('parent','parent'),('reader','reader'),('prefix','adapter')]}
s.update(provenance={'path':config['lm_provenance'],'sha256':'ec5d42dc87c2f2d8a25168de33b5c8324c8f777f75e7c1b69b8c6205fe97bee8'},model_path=config['lm_path'],previous_bundle_pin='b3ce3f5c15f62eacb330fe5a2c850b4d5c8f9991bdd5f751534a39ff055ce96c',awake_safety_receipt={'path':'C:/Users/benja/sol-stop-ordered-receipt-v1-s0/artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/actual-awake-s0/receipt.json','sha256':'5b9a47328a85f3ee928c902c42ad473a49f0fc530acb5a267a584cd788a9e55b'})
corpora=[p[:-len('/pairs.json')] for p in files if p.endswith('/pairs.json')];assert len(corpora)==1,corpora
binding={'version':'sol-ordered-night-v2','plan_sha256':sha(files[ar+'/PLAN.json']),'driver_sha256':sha(files['scripts/sol_sleep_ordered_v2.py']),'dependency_pins':{pc+'/'+p:sha(b) for p,b in files.items()},'seeds':{'0':s},'ordered_module':'sol_spatial_poc_ordered_v2','graph_module':'sol_translator_ground_ordered_v10','native_module':'sol_stop_ordered_api2','corpus':pc+'/'+corpora[0]}
dump(A/'BINDING-s0.json',binding);files[ar+'/BINDING-s0.json']=(A/'BINDING-s0.json').read_bytes()
# Validate source syntax without loading models or data.
for name,b in files.items():
 if name.endswith('.py'):compile(b,name,'exec')
archive=A/'payload-s0.tar.gz'
with tarfile.open(archive,'w:gz') as t:
 for name,b in sorted(files.items()):
  m=tarfile.TarInfo(name);m.size=len(b);m.mtime=0;t.addfile(m,io.BytesIO(b))
package={'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,'files':{p:sha(b) for p,b in files.items()},'scope':'25 actual core-only updates on verified static HUMAN TRAIN experience/replay; no day-learning or semantic success claim','seed1':'HELD no exact qualified ordered awake tuple','source_seeds_predeclared':[0,1],'optimizer_updates_requested':25,'output_cap_bytes':plan['output_cap_bytes'],'retained_disk_floor_bytes':plan['disk_floor_bytes']}
dump(A/'PACKAGE-s0.json',package)
q=f'''BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 22 minutes
LABEL: {job}

NEW static HUMAN replay engineering sleep25, seed0 exact awake tuple+nativefixed4 receipt. Seed1 HELD pending exact awake tuple. No day-data fulfillment/semantic/gain claim. No DEV/stop88; no model text targets. New1GiB floor+768MiB aggregate temporary/output cap, previous seals unchanged. Newroot, no rerun. 600s fit,900s training child,300s candidate CPU receipt,1300s outer. Original fixed4 explicitly unqualified learned stop. Guard failure retains prior bundle; no activation by static pipeline.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1300 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART={ar}
SOL_PC={pc}
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PRE'
from pathlib import Path
import shutil
r=Path('{pc}');assert not r.exists(),'NEW root only';assert shutil.disk_usage('C:/').free>=1073741824+805306368,'declared reserve+aggregate output budget';r.mkdir()
PRE
scp "$SOL_ART/payload-s0.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/PACKAGE-s0.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'RUN' 2>&1 | tee "$SOL_ART/PC-s0.log"
from pathlib import Path
import os,sys,subprocess,json,hashlib,tarfile,time
r=Path('{pc}');os.chdir(r);m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256']=='{package['sha256']}'
with tarfile.open(r/'payload.tar.gz') as t:
 assert set(t.getnames())==set(m['files'])
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
for p,h in m['files'].items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h
own=r/'{ar}';out=own/'run-s0'
env=dict(os.environ,JOB='{job}',TREE=str(r),PYTHONUTF8='1',PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='2')
rc=1;started=time.monotonic()
try:
 rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_sleep_ordered_v2.py','--binding',str(own/'BINDING-s0.json'),'--plan',str(own/'PLAN.json'),'--seed','0','--out',str(out),'--device','cuda'],env=env,timeout=900).returncode
 if rc==0 and json.loads((out/'decision.json').read_text())['activation_eligible']:
  rc=subprocess.run([sys.executable,'-X','utf8','-B','scripts/sol_assistant_candidate_pipeline_v2.py','--candidate-manifest',str(out/'candidate-manifest.json'),'--decision',str(out/'decision.json'),'--previous-bundle','C:/Users/benja/sol-translator-ordered-v10r2/artifacts/sol-assistant-20260930/frozen-ordered-v10r2-s0-u500/bundle.json','--package','artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/PACKAGE.json','--out','artifacts/sol-assistant-20260930/night-static-v2-s0','--receipt-out','artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0'],env=env,timeout=300).returncode
finally:
 result={{'returncode':rc,'wall_seconds':time.monotonic()-started,'actual_day_experience':False,'automatic_activation':False}}
 (own/'TRANSPORT-s0.json').write_text(json.dumps(result)+'\\n')
 with tarfile.open(r/'raw-s0.tar.gz','w:gz') as t:
  for base in [own,r/'artifacts/sol-assistant-20260930/night-static-v2-s0',r/'artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0']:
   if base.exists():
    for p in base.rglob('*'):
     if p.is_file() and p.suffix in ('.json','.jsonl','.log'):t.add(p,arcname=p.relative_to(r).as_posix())
 print(json.dumps(result),flush=True)
sys.exit(rc)
RUN
SOL_RC=${{PIPESTATUS[0]}}
set -e
scp benspc:"$SOL_PC/raw-s0.tar.gz" "$SOL_ART/raw-s0.tar.gz" || true
mkdir -p "$SOL_ART/collected-s0"
if [ -f "$SOL_ART/raw-s0.tar.gz" ]; then tar -xzf "$SOL_ART/raw-s0.tar.gz" -C "$SOL_ART/collected-s0"; fi
printf '%s\\n' "$SOL_RC" > "$SOL_ART/PC-s0.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: {ar}/PC-s0.log {ar}/PC-s0.exit {ar}/collected-s0
'''
subprocess.run(['bash','-n'],input=q.split('```bash\n')[1].split('```')[0],text=True,check=True)
(A/'queue-sol-compose-night-v2-s0-pc.md').write_text(q)
print(json.dumps({'package_sha256':package['sha256'],'bytes':package['bytes'],'files':len(files),'queue':'artifact only, not published','training_executed':False}))
