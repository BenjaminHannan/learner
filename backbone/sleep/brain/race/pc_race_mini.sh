#!/usr/bin/env bash
# Race-mini round 1, both sides, on BensPC (WSL). Started detached; waits for its go flag (default pc-jobs/handoff/GO-RACE-MINI, consumed) and a
# free GPU, runs every arm-seed in order (each skipped when its DONE file exists, so a rerun resumes), then writes its done flag.
# Pause between arm-seeds: create pc-jobs/handoff/PAUSE-RACE-MINI; the job finishes the running arm-seed, frees GPU-BUSY.txt, and waits until
# the file is gone and GPU-BUSY.txt is empty again. Addendum 1 (PROTOCOL-mini): 75 steps a night; the validity check is the 300-step vs 75-step dose check.
# Addendum 2: LFM3-1.7B on a llama.cpp Q4_0 (group 32) fake-quantized base (RM_MODEL overrides; arm args after it win), out dir fresh.
#   bash pc_race_mini.sh <src dir with backbone/> <out dir>
set -uo pipefail
SRC=${1:?src}; OUT=${2:?out}
J=${PCJ:-/mnt/c/Users/benja/pc-jobs}
BUSY=${PCBUSY:-/mnt/c/Users/benja/GPU-BUSY.txt}
CARD=$J/race-mini.md
GO=${RM_GO:-$J/handoff/GO-RACE-MINI}
PAUSE=${RM_PAUSE:-$J/handoff/PAUSE-RACE-MINI}
DONEFLAG=${RM_DONEFLAG:-$J/handoff/RACE-MINI-DONE}
MA=${RM_MODEL-"--model LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd --base q4_0"}
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14}  # a capped run fails with a real OOM instead of spilling into system memory (WSL)
mkdir -p "$OUT"
[ -f ~/bbvenv/bin/activate ] && source ~/bbvenv/bin/activate
unset PYTORCH_CUDA_ALLOC_CONF  # pc-launch-route: expandable segments misbehave under WSL
B=$SRC/backbone/sleep/brain
T=$B/race/tapes
W2=$B/data/week2.json; W1=$B/data/week1.json
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/job.log"; }

claim() {
  echo "race-mini (sleep race, both sides) since $(date -u +%FT%TZ); card $CARD; pause: touch $PAUSE" > "$BUSY"
  printf "# race-mini\nowner: Make whole-model sleep beat the add-on (+ add-on side)\nlog: %s/job.log\nstarted: %s\npause between arm-seeds: create %s\n" "$OUT" "$(date -u +%FT%TZ)" "$PAUSE" > "$CARD"
}
log "waiting for $GO and an empty GPU-BUSY.txt"
until [ -f "$GO" ] && { [ ! -s "$BUSY" ]; }; do sleep 60; done
[ -n "${RM_GO_KEEP:-}" ] || rm -f "$GO"; claim  # RM_GO_KEEP: another job still reads the flag
RC=0
finish() {
  : > "$BUSY"; rm -f "$CARD"
  mkdir -p "$(dirname "$DONEFLAG")"; echo "$RC $(date -u +%FT%TZ)" > "$DONEFLAG"
  log "finished rc=$RC; wrote $DONEFLAG"
}
trap finish EXIT

run() {  # name, then race_mini args
  local n=$1; shift
  if [ -f "$OUT/$n/DONE" ]; then log "skip $n (done)"; return 0; fi
  if [ -f "$PAUSE" ]; then
    : > "$BUSY"; rm -f "$CARD"; log "paused before $n (GPU-BUSY.txt freed)"
    until [ ! -f "$PAUSE" ] && [ ! -s "$BUSY" ]; do sleep 60; done
    claim; log "resumed"
  fi
  log "start $n: $*"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader >> "$OUT/job.log" 2>/dev/null
  python "$B/race/race_mini.py" --out "$OUT/$n" $MA "$@" ${RM_EXTRA:-} > "$OUT/$n.stdout" 2>&1
  local r=$?
  log "end $n rc=$r"
  [ $r -eq 0 ] || RC=$r
  return 0
}
gap() {  # C2+C4 forward recall of run $2 minus run $1, in points (empty if missing)
  python - "$OUT/$1/result.json" "$OUT/$2/result.json" <<'PY' 2>/dev/null
import json, sys
a, b = (json.load(open(p))["scores"]["final"]["forward"]["C24"] for p in sys.argv[1:3])
print(round(100 * (b - a), 2))
PY
}
R2="--tape $T/tape_week2.json --week $W2"

