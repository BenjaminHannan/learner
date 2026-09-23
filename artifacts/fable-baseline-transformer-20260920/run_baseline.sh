#!/bin/zsh
# Registered baseline runs: seeds 0, 1, 2 of four arms, then the report.
# Written by the build agent; NOT run by it.  Nothing here is executed automatically.
#
# Each wave runs three seeds concurrently, one torch thread each.  One wave of the
# primary arm is ~14 minutes of wall clock (measured 7.33 updates/s, 6,000 updates);
# scoring the 25 frozen cells is ~18 s per seed.  Four arms = four waves ~= 1 hour.
#
# Run ONE wave at a time.  Do not start a wave while any other registered training
# is running (`pgrep -f "fable_operator|fable_dispatcher.*train|fable_baseline.*train"`).

cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OUT=$PWD/artifacts/fable-baseline-transformer-20260920
PAN=$PWD/artifacts/fable-dispatcher-v3-20260920/panels
mkdir -p $OUT/logs
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1

wave() {                      # wave <dirname> <mode> <positions> [extra train flags...]
  local dir=$1 mode=$2 pos=$3; shift 3
  for s in 0 1 2; do (
    $PY -B scripts/fable_baseline_transformer.py train \
        --mode $mode --positions $pos --seed $s --updates 6000 \
        --lr 1e-3 --lr-final 1e-4 --warmup 100 --clip 1.0 --weight-decay 0.1 \
        --visits 16 --questions-per-world 4 --train-people 6 \
        --width 48 --layers 3 --heads 4 --hidden 208 \
        --time-cap 1700 --panels $PAN "$@" \
        --out $OUT/$dir/seed-$s > $OUT/logs/$dir-seed-$s.train.log 2>&1 \
    && $PY -B scripts/fable_baseline_transformer.py score \
        --run $OUT/$dir/seed-$s --panels $PAN \
        > $OUT/logs/$dir-seed-$s.score.log 2>&1
    echo "$(date +%H:%M:%S) $dir seed $s rc=$?"
  ) & done; wait
}

# ---- ARM A (PRIMARY): writes its reasoning steps, S-style line positions
wave steps-line        steps       line

# ---- ARM B: same model, answer only (ablates the chain of thought)
wave answer-only-line  answer-only line

# ---- ARM C: ordinary absolute positions (123,669 params; ~positions 325-590 untrained)
wave steps-absolute    steps       absolute

# ---- ARM D: no positional embedding at all
wave steps-none        steps       none

# ---- OPTIONAL, disclosed as a SEPARATE arm, not as "the" baseline:
#      supervision parity with S's lookup (supporting-line attention loss).
# wave steps-line-evidence steps line --evidence-aux 0.5
#
# ---- OPTIONAL, disclosed as a SEPARATE arm: 4x the compute budget, because the
#      matched 6,000-update run is still climbing when its schedule ends.
#      Needs a longer cap; one wave is ~55 min.
# wave steps-line-24k steps line --updates 24000 --time-cap 3600

$PY -B scripts/fable_baseline_report.py report --root $OUT \
    --dispatcher-run $PWD/artifacts/fable-dispatcher-v3-20260920/rl-cost01/seed-0 \
    | tee $OUT/REPORT.txt
