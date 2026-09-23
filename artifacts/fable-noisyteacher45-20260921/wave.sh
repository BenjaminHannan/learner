#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-noisyteacher45-20260921
cd $W/scripts; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for s in 4102 4103 4104 4105 4106; do
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_noisyteacher45.py --seed $s --out $A/runs > $A/runs/log-$s.txt 2>&1 &
done; wait; echo WAVE_DONE
