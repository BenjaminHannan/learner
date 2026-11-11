#!/bin/bash
# GW-L, second stage (A22 "anything between" + L-3). Idempotent and resumable (probe train keeps resume.pt). Order: N=64,000 seed 200 alone on 4 threads, then N=4,000 and 1,000 for both seeds.
SP=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad; R=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run; PY=$SP/venv/bin/python; W=$SP/gwl-code65
cd $W && export PYTHONPATH=.
log() { echo "$(date -u +%FT%TZ) $*" >> $R/progress.log; }
log "stage2 start (code $(git rev-parse --short=10 HEAD))"
D=$R/s200/n64000; mkdir -p $D
[ -f $D/train.json ] || OMP_NUM_THREADS=4 $PY -m game.probe train --parent $R/parents/s200.pt --data $R/data64k --n 64000 --seed 200 --out $D --threads 4 >> $D/train.out 2>&1
log "64k train done"
[ -f $D/eval.json ] || OMP_NUM_THREADS=4 $PY -m game.probe eval --ckpt $D/checkpoint.pt --ckpt $R/parents/s200.pt --names student parent --data $R/data64k --train-n 64000 --out $D/eval.json --threads 4 > $D/eval.out 2>&1
log "64k eval done"
[ -f $D/score-sample.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker sample --temp 1.0 --ckpt $D/checkpoint.pt --threads 2 --out $D/score-sample.json > $D/score-sample.out 2>&1 &
[ -f $D/score-top.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker top --ckpt $D/checkpoint.pt --threads 2 --out $D/score-top.json > $D/score-top.out 2>&1 &
wait; log "64k score done"; touch $R/DONE64
for N in 4000 1000; do
  for s in 200 201; do
    D=$R/s$s/n$N; mkdir -p $D
    [ -f $D/train.json ] || ( OMP_NUM_THREADS=2 $PY -m game.probe train --parent $R/parents/s$s.pt --data $R/data --n $N --seed $s --out $D --threads 2 >> $D/train.out 2>&1 ) &
  done
  wait; log "train n=$N done"
  for s in 200 201; do
    D=$R/s$s/n$N
    [ -f $D/eval.json ] || OMP_NUM_THREADS=2 $PY -m game.probe eval --ckpt $D/checkpoint.pt --names student --data $R/data --train-n $N --out $D/eval.json --threads 2 > $D/eval.out 2>&1 &
  done
  wait; log "eval n=$N done"
  for s in 200 201; do
    D=$R/s$s/n$N
    [ -f $D/score-sample.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker sample --temp 1.0 --ckpt $D/checkpoint.pt --threads 2 --out $D/score-sample.json > $D/score-sample.out 2>&1 &
  done
  wait; log "score n=$N done"
done
log "ALL DONE"; touch $R/DONE
