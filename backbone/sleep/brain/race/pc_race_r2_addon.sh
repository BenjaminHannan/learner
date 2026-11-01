#!/usr/bin/env bash
# Race-mini round 2, add-on side (PREREG-race-addon-r2-mini.md), on BensPC (WSL). Started detached; waits for its go flag (default pc-jobs/handoff/GO-RACE-R2A, consumed) and a
# free GPU, runs every arm-seed in order (each skipped when its DONE file exists, so a rerun resumes), then writes its done flag.
# Pause between arm-seeds: create pc-jobs/handoff/PAUSE-RACE-R2A; the job finishes the running arm-seed, frees GPU-BUSY.txt, and waits until
# the file is gone and GPU-BUSY.txt is empty again. Addendum 1 (PROTOCOL-mini): 75 steps a night; the validity check is the 300-step vs 75-step dose check.
# Addendum 2: LFM3-1.7B on a llama.cpp Q4_0 (group 32) fake-quantized base (RM_MODEL overrides; arm args after it win), out dir fresh.
#   bash pc_race_r2_addon.sh <src dir with backbone/> <out dir>
set -uo pipefail
SRC=${1:?src}; OUT=${2:?out}
J=${PCJ:-/mnt/c/Users/benja/pc-jobs}
BUSY=${PCBUSY:-/mnt/c/Users/benja/GPU-BUSY.txt}
CARD=$J/race-r2a.md
GO=${RM_GO:-$J/handoff/GO-RACE-R2A}
PAUSE=${RM_PAUSE:-$J/handoff/PAUSE-RACE-R2A}
DONEFLAG=${RM_DONEFLAG:-$J/handoff/RACE-R2A-DONE}
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
  echo "race-mini round 2 add-on (sleep race) since $(date -u +%FT%TZ); card $CARD; pause: touch $PAUSE" > "$BUSY"
  printf "# race-mini r2 add-on\nowner: Make add-on sleep beat whole-model\nlog: %s/job.log\nstarted: %s\npause between arm-seeds: create %s\n" "$OUT" "$(date -u +%FT%TZ)" "$PAUSE" > "$CARD"
}
log "waiting for $GO and an empty GPU-BUSY.txt"
gpu_idle() {  # under 8 GB in use (Ben's desktop apps alone can hold ~7 GB; a training job that forgot GPU-BUSY.txt holds more); no nvidia-smi (CPU simulation) = idle
  local m; m=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1) || return 0
  [ -z "$m" ] || [ "$m" -lt 8000 ]
}
set_cap() {  # cap each run at min(14 GiB, what is free now - 0.5 GiB), so desktop VRAM plus ours never spills past the card under WSL
  local t u; read -r t u < <(nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ',') || return 0
  [ -n "$u" ] || return 0
  export SLEEPB_CUDA_CAP_GIB=$(python -c "print(round(min(14.0, ($t - $u) / 1024 - 0.5), 2))")
}
until [ -f "$GO" ] && [ ! -s "$BUSY" ] && gpu_idle; do sleep 60; done
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
  set_cap
  log "start $n: $* (GPU cap ${SLEEPB_CUDA_CAP_GIB} GiB)"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader >> "$OUT/job.log" 2>/dev/null
  python "$B/race/race_mini.py" --out "$OUT/$n" $MA "$@" ${RM_EXTRA:-} > "$OUT/$n.stdout" 2>&1
  local r=$?
  log "end $n rc=$r"
  [ $r -eq 0 ] || RC=$r
  return 0
}
R1="--tape $T/tape_week1.json --week $W1"
R2="--tape $T/tape_week2.json --week $W2"
S="--steps 75"

# 0. GPU preflight (the plain-LoRA path at the top lr of the ladder): a failure stops the job at once
if [ -z "${RM_SKIP_PREFLIGHT:-}" ]; then
  run pf_lora_hi $R2 --storage lora --lr 6e-3 --steps 2 --nights 2 --mid 99 --arc-n 5 --replay-n 4 --bsz 4
  if [ ! -f "$OUT/pf_lora_hi/DONE" ]; then log "PREFLIGHT pf_lora_hi FAILED: stopping"; [ $RC -eq 0 ] && RC=4; exit; fi
fi
# 1. add-on lr scout, the whole-model side's round-1 rule: Week-1 tape, 3 nights x 75 steps, seed 1, ARC-100; pick = best final C2+C4 with ARC-100 >= base - 3 (ties: lower lr)
for LR in 6e-4 2e-3 6e-3; do
  run scout_lora_$LR $R1 --storage lora --lr $LR $S --nights 3 --mid 99 --arc-n 100 --seed 1
done
LLR=$(python - "$OUT" <<'PY'
import json, sys, pathlib
best = None
for lr in ("6e-4", "2e-3", "6e-3"):
    p = pathlib.Path(sys.argv[1]) / f"scout_lora_{lr}" / "result.json"
    try:
        r = json.loads(p.read_text())
        rec, arc, base = r["scores"]["final"]["forward"]["C24"], r["arc"], r["arc_base"]
    except Exception:
        continue
    if arc >= base - 0.03 - 1e-9 and (best is None or rec > best[0]):
        best = (rec, lr)
print(best[1] if best else "6e-4")
PY
)
log "lora lr picked: $LLR"; echo "$LLR" > "$OUT/lora_lr.txt"
# 2. the tuned add-on on Week-2, both seeds (compared offline with round 1's qs_s1 / qs_s2 and c75_s1 / c75_s2: same code path, tapes and seeds)
run lr_s1 $R2 --storage lora --lr "$LLR" $S --seed 1
run lr_s2 $R2 --storage lora --lr "$LLR" $S --seed 2
log "all runs attempted"
