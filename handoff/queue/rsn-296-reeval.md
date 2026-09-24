COMMON RULES (the director, Claude, wrote this task on 2026-09-23). You are a build/verification agent working in the git worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 (run every command from there).
First read /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt. It applies to you in full, even though you are not Opus. The key points:
- Additive only: create new files; never edit or delete an existing file. Never edit anything in archive/, premonition/, learnlab/, artifacts/opus-*, or another agent's sealed files. The ledger is append-only (cat >>).
- Fictional names only. Never write to the repo-root notebook/. No secrets. Never print config files that may hold keys.
- Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ... (plain python3 under bash may be a broken x86 binary). macOS has no `timeout` command.
- TEST-ONLY panels are never read item by item, never tuned on, and never quoted; you may run them only where your task says so, once.
- Check `uptime` and `df -g /` before heavy steps. Stop and report if free disk is under 3 GB. Use at most 4 parallel processes.
- Claims never exceed the numbers. Report every case, every miss and every deviation. Integer counts.
- You cannot message the director mid-run. When the task says "report", put it in your final reply, which the director reads.
Your final reply: verdict first, then a marks table with integer counts, every move, every miss, deviations, and what it means / doesn't mean in plain high-school English.

GETTING YOUR FILES: run git fetch -q origin main and read files with git show origin/main:<path> (the plan: design/v3/50-own-model/01-own-ear-mouth-plan.md). Builder outputs are on origin/builder-outbox (git show origin/builder-outbox:<path>). Never check out, merge or push any branch yourself; the watcher pushes your PUSH paths.
GPU: no

YOUR TASK: rsn-296-reeval. The rsn-296 run's panel JSONs were lost when the rental was destroyed (artifacts/claude-rsn296-20260924/runs/*/DATA-LOSS.txt on origin/builder-outbox). The 8 checkpoints are on this Mac at ~/premonition-models/rsn296/<run>/. Re-run the SAME eval commands on the CPU so the director can recount from files. No training, no rental, no GPU. Never edit code.
INDEPENDENCE: never open or print any item of artifacts/claude-reasonpanel296-20260924/ or artifacts/claude-reasonpanel294-20260923/. The eval commands write category-level counts only; report only those.

1. From the worktree root, after git fetch -q origin main, use a clean export of origin/main (git archive origin/main | tar -x -C /tmp/rsn296re) and run everything from /tmp/rsn296re. `shasum -a 256 -c` artifacts/claude-rsn296-20260924/SEAL-code.sha256.txt, artifacts/claude-reasonpanel296-20260924/SEAL-v2.sha256.txt and artifacts/claude-reasonpanel294-20260923/SEAL-v3.sha256.txt: every line OK, else stop and report.
2. Check the 8 checkpoints against origin/builder-outbox:artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt (its paths are W/<run>/<file>; map W/ to ~/premonition-models/rsn296/). Every line must match, else stop and report.
3. For each run R in plain-s1 plain-s2 loop-s1 loop-s2 and C in copy_only final (at most 4 processes at once, --device cpu):
   python -B scripts/claude_rsn296_run.py eval --device cpu --ckpt ~/premonition-models/rsn296/R/C.pt --panel artifacts/claude-reasonpanel296-20260924/items-v2.jsonl --out OUT/R/panel296-<copy|final>.json
   python -B scripts/claude_rsn296_run.py eval --device cpu --ckpt ~/premonition-models/rsn296/R/C.pt --panel artifacts/claude-reasonpanel294-20260923/items-v3.jsonl --out OUT/R/panel294-<copy|final>.json
   (C.pt is copy_only.pt or final.pt; <copy|final> is copy for copy_only.pt.) OUT = artifacts/claude-rsn296-20260924/reeval-cpu in the worktree.
4. REEVAL.md in OUT: for each of the 16 files, the "total" block (checked_right, raw_right, checked_answered_without_fact, raw_answered_without_fact, checked_idk, checked_wrong) as integers, and whether checked_right equals the number printed in RESULTS.md on origin/builder-outbox. Report every difference; do not explain it away.
PUSH: artifacts/claude-rsn296-20260924/reeval-cpu
