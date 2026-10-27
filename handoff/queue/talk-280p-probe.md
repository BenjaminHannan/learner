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


YOUR TASK: held-out probe for 280p (the sealed 280m join on base 260). CPU only. Report-only; no bar can be changed by it.
Never use git log. Never open any panel folder (artifacts/claude-*panel*). Read: the "280p result" section of design/v3/30-modes/280m-talking-join.md (git show origin/main:...), and in this worktree scripts/claude_join280p_score.py and scripts/claude_loop280m_agent.py (read-only).
Check artifacts/claude-join280m-20260923/SEAL.sha256.txt (12/12 OK) or stop. Then write 60 NEW dialogs of your own (fictional names; everyday chat: ability questions, teaches then called/named questions, greetings, thanks, goodbyes, mixed turns, plain questions, corrections) to artifacts/claude-probe280p-20260923/dialogs.json, and also use artifacts/claude-chatweak-20260923/dialogs.json (dev material). Run every dialog once on the five arms (260, 280b, 281, 282b, 280m) and score every turn with the sealed 280p scorer's mechanical owner rule.
Report: turns, agreement with owner, overlaps (ids), writes on non-teach turns, store differences vs 260, and owner counts. Write artifacts/claude-probe280p-20260923/RESULTS.md (result first, integer counts).
PUSH: artifacts/claude-probe280p-20260923 scripts/claude_probe280p_*
