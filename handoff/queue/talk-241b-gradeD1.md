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


YOUR TASK: careful English grader D, part 1 of 3. You grade; you build nothing and run nothing.
Read ONLY handoff/kit/briefs/241b-stylesheet.txt (sha256 must be 16bdf0cf0403bce26886ea345f1ea44242e54537380f0ab3b8c7ed40f2dad8ef) and lines 1 to 415 (1-based) of artifacts/claude-grade241b-set2-20260923/rows.jsonl (read it with git show origin/main:artifacts/claude-grade241b-set2-20260923/rows.jsonl; sha256 f4327edbc3cc891861e5df40684dc25cd38d110d468e5bc283784081f0be43d5). Open nothing else: no other grader's files, no scripts, no artifacts of exp 241 or 241b.
The rows are assistant replies with made-up names. Some rows contain real mistakes. Your job is to find them. For each row decide: is this reply fully correct, natural English under the style sheet? Mark it false for ANY error: agreement, a missing or wrong article, a lowercase proper name, a doubled word, a code like "(E1234)", a digit for a count under ten, a missing apostrophe, a wrong verb form, a raw database label that is not English (for example "language of work or name"), a repeated list item, or anything a careful editor would fix. Names are invented and may look strange; strange names are not errors.
Read each row yourself, one by one. Do not use a script, regex or search to decide, and do not mark rows in bulk.
Write artifacts/claude-grade241b-D-set2-20260923/part1.jsonl: {"id", "grammatical": true|false, "reason": "ok" or the exact error}, one line per row in your range, in order. Check the line count and that every id appears once.
Report: rows graded, number false, and every false id with its reason.
PUSH: artifacts/claude-grade241b-D-set2-20260923/part1.jsonl
