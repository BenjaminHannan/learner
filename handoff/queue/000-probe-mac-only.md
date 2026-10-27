COMMON RULES: READ-ONLY. Stop, delete, move, or edit nothing. NEVER use ssh in this task. Never print secrets. NEVER WebFetch. Finish within 5 minutes.
YOUR TASK (Director, 2026-09-27 02:35 UTC): Mac-side look at four long-running jobs that all use ssh benspc: 170-rv390-358i2-pc, 000-benspc-disklist, 000-peek-k1h-glm2b, 000-probe-benspc-hang.
1. `ps -axo pid,ppid,etime,stat,command | grep -E "ssh|rungo4|scp|claude -p|opencode" | grep -v grep | cut -c1-220`
2. Find the watcher queue dir from the rungo4 command lines, then for each of the four jobs print the last 20 lines of each <job>.go*.err.txt and <job>.go*.out* file there, plus `ls -la` of those files (mtimes).
3. `nc -z -G 5 $(ssh -G benspc | awk '/^hostname /{print $2}') 22; echo rc=$?` (this reads ssh config only, no ssh session).
Write all output verbatim to handoff/replies/000-probe-mac-only.md.
PUSH: handoff/replies/000-probe-mac-only.md
