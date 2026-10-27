#!/usr/bin/env bash
# Sleep-B on Ben's PC (RTX 5070 Ti, 16 GB; WSL; ~/bbvenv), second launch: the addendum 16 rerun, then addendum 17, from $J/src-next (a git
# archive of the commit with the selftest_shy memory fix). PC order (coordinator, 2026-10-26): the thinking thread's toy check, then this,
# then the thinking thread's P1/P2. The first launch (sleepb_pc.sh) ran out of GPU memory: arm A in its startup self-test, add16 at the first
# training step's full-vocabulary KL with --tok-budget 2048. In WSL, out of memory can show as "CUDA driver error: device not ready".
# - add16 (C, T1, T2): --tok-budget 1024 for all three (same loss and gradients, smaller pieces); if any run runs out of memory, all three
#   start again at 512, since the prereg fixes that the three match.
# - add17: --gen-bs 24 and --tok-budget 512; if it runs out of memory, it starts again at gen-bs 16.
# It waits for its turn: $R/GO-NEXT from the toy's owner (or 3 h with no GO-NEXT), then a free GPU (no GPU-BUSY.txt, under 4 GB used, twice
# 2 min apart). Small files go to $R/pull2. At the end it writes $R/pull2/DONE and clears its GPU-BUSY.txt and job card.
set -uo pipefail
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
P=$R/pull2
mkdir -p "$P"
exec >>"$P/run.log" 2>&1
finish() {
  echo "== sleepb-pc2 end $(date -u +%FT%TZ) code $1"
  [ -n "${PROG:-}" ] && kill "$PROG" 2>/dev/null
  echo "$1 $(date -u +%FT%TZ)" > "$P/DONE"
  grep -qs sleepb-pc2 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc2.md"
  exit "$1"
}
gpu_used() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1; }
free_now() { [ ! -f "$W/GPU-BUSY.txt" ] && [ "$(gpu_used)" -lt 4000 ] 2>/dev/null; }
busy() {  # busy WHAT: the GPU-BUSY.txt and job card for the current step
  echo "sleepb-pc2 (Design sleep like the human brain): $1, started $(date -u +%FT%TZ)" > "$W/GPU-BUSY.txt"
  printf '# sleepb-pc2\nowner: Design sleep like the human brain\nnow: %s (since %s)\nthen: addendum 17 (K2-Horizon-3.7B, ~8-10 h) unless it is running now\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull2\\run.log\nends: writes pull2\\DONE and removes this card and GPU-BUSY.txt\n' "$1" "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc2.md"
}
echo "== sleepb-pc2 waiting for its turn $(date -u +%FT%TZ)"
t0=$(date +%s)
while :; do
  if [ -f "$R/GO-NEXT" ] || [ $(( $(date +%s) - t0 )) -gt 10800 ]; then
    if free_now; then sleep 120; free_now && break; fi
  fi
  if [ $(( $(date +%s) - t0 )) -gt 108000 ]; then echo "== gave up waiting after 30 h"; finish 4; fi
  sleep 60
done
echo "== turn came $(date -u +%FT%TZ): GO-NEXT $([ -f "$R/GO-NEXT" ] && echo yes || echo no), GPU used $(gpu_used) MiB"
busy "addendum 16 rerun (3 Qwen3.5-2B runs, ~4 h), then addendum 17 (~8-10 h)"
source "$HOME/bbvenv/bin/activate" || finish 1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv || true
python3 -c "import torch, transformers, peft, datasets, fla, sys; print('versions', torch.__version__, transformers.__version__, peft.__version__, datasets.__version__, fla.__version__); sys.exit(0 if torch.cuda.is_available() and transformers.__version__ == '5.20.2' and peft.__version__ == '0.21.2' and fla.__version__ == '0.6.0' else 1)" || { echo "== STOP: version check failed"; finish 1; }
( while sleep 600; do [ -f "$R/cur2" ] && tail -n 60 "$(cat "$R/cur2")" > "$P/progress.txt"; done ) &
PROG=$!
A=ab_ob_b4_nb
mem() { grep -qs "OutOfMemoryError\|CUDA out of memory\|device not ready" "$1/sleepb.log"; }
run() {  # run NAME OUT EXTRA...: one sleepb run from $J/src-next; its log and result JSON are copied to pull2/NAME when it ends
  local n=$1 o=$2; shift 2
  if [ -f "$o/result_$A.json" ]; then echo "-- skip $n (done)"; return 0; fi
  mkdir -p "$o"
  echo "$o/sleepb.log" > "$R/cur2"
  echo "-- $n start $(date -u +%T) $*"
  (cd "$J/src-next" && python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" "$@") >> "$o/sleepb.log" 2>&1
  local rc=$?
  echo "-- $n exit $rc $(date -u +%T)"
  mkdir -p "$P/$n"
  cp -f "$o/sleepb.log" "$o/result_$A.json" "$P/$n/" 2>/dev/null
  return $rc
}
# addendum 16 rerun (sealed prereg: the same --gen-bs and --tok-budget for all three runs)
O16=$R/add16b/sleepb
add16() {  # add16 TOK_BUDGET: C, T1, T2; returns 2 if any of them ran out of memory
  local c="--model Qwen/Qwen3.5-2B --week backbone/sleep/brain/data/week2.json --seed 1 --tok-budget $1 --gen-bs 32 --budget-scale 2 --card-stats"
  run add16-C "$O16/C" $c || { mem "$O16/C" && return 2; }
  run add16-T1 "$O16/T1" $c --skip-known 0.25 || { mem "$O16/T1" && return 2; }
  run add16-T2 "$O16/T2" $c --rem-views 20 || { mem "$O16/T2" && return 2; }
  return 0
}
add16 1024
if [ $? = 2 ]; then
  echo "== add16 ran out of memory at tok-budget 1024: all three again at 512"
  mv "$O16" "$O16.mem1024"
  add16 512
  echo "add16 tok-budget 512" > "$P/add16-tokbudget.txt"
else
  echo "add16 tok-budget 1024" > "$P/add16-tokbudget.txt"
fi
# addendum 17 (k2c_r2_g570): arm B's flags + --gate-arc-n 570, at gen-bs 24 and tok-budget 512 to fit 16 GB
busy "addendum 17 (K2-Horizon-3.7B, ~8-10 h)"
O17=$R/add17/sleepb/$A
add17() {
  run add17 "$O17" --tok-budget 512 --model IFM/K2-Horizon-3.7B --week backbone/sleep/brain/data/week2.json --seed 1 \
    --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --arc-base --gen-bs "$1" \
    --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
    --reword backbone/sleep/brain/data/week2_reworded.json
}
add17 24
RC=$?
if [ "$RC" != 0 ] && mem "$O17"; then
  echo "== add17 ran out of memory at gen-bs 24: starting again at 16"
  mv "$O17" "$O17.mem24"
  add17 16
  RC=$?
fi
finish "$RC"
