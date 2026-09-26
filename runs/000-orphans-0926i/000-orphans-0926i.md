COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.

YOUR TASK: an orphan check (director, 2026-09-26 17:15 UTC). Rent nothing. Key only via $(cat ~/.config/vastai/vast_api_key), never printed.
1. `date -u`; `vastai show instances`: list every instance's id, label, status, dph and start time. For each label claude-<x>, say whether ~/premonition-watch/queue has a matching .running file for its job (ls ~/premonition-watch/queue/*.running), and for each running job whether its builder process is alive (`ps -axo pid,etime,command | grep <jobname>`; report PIDs only).
2. claude-sleep-358t: its builder exited (rc=2) at 13:10 Mac time. Wait until origin/builder-outbox has artifacts/claude-rsn358t-20260926/AUTOCAST-CHECK.md or no process for 000-check-358t is alive (poll every 2 min, up to 20 min). Then, if an instance labelled exactly claude-sleep-358t still exists, copy back any train_log.jsonl and *.log under its run dir into artifacts/claude-rsn358t-20260926/runs/orphan/ (no weights), `vastai destroy instance <id>`, and confirm it is gone. Record its id, hours, dph and cost.
3. Destroy nothing else. For any other claude-* instance with no alive builder, only report it.
Write artifacts/claude-orphans-20260926i/REPORT.md with 1-3. If you destroyed 358t, append a ledger line: `cat >> artifacts/fable-predictions-ledger.md`.
PUSH: artifacts/claude-orphans-20260926i/REPORT.md artifacts/claude-rsn358t-20260926/runs/orphan artifacts/fable-predictions-ledger.md
DISK: 0
