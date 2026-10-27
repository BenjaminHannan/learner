#!/usr/bin/env bash
#
# experiment 27 / M1-F "new names", name scale FROZEN at 1.2 -- WAVE 3: read the runs.
#
#   score (every completed run)  ->  readouts (DESCRIPTIVE)  ->  gates  ->  report
#
# Scoring is the fixed external loop (`astra_canonical_operator.execute`) through the
# unmodified `astra_canonical_operator_run.score_cell`, on the FINAL checkpoint only.
# Each checkpoint is hashed before it is loaded and its stored parameter fingerprint is
# re-derived after loading; a mismatch aborts that run's scoring.
#
#   control    one scoring of the ten gated cells (it has no names to re-draw).
#   F and L    TWO scorings of the SAME panel files -- training-pool codes and reserved
#              codes.  Arm F is also re-checked here: `check_frozen` must still hold and
#              the buffer must still be 1.2, and the answer is recorded as `buffer_ok`.
#              A false `buffer_ok` makes the whole experiment INVALID at the gates.
#   readouts   design 4.6's two DESCRIPTIVE read-outs, for the code arms only: open-set
#              scoring against the 1,024 reserved codes (A) and against all 4,096 (B),
#              and the attention read-out ("was the right line attended while the wrong
#              name was emitted").  They are reported; no mark and no verdict uses them.
#
# Scoring is run three jobs at a time rather than six: it is the reading of a frozen
# checkpoint, nothing is timed against a deadline, and leaving headroom keeps the machine
# usable.  Expected wall-clock at 512 units per cell, by analogy with experiment 21 (35 s
# for a one-scoring control run, 82 s for a two-scoring code run, two at a time): roughly
# 4 minutes for the six wave-1 runs, plus about 2 minutes for three arm-L runs, plus about
# a minute for the read-outs.  These are UNVERIFIED for this experiment: the fixture
# suites built here were 16 units, not 512.
#
# Nothing is overwritten: a scores/<arm>-<seed>.json or readouts/<arm>-<seed>.json already
# on disk is SKIPPED, and gates.json / report.txt are written only if absent (`gates` and
# `report` always print their result, so a re-run still shows the verdict).  Runs that do
# not exist are skipped with a note: arm L is descriptive and may legitimately be absent.
#
# Two checks before any of that (AUDIT-27 MINOR-3, MINOR-4): every gated run must already
# be finished, and a gates.json / report.txt older than the newest score file is refused
# rather than announced, because it would be a verdict for a smaller set.
#
# No PYTHONPATH is set, deliberately (see run_data.sh).
#
# Usage:  bash run_score.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames27-20260921
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames27.py

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

GATED_ARMS="control F"          # wave 1: these MUST be present
SOFT_ARMS="L"                   # wave 2: descriptive, may be absent
CODE_ARMS="F L"                 # the arms with names, i.e. the ones with read-outs
SEEDS="2103 2104 2105"
PARALLEL=3

LOGS=$EXP/logs
STATUS=$LOGS/.status-score
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" "$EXP/scores" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [score] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

score_run() {      # score_run <arm> <seed> <required:0|1>
    local arm=$1 seed=$2 required=$3
    local name=$arm-$seed
    local out=$EXP/scores/$name.json
    local log=$LOGS/score-$name.log
    local rc

    if [ -f "$out" ]; then
        say "SKIP $name -- $out already present"
        return 0
    fi
    if [ ! -f "$EXP/runs/$name/completion.json" ]; then
        if [ "$required" = "0" ]; then
            say "ABSENT $name -- no completed run (arm L is descriptive; not an error)"
            return 0
        fi
        say "SCORE_FAILED $name -- no completed run at $EXP/runs/$name"
        return 1
    fi

    say "START $name  (log: $log)"
    "$PY" -B "$RUN" score --exp "$EXP" --arm "$arm" --seed "$seed" >>"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "SCORE_FAILED $name -- exit $rc, see $log"
        return 1
    fi
    if [ "$arm" = "F" ] && ! grep -q '"buffer_ok": true' "$out"; then
        say "INVALID $name -- the frozen code_scale is not 1.2 in the saved checkpoint; \
this is a bug in the build, not a result"
        return 1
    fi
    say "OK $name"
    return 0
}

