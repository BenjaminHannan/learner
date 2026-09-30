BASH-ONLY: yes
GPU: no
LOAD-LIGHT: no
TIME CAP: 66 minutes
LABEL: sol-compose-stop-source-runtimefix
DISK: 1

Runtime-only successor to sol-stop-readiness-source-v2, which failed before Python/inputs/optimizer because /usr/local/bin/python3 has incompatible CPU architecture. Original queue/spec/marks/code preserved. Existing readiness-source-v2 output does not exist; no evaluation occurred. Same exact protocol/source checkpoints and presealed marks/noise recipe; no sleep or English qualification. CPU1 $0. 3600s driver,3950s process cap,4500s watcher cap. uv cached Python3.12 torch+numpy verified; no install/download. Raw frozen-input labels/masks and ordered prediction arrays are bound by SOURCE-v2-ROWBINDING-ADDENDUM.json. No rescore/resume after output reservation.
PUSH: artifacts/sol-stop-20260929/readiness-source-v2

```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
SOL_CPU_UV=/Users/ben-hannan/.local/bin/uv
test ! -e artifacts/sol-stop-20260929/readiness-source-v2
"$SOL_CPU_UV" run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/sol_stop_readiness_v2.py --phase source
perl -e 'alarm shift; exec @ARGV' 3950 "$SOL_CPU_UV" run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/sol_stop_readiness_v2.py --phase source --run --out artifacts/sol-stop-20260929/readiness-source-v2
```
