COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the listener spec: design/v3/60-listener/frame-spec.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open or read items of any TEST-ONLY panel. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main` and `git archive origin/builder-outbox <path>`.

TIME CAP: the whole task must finish within 45 minutes of starting. macOS has no `timeout` command, so wrap every long command yourself (for example, run it in the background and kill its exact PID after N seconds). If any single real-model load or read takes more than 5 minutes, stop it by exact PID and report the step and the exact error or hang.

YOUR TASK: lis-311b, a time-capped re-run of lis-311 (handoff/queue/lis-311-chat292.md). The first run launched at 13:56 UTC, and the Mac went to sleep during it.
FIRST, check whether lis-311 already finished:
- does `curl -s -m 5 http://127.0.0.1:8767/` answer?
- does origin/builder-outbox have artifacts/claude-lis311-20260923/RESULTS.md?
If both are true, do nothing else and report that. If a lis-311 process is still running (`ps aux | grep -i lis311`), report its PID and state; stop it by exact PID only if it has made no progress in 10 minutes. Then do the lis-311 task exactly as written in handoff/queue/lis-311-chat292.md, under the time cap above, writing into the same folder artifacts/claude-lis311-20260923/. If PASSMARKS.md already exists there, keep it and never overwrite it. Also write RESULTS.md there.
PUSH: artifacts/claude-lis311-20260923 scripts/claude_lis311_agent.py scripts/claude_lis311_try.py scripts/claude_lis311_server.py scripts/claude_lis311_start.sh artifacts/fable-predictions-ledger.md
