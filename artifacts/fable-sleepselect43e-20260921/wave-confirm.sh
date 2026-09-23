#!/bin/bash
# v2: the first version died at once (macOS xargs -I length limit) before any training; no data existed. Marks unchanged.
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-sleepselect43e-20260921
RUN="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p $A/confirm
for s in 4111 4112 4113; do $RUN fable_cardfold_sleep.py --seed $s --out $A/confirm/base$s --stage base > $A/confirm/log-base-$s.txt 2>&1 & done; wait
echo BASES_DONE; ls $A/confirm/base*/base.pt
for a in rank4 plain; do for s in 4111 4112 4113; do $RUN fable_sleepselect43e.py --seed $s --arm $a --base-dir $A/confirm/base$s --out $A/confirm > $A/confirm/log-$s-$a.txt 2>&1 & done; done; wait
echo WAVE_DONE; ls $A/confirm/*.json | wc -l
