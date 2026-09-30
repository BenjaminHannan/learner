BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 12 minutes
LABEL: sol-assistant-freeze-v6-s0-pc-v1

James publishes. READY on closed V6s0 TRANSPORT-RESULT rc0. GPU marker serializes with
seed1; this job uses CPU only, NO training/inference/eval. Max700s outer alarm.
Hardlink all .pt on same PC volume, no optimizer or LM copy. Hash frozen source and
actual full tuple against final transport+last DURABLE. No stop/sleep promotion.
Do not rerun an existing target; failed evidence retained, successor NEW path required.

```bash
set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 700 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
SOL_ART=artifacts/sol-assistant-20260930
SOL_PC=C:/Users/benja/sol-translator-human-v6
scp "$SOL_ART/freeze-v1.tar.gz" benspc:"$SOL_PC/assistant-freeze-v1.tar.gz"
scp "$SOL_ART/freeze-v1-package.json" benspc:"$SOL_PC/assistant-freeze-v1-package.json"
scp artifacts/sol-translator-20260929/ground-v6-s0-PC.log benspc:"$SOL_PC/assistant-v6-s0-stdout.log"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/freeze-v6-s0-PC.log"
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile
root=Path('C:/Users/benja/sol-translator-human-v6');os.chdir(root)
m=json.loads((root/'assistant-freeze-v1-package.json').read_text())
assert hashlib.sha256((root/'assistant-freeze-v1.tar.gz').read_bytes()).hexdigest()==m['archive_sha256']
assert m['archive_sha256']=='5c50cc33bf85d83e8bad872b3a542c7b168f0bee3e34434f5eced3c8ca297c44'
with tarfile.open(root/'assistant-freeze-v1.tar.gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in m['files'] and member.name.startswith('scripts/sol_assistant_')
  p=root/member.name
  if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][member.name],'existing assistant file differs; preserve it'
 tar.extractall(root)
for name,expected in m['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
command=[sys.executable,'-B','scripts/sol_assistant_freeze.py','--run','artifacts/sol-translator-20260929/ground-v6-s0','--seed','0','--stdout','assistant-v6-s0-stdout.log','--model','C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b','--out','artifacts/sol-assistant-20260930/frozen-v6-s0-u500']
env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
sys.exit(subprocess.run(command,env=env,timeout=600).returncode)
PYREMOTE
SOL_RC=${PIPESTATUS[0]}
set -e
mkdir -p "$SOL_ART/freeze-v6-s0-receipts"
for SOL_NAME in bundle.json freeze-receipt.json; do
 scp benspc:"$SOL_PC/$SOL_ART/frozen-v6-s0-u500/$SOL_NAME" "$SOL_ART/freeze-v6-s0-receipts/$SOL_NAME" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_ART/freeze-v6-s0-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-assistant-20260930/freeze-v6-s0-PC.log artifacts/sol-assistant-20260930/freeze-v6-s0-PC.exit artifacts/sol-assistant-20260930/freeze-v6-s0-receipts
