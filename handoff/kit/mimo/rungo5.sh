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
# BASH-ONLY: yes = no LLM builder: run the first ```bash fenced block of the task file in $W (cap 75 min), reply = stdout (Director 09-27, free builders rate-limited/hanging)
if grep -q '^BASH-ONLY: yes' "$t"; then
  awk '/^```bash/{f=1;next} f&&/^```/{exit} f' "$t" > "$Q/$n.bo.sh"
  echo "$(date +%T) bash-only $n" >> "$Q/log.txt"
  perl -e 'alarm shift; exec @ARGV' 4500 bash "$Q/$n.bo.sh" < /dev/null > "$Q/$n.go1.reply.md" 2> "$Q/$n.go1.err.txt"; rc=$?
  echo "rc=$rc" >> "$Q/$n.go1.reply.md"; [ $rc = 0 ] && echo bash-only > "$Q/$n.go1.done"
  echo "$(date +%T) bash-only-exit $n rc=$rc" >> "$Q/log.txt"; exit $rc
fi
NET="unknown certificate verification error\|Cannot connect to API\|socket connection was closed\|ECONNRESET\|ETIMEDOUT\|fetch failed\|getaddrinfo\|network error\|Failed query\|database is locked\|Failed to execute statement"
# DB lock errors (11:41: a long vacuum held the lock) are retried on the SAME model too, never by falling down the chain.
nr=0; rr=0
WAITNOTE="RUNNER NOTE (Director, 09-27): your builder model is rate-limited, so every tool call counts. To wait for a long background run, use ONE blocking command (e.g. while pgrep -f <exact script> >/dev/null; do sleep 60; done, capped under 75 min), never many short polls. Before starting any long run, check with pgrep that the same run is not already going (a previous agent may have started it).

"
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
  /usr/local/bin/opencode run --model "$m" --auto --dir "$W" --title "$TT" "$PRE$WAITNOTE$(cat "$t")" < /dev/null > "$Q/$n.go$k.reply.md" 2> "$Q/$n.go$k.err.txt" &
  op=$!; st=0; el=0
  # stall watchdog (09-27 08:xx UTC: free Zen builders sat at the bare "> build" line for 30+ min): if after 15 min the reply is empty and err is <= 60 bytes, stop THIS runner's own opencode child and retry later like a rate limit
  while kill -0 $op 2>/dev/null; do sleep 30; el=$((el+30))
    [ -e "$Q/$n.stop" ] && { kill $op 2>/dev/null; break; }
    if [ $el -ge 900 ] && [ ! -s "$Q/$n.go$k.reply.md" ] && [ "$(wc -c < "$Q/$n.go$k.err.txt")" -le 60 ]; then st=1; kill $op 2>/dev/null; break; fi
  done
  wait $op; rc=$?
  if [ $st = 1 ]; then del_title "$TT"
    if [ $rr -lt 6 ]; then rr=$((rr+1)); echo "$(date +%T) stalled-go$k $n $m (no output in 15 min; resume $rr/6 in 600 s)" >> "$Q/log.txt"; sleep 600; continue; fi
    echo "$(date +%T) stalled-giveup-go$k $n $m" >> "$Q/log.txt"; exit 5
  fi
  del_title "$TT"
  if [ "$rc" -gt 128 ] || [ -e "$Q/$n.stop" ]; then echo "$(date +%T) killed-go$k $n $m rc=$rc" >> "$Q/log.txt"; exit 2; fi
  if tail -5 "$Q/$n.go$k.err.txt" | sed 's/\x1b\[[0-9;]*m//g' | grep -q "$NET"; then
    if [ $nr -lt 6 ]; then nr=$((nr+1)); echo "$(date +%T) neterr-failed-go$k $n $m (resume $nr/6 in 120 s)" >> "$Q/log.txt"; sleep 120; continue; fi
    echo "$(date +%T) neterr-giveup-failed-go$k $n $m" >> "$Q/log.txt"; exit 4
  fi
  # free-model rate limit mid-task (006/008 agents died ~07:25 UTC 09-27 while their nohup'd Luna runs kept going): wait 10 min, resume on the SAME model with the RESUME NOTICE (it finds the running process), up to 6 times
  if tail -5 "$Q/$n.go$k.err.txt" | sed 's/\x1b\[[0-9;]*m//g' | grep -q "Rate limit exceeded"; then
    if [ $rr -lt 6 ]; then rr=$((rr+1)); echo "$(date +%T) ratelimit-failed-go$k $n $m (resume $rr/6 in 600 s)" >> "$Q/log.txt"; sleep 600; continue; fi
  fi
  # only the last 40 err lines count: agents print queue files whose WHY lines say "usage limit" (y1t-luna-pilot false fail, 07:16 UTC 09-27)
  if ! tail -n 40 "$Q/$n.go$k.err.txt" | grep -q "Rate limit exceeded\|usage limit\|Insufficient balance\|Failed to execute statement" && [ "$(wc -c < "$Q/$n.go$k.reply.md")" -gt 300 ]; then echo "$m" > "$Q/$n.go$k.done"; echo "$(date +%T) done-go$k $n $m" >> "$Q/log.txt"; exit 0; fi
  echo "$(date +%T) failed-go$k $n $m rc=$rc" >> "$Q/log.txt"; shift
done
exit 1
