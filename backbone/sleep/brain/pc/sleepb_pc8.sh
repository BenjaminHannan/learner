#!/usr/bin/env bash
# Sleep-B on Ben's PC: the chain in my PC slots (order from the coordinator, 2026-10-27 06:15Z and 11:06Z), with addendum 18 (sealed):
#   ... -> [race round 1] -> add18 pre-check + add17 -> [looping P1] -> add18 if Go, else arm A -> [looping P2a] -> R8 -> [looping P2b]
#   -> V8 -> [Notebook-2] ...
# Each step waits for its flag, then for a free GPU (no GPU-BUSY.txt, under 4 GB used, twice 2 min apart):
#   slot 1: $H/GO-SLEEP-A (written by the sleep race's round 1); slot 2: think2-p1/SEG2-DONE; R8: think2-p1/SEG3-DONE; V8: $V8_FLAG
#   (written by the looping thread after P2b).
# When a step ends, even if it fails, it clears its GPU-BUSY.txt and job card, then writes "<rc> <time>" to the next owner's flag:
# $H/GO-LOOP-P1 after slot 1, $H/GO-LOOP-P2A after slot 2, $H/GO-LOOP-P2B after R8, $H/GO-AFTER-V8 after V8.
# K2 on this 16 GB card: PyTorch's default CUDA allocator capped at SLEEPB_CUDA_CAP_GIB=14 (a full card under WSL spills into system
# memory instead of reporting out of memory), --tok-budget 256, code $J/src-cap3 (cuda_tidy at each night's start, before training and
# after REM writing; addendum 18's writer switches, off by default; log lines only otherwise).
# Each run stops (and its turn is passed on) if its log is silent for 90 min, or if, once night 2 or later ends, the remaining nights at
# 1.25x that night's seconds plus 75 min of final scoring would take it past its time budget (add17 10 h, add18 11 h, A 10 h, R8/V8 16 h).
# - Addendum 18 pre-check: k2_chain_probe.py on Week-1, q_think, tries 1, one night, today's writer and the fixed one (--also-fixed).
#   Go if the fixed one dreams >= 24 of 27 reachable tests forward (>= ceil(0.88 R) if R reachable is not 27) and >= today's + 3.
# - add17 (sealed): B's flags + --rem-steps-mult 2 --gate-arc-n 570, at --gen-bs 24; out of memory: again at 16.
# - add18 (sealed): add17's flags + --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96.
# - Arm A (addendum 14, k2c), only if add18 is No-go: its sealed flags, at --gen-bs 24; out of memory: again at 16.
# - Addendum 15 (sealed) R8 and V8: base flags from the sealed rule (A's flags if A passes no harm, else the defaults; the defaults when
#   A did not run, as recorded in addendum 18), without --think-eval, plus --reword, at --gen-bs 16 (8 if R8 runs out of memory).
# Small files go to $P (pull4/). The pre-check decision goes to $P/add18-go.txt, the base decision to $P/base.txt.
set -uo pipefail
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14}
V8_FLAG=${V8_FLAG:-/mnt/c/Users/benja/pc-jobs/handoff/GO-SLEEP-V8}
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
  echo "sleepb-pc8 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc8\nowner: Design sleep like the human brain\nnow: %s (since %s)\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull4\\run.log\nends: writes the next flag in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc8.md"
}
release() {  # release NEXT_FLAG RC
  grep -qs sleepb-pc8 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc8.md"
  echo "$2 $(date -u +%FT%TZ)" > "$H/$1"
  echo "== released the GPU: wrote $1 $(date -u +%FT%TZ)"
}
mem() { grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$1/sleepb.log"; }
A=ab_ob_b4_nb
run() {  # run NAME OUT BUDGET_H EXTRA...: one sleepb run from $J/src-cap3; log and result JSON are copied to pull4/NAME when it ends
  local n=$1 o=$2 bh=$3; shift 3
  if [ -f "$o/result_$A.json" ]; then echo "-- skip $n (done)"; return 0; fi
  mkdir -p "$o"
  echo "$o/sleepb.log" > "$R/cur4"
  echo "-- $n start $(date -u +%T) $*"
  touch "$o/sleepb.log"
  (cd "$J/src-cap3" && exec python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" "$@") >> "$o/sleepb.log" 2>&1 &
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
echo "== sleepb-pc8 start $(date -u +%FT%TZ)"
source "$HOME/bbvenv/bin/activate" || { echo "== STOP: no venv"; exit 1; }
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
( while sleep 600; do [ -f "$R/cur4" ] && tail -n 60 "$(cat "$R/cur4")" > "$P/progress.txt"; done ) &
PROG=$!
trap 'kill $PROG 2>/dev/null' EXIT
K2="--model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
# ---- slot 1: addendum 18's pre-check, then addendum 17 (steadier morning gate)
wait_turn "$H/GO-SLEEP-A"
busy "addendum 18 pre-check (~1 h), then addendum 17 (K2, ~7-10 h, stops itself past 10 h)"
mkdir -p "$R/probe18" "$P/probe18"
echo "$R/probe18/probe.log" > "$R/cur4"
echo "-- add18 pre-check start $(date -u +%T)"
if [ ! -f "$R/probe18/probe.json" ] || ! grep -q '"partial": false' "$R/probe18/probe.json"; then
  (cd "$J/src-cap3" && exec timeout 9000 python3 backbone/sleep/brain/k2_chain_probe.py --out "$R/probe18/probe.json" --variants q_think --tries 1 --gen-bs 24 --also-fixed) >> "$R/probe18/stdout.log" 2>&1
  echo "-- add18 pre-check exit $? $(date -u +%T)"
fi
cp -f "$R/probe18/probe.json" "$R/probe18/probe.log" "$P/probe18/" 2>/dev/null
python3 - "$R/probe18/probe.json" > "$P/add18-go.txt" <<'PY'
import json, math, sys
try:
    r = json.load(open(sys.argv[1]))
    a, b = r["variants"]["q_think"]["final"], r["variants"]["q_think_fix"]["final"]
    ka, kb = r["variants"]["q_think"]["kept_chains"], r["variants"]["q_think_fix"]["kept_chains"]
except Exception as e:
    print("NOGO", f"the pre-check has no complete result ({type(e).__name__})"); sys.exit()
R = b["reachable"]
need = 24 if R == 27 else math.ceil(0.88 * R)
ok = b["dreamed_forward"] >= need and b["dreamed_forward"] >= a["dreamed_forward"] + 3
print("GO" if ok else "NOGO", f"forward: fixed {b['dreamed_forward']}, today {a['dreamed_forward']}, of {R} reachable (needs >= {need} and >= today + 3); kept chains {kb} vs {ka}")
PY
echo "== addendum 18 pre-check: $(cat "$P/add18-go.txt")"
O17=$R/add17f/sleepb/$A
a17() { run add17 "$O17" 10 $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval; }
a17 24; R17=$?
if [ "$R17" != 0 ] && mem "$O17"; then echo "== add17 ran out of memory at gen-bs 24: again at 16"; mv "$O17" "$O17.mem24"; a17 16; R17=$?; fi
release GO-LOOP-P1 "$R17"
# ---- slot 2: addendum 18 if Go, else arm A (addendum 14, k2c)
wait_turn "$W/pc-jobs/think2-p1/SEG2-DONE"
OA=$R/add14A/sleepb/$A
if [ "$(cut -d' ' -f1 "$P/add18-go.txt")" = GO ]; then
  busy "addendum 18 (K2, ~8-10 h, stops itself past 11 h)"
  O18=$R/add18/sleepb/$A
  a18() { run add18 "$O18" 11 $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
            --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96; }
  a18 24; R2=$?
  if [ "$R2" != 0 ] && mem "$O18"; then echo "== add18 ran out of memory at gen-bs 24: again at 16"; mv "$O18" "$O18.mem24"; a18 16; R2=$?; fi
else
  busy "addendum 14 arm A (K2, ~6-10 h)"
  armA() { run add14-A "$OA" 10 $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --think-eval; }
  armA 24; R2=$?
  if [ "$R2" != 0 ] && mem "$OA"; then echo "== arm A ran out of memory at gen-bs 24: again at 16"; mv "$OA" "$OA.mem24"; armA 16; R2=$?; fi
fi
release GO-LOOP-P2A "$R2"
# ---- addendum 15's base, by the sealed rule (B failed no harm: recall 82.5 < 93.5); the defaults if A did not run (addendum 18)
if [ "$(cut -d' ' -f1 "$P/add18-go.txt")" = GO ]; then
  echo "DEFAULTS arm A did not run (addendum 18 took its slot): the sealed rule's fallback, as recorded in addendum 18" > "$P/base.txt"
else
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
fi
echo "== addendum 15 base: $(cat "$P/base.txt")"
SKIP=""
case "$(cut -d' ' -f1 "$P/base.txt")" in
  A) BASE="--rem-chain-mode q_think --rem-dirs both --rem-tries 2" ;;
  DEFAULTS) BASE="" ;;
  *) BASE=""; SKIP=1; echo "== no base for addendum 15: R8 and V8 are skipped, but their turns are still passed on" ;;
