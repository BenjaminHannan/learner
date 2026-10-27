#!/usr/bin/env bash
# Sleep-B on Ben's PC: addendum 17, fifth try, in the same PC slot (sleepb_pc5 is stopped by hand first, without its DONE).
# sleepb_pc5 (cuda_tidy, --tok-budget 256) trained night 1 in 1897 s (227 s for the whole night on the 5090), with PyTorch's reserved
# memory at 16.0 GiB on a 15.9 GiB card: under WSL a full card does not report out of memory, it spills into system memory and crawls.
# This run caps PyTorch at SLEEPB_CUDA_CAP_GIB=14 (code $J/src-cap: under the cap the allocator hands cached blocks back and retries
# instead of spilling; no number changes). Peak use in night 1 was 12.9 GiB. Out of memory under the cap: once more at --gen-bs 16.
# Stops: a 90 min silent log, or (after night 2 or later) a projected end after $DEADLINE. Either way it writes $R/pull3/DONE (the
# looping thread's segment 1 starts on it) and clears its GPU-BUSY.txt.
set -uo pipefail
export SLEEPB_CUDA_CAP_GIB=${SLEEPB_CUDA_CAP_GIB:-14}
DEADLINE=${DEADLINE:-2026-10-27T18:00:00Z}
J=${J:-$HOME/sleepb-pc}
R=${R:-/mnt/c/Users/benja/pc-jobs/sleepb-pc}
W=/mnt/c/Users/benja
P=$R/pull3
mkdir -p "$P"
exec >>"$P/run.log" 2>&1
A=ab_ob_b4_nb
O=$R/add17e/sleepb/$A
O2=$R/add17e2/sleepb/$A
finish() {
  echo "== sleepb-pc6 end $(date -u +%FT%TZ) code $1"
  for x in ${SMI:-} ${PROG:-} ${DOG:-}; do kill "$x" 2>/dev/null; done
  for o in "$O" "$O2"; do [ -d "$o" ] && mkdir -p "$P/$(basename "$(dirname "$(dirname "$o")")")" && cp -f "$o/sleepb.log" "$o/result_$A.json" "$P/$(basename "$(dirname "$(dirname "$o")")")/"; done 2>/dev/null
  echo "$1 $(date -u +%FT%TZ)" > "$P/DONE"
  grep -qs "sleepb-pc6" "$W/GPU-BUSY.txt" && rm -f "$W/GPU-BUSY.txt"
  rm -f "$W/pc-jobs/sleepb-pc3.md" "$W/pc-jobs/sleepb-pc5.md" "$W/pc-jobs/sleepb-pc6.md"
  exit "$1"
}
echo "== sleepb-pc6 start $(date -u +%FT%TZ)"
rm -f "$P/TOO-SLOW"
echo "sleepb-pc6 (Design sleep like the human brain): addendum 17 fifth try, started $(date -u +%FT%TZ), ~7-9 h if healthy; stops itself if training crawls or would end after $DEADLINE" > "$W/GPU-BUSY.txt"
rm -f "$W/pc-jobs/sleepb-pc3.md" "$W/pc-jobs/sleepb-pc5.md"
printf '# sleepb-pc6\nowner: Design sleep like the human brain\nwhat: Sleep-B addendum 17 fifth try (K2-Horizon-3.7B), ~7-9 h, stops if projected to end after 18:00Z\nstarted: %s\nlog: C:\\Users\\benja\\pc-jobs\\sleepb-pc\\pull3\\run.log\nends: writes pull3\\DONE and removes this card and GPU-BUSY.txt\n' "$(date -u +%FT%TZ)" > "$W/pc-jobs/sleepb-pc6.md"
source "$HOME/bbvenv/bin/activate" || finish 1
unset PYTORCH_CUDA_ALLOC_CONF PYTORCH_ALLOC_CONF
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu --format=csv -l 5 > "$P/smi6.csv" 2>&1 &
SMI=$!
go() {  # go OUT GENBS: one add17 run in the background, with the watchdog; returns its exit code
  local o=$1 gb=$2
  mkdir -p "$o"; touch "$o/sleepb.log"; echo "$o/sleepb.log" > "$P/cur"
  echo "-- add17 (fifth try) start $(date -u +%T): cap ${SLEEPB_CUDA_CAP_GIB} GiB, tok-budget 256, gen-bs $gb -> $o"
  (cd "$J/src-cap" && exec python3 backbone/sleep/brain/sleepb.py --arm "$A" --out "$o" --tok-budget 256 --model IFM/K2-Horizon-3.7B \
    --week backbone/sleep/brain/data/week2.json --seed 1 \
    --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 --arc-base --gen-bs "$gb" \
    --rem-chain-mode q_think --rem-dirs both --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --think-eval \
    --reword backbone/sleep/brain/data/week2_reworded.json) >> "$o/sleepb.log" 2>&1 &
  local py=$! dl
  dl=$(date -d "$DEADLINE" +%s)
  ( seen=0; while sleep 300; do
      if [ $(( $(date +%s) - $(stat -c %Y "$o/sleepb.log") )) -gt 5400 ]; then
        echo "== watchdog: no log line for 90 min at $(date -u +%T): stopping the run as too slow"; touch "$P/TOO-SLOW"; kill "$py"; break
      fi
      # once per night, within 5 min of night 2+ ending: the rest at 1.25x that night's seconds, plus 75 min of final scoring
      last=$(grep '^\[night [0-9]*\] done steps .* [0-9]*s$' "$o/sleepb.log" | tail -1)
      n=$(echo "$last" | sed -n 's/^\[night \([0-9]*\)\].*/\1/p'); sec=$(echo "$last" | sed -n 's/.* \([0-9]*\)s$/\1/p')
      if [ -n "$n" ] && [ -n "$sec" ] && [ "$n" -ge 2 ] && [ "$n" -lt 7 ] && [ "$n" -ne "$seen" ]; then
        seen=$n
        end=$(( $(date +%s) + (7 - n) * sec * 5 / 4 + 4500 ))
        if [ "$end" -gt "$dl" ]; then
          echo "== projection after night $n (${sec}s): would end $(date -u -d @$end +%FT%TZ), after $DEADLINE; stopping"; touch "$P/TOO-SLOW"; kill "$py"; break
        fi
      fi
    done ) &
  local dog=$!
  wait "$py"; local rc=$?
  kill "$dog" 2>/dev/null
  echo "-- add17 (fifth try) exit $rc $(date -u +%T)$([ -f "$P/TOO-SLOW" ] && echo ' (stopped)')"
  return "$rc"
}
( while sleep 600; do tail -n 60 "$(cat "$P/cur" 2>/dev/null)" > "$P/progress.txt" 2>/dev/null; done ) &
PROG=$!
go "$O" 24; RC=$?
if [ "$RC" -ne 0 ] && [ ! -f "$P/TOO-SLOW" ] && grep -qs "OutOfMemoryError\|CUDA out of memory" "$O/sleepb.log"; then
  echo "-- out of memory under the cap at gen-bs 24: once more at 16"
  go "$O2" 16; RC=$?
fi
finish "$RC"
