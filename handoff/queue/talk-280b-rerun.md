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


YOUR TASK: exp 280b panel RE-RUN after a VOID (column-name mismatch). CPU only. Nothing new is built.
Read: the section "280b re-run ruling" of design/v3/30-modes/280-282-chat-fixes.md (git show origin/main:...), and in this worktree artifacts/claude-capab280b-20260923/PASSMARKS.md and RESULTS.md. Never use git log. Never read the panel item by item and never quote it.
Steps: (1) from the worktree root, check artifacts/claude-capab280b-20260923/SEAL.sha256.txt (must be 15/15 OK) and artifacts/claude-capabilpanel280b-20260923/SEAL.sha256.txt (2/2 OK); stop and report on any failure. (2) Write the one new file scripts/claude_capab280b_paneladapt.py exactly as the ruling says: rename the key `user` to `user_text`, nothing else; it asserts row count 50, every other key and value equal, text equal, and writes artifacts/claude-capab280b-20260923/rerun/panel-adapted.jsonl plus rerun/ADAPT.txt (both sha256 values and the assert results). (3) Run the sealed panel steps (scripts/claude_280b_panel.sh, unchanged; if it takes a panel path argument or variable, point it at the adapted file; if it hard-codes the path, run its exact commands with only the panel path swapped and list them) ONCE per arm, 280 and 280b, writing into artifacts/claude-capab280b-20260923/rerun/. If a sealed step breaks for any other reason, stop and report; do not fix it.
(4) Report the sealed mechanical counts per category, 280 beside 280b, every changed reply by id only, the reply file paths for the director's claim check, and RESULTS-RERUN.md (result first, integer counts, categories only).
PUSH: artifacts/claude-capab280b-20260923 scripts/claude_capab280b_paneladapt.py scripts/claude_280b_runall.sh scripts/claude_280b_panel.sh
