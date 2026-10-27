#!/usr/bin/env bash
#
# novelty-19 registered experiment -- WAVE 1: the data side.
#
#   operator-history  ->  dev-panels  ->  (per seed, 3 seeds in parallel)
#                                          awake-stream -> memory -> buffers -> audit
#
# Real dependencies taken from the CLI of scripts/fable_novelty19_data.py:
#   * dev-panels REFUSES unless the operator-history reconstruction is complete
#     (ruling 2); we pass --operator-history explicitly.
#   * awake-stream and buffers both REQUIRE --dev-panels (the collision abort).
#   * memory needs --stream; buffers needs --memory; audit needs all five folders.
#   * Confirmation panels are NEVER touched here: --confirmation / --experiment are
#     never passed, so nothing can reach the section-7 suite.
#
# Nothing is overwritten.  A folder that already carries its completion marker
# (index.json for the stream, manifest.json for everything else) is SKIPPED.
# A folder that exists WITHOUT its marker is a half-built artifact: this script
# refuses to touch it and says so, because the generators themselves create their
# folders with exist_ok=False / write_new() and would abort anyway.
#
# Resume: only `awake-stream` is chunked (8 chunks of 750 updates, an existing
# hash-matching chunk is kept and skipped, index.json appears only when the whole
# [0, 6000) range is on disk).  We therefore LOOP it until index.json exists, with
# a hard round cap.  `dev-panels` has a --budget flag but exceeding it aborts and
# demands the folder be deleted, so we deliberately never pass it.
#
# Usage:  bash run_data.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19-replay-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
DATA=$W/scripts/fable_novelty19_data.py

# The scripts bootstrap their own imports (scripts/fable_dispatcher.py puts the base
# checkout's scripts/ on sys.path, and premonition_memnn.py reads the base checkout's
# runtime.local.json import_roots to find torch).  No PYTHONPATH is needed, and
# setting one could shadow that bootstrap -- so we do not set it.
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

SEEDS="1900 1901 1902"
STREAM_ROUNDS=4          # 8 chunks of 750; one unbudgeted call finishes them all

LOGS=$EXP/logs
STATUS=$LOGS/.status-data
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [data] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

# A folder is finished when its marker file exists; half-built folders are refused.
check_folder() {   # check_folder <name> <folder> <marker>  -> 0 build, 1 skip, 2 refuse
    local name=$1 folder=$2 marker=$3
    if [ -f "$folder/$marker" ]; then
        say "SKIP $name -- $folder/$marker already present (refusing to overwrite)"
        return 1
    fi
    if [ -d "$folder" ]; then
        say "DATA_FAILED $name -- $folder exists but has no $marker (half-built artifact); \
inspect it and remove it by hand before re-running"
        return 2
    fi
    return 0
}

run_step() {       # run_step <job-name> <command...>
    local name=$1; shift
    local log=$LOGS/$name.log
    say "START $name  (log: $log)"
    "$@" >>"$log" 2>&1
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        say "DATA_FAILED $name -- exit $rc, see $log"
        return 1
    fi
    say "OK $name"
    return 0
}

# --------------------------------------------------------------------- stage 1

say "wave start: operator-history -> dev-panels -> 3 seeds in parallel"

check_folder operator-history "$EXP/operator-history" manifest.json
case $? in
    0)  run_step operator-history "$PY" -B "$DATA" operator-history \
            --out "$EXP/operator-history" || exit 1 ;;
    2)  exit 1 ;;
esac

if ! grep -q '"complete": true' "$EXP/operator-history/manifest.json" 2>/dev/null; then
    say "DATA_FAILED operator-history -- manifest.json does not record complete=true; \
dev-panels would refuse it (ruling 2)"
    exit 1
fi

# --------------------------------------------------------------------- stage 2

check_folder dev-panels "$EXP/dev-panels" manifest.json
case $? in
    0)  run_step dev-panels "$PY" -B "$DATA" dev-panels \
            --out "$EXP/dev-panels" \
            --operator-history "$EXP/operator-history" || exit 1 ;;
    2)  exit 1 ;;
esac

# --------------------------------------------------------------------- stage 3

