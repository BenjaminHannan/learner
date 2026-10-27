#!/bin/zsh
# Registered factorial waves (arms D, B, C, A; 3 workers each), then transfer, then report.
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONUTF8=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
S=scripts/fable_startup_factorial_v2.py; L=artifacts/fable-startup-factorial-v2-20260920/logs
for arm in D B C A; do
  echo "$(date -u +%H:%M:%S) wave $arm start" >> $L/waves.log
  for s in 1300 1301 1302; do ( $PY -B $S train --arm $arm --seed $s --budget-seconds 1100 > $L/train-$arm-$s.log 2>&1; echo "$(date -u +%H:%M:%S) $arm $s exit $?" >> $L/waves.log ) & done; wait
done
for s in 1300 1301 1302; do $PY -B $S transfer --seed $s > $L/transfer-$s.log 2>&1; echo "$(date -u +%H:%M:%S) transfer $s exit $?" >> $L/waves.log; done
$PY -B $S report --seeds 1300,1301,1302 > $L/report-factorial.txt 2>&1
echo "$(date -u +%H:%M:%S) FACTORIAL_DONE" >> $L/waves.log
