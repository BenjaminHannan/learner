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



GPU: rent
DISK: 1
BUDGET: $0 (rents nothing; reads files off the running rent-358i rental, Sleep research asked 14:16 UTC 09-26)
YOUR TASK: save rsn-358i's trained nets before its rental is destroyed (director, 14:18 UTC). Rent nothing. Never stop, write to, or destroy any instance; READ ONLY on the rent-358i box; never touch its processes. Key only via $(cat ~/.config/vastai/vast_api_key), never printed.
1. Find the instance whose label contains 358i (`vastai show instances`). Poll every 3 min for up to 170 min: over ssh, list W/loop-s{1..4}/final.pt and W/plain-s{1..4}/final.pt under the run's work dir (find ~ -path '*loop-s*/final.pt' -o -path '*plain-s*/final.pt'). As soon as all 8 exist and none changed size across two polls, copy them with scp to ~/premonition-models/rsn358i/<run>/<same subpath> on the Mac, only if `df -g /` shows >= 6 GB free first. If the instance disappears first, stop and report GONE with whatever was copied.
2. On the Mac, sha256 each file and compare with SEAL-run.sha256.txt from the rental (copy that file too) or from origin/builder-outbox artifacts/*358i*/ once pushed. Report matches.
Write artifacts/claude-grab358i-20260926/REPORT.md (file list, sizes, sha matches). Do not push the .pt files.
PUSH: artifacts/claude-grab358i-20260926/REPORT.md