seed_pipeline() {
    local seed=$1
    local stream=$EXP/awake-$seed
    local memory=$EXP/memory-$seed
    local buffers=$EXP/buffers-$seed
    local rc

    # -- awake stream: the only resumable data producer ------------------------
    if [ -f "$stream/index.json" ]; then
        say "SKIP awake-stream-$seed -- $stream/index.json already present"
    else
        local round=0
        local log=$LOGS/awake-stream-$seed.log
        while [ "$round" -lt "$STREAM_ROUNDS" ]; do
            round=$((round + 1))
            say "START awake-stream-$seed round $round/$STREAM_ROUNDS  (log: $log)"
            "$PY" -B "$DATA" awake-stream \
                --seed "$seed" \
                --out "$stream" \
                --dev-panels "$EXP/dev-panels" \
                --updates 6000 \
                --chunk 750 >>"$log" 2>&1
            rc=$?
            if [ "$rc" -ne 0 ]; then
                say "DATA_FAILED awake-stream-$seed -- exit $rc on round $round, see $log"
                return 1
            fi
            if [ -f "$stream/index.json" ]; then
                say "OK awake-stream-$seed (complete after $round round(s))"
                break
            fi
            say "PARTIAL awake-stream-$seed round $round -- resuming with the same command"
        done
        if [ ! -f "$stream/index.json" ]; then
            say "DATA_FAILED awake-stream-$seed -- still incomplete after $STREAM_ROUNDS rounds, see $log"
            return 1
        fi
    fi

    # -- memory ---------------------------------------------------------------
    check_folder "memory-$seed" "$memory" manifest.json
    case $? in
        0)  run_step "memory-$seed" "$PY" -B "$DATA" memory \
                --seed "$seed" \
                --stream "$stream" \
                --out "$memory" || return 1 ;;
        2)  return 1 ;;
    esac

    # -- buffers --------------------------------------------------------------
    check_folder "buffers-$seed" "$buffers" manifest.json
    case $? in
        0)  run_step "buffers-$seed" "$PY" -B "$DATA" buffers \
                --seed "$seed" \
                --memory "$memory" \
                --out "$buffers" \
                --dev-panels "$EXP/dev-panels" || return 1 ;;
        2)  return 1 ;;
    esac

    # -- audit: must PASS, loudly ---------------------------------------------
    local alog=$LOGS/audit-$seed.log
    say "START audit-$seed  (log: $alog)"
    "$PY" -B "$DATA" audit \
        --seed "$seed" \
        --stream "$stream" \
        --memory "$memory" \
        --buffers "$buffers" \
        --dev-panels "$EXP/dev-panels" \
        --operator-history "$EXP/operator-history" >"$alog" 2>&1
    rc=$?
    # `audit` exits 1 whenever verdict['passed'] is false, and an absent expected check
    # is itself a failure, so the exit code is the authoritative signal.  The final
    # "checks run: N/M" line is checked too, so a truncated roster cannot pass quietly.
    if [ "$rc" -ne 0 ]; then
        say "DATA_FAILED audit-$seed -- the audit did NOT pass (exit $rc); see $alog"
        return 1
    fi
    local summary
    summary=$(grep -m1 '^checks run: ' "$alog")
    if [ -z "$summary" ]; then
        say "DATA_FAILED audit-$seed -- exit 0 but no 'checks run:' summary line; see $alog"
        return 1
    fi
    case "$summary" in
        *ABSENT*) say "DATA_FAILED audit-$seed -- $summary; see $alog"; return 1 ;;
    esac
    say "OK audit-$seed (passed; $summary)"
    return 0
}

rm -f "$STATUS"/*.status 2>/dev/null
for seed in $SEEDS; do
    (
        seed_pipeline "$seed"
        printf '%s\n' "$?" >"$STATUS/seed-$seed.status"
    ) &
done
wait

failed=""
for seed in $SEEDS; do
    st=$(cat "$STATUS/seed-$seed.status" 2>/dev/null)
    if [ "${st:-1}" != "0" ]; then
        failed="$failed seed-$seed"
    fi
done

if [ -n "$failed" ]; then
    say "DATA_FAILED --$failed"
    exit 1
fi

say "DATA_DONE"
exit 0
