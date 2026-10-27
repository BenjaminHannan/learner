#!/usr/bin/env bash
# Sleep-B on Ben's PC, pc10: takes over from sleepb_pc9.sh after its slot 1 (addendum 17, K2) and runs addendum 19 (the recipe on LFM3-1.7B,
# Ben's new small tier, 2026-10-27 19:45Z) in slot 2 instead of addendum 18.
#   pc9: ... add18 pre-check + add17 -> writes GO-LOOP-P1 -> waits for SEG2-DONE   <- pc10 stops pc9 here (it is only waiting)
#   pc10: [SEG2-DONE] -> add19 pre-check (LFM3, Week-1, ~1 h) -> add19 (LFM3 week) unless the port is broken, else add18 (K2) if Go, else arm A
#         -> GO-LOOP-P2A -> [SEG3-DONE] R8 -> GO-LOOP-P2B -> [V8 flag] V8 -> GO-AFTER-V8   (R8 / V8 exactly as pc9)
# Takeover: pc10 waits until pc9's run.log shows, after its last "sleepb-pc9 start" line, "released the GPU: wrote GO-LOOP-P1"; then
# it waits 3 min (pc9 is then in wait_turn's sleep loop) and stops pc9's bash and its subshells (command line `bash <path>/sleepb_pc9.sh`). pc9's add17 run and its
# watchdog are never touched: they have ended by then.
# Code: LFM3 runs use $J/src-l3 (the LFM3 port); K2 runs keep $J/src-cap4. Addendum 19's pre-check stops the LFM3 arm only if the
# port is broken (no complete probe, 0 chains kept by the fixed writer, or < 14 reachable two-hop tests); see PREREG-sleepB-addendum19.md.
# When addendum 19 takes slot 2, arm A does not run, so addendum 15's base is the defaults (addendum 18's recorded fallback).
set -uo pipefail
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14}
export SLEEPB_SAVE_ADAPTER=0  # C: was nearly full (2026-10-27): no adapter files; results and logs are a few MB per run
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
cfree() { df -m /mnt/c 2>/dev/null | awk 'NR==2 {print $4}'; }
wait_turn() {  # wait_turn FLAG_PATH
  echo "== waiting for $1 $(date -u +%FT%TZ), C: free $(cfree) MB"
  while :; do
    if [ -f "$1" ] && free_now; then sleep 120; free_now && break; fi
    sleep 60
  done
  echo "== turn came ($1) $(date -u +%FT%TZ), GPU used $(gpu_used) MiB, C: free $(cfree) MB"
}
busy() {  # busy WHAT
  echo "sleepb-pc10 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc10\nowner: Design sleep like the human brain\nnow: %s (since %s)\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull4\\run.log\nends: writes the next flag in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc10.md"
}
release() {  # release NEXT_FLAG RC
  grep -qs sleepb-pc10 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc10.md"
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
echo "== sleepb-pc10 start $(date -u +%FT%TZ)"
source "$HOME/bbvenv/bin/activate" || { echo "== STOP: no venv"; exit 1; }
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
K2="--model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
L3M="--model LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
L3="$L3M --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
[ -f "$J/src-l3/backbone/sleep/brain/sleepb.py" ] || { echo "== STOP: no $J/src-l3 (the LFM3 port)"; exit 1; }
# ---- takeover: wait for pc9 to finish slot 1 (add17) and pass GO-LOOP-P1 on, then stop pc9 (it is then only waiting for SEG2-DONE)
pc9_released() { awk '/== sleepb-pc9 start/ {r = 0} /== released the GPU: wrote GO-LOOP-P1/ {r = 1} END {exit !r}' "$P/run.log"; }
echo "== waiting for pc9 to release slot 1 (add17) $(date -u +%FT%TZ)"
until pc9_released; do sleep 60; done
sleep 180
PC9='^([^ ]*/)?bash [^ ]*sleepb_pc9\.sh$'  # pc9's own bash and its subshells only, not a command line that merely mentions it
echo "== pc9 released slot 1; stopping pc9 (waiting for SEG2-DONE): pids $(pgrep -f "$PC9" | tr '\n' ' ')"
pkill -f "$PC9"; sleep 5; pkill -9 -f "$PC9"
( while sleep 600; do [ -f "$R/cur4" ] && tail -n 60 "$(cat "$R/cur4")" > "$P/progress.txt"; done ) &
PROG=$!
trap 'kill $PROG 2>/dev/null' EXIT
# ---- slot 2: addendum 19 (LFM3); if its pre-check finds the port broken, addendum 18 (K2) if Go, else arm A (addendum 14, k2c)
wait_turn "$W/pc-jobs/think2-p1/SEG2-DONE"
OA=$R/add14A/sleepb/$A
busy "addendum 19 pre-check (LFM3, ~1 h), then the LFM3 week (~4-7 h, stops itself past 10 h)"
mkdir -p "$R/probe19" "$P/probe19"
echo "$R/probe19/probe.log" > "$R/cur4"
echo "-- add19 pre-check start $(date -u +%T)"
if [ ! -f "$R/probe19/probe.json" ] || ! grep -q '"partial": false' "$R/probe19/probe.json"; then
  (cd "$J/src-l3" && exec timeout 9000 python3 backbone/sleep/brain/k2_chain_probe.py $L3M --out "$R/probe19/probe.json" --variants q_think --tries 1 --gen-bs 24 --also-fixed) >> "$R/probe19/stdout.log" 2>&1
  echo "-- add19 pre-check exit $? $(date -u +%T)"
fi
cp -f "$R/probe19/probe.json" "$R/probe19/probe.log" "$R/probe19/stdout.log" "$P/probe19/" 2>/dev/null
python3 - "$R/probe19/probe.json" > "$P/add19-pre.txt" <<'PY'
import json, math, sys
try:
    r = json.load(open(sys.argv[1]))
    assert r.get("partial") is False
    a, b = r["variants"]["q_think"]["final"], r["variants"]["q_think_fix"]["final"]
    ka, kb = r["variants"]["q_think"]["kept_chains"], r["variants"]["q_think_fix"]["kept_chains"]
except Exception as e:
    print("STOP", f"the pre-check has no complete result ({type(e).__name__})"); sys.exit()
R = b["reachable"]
info = f"fixed writer: forward {b['dreamed_forward']} of {R} reachable (addendum 18's bar {math.ceil(0.88 * R)}), kept chains {kb}; today's writer: forward {a['dreamed_forward']}, kept {ka}"
print("RUN" if kb > 0 and R >= 14 else "STOP", info)
PY
echo "== addendum 19 pre-check: $(cat "$P/add19-pre.txt")"
if [ "$(cut -d' ' -f1 "$P/add19-pre.txt")" = RUN ]; then
  O19=$R/add19/sleepb/$A
  a19() { SRC=src-l3 run add19 "$O19" 10 $L3 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
            --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96; }
  a19 24; R2=$?
  if [ "$R2" != 0 ] && mem "$O19"; then echo "== add19 ran out of memory at gen-bs 24: again at 16"; mv "$O19" "$O19.mem24"; a19 16; R2=$?; fi
  SLOT2=add19
elif [ "$(cut -d' ' -f1 "$P/add18-go.txt")" = GO ]; then
  busy "addendum 18 (K2, ~8-10 h, stops itself past 11 h)"
  O18=$R/add18/sleepb/$A
  a18() { run add18 "$O18" 11 $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
            --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96; }
  a18 24; R2=$?
  if [ "$R2" != 0 ] && mem "$O18"; then echo "== add18 ran out of memory at gen-bs 24: again at 16"; mv "$O18" "$O18.mem24"; a18 16; R2=$?; fi
  SLOT2=add18
else
  busy "addendum 14 arm A (K2, ~6-10 h)"
  armA() { run add14-A "$OA" 10 $K2 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --think-eval; }
  armA 24; R2=$?
  if [ "$R2" != 0 ] && mem "$OA"; then echo "== arm A ran out of memory at gen-bs 24: again at 16"; mv "$OA" "$OA.mem24"; armA 16; R2=$?; fi
  SLOT2=A
fi
echo "slot 2 ran $SLOT2" > "$P/slot2.txt"
release GO-LOOP-P2A "$R2"
# ---- addendum 15's base, by the sealed rule (B failed no harm: recall 82.5 < 93.5); the defaults if A did not run (addendum 18)
if [ "$SLOT2" != A ]; then
  echo "DEFAULTS arm A did not run ($SLOT2 took its slot): the sealed rule's fallback, as recorded in addendum 18 and 19" > "$P/base.txt"
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
echo "== sleepb-pc10 end $(date -u +%FT%TZ)"
