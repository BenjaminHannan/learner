BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
DISK: 1
LOWDISK-OK: yes
TIME CAP: 12 minutes
LABEL: sol-assistant-freeze-v6-s0-pc-v2

Supersedes failed v1 UTF-8 decoding only; original files/failure preserved.
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
scp "$SOL_ART/freeze-v2.tar.gz" benspc:"$SOL_PC/assistant-freeze-v2.tar.gz"
scp "$SOL_ART/freeze-v2-package.json" benspc:"$SOL_PC/assistant-freeze-v2-package.json"
scp artifacts/sol-translator-20260929/ground-v6-s0-PC.log benspc:"$SOL_PC/assistant-v6-s0-stdout.log"
set +e
ssh -T -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=20 benspc 'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -' <<'PYREMOTE' 2>&1 | tee "$SOL_ART/freeze-v6-s0-r2-PC.log"
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile
root=Path('C:/Users/benja/sol-translator-human-v6');os.chdir(root)
m=json.loads((root/'assistant-freeze-v2-package.json').read_text(encoding='utf-8'))
assert hashlib.sha256((root/'assistant-freeze-v2.tar.gz').read_bytes()).hexdigest()==m['archive_sha256']
assert m['archive_sha256']=='3ca98b312a1d69096db72bb4f3422970ee6b5fff997a9a53e75cbbce83198e0c'
with tarfile.open(root/'assistant-freeze-v2.tar.gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and member.name in m['files'] and member.name.startswith('scripts/sol_assistant_')
  p=root/member.name
  if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][member.name],'existing assistant file differs; preserve it'
 tar.extractall(root)
for name,expected in m['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
base=json.loads((root/'assistant-freeze-v1-package.json').read_text(encoding='utf-8'))
assert base['archive_sha256']==m['base_package_sha256']
for name,h in base['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h
command=[sys.executable,'-X','utf8','-B','scripts/sol_assistant_freeze_v2.py','--run','artifacts/sol-translator-20260929/ground-v6-s0','--seed','0','--stdout','assistant-v6-s0-stdout.log','--model','C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b','--out','artifacts/sol-assistant-20260930/frozen-v6-s0-u500-r2']
env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),PYTHONUTF8='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
sys.exit(subprocess.run(command,env=env,timeout=600).returncode)
PYREMOTE
SOL_RC=${PIPESTATUS[0]}
set -e
mkdir -p "$SOL_ART/freeze-v6-s0-r2-receipts"
for SOL_NAME in bundle.json freeze-receipt.json; do
 scp benspc:"$SOL_PC/$SOL_ART/frozen-v6-s0-u500-r2/$SOL_NAME" "$SOL_ART/freeze-v6-s0-r2-receipts/$SOL_NAME" || true
done
printf '%s\n' "$SOL_RC" > "$SOL_ART/freeze-v6-s0-r2-PC.exit"
exit "$SOL_RC"
SOL_JOB
```
PUSH: artifacts/sol-assistant-20260930/freeze-v6-s0-r2-PC.log artifacts/sol-assistant-20260930/freeze-v6-s0-r2-PC.exit artifacts/sol-assistant-20260930/freeze-v6-s0-r2-receipts
