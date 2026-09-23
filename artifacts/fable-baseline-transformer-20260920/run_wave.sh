#!/bin/zsh
# usage: run_wave.sh <dirname> <mode> <positions> <updates> <time-cap>
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$PWD/artifacts/fable-baseline-transformer-20260920
PAN=$PWD/artifacts/fable-dispatcher-v3-20260920/panels
mkdir -p $OUT/logs
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
dir=$1; mode=$2; pos=$3; upd=$4; cap=$5
shasum -a 256 -c $OUT/FREEZE.sha256 > $OUT/logs/$dir.freezecheck.log 2>&1 || { echo "FREEZE MISMATCH"; exit 3; }
for s in 0 1 2; do (
  $PY -B scripts/fable_baseline_transformer.py train \
      --mode $mode --positions $pos --seed $s --updates $upd \
      --lr 1e-3 --lr-final 1e-4 --warmup 100 --clip 1.0 --weight-decay 0.1 \
      --visits 16 --questions-per-world 4 --train-people 6 \
      --width 48 --layers 3 --heads 4 --hidden 208 \
      --time-cap $cap --panels $PAN \
      --out $OUT/$dir/seed-$s > $OUT/logs/$dir-seed-$s.train.log 2>&1 \
  && $PY -B scripts/fable_baseline_transformer.py score \
      --run $OUT/$dir/seed-$s --panels $PAN > $OUT/logs/$dir-seed-$s.score.log 2>&1
  echo "$(date +%H:%M:%S) $dir seed $s rc=$?"
) & done; wait
echo "$(date +%H:%M:%S) WAVE $dir DONE"
