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



YOUR TASK: a read-only disk + credit check (director, 2026-09-26 01:50 UTC). Delete nothing, rent nothing, change no file outside your PUSH path.
1. `df -h /` and `df -h ~`.
2. Sizes (du -sh, largest first) of: ~/premonition-watch and each child (queue, outbox, runs, any clone), ~/premonition-models/* , ~/.local/share/opencode (and any opencode*.db file), ~/.cache/*, ~/Library/Caches/* (top 10), ~/Desktop/projects/beautiful-model/.claude/worktrees/* , /private/tmp/claude-502 (top 10), ~/.Trash. Also `find ~ -xdev -size +500M -mmin -300 2>/dev/null | head -40` with sizes (files that appeared in the last 5 hours).
3. Confirm ~/premonition-models/lis301-merged/model.safetensors exists; print its sha256 (expected b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890).
4. vast credit: `vastai show user --raw` and report ONLY the balance/credit number (key only via $(cat ~/.config/vastai/vast_api_key), never printed). Also `vastai show instances` (ids, labels, dph).
5. Name the 3 folders most likely to have grown in the last 5 hours and what writes to them (look at mtimes).
Write artifacts/claude-diskcheck-20260926/REPORT.md with all numbers (sizes in GB, one decimal).
PUSH: artifacts/claude-diskcheck-20260926/REPORT.md
