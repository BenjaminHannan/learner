WATCHER DEDUPE (director, 2026-09-23). Small housekeeping task on Ben's Mac. Several old watcher loops are still running. Keep only the newest.
1. Run: ps -axo pid,ppid,lstart,command | grep "[p]remonition-watch/watcher.sh"
2. A watcher LOOP is a "bash .../watcher.sh" process whose parent (ppid) is a "caffeinate" process. Task subshells also show as "bash .../watcher.sh", but their parent is another bash watcher process. NEVER kill a subshell, since that would orphan a running builder.
3. Keep the loop with the NEWEST start time. For every other loop, run kill <exact pid> (plain SIGTERM, one pid at a time). Kill nothing else: no caffeinate, no opencode, no python.
4. Wait 5 s and run step 1 again. Report the before and after lists, and which pids you killed.
Final reply: the before list, the pids killed, the after list, then DEDUPE-DONE.
