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


YOUR TASK: independent English grader A, part 5 of 6, for F1's M1 (talking line). You grade; you build nothing and run no experiment. CPU only, GPU: no.
Read ONLY these two inputs (git show origin/main:<path>): handoff/kit/briefs/241b-stylesheet.txt (the grading rules; check its sha256 is 16bdf0cf0403bce26886ea345f1ea44242e54537380f0ab3b8c7ed40f2dad8ef and stop if not) and artifacts/claude-gradef1-20260923/sweep.jsonl rows 1797 to 2245 by line number (1-based). Each row is {"id", "reply"}. Do not open any other file in that folder, no other grader's output, no file under artifacts/claude-f1-20260923, and no scripts. Never run a scorer.
For each row, judge the reply text alone against the style sheet: is it fully grammatical, natural, correct English with no machine text? Names and values may be odd or misspelled; that alone is never an error. Read every row yourself; do not use regex shortcuts or a script to decide.
Write artifacts/claude-gradef1-A-20260923/part5.jsonl, one line per row, in file order: {"id": <row id>, "grammatical": true|false, "reason": "ok" or the exact problem}. Exactly one line per row in your range (449 rows). Check your line count and that every id appears once.
Report: rows graded, number false, and the id and reason of every false row.
PUSH: artifacts/claude-gradef1-A-20260923/part5.jsonl
