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


YOUR TASK: builder for 280m, the talking line's JOIN of three already-built pieces on base 260. CPU only. No new behaviour.
Never use git log or older versions of any file. Never open any panel folder (artifacts/claude-*panel*) except joinpanel280m, and that only through your sealed runner.
Read: design/v3/30-modes/280m-talking-join.md (git show origin/main:...), and in this worktree scripts/claude_loop280b_agent.py, scripts/claude_loop281_agent.py, scripts/claude_loop282b_agent.py and the piece files they import (read-only), plus each piece's PASSMARKS.md (artifacts/claude-capab280b-20260923, claude-called281-20260923, claude-small282b-20260923).
Build: one new join agent scripts/claude_loop280m_agent.py (+ artifacts/claude-join280m-20260923/loop280m-config.json) that installs the pieces on 260 in the note's order, importing the piece files unchanged. Ledger P280m.n (append only). New files only.
Order: (1) write 60+ dev turns of your own (ability questions, called questions after teaches, small talk, mixed turns, controls) and show the three triggers never fire on the same turn; if any overlap exists, STOP before sealing and report it; (2) pilot the dev turns on all five arms (260, 280b, 281, 282b, 280m) and check agreement with the owner arm; pilot the frozen suites vs 260's rows and the verifier probes; (3) PASSMARKS with numbered predictions, the exact allowed suite and probe moves, and for every mixed-category shape which arm owns it; before sealing, run your panel runner and scorer end to end on a mock panel in exactly this schema: one row per turn {dialog_id, turn_index, user_text, category, gold} with categories ability / called / teach / smalltalk / mixed / control; the runner also accepts `user` for the text and stops with an error on any empty text; seal (SEAL.sha256.txt, listing every new file including .sh); ledger; (4) wait for artifacts/claude-joinpanel280m-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min), check it OK, run it ONCE on all five arms, and run smalltalkpanel234 once on 260 and 280m. After the seal never change a sealed file; if a sealed script breaks, stop and report.
Scoring: mechanical agreement and counts per category; list the reply files for the director's claim check.
Finish with RESULTS.md (result first, integer counts, categories only, never quote panel items) and your final reply.
PUSH: artifacts/claude-join280m-20260923 scripts/claude_loop280m_agent.py scripts/claude_join280m_* scripts/claude_280m_* artifacts/fable-predictions-ledger.md
