#!/usr/bin/env bash
#
# novelty-19b -- THE DATA WAVE: buffers, then panels, then the audit.
#
#   1. buffers --seed S    for 1900, 1901, 1902, IN PARALLEL (3 jobs)
#   2. dev-panels          ONCE, after all three buffer folders exist
#   3. audit --seed S      for 1900, 1901, 1902, IN PARALLEL (3 jobs)
#
# ORDER MATTERS and is not a convenience: the panels exclude the 19b buffer worlds at
# both the question-signature and the world-signature level, so the buffers must exist
# before `dev-panels` runs.  Running them the other way round would silently produce
# panels that do not exclude the training worlds, which is the one thing these fresh
# cells are for.  This script therefore refuses to build panels until all three buffer
# manifests are on disk.
#
# The audit is MANDATORY and is the gate, not a summary: `audit` exits non-zero on any
# failure, and its own roster treats an ABSENT check as a failure ("checks run: n/N
# ABSENT: [...]").  This script fails loudly on either.
#
# Nothing is overwritten: the data module writes with a refusing writer, so an existing
# buffers-<seed>/manifest.json or dev-panels/manifest.json is SKIPPED here rather than
# rebuilt.  Confirmation panels are NOT built -- they are locked behind
# EXP2/DEV-PASSED.json and are not part of this experiment.
#
# Usage:  bash run_data.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19b-u8-20260920
EXP19=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-novelty19-replay-20260920
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
DATA=$W/scripts/fable_novelty19b_data.py

# No PYTHONPATH: the scripts bootstrap their own sys.path.
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

SEEDS="1900 1901 1902"

LOGS=$EXP/logs
STATUS=$LOGS/.status-data
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" "$STATUS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [data] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

# --------------------------------------------- precondition: experiment 19's memory

# `buffers` consumes, by default and read-only: experiment 19's memory-<seed> (the same
# 1,024 six-person worlds and story bytes), its frozen dev-panels (an exclusion guard)
# and its buffers-<seed> (so U5 can be compared with experiment 19's U buffer).
missing=""
for seed in $SEEDS; do
    for folder in "memory-$seed" "buffers-$seed"; do
        if [ ! -f "$EXP19/$folder/manifest.json" ]; then
            missing="$missing exp19:$folder"
        fi
    done
done
if [ ! -f "$EXP19/dev-panels/manifest.json" ]; then
    missing="$missing exp19:dev-panels"
fi
if [ ! -f "$EXP19/operator-history/manifest.json" ]; then
    missing="$missing exp19:operator-history"
fi
if [ -n "$missing" ]; then
    say "DATA_FAILED -- refusing to start; 19b reuses experiment 19's worlds and excludes \
its artifacts, and cannot find:$missing"
    exit 1
fi
say "precondition OK: experiment 19's memory, buffers, dev-panels and operator-history \
are present (all read-only)"

# ------------------------------------------------------------------- stage 1: buffers

