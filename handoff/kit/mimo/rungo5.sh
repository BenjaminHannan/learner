#!/bin/bash
# rungo5 = rungo4 with a builder chain that avoids the opencode-go plan (weekly Go usage limit hit ~00:57 UTC 09-27; Ben 03:04:18 "use muse spark 1.3").
# Chain: $2 (watcher BM, default free Zen Muse), then free mimo-v2.6-flash (mimo-skill.md:13). Deployed by watcher.sh into $H each round (Director 03:17 UTC 09-27).
# NOT a Luna/Codex builder: on 2026-09-27 03:53 UTC the Director's permission check refused running `codex exec` (GPT-6 Luna) as a queue builder ("create unsafe agents"), even least-privilege (workspace-write + network). No session should retry that route; Luna is used only as a read-only text helper (scripts/claude_luna_codex.py). Ben or his Mac Claude may set it up themselves.
# rungo4 (= rungo3 + network-drop resume). 11:07-11:18 on 2026-09-22 six agents died on "unknown certificate verification error" /
# "Cannot connect to API" and rungo3 wrote .done for them (reply > 300 bytes). Now: if the last lines of err.txt show a network
# error, the run is NOT done; wait 120 s and resume on the SAME model (up to 6 network retries), with the RESUME NOTICE.
# A killed opencode (exit >128) or a $n.stop file ends the loop WITHOUT fallback and WITHOUT a done marker.
t="$1"; m1="${2:-opencode/muse-spark-1.3-contributor-free}"; Q=$(dirname "$t"); n=$(basename "$t" .md); W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
. "$W/handoff/kit/mimo/ocdb.sh"
cd "$W"
NET="unknown certificate verification error\|Cannot connect to API\|socket connection was closed\|ECONNRESET\|ETIMEDOUT\|fetch failed\|getaddrinfo\|network error\|Failed query\|database is locked\|Failed to execute statement"
# DB lock errors (11:41: a long vacuum held the lock) are retried on the SAME model too, never by falling down the chain.
nr=0
set -- "$m1" opencode/mimo-v2.6-flash-free
while [ $# -gt 0 ]; do
  m="$1"
  k=$(ls "$Q"/$n.go*.reply.md 2>/dev/null | wc -l); k=$((k+1))
  PRE=""; if [ "$k" -gt 1 ]; then PRE="RESUME NOTICE: a previous agent started this exact task and was cut off (usually a network drop, not a task problem). Its files may already exist (scripts with the prefix, artifact folder, PASSMARKS.md/SEAL, ledger predictions, partial outputs). Inspect what exists, keep anything sealed (never edit PASSMARKS.md, the agent code, config or case files if SEAL.sha256.txt exists; verify with shasum -a 256 -c from the repo root), continue from the first unfinished step, do not duplicate ledger predictions. Your 90-minute deadline starts now. The task follows.

"; fi
  [ -e "$Q/$n.stop" ] && { echo "$(date +%T) stopped $n" >> "$Q/log.txt"; exit 2; }
  w=0; while [ -e "$Q/PAUSE" ] || [ "$(df -k / | tail -1 | awk '{print int($4/1024)}')" -lt 2500 ]; do [ $w -eq 0 ] && echo "$(date +%T) waiting-disk $n" >> "$Q/log.txt"; w=$((w+1)); [ $w -gt 60 ] && { echo "$(date +%T) nospace $n" >> "$Q/log.txt"; exit 3; }; sleep 60; done
  v=0; while pgrep -f "wal_checkpoint.TRUNCATE" > /dev/null && [ $v -lt 40 ]; do v=$((v+1)); sleep 15; done
  echo "$(date +%T) go$k $n $m" >> "$Q/log.txt"
  TT="mimo:$n.go$k.$$"
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" --title "$TT" "$PRE$(cat "$t")" < /dev/null > "$Q/$n.go$k.reply.md" 2> "$Q/$n.go$k.err.txt"
  rc=$?
  del_title "$TT"
  if [ "$rc" -gt 128 ] || [ -e "$Q/$n.stop" ]; then echo "$(date +%T) killed-go$k $n $m rc=$rc" >> "$Q/log.txt"; exit 2; fi
  if tail -5 "$Q/$n.go$k.err.txt" | sed 's/\x1b\[[0-9;]*m//g' | grep -q "$NET"; then
    if [ $nr -lt 6 ]; then nr=$((nr+1)); echo "$(date +%T) neterr-failed-go$k $n $m (resume $nr/6 in 120 s)" >> "$Q/log.txt"; sleep 120; continue; fi
    echo "$(date +%T) neterr-giveup-failed-go$k $n $m" >> "$Q/log.txt"; exit 4
  fi
  if ! grep -q "Rate limit exceeded\|usage limit\|Insufficient balance\|Failed to execute statement" "$Q/$n.go$k.err.txt" && [ "$(wc -c < "$Q/$n.go$k.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.go$k.done"; echo "$(date +%T) done-go$k $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) failed-go$k $n $m rc=$rc" >> "$Q/log.txt"; shift
done
exit 1
