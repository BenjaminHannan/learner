#!/usr/bin/env bash
# Sleep-B on Ben's PC, third launch: addendum 17 alone, with PyTorch's default CUDA allocator. sleepb_pc2.sh's add17 died at night 1's first
# KL step with "CUDA driver error: device not ready" at gen-bs 24 and 16 (tok-budget 512), although by estimate that step needs well under
# the 16 GB the card has. Suggested (untested): expandable segments (PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True) misbehave under WSL.
# The allocator setting does not change any numbers. A 5 s nvidia-smi log ($P/smi.csv) shows whether memory was really full.
# Same flags as sleepb_pc2.sh's add17: gen-bs 24, tok-budget 512, code $J/src-next. No retries: on failure the GPU is handed back at once.
set -uo pipefail
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
P=$R/pull3
mkdir -p "$P"
exec >>"$P/run.log" 2>&1
finish() {
  echo "== sleepb-pc3 end $(date -u +%FT%TZ) code $1"
  [ -n "${SMI:-}" ] && kill "$SMI" 2>/dev/null
  [ -n "${PROG:-}" ] && kill "$PROG" 2>/dev/null
  echo "$1 $(date -u +%FT%TZ)" > "$P/DONE"
  grep -qs sleepb-pc3 "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc3.md"
  exit "$1"
}
echo "== sleepb-pc3 start $(date -u +%FT%TZ)"
if [ -s "$W/GPU-BUSY.txt" ]; then echo "== GPU-BUSY.txt is set: $(cat "$W/GPU-BUSY.txt"); not starting"; finish 5; fi
echo "sleepb-pc3 (Design sleep like the human brain): addendum 17, started $(date -u +%FT%TZ), ~8-10 h; if it fails it ends within minutes" > "$W/GPU-BUSY.txt"
printf '# sleepb-pc3\nowner: Design sleep like the human brain\nwhat: Sleep-B addendum 17 (K2-Horizon-3.7B, steadier morning gate), ~8-10 h\nstarted: %s\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull3\\run.log\nends: writes pull3\\DONE and removes this card and GPU-BUSY.txt\n' "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc3.md"
source "$HOME/bbvenv/bin/activate" || finish 1
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -l 5 > "$P/smi.csv" 2>&1 &
SMI=$!
( while sleep 600; do tail -n 60 "$R/add17c/sleepb/ab_ob_b4_nb/sleepb.log" > "$P/progress.txt" 2>/dev/null; done ) &
PROG=$!
A=ab_ob_b4_nb
O=$R/add17c/sleepb/$A
mkdir -p "$O"
echo "-- add17 start $(date -u +%T) (default allocator)"
(cd "$J/src-next" && python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$O" --tok-budget 512 --model IFM/K2-Horizon-3.7B \
  --week backbone/sleep/brain/data/week2.json --seed 1 \
  --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --arc-base --gen-bs 24 \
  --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
  --reword backbone/sleep/brain/data/week2_reworded.json) >> "$O/sleepb.log" 2>&1
RC=$?
echo "-- add17 exit $RC $(date -u +%T)"
mkdir -p "$P/add17"
cp -f "$O/sleepb.log" "$O/result_$A.json" "$P/add17/" 2>/dev/null
finish "$RC"
