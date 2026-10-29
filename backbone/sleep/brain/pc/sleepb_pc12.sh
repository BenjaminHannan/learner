#!/usr/bin/env bash
# Sleep-B on Ben's PC, pc12: pc11 with a GPU-free test that works with Ben's desktop apps open (2026-10-29). pc11 waited forever: its
# turn test was "GPU-BUSY.txt empty and under 4000 MiB used", but Discord, Chrome, Lunar Client and others hold ~6.7 GB of the card while
# the GPU is idle. pc12's test: GPU-BUSY.txt empty, under GPU_FREE_MIB (default 9000) used, and utilization under 30% (twice, 2 min apart).
# The PyTorch cap (SLEEPB_CUDA_CAP_GIB) is set before each job to min(14, the card's free GiB - 0.75), so a job runs out of memory for real
# instead of spilling into system memory under WSL. Changes no number. Everything else is pc11's, unchanged:
#   [SEG2-DONE] -> add19 pre-check + add19 -> GO-LOOP-P2A -> [SEG3-DONE] R8 (LFM3) -> GO-LOOP-P2B -> [V8 flag] V8 (LFM3) -> GO-AFTER-V8
# (addendum 19, LFM3-1.7B, after its Week-1 pre-check; addendum 20's R8 and V8 on LFM3, no K2 fallback). Base of R8 / V8 (addendum 20):
# addendum 19's flags if its run passes no harm (ARC >= pre - 5, diary >= base - 5, changed-new >= 53.3) and P1 (recall C2+C4 >= 88.5);
# else the defaults. If the pre-check finds the port broken, R8 and V8 are skipped and their turns are passed on. Both arms at
# --gen-bs 24; if R8 runs out of memory, both at 16. Budgets 16 h each. Code: $J/src-l3.
# Also new in pc12: if the pre-check runs out of memory at --gen-bs 24 (the cap is lower now), it reruns at 16 instead of reading as a broken port.
set -uo pipefail
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
  echo "sleepb-pc12 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc12\nowner: Design sleep like the human brain\nnow: %s (since %s)\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull4\\run.log\nends: writes the next flag in C:\\Users\\benja\\pc-jobs\\handoff and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc12.md"
}
release() {  # release NEXT_FLAG RC
  grep -qs sleepb-pc12 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc12.md"
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
echo "== sleepb-pc12 start $(date -u +%FT%TZ)"
source "$HOME/bbvenv/bin/activate" || { echo "== STOP: no venv"; exit 1; }
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
K2="--model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
L3M="--model LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd"
L3="$L3M --week backbone/sleep/brain/data/week2.json --seed 1 --arc-base --tok-budget 256 --reword backbone/sleep/brain/data/week2_reworded.json"
[ -f "$J/src-l3/backbone/sleep/brain/sleepb.py" ] || { echo "== STOP: no $J/src-l3 (the LFM3 port)"; exit 1; }
( while sleep 600; do [ -f "$R/cur4" ] && tail -n 60 "$(cat "$R/cur4")" > "$P/progress.txt"; done ) &
PROG=$!
trap 'kill $PROG 2>/dev/null' EXIT
# ---- slot 2: addendum 19 (LFM3), unless its pre-check finds the port broken
wait_turn "$W/pc-jobs/think2-p1/SEG2-DONE"
OA=$R/add14A/sleepb/$A
O19=$R/add19/sleepb/$A
busy "addendum 19 pre-check (LFM3, ~1 h), then the LFM3 week (~4-7 h, stops itself past 10 h)"
mkdir -p "$R/probe19" "$P/probe19"
echo "$R/probe19/probe.log" > "$R/cur4"
echo "-- add19 pre-check start $(date -u +%T)"
if [ ! -f "$R/probe19/probe.json" ] || ! grep -q '"partial": false' "$R/probe19/probe.json"; then
  (cd "$J/src-l3" && exec timeout 9000 python3 backbone/sleep/brain/k2_chain_probe.py $L3M --out "$R/probe19/probe.json" --variants q_think --tries 1 --gen-bs 24 --also-fixed) >> "$R/probe19/stdout.log" 2>&1
  echo "-- add19 pre-check exit $? $(date -u +%T)"
  if ! grep -qs '"partial": false' "$R/probe19/probe.json" && grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$R/probe19/stdout.log"; then
    echo "== add19 pre-check ran out of memory at gen-bs 24 (cap $SLEEPB_CUDA_CAP_GIB GiB): again at 16"
    mv "$R/probe19/stdout.log" "$R/probe19/stdout.mem24.log"
    (cd "$J/src-l3" && exec timeout 9000 python3 backbone/sleep/brain/k2_chain_probe.py $L3M --out "$R/probe19/probe.json" --variants q_think --tries 1 --gen-bs 16 --also-fixed) >> "$R/probe19/stdout.log" 2>&1
    echo "-- add19 pre-check (gen-bs 16) exit $? $(date -u +%T)"
  fi
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
  a19() { SRC=src-l3 run add19 "$O19" 10 $L3 --gen-bs "$1" --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
            --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96; }
  a19 24; R2=$?
  if [ "$R2" != 0 ] && mem "$O19"; then echo "== add19 ran out of memory at gen-bs 24: again at 16"; mv "$O19" "$O19.mem24"; a19 16; R2=$?; fi
  SLOT2=add19
else
  echo "== the LFM3 port is broken: slot 2 is passed on (addendum 20: K2 cannot finish a week within budget on this card)"
  R2=1; SLOT2=none
fi
echo "slot 2 ran $SLOT2" > "$P/slot2.txt"
release GO-LOOP-P2A "$R2"
# ---- addendum 20: the base of R8 / V8 on LFM3
if [ "$SLOT2" != add19 ]; then
  echo "NONE slot 2 did not run addendum 19 (the LFM3 port is broken): R8 and V8 are skipped" > "$P/base20.txt"
else
python3 - "$O19/result_$A.json" > "$P/base20.txt" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
    rec = 100 * r["scores"]["weights"]["forward"]["C24"]
    arc, arc0 = r["arc_easy"]["acc"], r["arc_easy_base"]["acc"]
    di, di0 = r["scores"]["diary"]["pooled"], r["scores"]["base_diary"]["pooled"]
    ch = 100 * r["scores"]["weights"]["changed"]["new"]
except Exception as e:
    print("DEFAULTS", f"addendum 19 has no complete result ({type(e).__name__})"); sys.exit()
ok = rec >= 88.5 and arc >= arc0 - 0.05 and di >= di0 - 0.05 and ch >= 53.3
why = f"add19 recall {rec:.1f} (>= 88.5), ARC {100*arc:.1f} vs pre {100*arc0:.1f} (>= pre - 5), diary {100*di:.1f} vs base {100*di0:.1f} (>= base - 5), changed-new {ch:.1f} (>= 53.3)"
print("ADD19" if ok else "DEFAULTS", why)
PY
fi
echo "== addendum 20 base: $(cat "$P/base20.txt")"
SKIP=""
case "$(cut -d' ' -f1 "$P/base20.txt")" in
  ADD19) BASE="--rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --rem-writer base --rem-pairs distinct --rem-parse first_q --rem-verify-tokens 96" ;;
  DEFAULTS) BASE="" ;;
  *) BASE=""; SKIP=1; echo "== no base for addendum 20: R8 and V8 are skipped, but their turns are still passed on" ;;
