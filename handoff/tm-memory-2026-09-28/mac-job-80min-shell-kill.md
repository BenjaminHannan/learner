---
name: mac-job-80min-shell-kill
description: Mac watcher job agents (opencode run) kill any single shell command after 80 min; run long steps in the background with short polls
metadata:
  type: project
  modified: 2026-09-27T03:05:38.741Z
---
Seen 2026-09-27: the watcher's diag err tail for madeup-g406-2-mac (builder-outbox status push at 03:02 UTC) read "shell tool terminated command after exceeding timeout 4800000 ms". The job agent (rungo4.sh -> `opencode run --auto`) kills any one command after 80 minutes. g406-2's GLM step ran from about 00:46 UTC and was killed at about 02:06 UTC. The agent then went silent.

The inferred mechanism: a GLM call via claude_glm_opencode_v11 can take about 15 minutes when opencode hangs (300 s timeout, 3 tries). Scripts that check their --max-minutes cap only between batches then overrun it.

**Why:** any job whose long step is one command (for example a "max 150 min" wording run) dies partway through and gives no RESULTS.

**How to apply:** in Mac job files, start long steps with `nohup ... & echo $! > X.pid`. Poll them with separate commands of under 10 minutes each. Stop them by exact PID (`pgrep -P` for the python child under uv) before 80 minutes. The pattern is in handoff/queue/madeup-mu407-prep-mac.md (a002c6930). A job file is copied to the Mac queue only when it launches, so an unlaunched job can still be edited on main. The watcher status lives on the builder-outbox branch in status/watcher.txt, in local EDT times. See [[mac-disk-watcher-hold]] and [[made-up-facts-line]].
