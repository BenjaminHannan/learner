#!/bin/bash
# GW-L stage 3: the N = 64,000 run on seed 201 (A22 marks need both seeds). Starts when stage 2 (4k, 1k) is done. Resumable.
SP=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad; R=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run; PY=$SP/venv/bin/python; W=$SP/gwl-code65
log() { echo "$(date -u +%FT%TZ) $*" >> $R/progress.log; }
until [ -f $R/DONE ]; do sleep 60; done
cd $W && export PYTHONPATH=.
D=$R/s201/n64000; mkdir -p $D
log "stage3 start: 64k seed 201 (code $(git rev-parse --short=10 HEAD))"
[ -f $D/train.json ] || OMP_NUM_THREADS=4 $PY -m game.probe train --parent $R/parents/s201.pt --data $R/data64k --n 64000 --seed 201 --out $D --threads 4 >> $D/train.out 2>&1
log "64k s201 train done"
[ -f $D/eval.json ] || OMP_NUM_THREADS=4 $PY -m game.probe eval --ckpt $D/checkpoint.pt --ckpt $R/parents/s201.pt --names student parent --data $R/data64k --train-n 64000 --out $D/eval.json --threads 4 > $D/eval.out 2>&1
log "64k s201 eval done"
[ -f $D/score-sample.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker sample --temp 1.0 --ckpt $D/checkpoint.pt --threads 2 --out $D/score-sample.json > $D/score-sample.out 2>&1 &
[ -f $D/score-top.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker top --ckpt $D/checkpoint.pt --threads 2 --out $D/score-top.json > $D/score-top.out 2>&1 &
wait; log "64k s201 score done"; touch $R/DONE201
