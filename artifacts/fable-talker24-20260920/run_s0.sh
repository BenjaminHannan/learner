#!/usr/bin/env bash
# Talker 24 -- S0 smoke test (design section 5, S0).
#
#   "Size S (~6M), ~30M tokens from one SimpleStories shard + generated fact sentences.
#    Includes the GRU-mouth side arm and a 3-minute throughput benchmark of size M."
#
# The whole thing is TIME-BOXED to <= 25 minutes of training by --max-minutes, so it ends
# when the clock says so and not when a step counter does.  Every stage writes its own
# result.json; nothing here needs to be watched.
#
# USAGE
#   bash run_s0.sh                        # full S0, needs a GPU
#   S0_DRY=1 bash run_s0.sh               # ~2-minute CPU dry run (what the Mac does)
#   S0_SHARDS=/path/to/shards bash run_s0.sh
#
# ENVIRONMENT
#   PY          python to use            (default: the project's uv python, else python3)
#   S0_OUT      output root              (default: artifacts/fable-talker24-20260920/s0)
#   S0_SHARDS   token shards (task 1)    (default: <artifacts>/shards, synthetic if absent)
#   S0_DIALOGUES artifacts root with dialogues/ (task 2; default: <artifacts>)
#   S0_DEVICE   cuda | cpu               (default: cuda, or cpu when S0_DRY=1)
#   S0_DRY      1 = minutes become seconds and the preset shrinks
#
# THE WINDOWS COMMAND LINE IS IN README-S0.md -- BensPC is driven over ssh with PowerShell
# and does not run this file.
set -u -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SCRIPTS="$REPO/scripts"

PY="${PY:-}"
if [ -z "$PY" ]; then
  UVPY="$HOME/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12"
  if [ -x "$UVPY" ]; then PY="$UVPY"; else PY="python3"; fi
fi

S0_OUT="${S0_OUT:-$HERE/s0}"
S0_SHARDS="${S0_SHARDS:-$HERE/shards}"
S0_DIALOGUES="${S0_DIALOGUES:-$HERE}"
S0_DRY="${S0_DRY:-0}"
if [ "$S0_DRY" = "1" ]; then
  # The dry run keeps the REAL preset S -- only the clock shrinks.  (A smaller preset
  # would have a smaller vocabulary than the shards and would quietly train on synthetic
  # sentences instead, which is exactly the confusion this run exists to avoid.)
  S0_DEVICE="${S0_DEVICE:-cpu}"; PRESET=S
  M_AE=0.4; M_GRU=0.3; M_SLOT=0.3; M_THINK=0.3       # minutes
  BENCH_PRESETS="S M"; BENCH_STEPS=3; BENCH_BATCH=4; BENCH_LEN=16
  MICRO=8; EVAL_N=32; DIALOGUES_N=512
else
  S0_DEVICE="${S0_DEVICE:-cuda}"; PRESET=S
  M_AE=11; M_GRU=3; M_SLOT=3; M_THINK=3              # 20 min of training
  BENCH_PRESETS="M L XL"; BENCH_STEPS=20; BENCH_BATCH=32; BENCH_LEN=48
  MICRO=64; EVAL_N=512; DIALOGUES_N=4096
fi

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
export PYTHONUNBUFFERED=1

mkdir -p "$S0_OUT"
LOG="$S0_OUT/s0.log"
STARTED=$(date +%s)
FAILURES=0

say() { printf '\n=== %s ===\n' "$*" | tee -a "$LOG"; }
note() { printf '%s\n' "$*" | tee -a "$LOG"; }

run() {                       # run <name> <args...>; never aborts the script
  local name="$1"; shift
  say "$name"
  note "\$ $PY -B $*"
  "$PY" -B "$@" 2>&1 | tee -a "$LOG"
  local code=${PIPESTATUS[0]}
  if [ "$code" -ne 0 ]; then
    note "!! $name exited $code"
    FAILURES=$((FAILURES + 1))
  fi
  return 0
}

# --dialogue-split train streams the practice dialogues STRAIGHT FROM THE GENERATOR
# (INTERFACE-dialogues.md section 1 ships no training file: a record is ~18 kB, so a
# million would be ~18 GB).  Indices start at 100,000, well past the sealed evaluation
# block 0..999 -- generating from index 0 would reproduce the test set exactly.
COMMON=(--device "$S0_DEVICE" --preset "$PRESET" --micro-batch "$MICRO"
        --shards "$S0_SHARDS" --dialogues "$S0_DIALOGUES"
        --dialogue-split train --generate-split L1 --symbol-mode m0
        --synthetic-dialogues "$DIALOGUES_N"
        --checkpoint-minutes 2 --checkpoint-steps 500 --log-every 25)

