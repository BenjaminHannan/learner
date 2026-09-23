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


YOUR TASK: builder for 292t, which puts the talking line's three layers (280b, 281, 282b, joined and verified as 280p) on the main base 292. CPU only. No new behaviour.
Never use git log or older versions of any file. Never open any panel folder except joinpanel292t, and that only through your sealed runner.
Read: the "292t" section of design/v3/30-modes/280m-talking-join.md (git show origin/main:...), and in this worktree scripts/claude_loop292_agent.py (build_agent292, DEFAULT_CONFIG292), scripts/claude_loop280m_agent.py, scripts/claude_join280p_score.py and the piece files they import (read-only).
Build: scripts/claude_loop292t_agent.py (+ artifacts/claude-join292t-20260923/loop292t-config.json) that installs 280m's layers on 292 in 280m's order, plus the three single-layer arms on 292, importing all piece files unchanged. Ledger P292t.n (append only). New files only.
Order: (1) write 60+ dev turns of your own (ability, teach then called, small talk, mixed, controls, and 292's own strengths: two-step questions, yes/no questions, corrections) and show that 0 turns have two layers firing on 292; if any do, STOP before sealing and report; (2) pilot the dev turns on all five arms with the 280p scorer's mechanical rule (base = 292); pilot the frozen suites (fable_suitediff218 --only rt136,rt143,sessions152,bench vs 292's rows) and the verifier probes, and list every move by id with its owning layer; (3) PASSMARKS with numbered predictions; mock-panel end-to-end test in exactly the schema {dialog_id, turn_index, user_text, category, gold} with categories ability / called / teach / smalltalk / mixed / control (accept `user` too; stop on empty text); seal SEAL.sha256.txt listing every new file including .sh; ledger; (4) wait for artifacts/claude-joinpanel292t-20260923/SEAL.sha256.txt (poll 2 min, up to 120 min), check it OK, run it ONCE on all five arms; run the suites and probes as a REGISTERED run after the seal; run smalltalkpanel234 once on 292 and 292t. After the seal never change a sealed file; if a sealed script breaks, stop and report.
Finish with RESULTS.md (result first, integer counts, categories only, never quote panel items), listing reply files for the director's claim check.
PUSH: artifacts/claude-join292t-20260923 scripts/claude_loop292t_agent.py scripts/claude_join292t_* scripts/claude_292t_* artifacts/fable-predictions-ledger.md