readouts_run() {   # readouts_run <arm> <seed>
    local arm=$1 seed=$2
    local name=$arm-$seed
    local out=$EXP/readouts/$name.json
    local log=$LOGS/readouts-$name.log

    if [ -f "$out" ]; then
        say "SKIP readouts $name -- already present"
        return 0
    fi
    if [ ! -f "$EXP/runs/$name/completion.json" ]; then
        say "ABSENT readouts $name -- no completed run"
        return 0
    fi
    say "START readouts $name  (DESCRIPTIVE; log: $log)"
    if ! "$PY" -B "$RUN" readouts --exp "$EXP" --arm "$arm" --seed "$seed" \
            >>"$log" 2>&1; then
        # The read-outs decide nothing.  A failure here is reported and does not stop the
        # gates from being computed.
        say "READOUTS_FAILED $name -- see $log (descriptive only; continuing)"
        return 0
    fi
    say "OK readouts $name ($(tail -n1 "$log"))"
    return 0
}

say "wave start: score -> readouts -> gates -> report"

# AUDIT-27 MINOR-4: check the gated runs are all there BEFORE spending several minutes
# scoring the ones that are.
missing=""
for arm in $GATED_ARMS; do
    for seed in $SEEDS; do
        if [ ! -f "$EXP/runs/$arm-$seed/completion.json" ] \
           && [ ! -f "$EXP/scores/$arm-$seed.json" ]; then
            missing="$missing $arm-$seed"
        fi
    done
done
if [ -n "$missing" ]; then
    say "SCORE_FAILED -- wave 1 is not finished; no completed run for:$missing"
    exit 1
fi

check_not_stale() {
    # AUDIT-27 MINOR-3: `gates` and `report` write only when the file is absent, so a
    # gates.json left over from an earlier, smaller set would be announced below while
    # the fresh verdict went only to the log.  Refuse rather than overwrite or mislead.
    local stale newer
    for stale in "$EXP/gates.json" "$EXP/report.txt"; do
        [ -f "$stale" ] || continue
        newer=$(find "$EXP/scores" -name '*.json' -newer "$stale" 2>/dev/null | head -n1)
        if [ -n "$newer" ]; then
            say "SCORE_FAILED -- $stale is older than $newer (a stale verdict from an \
earlier, smaller set); inspect it and move it aside by hand before re-running"
            return 1
        fi
    done
    return 0
}
check_not_stale || exit 1

rm -f "$STATUS"/*.status 2>/dev/null
running=0
for arm in $GATED_ARMS $SOFT_ARMS; do
    required=1
    case " $SOFT_ARMS " in *" $arm "*) required=0 ;; esac
    for seed in $SEEDS; do
        (
            score_run "$arm" "$seed" "$required"
            printf '%s\n' "$?" >"$STATUS/$arm-$seed.status"
        ) &
        running=$((running + 1))
        if [ "$running" -ge "$PARALLEL" ]; then
            wait
            running=0
        fi
    done
done
wait

failed=""
for arm in $GATED_ARMS $SOFT_ARMS; do
    for seed in $SEEDS; do
        st=$(cat "$STATUS/$arm-$seed.status" 2>/dev/null)
        if [ "${st:-1}" != "0" ]; then
            failed="$failed $arm-$seed"
        fi
    done
done
if [ -n "$failed" ]; then
    say "SCORE_FAILED --$failed"
    exit 1
fi

# ------------------------------------------------- the two descriptive read-outs (4.6)

running=0
for arm in $CODE_ARMS; do
    for seed in $SEEDS; do
        ( readouts_run "$arm" "$seed" ) &
        running=$((running + 1))
        if [ "$running" -ge "$PARALLEL" ]; then
            wait
            running=0
        fi
    done
done
wait

# ------------------------------------------------------------------- gates and report

check_not_stale || exit 1      # again: this run may have added scores since the first check

say "START gates  (log: $LOGS/gates.log)"
if ! "$PY" -B "$RUN" gates --exp "$EXP" --wave 1 >>"$LOGS/gates.log" 2>&1; then
    say "SCORE_FAILED gates -- see $LOGS/gates.log"
    exit 1
fi
say "START report  (log: $LOGS/report.log)"
if ! "$PY" -B "$RUN" report --exp "$EXP" --wave 1 >>"$LOGS/report.log" 2>&1; then
    say "SCORE_FAILED report -- see $LOGS/report.log"
    exit 1
fi

# The verdict is reported, never enforced: a FAIL, a PARTIAL and a VOID are all real
# results of a registered experiment and none of them is a broken script.  INVALID is the
# one exception -- it means the build did not do what it says, and nothing may be claimed
# from these runs at all.
VERDICT=$("$PY" -B -c "
import json
row = json.load(open('$EXP/gates.json'))
print(row['verdict'], '--', row['reason'],
      '| signatures:', json.dumps(row['signature_summary']))
")
say "VERDICT $VERDICT"
case "$VERDICT" in
    INVALID*) say "SCORE_DONE (INVALID -- report nothing from these runs)"; exit 1 ;;
esac
say "SCORE_DONE"
exit 0
