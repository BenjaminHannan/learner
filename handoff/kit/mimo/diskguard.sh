#!/bin/bash
# Every 5 min: prune finished agent sessions, give freed pages back to disk, and pause launches when disk is low.
# Prints a line only when it did something notable (for a Monitor). PAUSE file: rungo2 waits while it exists.
S=/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad
Q=$S/mimo/queue; . $S/mimo/ocdb.sh
while true; do
  before=$(stat -f %z "$DB"); n=$(prune_stale); reclaim; after=$(stat -f %z "$DB")
  free=$(df -k / | tail -1 | awk '{print int($4/1024)}')
  [ "$n" -gt 0 ] && echo "$(date +%T) diskguard: pruned $n sessions, db $((before/1000000)) -> $((after/1000000)) MB, free ${free} MB" | tee -a $Q/log.txt
  if [ "$free" -lt 3000 ]; then [ -e $Q/PAUSE ] || { touch $Q/PAUSE; echo "$(date +%T) diskguard: PAUSE launches, free ${free} MB" | tee -a $Q/log.txt; }
  elif [ -e $Q/PAUSE ] && [ "$free" -gt 5000 ]; then rm -f $Q/PAUSE; echo "$(date +%T) diskguard: resume launches, free ${free} MB" | tee -a $Q/log.txt; fi
  sleep 300
done
