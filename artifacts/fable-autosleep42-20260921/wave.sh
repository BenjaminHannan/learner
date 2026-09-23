#!/bin/bash
# Bases for new seeds first (2 jobs), while 4 jobs run arms on existing bases; then the rest. Max 6 jobs.
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-autosleep42-20260921
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
base() { $RUN fable_cardfold_sleep.py --seed $1 --stage base --out $A/base$1 > $A/base$1.log 2>&1; }
arm() { d=$W/artifacts/fable-cardfold-sleep-20260922/seed$1; [ -d $A/base$1 ] && d=$A/base$1; $RUN fable_autosleep42.py --seed $1 --arm $2 --base-dir $d --out $A/runs > $A/runs/log-$1-$2.txt 2>&1; }
export -f base arm; export W A RUN
mkdir -p $A/runs
{ for s in 4104 4105; do echo "base $s"; done
  for a in R100-squeeze-long R20-squeeze-long R20 R100 R400 R100-squeeze R100-surprise; do for s in 4101 4102 4103; do echo "arm $s $a"; done; done; } > $A/jobs1.txt
for a in R100-squeeze-long R20-squeeze-long R20 R100 R400 R100-squeeze R100-surprise; do for s in 4104 4105; do echo "arm $s $a"; done; done >> $A/jobs1.txt
# single queue: the two base jobs are first (≈9 min); seeds 4104/4105 arms are last, reached after the bases exist
xargs -P 6 -I{} bash -c '{}' < $A/jobs1.txt
echo WAVE_DONE; ls $A/runs/*.json | wc -l
