Stopping the two stuck Mac jobs — checking duplicate gate and locating PIDs.
No duplicate found — now mapping the stuck processes.
Found the stuck processes — now tracing the full job trees to avoid collateral.
Process trees mapped — now stopping both jobs.
Both jobs stopped — now cleaning up their orphaned sessions.
Sessions deleted — writing the final report.
STOPPED both — DUPLICATE gate passed (no REPORT on origin/main or origin/builder-outbox).

004-rd378k-gate3low: STOPPED
005-rd378g-writelow: STOPPED

Killed 8 PIDs by exact PID, KILL-9 count 0. Launchers never killed (98706/98794 exited on their own after agents died). Watcher, other jobs, luna, BensPC untouched.

004:
- agent 98771 ELAPSED 03:21:21 TITLE mimo:004-rd378k-gate3low.go1.98706
- uv 113 ELAPSED 03:20:09
- python 115 ELAPSED 03:20:09 CWD /private/tmp/rd378k-gate3low-LW2DC3
- opencode 95522 ELAPSED 04:06 TITLE glm11-3bc60b4bb6814829a892e1bebbdf3eb5

005:
- agent 98853 ELAPSED 03:21:21 TITLE mimo:005-rd378g-writelow.go1.98794
- uv 125 ELAPSED 03:20:06
- python 127 ELAPSED 03:20:06 CWD /private/tmp/rd378g-writelow
- opencode 98170 ELAPSED 01:25 TITLE glm11-0c09051e7fdb488b826aefc8808a4ef9

Order: agents first, then uv+python, then opencode children. 10s wait, none alive, KILL-9 0.

Sessions:
- TAG glm11-3bc60b4bb6814829a892e1bebbdf3eb5 FOUND 1 LEFT 0
- TAG glm11-0c09051e7fdb488b826aefc8808a4ef9 FOUND 1 LEFT 0
- cwd gone count 0

Counts: jobs 2, STOPPED 2, NOT-RUNNING 0, PIDs killed 8, kill-9 0, tags 2, sessions found 2, sessions left 0, other-job kills 0, launcher kills 0.
REPORT written: artifacts/claude-stop-rd378low-20260927/REPORT.md (PUSH ready, DISK 0).
No GPU, no model call, no log/output/command lines read or printed, no config/auth read.
