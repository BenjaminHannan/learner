#!/bin/sh
# Reproducer for E3 (exp 116): same taught-override shape on the second test chain (Z02 vs H02).
# Usage: sh repro/e3.sh   (~3 min, Mac CPU, offline)
set -u
ROOT="${1:-scripts/scratchpad/repro116-e3}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_sleep116_drive.py --root "$ROOT" --report "$ROOT/wave-report.json" --only taughtwin \
  2>&1 | grep -E '^E[1234]:'
echo '--- E3 expects BUG (taught Z02 active, daemon answers derived H02) ---'
