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


GETTING YOUR FILES: run git fetch -q origin claude/project-thread-p68q5v and read each named file with git show origin/claude/project-thread-p68q5v:<path>. Never check out or merge that branch.


YOUR TASK: re-measure exp 241b's M5 suite wall ONCE, per design/v3/30-modes/241b-director-rulings.md item 3. CPU only. Change nothing else.
Use the sealed checker exactly as 241b's PASSMARKS D6 protocol says (scripts/claude_mouth241b_check.py --wall241b and the same suite set), 228 vs 241b, 3 alternated runs each.
Before EACH run: run uptime; if load1 >= 40, wait (check every 2 minutes). If the total wait passes 90 minutes, stop and report "load gate not met" with the loads you saw. Do not lower the gate.
First verify: shasum -a 256 -c artifacts/claude-mouth241b-20260922/SEAL.sha256.txt from the worktree root (all OK, or stop).
Write artifacts/claude-mouth241b-20260922/wall-remeasure/ (the raw run outputs and wall.json with every run's seconds and load1). Never edit any existing file.
Report: the 6 walls with load1 before each, both medians, the % difference and whether it is within +5%.
PUSH: artifacts/claude-mouth241b-20260922/wall-remeasure
