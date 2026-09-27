#!/bin/bash
# rsn-358u vast guard (sleep research thread, 2026-09-27). Started detached on the Mac by vstart.sh; runs from $G (its own copy,
# so no worktree or queue job needs to stay alive). Every 5 minutes: money and time check, then the rental's progress file.
# Ends, always by copying back what exists and destroying the instance by its exact id (confirmed gone), on the first of:
#   DONE        drive.sh finished (all trains, seals, poison checks and evals)
#   FAILED      drive.sh stopped itself (its reason is kept)
#   BUDGET-STOP all rentals of this task reach $3.60 (cap $4)
#   TIME-STOP   4 h 30 min since the first rental
#   STALL       no log on the rental grew for 30 min and the GPU is idle
#   HOST-FAIL   no ssh answer for 20 min (nothing can be copied; destroyed anyway)
# The last line of $G/END is the reason. vcollect.sh (a queue job) moves the copied files into the repo.
set -u
G=$1
. "$G/vcommon.sh"
read -r ID H P < "$G/state"
SS=$(sshto "$H" "$P")
T0=$(head -1 "$G/rentals.txt" | awk '{print $3}')
end() { log "GUARD $1${2:+: $2}"; [ "${3:-}" = nocopy ] || copy_back; destroy "$ID"
        log "GUARD-END $1, spent \$$(spent)"; echo "END $1 spent $(spent)" > "$G/END"; exit 0; }
log "GUARD start pid $$ instance $ID"
miss=0; still=0; lastsz=""
while :; do
  over "$(spent)" "$CAP_STOP" && end BUDGET-STOP "spent \$$(spent)"
  [ $(( $(date +%s) - T0 )) -ge "$TIME_CAP" ] && end TIME-STOP "4 h 30 min since the first rental"
  out=$($SS 'tail -1 /root/r/W/drive-state.txt; cat /root/r/W/*.log /root/r/W/*/train_log.jsonl /root/r/W/drive-state.txt 2>/dev/null | wc -c; nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1' < /dev/null 2>/dev/null)
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
  sleep 300
done
