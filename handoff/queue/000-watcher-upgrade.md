WATCHER UPGRADE (director, 2026-09-23). Small housekeeping task on Ben's Mac. Change nothing else.
1. cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 && git fetch -q origin main
2. git show origin/main:handoff/kit/mimo/watcher.sh > ~/premonition-watch/watcher.sh.new && bash -n ~/premonition-watch/watcher.sh.new (stop and report if this fails).
3. touch ~/premonition-watch/STOP, then wait (sleep in a loop, max 5 min) until ~/premonition-watch/watch.log's last line contains "watcher stopped" printed after you touched STOP.
4. rm -f ~/premonition-watch/STOP && mv ~/premonition-watch/watcher.sh.new ~/premonition-watch/watcher.sh
5. Start it detached: (nohup caffeinate -i bash ~/premonition-watch/watcher.sh > /dev/null 2>&1 &) ; sleep 10; tail -3 ~/premonition-watch/watch.log
6. Confirm exactly one watcher loop runs: pgrep -fl "premonition-watch/watcher.sh" (running task subshells also match; report the list).
Never kill any process. Final reply: the outputs of steps 2, 5 and 6, then WATCHER-UPGRADED.
