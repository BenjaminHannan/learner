#!/usr/bin/env bash
#
# experiment 21 / M1 "new names" -- WAVE 2: the six runs.
#
#   arm {control, treatment}  x  seed {2100, 2101, 2102}  =  6 runs, all six at once,
#   one thread each, 6,000 updates, FINAL CHECKPOINT ONLY, no replacements.
#
# There is no chunking and no resume: the registered recipe is one 6,000-update loop and
# a run either finishes and writes completion.json or it does not exist.  A run that dies
# leaves failure.json with the traceback and is NOT retried here -- a silently restarted
# run is a different run.
#
# Measured on this Mac with two concurrent processes (fixture seed 9, 80 updates at each
# curriculum regime): 0.0566 / 0.0944 / 0.1231 s per update for the control at the
# reduced, growing and full-story stages, and 0.0583 / 0.0964 / 0.1252 for the treatment.
# Integrated over the grow curriculum (0 to 1,500 reduced, 1,500 to 3,000 ramp, 3,000 to
# 6,000 full) that is about 593 s for a control run and 605 s for a treatment run, and
# the six run in parallel, so the wave is the slowest single run, not their sum.  The
# registered three-process grow-blind wave took 628 to 715 s for the same 6,000 updates,
# which is the anchor these numbers were checked against.  The caps below are watchdogs,
# not part of the recipe: they abort a run, they never shorten one.
#
# Nothing is overwritten: a run directory holding completion.json is SKIPPED, and the
# trainer itself creates its folder with exist_ok=False.  This script deletes nothing.
#
# No PYTHONPATH is set, deliberately (see run_data.sh).
#
# Usage:  bash run_train.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/fixtures/exprun
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames21.py

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

ARMS="control treatment"
SEEDS="9"
UPDATES=20

LOGS=$EXP/logs
STATUS=$LOGS/.status-train
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [train] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

# The data wave must be finished, and its two gates must have passed.
for marker in "$EXP/pool/pool.json" "$EXP/panels/manifest.json" \
              "$EXP/panels/audit.json" "$EXP/control-equivalence.json"; do
    if [ ! -f "$marker" ]; then
        say "TRAIN_FAILED -- $marker is missing; run run_data.sh first"
        exit 1
    fi
done
if ! grep -q '"all_clear": true' "$EXP/panels/audit.json"; then
    say "TRAIN_FAILED -- the panel audit did not come out clear"
    exit 1
fi
if ! grep -q '"fingerprints_equal": true' "$EXP/control-equivalence.json"; then
    say "TRAIN_FAILED -- the control arm is not the registered recipe"
    exit 1
fi

WAVE_START=$("$PY" -B -c 'import time; print(time.monotonic())')

train_run() {
    local arm=$1 seed=$2
    local name=$arm-$seed
    local out=$EXP/runs/$name
    local log=$LOGS/train-$name.log
    local rc

    if [ -f "$out/completion.json" ]; then
        say "SKIP $name -- completion.json already present"
        return 0
    fi
    if [ -d "$out" ]; then
        say "TRAIN_FAILED $name -- $out exists without completion.json (a dead or \
running run); inspect it and remove it by hand before re-running"
        return 1
    fi

    say "START $name  ($UPDATES updates, one thread; log: $log)"
    "$PY" -B "$RUN" train \
        --exp "$EXP" \
        --arm "$arm" \
        --seed "$seed" \
        --updates "$UPDATES" \
        --wave-start "$WAVE_START" >>"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "TRAIN_FAILED $name -- exit $rc, see $log and $out/failure.json"
        return 1
    fi
    if [ ! -f "$out/completion.json" ]; then
        say "TRAIN_FAILED $name -- exit 0 but no completion.json, see $log"
        return 1
    fi
    say "OK $name ($(grep -o '\"seconds\": [0-9.]*' "$out/completion.json" | head -n1))"
    return 0
}

say "wave start: 6 runs (2 arms x 3 seeds) in parallel, $UPDATES updates each"

rm -f "$STATUS"/*.status 2>/dev/null
for arm in $ARMS; do
    for seed in $SEEDS; do
        (
            train_run "$arm" "$seed"
            printf '%s\n' "$?" >"$STATUS/$arm-$seed.status"
        ) &
    done
done
wait

failed=""
for arm in $ARMS; do
    for seed in $SEEDS; do
        st=$(cat "$STATUS/$arm-$seed.status" 2>/dev/null)
        if [ "${st:-1}" != "0" ]; then
            failed="$failed $arm-$seed"
        fi
    done
done

if [ -n "$failed" ]; then
    say "TRAIN_FAILED --$failed"
    exit 1
fi

say "TRAIN_DONE"
exit 0
