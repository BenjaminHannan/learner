#!/usr/bin/env bash
# EXPERIMENT 29 / M1-F10: derived mechanically from experiment 27's run_train.sh (paths, seeds 2106-2108,
# wave 2 = L + F6, no --updates flag: fable_newnames29.py fixes 10,000 updates for control/F/L and 6,000 for F6).
# Comments below that mention experiment 27, 6,000 updates or seeds 2103-2105 are inherited text.
#
# experiment 27 / M1-F "new names", name scale FROZEN at 1.2 -- the training waves.
#
#   bash run_train.sh 1     WAVE 1 (GATED):      control x {2103,2104,2105}
#                                            +   F       x {2103,2104,2105}   = 6 runs
#   bash run_train.sh 2     WAVE 2 (DESCRIPTIVE): L      x {2103,2104,2105}   = 3 runs
#
# Design 4.2.  Wave 1 alone decides the verdict.  Arm L (code_scale LEARNED, started at
# 1.2) is descriptive: it answers "does it stay up if it is allowed to move?" and no mark,
# no verdict and no claim depends on it.  Wave 2 may be run at any time after wave 0; it
# is kept separate so the machine runs six single-thread jobs, not nine.
#
#   control  byte-for-byte experiment 21's control recipe on the new seeds (proved by
#            run_data.sh stage 3, tensor for tensor).  No codes, no names.
#   F        code_scale is a CONSTANT BUFFER at 1.2: not a parameter at all, so it never
#            reaches the optimizer and never reaches clip_grad_norm_.  The trainer calls
#            check_frozen() after EVERY update; if the number ever moves, the run aborts,
#            writes failure.json with "invalid": true, and `gates` reports INVALID for the
#            whole experiment.  That is a bug report, never a result.
#   L        experiment 21's treatment with ONE number changed: the start value 1.2
#            instead of 0.13856 (proved equivalent at 0.13856 by run_data.sh stage 4).
#
# 6,000 updates, one thread each, FINAL CHECKPOINT ONLY, no replacements.  There is no
# chunking and no resume: a run either finishes and writes completion.json or it does not
# exist.  A run that dies leaves failure.json with the traceback and is NOT retried here
# -- a silently restarted run is a different run.
#
# Measured on this Mac with SIX concurrent processes (fixture seed 9, 60 updates at each
# of four curriculum clocks: 0 / 2,000 / 4,000 / 5,900):
#   control  0.0631 / 0.0889 / 0.1310 / 0.1308 s per update
#   arm F    0.0652 / 0.0895 / 0.1339 / 0.1333 s per update
# Integrated over the 6,000-update grow-blind curriculum that is about 640 s per run, and
# all six run in parallel, so wave 1 is about 11 minutes wall-clock, not 6 x 11.  (The
# registered three-process grow-blind wave took 628 to 715 s for the same 6,000 updates,
# which is the anchor these numbers were checked against.)  Wave 2 runs three jobs and is
# no slower.  The caps inside the trainer (28 minutes of training, 29 minutes of work)
# are watchdogs: they abort a run, they never shorten one.
#
# Nothing is overwritten: a run directory holding completion.json is SKIPPED, and the
# trainer creates its folder with exist_ok=False.  This script deletes nothing.
#
# No PYTHONPATH is set, deliberately (see run_data.sh).
#
set -u
set -o pipefail

WAVE=${1:-}
case "$WAVE" in
    1) ARMS="control F" ;;
    2) ARMS="L F6" ;;
    *) echo "usage: bash run_train.sh {1|2}   (1 = control+F, gated; 2 = L, descriptive)"
       exit 2 ;;
esac

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames29-20260921
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames29.py

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

SEEDS="2106 2107 2108"
UPDATES="10000 (arm F6: 6000)"   # experiment 29: the module sets each arm's registered count; --updates is NOT passed

LOGS=$EXP/logs
STATUS=$LOGS/.status-train-$WAVE
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [train-%s] %s\n' "$(ts)" "$WAVE" "$*" | tee -a "$WAVES"; }

# Wave 0 must be finished, and all four of its gates must have passed.
for marker in "$EXP/pool/pool-ref.json" "$EXP/panels/manifest.json" \
              "$EXP/panels/audit.json" "$EXP/control-equivalence.json" \
              "$EXP/treatment-equivalence.json" "$EXP/inertness.json"; do
    if [ ! -f "$marker" ]; then
        say "TRAIN_FAILED -- $marker is missing; run run_data.sh first"
        exit 1
    fi
done
if ! grep -q '"all_clear": true' "$EXP/panels/audit.json"; then
    say "TRAIN_FAILED -- the panel audit did not come out clear"
    exit 1
fi
# AUDIT-27 MINOR-2: `panels` accepts --namespace / --seed-base / --n, and anything but the
# defaults marks the suite "registered": false.  A fixture suite keeps the absolute
# cutoffs 487/461 and would auto-FAIL rather than auto-pass, but a wave must not be spent
# on one either way.
if ! grep -q '"registered": true' "$EXP/panels/newnames27-panels.json"; then
    say "TRAIN_FAILED -- the panel suite is not the registered one"
    exit 1
fi
if ! grep -q '"fingerprints_equal": true' "$EXP/control-equivalence.json"; then
    say "TRAIN_FAILED -- the control arm is not experiment 21's control"
    exit 1
fi
if ! grep -q '"tensors_equal": true' "$EXP/treatment-equivalence.json"; then
    say "TRAIN_FAILED -- arm L at 0.13856 does not reproduce experiment 21's treatment"
    exit 1
fi
if ! grep -q '"all_inert": true' "$EXP/inertness.json"; then
    say "TRAIN_FAILED -- the training trace is not inert"
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
        --wave-start "$WAVE_START" >>"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        if [ -f "$out/failure.json" ] && grep -q '"invalid": true' "$out/failure.json"; then
            say "INVALID $name -- the frozen code_scale MOVED; this is a bug in the \
build, not a result.  Do not report this experiment until it is fixed.  See $log"
        else
            say "TRAIN_FAILED $name -- exit $rc, see $log and $out/failure.json"
        fi
        return 1
    fi
    if [ ! -f "$out/completion.json" ]; then
        say "TRAIN_FAILED $name -- exit 0 but no completion.json, see $log"
        return 1
    fi
    say "OK $name ($(grep -o '"seconds": [0-9.]*' "$out/completion.json" | head -n1))"
    return 0
}

say "wave start: arms [$ARMS] x seeds [$SEEDS] in parallel, $UPDATES updates each"

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

say "TRAIN_DONE wave $WAVE"
exit 0
