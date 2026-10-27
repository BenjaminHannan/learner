#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-hardgate46-20260921
cd $W/scripts; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
run() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_hardgate46.py "$@"; }
for s in 4102 4103 4104 4105 4106; do run --seed $s --out $A/runs > $A/runs/log-$s.txt 2>&1 & done; wait
for s in 4107 4108 4109 4110 4111; do run --seed $s --out $A/runs > $A/runs/log-$s.txt 2>&1 & done; wait
echo WAVE_DONE
