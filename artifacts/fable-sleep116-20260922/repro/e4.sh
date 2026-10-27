#!/bin/sh
# Reproducer for E4 (exp 116): taught rows survive sleep intact (0 overwrites) yet the
# answer still follows the derived rule — override without overwrite.
# Usage: sh repro/e4.sh   (~3 min, Mac CPU, offline)
set -u
ROOT="${1:-scripts/scratchpad/repro116-e4}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_sleep116_drive.py --root "$ROOT" --report "$ROOT/wave-report.json" --only taughtwin \
  2>&1 | grep -E '^E[1234]:'
echo '--- E4 expects BUG (taught Z03 active with 0 overwrites, daemon answers derived H03) ---'
