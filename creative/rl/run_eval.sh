#!/usr/bin/env bash
# Research-loop eval entry point (LOCKED). Usage: bash creative/rl/run_eval.sh dev|holdout SEED [extra args, e.g. --ref job6]
# Runs on the rented GPU box when ~/rl/vast/url exists (creative/rl/remote.py checks the box's locked files match), else locally on CPU.
set -euo pipefail
split="$1"; seed="$2"; shift 2
cd "$(dirname "$0")/../.."
if [ -s "${RL_VAST_DIR:-$HOME/rl/vast}/url" ]; then
  exec python3 creative/rl/remote.py "$split" "$seed" "$@"
fi
PYTHONPATH=. OMP_NUM_THREADS="${RL_THREADS:-4}" exec python3 -m creative.rl.eval_c2 --split "$split" --seed "$seed" --threads "${RL_THREADS:-4}" "$@"
