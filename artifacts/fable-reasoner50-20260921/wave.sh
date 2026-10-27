#!/usr/bin/env bash
# Experiment 50 registered wave: parity/scale (one deterministic run) + 3 sleep seeds.
# Sequential: at most one process at a time, one thread each.  ~10-15 min wall-clock.
set -euo pipefail
cd "$(dirname "$0")/../.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=(uv run --offline --no-project --python 3.12 --with torch --with numpy python -B)
OUT=artifacts/fable-reasoner50-20260921/runs
LOGS=artifacts/fable-reasoner50-20260921/logs
mkdir -p "$OUT" "$LOGS"

"${PY[@]}" scripts/fable_reasoner50.py --stage selftest | tee "$LOGS/selftest.log"
"${PY[@]}" scripts/fable_reasoner50.py --stage scale --tag reg --questions 300 --out "$OUT" \
  | tee "$LOGS/scale.log"
for seed in 4131 4132 4133; do
  "${PY[@]}" scripts/fable_reasoner50.py --stage sleep --seed "$seed" --out "$OUT" \
    | tee "$LOGS/sleep-$seed.log"
done
"${PY[@]}" scripts/fable_reasoner50.py --stage score --out "$OUT" | tee "$LOGS/score.log"