esac
# ---- addendum 15 R8
wait_turn "$W/pc-jobs/think2-p1/SEG3-DONE"
GB=16
O8=$R/add15/sleepb
[ -n "$SKIP" ] || busy "addendum 15 R8 (K2 8x, ~10-14 h)"
RR=0; [ -n "$SKIP" ] || { run add15-R8 "$O8/R8" 16 $K2 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4; RR=$?; }
if [ "$RR" != 0 ] && mem "$O8/R8"; then
  echo "== R8 ran out of memory at gen-bs 16: again at 8 (V8 uses 8 too)"; mv "$O8/R8" "$O8/R8.mem16"; GB=8
  run add15-R8 "$O8/R8" 16 $K2 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4
fi
R8RC=$([ -f "$O8/R8/result_$A.json" ] && echo 0 || echo 1)
echo "add15 gen-bs $GB" > "$P/add15-genbs.txt"
release GO-LOOP-P2B "$R8RC"
# ---- addendum 15 V8
wait_turn "$V8_FLAG"
[ -n "$SKIP" ] || busy "addendum 15 V8 (K2 8x, ~12-16 h)"
RV=0; [ -n "$SKIP" ] || { run add15-V8 "$O8/V8" 16 $K2 $BASE --gen-bs $GB --budget-scale 8 --dream-vary mix; RV=$?; }
if [ "$RV" != 0 ] && mem "$O8/V8" && [ "$GB" = 16 ]; then
  echo "== V8 ran out of memory at gen-bs 16: again at 8 (now unequal to R8; recorded)"; mv "$O8/V8" "$O8/V8.mem16"
  echo "add15 V8 gen-bs 8 (R8 16)" >> "$P/add15-genbs.txt"
  run add15-V8 "$O8/V8" 16 $K2 $BASE --gen-bs 8 --budget-scale 8 --dream-vary mix
fi
release GO-AFTER-V8 "$([ -f "$O8/V8/result_$A.json" ] && echo 0 || echo 1)"
echo "done $(date -u +%FT%TZ)" > "$P/DONE"
echo "== sleepb-pc8 end $(date -u +%FT%TZ)"
