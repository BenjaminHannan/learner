#!/bin/bash
# Screen A, memory-safe: sleeps are flat at 3.8-4.0 GB each (cgroup limit 13.4 GiB). Pending: s201 rlc (night cached) when <= 2 runs; rp (batch 512, ~3 GB) when <= 2 runs.
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=1
run() { python3 -m creative.consol run --parent-dir ~/rl/parents/$1 --out ~/consol/A/$1 --arm $2 --updates 128 --seed 0 --threads 1 --micro 128 --check-every 32 --save-at 32,64,128 ${3:+--batch $3} >> ~/consol/A-$1-$2.log 2>&1; echo "A $1 $2 rc=$?" >> ~/consol/chainA.txt; }
slot() { while [ $(ps -eo args | grep -c "[c]reative.consol run") -gt $1 ]; do sleep 60; done; }
slot 2; echo "--- chainA6 $(date -u +%H:%M)" >> ~/consol/A-s201-rlc.log; run s201 rlc & sleep 120
slot 2; echo "--- chainA6 $(date -u +%H:%M)" >> ~/consol/A-s202-rp.log; run s202 rp 512 & sleep 120
slot 2; echo "--- chainA6 $(date -u +%H:%M)" >> ~/consol/A-s201-rp.log; run s201 rp 512 &
wait
echo "CHAINA done" >> ~/consol/chainA.txt
