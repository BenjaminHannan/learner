#!/bin/bash
# Amendment 2c: T1-long seeds 0-2, one job at a time, started only after the first queue (PID given as $1) has exited.
# Same resume rules as run_queue.sh. Appends to results/queue.log.
cd "$(dirname "$0")" || exit 1
WAIT_PID=$1
export PYTHONPATH=/Users/ben-hannan/tf519
PY=/Users/ben-hannan/ucv4/venv/bin/python
if [ -n "$WAIT_PID" ]; then
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 30; done
fi
for seed in 0 1 2; do
  arm=t1_long; d=results/${arm}_s${seed}
  [ -f $d/results.json ] && { echo "skip $arm s$seed (done)"; continue; }
  mode=""; [ -f $d/model.pt ] && mode="--eval-only"
  echo "$(date +%H:%M:%S) start $arm s$seed $mode"
  $PY run_t.py --arm $arm --seed $seed $mode > results/${arm}_s${seed}.stdout 2>&1 || echo "FAILED $arm s$seed"
  echo "$(date +%H:%M:%S) end $arm s$seed"
done
echo "t1_long queue done"
