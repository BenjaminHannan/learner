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
YOUR TASK: spending guard for rsn-351b-train (Ben 21:51 UTC: "don't use gpu rentals above 4$"; the $4 is the COMBINED limit per job, re-rents and extra machines included). You rent nothing and change no files except one ledger line.
- Read the vast.ai key only as $(cat ~/.config/vastai/vast_api_key); never print it.
- Every 60 s: run `vastai show instances --raw`. Take every instance whose label starts with "fair351b". Keep a running total, and never forget an instance after it disappears: for each instance id first seen, record its dph (dph_total) and its start time; its cost so far = dph × hours since start (or until it vanished).
- When the combined total of all fair351b* instances seen since you started reaches $3.80: destroy every live fair351b* instance by exact instance id (vastai destroy instance <id>), confirm they are gone, and append a line to artifacts/fable-predictions-ledger.md (cat >>) saying GUARD-STOP with the total.
- Stop watching when runs/rsn-351b-train/rsn-351b-train.exit exists on origin/builder-outbox (git fetch -q origin builder-outbox; git ls-tree) AND no fair351b* instance has been live for 5 min, or after 8 hours.
- Never touch an instance whose label does not start with fair351b.
Final reply: the instance ids seen, the dph and minutes of each, the combined dollars, and whether you had to stop anything.
PUSH: artifacts/fable-predictions-ledger.md
