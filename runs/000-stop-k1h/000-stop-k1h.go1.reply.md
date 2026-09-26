Stopping k1h-glm — reading the rules and locating its processes.
All 8 k1h PIDs exited on TERM — no `kill -9` needed. Verifying other jobs are untouched and counting output.
STOPPED — k1h-glm is fully stopped. Report filed at `artifacts/claude-stop-k1h-20260926/REPORT.md` (99 lines; watcher to push that path; I did no git ops).

**Step 1 — snapshot:** 24 lines matched the k1h/opencode-run filter (full PID/PPID/elapsed table in REPORT.md). k1h chain: watcher bash 20630 → agent 20664 → zsh 21178 → uv 21181 → python 21182 (cwd `/private/tmp/k1h-glm-iLDhRG`) → GLM children 31675, 33379, 34137, 34799 (PPID 21182). Other GLM children belonged to g406 (PPID 18119: 33507, 33853, 34760, 34928), lis320 (PPID 14197), and glm-helper-v11 (PPID 33525). Filter B matched 5 g406 PIDs (17032, 17081, 18114, 18118, 18119) plus my own agent (matched only because my task text names g406).

**Step 2 — kill:** TERM to exactly 8 PIDs (20664, 21178, 21181, 21182, 33379, 34137, 34799, and 35314, which appeared after the snapshot replacing the self-exited 31675). After 10 s: 8 of 8 dead, 0 survivors, no `kill -9` needed. Watcher 20630 was never signalled; it exited on its own afterward. g406 chain verified alive afterward (5 of 5). Nothing else touched; post-kill grep: 0 k1h processes remain.

**Step 3 — output so far:** k1h output dir `O/` empty: 0 files, 0 output .jsonl lines. Temp dir held 9 files total (1 staged input items.jsonl 70445 bytes, 1 partial chats-log.txt 499 bytes, 7 staged scripts). `artifacts/claude-k1h-20260926` does not exist in the worktree — nothing was copied back. `opencode session list -n 1000 | wc -l`: 11.

Pre-checks: load ~192, free disk 52 GB (over the 3 GB floor). Counts only throughout; no chats, answers, transcripts, or key material opened or quoted.
