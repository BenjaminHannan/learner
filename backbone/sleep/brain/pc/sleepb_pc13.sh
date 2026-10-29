#!/usr/bin/env bash
# Sleep-B on Ben's PC, pc13 (addendum 21): replaces sleepb_pc12.sh while pc12 waits for SEG3-DONE. Addendum 19's first run stopped at
# its 10 h budget after night 5 with no result, so its arm runs again from scratch, unchanged, with a 16 h budget, in the slot R8 had:
#   [SEG3-DONE] add19b (addendum 19's arm, 16 h) -> GO-LOOP-P2B -> [GO-SLEEP-V8] R8 (LFM3) -> GO-AFTER-V8 -> [GO-SLEEP-V8B] V8 -> GO-AFTER-V8B
# Base of R8 / V8 (addendum 20's rule, applied to add19b's result): addendum 19's flags if it passes no harm (ARC >= pre - 5, diary >=
# base - 5, changed-new >= 53.3) and P1 (recall C2+C4 >= 88.5); else the defaults. R8 and V8 at --gen-bs 24; if R8 runs out of memory,
# both at 16; 16 h budgets. Also new: pull4/gpuwatch.txt logs GPU use and WSL load every 10 min while this chain owns the GPU (report
# only). The turn test, memory cap and run() are pc12's. Code: $J/src-l3.
set -uo pipefail
export SLEEPB_SAVE_ADAPTER=0  # C: was nearly full (2026-10-27): no adapter files; results and logs are a few MB per run
R8_FLAG=${R8_FLAG:-/mnt/c/Users/benja/pc-jobs/handoff/GO-SLEEP-V8}  # addendum 21: R8 takes the slot V8 had
V8_FLAG=${V8_FLAG:-/mnt/c/Users/benja/pc-jobs/handoff/GO-SLEEP-V8B}  # addendum 21: V8 waits for a new slot the coordinator places
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
H=$W/pc-jobs/handoff
P=$R/pull4
mkdir -p "$P" "$H"
exec >>"$P/run.log" 2>&1
gpu_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; }
gpu_q() { nvidia-smi --query-gpu="$1" --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
gpu_util() { gpu_q utilization.gpu; }
free_now() {  # no GPU-BUSY card, memory used under GPU_FREE_MIB (must read as a number) and utilization under 30% (skipped if unreadable)
  [ -s "$W/GPU-BUSY.txt" ] && return 1
  local u t; u=$(gpu_used); t=$(gpu_util)
  [[ "$u" =~ ^[0-9]+$ ]] && [ "$u" -lt "${GPU_FREE_MIB:-9000}" ] || return 1
  [[ "$t" =~ ^[0-9]+$ ]] && [ "$t" -ge 30 ] && return 1
  return 0
}
capnow() {  # before each job: cap PyTorch at the card's free memory now (Ben's desktop apps hold several GB), at most 14 GiB
  local tot used
  tot=$(gpu_q memory.total); used=$(gpu_used)
  export SLEEPB_CUDA_CAP_GIB=$(python3 -c "print(round(min(14.0, ($tot - $used) / 1024 - 0.75), 2))" 2>/dev/null || echo 8)
  echo "== $1: GPU $used of $tot MiB used, util $(gpu_util)%; SLEEPB_CUDA_CAP_GIB=$SLEEPB_CUDA_CAP_GIB"
}
cfree() { df -m /mnt/c 2>/dev/null | awk 'NR==2 {print $4}'; }
wait_turn() {  # wait_turn FLAG_PATH
  echo "== waiting for $1 $(date -u +%FT%TZ), C: free $(cfree) MB"
  while :; do
    if [ -f "$1" ] && free_now; then sleep 120; free_now && break; fi
    sleep 60
  done
  echo "== turn came ($1) $(date -u +%FT%TZ), GPU used $(gpu_used) MiB, C: free $(cfree) MB"
  capnow "$1"
}
busy() {  # busy WHAT
  echo "sleepb-pc13 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc13\nowner: Design sleep like the human brain\nnow: %s (since %s)\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull4\\run.log\nends: writes the next flag in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc13.md"
}
release() {  # release NEXT_FLAG RC
  grep -qs sleepb-pc13 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc13.md"
  echo "$2 $(date -u +%FT%TZ)" > "$H/$1"
  echo "== released the GPU: wrote $1 $(date -u +%FT%TZ)"
}
mem() { grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$1/sleepb.log"; }
A=ab_ob_b4_nb
run() {  # run NAME OUT BUDGET_H EXTRA...: one sleepb run from $J/$SRC (default src-cap4); log and result JSON are copied to pull4/NAME when it ends
  local n=$1 o=$2 bh=$3; shift 3
  if [ -f "$o/result_$A.json" ]; then echo "-- skip $n (done)"; return 0; fi
  mkdir -p "$o"
  echo "$o/sleepb.log" > "$R/cur4"
  echo "-- $n start $(date -u +%T) $*"
  touch "$o/sleepb.log"
  (cd "$J/${SRC:-src-cap4}" && exec python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" "$@") >> "$o/sleepb.log" 2>&1 &
  local py=$! lim=$(( $(date +%s) + bh * 3600 ))
  ( seen=0; while sleep 300; do
      if [ $(( $(date +%s) - $(stat -c %Y "$o/sleepb.log") )) -gt 5400 ]; then
        echo "== watchdog: $n silent for 90 min at $(date -u +%T): stopped as too slow"; kill "$py"; break
      fi
      last=$(grep '^\[night [0-9]*\] done steps .* [0-9]*s$' "$o/sleepb.log" | tail -1)
      nn=$(echo "$last" | sed -n 's/^\[night \([0-9]*\)\].*/\1/p'); sec=$(echo "$last" | sed -n 's/.* \([0-9]*\)s$/\1/p')
      if [ -n "$nn" ] && [ -n "$sec" ] && [ "$nn" -ge 2 ] && [ "$nn" -lt 7 ] && [ "$nn" -ne "$seen" ]; then
        seen=$nn; end=$(( $(date +%s) + (7 - nn) * sec * 5 / 4 + 4500 ))
        echo "== $n after night $nn (${sec}s): projected end $(date -u -d @$end +%FT%TZ), budget end $(date -u -d @$lim +%FT%TZ)"
        if [ "$end" -gt "$lim" ]; then echo "== $n: over its ${bh} h budget; stopped"; kill "$py"; break; fi
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
echo "== sleepb-pc13 start $(date -u +%FT%TZ)"
source "$HOME/bbvenv/bin/activate" || { echo "== STOP: no venv"; exit 1; }
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
K2="--model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
L3M="--model LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
L3="$L3M --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
[ -f "$J/src-l3/backbone/sleep/brain/sleepb.py" ] || { echo "== STOP: no $J/src-l3 (the LFM3 port)"; exit 1; }
( while sleep 600; do [ -f "$R/cur4" ] && tail -n 60 "$(cat "$R/cur4")" > "$P/progress.txt"; done ) &
PROG=$!
trap 'kill $PROG 2>/dev/null' EXIT
GW=""
gpuwatch_on() { ( while :; do echo "$(date -u +%FT%TZ) $(nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu,clocks.sm --format=csv,noheader 2>/dev/null) load $(cut -d' ' -f1-3 /proc/loadavg) | $1" >> "$P/gpuwatch.txt"; sleep 600; done ) & GW=$!; }
gpuwatch_off() { [ -n "$GW" ] && kill "$GW" 2>/dev/null; GW=""; }
trap 'kill $PROG 2>/dev/null; gpuwatch_off' EXIT
A19="--rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96"
# ---- addendum 21: addendum 19's arm again (16 h budget)
wait_turn "$W/pc-jobs/think2-p1/SEG3-DONE"
O19=$R/add19b/sleepb/$A
busy "addendum 21: addendum 19's LFM3 week again (~11-13 h, stops itself past 16 h)"
gpuwatch_on add19b
SRC=src-l3 run add19b "$O19" 16 $L3 --gen-bs 24 $A19; R2=$?
if [ "$R2" != 0 ] && mem "$O19"; then echo "== add19b ran out of memory at gen-bs 24: again at 16"; mv "$O19" "$O19.mem24"; SRC=src-l3 run add19b "$O19" 16 $L3 --gen-bs 16 $A19; R2=$?; fi
gpuwatch_off
release GO-LOOP-P2B "$R2"
# ---- addendum 20: the base of R8 / V8 on LFM3 (from add19b)
python3 - "$O19/result_$A.json" > "$P/base20.txt" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
    rec = 100 * r["scores"]["weights"]["forward"]["C24"]
    arc, arc0 = r["arc_easy"]["acc"], r["arc_easy_base"]["acc"]
    di, di0 = r["scores"]["diary"]["pooled"], r["scores"]["base_diary"]["pooled"]
    ch = 100 * r["scores"]["weights"]["changed"]["new"]
except Exception as e:
    print("DEFAULTS", f"addendum 19 (add19b) has no complete result ({type(e).__name__})"); sys.exit()
ok = rec >= 88.5 and arc >= arc0 - 0.05 and di >= di0 - 0.05 and ch >= 53.3
why = f"add19b recall {rec:.1f} (>= 88.5), ARC {100*arc:.1f} vs pre {100*arc0:.1f} (>= pre - 5), diary {100*di:.1f} vs base {100*di0:.1f} (>= base - 5), changed-new {ch:.1f} (>= 53.3)"
print("ADD19" if ok else "DEFAULTS", why)
PY
echo "== addendum 20 base: $(cat "$P/base20.txt")"
case "$(cut -d' ' -f1 "$P/base20.txt")" in
  ADD19) BASE="--rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96" ;;
  *) BASE="" ;;
esac
# ---- addendum 20 R8 (LFM3), in the slot V8 had
wait_turn "$R8_FLAG"
GB=24
O8=$R/add20/sleepb
busy "addendum 20 R8 (LFM3 8x, ~8-12 h, stops itself past 16 h)"
gpuwatch_on R8
SRC=src-l3 run add20-R8 "$O8/R8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4; RR=$?
if [ "$RR" != 0 ] && mem "$O8/R8"; then
  echo "== R8 ran out of memory at gen-bs 24: again at 16 (V8 uses 16 too)"; mv "$O8/R8" "$O8/R8.mem24"; GB=16
  SRC=src-l3 run add20-R8 "$O8/R8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4
fi
gpuwatch_off
echo "add20 gen-bs $GB" > "$P/add20-genbs.txt"
release GO-AFTER-V8 "$([ -f "$O8/R8/result_$A.json" ] && echo 0 || echo 1)"
# ---- addendum 20 V8 (LFM3), in a new slot
wait_turn "$V8_FLAG"
busy "addendum 20 V8 (LFM3 8x, ~8-12 h, stops itself past 16 h)"
gpuwatch_on V8
SRC=src-l3 run add20-V8 "$O8/V8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --dream-vary mix; RV=$?
if [ "$RV" != 0 ] && mem "$O8/V8" && [ "$GB" = 24 ]; then
  echo "== V8 ran out of memory at gen-bs 24: again at 16 (now unequal to R8; recorded)"; mv "$O8/V8" "$O8/V8.mem24"
  echo "add20 V8 gen-bs 16 (R8 24)" >> "$P/add20-genbs.txt"
  SRC=src-l3 run add20-V8 "$O8/V8" 16 $L3 $BASE --gen-bs 16 --budget-scale 8 --dream-vary mix
fi
gpuwatch_off
release GO-AFTER-V8B "$([ -f "$O8/V8/result_$A.json" ] && echo 0 || echo 1)"
echo "done $(date -u +%FT%TZ)" > "$P/DONE"
echo "== sleepb-pc13 end $(date -u +%FT%TZ)"
