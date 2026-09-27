#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-lowrank43f-20260921
RUN="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
job() { d=$W/artifacts/fable-cardfold-sleep-20260922/seed$1; [ -d $W/artifacts/fable-autosleep42-20260921/base$1 ] && d=$W/artifacts/fable-autosleep42-20260921/base$1
  $RUN fable_lowrank43f.py --seed $1 --rank $2 --episodes $3 --base-dir $d --out $A/runs > $A/runs/log-$1-r$2-e$3.txt 2>&1; }
wave() { for s in 4102 4103 4104; do job $s $1 $2 & job $s $3 $4 & done; wait; echo "done $*"; }
wave 4 20 4 50
wave 1 100 2 100
wave 8 100 16 100
wave 0 20 0 50
echo WAVE_DONE; ls $A/runs/*.json | wc -l