say "Talker 24 -- S0, $(date -u '+%Y-%m-%d %H:%M:%SZ')"
note "python    $PY"
note "device    $S0_DEVICE   preset $PRESET   dry-run $S0_DRY"
note "shards    $S0_SHARDS"
note "dialogues $S0_DIALOGUES"
note "out       $S0_OUT"
"$PY" -B "$SCRIPTS/fable_talker24_model.py" sizes 2>&1 | tee -a "$LOG"
"$PY" -B "$SCRIPTS/fable_talker24_model.py" floor-plan 2>&1 | tee -a "$LOG"
"$PY" -B -c "import sys; sys.path.insert(0, '$SCRIPTS'); import fable_talker24_loader as L; print(L.describe_assumptions())" 2>&1 | tee -a "$LOG"

# 1. the autoencoder: a sentence -> 416 numbers -> the same sentence back.
run "1/7 autoencoder (transformer mouth), <= $M_AE min" \
    "$SCRIPTS/fable_talker24_train.py" train --stage autoencode \
    --steps 1000000 --max-minutes "$M_AE" --out "$S0_OUT/autoencode" "${COMMON[@]}"

# 2. the GRU side arm -- the D-decision's control, same data, same budget shape.
run "2/7 GRU-mouth side arm, <= $M_GRU min" \
    "$SCRIPTS/fable_talker24_train.py" train --stage autoencode --gru-mouth \
    --steps 1000000 --max-minutes "$M_GRU" --out "$S0_OUT/autoencode-gru" "${COMMON[@]}"

# 3. the typed slots: act, relation path, flags and the two pointers.
run "3/7 slot fine-tuning, <= $M_SLOT min" \
    "$SCRIPTS/fable_talker24_train.py" train --stage slots \
    --steps 1000000 --max-minutes "$M_SLOT" --out "$S0_OUT/slots" "${COMMON[@]}"

# 4. the thinker, trained through the FROZEN mouth.
run "4/7 thinker through the frozen mouth, <= $M_THINK min" \
    "$SCRIPTS/fable_talker24_train.py" train --stage thinker \
    --steps 1000000 --max-minutes "$M_THINK" --out "$S0_OUT/thinker" "${COMMON[@]}"

# 5. kill and resume -- the S0 mark is "parameter hash identical".
run "5/7 kill test (a real SIGKILL, then a real resume)" \
    "$SCRIPTS/fable_talker24_train.py" kill-test --out "$S0_OUT/kill" \
    --preset tiny --steps 40 --die-at 18 --micro-batch 8

# 6. the model marks: reconstruction, whole-thought exactness, the four interventions.
CKPT="$S0_OUT/autoencode/final.pt"
[ -f "$CKPT" ] || CKPT="$(ls -1 "$S0_OUT"/autoencode/step-*.pt 2>/dev/null | tail -1)"
if [ -n "${CKPT:-}" ] && [ -f "$CKPT" ]; then
  run "6/7 S0 model marks on $(basename "$CKPT")" \
      "$SCRIPTS/fable_talker24_train.py" eval --checkpoint "$CKPT" --n "$EVAL_N" \
      --device "$S0_DEVICE" --shards "$S0_SHARDS" --dialogues "$S0_DIALOGUES" \
      --json "$S0_OUT/s0-marks.json"
  run "6b/7 intervention harness (full report)" \
      "$SCRIPTS/fable_talker24_interventions.py" report --checkpoint "$CKPT" \
      --stage S0 --json "$S0_OUT/interventions.json"
else
  note "!! no autoencoder checkpoint; skipping the model marks"
  FAILURES=$((FAILURES + 1))
fi

# 7. throughput, so the hours in section 2.4 stop being a guess.
run "7/7 throughput benchmark ($BENCH_PRESETS)" \
    "$SCRIPTS/fable_talker24_train.py" bench --presets $BENCH_PRESETS \
    --steps "$BENCH_STEPS" --batch "$BENCH_BATCH" --length "$BENCH_LEN" \
    --device "$S0_DEVICE" --json "$S0_OUT/throughput.json"

ELAPSED=$(( $(date +%s) - STARTED ))
say "S0 finished in $((ELAPSED/60)) min $((ELAPSED%60)) s with $FAILURES failing step(s)"
note "log            $LOG"
note "model marks    $S0_OUT/s0-marks.json"
note "interventions  $S0_OUT/interventions.json"
note "throughput     $S0_OUT/throughput.json"
note "kill test      $S0_OUT/kill/kill-test.json"
note ''
note 'READ THIS BEFORE QUOTING ANY NUMBER: if the run printed "synthetic ... NOT real'
note 'text", build task 1 had shipped no shards and these numbers measure the plumbing'
note 'only. The same goes for "dialogues: synthetic". Both strings are in every'
note 'result.json on purpose.'
note ''
note 'If size-M throughput came out under 60,000 tokens/s, section 2.4 says the hours are'
note 're-quoted to Ben BEFORE anything long starts.'
exit $(( FAILURES > 0 ? 1 : 0 ))
