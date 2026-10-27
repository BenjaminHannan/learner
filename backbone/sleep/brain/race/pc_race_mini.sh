#!/usr/bin/env bash
# Race-mini round 1, both sides, on BensPC (WSL). Started detached; waits for the looping thread's segment-1 flag and a free GPU,
# runs every arm-seed in order (each skipped when its DONE file exists, so a rerun resumes), then hands the GPU to sleep arm A.
#   bash pc_race_mini.sh <src dir with backbone/> <out dir>
set -uo pipefail
SRC=${1:?src}; OUT=${2:?out}
J=${PCJ:-/mnt/c/Users/benja/pc-jobs}
BUSY=${PCBUSY:-/mnt/c/Users/benja/GPU-BUSY.txt}
CARD=$J/race-mini.md
mkdir -p "$OUT"
[ -f ~/bbvenv/bin/activate ] && source ~/bbvenv/bin/activate
unset PYTORCH_CUDA_ALLOC_CONF  # pc-launch-route: expandable segments misbehave under WSL
B=$SRC/backbone/sleep/brain
T=$B/race/tapes
W2=$B/data/week2.json; W1=$B/data/week1.json
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/job.log"; }

log "waiting for $J/think2-p1/SEG1-DONE and an empty GPU-BUSY.txt"
until [ -f "$J/think2-p1/SEG1-DONE" ] && { [ ! -s "$BUSY" ]; }; do sleep 60; done
echo "race-mini (sleep race, both sides) since $(date -u +%FT%TZ); card $CARD" > "$BUSY"
printf "# race-mini\nowner: Make whole-model sleep beat the add-on (+ add-on side)\nlog: %s/job.log\nstarted: %s\n" "$OUT" "$(date -u +%FT%TZ)" > "$CARD"
RC=0
finish() {
  : > "$BUSY"; rm -f "$CARD"
  mkdir -p "$J/handoff"; echo "$RC $(date -u +%FT%TZ)" > "$J/handoff/GO-SLEEP-A"
  log "finished rc=$RC; GPU handed to sleep arm A"
}
trap finish EXIT

run() {  # name, then race_mini args
  local n=$1; shift
  if [ -f "$OUT/$n/DONE" ]; then log "skip $n (done)"; return 0; fi
  log "start $n: $*"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader >> "$OUT/job.log" 2>/dev/null
  python "$B/race/race_mini.py" --out "$OUT/$n" "$@" ${RM_EXTRA:-} > "$OUT/$n.stdout" 2>&1
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

# 1. validity check, seed 1 (lora_s1 is also the add-on control)
run lora_s1 $R2 --storage lora --seed 1
run bf16_s1 $R2 --storage lora --base bf16 --seed 1
G=$(gap lora_s1 bf16_s1); log "validity seed 1: bf16 - q4 = ${G:-missing} points (fail if < 1)"
if [ -z "${RM_SKIP_GATE:-}" ] && { [ -z "$G" ] || python -c "import sys; sys.exit(0 if float('$G') < 1 else 1)"; }; then
  log "VALIDITY FAILED or missing: stopping (both sides rethink)"; RC=${RC:-0}; [ $RC -eq 0 ] && RC=3; exit
fi
# 2. seed 1: add-on LoRA+ x16, whole-model lr scout (Week-1 tape, 3 nights, fixed rule), whole-model qs
run lp16_s1 $R2 --storage lora --lora-plus 16 --seed 1
for LR in 1e-3 3e-3 1e-2; do
  run scout_qs_$LR --tape $T/tape_week1.json --week $W1 --storage qs --lr $LR --nights 3 --mid 99 --arc-n 100 --seed 1
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
run qs_s1 $R2 --storage qs --lr "$QLR" --seed 1
# 3. seed 2 for all, then the second validity seed
run lora_s2 $R2 --storage lora --seed 2
run lp16_s2 $R2 --storage lora --lora-plus 16 --seed 2
run qs_s2 $R2 --storage qs --lr "$QLR" --seed 2
run bf16_s2 $R2 --storage lora --base bf16 --seed 2
log "all runs attempted"
