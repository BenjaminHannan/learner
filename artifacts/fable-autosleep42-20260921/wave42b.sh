#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-autosleep42-20260921
until [ $(ls $A/runs/*.json 2>/dev/null | wc -l) -ge 35 ]; do sleep 15; done
cd $W/scripts; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; mkdir -p $A/runs42b
arm() { d=$W/artifacts/fable-cardfold-sleep-20260922/seed$1; [ -d $A/base$1 ] && d=$A/base$1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_autosleep42b.py --seed $1 --arm $2 --base-dir $d --out $A/runs42b > $A/runs42b/log-$1-$2.txt 2>&1; }
export -f arm; export W A
for a in R20-embed R20-norms R100-embed R100-norms; do for s in 4101 4102 4103 4104 4105; do echo "arm $s $a"; done; done | xargs -P 6 -I{} bash -c '{}'
echo WAVE42B_DONE; ls $A/runs42b/*.json | wc -l
