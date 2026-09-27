#!/usr/bin/env bash
#
# experiment 21 / M1 "new names" -- WAVE 3: read the six final checkpoints.
#
#   score (6 runs)  ->  gates  ->  report
#
# Scoring is the fixed external loop (`astra_canonical_operator.execute`) through the
# unmodified `astra_canonical_operator_run.score_cell`, on the FINAL checkpoint only.
# Each checkpoint is hashed before it is loaded and its stored parameter fingerprint is
# re-derived after loading; a mismatch aborts that run's scoring.
#
#   control    one scoring of the ten gated cells.
#   treatment  TWO scorings of the SAME panel files -- training-pool codes and reserved
#              codes -- plus, on the reserved pass only, the descriptive 64-person cells
#              (256 facts), which are reported and never gated.
#
# Measured on this Mac with two concurrent processes: about 35 s for a control run and
# about 82 s for a treatment run at 512 units per cell, so the whole wave is a few
# minutes.  Scoring is run three jobs at a time rather than six: it is the reading of a
# frozen checkpoint, nothing is timed against a deadline, and leaving headroom keeps the
# machine usable.
#
# Nothing is overwritten: a scores/<arm>-<seed>.json already on disk is SKIPPED, and
# gates.json / report.txt are written only if absent (`gates` and `report` always print
# their result, so a re-run still shows the verdict).
#
# No PYTHONPATH is set, deliberately (see run_data.sh).
#
# Usage:  bash run_score.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames21.py

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

ARMS="control treatment"
SEEDS="2100 2101 2102"
PARALLEL=3

LOGS=$EXP/logs
STATUS=$LOGS/.status-score
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" "$EXP/scores" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [score] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

score_run() {
    local arm=$1 seed=$2
    local name=$arm-$seed
    local out=$EXP/scores/$name.json
    local log=$LOGS/score-$name.log
    local rc

    if [ -f "$out" ]; then
        say "SKIP $name -- $out already present"
        return 0
    fi
    if [ ! -f "$EXP/runs/$name/completion.json" ]; then
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
    say "OK $name"
    return 0
}

say "wave start: score 6 runs ($PARALLEL at a time) -> gates -> report"

rm -f "$STATUS"/*.status 2>/dev/null
running=0
for arm in $ARMS; do
    for seed in $SEEDS; do
        (
            score_run "$arm" "$seed"
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
for arm in $ARMS; do
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

# ------------------------------------------------------------------- gates and report

say "START gates  (log: $LOGS/gates.log)"
if ! "$PY" -B "$RUN" gates --exp "$EXP" >>"$LOGS/gates.log" 2>&1; then
    say "SCORE_FAILED gates -- see $LOGS/gates.log"
    exit 1
fi
say "START report  (log: $LOGS/report.log)"
if ! "$PY" -B "$RUN" report --exp "$EXP" >>"$LOGS/report.log" 2>&1; then
    say "SCORE_FAILED report -- see $LOGS/report.log"
    exit 1
fi

# The verdict is reported, never enforced: a FAIL, a PARTIAL and a VOID are all real
# results of a registered experiment and none of them is a broken script.
VERDICT=$("$PY" -B -c "
import json
row = json.load(open('$EXP/gates.json'))
print(row['verdict'], '--', row['reason'],
      '| signatures:', json.dumps(row['signature_summary']))
")
say "VERDICT $VERDICT"
say "SCORE_DONE"
exit 0
