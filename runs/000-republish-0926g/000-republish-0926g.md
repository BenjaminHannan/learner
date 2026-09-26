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



YOUR TASK: republish every job whose results were skipped by the old publish (director, 16:18 UTC 09-26). Rent nothing. Delete only *.pushed marker files as below. Never open result file contents (names and counts only).
1. Confirm the running watcher script has `git add -f -- "$p"` in publish().
2. In ~/premonition-watch/queue: for every <job>.pushed modified on 2026-09-26, read the PUSH: line(s) of <job>.md; for each PUSH path, check whether it exists on origin/builder-outbox (`git ls-tree -r origin/builder-outbox -- <path>` non-empty). If any PUSH path is missing there but exists in the watcher worktree, remove exactly <job>.pushed. rent-02dr is known to be one (expect 24 files under artifacts/claude-e2e02dr-20260926); rent-sf401 may already be handled by 000-republish-0926f.
3. Wait up to 8 min; report per job: files now on builder-outbox under its PUSH paths (count), and for rent-02dr compare sha256 of those files against its copy-back manifest (report match counts only).
Write artifacts/claude-republish-20260926g/REPORT.md.
PUSH: artifacts/claude-republish-20260926g/REPORT.md
DISK: 0
