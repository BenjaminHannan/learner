COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
GPU: no (vast CLI only).

YOUR TASK: vast instance check (director, 2026-09-26 20:00 UTC). Key only via $(cat ~/.config/vastai/vast_api_key), never printed.
1. `vastai show instances --raw`: every instance's id, label, actual_status, dph_total, start_date; `date -u`.
2. If instance 52807320 (label claude-sleep-358t3, created by the director's 358t3 task, which has ended) still exists: `vastai destroy instance 52807320`, then show instances again and confirm it is gone. Destroy NOTHING else: not 52799251 (dl7b, running its job), not 52755827 (depot, stopped on purpose), not any instance whose label does not start with claude-sleep-358t3.
3. `vastai show user --raw`: the credit number only.
Write artifacts/claude-instances-20260926l/REPORT.md with those numbers only.
PUSH: artifacts/claude-instances-20260926l/REPORT.md
DISK: 0
