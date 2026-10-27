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


YOUR TASK: independent English grader B for exp 255b's M1. You grade; you build nothing and run nothing.
Read ONLY artifacts/claude-fixedtext255b-20260923/fixedtext.jsonl (228 rows of assistant replies with made-up names). First check from the worktree root: shasum -a 256 -c artifacts/claude-fixedtext255b-20260923/SEAL2.sha256.txt (must say OK). Do not open PASSMARKS, RESULTS, scripts, any other grader's file, or any other folder.
For each row, judge the reply text alone: is it fully grammatical, natural English with no machine text (codes, placeholders like USER, bare digits for small counts, "zero" counts, broken punctuation)? Read every row yourself; do not use a script or regex to decide.
Write artifacts/claude-grade255b-B-20260923/m1-grades.jsonl: {"id", "grammatical": true|false, "reason": "ok" or the exact problem}, one line per row, 228 lines, every id once.
Report: rows graded, number false, and the id and reason of every false row.
PUSH: artifacts/claude-grade255b-B-20260923/m1-grades.jsonl
