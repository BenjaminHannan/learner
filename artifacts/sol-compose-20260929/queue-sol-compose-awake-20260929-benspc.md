BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 70 minutes
LABEL: sol-compose-awake-20260929

AWAKE ONLY: zero sleep; original sleep-draft queues must not be submitted.
Owner Sol integrator. Two seeds0/1, six arms, original symbolic-only learned
composition. New ADDENDUM-AWAKE/SPEC-AWAKE/SEAL-AWAKE supersede sleep draft.
Driver cap3600 seconds; total wrapper4200 seconds, below watcher4500 hardcap.
$0, no rentals/downloads/caches. PC disk floor2GiB; one model/optimizer at a time.
No user activity/idle marker prerequisite because this job does NOT sleep.
Watcher owns GPU claim/busy marker. Leave other jobs, claims and apps untouched.
Use only packaged own seal files; no clone, entire review or existing source weights.
Stop on errors; never rerun scored panels or a burned job name. Raw file recount
is a later independent Sol step; no scientific promotion from this job.

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-compose-20260929
SOL_PC=C:/Users/benja/sol-compose-awake-20260929
# Packaging/manifest are built and reviewed before queue submission.
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY'
from pathlib import Path
import shutil
p=Path('C:/Users/benja/sol-compose-awake-20260929')
assert shutil.disk_usage('C:/').free >= 2*1024**3, 'LOW DISK'
p.mkdir(exist_ok=True)
assert not (p/'artifacts/sol-compose-20260929/awake-pc/sol_compose_awake_STARTED.json').exists(), 'DUPLICATE'
PY
scp "$SOL_ART/sol_compose_awake_payload.tar.gz" benspc:"$SOL_PC/payload.tar.gz"
scp "$SOL_ART/sol_compose_awake_PACKAGE.json" benspc:"$SOL_PC/package.json"
set +e
perl -e 'alarm shift; exec @ARGV' 3950 ssh -T -o BatchMode=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PY' 2>&1 | tee "$SOL_ART/sol_compose_awake_PC.log"
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile
root=Path('C:/Users/benja/sol-compose-awake-20260929')
manifest=json.loads((root/'package.json').read_text())
assert hashlib.sha256((root/'payload.tar.gz').read_bytes()).hexdigest()==manifest['sha256'],'PACKAGE HASH'
with tarfile.open(root/'payload.tar.gz') as f:
    for entry in f.getmembers():
        assert not entry.name.startswith('/') and '..' not in Path(entry.name).parts
    f.extractall(root)
os.chdir(root)
import torch
assert torch.cuda.is_available(),'NO CUDA'
print(json.dumps({'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),'scope':'awake only'}),flush=True)
work=root/'artifacts/sol-compose-20260929/awake-pc'
work.mkdir(exist_ok=True)
env=dict(os.environ,SOL_COMPOSE_QUEUE_JOB='sol-compose-awake-20260929',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONUTF8='1')
rc=1
try:
    subprocess.run([sys.executable,'-B','scripts/sol_compose_contracts.py','--out',str(work/'sol_compose_awake_PC-CONTRACT.json')],check=True,env=env,timeout=90)
    job=subprocess.run([sys.executable,'-B','scripts/sol_compose_awake.py','run','--device','cuda','--workdir',str(work)],env=env,timeout=3650)
    rc=job.returncode
finally:
    with tarfile.open(root/'raw-results.tar.gz','w:gz') as archive:
        for p in work.rglob('*'):
            if p.is_file() and p.suffix not in ('.pt','.tmp'):
                archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
    print(json.dumps({'returncode':rc,'raw_sha256':hashlib.sha256((root/'raw-results.tar.gz').read_bytes()).hexdigest()}),flush=True)
sys.exit(rc)
PY
SOL_RC=${PIPESTATUS[0]}
set -e
scp benspc:"$SOL_PC/raw-results.tar.gz" "$SOL_ART/sol_compose_awake_raw-results.tar.gz"
tar -xzf "$SOL_ART/sol_compose_awake_raw-results.tar.gz" -C /Users/ben-hannan/Desktop/projects/beautiful-model
# Weights remain untracked. These two small trained candidates feed joined work.
mkdir -p "$SOL_ART/awake-weights"
for SOL_SEED in 0 1; do
  scp benspc:"$SOL_PC/$SOL_ART/awake-pc/sol_compose_awake_compose-s$SOL_SEED.pt" "$SOL_ART/awake-weights/compose-s$SOL_SEED.pt" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_ART/sol_compose_awake_PC.exit"
exit "$SOL_RC"
```
PUSH: artifacts/sol-compose-20260929/awake-pc artifacts/sol-compose-20260929/sol_compose_awake_PC.log artifacts/sol-compose-20260929/sol_compose_awake_PC.exit
