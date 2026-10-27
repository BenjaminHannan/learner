#!/bin/bash
# task on a named Go model; fallback chain if it errors/rate-limits; resume preamble if any prior reply exists
t="$1"; m1="$2"; Q=$(dirname "$t"); n=$(basename "$t" .md); W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
cd "$W"; k=$(ls "$Q"/$n*.reply.md 2>/dev/null | wc -l); k=$((k+1))
PRE=""; if [ "$k" -gt 1 ]; then PRE="RESUME NOTICE: a previous agent started this exact task and was cut off. Its files may already exist (scripts with the prefix, artifact folder, PASSMARKS.md/SEAL, ledger predictions, partial downloads). Inspect what exists, keep anything sealed (never edit PASSMARKS.md if SEAL.sha256.txt exists; verify with shasum -a 256 -c from the repo root), continue from the first unfinished step, do not duplicate ledger predictions. The task follows.

"; fi
for m in "$m1" opencode-go/glm-5.3-flash opencode-go/kimi-k3 opencode-go/qwen3.8-flash opencode-go/minimax-m3; do
  echo "$(date +%T) go$k $n $m" >> "$Q/log.txt"
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" "$PRE$(cat "$t")" < /dev/null > "$Q/$n.go$k.reply.md" 2> "$Q/$n.go$k.err.txt"
  if ! grep -q "Rate limit exceeded\|usage limit\|Insufficient balance" "$Q/$n.go$k.err.txt" && [ "$(wc -c < "$Q/$n.go$k.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.go$k.done"; echo "$(date +%T) done-go$k $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) failed-go$k $n $m" >> "$Q/log.txt"; k=$((k+1))
done
