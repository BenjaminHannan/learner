#!/bin/zsh
# Dispatcher v4 — three seeds per arm, one thread each, one wave at a time.
# NOT EXECUTED BY THE BUILD AGENT.  Run one `wave` line at a time and read the log.
#
# Each wave is three concurrent single-threaded jobs.
#
# Measured on this Mac, 2026-09-20, dev seeds 996001/996002, registered batch size:
#   200 updates, four concurrent:  v3-repro 5.84  reg 5.62  ctx 5.46  reg+ctx 5.53 u/s
#   ~3,600 updates, three concurrent BUT sharing the box with another session's jobs:
#                                  v3-repro 5.42                      reg+ctx 5.09-5.12 u/s
# So the two new mechanisms cost roughly 6% of throughput; the rest of the gap to v3's
# registered 7.45-7.60 u/s is contention, not v4.  Worst case measured (5.09 u/s):
# 6,000 updates = 1,180 s, plus the ~35 s that score --diagnose took for v3, i.e. a
# wave of ~20 min.  On an idle box expect ~7.0 u/s and ~15 min.  The --time-cap of
# 1500 s therefore keeps a wave under 25 min with headroom either way; a time-capped
# job is a FAILURE by the preregistration, not a partial result.  Run `params` first
# and confirm the parameter counts against PREREGISTRATION.md.
set -e
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
OP=/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt
V3=$PWD/artifacts/fable-dispatcher-v3-20260920
PAN=$V3/panels                       # the FROZEN registered panels; v4 builds none
OUT=$PWD/artifacts/fable-dispatcher-v4-20260920
export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p $OUT/logs

# record exactly what is about to run
shasum -a 256 scripts/fable_dispatcher_v4.py scripts/fable_dispatcher_v3.py \
              scripts/fable_dispatcher.py $PAN/manifest.json \
              $OUT/PREREGISTRATION.md | tee $OUT/LAUNCH-HASHES.txt
$PY -B scripts/fable_dispatcher_v4.py params | tee $OUT/parameter-counts.json

wave() {                       # wave <arm> <directory>
  local arm=$1 dir=$2
  echo "$(date +%H:%M:%S) START $arm"
  for s in 0 1 2; do (
    $PY -B scripts/fable_dispatcher_v4.py train \
        --arm $arm --operator $OP --seed $s --updates 6000 --k 16 \
        --entropy 0.2 --entropy-final 0.02 --lr 3e-3 --warmup 100 --clip 1.0 \
        --train-hops 1,2,3 --train-people 6 --train-cap 4 --call-cost 0.01 \
        --visits 16 --width 32 --time-cap 1500 \
        --panels $PAN --out $OUT/$dir/seed-$s \
        > $OUT/logs/$dir-seed-$s.train.log 2>&1 \
    && $PY -B scripts/fable_dispatcher_v4.py score \
        --run $OUT/$dir/seed-$s --panels $PAN --eval-cap 16 --diagnose \
        > $OUT/logs/$dir-seed-$s.score.log 2>&1
    echo "$(date +%H:%M:%S) $dir seed $s rc=$?"
  ) & done
  wait
  echo "$(date +%H:%M:%S) DONE $arm"
}

# 1. faithfulness control first: if this does not reproduce v3, stop and fix the refactor.
# 2. the headline arm.
wave reg+ctx    reg-ctx
wave v3-repro   v3-repro
# 3. the two single-change arms, to attribute any failure.
wave reg        reg
wave ctx        ctx

echo "$(date +%H:%M:%S) V4 ALL WAVES DONE"
