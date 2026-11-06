#!/bin/zsh
T=$HOME/learner-ops/uncle-mac/test
idle=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'); free=$(memory_pressure | tail -1 | grep -oE '[0-9]+')
[[ $idle -ge 300 && $free -ge 40 ]] || { echo "$(date +%T) holding lock, waiting for Ben (idle $idle s, free $free %)" >> $T/e2e.log; exit 75; }
[[ -f $T/results.json ]] && mv $T/results.json $T/results-$(date +%s).json
$T/e2e.sh
result=$?
[[ $result -eq 75 ]] && exit 75
[[ $result -eq 0 ]] || { echo "$(date +%T) E2E FAILED" >> $T/e2e.log; exit 1; }
for g in Q4_K_M IQ3_M; do
  f=$HOME/learner-ops/uncle-mac/measure/Nanbeige_Nanbeige4.2-3B-$g.gguf
  [[ -f $f ]] || { echo "missing measurement brain $g" >> $T/e2e.log; exit 1; }
  $T/measure.sh $f $g >> $T/e2e.log 2>&1
  result=$?
  [[ $result -eq 75 ]] && exit 75
  [[ $result -eq 0 ]] || { echo "measurement failed: $g" >> $T/e2e.log; exit 1; }
done
$HOME/learner-ops/node22/bin/node $T/verdict.js || { echo "$(date +%T) RESULT CHECK FAILED" >> $T/e2e.log; exit 1; }
echo "$(date +%T) === all done; see results.json for the checked marks" >> $T/e2e.log
exit 0
