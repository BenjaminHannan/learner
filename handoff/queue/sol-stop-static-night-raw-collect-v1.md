BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: no
DISK: 1
LOWDISK-OK: yes
TIME CAP: 3 minutes
LABEL: sol-stop-static-night-raw-collect-v1

ARTIFACT DRAFT, collection-only. James reviews/publishes when authorized; no
live queue submitted by STOP. Preserve completed static25; NEVER rerun inference,
receipt writer, optimizer or sleep. The local night archive has receipt/binding
JSON but omits the two referenced numeric probe .pt files. Collect the exact PC
originals without changing them. If missing or hashes differ, retain failure;
do not recreate raw. This is no new release gate or qualification.

Three files only: existing receipt + raw-probe-0.pt + raw-probe-1.pt. No checkpoint,
LM, training text, panel, stop88 or DEV data. No model imports. Outer150s;
64MiB post-collection cap; 128MiB local free-space prerequisite. All exact pins
are in STATIC-NIGHT-RAW-COLLECTION-SPEC-v1.json, SHA below.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 150 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1
SOL_OUT="$SOL_ART/static-night-raw-collected-v1"
SOL_PC=C:/Users/benja/sol-compose-night-v2-s0/artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0/actual
python3 -B - <<'PY'
from pathlib import Path
import hashlib,shutil
p=Path('artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1')
assert hashlib.sha256((p/'STATIC-NIGHT-RAW-COLLECTION-SPEC-v1.json').read_bytes()).hexdigest()=='c9a5e0e3f48200943fa2af4f312c0c560f0fe0ac8ad90e64a140093632557e5d'
assert shutil.disk_usage(p).free>=128*1024**2,'128MiB local floor'
assert not (p/'static-night-raw-collected-v1').exists(),'NEW output required; preserve failed run'
PY
mkdir "$SOL_OUT"
for SOL_FILE in receipt.json raw-probe-0.pt raw-probe-1.pt; do
 scp -o BatchMode=yes -o ConnectTimeout=15 benspc:"$SOL_PC/$SOL_FILE" "$SOL_OUT/$SOL_FILE"
done
python3 -B - <<'PY'
from pathlib import Path
import hashlib,json
p=Path('artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1');out=p/'static-night-raw-collected-v1'
spec=json.loads((p/'STATIC-NIGHT-RAW-COLLECTION-SPEC-v1.json').read_text());records=[]
for pin in [spec['receipt'],*spec['raw_probes']]:
 local=out/pin['path'].rsplit('/',1)[-1];digest=hashlib.sha256(local.read_bytes()).hexdigest()
 assert digest==pin['sha256'],'COPY HASH '+str(local)
 records.append({'path':str(local),'sha256':digest,'bytes':local.stat().st_size})
assert sum(r['bytes'] for r in records)<=64*1024**2,'64MiB collection cap'
report={'scope':'Exact-byte collection only; originals preserved','records':records,'file_hash_checks_passed':3,'models_executed':0,'optimizer_updates':0,'sleep_repeated':False,'stage_proof_status':'NOT SHOWN'}
with (out/'COLLECTION.json').open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
PY
SOL_JOB
```

PUSH: artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/static-night-raw-collected-v1
