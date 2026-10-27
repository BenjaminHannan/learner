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


YOUR TASK: builder for exp 255b, the one follow-up to 255 (fixed-reply text). CPU only.
Read first: design/v3/30-modes/255b-fixedtext-decision.md (from the branch above; it is the whole change, with exact texts), handoff/kit/briefs/255-fixedtext.txt (how 255 was built). In this worktree read artifacts/claude-fixedtext255-20260922/PASSMARKS.md and RESULTS.md, and scripts/claude_fix255_text.py, claude_fix255_test.py, claude_loop255_agent.py, claude_255_*.py, claude_255_runall.sh (read-only; import them, never edit).
Base: 138m (scripts/claude_loop138m_agent.py + artifacts/claude-merge138m-20260922/loop138m-config.json). 255b replaces 255's wrapper; it does not stack on 255.
New files only:
- scripts/claude_fix255b_text.py: rewrite255b(line) imports claude_fix255_text; T02 and zero counts per the decision note; every other line exactly as rewrite255.
- scripts/claude_fix255b_test.py: 255's checks on all 60 templates with 255b texts, plus the n = 0..12 sweep of every count template (no "zero", no "1 <plural>", no "one <plural>"), plus the anchor family check on the new T02 text.
- scripts/claude_loop255b_agent.py and its config; scripts/claude_255b_*.py and claude_255b_runall.sh copied from 255's with 255b paths.
- artifacts/claude-fixedtext255b-20260923/ (PASSMARKS.md, predicted moves, SEAL.sha256.txt, fixedtext.jsonl + SEAL2.sha256.txt, RESULTS.md). Ledger lines P255b.n appended to artifacts/fable-predictions-ledger.md.
Order: (1) unit tests at 0 failures; (2) full pilot of M2, M4, M5, M6, M7 vs 138m on scratch, and the extra report 255b vs 255 (differences only on T02 and zero-count lines); (3) PASSMARKS.md with the marks from the decision note, numbered predictions and every predicted move by id; seal (shasum -a 256 > SEAL.sha256.txt); (4) generate the M1 render file with seed 2550923, seal it into SEAL2; (5) run the registered M2, M4, M5, M6, M7; (6) run the 239 panel ONCE on 255b and write the changes file vs artifacts/claude-convpanel239-138m-20260922/transcripts-138m.jsonl (mechanical only: count changed turns, unexplained changes and store changes; never quote or read items). Do not grade M1 or M3 yourself; the director does.
Report: verdict for your marks, marks table with integer counts, the paths and sha256 of fixedtext.jsonl and the M3 changes file, every move, miss and deviation.
PUSH: artifacts/claude-fixedtext255b-20260923 scripts/claude_fix255b_text.py scripts/claude_fix255b_test.py scripts/claude_loop255b_agent.py scripts/claude_255b_* artifacts/fable-predictions-ledger.md
