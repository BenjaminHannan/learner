#!/usr/bin/env bash
#
# experiment 27 / M1-F "new names", name scale FROZEN at 1.2 -- WAVE 0: the data side.
#
#   pool (a hash-checked REFERENCE to experiment 21's frozen pool -- nothing is re-drawn)
#     ->  panels (ten fresh gated cells + the data audit)
#     ->  control equivalence   (this file's control arm IS experiment 21's control)
#     ->  treatment equivalence (arm L started at 0.13856 IS experiment 21's treatment)
#     ->  inertness             (the every-100-update trace changes no parameter)
#
# Everything here is outcome-independent and must finish before a single registered
# update is trained.  Nothing in this wave touches a registered checkpoint.
#
#   pool        design 4.3: experiment 27 REUSES experiment 21's 4,096-code pool and its
#               3,072 / 1,024 train / reserved split.  `pool` writes pool/pool-ref.json,
#               which records the source folder and the sha256 of pool.json and of all
#               three tensors; every later command re-verifies all four before use.  If
#               experiment 21's pool ever changes on disk, every command here aborts.
#   panels      design 4.3: a FRESH ten-cell suite in a new namespace and seed base, so
#               no panel question is shared with experiment 21.  Ten gated cells at 512
#               units (c1..c6, p12-1..3, s3); NO 64-person descriptive cells (design 4.2
#               does not ask for them and experiment 21 found them uninformative).  The
#               audit checks within-suite disjointness, overlap against every development
#               source on this machine, and a PARTIAL replay of THIS experiment's
#               training stream (the replay borrows seed 2103; see BUILD-NOTES C3).  The
#               COMPLETE guarantee is still the run-time `forbidden` check the trainer
#               applies at every one of the 6,000 updates.
#   control     design 4.3: 50 updates of this file's control path, compared to the
#               registered training functions after EVERY update, AND compared tensor for
#               tensor to `fable_newnames21.train_run('control', ...)` on the same seed
#               and the same data wave.  If this is not exactly equal, the control arm is
#               not experiment 21's control and there is nothing to compare against.
#   treatment   design 4.3: 50 updates of arm L with code_scale started at 0.13856 --
#               experiment 21's number -- against `fable_newnames21`'s treatment, tensor
#               for tensor.  This is what makes 1.2 the ONLY scientific change.
#   inertness   design 4.6: 200 updates of arms F and L with the trace on and with it off.
#               Identical initial and final fingerprints, identical FLOP counts.
#
# Nothing is overwritten.  A stage whose marker file is already present is SKIPPED; a
# folder that exists WITHOUT its marker is a half-built artifact and this script refuses
# to touch it.  This script deletes nothing.
#
# No PYTHONPATH is set, deliberately: scripts/fable_newnames27.py imports
# fable_newnames21, which puts the base checkout and its scripts/ on sys.path itself, and
# premonition_memnn.py reads the base checkout's runtime.local.json import_roots to find
# torch.  A PYTHONPATH here could shadow that.
#
# Expected wall-clock: about 4 minutes (panels and their audit dominate; the three proofs
# are about 15 s, 15 s and 50 s).
#
# Usage:  bash run_data.sh
#
set -u
set -o pipefail

EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames27-20260921
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
RUN=$W/scripts/fable_newnames27.py
POOL_SOURCE=$W/artifacts/fable-newnames21-20260920

export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

PANEL_N=512
AUDIT_UPDATES=100        # PARTIAL by design; see the note above
EQUIV_UPDATES=50
EQUIV_SEED=0             # a registered grow-blind run exists on disk for this seed
L_EQUIV_SEED=9           # a fixture seed: this proof is about the number, not the seed
INERT_UPDATES=200        # two trace rows at the registered every-100
INERT_SEED=9

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

say "wave start: pool -> panels -> audit -> control/treatment equivalence -> inertness"

# ----------------------------------------------------------- stage 1: the reused pool

if [ ! -f "$POOL_SOURCE/pool/pool.json" ]; then
    say "DATA_FAILED pool -- experiment 21's pool is not at $POOL_SOURCE"
    exit 1
fi
check_folder pool "$EXP/pool" pool-ref.json
case $? in
    0)  run_step pool "$PY" -B "$RUN" pool --out "$EXP" --source "$POOL_SOURCE" || exit 1 ;;
    2)  exit 1 ;;
esac

# ---------------------------------------------------------------- stage 2: the panels

