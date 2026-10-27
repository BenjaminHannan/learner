#!/usr/bin/env bash
#
# novelty-19 registered experiment -- WAVE 4: scoring, then gates and report.
#
#   24 score jobs:  6 awake finals  (arch x seed)
#                  18 offline finals (arch x seed x arm)
#   at most 3 concurrent -- scoring peaks around 2.5 GB RSS per process.
#
# Then:  gates --exp EXP   -> stdout saved to logs/gates.txt
#        report --exp EXP  -> stdout saved to logs/report.txt
#
# `score` is NOT chunked or resumable: one invocation scores the whole panel suite and
# writes its JSON with write_new(), which refuses to overwrite.  A score file that
# already exists is therefore SKIPPED, not rewritten.  Only the FINAL checkpoint of a
# COMPLETED run is scored -- `report` rejects anything else as "(wrong checkpoint)".
#
# Registered caps are the defaults (--eval-cap 16 for D, --capacity 12 for T), so they
# are not passed: `score` prints a "non-registered-cap" diagnostic and `report` refuses
# to merge any file produced at another cap.  --cells is not passed either: cells are
# scored whole or not at all.  --confirmation / --experiment are NEVER passed, so the
# section-7 confirmation suite cannot be reached from here; only $EXP/dev-panels is.
#
# `report` writes $EXP/report.json and fails on an existing one; this script checks for
# it first and skips rather than passing --overwrite.
#
# Usage:  bash run_score.sh
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
AWAKE_FINAL=ckpt-006000.pt       # checkpoint_name(6000)
OFFLINE_FINAL=ckpt-002000.pt     # checkpoint_name(2000)
CONCURRENCY=3                    # ~2.5 GB RSS per scoring process

PANELS=$EXP/dev-panels
SCORES=$EXP/scores
LOGS=$EXP/logs
STATUS=$LOGS/.status-score
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" "$SCORES" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [score] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

if [ ! -f "$PANELS/manifest.json" ]; then
    say "SCORE_FAILED -- no $PANELS/manifest.json; run run_data.sh first"
    exit 1
fi

# ------------------------------------------------------------------- one job

score_run() {
    local arch=$1 seed=$2 phase=$3 arm=$4
    local name run ckpt out log rc
    if [ "$phase" = awake ]; then
        name=awake-$arch-s$seed
        run=$EXP/runs/$name
        ckpt=$run/$AWAKE_FINAL
    else
        name=offline-$arch-s$seed-$arm
        run=$EXP/runs/$name
        ckpt=$run/$OFFLINE_FINAL
    fi
    out=$SCORES/$name.json
    log=$LOGS/score-$name.log

    if [ -f "$out" ]; then
        say "SKIP score-$name -- $out already exists (never overwritten)"
        return 0
    fi
    if [ ! -f "$run/completion.json" ]; then
        say "SCORE_FAILED score-$name -- $run has no completion.json (not a completed run)"
        return 1
    fi
    if [ ! -f "$ckpt" ]; then
        say "SCORE_FAILED score-$name -- missing final checkpoint $ckpt"
        return 1
    fi

    say "START score-$name  (log: $log)"
    "$PY" -B "$TRAIN" score \
        --arch "$arch" \
        --ckpt "$ckpt" \
        --panels "$PANELS" \
        --out "$out" >>"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "SCORE_FAILED score-$name -- exit $rc, see $log"
        return 1
    fi
    if [ ! -f "$out" ]; then
        say "SCORE_FAILED score-$name -- exit 0 but $out was not written, see $log"
        return 1
    fi
    say "OK score-$name"
    return 0
}

# ------------------------------------------------- 24 jobs, 3 at a time

rm -f "$STATUS"/*.status 2>/dev/null
JOBS=""
for arch in $ARCHES; do
    for seed in $SEEDS; do
        JOBS="$JOBS $arch:$seed:awake:-"
    done
done
for arch in $ARCHES; do
    for seed in $SEEDS; do
        for arm in $ARMS; do
            JOBS="$JOBS $arch:$seed:offline:$arm"
        done
    done
done

say "wave start: scoring 6 awake + 18 offline finals, $CONCURRENCY at a time"

running=0
for job in $JOBS; do
    arch=${job%%:*};       rest=${job#*:}
    seed=${rest%%:*};      rest=${rest#*:}
    phase=${rest%%:*}
    arm=${rest#*:}
    (
        score_run "$arch" "$seed" "$phase" "$arm"
        printf '%s\n' "$?" >"$STATUS/$arch-$seed-$phase-$arm.status"
    ) &
    running=$((running + 1))
    if [ "$running" -ge "$CONCURRENCY" ]; then
        wait
        running=0
    fi
done
wait

failed=""
for job in $JOBS; do
    arch=${job%%:*};       rest=${job#*:}
    seed=${rest%%:*};      rest=${rest#*:}
    phase=${rest%%:*}
    arm=${rest#*:}
    st=$(cat "$STATUS/$arch-$seed-$phase-$arm.status" 2>/dev/null)
    if [ "${st:-1}" != "0" ]; then
        if [ "$phase" = awake ]; then
            failed="$failed score-awake-$arch-s$seed"
        else
            failed="$failed score-offline-$arch-s$seed-$arm"
        fi
    fi
done

if [ -n "$failed" ]; then
    say "SCORE_FAILED --$failed"
    exit 1
fi
say "all 24 score files present"

# ------------------------------------------------------------- gates / report

say "START gates  (stdout: $LOGS/gates.txt)"
"$PY" -B "$TRAIN" gates --exp "$EXP" 2>&1 | tee "$LOGS/gates.txt"
rc=$?
if [ "$rc" -ne 0 ]; then
    say "SCORE_FAILED gates -- exit $rc, see $LOGS/gates.txt"
    exit 1
fi
say "OK gates"

if [ -f "$EXP/report.json" ]; then
    say "SKIP report -- $EXP/report.json already exists (refusing to overwrite; \
--overwrite is deliberately not passed)"
else
    say "START report  (stdout: $LOGS/report.txt)"
    "$PY" -B "$TRAIN" report --exp "$EXP" 2>&1 | tee "$LOGS/report.txt"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "SCORE_FAILED report -- exit $rc, see $LOGS/report.txt"
        exit 1
    fi
    say "OK report"
fi

say "SCORE_DONE"
exit 0
