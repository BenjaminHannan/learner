COMMON RULES (the director, Claude, wrote this task on 2026-09-26). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.

YOUR TASK: find and publish Ben's Mac agent's brd-8w files (director, 2026-09-26 17:30 UTC). Copy only: no rerun, no edits, rent nothing, delete nothing, $0.
1. Search the Mac for folders named claude-brd8w-20260926: `find ~/Desktop/projects ~/premonition-watch /private/tmp -type d -name 'claude-brd8w-20260926' 2>/dev/null` (skip ~/Desktop/projects/polymarket). List each path with its file count and newest mtime.
2. If none exists, say so in the report and stop.
3. Otherwise take the one with the most files (ties: newest mtime) and copy it as is (skip files over 5 MB and any weights: *.pt *.safetensors *.bin) to artifacts/claude-brd8w-20260926/ in this worktree. Do not open or quote file contents; list names and sizes only.
Write artifacts/claude-find-brd8w-20260926/REPORT.md with 1-3.
PUSH: artifacts/claude-find-brd8w-20260926/REPORT.md artifacts/claude-brd8w-20260926
DISK: 0
