#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-sleepselect43e-20260921
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for a in rank4 plain; do for s in 4102 4103 4104; do echo "$s $a"; done; done | \
xargs -P 6 -L 1 bash -c 'd='$W'/artifacts/fable-cardfold-sleep-20260922/seed$0; [ -d '$W'/artifacts/fable-autosleep42-20260921/base$0 ] && d='$W'/artifacts/fable-autosleep42-20260921/base$0; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_sleepselect43e.py --seed $0 --arm $1 --base-dir $d --out '$A'/runs > '$A'/runs/log-$0-$1.txt 2>&1'
echo WAVE_DONE; ls $A/runs/*.json | wc -l
