Housekeeping the watcher loops — listing the running processes to identify the loops.
I've mapped the process tree — the older loop and its active task are still sorting out. I'll verify what's safe to terminate.
The old loop is gone — doing a final verification that the surviving builder wasn't affected.
BEFORE (ps -axo pid,ppid,lstart,command | grep "[p]remonition-watch/watcher.sh"):
- 8626, ppid 1, Tue Sep 22 22:48:10 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh (newest loop — kept)
- 8628, ppid 8626, Tue Sep 22 22:48:10 2026, caffeinate -i bash /Users/ben-hannan/premonition-watch/watcher.sh (caffeinate — never a kill target)
- 8945, ppid 8626, Tue Sep 22 22:50:16 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh (subshell, parent is bash 8626, child rungo4 talk-255b-build — not killed)
- 31909, ppid 8626, Tue Sep 22 23:15:53 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh (subshell, parent is bash 8626, child rungo4 000-watcher-dedupe = this task — not killed)
- 1305, ppid 1, Tue Sep 22 22:21:17 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh (older top-level loop — kill target)

Note: no bash watcher had a caffeinate parent; the two top-level loops (ppid 1) were 1305 and 8626, and the two subshells (parent = bash 8626) were 8945 and 31909. Classification by parent type per rule 2.

KILLED: 1305 (plain `kill 1305`, SIGTERM, single pid). Nothing else killed — no caffeinate, no subshell, no opencode, no python.

AFTER (same command, 5 s later):
- 8626, ppid 1, Tue Sep 22 22:48:10 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh
- 8628, ppid 8626, Tue Sep 22 22:48:10 2026, caffeinate -i bash /Users/ben-hannan/premonition-watch/watcher.sh
- 8945, ppid 8626, Tue Sep 22 22:50:16 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh
- 31909, ppid 8626, Tue Sep 22 23:15:53 2026, bash /Users/ben-hannan/premonition-watch/watcher.sh
1305 is gone. Only the newest loop (8626) remains. Its former task child 1307 (rungo4 263-build) plus opencode 1343 survived, reparented to ppid 1 and still running.

DEDUPE-DONE
