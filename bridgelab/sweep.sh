#!/bin/bash
# Full sweep: 5 arms x 3 seeds, 4 processes in parallel (1 thread each). Usage: bash bridgelab/sweep.sh [steps]
cd "$(dirname "$0")/.." || exit 1
STEPS=${1:-8000}
for s in 0 1 2; do for a in none ema_const pooled xattn slots; do echo "$a $s"; done; done |
  xargs -P4 -L1 bash -c 'python -m bridgelab.run --arm $0 --seed $1 --steps '"$STEPS"' > bridgelab/results/log_$0_s$1.txt 2>&1'
python -m bridgelab.summarize
