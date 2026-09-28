#!/bin/bash
# dir-h6 vast guard (kit sleeph6r, 2026-09-28; pattern of the sleep358n3r guard). Started detached on the Mac by vstart.sh AS SOON AS
# ssh answers (before any upload); runs from $G (its own copy, so no worktree or queue job needs to stay alive).
# Every 5 minutes: money and time check, then the rental's progress file. It writes its own pid to $G/guard.pid.
# Ends on the first of the reasons below, then:
#   copy back (checked file by file against a sha256 manifest made on the rental) -> destroy the instance by its exact id (confirmed
#   gone). If the copy check fails twice, or ssh is lost, it STOPS the instance instead (GPU billing ends, files stay on its disk)
#   and writes <reason>-STOPPED-NOT-DESTROYED for the Director. The last line of $G/END is the reason.
#   DONE           drive.sh finished (checks, 4 seed runs). Copy check "runs": every run has its result file or a DIED record.
#   FAILED         drive.sh stopped itself (its reason is kept; nothing was launched). Copy check "partial".
#   BUDGET-STOP    all rentals of this task reach $3.00 (cap $4.00). Runs are HALTED by exact pid first, then copy check "partial".
#   TIME-STOP      the time cap since the first rental (1.5 x the card's estimate; in $G/state). Halt, then "partial".
#   STALL          no log on the rental grew for 30 min and the GPU is idle (only judged once a seed run has launched). Halt, "partial".
#   PRELAUNCH-STOP no seed run had launched 45 min after ssh answered (uploads, pip, seals, checks, smoke). Halt, "partial".
#   HOST-FAIL      no ssh answer for 20 min (nothing can be copied: stopped, not destroyed)
# "partial" keeps what exists: a seed with no result file is a dead seed (PASSMARKS.md), it is not a reason to keep paying.
# Every 30 min the rental's small files are also copied to $G/snap (a save during the run; not checked against a manifest).
set -u
G=$1
. "$G/vcommon.sh"
read -r ID H P TC < "$G/state"; TIME_CAP=${TC:-$TIME_CAP}
SS=$(sshto "$H" "$P")
T0=$(head -1 "$G/rentals.txt" | awk '{print $3}')
GT0=$(date +%s)
[ -s "$G/END" ] && { echo "guard: already ended ($(cat "$G/END"))"; exit 0; }
echo $$ > "$G/guard.pid"
fin() { log "GUARD-END $1, spent \$$(spent)"; echo "END $1 spent $(spent)" > "$G/END"; rm -f "$G/guard.pid"; exit 0; }
# halt the runs and drive.sh by the exact pids drive.sh wrote to W/pids.txt, so nothing writes while the files are copied
halt() { $SS "bash /root/r/handoff/kit/sleeph6r/box/halt.sh $1" < /dev/null >> "$G/log.txt" 2>&1; }
snapshot() {
  mkdir -p "$G/snap"
  $SS 'cd /root/r && find W drive.log -type f ! -name "*.pt" 2>/dev/null | tar -cf - -T -' < /dev/null 2>/dev/null | tar -x -C "$G/snap" 2>/dev/null \
    && log "SNAPSHOT: the rental's small files copied to $G/snap (not manifest-checked)" || log "SNAPSHOT: failed (ssh?), the run goes on"
}
# end <REASON> <detail> <runs|partial|nocopy>
end() {
  log "GUARD $1${2:+: $2}"
  [ "$3" = partial ] && halt "$1"
  if [ "$3" != nocopy ] && { copy_back "$3" || copy_back "$3"; }; then destroy "$ID" && fin "$1" || fin "$1-DESTROY-UNCONFIRMED"; fi
  stop_inst "$ID" && fin "$1-STOPPED-NOT-DESTROYED" || fin "$1-STOP-UNCONFIRMED"
}
log "GUARD start pid $$ instance $ID"
miss=0; still=0; lastsz=""; good=0
while :; do
  over "$(spent)" "$CAP_STOP" && end BUDGET-STOP "spent \$$(spent)" partial
  [ $(( $(date +%s) - T0 )) -ge "$TIME_CAP" ] && end TIME-STOP "time cap $TIME_CAP s since the first rental" partial
  out=$($SS "$POLL" < /dev/null 2>/dev/null)
  if [ -z "$out" ]; then
    miss=$((miss+1)); log "no ssh answer ($miss), status $(status_of "$ID")"
    [ $miss -ge 4 ] && end HOST-FAIL "no ssh answer for 20 min" nocopy
  else
    miss=0
    last=$(echo "$out" | sed -n 's/^last=//p'); sz=$(echo "$out" | sed -n 's/^bytes=//p'); gpu=$(echo "$out" | sed -n 's/^gpu=//p'); nl=$(echo "$out" | sed -n 's/^launches=//p')
    case "$last" in *" DONE") end DONE "" runs;; *" FAILED "*) end FAILED "$last" partial;; esac
    if [ "${nl:-0}" = 0 ]; then
      [ $(( $(date +%s) - GT0 )) -ge "$PRE_MAX" ] && end PRELAUNCH-STOP "no seed run launched $PRE_MAX s after ssh answered (last: ${last:-none})" partial
    else
      if [ "$sz" = "$lastsz" ] && [ "${gpu:-0}" = 0 ]; then still=$((still+1)); else still=0; fi
      [ $still -ge 6 ] && end STALL "no log growth for 30 min, GPU idle" partial
    fi
    lastsz=$sz
    echo "$(now) ok: ${last:-no progress line yet} | bytes ${sz:-?} | gpu ${gpu:-?}% | spent \$$(spent)" >> "$G/log.txt"
    good=$((good+1)); [ $((good % SNAP_EVERY)) = 0 ] && snapshot
  fi
  sleep 300
done
