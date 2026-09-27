#!/bin/zsh
# Registered long run: arm D, 18,000 updates, three seeds, chunks <= 1,100 s; repeat rounds until complete.
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONUTF8=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
S=scripts/fable_startup_factorial_v2.py; L=artifacts/fable-startup-factorial-v2-20260920/logs
for round in 1 2 3 4 5; do
  echo "$(date -u +%H:%M:%S) longrun round $round start" >> $L/waves.log
  for s in 1300 1301 1302; do ( $PY -B $S longrun --seed $s --budget-seconds 1100 >> $L/longrun-$s.log 2>&1; echo "$(date -u +%H:%M:%S) longrun $s round $round exit $?" >> $L/waves.log ) & done; wait
  n=$(grep -l '"complete": true' $L/longrun-1300.log $L/longrun-1301.log $L/longrun-1302.log 2>/dev/null | wc -l)
  [ "$n" -eq 3 ] && break
done
$PY -B $S report --seeds 1300,1301,1302 > $L/report-final.txt 2>&1
echo "$(date -u +%H:%M:%S) LONGRUN_DONE" >> $L/waves.log
