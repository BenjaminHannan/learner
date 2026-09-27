#!/usr/bin/env bash
#
# experiment 21 / M1 "new names" -- WAVE 1: the data side.
#
#   pool  ->  panels (ten gated cells + 64-person descriptive cells + data audit)
#         ->  control-equivalence proof
#
# Everything here is outcome-independent and must finish before a single update is
# trained.  Nothing in this wave touches a model checkpoint.
#
#   pool        4,096 fixed codes at the model's embedding width, unit-norm Gaussian
#               directions, split 3,072 train / 1,024 RESERVED by a fixed permutation.
#               Written once with its sha256; `pool` refuses an existing folder.
#   panels      `fable_confirmation_panels.build_operator_suite` -- the registered
#               generator with this experiment's namespace and seed passed explicitly --
#               builds c1..c6, p12-1..3 and s3 at 512 units each, writes
#               forbidden-semantics.json, then the 64-person descriptive cells, then the
#               audit: within-suite disjointness (the builder's own hard failure), overlap
#               against every development source on this machine, and a PARTIAL replay of
#               the training stream.  The audit is advisory only in one direction: the
#               COMPLETE guarantee that these runs' training worlds never appear in the
#               panels is the run-time `forbidden` check the trainer applies at every one
#               of the 6,000 updates, which aborts the run on a collision.
#   equivalence 50 updates of this file's control path against the registered training
#               functions called directly, compared by parameter fingerprint after EVERY
#               update, plus the registered grow-blind seed-0 initial fingerprint on disk.
#               If this does not come out exactly equal, the control arm is not the frozen
#               recipe and there is no point training anything.
#
# Nothing is overwritten.  A stage whose marker file is already present is SKIPPED; a
# folder that exists WITHOUT its marker is a half-built artifact and this script refuses
# to touch it (the generators create their folders with exist_ok=False and would abort
# anyway).  This script deletes nothing.
#
# No PYTHONPATH is set, deliberately: scripts/fable_newnames21.py puts the base checkout
# and its scripts/ on sys.path itself, and premonition_memnn.py reads the base checkout's
# runtime.local.json import_roots to find torch.  A PYTHONPATH here could shadow that.
#
# Usage:  bash run_data.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920/fixtures/exprun
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames21.py

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

PANEL_N=16
WIDE_WORLDS=8
AUDIT_UPDATES=10        # PARTIAL by design; see the note above
EQUIV_UPDATES=8
EQUIV_SEED=0             # a registered grow-blind run exists on disk for this seed

LOGS=$EXP/logs
WAVES=$LOGS/waves.log
mkdir -p "$LOGS" || exit 1

ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
say() { printf '%s [data] %s\n' "$(ts)" "$*" | tee -a "$WAVES"; }

check_folder() {   # check_folder <name> <folder> <marker> -> 0 build, 1 skip, 2 refuse
    local name=$1 folder=$2 marker=$3
    if [ -f "$folder/$marker" ]; then
        say "SKIP $name -- $folder/$marker already present (refusing to overwrite)"
        return 1
    fi
    if [ -d "$folder" ]; then
        say "DATA_FAILED $name -- $folder exists but has no $marker (half-built \
artifact); inspect it and remove it by hand before re-running"
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

say "wave start: pool -> panels -> audit -> control-equivalence"

# --------------------------------------------------------------------- stage 1: pool

check_folder pool "$EXP/pool" pool.json
case $? in
    0)  run_step pool "$PY" -B "$RUN" pool --out "$EXP" --namespace newnames21/fixture-pool || exit 1 ;;
    2)  exit 1 ;;
esac

# --------------------------------------------------------------------- stage 2: panels

check_folder panels "$EXP/panels" manifest.json
case $? in
    0)  run_step panels "$PY" -B "$RUN" panels \
            --out "$EXP" \
            --n "$PANEL_N" \
            --wide-worlds "$WIDE_WORLDS" \
            --audit-updates "$AUDIT_UPDATES" --namespace newnames21-fixture-run --seed-base 999000003 || exit 1 ;;
    2)  exit 1 ;;
esac

# The audit is a hard gate on everything it DOES check: any overlap, or any development
# source that could not be checked, is a failure here and not a footnote in a JSON file.
if [ ! -f "$EXP/panels/audit.json" ]; then
    say "DATA_FAILED audit -- $EXP/panels/audit.json is missing"
    exit 1
fi
if ! "$PY" -B -c "
import json, sys
report = json.load(open('$EXP/panels/audit.json'))
if not report['all_clear']:
    print('audit failures:', report['failures']); sys.exit(1)
unchecked = [s['name'] for s in report['sources'] if not s.get('checked')]
if unchecked:
    print('UNVERIFIED development sources:', unchecked); sys.exit(1)
replay = report['replay']
if replay is None:
    print('no training-stream replay was run'); sys.exit(1)
print('audit clear; panel signatures', report['panel_signatures'],
      '; replay', replay['updates'], 'of', replay['full_updates'], 'updates (PARTIAL)')
" >>"$LOGS/audit.log" 2>&1; then
    say "DATA_FAILED audit -- see $LOGS/audit.log"
    exit 1
fi
say "OK audit ($(tail -n1 "$LOGS/audit.log"))"

# ------------------------------------------------------- stage 3: control equivalence

if [ -f "$EXP/control-equivalence.json" ]; then
    say "SKIP equivalence -- control-equivalence.json already present"
else
    run_step equivalence "$PY" -B "$RUN" train \
        --exp "$EXP" \
        --seed "$EQUIV_SEED" \
        --equivalence "$EQUIV_UPDATES" \
        --equivalence-out "$EXP/control-equivalence.json" || exit 1
fi

if ! "$PY" -B -c "
import json, sys
row = json.load(open('$EXP/control-equivalence.json'))
if not row['fingerprints_equal']:
    print('control path diverged at update', row['first_differing_update']); sys.exit(1)
if not row['losses_equal']:
    print('control path losses differ; max', row['max_abs_loss_difference']); sys.exit(1)
anchor = row['registered_reference']
if anchor and not anchor['initial_matches']:
    print('registered initial fingerprint not reproduced'); sys.exit(1)
print(row['updates'], 'updates: identical parameter fingerprints and identical losses;',
      'registered anchor', 'reproduced' if anchor else 'not on disk')
" >>"$LOGS/equivalence.log" 2>&1; then
    say "DATA_FAILED equivalence -- the control arm is NOT the registered recipe; \
see $LOGS/equivalence.log"
    exit 1
fi
say "OK equivalence-check ($(tail -n1 "$LOGS/equivalence.log"))"

say "DATA_DONE"
exit 0
