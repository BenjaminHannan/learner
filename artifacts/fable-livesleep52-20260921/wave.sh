#!/bin/bash
# Experiment 52 registered wave -- ONE training process at a time (seeds sequential).
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-livesleep52-20260921
cd $W/scripts; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
run() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_livesleep52.py "$@"; }
mkdir -p $A/runs
for s in 5201 5202 5203; do run --seed $s --out $A/runs > $A/runs/log-$s.txt 2>&1 || echo "SEED $s FAILED"; done
echo WAVE_DONE
