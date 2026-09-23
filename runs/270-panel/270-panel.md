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


GETTING YOUR FILES: git fetch -q origin main, then read each named file with git show origin/main:<path>.

YOUR TASK: builder for exp 264, the question-answering checker. Read design/v3/30-modes/264-qa-checker.md (the one change, exact prompts and save rule) and handoff/kit/briefs/261-earcheck.txt (BensPC, llama-server, ear, arms). In this worktree read artifacts/claude-earcheck261b-20260923/PASSMARKS.md + RESULTS.md and scripts/claude_earcheck261_*.py + scripts/claude_earcheck261b_*.py (read-only; import, never edit). New files only: scripts/claude_earcheck264_*.py, artifacts/claude-earcheck264-20260923/, ledger lines P264.n.

YOUR TASK: blind TEST-ONLY panel writer for exp 270 (casual typing). Read ONLY handoff/kit/briefs/earpanel264-spec.txt for the format (id, family, turn, gold, clear, notes). Do not read any code. Output artifacts/claude-typepanel270-20260923/panel.jsonl + make_panel.py + SEAL.sha256.txt. 100 turns, fictional names only, ids t270-NNN:
- casual 40: facts typed casually: all lowercase, missing possessive apostrophes ("anas cat is fig"), no final punctuation, some with both. Gold = the fact with correctly capitalised names.
- casual_q 15: lowercase questions about facts ("where does ana live") ; gold ASK.
- lower_trap 15: lowercase turns where a capitalised-looking word is NOT a name ("my boss is nice", "the rose is red", "i like may") ; gold = only the real fact or nothing.
- clean 30: normal well-typed facts and questions (control; must be unchanged).
PUSH: artifacts/claude-typepanel270-20260923
