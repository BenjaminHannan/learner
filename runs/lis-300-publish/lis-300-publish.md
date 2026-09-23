COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the listener spec: design/v3/60-listener/frame-spec.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
INDEPENDENCE: never open or read items of any TEST-ONLY panel. New files only. Never check out branches in the worktree; get a copy of the code for the GPU machine with `git archive origin/main` and `git archive origin/builder-outbox <path>`.

YOUR TASK: publish-only, for lis-300. CPU, under 10 minutes, and no new runs. lis-300-train finished at 08:53 ET, but its PUSH line used shell braces, so its result files were never pushed. In the worktree, check that these exist in artifacts/claude-lis300-20260923/ (the lis-300 builder wrote them there): RESULTS.md, THRESHOLD.txt, SEAL-run.sha256.txt, dev_sweep.txt, panel_score.json, panel_score_T0.json, train_summary.json, train_log.jsonl.
- If any of them is missing from the worktree, copy it from wherever the lis-300 builder left it: its work dir, or BensPC's work dir via ssh benspc. Do not re-run anything.
- Also copy the dev-set files from the lis-300 work dir into artifacts/claude-lis300-20260923/dev/: the built data/dev.jsonl, dev_rows.jsonl and dev_pred.jsonl. These are dev data, not a panel. Do NOT copy the panel predictions or anything with panel turns in it.
- Run `shasum -a 256 -c artifacts/claude-lis300-20260923/SEAL-run.sha256.txt` from wherever its paths resolve, and report the result.
- Report the file list with byte sizes. No new files beyond the dev/ copies.
PUSH: artifacts/claude-lis300-20260923 artifacts/fable-predictions-ledger.md
