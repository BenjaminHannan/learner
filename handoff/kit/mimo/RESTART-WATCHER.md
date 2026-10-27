# Restart the Mac watcher (for a Claude session on Ben's Mac)

The watcher stopped publishing status/watcher.txt on builder-outbox at 2026-09-23 14:01 UTC (Mac slept). Diagnose and restart it. Never print secrets. Stop processes by exact PID only; never touch pythonw or anything not listed here.

1. `pgrep -fl "premonition-watch/watcher.sh"`, `tail -20 ~/premonition-watch/watch.log`, `ls ~/premonition-watch/queue 2>/dev/null; ls ~/premonition-watch`. Report what is running and the log's last lines.
2. If a watcher loop exists but the log has not advanced for >5 min, find which child it is blocked on (`pstree` or `ps -o pid,ppid,etime,command -g <pgid>`). If it is lis-311-chat292 (a model load on MPS), or a hung git/ssh process, kill only that child by exact PID, then wait 3 min and check that the log advances.
3. If no watcher loop exists, or it still doesn't advance: `touch ~/premonition-watch/STOP`, wait until the log says "watcher stopped" (max 5 min; if it never does, kill the loop's exact PID), then `rm -f ~/premonition-watch/STOP` and start exactly one: `(nohup caffeinate -dis bash ~/premonition-watch/watcher.sh > /dev/null 2>&1 &)`.
4. Confirm there is exactly one loop, and that a new status push appears within 3 min: `git -C <worktree> fetch origin builder-outbox && git show origin/builder-outbox:status/watcher.txt | head -3`.
Final line: WATCHER-OK or WATCHER-STUCK plus the reason.
