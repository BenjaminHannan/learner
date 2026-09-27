Stopping the stuck Mac job — checking guardrails then killing by exact PID.
Found the stuck job's processes — now isolating the exact PIDs to stop.
No active GLM subprocesses — the agent is the only remainder. I'll stop it now.
Agent stopped cleanly and launcher exited — now finalizing the report.
STOPPED

counts (integers):
- launchers found for target: 1 (PID 10084, 04:26:24, rungo4.sh, never killed)
- agents killed: 1 (PID 10114, role agent, title mimo:lis320-fulloc-c1-mac.go1.10084, elapsed 04:26:58 at kill)
- step 1b python/shell/uv with claude_lis320_glm_oclow.py + --seeds: 0
- step 1c opencode children of python / tags: 0
- kill -9 needed: 0
- session-delete tags run: 0, found 0, left 0
- step 4 pgrep rungo lis320-fulloc-c1-mac.md: EMPTY (exit 1)
- step 5 temp rm: 0 (no cwd found, left alone)
- stop file created: 1 (~/premonition-watch/queue/lis320-fulloc-c1-mac.stop)
- misses/deviations: 0

moves: date 05:14:42 UTC, touch stop file, ps find, kill 10114, 10s wait confirmed gone, no kill -9, no tag deletes, step 4 EMPTY, step 5 no-op, date 05:16:19 UTC, wrote artifacts/claude-stop-lis320c1-20260927/REPORT.md for PUSH.

What it means: the stuck Mac job is stopped; its launcher exited on its own; nothing else was killed.
What it doesn't mean: no GPU/model work was done; no sessions were deleted (none existed); no other jobs were touched.
