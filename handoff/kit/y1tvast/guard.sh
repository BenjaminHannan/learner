#!/bin/bash
# y1t vast guard, run detached on the Mac (Answering-from-memory thread, 2026-09-27; ADDENDUM-9 change 13, asked for by the
# Thread manager at 14:39 UTC). Started by pass.sh (ensure_guard) once this task's instance answers ssh, from its own copy
# of the kit in $G, so it outlives the pass and the queue job. Between passes nothing else can stop the rental, so every
# GPOLL seconds it reads this task's vast state (pass.sh info) and acts on the first of:
#   money   dollars so far plus 15 minutes of the instance reach the $1.50 cap
#   time    the time cap scaled to the card has passed (create + 20 min + 2 x the offer's estimated chain minutes + 15 min)
#   done    the rental shows W/chain.done (looked at over ssh every GDONE seconds) and no pass is running
# To act it runs pass.sh in guard mode, which works like a last pass at its deadline: it asks the chain to stop, copies
# back and checks every file against the rental's sha256 manifest, then destroys the instance, else stops it (FLAG-DIRECTOR),
# and writes RESULTS-vast.md in the watcher's worktree. It never launches, rents, or touches another instance, and it skips
# a round while a pass holds the lock (that pass enforces the same caps itself). It ends when RESULTS-vast.md exists, the
# instance is gone or stopped, or after 12 hours.
# Usage: guard.sh <guard dir G> <the watcher's worktree> <pinned commit>
set -u
G=$1; W=$2; PIN=$3
KD=$G/kit
P=$KD/handoff/kit/y1tvast/pass.sh
R=artifacts/claude-y1t-20260926/run
CAP=${CAPY1T:-1.50}
T0=$(date +%s)
now() { date -u +%FT%TZ; }
log() { echo "$(now) guard: $*" >> "$G/guard.log"; }
fin() { log "END: $*"; rm -f "$G/guard.pid"; exit 0; }
cd "$W" 2>/dev/null || { echo "$(now) guard: no worktree $W" >> "$G/guard.log"; exit 0; }
log "start pid $$, worktree $W, kit $PIN"
lastdone=0
while :; do
  [ -s "$R/RESULTS-vast.md" ] && fin "RESULTS-vast.md exists"
  [ $(( $(date +%s) - T0 )) -lt 43200 ] || fin "12 hours since the guard started (ACTION NEEDED if an instance of this task is still listed)"
  set -- $(bash "$P" "$KD" "$PIN" y1t-vast-guard info 2>/dev/null | tail -1)
  s=${1:-}; id=${2:-none}; dph=${3:-0}; tc=${4:-0}; host=${5:--}; port=${6:--}; live=${7:-live}
  case "$s" in [0-9]*.[0-9]*) ;; *) log "no usable answer from pass.sh info ('$*')"; sleep "${GPOLLY1T:-120}"; continue ;; esac
  [ "$id" = none ] && fin "no instance of this task is running"
  [ "$live" = stopped ] && fin "instance $id is stopped"
  why=""
  awk -v s="$s" -v p="$dph" -v c="$CAP" 'BEGIN{exit !(s+p/4 >= c)}' && why="money: \$$s spent, cap \$$CAP"
  [ -z "$why" ] && [ "$(date +%s)" -ge "$tc" ] && why="time: the time cap $(date -u -r "$tc" +%FT%TZ 2>/dev/null || date -u -d "@$tc" +%FT%TZ) has passed"
  if [ -z "$why" ] && [ "$host" != - ] && [ $(( $(date +%s) - lastdone )) -ge "${GDONEY1T:-600}" ]; then
    lastdone=$(date +%s)
    d=$(perl -e 'alarm shift; exec @ARGV' 60 ${SSHBINY1T:-ssh} -i "${KEYY1T:-$HOME/.ssh/id_ed25519}" -o ConnectTimeout=15 -o BatchMode=yes \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -p "$port" "root@$host" \
        'test -e ~/tree/W/chain.done && echo DONE' < /dev/null 2>/dev/null)
    [ "$d" = DONE ] && why="done: the chain is done and no pass has copied it back"
  fi
  if [ -n "$why" ]; then
    if [ -d "$R/.pass-lock" ] && [ -z "$(find "$R/.pass-lock" -maxdepth 0 -mmin +80 2>/dev/null)" ]; then
      log "$why; a pass holds the lock, so it acts instead; next look in ${GPOLLY1T:-120} s"
    else
      log "$why: running pass.sh in guard mode"
      GUARDWHY="$why" bash "$P" "$KD" "$PIN" y1t-vast-guard guard >> "$G/guard.log" 2>&1
      log "pass.sh guard mode ended (rc $?)"
    fi
  fi
  sleep "${GPOLLY1T:-120}"
done
