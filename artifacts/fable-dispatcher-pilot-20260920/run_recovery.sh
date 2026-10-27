#!/bin/zsh
WT=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
BASE=/Users/ben-hannan/Desktop/projects/beautiful-model
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$WT/artifacts/fable-dispatcher-pilot-20260920
V1=$BASE/artifacts/astra-canonical-operator-screen-20260920
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
# wait until the four original waves, the v3 wave and the scale probe are all finished
until ! pgrep -f "[r]un_waves.sh$|[f]able_canonical_v3.py w|[f]able_scale_probe.py" >/dev/null; do sleep 30; done
echo "$(date +%H:%M:%S) START v3r operator wave"
cd $BASE && $PY -B scripts/fable_canonical_v3r.py freeze && $PY -B scripts/fable_canonical_v3r.py wave --seeds 0,1,2 --name wave-1
echo "$(date +%H:%M:%S) START rl-op2-recovery"
cd $WT
for s in 0 1 2; do
  ( $PY -B scripts/fable_dispatcher.py train --arm rl --operator $V1/astra_canonical_operator_seed-2/final.pt --seed $s --updates 6000 --k 16 --entropy 0.2 --entropy-final 0.02 --panels $OUT/panels --time-cap 1500 --out $OUT/rl-op2-recovery/seed-$s > $OUT/logs/rl-op2-recovery-seed-$s.train.log 2>&1 \
    && $PY -B scripts/fable_dispatcher.py score --run $OUT/rl-op2-recovery/seed-$s --panels $OUT/panels > $OUT/logs/rl-op2-recovery-seed-$s.score.log 2>&1; echo "$(date +%H:%M:%S) rl-op2-recovery seed $s rc=$?" ) &
done; wait
echo "$(date +%H:%M:%S) RECOVERY DONE"
