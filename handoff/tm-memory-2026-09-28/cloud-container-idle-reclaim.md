---
name: cloud-container-idle-reclaim
description: Detached (nohup/setsid) jobs in a thread's cloud container die when the container is reclaimed while the session is idle; keep a tracked watcher
metadata:
  type: feedback
---
A thread's cloud container is reclaimed when the session goes idle, and every process in it dies, including nohup/setsid jobs. Files on disk and the HF cache survive the restart. Seen 2026-09-26: the mu-405 CPU run died at 19:02 UTC, about 4 minutes after the thread ended its turn (uptime 0 min at 19:17).
**Why:** long free CPU runs in the container look safe but silently stop, which costs hours and forces an addendum.
**How to apply:** for any container job longer than a few minutes, also start a harness-tracked Bash watcher (run_in_background) that waits for the job's exit file, check it with hourly self-wakes, and write the job's own exit/progress files so a cut is visible. If it dies again, move the job to BensPC via the queue. See [[made-up-facts-line]].
Also: never commit (then git pull --rebase) a log a running job is still writing; the rebase replaces the file and the job's later lines go to the orphaned copy (mu-405b logU lost its last lines 23:20 UTC 09-26).
