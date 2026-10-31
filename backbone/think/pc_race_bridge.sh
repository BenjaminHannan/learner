#!/usr/bin/env bash
# PC order from 19:35Z Oct 27 (coordinator): sleep arm A -> hops B + A (pc_hops.sh A, DONE_FLAG=handoff/GO-RACE-MINI) -> race-mini v2 ->
# the rest of the sleep chain, which waits for think2-p1/SEG2-DONE. This bridge writes SEG2-DONE once race-mini v2 writes
# handoff/RACE-MINI-DONE. So that the sleep chain never stalls, it also writes SEG2-DONE when the flag AFTER_FLAG (default hops pair A's,
# handoff/HOPS-A-DONE) is there but no race-mini driver has run for STALL_S seconds in a row. Only flags newer than this script's start count.
#   bash pc_race_bridge.sh
# Two optional settings (env; with neither set, the bridge does what it did before, down to the text of SEG2-DONE):
#   AFTER_FLAG  the flag that starts the stall check, in place of handoff/HOPS-A-DONE. The order of Oct 28 runs the hops round-2 jobs ahead of race-mini,
#               so the flag is the last of them (handoff/HOPS-R-round2_hloopi-DONE): race-mini is held back until then, and a missing driver before
#               that flag proves nothing.
#   THEN_CMD    a command (run as bash -c, in the foreground, stdin from /dev/null) for the steps that must finish before the sleep chain may start
#               (pc_hops_chain.sh). It runs once the wait loop ends (race-mini done, or skipped), BEFORE OUTFLAG is written; its start, end and exit
#               code go to the log. OUTFLAG is written whatever the code was ("0 <utc> <why>; then rc=N": the flag only hands the GPU on, the
#               code is for whoever reads it). Default: none.
set -u
JOBS=${JOBS:-/mnt/c/Users/benja/pc-jobs}
HAND=$JOBS/handoff
OUTFLAG=${OUTFLAG:-$JOBS/think2-p1/SEG2-DONE}
LOG=${LOG:-$HOME/hops/race_bridge.log}
POLL=${POLL:-60}
STALL_S=${STALL_S:-900}  # seconds with no driver after AFTER_FLAG (hops pair A by default), before giving up on race-mini
AFTER_FLAG=${AFTER_FLAG:-$HAND/HOPS-A-DONE}
THEN_CMD=${THEN_CMD:-}
if [ "$AFTER_FLAG" = "$HAND/HOPS-A-DONE" ]; then AFTER_TXT="hops pair A"; else AFTER_TXT="$(basename "$AFTER_FLAG")"; fi
DRIVER_RE='^(/usr/bin/|/bin/)?bash [^ ]*pc_race_mini\.sh( |$)'
mkdir -p "$(dirname "$LOG")"
STAMP=$(mktemp)  # only flags newer than this count
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
fresh() { [ -f "$1" ] && [ "$1" -nt "$STAMP" ]; }
log "bridge start: waiting for $HAND/RACE-MINI-DONE, then writing $OUTFLAG"
if [ "$AFTER_FLAG" != "$HAND/HOPS-A-DONE" ] || [ -n "$THEN_CMD" ]; then log "bridge settings: AFTER_FLAG=$AFTER_FLAG THEN_CMD=${THEN_CMD:-(none)}"; fi
idle=0
while true; do
  if fresh "$HAND/RACE-MINI-DONE"; then why="race-mini v2 done: $(head -c 200 "$HAND/RACE-MINI-DONE" | tr '\n' ' ')"; break; fi
  if fresh "$AFTER_FLAG" && ! pgrep -f "$DRIVER_RE" > /dev/null; then
    idle=$((idle + 1))
    if [ $((idle * POLL)) -ge "$STALL_S" ]; then why="no race-mini driver for $STALL_S s after $AFTER_TXT; race-mini skipped"; break; fi
  else
    idle=0
  fi
  sleep "$POLL"
done
then_txt=""
if [ -n "$THEN_CMD" ]; then
  log "then-command start ($why): $THEN_CMD"
  bash -c "$THEN_CMD" < /dev/null
  then_rc=$?
  log "then-command end rc=$then_rc"
  then_txt="; then rc=$then_rc"
fi
mkdir -p "$(dirname "$OUTFLAG")"
echo "0 $(date -u +%FT%TZ) $why$then_txt" > "$OUTFLAG"
log "wrote $OUTFLAG ($why$then_txt)"
rm -f "$STAMP"
