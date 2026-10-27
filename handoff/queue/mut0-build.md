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

EXP mut-0: the SLEEP mark must fail closed (director, 2026-09-24 01:55 UTC). CPU only. ONE change.
Problem (director checked): scripts/fable_marks123_all.py:696-716 suite_sleep() returns "pass": True in BOTH branches while always skipping; make_daemon sets sleep_threshold=100000 (line 102), so no suite ever sleeps. scripts/fable_sleepsmoke206.py was dropped from scripts/claude_292_runall.sh, claude_292t_runall.sh and claude_f1_runall.sh (both on origin/builder-outbox).
The change (additive, new files only): scripts/claude_marks_mut0.py wraps fable_marks123_all (import, read-only) so that suite_sleep returns pass=False, status "NOT-RUN", whenever it skips, and every run-all verdict that includes SLEEP shows NOT-RUN instead of PASS. Plus new scripts/claude_292t_runall_mut0.sh, claude_273_runall_mut0.sh, claude_f1_runall_mut0.sh = copies of the originals that call the mut0 runner AND run fable_sleepsmoke206.py (the 273 one uses the 273 agent, scripts/claude_loop273_agent.py on builder-outbox).
Seal before running: artifacts/claude-mut0-20260924/PASSMARKS.md + SEAL.sha256.txt. Marks:
 M1 unit: suite_sleep via mut0 on the 292t agent returns pass False, status NOT-RUN (and the original returns pass True: report both).
 M2 the three new run-all scripts each run sleepsmoke206 to completion; report its per-world seconds and verdict (PASS or FAIL are both reportable, the mark is that it RAN and was recorded honestly).
 M3 every non-SLEEP suite verdict identical to the last recorded 292t/273/F1 run-all results.
Also measure and report (not a mark): sleep wall seconds per sleep on 273 (the smoke's timing).
Final report: then a short PLAN for mut-1 (semantic mutants of 273: e.g. swap tick order back, drop inbox check, make sleep never due), each mutant listed with the suite that should catch it. Don't run mut-1.
PUSH: scripts/claude_marks_mut0.py scripts/claude_292t_runall_mut0.sh scripts/claude_273_runall_mut0.sh scripts/claude_f1_runall_mut0.sh artifacts/claude-mut0-20260924/PASSMARKS.md artifacts/claude-mut0-20260924/SEAL.sha256.txt artifacts/claude-mut0-20260924/RESULTS.md artifacts/claude-mut0-20260924/results.json
