#!/usr/bin/env python3
"""Create new reviewable watcher packets; no GPU or optimization."""
from pathlib import Path
import ast,hashlib,json,subprocess,tarfile,time
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'artifacts/sol-translator-20260929';REL=O.relative_to(ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
 for key in ('FOLLOWUP-V7-SEAL.json','translator-followup-v7-payload.tar.gz'):
  if (O/key).exists():raise RuntimeError('preserve seal/package; NEW version required')
 base=json.loads((O/'DEPLOYMENT-V6-SEAL.json').read_text())
 files={k:v for k,v in base['files'].items() if not k.endswith('.pt') and '/queue-' not in k}
 for k,v in files.items():assert sha(ROOT/k)==v,'base changed '+k
 files.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts').glob('sol_translator_*v7.py')})
 for n in ('sol_translator_proof_v6.py','sol_translator_proof_contracts_v6.py','sol_translator_language_proof.py'):
  p=ROOT/'scripts'/n;files[str(p.relative_to(ROOT))]=sha(p)
 for n in ('DIAGNOSTIC-V7-PLAN.json','PREFIX-TRAIN-V7-PLAN.json','RUNTIME-PREFIX-SELECTION-V7.json','PREFIX-TRAIN-V7-BINDING-s0.json','PREFIX-TRAIN-V7-BINDING-s1.json','FROZEN-V6-CONTRACTS.json'):
  p=O/n;files[str(p.relative_to(ROOT))]=sha(p)
 # CLOSED tuple snapshots are held locally; PC reads old closed weights in place,
 # their digests pinned in new binding, avoiding 74MB duplicate parent files.
 tasks=[('diagnostic',s,0,'loop') for s in (0,1)]+[('prefix',s,d,a) for a in ('loop','no_state','embedding','untrained','shuffled_state') for s in (0,1) for d in (0,1)]
 for mode,seed,dseed,arm in tasks:
  label=f'sol-translator-{mode}-v7-s{seed}'+(f'-d{dseed}-{arm}' if mode=='prefix' else '')+'-pc'
  out=f'diagnostic-v7-s{seed}' if mode=='diagnostic' else f'prefix-v7-s{seed}-d{dseed}-{arm}'
  cap=1200 if mode=='diagnostic' else 3950
  header=f'BASH-ONLY: yes\nLOAD-LIGHT: yes\nGPU: yes\nDISK: 1\nLOWDISK-OK: yes\nTIME CAP: {20 if mode=="diagnostic" else 66} minutes\nLABEL: {label}\n\nREADY sealed TRAIN-only; no DEV/stop/sleep. Closed source tuple pinned.\nRead cached FP32 LFM and CLOSED parent/reader in place; no downloads/copies.\n1GiB free floor,256MiB aggregate new outputs. Queues serialized by watcher.\nPlain human parent not yet available; no plain comparison claimed.\nRuntime prefix selection predeclared loop/source0+1/decoder0 before DEV.\n\n```bash\n'
  script=f'''set -euo pipefail
perl -e 'alarm shift; exec @ARGV' {cap} bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-translator-20260929
SOL_PC=C:/Users/benja/sol-translator-followup-v7
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -' <<'PY'
from pathlib import Path
import shutil
p=Path('C:/Users/benja/sol-translator-followup-v7')
assert shutil.disk_usage('C:/').free>=1024**3,'DISK FLOOR'
p.mkdir(exist_ok=True)
assert not (p/'artifacts/sol-translator-20260929/{out}/TRANSPORT-LAUNCH.json').exists(),'DUPLICATE; new version/resume job needed'
PY
scp "$SOL_ART/translator-followup-v7-payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/FOLLOWUP-V7-PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -' <<'PY' 2>&1 | tee "$SOL_ART/{out}-PC.log"
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,sys,tarfile
r=Path('C:/Users/benja/sol-translator-followup-v7')
m=json.loads((r/'package.json').read_text())
assert hashlib.sha256((r/'payload.tar.gz').read_bytes()).hexdigest()==m['sha256'],'PACKAGE HASH'
with tarfile.open(r/'payload.tar.gz') as t:
 for x in t.getmembers():assert x.isfile() and not x.name.startswith('/') and '..' not in Path(x.name).parts,'UNSAFE PACKAGE'
 t.extractall(r)
os.chdir(r);sys.path[:0]=[str(r),str(r/'scripts')]
from sol_translator_followup_deploy_v7 import run
sys.exit(run(SimpleNamespace(root=str(r),seed={seed},decoder_seed={dseed},arm='{arm}',mode='{mode}',job='{label}')))
PY
SOL_RC=${{PIPESTATUS[0]}}
set -e
scp benspc:"$SOL_PC/{out}-raw.tar.gz" "$SOL_ART/{out}-raw.tar.gz" || true
if [ -f "$SOL_ART/{out}-raw.tar.gz" ]; then tar -xzf "$SOL_ART/{out}-raw.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model; fi
'''
  if mode=='prefix':script+=f'mkdir -p "$SOL_ART/{out}"\nscp benspc:"$SOL_PC/$SOL_ART/{out}/English.pt" "$SOL_ART/{out}/English.pt" || true\n'
  script+=f'''printf '%s\\n' "$SOL_RC" > "$SOL_ART/{out}-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-translator-20260929/{out} artifacts/sol-translator-20260929/{out}-PC.log artifacts/sol-translator-20260929/{out}-PC.exit
'''
  q=O/f'queue-{label}.md';q.write_text(header+script)
  check=subprocess.run(['bash','-n'],input=script.split('```')[0],text=True,capture_output=True)
  assert check.returncode==0,check.stderr
  files[str(q.relative_to(ROOT))]=sha(q)
 for path in files:
  if path.endswith('.py'):ast.parse((ROOT/path).read_text())
 seal={'sealed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'stage':'PRE-RUN TRAIN-only diagnostic + frozen-prefix adapter TRAIN, no DEV ever in this package','files':files,'closed_source_seeds':[0,1],'queues':len(tasks),'precision':'FULL FP32 frozen LFM/readers/core; only prefix optimizer','controls':'same bootstrap untouched diagnostic; then separately trained thin prefixes for all controls','noise':'INSUFFICIENT for scientific promotion; decoder two init/sampling replicas planned','DEV_examples':0,'sleep_updates':0,'tests':'7/7 numeric frozen mechanics; syntax/all queue bash checks only, CUDA generation not yet run'}
 sp=O/'FOLLOWUP-V7-SEAL.json';sp.write_text(json.dumps(seal,indent=2)+'\n')
 payload=O/'translator-followup-v7-payload.tar.gz'
 with tarfile.open(payload,'w:gz') as t:
  for name in sorted(files):t.add(ROOT/name,arcname=name,recursive=False)
  t.add(sp,arcname=str(sp.relative_to(ROOT)),recursive=False)
 result={'sha256':sha(payload),'bytes':payload.stat().st_size,'seal_sha256':sha(sp),'members':len(files)+1,'source_pins':len(files),'queues':len(tasks),'closed_weights':'PC old CLOSED root read in place; exact hashes bound, no binary/LM cache duplication'}
 (O/'FOLLOWUP-V7-PACKAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':build()
