#!/bin/bash
# ocdb helpers: delete opencode sessions by title or staleness; return freed pages to disk.
DB=$HOME/.local/share/opencode/opencode.db; W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
OC=/usr/local/bin/opencode
del_title() {  # $1 = exact session title; only sessions in this worktree
  for id in $(sqlite3 -cmd ".timeout 20000" "$DB" "SELECT id FROM session WHERE directory='$W' AND title='$1';"); do $OC session delete "$id" > /dev/null 2>&1; done
}
prune_stale() {  # delete worktree sessions last updated before the oldest running `opencode run` started (or all, if none run)
  local cut; cut=$(ps -axo lstart=,command= | grep "[o]pencode run" | while read -r d m day t y rest; do date -j -f "%a %b %d %T %Y" "$d $m $day $t $y" +%s; done | sort -n | head -1)
  [ -z "$cut" ] && cut=$(date +%s)
  local n=0
  for id in $(sqlite3 -cmd ".timeout 20000" "$DB" "SELECT id FROM session WHERE directory='$W' AND time_updated < ${cut}000 - 120000;"); do $OC session delete "$id" > /dev/null 2>&1 && n=$((n+1)); done
  echo $n
}
reclaim() { sqlite3 -cmd ".timeout 20000" "$DB" "PRAGMA incremental_vacuum; PRAGMA wal_checkpoint(TRUNCATE);" > /dev/null 2>&1; }
