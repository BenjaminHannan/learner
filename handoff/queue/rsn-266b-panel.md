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
YOUR TASK: blind panel writer for exp 266b (reasoning line). Read handoff/kit/briefs/chainpanel266b-spec.txt (from origin/main) and follow it exactly; it is your whole task. The base 266 files are on origin/builder-outbox (scripts/claude_fix266_chainlift.py, scripts/claude_loop266_agent.py, artifacts/claude-chain266-20260923/): copy only those files, unchanged, from origin/builder-outbox to run the base; do not read their code beyond what running needs. CPU only. One process at a time; df -g / first, and stop if under 3 GB free. Final reply: category level only, never quote an item.
PUSH: artifacts/claude-chainpanel266b-20260923
