#!/usr/bin/env bash
# Sleep-B on Ben's PC: addendum 17 again, in the same PC slot as sleepb_pc3.sh (which is stopped by hand first, without its DONE).
# sleepb_pc3's run trained night 1 (296 steps; 175 s on a 5090) for over 1.5 h with the card at 15.9 of 16.3 GB: suggested, a full card
# spilling into system memory under WSL. This run uses code with cuda_tidy() (cached blocks are handed back between generation and
# training; no number changes) and --tok-budget 256 (smaller training pieces; rounding only), from $J/src-fix.
# Watchdog: if the run log is silent for 90 min (the code now logs every 200 training steps), the run is stopped as too slow.
# It ends like sleepb_pc3 would have: it writes $R/pull3/DONE (the looping thread's segment 1 starts on it) and clears its GPU-BUSY.txt.
set -uo pipefail
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
P=$R/pull3
mkdir -p "$P"
exec >>"$P/run.log" 2>&1
A=ab_ob_b4_nb
O=$R/add17d/sleepb/$A
finish() {
  echo "== sleepb-pc5 end $(date -u +%FT%TZ) code $1"
  for x in ${SMI:-} ${PROG:-} ${DOG:-}; do kill "$x" 2>/dev/null; done
  mkdir -p "$P/add17d"
  cp -f "$O/sleepb.log" "$O/result_$A.json" "$P/add17d/" 2>/dev/null
  echo "$1 $(date -u +%FT%TZ)" > "$P/DONE"
  grep -qs "sleepb-pc5" "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc3.md" "$W/pc-jobs/sleepb-pc5.md"
  exit "$1"
}
echo "== sleepb-pc5 start $(date -u +%FT%TZ)"
echo "sleepb-pc5 (Design sleep like the human brain): addendum 17 retry, started $(date -u +%FT%TZ), ~8-10 h if healthy; stops itself if training crawls" > "$W/GPU-BUSY.txt"
rm -f "$W/pc-jobs/sleepb-pc3.md"
printf '# sleepb-pc5\nowner: Design sleep like the human brain\nwhat: Sleep-B addendum 17 retry (K2-Horizon-3.7B), ~8-10 h\nstarted: %s\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull3\\run.log\nends: writes pull3\\DONE and removes this card and GPU-BUSY.txt\n' "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc5.md"
source "$HOME/bbvenv/bin/activate" || finish 1
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -l 5 > "$P/smi5.csv" 2>&1 &
SMI=$!
mkdir -p "$O"
touch "$O/sleepb.log"
( while sleep 600; do tail -n 60 "$O/sleepb.log" > "$P/progress.txt" 2>/dev/null; done ) &
PROG=$!
echo "-- add17 (retry) start $(date -u +%T): tok-budget 256, gen-bs 24, cuda_tidy"
(cd "$J/src-fix" && exec python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$O" --tok-budget 256 --model IFM/K2-Horizon-3.7B \
  --week backbone/sleep/brain/data/week2.json --seed 1 \
  --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --arc-base --gen-bs 24 \
  --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
  --reword backbone/sleep/brain/data/week2_reworded.json) >> "$O/sleepb.log" 2>&1 &
PY=$!
( while sleep 300; do
    if [ $(( $(date +%s) - $(stat -c %Y "$O/sleepb.log") )) -gt 5400 ]; then
      echo "== watchdog: no log line for 90 min at $(date -u +%T): stopping the run as too slow"; touch "$P/TOO-SLOW"; kill "$PY"; break
    fi
  done ) &
DOG=$!
wait "$PY"
RC=$?
echo "-- add17 (retry) exit $RC $(date -u +%T)$([ -f "$P/TOO-SLOW" ] && echo ' (watchdog)')"
finish "$RC"