check_folder panels "$EXP/panels" manifest.json
case $? in
    0)  run_step panels "$PY" -B "$RUN" panels \
            --out "$EXP" \
            --n "$PANEL_N" \
            --audit-updates "$AUDIT_UPDATES" || exit 1 ;;
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
    say "SKIP control-equivalence -- already present"
else
    run_step control-equivalence "$PY" -B "$RUN" control-equivalence \
        --exp "$EXP" --seed "$EQUIV_SEED" --updates "$EQUIV_UPDATES" \
        --out "$EXP/control-equivalence.json" || exit 1
fi

if ! "$PY" -B -c "
import json, sys
row = json.load(open('$EXP/control-equivalence.json'))
if not row['fingerprints_equal']:
    print('control path diverged at update', row['first_differing_update']); sys.exit(1)
if not row['losses_equal']:
    print('control path losses differ; max', row['max_abs_loss_difference']); sys.exit(1)
against = row['against_experiment_21']
if not (against['initial_equal'] and against['final_equal'] and against['tensors_equal']):
    print('NOT experiment 21\'s control:', against['mismatched_tensors']); sys.exit(1)
anchor = row['registered_reference']
if anchor and not anchor['initial_matches']:
    print('registered initial fingerprint not reproduced'); sys.exit(1)
print(row['updates'], 'updates: identical fingerprints and losses;',
      against['tensors_compared'], 'tensors identical to experiment 21;',
      'registered anchor', 'reproduced' if anchor else 'not on disk')
" >>"$LOGS/control-equivalence.log" 2>&1; then
    say "DATA_FAILED control-equivalence -- the control arm is NOT experiment 21's \
control; see $LOGS/control-equivalence.log"
    exit 1
fi
say "OK control-equivalence ($(tail -n1 "$LOGS/control-equivalence.log"))"

# ----------------------------------------------------- stage 4: treatment equivalence

if [ -f "$EXP/treatment-equivalence.json" ]; then
    say "SKIP treatment-equivalence -- already present"
else
    run_step treatment-equivalence "$PY" -B "$RUN" treatment-equivalence \
        --exp "$EXP" --seed "$L_EQUIV_SEED" --updates "$EQUIV_UPDATES" \
        --out "$EXP/treatment-equivalence.json" || exit 1
fi

if ! "$PY" -B -c "
import json, sys
row = json.load(open('$EXP/treatment-equivalence.json'))
if not (row['initial_equal'] and row['final_equal'] and row['tensors_equal']):
    print('arm L at 0.13856 is NOT experiment 21\'s treatment:',
          row['mismatched_tensors']); sys.exit(1)
if abs(row['code_scale_start'] - 0.13856406460551018) > 1e-12:
    print('wrong start value', row['code_scale_start']); sys.exit(1)
print(row['updates'], 'updates at code_scale 0.13856:', row['tensors_compared'],
      'tensors identical to experiment 21\'s treatment')
" >>"$LOGS/treatment-equivalence.log" 2>&1; then
    say "DATA_FAILED treatment-equivalence -- 1.2 would not be the only change; see \
$LOGS/treatment-equivalence.log"
    exit 1
fi
say "OK treatment-equivalence ($(tail -n1 "$LOGS/treatment-equivalence.log"))"

# ---------------------------------------------------------- stage 5: the inert trace

if [ -f "$EXP/inertness.json" ]; then
    say "SKIP inertness -- already present"
else
    run_step inertness "$PY" -B "$RUN" inertness \
        --exp "$EXP" --seed "$INERT_SEED" --updates "$INERT_UPDATES" \
        --out "$EXP/inertness.json" || exit 1
fi

if ! "$PY" -B -c "
import json, sys
row = json.load(open('$EXP/inertness.json'))
if not row['all_inert']:
    print('the trace is NOT inert:', row['arms']); sys.exit(1)
for arm, entry in row['arms'].items():
    if entry['trace_rows_on'] < 1:
        print(arm, 'recorded no trace rows; the proof is vacuous'); sys.exit(1)
print(row['updates'], 'updates, arms', sorted(row['arms']),
      ': identical fingerprints and FLOPs with the trace on and off')
" >>"$LOGS/inertness.log" 2>&1; then
    say "DATA_FAILED inertness -- see $LOGS/inertness.log"
    exit 1
fi
say "OK inertness ($(tail -n1 "$LOGS/inertness.log"))"

say "DATA_DONE"
exit 0
