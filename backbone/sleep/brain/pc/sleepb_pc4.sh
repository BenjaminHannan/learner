#!/usr/bin/env bash
# Sleep-B on Ben's PC, the chain after addendum 17 (PC order from the coordinator, 2026-10-27 06:15Z):
#   ... -> [race round 1] -> arm A -> [looping P1] -> R8 -> [looping P2a] -> V8 -> [looping P2b] -> ...
# Each step waits for the flag of the job just before it, then for a free GPU (no GPU-BUSY.txt, under 4 GB used, twice 2 min apart):
#   arm A: $H/GO-SLEEP-A (written by the sleep race's round 1); R8: think2-p1/SEG2-DONE; V8: think2-p1/SEG3-DONE (the looping thread's).
# When a step ends, even if it fails, it clears its GPU-BUSY.txt and job card, then writes "<rc> <time>" to the next owner's flag:
# $H/GO-LOOP-P1 after arm A, $H/GO-LOOP-P2A after R8, $H/GO-LOOP-P2B after V8. There are no time-outs: a missing flag means waiting.
# K2 on this 16 GB card: PyTorch's default CUDA allocator (expandable segments failed under WSL) capped at SLEEPB_CUDA_CAP_GIB=14 (a full
# card under WSL spills into system memory instead of reporting out of memory), --tok-budget 256, code $J/src-cap
# (the selftest_shy memory fix, cuda_tidy between generation and training, the cap, and a log line every 200 training steps; it includes the
# addendum-15 code). A watchdog stops a run whose log is silent for 90 min (a full card spilling into system memory trained ~30x slower).
# - Arm A (addendum 14, k2c): its sealed flags, at --gen-bs 24 (B used 48); on running out of memory, again from the start at 16.
# - Addendum 15 (sealed, 02dca0a42e) R8 and V8: base flags from the sealed rule (B failed no harm, so A's flags if A passes no harm, else
#   the defaults), without --think-eval, plus --reword, at --gen-bs 16. If R8 runs out of memory at 16, it starts again at 8, and V8 then
#   uses 8 too.
# Small files go to $P (pull4/). The base decision is written to $P/base.txt before R8 runs.
set -uo pipefail
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14}
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
H=$W/pc-jobs/handoff
P=$R/pull4
mkdir -p "$P" "$H"
exec >>"$P/run.log" 2>&1
gpu_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; }
free_now() { [ ! -s "$W/GPU-BUSY.txt" ] && [ "$(gpu_used)" -lt 4000 ] 2>/dev/null; }
wait_turn() {  # wait_turn FLAG_PATH
  echo "== waiting for $1 $(date -u +%FT%TZ)"
  while :; do
    if [ -f "$1" ] && free_now; then sleep 120; free_now && break; fi
    sleep 60
  done
  echo "== turn came ($1) $(date -u +%FT%TZ), GPU used $(gpu_used) MiB"
}
busy() {  # busy WHAT
  echo "sleepb-pc4 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc4\nowner: Design sleep like the human brain\nnow: %s (since %s)\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull4\\run.log\nends: writes the next flag in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc4.md"
}
release() {  # release NEXT_FLAG RC
  grep -qs sleepb-pc4 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc4.md"
  echo "$2 $(date -u +%FT%TZ)" > "$H/$1"
  echo "== released the GPU: wrote $1 $(date -u +%FT%TZ)"
}
mem() { grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$1/sleepb.log"; }
A=ab_ob_b4_nb
run() {  # run NAME OUT EXTRA...: one sleepb run from $J/src-cap; log and result JSON are copied to pull4/NAME when it ends
  local n=$1 o=$2; shift 2
  if [ -f "$o/result_$A.json" ]; then echo "-- skip $n (done)"; return 0; fi
  mkdir -p "$o"
  echo "$o/sleepb.log" > "$R/cur4"
  echo "-- $n start $(date -u +%T) $*"
  touch "$o/sleepb.log"
  (cd "$J/src-cap" && exec python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" "$@") >> "$o/sleepb.log" 2>&1 &
  local py=$!
  ( while sleep 300; do
      if [ $(( $(date +%s) - $(stat -c %Y "$o/sleepb.log") )) -gt 5400 ]; then
        echo "== watchdog: $n silent for 90 min at $(date -u +%T): stopped as too slow"; kill "$py"; break
      fi
    done ) &
  local dog=$!
  wait "$py"
  local rc=$?
  kill "$dog" 2>/dev/null
  echo "-- $n exit $rc $(date -u +%T)"
  mkdir -p "$P/$n"
  cp -f "$o/sleepb.log" "$o/result_$A.json" "$P/$n/" 2>/dev/null
  return $rc
}
echo "== sleepb-pc4 start $(date -u +%FT%TZ)"
source "$HOME/bbvenv/bin/activate" || { echo "== STOP: no venv"; exit 1; }
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
( while sleep 600; do [ -f "$R/cur4" ] && tail -n 60 "$(cat "$R/cur4")" > "$P/progress.txt"; done ) &
PROG=$!
trap 'kill $PROG 2>/dev/null' EXIT
K2="--model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
# ---- arm A (addendum 14, k2c)
wait_turn "$H/GO-SLEEP-A"
busy "addendum 14 arm A (K2, ~6-8 h)"
OA=$R/add14A/sleepb/$A
armA() { run add14-A "$OA" $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --think-eval; }
armA 24; RA=$?
if [ "$RA" != 0 ] && mem "$OA"; then echo "== arm A ran out of memory at gen-bs 24: again at 16"; mv "$OA" "$OA.mem24"; armA 16; RA=$?; fi
release GO-LOOP-P1 "$RA"
# ---- addendum 15's base, by the sealed rule (B failed no harm: recall 82.5 < 93.5)
python3 - "$OA/result_$A.json" > "$P/base.txt" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
except Exception as e:
    print("NONE", f"arm A has no result ({type(e).__name__}); stop before addendum 15"); sys.exit()
rec = 100 * r["scores"]["weights"]["forward"]["C24"]
arc, arc0 = r["arc_easy"]["acc"], r["arc_easy_base"]["acc"]
di, di0 = r["scores"]["diary"]["pooled"], r["scores"]["base_diary"]["pooled"]
ok = rec >= 93.5 and arc >= arc0 - 0.05 and di >= di0 - 0.05
why = f"A recall {rec:.1f} (>= 93.5), ARC {100*arc:.1f} vs pre {100*arc0:.1f} (>= pre - 5), diary {100*di:.1f} vs base {100*di0:.1f} (>= base - 5)"
print("A" if ok else "DEFAULTS", why)
PY
echo "== addendum 15 base: $(cat "$P/base.txt")"
SKIP=""
case "$(cut -d' ' -f1 "$P/base.txt")" in
  A) BASE="--rem-chain-mode q_think --rem-dirs both --rem-tries 2" ;;
  DEFAULTS) BASE="" ;;
  *) BASE=""; SKIP=1; echo "== no base for addendum 15: R8 and V8 are skipped, but their turns are still passed on" ;;
