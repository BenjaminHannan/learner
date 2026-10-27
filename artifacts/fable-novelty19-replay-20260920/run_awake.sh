#!/usr/bin/env bash
#
# novelty-19 registered experiment -- WAVE 2: the six awake runs.
#
#   arch D,T  x  seed 1900,1901,1902  = 6 runs, all six in parallel.
#
# Each run is 6000 updates in chunks of 750 (the registered ceiling).  ONE invocation
# trains chunk after chunk until the phase is finished or --budget-seconds (1200 s,
# the registered compute budget; the flag's own ceiling is the 1500 s wave deadline)
# is spent at a chunk boundary.  An interrupted run resumes bit-identically from the
# highest ckpt-*.pt on disk when the SAME command is re-issued, so each job here is a
# loop that re-issues its command until the run writes completion.json, capped at
# MAX_ROUNDS.  A run cannot need more rounds than it has chunks (8), because every
# invocation makes at least one chunk of progress.
#
# Nothing is overwritten: a run directory that already holds completion.json is
# SKIPPED.  No confirmation-panel path is ever passed.
#
# NOTE on a hard kill: a wave killed MID-chunk leaves a half-written
# log-<start>-<stop>.jsonl, and the trainer opens that log with mode 'x'.  The next
# round will then abort with "refusing to overwrite ...jsonl".  Delete THAT LOG FILE
# and only that file (never a ckpt-*.pt or chunk-*.json) and re-run.  This script
# deliberately deletes nothing.
#
# Usage:  bash run_awake.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19-replay-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
TRAIN=$W/scripts/fable_novelty19_train.py

# No PYTHONPATH: the scripts bootstrap their own sys.path (base-checkout scripts/ plus
# the import_roots of the base checkout's runtime.local.json, which is where torch is).
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

ARCHES="D T"
SEEDS="1900 1901 1902"
UPDATES=6000
CHUNK=750               # registered ceiling for awake
BUDGET=1200             # registered compute budget per invocation
MAX_ROUNDS=12           # 8 chunks max; every round makes >= 1 chunk of progress

LOGS=$EXP/logs
STATUS=$LOGS/.status-awake
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [awake] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

awake_run() {
    local arch=$1 seed=$2
    local name=awake-$arch-s$seed
    local out=$EXP/runs/$name
    local stream=$EXP/awake-$seed
    local log=$LOGS/$name.log
    local round=0 rc

    if [ -f "$out/completion.json" ]; then
        say "SKIP $name -- completion.json already present (refusing to overwrite a completed run)"
        return 0
    fi
    if [ ! -f "$stream/index.json" ]; then
        say "AWAKE_FAILED $name -- no $stream/index.json; run run_data.sh first"
        return 1
    fi

    while [ "$round" -lt "$MAX_ROUNDS" ]; do
        round=$((round + 1))
        say "START $name round $round/$MAX_ROUNDS  (log: $log)"
        "$PY" -B "$TRAIN" awake \
            --arch "$arch" \
            --seed "$seed" \
            --stream "$stream" \
            --out "$out" \
            --updates "$UPDATES" \
            --chunk-updates "$CHUNK" \
            --budget-seconds "$BUDGET" >>"$log" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            say "AWAKE_FAILED $name -- exit $rc on round $round, see $log"
            return 1
        fi
        if [ -f "$out/completion.json" ]; then
            say "OK $name (complete after $round round(s))"
            return 0
        fi
        say "PARTIAL $name round $round hit the ${BUDGET}s budget -- resuming with the same command"
    done

    say "AWAKE_FAILED $name -- still incomplete after $MAX_ROUNDS rounds, see $log"
    return 1
}

say "wave start: 6 awake runs (2 arch x 3 seeds) in parallel, $UPDATES updates, chunk $CHUNK"

rm -f "$STATUS"/*.status 2>/dev/null
for arch in $ARCHES; do
    for seed in $SEEDS; do
        (
            awake_run "$arch" "$seed"
            printf '%s\n' "$?" >"$STATUS/$arch-$seed.status"
        ) &
    done
done
wait

failed=""
for arch in $ARCHES; do
    for seed in $SEEDS; do
        st=$(cat "$STATUS/$arch-$seed.status" 2>/dev/null)
        if [ "${st:-1}" != "0" ]; then
            failed="$failed awake-$arch-s$seed"
        fi
    done
done

if [ -n "$failed" ]; then
    say "AWAKE_FAILED --$failed"
    exit 1
fi

say "AWAKE_DONE"
exit 0
