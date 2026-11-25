#!/bin/zsh
# Detached waiter: retries run_step6.sh every 60 s while the M3 MPS lock is held by a live pid (exit 8); gives up after 3 h.
S=~/learner-ops/seven-problems-m3/PROBLEM-7/step6; end=$(( $(date +%s) + 10800 ))
while [ $(date +%s) -lt $end ]; do
  $S/run_step6.sh >> $S/waiter.log 2>&1; rc=$?
  [ $rc -ne 8 ] && { echo "run_step6 rc=$rc $(date)" >> $S/waiter.log; exit $rc; }
  sleep 60
done; echo "GAVE UP after 3 h $(date)" >> $S/waiter.log
