#!/bin/zsh
WT=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$WT/artifacts/fable-dispatcher-pilot-20260920
V1=/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/astra-canonical-operator-screen-20260920
cd $WT; export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
COMMON=(--updates 6000 --k 16 --entropy 0.2 --entropy-final 0.02 --panels $OUT/panels --time-cap 1500)
job() { # arm-dir op-seed disp-seed extra...
  local dir=$1 op=$2 s=$3; shift 3
  $PY -B scripts/fable_dispatcher.py train "$@" --operator $V1/astra_canonical_operator_seed-$op/final.pt --seed $s $COMMON --out $OUT/$dir/seed-$s > $OUT/logs/$dir-seed-$s.train.log 2>&1 \
   && $PY -B scripts/fable_dispatcher.py score --run $OUT/$dir/seed-$s --panels $OUT/panels > $OUT/logs/$dir-seed-$s.score.log 2>&1
  echo "$(date +%H:%M:%S) $dir seed $s rc=$?"
}
mkdir -p $OUT/logs
for spec in "rl-op1 1 --arm rl" "rl-op2 2 --arm rl" "supervised-op1 1 --arm supervised" "rl-abs-op1 1 --arm rl --absolute-positions"; do
  set -- ${=spec}; dir=$1; op=$2; shift 2
  echo "$(date +%H:%M:%S) WAVE $dir"
  for s in 0 1 2; do job $dir $op $s "$@" & done; wait
done
echo "$(date +%H:%M:%S) ALL WAVES DONE"
