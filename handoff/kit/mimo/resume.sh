#!/bin/bash
# resume a task whose first agent died (rate limit): same task text + RESUME preamble, MiMo first then Muse
t="$1"; Q=$(dirname "$t"); n=$(basename "$t" .md); W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
cd "$W"; k=$(ls "$Q"/$n.resume*.reply.md 2>/dev/null | wc -l); k=$((k+1))
PRE="RESUME NOTICE: a previous agent started this exact task and was cut off by a provider rate limit. Its files may already exist in the repo (scripts with the prefix, artifact folder, PASSMARKS.md/SEAL, ledger predictions, partial downloads in the HF cache or data dir). First inspect what exists, keep anything sealed (never re-seal or edit PASSMARKS.md if SEAL.sha256.txt exists — verify the seal with shasum -a 256 -c from the repo root), and continue from the first unfinished step. Do not duplicate ledger predictions (append an 'outcomes' block only). The task follows."
for m in opencode/mimo-v2.6-flash-free opencode/muse-spark-1.3-contributor-free; do
  echo "$(date +%T) resume$k $n $m" >> "$Q/log.txt"
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" "$PRE

$(cat "$t")" < /dev/null > "$Q/$n.resume$k.reply.md" 2> "$Q/$n.resume$k.err.txt"
  if ! grep -q "Rate limit exceeded" "$Q/$n.resume$k.err.txt" && [ "$(wc -c < "$Q/$n.resume$k.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.resume$k.done"; echo "$(date +%T) done-resume$k $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) ratelimited-resume$k $n $m" >> "$Q/log.txt"
done
