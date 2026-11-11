#!/bin/bash
# GW-L pipeline (A22). Idempotent: every step skips if its output exists. Code frozen at the worktree (commit a3e57da490).
SP=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad
W=$SP/gwl-code; R=$SP/glprobe/run; PY=$SP/venv/bin/python
cd $W && export PYTHONPATH=.
log() { echo "$(date -u +%FT%TZ) $*" >> $R/progress.log; }
git -C $W rev-parse HEAD > $R/code-commit.txt
log "start"

# 1. data
if [ ! -f $R/data/gen.json ]; then
  OMP_NUM_THREADS=3 $PY -m game.probe gen --out $R/data > $R/gen.out 2>&1; log "gen done"
fi

# 2. the labeller's own sealed score (the ceiling under this act rule)
if [ ! -f $R/score-oracle.json ]; then
  OMP_NUM_THREADS=3 $PY -m game.score --arm oracle --threads 3 --out $R/score-oracle.json > $R/score-oracle.out 2>&1; log "oracle sealed done"
fi

# 3. per N: train both seeds in parallel (2 threads each), eval, sealed score (sampled T=1; top too at N=16000)
for N in 16000 4000 1000; do
  for s in 200 201; do
    D=$R/s$s/n$N; mkdir -p $D
    if [ ! -f $D/train.json ]; then
      ( OMP_NUM_THREADS=2 $PY -m game.probe train --parent $R/parents/s$s.pt --data $R/data --n $N --seed $s --out $D --threads 2 > $D/train.out 2>&1 ) &
    fi
  done
  wait; log "train n=$N done"
  for s in 200 201; do
    D=$R/s$s/n$N
    if [ ! -f $D/eval.json ]; then
      if [ $N = 16000 ]; then
        OMP_NUM_THREADS=2 $PY -m game.probe eval --ckpt $D/checkpoint.pt --ckpt $R/parents/s$s.pt --ckpt $R/parents/gwp8-s$s.pt --names student parent gwp8_night8 --data $R/data --train-n $N --out $D/eval.json --threads 2 > $D/eval.out 2>&1 &
      else
        OMP_NUM_THREADS=2 $PY -m game.probe eval --ckpt $D/checkpoint.pt --names student --data $R/data --train-n $N --out $D/eval.json --threads 2 > $D/eval.out 2>&1 &
      fi
    fi
  done
  wait; log "eval n=$N done"
  for s in 200 201; do
    D=$R/s$s/n$N
    if [ ! -f $D/score-sample.json ]; then
      OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker sample --temp 1.0 --ckpt $D/checkpoint.pt --threads 2 --out $D/score-sample.json > $D/score-sample.out 2>&1 &
    fi
  done
  wait; log "score sample n=$N done"
  if [ $N = 16000 ]; then
    for s in 200 201; do
      D=$R/s$s/n$N
      if [ ! -f $D/score-top.json ]; then
        OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker top --ckpt $D/checkpoint.pt --threads 2 --out $D/score-top.json > $D/score-top.out 2>&1 &
      fi
    done
    wait; log "score top n=$N done"
  fi
done
log "ALL DONE"; touch $R/DONE