esac
# ---- addendum 20 R8 (LFM3)
wait_turn "$W/pc-jobs/think2-p1/SEG3-DONE"
GB=24
O8=$R/add20/sleepb
[ -n "$SKIP" ] || busy "addendum 20 R8 (LFM3 8x, ~8-12 h, stops itself past 16 h)"
RR=0; [ -n "$SKIP" ] || { SRC=src-l3 run add20-R8 "$O8/R8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4; RR=$?; }
if [ -z "$SKIP" ] && [ "$RR" != 0 ] && mem "$O8/R8"; then
  echo "== R8 ran out of memory at gen-bs 24: again at 16 (V8 uses 16 too)"; mv "$O8/R8" "$O8/R8.mem24"; GB=16
  SRC=src-l3 run add20-R8 "$O8/R8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --text-scale 4
fi
R8RC=$([ -f "$O8/R8/result_$A.json" ] && echo 0 || echo 1)
echo "add20 gen-bs $GB" > "$P/add20-genbs.txt"
release GO-LOOP-P2B "$R8RC"
# ---- addendum 20 V8 (LFM3)
wait_turn "$V8_FLAG"
[ -n "$SKIP" ] || busy "addendum 20 V8 (LFM3 8x, ~8-12 h, stops itself past 16 h)"
RV=0; [ -n "$SKIP" ] || { SRC=src-l3 run add20-V8 "$O8/V8" 16 $L3 $BASE --gen-bs $GB --budget-scale 8 --dream-vary mix; RV=$?; }
if [ -z "$SKIP" ] && [ "$RV" != 0 ] && mem "$O8/V8" && [ "$GB" = 24 ]; then
  echo "== V8 ran out of memory at gen-bs 24: again at 16 (now unequal to R8; recorded)"; mv "$O8/V8" "$O8/V8.mem24"
  echo "add20 V8 gen-bs 16 (R8 24)" >> "$P/add20-genbs.txt"
  SRC=src-l3 run add20-V8 "$O8/V8" 16 $L3 $BASE --gen-bs 16 --budget-scale 8 --dream-vary mix
fi
release GO-AFTER-V8 "$([ -f "$O8/V8/result_$A.json" ] && echo 0 || echo 1)"
echo "done $(date -u +%FT%TZ)" > "$P/DONE"
echo "== sleepb-pc12 end $(date -u +%FT%TZ)"
