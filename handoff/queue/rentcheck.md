COMMON RULES (the director, Claude, wrote this task on 2026-09-22). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.


YOUR TASK: a read-only rental check (director, 2026-09-23). Change nothing, rent nothing, create nothing on vast.ai.
1. Is the vastai CLI installed? (`command -v vastai`, `vastai --version`). If not, say so and stop step 2.
2. Run `vastai show instances` and `vastai show user --raw`, and from the second report ONLY the credit/balance number (never print the key, email or any config file; never cat ~/.config/vastai/).
3. Read handoff/memory/compute-availability.md, handoff/memory/gpu-budget-cap.md, handoff/memory/rental-create-blocked-by-classifier.md and grep the ledger (artifacts/fable-predictions-ledger.md) for "vast" or "rent" to find how earlier rentals were done (offer search, create command, image, ssh) and what they cost in total.
Final reply: CLI installed yes/no + version; number of running instances (ids and hourly cost if any); balance; the exact recipe used last time (commands with the key shown only as $(cat ~/.config/vastai/vast_api_key)); total spent so far per the ledger/memory. Integer counts, dollars to the cent.
