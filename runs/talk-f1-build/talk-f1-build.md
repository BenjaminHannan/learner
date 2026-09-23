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


YOUR TASK: builder for F1 (talking line): 241b's sealed reply rewriter as the outermost reply layer on 292t. CPU only.
Never use git log or older versions of any file. Never open any panel folder (artifacts/claude-*panel*) or artifacts/claude-convbench-f0-20260923 except through your sealed runner.
Read: the sections "F0 baseline" and "F1" of design/v3/30-modes/talk-fluency-plan.md (git show origin/main:...), and in this worktree scripts/claude_loop292t_agent.py, scripts/claude_loop241b_agent.py, scripts/claude_mouth241b_*.py, artifacts/claude-mouth241b-20260922/PASSMARKS.md, scripts/claude_convf0_run.py and scripts/claude_convf0_score.py (read-only; import them).
Build: scripts/claude_loopf1_agent.py (+ artifacts/claude-f1-20260923/loopf1-config.json) = 292t plus 241b's rewriter layer exactly as 241b installs it. New files only. Ledger PF1.n (append only).
Order: (1) write 60+ dev turns of your own (fictional names, everyday wording) and pilot 292t vs F1: every changed line, the brake verdict, 0 store changes; (2) pilot the frozen suites vs 292t's rows (fable_suitediff218 --only rt136,rt143,sessions152,bench) and the verifier probes; (3) PASSMARKS with numbered predictions; seal SEAL.sha256.txt listing every new file including .sh; ledger; (4) registered runs, once each: suites and probes, joinpanel292t (regression only, via 292t's sealed runner, both arms), and convbench-f0 via claude_convf0_run.py on both arms. Write artifacts/claude-f1-20260923/run/changed-lines.jsonl with every changed reply line (arm A = 292t text, arm B = F1 text, dialog/turn id). Do NOT grade grammar or run the judge; the director queues blind graders. (5) M5 wall: 3 alternated suite runs per arm, load1 < 40 before each run, waiting up to 6 hours; if never quiet, report VOID.
Finish with artifacts/claude-f1-20260923/RESULTS.md (result first, integer counts, never quote panel or benchmark user turns; quoting agent replies is fine).
PUSH: artifacts/claude-f1-20260923 scripts/claude_loopf1_agent.py scripts/claude_f1_* artifacts/fable-predictions-ledger.md
