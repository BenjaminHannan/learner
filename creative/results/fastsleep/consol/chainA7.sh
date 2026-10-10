#!/bin/bash
# Screen A, strictly 2 runs at once (a third pushed the cgroup, limit 13.4 GiB, to its limit at the update-32/64 checks).
# Order: s202 rlc, s201 rlc (nights cached), rp s202, rp s201 (batch 512).
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=1
run() { python3 -m creative.consol run --parent-dir ~/rl/parents/$1 --out ~/consol/A/$1 --arm $2 --updates 128 --seed 0 --threads 1 --micro 128 --check-every 32 --save-at 32,64,128 ${3:+--batch $3} >> ~/consol/A-$1-$2.log 2>&1; echo "A $1 $2 rc=$?" >> ~/consol/chainA.txt; }
slot() { while [ $(ps -eo args | grep -c "[c]reative.consol run") -gt $1 ]; do sleep 60; done; }
slot 1; echo "--- chainA7 $(date -u +%H:%M)" >> ~/consol/A-s202-rlc.log; run s202 rlc & sleep 120
slot 1; echo "--- chainA7 $(date -u +%H:%M)" >> ~/consol/A-s201-rlc.log; run s201 rlc & sleep 120
slot 1; echo "--- chainA7 $(date -u +%H:%M)" >> ~/consol/A-s202-rp.log; run s202 rp 512 & sleep 120
slot 1; echo "--- chainA7 $(date -u +%H:%M)" >> ~/consol/A-s201-rp.log; run s201 rp 512 &
wait
echo "CHAINA done" >> ~/consol/chainA.txt
