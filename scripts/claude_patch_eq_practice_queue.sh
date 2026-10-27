#!/bin/bash
# (Already done; kept for the record.) Four practice runs, one thread each, in parallel.
cd /home/user/learner
A=artifacts/claude-patch-eq-20260928/runs
for arm in patch loop_ep; do for seed in 0 1; do
  mkdir -p $A/$arm-s$seed
  nohup python3 -B -u scripts/claude_patch_eq_practice.py --arm $arm --seed $seed --threads 1 --out $A/$arm-s$seed > $A/$arm-s$seed/practice.log 2>&1 &
  echo "$arm-s$seed pid $!"
done; done
