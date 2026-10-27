#!/bin/sh
# Reproducer for E2 (exp 116): taught maternal_grandmother fact overridden by sleep-derived inference.
# Replays the sealed taughtwin scenario via the real Sleep104Daemon mailbox and checks E2.
# Usage: sh repro/e2.sh   (~3 min, Mac CPU, offline)
set -u
ROOT="${1:-scripts/scratchpad/repro116-e2}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
  scripts/fable_sleep116_drive.py --root "$ROOT" --report "$ROOT/wave-report.json" --only taughtwin \
  2>&1 | grep -E '^E[1234]:'
echo '--- E2 expects BUG (taught Z01 active, daemon answers derived H01) ---'
