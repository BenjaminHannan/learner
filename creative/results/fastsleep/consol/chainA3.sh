#!/bin/bash
# Screen A, memory-safe (cgroup limit 14.3 GB): s201's night only after s200's rebuild ends; the two fd runs after s201's night; ro after the rlc runs.
cd /home/user/learner
export PYTHONPATH=/home/user/learner OMP_NUM_THREADS=1
run() { python3 -m creative.consol run --parent-dir ~/rl/parents/$1 --out ~/consol/A/$1 --arm $2 --updates 128 --seed 0 --threads 1 --micro 128 --check-every 32 --save-at 32,64,128 >> ~/consol/A-$1-$2.log 2>&1; echo "A $1 $2 rc=$?" >> ~/consol/chainA.txt; }
until [ -s ~/rl/parents/s200/setup.pt ]; do sleep 30; done
run s201 rlc &
until [ -s ~/consol/A/s201/finds.pkl ]; do sleep 30; done
sleep 120
run s201 fd &
run s202 fd &
until grep -q "A s202 rlc rc=" ~/consol/chainA.txt; do sleep 60; done
run s202 ro
until grep -q "A s201 rlc rc=" ~/consol/chainA.txt; do sleep 60; done
run s201 ro
wait
echo "CHAINA done" >> ~/consol/chainA.txt