rm -f "$STATUS"/*.status 2>/dev/null

buffers_run() {
    local seed=$1
    local out=$EXP/buffers-$seed
    local log=$LOGS/data-buffers-$seed.log
    local rc
    if [ -f "$out/manifest.json" ]; then
        say "SKIP buffers-$seed -- manifest.json already present (never rebuilt)"
        return 0
    fi
    say "START buffers-$seed  (log: $log)"
    "$PY" -B "$DATA" buffers --seed "$seed" --experiment "$EXP" >>"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "DATA_FAILED buffers-$seed -- exit $rc, see $log"
        return 1
    fi
    if [ ! -f "$out/manifest.json" ]; then
        say "DATA_FAILED buffers-$seed -- exit 0 but $out/manifest.json was not written"
        return 1
    fi
    say "OK buffers-$seed"
    return 0
}

say "stage 1: buffers for 3 seeds in parallel"
for seed in $SEEDS; do
    (
        buffers_run "$seed"
        printf '%s\n' "$?" >"$STATUS/buffers-$seed.status"
    ) &
done
wait

failed=""
for seed in $SEEDS; do
    st=$(cat "$STATUS/buffers-$seed.status" 2>/dev/null)
    [ "${st:-1}" != "0" ] && failed="$failed buffers-$seed"
done
if [ -n "$failed" ]; then
    say "DATA_FAILED --$failed"
    exit 1
fi
say "stage 1 complete: three buffer folders present"

# --------------------------------------------------------------- stage 2: dev-panels

# The panels exclude the buffer worlds, so this is gated on stage 1 having finished --
# not merely started.
for seed in $SEEDS; do
    if [ ! -f "$EXP/buffers-$seed/manifest.json" ]; then
        say "DATA_FAILED -- refusing to build panels: buffers-$seed is not complete, and \
the panels must exclude every 19b buffer world"
        exit 1
    fi
done

if [ -f "$EXP/dev-panels/manifest.json" ]; then
    say "SKIP dev-panels -- manifest.json already present (never rebuilt)"
else
    say "stage 2: dev-panels (38 cells)  (log: $LOGS/data-dev-panels.log)"
    "$PY" -B "$DATA" dev-panels --experiment "$EXP" >>"$LOGS/data-dev-panels.log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "DATA_FAILED dev-panels -- exit $rc, see $LOGS/data-dev-panels.log"
        exit 1
    fi
    if [ ! -f "$EXP/dev-panels/manifest.json" ]; then
        say "DATA_FAILED dev-panels -- exit 0 but no manifest.json was written"
        exit 1
    fi
    say "OK dev-panels"
fi

# -------------------------------------------------------------------- stage 3: audit

audit_run() {
    local seed=$1
    local out=$EXP/audit/audit-$seed.json
    local log=$LOGS/data-audit-$seed.log
    local rc
    mkdir -p "$EXP/audit" || return 1
    say "START audit-$seed  (log: $log)"
    "$PY" -B "$DATA" audit --seed "$seed" --experiment "$EXP" >"$log" 2>&1
    rc=$?
    if [ "$rc" -ne 0 ]; then
        say "DATA_FAILED audit-$seed -- exit $rc (the audit itself refused), see $log"
        return 1
    fi
    # the subcommand PRINTS its verdict; the layout keeps it at audit/audit-<seed>.json,
    # so the JSON object is split off from the trailing "checks run:" summary line
    "$PY" -B -c "
import json, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
doc = json.loads(text[:text.rindex('}') + 1])
Path(sys.argv[2]).write_text(json.dumps(doc, indent=2))
" "$log" "$out"
    if [ ! -f "$out" ]; then
        say "DATA_FAILED audit-$seed -- the verdict could not be saved to $out, see $log"
        return 1
    fi
    # an ABSENT check is a failure in the module's own roster; refuse on it here too,
    # so a truncated roster can never read as a clean audit
    if grep -q 'ABSENT' "$log"; then
        say "DATA_FAILED audit-$seed -- the audit ran with ABSENT checks: \
$(grep 'ABSENT' "$log" | head -1)"
        return 1
    fi
    say "OK audit-$seed  ($(grep -m1 'checks run:' "$log" || echo 'checks run: ?'))"
    return 0
}

say "stage 3: audit for 3 seeds in parallel (mandatory; an ABSENT check is a failure)"
for seed in $SEEDS; do
    (
        audit_run "$seed"
        printf '%s\n' "$?" >"$STATUS/audit-$seed.status"
    ) &
done
wait

failed=""
for seed in $SEEDS; do
    st=$(cat "$STATUS/audit-$seed.status" 2>/dev/null)
    [ "${st:-1}" != "0" ] && failed="$failed audit-$seed"
done
if [ -n "$failed" ]; then
    say "DATA_FAILED --$failed"
    exit 1
fi

say "stage 3 complete: all three audits passed with a full roster"
say "DATA_DONE"
exit 0
