#!/bin/zsh
WT=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
BASE=/Users/ben-hannan/Desktop/projects/beautiful-model
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$WT/artifacts/fable-dispatcher-pilot-20260920
V1=$BASE/artifacts/astra-canonical-operator-screen-20260920
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
COMMON=(--updates 6000 --k 16 --entropy 0.2 --entropy-final 0.02 --panels $OUT/panels --time-cap 1500)
job() { local dir=$1 op=$2 s=$3; shift 3
  ( cd $WT && $PY -B scripts/fable_dispatcher.py train "$@" --operator $V1/astra_canonical_operator_seed-$op/final.pt --seed $s $COMMON --out $OUT/$dir/seed-$s > $OUT/logs/$dir-seed-$s.train.log 2>&1 \
    && $PY -B scripts/fable_dispatcher.py score --run $OUT/$dir/seed-$s --panels $OUT/panels > $OUT/logs/$dir-seed-$s.score.log 2>&1; echo "$(date +%H:%M:%S) $dir seed $s rc=$?" ) }
echo "$(date +%H:%M:%S) PHASE A: operator v3r + dispatcher rl-op2-recovery"
( cd $BASE && $PY -B scripts/fable_canonical_v3r.py freeze && $PY -B scripts/fable_canonical_v3r.py wave --seeds 0,1,2 --name wave-1 ) &
for s in 0 1 2; do job rl-op2-recovery 2 $s --arm rl & done; wait
echo "$(date +%H:%M:%S) PHASE B: supervised-op1-recovery + rl-abs-op1"
rmdir $OUT/rl-abs-op1/seed-* 2>/dev/null
for s in 0 1 2; do job supervised-op1-recovery 1 $s --arm supervised & job rl-abs-op1 1 $s --arm rl --absolute-positions & done; wait
echo "$(date +%H:%M:%S) MORNING RUNS DONE"