esac
# ---- addendum 15 R8
wait_turn "$W/pc-jobs/think2-p1/SEG2-DONE"
GB=16
O8=$R/add15/sleepb
[ -n "$SKIP" ] || busy "addendum 15 R8 (K2 8x, ~10-14 h)"
RR=0; [ -n "$SKIP" ] || { run add15-R8 "$O8/R8" $K2 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4; RR=$?; }
if [ "$RR" != 0 ] && mem "$O8/R8"; then
  echo "== R8 ran out of memory at gen-bs 16: again at 8 (V8 uses 8 too)"; mv "$O8/R8" "$O8/R8.mem16"; GB=8
  run add15-R8 "$O8/R8" $K2 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4
fi
R8RC=$([ -f "$O8/R8/result_$A.json" ] && echo 0 || echo 1)
echo "add15 gen-bs $GB" > "$P/add15-genbs.txt"
release GO-LOOP-P2A "$R8RC"
# ---- addendum 15 V8
wait_turn "$W/pc-jobs/think2-p1/SEG3-DONE"
[ -n "$SKIP" ] || busy "addendum 15 V8 (K2 8x, ~12-16 h)"
RV=0; [ -n "$SKIP" ] || { run add15-V8 "$O8/V8" $K2 $BASE --gen-bs $GB --budget-scale 8 --dream-vary mix; RV=$?; }
if [ "$RV" != 0 ] && mem "$O8/V8" && [ "$GB" = 16 ]; then
  echo "== V8 ran out of memory at gen-bs 16: again at 8 (now unequal to R8; recorded)"; mv "$O8/V8" "$O8/V8.mem16"
  echo "add15 V8 gen-bs 8 (R8 16)" >> "$P/add15-genbs.txt"
  run add15-V8 "$O8/V8" $K2 $BASE --gen-bs 8 --budget-scale 8 --dream-vary mix
fi
release GO-LOOP-P2B "$([ -f "$O8/V8/result_$A.json" ] && echo 0 || echo 1)"
echo "done $(date -u +%FT%TZ)" > "$P/DONE"
echo "== sleepb-pc4 end $(date -u +%FT%TZ)"
