#!/bin/zsh
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OP=/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt
OUT=$PWD/artifacts/fable-dispatcher-v3-20260920; PAN=$OUT/panels
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
run() { local dir=$1 cost=$2; shift 2
  for s in 0 1 2; do ( $PY -B scripts/fable_dispatcher_v3.py train --arm rl --operator $OP --seed $s --updates 6000 --k 16 --entropy 0.2 --entropy-final 0.02 --lr 3e-3 --warmup 100 --clip 1.0 --train-hops 1,2,3 --train-people 6 --train-cap 4 --call-cost $cost --visits 16 --width 32 --time-cap 1700 "$@" --panels $PAN --out $OUT/$dir/seed-$s > $OUT/logs/$dir-seed-$s.train.log 2>&1 && $PY -B scripts/fable_dispatcher_v3.py score --run $OUT/$dir/seed-$s --panels $PAN --eval-cap 16 --diagnose > $OUT/logs/$dir-seed-$s.score.log 2>&1; echo "$(date +%H:%M:%S) $dir seed $s rc=$?" ) & done; wait }
run abl-no-recent 0.01 --no-recent-flag
run abl-no-offsets 0.01 --no-offsets
run abl-cost0 0
echo "$(date +%H:%M:%S) ABLATIONS DONE"
