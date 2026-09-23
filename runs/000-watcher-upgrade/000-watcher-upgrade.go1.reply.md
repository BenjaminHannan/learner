Watcher upgrade started — fetching and staging the new version.
Old watcher stopped cleanly — installing the upgrade and restarting.
New watcher is up, but I see extra matches — verifying which loops are active.
Confirmed the extra processes are active builder tasks — doing a final check of the upgraded watcher.
Step 2 output (`git show ... > watcher.sh.new && bash -n`):
```
SYNTAX_OK
      59 /Users/ben-hannan/premonition-watch/watcher.sh.new
--- /Users/ben-hannan/premonition-watch/watcher.sh	2026-09-22 21:52:46
+++ /Users/ben-hannan/premonition-watch/watcher.sh.new	2026-09-22 22:46:15
@@ -13,12 +13,13 @@
 export OPENCODE_CONFIG_CONTENT='{"snapshot": false}'
 W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
 H=$HOME/premonition-watch; Q=$H/queue; O=$H/outbox
-IN=claude/project-thread-p68q5v; OUT=builder-outbox; MAX=${MAX:-3}
+IN=main; OUT=builder-outbox; MAX=${MAX:-3}
 RUN="$W/handoff/kit/mimo/rungo4.sh"
 mkdir -p "$Q"; LOG=$H/watch.log
 log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
 if [ ! -d "$O/.git" ]; then   # small separate repo that holds only builder results (no copy of the project)
   mkdir -p "$O" && git -C "$O" init -q && git -C "$O" remote add origin "$(git -C "$W" remote get-url origin)"
+  git -C "$O" config user.name "$(git -C "$W" config user.name || echo Ben)"; git -C "$O" config user.email "$(git -C "$W" config user.email || echo ben@localhost)"
   git -C "$O" checkout -q -b "$OUT"
   if git -C "$O" fetch -q origin "$OUT" 2>/dev/null; then git -C "$O" reset -q --hard FETCH_HEAD; fi
 fi
@@ -36,6 +37,10 @@
 log "watcher started (pid $$)"
 while [ ! -e "$H/STOP" ]; do
   git -C "$W" fetch -q origin "$IN" 2>>"$LOG"
+  # self-update: when the watcher on $IN changes, restart into the new version (running tasks keep going)
+  if git -C "$W" show "origin/$IN:handoff/kit/mimo/watcher.sh" > "$H/watcher.new" 2>/dev/null && [ -s "$H/watcher.new" ] && ! cmp -s "$H/watcher.new" "$0"; then
+    bash -n "$H/watcher.new" && { mv "$H/watcher.new" "$0"; log "self-update, restarting"; exec bash "$0"; }
+  fi
```

Step 3: touched `~/premonition-watch/STOP` at 22:46:17, waited loop, `watch.log` last line became `2026-09-22 22:48:05 watcher stopped` (detected at 22:48:07).

Step 5 output (`(nohup caffeinate -i bash ~/premonition-watch/watcher.sh ...); sleep 10; tail -3 watch.log`):
```
2026-09-22 22:46:05 launch talk-241b-restart
2026-09-22 22:48:05 watcher stopped
2026-09-22 22:48:10 watcher started (pid 8626)
```

Step 6 output (`pgrep -fl "premonition-watch/watcher.sh"`):
```
1305 bash /Users/ben-hannan/premonition-watch/watcher.sh
8283 bash /Users/ben-hannan/premonition-watch/watcher.sh
8626 bash /Users/ben-hannan/premonition-watch/watcher.sh
8628 caffeinate -i bash /Users/ben-hannan/premonition-watch/watcher.sh
```
Note: NOT exactly one loop. `ps` shows also 8255 `bash .../watcher.sh` (parent of this 000-watcher-upgrade task, PID 8257/8289) which `pgrep -fl` consistently omits. Pre-existing watchers 1305 (parent of 263-build task) and 8283 (parent of talk-241b-restart task) are still running; only one `watcher stopped` line was logged before STOP was removed. Killed nothing, per instructions.

WATCHER-UPGRADED
