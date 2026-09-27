#!/bin/bash
# usage: wave.sh <base-arm>   (randpos | randpos-loop)
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-sharedsleep43b-20260921
B=$W/artifacts/fable-lengthgate43-20260921/runs
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for a in rank4 subspace sign snr plain; do for s in 4102 4103 4104; do echo "$s $a"; done; done | \
xargs -P 6 -L 1 bash -c 'uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_sharedsleep43b.py --seed $0 --arm $1 --base '$B'/seed$0-'$1'.pt --out '$A'/runs > '$A'/runs/log-$0-$1.txt 2>&1'
echo WAVE_DONE; ls $A/runs/*.json | wc -l
