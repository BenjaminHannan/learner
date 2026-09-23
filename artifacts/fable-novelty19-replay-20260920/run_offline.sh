#!/usr/bin/env bash
#
# novelty-19 registered experiment -- WAVE 3: the eighteen offline runs.
#
#   arch D,T  x  seed 1900,1901,1902  x  arm R,G,U  = 18 runs,
#   at most 6 concurrent: three sub-waves of 6, one per arm.
#
# Each run is 2000 updates in chunks of 500 (the registered ceiling), starting from
# that arch/seed's AWAKE FINAL checkpoint ckpt-006000.pt.  Chunking/resume is the same
# contract as awake: one invocation trains chunk after chunk until the phase finishes
# or --budget-seconds is spent at a chunk boundary, and re-issuing the SAME command
# resumes from the highest ckpt-*.pt.  Each job therefore loops until completion.json
# appears, capped at MAX_ROUNDS (a run cannot need more rounds than its 4 chunks).
#
# The wave REFUSES to start unless all six awake finals exist and their runs completed.
# Nothing is overwritten: a run directory that already holds completion.json is SKIPPED.
# No confirmation-panel path is ever passed.
#
# NOTE on a hard kill: see the same note in run_awake.sh -- delete only the orphan
# log-<start>-<stop>.jsonl, never a ckpt-*.pt or chunk-*.json.  This script deletes
# nothing.
#
# Usage:  bash run_offline.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19-replay-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
TRAIN=$W/scripts/fable_novelty19_train.py

# No PYTHONPATH: the scripts bootstrap their own sys.path.
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

ARCHES="D T"
SEEDS="1900 1901 1902"
ARMS="R G U"
AWAKE_FINAL=ckpt-006000.pt      # checkpoint_name(6000): the awake final
UPDATES=2000
CHUNK=500                       # registered ceiling for offline
BUDGET=1200                     # registered compute budget per invocation
MAX_ROUNDS=8                    # 4 chunks max; every round makes >= 1 chunk of progress

LOGS=$EXP/logs
STATUS=$LOGS/.status-offline
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [offline] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

# ------------------------------------------------- precondition: 6 awake finals

missing=""
for arch in $ARCHES; do
    for seed in $SEEDS; do
        run=$EXP/runs/awake-$arch-s$seed
        if [ ! -f "$run/$AWAKE_FINAL" ] || [ ! -f "$run/completion.json" ]; then
            missing="$missing awake-$arch-s$seed"
        fi
    done
done
if [ -n "$missing" ]; then
    say "OFFLINE_FAILED -- refusing to start; missing completed awake run(s) or their \
$AWAKE_FINAL:$missing"
    exit 1
fi
say "precondition OK: all six awake finals ($AWAKE_FINAL + completion.json) are present"

# ------------------------------------------------------------------- one run

offline_run() {
    local arch=$1 seed=$2 arm=$3
    local name=offline-$arch-s$seed-$arm
    local out=$EXP/runs/$name
    local ckpt=$EXP/runs/awake-$arch-s$seed/$AWAKE_FINAL
    local buffers=$EXP/buffers-$seed
    local log=$LOGS/$name.log
    local round=0 rc

    if [ -f "$out/completion.json" ]; then
        say "SKIP $name -- completion.json already present (refusing to overwrite a completed run)"
        return 0
    fi
    if [ ! -f "$buffers/manifest.json" ]; then
        say "OFFLINE_FAILED $name -- no $buffers/manifest.json; run run_data.sh first"
        return 1
    fi

    while [ "$round" -lt "$MAX_ROUNDS" ]; do
        round=$((round + 1))
        say "START $name round $round/$MAX_ROUNDS  (log: $log)"
        "$PY" -B "$TRAIN" offline \
            --arch "$arch" \
            --seed "$seed" \
            --arm "$arm" \
            --awake-ckpt "$ckpt" \
            --buffers "$buffers" \
            --out "$out" \
            --updates "$UPDATES" \
            --chunk-updates "$CHUNK" \
            --budget-seconds "$BUDGET" >>"$log" 2>&1
        rc=$?
        if [ "$rc" -ne 0 ]; then
            say "OFFLINE_FAILED $name -- exit $rc on round $round, see $log"
            return 1
        fi
        if [ -f "$out/completion.json" ]; then
            say "OK $name (complete after $round round(s))"
            return 0
        fi
        say "PARTIAL $name round $round hit the ${BUDGET}s budget -- resuming with the same command"
    done

    say "OFFLINE_FAILED $name -- still incomplete after $MAX_ROUNDS rounds, see $log"
    return 1
}

# ------------------------------------------------- three sub-waves of six runs

rm -f "$STATUS"/*.status 2>/dev/null
failed=""

for arm in $ARMS; do
    say "sub-wave arm=$arm: 6 runs (2 arch x 3 seeds) in parallel"
    for arch in $ARCHES; do
        for seed in $SEEDS; do
            (
                offline_run "$arch" "$seed" "$arm"
                printf '%s\n' "$?" >"$STATUS/$arch-$seed-$arm.status"
            ) &
        done
    done
    wait
    for arch in $ARCHES; do
        for seed in $SEEDS; do
            st=$(cat "$STATUS/$arch-$seed-$arm.status" 2>/dev/null)
            if [ "${st:-1}" != "0" ]; then
                failed="$failed offline-$arch-s$seed-$arm"
            fi
        done
    done
    if [ -n "$failed" ]; then
        say "OFFLINE_FAILED --$failed (stopping after sub-wave arm=$arm)"
        exit 1
    fi
    say "sub-wave arm=$arm complete"
done

say "OFFLINE_DONE"
exit 0
