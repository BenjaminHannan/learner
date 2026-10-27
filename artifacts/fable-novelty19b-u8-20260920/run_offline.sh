#!/usr/bin/env bash
#
# novelty-19b -- THE OFFLINE WAVE: the six continuations.
#
#   seed 1900,1901,1902  x  arm U5,U8  =  6 runs, ALL SIX CONCURRENT.
#
# Unlike experiment 19 (which ran three sub-waves of six, one per arm), 19b's two arms
# are a CONTRAST and are run together: nothing about the machine's state can then differ
# systematically between control and treatment.
#
# Each run is 2000 updates in chunks of 500 (the registered ceiling), starting from that
# seed's experiment-19 D AWAKE FINAL ckpt-006000.pt -- read-only, in the experiment-19
# folder, and re-hashed against that run's own chunk record BEFORE torch.load sees it.
# Chunking/resume is the frozen contract: one invocation trains chunk after chunk until
# the phase finishes or --budget-seconds is spent at a chunk boundary, and re-issuing the
# SAME command resumes from the highest ckpt-*.pt.  Each job therefore loops until
# completion.json appears, capped at MAX_ROUNDS.
#
# The wave REFUSES to start unless the three awake finals exist with completed runs and
# every seed's buffers are built.  Nothing is overwritten: a run directory that already
# holds completion.json is SKIPPED.  No confirmation path is ever passed.
#
# MEASURED TIMING (disposable probe, 1,024 rollout rows, the registered batch shape, 3
# concurrent processes): 0.062 s/update at 5 executed lookups, 0.104 s at 8, so
# f(8)/f(5) = 1.42-1.67 across three copies.  Experiment 19's own recorded D-U runs took
# 570-590 s for 2,000 updates at six-way concurrency, so U5 here should land in the same
# place (~10 min) and U8 at 1.4-1.7x that (~14-16 min).  19b's wave is six D jobs where
# experiment 19's was three D and three cheaper T, so allow contention on top; even a
# generous +30% keeps U8 near 21 min, inside the 30-minute wave limit.  BUDGET below is
# the per-invocation ceiling, not the expected time.
#
# NOTE on a hard kill: as in experiment 19, delete only an orphan log-<start>-<stop>.jsonl
# (or a work-*.jsonl.partial, which is this experiment's ledger and is never read back),
# never a ckpt-*.pt or chunk-*.json.  This script deletes nothing.
#
# Usage:  bash run_offline.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19b-u8-20260920
EXP19=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19-replay-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
TRAIN=$W/scripts/fable_novelty19b_train.py

# No PYTHONPATH: the scripts bootstrap their own sys.path.
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

SEEDS="1900 1901 1902"
ARMS="U5 U8"
AWAKE_FINAL=ckpt-006000.pt      # checkpoint_name(6000): experiment 19's awake final
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

# ------------------------------- preconditions: awake finals AND buffers

missing=""
for seed in $SEEDS; do
    run=$EXP19/runs/awake-D-s$seed
    if [ ! -f "$run/$AWAKE_FINAL" ] || [ ! -f "$run/completion.json" ]; then
        missing="$missing exp19:awake-D-s$seed"
    fi
    if [ ! -f "$EXP/buffers-$seed/manifest.json" ]; then
        missing="$missing buffers-$seed"
    fi
done
if [ ! -f "$EXP/dev-panels/manifest.json" ]; then
    say "note: $EXP/dev-panels is not built yet -- training does not need it, but \
run_score.sh will refuse without it"
fi
if [ -n "$missing" ]; then
    say "OFFLINE_FAILED -- refusing to start; missing:$missing"
    exit 1
fi
say "precondition OK: three experiment-19 awake finals and three buffer folders present"

# ------------------------------------------------------------------- one run

offline_run() {
    local seed=$1 arm=$2
    local name=offline-D-s$seed-$arm
    local out=$EXP/runs/$name
    local ckpt=$EXP19/runs/awake-D-s$seed/$AWAKE_FINAL
    local log=$LOGS/$name.log
    local round=0 rc

    if [ -f "$out/completion.json" ]; then
        say "SKIP $name -- completion.json already present (refusing to overwrite a completed run)"
        return 0
    fi

    while [ "$round" -lt "$MAX_ROUNDS" ]; do
        round=$((round + 1))
        say "START $name round $round/$MAX_ROUNDS  (log: $log)"
        "$PY" -B "$TRAIN" offline \
            --seed "$seed" \
            --arm "$arm" \
            --exp "$EXP" \
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

# ----------------------------------------- one wave: all six runs together

rm -f "$STATUS"/*.status 2>/dev/null
say "wave start: 6 runs (3 seeds x 2 arms) in parallel; control and treatment together"

for seed in $SEEDS; do
    for arm in $ARMS; do
        (
            offline_run "$seed" "$arm"
            printf '%s\n' "$?" >"$STATUS/$seed-$arm.status"
        ) &
    done
done
wait

failed=""
for seed in $SEEDS; do
    for arm in $ARMS; do
        st=$(cat "$STATUS/$seed-$arm.status" 2>/dev/null)
        if [ "${st:-1}" != "0" ]; then
            failed="$failed offline-D-s$seed-$arm"
        fi
    done
done
if [ -n "$failed" ]; then
    say "OFFLINE_FAILED --$failed"
    exit 1
fi

say "all six continuations complete"
say "OFFLINE_DONE"
exit 0
