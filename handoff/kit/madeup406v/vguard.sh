#!/bin/bash
# mu-406 vast guard ("Making things up about you" thread, Claude, 2026-09-27; copy of the sleep research thread's
# handoff/kit/sleep358sv/vguard.sh with mu-406's log paths). Started detached on the Mac by vstart.sh; runs from $G (its own
# copy, so no worktree or queue job needs to stay alive). Every 5 minutes: money and time check, then the rental's progress file.
# Ends on the first of the reasons below. It copies back what exists and checks every file against a sha256 manifest made on
# the rental, the adapter's Mac copy against SEAL-run, and (after DONE) every expected output. Only then does it destroy the
# instance by its exact id (confirmed gone). If the check fails twice, or ssh is lost, it STOPS the instance instead (GPU
# billing ends, files stay on its disk) and writes <reason>-STOPPED-NOT-DESTROYED for the Director.
#   DONE        drive.sh finished (training, merge, smoke, the 5 arms, the no-harm runs and their score)
#   FAILED      drive.sh stopped itself (its reason is kept)
#   BUDGET-STOP all rentals of this task reach $3.00 (cap $4)
#   TIME-STOP   the time cap since the first rental (3.5 h on a 5090, scaled up for slower cards; in $G/state)
#   STALL       no log on the rental grew for 30 min and the GPU is idle
#   HOST-FAIL   no ssh answer for 20 min (nothing can be copied: stopped, not destroyed)
# The last line of $G/END is the reason. vcollect.sh (a queue job) moves the copied files into the repo.
set -u
G=$1
. "$G/vcommon.sh"
read -r ID H P TC < "$G/state"; TIME_CAP=${TC:-$TIME_CAP}
SS=$(sshto "$H" "$P")
T0=$(head -1 "$G/rentals.txt" | awk '{print $3}')
fin() { log "GUARD-END $1, spent \$$(spent)"; echo "END $1 spent $(spent)" > "$G/END"; exit 0; }
end() { log "GUARD $1${2:+: $2}"
  if [ "${3:-}" != nocopy ] && { copy_back runs || copy_back runs; }; then destroy "$ID" && fin "$1" || fin "$1-DESTROY-UNCONFIRMED"; fi
  stop_inst "$ID" && fin "$1-STOPPED-NOT-DESTROYED" || fin "$1-STOP-UNCONFIRMED"; }
[ -s "$G/END" ] && { echo "guard: already ended ($(cat "$G/END"))"; exit 0; }
log "GUARD start pid $$ instance $ID, time cap $TIME_CAP s, money stop \$$CAP_STOP"
miss=0; still=0; lastsz=""
while :; do
  over "$(spent)" "$CAP_STOP" && end BUDGET-STOP "spent \$$(spent)"
  [ $(( $(date +%s) - T0 )) -ge "$TIME_CAP" ] && end TIME-STOP "time cap $TIME_CAP s since the first rental"
  out=$($SS 'tail -1 /root/r/W/drive-state.txt; cat /root/r/W/*.log /root/r/W/*.err /root/r/W/*/*.txt /root/r/W/*/*.jsonl /root/r/W/drive-state.txt 2>/dev/null | wc -c; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1' < /dev/null 2>/dev/null)
  if [ -z "$out" ]; then
    miss=$((miss+1)); log "no ssh answer ($miss), status $(status_of "$ID")"
    [ $miss -ge 4 ] && end HOST-FAIL "no ssh answer for 20 min" nocopy
  else
    miss=0; last=$(echo "$out" | sed -n 1p); sz=$(echo "$out" | sed -n 2p | tr -d ' '); gpu=$(echo "$out" | sed -n 3p | tr -d ' ')
    case "$last" in *" DONE") end DONE;; *" FAILED "*) end FAILED "$last";; esac
    if [ "$sz" = "$lastsz" ] && [ "${gpu:-0}" = 0 ]; then still=$((still+1)); else still=0; fi; lastsz=$sz
    [ $still -ge 6 ] && end STALL "no log growth for 30 min, GPU idle"
    echo "$(now) ok: $last | bytes $sz | gpu $gpu% | spent \$$(spent)" >> "$G/log.txt"
  fi
  sleep ${PG406:-300}
done
