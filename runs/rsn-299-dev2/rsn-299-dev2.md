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
GPU: yes (BensPC RTX 5070 Ti; one job at a time). SHORT: about 10 minutes of GPU. Hard cap 30 minutes; stop and report if passed.

YOUR TASK: rsn-299-dev2 (a short PRACTICE run to check the prompt format; not a registered test). rsn-299-dev stopped with NO-BASE because the 1B is not on the Mac; it is on BensPC. Never edit code.
GETTING THE CODE: a fresh `git archive origin/main` copied to BensPC; run from its root. `python -B scripts/claude_rsn299_tool.py` must print "selftest ok".
MODEL on BensPC (never download any other model): BASE = openbmb/MiniCPM5-1B via huggingface_hub.snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True) (Ben's yes 2026-09-23 11:01 UTC covers it; only if that fails, download it once). Record the commit hash. Use the lis-301 venv (torch + transformers).
RUN on the DEV items only (artifacts/claude-rsn299-20260924/dev.jsonl, 16 items, not blind), one after the other:
   python -B scripts/claude_rsn299_run.py run --arm P --model BASE --items artifacts/claude-rsn299-20260924/dev.jsonl --out OUT/dev-P.jsonl
   python -B scripts/claude_rsn299_run.py run --arm T --model BASE --items artifacts/claude-rsn299-20260924/dev.jsonl --out OUT/dev-T.jsonl
   python -B scripts/claude_rsn299_run.py score --items artifacts/claude-rsn299-20260924/dev.jsonl --p OUT/dev-P.jsonl --t OUT/dev-T.jsonl --out OUT/dev-score.json
   OUT = artifacts/claude-rsn299-20260924/dev-pc. Copy OUT back to the Mac worktree.
Final reply: the printed score JSON, the model commit hash, GPU name, median seconds per item for each arm, and the full "steps" text of dev items d01, d04, d07, d10, d13, d15 for BOTH arms, verbatim.
PUSH: artifacts/claude-rsn299-20260924/dev-pc
