#!/bin/bash
# rungo2: cheap-Go-only runner. Chain = glm-5.3-flash -> qwen3.8-flash only (budget rule: <=2 agents, cheapest models).
# A killed opencode (exit >128) or a $n.stop file ends the loop WITHOUT fallback and WITHOUT a done marker.
t="$1"; m1="${2:-opencode-go/glm-5.3-flash}"; Q=$(dirname "$t"); n=$(basename "$t" .md); W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
cd "$W"; k=$(ls "$Q"/$n*.reply.md 2>/dev/null | wc -l); k=$((k+1))
PRE=""; if [ "$k" -gt 1 ]; then PRE="RESUME NOTICE: a previous agent started this exact task and was cut off. Its files may already exist (scripts with the prefix, artifact folder, PASSMARKS.md/SEAL, ledger predictions, partial downloads). Inspect what exists, keep anything sealed (never edit PASSMARKS.md if SEAL.sha256.txt exists; verify with shasum -a 256 -c from the repo root), continue from the first unfinished step, do not duplicate ledger predictions. The task follows.

"; fi
for m in "$m1" opencode-go/glm-5.3-flash opencode-go/qwen3.8-flash; do
  [ -e "$Q/$n.stop" ] && { echo "$(date +%T) stopped $n" >> "$Q/log.txt"; exit 2; }
  echo "$(date +%T) go$k $n $m" >> "$Q/log.txt"
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" "$PRE$(cat "$t")" < /dev/null > "$Q/$n.go$k.reply.md" 2> "$Q/$n.go$k.err.txt"
  rc=$?
  if [ "$rc" -gt 128 ] || [ -e "$Q/$n.stop" ]; then echo "$(date +%T) killed-go$k $n $m rc=$rc" >> "$Q/log.txt"; exit 2; fi
  if ! grep -q "Rate limit exceeded\|usage limit\|Insufficient balance" "$Q/$n.go$k.err.txt" && [ "$(wc -c < "$Q/$n.go$k.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.go$k.done"; echo "$(date +%T) done-go$k $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) failed-go$k $n $m rc=$rc" >> "$Q/log.txt"; k=$((k+1))
done
exit 1
