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

YOUR TASK: rsn-296-diag (report-only diagnosis, CPU, no training, no rental). Run the director's sealed diagnosis script on the two kept plain checkpoints. It uses GENERATED episodes only; it never opens a panel. Never edit code.
1. Clean export of origin/main to /tmp/rsn296diag (git archive origin/main | tar -x -C /tmp/rsn296diag); run from there. Check the checkpoints ~/premonition-models/rsn296/plain-s1/final.pt and plain-s2/final.pt against origin/builder-outbox:artifacts/claude-rsn296-20260924/SEAL-run.sha256.txt (W/ = ~/premonition-models/rsn296/). Mismatch = stop and report.
2. For R in plain-s1 plain-s2 (both may run at once):
   python -B scripts/claude_rsn296_diag.py --device cpu --n 200 --ckpt ~/premonition-models/rsn296/R/final.pt --out OUT/diag-R.json > OUT/diag-R.txt
   OUT = artifacts/claude-rsn296-20260924/diag-cpu in the worktree.
3. Your final reply: the two printed tables verbatim, and any error. No interpretation needed.
PUSH: artifacts/claude-rsn296-20260924/diag-cpu
