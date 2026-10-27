#!/bin/bash
# one task, muse first, mimo fallback on empty reply
t="$1"; Q=$(dirname "$t"); n=$(basename "$t" .md); W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
cd "$W"
for m in opencode/muse-spark-1.3-contributor-free opencode/mimo-v2.6-flash-free; do
  echo "$(date +%T) start $n $m" >> "$Q/log.txt"
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" "$(cat "$t")" < /dev/null > "$Q/$n.reply.md" 2> "$Q/$n.err.txt"
  if [ "$(wc -c < "$Q/$n.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.done"; echo "$(date +%T) done $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) empty $n $m" >> "$Q/log.txt"
done
echo FAILED > "$Q/$n.done"
