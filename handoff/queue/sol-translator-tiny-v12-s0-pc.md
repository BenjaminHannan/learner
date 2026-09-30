BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 30 minutes
LABEL: sol-translator-tiny-v12-s0-pc

READY HUMAN TRAIN four-example capacity diagnosis ONLY. Two arms200updates each: connected reader/core/prefix vs task-indexed prefix table (NOT release architecture). Initial four actualLM noopt cache/label alignment probes; CE-only gradients; no rawquestionLMbypass on connected. FP32cachedLM reused, no copies.384MiBaggregatebothseedoutputs includingatomictemporary;1GiBretainedreserve, startup1424MiB. FreshDEV/stop88 untouched. Raw generated prose never training labels. No semantic/grammar/sleep gain claim.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 1800 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-tiny-v12
ssh -T -o BatchMode=yes benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PYREMOTE'
from pathlib import Path
import shutil
r=Path('C:/Users/benja/sol-translator-tiny-v12');assert shutil.disk_usage('C:/').free>=1424*1024**2,'NEW DISK RESERVE';r.mkdir(exist_ok=True)
assert not (r/'artifacts/sol-translator-20260929/tiny-v12-s0/LAUNCH.json').exists(),'PRESERVE earlier run'
PYREMOTE
scp "$SOL_ART/translator-tiny-v12-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/TINY-V12-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/tiny-v12-s0-PC.log"
import hashlib,json,os,sys,subprocess,tarfile,time
from pathlib import Path
r=Path('C:/Users/benja/sol-translator-tiny-v12');m=json.loads((r/'package.json').read_text());assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256']
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts
 t.extractall(r)
os.chdir(r);env=dict(os.environ,JOB='sol-translator-tiny-v12-s0-pc',TREE=str(r),PYTHONPATH=str(r)+os.pathsep+str(r/'scripts'),PYTHONUTF8='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1');out=r/'artifacts/sol-translator-20260929/tiny-v12-s0';start=time.monotonic();rc=1
try:
 proc=subprocess.Popen([sys.executable,'-X','utf8','-B','scripts/sol_translator_tiny_v12.py','--seed','0'],env=env);rc=proc.wait(timeout=1600)
except subprocess.TimeoutExpired:
 proc.terminate();rc=124
 try:proc.wait(timeout=30)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
finally:
 out.mkdir(parents=True,exist_ok=True);record={'returncode':rc,'wall_seconds':time.monotonic()-start,'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},'stage':'tiny TRAIN capacity diagnostic NOTrelease'};(out/'TRANSPORT-RESULT.json').write_text(json.dumps(record)+'\n')
 with tarfile.open(r/'tiny-v12-s0-raw.tar.gz','w:gz') as t:
  for p in out.iterdir():
   if p.is_file() and p.suffix not in ('.pt','.tmp'):t.add(p,arcname=str(p.relative_to(r)),recursive=False)
 print(json.dumps(record),flush=True)
sys.exit(rc)
PYREMOTE
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/tiny-v12-s0-raw.tar.gz" "$SOL_ART/tiny-v12-s0-raw.tar.gz" || true
if [ -f "$SOL_ART/tiny-v12-s0-raw.tar.gz" ]; then tar -xzf "$SOL_ART/tiny-v12-s0-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
printf '%s\n' "$SOL_RC" > "$SOL_ART/tiny-v12-s0-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/tiny-v12-s0 artifacts/sol-translator-20260929/tiny-v12-s0-PC.log artifacts/sol-translator-20260929/tiny-v12-s0-PC.exit
