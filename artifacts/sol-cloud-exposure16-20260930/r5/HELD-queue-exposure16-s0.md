STATUS: HELD
BASH-ONLY: yes
LOAD-LIGHT: yes
GPU: yes
TIME CAP: 10 minutes
LABEL: sol-cloud-exposure16-v1-s0-pc

CONDITIONALLY RELEASED by Derek only after independentreviewPASS and actual
bridgecomplete, fresh inventory and resourcepreflight. Do not copy this held
template into a live queue until conditions are met. Seeds execute serially.
Existing V11 checkpoint tuple and frozen FP32 LM are reused without copies.
Fresh PC disk/GPU/process inventory, closure evidence and reviewed release pins
must be supplied by the designated integrator. This template alone authorizes no launch.

```bash
set -euo pipefail
: "${SOL_APPROVED_PC_TREE:?released delivery tree required}"
: "${SOL_APPROVED_RELEASE:?reviewed release path required}"
: "${SOL_APPROVED_RELEASE_SHA256:?reviewed release digest required}"
: "${SOL_FRESH_INVENTORY:?fresh inventory path required}"
: "${SOL_FRESH_INVENTORY_SHA256:?fresh inventory digest required}"
perl -e 'alarm shift; exec @ARGV' 600 ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc \
  "C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -B $SOL_APPROVED_PC_TREE/scripts/sol_cloud_exposure16_v5.py --seed 0 --release $SOL_APPROVED_RELEASE --release-sha256 $SOL_APPROVED_RELEASE_SHA256 --inventory $SOL_FRESH_INVENTORY --inventory-sha256 $SOL_FRESH_INVENTORY_SHA256"
```

Delivery, watcher environment, unique claim/exit receipts, timeout termination,
evidence collection and hash-verified archive are integrator release duties.
This held template is not a standalone transport or live watcher release.
