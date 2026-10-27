COMMON RULES: READ-ONLY. Stop, delete, move, or edit nothing. Never print secrets. NEVER WebFetch. Finish within 10 minutes.
YOUR TASK (Director, 2026-09-27 02:13 UTC): find out why three jobs are running long: 170-rv390-358i2-pc, 000-benspc-disklist, 000-peek-k1h-glm2b.
On the Mac:
1. `ps -axo pid,etime,command | grep -E "rungo4|claude|opencode|ssh benspc" | grep -v grep | cut -c1-200`
2. For each of the three jobs, print the last 25 lines of every file in the watcher queue dir (~/beautiful-model-watch or wherever $Q is; find it with `ls -d ~/*/handoff-watch* ~/*watch* 2>/dev/null` or from ps) matching <job>.go*.err.txt and <job>*.txt.
3. `timeout 20 ssh -o ConnectTimeout=10 -o BatchMode=yes benspc "type C:\Users\benja\GPU-BUSY.txt; Get-PSDrive C | Select Free; Get-Process python*,git,tar -ErrorAction SilentlyContinue | Select Id,StartTime,CPU,Path | Format-Table -Auto; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv"` and report the exit code. If it times out, say so.
Write every output verbatim to handoff/replies/000-probe-benspc-hang.md.
PUSH: handoff/replies/000-probe-benspc-hang.md
