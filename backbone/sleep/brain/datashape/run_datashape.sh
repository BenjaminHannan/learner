#!/usr/bin/env bash
# Data-shape round 1 (PREREG-datashape-r1.md) on the Radeon PC (WSL, user timot; also runs on BensPC with env overrides): race_mini.py UNCHANGED
# (frozen race code f5d5bc5f81), 75 steps a night, LFM3-1.7B on the served QAD-Q4_0 GGUF. Controls c75_s1 / c75_s2 (shared tape) rerun here, same machine.
# Waits for its go flag (default pc-jobs/handoff/GO-DATASHAPE, consumed) and an empty GPU-BUSY.txt; each arm-seed is skipped when its DONE exists.
#   bash run_datashape.sh <src dir with backbone/> <out dir>
# Env: PCJ (pc-jobs dir), PCBUSY (GPU-BUSY.txt), VENV (default ~/rvenv), GGUF (default ~/lfm3q4/LFM3-1.7B-QAD-Q4_0.gguf), DS_GO, DS_DONEFLAG,
# SLEEPB_CUDA_CAP_GIB (default 11). BensPC: PCJ=/mnt/c/Users/benja/pc-jobs PCBUSY=/mnt/c/Users/benja/GPU-BUSY.txt VENV=~/bbvenv SLEEPB_CUDA_CAP_GIB=14.
set -uo pipefail
SRC=${1:?src}; OUT=${2:?out}
J=${PCJ:-/mnt/c/Users/timot/pc-jobs}
BUSY=${PCBUSY:-/mnt/c/Users/timot/GPU-BUSY.txt}
CARD=$J/datashape.md
GO=${DS_GO:-$J/handoff/GO-DATASHAPE}
DONEFLAG=${DS_DONEFLAG:-$J/handoff/DATASHAPE-DONE}
GGUF=${GGUF:-$HOME/lfm3q4/LFM3-1.7B-QAD-Q4_0.gguf}
MA="--model LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd --base q4_0 --q4-gguf $GGUF"
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-11} HSA_ENABLE_DXG_DETECTION=1
mkdir -p "$OUT"
V=${VENV:-$HOME/rvenv}; [ -f "$V/bin/activate" ] && source "$V/bin/activate"
command -v python >/dev/null || { echo "no python (venv $V missing?)" >&2; exit 127; }
unset PYTORCH_CUDA_ALLOC_CONF
B=$SRC/backbone/sleep/brain
T=$B/datashape/tapes
W2=$B/data/week2.json
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/job.log"; }
log "waiting for $GO and an empty GPU-BUSY.txt"
until [ -f "$GO" ] && [ ! -s "$BUSY" ]; do sleep 60; done
rm -f "$GO"
echo "datashape (Shape training data for better sleep) since $(date -u +%FT%TZ); log $OUT/job.log" > "$BUSY"
printf "# datashape r1\nowner: Shape training data for better sleep\nlog: %s/job.log\nstarted: %s\n" "$OUT" "$(date -u +%FT%TZ)" > "$CARD"
RC=0
finish() { : > "$BUSY"; rm -f "$CARD"; mkdir -p "$(dirname "$DONEFLAG")"; echo "$RC $(date -u +%FT%TZ)" > "$DONEFLAG"; log "finished rc=$RC"; }
trap finish EXIT
sha256sum "$GGUF" "$B/race/tapes/tape_week2.json" "$T"/tape_week2_W.json "$T"/tape_week2_L.json | tee -a "$OUT/job.log"
run() {
  local n=$1; shift
  if [ -f "$OUT/$n/DONE" ]; then log "skip $n (done)"; return 0; fi
  log "start $n: $*"
  python "$B/race/race_mini.py" --out "$OUT/$n" $MA --storage lora --steps 75 --week "$W2" "$@" > "$OUT/$n.stdout" 2>&1
  local r=$?; log "end $n rc=$r"; [ $r -eq 0 ] || RC=$r
}
run c75_s1 --tape "$B/race/tapes/tape_week2.json" --seed 1
run W_s1 --tape "$T/tape_week2_W.json" --seed 1
run L_s1 --tape "$T/tape_week2_L.json" --seed 1
run c75_s2 --tape "$B/race/tapes/tape_week2.json" --seed 2
run W_s2 --tape "$T/tape_week2_W.json" --seed 2
run L_s2 --tape "$T/tape_week2_L.json" --seed 2
python "$B/datashape/analyze.py" --ctl "$OUT/c75_s1" "$OUT/c75_s2" --W "$OUT/W_s1" "$OUT/W_s2" --L "$OUT/L_s1" "$OUT/L_s2" --json "$OUT/verdict.json" >> "$OUT/job.log" 2>&1 || RC=$?
