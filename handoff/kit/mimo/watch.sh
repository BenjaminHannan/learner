#!/bin/bash
# Emits one line per newly finished agent (.done) and per new killed/failed log line. Seen-list kept in a file.
Q=/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/mimo/queue
SEEN=$Q/.watch_seen; touch $SEEN
n0=$(wc -l < $Q/log.txt)
while true; do
  for f in $Q/*.done; do
    [ -e "$f" ] || continue
    b=$(basename "$f")
    if ! grep -qx "$b" $SEEN; then echo "$b" >> $SEEN; echo "NEW DONE: $b [$(cat "$f")]"; fi
  done
  n1=$(wc -l < $Q/log.txt)
  if [ "$n1" -gt "$n0" ]; then tail -n $((n1-n0)) $Q/log.txt | grep "killed\|failed\|stopped" | sed 's/^/LOG: /'; n0=$n1; fi
  sleep 20
done
