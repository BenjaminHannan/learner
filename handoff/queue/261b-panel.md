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

GETTING YOUR FILES: the director works from GitHub. Run: git fetch -q origin claude/project-thread-p68q5v. Read each file named below with: git show origin/claude/project-thread-p68q5v:<path>. Never check out or merge that branch.

YOUR TASK: the blind panel writer for exp 261b (earpanel261b).
Read handoff/kit/briefs/earpanel261b-spec.txt (via git show as above) and follow it exactly. It is your whole task.
- Blind: besides that spec and OPUS-RULES.txt, read ONLY the schema and judgement-call sections of artifacts/claude-earpanel235-20260922/README.md. Never open any other file in artifacts/, scripts/, design/, data/ or the scratchpad.
- Write only inside artifacts/claude-earpanel261b-20260923/ (new folder). Write the items by hand inside make_panel.py; never generate items with a model.
- One process at a time. Check df -g / first; stop if under 3 GB free.
- When SEAL.sha256.txt is written, run from the repo root: shasum -a 256 -c artifacts/claude-earpanel261b-20260923/SEAL.sha256.txt and include its output.
- Final reply: category level only (family counts, R1-R15 quota counts, lower/typo/noq counts, number of clear:false items, SEAL lines and the -c output). Never quote an item.
PUSH: artifacts/claude-earpanel261b-20260923
