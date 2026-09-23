COMMON RULES (the director, Claude, wrote this task on 2026-09-22). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read handoff/kit/briefs/OPUS-RULES.txt (git show origin/main:handoff/kit/briefs/OPUS-RULES.txt). It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: the director works from GitHub. Run: git fetch -q origin main. Read each file named below that is not in your worktree with: git show origin/main:<path>. Never check out, merge or push main.
YOUR TASK: publish one missing file for exp 291 (reasoning line). No model changes, no runs. The 291 seal (artifacts/claude-join291-20260923/SEAL.sha256.txt) lists scripts/claude_fix291_glue.py, but that file was not in 291's PUSH list, so it never reached builder-outbox. Check that scripts/claude_fix291_glue.py exists in this worktree and that `shasum -a 256 -c` on its seal line passes from the repo root. Do not edit it. Report the check output in your final reply. If it is missing or its hash differs, say so and push nothing.
PUSH: scripts/claude_fix291_glue.py
