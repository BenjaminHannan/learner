#!/bin/bash
# opcpu vast guard (Opus manager, 2026-09-29; copy of handoff/kit/s3v/vguard.sh with the changes in DEVIATIONS.md). Started detached on the Mac by vstart.sh; runs
# from $G (its own copy, so no worktree or queue job needs to stay alive). Every 5 minutes: money and time check, then the rental's progress file.
# Ends on the first of the reasons below. It copies back what exists (small files only, never a .pt), checks every file against a sha256 manifest made on the
# rental (box/pack.sh), and, for DONE, that every job is accounted for (END with its return code, or SKIPPED). Only then does it destroy the instance by its
# exact id (confirmed gone). If the check fails twice, or ssh is lost, it STOPS the instance instead (compute billing ends, files stay on its disk) and
# writes <reason>-STOPPED-NOT-DESTROYED for the Director.
#   DONE        drive.sh finished (every job ended or was skipped)
#   FAILED      drive.sh stopped itself in its setup (torch pin, inputs, cores; its reason is kept)
#   BUDGET-STOP all rentals of this task reach $2.50
#   TIME-STOP   7 h since the first rental
#   STALL       no log on the rental grew for 30 min and the CPUs are idle (load average under 1): no GPU reading is used
#   HOST-FAIL   no ssh answer for 20 min (nothing can be copied: stopped, not destroyed)
# For BUDGET-STOP, TIME-STOP and STALL the rental's job processes are killed first (so the files stop changing), then the partial small files are copied back.
# The last line of $G/END is the reason. vcollect.sh (a queue job) moves the copied files into the repo.
set -u
G=$1
. "$G/vcommon.sh"
read -r ID H P TC < "$G/state"; TIME_CAP=${TC:-$TIME_CAP}
SS=$(sshto "$H" "$P")
T0=$(head -1 "$G/rentals.txt" | awk '{print $3}')
fin() { log "GUARD-END $1, spent \$$(spent)"; echo "END $1 spent $(spent)" > "$G/END"; exit 0; }
# kill only the kit's own processes on the rental (the bracket keeps pkill from matching this ssh command line)
haltbox() { $SS "pkill -f '[h]andoff/kit/opcpu/box/'; pkill -f '[/]venv/bin/python'; sleep 5; echo halted" < /dev/null 2>/dev/null | tail -1; }
end() { log "GUARD $1${2:+: $2}"
  mode=logs; [ "$1" = DONE ] && mode=runs
  case "$1" in BUDGET-STOP|TIME-STOP|STALL) log "halting the rental's jobs before the copy: $(haltbox)";; esac
  if [ "${3:-}" != nocopy ] && { copy_back $mode || copy_back $mode; }; then destroy "$ID" && fin "$1" || fin "$1-DESTROY-UNCONFIRMED"; fi
  stop_inst "$ID" && fin "$1-STOPPED-NOT-DESTROYED" || fin "$1-STOP-UNCONFIRMED"; }
[ -s "$G/END" ] && { echo "guard: already ended ($(cat "$G/END"))"; exit 0; }
log "GUARD start pid $$ instance $ID"
miss=0; still=0; lastsz=""
while :; do
  over "$(spent)" "$CAP_STOP" && end BUDGET-STOP "spent \$$(spent)"
  [ $(( $(date +%s) - T0 )) -ge "$TIME_CAP" ] && end TIME-STOP "time cap $TIME_CAP s since the first rental"
  # line 1: last progress line; line 2: bytes in every log/state file (growth = alive); line 3: 1-minute load average (CPU busy or idle)
  out=$($SS "tail -1 $BR/W/drive-state.txt; { cat $BR/W/*.out $BR/W/drive-state.txt; find $BR/premonition-* -type f \( -name '*.log' -o -name '*.jsonl' \) -exec cat {} + ; } 2>/dev/null | wc -c; cut -d' ' -f1 /proc/loadavg" < /dev/null 2>/dev/null)
  if [ -z "$out" ]; then
    miss=$((miss+1)); log "no ssh answer ($miss), status $(status_of "$ID")"
    [ $miss -ge 4 ] && end HOST-FAIL "no ssh answer for 20 min" nocopy
  else
    miss=0; last=$(echo "$out" | sed -n 1p); sz=$(echo "$out" | sed -n 2p | tr -d ' '); ld=$(echo "$out" | sed -n 3p | tr -d ' ')
    case "$last" in *" DONE") end DONE;; *" FAILED "*) end FAILED "$last";; esac
    idle=$(awk -v l="${ld:-0}" 'BEGIN{print (l+0 < 1) ? 1 : 0}')
    if [ "$sz" = "$lastsz" ] && [ "$idle" = 1 ]; then still=$((still+1)); else still=0; fi; lastsz=$sz
    [ $still -ge 6 ] && end STALL "no log growth for 30 min, CPUs idle (load $ld)"
    echo "$(now) ok: $last | bytes $sz | load $ld | spent \$$(spent)" >> "$G/log.txt"
  fi
  sleep 300
done
