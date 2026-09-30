BASH-ONLY: yes
STATUS: READY-FOR-COORDINATOR-RELEASE (template only; do not run here)
GPU: no (bounded Mac CPU fp32 development pilot, $0)
LOAD-LIGHT: no
TIME CAP: 90 minutes
DISK: 1
LABEL: sol-spatial-init512-s01-mac
Owner: Sol spatial. Latest deadline steering reduces the budget to512. No rental,
no holdout, no git operations, no edits to existing files. Stop on first error.
Coordinator copies this exact file to handoff/queue/sol-spatial-init512-s01-mac.md.
Run only after the Mac has a CPU slot. No automatic restart or deletion of run/.
The PC attention job is the main PoC path; this GRU pilot is a diagnostic.
Prerequisites: local review directory and two qualified sources retain sealed hashes;
Python environment exists; coordinator integrates new own scripts/artifacts first.
```bash
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2
SOLPY=/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python
"$SOLPY" -B scripts/sol_spatial_experiment.py check
"$SOLPY" -B scripts/sol_spatial_experiment.py run --queue-file handoff/queue/sol-spatial-init512-s01-mac.md
"$SOLPY" -B scripts/sol_spatial_report.py artifacts/sol-spatial-20260929/run/record.json > artifacts/sol-spatial-20260929/run/report.json
```
PUSH: artifacts/sol-spatial-20260929/run/record.json artifacts/sol-spatial-20260929/run/ledger.json artifacts/sol-spatial-20260929/run/report.json
Weights stay local in run/.pt; serialize all six final weights before queries.
Coordinator needs independent recount from marks/raw predictions, not model rescoring.
