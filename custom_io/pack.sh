#!/usr/bin/env bash
# Run many train.py jobs concurrently on one GPU.
#   custom_io/pack.sh JOBS_FILE [LOG_DIR]       (LOG_DIR default: ./pack_logs)
# JOBS_FILE: one shell command per line (blank lines and #comments skipped), e.g.
#   python3 -m custom_io.train --model plain_tf --steps 3000 --final-eval --out runs/a
# Each job runs from the repo root with PYTHONPATH set, logs to LOG_DIR/job_NN.log. Exit 1 if any job failed.
set -u
JOBS=${1:?usage: pack.sh JOBS_FILE [LOG_DIR]}
JOBS=$(realpath "$JOBS"); LOGS=${2:-pack_logs}; mkdir -p "$LOGS"; LOGS=$(realpath "$LOGS")
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"; export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
mapfile -t CMDS < <(grep -vE '^\s*(#|$)' "$JOBS")
# split CPU threads between jobs so dataloading/collation does not oversubscribe the box
export OMP_NUM_THREADS=$(( $(nproc) / ${#CMDS[@]} > 0 ? $(nproc) / ${#CMDS[@]} : 1 ))
PIDS=()
for i in "${!CMDS[@]}"; do
  log=$(printf '%s/job_%02d.log' "$LOGS" "$i")
  echo "[pack] job $i -> $log: ${CMDS[$i]}"
  bash -c "${CMDS[$i]}" > "$log" 2>&1 &
  PIDS+=($!)
done
fail=0
for i in "${!PIDS[@]}"; do
  if wait "${PIDS[$i]}"; then echo "[pack] job $i ok"; else echo "[pack] job $i FAILED (see $LOGS)"; fail=1; fi
done
exit $fail
