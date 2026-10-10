#!/bin/bash
# fd rerun on a 256-update schedule (MARKS.md, after Screen A): saves 128/192/256. Each starts when that parent's rp run has finished (2 runs at once at most).
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=1
run() { python3 -m creative.consol run --parent-dir ~/rl/parents/$1 --out ~/consol/A256/$1 --arm fd --updates 256 --seed 0 --threads 1 --micro 128 --check-every 32 --save-at 128,192,256 >> ~/consol/B-$1-fd256.log 2>&1; echo "B $1 fd256 rc=$?" >> ~/consol/chainA.txt; }
for p in s202 s201; do
  ( until grep -q "A $p rp rc=" ~/consol/chainA.txt; do sleep 60; done; run $p ) &
done
wait
echo "CHAINB done" >> ~/consol/chainA.txt
