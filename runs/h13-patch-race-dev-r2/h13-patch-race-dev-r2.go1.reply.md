Rate-limited run — queuing the 15-hour patch race in one shot.
Found the marks on origin/main — setting up the run directory.
No run in progress — preparing a clean checkout for the long queue.
Full clone stalled — retrying shallow.
Environment ready (torch 2.14.0 in venv) — launching the dev queue now with one blocking wait.
Launch failed on two setup bugs (shasum ran from wrong dir, `&&` skipped the start) — fixing both and relaunching.
Queue is live. One quick status check, then handing off.
Dev queue launched and healthy. Status for next thread:

- **Run dir:** `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/patch-eq-add2-run` (shallow clone of `origin/main`, venv `.venv` with torch 2.14.0 + numpy; `python3` resolves via PATH export at launch, inherited by jobs — do not disturb).
- **Sources:** 4/4 sha256 OK (from `claude/h13-patch-takeover-x4ph8v` via ssh fetch; launcher re-verified).
- **Queue:** PID 14160, `JOBS=4 bash scripts/claude_patch_eq_dev_queue_add2.sh`, phase 1 (patch-s0/s1, wsoff-s0/s1 first wave) progressing, rung checkpoints writing to `eq-runs/`, NO-TRACEBACK. Expect ~15h total.
- **Resume/wait (one blocking command, <75 min):** from run dir, `QP=$(cat artifacts/claude-patch-eq-20260928/logs/queue.pid); for i in $(seq 1 68); do kill -0 $QP 2>/dev/null || break; sleep 60; done` — if PID dead and queue incomplete, rerun the same `JOBS=4` queue command (ladders resume; finished jobs skip). Do not edit the script. Watch for Traceback / "unfinished".
- **Not this job:** holdout, RESULTS.md, blind recount.
