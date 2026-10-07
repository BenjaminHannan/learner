#!/usr/bin/env bash
# Research-loop eval entry point (LOCKED). Usage: bash creative/rl/run_eval.sh dev|holdout SEED [extra args, e.g. --ref job6]
set -euo pipefail
split="$1"; seed="$2"; shift 2
cd "$(dirname "$0")/../.."
PYTHONPATH=. OMP_NUM_THREADS="${RL_THREADS:-4}" exec python3 -m creative.rl.eval_c2 --split "$split" --seed "$seed" --threads "${RL_THREADS:-4}" "$@"
