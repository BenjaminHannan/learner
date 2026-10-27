#!/usr/bin/env bash
# Sleep-B on Ben's PC (RTX 5070 Ti, 16 GB; WSL Ubuntu; ~/bbvenv): addendum 14 arm A, then addendum 16's three runs (C, T1, T2), one
# after another on the one card. Flags are the GPU-queue jobs' (gpu-queue/inbox/add14-A.sh and add16-eff.sh) with one recorded change:
# arm A uses --gen-bs 24, not 48, to fit 16 GB (RESULTS-sleepB.md, "Addendum 14 arm A: run on Ben's PC").
# Layout made by the Mac-side launcher: $J/src-a7ed69d = git archive of a7ed69d79d (arm A's commit), $J/src-5fc4b87 = 5fc4b87a23 (add16's).
# Results go to $R on the Windows side so the Mac can scp them; $R/pull holds only the small files (result JSONs, logs, progress).
# A restart skips finished runs. At the end it writes $R/DONE and clears GPU-BUSY.txt and the job card if they are this job's.
set -uo pipefail
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
mkdir -p "$R/pull"
exec >>"$R/pull/run.log" 2>&1
finish() {
  echo "== sleepb-pc end $(date -u +%FT%TZ) code $1"
  [ -n "${PROG:-}" ] && kill "$PROG" 2>/dev/null
  echo "$1 $(date -u +%FT%TZ)" > "$R/pull/DONE"
  grep -qs sleepb-pc "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc.md"
  exit "$1"
}
echo "== sleepb-pc start $(date -u +%FT%TZ) host $(hostname)"
source "$HOME/bbvenv/bin/activate" || finish 1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv || true
# exit 0: all versions as on the reference runs; 2: flash-linear-attention is not 0.6.0 (add16's Qwen3.5 runs are skipped, arm A still
# runs); 1: transformers or peft differ (nothing runs). accelerate only places weights, so a different version is reported, not fatal.
python3 - <<'PY'
import sys, torch, transformers, peft
v = {"torch": torch.__version__, "cuda": torch.cuda.is_available(), "transformers": transformers.__version__, "peft": peft.__version__}
for m in ("accelerate", "datasets", "fla"):
    try:
        v[m] = __import__(m).__version__
    except Exception as e:
        v[m] = f"missing: {type(e).__name__}"
print("versions", v, flush=True)
if not v["cuda"] or v["transformers"] != "5.20.2" or v["peft"] != "0.21.2":
    sys.exit(1)
if v["accelerate"] != "1.15.0":
    print("note: accelerate is not 1.15.0 (reported only)")
sys.exit(0 if v["fla"] == "0.6.0" else 2)
PY
VC=$?
[ "$VC" = 1 ] && { echo "== STOP: transformers/peft/CUDA check failed"; finish 1; }
( while sleep 600; do [ -f "$R/cur" ] && tail -n 60 "$(cat "$R/cur")" > "$R/pull/progress.txt"; done ) &
PROG=$!
A=ab_ob_b4_nb
oom() { grep -qs "OutOfMemoryError\|CUDA out of memory" "$1/sleepb.log"; }
run() {  # run NAME SRC OUT EXTRA...: one sleepb run; the log and result JSON are copied to pull/ when it ends
  local n=$1 src=$2 o=$3; shift 3
  if [ -f "$o/result_$A.json" ]; then echo "-- skip $n (done)"; return 0; fi
  mkdir -p "$o"
  echo "$o/sleepb.log" > "$R/cur"
  echo "-- $n start $(date -u +%T) $*"
  (cd "$src" && python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" "$@") >> "$o/sleepb.log" 2>&1
  local rc=$?
  echo "-- $n exit $rc $(date -u +%T)"
  mkdir -p "$R/pull/$n"
  cp -f "$o/sleepb.log" "$R/pull/$n/" 2>/dev/null
  cp -f "$o/result_$A.json" "$R/pull/$n/" 2>/dev/null
  return $rc
}
# arm A at gen-bs 24; only if that runs out of memory, once more from the start at 16 (both recorded in RESULTS before the run)
OA="$R/add14-A/sleepb/$A"
armA() {
  run add14-A "$J/src-a7ed69d" "$OA" --tok-budget 1024 --model IFM/K2-Horizon-3.7B \
    --week backbone/sleep/brain/data/week2.json --seed 1 \
    --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --arc-base --gen-bs "$1" \
    --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --think-eval \
    --reword backbone/sleep/brain/data/week2_reworded.json
}
armA 24
RA=$?
if [ "$RA" != 0 ] && oom "$OA"; then
  echo "== add14-A ran out of memory at gen-bs 24: starting again at 16"
  mv "$OA" "$OA.oom24"
  armA 16
  RA=$?
fi
if [ "$VC" = 2 ]; then echo "== add16 skipped: flash-linear-attention is not 0.6.0"; finish 3; fi
# addendum 16 (sealed): the same --gen-bs and --tok-budget for all three runs. gen-bs 32 as in the queue job; if C runs out of memory,
# all three run at 16 instead (the prereg fixes only that the three match)
O16="$R/add16-eff/sleepb"
GB=32
common() { echo "--model Qwen/Qwen3.5-2B --week backbone/sleep/brain/data/week2.json --seed 1 --tok-budget 2048 --gen-bs $GB --budget-scale 2 --card-stats"; }
run add16-C "$J/src-5fc4b87" "$O16/C" $(common)
if [ $? != 0 ] && oom "$O16/C"; then
  echo "== add16 C ran out of memory at gen-bs 32: all three runs at 16"
  mv "$O16/C" "$O16/C.oom32"
  GB=16
  run add16-C "$J/src-5fc4b87" "$O16/C" $(common)
fi
echo "add16 gen-bs $GB" > "$R/pull/add16-genbs.txt"
run add16-T1 "$J/src-5fc4b87" "$O16/T1" $(common) --skip-known 0.25
run add16-T2 "$J/src-5fc4b87" "$O16/T2" $(common) --rem-views 20
finish "$RA"
