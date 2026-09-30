BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 5 minutes
LABEL: sol-stop-ordered-r2-s0-receipt-cpu-v1

READY for James review/publication; artifact draft only, not live queue.
Exact CLOSED500 ordered-r2 seed0 parent/reader/prefix, verified locally against
transport and exports. Basic native-fixed4 numerical safety, not learned-stop
qualification or semantic/sleep-gain proof. Two fresh numeric seeds0/1; native
begin/final/repeat/physical-trim comparison must be exactly equal. MATH scope,
actual four transitions, final query-only canonical packet, actual thin prefix
consumption, no mutations. Each seed has 21 enumerated boundary checks. Measured
repeat differences are saved; no assumed numerical noise or work-to-speed claim.

New isolated PC source root; reads closed r2 checkpoints and original qualified
LM provenance IN PLACE. Packet is 45,743 bytes, 17 pinned source files plus
package/tuple JSON. No model/LM copy or LM load. No optimizer, human text, stop88,
DEV/panel, sleep or generation. CPU only, GPU visibility disabled. Output budget
64MiB checked after writer; disk floor1GiB; outer300s, writer240s + binder20s.
Failure preserves raw and burns this run/root: never overwrite/rerun it.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 300 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1
SOL_PC=C:/Users/benja/sol-stop-ordered-receipt-v1-s0
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PY'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-stop-ordered-receipt-v1-s0')
assert not r.exists(),'NEW root required; preserve prior failure'
assert shutil.disk_usage('C:/').free>=1024**3,'1GiB disk floor'
r.mkdir()
PY
scp "$SOL_ART/packet-s0.tar.gz" benspc:"$SOL_PC/packet-s0.tar.gz"
scp "$SOL_ART/PACKET-s0.json" benspc:"$SOL_PC/PACKET-s0.json"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/actual-awake-s0-PC.log"
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,time
r=Path('C:/Users/benja/sol-stop-ordered-receipt-v1-s0');os.chdir(r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('PACKET-s0.json')=='8186c9a66e54d269731e88f3f32e94de174db9c72791fb977896e911a1b9c388'
m=json.loads(Path('PACKET-s0.json').read_text(encoding='utf-8'))
assert sha('packet-s0.tar.gz')==m['archive_sha256']=='c432e37626881c8203d0fa9fda0c94ead7c0b8b802dec846e760a72c9b6b958d'
with tarfile.open('packet-s0.tar.gz') as t:
 for x in t.getmembers():
  assert x.isfile() and x.name in m['files'] and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
for name,want in m['files'].items():assert sha(name)==want,'source pin '+name
a=Path('artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1')
spec=a/'binding-s0.json';out=a/'actual-awake-s0'
env=dict(os.environ,PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),PYTHONUTF8='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
started=time.monotonic();rc=1
try:
 bind=[sys.executable,'-X','utf8','-B','scripts/sol_stop_ordered_receipt_bind_v1.py','--package',str(a/'PACKAGE.json'),'--tuple',str(a/'TUPLE-s0.json'),'--out',str(spec)]
 subprocess.run(bind,env=env,check=True,timeout=20)
 command=[sys.executable,'-X','utf8','-B','scripts/sol_stop_ordered_checkpoint_receipt_v1.py','--spec',str(spec),'--out',str(out),'--device','cpu']
 rc=subprocess.run(command,env=env,timeout=240).returncode
 assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=64*1024**2,'64MiB output budget'
except Exception as exc:
 print(type(exc).__name__,str(exc));rc=1
finally:
 result={'returncode':rc,'wall_seconds':time.monotonic()-started,'execution_policy':'native-fixed4','optimizer_updates':0,'human_rows':0,'stop88_reads':0,'DEV_reads':0,'scope':'basic exact-tuple numeric safety; NOT semantic/learnedstop qualification'}
 if (out/'receipt.json').exists():result.update(receipt_path=str(r/out/'receipt.json'),receipt_sha256=sha(out/'receipt.json'))
 (a/'RESULT-s0.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 with tarfile.open('raw-s0.tar.gz','w:gz') as t:
  for p in (spec,a/'RESULT-s0.json',out):
   if p.exists():t.add(p,arcname=str(p))
 print(json.dumps(result));sys.exit(rc)
PYREMOTE
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/raw-s0.tar.gz" "$SOL_ART/actual-awake-s0-raw.tar.gz" || true
mkdir -p "$SOL_ART/collected-awake-s0"
if [ -f "$SOL_ART/actual-awake-s0-raw.tar.gz" ]; then tar -xzf "$SOL_ART/actual-awake-s0-raw.tar.gz" -C "$SOL_ART/collected-awake-s0"; fi
printf '%s\n' "$SOL_RC" > "$SOL_ART/actual-awake-s0-PC.exit"
exit "$SOL_RC"
SOL_JOB
```

PUSH: artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/actual-awake-s0-PC.log artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/actual-awake-s0-PC.exit artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/collected-awake-s0

Receipt intended path:
C:/Users/benja/sol-stop-ordered-receipt-v1-s0/artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/actual-awake-s0/receipt.json.
James/Bernoulli must pin its actual SHA independently after rc0. Seed1 gets a
separate exact CLOSED tuple/job after closure; this seed0 receipt never qualifies
seed1. A changed post-night parent/rebound prefix needs a NEW receipt.
