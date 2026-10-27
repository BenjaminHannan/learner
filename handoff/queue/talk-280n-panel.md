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


GETTING YOUR FILES: run git fetch -q origin main and read each named file with git show origin/main:<path>. Never check out or merge that branch.


YOUR TASK: blind panel writer for 280n (re-test of the talking-line join). You write test items only; you never read or run any code.
Read ONLY the "Panel spec (joinpanel280m ...)" section (joinpanel280n uses the same spec) of design/v3/30-modes/280m-talking-join.md (git show origin/main:...). Never use git log. Do not open scripts/ or any other artifacts folder or panel.
Write artifacts/claude-joinpanel280n-20260923/: panel.jsonl (one line per turn, exactly these keys: dialog_id, turn_index, user_text, category, gold; categories ability, called, teach, smalltalk, mixed, control; gold = "ability_list" for ability items, "smalltalk" for small talk, the exact expected value for called and control questions, the stored triple Subject|relation|Object for teach turns, or "abstain"), SPEC-COPY.md, README.md (counts per category).
Write turns the way real people type in a chat window. Fictional names only, freshly invented.
Then seal: from the worktree root, shasum -a 256 artifacts/claude-joinpanel280n-20260923/panel.jsonl artifacts/claude-joinpanel280n-20260923/SPEC-COPY.md > artifacts/claude-joinpanel280n-20260923/SEAL.sha256.txt. Never change the files after sealing.
Report: counts per category and the seal file's contents. Never quote items in your reply.
PUSH: artifacts/claude-joinpanel280n-20260923