# Addendum 1 (PROTOCOL-mini): the race runs at 75 steps a night (the 300-step K2 add-on control scored 0.98 final, at the ceiling).
# 1. validity check, seed 1: the 300-step control (lora_s1) must beat the 75-step control by >= 2 points
S="--steps 75"
run lora_s1 $R2 --storage lora --seed 1
run c75_s1 $R2 --storage lora $S --seed 1
G=$(gap c75_s1 lora_s1); log "validity seed 1: 300-step - 75-step = ${G:-missing} points (fail if < 2)"
if [ -z "${RM_SKIP_GATE:-}" ] && { [ -z "$G" ] || python -c "import sys; sys.exit(0 if float('$G') < 2 else 1)"; }; then
  log "VALIDITY FAILED or missing: stopping (both sides rethink)"; RC=${RC:-0}; [ $RC -eq 0 ] && RC=3; exit
fi
# 1b. the second control seed, then the ceiling decision (addendum 1), logged from c75 alone before any treatment arm runs
run c75_s2 $R2 --storage lora $S --seed 2
H=$(python - "$OUT" <<'PY'
import json, sys, pathlib
try:
    v = [json.loads((pathlib.Path(sys.argv[1]) / f"c75_s{k}" / "result.json").read_text())["scores"]["final"]["forward"]["C24"] for k in (1, 2)]
    print(f"{sum(v) / 2:.4f} {'night4' if sum(v) / 2 >= 0.90 else 'final'}")
except Exception as e:
    print(f"missing final ({type(e).__name__})")
PY
)
log "CEILING DECISION (c75 only): pooled c75 final C2+C4 = ${H% *}; headline = ${H##* }"; echo "$H" > "$OUT/headline.txt"
# 2. seed 1: add-on LoRA+ x16, whole-model lr scout (Week-1 tape, 3 nights, fixed rule), whole-model qs
run lp16_s1 $R2 --storage lora --lora-plus 16 $S --seed 1
for LR in 1e-3 3e-3 1e-2; do
  run scout_qs_$LR --tape $T/tape_week1.json --week $W1 --storage qs --lr $LR $S --nights 3 --mid 99 --arc-n 100 --seed 1
done
QLR=$(python - "$OUT" <<'PY'
import json, sys, pathlib
best = None
for lr in ("1e-3", "3e-3", "1e-2"):
    p = pathlib.Path(sys.argv[1]) / f"scout_qs_{lr}" / "result.json"
    try:
        r = json.loads(p.read_text())
        rec, arc, base = r["scores"]["final"]["forward"]["C24"], r["arc"], r["arc_base"]
    except Exception:
        continue
    if arc >= base - 0.03 - 1e-9 and (best is None or rec > best[0]):  # ties keep the lower lr (checked in ascending order)
        best = (rec, lr)
print(best[1] if best else "1e-3")
PY
)
log "qs lr picked: $QLR"; echo "$QLR" > "$OUT/qs_lr.txt"
run qs_s1 $R2 --storage qs --lr "$QLR" $S --seed 1
# 3. seed 2 of both treatment arms (the dose check is seed 1 only)
run lp16_s2 $R2 --storage lora --lora-plus 16 $S --seed 2
run qs_s2 $R2 --storage qs --lr "$QLR" $S --seed 2
# 4. reported only, not a gate (addendum 2): the add-on on the bf16 base, 75 steps, seed 1 (what the Q4_0 base costs the add-on)
run bf16c75_s1 $R2 --storage lora $S --base bf16 --seed 1
log "all runs attempted"
