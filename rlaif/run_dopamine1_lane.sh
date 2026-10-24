#!/usr/bin/env bash
# One Dopamine-1 lane (one GPU). Usage: run_dopamine1_lane.sh OUTROOT ARM [ARM ...]; ARM = base | none | value | self.
# Kaggle T4: DTYPE=fp16 (default here). PC: DTYPE=bf16.
set -euo pipefail
R=$1; shift; D=${DTYPE:-fp16}
C="--reward checks --group 1 --tasks-per-step 16 --steps 20 --seed 0 --gen-batch 8 --dtype $D"
for B in "$@"; do
  if [ "$B" = base ]; then python -m rlaif.train --eval-only --eval-predict --dtype $D --gen-batch 8 --outdir $R/base; continue; fi
  python -m rlaif.train $C --baseline $B --outdir $R/d_$B
  python -m rlaif.train --eval-only --dtype $D --gen-batch 8 --adapter $R/d_$B/adapter_final --outdir $R/d_$B
  rm -rf $R/d_$B/adapter_step*
done
