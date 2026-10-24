#!/usr/bin/env bash
# Dopamine-1 (PREREG-dopamine1.md): one GPU, no API key. Run from the repo root.
set -euo pipefail
C="--reward checks --group 1 --tasks-per-step 16 --steps 20 --seed 0"
python -m rlaif.train --eval-only --outdir runs/dopa1/base
for B in none value; do
  python -m rlaif.train $C --baseline $B --outdir runs/dopa1/d_$B
  python -m rlaif.train --eval-only --adapter runs/dopa1/d_$B/adapter_final --outdir runs/dopa1/d_$B
done
grep -h success_rate runs/dopa1/*/eval_*.json || cat runs/dopa1/*/eval_*.json
