#!/bin/bash
# Sequential, resumable queue for the Amendment 2 runs (one job at a time: three at once panicked the Mac).
# A run with results.json is skipped; one with model.pt but no results.json is only evaluated; otherwise trained.
cd "$(dirname "$0")" || exit 1
export PYTHONPATH=/Users/ben-hannan/tf519
PY=/Users/ben-hannan/ucv4/venv/bin/python
PRE=/Users/ben-hannan/talker_gap_cache/fineweb/pre
JOBS="t1:0 t1:1 t1:2 t1_nothinker:0 t1_nothinker:1 t1_nothinker:2 t2:0 t2:1 t2:2"
for job in $JOBS; do
  arm=${job%%:*}; seed=${job##*:}; d=results/${arm}_s${seed}
  [ -f $d/results.json ] && { echo "skip $arm s$seed (done)"; continue; }
  extra=""; [ "$arm" = t2 ] && extra="--pretrain-dir $PRE --pretrain-steps 3000"
  mode=""; [ -f $d/model.pt ] && mode="--eval-only"
  echo "$(date +%H:%M:%S) start $arm s$seed $mode"
  $PY run_t.py --arm $arm --seed $seed $extra $mode > results/${arm}_s${seed}.stdout 2>&1 || echo "FAILED $arm s$seed"
  echo "$(date +%H:%M:%S) end $arm s$seed"
done
echo "queue done"
