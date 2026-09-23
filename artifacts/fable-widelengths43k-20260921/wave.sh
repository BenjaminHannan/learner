#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-widelengths43k-20260921
cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4 FABLE43J_K=2
run() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_widelengths43k.py "$@"; }
for s in 4102 4103 4104 4111 4112 4113; do run --stage base --seed $s --out $A/runs > $A/runs/log-base-$s.txt 2>&1 & done; wait
echo BASES_DONE
for s in 4102 4103 4104 4111 4112 4113; do run --stage sleep --seed $s --episodes 20 --out $A/runs > $A/runs/log-sleep-$s-20.txt 2>&1 & done; wait
echo WAVE_DONE; ls $A/runs/*.json | wc -l
