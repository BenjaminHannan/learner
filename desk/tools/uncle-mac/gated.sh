#!/bin/zsh
# Waits for Ben (idle >= 5 min, >= 40 % memory free), takes the lock queue, re-checks inside the lock; if Ben came back
# meanwhile it gives the lock back and waits again. Then e2e + memory measurements.
T=$HOME/learner-ops/uncle-mac/test
ok() { local idle=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'); local free=$(memory_pressure | tail -1 | grep -oE '[0-9]+'); [[ $idle -ge 300 && $free -ge 40 ]]; }
while :; do
  until ok; do sleep 30; done
  echo "$(date +%T) gate open; queueing for the lock" >> $T/e2e.log
  $HOME/learner-ops/bin/realmodel-lock.sh uncle-mac $T/gated-inner.sh
  result=$?
  [[ $result -eq 0 ]] && break
  [[ $result -ne 75 ]] && { echo "$(date +%T) test failed ($result); needs a fix, not a pass" >> $T/e2e.log; exit $result; }
  echo "$(date +%T) gave the lock back (Ben active); waiting again" >> $T/e2e.log
done
