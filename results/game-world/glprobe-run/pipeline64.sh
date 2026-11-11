#!/bin/bash
# A22 pre-registered follow-up for "anything between": one run at N = 64,000 on seed 200. Starts when the main pipeline (4k, 1k) is done and the data exist.
SP=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad; R=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run; PY=$SP/venv/bin/python; W=$SP/gwl-code64
log() { echo "$(date -u +%FT%TZ) $*" >> $R/progress.log; }
until [ -f $R/DONE ] && grep -q "gen64k done" $R/progress.log; do sleep 60; done
cd $W && export PYTHONPATH=.
D=$R/s200/n64000; mkdir -p $D
log "64k start (code $(git rev-parse --short=10 HEAD))"
[ -f $D/train.json ] || OMP_NUM_THREADS=4 $PY -m game.probe train --parent $R/parents/s200.pt --data $R/data64k --n 64000 --seed 200 --out $D --threads 4 > $D/train.out 2>&1
log "64k train done"
[ -f $D/eval.json ] || OMP_NUM_THREADS=4 $PY -m game.probe eval --ckpt $D/checkpoint.pt --ckpt $R/parents/s200.pt --names student parent --data $R/data64k --train-n 64000 --out $D/eval.json --threads 4 > $D/eval.out 2>&1
log "64k eval done"
[ -f $D/score-sample.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker sample --temp 1.0 --ckpt $D/checkpoint.pt --threads 2 --out $D/score-sample.json > $D/score-sample.out 2>&1 &
[ -f $D/score-top.json ] || OMP_NUM_THREADS=2 $PY -m game.score --arm model --picker top --ckpt $D/checkpoint.pt --threads 2 --out $D/score-top.json > $D/score-top.out 2>&1 &
wait; log "64k score done"; touch $R/DONE64
