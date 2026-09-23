#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-lengthgate43-20260921
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for a in randpos randpos-loop; do for s in 4102 4103 4104; do echo "$s $a"; done; done | \
xargs -P 6 -L 1 bash -c 'uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_lengthgate43.py --seed $0 --arm $1 --out '$A'/runs > '$A'/runs/log-$0-$1.txt 2>&1'
echo WAVE_DONE; ls $A/runs/*.json | wc -l
