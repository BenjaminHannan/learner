#!/usr/bin/env bash
# PC order from 19:35Z Oct 27 (coordinator): sleep arm A -> hops B + A (pc_hops.sh A, DONE_FLAG=handoff/GO-RACE-MINI) -> race-mini v2 ->
# the rest of the sleep chain, which waits for think2-p1/SEG2-DONE. This bridge writes SEG2-DONE once race-mini v2 writes
# handoff/RACE-MINI-DONE. So that the sleep chain never stalls, it also writes SEG2-DONE when hops pair A has finished
# (handoff/HOPS-A-DONE) but no race-mini driver has run for STALL_S seconds in a row. Only flags newer than this script's start count.
#   bash pc_race_bridge.sh
set -u
JOBS=${JOBS:-/mnt/c/Users/benja/pc-jobs}
HAND=$JOBS/handoff
OUTFLAG=${OUTFLAG:-$JOBS/think2-p1/SEG2-DONE}
LOG=${LOG:-$HOME/hops/race_bridge.log}
POLL=${POLL:-60}
STALL_S=${STALL_S:-900}  # seconds with no driver after hops pair A, before giving up on race-mini
DRIVER_RE='^(/usr/bin/|/bin/)?bash [^ ]*pc_race_mini\.sh( |$)'
mkdir -p "$(dirname "$LOG")"
STAMP=$(mktemp)  # only flags newer than this count
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
fresh() { [ -f "$1" ] && [ "$1" -nt "$STAMP" ]; }
log "bridge start: waiting for $HAND/RACE-MINI-DONE, then writing $OUTFLAG"
idle=0
while true; do
  if fresh "$HAND/RACE-MINI-DONE"; then why="race-mini v2 done: $(head -c 200 "$HAND/RACE-MINI-DONE" | tr '\n' ' ')"; break; fi
  if fresh "$HAND/HOPS-A-DONE" && ! pgrep -f "$DRIVER_RE" > /dev/null; then
    idle=$((idle + 1))
    if [ $((idle * POLL)) -ge "$STALL_S" ]; then why="no race-mini driver for $STALL_S s after hops pair A; race-mini skipped"; break; fi
  else
    idle=0
  fi
  sleep "$POLL"
done
mkdir -p "$(dirname "$OUTFLAG")"
echo "0 $(date -u +%FT%TZ) $why" > "$OUTFLAG"
log "wrote $OUTFLAG ($why)"
rm -f "$STAMP"
