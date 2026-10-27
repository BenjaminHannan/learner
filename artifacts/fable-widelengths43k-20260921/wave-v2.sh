#!/bin/bash
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
A=$W/artifacts/fable-widelengths43k-20260921
mkdir -p $A/runs-v2; cd $W/scripts
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4 FABLE43J_K=2
run() { uv run --offline --no-project --python 3.12 --with torch --with numpy python -B fable_widelengths43k_v2.py "$@"; }
for s in 4102 4103 4104 4111 4112 4113; do run --stage base --seed $s --out $A/runs-v2 > $A/runs-v2/log-base-$s.txt 2>&1 & done; wait
for s in 4121 4122 4123; do run --stage base --seed $s --out $A/runs-v2 > $A/runs-v2/log-base-$s.txt 2>&1 & done; wait
echo BASES_DONE
for s in 4102 4103 4104 4111 4112 4113; do run --stage sleep --seed $s --episodes 20 --out $A/runs-v2 > $A/runs-v2/log-sleep-$s-20.txt 2>&1 & done; wait
for s in 4121 4122 4123; do run --stage sleep --seed $s --episodes 20 --out $A/runs-v2 > $A/runs-v2/log-sleep-$s-20.txt 2>&1 & done; wait
echo WAVE_DONE; ls $A/runs-v2/*.json | wc -l
